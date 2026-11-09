"""Dữ liệu vào / ra của API chat."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.schemas.product import ProductOut

MAX_MESSAGE_CHARS = 2000
MAX_SESSION_ID_CHARS = 100
MAX_PLATFORM_CHARS = 50
MAX_COMPARE_PRODUCTS = 10


class ChatRequest(BaseModel):
    session_id: str | None = Field(None, max_length=MAX_SESSION_ID_CHARS)
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    platform: str | None = Field("all", max_length=MAX_PLATFORM_CHARS)
    language: Literal["vi", "en"] = "vi"  # ngôn ngữ trả lời theo Cài đặt của người dùng


class CompareRequest(BaseModel):
    session_id: str | None = Field(None, max_length=MAX_SESSION_ID_CHARS)
    products: list[ProductOut] = Field(min_length=2, max_length=MAX_COMPARE_PRODUCTS)


class ChatResponse(BaseModel):
    session_id: str
    message: str
    intent: str | None = None
    criteria: dict[str, Any] | None = None
    recommended_product: dict[str, Any] | None = None
    products: list[dict[str, Any]] = []
    suggestions: list[str] = []
    comparison: dict[str, Any] | None = None
    clarification: dict[str, Any] | None = None
    relaxed_search: str | None = None
    search_notes: list[str] = []
    llm_provider: str = "groq"
    langsmith_tracing: bool = False
