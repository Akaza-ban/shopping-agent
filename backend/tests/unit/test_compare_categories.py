"""
So sánh sản phẩm khác ngành hàng (VD điện thoại với laptop): công cụ không lập bảng, không chấm "tốt nhất",
trả về lời giải thích; cùng ngành hàng thì so sánh bình thường. Ngành hàng lấy từ bảng quy đổi danh mục.
"""

import asyncio
import sys

from core.agents.comparison_agent import ComparisonAgent
from core.state import AgentState, ProductItemModel
from core.tools.spec_comparator import SpecComparatorTool, mixed_categories

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def _product(pid, url, price, category="all"):
    return {
        "id": pid,
        "name": pid,
        "platform": "tgdd",
        "platformName": "Thế Giới Di Động",
        "currentPrice": price,
        "originalPrice": price,
        "aiMatchScore": 90,
        "rating": 4.8,
        "externalUrl": url,
        "category": category,
    }


PHONE = _product("iphone-16", "https://www.thegioididong.com/dtdd/iphone-16", 21_990_000)
PHONE_2 = _product("galaxy-s25", "https://www.thegioididong.com/dtdd/samsung-galaxy-s25", 19_990_000)
LAPTOP = _product("dell-xps", "https://fptshop.com.vn/may-tinh-xach-tay/dell-xps-13", 35_990_000)
CASE = _product("op-lung", "https://www.thegioididong.com/op-lung-iphone/op-lung-16", 300_000)


def test_mixed_categories_detection():
    assert mixed_categories([PHONE, LAPTOP]) == ["phones", "laptops"]
    assert mixed_categories([PHONE, PHONE_2]) == []
    assert mixed_categories([PHONE, CASE]) == []  # phụ kiện / chưa rõ ngành hàng không tính là khác loại
    # Tiki: ngành hàng theo mã danh mục lưu trong sản phẩm
    tiki_laptop = {
        **_product("tiki-1", "https://tiki.vn/laptop-x.html", 20_000_000),
        "platform": "tiki",
        "sourceCategoryPath": "1/2/1846/8095",
    }
    assert mixed_categories([PHONE, tiki_laptop]) == ["phones", "laptops"]


def test_tool_refuses_cross_category_comparison():
    res = asyncio.run(SpecComparatorTool().run([PHONE, LAPTOP]))
    assert res["status"] == "mixed_categories" and res["table"] is None and res["markdown"] == ""
    assert "Không so sánh trực tiếp được" in res["recommendation"]
    assert "Phù hợp nhất" not in res["recommendation"] and "Rẻ nhất" not in res["recommendation"]

    same = asyncio.run(SpecComparatorTool().run([PHONE, PHONE_2]))
    assert same["table"]["rows"] and "Phù hợp nhất" in same["recommendation"]


def test_agent_passes_note_to_advisor():
    state = AgentState(
        session_id="s",
        user_query="so sánh iPhone 16 với laptop Dell",
        found_products=[ProductItemModel(**PHONE), ProductItemModel(**LAPTOP)],
    )
    state = asyncio.run(ComparisonAgent().compare(state))
    assert state.comparison_table is None and state.comparison_markdown == ""
    assert any("KHÁC LOẠI" in n for n in state.search_notes)


def test_router_null_fields_do_not_break_criteria():
    """LLM router trả null cho trường không áp dụng -> dùng mặc định, không rơi xuống đường dự phòng bằng từ khóa."""
    from core.state import UniversalSearchCriteria

    c = UniversalSearchCriteria(is_accessory=None, cleaned_query=None, attributes=None)
    assert (c.is_accessory, c.cleaned_query, c.attributes) == (False, "", {})


def test_same_category_but_different_platform_category_asks_llm(monkeypatch, _offline_category_resolver):
    """Tủ lạnh và máy giặt cùng ngành "gia dụng" nhưng khác danh mục của sàn -> hỏi LLM; cùng danh mục -> không hỏi."""
    fridge = _product("tu-lanh", "https://www.dienmayxanh.com/tu-lanh/toshiba-460", 14_000_000)
    washer = _product("may-giat", "https://www.dienmayxanh.com/may-giat/casper-9kg", 5_890_000)
    washer_2 = _product("may-giat-2", "https://www.dienmayxanh.com/may-giat/aqua-8kg", 5_350_000)
    _offline_category_resolver.remember({"dmx:tu-lanh": ("home_appliances", False)})  # dmx:may-giat có sẵn
    asked = []

    async def fake_same_kind(products):
        asked.append([p["id"] for p in products])
        return False

    monkeypatch.setattr(_offline_category_resolver, "same_kind", fake_same_kind)
    blocked = asyncio.run(
        ComparisonAgent().compare(
            AgentState(
                session_id="s",
                user_query="so sánh",
                found_products=[ProductItemModel(**fridge), ProductItemModel(**washer)],
            )
        )
    )
    assert blocked.comparison_table is None and asked == [["tu-lanh", "may-giat"]]

    same = asyncio.run(
        ComparisonAgent().compare(
            AgentState(
                session_id="s",
                user_query="so sánh",
                found_products=[ProductItemModel(**washer), ProductItemModel(**washer_2)],
            )
        )
    )
    assert same.comparison_table is not None and len(asked) == 1  # cùng danh mục dmx:may-giat: không hỏi LLM
