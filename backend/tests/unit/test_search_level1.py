"""
Kiểm thử Mức 1 của luồng tư vấn mua sắm:
- Parser TGDĐ/ĐMX theo giao diện Next.js 2026 (fixture HTML thật, chạy offline).
- Lọc phụ kiện theo bảng quy đổi danh mục (cờ is_accessory).
- Ghi chú thuộc tính chưa xác minh & nới lỏng tiêu chí khi không có kết quả.
- Advisor không được dùng sản phẩm cũ / bịa dữ liệu khi lượt tìm kiếm rỗng.
"""
import asyncio
import os
import re
import pytest

from core.tools.ecom_search import EcomSearchTool
from integrations.platforms.common import query_candidates
from integrations.platforms.mwg import DMX, TGDD
from core.state import AgentState, UniversalSearchCriteria
from core.flows.search_flow import relaxation_steps
from core.tools import attribute_match
from core.agents import advisor_context, advisor_fallback
from services.catalog.data_processor import data_processor

FIXTURES = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fixtures")


def _read(name: str) -> str:
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


def test_parse_tgdd_listing_2026():
    # Fixture gồm 1 banner (không có giá, phải bị bỏ qua) + 3 thẻ sản phẩm thật
    items = TGDD.parse_listing(_read("tgdd_laptop_gaming_2026.html"))
    assert len(items) == 3
    assert all("Banner" not in it["name"] for it in items)
    first = items[0]
    assert "VICTUS" in first["name"]
    assert first["currentPrice"] == 27_990_000
    assert first["originalPrice"] == 32_490_000
    assert first["discountPercent"] == 13
    assert first["href"].startswith("https://www.thegioididong.com/laptop/")
    assert "RAM 16 GB" in first["specs"]
    assert first["image"].startswith("https://")
    for it in items:
        assert it["currentPrice"] > 1_000_000  # không nhầm "Quà 100.000₫" thành giá bán


def test_parse_dmx_listing_2026():
    # Fixture gồm 1 banner + 2 thẻ máy giặt thật
    items = DMX.parse_listing(_read("dmx_may_giat_2026.html"))
    assert len(items) == 2
    assert all(it["href"].startswith("https://www.dienmayxanh.com/may-giat/") for it in items)
    assert all(it["originalPrice"] >= it["currentPrice"] > 0 for it in items)


def test_mwg_query_candidates_drop_attributes():
    c = UniversalSearchCriteria(target_entity="laptop", attributes={"gpu": "RTX 4070"}, cleaned_query="laptop gaming RTX 4070")
    cands = query_candidates("laptop gaming RTX 4070", c)
    assert cands[0] == "laptop gaming RTX 4070"
    assert "laptop gaming" in cands
    assert cands[-1] == "laptop"


def test_accessories_filtered_by_learned_mapping(_offline_category_resolver):
    """Phụ kiện bị bỏ theo cờ is_accessory của bảng quy đổi, trừ khi người dùng chủ đích tìm phụ kiện."""
    _offline_category_resolver.remember({"tiki:1/2/1846/8095": ("laptops", False), "tiki:1/2/1846/8129": ("other", True)})
    laptop = {"id": "tiki-1", "name": "Laptop", "platform": "tiki", "sourceCategoryPath": "1/2/1846/8095"}
    charger = {"id": "tiki-2", "name": "Adapter Sạc Laptop", "platform": "tiki", "sourceCategoryPath": "1/2/1846/8129"}
    unknown = {"id": "tiki-3", "name": "Thứ chưa rõ", "platform": "tiki", "sourceCategoryPath": "1/2/77777"}
    tool = EcomSearchTool(platforms=[])

    lists = {"tiki": [laptop, charger, unknown]}
    asyncio.run(tool._apply_categories(lists, UniversalSearchCriteria(category="laptops", is_accessory=False)))
    assert [p["id"] for p in lists["tiki"]] == ["tiki-1", "tiki-3"]  # chưa rõ: để bộ lọc ngữ nghĩa quyết định
    assert lists["tiki"][0]["category"] == "laptops"

    lists = {"tiki": [laptop, charger]}
    asyncio.run(tool._apply_categories(lists, UniversalSearchCriteria(category="laptops", is_accessory=True)))
    assert [p["id"] for p in lists["tiki"]] == ["tiki-1", "tiki-2"]


