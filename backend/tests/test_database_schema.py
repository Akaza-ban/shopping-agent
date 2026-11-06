import sys
import io
import asyncio
from datetime import datetime, timedelta
import json
import pytest

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

sys.path.insert(0, ".")


from sqlalchemy import select, inspect
from database.connection import init_db, close_db, async_session, engine
from database.models import ProductModel, PriceHistoryModel, SearchCacheModel

@pytest.mark.anyio
async def test_init_db_creates_all_tables():
    """Kiểm tra khởi tạo CSDL và xác nhận tất cả các bảng đều được tạo thành công."""
    await init_db()
    
    async with engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
    
    print("\n[DB Tables]:", tables)
    assert "products" in tables
    assert "price_history" in tables
    assert "search_cache" in tables

@pytest.mark.anyio
async def test_product_crud_operations():
    """Kiểm tra thêm, đọc và cập nhật sản phẩm trong bảng products."""
    await init_db()
    
    test_id = "tgdd-test-370982"
    async with async_session() as session:
        # Xóa bản ghi cũ nếu có
        existing = await session.get(ProductModel, test_id)
        if existing:
            await session.delete(existing)
            await session.commit()
            
        # Thêm sản phẩm mới
        product = ProductModel(
            id=test_id,
            name="Điện thoại iPhone 18 Pro Max 256GB",
            category="phones",
            category_name="Điện thoại & Tablet",
            platform="tgdd",
            platform_name="Thế Giới Di Động",
            original_price=41990000.0,
            current_price=41990000.0,
            discount_percent=0,
            rating=5.0,
            reviews_count="Đã bán 10,1k",
            image="https://cdn.tgdd.vn/iphone-18-pro-max.jpg",
            specs="Chip Apple A20 Pro - RAM 8GB - Pin 43 giờ",
            ai_summary="Sản phẩm cao cấp tại TGDĐ",
            warranty="Chính hãng TGDĐ",
            delivery_tag="Giao nhanh 2h",
            external_url="https://www.thegioididong.com/dtdd/iphone-18-pro-max"
        )
        session.add(product)
        await session.commit()

    # Truy vấn lại để xác thực
    async with async_session() as session:
        queried = await session.get(ProductModel, test_id)
        assert queried is not None
        assert queried.name == "Điện thoại iPhone 18 Pro Max 256GB"
        assert queried.platform == "tgdd"
        assert queried.current_price == 41990000.0
        assert "Chip Apple A20 Pro" in queried.specs
        assert queried.created_at is not None

@pytest.mark.anyio
async def test_price_history_tracking():
    """Kiểm tra lưu vết lịch sử biến động giá của sản phẩm."""
    await init_db()
    test_id = "dmx-test-refrigerator"
    
    async with async_session() as session:
        # Xóa bản ghi cũ nếu có
        existing = await session.get(ProductModel, test_id)
        if existing:
            await session.delete(existing)
            await session.commit()

        # Tạo sản phẩm
        product = ProductModel(
            id=test_id,
            name="Tủ lạnh Toshiba Inverter 460 lít",
            category="home_appliances",
            category_name="Đồ gia dụng & Nhà bếp",
            platform="dmx",
            platform_name="Điện Máy Xanh",
            original_price=16000000.0,
            current_price=14200000.0,
            discount_percent=11,
            external_url="https://www.dienmayxanh.com/tu-lanh-toshiba"
        )
        session.add(product)
        await session.commit()

        # Thêm các mốc biến động giá
        history1 = PriceHistoryModel(
            product_id=test_id,
            price=15000000.0,
            original_price=16000000.0,
            discount_percent=6,
            recorded_at=datetime.utcnow() - timedelta(days=7)
        )
        history2 = PriceHistoryModel(
            product_id=test_id,
            price=14200000.0,
            original_price=16000000.0,
            discount_percent=11,
            recorded_at=datetime.utcnow()
        )
        session.add_all([history1, history2])
        await session.commit()

    # Truy vấn lịch sử giá qua quan hệ ORM
    async with async_session() as session:
        stmt = select(PriceHistoryModel).where(PriceHistoryModel.product_id == test_id).order_by(PriceHistoryModel.recorded_at.desc())
        res = await session.execute(stmt)
        histories = res.scalars().all()
        
        assert len(histories) == 2
        # Bản ghi mới nhất giá 14.2tr
        assert histories[0].price == 14200000.0
        # Bản ghi cũ hơn giá 15.0tr
        assert histories[1].price == 15000000.0

@pytest.mark.anyio
async def test_search_cache_ttl():
    """Kiểm tra lưu và kiểm tra hạn sử dụng (TTL) của search_cache."""
    await init_db()
    
    now = datetime.utcnow()
    valid_expire = now + timedelta(hours=2)
    expired_time = now - timedelta(minutes=5)
    
    async with async_session() as session:
        # Xóa cache test cũ để đảm bảo tính độc lập
        from sqlalchemy import delete
        await session.execute(
            delete(SearchCacheModel).where(SearchCacheModel.query.in_(["iphone", "laptop cũ"]))
        )
        await session.commit()

        # Cache hợp lệ
        valid_cache = SearchCacheModel(
            query="iphone",
            platform="all",
            product_ids=json.dumps(["tgdd-1", "tiki-2"]),
            expires_at=valid_expire
        )
        # Cache đã hết hạn
        expired_cache = SearchCacheModel(
            query="laptop cũ",
            platform="tgdd",
            product_ids=json.dumps(["tgdd-old"]),
            expires_at=expired_time
        )
        session.add_all([valid_cache, expired_cache])
        await session.commit()


    # Kiểm tra truy vấn cache còn hạn
    async with async_session() as session:
        stmt = select(SearchCacheModel).where(
            SearchCacheModel.query == "iphone",
            SearchCacheModel.platform == "all",
            SearchCacheModel.expires_at > datetime.utcnow()
        )
        result = await session.execute(stmt)
        cached_entry = result.scalar_one_or_none()
        
        assert cached_entry is not None
        ids = json.loads(cached_entry.product_ids)
        assert len(ids) == 2
        assert "tgdd-1" in ids

        # Kiểm tra cache hết hạn sẽ không được lấy
        expired_stmt = select(SearchCacheModel).where(
            SearchCacheModel.query == "laptop cũ",
            SearchCacheModel.expires_at > datetime.utcnow()
        )
        expired_res = await session.execute(expired_stmt)
        assert expired_res.scalar_one_or_none() is None

if __name__ == "__main__":
    async def main():
        print("=== BẮT ĐẦU CHẠY KIỂM THỬ BƯỚC 1 (SCHEMA & CSDL) ===")
        await test_init_db_creates_all_tables()
        print(" [OK] 1. Kiểm tra khởi tạo bảng CSDL thành công")
        await test_product_crud_operations()
        print(" [OK] 2. Kiểm tra thao tác CRUD bảng Products thành công")
        await test_price_history_tracking()
        print(" [OK] 3. Kiểm tra lưu vết Lịch sử giá PriceHistory thành công")
        await test_search_cache_ttl()
        print(" [OK] 4. Kiểm tra bộ nhớ đệm SearchCache & TTL thành công")
        await close_db()
        print("\n TẤT CẢ CÁC BÀI TEST BƯỚC 1 ĐỀU ĐẠT 100%!")

    asyncio.run(main())
