"""Các loại lỗi của hệ thống.

Nguyên tắc dùng:
1. Lỗi của thư viện ngoài (openai, httpx, SQLAlchemy, ChromaDB...) chỉ được bắt ở đúng chỗ gọi thư viện đó
   và đổi thành một lỗi bên dưới (`raise XxxError(...) from e`).
2. Nơi gọi chỉ bắt đúng loại lỗi mình xử lý được (VD `except LLMError` để chuyển sang fallback),
   không dùng `except Exception` - lỗi lập trình (KeyError, AttributeError...) phải hiện ra.
3. Lỗi nghiệp vụ (DomainError) được src/errors.py đổi thành HTTP response, route chỉ cần `raise`.

    AppError
    ├── ExternalServiceError         dịch vụ bên ngoài lỗi, thường có fallback
    │   ├── LLMError
    │   │   └── LLMResponseError     LLM trả lời sai định dạng
    │   ├── EmbeddingError
    │   └── CrawlerError             cào sàn / tải trang lỗi
    ├── StorageError                 lưu trữ lỗi
    │   └── DatabaseError
    └── DomainError                  lỗi nghiệp vụ, trả về client (4xx)
        ├── InvalidInputError        400
        ├── AuthenticationError      401
        ├── PermissionDeniedError    403
        ├── NotFoundError            404
        ├── ConflictError            409
        │   └── EmailAlreadyRegistered
        ├── PayloadTooLargeError     413
        ├── ValidationFailedError    422
        └── RateLimitedError         429
"""
from typing import Dict, Optional


class AppError(Exception):
    """Gốc của mọi lỗi do hệ thống tự định nghĩa."""


# Dịch vụ bên ngoài
class ExternalServiceError(AppError):
    """Dịch vụ bên ngoài (LLM, embedding API, trang của sàn) không dùng được."""


class LLMError(ExternalServiceError):
    """Gọi LLM thất bại: chưa cấu hình, mất kết nối, hết thời gian chờ, nhà cung cấp báo lỗi."""


class LLMResponseError(LLMError, ValueError):
    """LLM có trả lời nhưng sai định dạng (không phải JSON, thiếu trường, sai kiểu)."""


class EmbeddingError(ExternalServiceError, RuntimeError):
    """Không tạo được embedding (sai key, API lỗi, đang tạm ngừng sau lỗi gần nhất)."""


class CrawlerError(ExternalServiceError):
    """Cào sàn hoặc tải trang sản phẩm thất bại."""

    def __init__(self, source: str, message: str):
        super().__init__(f"[{source}] {message}")
        self.source = source


# Lưu trữ
class StorageError(AppError):
    """Lỗi tầng lưu trữ."""


class DatabaseError(StorageError):
    """Lỗi SQLite / SQLAlchemy."""


# Nghiệp vụ -> HTTP 4xx
class DomainError(AppError):
    """Lỗi nghiệp vụ trả về cho client; `message` là nội dung hiển thị cho người dùng."""

    status_code: int = 400

    def __init__(self, message: str, headers: Optional[Dict[str, str]] = None):
        super().__init__(message)
        self.message = message
        self.headers = headers


class InvalidInputError(DomainError, ValueError):
    status_code = 400


class AuthenticationError(DomainError):
    status_code = 401


class PermissionDeniedError(DomainError):
    status_code = 403


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class EmailAlreadyRegistered(ConflictError):
    def __init__(self, email: str = ""):
        super().__init__("Email này đã được đăng ký.")
        self.email = email


class PayloadTooLargeError(DomainError):
    status_code = 413


class ValidationFailedError(DomainError):
    status_code = 422


class RateLimitedError(DomainError):
    status_code = 429
