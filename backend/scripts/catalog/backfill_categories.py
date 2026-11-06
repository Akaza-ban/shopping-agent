"""Gán lại ngành hàng cho sản phẩm đã lưu trong SQLite theo bảng quy đổi danh mục (category_mappings)."""
import asyncio
import collections
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.connection import close_db, init_db  # noqa: E402
from scripts.rag.reindex import BACKEND_DIR, _backfill_tiki_categories  # noqa: E402
from services.catalog.categories import categorize  # noqa: E402
from services.catalog.category_resolver import category_resolver  # noqa: E402


async def main():
    await init_db()
    con = sqlite3.connect(os.path.join(BACKEND_DIR, "shopai.db"))
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT id, name, platform, external_url, source_category_path FROM products").fetchall()
    products = [{"id": r["id"], "name": r["name"], "platform": r["platform"], "externalUrl": r["external_url"],
                 "sourceCategoryPath": r["source_category_path"]} for r in rows]

    _backfill_tiki_categories(products)
    await category_resolver.resolve(products)

    for p in products:
        p["category"] = categorize(p)
    con.executemany("UPDATE products SET category = ?, source_category_path = ? WHERE id = ?",
                    [(p["category"], p["sourceCategoryPath"], p["id"]) for p in products])
    con.commit()
    con.close()
    unresolved = sum(1 for p in products if category_resolver.lookup(p) is None)
    print("Ngành hàng sau khi cập nhật:", collections.Counter(p["category"] for p in products).most_common())
    print(f"Chưa quy đổi được: {unresolved} sản phẩm")
    await close_db()


if __name__ == "__main__":
    asyncio.run(main())
