import asyncio
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field
from services.batch_crawler import batch_crawler_service

router = APIRouter(prefix="/crawler", tags=["Crawler Management"])

class TriggerCrawlRequest(BaseModel):
    limit_per_query: int = Field(default=3, ge=1, le=10, description="Số sản phẩm lấy tối đa cho mỗi từ khóa")
    force_refresh: bool = Field(default=True, description="Bỏ qua cache, cào dữ liệu mới nhất")
    background: bool = Field(default=True, description="Chạy ngầm không làm đơ Swagger/API")

@router.get("/status", summary="Xem trạng thái hoạt động của Crawler và CSDL")
async def get_crawler_status():
    """
    Trả về thông tin tổng quan:
    - isRunning: Đang có tiến trình cào ngầm nào chạy không
    - totalProductsInDb: Tổng số lượng sản phẩm trong kho SQLite
    - latestDataUpdate: Thời điểm bản ghi mới nhất được cập nhật
    - lastRunTime: Lần cào gần nhất
    - lastRunStats: Kết quả chi tiết lần cào trước
    """
    return await batch_crawler_service.get_crawler_status()

@router.post("/trigger", summary="Kích hoạt thu thập dữ liệu hàng loạt")
async def trigger_crawl(
    background_tasks: BackgroundTasks,
    payload: Optional[TriggerCrawlRequest] = None
):
    """
    Chủ động kích hoạt đợt cào dữ liệu cho danh mục HOT.
    Mặc định chạy ngầm (background=True) để người dùng có thể theo dõi qua GET /crawler/status.
    """
    req = payload or TriggerCrawlRequest()
    if batch_crawler_service.is_running:
        return {
            "status": "already_running",
            "message": "Crawler is currently running in background. Please check /api/v1/crawler/status."
        }

    if req.background:
        background_tasks.add_task(
            batch_crawler_service.run_batch_crawl,
            limit_per_query=req.limit_per_query,
            force_refresh=req.force_refresh
        )
        return {
            "status": "started",
            "message": "Batch crawl started in background. You can track progress via GET /api/v1/crawler/status.",
            "limit_per_query": req.limit_per_query
        }
    else:
        # Chạy đồng bộ (đợi kết quả trả về)
        stats = await batch_crawler_service.run_batch_crawl(
            limit_per_query=req.limit_per_query,
            force_refresh=req.force_refresh
        )
        return stats

