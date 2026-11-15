"""内容服务：公告、已读回执、FAQ、服务电话。"""
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BizError, ErrCode
from app.core.timeutil import human_dt, iso, local_date_str, local_today, utcnow
from app.models import DormBed, DormRoom, Faq, Notice, NoticeReceipt, User
from app.services.audit import write_audit

NOTICE_TYPE_LABEL = {"notice": "通知", "check": "查寝", "utility": "停水停电", "safety": "安全"}

HOTLINES = [
    {"name": "宿管中心", "time": "7 × 24 小时", "phone": "0510-8818 6112", "tel": "051088186112"},
    {"name": "维修班组", "time": "08:00 – 20:00", "phone": "0510-8818 9553", "tel": "051088189553"},
]


async def _room_of(session: AsyncSession, user: User) -> DormRoom | None:
    bed = await session.scalar(select(DormBed).where(DormBed.student_id == user.id, DormBed.status == 1))
    return await session.get(DormRoom, bed.room_id) if bed else None


def _visible_filter(stmt, room: DormRoom | None):
    if room is None:
        return stmt.where(Notice.scope == "all")
    return stmt.where(
        or_(
            Notice.scope == "all",
            (Notice.scope == "building") & (Notice.building == room.building),
            (Notice.scope == "room") & (Notice.room_id == room.id),
        )
    )


