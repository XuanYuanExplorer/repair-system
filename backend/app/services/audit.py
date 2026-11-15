"""审计日志：管理端写操作、登录失败、改密等必写。"""
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tracing import current_trace_id
from app.models import AuditLog


async def write_audit(
    session: AsyncSession,
    *,
    actor_id: int | None,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    detail: dict | None = None,
    request: Request | None = None,
) -> None:
    ip = None
    if request is not None:
        ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
            request.client.host if request.client else None
        )
    session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
            ip=ip,
            trace_id=current_trace_id(),
        )
    )
