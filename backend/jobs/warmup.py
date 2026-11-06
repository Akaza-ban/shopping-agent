"""Làm ấm kho dữ liệu lúc khởi động: kho trống hoặc đã cũ thì cào các mặt hàng HOT ở nền."""
import asyncio
import logging

from jobs.batch_crawler import batch_crawler_service

logger = logging.getLogger("warmup")

STARTUP_DELAY_SECONDS = 1.0  # chờ server sẵn sàng nhận request trước khi cào


async def run_startup_warmup() -> None:
    try:
        await asyncio.sleep(STARTUP_DELAY_SECONDS)
        if await batch_crawler_service.should_warmup():
            logger.info("[Startup Warm-up] CSDL cần làm ấm, bắt đầu thu thập các mặt hàng HOT...")
            await batch_crawler_service.run_batch_crawl(limit_per_query=3, force_refresh=True)
            logger.info("[Startup Warm-up] Đã làm ấm CSDL với dữ liệu thực.")
        else:
            logger.info("[Startup Warm-up] Dữ liệu trong CSDL vẫn còn mới, bỏ qua thu thập nền.")
    except Exception:  # chốt chặn: lỗi làm ấm không được làm sập server
        logger.exception("[Startup Warm-up] Lỗi tiến trình làm ấm CSDL")
