"""Đọc thông tin sản phẩm từ link người dùng dán vào (tải trang / gọi API của sàn).

    read_tiki()     Tiki: API v2 theo mã sản phẩm trong link; không được thì đọc như trang thường
    read_mwg()      TGDĐ / ĐMX (và các sàn có trang chi tiết): JSON-LD -> OpenGraph -> giá trong HTML
    read_generic()  trang bất kỳ: OpenGraph + thẻ product:price:amount

Kết quả là dict sản phẩm dạng chung của hệ thống (chưa phân loại ngành hàng, chưa kiểm định giá).
Lỗi mạng khi tải trang -> coi như không đọc được (tên lấy từ slug của link, giá 0).
"""

import json
import logging
import re
import urllib.parse
from typing import Any

import httpx
from bs4 import BeautifulSoup

from integrations import safe_http
from integrations.platforms.errors import CRAWL_ERRORS
from integrations.platforms.mwg import parse_mwg_detail, parse_mwg_price
from integrations.tls import ssl_context
from shared.categories import tiki_path_from_breadcrumbs

logger = logging.getLogger("link_reader")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "vi,vi-VN;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}
TIMEOUT_SECONDS = 8.0
GENERIC_BADGE = ("#64748b", "rgba(100, 116, 139, 0.15)")
TIKI_BADGE = ("#1a94ff", "rgba(26, 148, 255, 0.15)")
TIKI_API = "https://tiki.vn/api/v2/products/{product_id}"
MIN_HTML_PRICE = 100_000

_HTML_PRICE_RE = re.compile(r"(\d{1,3}(?:\.\d{3}){2})\s*(?:₫|đ)")
_TIKI_ID_PATTERNS = [r"-p(\d+)\.html", r"-p(\d+)", r"[/-]p(\d+)", r"[?&]spid=(\d+)", r"/(\d{6,})"]


# Đọc trang
def _url_hash(url: str, mod: int) -> int:
    return abs(hash(url)) % mod


def _page_meta(soup: BeautifulSoup) -> tuple[str, str, str]:
    """(tên, ảnh, mô tả) từ thẻ OpenGraph; tên lấy <title> nếu không có og:title."""

    def og(prop: str) -> str:
        tag = soup.find("meta", property=prop)
        return tag["content"].strip() if tag and tag.get("content") else ""

    name = og("og:title") or (soup.title.string.strip() if soup.title and soup.title.string else "")
    return name, og("og:image"), og("og:description")


def _jsonld_product(soup: BeautifulSoup) -> dict[str, Any]:
    """Tên, hãng, giá, ảnh từ khối JSON-LD @type Product đầu tiên của trang; {} nếu không có."""
    for script in soup.find_all("script", type="application/ld+json"):
        if not script.string:
            continue
        try:
            schema = json.loads(script.string)
        except ValueError:
            continue
        if not isinstance(schema, dict) or schema.get("@type") != "Product":
            continue
        brand = schema.get("brand")
        out: dict[str, Any] = {
            "name": schema.get("name") or "",
            "brand": (brand.get("name") if isinstance(brand, dict) else brand) or "",
        }
        try:
            out["price"] = float((schema.get("offers") or {}).get("price") or 0)
        except (ValueError, TypeError):
            out["price"] = 0.0
        rating = schema.get("aggregateRating")
        if isinstance(rating, dict):
            try:
                out["rating"] = float(rating.get("ratingValue") or 0)
                out["review_count"] = int(float(rating.get("reviewCount") or rating.get("ratingCount") or 0))
            except (ValueError, TypeError):
                pass
        image = schema.get("image")
        if isinstance(image, list) and image:
            out["image"] = image[0] if isinstance(image[0], str) else image[0].get("url", "")
        elif isinstance(image, str):
            out["image"] = image
        return out
    return {}


def _html_price(html: str) -> float:
    """Giá hợp lý đầu tiên (>= 100.000 đ) xuất hiện trong HTML; 0 nếu không thấy."""
    prices = [float(p.replace(".", "")) for p in _HTML_PRICE_RE.findall(html)]
    return next((p for p in prices if p >= MIN_HTML_PRICE), 0.0)


