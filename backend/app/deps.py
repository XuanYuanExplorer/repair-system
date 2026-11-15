"""依赖注入：会话、当前用户、角色守卫、寝室长派生权限。"""
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache
from app.core.errors import BizError, ErrCode
from app.core.security import decode_token
from app.db import get_session
from app.models import DormRoom, User

bearer = HTTPBearer(auto_error=False, description="Bearer <access_token>")

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    cred: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> User:
    if cred is None or not cred.credentials:
        raise BizError(ErrCode.UNAUTHORIZED)
    payload = decode_token(cred.credentials, expect="access")
    if await cache.exists(f"jwt:blacklist:{payload['jti']}"):
        raise BizError(ErrCode.TOKEN_INVALID)
    user = await session.get(User, int(payload["sub"]))
    if user is None:
        raise BizError(ErrCode.UNAUTHORIZED)
    if user.status != 1:
        raise BizError(ErrCode.ACCOUNT_DISABLED)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):
    async def _dep(user: CurrentUser) -> User:
        if user.role not in roles:
            raise BizError(ErrCode.FORBIDDEN)
        return user

    return _dep


StudentUser = Annotated[User, Depends(require_role("student"))]
WorkerUser = Annotated[User, Depends(require_role("worker", "admin"))]
AdminUser = Annotated[User, Depends(require_role("admin"))]


async def get_room_of_user(session: AsyncSession, user: User) -> DormRoom | None:
    from app.models import DormBed

    bed = await session.scalar(
        select(DormBed).where(DormBed.student_id == user.id, DormBed.status == 1)
    )
    if not bed:
        return None
    return await session.get(DormRoom, bed.room_id)


async def require_room_leader(session: AsyncSession, user: User, room_id: int) -> DormRoom:
    room = await session.get(DormRoom, room_id)
    if room is None:
        raise BizError(ErrCode.NOT_FOUND, "寝室不存在")
    if user.role != "admin" and room.leader_id != user.id:
        raise BizError(ErrCode.FORBIDDEN)
    return room


def client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else None
    )
    ua = request.headers.get("user-agent")
    return ip, (ua[:255] if ua else None)
