"""种子数据脚本：可重复执行（库非空则跳过）。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import SessionLocal, create_all  # noqa: E402
from app.seed_data import seed  # noqa: E402


async def main() -> None:
    await create_all()
    async with SessionLocal() as session:
        await seed(session)
    print("种子数据已就绪：学生 20223601 / 维修工 WX0087（Abc123456），管理员 admin / Admin@123")


if __name__ == "__main__":
    asyncio.run(main())
