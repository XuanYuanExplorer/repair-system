"""首页聚合与公共接口。"""
from fastapi import APIRouter
from sqlalchemy import text

from app.core.response import ok
from app.db import engine
from app.deps import CurrentUser, SessionDep
from app.services import content_service, home_service

router = APIRouter(tags=["首页"])


@router.get("/home/summary", summary="服务大厅聚合数据")
async def summary(user: CurrentUser, session: SessionDep):
    return ok(await home_service.summary(session, user))


@router.get("/public/notices/latest", summary="登录页公告条（无需鉴权）")
async def latest_notices(session: SessionDep):
    return ok(await content_service.latest_public_notices(session))


@router.get("/healthz", summary="存活探针")
async def healthz():
    return {"status": "ok"}


@router.get("/readyz", summary="就绪探针（校验数据库）")
async def readyz(session: SessionDep):
    await session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}


@router.get("/meta", summary="平台元信息")
async def meta():
    from app.config import settings

    return ok(
        {
            "app_name": settings.app_name,
            "env": settings.env,
            "pay_provider": settings.pay_provider,
            "sms_provider": settings.sms_provider,
            "school": "江南大学 · 智慧宿管中心",
        }
    )


__all__ = ["router", "engine"]
