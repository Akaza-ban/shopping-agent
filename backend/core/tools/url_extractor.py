import asyncio
import re
import json
import logging
import urllib.parse
from typing import Dict, Any, Optional, Tuple
import httpx
from bs4 import BeautifulSoup

from .base import BaseTool
from services.catalog.data_processor import data_processor
from services.catalog.categories import categorize, tiki_path_from_breadcrumbs
from services.catalog.category_resolver import category_resolver
from services.catalog.platforms import display_names, platform_for_url
from services.catalog.platforms.mwg import parse_mwg_price
from services.pricing import guardrails as price_guardrails

logger = logging.getLogger("url_extractor")

# Các sàn đã bỏ vì chặn bot, không đọc được dữ liệu tin cậy
UNSUPPORTED_SITES = {"shopee.vn": "Shopee", "shp.ee": "Shopee", "lazada.vn": "Lazada"}
GENERIC_BADGE = ("#64748b", "rgba(100, 116, 139, 0.15)")
TIKI_BADGE = ("#1a94ff", "rgba(26, 148, 255, 0.15)")
_HTML_PRICE_RE = re.compile(r"(\d{1,3}(?:\.\d{3}){2})\s*(?:₫|đ)")
_TIKI_ID_PATTERNS = [r"-p(\d+)\.html", r"-p(\d+)", r"[/-]p(\d+)", r"[?&]spid=(\d+)", r"/(\d{6,})"]


def unsupported_site(url: str) -> Optional[str]:
    """Tên sàn nếu link thuộc sàn không hỗ trợ, ngược lại None."""
    url_lower = (url or "").lower()
    return next((name for domain, name in UNSUPPORTED_SITES.items() if domain in url_lower), None)


def _url_hash(url: str, mod: int) -> int:
    return abs(hash(url)) % mod


def _page_meta(soup: BeautifulSoup) -> Tuple[str, str, str]:
    """(tên, ảnh, mô tả) từ thẻ OpenGraph; tên lấy <title> nếu không có og:title."""
    def og(prop: str) -> str:
        tag = soup.find("meta", property=prop)
        return tag["content"].strip() if tag and tag.get("content") else ""

    name = og("og:title") or (soup.title.string.strip() if soup.title and soup.title.string else "")
    return name, og("og:image"), og("og:description")


def _jsonld_product(soup: BeautifulSoup) -> Dict[str, Any]:
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
        out: Dict[str, Any] = {"name": schema.get("name") or "",
                               "brand": (brand.get("name") if isinstance(brand, dict) else brand) or ""}
        try:
            out["price"] = float((schema.get("offers") or {}).get("price") or 0)
        except (ValueError, TypeError):
            out["price"] = 0.0
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
    return next((p for p in prices if p >= 100_000), 0.0)


def _page_specs(soup: BeautifulSoup, limit: int = 8) -> Dict[str, str]:
    """Vài dòng thông số "Nhãn: giá trị" trong bảng thông số của trang (giao diện cũ của TGDĐ / ĐMX)."""
    specs: Dict[str, str] = {}
    for li in soup.select(".parameter li, .box-specifi li, ul.parameter > li")[:limit]:
        text = li.get_text(":", strip=True)
        if ":" in text:
            k, v = text.split(":", 1)
            specs[k.strip()] = v.strip()
    return specs


def _tiki_product_id(url: str) -> Optional[str]:
    for pattern in _TIKI_ID_PATTERNS:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def _tiki_specs(data: Dict[str, Any]) -> Dict[str, str]:
    return {str(a["name"]).strip(): str(a["value"]).strip()
            for group in data.get("specifications", []) for a in group.get("attributes", [])
            if a.get("name") and a.get("value")}


def _tiki_warranty(data: Dict[str, Any]) -> str:
    return next((str(w["value"]) for w in data.get("warranty_info", []) if w.get("value")), "Chính hãng 12 tháng")


