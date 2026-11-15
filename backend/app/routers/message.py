"""消息中心接口。"""
from fastapi import APIRouter, Query

from app.core.response import ok
from app.deps import CurrentUser, SessionDep
from app.schemas import PreferenceIn
from app.services import message_service

router = APIRouter(prefix="/messages", tags=["消息"])


@router.get("", summary="按业务类型分组的消息列表")
async def list_messages(
    session: SessionDep,
    user: CurrentUser,
    type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=50),
):
    return ok(await message_service.list_messages(session, user, type, page, page_size))


@router.get("/unread-count", summary="未读数（导航红点轻量轮询）")
async def unread_count(session: SessionDep, user: CurrentUser):
    return ok(await message_service.unread_count(session, user))


@router.get("/preferences", summary="推送偏好")
async def get_preferences(session: SessionDep, user: CurrentUser):
    return ok(await message_service.get_preferences(session, user))


@router.put("/preferences", summary="保存推送偏好")
async def put_preferences(payload: PreferenceIn, session: SessionDep, user: CurrentUser):
    return ok(await message_service.update_preferences(session, user, payload))


@router.post("/read-all", summary="一键全部已读（可按类型）")
async def read_all(session: SessionDep, user: CurrentUser, type: str | None = None):
    return ok(await message_service.read_all(session, user, type))


@router.post("/{message_id}/read", summary="单条已读")
async def read_one(message_id: int, session: SessionDep, user: CurrentUser):
    return ok(await message_service.read_one(session, user, message_id))
