"""寝室接口。"""
from fastapi import APIRouter, status

from app.core.response import ok
from app.deps import AdminUser, CurrentUser, SessionDep
from app.schemas import RoomChangeIn, RulesIn
from app.services import dorm_service

router = APIRouter(prefix="/dorm", tags=["寝室"])


@router.get("/my-room", summary="我的寝室信息 + 设施清单")
async def my_room(session: SessionDep, user: CurrentUser):
    return ok(await dorm_service.my_room(session, user))


@router.get("/members", summary="成员名单（含 can_edit 标记）")
async def members(session: SessionDep, user: CurrentUser, room_id: int | None = None):
    return ok(await dorm_service.members(session, user, room_id))


@router.get("/rules", summary="本寝公约")
async def get_rules(session: SessionDep, user: CurrentUser):
    return ok(await dorm_service.get_rules(session, user))


@router.put("/rules", summary="覆盖式更新公约（仅寝室长）")
async def put_rules(payload: RulesIn, session: SessionDep, user: CurrentUser):
    return ok(await dorm_service.update_rules(session, user, payload.items))


@router.get("/assets", summary="公共物品与领用记录")
async def assets(session: SessionDep, user: CurrentUser):
    return ok(await dorm_service.assets(session, user))


@router.post("/assets/{asset_id}/borrow", summary="借用登记")
async def borrow(asset_id: int, session: SessionDep, user: CurrentUser):
    return ok(await dorm_service.borrow_asset(session, user, asset_id))


@router.post("/assets/{asset_id}/return", summary="归还")
async def give_back(asset_id: int, session: SessionDep, user: CurrentUser):
    return ok(await dorm_service.return_asset(session, user, asset_id))


@router.post("/room-change-requests", status_code=status.HTTP_201_CREATED, summary="提交入住 / 退宿 / 调宿申请")
async def create_request(payload: RoomChangeIn, session: SessionDep, user: CurrentUser):
    return ok(await dorm_service.create_room_change(session, user, payload))


@router.get("/room-change-requests", summary="我的 / 本寝申请进度")
async def list_requests(session: SessionDep, user: CurrentUser):
    return ok(await dorm_service.list_room_changes(session, user))


@router.get("/admin/members/{room_id}", summary="宿管查看指定寝室成员")
async def admin_members(room_id: int, session: SessionDep, admin: AdminUser):
    return ok(await dorm_service.members(session, admin, room_id))
