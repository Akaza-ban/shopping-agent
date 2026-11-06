"""Nơi duy nhất gọi LLM: đổi lỗi của nhà cung cấp (openai, httpx, LangChain, hết thời gian chờ) thành LLMError."""
import asyncio
import json
import re
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
import openai
from langchain_core.exceptions import LangChainException
from langchain_core.messages import BaseMessage

from shared.exceptions import LLMError, LLMResponseError
from integrations.llm.client import get_chat_model, is_reachable

__all__ = ["ask_llm", "stream_llm", "parse_llm_json", "get_chat_model", "is_reachable", "LLM_PROVIDER_ERRORS"]

# Lỗi có thể đến từ nhà cung cấp LLM (TimeoutError gồm cả asyncio.TimeoutError, OSError gồm lỗi mạng)
LLM_PROVIDER_ERRORS = (openai.OpenAIError, LangChainException, httpx.HTTPError, TimeoutError, OSError)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def _content(message: Any) -> str:
    return str(getattr(message, "content", message))


async def ask_llm(model, messages: List[BaseMessage], timeout: Optional[float] = None) -> str:
    """Nội dung câu trả lời của LLM; lỗi nhà cung cấp -> LLMError."""
    if model is None:
        raise LLMError("Chưa cấu hình LLM")
    try:
        call = model.ainvoke(messages)
        response = await (asyncio.wait_for(call, timeout) if timeout else call)
    except LLM_PROVIDER_ERRORS as e:
        raise LLMError(f"Gọi LLM thất bại: {e}") from e
    return _content(response)


async def stream_llm(model, messages: List[BaseMessage]) -> AsyncIterator[str]:
    """Các token câu trả lời (bỏ token rỗng); lỗi nhà cung cấp -> LLMError."""
    if model is None:
        raise LLMError("Chưa cấu hình LLM")
    try:
        async for chunk in model.astream(messages):
            token = _content(chunk)
            if token:
                yield token
    except LLM_PROVIDER_ERRORS as e:
        raise LLMError(f"Stream LLM thất bại: {e}") from e


def parse_llm_json(raw: str) -> Dict[str, Any]:
    """Đối tượng JSON trong câu trả lời của LLM (bỏ khối ```json ... ``` nếu có); sai định dạng -> LLMResponseError."""
    text = (raw or "").strip()
    fenced = _FENCE_RE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        data = json.loads(text)
    except ValueError as e:
        raise LLMResponseError(f"LLM không trả về JSON hợp lệ: {text[:200]!r}") from e
    if not isinstance(data, dict):
        raise LLMResponseError(f"LLM trả về {type(data).__name__}, cần một đối tượng JSON")
    return data
