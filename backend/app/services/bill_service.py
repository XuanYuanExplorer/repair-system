"""账单服务：汇总、列表、详情、缴费记录、对账单导出、电子票据。"""
from __future__ import annotations

import csv
import io
import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.errors import BizError, ErrCode
from app.core.timeutil import days_until, human_dt, iso, local_date_str, utcnow
from app.models import Bill, DormBed, DormRoom, PaymentTransaction, PaymentTxnBill, Receipt, User
from app.services.audit import write_audit

TYPE_LABEL = {
    "electricity": "电费",
    "accommodation": "住宿费",
    "material": "维修材料费",
    "water": "水费",
    "penalty": "罚金",
}
STATUS_LABEL = {"unpaid": "待缴", "paid": "已缴", "overdue": "已逾期", "closed": "已关闭"}


def money(value: Decimal | float | int | None) -> str:
    return f"{Decimal(str(value or 0)).quantize(Decimal('0.01')):.2f}"


def _due_text(bill: Bill) -> tuple[str, bool]:
    if bill.status == "paid":
        return f"已于 {human_dt(bill.paid_at)} 缴纳", False
    if bill.status == "overdue":
        return f"已逾期 {bill.overdue_days} 天", True
    left = days_until(bill.due_date)
    if left < 0:
        return f"已逾期 {-left} 天", True
    if left == 0:
        return "今日到期", True
    return f"截止 {bill.due_date.strftime('%m-%d')} · 剩 {left} 天", left <= 3


def serialize_bill(bill: Bill, receipt: Receipt | None = None) -> dict:
    due_text, urgent = _due_text(bill)
    room_text = None
    return {
        "id": bill.id,
        "bill_no": bill.bill_no,
        "type": bill.type,
        "type_label": TYPE_LABEL[bill.type],
        "title": bill.title,
        "period": bill.period,
        "amount": money(bill.amount),
        "late_fee": money(bill.late_fee),
        "total": money(bill.amount + bill.late_fee),
        "status": bill.status,
        "status_label": STATUS_LABEL[bill.status],
        "due_date": local_date_str(bill.due_date),
        "due_text": due_text,
        "urgent": urgent,
        "overdue_days": bill.overdue_days,
        "paid_at": iso(bill.paid_at),
        "payable": bill.status in ("unpaid", "overdue"),
        "mergeable": bill.type != "penalty",
        "source_type": bill.source_type,
        "source_id": bill.source_id,
        "receipt": (
            {"id": receipt.id, "status": receipt.status, "receipt_no": receipt.receipt_no, "file_url": receipt.file_url}
            if receipt
            else None
        ),
        "room_text": room_text,
    }


async def summary(session: AsyncSession, user: User) -> dict:
    rows = (
        await session.execute(
            select(Bill.status, func.count(), func.coalesce(func.sum(Bill.amount + Bill.late_fee), 0))
            .where(Bill.student_id == user.id)
            .group_by(Bill.status)
        )
    ).all()
    agg = {status: (count, Decimal(str(total or 0))) for status, count, total in rows}
    unpaid_count, unpaid_amount = agg.get("unpaid", (0, Decimal("0")))
    overdue_count, overdue_amount = agg.get("overdue", (0, Decimal("0")))
    paid_count, paid_amount = agg.get("paid", (0, Decimal("0")))
    return {
        "unpaid_count": unpaid_count,
        "unpaid_amount": money(unpaid_amount),
        "overdue_count": overdue_count,
        "overdue_amount": money(overdue_amount),
        "paid_count": paid_count,
        "due_count": unpaid_count + overdue_count,
        "due_amount": money(unpaid_amount + overdue_amount),
        "semester_total": money(paid_amount),
        "semester_label": "本学期",
    }


