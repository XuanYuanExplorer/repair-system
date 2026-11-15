"""消息域：站内消息、推送偏好、投递日志。"""
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Index, SmallInteger, String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import enum


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    type: Mapped[str] = mapped_column(enum("order", "bill", "notice", "paid", "system", name="message_type"), nullable=False)
    biz_type: Mapped[str | None] = mapped_column(String(20))
    biz_id: Mapped[int | None] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    is_read: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_msg_user_type", "user_id", "type", "created_at"),
        Index("idx_msg_user_unread", "user_id", "is_read"),
    )


class MessagePreference(Base):
    __tablename__ = "message_preferences"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sms_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    wechat_types: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class PushLog(Base):
    __tablename__ = "push_logs"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    message_id: Mapped[int | None] = mapped_column(BigInteger)
    channel: Mapped[str] = mapped_column(enum("sms", "wechat", "push", name="push_channel"), nullable=False)
    status: Mapped[str] = mapped_column(enum("success", "failed", name="push_status"), nullable=False)
    error: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
