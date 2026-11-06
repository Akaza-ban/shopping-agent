"""Điểm vào của API: tạo app FastAPI, gắn middleware, xử lý lỗi, các router và vòng đời khởi động / tắt."""
import sys
import asyncio

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except AttributeError:  # bản Python không còn WindowsProactorEventLoopPolicy
        pass

from fastapi import Depends, FastAPI

from shared.config import settings
from shared.logging_config import setup_logging
from src.dependencies.auth import require_user
from src.errors import register_error_handlers
from src.lifespan import lifespan
from src.middleware import setup_middleware
from src.routes import (
    alerts_router, auth_router, chat_router, crawler_router, feedback_router, link_parser_router, policies_router,
    products_router,
)

setup_logging()

app = FastAPI(
    title=settings.APP_NAME,
    description="Hệ thống Backend Multi-Agent thông minh (Hỗ trợ Groq / OpenRouter & LangSmith Tracing)",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI tại http://localhost:8000/docs
    redoc_url="/redoc",    # Redoc UI tại http://localhost:8000/redoc
    lifespan=lifespan,
)
setup_middleware(app)
register_error_handlers(app)

# (router, cần đăng nhập cho mọi endpoint không). Router không đánh dấu tự kiểm tra quyền trong từng endpoint.
ROUTERS = [
    (auth_router, False),
    (chat_router, False),
    (products_router, True),
    (link_parser_router, True),
    (alerts_router, False),
    (crawler_router, False),
    (policies_router, True),
    (feedback_router, False),
]
for router, login_required in ROUTERS:
    dependencies = [Depends(require_user)] if login_required else []
    for prefix in ("/api", "/api/v1"):
        app.include_router(router, prefix=prefix, dependencies=dependencies)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "ShopAI Agent Backend is running!",
        "docs_url": "http://localhost:8000/docs",
        "llm_provider": settings.LLM_PROVIDER,
        "langsmith_tracing": settings.LANGCHAIN_TRACING_V2.lower() in ("true", "1") and bool(settings.LANGCHAIN_API_KEY)
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "provider": settings.LLM_PROVIDER,
        "langsmith_project": settings.LANGCHAIN_PROJECT,
        "langsmith_tracing_enabled": settings.LANGCHAIN_TRACING_V2.lower() in ("true", "1")
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host=settings.HOST, port=settings.PORT, reload=True)
