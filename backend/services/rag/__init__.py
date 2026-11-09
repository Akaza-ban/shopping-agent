"""RAG sản phẩm — xem docs/11-rag.md."""

from services.rag.scoring import Thresholds
from services.rag.service import DEFAULT_CHROMA_PATH, ProductRAGService

# Instance dùng chung trong toàn bộ backend
rag_service = ProductRAGService()

__all__ = ["DEFAULT_CHROMA_PATH", "ProductRAGService", "Thresholds", "rag_service"]
