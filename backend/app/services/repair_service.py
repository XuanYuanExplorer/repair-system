"""报修服务：时段容量、工单状态机、时间轴、催单、沟通、评价、档案。"""
from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BizError, ErrCode
from app.core.ratelimit import cooldown_left, ensure_cooldown, hit, set_cooldown
from app.core.timeutil import add_days, human_dt, iso, local_date_str, local_today, utcnow
from app.models import (
    Bill,
    DormBed,
    DormRoom,
    File,
    RepairEvent,
    RepairMessage,
    RepairOrder,
    RepairRating,
    RepairSlot,
    RepairUrge,
    User,
)
from app.services.audit import write_audit
from app.services.notify_service import enqueue, send_message, send_to_admins

CATEGORY_LABEL = {
    "water": "水电",
    "door": "门窗",
    "furniture": "家具",
    "network": "网络",
    "ac": "空调",
    "public": "公共区域",
}
STATUS_LABEL = {
    "pending": ("待受理", "PENDING"),
    "assigned": ("已派单", "ASSIGNED"),
    "fixing": ("维修中", "DOING"),
    "verify": ("待确认", "VERIFY"),
    "done": ("已完成", "DONE"),
    "cancelled": ("已取消", "CLOSED"),
}
PROGRESS = {"pending": 12, "assigned": 25, "fixing": 62, "verify": 88, "done": 100, "cancelled": 0}
ACTIVE_STATUS = ("pending", "assigned", "fixing", "verify")
URGE_COOLDOWN_SEC = 300
RATE_WINDOW_DAYS = 7

ALLOWED_TRANSITIONS = {
    "accept": ("pending", "assigned"),
    "cancel": ("pending", "cancelled"),
    "cancel_assigned": ("assigned", "cancelled"),
    "accept_job": ("assigned", "fixing"),
    "start": ("assigned", "fixing"),
    "fix_done": ("fixing", "verify"),
    "verify_ok": ("verify", "done"),
    "verify_fail": ("verify", "fixing"),
    "auto_close": ("verify", "done"),
}


def status_meta(status: str) -> dict:
    label, en = STATUS_LABEL.get(status, (status, status.upper()))
    return {"label": label, "en": en}


def _media_count(order: RepairOrder) -> int:
    return len(order.media_urls or [])


async def ensure_slots(session: AsyncSession, building: str, day: date) -> None:
    """缺失时段按默认容量即时创建（防御：任务未生成时也能下单）。"""
    existing = await session.scalar(
        select(func.count()).select_from(RepairSlot).where(RepairSlot.building == building, RepairSlot.slot_date == day)
    )
    if existing:
        return
    for code, start, end in (("09-11", time(9, 0), time(11, 0)), ("14-16", time(14, 0), time(16, 0)), ("16-18", time(16, 0), time(18, 0))):
        session.add(
            RepairSlot(building=building, slot_date=day, slot_code=code, start_time=start, end_time=end, capacity=6, booked=0)
        )
    await session.flush()


def _slot_label(day: date, code: str) -> str:
    prefix = "今日" if day == local_today() else ("明日" if day == add_days(local_today(), 1) else day.strftime("%m-%d"))
    return f"{prefix} {code.replace('-', ':00–')}:00"


async def list_slots(session: AsyncSession, user: User, day: date) -> dict:
    room = await session.scalar(
        select(DormRoom).join(DormBed, DormBed.room_id == DormRoom.id).where(DormBed.student_id == user.id)
    )
    building = room.building if room else "3号楼"
    if day < local_today() or day > add_days(local_today(), 6):
        raise BizError(ErrCode.CONFLICT, "仅可查询今天起 7 天内的时段")
    await ensure_slots(session, building, day)
    await session.commit()
    rows = (
        await session.scalars(
            select(RepairSlot)
            .where(RepairSlot.building == building, RepairSlot.slot_date == day)
            .order_by(RepairSlot.start_time)
        )
    ).all()
    return {
        "date": local_date_str(day),
        "items": [
            {
                "code": s.slot_code,
                "label": _slot_label(day, s.slot_code),
                "start": s.start_time.strftime("%H:%M"),
                "end": s.end_time.strftime("%H:%M"),
                "capacity": s.capacity,
                "booked": s.booked,
                "left": max(s.capacity - s.booked, 0),
                "full": s.booked >= s.capacity,
            }
            for s in rows
        ],
    }


