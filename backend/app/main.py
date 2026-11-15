"""应用装配：生命周期、中间件、异常处理、路由、静态资源（单端口托管前端）。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.cache import cache
from app.core.errors import BizError, ErrCode
from app.core.response import fail
from app.core.tracing import TraceIdMiddleware
from app.db import SessionLocal, create_all, engine
from app.routers import admin, auth, dorm, duty, feedback, files, home, message, notice, payment, profile, repair
from app.tasks import scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("dorm.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    if settings.auto_init:
        await create_all()
        from app.seed_data import seed

        async with SessionLocal() as session:
            await seed(session)
        logger.info("database ready (auto_init=%s)", settings.auto_init)
    if settings.enable_scheduler:
        scheduler.start()
    try:
        yield
    finally:
        await scheduler.stop()
        await engine.dispose()
        await cache.close()


app = FastAPI(
    title="学生宿舍服务平台 API",
    version="1.1.0",
    description="报修 / 缴费 / 寝室 / 值日 / 公告 / 消息 / 反馈 / 帮助 —— 统一响应包 {code,message,data,trace_id}",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=f"{settings.api_prefix}/openapi.json",
)

# 自定义 Docs / ReDoc：使用国内可访问的 CDN（默认 jsdelivr 不可达导致页面空白）
_SWAGGER_JS = "https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.17.14/swagger-ui-bundle.min.js"
_SWAGGER_CSS = "https://cdn.bootcdn.net/ajax/libs/swagger-ui/5.17.14/swagger-ui.min.css"
_REDOC_JS = "https://cdn.redoc.ly/redoc/v2.1.5/bundles/redoc.standalone.js"


@app.get(f"{settings.api_prefix}/docs", include_in_schema=False)
async def swagger_ui():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url=_SWAGGER_JS,
        swagger_css_url=_SWAGGER_CSS,
    )


@app.get(f"{settings.api_prefix}/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url=_REDOC_JS,
        with_google_fonts=False,
    )

app.add_middleware(TraceIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Trace-Id", "Content-Disposition"],
)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    # 只对 API 限流：静态资源与 SPA 页面（HTML）不占用业务配额，否则正常浏览会误伤
    if not path.startswith(settings.api_prefix) or path.endswith(("/healthz", "/readyz")):
        return await call_next(request)
    client = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
        request.client.host if request.client else "unknown"
    )
    count = await cache.incr(f"rate:global:{client}", ttl=60)
    if count > settings.rate_limit_per_minute:
        return JSONResponse(
            status_code=429,
            content=fail(ErrCode.RATE_LIMITED, "请求过于频繁，请稍后再试"),
            headers={"Retry-After": "60"},
        )
    return await call_next(request)


@app.exception_handler(BizError)
async def biz_error_handler(request: Request, exc: BizError):
    return JSONResponse(status_code=exc.http_status, content=fail(exc.code, exc.message, exc.data))


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    loc = ".".join(str(x) for x in first.get("loc", []) if x not in ("body", "query", "path"))
    message = f"{loc}：{first.get('msg', '参数不合法')}" if loc else "参数不合法"
    return JSONResponse(status_code=422, content=fail(422, message, {"errors": exc.errors()[:5]}))


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return JSONResponse(status_code=404, content=fail(ErrCode.NOT_FOUND, "接口或资源不存在"))
    return JSONResponse(status_code=exc.status_code, content=fail(exc.status_code, str(exc.detail)))


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    logger.exception("unhandled_error path=%s", request.url.path)
    return JSONResponse(status_code=500, content=fail(ErrCode.INTERNAL, "服务器内部错误，请稍后重试"))


for router in (
    auth.router,
    home.router,
    repair.router,
    payment.router,
    dorm.router,
    duty.router,
    notice.router,
    message.router,
    profile.router,
    feedback.router,
    admin.router,
    files.router,
):
    app.include_router(router, prefix=settings.api_prefix)

# ---- 静态资源：上传目录 + 前端构建产物（单端口运行）----
upload_dir = Path(settings.upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

dist_dir = Path(settings.frontend_dist)
if dist_dir.exists():
    if (dist_dir / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(dist_dir / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        if full_path.startswith(("api/", "uploads/")):
            return JSONResponse(status_code=404, content=fail(ErrCode.NOT_FOUND, "接口不存在"))
        candidate = dist_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(dist_dir / "index.html")
else:

    @app.get("/", include_in_schema=False)
    async def dev_root():
        return {
            "message": "前端尚未构建（frontend/dist 不存在）。开发模式请运行 cd frontend && pnpm dev",
            "docs": f"{settings.api_prefix}/docs",
        }
