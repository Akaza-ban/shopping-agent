"""Bộ nhớ hội thoại: tin nhắn, sản phẩm đã đề xuất và trạng thái hỏi làm rõ của từng phiên.

Đọc từ RAM (nạp từ SQLite ở lượt đầu); ghi xuống SQLite chạy nền để không làm chậm câu trả lời.
"""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

from core.state import MessageItem
from database.repositories.chat_repo import chat_repository

logger = logging.getLogger("session_memory")


def _as_dict(value: Any) -> dict[str, Any] | None:
    """Dict hoặc model pydantic -> dict; kiểu khác -> None."""
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return None


class SessionMemoryManager:
    def __init__(self):
        self._sessions: dict[str, dict[str, Any]] = {}

    def _ensure_session(self, session_id: str) -> dict[str, Any]:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "messages": [],
                "last_products": [],
                "conversation_state": {},
                "state_loaded": False,
                "state_write_task": None,
            }
        return self._sessions[session_id]

    async def load_session_from_db(self, session_id: str) -> None:
        sess = self._ensure_session(session_id)
        if not sess["state_loaded"]:
            sess["conversation_state"] = {
                **(await chat_repository.get_conversation_state(session_id)),
                **sess["conversation_state"],
            }
            sess["state_loaded"] = True
        if sess["messages"]:
            return

        db_msgs = await chat_repository.get_messages(session_id, limit=20)
        ctx = await chat_repository.get_last_context(session_id)

        sess["messages"] = [
            MessageItem(id=m["id"], sender=m["sender"], text=m["text"], timestamp=m["timestamp"]) for m in db_msgs
        ]
        sess["last_products"] = ctx.get("last_products") or []

    def get_messages(self, session_id: str) -> list[MessageItem]:
        return self._ensure_session(session_id)["messages"]

    def get_last_products(self, session_id: str) -> list[dict[str, Any]]:
        return self._ensure_session(session_id).get("last_products", [])

    def get_conversation_state(self, session_id: str) -> dict[str, Any]:
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

        sess["state_write_task"] = self._run_in_background(_write())

    def save_turn(
        self,
        session_id: str,
        user_message: MessageItem,
        ai_message: MessageItem,
        products: list[Any] | None = None,
        criteria: Any | None = None,
    ) -> None:
        """Lưu một lượt hỏi đáp vào RAM; sản phẩm đề xuất (nếu có) thành ngữ cảnh cho lượt sau; ghi SQLite chạy nền."""
        sess = self._ensure_session(session_id)
        sess["messages"].extend([user_message, ai_message])
        product_dicts = [d for d in map(_as_dict, products or []) if d is not None]
        if products:
            sess["last_products"] = product_dicts
        self._run_in_background(
            chat_repository.save_turn(
                session_id=session_id,
                user_text=user_message.text,
                ai_text=ai_message.text,
                products=product_dicts,
                criteria=_as_dict(criteria) if criteria else None,
            )
        )

    def format_chat_history_for_prompt(self, session_id: str, max_turns: int = 3) -> str:
        """Vài lượt hội thoại gần nhất dạng văn bản cho prompt (tin nhắn dài của AI được rút gọn)."""
        messages = self.get_messages(session_id)
        if not messages:
            return ""

        # Lấy tối đa max_turns * 2 tin nhắn gần nhất
        recent_msgs = messages[-(max_turns * 2) :]
        history_lines = []
        for msg in recent_msgs:
            sender_label = "Khách hàng" if msg.sender == "user" else "ShopAI Copilot"
            # Rút ngắn tin nhắn dài của AI nhưng giữ cả đoạn cuối: lời đề nghị / câu hỏi lại thường nằm ở cuối
            txt = msg.text
            if msg.sender == "ai" and len(txt) > 450:
                txt = f"{txt[:200]} [...] {txt[-250:]}"
            history_lines.append(f"- {sender_label}: {txt}")

        return "\n".join(history_lines)

    def format_previous_products_for_prompt(self, session_id: str, max_items: int = 3) -> str:
        """Các sản phẩm đã đề xuất ở lượt trước (tên, giá, sàn, vài thông số) cho prompt."""
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

    @staticmethod
    def _run_in_background(coro: Coroutine[Any, Any, Any]) -> asyncio.Task | None:
        """Chạy việc ghi SQLite ở nền; ngoài event loop (script, test đồng bộ) thì bỏ qua."""
        try:
            return asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            coro.close()  # tránh cảnh báo "coroutine was never awaited"
            return None


session_memory = SessionMemoryManager()
