import json
import os
import re
from collections.abc import Callable
from typing import Any

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVAL_SET_PATH = os.path.join(_BACKEND_DIR, "tests", "fixtures", "rag_eval_set.json")


def load_eval_set(path: str = EVAL_SET_PATH) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    macros = data.get("macros", {})

    def expand(pattern: str) -> re.Pattern:
        for key, value in macros.items():
            pattern = pattern.replace(f"@{key}", value)
        return re.compile(pattern, re.IGNORECASE)

    queries = []
    for q in data["queries"]:
        q = dict(q)
        q["_name"] = [expand(p) for p in q.get("name", [])]
        q["_url"] = expand(q["url"]) if q.get("url") else None
        q["_exclude"] = expand(q["exclude"]) if q.get("exclude") else None
        queries.append(q)
    return queries


def is_relevant(q: dict[str, Any], name: str, url: str) -> bool:
    if q.get("negative"):
        return False
    if q["_exclude"] and q["_exclude"].search(name):
        return False
    by_name = bool(q["_name"]) and all(p.search(name) for p in q["_name"])
    by_url = bool(q["_url"]) and bool(q["_url"].search(url or ""))
    return by_name or by_url


def _key(name: str, url: str) -> str:
    return (url or "").split("?")[0].rstrip("/") or name


def evaluate(
    search: Callable[[dict[str, Any]], list[dict[str, Any]]],
    corpus: list[dict[str, Any]],
    queries: list[dict[str, Any]],
) -> dict[str, Any]:
    """search(q) -> danh sách sản phẩm đã xếp hạng (dict có name, externalUrl, currentPrice)."""
    rows, pos, neg = [], [], []
    for q in queries:
        ranked = _dedupe(search(q))
        if q.get("negative"):
            row = _negative_row(q, ranked)
            neg.append(row["ok"])
        else:
            row = _positive_row(q, ranked, _relevant_keys(q, corpus))
            pos.append(row)
        rows.append(row)
    return {"summary": _summary(pos, neg), "rows": rows}


def _dedupe(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bỏ kết quả trùng (cùng link, hoặc cùng tên khi không có link), giữ thứ hạng."""
    seen, ranked = set(), []
    for p in results:
        k = _key(p.get("name", ""), p.get("externalUrl", ""))
        if k not in seen:
            seen.add(k)
            ranked.append(p)
    return ranked


def _relevant_keys(q: dict[str, Any], corpus: list[dict[str, Any]]) -> set:
    """Các đáp án đúng có trong kho (đã áp ngân sách của câu hỏi)."""
    return {
        _key(m["name"], m.get("external_url", ""))
        for m in corpus
        if is_relevant(q, m["name"], m.get("external_url", ""))
        and (not q.get("max_price") or float(m.get("current_price") or 0) <= q["max_price"])
    }


def _negative_row(q: dict[str, Any], ranked: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "query": q["query"],
        "negative": True,
        "returned": len(ranked),
        "ok": len(ranked) == 0,
        "top": [p.get("name", "")[:50] for p in ranked[:3]],
    }


def _positive_row(q: dict[str, Any], ranked: list[dict[str, Any]], relevant: set) -> dict[str, Any]:
    flags = [is_relevant(q, p.get("name", ""), p.get("externalUrl", "")) for p in ranked]
    n_rel = len(relevant)
    first = next((i for i, f in enumerate(flags[:10]) if f), None)
    top5 = flags[:5]
    return {
        "query": q["query"],
        "n_relevant": n_rel,
        "returned": len(ranked),
        "hit@1": float(bool(flags[:1] and flags[0])),
        "hit@5": float(any(top5)),
        "recall@5": (sum(top5) / min(5, n_rel)) if n_rel else 0.0,
        "precision@5": (sum(top5) / len(top5)) if top5 else 0.0,
        "mrr@10": 1.0 / (first + 1) if first is not None else 0.0,
        "top": [("OK  " if f else "SAI ") + p.get("name", "")[:50] for p, f in zip(ranked[:3], flags[:3], strict=True)],
    }


def _summary(pos: list[dict[str, Any]], neg: list[bool]) -> dict[str, Any]:
    def mean(key):
        return round(sum(r[key] for r in pos) / len(pos), 3) if pos else 0.0

    return {
        "queries": len(pos),
        **{k: mean(k) for k in ("hit@1", "hit@5", "recall@5", "precision@5", "mrr@10")},
        "negatives": len(neg),
        "negative_reject_rate": round(sum(neg) / len(neg), 3) if neg else 0.0,
    }


def evaluate_service(service, queries: list[dict[str, Any]] = None) -> dict[str, Any]:
    """Đánh giá một ProductRAGService (bỏ giới hạn độ mới để kết quả không phụ thuộc ngày chạy)."""
    return evaluate(
        lambda q: service.search(
            q["query"], category=q.get("category"), max_price=q.get("max_price"), limit=10, max_age_days=None
        ),
        service.corpus(),
        queries if queries is not None else load_eval_set(),
    )
