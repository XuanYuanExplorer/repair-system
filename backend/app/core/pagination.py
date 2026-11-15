"""分页工具：page 从 1 开始，page_size 上限 50。"""
from dataclasses import dataclass

from fastapi import Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def pagination(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


async def count_of(session: AsyncSession, stmt) -> int:
    sub = stmt.order_by(None).subquery()
    return int(await session.scalar(select(func.count()).select_from(sub)) or 0)


async def fetch_page(session: AsyncSession, stmt, params: PageParams) -> tuple[list, int]:
    total = await count_of(session, stmt)
    rows = (await session.scalars(stmt.offset(params.offset).limit(params.page_size))).all()
    return list(rows), total
