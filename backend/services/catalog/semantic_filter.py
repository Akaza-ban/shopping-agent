import json
import logging
from typing import List, Dict, Any, Tuple, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from integrations.llm import get_chat_model
from integrations.llm import ask_llm, parse_llm_json
from shared.exceptions import LLMError, LLMResponseError

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

5. KHI NGƯỜI DÙNG CHỦ ĐÍCH TÌM PHỤ KIỆN / VẬT TƯ (yêu cầu ghi rõ "chủ đích tìm phụ kiện"):
   - Đối tượng chính lúc này CHÍNH LÀ loại phụ kiện đó (VD tìm "lót chuột" -> tấm lót chuột là đối tượng chính).
   - GIỮ sản phẩm đúng là loại phụ kiện người dùng tìm; LOẠI BỎ thiết bị chính và mọi mặt hàng khác loại dù tên có nhắc tới từ khóa
     (VD tìm "lót chuột" thì loại "USB Bluetooth ... - miếng lót chuột", chuột máy tính, bàn phím).

6. THẨM ĐỊNH SỰ TỒN TẠI TRÊN THỊ TRƯỜNG (MARKET AVAILABILITY CHECK):
   - Nếu sản phẩm chưa từng được thương mại hóa chính thức (ví dụ: model tương lai chưa ra mắt) và toàn bộ kết quả trên sàn chỉ là hàng phụ kiện ăn theo -> LOẠI BỎ TOÀN BỘ và đánh dấu "is_target_available_on_market": false.

=== ĐỊNH DẠNG ĐẦU RA (STRICT JSON ONLY) ===
BẮT BUỘC trả về JSON strictly theo định dạng sau (không viết bất kỳ lời dẫn hay markdown nào ngoài JSON):
{"matched_product_ids": ["id_máy_thật_1", "id_máy_thật_2"], "is_target_available_on_market": true}
Chỉ trả về đúng hai trường trên, không giải thích (câu trả lời càng ngắn càng tốt để giảm độ trễ)."""


def _user_prompt(query: str, products: List[Dict[str, Any]], accessory_search: bool = False) -> str:
    """Chỉ gửi id, tên, giá, sàn (tiết kiệm token và giảm độ trễ)."""
    intent = ("\nNgười dùng CHỦ ĐÍCH tìm phụ kiện / vật tư này (quy tắc 5): giữ đúng loại phụ kiện đó, loại mặt hàng khác loại."
              if accessory_search else "")
    compact_items = [
        {
            "id": str(p.get("id")),
            "name": str(p.get("name")),
            "price": float(p.get("currentPrice", 0)),
            "platform": str(p.get("platformName", "")),
        }
        for p in products
    ]
    return f"""Yêu cầu tìm kiếm của người dùng: "{query}"{intent}

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
        """
        Chỉ giữ đúng thứ người dùng tìm: máy chính (bỏ phụ kiện ăn theo, hàng mô hình), hoặc đúng loại phụ kiện
        khi người dùng chủ đích tìm phụ kiện (bỏ hàng khác loại); LLM lỗi thì giữ nguyên.
        """
        if not products:
            return [], {"is_target_available_on_market": False, "explanation": "Không có sản phẩm đầu vào"}
        accessory_search = bool(criteria and getattr(criteria, "is_accessory", False))

        chat_model = get_chat_model(temperature=0.0, fast=True)
        if not chat_model:
            logger.warning("Không khởi tạo được Chat Model, tạm thời giữ nguyên danh sách cào.")
            return products, {"is_target_available_on_market": True, "used_llm": False}
        try:
            kept, meta = await self._judge(chat_model, query, products, accessory_search)
            return kept, {**meta, "is_accessory_search": accessory_search}
        except LLMError as err:
            logger.warning(f"[LLM Ontology Filter Error]: {err}. Giữ nguyên danh sách an toàn.")
            return products, {"is_target_available_on_market": True, "used_llm": False, "error": str(err)}

    @staticmethod
    async def _judge(chat_model, query: str, products: List[Dict[str, Any]],
                     accessory_search: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        raw = await ask_llm(chat_model, [
            SystemMessage(content=PRODUCT_ONTOLOGY_SYSTEM_PROMPT),
            HumanMessage(content=_user_prompt(query, products, accessory_search)),
        ])
        parsed = parse_llm_json(raw)
        ids = parsed.get("matched_product_ids", [])
        if not isinstance(ids, list):
            raise LLMResponseError(f"matched_product_ids phải là danh sách, nhận được {type(ids).__name__}")
        matched_ids = {str(i) for i in ids}
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
