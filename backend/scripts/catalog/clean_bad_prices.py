import argparse
import asyncio
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.pricing import guardrails  # noqa: E402
from services.rag import rag_service  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _sqlite_products():
    con = sqlite3.connect(os.path.join(BACKEND_DIR, "shopai.db"))
    rows = con.execute("SELECT id, name, platform, current_price, external_url, category FROM products").fetchall()
    con.close()
    return [{"id": r[0], "name": r[1], "platform": r[2], "currentPrice": r[3], "externalUrl": r[4], "category": r[5]}
            for r in rows]

def _rag_products():
    out = []
    for meta in rag_service.corpus():
        try:
            p = json.loads(meta["raw_json"])
        except (KeyError, ValueError):
            continue
        out.append({**p, "id": meta["product_id"], "currentPrice": meta["current_price"]})
    return out

def _bad(products, extra_references=()):
    refs = {}
    for p in list(products) + list(extra_references):
        refs.setdefault(guardrails.product_key(p.get("name", "")), []).append(float(p.get("currentPrice") or 0))
    bad = []
    for p in products:
        key = guardrails.product_key(p.get("name", ""))
        others = list(refs.get(key, []))
        others.remove(float(p.get("currentPrice") or 0))
        _, rejected = guardrails.screen_products([p], {key: others})
        if rejected:
            bad.append(rejected[0])
    return bad


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="xóa thật (mặc định chỉ liệt kê)")
    args = ap.parse_args()

    db_products, rag_products = _sqlite_products(), _rag_products()
    bad_db = _bad(db_products, rag_products)
    bad_rag = _bad(rag_products, db_products)

    for label, bad in (("SQLite products", bad_db), (f"Kho RAG {rag_service.collection_name}", bad_rag)):
        print(f"\n{label}: {len(bad)} bản ghi giá sai")
        for p, verdict in bad:
            print(f"  - {p['id']}: {p['name'][:60]} — {verdict.reason}")

    if not args.apply:
        print("\nChạy lại với --apply để xóa.")
        return
    from database.repositories import product_repository
    deleted_db = await product_repository.delete_products([p["id"] for p, _ in bad_db])
    deleted_rag = rag_service.delete_products([p["id"] for p, _ in bad_rag])
    print(f"\nĐã xóa {deleted_db} sản phẩm khỏi SQLite (kèm lịch sử giá) và {deleted_rag} khỏi kho RAG.")


if __name__ == "__main__":
    asyncio.run(main())
