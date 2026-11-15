"""认证服务：登录、注册绑定、刷新轮换、改密、短信验证码、设备管理。"""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.cache import cache
from app.core.errors import BizError, ErrCode
from app.core.ratelimit import bump_daily, ensure_cooldown, hit, set_cooldown
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    password_strength,
    sha256_hex,
    validate_password_strength,
    verify_password,
)
from app.core.timeutil import local_today, utcnow
from app.models import DormBed, DormRoom, LoginDevice, PasswordHistory, RefreshToken, User
from app.services.audit import write_audit
from app.services.notify_service import send_message


def mask_phone(phone: str | None) -> str:
    if not phone or len(phone) < 7:
        return phone or ""
    return phone[:3] + "****" + phone[-4:]


def mask_name(name: str) -> str:
    if not name:
        return ""
    return name[0] + "*" * (len(name) - 1)


async def _bed_and_room(session: AsyncSession, user_id: int):
    bed = await session.scalar(select(DormBed).where(DormBed.student_id == user_id, DormBed.status == 1))
    room = await session.get(DormRoom, bed.room_id) if bed else None
    return bed, room


async def serialize_user(session: AsyncSession, user: User) -> dict:
    bed, room = await _bed_and_room(session, user.id)
    return {
        "id": user.id,
        "name": user.name,
        "student_no": user.student_no,
        "role": user.role,
        "college": user.college,
        "class_name": user.class_name,
        "grade": user.grade,
        "avatar_url": user.avatar_url,
        "phone": mask_phone(user.phone),
        "worker_no": user.worker_no,
        "room": f"{room.building} {room.room_no}室" if room else None,
        "room_id": room.id if room else None,
        "bed_no": bed.bed_no if bed else None,
        "bed_position": bed.position if bed else None,
        "is_leader": bool(room and room.leader_id == user.id),
    }


async def student_check(session: AsyncSession, student_no: str) -> dict:
    if not student_no.isdigit() or not 8 <= len(student_no) <= 12:
        raise BizError(ErrCode.STUDENT_NOT_FOUND)
    user = await session.scalar(select(User).where(User.student_no == student_no))
    if user is None:
        raise BizError(ErrCode.STUDENT_NOT_FOUND)
    bed, room = await _bed_and_room(session, user.id)
    if bed is None or room is None:
        raise BizError(ErrCode.DORM_NOT_MATCHED)
    return {
        "student_no": student_no,
        "name_masked": mask_name(user.name),
        "room": f"{room.building} · {room.room_no} 室",
        "room_id": room.id,
        "bed_no": bed.bed_no,
        "bed_position": bed.position,
        "bed_position_label": "上铺" if bed.position == "upper" else "下铺",
        "registered": bool(user.password_hash),
        "matched": True,
    }


async def register(session: AsyncSession, payload, request: Request | None = None) -> dict:
    validate_password_strength(payload.password)
    user = await session.scalar(select(User).where(User.student_no == payload.student_no))
    if user is None:
        raise BizError(ErrCode.STUDENT_NOT_FOUND)
    if user.password_hash:
        raise BizError(ErrCode.STUDENT_EXISTS)
    if user.name != payload.name.strip():
        raise BizError(ErrCode.STUDENT_NOT_FOUND, "姓名与学籍信息不一致")
    if user.phone != payload.phone and user.phone:
        raise BizError(ErrCode.DORM_NOT_MATCHED, "手机号与预留号码不一致，请联系宿管")
    bed, room = await _bed_and_room(session, user.id)
    if bed is None:
        raise BizError(ErrCode.DORM_NOT_MATCHED)
    if bed.student_id != user.id:
        raise BizError(ErrCode.BED_OCCUPIED)

    user.password_hash = hash_password(payload.password)
    user.phone = payload.phone
    user.status = 1
    session.add(PasswordHistory(user_id=user.id, password_hash=user.password_hash))
    await write_audit(session, actor_id=user.id, action="auth.register", target_type="user", target_id=user.id, request=request)
    await send_message(
        session, user.id, "system", "欢迎使用宿舍服务平台",
        f"已为你绑定 {room.building} {room.room_no} 室 · 床位 {bed.bed_no}，可在「我的寝室」查看。",
        dedup=False,
    )
    await session.commit()
    return {
        "user_id": user.id,
        "room": f"{room.building} · {room.room_no} 室",
        "bed_no": bed.bed_no,
        "bed_position": bed.position,
        "bed_position_label": "上铺" if bed.position == "upper" else "下铺",
        "verified": True,
    }


async def _find_by_account(session: AsyncSession, account: str) -> User | None:
    stmt = select(User).where(
        (User.student_no == account) | (User.phone == account) | (User.worker_no == account) | (User.username == account)
    )
    return await session.scalar(stmt)


