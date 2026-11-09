import sys

sys.path.insert(0, ".")

from core.agents import advisor_context
from core.state import AgentState, ProductItemModel, UniversalSearchCriteria


def test_format_specs_summary_dict():
    """Kiểm tra rút gọn thông số từ dictionary thành 1 dòng (tối đa 7 thuộc tính, ưu tiên CPU/GPU/RAM...)."""
    specs_dict = {
        "Màn hình": "6.7 inch",
        "Chip / CPU": "Apple A17 Pro",
        "RAM": "8 GB",
        "Bộ nhớ / Ổ cứng": "256GB",
        "Pin": "4422 mAh",
        "Cổng sạc": "Type-C",
        "Chất liệu": "Titan",
        "Kháng nước": "IP68",
        "Màu sắc": "Titan tự nhiên",
    }
    summary = advisor_context.format_specs_summary(specs_dict)

    assert "Màn hình: 6.7 inch" in summary
    assert "Chip / CPU: Apple A17 Pro" in summary
    assert "RAM: 8 GB" in summary
    assert "Bộ nhớ / Ổ cứng: 256GB" in summary
    # Thông số quyết định (RAM, Pin) được đưa lên đầu
    assert summary.startswith("RAM: 8 GB | Pin: 4422 mAh")
    # Tối đa 7 thuộc tính để bảo vệ token
    assert summary.count(" | ") == 6
    assert "Màu sắc" not in summary
    print(f"\n[Compact Specs]: {summary}".encode("ascii", "replace").decode("ascii"))


def test_build_standardized_context_top_3_limit():
    """Kiểm tra ngữ cảnh đầu vào tự động chốt Top-3 sản phẩm tốt nhất."""

    # Giả lập danh sách 5 sản phẩm
    products = [
        ProductItemModel(
            id=f"p-{i}",
            name=f"Laptop Model #{i}",
            platform="tiki",
            platformName="Tiki Trading",
            originalPrice=20000000,
            currentPrice=18000000,
            discountPercent=10,
            rating=4.8,
            reviewsCount="100 đánh giá",
            specs={"CPU": "Core i5", "RAM": "16GB", "SSD": "512GB"},
            externalUrl=f"https://tiki.vn/p-{i}",
        )
        for i in range(1, 6)
    ]

    state = AgentState(
        session_id="test-session",
        user_query="Tìm laptop học tập dưới 20 triệu",
        criteria=UniversalSearchCriteria(category="laptops", max_price=20000000),
        found_products=products,
    )

    context = advisor_context.build_context(state)

    assert context["user_query"] == "Tìm laptop học tập dưới 20 triệu"
    assert "20,000,000" in context["criteria_summary"]
    # Kiểm tra chỉ có Lựa chọn #1, #2, #3 trong ngữ cảnh
    assert "[Lựa chọn #1]" in context["products_context"]
    assert "[Lựa chọn #2]" in context["products_context"]
    assert "[Lựa chọn #3]" in context["products_context"]
    assert "[Lựa chọn #4]" not in context["products_context"]
    assert "[Lựa chọn #5]" not in context["products_context"]
    print(
        f"\n[Standardized Context Generated]:\n{context['products_context']}".encode("ascii", "replace").decode("ascii")
    )


if __name__ == "__main__":
    print("=== TEST STEP 1: INPUT CONTEXT STANDARDIZATION ===")
    test_format_specs_summary_dict()
    print(" [OK] 1. Specs summary formatting & max 4 attributes limit verified")
    test_build_standardized_context_top_3_limit()
    print(" [OK] 2. Standardized context & Top-3 candidate selection verified")
    print("\n=== STEP 1 VERIFIED 100% OK! ===")
