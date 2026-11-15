"""账单与支付接口。"""
from urllib.parse import quote

from fastapi import APIRouter, Header, Query, Request, Response, status
from fastapi.responses import FileResponse

from app.core.response import ok
from app.deps import CurrentUser, SessionDep
from app.schemas import PaymentCreateIn, ReceiptApplyIn
from app.services import bill_service, payment_service

router = APIRouter(tags=["账单与支付"])


@router.get("/bills/summary", summary="账单汇总（待缴/已缴/逾期/本学期累计）")
async def bill_summary(session: SessionDep, user: CurrentUser):
    return ok(await bill_service.summary(session, user))


@router.get("/bills/records/export", summary="导出对账单 CSV")
async def export_records(session: SessionDep, user: CurrentUser, year: str | None = None):
    filename, content = await bill_service.export_csv(session, user, year)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get("/bills/records", summary="缴费记录（按自然月分组 + 逾期留痕）")
async def bill_records(session: SessionDep, user: CurrentUser, year: str | None = None, type: str | None = None):
    return ok(await bill_service.records(session, user, year=year, type_=type))


@router.get("/bills", summary="账单列表")
async def bills(
    session: SessionDep,
    user: CurrentUser,
    status_: str | None = Query(default=None, alias="status"),
    type: str | None = None,
    year: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    return ok(await bill_service.list_bills(session, user, status=status_, type_=type, year=year, page=page, page_size=page_size))


@router.get("/bills/{bill_id}", summary="账单详情（含费用明细与可支付标记）")
async def bill_detail(bill_id: int, session: SessionDep, user: CurrentUser):
    return ok(await bill_service.detail(session, user, bill_id))


@router.post("/bills/{bill_id}/receipt", summary="申请电子票据")
async def apply_receipt(bill_id: int, payload: ReceiptApplyIn, session: SessionDep, user: CurrentUser):
    return ok(await bill_service.apply_receipt(session, user, bill_id, payload))


@router.get("/receipts/{receipt_id}/file", summary="下载票据 PDF")
async def receipt_file(receipt_id: int, session: SessionDep, user: CurrentUser):
    filename, path = await bill_service.receipt_file(session, user, receipt_id)
    return FileResponse(path, media_type="application/pdf", filename=filename)


@router.post("/payment/create", status_code=status.HTTP_200_OK, summary="创建支付（单笔 / 合并）")
async def create_payment(
    payload: PaymentCreateIn,
    session: SessionDep,
    user: CurrentUser,
    idem_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    return ok(await payment_service.create_payment(session, user, payload.bill_ids, payload.channel, idem_key))


@router.get("/payment/transactions/{txn_no}", summary="服务端主动查单并返回终态（防掉单）")
async def query_transaction(txn_no: str, session: SessionDep, user: CurrentUser):
    return ok(await payment_service.query_result(session, user, txn_no))


@router.post("/payment/mock/pay", summary="仅 dev：模拟网关支付结果")
async def mock_pay(session: SessionDep, user: CurrentUser, txn_no: str, success: bool = True):
    return ok(await payment_service.mock_pay(session, user, txn_no, success))


@router.post("/payment/callback/{channel}", summary="网关异步回调（验签 + 只信服务端查单）")
async def payment_callback(channel: str, request: Request, session: SessionDep):
    body = await request.json()
    signature = request.headers.get("x-pay-signature")
    return ok(await payment_service.handle_callback(session, channel, body, signature))