class UrlExtractorTool(BaseTool):
    name = "url_extractor"
    description = f"Trích xuất và thẩm định thông tin sản phẩm thực tế từ đường dẫn link (URL) {display_names()}"

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "vi,vi-VN;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }

    async def run(self, url: str) -> Dict[str, Any]:
        """Đọc sản phẩm từ link: nhận diện sàn -> đọc trang -> ngành hàng -> kiểm định giá -> lưu kho RAG."""
        url = (url or "").strip()
        if not url:
            raise ValueError("URL không được để trống")
        site = unsupported_site(url)
        if site:
            raise ValueError(f"Chưa hỗ trợ đọc link {site}")

        item = await self._read_link(url)
        await self._apply_category(item)

        processed = data_processor.process_product(item)
        verdict = price_guardrails.check_price((processed or item).get("currentPrice"), categorize(processed or item))
        if not processed or not verdict.ok:
            item = processed or item
            item.update(currentPrice=0.0, originalPrice=0.0, priceUnavailable=True)
            item["aiSummary"] = self._generate_ai_summary(item)
            logger.warning(f"[UrlExtractor] Không lấy được giá hợp lệ cho {url}: {verdict.reason}")
            return item

        processed["aiSummary"] = self._generate_ai_summary(processed)
        await self._store_in_rag(processed)
        return processed

    async def _read_link(self, url: str) -> Dict[str, Any]:
        """Dữ liệu thô của sản phẩm theo sàn của link (Tiki qua API, các sàn khác qua trang sản phẩm)."""
        platform = platform_for_url(url)
        if platform is None:
            return await self._extract_generic(url)
        if platform.id == "tiki":
            return await self._extract_tiki(url)
        item = await self._extract_mwg(url, platform=platform.id, platform_name=platform.name,
                                       badge_color=platform.badge_color, badge_bg=platform.badge_bg)
        item["name"] = platform.clean_link_name(str(item.get("name") or ""))
        return item

    @staticmethod
    async def _apply_category(item: Dict[str, Any]) -> None:
        """Ngành hàng theo danh mục của sàn (danh mục mới được LLM quy đổi một lần rồi lưu lại)."""
        await category_resolver.resolve([item])
        mapping = category_resolver.lookup(item)
        if mapping:
            item["category"] = mapping.category

    @staticmethod
    async def _store_in_rag(product: Dict[str, Any]) -> None:
        """Lưu vào kho RAG để lần sau tìm được sản phẩm này; lỗi thì bỏ qua."""
        try:
            from services.rag import rag_service
            await asyncio.to_thread(rag_service.upsert_products, [product])
            logger.info(f"[UrlExtractor] Đã tự động lưu sản phẩm '{product['name']}' vào ChromaDB.")
        except Exception as e:
            logger.debug(f"Không thể upsert vào RAG: {e}")

    async def _fetch_html(self, url: str) -> Optional[str]:
        """HTML của trang; None nếu lỗi mạng hoặc mã trả về khác 200."""
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=8.0) as client:
                resp = await client.get(url)
            return resp.text if resp.status_code == 200 else None
        except Exception as e:
            logger.warning(f"Lỗi tải trang {url}: {e}")
            return None

    async def _extract_tiki(self, url: str) -> Dict[str, Any]:
        """Sản phẩm Tiki qua API v2; không có mã sản phẩm hoặc API lỗi thì đọc như trang thường."""
        product_id = _tiki_product_id(url)
        if product_id:
            try:
                async with httpx.AsyncClient(headers=self.headers, timeout=8.0) as client:
                    resp = await client.get(f"https://tiki.vn/api/v2/products/{product_id}")
                if resp.status_code == 200:
                    return self._tiki_product(resp.json(), product_id, url)
            except Exception as e:
                logger.warning(f"Lỗi gọi Tiki API v2 cho {url}: {e}")
        return await self._extract_generic(url, platform="tiki", platform_name="Tiki Trading",
                                           badge_color=TIKI_BADGE[0], badge_bg=TIKI_BADGE[1])

    @staticmethod
    def _tiki_product(data: Dict[str, Any], product_id: str, url: str) -> Dict[str, Any]:
        price = float(data.get("price") or 0)
        crumbs = data.get("breadcrumbs", [])
        cat_names = [str(c.get("name", "")) for c in crumbs if c.get("category_id")]
        seller = data.get("current_seller", {}).get("name") or "Tiki Trading"
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
            "rating": float(data.get("rating_average") or 5.0),
            "reviewsCount": f"{data.get('review_count', 0)} đánh giá",
            "sku": str(data.get("sku") or f"TIKI-{product_id}"),
            "image": data.get("thumbnail_url") or "",
            "specs": _tiki_specs(data),
            "brand": data.get("brand", {}).get("name", "Chính hãng"),
            "warranty": _tiki_warranty(data),
            "deliveryTag": "TikiNOW Giao 2h",
            "selected": True,
            "externalUrl": url,
        }

    async def _extract_mwg(self, url: str, platform: str, platform_name: str, badge_color: str, badge_bg: str) -> Dict[str, Any]:
        """Sản phẩm từ trang chi tiết: JSON-LD trước, rồi OpenGraph, cuối cùng giá trong HTML."""
        name, image, description, price, original, brand, specs = "", "", "", 0.0, 0.0, "Chính hãng", {}
        html = await self._fetch_html(url)
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
        return self._link_product(
            url, name or self._slug_to_title(url, platform_name), platform, platform_name, badge_color, badge_bg,
            id=f"{platform}-{_url_hash(url, 1000000)}", categoryName=platform_name, aiMatchScore=95,
            price=price, original=original, rating=4.8, image=image, specs=specs or description, brand=brand,
            sku=f"{platform.upper()}-{_url_hash(url, 10000)}",
            warranty="Bảo hành 12 tháng tại hệ thống", deliveryTag="Sẵn hàng tại siêu thị",
        )

    async def _extract_generic(self, url: str, platform="all", platform_name="Website",
                               badge_color=GENERIC_BADGE[0], badge_bg=GENERIC_BADGE[1]) -> Dict[str, Any]:
        """Sản phẩm từ trang bất kỳ qua OpenGraph và thẻ giá product:price:amount."""
        name, image, description, price = "", "", "", 0.0
        html = await self._fetch_html(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            name, image, description = _page_meta(soup)
            og_price = soup.find("meta", property="product:price:amount")
            try:
                price = float(og_price["content"]) if og_price and og_price.get("content") else 0.0
            except ValueError:
                price = 0.0
        return self._link_product(
            url, name or self._slug_to_title(url, platform_name), platform, platform_name, badge_color, badge_bg,
            id=f"parsed-{_url_hash(url, 1000000)}", categoryName="Sản phẩm liên kết", aiMatchScore=90,
            price=price, rating=5.0, image=image, specs=description, brand="Chính hãng",
            sku=f"URL-{_url_hash(url, 10000)}", warranty="Theo chính sách gian hàng", deliveryTag="Tiêu chuẩn",
        )

    @staticmethod
    def _link_product(url, name, platform, platform_name, badge_color, badge_bg, *, price, **fields) -> Dict[str, Any]:
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
            "rating": fields.pop("rating"),
            "reviewsCount": "Chính hãng",
            "sku": fields.pop("sku"),
            "image": fields.pop("image"),
            "specs": fields.pop("specs"),
            "brand": fields.pop("brand"),
            "warranty": fields.pop("warranty"),
            "deliveryTag": fields.pop("deliveryTag"),
            "selected": True,
            "externalUrl": url,
        }

    def _slug_to_title(self, url: str, fallback_prefix: str) -> str:
        """Trích xuất tên sản phẩm dễ đọc từ URL slug."""
        match = re.search(r'https?://[^/]+/([^/?#]+)', url)
        if match:
            raw_slug = match.group(1).replace(".html", "")
            raw_slug = urllib.parse.unquote(raw_slug)
            raw_slug = re.sub(r'-i\.\d+\.\d+$', '', raw_slug)
            raw_slug = re.sub(r'-i\d+$', '', raw_slug)
            raw_slug = re.sub(r'-p\d+$', '', raw_slug)
            clean = raw_slug.replace("-", " ").strip()
            if clean and clean.lower() not in ["product", "products", "item"]:
                return clean.capitalize()
        return f"Sản phẩm từ {fallback_prefix}"

    def _generate_ai_summary(self, product: Dict[str, Any]) -> str:
        """Sinh đánh giá và tóm tắt thẩm định AI súc tích cho sản phẩm."""
        name = product.get("name", "")
        p_name = product.get("platformName", "")
        price = product.get("currentPrice", 0)
        orig_price = product.get("originalPrice", price)
        discount = product.get("discountPercent", 0)

        parts = [f"Thẩm định liên kết từ **{p_name}**."]
        if discount > 0 and orig_price > price:
            savings = orig_price - price
            parts.append(f"Đang có ưu đãi giảm {discount}% (tiết kiệm {savings:,.0f} đ).")
        elif price > 0:
            parts.append(f"Mức giá niêm yết hiện tại là {price:,.0f} đ.")

        rating = product.get("rating", 5.0)
        reviews = product.get("reviewsCount", "")
        parts.append(f"Độ uy tín: {rating}/5.0 ({reviews}).")

        warranty = product.get("warranty", "")
        if warranty:
            parts.append(f"Bảo hành: {warranty}.")

        return " ".join(parts)
