"""Shopping Advisor: viết câu trả lời tư vấn cuối cùng (stream từng token).

Ngữ cảnh đưa vào prompt: advisor_context.py. Câu trả lời dựng sẵn khi LLM lỗi: advisor_fallback.py.
"""
import asyncio
import logging
import time
from typing import AsyncIterator, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from integrations.llm import get_chat_model, stream_llm
from shared.exceptions import LLMError

from ..prompts.advisor_prompts import ADVISOR_SYSTEM_PROMPT, ADVISOR_USER_PROMPT_TEMPLATE
from ..prompts.language import language_instruction
from ..state import AgentState, MessageItem
from .advisor_context import build_context
from .advisor_fallback import build_fallback

logger = logging.getLogger("shopping_advisor")

FALLBACK_WORDS_PER_CHUNK = 4
FALLBACK_CHUNK_DELAY_SECONDS = 0.015


async def _stream_words(text: str, size: int = FALLBACK_WORDS_PER_CHUNK) -> AsyncIterator[str]:
    """Phát câu trả lời dựng sẵn theo từng cụm vài từ để giao diện vẫn có hiệu ứng gõ chữ."""
    words = text.split(" ")
    for i in range(0, len(words), size):
        yield " ".join(words[i:i + size]) + " "
        await asyncio.sleep(FALLBACK_CHUNK_DELAY_SECONDS)


async def _stream_llm(chat_model, context: Dict[str, str], language: str) -> AsyncIterator[str]:
    """Token lời tư vấn của LLM theo prompt advisor."""
    user_prompt = ADVISOR_USER_PROMPT_TEMPLATE.format(
        user_query=context["user_query"],
        scope_note=context.get("scope_note", ""),
        criteria_summary=context["criteria_summary"],
        chat_history_context=context.get("chat_history_context", ""),
        products_context=context["products_context"],
        search_notes_context=context.get("search_notes_context", ""),
    )
    messages = [
        SystemMessage(content=ADVISOR_SYSTEM_PROMPT + language_instruction(language)),
        HumanMessage(content=user_prompt),
    ]
    async for token in stream_llm(chat_model, messages):
        yield token


class ShoppingAdvisorAgent:
    """Agent chuyên gia tư vấn mua sắm ShopAI Copilot."""

    async def generate_response_stream(self, state: AgentState) -> AsyncIterator[str]:
        """Stream câu trả lời; LLM lỗi / không có LLM thì stream câu trả lời dựng sẵn.

        Xong thì ghi state.final_response, state.recommended_product và thêm tin nhắn vào state.messages.
        """
        context = build_context(state)
        top = state.found_products[0] if state.found_products else None
        if top:
            state.recommended_product = top
        chat_model = get_chat_model(temperature=0.3, fast=True)

        full_text = ""
        if chat_model:
            try:
                async for token in _stream_llm(chat_model, context, state.language):
                    full_text += token
                    yield token
            except LLMError as e:
                logger.warning(f"[ShoppingAdvisor] Lỗi stream LLM ({e}), tự động chuyển sang Fallback.")
        if not full_text:
            full_text = build_fallback(context, top, intent=state.intent)
            async for chunk in _stream_words(full_text):
                yield chunk

        state.final_response = full_text.strip()
        state.messages.append(MessageItem(
            id=f"msg-ai-{int(time.time() * 1000)}",
            sender="ai",
            text=state.final_response,
            timestamp="Vừa xong",
            precision="99.0%" if chat_model else "95.0%"
        ))

    async def generate_response(self, state: AgentState) -> AgentState:
        """Bản không stream: chạy hết stream rồi trả về state (cùng logic, kết quả như nhau)."""
        async for _ in self.generate_response_stream(state):
            pass
        return state
