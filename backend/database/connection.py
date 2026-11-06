from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from src.config import settings

Base = declarative_base()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    """Dependency cung cấp db session cho route."""
    async with async_session() as session:
        yield session

async def init_db():
    """Tự động khởi tạo database SQLite và các bảng nếu chưa tồn tại."""
    from . import models  # Đảm bảo tất cả model được load vào Base.metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """Đóng connection pool khi ứng dụng tắt."""
    await engine.dispose()

