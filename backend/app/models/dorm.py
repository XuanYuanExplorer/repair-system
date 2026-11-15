"""寝室域：房间、床位、设施、公共物品、公约、住宿调整申请。"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, Numeric, SmallInteger, String, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin
from app.models.common import enum


class DormRoom(Base, TimestampMixin):
    __tablename__ = "dorm_rooms"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    building: Mapped[str] = mapped_column(String(20), nullable=False)
    room_no: Mapped[str] = mapped_column(String(10), nullable=False)
    floor: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    room_type: Mapped[str] = mapped_column(String(30), default="标准四人间", nullable=False)
    area: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    capacity: Mapped[int] = mapped_column(SmallInteger, default=4, nullable=False)
    leader_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)

    __table_args__ = (UniqueConstraint("building", "room_no", name="uk_building_room"),)


class DormBed(Base):
    __tablename__ = "dorm_beds"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    room_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    bed_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    position: Mapped[str] = mapped_column(enum("upper", "lower", name="bed_position"), nullable=False)
    student_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    check_in_at: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("room_id", "bed_no", name="uk_room_bed"),)


class DormFacility(Base, TimestampMixin):
    __tablename__ = "dorm_facilities"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    room_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(enum("normal", "fault", "repairing", name="facility_status"), default="normal")
    enabled_year: Mapped[int | None] = mapped_column(SmallInteger)
    fault_note: Mapped[str | None] = mapped_column(String(200))
    last_repair_at: Mapped[date | None] = mapped_column(Date)


class DormAsset(Base):
    __tablename__ = "dorm_assets"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    room_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    holder_id: Mapped[int | None] = mapped_column(BigInteger)
    borrowed_at: Mapped[datetime | None] = mapped_column(DateTime)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(enum("available", "borrowed", "lost", name="asset_status"), default="available")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DormRule(Base):
    __tablename__ = "dorm_rules"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    room_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seq: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    content: Mapped[str] = mapped_column(String(200), nullable=False)
    updated_by: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("room_id", "seq", name="uk_room_seq"),)


class RoomChangeRequest(Base):
    __tablename__ = "room_change_requests"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    room_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    student_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    req_type: Mapped[str] = mapped_column(enum("checkin", "checkout", "swap", name="room_req_type"), nullable=False)
    target_room: Mapped[str | None] = mapped_column(String(20))
    reason: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(enum("pending", "approved", "rejected", name="room_req_status"), default="pending")
    reviewer_id: Mapped[int | None] = mapped_column(BigInteger)
    review_note: Mapped[str | None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
