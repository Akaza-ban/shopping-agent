"""Cấu hình của toàn bộ backend, đọc từ biến môi trường / file .env (settings là singleton dùng chung)."""
import os
import logging
from typing import List, Literal

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

    # Email đặt lại mật khẩu (SMTP, VD Gmail: smtp.gmail.com, 587, mật khẩu ứng dụng)
    SMTP_HOST: str = Field(default="")
    SMTP_PORT: int = Field(default=587)
    SMTP_USERNAME: str = Field(default="")
    SMTP_PASSWORD: str = Field(default="")
    SMTP_FROM: str = Field(default="")
    # Địa chỉ giao diện web, dùng để tạo link trong email
    FRONTEND_URL: str = Field(default="http://localhost:3000")
    PASSWORD_RESET_TTL_MINUTES: int = Field(default=30)

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
