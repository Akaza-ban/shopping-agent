"""API quản lý crawler. Logic nằm ở application/crawler.py."""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends

import application.crawler as crawler
from database.models import UserModel
from src.dependencies.auth import require_admin, require_user
from src.schemas.crawler import TriggerCrawlRequest

router = APIRouter(prefix="/crawler", tags=["Crawler Management"])


@router.get("/status", summary="Xem trạng thái hoạt động của Crawler và CSDL")
async def get_crawler_status(user: UserModel = Depends(require_user)):
    return await crawler.status()


@router.post("/trigger", summary="Kích hoạt thu thập dữ liệu hàng loạt")
async def trigger_crawl(background_tasks: BackgroundTasks, payload: Optional[TriggerCrawlRequest] = None,
                        user: UserModel = Depends(require_admin)):
    """Chủ động kích hoạt đợt cào dữ liệu cho danh mục HOT."""
    req = payload or TriggerCrawlRequest()
    return await crawler.trigger(req.limit_per_query, req.force_refresh, req.background,
                                 schedule=background_tasks.add_task)