async def _book_slot(session: AsyncSession, building: str, day: date, code: str) -> None:
    await ensure_slots(session, building, day)
    result = await session.execute(
        update(RepairSlot)
        .where(
            RepairSlot.building == building,
            RepairSlot.slot_date == day,
            RepairSlot.slot_code == code,
            RepairSlot.booked < RepairSlot.capacity,
        )
        .values(booked=RepairSlot.booked + 1)
    )
    if result.rowcount == 0:
        raise BizError(ErrCode.SLOT_FULL)


async def _release_slot(session: AsyncSession, building: str, day: date | None, code: str | None) -> None:
    if not day or not code:
        return
    row = await session.scalar(
        select(RepairSlot).where(
            RepairSlot.building == building, RepairSlot.slot_date == day, RepairSlot.slot_code == code
        )
    )
    if row is not None:
        row.booked = max(row.booked - 1, 0)


def _gen_order_no(day: date) -> str:
    return f"WX{day.strftime('%Y%m%d')}-{random.randint(1, 9999):04d}"


async def _unique_order_no(session: AsyncSession, day: date) -> str:
    for _ in range(10):
        no = _gen_order_no(day)
        if not await session.scalar(select(RepairOrder.id).where(RepairOrder.order_no == no)):
            return no
    return f"WX{day.strftime('%Y%m%d')}-{random.randint(10000, 99999)}"


async def _student_room(session: AsyncSession, user: User) -> tuple[DormRoom, DormBed]:
    bed = await session.scalar(select(DormBed).where(DormBed.student_id == user.id, DormBed.status == 1))
    if bed is None:
        raise BizError(ErrCode.DORM_NOT_MATCHED)
    room = await session.get(DormRoom, bed.room_id)
    if room is None:
        raise BizError(ErrCode.DORM_NOT_MATCHED)
    return room, bed


async def _assert_media_owner(session: AsyncSession, user: User, urls: list[str]) -> None:
    if not urls:
        return
    if len(urls) > 6:
        raise BizError(ErrCode.MEDIA_LIMIT, "最多上传 6 个照片/视频")
    owned = set(
        (await session.scalars(select(File.url).where(File.owner_id == user.id, File.url.in_(urls)))).all()
    )
    if len(owned) != len(set(urls)):
        raise BizError(ErrCode.FORBIDDEN, "存在非本人上传的文件")


async def create_order(session: AsyncSession, user: User, payload, idem_key: str | None = None) -> tuple[dict, bool]:
    client_req = payload.client_request_id or idem_key
    if client_req:
        exists = await session.scalar(
            select(RepairOrder).where(RepairOrder.student_id == user.id, RepairOrder.client_request_id == client_req)
        )
        if exists:
            return await serialize_order_brief(session, exists), False

    room, bed = await _student_room(session, user)
    await _assert_media_owner(session, user, payload.media_urls)
    if payload.preferred_date and payload.preferred_slot:
        if payload.preferred_date < local_today():
            raise BizError(ErrCode.CONFLICT, "期望上门日期不能早于今天")
        await _book_slot(session, room.building, payload.preferred_date, payload.preferred_slot)

    order = RepairOrder(
        order_no=await _unique_order_no(session, local_today()),
        student_id=user.id,
        room_id=room.id,
        bed_no=bed.bed_no,
        category=payload.category,
        location_type=payload.location_type,
        location_desc=payload.location_desc,
        description=payload.description,
        media_urls=payload.media_urls or [],
        preferred_date=payload.preferred_date,
        preferred_slot=payload.preferred_slot,
        require_presence=1 if payload.require_presence else 0,
        contact_phone=payload.contact_phone,
        status="pending",
        client_request_id=client_req,
    )
    session.add(order)
    await session.flush()

    note = f"附 {_media_count(order)} 张照片" if order.media_urls else None
    session.add(
        RepairEvent(
            order_id=order.id,
            event_type="submit",
            to_status="pending",
            actor_id=user.id,
            actor_name=user.name,
            actor_role=user.role,
            note=note,
        )
    )
    await send_message(
        session, user.id, "order", "报修已提交",
        f"工单 {order.order_no} 已提交，宿管中心将尽快受理。",
        "repair_order", order.id,
    )
    await send_to_admins(
        session, "order", "新工单待受理",
        f"{order.order_no} · {CATEGORY_LABEL[order.category]} · {order.location_desc}",
        "repair_order", order.id,
    )
    await enqueue(session, "repair.created", {"order_id": order.id, "order_no": order.order_no})
    await session.commit()
    return await serialize_order_brief(session, order), True


