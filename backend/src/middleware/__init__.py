"""Middleware chạy quanh mọi request (CORS, ghi log)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import settings
from src.middleware.request_logging import RequestLoggingMiddleware


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
