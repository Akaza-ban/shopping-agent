"""Tool đọc sản phẩm từ link người dùng dán vào:

    nhận diện sàn -> đọc trang (integrations/platforms/link_reader.py) -> phân loại ngành hàng
    -> làm sạch + kiểm định giá -> lưu kho RAG để lần sau tìm được.

Giá không hợp lệ -> trả sản phẩm với priceUnavailable=True (không lưu kho).
"""
import asyncio
import logging
from typing import Any, Dict, Optional

from integrations.platforms import display_names, platform_for_url
from integrations.platforms import link_reader
from integrations.platforms.errors import crawling
from services.catalog.categories import categorize
from services.catalog.category_resolver import category_resolver
from services.catalog.data_processor import data_processor
from services.pricing import guardrails as price_guardrails
from shared.exceptions import InvalidInputError

from .base import BaseTool

logger = logging.getLogger("url_extractor")

# Các sàn đã bỏ vì chặn bot, không đọc được dữ liệu tin cậy
UNSUPPORTED_SITES = {"shopee.vn": "Shopee", "shp.ee": "Shopee", "lazada.vn": "Lazada"}


def unsupported_site(url: str) -> Optional[str]:
    """Tên sàn nếu link thuộc sàn không hỗ trợ, ngược lại None."""
    url_lower = (url or "").lower()
    return next((name for domain, name in UNSUPPORTED_SITES.items() if domain in url_lower), None)


def _ai_summary(product: Dict[str, Any]) -> str:
    """Tóm tắt thẩm định ngắn: sàn, ưu đãi / giá niêm yết, đánh giá, bảo hành."""
    price = product.get("currentPrice", 0)
    orig_price = product.get("originalPrice", price)
    discount = product.get("discountPercent", 0)

    parts = [f"Thẩm định liên kết từ **{product.get('platformName', '')}**."]
    if discount > 0 and orig_price > price:
        parts.append(f"Đang có ưu đãi giảm {discount}% (tiết kiệm {orig_price - price:,.0f} đ).")
    elif price > 0:
        parts.append(f"Mức giá niêm yết hiện tại là {price:,.0f} đ.")
    parts.append(f"Độ uy tín: {product.get('rating', 5.0)}/5.0 ({product.get('reviewsCount', '')}).")
    if product.get("warranty"):
        parts.append(f"Bảo hành: {product['warranty']}.")
    return " ".join(parts)


class UrlExtractorTool(BaseTool):
    name = "url_extractor"
    description = f"Trích xuất và thẩm định thông tin sản phẩm thực tế từ đường dẫn link (URL) {display_names()}"

    async def run(self, url: str) -> Dict[str, Any]:
        url = (url or "").strip()
        if not url:
            raise InvalidInputError("URL không được để trống")
        site = unsupported_site(url)
        if site:
            raise InvalidInputError(f"Chưa hỗ trợ đọc link {site}")

        item = await self._read_link(url)
        await self._apply_category(item)

        processed = data_processor.process_product(item)
        verdict = price_guardrails.check_price((processed or item).get("currentPrice"), categorize(processed or item))
        if not processed or not verdict.ok:
            item = processed or item
            item.update(currentPrice=0.0, originalPrice=0.0, priceUnavailable=True)
            item["aiSummary"] = _ai_summary(item)
            logger.warning(f"[UrlExtractor] Không lấy được giá hợp lệ cho {url}: {verdict.reason}")
            return item

        processed["aiSummary"] = _ai_summary(processed)
        await self._store_in_rag(processed)
        return processed

    @staticmethod
    async def _read_link(url: str) -> Dict[str, Any]:
        """Dữ liệu thô của sản phẩm theo sàn của link; trang đổi cấu trúc / dữ liệu hỏng -> CrawlerError."""
        platform = platform_for_url(url)
        with crawling(platform.name if platform else url):
            if platform is None:
                return await link_reader.read_generic(url)
            if platform.id == "tiki":
                return await link_reader.read_tiki(url)
            item = await link_reader.read_mwg(url, platform=platform.id, platform_name=platform.name,
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
        from services.rag import rag_service  # rag_service tự bỏ qua lỗi ChromaDB / embedding
        stored = await asyncio.to_thread(rag_service.upsert_products, [product])
        if stored:
            logger.info(f"[UrlExtractor] Đã tự động lưu sản phẩm '{product['name']}' vào ChromaDB.")