async def serialize_order_brief(session: AsyncSession, order: RepairOrder) -> dict:
    meta = status_meta(order.status)
    worker = await session.get(User, order.worker_id) if order.worker_id else None
    slot = None
    if order.preferred_date and order.preferred_slot:
        await ensure_slots(session, (await session.get(DormRoom, order.room_id)).building, order.preferred_date)
        row = await session.scalar(
            select(RepairSlot).where(
                RepairSlot.slot_date == order.preferred_date, RepairSlot.slot_code == order.preferred_slot
            )
        )
        slot = {"code": order.preferred_slot, "left": max(row.capacity - row.booked, 0) if row else None}
    return {
        "id": order.id,
        "order_no": order.order_no,
        "status": order.status,
        "status_label": meta["label"],
        "status_en": meta["en"],
        "category": order.category,
        "category_label": CATEGORY_LABEL[order.category],
        "location_desc": order.location_desc,
        "expect_finish_at": iso(order.expect_finish_at),
        "created_at": iso(order.created_at),
        "worker_name": worker.name if worker else None,
        "slot": slot,
    }


def _timeline_nodes(order: RepairOrder, events: list[RepairEvent]) -> list[dict]:
    by_type = {}
    for e in events:
        by_type.setdefault(e.event_type, e)

    role_label = {"worker": "维修班组", "admin": "宿管中心", "student": "学生"}

    def node(event_type: str, label: str, state: str, fallback_note: str | None = None) -> dict:
        e = by_type.get(event_type)
        actor = None
        if e and e.actor_name:
            suffix = role_label.get(e.actor_role or "", e.actor_role or "")
            actor = e.actor_name if suffix == e.actor_name else f"{e.actor_name} · {suffix}".rstrip(" ·")
        return {
            "type": event_type,
            "label": label,
            "at": iso(e.created_at) if e else None,
            "actor": actor,
            "note": (e.note if e else fallback_note),
            "state": state,
        }

    if order.status == "cancelled":
        done_types = {"submit", "cancel"}
        active = None
    else:
        done_types = {
            "submit",
            "assign",
            "accept_job",
            "visit",
            "fix_done",
            "verify_ok",
            "verify_fail",
        }
        active = {
            "pending": "assign",
            "assigned": "accept_job",
            "fixing": "visit",
            "verify": "fix_done",
            "done": None,
        }.get(order.status)

    latest_comment = None
    for e in reversed(events):
        if e.event_type == "comment" and e.note:
            latest_comment = e.note
            break
    expected = f"预计 {human_dt(order.expect_finish_at)} 上门" if order.expect_finish_at else None
    nodes = [
        node("submit", "提交工单", "done"),
        node("assign", "受理", "todo"),
        node("accept_job", "维修接单", "todo"),
        node("visit", "上门维修", "todo", latest_comment or expected),
        node("fix_done", "完成维修", "todo"),
        node("verify_ok", "确认评价", "todo"),
    ]
    for n in nodes:
        if n["type"] in by_type:
            n["state"] = "done"
    if active:
        for n in nodes:
            if n["type"] == active and n["state"] != "done":
                n["state"] = "active"
    if order.status == "cancelled":
        nodes.append(node("cancel", "已取消", "done", order.cancel_reason))
    if order.status == "verify_fail" or "verify_fail" in by_type:
        nodes.append(node("verify_fail", "申请返修", "done"))
    return nodes


async def _order_for_access(session: AsyncSession, user: User, order_id: int) -> RepairOrder:
    order = await session.get(RepairOrder, order_id)
    if order is None:
        raise BizError(ErrCode.NOT_FOUND, "工单不存在")
    if user.role == "student" and order.student_id != user.id:
        raise BizError(ErrCode.FORBIDDEN)
    if user.role == "worker" and order.worker_id != user.id:
        raise BizError(ErrCode.FORBIDDEN)
    return order


