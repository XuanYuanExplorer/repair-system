"""值日与卫生服务：周视图、轮换规则、排班生成、卫生检查与整改。"""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BizError, ErrCode
from app.core.timeutil import current_week_no, human_dt, iso, local_date_str, local_today, utcnow, week_start_of
from app.models import DutyRule, DutySchedule, HygieneCheck, User
from app.services.audit import write_audit
from app.services.dorm_service import current_room
from app.services.notify_service import send_message

LEVEL_LABEL = {"excellent": "优秀", "good": "良好", "pass": "合格", "fail": "不合格"}
WEEKDAY_CN = ["一", "二", "三", "四", "五", "六", "日"]


async def _rule(session: AsyncSession, room_id: int) -> DutyRule | None:
    return await session.get(DutyRule, room_id)


async def schedule(session: AsyncSession, user: User, week_start: date | None) -> dict:
    room, bed = await current_room(session, user)
    start = week_start or week_start_of(local_today())
    start = week_start_of(start)
    rule = await _rule(session, room.id)
    rows = (
        await session.scalars(
            select(DutySchedule).where(DutySchedule.room_id == room.id, DutySchedule.week_start == start).order_by(DutySchedule.weekday)
        )
    ).all()
    today = local_today()
    items = []
    for i in range(7):
        d = start + timedelta(days=i)
        row = next((r for r in rows if r.weekday == i + 1), None)
        person = await session.get(User, row.user_id) if row and row.user_id else None
        items.append(
            {
                "id": row.id if row else None,
                "weekday": i + 1,
                "weekday_cn": WEEKDAY_CN[i],
                "date": local_date_str(d),
                "user_id": row.user_id if row else None,
                "user_name": person.name if person else ("全员" if row else None),
                "short_name": (person.name[0] if person else ("全员" if row else "—")),
                "areas": (row.areas if row and row.areas else (rule.areas if rule else [])),
                "is_today": d == today,
                "reminded": bool(row.reminded_at) if row else False,
            }
        )
    today_item = next((i for i in items if i["is_today"]), None)
    return {
        "week_start": local_date_str(start),
        "week_no": start.isocalendar().week,
        "items": items,
        "today": today_item,
        "areas": rule.areas if rule else [],
        "can_edit": room.leader_id == user.id,
        "is_empty": len(rows) == 0,
        "rule": {
            "mode": rule.mode if rule else "daily",
            "member_order": rule.member_order if rule else [],
            "areas": rule.areas if rule else [],
        },
    }


async def get_rule(session: AsyncSession, user: User) -> dict:
    room, _ = await current_room(session, user)
    rule = await _rule(session, room.id)
    members = []
    if rule and rule.member_order:
        for uid in rule.member_order:
            if not uid:
                continue
            u = await session.get(User, uid)
            if u:
                members.append({"id": u.id, "name": u.name})
    return {
        "mode": rule.mode if rule else "daily",
        "member_order": rule.member_order if rule else [],
        "areas": rule.areas if rule else ["地面", "桌面", "阳台", "卫浴"],
        "members": members,
        "can_edit": room.leader_id == user.id,
    }


async def update_rule(session: AsyncSession, user: User, payload) -> dict:
    room, _ = await current_room(session, user)
    if room.leader_id != user.id:
        raise BizError(ErrCode.FORBIDDEN)
    rule = await _rule(session, room.id)
    if rule is None:
        rule = DutyRule(room_id=room.id, anchor_date=local_today())
        session.add(rule)
    rule.mode = payload.mode
    rule.member_order = payload.member_order or rule.member_order
    rule.areas = payload.areas or rule.areas
    await write_audit(session, actor_id=user.id, action="duty.rule.update", target_type="room", target_id=room.id)
    await session.commit()
    return await get_rule(session, user)


async def generate(session: AsyncSession, user: User, week_start: date | None) -> dict:
    room, _ = await current_room(session, user)
    if room.leader_id != user.id:
        raise BizError(ErrCode.FORBIDDEN)
    rule = await _rule(session, room.id)
    if rule is None or not rule.member_order:
        raise BizError(ErrCode.CONFLICT, "请先设置值日轮换规则")

    start = week_start_of(week_start or local_today())
    order = [uid for uid in rule.member_order]
    today = local_today()
    created = 0
    for i in range(7):
        d = start + timedelta(days=i)
        idx = (d - rule.anchor_date).days % len(order) if order else 0
        uid = order[idx] if order else None
        uid = uid or None
        existing = await session.scalar(
            select(DutySchedule).where(
                DutySchedule.room_id == room.id, DutySchedule.week_start == start, DutySchedule.weekday == i + 1
            )
        )
        if existing:
            if d >= today:
                existing.user_id = uid
                existing.duty_date = d
                existing.areas = rule.areas
            continue
        session.add(
            DutySchedule(
                room_id=room.id, week_start=start, weekday=i + 1, user_id=uid, duty_date=d, areas=rule.areas
            )
        )
        created += 1
    await write_audit(session, actor_id=user.id, action="duty.schedule.generate", target_type="room", target_id=room.id)
    await session.commit()
    return await schedule(session, user, start)


