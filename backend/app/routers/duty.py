"""值日与卫生接口。"""
from datetime import date

from fastapi import APIRouter, Query

from app.core.response import ok
from app.deps import CurrentUser, SessionDep
from app.schemas import DutyRuleIn, RectifyIn, ScheduleGenerateIn, ScheduleUpdateIn
from app.services import duty_service

router = APIRouter(tags=["值日与卫生"])


@router.get("/duty/schedule", summary="周视图（7 天 + 今日值日 + 区域）")
async def schedule(session: SessionDep, user: CurrentUser, week_start: date | None = None):
    return ok(await duty_service.schedule(session, user, week_start))


@router.get("/duty/rules", summary="值日轮换规则")
async def get_rules(session: SessionDep, user: CurrentUser):
    return ok(await duty_service.get_rule(session, user))


@router.put("/duty/rules", summary="设置轮换规则（仅寝室长）")
async def put_rules(payload: DutyRuleIn, session: SessionDep, user: CurrentUser):
    return ok(await duty_service.update_rule(session, user, payload))


@router.post("/duty/schedule/generate", summary="按规则生成本周排班")
async def generate(payload: ScheduleGenerateIn, session: SessionDep, user: CurrentUser):
    return ok(await duty_service.generate(session, user, payload.week_start))


@router.put("/duty/schedule/{schedule_id}", summary="手动调整某天值日生")
async def update_day(schedule_id: int, payload: ScheduleUpdateIn, session: SessionDep, user: CurrentUser):
    return ok(await duty_service.update_day(session, user, schedule_id, payload))


@router.get("/hygiene/checks", summary="卫生检查记录 + 学期均分")
async def checks(
    session: SessionDep,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    return ok(await duty_service.hygiene_checks(session, user, page, page_size))


@router.post("/hygiene/checks/{check_id}/rectify", summary="上传整改照片（1–4 张）")
async def rectify(check_id: int, payload: RectifyIn, session: SessionDep, user: CurrentUser):
    return ok(await duty_service.rectify(session, user, check_id, payload.media_urls))
