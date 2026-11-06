import logging
import asyncio
from typing import Dict, List, Optional, Any
from core.state import MessageItem, ProductItemModel, UniversalSearchCriteria
from database.repositories.chat_repo import chat_repository

logger = logging.getLogger("session_memory")

class SessionMemoryManager:

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def _ensure_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "messages": [],
                "last_products": [],
                "last_criteria": None,
                "conversation_state": {},
                "state_loaded": False,
                "state_write_task": None
            }
        return self._sessions[session_id]

    async def load_session_from_db(self, session_id: str) -> None:
        sess = self._ensure_session(session_id)
        if not sess["state_loaded"]:
            sess["conversation_state"] = {**(await chat_repository.get_conversation_state(session_id)), **sess["conversation_state"]}
            sess["state_loaded"] = True
        if sess["messages"]:
            return

        db_msgs = await chat_repository.get_messages(session_id, limit=20)
        ctx = await chat_repository.get_last_context(session_id)

        sess["messages"] = [
            MessageItem(
                id=m["id"],
                sender=m["sender"],
                text=m["text"],
                timestamp=m["timestamp"]
            )
            for m in db_msgs
        ]
        sess["last_products"] = ctx.get("last_products") or []
        sess["last_criteria"] = ctx.get("last_criteria") or None

    def get_messages(self, session_id: str) -> List[MessageItem]:
        return self._ensure_session(session_id)["messages"]

    def get_last_products(self, session_id: str) -> List[Dict[str, Any]]:
        return self._ensure_session(session_id).get("last_products", [])

    def get_last_criteria(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self._ensure_session(session_id).get("last_criteria")

    def get_conversation_state(self, session_id: str) -> Dict[str, Any]:
        return self._ensure_session(session_id)["conversation_state"]

    def update_conversation_state(self, session_id: str, **changes: Any) -> None:
        sess = self._ensure_session(session_id)
        state = sess["conversation_state"]
        for key, value in changes.items():
            if value is None:
                state.pop(key, None)
            else:
                state[key] = value
        snapshot = dict(state)
        previous = sess.get("state_write_task")

        async def _write():
            if previous and not previous.done():
                await asyncio.gather(previous, return_exceptions=True)
            await chat_repository.save_conversation_state(session_id, snapshot)

        try:
            sess["state_write_task"] = asyncio.get_running_loop().create_task(_write())
        except RuntimeError:
            pass

    def add_message(self, session_id: str, message: MessageItem):
        """Thêm tin nhắn đơn lẻ vào in-memory."""
        sess = self._ensure_session(session_id)
        sess["messages"].append(message)

    def save_turn(
        self,
        session_id: str,
        user_message: MessageItem,
        ai_message: MessageItem,
        products: Optional[List[Any]] = None,
        criteria: Optional[Any] = None
    ) -> None:
       
        sess = self._ensure_session(session_id)
        sess["messages"].append(user_message)
        sess["messages"].append(ai_message)

        # Chuyển đổi products sang dict chuẩn
        clean_prods = []
        if products:
            for p in products:
                if isinstance(p, dict):
                    clean_prods.append(p)
                elif hasattr(p, "model_dump"):
                    clean_prods.append(p.model_dump())
            sess["last_products"] = clean_prods

        # Chuyển đổi criteria sang dict
        clean_crit = None
        if criteria:
            if isinstance(criteria, dict):
                clean_crit = criteria
            elif hasattr(criteria, "model_dump"):
                clean_crit = criteria.model_dump()
            sess["last_criteria"] = clean_crit

        # Đồng bộ xuống SQLite Database (Task nền hoặc coroutine)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                chat_repository.save_turn(
                    session_id=session_id,
                    user_text=user_message.text,
                    ai_text=ai_message.text,
                    products=clean_prods,
                    criteria=clean_crit
                )
            )
        except RuntimeError:
            pass

    def format_chat_history_for_prompt(self, session_id: str, max_turns: int = 3) -> str:
        
        messages = self.get_messages(session_id)
        if not messages:
            return ""

        # Lấy tối đa max_turns * 2 tin nhắn gần nhất
        recent_msgs = messages[-(max_turns * 2):]
        history_lines = []
        for msg in recent_msgs:
            sender_label = "Khách hàng" if msg.sender == "user" else "ShopAI Copilot"
            # Rút ngắn tin nhắn quá dài của AI để tiết kiệm token
            txt = msg.text
            if msg.sender == "ai" and len(txt) > 250:
                txt = txt[:250] + "..."
            history_lines.append(f"- {sender_label}: {txt}")

        return "\n".join(history_lines)

    def format_previous_products_for_prompt(self, session_id: str, max_items: int = 3) -> str:
        
        last_prods = self.get_last_products(session_id)
        if not last_prods:
            return ""

        lines = ["[Các sản phẩm đã đề xuất ở lượt trao đổi trước]:"]
        for idx, p in enumerate(last_prods[:max_items], 1):
            name = p.get("name", "")
            price = p.get("currentPrice", 0)
            platform = p.get("platformName", "")
            specs = p.get("specs", "")
            specs_summary = ""
            if isinstance(specs, dict):
                specs_summary = ", ".join([f"{k}: {v}" for k, v in list(specs.items())[:3]])
            elif isinstance(specs, str):
                specs_summary = specs[:60]

            lines.append(
                f"- Lựa chọn #{idx}: {name} (Giá: {price:,.0f} đ tại {platform})"
                f"{f' | {specs_summary}' if specs_summary else ''}"
            )
        return "\n".join(lines)

    async def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        await chat_repository.clear_session(session_id)

    def clear_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(chat_repository.clear_session(session_id))
        except RuntimeError:
            pass

session_memory = SessionMemoryManager()
