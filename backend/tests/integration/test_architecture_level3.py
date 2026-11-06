"""
Kiểm thử Mức 3 (kiến trúc LangGraph & dọn dẹp), chạy offline: agent/tool được thay bằng bản giả.
- Graph có đủ các node; ainvoke và astream dùng chung một graph, thứ tự sự kiện SSE đúng.
- Tham số `platform` của /chat được áp vào tiêu chí trước khi tìm kiếm.
- Câu hỏi làm rõ đang chờ được lưu SQLite và khôi phục sau khi "khởi động lại" (session memory mới).
- Săn deal: xếp theo mức giảm, dùng lại sản phẩm lượt trước khi câu hỏi không nêu sản phẩm.
- Endpoint /chat/compare dựng bảng so sánh từ sản phẩm giao diện gửi lên.
"""
import asyncio
import sys
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.state import AgentState, ProductItemModel, UniversalSearchCriteria
from core.graph import ShopAIAgentWorkflow
from core.flows import clarification
from core.agents.deal_finder_agent import DealFinderAgent
from database.connection import Base
from database.repositories.chat_repo import ChatRepository
import memory.session_manager as session_module

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def _product(pid, price, original=None, platform="tgdd"):
    return {
        "id": pid, "name": f"Laptop {pid}", "platform": platform, "platformName": platform.upper(),
        "currentPrice": price, "originalPrice": original or price,
        "discountPercent": round((1 - price / original) * 100) if original else 0,
        "rating": 4.5, "reviewsCount": "Đã bán 1k", "specs": {"RAM": "16 GB"}, "externalUrl": f"https://x/{pid}",
    }


def _stub_workflow(monkeypatch, intent="search_products", criteria=None, products=None, calls=None):
    """Workflow với router / tìm kiếm / advisor giả để chạy graph không cần mạng & LLM."""
    wf = ShopAIAgentWorkflow()
    criteria = criteria or UniversalSearchCriteria(
        category="laptops", target_entity="laptop", cleaned_query="laptop gaming", max_price=30_000_000
    )

    async def fake_route(state):
        state.intent = intent
        state.criteria = criteria
        return state

    async def fake_search(query, category="all", criteria=None, platform="all", limit=6, force_refresh=False, notes=None):
        if calls is not None:
            calls.append({"query": query, "platforms": list(criteria.target_platforms) if criteria else None})
        return [dict(p) for p in (products or [])]

    async def fake_stream(state):
        state.final_response = f"Tư vấn cho {len(state.found_products)} sản phẩm"
        for token in ("Tư vấn ", "xong"):
            yield token

    async def no_db(session_id):
        return None

    monkeypatch.setattr(wf.orchestrator, "route", fake_route)
    monkeypatch.setattr(wf.search_tool, "run", fake_search)
    monkeypatch.setattr(wf.advisor, "generate_response_stream", fake_stream)
    monkeypatch.setattr(session_module.session_memory, "load_session_from_db", no_db)
    monkeypatch.setattr(session_module.session_memory, "save_turn", lambda **kw: None)
    return wf


async def _collect(wf, state):
    return [e async for e in wf.execute_stream(state)]


# ---------------------------------------------------------------- cấu trúc graph
def test_graph_has_expected_nodes():
    nodes = set(ShopAIAgentWorkflow().graph.get_graph().nodes)
    assert {"load_session", "route", "clarify", "ask", "parse_link", "search",
            "deal", "compare", "respond", "finalize"} <= nodes


def test_stream_event_order_for_search(monkeypatch):
    products = [_product("a", 25_000_000), _product("b", 27_000_000, platform="tiki")]
    wf = _stub_workflow(monkeypatch, products=products)
    events = asyncio.run(_collect(wf, AgentState(session_id="lvl3-stream", user_query="laptop gaming dưới 30 triệu")))
    kinds = [e["event"] for e in events]

    assert kinds[0] == "status" and events[0]["data"]["stage"] == "routing"
    for earlier, later in [("products", "comparison"), ("comparison", "token"), ("token", "suggestions"), ("suggestions", "done")]:
        assert kinds.index(earlier) < kinds.index(later), kinds
    assert kinds[-1] == "done"
    comparison = next(e for e in events if e["event"] == "comparison")["data"]
    assert len(comparison["table"]["columns"]) == 2


def test_execute_and_stream_share_graph(monkeypatch):
    products = [_product("a", 25_000_000), _product("b", 27_000_000)]
    wf = _stub_workflow(monkeypatch, products=products)
    result = asyncio.run(wf.execute(AgentState(session_id="lvl3-invoke", user_query="laptop gaming dưới 30 triệu")))
    assert isinstance(result, AgentState)
    assert [p.id for p in result.found_products] == ["a", "b"]
    assert result.comparison_table and result.final_response.startswith("Tư vấn cho 2")
    assert result.suggested_questions


def test_platform_filter_applied_before_search(monkeypatch):
    calls = []
    wf = _stub_workflow(monkeypatch, products=[_product("a", 25_000_000, platform="tiki")], calls=calls)
    asyncio.run(wf.execute(AgentState(session_id="lvl3-plat", user_query="laptop gaming dưới 30 triệu", platform_filter="tiki")))
    assert calls and calls[0]["platforms"] == ["tiki"]