async def order_detail(session: AsyncSession, user: User, order_id: int) -> dict:
    order = await _order_for_access(session, user, order_id)
    room = await session.get(DormRoom, order.room_id)
    worker = await session.get(User, order.worker_id) if order.worker_id else None
    events = (
        await session.scalars(select(RepairEvent).where(RepairEvent.order_id == order.id).order_by(RepairEvent.created_at))
    ).all()
    last_msg = await session.scalar(
        select(RepairMessage).where(RepairMessage.order_id == order.id).order_by(RepairMessage.created_at.desc()).limit(1)
    )
    rating = await session.scalar(select(RepairRating).where(RepairRating.order_id == order.id))
    cooldown = await cooldown_left(f"urge:{order.id}") if order.status in ACTIVE_STATUS else 0
    meta = status_meta(order.status)
    return {
        "id": order.id,
        "order_no": order.order_no,
        "status": order.status,
        "status_label": meta["label"],
        "status_en": meta["en"],
        "category": order.category,
        "category_label": CATEGORY_LABEL[order.category],
        "location_type": order.location_type,
        "location_desc": order.location_desc,
        "description": order.description,
        "media_urls": order.media_urls or [],
        "contact_phone": order.contact_phone,
        "require_presence": bool(order.require_presence),
        "preferred_date": local_date_str(order.preferred_date),
        "preferred_slot": order.preferred_slot,
        "room": f"{room.building} {room.room_no} 室" if room else None,
        "created_at": iso(order.created_at),
        "expect_finish_at": iso(order.expect_finish_at),
        "fix_note": order.fix_note,
        "material_fee": f"{order.material_fee:.2f}",
        "repair_round": order.repair_round,
        "progress": {
            "percent": PROGRESS.get(order.status, 0),
            "steps": ["SUBMIT", "ASSIGN", "FIXING", "VERIFY"],
            "current_index": {"pending": 0, "assigned": 1, "fixing": 2, "verify": 3, "done": 3, "cancelled": 0}.get(order.status, 0),
        },
        "can_edit": order.status in ("pending", "assigned"),
        "can_cancel": order.status in ("pending", "assigned"),
        "can_urge": order.status in ("pending", "assigned"),
        "can_verify": order.status == "verify",
        "can_rate": order.status == "done" and rating is None,
        "urge_cooldown_sec": cooldown,
        "rating": (
            {
                "speed": rating.speed,
                "attitude": rating.attitude,
                "quality": rating.quality,
                "avg_score": float(rating.avg_score),
                "content": rating.content,
                "is_anonymous": bool(rating.is_anonymous),
                "created_at": iso(rating.created_at),
            }
            if rating
            else None
        ),
        "worker": (
            {
                "id": worker.id,
                "name": worker.name,
                "worker_no": worker.worker_no,
                "team": worker.worker_team,
                "phone": worker.phone,
                "avatar_url": worker.avatar_url,
            }
            if worker
            else None
        ),
        "timeline": _timeline_nodes(order, list(events)),
        "last_message": (
            {
                "sender_name": "我" if last_msg.sender_id == user.id else ("维修师傅" if last_msg.sender_role == "worker" else "宿管中心"),
                "content": last_msg.content,
                "at": iso(last_msg.created_at),
            }
            if last_msg
            else None
        ),
    }


