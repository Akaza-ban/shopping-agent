"""Workflow đa agent xây bằng LangGraph StateGraph."""
import re
import time
import logging
from typing import Dict, Any, List, Tuple, AsyncIterator

from langgraph.graph import StateGraph, START, END
from langgraph.config import get_stream_writer

from .state import AgentState, ProductItemModel, MessageItem, UniversalSearchCriteria
from .agents.orchestrator import OrchestratorAgent
from .agents.shopping_advisor import ShoppingAdvisorAgent
from .agents.comparison_agent import ComparisonAgent
from .agents.link_parser_agent import LinkParserAgent
from .agents.deal_finder_agent import DealFinderAgent
from .tools.ecom_search import EcomSearchTool
from memory.session_manager import session_memory
from services.catalog.ranker import rank_products, verifiable_attributes

logger = logging.getLogger("graph")

SEARCH_INTENTS = ("search_products", "compare_products")


def _widened_budget(max_price: float) -> float:
    """Ngân sách nới thêm 20%, làm tròn tới 100.000 đ."""
    return float(round(max_price * 1.2 / 100_000) * 100_000)


def _status(stage: str, message: str) -> Dict[str, Any]:
    return {"event": "status", "data": {"stage": stage, "message": message}}


def _products_event(products: List[ProductItemModel]) -> Dict[str, Any]:
    return {"event": "products", "data": {"count": len(products), "items": [p.model_dump() for p in products]}}


def _updates(state: AgentState) -> Dict[str, Any]:
    """Node trả về toàn bộ các trường của state (agent con sửa state tại chỗ)."""
    return {name: getattr(state, name) for name in AgentState.model_fields}


