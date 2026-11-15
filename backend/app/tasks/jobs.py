"""定时任务实现：outbox 消费、支付兜底、逾期计算、超时扫描、自动归档、提醒、票据签发。"""
from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import select, update

from app.core.timeutil import local_today, utcnow
from app.db import SessionLocal
from app.models import Bill, OutboxEvent, RepairOrder, User
from app.services import bill_service, duty_service, home_service, payment_service, repair_service
from app.services.notify_service import send_message, send_to_admins

logger = logging.getLogger("dorm.jobs")


async def dispatch_outbox(session) -> int:
    rows = (
        await session.scalars(
            select(OutboxEvent)
            .where(OutboxEvent.status == "pending", OutboxEvent.available_at <= utcnow())
            .order_by(OutboxEvent.id)
            .limit(50)
        )
    ).all()
    for event in rows:
        try:
            if event.event_type == "repair.completed":
                payload = event.payload or {}
                bill = await bill_service.create_material_bill(session, int(payload["order_id"]))
                if bill is not None:
                    await send_message(
                        session,
                        bill.student_id,
                        "bill",
                        "维修材料费账单已生成",
                        f"工单 {payload.get('order_no')} 材料费 ¥{bill.amount:.2f}，请在 {bill.due_date} 前缴纳。",
                        "bill",
                        bill.id,
                        dedup=False,
                    )
            elif event.event_type == "bill.paid":
                payload = event.payload or {}
                if payload.get("user_id"):
                    await home_service.invalidate(int(payload["user_id"]))
            event.status = "done"
        except Exception as exc:  # noqa: BLE001 - 单条失败不影响其余事件
            logger.exception("outbox_failed", extra={"event_id": event.id, "error": str(exc)})
            event.retry_count += 1
            event.available_at = utcnow() + timedelta(seconds=min(2 ** event.retry_count * 5, 600))
            if event.retry_count >= 5:
                event.status = "failed"
    await session.commit()
    return len(rows)


async def poll_payments(session) -> int:
    return await payment_service.poll_pending_payments(session)


async def mark_overdue(session) -> int:
    count = await bill_service.mark_overdue(session)
    today = local_today()
    overdue = (await session.scalars(select(Bill).where(Bill.status == "overdue", Bill.overdue_days == 1))).all()
    for bill in overdue:
        await send_message(
            session,
            bill.student_id,
            "bill",
            f"{bill.title} 已逾期",
            f"¥{bill.amount + bill.late_fee:.2f} · 逾期 {bill.overdue_days} 天，含滞纳金 ¥{bill.late_fee:.2f}",
            "bill",
            bill.id,
            dedup=False,
        )
    await session.commit()
    return count


async def scan_timeouts(session) -> int:
    count = await repair_service.mark_timeout_orders(session)
    rows = (
        await session.scalars(
            select(RepairOrder).where(RepairOrder.status == "pending", RepairOrder.is_timeout == 1)
        )
    ).all()
    for order in rows:
        await send_to_admins(
            session, "order", "工单超时未受理", f"{order.order_no} 已超过 4 小时未受理，请尽快派单。", "repair_order", order.id
        )
    await session.commit()
    return count


async def auto_close(session) -> int:
    return await repair_service.auto_close_expired(session)


async def duty_remind(session) -> int:
    return await duty_service.duty_reminder(session)


async def due_reminder(session) -> int:
    deadline = local_today() + timedelta(days=3)
    rows = (
        await session.scalars(
            select(Bill).where(Bill.status == "unpaid", Bill.due_date <= deadline, Bill.due_date >= local_today())
        )
    ).all()
    for bill in rows:
        days = (bill.due_date - local_today()).days
        await send_message(
            session,
            bill.student_id,
            "bill",
            "账单到期提醒",
            f"{bill.title} · ¥{bill.amount + bill.late_fee:.2f} · 截止 {bill.due_date.strftime('%m-%d')}"
            + (f" · 剩 {days} 天" if days else " · 今日到期"),
            "bill_due",
            bill.id,
        )
    await session.commit()
    return len(rows)


async def issue_receipts(session) -> int:
    return await bill_service.issue_receipts(session)


async def tick(force_daily: bool = False) -> None:
    """调度入口：30 秒一次；日任务用缓存键去重。"""
    from app.core.cache import cache

    today = local_today().isoformat()
    async with SessionLocal() as session:
        await dispatch_outbox(session)
        await poll_payments(session)

        if force_daily or not await cache.exists(f"job:30min:{today}:{utcnow().hour}:{utcnow().minute // 30}"):
            await scan_timeouts(session)
            await cache.set(f"job:30min:{today}:{utcnow().hour}:{utcnow().minute // 30}", 1, ttl=1800)

    async with SessionLocal() as session:
        if force_daily or not await cache.exists(f"job:daily:{today}:overdue"):
            await mark_overdue(session)
            await cache.set(f"job:daily:{today}:overdue", 1, ttl=86400)
        if force_daily or not await cache.exists(f"job:daily:{today}:autoclose"):
            await auto_close(session)
            await cache.set(f"job:daily:{today}:autoclose", 1, ttl=86400)
        if force_daily or not await cache.exists(f"job:daily:{today}:duty"):
            await duty_remind(session)
            await cache.set(f"job:daily:{today}:duty", 1, ttl=86400)
        if force_daily or not await cache.exists(f"job:daily:{today}:due"):
            await due_reminder(session)
            await cache.set(f"job:daily:{today}:due", 1, ttl=86400)
        if force_daily or not await cache.exists(f"job:5min:{today}:{utcnow().hour}:{utcnow().minute // 5}"):
            await issue_receipts(session)
            await cache.set(f"job:5min:{today}:{utcnow().hour}:{utcnow().minute // 5}", 1, ttl=300)


async def mark_all_messages_read(session, user_id: int) -> None:
    from app.models import Message

    await session.execute(update(Message).where(Message.user_id == user_id).values(is_read=1, read_at=utcnow()))
    await session.commit()


__all__ = ["tick", "dispatch_outbox", "poll_payments", "mark_overdue", "scan_timeouts", "auto_close", "duty_remind"]
