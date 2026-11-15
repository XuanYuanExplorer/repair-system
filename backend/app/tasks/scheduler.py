"""进程内异步调度器。

生产可替换为 ARQ / Celery + Redis（同一 jobs 实现，仅调度方式不同）；
默认单进程 asyncio 循环，零外部依赖，便于本地与演示环境一键运行。
"""
from __future__ import annotations

import asyncio
import logging

from app.tasks import jobs

logger = logging.getLogger("dorm.scheduler")
_task: asyncio.Task | None = None
_stop = asyncio.Event()


async def _loop(interval: int = 30) -> None:
    await asyncio.sleep(2)
    while not _stop.is_set():
        try:
            await jobs.tick()
        except Exception as exc:  # noqa: BLE001
            logger.warning("scheduler_tick_failed: %s", exc)
        try:
            await asyncio.wait_for(_stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue


def start(interval: int = 30) -> None:
    global _task
    _stop.clear()
    _task = asyncio.create_task(_loop(interval))
    logger.info("scheduler_started interval=%ss", interval)


async def stop() -> None:
    global _task
    _stop.set()
    if _task:
        _task.cancel()
        try:
            await _task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        _task = None
