"""Việc chạy lúc server khởi động và tắt: tạo bảng, nạp dữ liệu nền, bật / tắt các job chạy nền."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from application.policies import ensure_seeded as seed_policies
from database.connection import close_db, init_db
from jobs.price_watcher import price_watcher_service
from jobs.warmup import run_startup_warmup
from services.catalog.category_resolver import category_resolver
from services.pricing.category_floors import category_floors
from shared.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động: CSDL, bảng quy đổi danh mục, ngưỡng giá theo ngành, chính sách mặc định
    await init_db()
    await category_resolver.load()
    await category_floors.refresh(force=True)
    await seed_policies()

    # Job nền: làm ấm kho, theo dõi giá định kỳ
    warmup_task = asyncio.create_task(run_startup_warmup())
    price_watcher_service.interval = max(60, settings.PRICE_WATCH_INTERVAL_MINUTES * 60)
    watcher_task = asyncio.create_task(price_watcher_service.start())

    yield

    # Tắt: dừng job nền, đóng kết nối CSDL
    price_watcher_service.stop()
    for task in (warmup_task, watcher_task):
        if not task.done():
            task.cancel()
    await close_db()
