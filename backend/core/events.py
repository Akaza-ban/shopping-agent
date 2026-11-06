"""Các event SSE agent phát ra trong lúc xử lý (giao diện đọc theo thứ tự nhận được).

    status       {"stage", "message"}   đang ở giai đoạn nào (routing, retrieval, relaxing, upsell, comparing...)
    products     {"count", "items"}     danh sách sản phẩm tìm được
    clarification {...}                 câu hỏi làm rõ kèm lựa chọn
    comparison   {"summary", "table"}   bảng so sánh
    token        {"content"}            một đoạn câu trả lời (hiệu ứng gõ chữ)
    suggestions  [câu hỏi]              câu hỏi gợi ý tiếp theo
    done         {...}                  kết thúc lượt
"""
from typing import Any, Dict, List

from .state import ProductItemModel

Event = Dict[str, Any]


def status(stage: str, message: str) -> Event:
    return {"event": "status", "data": {"stage": stage, "message": message}}


def products(items: List[ProductItemModel]) -> Event:
    return {"event": "products", "data": {"count": len(items), "items": [p.model_dump() for p in items]}}


def clarification(data: Dict[str, Any]) -> Event:
    return {"event": "clarification", "data": data}


def comparison(summary: Any, table: Any) -> Event:
    return {"event": "comparison", "data": {"summary": summary, "table": table}}


def token(content: str) -> Event:
    return {"event": "token", "data": {"content": content}}


def suggestions(questions: List[str]) -> Event:
    return {"event": "suggestions", "data": questions}


def done(data: Dict[str, Any]) -> Event:
    return {"event": "done", "data": data}
