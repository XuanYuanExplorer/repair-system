"""账单与支付：bills / payment_transactions / payment_txn_bills / receipts。"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, Date, DateTime, Index, Numeric, SmallInteger, String, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin
from app.models.common import enum


class Bill(Base, TimestampMixin):
    __tablename__ = "bills"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    bill_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    student_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    room_id: Mapped[int | None] = mapped_column(BigInteger)
    bed_no: Mapped[int | None] = mapped_column(SmallInteger)
    type: Mapped[str] = mapped_column(
        enum("electricity", "accommodation", "material", "water", "penalty", name="bill_type"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    late_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSON)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        enum("unpaid", "paid", "overdue", "closed", name="bill_status"), default="unpaid", nullable=False
    )
    overdue_days: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(20))
    source_id: Mapped[int | None] = mapped_column(BigInteger)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (
        UniqueConstraint("source_type", "source_id", "type", name="uk_source"),
        Index("idx_bill_student_status", "student_id", "status", "due_date"),
        Index("idx_bill_due", "status", "due_date"),
    )


class PaymentTransaction(Base, TimestampMixin):
    __tablename__ = "payment_transactions"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    txn_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    channel: Mapped[str] = mapped_column(enum("wechat", "alipay", "campus_card", name="pay_channel"), nullable=False)
    status: Mapped[str] = mapped_column(
        enum("created", "paying", "success", "failed", "closed", name="txn_status"), default="created", nullable=False
    )
    gateway_txn_id: Mapped[str | None] = mapped_column(String(64))
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    expire_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)
    fail_reason: Mapped[str | None] = mapped_column(String(200))
    query_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    last_query_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (Index("idx_txn_poll", "status", "created_at"),)


class PaymentTxnBill(Base):
    __tablename__ = "payment_txn_bills"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    txn_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    bill_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    __table_args__ = (UniqueConstraint("txn_id", "bill_id", name="uk_txn_bill"),)


class Receipt(Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    receipt_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    bill_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    txn_id: Mapped[int | None] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(100), default="个人", nullable=False)
    email: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(
        enum("applied", "issued", "sent", "failed", name="receipt_status"), default="applied", nullable=False
    )
    file_url: Mapped[str | None] = mapped_column(String(255))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