async def update_day(session: AsyncSession, user: User, schedule_id: int, payload) -> dict:
    room, _ = await current_room(session, user)
    if room.leader_id != user.id:
        raise BizError(ErrCode.FORBIDDEN)
    row = await session.get(DutySchedule, schedule_id)
    if row is None or row.room_id != room.id:
        raise BizError(ErrCode.NOT_FOUND, "排班不存在")
    if payload.user_id is not None:
        row.user_id = payload.user_id or None
    if payload.areas is not None:
        row.areas = payload.areas
    await write_audit(session, actor_id=user.id, action="duty.schedule.update", target_type="duty", target_id=row.id)
    await session.commit()
    return await schedule(session, user, row.week_start)


async def hygiene_checks(session: AsyncSession, user: User, page: int, page_size: int) -> dict:
    room, _ = await current_room(session, user)
    total = int(
        await session.scalar(select(func.count()).select_from(HygieneCheck).where(HygieneCheck.room_id == room.id)) or 0
    )
    rows = (
        await session.scalars(
            select(HygieneCheck)
            .where(HygieneCheck.room_id == room.id)
            .order_by(HygieneCheck.check_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    avg = await session.scalar(select(func.avg(HygieneCheck.score)).where(HygieneCheck.room_id == room.id))
    return {
        "items": [
            {
                "id": h.id,
                "check_date": local_date_str(h.check_date),
                "date_text": h.check_date.strftime("%m-%d"),
                "week_no": h.week_no,
                "score": h.score,
                "level": h.level,
                "level_label": LEVEL_LABEL[h.level],
                "deductions": h.deductions or [],
                "deduction_text": "、".join(f"{d['item']} {d['score']}" for d in (h.deductions or [])) or "无扣分项",
                "requirement": h.requirement,
                "rectify_status": h.rectify_status,
                "rectify_media": h.rectify_media or [],
                "can_rectify": h.rectify_status in ("required", "submitted") and room.leader_id == user.id,
            }
            for h in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
        "average": round(float(avg), 1) if avg is not None else None,
        "can_edit": room.leader_id == user.id,
    }


async def rectify(session: AsyncSession, user: User, check_id: int, media_urls: list[str]) -> dict:
    room, _ = await current_room(session, user)
    if room.leader_id != user.id:
        raise BizError(ErrCode.FORBIDDEN)
    check = await session.get(HygieneCheck, check_id)
    if check is None or check.room_id != room.id:
        raise BizError(ErrCode.NOT_FOUND, "检查记录不存在")
    if len(media_urls) > 4:
        raise BizError(ErrCode.MEDIA_LIMIT, "整改照片最多 4 张")
    check.rectify_status = "submitted"
    check.rectify_media = media_urls
    check.rectify_at = utcnow()
    await write_audit(session, actor_id=user.id, action="hygiene.rectify", target_type="hygiene", target_id=check.id)
    await session.commit()
    return {"id": check.id, "rectify_status": check.rectify_status, "rectify_at": iso(check.rectify_at)}


async def duty_reminder(session: AsyncSession) -> int:
    today = local_today()
    rows = (
        await session.scalars(
            select(DutySchedule).where(DutySchedule.duty_date == today, DutySchedule.reminded_at.is_(None))
        )
    ).all()
    for row in rows:
        if not row.user_id:
            row.reminded_at = utcnow()
            continue
        await send_message(
            session,
            row.user_id,
            "notice",
            "今日值日提醒",
            f"今天由你负责值日：{'、'.join(row.areas or [])}",
            "duty",
            row.id,
            dedup=False,
        )
        row.reminded_at = utcnow()
    await session.commit()
    return len(rows)


def week_label(week_start: date) -> str:
    return f"W{current_week_no(week_start)}"


def fmt_human(dt) -> str | None:
    return human_dt(dt)
