import sys
import asyncio

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.routes import chat_router, products_router, link_parser_router, alerts_router, crawler_router
from database.connection import init_db, close_db
from services.batch_crawler import batch_crawler_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo CSDL SQLite và các bảng tự động khi khởi động
    await init_db()

    # Phương án 2: Tự động chạy ngầm làm ấm CSDL (Startup Warm-up) nếu kho rỗng hoặc dữ liệu > 12h
    async def _startup_warmup():
        try:
            # Chờ 1 giây để server FastAPI sẵn sàng lắng nghe request
            await asyncio.sleep(1.0)
            if await batch_crawler_service.should_warmup():
                print("⚡ [Startup Warm-up] Phat hien CSDL can lam am, khoi dong thu thap tu dong cac mat hang HOT...")
                await batch_crawler_service.run_batch_crawl(limit_per_query=3, force_refresh=True)
                print("✅ [Startup Warm-up] Da hoan tat lam am CSDL voi du lieu thuc!")
            else:
                print("✨ [Startup Warm-up] Du lieu trong CSDL van con moi, bo qua thu thap nen.")
        except Exception as e:
            print(f"⚠️ [Startup Warm-up] Loi tien trinh lam am CSDL: {e}")

    warmup_task = asyncio.create_task(_startup_warmup())

    yield

    # Huy task nen neu con dang chay khi tat server
    if not warmup_task.done():
        warmup_task.cancel()
    # Giải phóng kết nối khi tắt server
    await close_db()

app = FastAPI(
    title=settings.APP_NAME,
    description="Hệ thống Backend Multi-Agent thông minh (Hỗ trợ Groq / OpenRouter & LangSmith Tracing)",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI tại http://localhost:8000/docs
    redoc_url="/redoc",    # Redoc UI tại http://localhost:8000/redoc
    lifespan=lifespan
)


# Cấu hình CORS để Frontend G (React/Next.js tại port 3000) có thể gọi trực tiếp
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các router API
app.include_router(chat_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(link_parser_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(crawler_router, prefix="/api/v1")

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
