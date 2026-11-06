"""Embedding đa ngôn ngữ qua API (mặc định BAAI bge-m3 trên OpenRouter, 1024 chiều)."""
import logging
import math
import time
from collections import OrderedDict
from typing import List, Optional

import httpx

logger = logging.getLogger("embeddings")


class EmbeddingError(RuntimeError):
    pass


class APIEmbeddings:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float = 20.0,
        query_timeout: float = 8.0,
        batch_size: int = 64,
        query_cache_size: int = 512,
    ):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").rstrip("/")
        self.model = model
        self.timeout = timeout
        self.query_timeout = query_timeout
        self.batch_size = batch_size
        self._query_cache: "OrderedDict[str, List[float]]" = OrderedDict()
        self._query_cache_size = query_cache_size
        self._cooldown_until = 0.0

    @property
    def available(self) -> bool:
        return bool(self.api_key) and time.time() >= self._cooldown_until

    def _post(self, texts: List[str], timeout: float) -> List[List[float]]:
        last_err: Optional[Exception] = None
        for attempt in range(2):
            try:
                resp = httpx.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": self.model, "input": texts},
                    timeout=timeout,
                )
                if resp.status_code != 200:
                    last_err = EmbeddingError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                    if 400 <= resp.status_code < 500 and resp.status_code != 429:
                        break  # sai key / sai model -> thử lại cũng vô ích
                else:
                    data = sorted(resp.json()["data"], key=lambda d: d["index"])
                    if len(data) != len(texts):
                        raise EmbeddingError(f"API trả {len(data)} vector cho {len(texts)} văn bản")
                    return [_l2_normalize(d["embedding"]) for d in data]
            except (httpx.HTTPError, EmbeddingError, KeyError, ValueError) as e:
                last_err = e
            if attempt == 0:
                time.sleep(1.0)
        self._cooldown_until = time.time() + 60
        raise EmbeddingError(f"Không gọi được embedding API ({self.model}): {last_err}")

    def embed_documents(self, texts: List[str], timeout: Optional[float] = None) -> List[List[float]]:
        if not self.api_key:
            raise EmbeddingError("Chưa cấu hình API key cho embedding")
        vectors: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            vectors.extend(self._post(texts[i:i + self.batch_size], timeout or self.timeout))
        return vectors

    def embed_query(self, text: str) -> List[float]:
        key = text.strip().lower()
        if key in self._query_cache:
            self._query_cache.move_to_end(key)
            return self._query_cache[key]
        if not self.available:
            raise EmbeddingError("Embedding API đang tạm ngừng sau lỗi gần nhất")
        vec = self.embed_documents([text.strip()], timeout=self.query_timeout)[0]
        self._query_cache[key] = vec
        if len(self._query_cache) > self._query_cache_size:
            self._query_cache.popitem(last=False)
        return vec


def _l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def cosine_distance(a: List[float], b: List[float]) -> float:
    """Khoảng cách cosine cho 2 vector đã chuẩn hóa (khớp `hnsw:space = cosine` của ChromaDB)."""
    return 1.0 - sum(x * y for x, y in zip(a, b))


def build_default_embeddings() -> APIEmbeddings:
    from src.config import settings
    return APIEmbeddings(
        api_key=settings.EMBEDDING_API_KEY or settings.OPENROUTER_API_KEY,
        base_url=settings.EMBEDDING_BASE_URL or settings.OPENROUTER_BASE_URL,
        model=settings.EMBEDDING_MODEL,
        timeout=settings.EMBEDDING_TIMEOUT_SECONDS,
        query_timeout=settings.EMBEDDING_QUERY_TIMEOUT_SECONDS,
    )