def _page_specs(soup: BeautifulSoup, limit: int = 8) -> dict[str, str]:
    """Vài dòng thông số "Nhãn: giá trị" trong bảng thông số của trang (giao diện cũ của TGDĐ / ĐMX)."""
    specs: dict[str, str] = {}
    for li in soup.select(".parameter li, .box-specifi li, ul.parameter > li")[:limit]:
        text = li.get_text(":", strip=True)
        if ":" in text:
            k, v = text.split(":", 1)
            specs[k.strip()] = v.strip()
    return specs


def slug_to_title(url: str, fallback_prefix: str) -> str:
    """Tên sản phẩm dễ đọc từ slug của link (khi không đọc được trang)."""
    match = re.search(r"https?://[^/]+/([^/?#]+)", url)
    if match:
        raw_slug = urllib.parse.unquote(match.group(1).replace(".html", ""))
        raw_slug = re.sub(r"-i\.\d+\.\d+$", "", raw_slug)
        raw_slug = re.sub(r"-i\d+$", "", raw_slug)
        raw_slug = re.sub(r"-p\d+$", "", raw_slug)
        clean = raw_slug.replace("-", " ").strip()
        if clean and clean.lower() not in ["product", "products", "item"]:
            return clean.capitalize()
    return f"Sản phẩm từ {fallback_prefix}"


async def _fetch_html(url: str) -> str | None:
    """HTML của trang; None nếu lỗi mạng, mã trả về khác 200, link trỏ vào mạng nội bộ hoặc trang quá lớn."""
    return await safe_http.fetch_text(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)


def _reviews_label(count: Any) -> str:
    """Số lượt đánh giá trên trang -> nhãn; không có thì nói rõ là chưa có."""
    try:
        n = int(count or 0)
    except (ValueError, TypeError):
        n = 0
    return f"{n} đánh giá" if n > 0 else "Chưa có đánh giá"


def _link_product(url, name, platform, platform_name, badge_color, badge_bg, *, price, **fields) -> dict[str, Any]:
    """Dạng sản phẩm chung của mọi link đọc từ trang (không biết giá gốc thì lấy bằng giá bán)."""
    original = max(fields.pop("original", 0.0) or 0.0, price)
    return {
        "id": fields.pop("id"),
        "name": name,
        "category": "all",
        "categoryName": fields.pop("categoryName"),
        "platform": platform,
        "platformName": platform_name,
        "platformBadgeColor": badge_color,
        "platformBadgeBg": badge_bg,
        "aiMatchScore": fields.pop("aiMatchScore"),
        "originalPrice": original,
        "currentPrice": price,
        "discountPercent": int(round((1 - price / original) * 100)) if original > price else 0,
        "rating": fields.pop("rating", 0.0),  # 0 = chưa có đánh giá
        "reviewsCount": fields.pop("reviewsCount", ""),
        "sku": fields.pop("sku"),
        "image": fields.pop("image"),
        "specs": fields.pop("specs"),
        "brand": fields.pop("brand"),
        "warranty": fields.pop("warranty", None),  # None = chưa rõ
        "returnPolicy": fields.pop("returnPolicy", None),
        "deliveryTag": None,  # trang sản phẩm không cho biết thời gian giao tới địa chỉ người dùng
        "selected": True,
        "externalUrl": url,
    }


# Theo sàn
async def read_mwg(url: str, platform: str, platform_name: str, badge_color: str, badge_bg: str) -> dict[str, Any]:
    """Trang chi tiết: JSON-LD trước, rồi OpenGraph, cuối cùng giá trong HTML."""
    name, image, description, price, original, brand, specs = "", "", "", 0.0, 0.0, "Chính hãng", {}
    ld: dict[str, Any] = {}
    detail: dict[str, Any] = {}
    html = await _fetch_html(url)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        ld = _jsonld_product(soup)
        og_name, og_image, description = _page_meta(soup)
        name = ld.get("name") or og_name
        image = ld.get("image") or og_image
        brand = ld.get("brand") or brand
        # Giá đang hiển thị trước: JSON-LD của TGDĐ / ĐMX ghi giá của khu vực giá khác
        price, original = parse_mwg_price(html) or (ld.get("price") or _html_price(html), 0.0)
        specs = _page_specs(soup)
        detail = parse_mwg_detail(html)  # bảo hành / đổi trả ghi trên trang
    return _link_product(
        url,
        name or slug_to_title(url, platform_name),
        platform,
        platform_name,
        badge_color,
        badge_bg,
        id=f"{platform}-{_url_hash(url, 1000000)}",
        categoryName=platform_name,
        aiMatchScore=95,
        price=price,
        original=original,
        rating=ld.get("rating", 0.0),
        reviewsCount=_reviews_label(ld.get("review_count")),
        image=image,
        specs=specs or description,
        brand=brand,
        sku=f"{platform.upper()}-{_url_hash(url, 10000)}",
        warranty=detail.get("warranty"),
        returnPolicy=detail.get("returnPolicy"),
    )


