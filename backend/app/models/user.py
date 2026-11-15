"""账号与安全：users / refresh_tokens / login_devices / password_history。"""
from datetime import datetime

from sqlalchemy import CHAR, BigInteger, DateTime, Index, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, TimestampMixin
from app.models.common import enum


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    student_no: Mapped[str | None] = mapped_column(String(20), unique=True)
    username: Mapped[str | None] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(enum("student", "worker", "admin", name="user_role"), default="student", index=True)
    gender: Mapped[int | None] = mapped_column(SmallInteger)
    college: Mapped[str | None] = mapped_column(String(50))
    class_name: Mapped[str | None] = mapped_column(String(50))
    grade: Mapped[int | None] = mapped_column(SmallInteger)
    avatar_url: Mapped[str | None] = mapped_column(String(255))
    emergency_name: Mapped[str | None] = mapped_column(String(50))
    emergency_phone: Mapped[str | None] = mapped_column(String(20))
    worker_no: Mapped[str | None] = mapped_column(String(20), unique=True)
    worker_team: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True, nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime)
    replaced_by: Mapped[str | None] = mapped_column(CHAR(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (Index("idx_refresh_user", "user_id", "revoked_at"),)


class LoginDevice(Base):
    __tablename__ = "login_devices"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(100))
    ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    revoked: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "device_id", name="uk_user_device"),)


class PasswordHistory(Base):
    __tablename__ = "password_history"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
