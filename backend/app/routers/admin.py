"""管理端接口（宿管中心）。"""
from fastapi import APIRouter, Query, status

from app.core.response import ok
from app.deps import AdminUser, SessionDep
from app.models import User
from app.schemas import AssignIn, BillGenerateIn, FeedbackReplyIn, FinishIn, NoticeIn
from app.services import bill_service, content_service, feedback_service, repair_service
from sqlalchemy import select

router = APIRouter(prefix="/admin", tags=["管理端"])


@router.get("/repair/orders", summary="工单队列（默认待受理 + 处理中）")
async def queue(session: SessionDep, admin: AdminUser, status: str | None = None, building: str | None = None):
    return ok(await repair_service.admin_queue(session, status, building))


@router.post("/repair/orders/{order_id}/assign", summary="派单")
async def assign(order_id: int, payload: AssignIn, session: SessionDep, admin: AdminUser):
    return ok(await repair_service.assign_order(session, admin, order_id, payload.worker_id, payload.expect_finish_at))


@router.post("/repair/orders/{order_id}/finish", summary="代完工（含材料费）")
async def finish(order_id: int, payload: FinishIn, session: SessionDep, admin: AdminUser):
    return ok(await repair_service.finish_order(session, admin, order_id, payload.note, payload.material_fee))


@router.get("/workers", summary="维修工列表（派单下拉）")
async def workers(session: SessionDep, admin: AdminUser):
    rows = (await session.scalars(select(User).where(User.role == "worker", User.status == 1))).all()
    return ok(
        [{"id": w.id, "name": w.name, "worker_no": w.worker_no, "team": w.worker_team, "phone": w.phone} for w in rows]
    )


@router.post("/bills/generate", status_code=status.HTTP_201_CREATED, summary="批量生成账单")
async def generate_bills(payload: BillGenerateIn, session: SessionDep, admin: AdminUser):
    return ok(await bill_service.generate_bills(session, admin, payload))


@router.get("/feedbacks", summary="反馈列表")
async def feedbacks(
    session: SessionDep,
    admin: AdminUser,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    return ok(await feedback_service.admin_list(session, status, page, page_size))


@router.post("/feedbacks/{feedback_id}/reply", summary="回复反馈")
async def reply(feedback_id: int, payload: FeedbackReplyIn, session: SessionDep, admin: AdminUser):
    return ok(await feedback_service.admin_reply(session, admin, feedback_id, payload.content))


@router.post("/notices", status_code=status.HTTP_201_CREATED, summary="发布公告")
async def create_notice(payload: NoticeIn, session: SessionDep, admin: AdminUser):
    return ok(await content_service.create_notice(session, admin, payload))


@router.get("/notices/{notice_id}/receipts", summary="未读 / 未回执名单")
async def notice_receipts(notice_id: int, session: SessionDep, admin: AdminUser):
    return ok(await content_service.notice_receipts(session, notice_id))
