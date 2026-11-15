"""SQLAlchemy 2.0 异步引擎与会话。"""
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path

from sqlalchemy import DateTime, MetaData, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import NullPool

from app.config import settings

NAMING_CONVENTION = {
    "ix": "idx_%(column_0_label)s",
    "uq": "uk_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


if settings.is_sqlite:
    Path(settings.database_url.split("///")[-1]).parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        poolclass=NullPool,
        connect_args={"timeout": 30},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragma(dbapi_conn, _):  # pragma: no cover - 基础设施
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
else:
    engine = create_async_engine(
        settings.database_url,
        echo=settings.db_echo,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
        pool_recycle=1800,
    )

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def create_all() -> None:
    import app.models  # noqa: F401  确保全部模型已注册

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
