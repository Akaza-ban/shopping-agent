import sys
import os
import json
import asyncio
import argparse
import time

# Đảm bảo đường dẫn import từ thư mục gốc backend B
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


from sqlalchemy import select
from database.connection import init_db, close_db, async_session
from database.models import ProductModel
from services.rag import rag_service
from core.tools.ecom_search import EcomSearchTool

EXPANDED_HOT_CATALOG = [
    # 1. Điện thoại & Máy tính bảng (Phones & Tablets)
    {"query": "iphone 15", "platform": "all", "category": "phones", "categoryName": "Điện thoại"},
    {"query": "iphone 16", "platform": "all", "category": "phones", "categoryName": "Điện thoại"},
    {"query": "iphone 13", "platform": "all", "category": "phones", "categoryName": "Điện thoại"},
    {"query": "samsung galaxy s24", "platform": "all", "category": "phones", "categoryName": "Điện thoại"},
    {"query": "samsung galaxy a55", "platform": "all", "category": "phones", "categoryName": "Điện thoại"},
    {"query": "xiaomi 14", "platform": "all", "category": "phones", "categoryName": "Điện thoại"},
    {"query": "redmi note 13", "platform": "all", "category": "phones", "categoryName": "Điện thoại"},
    {"query": "oppo reno 12", "platform": "all", "category": "phones", "categoryName": "Điện thoại"},
    {"query": "ipad air", "platform": "all", "category": "phones", "categoryName": "Máy tính bảng"},
    {"query": "ipad pro", "platform": "all", "category": "phones", "categoryName": "Máy tính bảng"},

    # 2. Laptop & Máy tính (Laptops & Computing)
    {"query": "macbook air m2", "platform": "all", "category": "laptops", "categoryName": "Laptop"},
    {"query": "macbook pro m3", "platform": "all", "category": "laptops", "categoryName": "Laptop"},
    {"query": "laptop asus vivobook", "platform": "all", "category": "laptops", "categoryName": "Laptop"},
    {"query": "laptop lenovo ideapad", "platform": "all", "category": "laptops", "categoryName": "Laptop"},
    {"query": "laptop dell inspiron", "platform": "all", "category": "laptops", "categoryName": "Laptop"},
    {"query": "laptop hp pavilion", "platform": "all", "category": "laptops", "categoryName": "Laptop"},
    {"query": "laptop gaming asus tuf", "platform": "all", "category": "laptops", "categoryName": "Laptop"},
    {"query": "laptop gaming acer nitro", "platform": "all", "category": "laptops", "categoryName": "Laptop"},
    {"query": "laptop lenovo legion", "platform": "all", "category": "laptops", "categoryName": "Laptop"},
    {"query": "laptop mỏng nhẹ", "platform": "all", "category": "laptops", "categoryName": "Laptop"},

    # 3. Đồ gia dụng & Đời sống (Home Appliances)
    {"query": "noi chien khong dau", "platform": "all", "category": "home_appliances", "categoryName": "Đồ gia dụng"},
    {"query": "robot hut bui", "platform": "all", "category": "home_appliances", "categoryName": "Đồ gia dụng"},
    {"query": "may loc khong khi", "platform": "all", "category": "home_appliances", "categoryName": "Đồ gia dụng"},
    {"query": "tu lanh toshiba inverter", "platform": "all", "category": "home_appliances", "categoryName": "Đồ gia dụng"},
    {"query": "may giat panasonic", "platform": "all", "category": "home_appliances", "categoryName": "Đồ gia dụng"},
    {"query": "noi com dien cuckoo", "platform": "all", "category": "home_appliances", "categoryName": "Đồ gia dụng"},
    {"query": "quat cay panasonic", "platform": "all", "category": "home_appliances", "categoryName": "Đồ gia dụng"},
    {"query": "may say toc philips", "platform": "all", "category": "home_appliances", "categoryName": "Đồ gia dụng"},
    {"query": "bep tu don", "platform": "all", "category": "home_appliances", "categoryName": "Đồ gia dụng"},
    {"query": "lo vi song", "platform": "all", "category": "home_appliances", "categoryName": "Đồ gia dụng"},

    # 4. Thiết bị âm thanh & Phụ kiện (Audio & Accessories)
    {"query": "tai nghe airpods pro", "platform": "all", "category": "audio", "categoryName": "Thiết bị âm thanh"},
    {"query": "tai nghe sony wh-1000xm5", "platform": "all", "category": "audio", "categoryName": "Thiết bị âm thanh"},
    {"query": "tai nghe bluetooth", "platform": "all", "category": "audio", "categoryName": "Thiết bị âm thanh"},
    {"query": "loa bluetooth jbl", "platform": "all", "category": "audio", "categoryName": "Thiết bị âm thanh"},
    {"query": "loa bluetooth marshall", "platform": "all", "category": "audio", "categoryName": "Thiết bị âm thanh"},
    {"query": "sac du phong anker", "platform": "all", "category": "accessories", "categoryName": "Phụ kiện"},
    {"query": "chuot khong day logitech", "platform": "all", "category": "accessories", "categoryName": "Phụ kiện"},
    {"query": "ban phim co", "platform": "all", "category": "accessories", "categoryName": "Phụ kiện"},
    {"query": "dong ho apple watch", "platform": "all", "category": "accessories", "categoryName": "Đồng hồ thông minh"},
    {"query": "dong ho garmin", "platform": "all", "category": "accessories", "categoryName": "Đồng hồ thông minh"}
]


