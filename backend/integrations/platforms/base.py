"""Giao diện chung của một sàn (Strategy): tìm kiếm, đọc trang chi tiết, đọc giá hiện tại, phân loại ngành hàng."""
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from core.state import UniversalSearchCriteria
from integrations.platforms.common import PAGE_HEADERS, fetch_page_price, parse_jsonld_detail


class PlatformAdapter:
    id: str = ""
    name: str = ""
    type: str = "Chuỗi bán lẻ"  
    hosts: Tuple[str, ...] = ()  
    aliases: Tuple[str, ...] = ()  
    badge_color: str = "#1a94ff"
    badge_bg: str = "rgba(26, 148, 255, 0.15)"
    warranty: str = ""
    delivery_tag: str = ""

    def owns_url(self, url: Optional[str]) -> bool:
        host = urlparse(url or "").netloc.lower()
        return any(host == h or host.endswith("." + h) for h in self.hosts)

    def mentioned_in(self, text: str) -> bool:
        lower = (text or "").lower()
        return any(a in lower for a in self.aliases)

    async def search(
        self,
        keyword: str,
        criteria: Optional[UniversalSearchCriteria],
        limit: int,
        notes: List[str],
        user_query: str = "",
    ) -> List[Dict[str, Any]]:
        """Sản phẩm đã lọc giá / phụ kiện, ở dạng dict chung của hệ thống. `user_query`: câu gốc của người dùng."""
        raise NotImplementedError

    def product_base(self, criteria: Optional[UniversalSearchCriteria]) -> Dict[str, Any]:
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

    def detail_cache_key(self, product: Dict[str, Any]) -> Optional[str]:
        url = product.get("externalUrl") or ""
        return url if url.startswith("http") else None

    async def fetch_detail(self, client, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """{"specs", "warranty", "returnPolicy", ...} từ trang chi tiết; None nếu sàn không hỗ trợ / không đọc được."""
        return None

    async def fetch_price(self, client, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """{"currentPrice", "originalPrice", "inStock"} đọc trực tiếp từ sàn (dùng cho theo dõi giá)."""
        return None

    # ngành hàng, link
    def category_source(self, product: Dict[str, Any]) -> Optional[Tuple[str, str]]:
        """(khóa, mô tả) danh mục của sản phẩm theo chính sàn này; CategoryResolver quy đổi sang ngành hàng chuẩn."""
        return None

    def clean_link_name(self, name: str) -> str:
        """Chuẩn hóa tên đọc được khi người dùng dán link (VD bỏ hậu tố tiếp thị)."""
        return name


class JsonLdDetailAdapter(PlatformAdapter):
    """Sàn có trang chi tiết mang khối JSON-LD Product (FPT Shop, CellphoneS): thông số, điểm đánh giá, giá, tình trạng."""

    async def fetch_detail(self, client, product):
        url = product.get("externalUrl") or ""
        if not url.startswith("http"):
            return None
        resp = await client.get(url, headers=PAGE_HEADERS)
        return parse_jsonld_detail(resp.text) if resp.status_code == 200 else None

    async def fetch_price(self, client, product):
        url = product.get("externalUrl") or ""
        return await fetch_page_price(client, url) if url.startswith("http") else None
