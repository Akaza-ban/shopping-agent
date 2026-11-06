"""Dữ liệu vào / ra của API chat."""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel

from src.schemas.product import ProductOut


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    platform: Optional[str] = "all"
    language: Literal["vi", "en"] = "vi"  # ngôn ngữ trả lời theo Cài đặt của người dùng


class CompareRequest(BaseModel):
    session_id: Optional[str] = None
    products: List[ProductOut]


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
