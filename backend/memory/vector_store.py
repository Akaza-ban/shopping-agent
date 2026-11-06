from typing import List, Dict, Any

class VectorStoreService:
    """Tầng trừu tượng phục vụ RAG (Vector embeddings cho đánh giá và danh mục sản phẩm)."""

    def __init__(self):
        self._documents: List[Dict[str, Any]] = []

    def add_documents(self, docs: List[Dict[str, Any]]):
        self._documents.extend(docs)

    async def search_relevant_reviews(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        # Tìm kiếm dựa trên từ khóa trong documents đã được lưu
        matches = [d for d in self._documents if any(w in str(d).lower() for w in query.lower().split())]
        return matches[:top_k]

vector_store = VectorStoreService()
