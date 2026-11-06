import sys
import os
import asyncio

# Đảm bảo đường dẫn import từ thư mục gốc backend B
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import init_db, close_db
from services.batch_crawler import batch_crawler_service

async def main():
    print("=" * 65)
    print(" [SHOPAI] PROACTIVE BATCH CRAWLER (OPTION 1)")
    print(" Collecting hot products from TGDD, DMX & Tiki into SQLite...")
    print("=" * 65)

    # 1. Khởi tạo CSDL
    await init_db()

    # 2. Chạy đợt thu thập hàng loạt (giới hạn 3 món/danh mục để test nhanh)
    stats = await batch_crawler_service.run_batch_crawl(
        limit_per_query=3,
        force_refresh=True
    )

    print("\n" + "=" * 65)
    print(" SUMMARY REPORT:")
    print(f"  - Status:            {stats.get('status')}")
    print(f"  - Hot Queries:       {stats.get('queriesCount')}")
    print(f"  - Products Crawled:  {stats.get('totalProducts')}")
    print(f"  - Duration:          {stats.get('durationSeconds')}s")
    print("=" * 65)

    for item in stats.get("details", []):
        print(f"  * [{item['platform'].upper():4}] '{item['query']:22}' -> {item['count']} items saved to DB")

    await close_db()
    print("\n DONE! Database 'shopai.db' is now refreshed with live products!")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
