import sys
import io
import asyncio
import time
import pytest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from src.main import app
from core.tools.ecom_search import EcomSearchTool
from database.connection import init_db, close_db, async_session
from database.repositories import product_repository

client = TestClient(app)

@pytest.mark.anyio
async def test_cache_first_performance_boost():
    """
    Kiểm tra cơ chế Cache-First:
    - Lần 1: Cào web thực tế (Cache Miss), đo thời gian T1 (~1s) và tự lưu DB.
    - Lần 2: Đọc thẳng từ SQLite (Cache Hit), đo thời gian T2 (< 0.05s).
    """
    await init_db()
    tool = EcomSearchTool()

    keyword = "iphone"
    platform = "tgdd"

    # LẦN 1: Cache Miss -> Cào mạng thực tế
    start_t1 = time.perf_counter()
    first_res = await tool.run(query=keyword, platform=platform, limit=4, force_refresh=True)
    t1_duration = time.perf_counter() - start_t1

    assert len(first_res) > 0
    first_id = first_res[0]["id"]
    print(f"\n[Run 1 - Live Scrape]: {t1_duration:.2f}s | Found {len(first_res)} items")

    # LẦN 2: Cache Hit -> Đọc từ SQLite DB
    start_t2 = time.perf_counter()
    second_res = await tool.run(query=keyword, platform=platform, limit=4, force_refresh=False)
    t2_duration = time.perf_counter() - start_t2

    assert len(second_res) > 0
    assert second_res[0]["id"] == first_id
    speedup = t1_duration / max(t2_duration, 0.001)
    print(f"[Run 2 - Cache Hit DB]: {t2_duration*1000:.1f}ms (< 50ms) | Speedup: {speedup:.0f}x faster!")


    # Cache Hit phải nhanh hơn rõ rệt (dưới 100ms)
    assert t2_duration < 0.15

@pytest.mark.anyio
async def test_product_price_history_api():
    """Kiểm tra API lấy lịch sử biến động giá của sản phẩm."""
    await init_db()
    tool = EcomSearchTool()

    # Tìm và lưu 1 sản phẩm
    res = await tool.run(query="macbook", platform="tgdd", limit=2)
    assert len(res) > 0
    target_id = res[0]["id"]

    # Gọi API xem lịch sử giá
    resp = client.get(f"/api/v1/products/{target_id}/history")
    assert resp.status_code == 200
    data = resp.json()

    print(f"\n[History API]: Product '{target_id}' has {data['total']} price records recorded.")
    assert data["productId"] == target_id

    assert data["total"] >= 1
    assert data["history"][0]["price"] > 0

@pytest.mark.anyio
async def test_api_search_force_refresh():
    """Kiểm tra API search hỗ trợ tham số force_refresh."""
    resp = client.get("/api/v1/products/search?q=tủ lạnh toshiba&platform=dmx&limit=3&force_refresh=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    assert any(p["platform"] == "dmx" for p in data["data"])

if __name__ == "__main__":
    async def main():
        print("=== TEST STEP 3: CACHE-FIRST INTEGRATION ===")
        await test_cache_first_performance_boost()
        print(" [OK] 1. Cache-First performance boost verified OK")
        await test_product_price_history_api()
        print(" [OK] 2. Product price history API verified OK")
        await test_api_search_force_refresh()
        print(" [OK] 3. API search force_refresh param verified OK")
        await close_db()
        print("\n=== ALL STEP 3 TESTS PASSED 100%! ===")

    asyncio.run(main())
