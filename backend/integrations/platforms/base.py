"""Giao diện chung của một sàn (Strategy): tìm kiếm, đọc trang chi tiết, đọc giá hiện tại, phân loại ngành hàng."""

from typing import Any
from urllib.parse import urlparse

from core.state import UniversalSearchCriteria
from integrations.platforms.common import PAGE_HEADERS, fetch_page_price, parse_jsonld_detail


class PlatformAdapter:
    id: str = ""
    name: str = ""
    type: str = "Chuỗi bán lẻ"
    hosts: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    badge_color: str = "#1a94ff"
    badge_bg: str = "rgba(26, 148, 255, 0.15)"
    warranty: str = ""
    delivery_tag: str = ""

    def owns_url(self, url: str | None) -> bool:
        host = (urlparse(url or "").hostname or "").lower()
        return any(host == h or host.endswith("." + h) for h in self.hosts)

    def page_url(self, product: dict[str, Any]) -> str | None:
        """Link trang sản phẩm nếu là http(s) và thuộc chính sàn này; None nếu không (không gọi tới host lạ)."""
        url = product.get("externalUrl") or ""
        if urlparse(url).scheme not in ("http", "https") or not self.owns_url(url):
            return None
        return url

    def mentioned_in(self, text: str) -> bool:
        lower = (text or "").lower()
        return any(a in lower for a in self.aliases)

    async def search(
        self,
        keyword: str,
        criteria: UniversalSearchCriteria | None,
        limit: int,
        notes: list[str],
        user_query: str = "",
    ) -> list[dict[str, Any]]:
        """Sản phẩm đã lọc giá / phụ kiện, ở dạng dict chung của hệ thống. `user_query`: câu gốc của người dùng."""
        raise NotImplementedError

    def product_base(self, criteria: UniversalSearchCriteria | None) -> dict[str, Any]:
        """Các trường giống nhau của mọi sản phẩm thuộc sàn này."""
        return {
            "categoryName": criteria.category_name if criteria else "Sản phẩm",
            "platform": self.id,
            "platformName": self.name,
            "platformBadgeColor": self.badge_color,
            "platformBadgeBg": self.badge_bg,
            "warranty": self.warranty,
            "deliveryTag": self.delivery_tag,
            "selected": False,
        }

    def detail_cache_key(self, product: dict[str, Any]) -> str | None:
        url = product.get("externalUrl") or ""
        return url if url.startswith("http") else None

    async def fetch_detail(self, client, product: dict[str, Any]) -> dict[str, Any] | None:
        """{"specs", "warranty", "returnPolicy", ...} từ trang chi tiết; None nếu sàn không hỗ trợ / không đọc được."""
        return None

    async def fetch_price(self, client, product: dict[str, Any]) -> dict[str, Any] | None:
        """{"currentPrice", "originalPrice", "inStock"} đọc trực tiếp từ sàn (dùng cho theo dõi giá)."""
        return None

    # ngành hàng, link
    def category_source(self, product: dict[str, Any]) -> tuple[str, str] | None:
        """(khóa, mô tả) danh mục của sản phẩm theo chính sàn này; CategoryResolver quy đổi sang ngành hàng chuẩn."""
        return None

    def clean_link_name(self, name: str) -> str:
        """Chuẩn hóa tên đọc được khi người dùng dán link (VD bỏ hậu tố tiếp thị)."""
        return name


class JsonLdDetailAdapter(PlatformAdapter):
    """Sàn có trang chi tiết mang khối JSON-LD Product (FPT Shop, CellphoneS): thông số, điểm đánh giá, giá, tình trạng."""

    async def fetch_detail(self, client, product):
        url = self.page_url(product)
        if not url:
            return None
        resp = await client.get(url, headers=PAGE_HEADERS)
        return parse_jsonld_detail(resp.text) if resp.status_code == 200 else None

    async def fetch_price(self, client, product):
        url = self.page_url(product)
        return await fetch_page_price(client, url) if url else None
