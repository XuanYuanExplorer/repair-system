"""个人中心与帮助中心接口。"""
from fastapi import APIRouter, Body, Query

from app.core.response import ok
from app.deps import CurrentUser, SessionDep
from app.services import content_service, profile_service

router = APIRouter(tags=["个人中心"])


@router.get("/profile", summary="个人资料 + 认证信息（只读）+ 安全项")
async def profile(session: SessionDep, user: CurrentUser):
    return ok(await profile_service.profile(session, user))


@router.put("/profile", summary="仅头像、性别、紧急联系人、邮箱可改")
async def update_profile(session: SessionDep, user: CurrentUser, payload: dict = Body(default_factory=dict)):
    return ok(await profile_service.update_profile(session, user, payload))


@router.get("/profile/devices", summary="登录设备与安全记录")
async def devices(session: SessionDep, user: CurrentUser):
    return ok(await profile_service.devices(session, user))


@router.get("/help/faqs", summary="FAQ 搜索（无需鉴权）")
async def faqs(session: SessionDep, q: str | None = None, category: str | None = None):
    return ok(await content_service.search_faqs(session, q, category))


@router.get("/help/hotlines", summary="服务电话（无需鉴权）")
async def hotlines():
    return ok(content_service.hotlines())


@router.get("/help/search", summary="帮助中心统一搜索", include_in_schema=False)
async def search(session: SessionDep, q: str = Query(min_length=1)):
    return ok({"faqs": await content_service.search_faqs(session, q, None)})
