"""报修接口：时段、工单、催单、沟通、确认、评价、档案。"""
from datetime import date

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.core.response import ok
from app.core.timeutil import parse_date
from app.deps import CurrentUser, SessionDep, WorkerUser, require_role
from app.schemas import CancelIn, OrderMessageIn, RateIn, RepairOrderIn, RepairOrderPatch, VerifyIn
from app.services import repair_service

router = APIRouter(prefix="/repair", tags=["报修"])


@router.get("/slots", summary="上门时段余量")
async def slots(session: SessionDep, user: CurrentUser, day: date | None = Query(default=None, alias="date")):
    from app.core.timeutil import local_today

    return ok(await repair_service.list_slots(session, user, day or local_today()))


@router.post("/orders", status_code=status.HTTP_201_CREATED, summary="创建工单（支持 Idempotency-Key）")
async def create_order(
    payload: RepairOrderIn,
    session: SessionDep,
    user: CurrentUser,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    data, created = await repair_service.create_order(session, user, payload, idempotency_key)
    if not created:
        response.status_code = status.HTTP_200_OK
    return ok(data, "工单已提交" if created else "工单已存在")


@router.get("/orders", summary="我的工单分页 + 状态计数")
async def list_orders(
    session: SessionDep,
    user: CurrentUser,
    status_: str | None = Query(default=None, alias="status"),
    category: str | None = None,
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    return ok(
        await repair_service.list_orders(
            session, user, status=status_, category=category, keyword=keyword, page=page, page_size=page_size
        )
    )


@router.get("/orders/{order_id}", summary="工单详情（含时间轴、师傅、最近沟通）")
async def order_detail(order_id: int, session: SessionDep, user: CurrentUser):
    return ok(await repair_service.order_detail(session, user, order_id))


@router.patch("/orders/{order_id}", summary="修改工单（仅待受理 / 已派单）")
async def patch_order(order_id: int, payload: RepairOrderPatch, session: SessionDep, user: CurrentUser):
    return ok(await repair_service.update_order(session, user, order_id, payload))


@router.post("/orders/{order_id}/cancel", summary="取消工单（开工前）")
async def cancel_order(order_id: int, payload: CancelIn, session: SessionDep, user: CurrentUser):
    return ok(await repair_service.cancel_order(session, user, order_id, payload.reason))


@router.post("/orders/{order_id}/urge", summary="催单（5 分钟冷却）")
async def urge_order(order_id: int, session: SessionDep, user: CurrentUser):
    return ok(await repair_service.urge_order(session, user, order_id))


@router.get("/orders/{order_id}/messages", summary="工单沟通记录（after_id 增量）")
async def get_messages(order_id: int, session: SessionDep, user: CurrentUser, after_id: int | None = None):
    return ok(await repair_service.list_messages(session, user, order_id, after_id))


@router.post("/orders/{order_id}/messages", summary="发送沟通消息（每分钟 10 条）")
async def post_message(order_id: int, payload: OrderMessageIn, session: SessionDep, user: CurrentUser):
    return ok(await repair_service.post_message(session, user, order_id, payload.content))


@router.post("/orders/{order_id}/verify", summary="完工确认 / 申请返修")
async def verify_order(order_id: int, payload: VerifyIn, session: SessionDep, user: CurrentUser):
    return ok(await repair_service.verify_order(session, user, order_id, payload))


@router.post("/orders/{order_id}/rate", summary="三维评分 + 文字 + 匿名")
async def rate_order(order_id: int, payload: RateIn, session: SessionDep, user: CurrentUser):
    return ok(await repair_service.rate_order(session, user, order_id, payload))


@router.get("/archive", summary="维修档案统计")
async def archive(session: SessionDep, user: CurrentUser):
    return ok(await repair_service.archive(session, user))


@router.get("/worker/orders", summary="维修工待办工单")
async def worker_orders(session: SessionDep, user: WorkerUser):
    return ok(await repair_service.my_worker_orders(session, user))


@router.post("/worker/orders/{order_id}/accept", summary="维修工接单")
async def worker_accept(order_id: int, session: SessionDep, worker=Depends(require_role("worker"))):
    return ok(await repair_service.worker_accept(session, worker, order_id))


__all__ = ["router", "parse_date"]
