"""公共模型：文件、审计日志、事务性发件箱。"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CHAR, JSON, BigInteger, DateTime, Enum, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin

Money = Numeric(10, 2)


def enum(*values: str, name: str):
    """跨库枚举：MySQL 用 VARCHAR+应用校验，SQLite 同样可用（不建原生 ENUM）。"""
    return Enum(*values, name=name, native_enum=False, length=24, validate_strings=True)


class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    biz_type: Mapped[str] = mapped_column(String(20), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(60), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str | None] = mapped_column(CHAR(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(30))
    target_id: Mapped[int | None] = mapped_column(BigInteger)
    detail: Mapped[dict | None] = mapped_column(JSON)
    ip: Mapped[str | None] = mapped_column(String(45))
    trace_id: Mapped[str | None] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(enum("pending", "done", "failed", name="outbox_status"), default="pending", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


__all__ = ["File", "AuditLog", "OutboxEvent", "Money", "enum", "TimestampMixin", "Decimal"]