async def list_bills(
    session: AsyncSession, user: User, *, status: str | None, type_: str | None, year: str | None, page: int, page_size: int
) -> dict:
    stmt = select(Bill).where(Bill.student_id == user.id)
    if status and status != "all":
        stmt = stmt.where(Bill.status == status)
    if type_ and type_ != "all":
        stmt = stmt.where(Bill.type == type_)
    if year:
        stmt = stmt.where(Bill.period.like(f"%{year}%"))

    total = int(await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    rows = (
        await session.scalars(stmt.order_by(Bill.due_date.asc(), Bill.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).all()
    items = []
    for b in rows:
        receipt = await session.scalar(select(Receipt).where(Receipt.bill_id == b.id))
        items.append(serialize_bill(b, receipt))
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
    }


async def _get_owned(session: AsyncSession, user: User, bill_id: int) -> Bill:
    bill = await session.get(Bill, bill_id)
    if bill is None:
        raise BizError(ErrCode.NOT_FOUND, "账单不存在")
    if bill.student_id != user.id:
        raise BizError(ErrCode.FORBIDDEN)
    return bill


async def detail(session: AsyncSession, user: User, bill_id: int) -> dict:
    bill = await _get_owned(session, user, bill_id)
    room = await session.get(DormRoom, bill.room_id) if bill.room_id else None
    receipt = await session.scalar(select(Receipt).where(Receipt.bill_id == bill.id))
    data = serialize_bill(bill, receipt)
    data.update(
        {
            "room_text": f"{room.building} {room.room_no} 室 · 床位 {bill.bed_no}" if room else None,
            "detail": bill.detail or {},
            "channel_options": [
                {"value": "wechat", "label": "微信支付", "hint": "推荐", "disabled": False},
                {"value": "alipay", "label": "支付宝", "hint": None, "disabled": False},
                {"value": "campus_card", "label": "校园卡余额", "hint": "¥236.50", "disabled": False},
            ],
        }
    )
    return data


async def records(session: AsyncSession, user: User, *, year: str | None, type_: str | None) -> dict:
    stmt = select(Bill).where(Bill.student_id == user.id, Bill.status == "paid")
    if year:
        stmt = stmt.where(Bill.period.like(f"%{year}%"))
    if type_ and type_ != "all":
        stmt = stmt.where(Bill.type == type_)
    rows = (await session.scalars(stmt.order_by(Bill.paid_at.desc()))).all()

    groups: dict[str, dict] = {}
    total = Decimal("0.00")
    for b in rows:
        paid_at = b.paid_at or b.updated_at
        key = paid_at.strftime("%Y-%m")
        group = groups.setdefault(
            key,
            {
                "month": key,
                "label": f"{paid_at.year} 年 {paid_at.month} 月",
                "en": paid_at.strftime("%b").upper(),
                "total": Decimal("0.00"),
                "items": [],
            },
        )
        receipt = await session.scalar(select(Receipt).where(Receipt.bill_id == b.id))
        txn = await session.scalar(
            select(PaymentTransaction)
            .join(PaymentTxnBill, PaymentTxnBill.txn_id == PaymentTransaction.id)
            .where(PaymentTxnBill.bill_id == b.id)
            .limit(1)
        )
        group["total"] += b.amount + b.late_fee
        group["items"].append(
            {
                "id": b.id,
                "title": f"{b.title}",
                "sub": f"{human_dt(paid_at)} · {_channel_label(txn.channel) if txn else '校园卡'}",
                "amount": money(-(b.amount + b.late_fee)),
                "receipt_status": receipt.status if receipt else None,
                "receipt_id": receipt.id if receipt else None,
                "receipt_file": receipt.file_url if receipt else None,
                "can_apply_receipt": receipt is None,
            }
        )
        total += b.amount + b.late_fee

    overdue_rows = (
        await session.scalars(
            select(Bill).where(Bill.student_id == user.id, Bill.status.in_(("overdue", "paid")), Bill.overdue_days > 0).order_by(Bill.due_date.desc())
        )
    ).all()
    overdue = [
        {
            "id": b.id,
            "period": b.period,
            "title": b.title,
            "text": f"{b.period} · {TYPE_LABEL[b.type]} 逾期 {b.overdue_days} 天{'缴纳' if b.status == 'paid' else '未缴'}",
            "late_fee": money(b.late_fee),
            "amount": money(b.amount + b.late_fee),
            "note": "含滞纳金 · 记录保留至毕业",
        }
        for b in overdue_rows
    ]
    return {
        "groups": [
            {**g, "total": money(g["total"])} for g in sorted(groups.values(), key=lambda x: x["month"], reverse=True)
        ],
        "overdue": overdue,
        "year_total": money(total),
        "year": year or "2023–2024",
    }


def _channel_label(channel: str | None) -> str:
    return {"wechat": "微信支付", "alipay": "支付宝", "campus_card": "校园卡"}.get(channel or "", "在线支付")


async def export_csv(session: AsyncSession, user: User, year: str | None) -> tuple[str, bytes]:
    data = await records(session, user, year=year, type_=None)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["账期", "类型", "标题", "金额", "缴纳时间", "票据状态"])
    for group in data["groups"]:
        for item in group["items"]:
            writer.writerow([group["label"], "", item["title"], item["amount"], item["sub"], item["receipt_status"] or "未开票"])
    writer.writerow(["合计", "", "", money(-Decimal(data["year_total"])), "", ""])
    filename = f"对账单_{year or '2023-2024'}_{(user.student_no or 'user')[-4:]}.csv"
    return filename, buf.getvalue().encode("utf-8-sig")


async def apply_receipt(session: AsyncSession, user: User, bill_id: int, payload) -> dict:
    bill = await _get_owned(session, user, bill_id)
    if bill.status != "paid":
        raise BizError(ErrCode.CONFLICT, "仅已支付账单可申请票据")
    exists = await session.scalar(select(Receipt).where(Receipt.bill_id == bill.id))
    if exists:
        return {"id": exists.id, "receipt_no": exists.receipt_no, "status": exists.status, "message": "该账单已申请票据"}
    receipt = Receipt(
        receipt_no=f"RC{datetime.now().strftime('%Y%m%d')}{bill.id:04d}",
        bill_id=bill.id,
        title=payload.title or "个人",
        email=payload.email or user.email,
        status="applied",
    )
    session.add(receipt)
    await session.flush()
    await write_audit(session, actor_id=user.id, action="bill.receipt.apply", target_type="bill", target_id=bill.id)
    await session.commit()
    return {"id": receipt.id, "receipt_no": receipt.receipt_no, "status": receipt.status}


async def issue_receipts(session: AsyncSession) -> int:
    """生成 PDF 并标记已发送（定时任务每 5 分钟兜底）。"""
    from app.services.receipt_pdf import build_receipt_pdf

    rows = (await session.scalars(select(Receipt).where(Receipt.status == "applied").limit(50))).all()
    for r in rows:
        bill = await session.get(Bill, r.bill_id)
        user = await session.get(User, bill.student_id) if bill else None
        if not bill or not user:
            r.status = "failed"
            continue
        path, url = build_receipt_pdf(r, bill, user)
        r.file_url = url
        r.issued_at = utcnow()
        r.status = "sent" if r.email else "issued"
    await session.commit()
    return len(rows)


async def receipt_file(session: AsyncSession, user: User, receipt_id: int) -> tuple[str, str]:
    receipt = await session.get(Receipt, receipt_id)
    if receipt is None:
        raise BizError(ErrCode.NOT_FOUND, "票据不存在")
    bill = await session.get(Bill, receipt.bill_id)
    if bill is None or (bill.student_id != user.id and user.role != "admin"):
        raise BizError(ErrCode.FORBIDDEN)
    if not receipt.file_url:
        from app.services.receipt_pdf import build_receipt_pdf

        path, url = build_receipt_pdf(receipt, bill, user)
        receipt.file_url = url
        receipt.status = "issued"
        await session.commit()
    else:
        path = settings.upload_dir + receipt.file_url.replace("/uploads", "")
    return f"{receipt.receipt_no}.pdf", path


async def generate_bills(session: AsyncSession, admin: User, payload) -> dict:
    due = datetime.strptime(payload.due_date, "%Y-%m-%d").date()
    stmt = select(User).where(User.role == "student", User.status == 1)
    if payload.student_ids:
        stmt = stmt.where(User.id.in_(payload.student_ids))
    students = (await session.scalars(stmt)).all()
    created = 0
    skipped = 0

    async def unique_bill_no(student_id: int) -> str:
        stamp = datetime.now().strftime("%y%m%d%H%M%S")
        for _ in range(20):
            candidate = f"B{payload.period.replace('-', '')[-6:]}-{student_id:05d}{random.randint(0, 999):03d}"
            if not await session.scalar(select(Bill.id).where(Bill.bill_no == candidate)):
                return candidate
        return f"B{stamp}-{student_id:05d}"

    for stu in students:
        bed = await session.scalar(select(DormBed).where(DormBed.student_id == stu.id))
        if payload.room_ids and (bed is None or bed.room_id not in payload.room_ids):
            continue
        exists = await session.scalar(
            select(Bill.id).where(
                Bill.student_id == stu.id, Bill.type == payload.type, Bill.period == payload.period, Bill.title == payload.title
            )
        )
        if exists:
            skipped += 1
            continue
        session.add(
            Bill(
                bill_no=await unique_bill_no(stu.id),
                student_id=stu.id,
                room_id=bed.room_id if bed else None,
                bed_no=bed.bed_no if bed else None,
                type=payload.type,
                period=payload.period,
                title=payload.title,
                amount=payload.amount,
                due_date=due,
                status="unpaid",
                detail={"items": [{"label": "应缴金额", "value": money(payload.amount), "unit": "元"}]},
            )
        )
        created += 1
    await write_audit(session, actor_id=admin.id, action="bill.generate", target_type="bill", detail={"created": created})
    await session.commit()
    return {"created": created, "skipped": skipped}


async def create_material_bill(session: AsyncSession, order_id: int) -> Bill | None:
    from app.models import RepairOrder

    order = await session.get(RepairOrder, order_id)
    if order is None or not order.material_fee or order.material_fee <= 0:
        return None
    exists = await session.scalar(
        select(Bill).where(Bill.source_type == "repair_order", Bill.source_id == order_id, Bill.type == "material")
    )
    if exists:
        return exists
    due = (utcnow() + timedelta(days=15)).date()
    bill = Bill(
        bill_no=f"B{datetime.now().strftime('%Y%m')}-{order.id:04d}",
        student_id=order.student_id,
        room_id=order.room_id,
        bed_no=order.bed_no,
        type="material",
        period=f"{datetime.now().year}-{datetime.now().month:02d}",
        title=f"维修材料费 · 工单 {order.order_no[-4:]}",
        amount=order.material_fee,
        due_date=due,
        status="unpaid",
        source_type="repair_order",
        source_id=order.id,
        detail={"items": [{"label": "材料费", "value": money(order.material_fee), "unit": "元"}], "remark": order.fix_note},
    )
    session.add(bill)
    await session.flush()
    return bill


async def mark_overdue(session: AsyncSession) -> int:
    from app.core.timeutil import local_today

    today = local_today()
    rows = (await session.scalars(select(Bill).where(Bill.status == "unpaid", Bill.due_date < today))).all()
    for bill in rows:
        days = (today - bill.due_date).days
        fee = min(bill.amount * Decimal("0.0005") * days, bill.amount * Decimal("0.3"))
        bill.status = "overdue"
        bill.overdue_days = days
        bill.late_fee = fee.quantize(Decimal("0.01"))
    await session.commit()
    return len(rows)
