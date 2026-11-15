"""反馈域：意见反馈与处理轨迹。"""
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, SmallInteger, String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.common import enum


class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    fb_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    type: Mapped[str] = mapped_column(enum("attitude", "quality", "charge", "suggestion", name="feedback_type"), nullable=False)
    order_id: Mapped[int | None] = mapped_column(BigInteger)
    content: Mapped[str] = mapped_column(String(300), nullable=False)
    media_urls: Mapped[list | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        enum("submitted", "processing", "replied", "closed", name="feedback_status"), default="submitted", nullable=False
    )
    reply: Mapped[str | None] = mapped_column(String(500))
    replied_at: Mapped[datetime | None] = mapped_column(DateTime)
    satisfaction: Mapped[int | None] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class FeedbackReply(Base):
    __tablename__ = "feedback_replies"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    feedback_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    replier_id: Mapped[int | None] = mapped_column(BigInteger)
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
