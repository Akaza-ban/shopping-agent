"""
Trò chuyện xã giao do LLM router tự phân loại và trả lời trong cùng một lần gọi:
không có bước trạng thái, không tìm kiếm, không gọi LLM lần hai.
"""

import asyncio
import json

import core.agents.orchestrator as orchestrator_module
from core.agents.orchestrator import OrchestratorAgent
from core.graph import ShopAIAgentWorkflow
from core.state import AgentState


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0
        self.prompts = []

    async def ainvoke(self, messages):
        self.calls += 1
        self.prompts.append(messages)

        class R:
            content = json.dumps(self.payload, ensure_ascii=False)

        return R()


def use_llm(monkeypatch, payload):
    llm = FakeLLM(payload)
    monkeypatch.setattr(orchestrator_module, "get_chat_model", lambda temperature=0.1, fast=False: llm)
    return llm


def state(query="dạo này sao rồi", **kw):
    return AgentState(session_id="smalltalk-test", user_query=query, **kw)


def test_router_reply_is_used_directly(monkeypatch):
    use_llm(monkeypatch, {"intent": "smalltalk", "criteria": {}, "reply": "Mình vẫn ổn, cảm ơn bạn!"})
    s = asyncio.run(OrchestratorAgent().route(state()))
    assert s.intent == "smalltalk" and s.final_response == "Mình vẫn ổn, cảm ơn bạn!" and s.criteria is None


def test_smalltalk_without_reply_falls_back_to_advisor(monkeypatch):
    use_llm(monkeypatch, {"intent": "smalltalk", "criteria": {}})
    assert asyncio.run(OrchestratorAgent().route(state())).intent == "general_advice"


def test_search_request_is_unaffected(monkeypatch):
    use_llm(
        monkeypatch,
        {"intent": "search_products", "criteria": {"category": "laptops", "cleaned_query": "laptop gaming"}},
    )
    s = asyncio.run(OrchestratorAgent().route(state("chào bạn, tìm laptop gaming")))
    assert s.intent == "search_products" and s.criteria.cleaned_query == "laptop gaming"


def test_english_setting_reaches_the_router(monkeypatch):
    llm = use_llm(monkeypatch, {"intent": "smalltalk", "criteria": {}, "reply": "Hi!"})
    asyncio.run(OrchestratorAgent().route(state("hello", language="en")))
    assert "English" in llm.prompts[0][0].content


def run_graph(query="hôm nay buồn quá"):
    async def scenario():
        wf = ShopAIAgentWorkflow()
        wf.advisor = None  # không được gọi Advisor
        wf.search_tool = None  # không được tìm kiếm
        return [e async for e in wf.execute_stream(state(query))]

    return asyncio.run(scenario())


def test_graph_replies_without_status_search_or_second_llm_call(monkeypatch):
    llm = use_llm(monkeypatch, {"intent": "smalltalk", "criteria": {}, "reply": "Mình nghe đây, có chuyện gì vậy bạn?"})
    monkeypatch.setattr("memory.session_manager.session_memory.save_turn", lambda **kw: None)
    events = run_graph()
    names = [e["event"] for e in events]
    assert "status" not in names and "products" not in names
    assert names[0] == "token" and events[0]["data"]["content"].startswith("Mình nghe đây")
    assert names[-1] == "done" and events[-1]["data"]["intent"] == "smalltalk"
    assert llm.calls == 1


def test_smalltalk_keeps_pending_clarification(monkeypatch):
    from memory.session_manager import session_memory

    pending = {"pending_clarification": {"category": "laptops"}}
    use_llm(monkeypatch, {"intent": "smalltalk", "criteria": {}, "reply": "Chào bạn!"})
    monkeypatch.setattr(session_memory, "get_conversation_state", lambda sid: pending)
    monkeypatch.setattr(session_memory, "save_turn", lambda **kw: None)
    updates = []
    monkeypatch.setattr(session_memory, "update_conversation_state", lambda *a, **k: updates.append(k))
    events = run_graph("chào bạn")
    assert events[-1]["data"]["intent"] == "smalltalk" and updates == []