async def read_generic(
    url: str, platform="all", platform_name="Website", badge_color=GENERIC_BADGE[0], badge_bg=GENERIC_BADGE[1]
) -> dict[str, Any]:
    """Trang bất kỳ qua OpenGraph và thẻ giá product:price:amount."""
    name, image, description, price = "", "", "", 0.0
    ld: dict[str, Any] = {}
    html = await _fetch_html(url)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        ld = _jsonld_product(soup)
        name, image, description = _page_meta(soup)
        og_price = soup.find("meta", property="product:price:amount")
        try:
            price = float(og_price["content"]) if og_price and og_price.get("content") else 0.0
        except ValueError:
            price = 0.0
    return _link_product(
        url,
        name or slug_to_title(url, platform_name),
        platform,
        platform_name,
        badge_color,
        badge_bg,
        id=f"parsed-{_url_hash(url, 1000000)}",
        categoryName="Sản phẩm liên kết",
        aiMatchScore=90,
        price=price,
        rating=ld.get("rating", 0.0),
        reviewsCount=_reviews_label(ld.get("review_count")),
        image=image,
        specs=description,
        brand="Chính hãng",
        sku=f"URL-{_url_hash(url, 10000)}",
    )


def _tiki_product_id(url: str) -> str | None:
    for pattern in _TIKI_ID_PATTERNS:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def _tiki_product(data: dict[str, Any], product_id: str, url: str) -> dict[str, Any]:
    """Phản hồi API v2 của Tiki -> dict sản phẩm."""
    price = float(data.get("price") or 0)
    crumbs = data.get("breadcrumbs", [])
    cat_names = [str(c.get("name", "")) for c in crumbs if c.get("category_id")]
    seller = data.get("current_seller", {}).get("name") or "Tiki Trading"
    specs = {
        str(a["name"]).strip(): str(a["value"]).strip()
        for group in data.get("specifications", [])
        for a in group.get("attributes", [])
        if a.get("name") and a.get("value")
    }
    warranty = next((str(w["value"]) for w in data.get("warranty_info", []) if w.get("value")), None)
    return {
        "id": f"tiki-{product_id}",
        "name": data.get("name", "").strip(),
        "category": "all",
        "categoryName": "Tiki Trading",
        "sourceCategoryPath": tiki_path_from_breadcrumbs(crumbs),
        "sourceCategoryName": cat_names[-1] if cat_names else "",
        "platform": "tiki",
        "platformName": f"Tiki ({seller})",
        "platformBadgeColor": TIKI_BADGE[0],
        "platformBadgeBg": TIKI_BADGE[1],
        "aiMatchScore": 96,
        "originalPrice": float(data.get("original_price") or data.get("list_price") or price),
        "currentPrice": price,
        "discountPercent": int(data.get("discount_rate") or 0),
        "rating": float(data.get("rating_average") or 0.0),  # 0 = chưa có đánh giá
        "reviewsCount": _reviews_label(data.get("review_count")),
        "sku": str(data.get("sku") or f"TIKI-{product_id}"),
        "image": data.get("thumbnail_url") or "",
        "specs": specs,
        "brand": data.get("brand", {}).get("name", "Chính hãng"),
        "warranty": warranty,
        "deliveryTag": None,
        "selected": True,
        "externalUrl": url,
    }


async def read_tiki(url: str) -> dict[str, Any]:
    """Tiki qua API v2; không có mã sản phẩm hoặc API lỗi thì đọc như trang thường."""
    product_id = _tiki_product_id(url)
    if product_id:
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT_SECONDS, verify=ssl_context()) as client:
                resp = await client.get(TIKI_API.format(product_id=product_id))
            if resp.status_code == 200:
                return _tiki_product(resp.json(), product_id, url)
        except CRAWL_ERRORS as e:
            logger.warning(f"Lỗi gọi Tiki API v2 cho {url}: {e}")
    return await read_generic(
        url, platform="tiki", platform_name="Tiki Trading", badge_color=TIKI_BADGE[0], badge_bg=TIKI_BADGE[1]
    )