async def login(
    session: AsyncSession,
    payload,
    *,
    ip: str | None = None,
    ua: str | None = None,
    request: Request | None = None,
) -> dict:
    account = payload.account.strip()
    fail_key = f"login:fail:{account}"
    fails = await cache.get(fail_key) or 0
    if fails >= settings.login_max_fail:
        ttl = await cache.ttl(fail_key)
        raise BizError(ErrCode.ACCOUNT_LOCKED, data={"retry_after": max(ttl, 1)})

    user = await _find_by_account(session, account)
    # 统一错误提示，避免账号枚举；不存在的账号也走一次哈希，弱化时序差异
    if user is None or not user.password_hash:
        verify_password(payload.password, "$2b$12$" + "x" * 53)
        await cache.incr(fail_key, ttl=settings.login_lock_minutes * 60)
        await write_audit(session, actor_id=None, action="auth.login.fail", detail={"account": account}, request=request)
        await session.commit()
        raise BizError(ErrCode.BAD_CREDENTIALS)

    if not verify_password(payload.password, user.password_hash):
        await cache.incr(fail_key, ttl=settings.login_lock_minutes * 60)
        await write_audit(session, actor_id=user.id, action="auth.login.fail", target_type="user", target_id=user.id, request=request)
        await session.commit()
        raise BizError(ErrCode.BAD_CREDENTIALS)

    if user.status != 1:
        raise BizError(ErrCode.ACCOUNT_DISABLED)

    await cache.delete(fail_key)
    user.last_login_at = utcnow()
    device_id = payload.device_id or (ua or "web")[:64]
    device = await session.scalar(select(LoginDevice).where(LoginDevice.user_id == user.id, LoginDevice.device_id == device_id))
    if device is None:
        session.add(
            LoginDevice(
                user_id=user.id,
                device_id=device_id,
                device_name=payload.device_name or "Web 浏览器",
                ip=ip,
                user_agent=ua,
                last_active_at=utcnow(),
            )
        )
    else:
        device.last_active_at = utcnow()
        device.ip = ip
        device.revoked = 0

    access, _ = create_access_token(user.id, user.role)
    refresh, _, expires_at = create_refresh_token(user.id, user.role)
    session.add(RefreshToken(user_id=user.id, token_hash=sha256_hex(refresh), device_id=device_id, expires_at=expires_at))
    await write_audit(session, actor_id=user.id, action="auth.login", target_type="user", target_id=user.id, request=request)
    await session.commit()

    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "Bearer",
        "expires_in": settings.access_token_minutes * 60,
        "user": await serialize_user(session, user),
    }


async def revoke_all_refresh(session: AsyncSession, user_id: int) -> None:
    await session.execute(
        update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)).values(revoked_at=utcnow())
    )


async def refresh_session(session: AsyncSession, raw_refresh: str) -> dict:
    payload = decode_token(raw_refresh, expect="refresh")
    token_hash = sha256_hex(raw_refresh)
    row = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if row is None or row.revoked_at is not None or row.expires_at < utcnow():
        # 复用已轮换的 refresh → 判定盗用，吊销该用户全部 refresh
        await revoke_all_refresh(session, int(payload["sub"]))
        await session.commit()
        raise BizError(ErrCode.TOKEN_INVALID, "登录状态异常，请重新登录")

    user = await session.get(User, row.user_id)
    if user is None or user.status != 1:
        raise BizError(ErrCode.ACCOUNT_DISABLED)

    new_refresh, _, expires_at = create_refresh_token(user.id, user.role)
    row.revoked_at = utcnow()
    row.replaced_by = sha256_hex(new_refresh)
    session.add(
        RefreshToken(user_id=user.id, token_hash=sha256_hex(new_refresh), device_id=row.device_id, expires_at=expires_at)
    )
    access, _ = create_access_token(user.id, user.role)
    await session.commit()
    return {
        "access_token": access,
        "refresh_token": new_refresh,
        "token_type": "Bearer",
        "expires_in": settings.access_token_minutes * 60,
    }


async def logout(session: AsyncSession, user: User, access_token: str, refresh_token: str | None) -> None:
    try:
        payload = decode_token(access_token, expect="access")
        exp = payload.get("exp", 0)
        ttl = max(int(exp - datetime.now().timestamp()), 1)
        await cache.set(f"jwt:blacklist:{payload['jti']}", 1, ttl=ttl)
    except BizError:
        pass
    if refresh_token:
        row = await session.scalar(select(RefreshToken).where(RefreshToken.token_hash == sha256_hex(refresh_token)))
        if row is not None:
            row.revoked_at = utcnow()
    else:
        await revoke_all_refresh(session, user.id)
    await write_audit(session, actor_id=user.id, action="auth.logout", target_type="user", target_id=user.id)
    await session.commit()