# ---------------------------------------------------------------- làm rõ: lưu & khôi phục
def test_pending_clarification_survives_restart(tmp_path, monkeypatch):
    async def scenario():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'state.db'}")
        async with engine.begin() as conn:
            from database import models  # noqa: F401  (nạp model vào metadata)
            await conn.run_sync(Base.metadata.create_all)
        repo = ChatRepository(sessionmaker(engine, class_=AsyncSession, expire_on_commit=False))
        monkeypatch.setattr(session_module, "chat_repository", repo)

        # Tiến trình 1: hỏi làm rõ rồi "tắt server"
        before = session_module.SessionMemoryManager()
        monkeypatch.setattr(session_module, "session_memory", before)
        monkeypatch.setattr("core.flows.clarification.session_memory", before)
        broad = UniversalSearchCriteria(category="laptops", product_type="laptop gaming", target_entity="laptop", cleaned_query="laptop gaming")
        s1 = AgentState(session_id="restart-1", user_query="tìm laptop gaming", intent="search_products", criteria=broad)
        clarification.maybe_ask(s1)
        assert s1.clarification
        await before._sessions["restart-1"]["state_write_task"]

        # Tiến trình 2: bộ nhớ RAM trống, nạp lại từ SQLite
        after = session_module.SessionMemoryManager()
        monkeypatch.setattr("core.flows.clarification.session_memory", after)
        await after.load_session_from_db("restart-1")
        s2 = AgentState(session_id="restart-1", user_query="20 - 25 triệu", intent="general_advice",
                        criteria=UniversalSearchCriteria(min_price=20_000_000, max_price=25_000_000))
        clarification.apply_pending(s2)
        await after._sessions["restart-1"]["state_write_task"]
        await engine.dispose()
        return s2, after.get_conversation_state("restart-1")

    s2, conv = asyncio.run(scenario())
    assert s2.intent == "search_products"
    assert s2.criteria.cleaned_query == "laptop gaming" and s2.criteria.max_price == 25_000_000
    assert "pending_clarification" not in conv and conv["clarified_categories"] == ["laptops"]


# ---------------------------------------------------------------- săn deal
def test_deal_finder_orders_by_discount_and_notes():
    state = AgentState(session_id="deal-1", user_query="deal laptop", found_products=[
        ProductItemModel(**_product("full", 20_000_000)),
        ProductItemModel(**_product("small", 19_000_000, original=20_000_000)),
        ProductItemModel(**_product("big", 15_000_000, original=20_000_000)),
    ])
    state = asyncio.run(DealFinderAgent().find_deals(state))
    assert [p.id for p in state.found_products] == ["big", "small", "full"]
    assert "giảm 25%" in state.search_notes[-1] and "tiết kiệm 5,000,000 đ" in state.search_notes[-1]


def test_deal_node_reuses_previous_products(monkeypatch):
    calls = []
    wf = _stub_workflow(monkeypatch, intent="find_deal", criteria=UniversalSearchCriteria(), calls=calls)
    last = [_product("x", 18_000_000, original=20_000_000), _product("y", 10_000_000, original=20_000_000)]
    monkeypatch.setattr(session_module.session_memory, "get_last_products", lambda sid: last)
    result = asyncio.run(wf.execute(AgentState(session_id="deal-2", user_query="con nào đang giảm sâu nhất?")))
    assert calls == []  # không cào lại
    assert [p.id for p in result.found_products] == ["y", "x"]
    assert result.comparison_table is not None


# ---------------------------------------------------------------- xóa đoạn chat
def test_delete_conversation_clears_memory_and_db(tmp_path, monkeypatch):
    async def scenario():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'del.db'}")
        async with engine.begin() as conn:
            from database import models  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
        repo = ChatRepository(sessionmaker(engine, class_=AsyncSession, expire_on_commit=False))
        monkeypatch.setattr(session_module, "chat_repository", repo)
        memory = session_module.SessionMemoryManager()
        monkeypatch.setattr("application.chat.session_memory", memory)
        monkeypatch.setattr("application.chat.chat_repository", repo)

        await repo.save_turn("chat-del", "tìm laptop", "Bạn dự định chi bao nhiêu?")
        memory.update_conversation_state("chat-del", pending_clarification={"category": "laptops"})
        await memory._sessions["chat-del"]["state_write_task"]

        from src.routes.chat import delete_chat_history
        res = await delete_chat_history("chat-del", SimpleNamespace(id="user-1"))
        left = (await repo.get_messages("chat-del"), await repo.get_conversation_state("chat-del"), "chat-del" in memory._sessions)
        await engine.dispose()
        return res, left

    res, (messages, conv_state, in_memory) = asyncio.run(scenario())
    assert res["deleted"] is True
    assert messages == [] and conv_state == {} and not in_memory


# ---------------------------------------------------------------- API so sánh
def test_compare_endpoint_builds_table():
    from src.routes.chat import compare_products
    from src.schemas.chat import CompareRequest
    req = CompareRequest(products=[_product("a", 25_000_000), _product("b", 22_000_000)])
    res = asyncio.run(compare_products(req, SimpleNamespace(id="user-1")))
    rows = {r["label"]: r for r in res["table"]["rows"]}
    assert rows["Giá hiện tại"]["best_index"] == 1
    assert res["summary"]
