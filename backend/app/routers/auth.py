"""认证接口。"""
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from app.deps import CurrentUser, SessionDep, client_meta
from app.core.response import ok
from app.schemas import ChangePasswordIn, LoginIn, LogoutIn, RebindPhoneIn, RefreshIn, RegisterIn, ResetPasswordIn, SmsCodeIn
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["认证"])


@router.get("/check-student", summary="学号预校验（返回脱敏住宿预览）")
async def check_student(student_no: str, session: SessionDep):
    return ok(await auth_service.student_check(session, student_no))


@router.post("/register", status_code=status.HTTP_201_CREATED, summary="注册并自动绑定床位")
async def register(payload: RegisterIn, session: SessionDep, request: Request):
    return ok(await auth_service.register(session, payload, request), "注册成功")


@router.post("/login", summary="登录（学号 / 工号 / 手机号 / 管理员账号）")
async def login(payload: LoginIn, session: SessionDep, request: Request):
    ip, ua = client_meta(request)
    return ok(await auth_service.login(session, payload, ip=ip, ua=ua, request=request))


@router.get("/wechat/qrcode", summary="微信扫码登录（P2，占位）")
async def wechat_qrcode():
    return ok({"enabled": False, "message": "即将开放"})


@router.post("/refresh", summary="刷新 access_token（refresh 轮换）")
async def refresh(payload: RefreshIn, session: SessionDep):
    return ok(await auth_service.refresh_session(session, payload.refresh_token))


@router.post("/logout", summary="退出登录（access 进黑名单 + 吊销 refresh）")
async def logout(payload: LogoutIn, user: CurrentUser, session: SessionDep, request: Request):
    auth_header = request.headers.get("authorization", "")
    access = auth_header[7:] if auth_header.lower().startswith("bearer ") else ""
    await auth_service.logout(session, user, access, payload.refresh_token)
    return ok({"logged_out": True})


@router.post("/sms-code", summary="发送短信验证码（60s / 5 次每日 / 20 次每 IP 每小时）")
async def sms_code(payload: SmsCodeIn, session: SessionDep, request: Request):
    ip, _ = client_meta(request)
    return ok(await auth_service.send_sms_code(session, payload.phone, payload.scene, ip))


@router.post("/reset-password", summary="短信验证码重置密码")
async def reset_password(payload: ResetPasswordIn, session: SessionDep, request: Request):
    await auth_service.reset_password(session, payload, request)
    return ok({"reset": True})


@router.post("/change-password", summary="登录态修改密码（吊销全部 refresh）")
async def change_password(payload: ChangePasswordIn, user: CurrentUser, session: SessionDep, request: Request):
    await auth_service.change_password(session, user, payload, request)
    return ok({"changed": True})


@router.post("/rebind-phone", summary="换绑手机（新旧手机双验证码）")
async def rebind_phone(payload: RebindPhoneIn, user: CurrentUser, session: SessionDep):
    await auth_service.rebind_phone(session, user, payload)
    return ok({"rebound": True})


@router.get("/devices", summary="登录设备列表")
async def devices(user: CurrentUser, session: SessionDep, request: Request):
    return ok(await auth_service.list_devices(session, user, request.headers.get("x-device-id")))


@router.delete("/devices/{device_id}", summary="下线指定设备")
async def delete_device(device_id: int, user: CurrentUser, session: SessionDep):
    await auth_service.revoke_device(session, user, device_id)
    return ok({"revoked": True})


@router.post("/password-strength", summary="密码强度（调试用，与前端同规则）")
async def password_strength(password: str):
    return ok({"strength": auth_service.password_strength(password)})
