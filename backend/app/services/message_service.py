"""消息服务：分组列表、未读数、已读、推送偏好。"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BizError, ErrCode
from app.core.timeutil import human_dt, iso, utcnow
from app.models import Message, MessagePreference, User
from app.services.notify_service import TYPE_LABELS

GROUP_ORDER = ["order", "bill", "notice", "paid", "system"]
EN_LABEL = {"order": "ORDER", "bill": "BILL", "notice": "NOTICE", "paid": "PAID", "system": "SYSTEM"}


async def list_messages(session: AsyncSession, user: User, msg_type: str | None, page: int, page_size: int) -> dict:
    stmt = select(Message).where(Message.user_id == user.id)
    if msg_type and msg_type != "all":
        stmt = stmt.where(Message.type == msg_type)
    total = int(await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = (
        await session.scalars(stmt.order_by(Message.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).all()

    counts_rows = (
        await session.execute(
            select(Message.type, Message.is_read, func.count()).where(Message.user_id == user.id).group_by(Message.type, Message.is_read)
        )
    ).all()
    unread = {t: 0 for t in GROUP_ORDER}
    totals = {t: 0 for t in GROUP_ORDER}
    for t, is_read, c in counts_rows:
        totals[t] = totals.get(t, 0) + c
        if not is_read:
            unread[t] = unread.get(t, 0) + c

    groups = []
    for t in GROUP_ORDER:
        if totals.get(t, 0) == 0 and t not in ("order", "bill", "notice", "paid"):
            continue
        groups.append(
            {
                "type": t,
                "label": TYPE_LABELS.get(t, t),
                "en": EN_LABEL.get(t, t.upper()),
                "total": totals.get(t, 0),
                "unread": unread.get(t, 0),
                "items": [],
            }
        )
    group_map = {g["type"]: g for g in groups}
    for m in rows:
        group = group_map.get(m.type)
        if group is None:
            continue
        group["items"].append(
            {
                "id": m.id,
                "type": m.type,
                "title": m.title,
                "content": m.content,
                "is_read": bool(m.is_read),
                "biz_type": m.biz_type,
                "biz_id": m.biz_id,
                "created_at": iso(m.created_at),
                "time_text": human_dt(m.created_at),
            }
        )
    return {
        "groups": groups,
        "items": [i for g in groups for i in g["items"]],
        "unread_total": sum(unread.values()),
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
    }


async def unread_count(session: AsyncSession, user: User) -> dict:
    rows = (
        await session.execute(
            select(Message.type, func.count())
            .where(Message.user_id == user.id, Message.is_read == 0)
            .group_by(Message.type)
        )
    ).all()
    by_type = {t: c for t, c in rows}
    return {"total": sum(by_type.values()), "by_type": by_type}


async def read_one(session: AsyncSession, user: User, message_id: int) -> dict:
    msg = await session.get(Message, message_id)
    if msg is None:
        raise BizError(ErrCode.NOT_FOUND, "消息不存在")
    if msg.user_id != user.id:
        raise BizError(ErrCode.FORBIDDEN)
    if not msg.is_read:
        msg.is_read = 1
        msg.read_at = utcnow()
        await session.commit()
    return {"id": msg.id, "is_read": True}


async def read_all(session: AsyncSession, user: User, msg_type: str | None) -> dict:
    stmt = select(Message).where(Message.user_id == user.id, Message.is_read == 0)
    if msg_type and msg_type != "all":
        stmt = stmt.where(Message.type == msg_type)
    rows = (await session.scalars(stmt)).all()
    for m in rows:
        m.is_read = 1
        m.read_at = utcnow()
    await session.commit()
    return {"affected": len(rows), "unread": await unread_count(session, user)}


async def get_preferences(session: AsyncSession, user: User) -> dict:
    pref = await session.get(MessagePreference, user.id)
    if pref is None:
        pref = MessagePreference(user_id=user.id, sms_types=["bill", "notice"], wechat_types=["bill", "notice"])
        session.add(pref)
        await session.commit()
    return {
        "sms_types": pref.sms_types,
        "wechat_types": pref.wechat_types,
        "sms_on": bool(pref.sms_types),
        "wechat_on": bool(pref.wechat_types),
        "note": "仅限账单 / 查寝类",
    }


async def update_preferences(session: AsyncSession, user: User, payload) -> dict:
    pref = await session.get(MessagePreference, user.id)
    if pref is None:
        pref = MessagePreference(user_id=user.id)
        session.add(pref)
    pref.sms_types = [t for t in payload.sms_types if t in TYPE_LABELS]
    pref.wechat_types = [t for t in payload.wechat_types if t in TYPE_LABELS]
    await session.commit()
    return await get_preferences(session, user)