class ShopAIAgentWorkflow:
    """Workflow điều phối toàn bộ chu trình xử lý của các Agent kèm Trí nhớ đa lượt."""

    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self.advisor = ShoppingAdvisorAgent()
        self.comparator = ComparisonAgent()
        self.link_parser = LinkParserAgent()
        self.deal_finder = DealFinderAgent()
        self.search_tool = EcomSearchTool()
        self.graph = self._build_graph()

    # Xây graph
    def _build_graph(self):
        g = StateGraph(AgentState)
        g.add_node("load_session", self._node_load_session)
        g.add_node("route", self._node_route)
        g.add_node("clarify", self._node_clarify)
        g.add_node("ask", self._node_ask)
        g.add_node("smalltalk", self._node_ask)
        g.add_node("parse_link", self._node_parse_link)
        g.add_node("search", self._node_search)
        g.add_node("deal", self._node_deal)
        g.add_node("compare", self._node_compare)
        g.add_node("respond", self._node_respond)
        g.add_node("finalize", self._node_finalize)

        g.add_edge(START, "load_session")
        g.add_edge("load_session", "route")
        g.add_edge("route", "clarify")
        g.add_conditional_edges("clarify", self._next_after_clarify, {
            "ask": "ask",
            "smalltalk": "smalltalk",
            "parse_link": "parse_link",
            "search": "search",
            "deal": "deal",
            "respond": "respond",
        })
        g.add_edge("ask", "finalize")
        g.add_edge("smalltalk", "finalize")
        g.add_edge("parse_link", "respond")
        g.add_edge("search", "compare")
        g.add_edge("deal", "compare")
        g.add_edge("compare", "respond")
        g.add_edge("respond", "finalize")
        g.add_edge("finalize", END)
        return g.compile(name="shopai_agent")

    @staticmethod
    def _next_after_clarify(state: AgentState) -> str:
        if state.clarification:
            return "ask"
        if state.intent == "smalltalk":
            return "smalltalk"
        if state.intent == "parse_link":
            return "parse_link"
        if state.intent in SEARCH_INTENTS:
            return "search"
        if state.intent == "find_deal":
            return "deal"
        return "respond"

    # API công khai
    async def execute(self, state: AgentState) -> AgentState:
        result = await self.graph.ainvoke(state)
        return AgentState(**result) if isinstance(result, dict) else result

    async def execute_stream(self, state: AgentState) -> AsyncIterator[Dict[str, Any]]:
        """Workflow thực thi dạng Streaming SSE đa giai đoạn (Multi-stage events)."""
        async for event in self.graph.astream(state, stream_mode="custom"):
            yield event

    # Các node
    async def _node_load_session(self, state: AgentState) -> Dict[str, Any]:
        if state.session_id:
            await session_memory.load_session_from_db(state.session_id)
        return {}

    async def _node_route(self, state: AgentState) -> Dict[str, Any]:
        state = await self.orchestrator.route(state)
        if state.intent != "smalltalk":
            get_stream_writer()(_status("routing", "Đã hiểu yêu cầu, đang xử lý..."))
        platform = (state.platform_filter or "").lower().strip()
        if platform and platform != "all" and state.criteria:
            state.criteria = state.criteria.model_copy(update={"target_platforms": [platform]})
        return _updates(state)

    async def _node_clarify(self, state: AgentState) -> Dict[str, Any]:
        if state.intent == "smalltalk":
            return {}  # giữ nguyên câu hỏi làm rõ đang chờ (nếu có)
        self._apply_pending_clarification(state)
        self._maybe_ask_clarification(state)
        return _updates(state)

    async def _node_ask(self, state: AgentState) -> Dict[str, Any]:
        writer = get_stream_writer()
        if state.clarification:
            writer({"event": "clarification", "data": state.clarification})
        writer({"event": "token", "data": {"content": state.final_response}})
        return {}

    async def _node_parse_link(self, state: AgentState) -> Dict[str, Any]:
        writer = get_stream_writer()
        writer(_status("parsing_link", "Đang bóc tách thông tin và thẩm định liên kết sản phẩm..."))
        state = await self.link_parser.parse(state)
        if state.found_products:
            writer(_products_event(state.found_products))
        return _updates(state)

    async def _node_search(self, state: AgentState) -> Dict[str, Any]:
        writer = get_stream_writer()
        async for event in self._run_search(state):
            writer(event)
        if state.found_products:
            writer(_products_event(state.found_products))
        return _updates(state)

    async def _node_deal(self, state: AgentState) -> Dict[str, Any]:
        writer = get_stream_writer()
        writer(_status("finding_deal", "Đang săn các deal và mức giảm giá tốt nhất..."))
        c = state.criteria
        has_target = bool(c and (c.target_entity or c.product_type))
        last_products = session_memory.get_last_products(state.session_id) if state.session_id else []
        if not has_target and last_products:
            state.found_products = [ProductItemModel(**p) for p in last_products]
        elif c:
            async for event in self._run_search(state):
                writer(event)
        state = await self.deal_finder.find_deals(state)
        if state.found_products:
            writer(_products_event(state.found_products))
        return _updates(state)

    async def _node_compare(self, state: AgentState) -> Dict[str, Any]:
        if len(state.found_products) < 2:
            return {}
        writer = get_stream_writer()
        writer(_status("comparing", "Đang tổng hợp bảng so sánh cấu hình, giá, bảo hành và đổi trả..."))
        state = await self.comparator.compare(state)
        if state.comparison_table:
            writer({"event": "comparison", "data": {"summary": state.comparison_summary, "table": state.comparison_table}})
        return _updates(state)

    async def _node_respond(self, state: AgentState) -> Dict[str, Any]:
        writer = get_stream_writer()
        if state.intent == "parse_link" and not state.found_products and state.final_response:
            writer({"event": "token", "data": {"content": state.final_response}})
            return {}
        writer(_status("synthesizing", "Chuyên gia AI đang phân tích ưu nhược điểm và soạn lời khuyên..."
                       if state.found_products else "Đang soạn câu trả lời..."))
        async for token in self.advisor.generate_response_stream(state):
            writer({"event": "token", "data": {"content": token}})
        return _updates(state)

    async def _node_finalize(self, state: AgentState) -> Dict[str, Any]:
        # Ghi nhớ lượt hội thoại vào Session Memory & SQLite
        if state.session_id and state.final_response:
            now_ms = int(time.time() * 1000)
            session_memory.save_turn(
                session_id=state.session_id,
                user_message=MessageItem(id=f"msg-user-{now_ms}", sender="user", text=state.user_query, timestamp="Vừa xong"),
                ai_message=MessageItem(id=f"msg-ai-{now_ms + 1}", sender="ai", text=state.final_response, timestamp="Vừa xong"),
                products=state.found_products,
                criteria=state.criteria
            )

        state.suggested_questions = self.generate_suggested_questions(state)
        writer = get_stream_writer()
        writer({"event": "suggestions", "data": state.suggested_questions})
        writer({
            "event": "done",
            "data": {
                "session_id": state.session_id,
                "intent": state.intent,
                "recommended_product": state.recommended_product.model_dump() if state.recommended_product else None,
                "clarification": state.clarification,
                "relaxed_search": state.relaxed_search,
                "search_notes": state.search_notes
            }
        })
        return {"suggested_questions": state.suggested_questions}

    BUDGET_OPTIONS = {
        "laptops": ["Dưới 15 triệu", "15 - 20 triệu", "20 - 25 triệu", "25 - 30 triệu", "Trên 30 triệu"],
        "phones": ["Dưới 5 triệu", "5 - 10 triệu", "10 - 20 triệu", "Trên 20 triệu"],
        "audio": ["Dưới 1 triệu", "1 - 3 triệu", "3 - 7 triệu", "Trên 7 triệu"],
        "wearables": ["Dưới 2 triệu", "2 - 5 triệu", "5 - 10 triệu", "Trên 10 triệu"],
        "home_appliances": ["Dưới 5 triệu", "5 - 10 triệu", "10 - 20 triệu", "Trên 20 triệu"],
        "monitors": ["Dưới 3 triệu", "3 - 6 triệu", "6 - 12 triệu", "Trên 12 triệu"],
    }
    DEFAULT_BUDGET_OPTIONS = ["Dưới 1 triệu", "1 - 5 triệu", "5 - 15 triệu", "Trên 15 triệu"]
    SKIP_BUDGET_OPTION = "Không giới hạn ngân sách, cứ tìm giúp tôi"

    @staticmethod
    def _budget_label(option: str, language: str) -> str:
        """Nhãn hiển thị của mức ngân sách theo ngôn ngữ; giá trị gửi lại vẫn là câu tiếng Việt gốc."""
        if language != "en":
            return option
        if option == ShopAIAgentWorkflow.SKIP_BUDGET_OPTION:
            return "No budget limit, just search"
        m = re.fullmatch(r"(Dưới|Trên) (\d+) triệu", option)
        if m:
            return f"{'Under' if m.group(1) == 'Dưới' else 'Over'} {m.group(2)} million VND"
        m = re.fullmatch(r"(\d+) - (\d+) triệu", option)
        if m:
            return f"{m.group(1)}–{m.group(2)} million VND"
        return option
    SKIP_PATTERN = re.compile(r"không giới hạn|bất kỳ|giá nào cũng|cứ tìm|tìm luôn|không quan trọng|bỏ qua", re.IGNORECASE)

    def _maybe_ask_clarification(self, state: AgentState) -> None:
        """Hỏi ngân sách trước khi cào nếu yêu cầu tìm mua quá chung (VD:"""
        c = state.criteria
        if not c or not self._is_vague_purchase(state, c):
            return
        category = c.category or "all"
        asked = list(session_memory.get_conversation_state(state.session_id).get("clarified_categories") or [])
        if category in asked:
            return

        en = state.language == "en"
        entity = c.product_type or c.target_entity or ("the product" if en else "sản phẩm")
        question = (f"Roughly how much do you plan to spend on {entity}?" if en
                    else f"Bạn dự định chi khoảng bao nhiêu cho {entity}?")
        state.clarification = self._budget_clarification(question, category, state.language)
        if c.usage_purpose:
            purpose_hint = ""
        else:
            purpose_hint = " If you can, also tell me what you mainly need it for." if en else " Nếu được, bạn cho biết thêm mục đích sử dụng chính nhé."
        state.final_response = f"{question}{purpose_hint}"
        state.intent = "search_products"
        session_memory.update_conversation_state(
            state.session_id,
            pending_clarification=c.model_dump(),
            clarified_categories=asked + [category],
        )
        logger.info(f"[Clarification] Hỏi ngân sách cho '{entity}' (session={state.session_id})")

    def _is_vague_purchase(self, state: AgentState, c: UniversalSearchCriteria) -> bool:
        """Yêu cầu tìm mua chưa có giá, hãng, model cụ thể và người dùng không bảo "cứ tìm"."""
        wants_to_buy = (
            state.intent == "general_advice"
            and c.target_entity
            and re.search(r"\b(?:tìm|mua)\b", state.user_query, re.IGNORECASE)
            and not session_memory.get_last_products(state.session_id)
        )
        if state.intent != "search_products" and not wants_to_buy:
            return False
        if c.max_price or c.min_price or c.brands:
            return False
        product_text = f"{c.product_type or ''} {c.cleaned_query or ''}"
        return not (re.search(r"\d", product_text) or self.SKIP_PATTERN.search(state.user_query))

    def _budget_clarification(self, question: str, category: str, language: str) -> Dict[str, Any]:
        options = self.BUDGET_OPTIONS.get(category, self.DEFAULT_BUDGET_OPTIONS) + [self.SKIP_BUDGET_OPTION]
        return {
            "id": f"clar-budget-{int(time.time() * 1000)}",
            "field": "budget",
            "question": question,
            "context_hint": ("Knowing your budget lets the assistant filter the right price segment and rank more accurately before scanning the stores."
                             if language == "en" else "Biết ngân sách giúp trợ lý lọc đúng phân khúc và xếp hạng chính xác hơn trước khi quét các sàn."),
            "options": [{"id": f"opt-{i}", "label": self._budget_label(o, language), "value": o}
                        for i, o in enumerate(options)],
            "allow_custom_input": True,
        }

    def _apply_pending_clarification(self, state: AgentState) -> None:
        """Nếu lượt trước vừa hỏi làm rõ, gộp câu trả lời (VD:"""
        pending = session_memory.get_conversation_state(state.session_id).get("pending_clarification")
        if not pending:
            return
        session_memory.update_conversation_state(state.session_id, pending_clarification=None)
        if state.intent in ("parse_link", "out_of_scope"):
            return
        new = state.criteria
        new_cat = (new.category if new else None) or "all"
        if new and new_cat not in ("all", pending.get("category")) and (new.product_type or new.target_entity):
            return  # chủ đề mới

        merged = dict(pending)
        if new:
            for field in ("min_price", "max_price", "usage_purpose", "priority"):
                value = getattr(new, field)
                if value not in (None, "", "best_value"):
                    merged[field] = value
            if new.brands:
                merged["brands"] = new.brands
            if new.attributes:
                merged["attributes"] = {**(pending.get("attributes") or {}), **new.attributes}
            if new.target_platforms and new.target_platforms != ["all"]:
                merged["target_platforms"] = new.target_platforms
        state.criteria = UniversalSearchCriteria(**merged)
        state.intent = "search_products"
        logger.info(
            f"[Clarification] Gộp câu trả lời vào tiêu chí: max_price={state.criteria.max_price}, "
            f"min_price={state.criteria.min_price}, usage={state.criteria.usage_purpose}"
        )

    def _relaxation_steps(self, criteria: UniversalSearchCriteria) -> List[Tuple[UniversalSearchCriteria, str]]:
        """Sinh các bước nới lỏng tiêu chí (cộng dồn) khi tìm đúng yêu cầu không có kết quả:"""
        steps: List[Tuple[UniversalSearchCriteria, str]] = []
        current = criteria
        changes: List[str] = []

        def strip_terms(text: str, terms: List[str]) -> str:
            for t in terms:
                if t:
                    text = re.sub(re.escape(t), " ", text, flags=re.IGNORECASE)
            return re.sub(r"\s+", " ", text).strip()

        base_query = criteria.cleaned_query or criteria.product_type or criteria.target_entity or ""

        attr_values = [str(v).strip() for v in (criteria.attributes or {}).values() if isinstance(v, str) and str(v).strip()]
        if criteria.attributes:
            changes.append(f"bỏ yêu cầu {', '.join(attr_values)}" if attr_values else "bỏ yêu cầu thông số chi tiết")
            base_query = strip_terms(base_query, attr_values)
            current = current.model_copy(update={"attributes": {}, "cleaned_query": base_query})
            steps.append((current, "; ".join(changes)))

        if criteria.max_price:
            widened = _widened_budget(criteria.max_price)
            changes.append(f"nới ngân sách lên {widened:,.0f} đ")
            current = current.model_copy(update={"max_price": widened})
            steps.append((current, "; ".join(changes)))

        if criteria.brands:
            changes.append("mở rộng sang các hãng khác")
            base_query = strip_terms(base_query, list(criteria.brands))
            current = current.model_copy(update={"brands": [], "cleaned_query": base_query})
            steps.append((current, "; ".join(changes)))

        fallback_query = criteria.target_entity or criteria.product_type or ""
        return [
            (c if c.cleaned_query.strip() else c.model_copy(update={"cleaned_query": fallback_query}), desc)
            for c, desc in steps
        ]

    async def _run_search(self, state: AgentState):
        """Tìm sản phẩm theo tiêu chí;"""
        criteria = state.criteria
        search_query = criteria.cleaned_query if (criteria and criteria.cleaned_query) else state.user_query
        can_relax = criteria is not None and state.intent in ("search_products", "find_deal")
        yield _status("retrieval", f"Đang truy xuất kho dữ liệu & quét các sàn cho '{search_query}'...")
        raw_products = await self._search(search_query, criteria, state.search_notes)

        if not raw_products and can_relax:
            for relaxed, description in self._relaxation_steps(criteria):
                yield _status(
                    "relaxing",
                    f"Không có sản phẩm khớp hoàn toàn yêu cầu, đang tìm phương án gần nhất ({description})..."
                )
                relaxed_notes: List[str] = []
                raw_products = await self._search(relaxed.cleaned_query, relaxed, relaxed_notes)
                if raw_products:
                    state.relaxed_search = description
                    state.search_notes.extend(relaxed_notes)
                    logger.info(f"[Relaxed Search] '{search_query}' -> {description}: {len(raw_products)} sản phẩm")
                    break

        if raw_products and can_relax and self._needs_upsell(criteria, raw_products):
            widened = _widened_budget(criteria.max_price)
            wanted = ", ".join(verifiable_attributes(criteria).values())
            yield _products_event([ProductItemModel(**p) for p in raw_products])
            yield _status("upsell", f"Chưa có sản phẩm đúng {wanted} trong ngân sách, đang tìm thêm tới {widened:,.0f} đ...")
            raw_products = await self._upsell(state, search_query, raw_products, widened, wanted)

        state.found_products = [ProductItemModel(**p) for p in raw_products]

    async def _search(self, query: str, criteria, notes: List[str], force_refresh: bool = False) -> List[Dict[str, Any]]:
        return await self.search_tool.run(
            query=query,
            category=criteria.category if criteria else "all",
            criteria=criteria,
            limit=4,
            force_refresh=force_refresh,
            notes=notes,
        )

    def _needs_upsell(self, criteria: UniversalSearchCriteria, products: List[Dict[str, Any]]) -> bool:
        """Có thông số bắt buộc và ngân sách, nhưng chưa sản phẩm nào xác nhận đúng thông số."""
        return bool(verifiable_attributes(criteria) and criteria.max_price
                    and not any(self._fully_verified(p) for p in products))

    async def _upsell(self, state: AgentState, search_query: str, products: List[Dict[str, Any]],
                      widened: float, wanted: str) -> List[Dict[str, Any]]:
        """Thêm sản phẩm ĐÚNG thông số nhưng vượt ngân sách (tới widened) vào danh sách, ghi chú cho Advisor."""
        criteria = state.criteria
        alt = await self._search(search_query, criteria.model_copy(update={"max_price": widened}), [], force_refresh=True)
        known_ids = {p.get("id") for p in products}
        alt_ok = [p for p in alt if self._fully_verified(p) and p.get("id") not in known_ids]
        if not alt_ok:
            state.search_notes.append(
                f"Đã tìm thêm tới {widened:,.0f} đ nhưng vẫn không có sản phẩm nào xác nhận đúng {wanted} trên các sàn đã quét."
            )
            return products
        ranked, _ = rank_products(products + alt_ok, criteria)
        state.search_notes.append(
            f"Trong ngân sách không có sản phẩm đúng {wanted}; khi tìm thêm tới {widened:,.0f} đ có "
            f"{len(alt_ok)} sản phẩm ĐÚNG yêu cầu nhưng vượt ngân sách (đã đưa vào danh sách, lý do ghi 'Vượt ngân sách')."
        )
        return ranked[:4]

    @staticmethod
    def _fully_verified(p: Dict[str, Any]) -> bool:
        status = p.get("attributeMatch") or {}
        return bool(status) and all(v == "verified" for v in status.values())

    # Gợi ý câu hỏi tiếp theo (Quick Chips)
    GENERIC_NAME_WORDS = re.compile(
        r"^(?:tai|nghe|chụp|nhét|không|dây|laptop|điện|thoại|máy|giặt|tính|bảng|tivi|smart|loa|đồng|hồ|thông|minh|tủ|lạnh|new|full|box|chính|hãng)$",
        re.IGNORECASE,
    )

    def _short_name(self, name: str) -> str:
        """'Tai nghe Chụp Tai Sony WH1000XM6' -> 'Sony WH1000XM6' (bỏ từ chỉ loại sản phẩm ở đầu tên)."""
        words = name.split()
        start = next((i for i, w in enumerate(words) if not self.GENERIC_NAME_WORDS.match(w)), 0)
        return " ".join(words[start:start + 2]) or name[:15]

    def generate_suggested_questions(self, state: AgentState) -> list:
        """2-3 câu hỏi gợi ý nhanh (Quick Chips) theo ngữ cảnh: link vừa đọc, sản phẩm đang xem, hoặc chủ đề câu hỏi."""
        if state.clarification:
            return []
        text = SUGGESTIONS["en" if state.language == "en" else "vi"]
        if state.intent == "parse_link" and state.found_products:
            return [q.format(name=state.found_products[0].name[:25]) for q in text["link"]]
        prods = self._context_products(state)
        if len(prods) >= 2:
            a, b = self._short_name(prods[0].name), self._short_name(prods[1].name)
            return [q.format(a=a, b=b) for q in text["pair"]]
        if len(prods) == 1:
            return [q.format(name=prods[0].name[:25], platform=prods[0].platformName) for q in text["single"]]
        q_lower = state.user_query.lower()
        if any(w in q_lower for w in text["phone_words"]):
            return list(text["phones"])
        if "laptop" in q_lower:
            return list(text["laptops"])
        return list(text["default"])

    @staticmethod
    def _context_products(state: AgentState) -> List[ProductItemModel]:
        """Sản phẩm của lượt này; không có thì lấy sản phẩm đã đề xuất ở lượt trước trong phiên."""
        if state.found_products or not state.session_id:
            return state.found_products
        return [ProductItemModel(**p) for p in session_memory.get_last_products(state.session_id) or []]


