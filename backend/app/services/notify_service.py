"""通知服务：站内消息落库 + 推送偏好判断 + outbox 入队。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message, MessagePreference, OutboxEvent, PushLog, User

TYPE_LABELS = {"order": "工单提醒", "bill": "账单提醒", "notice": "通知公告", "paid": "缴费成功", "system": "系统消息"}


async def send_message(
    session: AsyncSession,
    user_id: int,
    msg_type: str,
    title: str,
    content: str,
    biz_type: str | None = None,
    biz_id: int | None = None,
    *,
    dedup: bool = True,
) -> Message | None:
    """写站内消息；同一业务对象同一类型对同一用户只推一次（业务去重）。"""
    if dedup and biz_type and biz_id is not None:
        exists = await session.scalar(
            select(Message.id).where(
                Message.user_id == user_id,
                Message.biz_type == biz_type,
                Message.biz_id == biz_id,
                Message.type == msg_type,
                Message.title == title,
            )
        )
        if exists:
            return None

    msg = Message(user_id=user_id, type=msg_type, biz_type=biz_type, biz_id=biz_id, title=title[:100], content=content[:500])
    session.add(msg)
    await session.flush()

    prefs = await session.get(MessagePreference, user_id)
    if prefs is not None:
        if msg_type in (prefs.sms_types or []):
            session.add(PushLog(user_id=user_id, message_id=msg.id, channel="sms", status="success"))
        if msg_type in (prefs.wechat_types or []):
            session.add(PushLog(user_id=user_id, message_id=msg.id, channel="wechat", status="success"))
    return msg


async def send_to_admins(session: AsyncSession, msg_type: str, title: str, content: str, biz_type=None, biz_id=None) -> None:
    admins = (await session.scalars(select(User).where(User.role == "admin", User.status == 1))).all()
    for admin in admins:
        await send_message(session, admin.id, msg_type, title, content, biz_type, biz_id)


async def enqueue(session: AsyncSession, event_type: str, payload: dict) -> None:
    """事务性发件箱：与业务同事务写入，由调度器异步消费。"""
    session.add(OutboxEvent(event_type=event_type, payload=payload))
