"""Tạo LangChain chat model theo nhà cung cấp đã cấu hình (DeepSeek / OpenRouter / Groq), có model dự phòng."""
import time
import socket
import logging
from typing import Dict, Tuple
from urllib.parse import urlparse

import httpx

from shared.config import settings

logger = logging.getLogger("llm_client")

REACHABILITY_TIMEOUT_SECONDS = 1.5
REACHABLE_CACHE_SECONDS = 300    # đang tốt: 5 phút mới kiểm tra lại
UNREACHABLE_CACHE_SECONDS = 60
FAST_MODEL_TIMEOUT_SECONDS = 15.0
_reachability: Dict[str, Tuple[float, bool]] = {}


def is_reachable(base_url: str) -> bool:
    """Mở được kết nối TCP tới máy chủ của nhà cung cấp hay không (có ghi nhớ kết quả)."""
    parsed = urlparse(base_url)
    host, port = parsed.hostname, parsed.port or 443
    if not host:
        return True
    now = time.monotonic()
    expires, ok = _reachability.get(host, (0.0, False))
    if now < expires:
        return ok
    try:
        socket.create_connection((host, port), timeout=REACHABILITY_TIMEOUT_SECONDS).close()
        ok = True
    except OSError:
        ok = False
        logger.warning(f"Không kết nối được {host}, tạm bỏ qua nhà cung cấp LLM này.")
    _reachability[host] = (now + (REACHABLE_CACHE_SECONDS if ok else UNREACHABLE_CACHE_SECONDS), ok)
    return ok


def _fast_chat_model(temperature: float):
    """Model nhanh qua OpenRouter; None nếu chưa cấu hình hoặc không kết nối được."""
    from langchain_openai import ChatOpenAI

    model = settings.FAST_LLM_MODEL.strip()
    key = settings.OPENROUTER_API_KEY.strip()
    base_url = settings.OPENROUTER_BASE_URL.strip() or "https://openrouter.ai/api/v1"
    if not model or not key or not is_reachable(base_url):
        return None
    provider = settings.FAST_LLM_PROVIDER.strip()
    return ChatOpenAI(
        base_url=base_url,
        api_key=key,
        model=model,
        temperature=temperature,
        max_tokens=1200,
        timeout=httpx.Timeout(FAST_MODEL_TIMEOUT_SECONDS, connect=5.0),
        max_retries=0,
        extra_body={"provider": {"order": [provider], "allow_fallbacks": False}} if provider else None,
    )


def get_chat_model(temperature: float = 0.7, fast: bool = False):
    """Chat model: nhà cung cấp trong LLM_PROVIDER trước, các bên còn lại làm dự phòng (fast=True: thêm model nhanh lên đầu); None nếu chưa có API key."""
    from langchain_openai import ChatOpenAI

    provider = settings.LLM_PROVIDER.lower().strip()
    candidates = {
        "deepseek": (
            settings.DEEPSEEK_API_KEY.strip(),
            settings.DEEPSEEK_BASE_URL.strip() or "https://api.deepseek.com",
            settings.DEEPSEEK_MODEL.strip() or "deepseek-chat",
        ),
        "openrouter": (
            settings.OPENROUTER_API_KEY.strip(),
            settings.OPENROUTER_BASE_URL.strip() or "https://openrouter.ai/api/v1",
            settings.OPENROUTER_MODEL.strip() or "deepseek/deepseek-chat",
        ),
        "groq": (
            settings.GROQ_API_KEY.strip(),
            "https://api.groq.com/openai/v1",
            settings.GROQ_MODEL.strip() or "llama-3.3-70b-versatile",
        ),
    }
    order = [provider] + [p for p in ("deepseek", "openrouter", "groq") if p != provider]
    usable = [n for n in order if n in candidates and candidates[n][0]]
    reachable = [n for n in usable if is_reachable(candidates[n][1])] or usable

    models = []
    fast_model = _fast_chat_model(temperature) if fast else None
    if fast_model:
        models.append(fast_model)
    for name in reachable:
        key, base_url, model = candidates[name]
        try:
            models.append(ChatOpenAI(
                base_url=base_url,
                api_key=key,
                model=model,
                temperature=temperature,
                max_tokens=1200,
                timeout=httpx.Timeout(45.0, connect=5.0),
                max_retries=0 if len(reachable) > 1 or fast_model else 1,
            ))
        except ValueError as e:  
            logger.warning(f"Không thể khởi tạo {name}: {e}")

    if not models:
        logger.warning("Chưa có API key hợp lệ cho DeepSeek, OpenRouter hoặc Groq.")
        return None
    if len(models) == 1:
        return models[0]
    return models[0].with_fallbacks(models[1:])

