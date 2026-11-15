"""支付服务：幂等下单、合并支付、服务端主动查单、防掉单轮询。"""
from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache
from app.core.errors import BizError, ErrCode
from app.core.timeutil import human_dt, iso, utcnow
from app.models import Bill, PaymentTransaction, PaymentTxnBill, Receipt, User
from app.services.audit import write_audit
from app.services.bill_service import money
from app.services.notify_service import enqueue, send_message

CHANNEL_LABEL = {"wechat": "微信支付", "alipay": "支付宝", "campus_card": "校园卡"}


class MockGateway:
    """本地假网关：状态存于缓存，接口与真实网关一致，切换只改配置。

    真实接入时替换 create_order / query 两个方法即可（HTTP 调用走 httpx.AsyncClient）。
    """

    async def create_order(self, txn_no: str, amount: Decimal, channel: str) -> dict:
        await cache.set(f"pay:gw:{txn_no}", {"status": "PENDING", "txn_id": None}, ttl=1800)
        return {
            "prepay_id": f"mock_{txn_no}",
            "appId": "wxmock0000000000",
            "timeStamp": str(int(datetime.now().timestamp())),
            "nonceStr": f"{random.randint(10**9, 10**10 - 1)}",
            "package": f"prepay_id=mock_{txn_no}",
            "signType": "RSA",
            "paySign": hashlib.sha256(f"{txn_no}{settings.jwt_secret}".encode()).hexdigest()[:32],
            "mock": True,
        }

    async def query(self, txn_no: str) -> dict:
        state = await cache.get(f"pay:gw:{txn_no}") or {"status": "PENDING"}
        return {"status": state.get("status", "PENDING"), "txn_id": state.get("txn_id"), "reason": state.get("reason")}

    async def mark(self, txn_no: str, status: str, reason: str | None = None) -> None:
        await cache.set(
            f"pay:gw:{txn_no}",
            {"status": status, "txn_id": f"MOCK{random.randint(10**8, 10**9 - 1)}", "reason": reason},
            ttl=1800,
        )


gateway = MockGateway()


def _gen_txn_no() -> str:
    return "PAY" + datetime.now().strftime("%Y%m%d%H%M%S") + f"{random.randint(0, 999):03d}"


async def create_payment(session: AsyncSession, user: User, bill_ids: list[int], channel: str, idem_key: str | None) -> dict:
    cache_key = f"idem:payment:{user.id}:{idem_key}" if idem_key else None
    if cache_key:
        cached = await cache.get(cache_key)
        if cached:
            return json.loads(cached)
        exists = await session.scalar(
            select(PaymentTransaction).where(
                PaymentTransaction.user_id == user.id, PaymentTransaction.idempotency_key == idem_key
            )
        )
        if exists:
            return await serialize_txn(session, exists)

    bills = (
        await session.scalars(
            select(Bill).where(Bill.id.in_(bill_ids), Bill.student_id == user.id).with_for_update()
        )
    ).all()
    if len(bills) != len(set(bill_ids)):
        raise BizError(ErrCode.NOT_FOUND, "账单不存在或不属于当前用户")
    if any(b.status == "paid" for b in bills):
        raise BizError(ErrCode.BILL_ALREADY_PAID)
    if any(b.status not in ("unpaid", "overdue") for b in bills):
        raise BizError(ErrCode.BILL_ALREADY_PAID)
    if any(b.type == "penalty" for b in bills) and len(bills) > 1:
        raise BizError(ErrCode.PENALTY_NOT_MERGEABLE)

    # 同一账单已有未完成的支付单：账单集合一致则复用（幂等），否则拒绝（并发下的第二道闸）
    open_txn = await session.scalar(
        select(PaymentTransaction)
        .join(PaymentTxnBill, PaymentTxnBill.txn_id == PaymentTransaction.id)
        .where(
            PaymentTxnBill.bill_id.in_([b.id for b in bills]),
            PaymentTransaction.user_id == user.id,
            PaymentTransaction.status.in_(("created", "paying")),
        )
        .order_by(PaymentTransaction.created_at.desc())
        .limit(1)
    )
    if open_txn:
        linked = set(
            (await session.scalars(select(PaymentTxnBill.bill_id).where(PaymentTxnBill.txn_id == open_txn.id))).all()
        )
        if linked != {b.id for b in bills}:
            raise BizError(ErrCode.BILL_ALREADY_PAID, "该账单已存在待支付的支付单，请勿重复下单")
        pay_params = await gateway.create_order(open_txn.txn_no, open_txn.amount, open_txn.channel)
        payload = {
            "txn_no": open_txn.txn_no,
            "amount": money(open_txn.amount),
            "channel": open_txn.channel,
            "channel_label": CHANNEL_LABEL.get(open_txn.channel, open_txn.channel),
            "status": "created",
            "expire_at": iso(open_txn.expire_at),
            "countdown_sec": max(int((open_txn.expire_at - utcnow()).total_seconds()), 0),
            "pay_params": pay_params,
            "bill_ids": sorted(linked),
            "reused": True,
        }
        if cache_key:
            await cache.set(cache_key, json.dumps(payload, ensure_ascii=False), ttl=86400)
        return payload

    amount = sum((b.amount + b.late_fee for b in bills), Decimal("0.00"))
    txn = PaymentTransaction(
        txn_no=_gen_txn_no(),
        user_id=user.id,
        amount=amount,
        channel=channel,
        status="created",
        idempotency_key=idem_key,
        expire_at=utcnow() + timedelta(minutes=settings.pay_expire_minutes),
    )
    session.add(txn)
    await session.flush()
    for b in bills:
        session.add(PaymentTxnBill(txn_id=txn.id, bill_id=b.id, amount=b.amount + b.late_fee))
    await session.commit()

    pay_params = await gateway.create_order(txn.txn_no, amount, channel)
    payload = {
        "txn_no": txn.txn_no,
        "amount": money(amount),
        "channel": channel,
        "channel_label": CHANNEL_LABEL.get(channel, channel),
        "status": "created",
        "expire_at": iso(txn.expire_at),
        "countdown_sec": settings.pay_expire_minutes * 60,
        "pay_params": pay_params,
        "bill_ids": [b.id for b in bills],
    }
    if cache_key:
        await cache.set(cache_key, json.dumps(payload, ensure_ascii=False), ttl=86400)
    return payload


