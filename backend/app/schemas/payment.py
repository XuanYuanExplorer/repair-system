"""请求模型：账单与支付。"""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PaymentCreateIn(BaseModel):
    bill_ids: list[int] = Field(min_length=1, max_length=20)
    channel: Literal["wechat", "alipay", "campus_card"] = "wechat"

    @field_validator("bill_ids")
    @classmethod
    def _dedup(cls, v: list[int]) -> list[int]:
        seen, out = set(), []
        for i in v:
            if i not in seen:
                seen.add(i)
                out.append(i)
        return out


class ReceiptApplyIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str | None = Field(default=None, max_length=100)
    title: str = Field(default="个人", max_length=100)


class BillGenerateIn(BaseModel):
    type: Literal["electricity", "accommodation", "water", "penalty"]
    period: str = Field(min_length=3, max_length=20)
    title: str = Field(min_length=2, max_length=100)
    amount: Decimal = Field(gt=0, le=Decimal("100000"))
    due_date: str
    student_ids: list[int] | None = None
    room_ids: list[int] | None = None
