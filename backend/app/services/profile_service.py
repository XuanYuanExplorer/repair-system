"""个人中心服务：资料读取、受限字段更新、安全项统计。"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BizError, ErrCode
from app.models import DormBed, DormRoom, LoginDevice, User
from app.services.audit import write_audit
from app.services.auth_service import mask_name, mask_phone

IMMUTABLE_FIELDS = {"student_no", "name", "room_id", "bed_no", "role", "password_hash"}


async def profile(session: AsyncSession, user: User) -> dict:
    bed = await session.scalar(select(DormBed).where(DormBed.student_id == user.id, DormBed.status == 1))
    room = await session.get(DormRoom, bed.room_id) if bed else None
    device_count = int(
        await session.scalar(
            select(func.count()).select_from(LoginDevice).where(LoginDevice.user_id == user.id, LoginDevice.revoked == 0)
        )
        or 0
    )
    return {
        "id": user.id,
        "name": user.name,
        "student_no": user.student_no,
        "worker_no": user.worker_no,
        "role": user.role,
        "avatar_url": user.avatar_url,
        "gender": user.gender,
        "college": user.college,
        "class_name": user.class_name,
        "grade": user.grade,
        "email": user.email,
        "phone": mask_phone(user.phone),
        "emergency_name": user.emergency_name,
        "emergency_phone": mask_phone(user.emergency_phone),
        "verified": {
            "student_no": user.student_no,
            "college_class": f"{user.college or '—'} · {user.class_name or '—'} 班",
            "dorm": f"{room.building} {room.room_no} 室 · 床位 {bed.bed_no}" if room and bed else "—",
            "readonly": True,
        },
        "security": {
            "device_count": device_count,
            "phone": mask_phone(user.phone),
            "emergency_text": f"{user.emergency_name or '未设置'} · {mask_phone(user.emergency_phone) or '—'}",
        },
        "subtitle": f"{user.college or ''} {user.grade or ''} 级 · {room.building + ' ' + room.room_no + ' 室' if room else '未绑定寝室'}",
        "version": "DORM SERVICE V1.0",
    }


async def update_profile(session: AsyncSession, user: User, payload: dict) -> dict:
    forbidden = IMMUTABLE_FIELDS & set(payload.keys())
    if forbidden:
        raise BizError(ErrCode.FORBIDDEN, "学号、姓名、宿舍等信息不可自行修改")
    if payload.get("emergency_phone"):
        phone = payload["emergency_phone"]
        if not (phone.isdigit() and len(phone) == 11 and phone[0] == "1"):
            raise BizError(ErrCode.NOT_VERIFIED, "紧急联系人手机号格式不正确")
    allowed = {"avatar_url", "gender", "emergency_name", "emergency_phone", "email"}
    for key in allowed & set(payload.keys()):
        setattr(user, key, payload[key])
    await write_audit(session, actor_id=user.id, action="profile.update", target_type="user", target_id=user.id, detail={"fields": sorted(allowed & set(payload.keys()))})
    await session.commit()
    return await profile(session, user)


async def devices(session: AsyncSession, user: User) -> list[dict]:
    rows = (
        await session.scalars(select(LoginDevice).where(LoginDevice.user_id == user.id).order_by(LoginDevice.last_active_at.desc()))
    ).all()
    return [
        {
            "id": d.id,
            "device_name": d.device_name or "未知设备",
            "ip": d.ip,
            "last_active_at": d.last_active_at.isoformat(),
            "revoked": bool(d.revoked),
        }
        for d in rows
    ]


def display_name(user: User, anonymous: bool) -> str:
    return "匿名同学" if anonymous else user.name


def masked(name: str) -> str:
    return mask_name(name)
