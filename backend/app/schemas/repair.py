"""请求模型：报修域。"""
from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CATEGORY = Literal["water", "door", "furniture", "network", "ac", "public"]


class RepairOrderIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    category: CATEGORY
    location_type: Literal["in_room", "public"] = "in_room"
    location_desc: str = Field(min_length=4, max_length=100)
    description: str = Field(min_length=10, max_length=500)
    media_urls: list[str] = Field(default_factory=list, max_length=6)
    preferred_date: date | None = None
    preferred_slot: str | None = Field(default=None, max_length=10)
    require_presence: bool = True
    contact_phone: str = Field(pattern=r"^1[3-9]\d{9}$")
    client_request_id: str | None = Field(default=None, max_length=64)


class RepairOrderPatch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    description: str | None = Field(default=None, min_length=10, max_length=500)
    preferred_date: date | None = None
    preferred_slot: str | None = Field(default=None, max_length=10)
    contact_phone: str | None = Field(default=None, pattern=r"^1[3-9]\d{9}$")
    require_presence: bool | None = None


class CancelIn(BaseModel):
    reason: str | None = Field(default=None, max_length=200)


class VerifyIn(BaseModel):
    resolved: bool
    reason: str | None = Field(default=None, max_length=100)


class RateIn(BaseModel):
    speed: int = Field(ge=1, le=5)
    attitude: int = Field(ge=1, le=5)
    quality: int = Field(ge=1, le=5)
    content: str | None = Field(default=None, max_length=40)
    is_anonymous: bool = False


class OrderMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class AssignIn(BaseModel):
    worker_id: int = Field(gt=0)
    expect_finish_at: str | None = None


class FinishIn(BaseModel):
    note: str = Field(min_length=5, max_length=500)
    material_fee: float = Field(default=0, ge=0, le=9999)
