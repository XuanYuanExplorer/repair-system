"""意见反馈接口。"""
from fastapi import APIRouter, Query, status

from app.core.response import ok
from app.deps import CurrentUser, SessionDep
from app.schemas import FeedbackIn, SatisfactionIn
from app.services import feedback_service

router = APIRouter(prefix="/feedbacks", tags=["反馈"])


@router.post("", status_code=status.HTTP_201_CREATED, summary="提交反馈")
async def create(payload: FeedbackIn, session: SessionDep, user: CurrentUser):
    return ok(await feedback_service.create(session, user, payload))


@router.get("", summary="我的反馈与处理进度")
async def list_mine(
    session: SessionDep, user: CurrentUser, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=50)
):
    return ok(await feedback_service.list_mine(session, user, page, page_size))


@router.post("/{feedback_id}/satisfaction", summary="满意度评价（仅已回复）")
async def rate(feedback_id: int, payload: SatisfactionIn, session: SessionDep, user: CurrentUser):
    return ok(await feedback_service.rate(session, user, feedback_id, payload.score))
