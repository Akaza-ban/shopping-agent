# Backend FastAPI + LangGraph. Dữ liệu (SQLite, kho RAG) nằm ở /data: trên Railway gắn volume vào /data.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATABASE_URL=sqlite+aiosqlite:////data/shopai.db \
    CHROMA_PATH=/data/chroma_db \
    ENVIRONMENT=production

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN mkdir -p /data

# Một worker: bộ đếm giới hạn tần suất, bộ nhớ hội thoại và các việc chạy nền nằm trong RAM của tiến trình
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips='*'"]
