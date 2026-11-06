import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy import select, func
from database.connection import async_session
from database.models import ProductModel, SearchCacheModel
from core.tools.ecom_search import EcomSearchTool

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
    {"query": "tai nghe bluetooth", "platform": "tiki", "category": "audio", "categoryName": "Thiết bị âm thanh"}
]

class BatchCrawlerService:
    """
    Dịch vụ thu thập dữ liệu hàng loạt cho các mặt hàng HOT:
    - Hỗ trợ chạy thủ công qua CLI (make crawl).
    - Hỗ trợ tự động chạy ngầm làm ấm CSDL khi bật server (Startup Warm-up).
    """

    def __init__(self, search_tool: Optional[EcomSearchTool] = None):
        self.search_tool = search_tool or EcomSearchTool()
        self.is_running = False
        self.last_run_time: Optional[datetime] = None
        self.last_run_stats: Dict[str, Any] = {}

    async def should_warmup(self, max_stale_hours: int = 12) -> bool:
        """
        Kiểm tra xem CSDL có cần chạy làm ấm (warm-up) hay không:
        - Nếu kho rỗng (chưa có sản phẩm) -> Cần warm-up (True).
        - Nếu sản phẩm mới nhất đã cũ hơn max_stale_hours -> Cần warm-up (True).
        - Nếu dữ liệu còn mới (< max_stale_hours) -> Không cần (False).
        """
        try:
            async with async_session() as session:
                # Kiểm tra số lượng sản phẩm
                count_stmt = select(func.count()).select_from(ProductModel)
                count_res = await session.execute(count_stmt)
                total_products = count_res.scalar() or 0

                if total_products == 0:
                    return True

                # Kiểm tra thời điểm cập nhật mới nhất
                latest_stmt = select(ProductModel.updated_at).order_by(ProductModel.updated_at.desc()).limit(1)
                latest_res = await session.execute(latest_stmt)
                latest_update = latest_res.scalar_one_or_none()

                if not latest_update:
                    return True

                stale_threshold = datetime.utcnow() - timedelta(hours=max_stale_hours)
                return latest_update < stale_threshold

        except Exception as e:
            logger.warning(f"Lỗi kiểm tra trạng thái warm-up: {e}")
            return True

    async def run_batch_crawl(
        self,
        catalog: Optional[List[Dict[str, str]]] = None,
        limit_per_query: int = 4,
        force_refresh: bool = True
    ) -> Dict[str, Any]:
        """
        Thực hiện một đợt thu thập dữ liệu tự động cho danh sách từ khóa HOT.
        Dữ liệu cào về tự động được nạp vào SQLite và lưu cache nhờ EcomSearchTool.
        """
        if self.is_running:
            logger.warning("⚠️ Một đợt cào dữ liệu đang diễn ra, vui lòng chờ...")
            return {"status": "already_running", "message": "Crawler is currently running"}

        self.is_running = True
        target_catalog = catalog or DEFAULT_HOT_CATALOG
        start_time = time.perf_counter()

        logger.info(f"🚀 [BatchCrawler] Bắt đầu thu thập tự động cho {len(target_catalog)} danh mục HOT...")
        
        crawled_summary = []
        total_items_saved = 0

        try:
            for idx, target in enumerate(target_catalog, 1):
                query = target["query"]
                platform = target.get("platform", "all")
                category = target.get("category", "all")

                logger.info(f"  [{idx}/{len(target_catalog)}] Đang quét '{query}' ({platform.upper()})...")

                try:
                    # Gọi EcomSearchTool để cào thực tế (tự động nạp vào DB và ghi nhận lịch sử giá)
                    results = await self.search_tool.run(
                        query=query,
                        category=category,
                        platform=platform,
                        limit=limit_per_query,
                        force_refresh=force_refresh
                    )
                    count = len(results)
                    total_items_saved += count
                    crawled_summary.append({
                        "query": query,
                        "platform": platform,
                        "count": count
                    })
                except Exception as query_err:
                    logger.warning(f"  ❌ Lỗi khi quét '{query}': {query_err}")

                # Giãn cách 1.5 giây giữa các lượt quét để đảm bảo an toàn và không gây tải cao
                if idx < len(target_catalog):
                    await asyncio.sleep(1.5)

        finally:
            self.is_running = False

        duration = time.perf_counter() - start_time
        self.last_run_time = datetime.utcnow()
        self.last_run_stats = {
            "status": "completed",
            "queriesCount": len(target_catalog),
            "totalProducts": total_items_saved,
            "durationSeconds": round(duration, 2),
            "timestamp": self.last_run_time.isoformat(),
            "details": crawled_summary
        }

        logger.info(
            f"✨ [BatchCrawler] Hoàn tất đợt thu thập: {total_items_saved} sản phẩm được nạp vào CSDL "
            f"trong {duration:.1f}s."
        )
        return self.last_run_stats

    async def get_crawler_status(self) -> Dict[str, Any]:
        """Lấy thông tin tổng quan về trạng thái kho CSDL và crawler."""
        total_products = 0
        latest_update_str = None

        try:
            async with async_session() as session:
                count_stmt = select(func.count()).select_from(ProductModel)
                count_res = await session.execute(count_stmt)
                total_products = count_res.scalar() or 0

                latest_stmt = select(ProductModel.updated_at).order_by(ProductModel.updated_at.desc()).limit(1)
                latest_res = await session.execute(latest_stmt)
                latest_update = latest_res.scalar_one_or_none()
                if latest_update:
                    latest_update_str = latest_update.isoformat()
        except Exception:
            pass

        return {
            "isRunning": self.is_running,
            "totalProductsInDb": total_products,
            "latestDataUpdate": latest_update_str,
            "lastRunTime": self.last_run_time.isoformat() if self.last_run_time else None,
            "lastRunStats": self.last_run_stats,
            "hotCatalogCount": len(DEFAULT_HOT_CATALOG)
        }

# Singleton instance
batch_crawler_service = BatchCrawlerService()
