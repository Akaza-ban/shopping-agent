"""Quản lý cào dữ liệu hàng loạt: xem trạng thái kho, kích hoạt một đợt cào (chạy ngầm hoặc chờ kết quả).

Bản thân việc cào nằm ở jobs/batch_crawler.py.
"""

from collections.abc import Callable
from typing import Any

from jobs.batch_crawler import batch_crawler_service

ALREADY_RUNNING = {
    "status": "already_running",
    "message": "Crawler is currently running in background. Please check /api/v1/crawler/status.",
}


async def status() -> dict[str, Any]:
    return await batch_crawler_service.get_crawler_status()


async def trigger(
    limit_per_query: int, force_refresh: bool, background: bool, schedule: Callable[..., None]
) -> dict[str, Any]:
    """`background` = True: đưa đợt cào vào `schedule` (BackgroundTasks.add_task) và trả lời ngay."""
    if batch_crawler_service.is_running:
        return ALREADY_RUNNING
    if background:
        schedule(batch_crawler_service.run_batch_crawl, limit_per_query=limit_per_query, force_refresh=force_refresh)
        return {
            "status": "started",
            "message": "Batch crawl started in background. You can track progress via GET /api/v1/crawler/status.",
            "limit_per_query": limit_per_query,
        }
    return await batch_crawler_service.run_batch_crawl(limit_per_query=limit_per_query, force_refresh=force_refresh)
