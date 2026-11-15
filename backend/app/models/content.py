"""内容域：公告、已读回执、FAQ。"""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import enum


class Notice(Base):
    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    scope: Mapped[str] = mapped_column(enum("all", "building", "room", name="notice_scope"), default="all")
    building: Mapped[str | None] = mapped_column(String(20))
    room_id: Mapped[int | None] = mapped_column(BigInteger)
    type: Mapped[str] = mapped_column(enum("notice", "check", "utility", "safety", name="notice_type"), default="notice")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_pinned: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    require_receipt: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    publisher_id: Mapped[int | None] = mapped_column(BigInteger)
    publisher_name: Mapped[str | None] = mapped_column(String(50))
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class NoticeReceipt(Base):
    __tablename__ = "notice_receipts"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    notice_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    is_read: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    receipt_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (UniqueConstraint("notice_id", "user_id", name="uk_notice_user"),)


class Faq(Base):
    __tablename__ = "faqs"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    category: Mapped[str] = mapped_column(String(30), default="通用", nullable=False)
    question: Mapped[str] = mapped_column(String(200), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    is_self_help: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
