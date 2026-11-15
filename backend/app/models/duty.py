"""值日与卫生：规则、排班、检查记录。"""
from datetime import date, datetime

from sqlalchemy import JSON, BigInteger, Date, DateTime, SmallInteger, String, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import enum


class DutyRule(Base):
    __tablename__ = "duty_rules"

    room_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    mode: Mapped[str] = mapped_column(enum("daily", "weekly", name="duty_mode"), default="daily", nullable=False)
    member_order: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    areas: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    anchor_date: Mapped[date] = mapped_column(Date, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class DutySchedule(Base):
    __tablename__ = "duty_schedules"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    room_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger)
    duty_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    areas: Mapped[list | None] = mapped_column(JSON)
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("room_id", "week_start", "weekday", name="uk_room_week_day"),)


class HygieneCheck(Base):
    __tablename__ = "hygiene_checks"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    room_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    check_date: Mapped[date] = mapped_column(Date, nullable=False)
    week_no: Mapped[int | None] = mapped_column(SmallInteger)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    level: Mapped[str] = mapped_column(enum("excellent", "good", "pass", "fail", name="hygiene_level"), nullable=False)
    deductions: Mapped[list | None] = mapped_column(JSON)
    requirement: Mapped[str | None] = mapped_column(String(300))
    inspector: Mapped[str | None] = mapped_column(String(50))
    rectify_status: Mapped[str] = mapped_column(
        enum("none", "required", "submitted", "passed", name="rectify_status"), default="none", nullable=False
    )
    rectify_media: Mapped[list | None] = mapped_column(JSON)
    rectify_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("room_id", "check_date", name="uk_room_date"),)
