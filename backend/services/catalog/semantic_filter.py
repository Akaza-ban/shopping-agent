import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from src.config import settings, get_chat_model

logger = logging.getLogger("semantic_filter")

PRODUCT_ONTOLOGY_SYSTEM_PROMPT = """Bạn là chuyên gia thẩm định dữ liệu thương mại điện tử cấp cao (E-commerce Product Ontology Arbiter).
Nhiệm vụ của bạn là phân tích ngữ nghĩa sâu sắc để xác định các sản phẩm cào về từ sàn có đúng là ĐỐI TƯỢNG CHÍNH mà người dùng muốn tìm hay không.

 BẢN THỂ HỌC PHÂN LOẠI (ONTOLOGY REASONING RULES) 
1. THỰC THỂ NGUYÊN CHIẾC ĐỘC LẬP (PRIMARY STANDALONE ENTITY):
   - Là bản thân sản phẩm hoàn chỉnh, có khả năng hoạt động/sử dụng độc lập đúng như nhu cầu cốt lõi của người mua.
   - Ví dụ:
     * Tìm "điện thoại iPhone 17" -> Phải là chiếc điện thoại iPhone 17 nguyên máy.
     * Tìm "nước hoa Dior Sauvage" -> Phải là chai nước hoa chính hãng nguyên bản.
     * Tìm "đồng hồ Rolex Submariner" -> Phải là chiếc đồng hồ.
     * Tìm "máy ảnh Sony A7 IV" -> Phải là thân máy (body) hoặc máy kèm ống kính kit.

2. VẬT PHẨM BỔ TRỢ / PHỤ KIỆN ĂN THEO (ACCESSORY / PERIPHERAL / DERIVATIVE):
   - Bất kỳ món đồ nào sinh ra để: PHỤC VỤ, BẢO VỆ, TRANG TRÍ, CẮM VÀO, ĐỰNG, SỬA CHỮA hoặc TƯƠNG THÍCH VỚI Thực thể mục tiêu đều là PHỤ KIỆN.
   - QUY TẮC SUY LUẬN: Nếu người dùng KHÔNG chủ đích tìm phụ kiện mà sản phẩm là thứ dùng "CHO", "DÀNH CHO", "GẮN VÀO", "BẢO VỆ", "TƯƠNG THÍCH VỚI" đối tượng tìm kiếm (như ốp lưng, bao da, dán cường lực, dây đeo, cáp sạc, dock sạc, lọ chiết rỗng, túi bọc, cúc áo, ngàm chuyển, khay sim...) -> BẮT BUỘC LOẠI BỎ NGAY LẬP TỨC.

3. HÀNG GIẢ LẬP / LINH KIỆN (REPLICA / PARTS / DUMMY):
   - Mô hình trưng bày, đồ chơi bản sao mini, sách hướng dẫn, vỏ hộp rỗng, linh kiện rã máy -> BẮT BUỘC LOẠI BỎ.

4. KHÔNG LOẠI VÌ THIẾU THÔNG SỐ:
   - Chỉ phán định LOẠI sản phẩm (máy chính hay phụ kiện/hàng giả/không liên quan).
   - KHÔNG được loại một sản phẩm chính chỉ vì tên không ghi rõ thông số (GPU, CPU, dung lượng...). Việc xác minh thông số do bước khác đảm nhiệm.

5. THẨM ĐỊNH SỰ TỒN TẠI TRÊN THỊ TRƯỜNG (MARKET AVAILABILITY CHECK):
   - Nếu sản phẩm chưa từng được thương mại hóa chính thức (ví dụ: model tương lai chưa ra mắt) và toàn bộ kết quả trên sàn chỉ là hàng phụ kiện ăn theo -> LOẠI BỎ TOÀN BỘ và đánh dấu "is_target_available_on_market": false.

=== ĐỊNH DẠNG ĐẦU RA (STRICT JSON ONLY) ===
BẮT BUỘC trả về JSON strictly theo định dạng sau (không viết bất kỳ lời dẫn hay markdown nào ngoài JSON):
{"matched_product_ids": ["id_máy_thật_1", "id_máy_thật_2"], "is_target_available_on_market": true}
Chỉ trả về đúng hai trường trên, không giải thích (câu trả lời càng ngắn càng tốt để giảm độ trễ)."""


def _parse_json(raw: str) -> Dict[str, Any]:
    """JSON trong câu trả lời của LLM (bỏ khối ```json ... ``` nếu có)."""
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    return json.loads(text)


def _user_prompt(query: str, products: List[Dict[str, Any]]) -> str:
    """Chỉ gửi id, tên, giá, sàn (tiết kiệm token và giảm độ trễ)."""
    compact_items = [
        {
            "id": str(p.get("id")),
            "name": str(p.get("name")),
            "price": float(p.get("currentPrice", 0)),
            "platform": str(p.get("platformName", "")),
        }
        for p in products
    ]
    return f"""Yêu cầu tìm kiếm của người dùng: "{query}"

Danh sách sản phẩm cào được từ sàn TMĐT:
{json.dumps(compact_items, ensure_ascii=False, separators=(",", ":"))}

Hãy thẩm định theo các quy tắc bản thể học và trả về JSON."""


class LLMSemanticFilter:

    async def filter_products(
        self,
        query: str,
        products: List[Dict[str, Any]],
        criteria: Optional[Any] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Chỉ giữ máy chính đúng thứ người dùng tìm (bỏ phụ kiện ăn theo, hàng mô hình); LLM lỗi thì giữ nguyên."""
        if not products:
            return [], {"is_target_available_on_market": False, "explanation": "Không có sản phẩm đầu vào"}
        if criteria and getattr(criteria, "is_accessory", False):
            logger.info(f"ℹ [Semantic Filter] Người dùng chủ đích tìm phụ kiện cho '{query}', giữ nguyên 100% kết quả.")
            return products, {"is_target_available_on_market": True, "is_accessory_search": True}

        chat_model = get_chat_model(temperature=0.0, fast=True)
        if not chat_model:
            logger.warning("Không khởi tạo được Chat Model, tạm thời giữ nguyên danh sách cào.")
            return products, {"is_target_available_on_market": True, "used_llm": False}
        try:
            return await self._judge(chat_model, query, products)
        except Exception as err:
            logger.warning(f"[LLM Ontology Filter Error]: {err}. Giữ nguyên danh sách an toàn.")
            return products, {"is_target_available_on_market": True, "used_llm": False, "error": str(err)}

    @staticmethod
    async def _judge(chat_model, query: str, products: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        response = await chat_model.ainvoke([
            SystemMessage(content=PRODUCT_ONTOLOGY_SYSTEM_PROMPT),
            HumanMessage(content=_user_prompt(query, products)),
        ])
        parsed = _parse_json(response.content if hasattr(response, "content") else str(response))
        matched_ids = set(parsed.get("matched_product_ids", []))
        is_available = bool(parsed.get("is_target_available_on_market", True))
        explanation = str(parsed.get("explanation", ""))
        final_products = [p for p in products if str(p.get("id")) in matched_ids]
        logger.info(
            f"[LLM Ontology Filter] Query: '{query}' | Input: {len(products)} -> "
            f"Giữ lại: {len(final_products)} máy thật. Có trên thị trường: {is_available}. Giải thích: {explanation}"
        )
        return final_products, {
            "is_target_available_on_market": is_available,
            "explanation": explanation,
            "rejected_items": parsed.get("rejected_items", []),
            "used_llm": True,
        }


semantic_filter = LLMSemanticFilter()