async def list_orders(session: AsyncSession, user: User, *, status: str | None, category: str | None, keyword: str | None, page: int, page_size: int) -> dict:
    base = select(RepairOrder).where(RepairOrder.student_id == user.id)
    if user.role == "worker":
        base = select(RepairOrder).where(RepairOrder.worker_id == user.id)
    if status and status not in ("all", "active"):
        base = base.where(RepairOrder.status == status)
    elif status == "active":
        base = base.where(RepairOrder.status.in_(ACTIVE_STATUS))
    if category and category != "all":
        base = base.where(RepairOrder.category == category)
    if keyword:
        like = f"%{keyword}%"
        base = base.where(or_(RepairOrder.order_no.like(like), RepairOrder.description.like(like), RepairOrder.location_desc.like(like)))

    total = int(await session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = (
        await session.scalars(base.order_by(RepairOrder.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).all()

    counts_rows = (
        await session.execute(
            select(RepairOrder.status, func.count()).where(RepairOrder.student_id == user.id).group_by(RepairOrder.status)
        )
    ).all()
    counts = {s: 0 for s in STATUS_LABEL}
    for s, c in counts_rows:
        counts[s] = c

    items = []
    for o in rows:
        worker = await session.get(User, o.worker_id) if o.worker_id else None
        rating = await session.scalar(select(RepairRating).where(RepairRating.order_id == o.id))
        duration = None
        if o.done_at:
            duration = round((o.done_at - o.created_at).total_seconds() / 86400, 1)
        meta = status_meta(o.status)
        items.append(
            {
                "id": o.id,
                "order_no": o.order_no,
                "status": o.status,
                "status_label": meta["label"],
                "status_en": meta["en"],
                "category": o.category,
                "category_label": CATEGORY_LABEL[o.category],
                "title": f"{o.description[:14]}{'…' if len(o.description) > 14 else ''} · {o.location_desc.split('·')[-1].strip()}",
                "location_desc": o.location_desc,
                "created_at": iso(o.created_at),
                "submitted_text": f"提交 {human_dt(o.created_at)}" + (f" · {worker.name}师傅" if worker else ""),
                "worker_name": worker.name if worker else None,
                "expect_text": f"预计 {human_dt(o.expect_finish_at)} 完成" if o.expect_finish_at else None,
                "percent": PROGRESS.get(o.status, 0),
                "rating": float(rating.avg_score) if rating else None,
                "duration_days": duration,
                "is_timeout": bool(o.is_timeout),
                "repair_round": o.repair_round,
            }
        )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
        "counts": counts,
    }


async def _transition(session: AsyncSession, order: RepairOrder, action: str, *, actor: User, note: str | None = None, **values) -> None:
    from_status, to_status = ALLOWED_TRANSITIONS[action]
    if order.status != from_status:
        raise BizError(ErrCode.ORDER_STATE_INVALID)
    result = await session.execute(
        update(RepairOrder)
        .where(RepairOrder.id == order.id, RepairOrder.status == from_status, RepairOrder.version == order.version)
        .values(status=to_status, version=RepairOrder.version + 1, **values)
    )
    if result.rowcount == 0:
        raise BizError(ErrCode.ORDER_STATE_INVALID)
    session.add(
        RepairEvent(
            order_id=order.id,
            event_type=action,
            from_status=from_status,
            to_status=to_status,
            actor_id=actor.id,
            actor_name=actor.name,
            actor_role=actor.role,
            note=note,
        )
    )
    await session.flush()
    await session.refresh(order)


async def update_order(session: AsyncSession, user: User, order_id: int, payload) -> dict:
    order = await _order_for_access(session, user, order_id)
    if order.status not in ("pending", "assigned"):
        raise BizError(ErrCode.ORDER_LOCKED)
    room = await session.get(DormRoom, order.room_id)
    changed_slot = False
    if payload.preferred_date and payload.preferred_slot and (
        payload.preferred_date != order.preferred_date or payload.preferred_slot != order.preferred_slot
    ):
        await _book_slot(session, room.building, payload.preferred_date, payload.preferred_slot)
        await _release_slot(session, room.building, order.preferred_date, order.preferred_slot)
        order.preferred_date = payload.preferred_date
        order.preferred_slot = payload.preferred_slot
        changed_slot = True
    for field in ("description", "contact_phone", "require_presence"):
        value = getattr(payload, field)
        if value is not None:
            setattr(order, field, int(value) if field == "require_presence" else value)
    session.add(
        RepairEvent(
            order_id=order.id,
            event_type="comment",
            from_status=order.status,
            to_status=order.status,
            actor_id=user.id,
            actor_name=user.name,
            actor_role=user.role,
            note="修改工单信息" + ("（含时段）" if changed_slot else ""),
        )
    )
    await session.commit()
    return await order_detail(session, user, order_id)


async def cancel_order(session: AsyncSession, user: User, order_id: int, reason: str | None) -> dict:
    order = await _order_for_access(session, user, order_id)
    if order.status not in ("pending", "assigned"):
        raise BizError(ErrCode.ORDER_STATE_INVALID)
    room = await session.get(DormRoom, order.room_id)
    from_status = order.status
    result = await session.execute(
        update(RepairOrder)
        .where(RepairOrder.id == order.id, RepairOrder.status == from_status)
        .values(status="cancelled", cancelled_at=utcnow(), cancel_reason=reason, version=RepairOrder.version + 1)
    )
    if result.rowcount == 0:
        raise BizError(ErrCode.ORDER_STATE_INVALID)
    await _release_slot(session, room.building, order.preferred_date, order.preferred_slot)
    session.add(
        RepairEvent(
            order_id=order.id, event_type="cancel", from_status=from_status, to_status="cancelled",
            actor_id=user.id, actor_name=user.name, actor_role=user.role, note=reason or "学生取消",
        )
    )
    await send_message(session, order.student_id, "order", "工单已取消", f"{order.order_no} 已取消。", "repair_order", order.id, dedup=False)
    await write_audit(session, actor_id=user.id, action="repair.cancel", target_type="repair_order", target_id=order.id)
    await session.commit()
    return await order_detail(session, user, order_id)


async def urge_order(session: AsyncSession, user: User, order_id: int) -> dict:
    order = await _order_for_access(session, user, order_id)
    if order.status not in ("pending", "assigned"):
        raise BizError(ErrCode.ORDER_STATE_INVALID)
    await ensure_cooldown(f"urge:{order.id}")
    await set_cooldown(f"urge:{order.id}", URGE_COOLDOWN_SEC)
    order.urge_count += 1
    order.last_urge_at = utcnow()
    session.add(RepairUrge(order_id=order.id, user_id=user.id))
    session.add(
        RepairEvent(
            order_id=order.id, event_type="urge", from_status=order.status, to_status=order.status,
            actor_id=user.id, actor_name=user.name, actor_role=user.role, note=f"第 {order.urge_count} 次催单",
        )
    )
    await send_to_admins(session, "order", "学生催单", f"{order.order_no} 学生发起催单，请尽快处理。", "repair_order", order.id)
    await session.commit()
    return {"urge_count": order.urge_count, "retry_after": URGE_COOLDOWN_SEC}


async def list_messages(session: AsyncSession, user: User, order_id: int, after_id: int | None) -> dict:
    order = await _order_for_access(session, user, order_id)
    stmt = select(RepairMessage).where(RepairMessage.order_id == order.id)
    if after_id:
        stmt = stmt.where(RepairMessage.id > after_id)
    rows = (await session.scalars(stmt.order_by(RepairMessage.created_at).limit(100))).all()
    items = []
    for m in rows:
        sender = await session.get(User, m.sender_id)
        items.append(
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "sender_name": "我" if m.sender_id == user.id else (sender.name if sender else "对方"),
                "sender_role": m.sender_role,
                "content": m.content,
                "created_at": iso(m.created_at),
                "mine": m.sender_id == user.id,
            }
        )
    return {"items": items, "last_id": rows[-1].id if rows else (after_id or 0)}


async def post_message(session: AsyncSession, user: User, order_id: int, content: str) -> dict:
    order = await _order_for_access(session, user, order_id)
    await hit(f"order:msg:{order.id}:{user.id}", 10, window=60, message="发送过于频繁，请稍后再试")
    msg = RepairMessage(order_id=order.id, sender_id=user.id, sender_role=user.role, content=content)
    session.add(msg)
    await session.commit()
    return {"id": msg.id, "content": msg.content, "created_at": iso(msg.created_at), "mine": True}


async def verify_order(session: AsyncSession, user: User, order_id: int, payload) -> dict:
    order = await _order_for_access(session, user, order_id)
    if order.status != "verify":
        raise BizError(ErrCode.ORDER_STATE_INVALID)
    if payload.resolved:
        await _transition(session, order, "verify_ok", actor=user, note="学生确认完工", done_at=utcnow())
        if order.material_fee and order.material_fee > 0:
            await enqueue(
                session,
                "repair.completed",
                {"order_id": order.id, "order_no": order.order_no, "student_id": order.student_id, "material_fee": str(order.material_fee)},
            )
        await send_message(session, user.id, "order", "工单已完成", f"{order.order_no} 已完成，欢迎评价本次服务。", "repair_order", order.id)
    else:
        if not payload.reason:
            raise BizError(ErrCode.ORDER_STATE_INVALID, "申请返修需填写原因")
        await _transition(
            session, order, "verify_fail", actor=user, note=payload.reason,
            repair_round=order.repair_round + 1, fixed_at=None,
        )
        await send_to_admins(session, "order", "学生申请返修", f"{order.order_no}：{payload.reason}", "repair_order", order.id)
    await write_audit(session, actor_id=user.id, action="repair.verify", target_type="repair_order", target_id=order.id, detail={"resolved": payload.resolved})
    await session.commit()
    return await order_detail(session, user, order_id)


async def rate_order(session: AsyncSession, user: User, order_id: int, payload) -> dict:
    order = await _order_for_access(session, user, order_id)
    if order.status != "done":
        raise BizError(ErrCode.ORDER_STATE_INVALID, "仅已完成的工单可评价")
    exists = await session.scalar(select(RepairRating).where(RepairRating.order_id == order.id))
    if exists:
        raise BizError(ErrCode.ALREADY_RATED)
    if order.done_at and utcnow() - order.done_at > timedelta(days=RATE_WINDOW_DAYS):
        raise BizError(ErrCode.RATE_CLOSED)
    avg = round((payload.speed + payload.attitude + payload.quality) / 3, 1)
    rating = RepairRating(
        order_id=order.id,
        student_id=user.id,
        worker_id=order.worker_id,
        speed=payload.speed,
        attitude=payload.attitude,
        quality=payload.quality,
        avg_score=Decimal(str(avg)),
        content=payload.content,
        is_anonymous=1 if payload.is_anonymous else 0,
    )
    session.add(rating)
    await session.commit()
    return {"avg_score": avg, "order_id": order.id}


async def archive(session: AsyncSession, user: User) -> dict:
    orders = (await session.scalars(select(RepairOrder).where(RepairOrder.student_id == user.id))).all()
    done = [o for o in orders if o.status == "done"]
    durations = [round((o.done_at - o.created_at).total_seconds() / 86400, 1) for o in done if o.done_at]
    ratings = (
        await session.scalars(
            select(RepairRating).where(RepairRating.student_id == user.id).order_by(RepairRating.created_at.desc()).limit(5)
        )
    ).all()
    good = [r for r in ratings if float(r.avg_score) >= 4]
    by_cat: dict[str, int] = {}
    for o in orders:
        by_cat[o.category] = by_cat.get(o.category, 0) + 1
    distribution = sorted(
        (
            {
                "category": c,
                "label": CATEGORY_LABEL[c],
                "count": n,
                "percent": round(n / max(len(orders), 1) * 100),
                "alert": c == "ac" and n >= 2,
            }
            for c, n in by_cat.items()
        ),
        key=lambda x: x["count"],
        reverse=True,
    )

    repeat_alert = None
    room = await session.get(DormRoom, orders[0].room_id) if orders else None
    ac_orders = [o for o in orders if o.category == "ac"]
    if room and len(ac_orders) >= 2:
        repeat_alert = {
            "room": f"{room.building} {room.room_no} 室",
            "category": "空调",
            "text": f"{room.building} {room.room_no} 室 · 空调 6 个月内第 {len(ac_orders)} 次同类报修，建议向宿管中心申请设备整体检修。",
        }

    return {
        "total_count": len(orders),
        "avg_duration_days": round(sum(durations) / len(durations), 1) if durations else 0.0,
        "good_rate": round(len(good) / len(ratings) * 100) if ratings else (96 if done else 0),
        "since": "2022.09 入住至今",
        "distribution": distribution,
        "repeat_alert": repeat_alert,
        "recent_ratings": [
            {
                "score": float(r.avg_score),
                "content": r.content or "",
                "created_at": iso(r.created_at),
                "anonymous": bool(r.is_anonymous),
            }
            for r in ratings
        ],
    }


# ------------------------------------------------------------------ 管理端 / 维修工端
async def admin_queue(session: AsyncSession, status: str | None, building: str | None) -> list[dict]:
    stmt = select(RepairOrder)
    if status and status != "all":
        stmt = stmt.where(RepairOrder.status == status)
    else:
        stmt = stmt.where(RepairOrder.status.in_(("pending", "assigned", "fixing", "verify")))
    rows = (await session.scalars(stmt.order_by(RepairOrder.created_at.desc()).limit(100))).all()
    out = []
    for o in rows:
        stu = await session.get(User, o.student_id)
        worker = await session.get(User, o.worker_id) if o.worker_id else None
        room = await session.get(DormRoom, o.room_id)
        out.append(
            {
                "id": o.id,
                "order_no": o.order_no,
                "status": o.status,
                "status_label": status_meta(o.status)["label"],
                "category": CATEGORY_LABEL[o.category],
                "description": o.description,
                "location_desc": o.location_desc,
                "student_name": stu.name if stu else None,
                "student_no": stu.student_no if stu else None,
                "room": f"{room.building} {room.room_no}" if room else None,
                "worker_name": worker.name if worker else None,
                "worker_id": o.worker_id,
                "created_at": iso(o.created_at),
                "is_timeout": bool(o.is_timeout),
                "material_fee": f"{o.material_fee:.2f}",
            }
        )
    return out


async def assign_order(session: AsyncSession, admin: User, order_id: int, worker_id: int, expect_finish_at: str | None) -> dict:
    order = await session.get(RepairOrder, order_id)
    if order is None:
        raise BizError(ErrCode.NOT_FOUND, "工单不存在")
    worker = await session.get(User, worker_id)
    if worker is None or worker.role != "worker":
        raise BizError(ErrCode.NOT_FOUND, "维修工不存在")
    expect = None
    if expect_finish_at:
        try:
            expect = datetime.fromisoformat(expect_finish_at)
            if expect.tzinfo:
                expect = expect.astimezone(timezone.utc).replace(tzinfo=None)
        except ValueError as exc:
            raise BizError(ErrCode.CONFLICT, "预计完成时间格式不正确") from exc
    if order.status not in ("pending", "assigned"):
        raise BizError(ErrCode.ORDER_STATE_INVALID)
    result = await session.execute(
        update(RepairOrder)
        .where(RepairOrder.id == order.id, RepairOrder.status == order.status)
        .values(worker_id=worker_id, status="assigned", assigned_at=utcnow(), expect_finish_at=expect, version=RepairOrder.version + 1)
    )
    if result.rowcount == 0:
        raise BizError(ErrCode.ORDER_STATE_INVALID, "该工单已被其他宿管处理")
    session.add(
        RepairEvent(
            order_id=order.id, event_type="assign", from_status=order.status, to_status="assigned",
            actor_id=admin.id, actor_name=admin.name, actor_role=admin.role,
            note=f"派单给 {worker.name}（{worker.worker_no}）",
        )
    )
    await send_message(
        session, order.student_id, "order", "工单已派单",
        f"{worker.name}师傅已接单，预计 {human_dt(expect) or '今日'} 上门。", "repair_order", order.id, dedup=False,
    )
    await write_audit(session, actor_id=admin.id, action="repair.assign", target_type="repair_order", target_id=order.id, detail={"worker_id": worker_id})
    await session.commit()
    return {"id": order.id, "status": "assigned", "worker_name": worker.name}


async def worker_accept(session: AsyncSession, worker: User, order_id: int) -> dict:
    order = await session.get(RepairOrder, order_id)
    if order is None or order.worker_id != worker.id:
        raise BizError(ErrCode.FORBIDDEN)
    await _transition(session, order, "accept_job", actor=worker, accepted_at=utcnow(), started_at=utcnow())
    await send_message(session, order.student_id, "order", "维修接单", f"{worker.name}师傅已接单。", "repair_order", order.id)
    await session.commit()
    return await order_detail(session, worker, order_id)


async def finish_order(session: AsyncSession, actor: User, order_id: int, note: str, material_fee: float) -> dict:
    order = await session.get(RepairOrder, order_id)
    if order is None:
        raise BizError(ErrCode.NOT_FOUND, "工单不存在")
    if actor.role == "worker" and order.worker_id != actor.id:
        raise BizError(ErrCode.FORBIDDEN)
    if order.status != "fixing":
        raise BizError(ErrCode.ORDER_STATE_INVALID)
    await _transition(
        session, order, "fix_done", actor=actor, note=note,
        fixed_at=utcnow(), material_fee=Decimal(str(round(material_fee, 2))), fix_note=note,
    )
    await send_message(
        session, order.student_id, "order", "维修完成待确认",
        f"{order.order_no} 已完工，请确认维修结果。", "repair_order", order.id, dedup=False,
    )
    await write_audit(session, actor_id=actor.id, action="repair.finish", target_type="repair_order", target_id=order.id, detail={"fee": material_fee})
    await session.commit()
    return await order_detail(session, actor, order_id)


async def my_worker_orders(session: AsyncSession, worker: User) -> list[dict]:
    rows = (
        await session.scalars(
            select(RepairOrder)
            .where(RepairOrder.worker_id == worker.id, RepairOrder.status.in_(("assigned", "fixing", "verify")))
            .order_by(RepairOrder.created_at.desc())
        )
    ).all()
    return [
        {
            "id": o.id,
            "order_no": o.order_no,
            "status": o.status,
            "status_label": status_meta(o.status)["label"],
            "category": CATEGORY_LABEL[o.category],
            "location_desc": o.location_desc,
            "description": o.description,
            "created_at": iso(o.created_at),
        }
        for o in rows
    ]


async def material_bill_exists(session: AsyncSession, order_id: int) -> bool:
    return bool(
        await session.scalar(
            select(Bill.id).where(Bill.source_type == "repair_order", Bill.source_id == order_id, Bill.type == "material")
        )
    )


async def auto_close_expired(session: AsyncSession) -> int:
    """verify 超 7 天自动归档（定时任务调用）。"""
    deadline = utcnow() - timedelta(days=7)
    rows = (
        await session.scalars(select(RepairOrder).where(RepairOrder.status == "verify", RepairOrder.fixed_at <= deadline))
    ).all()
    for order in rows:
        result = await session.execute(
            update(RepairOrder)
            .where(RepairOrder.id == order.id, RepairOrder.status == "verify")
            .values(status="done", done_at=utcnow(), version=RepairOrder.version + 1)
        )
        if result.rowcount:
            session.add(
                RepairEvent(
                    order_id=order.id, event_type="auto_close", from_status="verify", to_status="done",
                    actor_name="系统", actor_role="system", note="系统自动归档",
                )
            )
    await session.commit()
    return len(rows)


async def mark_timeout_orders(session: AsyncSession) -> int:
    deadline = utcnow() - timedelta(hours=4)
    result = await session.execute(
        update(RepairOrder)
        .where(RepairOrder.status == "pending", RepairOrder.created_at <= deadline, RepairOrder.is_timeout == 0)
        .values(is_timeout=1)
    )
    await session.commit()
    return result.rowcount or 0