async def serialize_txn(session: AsyncSession, txn: PaymentTransaction) -> dict:
    links = (await session.scalars(select(PaymentTxnBill).where(PaymentTxnBill.txn_id == txn.id))).all()
    bills = []
    for link in links:
        bill = await session.get(Bill, link.bill_id)
        if bill:
            bills.append({"id": bill.id, "title": bill.title, "amount": money(link.amount)})
    receipt_ready = False
    if bills:
        receipt_ready = bool(
            await session.scalar(select(Receipt.id).where(Receipt.bill_id == bills[0]["id"]))
        )
    return {
        "txn_no": txn.txn_no,
        "status": {"created": "processing", "paying": "processing", "success": "success", "failed": "failed", "closed": "closed"}.get(
            txn.status, txn.status
        ),
        "raw_status": txn.status,
        "amount": money(txn.amount),
        "channel": txn.channel,
        "channel_label": CHANNEL_LABEL.get(txn.channel, txn.channel),
        "paid_at": iso(txn.paid_at),
        "created_at": iso(txn.created_at),
        "expire_at": iso(txn.expire_at),
        "fail_reason": txn.fail_reason,
        "bills": bills,
        "receipt_available": txn.status == "success",
        "receipt_applied": receipt_ready,
    }


async def query_result(session: AsyncSession, user: User, txn_no: str) -> dict:
    txn = await session.scalar(
        select(PaymentTransaction).where(PaymentTransaction.txn_no == txn_no).with_for_update()
    )
    if txn is None:
        raise BizError(ErrCode.NOT_FOUND, "支付单不存在")
    if txn.user_id != user.id:
        raise BizError(ErrCode.FORBIDDEN)

    if txn.status in ("created", "paying"):
        remote = await gateway.query(txn.txn_no)
        txn.query_count += 1
        txn.last_query_at = utcnow()
        if remote["status"] == "SUCCESS":
            await mark_paid(session, txn, remote)
        elif remote["status"] == "FAIL":
            txn.status = "failed"
            txn.fail_reason = remote.get("reason") or "支付未完成"
        elif txn.expire_at < utcnow():
            txn.status = "closed"
        await session.commit()
    return await serialize_txn(session, txn)


