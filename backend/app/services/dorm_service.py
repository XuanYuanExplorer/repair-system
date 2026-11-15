"""寝室服务：房间信息、成员、公约、公共物品、住宿调整申请。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BizError, ErrCode
from app.core.timeutil import human_dt, local_date_str, utcnow
from app.models import DormAsset, DormBed, DormFacility, DormRoom, DormRule, RoomChangeRequest, User
from app.services.audit import write_audit
from app.services.auth_service import mask_phone


async def current_room(session: AsyncSession, user: User) -> tuple[DormRoom, DormBed]:
    bed = await session.scalar(select(DormBed).where(DormBed.student_id == user.id, DormBed.status == 1))
    if bed is None:
        raise BizError(ErrCode.DORM_NOT_MATCHED)
    room = await session.get(DormRoom, bed.room_id)
    if room is None:
        raise BizError(ErrCode.DORM_NOT_MATCHED)
    return room, bed


async def _facilities(session: AsyncSession, room_id: int) -> list[dict]:
    rows = (await session.scalars(select(DormFacility).where(DormFacility.room_id == room_id).order_by(DormFacility.id))).all()
    return [
        {
            "id": f.id,
            "name": f.name,
            "category": f.category,
            "status": f.status,
            "status_label": {"normal": "正常", "fault": "故障", "repairing": "维修中"}[f.status],
            "enabled_year": f.enabled_year,
            "fault_note": f.fault_note,
            "last_repair_at": local_date_str(f.last_repair_at),
        }
        for f in rows
    ]


async def my_room(session: AsyncSession, user: User) -> dict:
    room, bed = await current_room(session, user)
    beds = (await session.scalars(select(DormBed).where(DormBed.room_id == room.id).order_by(DormBed.bed_no))).all()
    leader = await session.get(User, room.leader_id) if room.leader_id else None
    occupied = [b for b in beds if b.student_id]
    facilities = await _facilities(session, room.id)
    return {
        "id": room.id,
        "building": room.building,
        "room_no": room.room_no,
        "title": f"{room.building} {room.room_no} 室",
        "floor": room.floor,
        "room_type": room.room_type,
        "area": str(room.area) if room.area is not None else None,
        "subtitle": f"{'男生宿舍' if user.gender == 1 else '学生宿舍'} · {room.room_type} · {str(room.area).rstrip('0').rstrip('.') if room.area else '—'} ㎡",
        "capacity": room.capacity,
        "occupied": len(occupied),
        "leader_name": leader.name if leader else "—",
        "leader_id": room.leader_id,
        "my_bed": {
            "bed_no": bed.bed_no,
            "position": bed.position,
            "position_label": "上铺" if bed.position == "upper" else "下铺",
            "check_in_at": local_date_str(bed.check_in_at),
        },
        "is_leader": room.leader_id == user.id,
        "facilities": facilities,
    }


async def members(session: AsyncSession, user: User, room_id: int | None = None) -> dict:
    own_room, _ = await current_room(session, user)
    if room_id is not None and room_id != own_room.id:
        # 非本寝成员（含跨楼栋）一律拒绝，管理员走 /dorm/admin/members/{room_id}
        if user.role != "admin":
            raise BizError(ErrCode.FORBIDDEN)
        room = await session.get(DormRoom, room_id)
        if room is None:
            raise BizError(ErrCode.NOT_FOUND, "寝室不存在")
    else:
        room = own_room

    beds = (await session.scalars(select(DormBed).where(DormBed.room_id == room.id).order_by(DormBed.bed_no))).all()
    items = []
    for b in beds:
        if b.student_id is None:
            items.append(
                {
                    "bed_no": b.bed_no,
                    "position": b.position,
                    "position_label": "上铺" if b.position == "upper" else "下铺",
                    "name": "空床位",
                    "empty": True,
                    "is_leader": False,
                    "is_me": False,
                }
            )
            continue
        stu = await session.get(User, b.student_id)
        if stu is None:
            continue
        items.append(
            {
                "user_id": stu.id,
                "bed_no": b.bed_no,
                "position": b.position,
                "position_label": "上铺" if b.position == "upper" else "下铺",
                "name": stu.name,
                "empty": False,
                "college": stu.college,
                "class_name": stu.class_name,
                "phone": mask_phone(stu.phone),
                "is_leader": room.leader_id == stu.id,
                "is_me": stu.id == user.id,
            }
        )
    return {
        "room_id": room.id,
        "room": f"{room.building} {room.room_no} 室",
        "capacity": room.capacity,
        "occupied": sum(1 for i in items if not i["empty"]),
        "can_edit": room.leader_id == user.id,
        "is_leader": room.leader_id == user.id,
        "items": items,
    }


async def get_rules(session: AsyncSession, user: User) -> dict:
    room, _ = await current_room(session, user)
    rows = (await session.scalars(select(DormRule).where(DormRule.room_id == room.id).order_by(DormRule.seq))).all()
    return {
        "room_id": room.id,
        "can_edit": room.leader_id == user.id,
        "items": [{"seq": r.seq, "content": r.content} for r in rows],
    }


async def update_rules(session: AsyncSession, user: User, items: list[str]) -> dict:
    room, _ = await current_room(session, user)
    if room.leader_id != user.id:
        raise BizError(ErrCode.FORBIDDEN)
    if len(items) > 8:
        raise BizError(ErrCode.CONFLICT, "公约最多 8 条")
    old = (await session.scalars(select(DormRule).where(DormRule.room_id == room.id))).all()
    for r in old:
        await session.delete(r)
    await session.flush()
    for idx, content in enumerate(items, start=1):
        session.add(DormRule(room_id=room.id, seq=idx, content=content.strip(), updated_by=user.id))
    await write_audit(session, actor_id=user.id, action="dorm.rules.update", target_type="room", target_id=room.id, detail={"count": len(items)})
    await session.commit()
    return await get_rules(session, user)


async def assets(session: AsyncSession, user: User) -> list[dict]:
    room, _ = await current_room(session, user)
    rows = (await session.scalars(select(DormAsset).where(DormAsset.room_id == room.id).order_by(DormAsset.id))).all()
    out = []
    for a in rows:
        holder = await session.get(User, a.holder_id) if a.holder_id else None
        out.append(
            {
                "id": a.id,
                "name": a.name,
                "status": a.status,
                "holder_name": holder.name if holder else None,
                "holder_is_me": a.holder_id == user.id,
                "borrowed_at": human_dt(a.borrowed_at),
                "returned_at": human_dt(a.returned_at),
                "text": (
                    f"{holder.name} · {human_dt(a.borrowed_at)} 借 · 未归还"
                    if a.status == "borrowed" and holder
                    else (f"{holder.name} · {human_dt(a.returned_at)} 已归还" if holder else "在库 · 可借用")
                ),
            }
        )
    return out


async def borrow_asset(session: AsyncSession, user: User, asset_id: int) -> dict:
    room, _ = await current_room(session, user)
    asset = await session.get(DormAsset, asset_id)
    if asset is None or asset.room_id != room.id:
        raise BizError(ErrCode.NOT_FOUND, "物品不存在")
    if asset.status == "borrowed":
        raise BizError(ErrCode.CONFLICT, "该物品已被借出")
    asset.status = "borrowed"
    asset.holder_id = user.id
    asset.borrowed_at = utcnow()
    asset.returned_at = None
    await write_audit(session, actor_id=user.id, action="dorm.asset.borrow", target_type="asset", target_id=asset.id)
    await session.commit()
    return await assets(session, user)


async def return_asset(session: AsyncSession, user: User, asset_id: int) -> dict:
    room, _ = await current_room(session, user)
    asset = await session.get(DormAsset, asset_id)
    if asset is None or asset.room_id != room.id:
        raise BizError(ErrCode.NOT_FOUND, "物品不存在")
    if asset.status != "borrowed":
        raise BizError(ErrCode.CONFLICT, "该物品未借出")
    if asset.holder_id != user.id and room.leader_id != user.id:
        raise BizError(ErrCode.FORBIDDEN, "仅借用人或寝室长可归还")
    asset.status = "available"
    asset.returned_at = utcnow()
    await write_audit(session, actor_id=user.id, action="dorm.asset.return", target_type="asset", target_id=asset.id)
    await session.commit()
    return await assets(session, user)


async def create_room_change(session: AsyncSession, user: User, payload) -> dict:
    room, _ = await current_room(session, user)
    req = RoomChangeRequest(
        room_id=room.id,
        student_id=user.id,
        req_type=payload.req_type,
        target_room=payload.target_room,
        reason=payload.reason,
    )
    session.add(req)
    await write_audit(session, actor_id=user.id, action="dorm.room_change.create", target_type="room", target_id=room.id)
    await session.commit()
    return {
        "id": req.id,
        "req_type": req.req_type,
        "status": req.status,
        "created_at": req.created_at,
        "message": "申请已提交，宿管中心将在 2 个工作日内处理",
    }


async def list_room_changes(session: AsyncSession, user: User) -> list[dict]:
    room, _ = await current_room(session, user)
    scope = select(RoomChangeRequest).where(RoomChangeRequest.room_id == room.id)
    if room.leader_id != user.id:
        scope = scope.where(RoomChangeRequest.student_id == user.id)
    rows = (await session.scalars(scope.order_by(RoomChangeRequest.created_at.desc()).limit(20))).all()
    label = {"checkin": "入住申请", "checkout": "退宿申请", "swap": "调宿申请"}
    return [
        {
            "id": r.id,
            "req_type": r.req_type,
            "type_label": label.get(r.req_type, r.req_type),
            "target_room": r.target_room,
            "reason": r.reason,
            "status": r.status,
            "status_label": {"pending": "待审批", "approved": "已通过", "rejected": "已驳回"}[r.status],
            "created_at": r.created_at,
        }
        for r in rows
    ]
