"""公告接口。"""
from fastapi import APIRouter, Query

from app.core.response import ok
from app.deps import CurrentUser, SessionDep
from app.services import content_service

router = APIRouter(prefix="/notices", tags=["公告"])


@router.get("", summary="公告列表（置顶优先 + 未读态）")
async def list_notices(
    session: SessionDep,
    user: CurrentUser,
    type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    return ok(await content_service.list_notices(session, user, type_=type, page=page, page_size=page_size))


@router.get("/{notice_id}", summary="公告详情（首次查看自动标记已读）")
async def notice_detail(notice_id: int, session: SessionDep, user: CurrentUser):
    return ok(await content_service.detail(session, user, notice_id))


@router.post("/{notice_id}/read", summary="标记已读")
async def mark_read(notice_id: int, session: SessionDep, user: CurrentUser):
    return ok(await content_service.mark_read(session, user, notice_id))


@router.post("/{notice_id}/receipt", summary="回执确认")
async def receipt(notice_id: int, session: SessionDep, user: CurrentUser):
    return ok(await content_service.confirm_receipt(session, user, notice_id))
