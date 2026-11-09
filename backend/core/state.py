import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# Trường mô tả nhu cầu của tiêu chí (không phải thông số sản phẩm) và các phần trong tên của chúng
_DESCRIPTIVE_FIELDS = ("usage_purpose", "priority", "brand_tier", "brands", "suggested_brands", "category")
_USAGE_KEY_PARTS = set("usage_purpose".split("_"))
_DESCRIPTIVE_KEY_PARTS = {part for name in _DESCRIPTIVE_FIELDS for part in name.split("_")}


class UniversalSearchCriteria(BaseModel):
    """Tiêu chí tìm kiếm & phân tích tổng quát áp dụng cho mọi ngành hàng."""

    category: str | None = Field(
        default="all", description="Mã danh mục: laptops, phones, audio, home_appliances, fashion, beauty..."
    )
    category_name: str | None = Field(default="Tất cả", description="Tên danh mục hiển thị tiếng Việt")
    product_type: str | None = Field(
        default=None, description="Loại sản phẩm cụ thể: chảo, laptop, tai nghe, điện thoại, giày..."
    )
    target_entity: str | None = Field(
        default=None,
        description="Thực thể chính người dùng tìm kiếm: điện thoại, tivi, laptop, máy giặt, tai nghe, ốp lưng, máy ảnh...",
    )
    is_accessory: bool = Field(
        default=False,
        description="True nếu người dùng tìm phụ kiện/linh kiện/vật tư thay thế, False nếu tìm thiết bị/sản phẩm chính",
    )
    min_price: float | None = Field(default=None, description="Mức giá tối thiểu (VND)")
    max_price: float | None = Field(default=None, description="Mức giá tối đa (VND)")
    brands: list[str] | None = Field(default_factory=list, description="Thương hiệu người dùng nêu đích danh")
    brand_tier: str | None = Field(
        default=None, description="Phân khúc thương hiệu: thương hiệu lớn, cao cấp, phổ thông..."
    )
    suggested_brands: list[str] | None = Field(
        default_factory=list, description="Gợi ý các hãng uy tín nếu người dùng chưa chỉ định"
    )
    usage_purpose: str | None = Field(
        default=None, description="Mục đích sử dụng: học tập, gaming, văn phòng, nấu ăn..."
    )
    priority: str | None = Field(
        default="best_value", description="Tiêu chí ưu tiên: cheapest, best_rating, brand_reputation, best_performance"
    )
    target_platforms: list[str] | None = Field(
        default_factory=lambda: ["all"],
        description="Sàn TMĐT người dùng nhắc tới: tiki, tgdd, dmx, hoặc all; sàn khác giữ nguyên tên để báo không hỗ trợ",
    )

    attributes: dict[str, Any] = Field(default_factory=dict, description="Thuộc tính đặc thù theo ngành hàng")

    # Từ khóa đã được làm sạch và tối ưu để search sàn TMĐT
    cleaned_query: str = Field(default="", description="Từ khóa tinh gọn phục vụ tìm kiếm")

    @field_validator("is_accessory", mode="before")
    @classmethod
    def _null_is_not_accessory(cls, v):
        return False if v is None else v

    @model_validator(mode="after")
    def _descriptive_fields_are_not_specs(self):
        """
        LLM đôi khi ghi lại mục đích / ưu tiên vào `attributes` ({"usage": "gaming"}): đó không phải thông số kiểm chứng
        được trên trang sản phẩm, để lại thì bộ xếp hạng coi là thông số bắt buộc và chấm sai.
        Khóa trùng tên (hoặc một phần tên) trường mô tả của chính tiêu chí -> chuyển sang trường đó hoặc bỏ.
        """
        if not self.attributes:
            return self
        kept = {}
        for key, value in self.attributes.items():
            parts = set(re.split(r"[\W_]+", str(key).lower())) - {""}
            if parts & _USAGE_KEY_PARTS:
                if not self.usage_purpose and isinstance(value, str) and value.strip():
                    self.usage_purpose = value.strip()
                continue
            if parts & _DESCRIPTIVE_KEY_PARTS:
                if parts & {"brand", "brands"} and not self.brands and isinstance(value, str) and value.strip():
                    self.brands = [value.strip()]
                continue
            if self.usage_purpose and str(value).strip().lower() == self.usage_purpose.strip().lower():
                continue
            kept[key] = value
        self.attributes = kept
        return self

    @field_validator("cleaned_query", mode="before")
    @classmethod
    def _null_query_is_empty(cls, v):
        return "" if v is None else v

    @field_validator("attributes", mode="before")
    @classmethod
    def _null_attributes_are_empty(cls, v):
        return {} if v is None else v


class ProductItemModel(BaseModel):
    id: str
    name: str
    category: str = "all"
    categoryName: str = "Tất cả"
    platform: str
    platformName: str
    platformBadgeColor: str = "#ee4d2d"
    platformBadgeBg: str = "rgba(238, 77, 45, 0.15)"
    aiMatchScore: int = 90
    originalPrice: float
    currentPrice: float
    discountPercent: int = 0
    rating: float = 4.8
    reviewsCount: str = "100+ đánh giá"
    sku: str = ""
    image: str = ""
    specs: dict[str, Any] | str | None = ""
    aiSummary: str = ""
    warranty: str = "Chính hãng 12 tháng"
    deliveryTag: str | None = "Freeship"
    selected: bool = False
    externalUrl: str = ""
    sourceCategoryPath: str | None = None
    sourceCategoryName: str | None = None
    updatedAt: str | None = None
    # Mức 2: dữ liệu từ trang chi tiết & kết quả xếp hạng
    returnPolicy: str | None = None
    detailFetched: bool = False
    matchReasons: list[str] = Field(default_factory=list)
    attributeMatch: dict[str, str] = Field(default_factory=dict)  # thuộc tính -> verified | mismatch | unknown


class MessageItem(BaseModel):
    id: str
    sender: Literal["user", "ai"]
    text: str
    timestamp: str
    precision: str | None = None


class AgentState(BaseModel):
    """Trạng thái chia sẻ giữa các Agent trong hệ thống."""

    session_id: str
    user_query: str
    # Ngôn ngữ câu trả lời của trợ lý (Cài đặt người dùng)
    language: Literal["vi", "en"] = "vi"
    intent: (
        Literal[
            "smalltalk",
            "general_advice",
            "search_products",
            "compare_products",
            "parse_link",
            "find_deal",
            "out_of_scope",
        ]
        | None
    ) = None
    criteria: UniversalSearchCriteria | None = None
    # Router: câu hỏi có nói về sản phẩm đã đề xuất ở lượt trước không (None = không rõ, VD khi không có LLM)
    about_previous_products: bool | None = None
    messages: list[MessageItem] = Field(default_factory=list)
    found_products: list[ProductItemModel] = Field(default_factory=list)
    recommended_product: ProductItemModel | None = None
    comparison_summary: str | None = None
    comparison_table: dict[str, Any] | None = None
    comparison_markdown: str = ""
    clarification: dict[str, Any] | None = None
    search_notes: list[str] = Field(default_factory=list)
    relaxed_search: str | None = None
    target_link: str | None = None
    platform_filter: str | None = None
    final_response: str = ""
    suggested_questions: list[str] = Field(default_factory=list)
    intermediate_steps: list[dict[str, Any]] = Field(default_factory=list)
