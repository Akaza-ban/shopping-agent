"""
Kiểm thử registry các sàn (services/catalog/platforms):
- Mỗi sàn có đủ thông tin hiển thị, nhận đúng link của mình.
- Tên sàn trong câu hỏi / tiêu chí -> đúng sàn; tên lạ (Shopee) không khớp sàn nào.
- categorize, màu nhãn, nhận diện sàn của router đều lấy từ registry.
- EcomSearchTool chỉ gọi các sàn được yêu cầu và đan xen kết quả theo thứ tự registry.
"""
import asyncio
import sys

from core.tools.ecom_search import EcomSearchTool
from services.catalog.categories import categorize
from integrations.platforms import (
    PlatformAdapter, all_platforms, get_platform, platform_for_url, platform_mentioned, resolve_targets,
)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def test_every_platform_is_complete_and_owns_its_links():
    ids = [p.id for p in all_platforms()]
    assert ids == ["tgdd", "dmx", "tiki", "fpt-shop", "cellphones"]
    interface = [n for n, v in vars(PlatformAdapter).items() if callable(v) and not n.startswith("_")]
    assert {"search", "detail_cache_key", "fetch_detail", "fetch_price", "category_source"} <= set(interface)
    for p in all_platforms():
        assert p.name and p.hosts and p.aliases and p.badge_color.startswith("#")
        assert all(callable(getattr(p, n, None)) for n in interface), p.id  # đủ phương thức của giao diện chung
        assert platform_for_url(f"https://{p.hosts[0]}/san-pham/x") is p
        assert platform_for_url(f"https://www.{p.hosts[0]}/x") is p
    assert platform_for_url("https://shopee.vn/x") is None
    assert platform_for_url("https://evil-tiki.vn.example.com/x") is None


def test_names_resolve_to_platforms():
    assert [p.id for p in resolve_targets(["all"])] == [p.id for p in all_platforms()]
    assert [p.id for p in resolve_targets(["thegioididong", "fpt"])] == ["tgdd", "fpt-shop"]
    assert resolve_targets(["shopee"]) == []
    assert platform_mentioned("có bán ở điện máy xanh không").id == "dmx"
    assert platform_mentioned("giá trên CellphoneS").id == "cellphones"
    assert platform_mentioned("laptop gaming dưới 25 triệu") is None


def test_categorize_and_badges_come_from_platforms(_offline_category_resolver):
    _offline_category_resolver.remember({"tgdd:dtdd": ("phones", False), "fpt-shop:/may-tinh-xach-tay": ("laptops", False),
                                         "cellphones:Âm thanh/Tai nghe": ("audio", False)})
    assert categorize({"externalUrl": "https://www.thegioididong.com/dtdd/iphone-16"}) == "phones"
    assert categorize({"externalUrl": "https://fptshop.com.vn/may-tinh-xach-tay/asus"}) == "laptops"
    assert categorize({"platform": "cellphones", "sourceCategoryPath": "cellphones:Âm thanh/Tai nghe"}) == "audio"
    assert categorize({"externalUrl": "https://example.com/x"}) == "other"

    from database.models import ProductModel
    from database.repositories.product_repo import product_model_to_dict
    product = product_model_to_dict(ProductModel(id="cps-1", name="x", platform="cellphones", current_price=1, original_price=1, rating=0.0))
    assert product["platformBadgeColor"] == get_platform("cellphones").badge_color


def test_router_fallback_detects_platform_from_registry():
    """Đường dự phòng bằng từ khóa khi không gọi được LLM."""
    from core.agents.orchestrator import OrchestratorAgent
    from core.state import AgentState
    agent = OrchestratorAgent.__new__(OrchestratorAgent)
    routed = {q: agent._fallback_route(AgentState(session_id="s", user_query=q)).criteria
              for q in ("tìm mua iphone 16 ở fpt shop", "tìm mua laptop trên shopee", "tìm mua máy giặt")}
    assert routed["tìm mua iphone 16 ở fpt shop"].target_platforms == ["fpt-shop"]
    assert routed["tìm mua laptop trên shopee"].target_platforms == ["shopee"]  # sàn không hỗ trợ vẫn được ghi lại
    assert routed["tìm mua máy giặt"].target_platforms == ["all"]


class _Fake(PlatformAdapter):
    def __init__(self, pid, items):
        self.id, self.name, self.items, self.calls = pid, pid.upper(), items, 0

    async def search(self, keyword, criteria, limit, notes, user_query=""):
        self.calls += 1
        return [{"id": f"{self.id}-{i}", "name": f"Laptop {self.id} {i}", "platform": self.id, "platformName": self.name,
                 "currentPrice": 20_000_000 + i, "originalPrice": 20_000_000 + i,
                 "externalUrl": f"https://{self.id}.vn/{i}"} for i in range(self.items)]


def test_crawl_only_calls_requested_platforms_and_interleaves():
    a, b, c = _Fake("tgdd", 2), _Fake("tiki", 2), _Fake("cellphones", 0)
    tool = EcomSearchTool(platforms=[a, b, c])
    products, counts = asyncio.run(tool._crawl("laptop", None, "tiki", 4, []))
    assert (a.calls, b.calls, c.calls) == (0, 1, 0)
    assert counts == {"tiki": 2}

    products, counts = asyncio.run(tool._crawl("laptop", None, "all", 4, []))
    assert counts == {"tgdd": 2, "tiki": 2, "cellphones": 0}
    assert [p["platform"] for p in products] == ["tgdd", "tiki", "tgdd", "tiki"]  # đan xen theo thứ tự registry