async def send_sms_code(session: AsyncSession, phone: str, scene: str, ip: str | None) -> dict:
    await ensure_cooldown(f"sms:60:{phone}")
    await bump_daily(f"sms:day:{phone}", 5)
    if ip:
        await hit(f"sms:ip:{ip}", 20, window=3600, message="短信发送过于频繁，请稍后再试")

    # 真实网关在 sms_provider=aliyun 时接入；mock 环境把验证码写入缓存并在响应中回显
    from app.core.security import gen_nonce

    code = gen_nonce(6)
    await cache.set(f"sms:code:{scene}:{phone}", code, ttl=300)
    await set_cooldown(f"sms:60:{phone}", 60)
    result = {"phone": mask_phone(phone), "expires_in": 300, "retry_after": 60, "scene": scene}
    if settings.is_dev or settings.sms_provider == "mock":
        result["debug_code"] = code
    return result


async def _check_sms(phone: str, scene: str, code: str) -> None:
    saved = await cache.get(f"sms:code:{scene}:{phone}")
    if not saved or str(saved) != str(code):
        raise BizError(ErrCode.SMS_CODE_INVALID)


async def _check_password_reuse(session: AsyncSession, user_id: int, new_password: str) -> None:
    rows = (
        await session.scalars(
            select(PasswordHistory)
            .where(PasswordHistory.user_id == user_id)
            .order_by(PasswordHistory.created_at.desc())
            .limit(3)
        )
    ).all()
    if any(verify_password(new_password, r.password_hash) for r in rows):
        raise BizError(ErrCode.PASSWORD_REUSED)


async def reset_password(session: AsyncSession, payload, request: Request | None = None) -> None:
    validate_password_strength(payload.new_password)
    await _check_sms(payload.phone, "reset", payload.code)
    user = await session.scalar(select(User).where(User.phone == payload.phone))
    if user is None:
        raise BizError(ErrCode.STUDENT_NOT_FOUND, "手机号未绑定任何账号")
    await _check_password_reuse(session, user.id, payload.new_password)
    user.password_hash = hash_password(payload.new_password)
    session.add(PasswordHistory(user_id=user.id, password_hash=user.password_hash))
    await revoke_all_refresh(session, user.id)
    await cache.delete(f"sms:code:reset:{payload.phone}")
    await write_audit(session, actor_id=user.id, action="auth.password.reset", target_type="user", target_id=user.id, request=request)
    await session.commit()


async def change_password(session: AsyncSession, user: User, payload, request: Request | None = None) -> None:
    validate_password_strength(payload.new_password)
    if not verify_password(payload.old_password, user.password_hash):
        raise BizError(ErrCode.BAD_CREDENTIALS, "原密码不正确")
    if payload.old_password == payload.new_password:
        raise BizError(ErrCode.PASSWORD_REUSED, "新密码不能与原密码相同")
    await _check_password_reuse(session, user.id, payload.new_password)
    user.password_hash = hash_password(payload.new_password)
    session.add(PasswordHistory(user_id=user.id, password_hash=user.password_hash))
    await revoke_all_refresh(session, user.id)
    await write_audit(session, actor_id=user.id, action="auth.password.change", target_type="user", target_id=user.id, request=request)
    await session.commit()


async def rebind_phone(session: AsyncSession, user: User, payload) -> None:
    await _check_sms(user.phone, "bind", payload.old_code)
    await _check_sms(payload.new_phone, "bind", payload.new_code)
    exists = await session.scalar(select(User).where(User.phone == payload.new_phone, User.id != user.id))
    if exists:
        raise BizError(ErrCode.CONFLICT, "该手机号已被其他账号绑定")
    user.phone = payload.new_phone
    await write_audit(session, actor_id=user.id, action="auth.phone.rebind", target_type="user", target_id=user.id)
    await session.commit()


async def list_devices(session: AsyncSession, user: User, current_device_id: str | None) -> list[dict]:
    rows = (
        await session.scalars(select(LoginDevice).where(LoginDevice.user_id == user.id).order_by(LoginDevice.last_active_at.desc()))
    ).all()
    return [
        {
            "id": d.id,
            "device_id": d.device_id,
            "device_name": d.device_name,
            "ip": d.ip,
            "last_active_at": d.last_active_at,
            "revoked": bool(d.revoked),
            "current": d.device_id == current_device_id,
        }
        for d in rows
    ]


async def revoke_device(session: AsyncSession, user: User, device_row_id: int) -> None:
    device = await session.get(LoginDevice, device_row_id)
    if device is None or device.user_id != user.id:
        raise BizError(ErrCode.NOT_FOUND, "设备不存在")
    device.revoked = 1
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.device_id == device.device_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    await write_audit(session, actor_id=user.id, action="auth.device.revoke", target_type="device", target_id=device.id)
    await session.commit()


def today_str() -> str:
    return local_today().strftime("%Y-%m-%d")


def password_hint(password: str) -> str:
    return password_strength(password)


def refresh_expiry() -> datetime:
    return utcnow() + timedelta(days=settings.refresh_token_days)
