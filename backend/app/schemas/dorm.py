"""请求模型：寝室、值日、公告、消息、个人、反馈。"""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RulesIn(BaseModel):
    items: list[str] = Field(min_length=1, max_length=8)

    @field_validator("items")
    @classmethod
    def _check_items(cls, v: list[str]) -> list[str]:
        cleaned = [i.strip() for i in v if i and i.strip()]
        if not cleaned:
            raise ValueError("公约内容不能为空")
        if any(len(i) > 200 for i in cleaned):
            raise ValueError("单条公约不超过 200 字")
        return cleaned


class RoomChangeIn(BaseModel):
    req_type: Literal["checkin", "checkout", "swap"]
    target_room: str | None = Field(default=None, max_length=20)
    reason: str | None = Field(default=None, max_length=300)


class DutyRuleIn(BaseModel):
    mode: Literal["daily", "weekly"] = "daily"
    member_order: list[int] = Field(default_factory=list, max_length=10)
    areas: list[str] = Field(default_factory=lambda: ["地面", "桌面", "阳台", "卫浴"], max_length=10)


class ScheduleGenerateIn(BaseModel):
    week_start: date | None = None


class ScheduleUpdateIn(BaseModel):
    user_id: int | None = None
    areas: list[str] | None = None


class RectifyIn(BaseModel):
    media_urls: list[str] = Field(min_length=1, max_length=4)


class NoticeIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    scope: Literal["all", "building", "room"] = "all"
    building: str | None = Field(default=None, max_length=20)
    room_id: int | None = None
    type: Literal["notice", "check", "utility", "safety"] = "notice"
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=2, max_length=5000)
    is_pinned: bool = False
    require_receipt: bool = False
    expire_at: str | None = None


class PreferenceIn(BaseModel):
    sms_types: list[str] = Field(default_factory=list)
    wechat_types: list[str] = Field(default_factory=list)


class ProfileUpdateIn(BaseModel):
    avatar_url: str | None = Field(default=None, max_length=255)
    gender: int | None = Field(default=None, ge=0, le=2)
    emergency_name: str | None = Field(default=None, max_length=50)
    emergency_phone: str | None = Field(default=None, pattern=r"^1[3-9]\d{9}$")
    email: str | None = Field(default=None, max_length=100)


class FeedbackIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    type: Literal["attitude", "quality", "charge", "suggestion"]
    order_id: int | None = None
    content: str = Field(min_length=10, max_length=300)
    media_urls: list[str] = Field(default_factory=list, max_length=4)


class SatisfactionIn(BaseModel):
    score: int = Field(ge=1, le=5)


class FeedbackReplyIn(BaseModel):
    content: str = Field(min_length=2, max_length=500)
