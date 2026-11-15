"""测试基础设施：独立 SQLite 库 + ASGITransport，用例之间共享已灌种子的库。

运行：`cd backend && pytest`
"""
import os
import tempfile
from pathlib import Path

TMP_DIR = Path(tempfile.mkdtemp(prefix="dorm-test-"))
os.environ.setdefault("ENV", "dev")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TMP_DIR / 'test.db'}"
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["AUTO_INIT"] = "true"
os.environ["UPLOAD_DIR"] = str(TMP_DIR / "uploads")
os.environ["RATE_LIMIT_PER_MINUTE"] = "100000"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db import SessionLocal, create_all
from app.main import app
from app.seed_data import seed


@pytest_asyncio.fixture(scope="session")
async def client():
    await create_all()
    async with SessionLocal() as session:
        await seed(session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def student(client):
    r = await client.post("/api/v1/auth/login", json={"account": "20223601", "password": "Abc123456"})
    assert r.json()["code"] == 0
    data = r.json()["data"]
    return {"Authorization": f"Bearer {data['access_token']}"}, data


@pytest_asyncio.fixture
async def leader(client):
    r = await client.post("/api/v1/auth/login", json={"account": "20223602", "password": "Abc123456"})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


@pytest_asyncio.fixture
async def admin(client):
    r = await client.post("/api/v1/auth/login", json={"account": "admin", "password": "Admin@123"})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


@pytest_asyncio.fixture
async def worker(client):
    r = await client.post("/api/v1/auth/login", json={"account": "WX0087", "password": "Abc123456"})
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


@pytest.fixture
def auth():
    return lambda token: {"Authorization": f"Bearer {token}"}


def pytest_sessionfinish(session, exitstatus):
    import shutil

    shutil.rmtree(TMP_DIR, ignore_errors=True)
