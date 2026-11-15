"""反馈服务：提交、进度、满意度、官方回复。"""
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BizError, ErrCode
from app.core.timeutil import human_dt, iso, utcnow
from app.models import Feedback, FeedbackReply, RepairOrder, User
from app.services.audit import write_audit
from app.services.notify_service import send_message

TYPE_LABEL = {"attitude": "服务态度", "quality": "维修质量", "charge": "收费疑问", "suggestion": "设施建议"}
STATUS_LABEL = {"submitted": "已提交", "processing": "处理中", "replied": "已回复", "closed": "已关闭"}


async def _gen_fb_no(session: AsyncSession) -> str:
    day = datetime.now().strftime("%m%d")
    count = int(await session.scalar(select(func.count()).select_from(Feedback)) or 0)
    return f"FB{day}-{count + 1:02d}"


async def create(session: AsyncSession, user: User, payload) -> dict:
    if payload.order_id:
        order = await session.get(RepairOrder, payload.order_id)
        if order is None:
            raise BizError(ErrCode.NOT_FOUND, "关联工单不存在")
        if order.student_id != user.id:
            raise BizError(ErrCode.FORBIDDEN)
    fb = Feedback(
        fb_no=await _gen_fb_no(session),
        user_id=user.id,
        type=payload.type,
        order_id=payload.order_id,
        content=payload.content,
        media_urls=payload.media_urls or [],
        status="submitted",
    )
    session.add(fb)
    await write_audit(session, actor_id=user.id, action="feedback.create", target_type="feedback", detail={"type": payload.type})
    await session.commit()
    return {"id": fb.id, "fb_no": fb.fb_no, "status": fb.status, "message": "反馈已提交，可在下方查看进度"}


async def list_mine(session: AsyncSession, user: User, page: int, page_size: int) -> dict:
    stmt = select(Feedback).where(Feedback.user_id == user.id)
    total = int(await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = (
        await session.scalars(stmt.order_by(Feedback.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).all()
    items = []
    for fb in rows:
        order = await session.get(RepairOrder, fb.order_id) if fb.order_id else None
        items.append(
            {
                "id": fb.id,
                "fb_no": fb.fb_no,
                "type": fb.type,
                "type_label": TYPE_LABEL[fb.type],
                "content": fb.content,
                "media_urls": fb.media_urls or [],
                "status": fb.status,
                "status_label": STATUS_LABEL[fb.status],
                "reply": fb.reply,
                "replied_at": iso(fb.replied_at),
                "satisfaction": fb.satisfaction,
                "order_no": order.order_no if order else None,
                "created_text": human_dt(fb.created_at),
                "progress_text": (
                    fb.reply or ("宿管中心受理中 · 预计 2 个工作日回复" if fb.status in ("submitted", "processing") else "已关闭")
                ),
                "can_rate": fb.status in ("replied", "closed") and fb.satisfaction is None,
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size, "has_more": page * page_size < total}


async def rate(session: AsyncSession, user: User, feedback_id: int, score: int) -> dict:
    fb = await session.get(Feedback, feedback_id)
    if fb is None or fb.user_id != user.id:
        raise BizError(ErrCode.NOT_FOUND, "反馈不存在")
    if fb.status not in ("replied", "closed"):
        raise BizError(ErrCode.CONFLICT, "反馈尚未回复，暂不能评价")
    if fb.satisfaction is not None:
        raise BizError(ErrCode.CONFLICT, "该反馈已评价，感谢反馈")
    fb.satisfaction = score
    await session.commit()
    return {"id": fb.id, "satisfaction": score}


async def admin_reply(session: AsyncSession, admin: User, feedback_id: int, content: str) -> dict:
    fb = await session.get(Feedback, feedback_id)
    if fb is None:
        raise BizError(ErrCode.NOT_FOUND, "反馈不存在")
    fb.reply = content
    fb.replied_at = utcnow()
    fb.status = "replied"
    session.add(FeedbackReply(feedback_id=fb.id, replier_id=admin.id, content=content))
    await send_message(
        session, fb.user_id, "system", "反馈已回复", f"{fb.fb_no}：{content}", "feedback", fb.id, dedup=False
    )
    await write_audit(session, actor_id=admin.id, action="feedback.reply", target_type="feedback", target_id=fb.id)
    await session.commit()
    return {"id": fb.id, "status": fb.status, "reply": fb.reply}


async def admin_list(session: AsyncSession, status: str | None, page: int, page_size: int) -> dict:
    stmt = select(Feedback)
    if status and status != "all":
        stmt = stmt.where(Feedback.status == status)
    total = int(await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = (
        await session.scalars(stmt.order_by(Feedback.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).all()
    items = []
    for fb in rows:
        u = await session.get(User, fb.user_id)
        items.append(
            {
                "id": fb.id,
                "fb_no": fb.fb_no,
                "type": TYPE_LABEL[fb.type],
                "content": fb.content,
                "status": fb.status,
                "student_name": u.name if u else None,
                "created_text": human_dt(fb.created_at),
                "reply": fb.reply,
            }
        )
    return {"items": items, "total": total, "page": page, "page_size": page_size, "has_more": page * page_size < total}
