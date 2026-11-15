"""统一响应包与分页。"""
from typing import Any

from app.core.tracing import current_trace_id


def ok(data: Any = None, message: str = "ok") -> dict:
    return {"code": 0, "message": message, "data": data, "trace_id": current_trace_id()}


def page(items: list, total: int, page_no: int, page_size: int) -> dict:
    return {
        "items": items,
        "total": total,
        "page": page_no,
        "page_size": page_size,
        "has_more": page_no * page_size < total,
    }


def fail(code: int, message: str, data: Any = None) -> dict:
    return {"code": code, "message": message, "data": data, "trace_id": current_trace_id()}
