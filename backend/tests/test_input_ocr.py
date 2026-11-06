import asyncio
import json
import sys
import os

# Đảm bảo đường dẫn import
sys.path.append(os.path.abspath('.'))

from core.state import AgentState
from core.agents.orchestrator import OrchestratorAgent


# Danh sách các câu hỏi test mẫu đa dạng các ngành hàng
SAMPLE_QUERIES = [
    "Tìm cho tôi laptop dưới 30 triệu với CPU intel core i7 và card RTX 3050",
    "Tôi muốn tìm 1 chiếc chảo chống dính thương hiệu lớn",
    "Tìm tai nghe Sony chống ồn pin trên 20 tiếng tầm giá 4 triệu",
    "Tìm iPhone 15 Pro Max 256GB màu titan tự nhiên chính hãng giá tốt nhất",
    "Tìm giày chạy bộ Nike nam size 42 êm chân dưới 2 triệu rưỡi",
    "So sánh laptop Dell XPS 13 và Macbook Air M2",
    "Có voucher Shopee giảm giá nào cho đơn hàng công nghệ 500k không"
]

async def run_extraction(query: str):
    orchestrator = OrchestratorAgent()
    state = AgentState(
        session_id=f"test-{abs(hash(query)) % 10000}",
        user_query=query
    )
    result = await orchestrator.route(state)

    print("\n" + "=" * 80)
    print(f"📥 CÂU LỆNH ĐẦU VÀO: \"{query}\"")
    print("=" * 80)
    print(f"🎯 Ý định (Intent): {result.intent}")

    if result.criteria:
        c = result.criteria
        print(f"📂 Ngành hàng (Category):       {c.category_name} ({c.category})")
        print(f"📦 Loại sản phẩm (Product Type): {c.product_type or 'Chưa xác định'}")
        
        # Mức giá
        min_p = f"{c.min_price:,.0f} đ" if c.min_price else "Không giới hạn"
        max_p = f"{c.max_price:,.0f} đ" if c.max_price else "Không giới hạn"
        print(f"💰 Ngân sách (Budget):          {min_p} -> {max_p}")
        
        # Thương hiệu
        print(f"🏷️  Thương hiệu chỉ định:        {c.brands if c.brands else 'Chưa nêu cụ thể'}")
        if c.brand_tier:
            print(f"⭐ Phân khúc thương hiệu:       {c.brand_tier}")
        if c.suggested_brands:
            print(f"💡 Gợi ý thương hiệu đầu ngành:  {', '.join(c.suggested_brands)}")

        # Thuộc tính động
        print(f"⚙️  Thông số bóc tách (Specs):   {json.dumps(c.attributes, ensure_ascii=False)}")
        
        # Mục đích & Ưu tiên
        if c.usage_purpose:
            print(f"🎯 Nhu cầu sử dụng:             {c.usage_purpose}")
        if c.priority:
            print(f"⚡ Tiêu chí ưu tiên:           {c.priority}")

        print(f"🔍 Từ khóa tinh gọn (Cleaned):   \"{c.cleaned_query}\"")
        
        print("\n📄 TOÀN BỘ JSON DỮ LIỆU:")
        print(json.dumps(c.model_dump(), ensure_ascii=False, indent=2))
    else:
        print("⚠️ Không bóc tách được tiêu chí (Intent thông thường).")

async def main():
    print("=" * 80)
    print("🚀 BỘ KIỂM THỬ BÓC TÁCH THÔNG TIN ĐẦU VÀO (INPUT OCR & ENTITY EXTRACTOR)")
    print("=" * 80)

    # Nếu người dùng truyền câu lệnh qua tham số dòng lệnh
    if len(sys.argv) > 1:
        custom_query = " ".join(sys.argv[1:])
        await run_extraction(custom_query)
        return

    # Chạy 3 kịch bản tiêu biểu: Laptop, Chảo gia dụng, Tai nghe âm thanh
    for query in SAMPLE_QUERIES[:3]:
        await run_extraction(query)

    print("\n" + "=" * 80)
    print("💡 MẸO TEST: Bạn có thể test câu bất kỳ bằng cách chạy:")
    print("python tests/test_input_ocr.py \"câu hỏi của bạn ở đây\"")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
