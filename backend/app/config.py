"""应用配置：全部通过环境变量注入，禁止在代码里硬编码密钥。"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # ---- 基础 ----
    env: str = "dev"
    debug: bool = False
    api_prefix: str = "/api/v1"
    timezone: str = "Asia/Shanghai"
    app_name: str = "学生宿舍服务平台"

    # ---- 数据库 ----
    # 默认 SQLite（零外置依赖，开箱即跑）；生产切 MySQL：
    # mysql+asyncmy://user:pwd@host:3306/dorm?charset=utf8mb4
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR}/data/dorm.db"
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_echo: bool = False

    # ---- 缓存（默认进程内 TTL 实现，生产可换 Redis）----
    redis_url: str = ""
    cache_prefix: str = "dorm"

    # ---- 认证 ----
    jwt_secret: str = "dev-only-change-me-32bytes-secret-key"
    jwt_alg: str = "HS256"
    access_token_minutes: int = 120
    refresh_token_days: int = 7
    login_max_fail: int = 5
    login_lock_minutes: int = 15
    password_bcrypt_rounds: int = 12

    # ---- 上传 ----
    upload_dir: str = str(BASE_DIR / "data" / "uploads")
    upload_base_url: str = "/uploads"
    max_image_mb: int = 5
    max_video_mb: int = 20
    max_media_count: int = 6

    # ---- 外部网关 ----
    sms_provider: str = "mock"          # mock | aliyun
    pay_provider: str = "mock"          # mock | wechat | campus
    pay_expire_minutes: int = 15

    # ---- CORS / 限流 ----
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])
    rate_limit_per_minute: int = 120
    enable_scheduler: bool = True
    auto_init: bool = True          # 启动时建表 + 空库自动灌种子（生产设 false，走迁移与运维脚本）

    # ---- 静态资源（前端构建产物）----
    frontend_dist: str = str(BASE_DIR.parent / "frontend" / "dist")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
