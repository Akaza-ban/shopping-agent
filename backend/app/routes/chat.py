from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import time
from ...core.state import AgentState, MessageItem
from ...core.graph import ShopAIAgentWorkflow
from ...memory.session_manager import session_memory

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

@router.post("", response_model=ChatResponse)
async def send_chat_message(req: ChatRequest):
    session_id = req.session_id or f"session-{int(time.time())}"
    
    # Lấy lịch sử hội thoại trước đó
    history = session_memory.get_messages(session_id)
    
    # Tạo user message mới
    user_msg = MessageItem(
        id=f"msg-user-{int(time.time() * 1000)}",
        sender="user",
        text=req.message,
        timestamp="Vừa xong"
    )
    session_memory.add_message(session_id, user_msg)
    
    # Khởi tạo state cho workflow
    state = AgentState(
        session_id=session_id,
        user_query=req.message,
        messages=history + [user_msg]
    )
    
    # Chạy hệ thống Multi-Agent
    result_state = await workflow.execute(state)
    
    # Lưu tin nhắn phản hồi của AI vào memory
    if result_state.messages and result_state.messages[-1].sender == "ai":
        session_memory.add_message(session_id, result_state.messages[-1])
        
    return ChatResponse(
        session_id=session_id,
        message=result_state.final_response,
        recommended_product=result_state.recommended_product.model_dump() if result_state.recommended_product else None,
        products=[p.model_dump() for p in result_state.found_products]
    )

@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    messages = session_memory.get_messages(session_id)
    return {"session_id": session_id, "messages": [m.model_dump() for m in messages]}
