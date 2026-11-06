import os
import logging
from typing import List, Literal, Optional
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

    # =========================================================================
    # LLM PROVIDERS: GROQ & OPENROUTER (Thay vì giả định OpenAI)
    # =========================================================================
    LLM_PROVIDER: Literal["groq", "openrouter"] = Field(
        default="groq",
        description="Lựa chọn LLM Provider chính: 'groq' hoặc 'openrouter'"
    )
    
    # Cấu hình Groq API
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = Field(default="openai/gpt-oss-20b")

    # Cấu hình OpenRouter API
    OPENROUTER_API_KEY: str = Field(default="")
    OPENROUTER_MODEL: str = Field(default="deepseek/deepseek-chat")
    OPENROUTER_BASE_URL: str = Field(default="https://openrouter.ai/api/v1")

    # =========================================================================
    # LANGSMITH TRACING (3 Environment Variables)
    # =========================================================================
    LANGCHAIN_TRACING_V2: str = Field(default="true")
    LANGCHAIN_API_KEY: str = Field(default="")
    LANGCHAIN_PROJECT: str = Field(default="shopai-agent")
    LANGCHAIN_ENDPOINT: str = Field(default="https://api.smith.langchain.com")

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./shopai.db"

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
        logger.info(f"🔍 LangSmith Tracing đã kích hoạt cho dự án: '{settings.LANGCHAIN_PROJECT}'")
    else:
        logger.warning("⚠️ LANGCHAIN_TRACING_V2 được bật nhưng chưa điền LANGCHAIN_API_KEY trong .env")

def get_chat_model(temperature: float = 0.7):
    """
    Trả về LangChain Chat Model dựa trên cấu hình Groq hoặc OpenRouter.
    Tự động loại bỏ khoảng trắng thừa và hỗ trợ fallback thông minh.
    """
    provider = settings.LLM_PROVIDER.lower().strip()
    groq_key = settings.GROQ_API_KEY.strip()
    openrouter_key = settings.OPENROUTER_API_KEY.strip()

    # Thử Groq nếu được cấu hình
    if provider == "groq" and groq_key:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key,
                model=settings.GROQ_MODEL.strip() or "openai/gpt-oss-20b",
                temperature=temperature,
                max_tokens=1000
            )
        except Exception as e:
            logger.warning(f"Không thể khởi tạo Groq: {e}. Thử chuyển sang OpenRouter...")

    # Thử OpenRouter
    if openrouter_key:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                base_url=settings.OPENROUTER_BASE_URL.strip(),
                api_key=openrouter_key,
                model=settings.OPENROUTER_MODEL.strip(),
                temperature=temperature,
                max_tokens=1000
            )
        except Exception as e:
            logger.warning(f"Không thể khởi tạo OpenRouter: {e}")

    # Fallback lại Groq nếu chưa thử
    if groq_key and provider != "groq":
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key,
                model=settings.GROQ_MODEL.strip() or "openai/gpt-oss-20b",
                temperature=temperature,
                max_tokens=1000
            )
        except Exception as e:
            logger.warning(f"Fallback Groq thất bại: {e}")

    logger.warning("Chưa có API key hợp lệ cho Groq hoặc OpenRouter.")
    return None

