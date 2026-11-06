"""CellphoneS: API tìm kiếm công khai (GraphQL advanced_search mà trang tìm kiếm của sàn dùng); trang chi tiết có JSON-LD."""
import json
import logging
from typing import Any, Dict, List

import httpx

from shared.categories import category_path
from integrations.platforms.base import JsonLdDetailAdapter
from integrations.platforms.common import (
    BROWSER_HEADERS, broadened_note, first_hit, query_candidates, within_price,
)

logger = logging.getLogger("platforms.cellphones")

CPS_DOMAIN = "https://cellphones.com.vn"
CPS_SEARCH_URL = "https://api.cellphones.com.vn/graphql-search/v2/graphql/query"
CPS_IMAGE_BASE = "https://cdn2.cellphones.com.vn/358x/media/catalog/product"
CPS_SEARCH_QUERY = """query advanced_search { advanced_search(user_query: { terms: %s, province: 30 } page: 1) {
  products { product_id name url_path price special_price thumbnail category_objects { name } } meta { total } } }"""


def _strip_marketing(name: str) -> str:
    """"iPhone 16 128GB | Chính hãng VN/A" -> "iPhone 16 128GB"."""
    return str(name or "").split(" | ")[0].strip()


def parse_cellphones_search(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Sản phẩm trong kết quả GraphQL advanced_search của CellphoneS."""
    result = ((data or {}).get("data") or {}).get("advanced_search") or {}
    items = []
    for it in result.get("products") or []:
        price = float(it.get("price") or 0)
        special = float(it.get("special_price") or 0)  # 0 = không giảm giá
        current = special if 0 < special < price else price
        url_path = str(it.get("url_path") or "").strip("/")
        if current <= 0 or not url_path:
            continue
        names = [str(c.get("name") or "") for c in it.get("category_objects") or []]
        name = _strip_marketing(it.get("name"))
        thumb = str(it.get("thumbnail") or "")
        used = "Hàng cũ" in names or " cũ" in name.lower()
        if used and "cũ" not in name.lower():
            name += " (cũ)"  # máy cũ chỉ ghi "cũ" ở danh mục / đường dẫn
        items.append({
            "id": f"cps-{it.get('product_id')}",
            "name": name,
            "href": f"{CPS_DOMAIN}/{url_path}",
            "currentPrice": current,
            "originalPrice": price or current,
            "discountPercent": round((1 - current / price) * 100) if price > current else 0,
            "image": (CPS_IMAGE_BASE + thumb) if thumb.startswith("/") else thumb,
            "categoryPath": category_path("cellphones", names),
            "used": used,
        })
    return items


class CellphonesAdapter(JsonLdDetailAdapter):
    id = "cellphones"
    name = "CellphoneS"
    hosts = ("cellphones.com.vn",)
    aliases = ("cellphones", "cellphone s", "cellphone")
    badge_color = "#d70018"
    badge_bg = "rgba(215, 0, 24, 0.12)"
    warranty = "Chính hãng CellphoneS"
    delivery_tag = "Giao nhanh tại CellphoneS"

    async def search(self, keyword, criteria, limit, notes, user_query=""):
        wants_used = "cũ" in f"{user_query} {keyword}".lower().split()
        candidates = query_candidates(keyword, criteria)
        if wants_used and user_query:
            candidates = [user_query] + [q for q in candidates if q != user_query]
        headers = {**BROWSER_HEADERS, "Accept": "application/json", "Origin": CPS_DOMAIN, "Referer": f"{CPS_DOMAIN}/"}
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
            raw, used = await first_hit(candidates, lambda q: self._fetch_search(client, q))
        if not raw:
            logger.info(f"[CellphoneS] Không có sản phẩm nào cho '{keyword}'")
            return []
        note = broadened_note("CellphoneS", keyword, used, user_query)
        if note:
            notes.append(note)
        # Máy cũ, hàng trưng bày chỉ giữ khi người dùng hỏi hàng cũ
        kept = [it for it in raw if (wants_used or not it["used"]) and within_price(it["currentPrice"], criteria)]
        return [self._to_product(it, criteria) for it in kept][:limit]

    @staticmethod
    async def _fetch_search(client, query: str) -> List[Dict[str, Any]]:
        try:
            resp = await client.post(CPS_SEARCH_URL, json={"query": CPS_SEARCH_QUERY % json.dumps(query, ensure_ascii=False)})
            return parse_cellphones_search(resp.json()) if resp.status_code == 200 else []
        except (httpx.HTTPError, ValueError) as e:
            logger.warning(f"Lỗi kết nối CellphoneS cho '{query}': {e}")
            return []

    def _to_product(self, it: Dict[str, Any], criteria) -> Dict[str, Any]:
        return {
            **self.product_base(criteria),
            "id": it["id"],
            "name": it["name"],
            "category": criteria.category if criteria else "all",  # ngành hàng thật: CategoryResolver
            "sourceCategoryPath": it["categoryPath"],
            "aiMatchScore": 85,
            "originalPrice": it["originalPrice"],
            "currentPrice": it["currentPrice"],
            "discountPercent": it["discountPercent"],
            "rating": 0.0,
            "reviewsCount": "Chưa có đánh giá",
            "sku": f"CPS-{it['id'].split('-', 1)[-1]}",
            "image": it["image"],
            "aiSummary": f"Sản phẩm thực tế tại CellphoneS: {it['name']}.",
            "externalUrl": it["href"],
        }

    def category_source(self, product):
        """Hai cấp đầu của cây danh mục CellphoneS ("Âm thanh/Tai nghe"); cấp sau thường là hãng."""
        path = str(product.get("sourceCategoryPath") or "")
        if not path.startswith("cellphones:"):
            return None
        levels = [x for x in path.split(":", 1)[1].split("/") if x][:2]
        return (f"cellphones:{'/'.join(levels)}", f"danh mục CellphoneS: {' > '.join(levels)}") if levels else None

    def clean_link_name(self, name):
        return _strip_marketing(name)
