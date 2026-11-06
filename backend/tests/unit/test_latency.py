"""Các tối ưu độ trễ của một lượt tư vấn: model nhanh, giới hạn đọc trang chi tiết, RAG và cào chạy song song."""
import asyncio
import functools
import time

import pytest

import integrations.llm.client as config
from core.tools.ecom_search import EcomSearchTool
from core.tools.url_extractor import unsupported_site
from services.catalog.enricher import ProductEnricher
from integrations.platforms import PlatformAdapter, all_platforms


def run_async(test):
    @functools.wraps(test)
    def wrapper(*args, **kwargs):
        return asyncio.run(test(*args, **kwargs))
    return wrapper


@pytest.fixture
def llm_settings(monkeypatch):
    monkeypatch.setattr(config, "_reachability", {})
    monkeypatch.setattr(config, "is_reachable", lambda base_url: True)
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "openrouter")
    monkeypatch.setattr(config.settings, "OPENROUTER_API_KEY", "khoa-gia")
    monkeypatch.setattr(config.settings, "DEEPSEEK_API_KEY", "")
    monkeypatch.setattr(config.settings, "GROQ_API_KEY", "")
    monkeypatch.setattr(config.settings, "OPENROUTER_MODEL", "deepseek/deepseek-chat")
    monkeypatch.setattr(config.settings, "FAST_LLM_MODEL", "google/gemini-2.5-flash-lite")
    monkeypatch.setattr(config.settings, "FAST_LLM_PROVIDER", "")


def test_fast_model_comes_first_with_main_model_as_fallback(llm_settings):
    model = config.get_chat_model(fast=True)
    assert model.runnable.model_name == "google/gemini-2.5-flash-lite"
    assert [m.model_name for m in model.fallbacks] == ["deepseek/deepseek-chat"]


def test_main_model_is_used_when_fast_not_requested(llm_settings):
    assert config.get_chat_model().model_name == "deepseek/deepseek-chat"


def test_empty_fast_model_uses_main_model(llm_settings, monkeypatch):
    monkeypatch.setattr(config.settings, "FAST_LLM_MODEL", "")
    assert config.get_chat_model(fast=True).model_name == "deepseek/deepseek-chat"


def test_fast_provider_is_pinned_on_openrouter(llm_settings, monkeypatch):
    monkeypatch.setattr(config.settings, "FAST_LLM_PROVIDER", "Groq")
    model = config.get_chat_model(fast=True)
    assert model.runnable.extra_body == {"provider": {"order": ["Groq"], "allow_fallbacks": False}}


class SlowEnricher(ProductEnricher):
    """Trang "chậm" mất nhiều thời gian hơn giới hạn chờ; các trang khác xong ngay."""

    async def _fetch_detail(self, client, product):
        if product["slow"]:
            await asyncio.sleep(0.2)
        detail = {"specs": {"Nguồn": product["name"]}}
        self._cache[self._cache_key(product)] = (time.time(), detail)
        return detail


def product(name, slow):
    return {"id": name, "name": name, "platform": "tgdd", "externalUrl": f"https://x.vn/{name}", "slow": slow}


@run_async
async def test_enrich_returns_finished_pages_when_budget_runs_out():
    enricher = SlowEnricher()
    products = [product("nhanh", False), product("cham", True)]

    result = await enricher.enrich(products, budget_seconds=0.05)

    assert result[0]["detailFetched"] is True
    assert "detailFetched" not in result[1] and result[1] == products[1]


@run_async
async def test_late_pages_fill_the_cache_for_next_time():
    enricher = SlowEnricher()
    products = [product("cham", True)]

    await enricher.enrich(products, budget_seconds=0.01)
    await asyncio.gather(*enricher._pending)
    result = await enricher.enrich(products, budget_seconds=0.01)

    assert result[0]["detailFetched"] is True


