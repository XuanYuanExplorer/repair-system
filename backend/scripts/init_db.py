"""建表脚本（生产走 Alembic 时使用 `alembic upgrade head`）。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import create_all  # noqa: E402


if __name__ == "__main__":
    asyncio.run(create_all())
    print("数据库表已创建")
