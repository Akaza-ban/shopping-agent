import os
import time
import socket
import logging
from typing import Dict, List, Literal, Optional, Tuple
from urllib.parse import urlparse

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv

# Nạp file .env từ thư mục gốc của backend
load_dotenv()

logger = logging.getLogger("config")

class Settings(BaseSettings):
    # App Information
    APP_NAME: str = "ShopAI Agent Backend"
    ENVIRONMENT: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS Origins (Hỗ trợ Frontend React G chạy ở port 3000)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173"
    ]

    # LLM PROVIDERS: DEEPSEEK, GROQ & OPENROUTER
    LLM_PROVIDER: Literal["deepseek", "groq", "openrouter"] = Field(
        default="deepseek",
        description="Lựa chọn LLM Provider chính: 'deepseek', 'groq' hoặc 'openrouter'"
    )
    
    # Cấu hình DeepSeek API trực tiếp (Bản trả tiền chính thức)
    DEEPSEEK_API_KEY: str = Field(default="")
    DEEPSEEK_MODEL: str = Field(default="deepseek-chat")
    DEEPSEEK_BASE_URL: str = Field(default="https://api.deepseek.com")

    # Cấu hình Groq API
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile")

    # Cấu hình OpenRouter API
    OPENROUTER_API_KEY: str = Field(default="")
    OPENROUTER_MODEL: str = Field(default="deepseek/deepseek-chat")
    OPENROUTER_BASE_URL: str = Field(default="https://openrouter.ai/api/v1")
    # Model nhanh, rẻ qua OpenRouter; để trống -> dùng model chính
    FAST_LLM_MODEL: str = Field(default="google/gemini-2.5-flash-lite")
    FAST_LLM_PROVIDER: str = Field(default="")

    # LANGSMITH TRACING (3 Environment Variables)
    LANGCHAIN_TRACING_V2: str = Field(default="true")
    LANGCHAIN_API_KEY: str = Field(default="")
    LANGCHAIN_PROJECT: str = Field(default="shopai-agent")
    LANGCHAIN_ENDPOINT: str = Field(default="https://api.smith.langchain.com")

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./shopai.db"

    # Chu kỳ kiểm tra giá cho tính năng theo dõi giá (phút)
    PRICE_WATCH_INTERVAL_MINUTES: int = Field(default=360)

    EMBEDDING_MODEL: str = Field(default="baai/bge-m3")
    EMBEDDING_API_KEY: str = Field(default="")
    EMBEDDING_BASE_URL: str = Field(default="")
    EMBEDDING_TIMEOUT_SECONDS: float = Field(default=20.0)
    EMBEDDING_QUERY_TIMEOUT_SECONDS: float = Field(default=8.0)
    RAG_COLLECTION: str = Field(default="products_v2")
    RAG_MAX_AGE_DAYS: int = Field(default=30)

    ADMIN_EMAILS: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Khởi tạo singleton settings
settings = Settings()

# Tự động gán biến môi trường cho LangSmith tracing
if settings.LANGCHAIN_TRACING_V2.lower() in ("true", "1"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
    if settings.LANGCHAIN_API_KEY:
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
        logger.info(f"LangSmith Tracing đã kích hoạt cho dự án: '{settings.LANGCHAIN_PROJECT}'")
    else:
        logger.warning("LANGCHAIN_TRACING_V2 được bật nhưng chưa điền LANGCHAIN_API_KEY trong .env")

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
    """Trả về LangChain Chat Model theo thứ tự ưu tiên:"""
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
        except Exception as e:
            logger.warning(f"Không thể khởi tạo {name}: {e}")

    if not models:
        logger.warning("Chưa có API key hợp lệ cho DeepSeek, OpenRouter hoặc Groq.")
        return None
    if len(models) == 1:
        return models[0]
    return models[0].with_fallbacks(models[1:])

