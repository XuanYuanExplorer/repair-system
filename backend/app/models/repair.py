"""报修域：时段、工单、事件时间轴、催单、沟通、评价。"""
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import JSON, BigInteger, Date, DateTime, Index, Integer, Numeric, SmallInteger, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin
from app.models.common import enum


class RepairSlot(Base):
    __tablename__ = "repair_slots"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    building: Mapped[str] = mapped_column(String(20), nullable=False)
    slot_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    slot_code: Mapped[str] = mapped_column(String(10), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    capacity: Mapped[int] = mapped_column(SmallInteger, default=6, nullable=False)
    booked: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    __table_args__ = (UniqueConstraint("building", "slot_date", "slot_code", name="uk_slot"),)


class RepairOrder(Base, TimestampMixin):
    __tablename__ = "repair_orders"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    student_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    room_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    bed_no: Mapped[int | None] = mapped_column(SmallInteger)
    category: Mapped[str] = mapped_column(enum("water", "door", "furniture", "network", "ac", "public", name="repair_category"), nullable=False)
    location_type: Mapped[str] = mapped_column(enum("in_room", "public", name="repair_location_type"), default="in_room")
    location_desc: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    media_urls: Mapped[list | None] = mapped_column(JSON, default=list)
    preferred_date: Mapped[date | None] = mapped_column(Date)
    preferred_slot: Mapped[str | None] = mapped_column(String(10))
    require_presence: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        enum("pending", "assigned", "fixing", "verify", "done", "cancelled", name="repair_status"),
        default="pending",
        nullable=False,
    )
    worker_id: Mapped[int | None] = mapped_column(BigInteger)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    fixed_at: Mapped[datetime | None] = mapped_column(DateTime)
    done_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancel_reason: Mapped[str | None] = mapped_column(String(200))
    expect_finish_at: Mapped[datetime | None] = mapped_column(DateTime)
    fix_note: Mapped[str | None] = mapped_column(String(500))
    material_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    is_timeout: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    urge_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    last_urge_at: Mapped[datetime | None] = mapped_column(DateTime)
    repair_round: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    client_request_id: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint("student_id", "client_request_id", name="uk_client_req"),
        Index("idx_order_student_status", "student_id", "status", "created_at"),
        Index("idx_order_worker_status", "worker_id", "status"),
        Index("idx_order_status_created", "status", "created_at"),
    )


class RepairEvent(Base):
    __tablename__ = "repair_events"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str | None] = mapped_column(String(20))
    actor_id: Mapped[int | None] = mapped_column(BigInteger)
    actor_name: Mapped[str | None] = mapped_column(String(50))
    actor_role: Mapped[str | None] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("idx_event_order_time", "order_id", "created_at"),)


class RepairUrge(Base):
    __tablename__ = "repair_urges"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RepairMessage(Base):
    __tablename__ = "repair_messages"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    sender_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("idx_msg_order_time", "order_id", "created_at"),)


class RepairRating(Base):
    __tablename__ = "repair_ratings"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    order_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    student_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    worker_id: Mapped[int | None] = mapped_column(BigInteger)
    speed: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    attitude: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    quality: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    avg_score: Mapped[Decimal] = mapped_column(Numeric(2, 1), nullable=False)
    content: Mapped[str | None] = mapped_column(String(200))
    is_anonymous: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("idx_rating_worker", "worker_id", "created_at"),)
