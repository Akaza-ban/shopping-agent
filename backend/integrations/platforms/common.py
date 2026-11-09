"""Phần dùng chung giữa các sàn: header trình duyệt, chuẩn hóa nhãn thông số, đọc JSON-LD, biến thể từ khóa, lọc giá."""

import json
import re
from typing import Any

from core.state import UniversalSearchCriteria

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
BROWSER_HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
}
PAGE_HEADERS = {"User-Agent": BROWSER_UA, "Accept-Language": "vi-VN,vi;q=0.9"}
MAX_SPEC_ITEMS = 40

SPEC_LABEL_ALIASES = [
    (re.compile(r"^(khối lượng giặt)", re.I), "Khối lượng giặt"),
    (re.compile(r"^card (màn hình|đồ họa)|^chip đồ họa|^gpu", re.I), "GPU"),
    (re.compile(r"^(chip xử lý|cpu|công nghệ cpu)", re.I), "CPU"),
    (re.compile(r"^ram$|^dung lượng ram", re.I), "RAM"),
    (re.compile(r"^(ổ cứng|dung lượng lưu trữ|bộ nhớ trong)", re.I), "Lưu trữ"),
    (re.compile(r"^(kích thước màn hình|màn hình rộng)", re.I), "Kích thước màn hình"),
    (re.compile(r"^(độ phân giải|độ phân giải màn hình)$", re.I), "Độ phân giải"),
    (re.compile(r"^(tần số quét)", re.I), "Tần số quét"),
    (re.compile(r"^(thông tin pin|dung lượng pin|pin)$", re.I), "Pin"),
    (re.compile(r"^(kích thước, khối lượng|khối lượng|trọng lượng)", re.I), "Khối lượng"),
    (re.compile(r"^(hệ điều hành)", re.I), "Hệ điều hành"),
    (re.compile(r"^(dung tích)", re.I), "Dung tích"),
    (re.compile(r"^(kiểu động cơ|công nghệ inverter|inverter)", re.I), "Động cơ / Inverter"),
    (re.compile(r"^(công suất)", re.I), "Công suất"),
    (re.compile(r"^(thời điểm ra mắt|năm ra mắt)", re.I), "Năm ra mắt"),
]


def canonical_spec_label(label: str) -> str:
    label = label.strip().rstrip(":").strip()
    for pattern, canonical in SPEC_LABEL_ALIASES:
        if pattern.search(label):
            return canonical
    return label


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


_LD_JSON_RE = re.compile(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)


def _ld_blocks(html: str):
    for raw in _LD_JSON_RE.findall(html or ""):
        try:
            yield json.loads(raw.strip())
        except ValueError:
            continue


def _ld_products(node: Any):
    """Các khối @type Product trong JSON-LD (có thể nằm trong danh sách hoặc @graph)."""
    if isinstance(node, list):
        for x in node:
            yield from _ld_products(x)
    elif isinstance(node, dict):
        if node.get("@type") == "Product":
            yield node
        yield from _ld_products(node.get("@graph") or [])


def parse_offer_price(html: str) -> float | None:
    """Giá bán hiện tại trên trang chi tiết (JSON-LD Product.offers.price); dùng cho TGDĐ, ĐMX, FPT Shop, CellphoneS."""

    def find_price(node: Any) -> float | None:
        if isinstance(node, dict):
            offers = node.get("offers")
            if isinstance(offers, (dict, list)):
                for offer in offers if isinstance(offers, list) else [offers]:
                    if isinstance(offer, dict) and str(offer.get("price", "")).replace(".", "").isdigit():
                        return float(offer["price"])
            for value in node.values():
                found = find_price(value)
                if found:
                    return found
        elif isinstance(node, list):
            for value in node:
                found = find_price(value)
                if found:
                    return found
        return None

    for block in _ld_blocks(html):
        price = find_price(block)
        if price:
            return price
    m = re.search(r'"price"\s*:\s*"?(\d{4,})', html or "")
    return float(m.group(1)) if m else None


# schema.org/ItemAvailability: còn mua được ngay hay không
_IN_STOCK = {"instock", "limitedavailability", "onlineonly", "instoreonly"}
_OUT_OF_STOCK = {"outofstock", "soldout", "discontinued", "preorder", "presale", "backorder"}


