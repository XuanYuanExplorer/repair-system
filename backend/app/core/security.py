"""密码哈希、JWT 签发/校验、密码强度规则。"""
import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.config import settings
from app.core.errors import BizError, ErrCode


# ---------------------------------------------------------------- 密码
def _prepare(password: str) -> bytes:
    """先 sha256 再 base64，规避 bcrypt 72 字节截断（对中文/长密码安全）。"""
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt(rounds=settings.password_bcrypt_rounds)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(password), hashed.encode())
    except (ValueError, TypeError):
        return False


def password_strength(password: str) -> str:
    """与前端 calcStrength 完全一致：weak / medium / strong。"""
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    if len(password) < 6 or not (has_letter and has_digit):
        return "weak"
    if len(password) >= 8 and has_symbol:
        return "strong"
    return "medium"


def validate_password_strength(password: str) -> None:
    if password_strength(password) == "weak":
        raise BizError(ErrCode.WEAK_PASSWORD)


# ---------------------------------------------------------------- JWT
def _encode(payload: dict, minutes: int | None = None, days: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    delta = timedelta(minutes=minutes) if minutes else timedelta(days=days or 0)
    payload = {**payload, "iat": int(now.timestamp()), "exp": int((now + delta).timestamp())}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_alg)


def create_access_token(user_id: int, role: str) -> tuple[str, str]:
    jti = uuid.uuid4().hex
    token = _encode(
        {"sub": str(user_id), "role": role, "jti": jti, "type": "access"},
        minutes=settings.access_token_minutes,
    )
    return token, jti


def create_refresh_token(user_id: int, role: str) -> tuple[str, str, datetime]:
    jti = uuid.uuid4().hex
    token = _encode(
        {"sub": str(user_id), "role": role, "jti": jti, "type": "refresh"},
        days=settings.refresh_token_days,
    )
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=settings.refresh_token_days)
    return token, jti, expires_at


def decode_token(token: str, expect: str = "access") -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
    except jwt.ExpiredSignatureError as exc:
        raise BizError(ErrCode.TOKEN_INVALID, "登录已过期，请重新登录") from exc
    except jwt.PyJWTError as exc:
        raise BizError(ErrCode.UNAUTHORIZED) from exc
    if payload.get("type") != expect:
        raise BizError(ErrCode.UNAUTHORIZED)
    return payload


def sha256_hex(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def gen_nonce(n: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(n))
