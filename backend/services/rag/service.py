"""RAG sản phẩm trên ChromaDB: truy xuất lai vector (bge-m3 qua API) + BM25, hợp nhất bằng RRF."""
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from services.rag.bm25 import BM25Index
from services.rag.documents import Product, build_document, build_metadata, product_from_metadata, product_id
from services.rag.embeddings import APIEmbeddings, EmbeddingError, build_default_embeddings, cosine_distance
from services.rag.filters import SearchFilters
from services.rag.scoring import Candidate, Thresholds
from services.rag.text import query_terms

logger = logging.getLogger("rag_service")

DEFAULT_CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "chroma_db")
RRF_K = 60
_FROM_CONFIG = object()


class ProductRAGService:
    def __init__(
        self,
        persist_directory: str = DEFAULT_CHROMA_PATH,
        collection_name: Optional[str] = None,
        embedder: Optional[APIEmbeddings] = None,
        max_age_days: Optional[int] = None,
        disabled_platforms: Optional[List[str]] = None,
        thresholds: Thresholds = Thresholds(),
        hybrid: bool = True,
    ):
        from src.config import settings
        self.persist_directory = persist_directory
        self.collection_name = collection_name or settings.RAG_COLLECTION
        self.embedder = embedder or build_default_embeddings()
        self.max_age_days = settings.RAG_MAX_AGE_DAYS if max_age_days is None else max_age_days
        if disabled_platforms is None:
            disabled_platforms = ["shopee", "lazada"]  # sàn đã bỏ, bản cũ trong kho không được trả về
        self.disabled_platforms = disabled_platforms
        self.thresholds = thresholds
        self.hybrid = hybrid  # False = chỉ vector (dùng để so sánh khi đánh giá)

        self._client = None
        self._collection = None
        self._bm25: Optional[BM25Index] = None
        self._bm25_lock = threading.Lock()
        self._connect()


    def _connect(self):
        try:
            os.makedirs(self.persist_directory, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=self.persist_directory, settings=ChromaSettings(anonymized_telemetry=False)
            )
            self._collection = self._get_or_create()
            logger.info(f"[ChromaDB] '{self.collection_name}' ({self.embedder.model}), {self._collection.count()} sản phẩm")
        except Exception as e:
            logger.error(f"[ChromaDB] Lỗi khởi tạo Vector Database: {e}", exc_info=True)
            self._client = self._collection = None

    def _get_or_create(self):
        return self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine", "embedding_model": self.embedder.model},
        )

    def _invalidate_bm25(self):
        self._bm25 = None

    def _bm25_index(self) -> BM25Index:
        with self._bm25_lock:
            if self._bm25 is None:
                data = self._collection.get(include=["documents", "metadatas"])
                self._bm25 = BM25Index(data["ids"], data["documents"], data["metadatas"])
            return self._bm25


    def upsert_products(self, products: List[Product], timestamps: Optional[List[int]] = None) -> int:
        """Nạp / cập nhật sản phẩm (id sản phẩm làm id tài liệu -> không trùng lặp)."""
        if not self._collection or not products:
            return 0

        ids: List[str] = []
        for p in products:
            ids.append(product_id(p, set(ids)))
        documents = [build_document(p) for p in products]
        metadatas = [
            build_metadata(pid, p, timestamps[i] if timestamps else None)
            for i, (pid, p) in enumerate(zip(ids, products))
        ]

        try:
            embeddings = self.embedder.embed_documents(documents)
        except EmbeddingError as e:
            logger.warning(f"[RAG Upsert] Bỏ qua {len(ids)} sản phẩm vì chưa tạo được embedding: {e}")
            return 0
        try:
            self._collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
        except Exception as e:
            logger.error(f"[RAG Upsert Error]: {e}", exc_info=True)
            return 0

        self._invalidate_bm25()
        logger.info(f"[RAG Upsert] {len(ids)} sản phẩm, tổng kho {self._collection.count()}")
        return len(ids)


    def _filters(self, category, min_price, max_price, platform, max_age_days) -> SearchFilters:
        return SearchFilters(
            category=category, platform=platform, min_price=min_price, max_price=max_price,
            max_age_days=self.max_age_days if max_age_days is _FROM_CONFIG else max_age_days,
            excluded_platforms=self.disabled_platforms,
        )

    def _vector_ranking(self, q_vec: List[float], filters: SearchFilters, n: int):
        kwargs: Dict[str, Any] = {
            "query_embeddings": [q_vec],
            "n_results": min(n, self._collection.count()),
            "include": ["distances"],
        }
        where = filters.where()
        if where:
            kwargs["where"] = where
        res = self._collection.query(**kwargs)
        return res["ids"][0], dict(zip(res["ids"][0], res["distances"][0]))

    def retrieve_candidates(
        self,
        query: str,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        platform: Optional[str] = None,
        n: int = 20,
        max_age_days: Any = _FROM_CONFIG,
    ) -> List[Candidate]:
        """Ứng viên trước khi áp ngưỡng, sắp theo điểm RRF."""
        if not self._collection or not query.strip() or self._collection.count() == 0:
            return []
        filters = self._filters(category, min_price, max_price, platform, max_age_days)
        terms = query_terms(query)
        bm25 = self._bm25_index()

        q_vec, vec_ids, distances = None, [], {}
        try:
            q_vec = self.embedder.embed_query(query)
            vec_ids, distances = self._vector_ranking(q_vec, filters, n)
        except EmbeddingError as e:
            logger.warning(f"[RAG] Embedding API không dùng được, chỉ tìm theo từ khóa: {e}")
        bm25_ids = bm25.top(terms, n, filters.matcher()) if (self.hybrid or q_vec is None) else []

        rrf: Dict[str, float] = {}
        for ranking in (vec_ids, bm25_ids):
            for rank, pid in enumerate(ranking):
                rrf[pid] = rrf.get(pid, 0.0) + 1.0 / (RRF_K + rank + 1)

        missing = [pid for pid in rrf if pid not in distances]
        if q_vec is not None and missing:
            got = self._collection.get(ids=missing, include=["embeddings"])
            distances.update({pid: cosine_distance(q_vec, list(e)) for pid, e in zip(got["ids"], got["embeddings"])})

        return [
            Candidate(id=pid, meta=bm25.meta(pid), rrf=score, coverage=bm25.coverage(pid, terms),
                      distance=distances.get(pid))
            for pid, score in sorted(rrf.items(), key=lambda kv: kv[1], reverse=True)
            if bm25.meta(pid) is not None
        ]

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        platform: Optional[str] = None,
        limit: int = 4,
        max_age_days: Any = _FROM_CONFIG,
    ) -> List[Product]:
        """Sản phẩm đạt ngưỡng (kèm aiMatchScore, updatedAt); [] khi không có hoặc lỗi."""
        try:
            candidates = self.retrieve_candidates(
                query, category, min_price, max_price, platform, n=max(limit * 3, 20), max_age_days=max_age_days
            )
        except Exception as e:
            logger.error(f"[RAG Search Error]: {e}", exc_info=True)
            return []

        matched = []
        for c in candidates:
            if not c.accepted(self.thresholds):
                continue
            product = product_from_metadata(c.meta)
            product["aiMatchScore"] = c.match_score(self.thresholds)
            matched.append(product)
            if len(matched) >= limit:
                break

        top = f"top {matched[0]['aiMatchScore']}%" if matched else "không có sản phẩm đạt ngưỡng"
        logger.info(f"[RAG Search] '{query}' (category={category}, price≤{max_price}) -> "
                    f"{len(matched)}/{len(candidates)} ứng viên, {top}")
        return matched


    def prune(self, max_age_days: Optional[int] = None) -> int:
        """Xóa sản phẩm quá cũ và sản phẩm của sàn đang tắt; trả về số bản ghi đã xóa."""
        if not self._collection:
            return 0
        age = self.max_age_days if max_age_days is None else max_age_days
        conds = []
        if age:
            conds.append({"updated_at": {"$lt": int(time.time()) - int(age) * 86400}})
        if self.disabled_platforms:
            conds.append({"platform": {"$in": list(self.disabled_platforms)}})
        if not conds:
            return 0
        ids = self._collection.get(where=conds[0] if len(conds) == 1 else {"$or": conds}, include=[])["ids"]
        if ids:
            self._collection.delete(ids=ids)
            self._invalidate_bm25()
            logger.info(f"[RAG Prune] Đã xóa {len(ids)} sản phẩm cũ / thuộc sàn đang tắt.")
        return len(ids)

    def delete_products(self, ids: List[str]) -> int:
        """Xóa các tài liệu theo id (VD: sản phẩm có giá sai bị guardrails loại)."""
        if not self._collection or not ids:
            return 0
        existing = self._collection.get(ids=ids, include=[])["ids"]
        if existing:
            self._collection.delete(ids=existing)
            self._invalidate_bm25()
        return len(existing)

    def corpus(self) -> List[Dict[str, Any]]:
        """Metadata của toàn bộ kho (dùng cho đánh giá / thống kê)."""
        return self._collection.get(include=["metadatas"])["metadatas"] if self._collection else []

    def count(self) -> int:
        return self._collection.count() if self._collection else 0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "status": "ready" if self._collection else "error",
            "collection_name": self.collection_name,
            "total_products": self.count(),
            "persist_directory": self.persist_directory,
            "embedding_model": self.embedder.model,
            "embedding_available": self.embedder.available,
            "max_age_days": self.max_age_days,
        }

    def clear(self) -> bool:
        """Xóa toàn bộ dữ liệu trong collection hiện tại."""
        if not (self._client and self._collection):
            return False
        try:
            self._client.delete_collection(self.collection_name)
            self._collection = self._get_or_create()
            self._invalidate_bm25()
            logger.info(f"Đã dọn dẹp sạch collection '{self.collection_name}'.")
            return True
        except Exception as e:
            logger.error(f"Lỗi khi dọn dẹp collection: {e}")
            return False