SUGGESTIONS = {
    "vi": {
        "link": [
            "So sánh {name} với các đối thủ cùng phân khúc",
            "Chính sách bảo hành và đổi trả của link này ra sao?",
            "Có mã giảm giá hoặc freeship nào áp dụng được thêm không?",
        ],
        "pair": [
            "So sánh chi tiết {a} và {b}",
            "Con nào pin trâu và dùng bền hơn?",
            "Có chính sách bảo hành hoặc trả góp 0% không?",
        ],
        "single": [
            "Thời lượng pin thực tế của {name} là mấy tiếng?",
            "Chính sách bảo hành tại {platform} thế nào?",
            "Có mẫu nào khác cùng tầm giá để so sánh không?",
        ],
        "phone_words": ("iphone", "điện thoại"),
        "phones": [
            "Top điện thoại pin trâu tầm giá 15 - 20 triệu",
            "Nên mua iPhone 15 hay cố lên iPhone 16?",
            "Điện thoại chụp ảnh đẹp nhất phân khúc",
        ],
        "laptops": [
            "Laptop văn phòng mỏng nhẹ dưới 15 triệu",
            "Laptop gaming tầm trung tốt nhất hiện nay",
            "Nên chọn MacBook hay laptop Windows?",
        ],
        "default": [
            "Tư vấn điện thoại tốt nhất tầm giá 10 - 15 triệu",
            "Gợi ý laptop văn phòng mỏng nhẹ pin trâu",
            "Săn deal công nghệ giảm giá sâu hôm nay",
        ],
    },
    "en": {
        "link": [
            "Compare {name} with rivals in the same price range",
            "What are the warranty and return policies for this link?",
            "Are there any extra vouchers or free shipping deals?",
        ],
        "pair": [
            "Compare {a} and {b} in detail",
            "Which one has better battery life and durability?",
            "Is there a warranty plan or 0% installment option?",
        ],
        "single": [
            "How many hours does the {name} battery really last?",
            "What is the warranty policy at {platform}?",
            "Are there other models in the same price range to compare?",
        ],
        "phone_words": ("iphone", "phone"),
        "phones": ["Best battery-life phones for 15–20 million VND", "iPhone 15 or iPhone 16?", "Best camera phone in its segment"],
        "laptops": ["Thin and light office laptop under 15 million VND", "Best mid-range gaming laptop right now", "MacBook or Windows laptop?"],
        "default": ["Best phone for 10–15 million VND", "Thin and light office laptop with long battery life", "Today's biggest tech deals"],
    },
}