async def sync_sqlite_to_chroma() -> int:
    """Nạp toàn bộ sản phẩm hiện có trong SQLite ProductModel vào ChromaDB."""
    print("[Bước 1] Đang đồng bộ sản phẩm sẵn có từ SQLite (shopai.db) sang ChromaDB...")
    async with async_session() as session:
        stmt = select(ProductModel)
        res = await session.execute(stmt)
        db_products = res.scalars().all()

        if not db_products:
            print("  ℹ️ SQLite hiện chưa có sản phẩm nào.")
            return 0

        product_dicts = []
        for p in db_products:
            specs_parsed = p.specs
            try:
                if p.specs and (p.specs.startswith("{") or p.specs.startswith("[")):
                    specs_parsed = json.loads(p.specs)
            except Exception:
                specs_parsed = p.specs

            product_dicts.append({
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "categoryName": p.category_name,
                "platform": p.platform,
                "platformName": p.platform_name,
                "originalPrice": p.original_price,
                "currentPrice": p.current_price,
                "discountPercent": p.discount_percent,
                "rating": p.rating,
                "reviewsCount": p.reviews_count,
                "image": p.image,
                "specs": specs_parsed,
                "aiSummary": p.ai_summary,
                "warranty": p.warranty,
                "deliveryTag": p.delivery_tag,
                "externalUrl": p.external_url
            })

        count = rag_service.upsert_products(product_dicts)
        print(f"  Đã đồng bộ thành công {count} sản phẩm từ SQLite vào ChromaDB!")
        return count


async def crawl_and_seed_chroma(catalog: list, limit_per_query: int = 5) -> int:
    """Cào thêm sản phẩm thực tế từ Tiki, TGDĐ, ĐMX và tự động nạp thẳng vào ChromaDB."""
    print(f"\n[Bước 2] Bắt đầu quét {len(catalog)} từ khóa HOT (mỗi từ khóa lấy ~{limit_per_query} sản phẩm)...")
    search_tool = EcomSearchTool()
    total_crawled = 0
    start_time = time.perf_counter()

    for idx, item in enumerate(catalog, 1):
        q = item["query"]
        platform = item.get("platform", "all")
        cat = item.get("category", "all")
        cat_name = item.get("categoryName", "Sản phẩm")

        print(f"  [{idx:02d}/{len(catalog):02d}] Đang quét: '{q}' trên {platform.upper()}...", end=" ", flush=True)

        try:
            prods = await search_tool.run(
                query=q,
                category=cat,
                platform=platform,
                limit=limit_per_query,
                force_refresh=True
            )

            if prods:
                # Gán lại categoryName thân thiện
                for p in prods:
                    if not p.get("categoryName"):
                        p["categoryName"] = cat_name

                # Nạp ngay vào ChromaDB
                rag_service.upsert_products(prods)
                print(f"-> Thu được {len(prods)} sản phẩm ")
                total_crawled += len(prods)
            else:
                print("-> 0 sản phẩm (Bỏ qua)")

        except Exception as e:
            print(f"-> Lỗi: {e}")

        # Nghỉ nhẹ 1.2 giây giữa các request để tránh bị sàn chặn IP
        if idx < len(catalog):
            await asyncio.sleep(1.2)

    elapsed = time.perf_counter() - start_time
    print(f"\nĐã hoàn tất cào dữ liệu: {total_crawled} sản phẩm trong {elapsed:.1f} giây!")
    return total_crawled


async def main():
    parser = argparse.ArgumentParser(description="Seed RAG Catalog into ChromaDB")
    parser.add_argument("--sync-only", action="store_true", help="Chỉ đồng bộ sản phẩm từ SQLite sang ChromaDB")
    parser.add_argument("--queries", type=int, default=15, help="Số lượng từ khóa muốn quét cào mới (mặc định: 15)")
    parser.add_argument("--limit-per-query", type=int, default=5, help="Số sản phẩm lấy cho mỗi từ khóa (mặc định: 5)")
    args = parser.parse_args()

    print("=" * 70)
    print(" SHOPAI RAG SEED ENGINE - NẠP SẢN PHẨM VÀO CHROMADB VECTOR STORE")
    print("=" * 70)

    await init_db()

    # 1. Đồng bộ dữ liệu hiện có trong SQLite vào ChromaDB trước
    synced_count = await sync_sqlite_to_chroma()

    crawled_count = 0
    if not args.sync_only:
        selected_catalog = EXPANDED_HOT_CATALOG[:args.queries]
        crawled_count = await crawl_and_seed_chroma(
            catalog=selected_catalog,
            limit_per_query=args.limit_per_query
        )

    await close_db()

    # 3. Báo cáo thống kê
    stats = rag_service.get_stats()
    print("\n" + "=" * 70)
    print(" BÁO CÁO TỔNG KHO RAG VECTOR DATABASE (ChromaDB):")
    print(f"  - Trạng thái ChromaDB:       {stats.get('status').upper()}")
    print(f"  - Collection Name:           {stats.get('collection_name')}")
    print(f"  - Sản phẩm đồng bộ SQLite:   {synced_count}")
    print(f"  - Sản phẩm cào mới bổ sung:  {crawled_count}")
    print(f"  - TỔNG SẢN PHẨM TRONG RAG:   {stats.get('total_products')} sản phẩm")
    print(f"  - Đường dẫn lưu trữ:         {stats.get('persist_directory')}")
    print("=" * 70)
    print(" Chúc mừng! Kho tri thức RAG đã sẵn sàng phục vụ tìm kiếm siêu tốc!\n")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
