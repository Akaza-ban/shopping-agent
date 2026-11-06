import re
from typing import List, Dict, Any, Optional
from .base import BaseTool
from services.catalog.categories import known_category
from shared.categories import LABELS
from shared.spec_rows import PREFERRED_SPEC_ROWS
from services.catalog.reviews import rating_text

MAX_SPEC_ROWS = 10


def product_category(product: Dict[str, Any]) -> Optional[str]:
    """Ngành hàng đã quy đổi từ danh mục của sàn; None khi chưa rõ hoặc là "other" (không đủ căn cứ để so)."""
    code = known_category(product)
    return code if code and code != "other" else None


def mixed_categories(products: List[Dict[str, Any]]) -> List[str]:
    """Các ngành hàng khác nhau trong danh sách (theo thứ tự xuất hiện); có từ 2 ngành trở lên là không so sánh được."""
    found: List[str] = []
    for p in products:
        code = product_category(p)
        if code and code not in found:
            found.append(code)
    return found if len(found) >= 2 else []


def _num(text: Any) -> Optional[float]:
    m = re.search(r"(\d+(?:[.,]\d+)?)", str(text or ""))
    return float(m.group(1).replace(",", ".")) if m else None


class SpecComparatorTool(BaseTool):
    name = "spec_comparator"
    description = "So sánh giá, đánh giá, bảo hành, đổi trả và thông số kỹ thuật chuẩn hóa giữa các sản phẩm"

    def build_table(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bảng so sánh {columns, rows}; mỗi hàng có best_index = cột tốt nhất (giá thấp nhất, điểm / đánh giá cao nhất)."""
        columns = [
            {"id": p.get("id"), "name": p.get("name"), "platformName": p.get("platformName"), "externalUrl": p.get("externalUrl")}
            for p in products
        ]
        rows: List[Dict[str, Any]] = []

        def add_row(label: str, values: List[Any], best: Optional[str] = None, nums: Optional[List[Optional[float]]] = None):
            best_index = None
            if best and nums and sum(n is not None for n in nums) >= 2:
                candidates = [(n, i) for i, n in enumerate(nums) if n is not None]
                best_index = (min if best == "min" else max)(candidates)[1]
            rows.append({"label": label, "values": values, "best_index": best_index})

        prices = [float(p.get("currentPrice") or 0) for p in products]
        add_row("Giá hiện tại", [f"{v:,.0f} đ" for v in prices], "min", prices)
        add_row("Giảm giá", [f"{int(p.get('discountPercent') or 0)}%" for p in products])
        add_row("Điểm phù hợp", [f"{p.get('aiMatchScore', '—')}" for p in products], "max", [_num(p.get("aiMatchScore")) for p in products])
        ratings = [float(p.get("rating") or 0) or None for p in products]
        add_row(
            "Đánh giá",
            [rating_text(r, p.get("reviewsCount")) for r, p in zip(ratings, products)],
            "max", ratings
        )
        add_row("Nơi bán", [p.get("platformName", "") for p in products])
        add_row("Bảo hành", [p.get("warranty") or "Chưa rõ" for p in products])
        add_row("Đổi trả", [p.get("returnPolicy") or "Theo chính sách của sàn" for p in products])

        specs_list = [p.get("specs") if isinstance(p.get("specs"), dict) else {} for p in products]
        spec_keys = [k for k in PREFERRED_SPEC_ROWS if sum(1 for s in specs_list if s.get(k)) >= 2]
        for key in spec_keys[:MAX_SPEC_ROWS]:
            values = [s.get(key, "—") for s in specs_list]
            best = "max" if key in ("RAM", "Lưu trữ", "Pin", "Tần số quét", "Khối lượng giặt", "Dung tích") else (
                "min" if key == "Khối lượng" else None
            )
            add_row(key, values, best, [_num(v) for v in values] if best else None)

        return {"columns": columns, "rows": rows}

    @staticmethod
    def table_to_markdown(table: Dict[str, Any], max_cell: int = 45) -> str:
        cols = table.get("columns") or []
        if not cols:
            return ""
        header = "| Tiêu chí | " + " | ".join(f"#{i + 1} {str(c.get('name', ''))[:30]}" for i, c in enumerate(cols)) + " |"
        sep = "|---" * (len(cols) + 1) + "|"
        lines = [header, sep]
        for row in table.get("rows", []):
            cells = []
            for i, v in enumerate(row["values"]):
                cell = str(v).replace("|", "/")[:max_cell]
                cells.append(f"**{cell}**" if row.get("best_index") == i else cell)
            lines.append(f"| {row['label']} | " + " | ".join(cells) + " |")
        return "\n".join(lines)

    async def run(self, products: List[Dict[str, Any]], same_kind: Optional[bool] = None) -> Dict[str, Any]:
        """`same_kind`: kết luận cùng loại hay không do nơi gọi đã hỏi (khi ngành hàng chưa đủ để tự kết luận)."""
        if not products:
            return {"status": "empty", "message": "Không có sản phẩm để so sánh"}

        categories = mixed_categories(products)
        if categories or same_kind is False:
            labels = f" ({', '.join(LABELS[c] for c in categories)})" if categories else ""
            return {
                "status": "mixed_categories",
                "categories": categories,
                "total_compared": len(products),
                "recommendation": (
                    f"Không so sánh trực tiếp được: các sản phẩm thuộc những loại khác nhau{labels}, "
                    "phục vụ nhu cầu khác nhau nên không có tiêu chí chung để chọn ra sản phẩm tốt hơn. "
                    "Hãy chọn các sản phẩm cùng loại để so sánh, hoặc cho biết nhu cầu chính để được tư vấn nên ưu tiên loại nào."
                ),
                "table": None,
                "markdown": "",
            }

        sorted_by_price = sorted(products, key=lambda x: x.get("currentPrice", float("inf")))
        cheapest = sorted_by_price[0]
        best_match = max(products, key=lambda x: x.get("aiMatchScore", 0))
        rated = [p for p in products if float(p.get("rating") or 0) > 0]
        best_rated = max(rated, key=lambda x: float(x.get("rating") or 0)) if rated else None
        price_diff = sorted_by_price[-1].get("currentPrice", 0) - cheapest.get("currentPrice", 0)

        parts = [f"Phù hợp nhất: {best_match.get('name')} ({best_match.get('aiMatchScore')} điểm)."]
        if cheapest.get("id") != best_match.get("id"):
            gap = best_match.get("currentPrice", 0) - cheapest.get("currentPrice", 0)
            parts.append(f"Rẻ nhất: {cheapest.get('name')} tại {cheapest.get('platformName')} ({cheapest.get('currentPrice', 0):,.0f} đ, rẻ hơn lựa chọn phù hợp nhất {gap:,.0f} đ).")
        else:
            parts.append("Lựa chọn phù hợp nhất cũng là lựa chọn rẻ nhất.")
        if best_rated and best_rated.get("id") not in (best_match.get("id"), cheapest.get("id")):
            parts.append(f"Đánh giá cao nhất: {best_rated.get('name')} ({best_rated.get('rating')}/5).")
        parts.append(f"Chênh lệch giá cao nhất - thấp nhất: {price_diff:,.0f} đ.")

        table = self.build_table(products)
        return {
            "total_compared": len(products),
            "best_deal": cheapest,
            "best_match": best_match,
            "price_diff": price_diff,
            "recommendation": " ".join(parts),
            "table": table,
            "markdown": self.table_to_markdown(table),
        }
