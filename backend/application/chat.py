"""Trò chuyện với trợ lý: gửi tin nhắn (trả một lần hoặc stream), xem / xóa lịch sử.

Mỗi hội thoại thuộc về một người dùng; người khác truy cập -> PermissionDeniedError.
Cách trợ lý xử lý một câu hỏi nằm ở core/graph.py.
"""

import uuid
from collections.abc import AsyncIterator
from typing import Any

from core.graph import ShopAIAgentWorkflow
from core.state import AgentState
from database.models import UserModel
from database.repositories import chat_repository
from memory.session_manager import session_memory
from shared.config import settings
from shared.exceptions import PermissionDeniedError

NO_ACCESS = "Bạn không có quyền truy cập hội thoại này."


async def _own_session(session_id: str | None, user: UserModel, title: str = "") -> str:
    """Hội thoại phải thuộc người dùng hiện tại (tạo mới nếu chưa có); trả về session_id dùng cho lượt này."""
    session_id = session_id or f"chat-{uuid.uuid4().hex[:16]}"
    if not await chat_repository.claim_session(session_id, user.id, title):
        raise PermissionDeniedError(NO_ACCESS)
    return session_id


async def _check_owner(session_id: str, user: UserModel) -> None:
    owner = await chat_repository.get_session_owner(session_id)
    if owner is not None and owner != user.id:
        raise PermissionDeniedError(NO_ACCESS)


async def _start_turn(
    user: UserModel, message: str, session_id: str | None, platform: str | None, language: str
) -> AgentState:
    """State đầu vào của agent cho một lượt hỏi, kèm lịch sử hội thoại đã lưu."""
    session_id = await _own_session(session_id, user, message)
    await session_memory.load_session_from_db(session_id)
    return AgentState(
        session_id=session_id,
        user_query=message,
        messages=list(session_memory.get_messages(session_id)),
        platform_filter=platform,
        language=language,
    )


def _tracing_enabled() -> bool:
    return settings.LANGCHAIN_TRACING_V2.lower() in ("true", "1") and bool(settings.LANGCHAIN_API_KEY)


async def send_message(
    workflow: ShopAIAgentWorkflow,
    user: UserModel,
    message: str,
    session_id: str | None,
    platform: str | None,
    language: str,
) -> dict[str, Any]:
    """Chạy trọn một lượt và trả toàn bộ kết quả một lần (các trường của ChatResponse)."""
    result = await workflow.execute(await _start_turn(user, message, session_id, platform, language))
    return {
        "session_id": result.session_id,
        "message": result.final_response,
        "intent": result.intent,
        "criteria": result.criteria.model_dump() if result.criteria else None,
        "recommended_product": result.recommended_product.model_dump() if result.recommended_product else None,
        "products": [p.model_dump() for p in result.found_products],
        "suggestions": result.suggested_questions,
        "comparison": (
            {"summary": result.comparison_summary, "table": result.comparison_table}
            if result.comparison_table
            else None
        ),
        "clarification": result.clarification,
        "relaxed_search": result.relaxed_search,
        "search_notes": result.search_notes,
        "llm_provider": settings.LLM_PROVIDER,
        "langsmith_tracing": _tracing_enabled(),
    }


async def stream_message(
    workflow: ShopAIAgentWorkflow,
    user: UserModel,
    message: str,
    session_id: str | None,
    platform: str | None,
    language: str,
) -> tuple[str, AsyncIterator[dict[str, Any]]]:
    """(session_id, các event {"event", "data"} theo từng giai đoạn: status, products, token, ..., done).

    Quyền truy cập được kiểm tra ngay (trước khi mở luồng stream).
    """
    state = await _start_turn(user, message, session_id, platform, language)
    return state.session_id, workflow.execute_stream(state)


async def history(user: UserModel, session_id: str) -> dict[str, Any]:
    await _check_owner(session_id, user)
    await session_memory.load_session_from_db(session_id)
    return {"session_id": session_id, "messages": [m.model_dump() for m in session_memory.get_messages(session_id)]}


async def delete(user: UserModel, session_id: str) -> dict[str, Any]:
    """Xóa đoạn chat: tin nhắn, ngữ cảnh sản phẩm và trạng thái hỏi làm rõ của phiên (RAM + SQLite)."""
    await _check_owner(session_id, user)
    await session_memory.delete_session(session_id)
    return {"session_id": session_id, "deleted": True}
