"""Tiki: API tìm kiếm /api/v2/products và API chi tiết /api/v2/products/{id}."""
import logging
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from core.state import UniversalSearchCriteria
from services.catalog.categories import tiki_path_from_breadcrumbs
from services.catalog.platforms.base import PlatformAdapter
from services.catalog.platforms.common import BROWSER_UA, canonical_spec_label, clean_text, strip_attribute_terms, within_price

logger = logging.getLogger("platforms.tiki")

API_HEADERS = {"User-Agent": BROWSER_UA, "Accept": "application/json, text/plain, */*", "Referer": "https://tiki.vn/"}
def parse_tiki_detail(data: Dict[str, Any]) -> Dict[str, Any]:
    """Đọc JSON chi tiết sản phẩm Tiki."""
    specs: Dict[str, str] = {}
    for group in data.get("specifications") or []:
        for attr in group.get("attributes") or []:
            name = clean_text(str(attr.get("name", "")))
            value = clean_text(BeautifulSoup(str(attr.get("value", "")), "html.parser").get_text(" "))
            if name and value and len(value) <= 200:
                specs.setdefault(canonical_spec_label(name), value)

    warranty = None
    for key in ("Thời gian bảo hành", "Hình thức bảo hành", "Sản phẩm có được bảo hành không?"):
        if key in specs:
            warranty = f"{key}: {specs[key]}"
            break

    return_policy = None
    raw_return = data.get("return_and_exchange_policy")
    if raw_return:
        return_policy = clean_text(BeautifulSoup(str(raw_return), "html.parser").get_text(" "))

    return {"specs": specs, "warranty": warranty, "returnPolicy": return_policy}


def _tiki_id(product: Dict[str, Any]) -> Optional[str]:
    tiki_id = str(product.get("id", "")).replace("tiki-", "")
    return tiki_id if tiki_id.isdigit() else None


class TikiAdapter(PlatformAdapter):
    id = "tiki"
    name = "Tiki Trading"
    type = "Sàn TMĐT"
    hosts = ("tiki.vn",)
    aliases = ("tiki",)
    badge_color = "#1a94ff"
    badge_bg = "rgba(26, 148, 255, 0.15)"
    warranty = "Chính hãng Tiki"
    delivery_tag = "TikiNOW"

    async def search(self, keyword, criteria, limit, notes, user_query=""):
        products = await self._search_once(keyword, criteria, limit)
        stripped = strip_attribute_terms(keyword, criteria)
        if not products and stripped and stripped != keyword:
            products = await self._search_once(stripped, criteria, limit)
            if products:
                notes.append(f"{self.name}: không có kết quả cho '{keyword}', đã tìm rộng hơn với '{stripped}'.")
        return products

    async def _search_once(self, keyword: str, criteria: Optional[UniversalSearchCriteria], limit: int) -> List[Dict[str, Any]]:
        products: List[Dict[str, Any]] = []
        # Lấy dư vì nhiều kết quả sẽ bị loại ở bước lọc phụ kiện/giá
        params = {"q": keyword, "limit": max(limit * 3, 20)}
        if criteria and (criteria.min_price or criteria.max_price):
            params["price"] = f"{int(criteria.min_price or 0)},{int(criteria.max_price or 1000000000)}"
        try:
            async with httpx.AsyncClient(headers=API_HEADERS, follow_redirects=True, timeout=8.0) as client:
                resp = await client.get("https://tiki.vn/api/v2/products", params=params)
            if resp.status_code != 200:
                return []
            for item in resp.json().get("data", []):
                cat_name = str(item.get("primary_category_name") or "")
                cat_path = str(item.get("primary_category_path") or "")
                curr_price = float(item.get("price", 0))
                if not within_price(curr_price, criteria):
                    continue
                rating = float(item.get("rating_average") or 0.0)  # 0 = chưa có đánh giá
                reviews_count = item.get("review_count") or 0
                url_path = item.get("url_path") or ""
                products.append({
                    **self.product_base(criteria),
                    "id": f"tiki-{item.get('id', '')}",
                    "name": str(item.get("name", "")).strip(),
                    "category": criteria.category if criteria else "all",  # ngành hàng thật: CategoryResolver
                    "sourceCategoryPath": cat_path,
                    "sourceCategoryName": cat_name,
                    "aiMatchScore": 95 if rating >= 4.5 else 85,
                    "originalPrice": float(item.get("original_price") or curr_price),
                    "currentPrice": curr_price,
                    "discountPercent": int(item.get("discount_rate") or 0),
                    "rating": rating,
                    "reviewsCount": f"{reviews_count} đánh giá",
                    "sku": str(item.get("sku") or f"TIKI-{item.get('id')}"),
                    "image": item.get("thumbnail_url") or "",
                    "aiSummary": f"Sản phẩm thực tế trên Tiki: {item.get('name')}. Đánh giá {rating}/5 với {reviews_count} lượt mua.",
                    "externalUrl": f"https://tiki.vn/{url_path}" if url_path else "https://tiki.vn",
                })
                if len(products) >= limit:
                    break
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm Tiki: {e}")
        return products

    def detail_cache_key(self, product):
        tiki_id = _tiki_id(product)
        return f"tiki:{tiki_id}" if tiki_id else None

    async def fetch_detail(self, client, product):
        tiki_id = _tiki_id(product)
        if not tiki_id:
            return None
        resp = await client.get(f"https://tiki.vn/api/v2/products/{tiki_id}", headers=API_HEADERS)
        return parse_tiki_detail(resp.json()) if resp.status_code == 200 else None

    async def fetch_price(self, client, product):
        tiki_id = _tiki_id(product)
        if not tiki_id:
            return None
        resp = await client.get(f"https://tiki.vn/api/v2/products/{tiki_id}", headers=API_HEADERS)
        if resp.status_code != 200:
            return None
        data = resp.json()
        status = data.get("inventory_status")
        in_stock = None if not status else status == "available"
        if not data.get("price") and in_stock is not False:
            return None
        price = float(data["price"]) if data.get("price") else None
        return {"currentPrice": price, "originalPrice": float(data.get("list_price") or price or 0) or None,
                "inStock": in_stock, "sourceCategoryPath": tiki_path_from_breadcrumbs(data.get("breadcrumbs"))}

    def category_source(self, product):
        path = str(product.get("sourceCategoryPath") or "").strip("/")
        if not path or not path.replace("/", "").isdigit():
            return None
        return f"tiki:{path}", product.get("sourceCategoryName") or f"mã danh mục Tiki {path}"
