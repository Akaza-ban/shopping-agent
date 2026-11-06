from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import chat_router, products_router, link_parser_router, alerts_router
from ..config.settings import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Hệ thống Backend Multi-Agent thông minh phục vụ ShopAI Frontend",
    version="1.0.0"
)

# Cấu hình CORS để Frontend G (React/Next.js chạy ở port 3000) có thể gọi trực tiếp
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

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
