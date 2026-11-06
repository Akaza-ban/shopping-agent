import time
import json
import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ...core.state import AgentState, MessageItem
from ...core.graph import ShopAIAgentWorkflow
from ...memory.session_manager import session_memory

logger = logging.getLogger("chat_route")
router = APIRouter(prefix="/chat", tags=["Chat"])
workflow = ShopAIAgentWorkflow()

class ChatRequest(BaseModel):
    session_id: Optional[str] = "default-session"
    message: str

class ChatResponse(BaseModel):
    session_id: str
    message: str
    recommended_product: Optional[dict] = None
    products: List[dict] = []
    suggestions: List[str] = []

@router.post("", response_model=ChatResponse)
async def send_chat_message(req: ChatRequest):
    session_id = req.session_id or f"session-{int(time.time())}"
    
    # Nạp lịch sử trước đó nếu có
    await session_memory.load_session_from_db(session_id)
    history = session_memory.get_messages(session_id)
    
    # Khởi tạo state cho workflow
    state = AgentState(
        session_id=session_id,
        user_query=req.message,
        messages=list(history)
    )
    
    result_state = await workflow.execute(state)
        
    return ChatResponse(
        session_id=session_id,
        message=result_state.final_response,
        recommended_product=result_state.recommended_product.model_dump() if result_state.recommended_product else None,
        products=[p.model_dump() for p in result_state.found_products],
        suggestions=result_state.suggested_questions
    )

@router.post("/stream")
async def chat_stream_post(req: ChatRequest):
    """Streaming SSE Chat API (POST)."""
    session_id = req.session_id or f"session-{int(time.time())}"
    
    # Nạp lịch sử trước đó nếu có
    await session_memory.load_session_from_db(session_id)
    history = session_memory.get_messages(session_id)
    
    state = AgentState(
        session_id=session_id,
        user_query=req.message,
        messages=list(history)
    )
    
    async def sse_generator():
        try:
            async for event_item in workflow.execute_stream(state):
                yield {
                    "event": event_item["event"],
                    "data": json.dumps(event_item["data"], ensure_ascii=False)
                }
        except Exception as e:
            logger.error(f"⚠️ [SSE Stream Error]: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False)
            }

    return EventSourceResponse(sse_generator())

@router.get("/stream")
async def chat_stream_get(session_id: Optional[str] = "default-session", message: str = ""):
    """Streaming SSE Chat API (GET) phục vụ Native HTML5 EventSource."""
    req = ChatRequest(session_id=session_id, message=message)
    return await chat_stream_post(req)

@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    await session_memory.load_session_from_db(session_id)
    messages = session_memory.get_messages(session_id)
    return {"session_id": session_id, "messages": [m.model_dump() for m in messages]}
