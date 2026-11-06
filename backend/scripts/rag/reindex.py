import argparse
import json
import asyncio
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import httpx  # noqa: E402
import chromadb  # noqa: E402
from chromadb.config import Settings as ChromaSettings  # noqa: E402
from chromadb.errors import NotFoundError  # noqa: E402

from shared.categories import tiki_path_from_breadcrumbs  # noqa: E402
from services.catalog.category_resolver import category_resolver  # noqa: E402
from services.rag import DEFAULT_CHROMA_PATH, ProductRAGService  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _from_old_collection(name: str):
    client = chromadb.PersistentClient(path=DEFAULT_CHROMA_PATH, settings=ChromaSettings(anonymized_telemetry=False))
    try:
        col = client.get_collection(name)
    except (NotFoundError, ValueError):  # collection không tồn tại
        print(f"Không có collection '{name}', bỏ qua.")
        return []
    data = col.get(include=["metadatas"])
    out = []
    for meta in data["metadatas"]:
        try:
            p = json.loads(meta["raw_json"])
        except (KeyError, TypeError, ValueError):  # bản ghi cũ thiếu / hỏng raw_json
            continue
        out.append((p, int(meta.get("updated_at") or 0)))
    return out


def _from_sqlite():
    from database.repositories.product_repo import product_model_to_dict
    from database.models.product import ProductModel
    db_path = os.path.join(BACKEND_DIR, "shopai.db")
    if not os.path.exists(db_path):
        return []
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    out = []
    for row in con.execute("SELECT * FROM products"):
        row = dict(row)
        updated = row.get("updated_at")
        if isinstance(updated, str):
            try:
                row["updated_at"] = datetime.fromisoformat(updated)
            except ValueError:
                row["updated_at"] = None
        model = ProductModel(**{k: v for k, v in row.items() if hasattr(ProductModel, k)})
        p = product_model_to_dict(model)
        # SQLite lưu giờ UTC không kèm múi giờ
        ts = int(model.updated_at.replace(tzinfo=timezone.utc).timestamp()) if model.updated_at else 0
        out.append((p, ts))
    return out


TIKI_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://tiki.vn/",
}


def _backfill_tiki_categories(products):
    """Bổ sung sourceCategoryPath cho sản phẩm Tiki cũ từ breadcrumbs của API chi tiết."""
    todo = [p for p in products if p.get("platform") == "tiki" and not p.get("sourceCategoryPath")]
    ok = 0
    with httpx.Client(headers=TIKI_HEADERS, timeout=10) as client:
        for p in todo:
            tiki_id = str(p.get("id", "")).removeprefix("tiki-").split("-")[0]
            if not tiki_id.isdigit():
                continue
            try:
                resp = client.get(f"https://tiki.vn/api/v2/products/{tiki_id}")
                if resp.status_code != 200:
                    continue
                crumbs = resp.json().get("breadcrumbs", [])
            except (httpx.HTTPError, ValueError):
                continue
            path = tiki_path_from_breadcrumbs(crumbs)
            if path:
                p["sourceCategoryPath"] = path
                p["sourceCategoryName"] = next((c.get("name") for c in reversed(crumbs) if c.get("category_id")), "")
                ok += 1
            time.sleep(0.3)
    print(f"Bổ sung mã danh mục Tiki: {ok}/{len(todo)} sản phẩm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="products_v1", help="collection cũ để lấy dữ liệu")
    ap.add_argument("--rebuild", action="store_true", help="xóa collection đích trước khi nạp")
    ap.add_argument("--no-backfill", action="store_true", help="không gọi API Tiki để bổ sung mã danh mục")
    args = ap.parse_args()

    rag = ProductRAGService()
    if args.rebuild:
        rag.clear()

    items = _from_old_collection(args.source) + _from_sqlite()
    if rag.collection_name != args.source:
        items += _from_old_collection(rag.collection_name)

    best, skipped = _dedupe(items, rag)
    products = [p for p, _ in best.values()]
    timestamps = [ts or int(time.time()) for _, ts in best.values()]
    print(f"Nguồn: {len(items)} bản ghi -> {len(products)} sản phẩm không trùng | bỏ: {skipped}")
    if not args.no_backfill:
        _backfill_tiki_categories(products)
    asyncio.run(category_resolver.resolve(products))

    t0 = time.time()
    done = 0
    for i in range(0, len(products), 64):
        done += rag.upsert_products(products[i:i + 64], timestamps=timestamps[i:i + 64])
    print(f"Đã nạp {done}/{len(products)} vào '{rag.collection_name}' ({rag.embedder.model}) trong {time.time() - t0:.1f}s")
    print(f"Dọn bản ghi cũ / sàn tắt: {rag.prune()} | Tổng kho: {rag.count()}")


def _dedupe(items, rag):
    """Bỏ bản ghi rác / sàn tắt / quá cũ; gộp các bản cùng link -> ({khóa: (sản phẩm, thời điểm)}, số bị bỏ theo lý do)."""
    cutoff = int(time.time()) - rag.max_age_days * 86400 if rag.max_age_days else 0
    best = {}
    skipped = {"rác": 0, "sàn tắt": 0, "quá cũ": 0}
    for p, ts in items:
        reason = _skip_reason(p, ts, rag.disabled_platforms, cutoff)
        if reason:
            skipped[reason] += 1
            continue
        key = (p.get("externalUrl") or "").split("?")[0].rstrip("/") or p.get("id")
        best[key] = _merge_versions(best[key], (p, ts)) if key in best else (p, ts)
    return best, skipped


def _skip_reason(p, ts, disabled_platforms, cutoff):
    name = (p.get("name") or "").strip()
    if not name or name.startswith("Sản phẩm từ") or not float(p.get("currentPrice") or 0):
        return "rác"
    if (p.get("platform") or "").lower() in disabled_platforms:
        return "sàn tắt"
    if ts and ts < cutoff:
        return "quá cũ"
    return None


def _merge_versions(a, b):
    """Giữ bản mới nhất (giá mới nhất), lấy bù từ bản cũ phần bản mới còn thiếu."""
    older, newer = sorted([a, b], key=lambda x: x[1])
    product = newer[0]
    # Thông số làm giàu từ trang chi tiết có thể chỉ nằm ở bản cũ
    if not isinstance(product.get("specs"), dict) and isinstance(older[0].get("specs"), dict):
        product = {**product, "specs": older[0]["specs"], "warranty": older[0].get("warranty") or product.get("warranty")}
    # Sản phẩm SQLite cũ có thể chưa có mã danh mục của sàn
    if not product.get("sourceCategoryPath") and older[0].get("sourceCategoryPath"):
        product = {**product, "sourceCategoryPath": older[0]["sourceCategoryPath"],
                   "sourceCategoryName": older[0].get("sourceCategoryName", "")}
    return product, newer[1]


if __name__ == "__main__":
    main()