def parse_availability(html: str) -> bool | None:
    """Còn hàng: True / False theo JSON-LD offers.availability; None nếu trang không ghi."""
    for value in re.findall(r'"availability"\s*:\s*"([^"]+)"', html or ""):
        state = value.rsplit("/", 1)[-1].lower()
        if state in _IN_STOCK:
            return True
        if state in _OUT_OF_STOCK:
            return False
    if re.search(r"Ngừng kinh doanh|Tạm hết hàng|Sản phẩm (đã |đang )?hết hàng", html or ""):
        return False
    return None


def parse_jsonld_detail(html: str) -> dict[str, Any]:
    """Thông số, điểm đánh giá, số lượt đánh giá từ khối JSON-LD Product của trang chi tiết."""
    specs: dict[str, str] = {}
    rating, reviews = None, None
    for block in _ld_blocks(html):
        for product in _ld_products(block):
            for prop in product.get("additionalProperty") or []:
                name, value = clean_text(str(prop.get("name", ""))), clean_text(str(prop.get("value", "")))
                if name and value and len(value) <= 200 and len(specs) < MAX_SPEC_ITEMS:
                    specs.setdefault(canonical_spec_label(name), value)
            agg = product.get("aggregateRating") or {}
            try:
                rating = float(agg.get("ratingValue")) if agg.get("ratingValue") else rating
                reviews = int(agg.get("reviewCount")) if agg.get("reviewCount") else reviews
            except (TypeError, ValueError):
                pass
    return {"specs": specs, "warranty": None, "returnPolicy": None, "rating": rating, "reviewsCount": reviews}


async def fetch_page_price(client, url: str) -> dict[str, Any] | None:
    """Giá hiện tại + còn hàng đọc từ trang chi tiết; None nếu không đọc được trang hoặc không thấy giá."""
    resp = await client.get(url, headers=PAGE_HEADERS)
    return page_offer(resp.text) if resp.status_code == 200 else None


def page_offer(html: str) -> dict[str, Any] | None:
    """Giá (JSON-LD / thẻ meta) và tình trạng còn hàng của một trang chi tiết đã tải."""
    price, in_stock = parse_offer_price(html), parse_availability(html)
    if not price and in_stock is not False:
        return None
    return {"currentPrice": price, "originalPrice": price, "inStock": in_stock}


def strip_attribute_terms(text: str, criteria: UniversalSearchCriteria | None) -> str:
    """Bỏ các giá trị thuộc tính kỹ thuật (VD: "RTX 4070") khỏi từ khóa, giữ lại loại sản phẩm."""
    if criteria and criteria.attributes:
        for val in criteria.attributes.values():
            if isinstance(val, str) and val.strip():
                text = re.sub(re.escape(val.strip()), " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def query_candidates(crawler_query: str, criteria: UniversalSearchCriteria | None) -> list[str]:
    """Các từ khóa thử lần lượt khi tìm không ra: nguyên câu -> bỏ thông số -> loại sản phẩm + hãng -> loại sản phẩm."""
    candidates = [crawler_query, strip_attribute_terms(crawler_query, criteria)]
    if criteria and criteria.target_entity:
        entity = criteria.target_entity.strip()
        if criteria.brands:
            candidates.append(f"{entity} {criteria.brands[0]}")
        candidates.append(entity)
    result: list[str] = []
    for c in candidates:
        if c and c.lower() not in [r.lower() for r in result]:
            result.append(c)
    return result


def within_price(price: float, criteria: UniversalSearchCriteria | None) -> bool:
    if criteria:
        if criteria.max_price and price > criteria.max_price:
            return False
        if criteria.min_price and price < criteria.min_price:
            return False
    return True


async def first_hit(candidates: list[str], fetch) -> tuple[list[dict[str, Any]], str | None]:
    """Thử lần lượt các biến thể từ khóa, dừng ở biến thể đầu tiên có kết quả: (kết quả, biến thể đã dùng)."""
    for q in candidates:
        items = await fetch(q)
        if items:
            return items, q
    return [], None


def broadened_note(platform_name: str, keyword: str, used: str | None, *same_as: str) -> str | None:
    """Ghi chú khi phải tìm rộng hơn từ khóa gốc (để Advisor nói rõ kết quả không khớp hẳn từ khóa)."""
    if not used or used in (keyword, *same_as):
        return None
    return f"{platform_name}: không có kết quả cho '{keyword}', đã tìm rộng hơn với '{used}'."