async def mark_paid(session: AsyncSession, txn: PaymentTransaction, remote: dict) -> None:
    if txn.status == "success":
        return
    links = (await session.scalars(select(PaymentTxnBill).where(PaymentTxnBill.txn_id == txn.id))).all()
    bill_ids = [link.bill_id for link in links]
    result = await session.execute(
        update(Bill)
        .where(Bill.id.in_(bill_ids), Bill.status.in_(("unpaid", "overdue")))
        .values(status="paid", paid_at=utcnow())
    )
    if result.rowcount != len(bill_ids):
        await session.rollback()
        raise BizError(ErrCode.CONFLICT, "存在重复支付，已阻断并记录，请联系财务核实")
    txn.status = "success"
    txn.paid_at = utcnow()
    txn.gateway_txn_id = remote.get("txn_id")
    await enqueue(session, "bill.paid", {"txn_no": txn.txn_no, "bill_ids": bill_ids, "user_id": txn.user_id, "amount": money(txn.amount)})
    await send_message(
        session, txn.user_id, "paid", f"¥{money(txn.amount)} 支付成功",
        f"{CHANNEL_LABEL.get(txn.channel, txn.channel)} · 已到账 · 共 {len(bill_ids)} 笔账单",
        "payment", txn.id, dedup=False,
    )
    await session.flush()


async def mock_pay(session: AsyncSession, user: User, txn_no: str, success: bool) -> dict:
    if not settings.is_dev:
        raise BizError(ErrCode.NOT_FOUND)
    txn = await session.scalar(select(PaymentTransaction).where(PaymentTransaction.txn_no == txn_no))
    if txn is None or txn.user_id != user.id:
        raise BizError(ErrCode.NOT_FOUND, "支付单不存在")
    if txn.status not in ("created", "paying"):
        raise BizError(ErrCode.TXN_CLOSED)
    await gateway.mark(txn_no, "SUCCESS" if success else "FAIL", None if success else "用户取消支付")
    return {"txn_no": txn_no, "mock_status": "SUCCESS" if success else "FAIL"}


async def handle_callback(session: AsyncSession, channel: str, body: dict, signature: str | None) -> dict:
    """回调只用于触发主动查单，金额与状态一律以服务端查询结果为准。"""
    txn_no = body.get("txn_no")
    if not txn_no:
        raise BizError(ErrCode.CONFLICT, "缺少 txn_no")
    expected = hashlib.sha256(f"{txn_no}:{settings.jwt_secret}".encode()).hexdigest()
    if signature != expected:
        await write_audit(session, actor_id=None, action="payment.callback.invalid", detail={"channel": channel, "txn_no": txn_no})
        await session.commit()
        raise BizError(ErrCode.UNAUTHORIZED, "回调验签失败")
    txn = await session.scalar(select(PaymentTransaction).where(PaymentTransaction.txn_no == txn_no))
    if txn is None:
        raise BizError(ErrCode.NOT_FOUND, "支付单不存在")
    remote = await gateway.query(txn_no)
    if remote["status"] == "SUCCESS":
        await mark_paid(session, txn, remote)
    await enqueue(session, "payment.callback", {"txn_no": txn_no, "channel": channel})
    await session.commit()
    return {"received": True}


async def poll_pending_payments(session: AsyncSession) -> int:
    """兜底轮询：网关已成功但回调丢失时也能置为 success（防掉单）。"""
    deadline = utcnow() - timedelta(minutes=2)
    rows = (
        await session.scalars(
            select(PaymentTransaction)
            .where(PaymentTransaction.status.in_(("created", "paying")), PaymentTransaction.created_at <= deadline)
            .limit(50)
        )
    ).all()
    for txn in rows:
        remote = await gateway.query(txn.txn_no)
        if remote["status"] == "SUCCESS":
            await mark_paid(session, txn, remote)
        elif remote["status"] == "FAIL":
            txn.status = "failed"
            txn.fail_reason = remote.get("reason") or "支付失败"
        elif txn.expire_at < utcnow():
            txn.status = "closed"
        txn.query_count += 1
        txn.last_query_at = utcnow()
    await session.commit()
    return len(rows)


async def bonus_hint(session: AsyncSession, user: User) -> str | None:
    txn = await session.scalar(
        select(PaymentTransaction).where(PaymentTransaction.user_id == user.id).order_by(PaymentTransaction.created_at.desc()).limit(1)
    )
    return human_dt(txn.created_at) if txn else None
