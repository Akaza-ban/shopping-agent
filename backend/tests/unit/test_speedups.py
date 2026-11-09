"""Tăng tốc lượt tìm kiếm: bớt các lần gọi LLM / chờ chạy nối tiếp (chạy offline)."""

import asyncio
import json
from types import SimpleNamespace

from core.agents import comparison_agent as comparison_module
from core.agents.comparison_agent import ComparisonAgent
from core.state import AgentState, ProductItemModel, UniversalSearchCriteria
from core.tools import search_sources
from core.tools.search_sources import SearchRequest
from services.catalog import spec_fit
from shared.exceptions import LLMError


def _product(pid, platform="tgdd"):
    return {
        "id": pid,
        "name": f"Laptop {pid}",
        "platform": platform,
        "platformName": platform,
        "currentPrice": 20e6,
        "originalPrice": 20e6,
        "specs": {"RAM": "16 GB"},
    }


# ---------------------------------------------------------------- mục 1: so sánh kết quả tìm kiếm
def _compare(monkeypatch, trusted):
    calls = []

    async def same_kind(products):
        calls.append(len(products))
        return True

    async def resolve(products):
        return None

    monkeypatch.setattr(comparison_module.category_resolver, "same_kind", same_kind)
    monkeypatch.setattr(comparison_module.category_resolver, "resolve", resolve)
    monkeypatch.setattr(comparison_module.category_resolver, "source_of", lambda p: None)
    state = AgentState(
        session_id="cmp",
        user_query="x",
        found_products=[ProductItemModel(**_product("a")), ProductItemModel(**_product("b"))],
    )
    state = asyncio.run(ComparisonAgent().compare(state, trusted_same_kind=trusted))
    return state, calls


def test_search_results_skip_same_kind_llm(monkeypatch):
    state, calls = _compare(monkeypatch, trusted=True)
    assert calls == [] and state.comparison_table


def test_saved_products_still_ask_same_kind(monkeypatch):
    _, calls = _compare(monkeypatch, trusted=False)
    assert calls == [2]


# ---------------------------------------------------------------- mục 2 + 3: đọc chi tiết rồi MỘT lần LLM lọc + chấm
class FakeLLM:
    def __init__(self, reply):
        self.reply, self.calls = reply, 0

    async def ainvoke(self, messages):
        self.calls += 1
        if isinstance(self.reply, Exception):
            raise self.reply
        return SimpleNamespace(content=json.dumps(self.reply, ensure_ascii=False))


GAMING = UniversalSearchCriteria(category="laptops", usage_purpose="chơi game", max_price=25e6)


def _use(monkeypatch, llm):
    spec_fit._cache.clear()
    monkeypatch.setattr(spec_fit, "get_chat_model", lambda **_: llm)


def test_screen_reads_details_then_one_llm_call_filters_and_scores(monkeypatch):
    seen = []

    async def fake_enrich(products, max_items=10, budget_seconds=None):
        seen.append([p["id"] for p in products])
        return [{**p, "detailFetched": True} for p in products]

    llm = FakeLLM(
        {
            "products": [
                {"id": "a", "keep": True, "fit": 9, "reason": "RTX 4060 chơi game tốt", "mismatch": {}},
                {"id": "case", "keep": False},
                {"id": "b", "keep": True, "fit": None, "reason": "", "mismatch": {}},
            ]
        }
    )
    _use(monkeypatch, llm)
    monkeypatch.setattr(search_sources.product_enricher, "enrich", fake_enrich)
    s = SearchRequest(
        keyword="laptop gaming", criteria=GAMING, category="laptops", target_platform="all", limit=4, notes=[]
    )
    out = asyncio.run(search_sources.screen([_product("a"), _product("case"), _product("b")], s))

    assert seen == [["a", "case", "b"]]  # đọc chi tiết cả danh sách trước khi lọc
    assert [p["id"] for p in out] == ["a", "b"] and all(p["detailFetched"] for p in out)
    assert out[0]["specFit"] == {"score": 0.9, "reason": "RTX 4060 chơi game tốt"} and "specFit" not in out[1]
    assert llm.calls == 1

    # Lượt sau trúng cache tìm kiếm: assess() dùng lại điểm vừa chấm, không gọi LLM nữa
    again = asyncio.run(spec_fit.assess([out[0]], GAMING))
    assert again[0]["specFit"]["score"] == 0.9 and llm.calls == 1


