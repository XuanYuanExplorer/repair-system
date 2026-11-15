"""trace_id 中间件：每条请求一个 trace，贯穿日志与响应体。"""
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


def current_trace_id() -> str:
    return _trace_id.get() or "-"


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tid = request.headers.get("X-Trace-Id") or uuid.uuid4().hex[:12]
        token = _trace_id.set(tid)
        request.state.trace_id = tid
        try:
            response = await call_next(request)
        finally:
            _trace_id.reset(token)
        response.headers["X-Trace-Id"] = tid
        return response
