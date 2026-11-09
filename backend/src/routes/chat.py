"""API chat với trợ lý (trả một lần hoặc stream SSE), so sánh sản phẩm, lịch sử hội thoại.

Logic nằm ở application/chat.py và application/compare.py.
"""

import json
import logging
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sse_starlette.sse import EventSourceResponse

import application.chat as chat
import application.compare as compare
from core.graph import ShopAIAgentWorkflow
from database.models import UserModel
from src.dependencies.auth import require_user
from src.dependencies.providers import get_workflow
from src.dependencies.rate_limit import rate_limit
from src.schemas.chat import (
    MAX_MESSAGE_CHARS,
    MAX_PLATFORM_CHARS,
    MAX_SESSION_ID_CHARS,
    ChatRequest,
    ChatResponse,
    CompareRequest,
)

logger = logging.getLogger("chat_route")
router = APIRouter(prefix="/chat", tags=["Chat"])
chat_limit = [Depends(rate_limit("chat"))]
STREAM_ERROR_MESSAGE = "Trợ lý đang gặp sự cố tạm thời, bạn thử lại sau ít phút nhé."


@router.post("", response_model=ChatResponse, dependencies=chat_limit)
async def send_chat_message(
    req: ChatRequest, user: UserModel = Depends(require_user), workflow: ShopAIAgentWorkflow = Depends(get_workflow)
):
    return ChatResponse(
        **await chat.send_message(workflow, user, req.message, req.session_id, req.platform, req.language)
    )


async def _stream(req: ChatRequest, user: UserModel, workflow: ShopAIAgentWorkflow) -> EventSourceResponse:
    """Mở luồng SSE: mỗi giai đoạn xử lý là một event (status, products, token, comparison, suggestions, done)."""
    _, events = await chat.stream_message(workflow, user, req.message, req.session_id, req.platform, req.language)

    async def sse_generator():
        try:
            async for event in events:
                yield {"event": event["event"], "data": json.dumps(event["data"], ensure_ascii=False)}
        except Exception as e:  # chốt chặn: lỗi giữa luồng SSE phải báo cho giao diện thay vì cắt ngang kết nối
            # Chi tiết lỗi chỉ ghi log; người dùng chỉ nhận thông báo chung (không lộ nội dung exception)
            logger.error(f"[SSE Stream Error]: {e}", exc_info=True)
            yield {"event": "error", "data": json.dumps({"error": STREAM_ERROR_MESSAGE}, ensure_ascii=False)}

    return EventSourceResponse(sse_generator())


@router.post("/stream", dependencies=chat_limit)
async def chat_stream_post(
    req: ChatRequest, user: UserModel = Depends(require_user), workflow: ShopAIAgentWorkflow = Depends(get_workflow)
):
    """Streaming SSE: mỗi giai đoạn xử lý là một event (status, products, token, comparison, suggestions, done)."""
    return await _stream(req, user, workflow)


@router.get("/stream", dependencies=chat_limit)
async def chat_stream_get(
    session_id: str | None = Query(None, max_length=MAX_SESSION_ID_CHARS),
    message: str = Query(..., min_length=1, max_length=MAX_MESSAGE_CHARS),
    platform: str | None = Query("all", max_length=MAX_PLATFORM_CHARS),
    language: Literal["vi", "en"] = "vi",
    user: UserModel = Depends(require_user),
    workflow: ShopAIAgentWorkflow = Depends(get_workflow),
):
    """Bản GET cho EventSource của trình duyệt (token truyền qua ?access_token=)."""
    req = ChatRequest(session_id=session_id, message=message, platform=platform, language=language)
    return await _stream(req, user, workflow)


@router.post("/compare")
async def compare_products(req: CompareRequest, user: UserModel = Depends(require_user)):
    """Tool so sánh cho các sản phẩm giao diện đang giữ (VD sản phẩm đã lưu)."""
    return await compare.compare([p.model_dump() for p in req.products], req.session_id)


@router.get("/history/{session_id}")
async def get_chat_history(session_id: str, user: UserModel = Depends(require_user)):
    return await chat.history(user, session_id)


@router.delete("/history/{session_id}")
async def delete_chat_history(session_id: str, user: UserModel = Depends(require_user)):
    return await chat.delete(user, session_id)