def test_screen_keeps_everything_when_llm_fails(monkeypatch):
    _use(monkeypatch, FakeLLM(LLMError("hết hạn mức")))
    items = [_product("a"), _product("b")]
    out = asyncio.run(spec_fit.screen(items, GAMING, "laptop gaming"))
    assert [p["id"] for p in out] == ["a", "b"] and not any("specFit" in p for p in out)


def test_screen_drops_products_the_llm_left_out(monkeypatch):
    _use(monkeypatch, FakeLLM({"products": [{"id": "a", "keep": True}]}))
    out = asyncio.run(spec_fit.screen([_product("a"), _product("b")], GAMING, "laptop"))
    assert [p["id"] for p in out] == ["a"]


# ---------------------------------------------------------------- đường cào trực tiếp
class FakePlatform:
    def __init__(self, pid, delay, items=1):
        self.id, self.name, self.delay, self.items = pid, pid.upper(), delay, items

    async def search(self, query, criteria, cap, notes, user_query=""):
        await asyncio.sleep(self.delay)
        notes.append(f"ghi chú {self.id}")
        return [{**_product(f"{self.id}-{i}", self.id)} for i in range(self.items)]


def _crawl_platforms(targets, budget):
    from core.tools.ecom_search import EcomSearchTool

    notes: list[str] = []
    per = asyncio.run(EcomSearchTool._search_platforms(targets, "laptop", None, 12, notes, "laptop", budget=budget))
    return per, notes


def test_slow_platform_does_not_hold_the_turn_and_is_stored_later(monkeypatch):
    from core.tools import ecom_search

    stored = []

    async def store(products):
        stored.extend(p["id"] for p in products)

    monkeypatch.setattr(ecom_search.search_sources, "store_in_rag", store)

    async def scenario():
        notes: list[str] = []
        per = await ecom_search.EcomSearchTool._search_platforms(
            [FakePlatform("tiki", 0.01), FakePlatform("dmx", 0.3)], "laptop", None, 12, notes, "laptop", budget=0.1
        )
        assert stored == []  # sàn chậm chưa xong lúc trả kết quả
        await asyncio.sleep(0.4)  # ...nhưng vẫn chạy tiếp ở nền rồi nạp vào kho RAG
        return per, notes

    per, notes = asyncio.run(scenario())
    assert list(per) == ["tiki"] and len(per["tiki"]) == 1
    assert "ghi chú tiki" in notes and "ghi chú dmx" not in notes
    assert any("DMX phản hồi chậm" in n for n in notes)
    assert stored == ["dmx-0"]


def test_keeps_waiting_past_budget_when_no_platform_has_results_yet():
    per, notes = _crawl_platforms([FakePlatform("tiki", 0.01, items=0), FakePlatform("dmx", 0.2)], budget=0.05)
    assert len(per["dmx"]) == 1 and not any("phản hồi chậm" in n for n in notes)


def test_all_fast_platforms_are_waited_for():
    per, notes = _crawl_platforms([FakePlatform("tiki", 0.01), FakePlatform("fpt", 0.02)], budget=1)
    assert set(per) == {"tiki", "fpt"} and not any("phản hồi chậm" in n for n in notes)


def test_shop_accessory_category_kept_when_it_would_remove_everything(monkeypatch):
    from core.tools import ecom_search

    async def resolve(items):
        return None

    accessory = SimpleNamespace(category="other", is_accessory=True, noun=None)
    main = SimpleNamespace(category="laptops", is_accessory=False, noun=None)
    monkeypatch.setattr(ecom_search.category_resolver, "resolve", resolve)
    crit = UniversalSearchCriteria(target_entity="bàn phím", is_accessory=False)
    tool = ecom_search.EcomSearchTool(platforms=[])

    # Mọi kết quả đều là "phụ kiện" theo danh mục sàn (VD bàn phím): giữ lại để LLM xét theo câu hỏi
    monkeypatch.setattr(ecom_search.category_resolver, "lookup", lambda p: accessory)
    per = {"tiki": [_product("kb1", "tiki")], "fpt-shop": [_product("kb2", "fpt-shop")]}
    asyncio.run(tool._apply_categories(per, crit))
    assert [p["id"] for p in per["tiki"] + per["fpt-shop"]] == ["kb1", "kb2"]

    # Có cả sản phẩm chính: vẫn bỏ phụ kiện ăn theo như cũ
    monkeypatch.setattr(ecom_search.category_resolver, "lookup", lambda p: main if p["id"] == "lap" else accessory)
    per = {"tiki": [_product("lap", "tiki"), _product("case", "tiki")]}
    asyncio.run(tool._apply_categories(per, crit))
    assert [p["id"] for p in per["tiki"]] == ["lap"]
