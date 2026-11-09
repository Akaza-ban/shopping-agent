import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any

from core.tools.ecom_search import EcomSearchTool
from database.repositories import product_repository
from shared.exceptions import DatabaseError

logger = logging.getLogger("batch_crawler")

# Danh mục từ khóa HOT mặc định được quan tâm nhiều nhất
DEFAULT_HOT_CATALOG = [
    {"query": "iphone", "platform": "tgdd", "category": "phones", "categoryName": "Điện thoại & Tablet"},
    {"query": "samsung galaxy", "platform": "tgdd", "category": "phones", "categoryName": "Điện thoại & Tablet"},
    {"query": "macbook", "platform": "tgdd", "category": "laptops", "categoryName": "Laptop & Máy tính"},
    {"query": "laptop gaming", "platform": "tgdd", "category": "laptops", "categoryName": "Laptop & Máy tính"},
    {"query": "tu lanh toshiba", "platform": "dmx", "category": "home_appliances", "categoryName": "Đồ gia dụng"},
    {"query": "may giat", "platform": "dmx", "category": "home_appliances", "categoryName": "Đồ gia dụng"},
    {"query": "noi chien khong dau", "platform": "dmx", "category": "home_appliances", "categoryName": "Đồ gia dụng"},
    {"query": "tai nghe bluetooth", "platform": "tiki", "category": "audio", "categoryName": "Thiết bị âm thanh"},
    {"query": "iphone", "platform": "fpt-shop", "category": "phones", "categoryName": "Điện thoại & Tablet"},
    {"query": "laptop", "platform": "fpt-shop", "category": "laptops", "categoryName": "Laptop & Máy tính"},
    {"query": "samsung galaxy", "platform": "cellphones", "category": "phones", "categoryName": "Điện thoại & Tablet"},
    {"query": "tai nghe", "platform": "cellphones", "category": "audio", "categoryName": "Thiết bị âm thanh"},
]


class BatchCrawlerService:
    def __init__(self, search_tool: EcomSearchTool | None = None):
        self.search_tool = search_tool or EcomSearchTool()
        self.is_running = False
        self.last_run_time: datetime | None = None
        self.last_run_stats: dict[str, Any] = {}

    async def should_warmup(self, max_stale_hours: int = 12) -> bool:
        """Cần cào lại khi kho trống hoặc lần cập nhật gần nhất đã quá max_stale_hours (lỗi CSDL cũng cào)."""
        try:
            total_products, latest_update = await product_repository.catalog_snapshot()
        except DatabaseError as e:
            logger.warning(f"Lỗi kiểm tra trạng thái warm-up: {e}")
            return True
        if total_products == 0 or not latest_update:
            return True
        return latest_update < datetime.utcnow() - timedelta(hours=max_stale_hours)

    async def run_batch_crawl(
        self, catalog: list[dict[str, str]] | None = None, limit_per_query: int = 4, force_refresh: bool = True
    ) -> dict[str, Any]:
        if self.is_running:
            logger.warning("Một đợt cào dữ liệu đang diễn ra, vui lòng chờ...")
            return {"status": "already_running", "message": "Crawler is currently running"}

        self.is_running = True
        target_catalog = catalog or DEFAULT_HOT_CATALOG
        start_time = time.perf_counter()
        logger.info(f"[BatchCrawler] Bắt đầu thu thập tự động cho {len(target_catalog)} danh mục HOT...")
        crawled_summary = []
        try:
            for idx, target in enumerate(target_catalog, 1):
                logger.info(
                    f"  [{idx}/{len(target_catalog)}] Đang quét '{target['query']}' "
                    f"({target.get('platform', 'all').upper()})..."
                )
                summary = await self._crawl_one(target, limit_per_query, force_refresh)
                if summary:
                    crawled_summary.append(summary)
                if idx < len(target_catalog):
                    await asyncio.sleep(1.5)
        finally:
            self.is_running = False
        return self._record_run(len(target_catalog), crawled_summary, time.perf_counter() - start_time)

    async def _crawl_one(self, target: dict[str, str], limit: int, force_refresh: bool) -> dict[str, Any] | None:
        """Cào thật một từ khóa (EcomSearchTool tự nạp vào CSDL và ghi lịch sử giá); lỗi thì bỏ qua từ khóa đó."""
        query, platform = target["query"], target.get("platform", "all")
        try:
            results = await self.search_tool.run(
                query=query,
                category=target.get("category", "all"),
                platform=platform,
                limit=limit,
                force_refresh=force_refresh,
            )
        except Exception:  # chốt chặn: một từ khóa lỗi không được dừng cả đợt cào
            logger.exception(f"  Lỗi khi quét '{query}'")
            return None
        return {"query": query, "platform": platform, "count": len(results)}

    def _record_run(self, queries_count: int, crawled_summary: list[dict[str, Any]], duration: float) -> dict[str, Any]:
        total_items_saved = sum(item["count"] for item in crawled_summary)
        self.last_run_time = datetime.utcnow()
        self.last_run_stats = {
            "status": "completed",
            "queriesCount": queries_count,
            "totalProducts": total_items_saved,
            "durationSeconds": round(duration, 2),
            "timestamp": self.last_run_time.isoformat(),
            "details": crawled_summary,
        }
        logger.info(
            f"[BatchCrawler] Hoàn tất đợt thu thập: {total_items_saved} sản phẩm được nạp vào CSDL "
            f"trong {duration:.1f}s."
        )
        return self.last_run_stats

    async def get_crawler_status(self) -> dict[str, Any]:
        """Lấy thông tin tổng quan về trạng thái kho CSDL và crawler."""
        try:
            total_products, latest_update = await product_repository.catalog_snapshot()
        except DatabaseError as e:
            logger.warning(f"Lỗi đọc trạng thái kho: {e}")
            total_products, latest_update = 0, None
        return {
            "isRunning": self.is_running,
            "totalProductsInDb": total_products,
            "latestDataUpdate": latest_update.isoformat() if latest_update else None,
            "lastRunTime": self.last_run_time.isoformat() if self.last_run_time else None,
            "lastRunStats": self.last_run_stats,
            "hotCatalogCount": len(DEFAULT_HOT_CATALOG),
        }


batch_crawler_service = BatchCrawlerService()
