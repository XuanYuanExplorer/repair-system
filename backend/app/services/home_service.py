"""首页聚合服务：一次请求返回服务大厅所需全部数据（串行查询 + 短缓存）。"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.timeutil import greeting, human_dt, local_today
from app.models import Bill, DormBed, DormRoom, Message, Notice, RepairOrder, User
from app.services.bill_service import money
from app.services.content_service import latest_public_notices
from app.services.message_service import unread_count
from app.services.repair_service import ACTIVE_STATUS, CATEGORY_LABEL, PROGRESS, status_meta


async def summary(session: AsyncSession, user: User) -> dict:
    cache_key = f"cache:home:{user.id}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    bed = await session.scalar(select(DormBed).where(DormBed.student_id == user.id, DormBed.status == 1))
    room = await session.get(DormRoom, bed.room_id) if bed else None

    due_count, due_sum = (
        await session.execute(
            select(func.count(), func.coalesce(func.sum(Bill.amount + Bill.late_fee), 0)).where(
                Bill.student_id == user.id, Bill.status.in_(("unpaid", "overdue"))
            )
        )
    ).one()
    active_count = int(
        await session.scalar(
            select(func.count()).select_from(RepairOrder).where(
                RepairOrder.student_id == user.id, RepairOrder.status.in_(ACTIVE_STATUS)
            )
        )
        or 0
    )
    latest = await session.scalar(
        select(RepairOrder).where(RepairOrder.student_id == user.id).order_by(RepairOrder.created_at.desc()).limit(1)
    )
    unread = await unread_count(session, user)
    notices = await latest_public_notices(session)

    latest_order = None
    if latest:
        worker = await session.get(User, latest.worker_id) if latest.worker_id else None
        meta = status_meta(latest.status)
        latest_order = {
            "id": latest.id,
            "order_no": latest.order_no,
            "short_no": latest.order_no[-4:],
            "title": f"{latest.description.split('，')[0][:14]} · {room.building + ' ' + room.room_no + ' 室' if room else latest.location_desc}",
            "status": latest.status,
            "status_label": meta["label"],
            "status_en": meta["en"],
            "worker_name": worker.name if worker else None,
            "expect_text": (
                f"{worker.name if worker else '维修师傅'} · 预计 {human_dt(latest.expect_finish_at)} 上门"
                if latest.expect_finish_at
                else "等待宿管受理"
            ),
            "percent": PROGRESS.get(latest.status, 0),
        }

    bill_cta = await session.scalar(
        select(Bill)
        .where(Bill.student_id == user.id, Bill.status.in_(("unpaid", "overdue")))
        .order_by(Bill.due_date.asc())
        .limit(1)
    )
    cta = None
    if bill_cta:
        cta = {
            "id": bill_cta.id,
            "title": f"{bill_cta.period} 账单" if bill_cta.type != "material" else bill_cta.title,
            "amount": money(bill_cta.amount + bill_cta.late_fee),
        }

    data = {
        "greeting": f"{room.room_no} 室，{greeting()}" if room else f"{user.name}，{greeting()}",
        "room_no": room.room_no if room else None,
        "user_name": user.name,
        "subtitle": f"{user.college or '—'} / {user.grade or '—'} 级",
        "today": local_today().strftime("%Y-%m-%d"),
        "due": {"amount": money(due_sum), "count": int(due_count)},
        "orders": {"active_count": active_count},
        "latest_order": latest_order,
        "unread": unread,
        "notices": notices[:2],
        "bill_cta": cta,
        "services": [
            {"key": "repair-new", "label": "我要报修", "en": "REPAIR", "icon": "tool", "to": "/repair/submit", "hot": False},
            {"key": "repair-list", "label": "我的报修", "en": "ORDERS", "icon": "doc", "to": "/repair/list", "hot": False},
            {"key": "payment", "label": "在线缴费", "en": "PAY", "icon": "card", "to": "/payment", "hot": True},
            {"key": "room", "label": "我的寝室", "en": "ROOM", "icon": "bed", "to": "/dorm", "hot": False},
            {"key": "duty", "label": "值日排班", "en": "DUTY", "icon": "cal", "to": "/dorm/duty", "hot": False},
            {"key": "all", "label": "全部分类", "en": "ALL", "icon": "grid", "to": "/help", "hot": False},
        ],
    }
    await cache.set(cache_key, data, ttl=60)
    return data


async def invalidate(user_id: int) -> None:
    await cache.delete(f"cache:home:{user_id}")
