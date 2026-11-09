"""Đổi lỗi của hệ thống (shared.exceptions) thành HTTP response; route chỉ cần `raise NotFoundError(...)`."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.exceptions import DomainError, ExternalServiceError, StorageError

logger = logging.getLogger("errors")


async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message}, headers=exc.headers)


async def _service_unavailable(request: Request, exc: Exception) -> JSONResponse:
    logger.error("%s %s: %s", request.method, request.url.path, exc, exc_info=exc)
    return JSONResponse(status_code=503, content={"detail": "Dịch vụ tạm thời không khả dụng, vui lòng thử lại sau."})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error)
    app.add_exception_handler(ExternalServiceError, _service_unavailable)
    app.add_exception_handler(StorageError, _service_unavailable)
