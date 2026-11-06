import sys
import io
import asyncio
import json
import pytest
from datetime import datetime, timedelta

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

sys.path.insert(0, ".")

from database.connection import init_db, close_db, async_session
from database.repositories import product_repository

@pytest.mark.anyio
async def test_upsert_new_products():
    """Kiểm tra nạp sản phẩm mới vào DB và tự tạo mốc giá ban đầu."""
    await init_db()

    sample_products = [
        {
            "id": "tgdd-repo-test-1",
            "name": "Điện thoại iPhone 18 Pro Max 256GB",
            "category": "phones",
            "categoryName": "Điện thoại & Tablet",
            "platform": "tgdd",
            "platformName": "Thế Giới Di Động",
            "originalPrice": 41990000.0,
            "currentPrice": 41990000.0,
            "discountPercent": 0,
            "rating": 5.0,
            "reviewsCount": "Đã bán 10,1k",
            "image": "https://cdn.tgdd.vn/iphone-18.jpg",
            "specs": "Apple A20 Pro - 256GB",
            "aiSummary": "iPhone 18 Pro Max chính hãng TGDĐ",
            "warranty": "Chính hãng 1 đổi 1",
            "deliveryTag": "Giao nhanh 2h",
            "externalUrl": "https://www.thegioididong.com/dtdd/iphone-18"
        },
        {
            "id": "dmx-repo-test-2",
            "name": "Tủ lạnh Toshiba Inverter 460 lít",
            "category": "home_appliances",
            "categoryName": "Đồ gia dụng & Nhà bếp",
            "platform": "dmx",
            "platformName": "Điện Máy Xanh",
            "originalPrice": 16000000.0,
            "currentPrice": 14200000.0,
            "discountPercent": 11,
            "rating": 4.9,
            "reviewsCount": "Đã bán 12k",
            "image": "https://cdn.tgdd.vn/tu-lanh-toshiba.jpg",
            "specs": "Inverter tiết kiệm điện",
            "aiSummary": "Tủ lạnh Toshiba tiết kiệm điện",
            "warranty": "Bảo hành 2 năm ĐMX",
            "deliveryTag": "Miễn phí lắp đặt",
            "externalUrl": "https://www.dienmayxanh.com/tu-lanh-toshiba"
        }
    ]

    saved = await product_repository.upsert_products(sample_products)
    assert len(saved) == 2
    assert saved[0]["id"] == "tgdd-repo-test-1"
    assert saved[0]["currentPrice"] == 41990000.0
    assert saved[1]["id"] == "dmx-repo-test-2"

    # Kiểm tra lịch sử giá ban đầu đã được tạo
    history_1 = await product_repository.get_price_history("tgdd-repo-test-1")
    assert len(history_1) >= 1
    assert history_1[0]["price"] == 41990000.0

@pytest.mark.anyio
async def test_upsert_price_change_tracking():
    """Kiểm tra cơ chế tự động ghi lại mốc lịch sử mới khi giá thay đổi."""
    await init_db()

    target_id = "tgdd-repo-price-tracker"
    initial_product = {
        "id": target_id,
        "name": "Laptop ASUS Zenbook 14 OLED",
        "category": "laptops",
        "categoryName": "Laptop",
        "platform": "tgdd",
        "platformName": "Thế Giới Di Động",
        "originalPrice": 28000000.0,
        "currentPrice": 26000000.0,
        "discountPercent": 7,
        "rating": 4.8,
        "reviewsCount": "Đã bán 500",
        "externalUrl": "https://www.thegioididong.com/laptop-asus"
    }

    # Lần 1: Nạp sản phẩm giá 26tr
    await product_repository.upsert_products([initial_product])
    hist_1 = await product_repository.get_price_history(target_id)
    initial_hist_count = len(hist_1)

    # Lần 2: Nạp lại cùng sản phẩm nhưng TGDĐ giảm giá còn 24tr
    updated_product = dict(initial_product)
    updated_product["currentPrice"] = 24000000.0
    updated_product["discountPercent"] = 14
    await product_repository.upsert_products([updated_product])

    # Lịch sử giá phải có thêm mốc mới
    hist_2 = await product_repository.get_price_history(target_id)
    assert len(hist_2) == initial_hist_count + 1
    # Mốc giá mới nhất là 24tr
    assert hist_2[-1]["price"] == 24000000.0

    # Lấy lại sản phẩm trong kho: giá hiện tại phải là 24tr
    prod = await product_repository.get_product_by_id(target_id)
    assert prod is not None
    assert prod["currentPrice"] == 24000000.0

@pytest.mark.anyio
async def test_search_cache_hit_and_miss():
    """Kiểm tra cơ chế lưu và truy xuất nhanh kết quả tìm kiếm từ cache."""
    await init_db()

    query = "macbook m3 pro"
    platform = "tgdd"
    products = [
        {
            "id": "tgdd-macbook-m3-pro",
            "name": "MacBook Pro 14 M3 Pro",
            "category": "laptops",
            "categoryName": "Laptop",
            "platform": "tgdd",
            "platformName": "Thế Giới Di Động",
            "originalPrice": 50000000.0,
            "currentPrice": 48990000.0,
            "discountPercent": 2,
            "externalUrl": "https://www.thegioididong.com/macbook-pro-m3"
        }
    ]

    # Lưu cache có hiệu lực 2 tiếng
    await product_repository.save_search_cache(query, platform, products, ttl_hours=2)

    # 1. Truy vấn đúng query + platform -> Cache Hit
    hit = await product_repository.get_cached_search(query, platform)
    assert hit is not None
    assert len(hit) == 1
    assert hit[0]["id"] == "tgdd-macbook-m3-pro"
    assert hit[0]["currentPrice"] == 48990000.0

    # 2. Truy vấn khác platform -> Cache Miss
    miss_plat = await product_repository.get_cached_search(query, platform="dmx")
    assert miss_plat is None

    # 3. Truy vấn từ khóa chưa có -> Cache Miss
    miss_q = await product_repository.get_cached_search("từ khóa chưa từng tìm", "all")
    assert miss_q is None

@pytest.mark.anyio
async def test_search_cache_expiration():
    """Kiểm tra cache quá hạn sẽ không được trả về (Cache Miss)."""
    await init_db()

    query = "chảo chống dính cũ"
    platform = "dmx"
    products = [
        {
            "id": "dmx-chao-cu",
            "name": "Chảo nhôm chống dính cũ",
            "category": "home_appliances",
            "platform": "dmx",
            "platformName": "Điện Máy Xanh",
            "currentPrice": 200000.0
        }
    ]

    # Lưu cache với TTL âm (-1 giờ: đã hết hạn)
    await product_repository.save_search_cache(query, platform, products, ttl_hours=-1)

    # Truy vấn phải trả về None (hết hạn)
    cached = await product_repository.get_cached_search(query, platform)
    assert cached is None

if __name__ == "__main__":
    async def main():
        print("=== TEST STEP 2: PRODUCT REPOSITORY ===")
        await test_upsert_new_products()
        print(" [OK] 1. Upsert new products and initial price tracking OK")
        await test_upsert_price_change_tracking()
        print(" [OK] 2. Automatic price change history tracking OK")
        await test_search_cache_hit_and_miss()
        print(" [OK] 3. Search cache hit and miss retrieval OK")
        await test_search_cache_expiration()
        print(" [OK] 4. Search cache TTL expiration OK")
        await close_db()
        print("\n=== ALL STEP 2 TESTS PASSED 100%! ===")

    asyncio.run(main())

