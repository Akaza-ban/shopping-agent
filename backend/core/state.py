from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

class UniversalSearchCriteria(BaseModel):
    """Tiêu chí tìm kiếm & phân tích tổng quát áp dụng cho mọi ngành hàng."""
    category: Optional[str] = Field(default="all", description="Mã danh mục: laptops, phones, audio, home_appliances, fashion, beauty...")
    category_name: Optional[str] = Field(default="Tất cả", description="Tên danh mục hiển thị tiếng Việt")
    product_type: Optional[str] = Field(default=None, description="Loại sản phẩm cụ thể: chảo, laptop, tai nghe, điện thoại, giày...")
    min_price: Optional[float] = Field(default=None, description="Mức giá tối thiểu (VND)")
    max_price: Optional[float] = Field(default=None, description="Mức giá tối đa (VND)")
    brands: Optional[List[str]] = Field(default_factory=list, description="Thương hiệu người dùng nêu đích danh")
    brand_tier: Optional[str] = Field(default=None, description="Phân khúc thương hiệu: thương hiệu lớn, cao cấp, phổ thông...")
    suggested_brands: Optional[List[str]] = Field(default_factory=list, description="Gợi ý các hãng uy tín nếu người dùng chưa chỉ định")
    usage_purpose: Optional[str] = Field(default=None, description="Mục đích sử dụng: học tập, gaming, văn phòng, nấu ăn...")
    priority: Optional[str] = Field(default="best_value", description="Tiêu chí ưu tiên: cheapest, best_rating, brand_reputation, best_performance")
    target_platforms: Optional[List[str]] = Field(default_factory=lambda: ["all"], description="Sàn TMĐT: shopee, tiki, lazada, tgdd, dmx, hoặc all")
    
    # Các thuộc tính kỹ thuật linh hoạt cho mọi sản phẩm
    # Ví dụ laptop: {"cpu": "Core i7", "gpu": "RTX 3050", "ram": "16GB"}
    # Ví dụ tai nghe: {"anc": True, "battery_hours": 30, "type": "over-ear"}
    # Ví dụ đồ gia dụng: {"capacity_liters": 6.5, "power_watt": 1800}
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Thuộc tính đặc thù theo ngành hàng")
    
    # Từ khóa đã được làm sạch và tối ưu để search sàn TMĐT
    cleaned_query: str = Field(default="", description="Từ khóa tinh gọn phục vụ tìm kiếm")

class ProductItemModel(BaseModel):
    id: str
    name: str
    category: str = "all"
    categoryName: str = "Tất cả"
    platform: Literal["shopee", "tiki", "lazada", "tgdd", "dmx"]
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
    specs: Optional[str] = ""
    aiSummary: str = ""
    warranty: str = "Chính hãng 12 tháng"
    deliveryTag: Optional[str] = "Freeship"
    selected: bool = False
    externalUrl: str = ""
    updatedAt: Optional[str] = None


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
    intent: Optional[Literal["general_advice", "search_products", "compare_products", "parse_link", "find_deal"]] = None
    criteria: Optional[UniversalSearchCriteria] = None
    messages: List[MessageItem] = Field(default_factory=list)
    found_products: List[ProductItemModel] = Field(default_factory=list)
    recommended_product: Optional[ProductItemModel] = None
    comparison_summary: Optional[str] = None
    target_link: Optional[str] = None
    final_response: str = ""
    intermediate_steps: List[Dict[str, Any]] = Field(default_factory=list)
