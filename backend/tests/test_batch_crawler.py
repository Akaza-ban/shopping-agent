import sys
import asyncio
import pytest

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from src.main import app
from database.connection import init_db, close_db
from services.batch_crawler import batch_crawler_service

client = TestClient(app)

@pytest.mark.anyio
async def test_crawler_status():
    """Kiểm tra API GET /api/v1/crawler/status trả về đúng cấu trúc."""
    await init_db()
    status = await batch_crawler_service.get_crawler_status()
    assert "isRunning" in status
    assert "totalProductsInDb" in status
    assert "hotCatalogCount" in status
    assert status["hotCatalogCount"] > 0

    # Kiểm tra qua HTTP API
    resp = client.get("/api/v1/crawler/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["isRunning"] == status["isRunning"]
    assert data["totalProductsInDb"] >= 0

@pytest.mark.anyio
async def test_should_warmup_logic():
    """Kiểm tra logic should_warmup với các ngưỡng thời gian."""
    await init_db()
    # Nếu ngưỡng stale rất lớn (ví dụ 10000 giờ) và DB đã có dữ liệu, should_warmup nên trả về False
    # Nếu DB rỗng, sẽ trả về True
    status = await batch_crawler_service.get_crawler_status()
    if status["totalProductsInDb"] > 0:
        needs_warmup = await batch_crawler_service.should_warmup(max_stale_hours=10000)
        assert needs_warmup is False
    else:
        needs_warmup = await batch_crawler_service.should_warmup(max_stale_hours=12)
        assert needs_warmup is True

@pytest.mark.anyio
async def test_batch_crawl_execution():
    """
    Kiểm tra chạy thu thập hàng loạt với 1 danh mục nhỏ (1 query, 2 sản phẩm)
    để xác nhận luồng nạp dữ liệu vào SQLite và cập nhật thống kê.
    """
    await init_db()
    test_catalog = [
        {"query": "tai nghe bluetooth", "platform": "tiki", "category": "audio", "categoryName": "Thiết bị âm thanh"}
    ]

    stats = await batch_crawler_service.run_batch_crawl(
        catalog=test_catalog,
        limit_per_query=2,
        force_refresh=True
    )

    assert stats["status"] == "completed"
    assert stats["queriesCount"] == 1
    assert stats["totalProducts"] > 0
    assert len(stats["details"]) == 1
    assert stats["details"][0]["count"] > 0

    # Kiểm tra lại status sau khi cào
    current_status = await batch_crawler_service.get_crawler_status()
    assert current_status["totalProductsInDb"] > 0
    assert current_status["lastRunTime"] is not None

@pytest.mark.anyio
async def test_crawler_trigger_api_background():
    """Kiểm tra gọi API POST /api/v1/crawler/trigger với background=True."""
    resp = client.post("/api/v1/crawler/trigger", json={"limit_per_query": 2, "force_refresh": False, "background": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("started", "already_running")

if __name__ == "__main__":
    async def main():
        print("=== TEST STEP 4: COMBINED OPTION 1 & OPTION 2 ===")
        await test_crawler_status()
        print(" [OK] 1. Crawler status & API verified OK")
        await test_should_warmup_logic()
        print(" [OK] 2. Startup warm-up decision logic verified OK")
        await test_batch_crawl_execution()
        print(" [OK] 3. Proactive batch crawl execution verified OK")
        await test_crawler_trigger_api_background()
        print(" [OK] 4. Trigger crawler background API verified OK")
        await close_db()
        print("\n=== ALL STEP 4 TESTS PASSED 100%! ===")

    asyncio.run(main())