async def list_notices(session: AsyncSession, user: User, *, type_: str | None, page: int, page_size: int) -> dict:
    room = await _room_of(session, user)
    now = utcnow()
    base = select(Notice).where(Notice.deleted_at.is_(None))
    base = _visible_filter(base, room).where(or_(Notice.expire_at.is_(None), Notice.expire_at > now))
    if type_ and type_ != "all":
        base = base.where(Notice.type == type_)

    total = int(await session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = (
        await session.scalars(
            base.order_by(Notice.is_pinned.desc(), Notice.published_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    receipts = {
        r.notice_id: r
        for r in (
            await session.scalars(select(NoticeReceipt).where(NoticeReceipt.user_id == user.id))
        ).all()
    }
    items = []
    for n in rows:
        r = receipts.get(n.id)
        items.append(
            {
                "id": n.id,
                "type": n.type,
                "type_label": NOTICE_TYPE_LABEL.get(n.type, n.type),
                "title": n.title,
                "summary": n.content[:80],
                "content": n.content,
                "is_pinned": bool(n.is_pinned),
                "require_receipt": bool(n.require_receipt),
                "is_read": bool(r and r.is_read),
                "receipt_at": iso(r.receipt_at) if r else None,
                "published_at": iso(n.published_at),
                "date_text": human_dt(n.published_at),
                "publisher": n.publisher_name or "宿管中心",
            }
        )
    unread = sum(1 for i in items if not i["is_read"])
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
        "unread": unread,
        "receipt_progress": {
            "read": len(items) - unread,
            "total": len(items),
            "text": f"未读 {unread} / {len(items)}",
        },
    }


async def detail(session: AsyncSession, user: User, notice_id: int) -> dict:
    notice = await session.get(Notice, notice_id)
    if notice is None or notice.deleted_at is not None:
        raise BizError(ErrCode.NOT_FOUND, "公告不存在")
    receipt = await session.scalar(
        select(NoticeReceipt).where(NoticeReceipt.notice_id == notice_id, NoticeReceipt.user_id == user.id)
    )
    if receipt is None:
        receipt = NoticeReceipt(notice_id=notice_id, user_id=user.id, is_read=1, read_at=utcnow())
        session.add(receipt)
    elif not receipt.is_read:
        receipt.is_read = 1
        receipt.read_at = utcnow()
    await session.commit()
    return {
        "id": notice.id,
        "title": notice.title,
        "content": notice.content,
        "type": notice.type,
        "type_label": NOTICE_TYPE_LABEL.get(notice.type, notice.type),
        "is_pinned": bool(notice.is_pinned),
        "require_receipt": bool(notice.require_receipt),
        "is_read": True,
        "receipt_at": iso(receipt.receipt_at),
        "published_at": iso(notice.published_at),
        "publisher": notice.publisher_name or "宿管中心",
    }


async def mark_read(session: AsyncSession, user: User, notice_id: int) -> dict:
    notice = await session.get(Notice, notice_id)
    if notice is None:
        raise BizError(ErrCode.NOT_FOUND, "公告不存在")
    receipt = await session.scalar(
        select(NoticeReceipt).where(NoticeReceipt.notice_id == notice_id, NoticeReceipt.user_id == user.id)
    )
    if receipt is None:
        session.add(NoticeReceipt(notice_id=notice_id, user_id=user.id, is_read=1, read_at=utcnow()))
    elif not receipt.is_read:
        receipt.is_read = 1
        receipt.read_at = utcnow()
    await session.commit()
    return {"notice_id": notice_id, "is_read": True}


async def confirm_receipt(session: AsyncSession, user: User, notice_id: int) -> dict:
    notice = await session.get(Notice, notice_id)
    if notice is None:
        raise BizError(ErrCode.NOT_FOUND, "公告不存在")
    if not notice.require_receipt:
        raise BizError(ErrCode.NOT_FOUND, "该公告无需回执")
    receipt = await session.scalar(
        select(NoticeReceipt).where(NoticeReceipt.notice_id == notice_id, NoticeReceipt.user_id == user.id)
    )
    if receipt is None:
        receipt = NoticeReceipt(notice_id=notice_id, user_id=user.id, is_read=1, read_at=utcnow())
        session.add(receipt)
    receipt.receipt_at = utcnow()
    await session.commit()
    return {"notice_id": notice_id, "receipt_at": iso(receipt.receipt_at), "receipted": True}


async def create_notice(session: AsyncSession, admin: User, payload) -> dict:
    expire = None
    if payload.expire_at:
        try:
            expire = datetime.fromisoformat(payload.expire_at)
            if expire.tzinfo:
                expire = expire.replace(tzinfo=None)
        except ValueError as exc:
            raise BizError(ErrCode.CONFLICT, "有效期格式不正确") from exc
    notice = Notice(
        scope=payload.scope,
        building=payload.building,
        room_id=payload.room_id,
        type=payload.type,
        title=payload.title,
        content=payload.content,
        is_pinned=1 if payload.is_pinned else 0,
        require_receipt=1 if payload.require_receipt else 0,
        publisher_id=admin.id,
        publisher_name="宿管中心",
        published_at=utcnow(),
        expire_at=expire,
    )
    session.add(notice)
    await write_audit(session, actor_id=admin.id, action="notice.publish", target_type="notice", detail={"title": payload.title})
    await session.commit()
    return {"id": notice.id, "title": notice.title, "published_at": iso(notice.published_at)}


async def notice_receipts(session: AsyncSession, notice_id: int) -> dict:
    notice = await session.get(Notice, notice_id)
    if notice is None:
        raise BizError(ErrCode.NOT_FOUND, "公告不存在")
    students = (await session.scalars(select(User).where(User.role == "student", User.status == 1))).all()
    receipts = {
        r.user_id: r for r in (await session.scalars(select(NoticeReceipt).where(NoticeReceipt.notice_id == notice_id))).all()
    }
    items = []
    for s in students:
        r = receipts.get(s.id)
        items.append(
            {
                "user_id": s.id,
                "name": s.name,
                "student_no": s.student_no,
                "is_read": bool(r and r.is_read),
                "receipt_at": iso(r.receipt_at) if r else None,
            }
        )
    return {
        "notice_id": notice_id,
        "items": items,
        "unread": [i for i in items if not i["is_read"]],
        "unreceipted": [i for i in items if i["is_read"] and not i["receipt_at"]],
    }


async def search_faqs(session: AsyncSession, q: str | None, category: str | None) -> list[dict]:
    stmt = select(Faq).where(Faq.is_published.is_(True))
    if category and category != "all":
        stmt = stmt.where(Faq.category == category)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Faq.question.like(like), Faq.answer.like(like)))
    rows = (await session.scalars(stmt.order_by(Faq.sort, Faq.id))).all()
    return [
        {
            "id": f.id,
            "category": f.category,
            "question": f.question,
            "answer": f.answer,
            "is_self_help": bool(f.is_self_help),
            "index": idx + 1,
        }
        for idx, f in enumerate(rows)
    ]


def hotlines() -> list[dict]:
    return HOTLINES


async def latest_public_notices(session: AsyncSession) -> list[dict]:
    rows = (
        await session.scalars(
            select(Notice)
            .where(Notice.deleted_at.is_(None), or_(Notice.expire_at.is_(None), Notice.expire_at > utcnow()))
            .order_by(Notice.is_pinned.desc(), Notice.published_at.desc())
            .limit(3)
        )
    ).all()
    return [
        {"id": n.id, "title": n.title, "date": human_dt(n.published_at), "type": n.type} for n in rows
    ]


def today_text() -> str:
    return local_today().strftime("%Y-%m-%d")


def date_label(d) -> str | None:
    return local_date_str(d)
