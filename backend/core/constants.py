"""Hằng số nghiệp vụ của agent (ngân sách gợi ý, số sản phẩm trả về, mức nới ngân sách...)."""
import re

# Ý định cần tìm sản phẩm trên các sàn
SEARCH_INTENTS = ("search_products", "compare_products")

# Số sản phẩm đưa vào câu trả lời
RESULT_LIMIT = 4

# Không có sản phẩm đúng yêu cầu thì nới ngân sách thêm 20%, làm tròn tới 100.000 đ
BUDGET_WIDEN_FACTOR = 1.2
BUDGET_ROUND_TO = 100_000

# Lựa chọn ngân sách khi hỏi làm rõ, theo ngành hàng. Giá trị gửi lại là câu tiếng Việt gốc (agent đọc được).
BUDGET_OPTIONS = {
    "laptops": ["Dưới 15 triệu", "15 - 20 triệu", "20 - 25 triệu", "25 - 30 triệu", "Trên 30 triệu"],
    "phones": ["Dưới 5 triệu", "5 - 10 triệu", "10 - 20 triệu", "Trên 20 triệu"],
    "audio": ["Dưới 1 triệu", "1 - 3 triệu", "3 - 7 triệu", "Trên 7 triệu"],
    "wearables": ["Dưới 2 triệu", "2 - 5 triệu", "5 - 10 triệu", "Trên 10 triệu"],
    "home_appliances": ["Dưới 5 triệu", "5 - 10 triệu", "10 - 20 triệu", "Trên 20 triệu"],
    "monitors": ["Dưới 3 triệu", "3 - 6 triệu", "6 - 12 triệu", "Trên 12 triệu"],
}
DEFAULT_BUDGET_OPTIONS = ["Dưới 1 triệu", "1 - 5 triệu", "5 - 15 triệu", "Trên 15 triệu"]
SKIP_BUDGET_OPTION = "Không giới hạn ngân sách, cứ tìm giúp tôi"

# Người dùng bảo "cứ tìm" -> không hỏi lại ngân sách
SKIP_PATTERN = re.compile(r"không giới hạn|bất kỳ|giá nào cũng|cứ tìm|tìm luôn|không quan trọng|bỏ qua", re.IGNORECASE)
