from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field, field_validator

class UniversalSearchCriteria(BaseModel):
    """Tiêu chí tìm kiếm & phân tích tổng quát áp dụng cho mọi ngành hàng."""
    category: Optional[str] = Field(default="all", description="Mã danh mục: laptops, phones, audio, home_appliances, fashion, beauty...")
    category_name: Optional[str] = Field(default="Tất cả", description="Tên danh mục hiển thị tiếng Việt")
    product_type: Optional[str] = Field(default=None, description="Loại sản phẩm cụ thể: chảo, laptop, tai nghe, điện thoại, giày...")
    target_entity: Optional[str] = Field(default=None, description="Thực thể chính người dùng tìm kiếm: điện thoại, tivi, laptop, máy giặt, tai nghe, ốp lưng, máy ảnh...")
    is_accessory: bool = Field(default=False, description="True nếu người dùng tìm phụ kiện/linh kiện/vật tư thay thế, False nếu tìm thiết bị/sản phẩm chính")
    min_price: Optional[float] = Field(default=None, description="Mức giá tối thiểu (VND)")
    max_price: Optional[float] = Field(default=None, description="Mức giá tối đa (VND)")
    brands: Optional[List[str]] = Field(default_factory=list, description="Thương hiệu người dùng nêu đích danh")
    brand_tier: Optional[str] = Field(default=None, description="Phân khúc thương hiệu: thương hiệu lớn, cao cấp, phổ thông...")
    suggested_brands: Optional[List[str]] = Field(default_factory=list, description="Gợi ý các hãng uy tín nếu người dùng chưa chỉ định")
    usage_purpose: Optional[str] = Field(default=None, description="Mục đích sử dụng: học tập, gaming, văn phòng, nấu ăn...")
    priority: Optional[str] = Field(default="best_value", description="Tiêu chí ưu tiên: cheapest, best_rating, brand_reputation, best_performance")
    target_platforms: Optional[List[str]] = Field(default_factory=lambda: ["all"], description="Sàn TMĐT người dùng nhắc tới: tiki, tgdd, dmx, hoặc all; sàn khác giữ nguyên tên để báo không hỗ trợ")
    
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Thuộc tính đặc thù theo ngành hàng")
    
    # Từ khóa đã được làm sạch và tối ưu để search sàn TMĐT
    cleaned_query: str = Field(default="", description="Từ khóa tinh gọn phục vụ tìm kiếm")

    @field_validator("is_accessory", mode="before")
    @classmethod
    def _null_is_not_accessory(cls, v):
        return False if v is None else v

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
    specs: Optional[Union[Dict[str, Any], str]] = ""
    aiSummary: str = ""
    warranty: str = "Chính hãng 12 tháng"
    deliveryTag: Optional[str] = "Freeship"
    selected: bool = False
    externalUrl: str = ""
    sourceCategoryPath: Optional[str] = None
    sourceCategoryName: Optional[str] = None
    updatedAt: Optional[str] = None
    # Mức 2: dữ liệu từ trang chi tiết & kết quả xếp hạng
    returnPolicy: Optional[str] = None
    detailFetched: bool = False
    matchReasons: List[str] = Field(default_factory=list)
    attributeMatch: Dict[str, str] = Field(default_factory=dict)  # thuộc tính -> verified | mismatch | unknown


class MessageItem(BaseModel):
    id: str
    sender: Literal["user", "ai"]
    text: str
    timestamp: str
    precision: Optional[str] = None

class AgentState(BaseModel):
    """Trạng thái chia sẻ giữa các Agent trong hệ thống."""
    session_id: str
    user_query: str
    # Ngôn ngữ câu trả lời của trợ lý (Cài đặt người dùng)
    language: Literal["vi", "en"] = "vi"
    intent: Optional[Literal["smalltalk", "general_advice", "search_products", "compare_products", "parse_link", "find_deal", "out_of_scope"]] = None
    criteria: Optional[UniversalSearchCriteria] = None
    messages: List[MessageItem] = Field(default_factory=list)
    found_products: List[ProductItemModel] = Field(default_factory=list)
    recommended_product: Optional[ProductItemModel] = None
    comparison_summary: Optional[str] = None
    comparison_table: Optional[Dict[str, Any]] = None
    comparison_markdown: str = ""
    clarification: Optional[Dict[str, Any]] = None
    search_notes: List[str] = Field(default_factory=list)
    relaxed_search: Optional[str] = None
    target_link: Optional[str] = None
    platform_filter: Optional[str] = None
    final_response: str = ""
    suggested_questions: List[str] = Field(default_factory=list)
    intermediate_steps: List[Dict[str, Any]] = Field(default_factory=list)
