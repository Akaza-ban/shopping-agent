import json
import uuid
import logging
from typing import Optional, List, Dict, Any, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from core.state import AgentState, ProductItemModel
from core.graph import ShopAIAgentWorkflow
from core.agents.comparison_agent import ComparisonAgent
from memory.session_manager import session_memory
from database.models import UserModel
from database.repositories import chat_repository
from src.auth import require_user
from src.config import settings

logger = logging.getLogger("chat_route_src")
router = APIRouter(prefix="/chat", tags=["Chat"])
workflow = ShopAIAgentWorkflow()
comparison_agent = ComparisonAgent()

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    platform: Optional[str] = "all"
    # Ngôn ngữ trả lời theo Cài đặt của người dùng
    language: Literal["vi", "en"] = "vi"

class CompareRequest(BaseModel):
    session_id: Optional[str] = None
    products: List[ProductItemModel]

class ChatResponse(BaseModel):
    session_id: str
    message: str
    intent: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    recommended_product: Optional[Dict[str, Any]] = None
    products: List[Dict[str, Any]] = []
    suggestions: List[str] = []
    comparison: Optional[Dict[str, Any]] = None
    clarification: Optional[Dict[str, Any]] = None
    relaxed_search: Optional[str] = None
    search_notes: List[str] = []
    llm_provider: str = "groq"
    langsmith_tracing: bool = False

async def _own_session(session_id: Optional[str], user: UserModel, title: str = "") -> str:
    """Hội thoại phải thuộc người dùng hiện tại (tạo mới nếu chưa có); trả về session_id dùng cho lượt này."""
    session_id = session_id or f"chat-{uuid.uuid4().hex[:16]}"
    if not await chat_repository.claim_session(session_id, user.id, title):
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập hội thoại này.")
    return session_id


async def _check_owner(session_id: str, user: UserModel) -> None:
    owner = await chat_repository.get_session_owner(session_id)
    if owner is not None and owner != user.id:
        raise HTTPException(status_code=403, detail="Bạn không có quyền truy cập hội thoại này.")


@router.post("", response_model=ChatResponse)
async def send_chat_message(req: ChatRequest, user: UserModel = Depends(require_user)):
    session_id = await _own_session(req.session_id, user, req.message)

    # 1. Nạp lịch sử trước đó từ SQLite nếu có
    await session_memory.load_session_from_db(session_id)
    history = session_memory.get_messages(session_id)
    
    # 2. Khởi tạo Agent State
    state = AgentState(
        session_id=session_id,
        user_query=req.message,
        messages=list(history),
        platform_filter=req.platform,
        language=req.language,
    )
    
    result_state = await workflow.execute(state)
    
    is_tracing_enabled = settings.LANGCHAIN_TRACING_V2.lower() in ("true", "1") and bool(settings.LANGCHAIN_API_KEY)

    return ChatResponse(
        session_id=session_id,
        message=result_state.final_response,
        intent=result_state.intent,
        criteria=result_state.criteria.model_dump() if result_state.criteria else None,
        recommended_product=result_state.recommended_product.model_dump() if result_state.recommended_product else None,
        products=[p.model_dump() for p in result_state.found_products],
        suggestions=result_state.suggested_questions,
        comparison=(
            {"summary": result_state.comparison_summary, "table": result_state.comparison_table}
            if result_state.comparison_table else None
        ),
        clarification=result_state.clarification,
        relaxed_search=result_state.relaxed_search,
        search_notes=result_state.search_notes,
        llm_provider=settings.LLM_PROVIDER,
        langsmith_tracing=is_tracing_enabled
    )

@router.post("/stream")
async def chat_stream_post(req: ChatRequest, user: UserModel = Depends(require_user)):
    """Streaming SSE Chat API (POST)."""
    session_id = await _own_session(req.session_id, user, req.message)

    # Nạp lịch sử trước đó nếu có
    await session_memory.load_session_from_db(session_id)
    history = session_memory.get_messages(session_id)
    
    state = AgentState(
        session_id=session_id,
        user_query=req.message,
        messages=list(history),
        platform_filter=req.platform,
        language=req.language,
    )
    
    async def sse_generator():
        try:
            async for event_item in workflow.execute_stream(state):
                yield {
                    "event": event_item["event"],
                    "data": json.dumps(event_item["data"], ensure_ascii=False)
                }
        except Exception as e:
            logger.error(f"[SSE Stream Error]: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False)
            }

    return EventSourceResponse(sse_generator())

@router.get("/stream")
async def chat_stream_get(
    session_id: Optional[str] = None, message: str = "", platform: Optional[str] = "all", language: Literal["vi", "en"] = "vi",
    user: UserModel = Depends(require_user)
):
    """Streaming SSE Chat API (GET) phục vụ Native HTML5 EventSource (token truyền qua ?access_token=)."""
    req = ChatRequest(session_id=session_id, message=message, platform=platform, language=language)
    return await chat_stream_post(req, user)

@router.post("/compare")
async def compare_products(req: CompareRequest, user: UserModel = Depends(require_user)):
    """Tool so sánh cho các sản phẩm giao diện đang giữ (VD:"""
    state = AgentState(session_id=req.session_id or "compare", user_query="so sánh", found_products=req.products)
    state = await comparison_agent.compare(state)
    return {"summary": state.comparison_summary, "table": state.comparison_table}

@router.get("/history/{session_id}")
async def get_chat_history(session_id: str, user: UserModel = Depends(require_user)):
    await _check_owner(session_id, user)
    await session_memory.load_session_from_db(session_id)
    messages = session_memory.get_messages(session_id)
    return {"session_id": session_id, "messages": [m.model_dump() for m in messages]}

@router.delete("/history/{session_id}")
async def delete_chat_history(session_id: str, user: UserModel = Depends(require_user)):
    """Xóa đoạn chat: tin nhắn, ngữ cảnh sản phẩm và trạng thái hỏi làm rõ của phiên (RAM + SQLite)."""
    await _check_owner(session_id, user)
    await session_memory.delete_session(session_id)
    return {"session_id": session_id, "deleted": True}
