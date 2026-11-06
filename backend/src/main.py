import sys
import asyncio

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.routes import chat_router, products_router, link_parser_router, alerts_router, crawler_router, auth_router, policies_router
from src.auth import require_user
from database.connection import init_db, close_db
from services.catalog.batch_crawler import batch_crawler_service
from services.pricing.watcher import price_watcher_service
from services.policy.service import ensure_seeded as seed_policies
from services.catalog.category_resolver import category_resolver
from services.pricing.category_floors import category_floors

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo CSDL SQLite và các bảng tự động khi khởi động
    await init_db()
    await category_resolver.load()
    await category_floors.refresh(force=True)
    await seed_policies()

    async def _startup_warmup():
        try:
            # Chờ 1 giây để server FastAPI sẵn sàng lắng nghe request
            await asyncio.sleep(1.0)
            if await batch_crawler_service.should_warmup():
                print("[Startup Warm-up] Phat hien CSDL can lam am, khoi dong thu thap tu dong cac mat hang HOT...")
                await batch_crawler_service.run_batch_crawl(limit_per_query=3, force_refresh=True)
                print("[Startup Warm-up] Da hoan tat lam am CSDL voi du lieu thuc!")
            else:
                print("[Startup Warm-up] Du lieu trong CSDL van con moi, bo qua thu thap nen.")
        except Exception as e:
            print(f"[Startup Warm-up] Loi tien trinh lam am CSDL: {e}")

    warmup_task = asyncio.create_task(_startup_warmup())

    # Theo dõi giá định kỳ cho các yêu cầu "báo khi giảm giá"
    price_watcher_service.interval = max(60, settings.PRICE_WATCH_INTERVAL_MINUTES * 60)
    watcher_task = asyncio.create_task(price_watcher_service.start())

    yield

    # Huy task nen neu con dang chay khi tat server
    price_watcher_service.stop()
    for task in (warmup_task, watcher_task):
        if not task.done():
            task.cancel()
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api", dependencies=[Depends(require_user)])
app.include_router(products_router, prefix="/api/v1", dependencies=[Depends(require_user)])
app.include_router(link_parser_router, prefix="/api", dependencies=[Depends(require_user)])
app.include_router(link_parser_router, prefix="/api/v1", dependencies=[Depends(require_user)])
app.include_router(alerts_router, prefix="/api")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(crawler_router, prefix="/api")
app.include_router(crawler_router, prefix="/api/v1")
app.include_router(policies_router, prefix="/api", dependencies=[Depends(require_user)])
app.include_router(policies_router, prefix="/api/v1", dependencies=[Depends(require_user)])

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