def test_attribute_match_orders_verified_first_and_notes():
    c = UniversalSearchCriteria(attributes={"gpu": "RTX 4070"})
    products = [
        {"name": "Laptop A RTX 4060", "specs": {}},
        {"name": "Laptop B", "specs": {"GPU": "NVIDIA GeForce RTX4070 8GB"}},
    ]
    notes = []
    result = attribute_match.annotate(products, c, notes)
    assert result[0]["name"] == "Laptop B"
    assert len(notes) == 1 and "1/2" in notes[0]

    notes = []
    attribute_match.annotate([{"name": "Laptop C", "specs": {}}], c, notes)
    assert "KHÔNG sản phẩm nào" in notes[0]


def test_relaxation_steps_are_cumulative():
    c = UniversalSearchCriteria(
        target_entity="laptop", max_price=30_000_000, brands=["ASUS"],
        attributes={"gpu": "RTX 4070"}, cleaned_query="laptop gaming ASUS RTX 4070"
    )
    steps = relaxation_steps(c)
    assert len(steps) == 3
    first, desc1 = steps[0]
    assert first.attributes == {} and "RTX 4070" not in first.cleaned_query and first.max_price == 30_000_000
    second, desc2 = steps[1]
    assert second.max_price == 36_000_000 and "ngân sách" in desc2
    third, _ = steps[2]
    assert third.brands == [] and "ASUS" not in third.cleaned_query and third.cleaned_query


def test_advisor_reports_no_products_instead_of_reusing_old_ones(monkeypatch):
    from memory.session_manager import session_memory
    # Giả lập phiên có sản phẩm từ lượt trước
    monkeypatch.setattr(session_memory, "get_last_products", lambda sid: [{
        "id": "old-1", "name": "Sản phẩm lượt trước", "platform": "tiki", "platformName": "Tiki",
        "originalPrice": 1, "currentPrice": 1
    }])
    state = AgentState(session_id="s-empty", user_query="laptop RTX 5090 dưới 10 triệu", intent="search_products")
    ctx = advisor_context.build_context(state)
    assert "KHÔNG TÌM THẤY SẢN PHẨM" in ctx["products_context"]
    assert "Sản phẩm lượt trước" not in ctx["products_context"]

    fallback = advisor_fallback.build_fallback(ctx, None, intent="search_products")
    assert "Chưa tìm thấy sản phẩm" in fallback
    assert not re.search(r"\d[\d.,]*\s*(?:đ|₫)", fallback)  # không có con số giá nào


def test_advisor_followup_question_still_reuses_previous_products(monkeypatch):
    from memory.session_manager import session_memory
    monkeypatch.setattr(session_memory, "get_last_products", lambda sid: [{
        "id": "old-1", "name": "Sản phẩm lượt trước", "platform": "tiki", "platformName": "Tiki",
        "originalPrice": 1, "currentPrice": 1
    }])
    state = AgentState(session_id="s-follow", user_query="con thứ nhất pin mấy tiếng?", intent="general_advice")
    ctx = advisor_context.build_context(state)
    assert "Sản phẩm lượt trước" in ctx["products_context"]


def test_missing_rating_is_not_five_stars():
    rating, reviews = data_processor.normalize_rating_and_reviews(None, None)
    assert rating == 0.0
    assert reviews == "Chưa có đánh giá"
    assert data_processor.normalize_rating_and_reviews(4.7, "10 đánh giá")[0] == 4.7


@pytest.mark.skipif(not os.getenv("RUN_LIVE_TESTS"), reason="Đặt RUN_LIVE_TESTS=1 để chạy test gọi trang thật")
@pytest.mark.asyncio
async def test_live_tgdd_layout_still_parsable():
    """Cảnh báo sớm khi TGDĐ đổi giao diện: trang danh mục laptop gaming phải đọc được sản phẩm."""
    c = UniversalSearchCriteria(category="laptops", target_entity="laptop", cleaned_query="laptop gaming")
    res = await TGDD.search("laptop gaming", c, 5, [])
    assert len(res) >= 3, "Không đọc được sản phẩm TGDĐ — có thể trang đã đổi giao diện"
