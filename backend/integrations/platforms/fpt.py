"""FPT Shop: trang tìm kiếm Next.js nhúng kết quả JSON (RSC); trang chi tiết có JSON-LD Product."""
import json
import logging
import re
from typing import Any, Dict, List
from urllib.parse import urlparse

import httpx

from shared.categories import category_path
from integrations.platforms.base import JsonLdDetailAdapter
from services.catalog.reviews import sold_label
from integrations.platforms.common import (
    BROWSER_HEADERS, broadened_note, first_hit, query_candidates, within_price,
)

logger = logging.getLogger("platforms.fpt")

FPT_DOMAIN = "https://fptshop.com.vn"
_RSC_PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', re.S)


def parse_fpt_search(html: str) -> List[Dict[str, Any]]:
    """Sản phẩm trong trang tìm kiếm FPT Shop (/tim-kiem?s=...)."""
    try:
        rsc = "".join(json.loads('"' + p + '"') for p in _RSC_PUSH_RE.findall(html))
    except ValueError:
        return []
    start = rsc.find('"product":{"name":')
    if start < 0:
        return []
    result_at = rsc.find('"result":', start)
    if result_at < 0:
        return []
    try:
        result, _ = json.JSONDecoder().raw_decode(rsc, result_at + len('"result":'))
    except ValueError:
        return []
    items = []
    for it in (result or {}).get("items") or []:
        slug = str(it.get("slug") or "").strip("/")
        name = str(it.get("displayName") or it.get("name") or "").strip()
        current = float(it.get("currentPrice") or 0)
        if not slug or not name or current <= 0:
            continue
        points = [f"{p.get('title', '')} {p.get('description', '')}".strip() for p in it.get("keySellingPoints") or []]
        sold = (it.get("sold") or {}).get("realQuantity") or 0
        names = [(it.get(k) or {}).get("name") for k in ("industry", "productType", "group")]
        items.append({
            "id": f"fpt-{it.get('code') or slug.split('/')[-1]}",
            "name": name,
            "href": f"{FPT_DOMAIN}/{slug}",
            "currentPrice": current,
            "originalPrice": float(it.get("originalPrice") or current),
            "discountPercent": int(it.get("discountPercentage") or 0),
            "rating": float(it.get("averageScore") or 0),
            "sold": sold_label(sold),
            "image": str((it.get("image") or {}).get("src") or ""),
            "specs": "; ".join(p for p in points if p),
            "categoryPath": category_path("fpt-shop", [n for n in names if n]) if any(names) else "",
        })
    return items


class FptAdapter(JsonLdDetailAdapter):
    id = "fpt-shop"
    name = "FPT Shop"
    hosts = ("fptshop.com.vn",)
    aliases = ("fpt shop", "fptshop", "fpt-shop", "fpt")
    badge_color = "#cb1c22"
    badge_bg = "rgba(203, 28, 34, 0.12)"
    warranty = "Chính hãng FPT Shop"
    delivery_tag = "Giao nhanh tại FPT Shop"

    async def search(self, keyword, criteria, limit, notes, user_query=""):
        """Thử các biến thể từ khóa như TGDĐ / ĐMX."""
        async with httpx.AsyncClient(headers={**BROWSER_HEADERS, "Referer": f"{FPT_DOMAIN}/"},
                                     follow_redirects=True, timeout=12.0) as client:
            raw, used = await first_hit(query_candidates(keyword, criteria), lambda q: self._fetch_search(client, q))
        if not raw:
            logger.info(f"[FPT Shop] Không có sản phẩm nào cho '{keyword}'")
            return []
        note = broadened_note("FPT Shop", keyword, used)
        if note:
            notes.append(note)
        return [self._to_product(it, criteria) for it in raw if within_price(it["currentPrice"], criteria)][:limit]

    @staticmethod
    async def _fetch_search(client, query: str) -> List[Dict[str, Any]]:
        try:
            resp = await client.get(f"{FPT_DOMAIN}/tim-kiem", params={"s": query})
        except httpx.HTTPError as e:
            logger.warning(f"Lỗi kết nối FPT Shop cho '{query}': {e}")
            return []
        return parse_fpt_search(resp.text) if resp.status_code == 200 else []

    def _to_product(self, it: Dict[str, Any], criteria) -> Dict[str, Any]:
        return {
            **self.product_base(criteria),
            "id": it["id"],
            "name": it["name"],
            "category": criteria.category if criteria else "all",  # ngành hàng thật: CategoryResolver
            "sourceCategoryPath": it["categoryPath"],
            "aiMatchScore": 95 if it["rating"] >= 4.5 else 85,
            "originalPrice": it["originalPrice"],
            "currentPrice": it["currentPrice"],
            "discountPercent": it["discountPercent"],
            "rating": it["rating"],
            "reviewsCount": it["sold"] or "Chưa có đánh giá",
            "sku": f"FPT-{it['id'].split('-', 1)[-1]}",
            "image": it["image"],
            "specs": it["specs"],
            "aiSummary": f"Sản phẩm thực tế tại FPT Shop: {it['name']}." + (f" {it['specs']}" if it["specs"] else ""),
            "externalUrl": it["href"],
        }

    def category_source(self, product):
        """Ngành + loại do FPT gán; sản phẩm lưu từ trước (chưa có) thì dùng đoạn đầu đường dẫn."""
        path = str(product.get("sourceCategoryPath") or "")
        if path.startswith("fpt-shop:") and len(path) > len("fpt-shop:"):
            return path, f"danh mục FPT Shop: {path.split(':', 1)[1]}"
        url = product.get("externalUrl") or ""
        slug = urlparse(url).path.strip("/").split("/")[0].lower() if self.owns_url(url) else ""
        return (f"fpt-shop:/{slug}", f"danh mục /{slug}/ của FPT Shop") if slug else None