class FakeSearch(EcomSearchTool):
    def __init__(self):
        super().__init__()
        self.crawl_started = asyncio.Event()
        self.crawl_cancelled = False

    async def _crawl(self, search_keyword, criteria, platform, limit, notes):
        self.crawl_started.set()
        try:
            await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            self.crawl_cancelled = True
            raise
        notes.append("ghi chú của phần cào")
        return [{"id": "web", "name": "Từ sàn"}], {"tgdd": 1}

    async def _finalize(self, products, criteria, notes, limit, detail_budget=None):
        self.detail_budget = detail_budget
        return products


@pytest.fixture
def no_cache(monkeypatch):
    import core.tools.search_sources as module

    async def miss(**kwargs):
        return None

    async def nothing(**kwargs):
        return None

    async def keep(query, products, criteria=None):
        return products, True

    monkeypatch.setattr(module.product_repository, "get_cached_search", miss)
    monkeypatch.setattr(module.product_repository, "save_search_cache", nothing)
    monkeypatch.setattr(module.semantic_filter, "filter_products", keep)
    monkeypatch.setattr(module.rag_service, "upsert_products", lambda products: len(products))
    return module


@run_async
async def test_rag_hit_cancels_the_crawl(no_cache, monkeypatch):
    tool = FakeSearch()
    monkeypatch.setattr(no_cache.rag_service, "search", lambda **k: [{"id": "kho", "name": "Từ kho", "aiMatchScore": 90}])
    notes = []

    result = await tool.run("laptop", notes=notes)
    await asyncio.sleep(0)

    assert [p["id"] for p in result] == ["kho"]
    assert tool.crawl_cancelled
    assert "ghi chú của phần cào" not in notes


@run_async
async def test_crawl_starts_together_with_rag_and_is_used_on_miss(no_cache, monkeypatch):
    tool = FakeSearch()
    started_before_rag_finished = []

    def rag_miss(**kwargs):
        time.sleep(0.02)
        started_before_rag_finished.append(tool.crawl_started.is_set())
        return []

    monkeypatch.setattr(no_cache.rag_service, "search", rag_miss)
    notes = []

    result = await tool.run("laptop", notes=notes)

    assert [p["id"] for p in result] == ["web"]
    assert started_before_rag_finished == [True]
    assert "ghi chú của phần cào" in notes


@run_async
async def test_rag_upsert_does_not_delay_the_answer(no_cache, monkeypatch):
    tool = FakeSearch()
    monkeypatch.setattr(no_cache.rag_service, "search", lambda **k: [])
    finished = []

    def slow_upsert(products):
        time.sleep(0.2)
        finished.append(True)
        return len(products)

    monkeypatch.setattr(no_cache.rag_service, "upsert_products", slow_upsert)

    await tool.run("laptop")

    assert not finished
    await asyncio.gather(*no_cache._background_tasks)
    assert finished


@run_async
async def test_cache_hit_does_not_wait_for_detail_pages(no_cache, monkeypatch):
    tool = FakeSearch()

    async def hit(**kwargs):
        return [{"id": "cache", "name": "Từ cache", "currentPrice": 1_000_000}]

    monkeypatch.setattr(no_cache.product_repository, "get_cached_search", hit)

    await tool.run("laptop")

    assert tool.detail_budget == 0


@run_async
async def test_unsupported_platform_falls_back_to_supported_ones():
    calls = []

    class FakePlatform(PlatformAdapter):
        def __init__(self, pid):
            self.id, self.name = pid, pid

        async def search(self, keyword, criteria, limit, notes, user_query=""):
            calls.append(self.id)
            return []

    # Sàn giả: không gọi mạng thật (trước đây test này vô tình cào thật FPT Shop, CellphoneS)
    tool = EcomSearchTool(platforms=[FakePlatform(p.id) for p in all_platforms()])
    notes = []

    await tool._crawl("laptop", None, "shopee", 4, notes)

    assert sorted(calls) == sorted(p.id for p in all_platforms())
    assert any("không tìm trên sàn này" in n for n in notes)


def test_unsupported_links_are_recognised():
    assert unsupported_site("https://shopee.vn/product/1/2") == "Shopee"
    assert unsupported_site("https://s.lazada.vn/abc") == "Lazada"
    assert unsupported_site("https://tiki.vn/p123.html") is None
