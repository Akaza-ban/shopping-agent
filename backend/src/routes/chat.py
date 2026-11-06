from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import time
from core.state import AgentState, MessageItem
from core.graph import ShopAIAgentWorkflow
from memory.session_manager import session_memory
from src.config import settings, get_chat_model

router = APIRouter(prefix="/chat", tags=["Chat"])
workflow = ShopAIAgentWorkflow()

class ChatRequest(BaseModel):
    session_id: Optional[str] = "default-session"
    message: str
    platform: Optional[str] = "all"

class ChatResponse(BaseModel):
    session_id: str
    message: str
    intent: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    recommended_product: Optional[Dict[str, Any]] = None
    products: List[Dict[str, Any]] = []
    llm_provider: str
    langsmith_tracing: bool

@router.post("", response_model=ChatResponse)
async def send_chat_message(req: ChatRequest):
    session_id = req.session_id or f"session-{int(time.time())}"
    
    # 1. Lấy lịch sử hội thoại
    history = session_memory.get_messages(session_id)
    
    user_msg = MessageItem(
        id=f"msg-user-{int(time.time() * 1000)}",
        sender="user",
        text=req.message,
        timestamp="Vừa xong"
    )
    session_memory.add_message(session_id, user_msg)
    
    # 2. Khởi tạo Agent State
    state = AgentState(
        session_id=session_id,
        user_query=req.message,
        messages=history + [user_msg]
    )
    
    # 3. Chạy Multi-Agent workflow
    result_state = await workflow.execute(state)
    
    # Nếu client truyền tham số platform riêng biệt và criteria có target_platforms, ghi đè
    if req.platform and req.platform.lower() != "all" and result_state.criteria:
        result_state.criteria.target_platforms = [req.platform.lower()]
    
    # 4. Nếu có Chat Model cấu hình (Groq hoặc OpenRouter), gọi LLM để tinh chỉnh câu trả lời
    chat_model = get_chat_model()
    if chat_model:
        try:
            # LangSmith tracing sẽ tự động bắt lấy lệnh gọi này khi LANGCHAIN_TRACING_V2=true
            ai_response = await chat_model.ainvoke(
                f"Bạn là ShopAI Copilot. Trả lời yêu cầu mua sắm sau: {req.message}. Dữ liệu tóm tắt: {result_state.final_response}"
            )
            if hasattr(ai_response, 'content'):
                result_state.final_response = str(ai_response.content)
        except Exception as e:
            # Fallback nếu API key chưa kích hoạt hoặc hết quota
            pass
    
    # 5. Lưu kết quả vào memory
    ai_msg = MessageItem(
        id=f"msg-ai-{int(time.time() * 1000)}",
        sender="ai",
        text=result_state.final_response,
        timestamp="Vừa xong"
    )
    session_memory.add_message(session_id, ai_msg)
    
    is_tracing_enabled = settings.LANGCHAIN_TRACING_V2.lower() in ("true", "1") and bool(settings.LANGCHAIN_API_KEY)

    return ChatResponse(
        session_id=session_id,
        message=result_state.final_response,
        intent=result_state.intent,
        criteria=result_state.criteria.model_dump() if result_state.criteria else None,
        recommended_product=result_state.recommended_product.model_dump() if result_state.recommended_product else None,
        products=[p.model_dump() for p in result_state.found_products],
        llm_provider=settings.LLM_PROVIDER,
        langsmith_tracing=is_tracing_enabled
    )

@router.get("/history/{session_id}")
async def get_chat_history(session_id: str):
    messages = session_memory.get_messages(session_id)
    return {"session_id": session_id, "messages": [m.model_dump() for m in messages]}
