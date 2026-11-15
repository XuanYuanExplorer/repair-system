"""请求模型：认证与账号安全。"""
from pydantic import BaseModel, ConfigDict, Field


class LoginIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    account: str = Field(min_length=2, max_length=64, description="学号 / 工号 / 管理员账号 / 手机号")
    password: str = Field(min_length=6, max_length=64)
    remember: bool = True
    device_id: str | None = Field(default=None, max_length=64)
    device_name: str | None = Field(default=None, max_length=100)


class RegisterIn(BaseModel):
    student_no: str = Field(pattern=r"^\d{8,12}$", description="8–12 位学号")
    name: str = Field(min_length=2, max_length=20)
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    password: str = Field(min_length=6, max_length=64)
    sms_code: str | None = Field(default=None, max_length=6)


class SmsCodeIn(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    scene: str = Field(default="reset", pattern="^(reset|bind|register)$")


class ResetPasswordIn(BaseModel):
    phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    code: str = Field(min_length=4, max_length=6)
    new_password: str = Field(min_length=6, max_length=64)


class ChangePasswordIn(BaseModel):
    old_password: str = Field(min_length=6, max_length=64)
    new_password: str = Field(min_length=6, max_length=64)


class RebindPhoneIn(BaseModel):
    new_phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    old_code: str = Field(min_length=4, max_length=6)
    new_code: str = Field(min_length=4, max_length=6)


class RefreshIn(BaseModel):
    refresh_token: str = Field(min_length=20)


class LogoutIn(BaseModel):
    refresh_token: str | None = None


class StudentCheckOut(BaseModel):
    student_no: str
    name_masked: str
    room: str
    bed_no: int
    bed_position: str
    matched: bool = True
