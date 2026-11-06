export type NavigationTab = 'dashboard' | 'search' | 'policy' | 'saved' | 'alerts' | 'activity';

// Yêu cầu từ màn khác gửi sang khung chat cho agent xử lý
export type ChatRequest =
  | { id: string; kind: 'compare'; products: ProductItem[] } // agent gọi tool so sánh
  | { id: string; kind: 'restore'; query: string; products: ProductItem[] }; // hiển thị lại kết quả cũ

export type ActivityType = 'search' | 'save' | 'unsave' | 'compare' | 'policy' | 'settings' | 'support' | 'alert';

export interface ActivityItem {
  id: string;
  type: ActivityType;
  title: string;
  detail?: string;
  timestamp: string; // ISO
  query?: string;
  products?: ProductItem[]; // để mở lại kết quả trong khung chat
  targetTab?: NavigationTab;
}

export interface SearchRecord {
  id: string;
  query: string;
  timestamp: string;
  products: ProductItem[];
}

export interface SavedProduct {
  product: ProductItem;
  sourceQuery: string;
  savedAt: string;
}

export interface ReasoningStep {
  id: string;
  label: string;
  detail?: string;
  status: 'pending' | 'running' | 'completed';
}

export interface ClarificationOption {
  id: string;
  label: string;
  value: string; // câu trả lời gửi lại cho agent
  sublabel?: string;
}

// Câu hỏi làm rõ do agent gửi qua sự kiện SSE `clarification`
export interface ClarificationQuestion {
  id: string;
  field: string; // VD: "budget"
  question: string;
  contextHint?: string;
  options: ClarificationOption[];
  allowCustomInput: boolean;
}

// Kết quả tool so sánh của backend: mỗi hàng là một tiêu chí, best_index = cột tốt nhất (hoặc null)
export interface ComparisonRow {
  label: string;
  values: string[];
  bestIndex: number | null;
}

export interface ComparisonResult {
  summary: string;
  columns: string[];
  rows: ComparisonRow[];
}

export interface CitationItem {
  id: string;
  index: number;
  sourceName: string;
  platformId: string;
  price?: string;
  officialPrice?: string;
  excerpt: string;
  verifiedDate: string;
  url?: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  timestamp: string;
  citations?: CitationItem[];
  products?: ProductItem[];
  query?: string; // câu hỏi gốc sinh ra danh sách products
  showProductCards?: boolean; // false: chỉ hiện bảng so sánh
  comparisonOpen?: boolean; // bảng so sánh mở sẵn
  showPolicyAction?: boolean;
  comparison?: ComparisonResult; // bảng so sánh do tool của agent tạo
  notes?: string[]; // ghi chú độ tin cậy (đã nới tiêu chí, dữ liệu cũ, thông số chưa xác minh...)
  suggestions?: string[]; // câu hỏi gợi ý tiếp theo
  clarification?: ClarificationQuestion; // câu hỏi làm rõ agent đặt ra ở lượt này
  isError?: boolean;
}

// Một đoạn chat tư vấn mua sắm; id cũng là session_id gửi lên backend (mỗi đoạn có trí nhớ riêng)
export interface ChatConversation {
  id: string;
  title: string; // câu hỏi đầu tiên người dùng nhập
  createdAt: string; // ISO
  updatedAt: string; // ISO
  messages: ChatMessage[];
}

export interface Platform {
  id: string;
  name: string;
  type: string; // 'Sàn TMĐT' | 'Chuỗi bán lẻ' (dịch khi hiển thị)
}

export interface ProductItem {
  id: string;
  name: string;
  brand: string;
  category: string;
  currentPrice: number;
  originalPrice: number;
  rating: number;
  reviewCount: number;
  imageUrl: string;
  retailer: string;
  platformId: string;
  productUrl: string;
  matchScore: number; // 0-100: mức độ đáp ứng tiêu chí người dùng
  keySpecs: { [key: string]: string };
  pros: string[]; // lý do cộng điểm khi xếp hạng
  cons: string[]; // lý do trừ điểm (sai thông số, vượt ngân sách...)
  inStock: boolean;
  warranty: string;
  reviewsLabel?: string; // VD: "Đã bán 2,4k", "Chưa có đánh giá"
  returnPolicy?: string;
  attributeMatch?: Record<string, 'verified' | 'mismatch' | 'unknown'>;
  updatedAt?: string;
  raw?: BackendProduct; // bản gốc từ backend, dùng khi gửi lại cho tool so sánh
}

// Sản phẩm theo schema ProductItemModel của backend (backend/core/state.py)
export interface BackendProduct {
  id: string;
  name: string;
  category?: string;
  categoryName?: string;
  platform: 'tiki' | 'tgdd' | 'dmx' | 'fpt-shop' | 'cellphones';
  platformName: string;
  aiMatchScore: number;
  originalPrice: number;
  currentPrice: number;
  discountPercent: number;
  rating: number;
  reviewsCount: string;
  image: string;
  specs: Record<string, string> | string | null;
  warranty: string;
  externalUrl: string;
  updatedAt?: string | null;
  returnPolicy?: string | null;
  detailFetched?: boolean;
  matchReasons?: string[];
  attributeMatch?: Record<string, 'verified' | 'mismatch' | 'unknown'>;
  [key: string]: unknown;
}

export interface PlatformPolicy {
  platformId: string;
  returnWindowDays: number;
  freeReturn: boolean;
  returnConditions: string[];
  returnShippingFee: string;
  refundTime: string;
  defectExchange: string; // chính sách 1 đổi 1 khi lỗi NSX
  warrantyHandling: string; // ai tiếp nhận bảo hành
  exceptions: string[];
  policyUrl: string;
  lastChecked: string;
  verified?: boolean; // điều khoản rút từ trang chính sách gốc
}

// Đoạn trích trang chính sách liên quan tới câu hỏi (POST /api/policies/lookup)
export interface PolicyExcerpt {
  id: number;
  platformId: string;
  text: string;
  url: string;
  title?: string;
}

// Phạm vi tra cứu: chính sách áp dụng là của nơi bán sản phẩm
export interface PolicyScope {
  kind: 'product' | 'link' | 'catalog' | 'unknown_link' | 'compare';
  platformIds: string[];
  matches: Record<string, { count: number; example: string }>;
}

// Tình huống người mua chọn khi tra cứu chính sách
export type PolicyScenario = 'defect' | 'change_mind' | 'wrong_item' | 'warranty';

export interface PolicyLookupResult {
  policies: PlatformPolicy[];
  excerpts: PolicyExcerpt[];
  summary: string;
  sourceIds: number[]; // id các đoạn trích làm căn cứ cho câu trả lời
  usedLlm: boolean;
  scope: PolicyScope;
  scenario: PolicyScenario | null;
}

// Mở màn tra cứu từ kết quả tư vấn: câu hỏi gốc + sàn đang bán các sản phẩm đã gợi ý
export interface PolicyRequest {
  query: string;
  productPlatformIds: string[];
}

// Mốc lịch sử giá (GET /api/products/{id}/history)
export interface PricePoint {
  price: number;
  originalPrice: number;
  recordedAt: string; // ISO (UTC)
}

// Yêu cầu theo dõi giá (bảng price_alerts ở backend)
export interface PriceAlert {
  id: string;
  productId: string;
  productName: string;
  productUrl: string;
  image: string;
  platform: string;
  platformName: string;
  targetPrice: number;
  initialPrice: number;
  lastPrice: number;
  lowestPrice: number;
  status: 'watching' | 'triggered';
  lastCheckedAt: string | null;
  triggeredAt: string | null;
  lastNote: string;
  pendingPrice: number | null; // giá bất thường chờ lần đọc sau xác nhận
  inStock: boolean | null;     // còn hàng ở lần đọc gần nhất (null = sàn không ghi)
  createdAt: string;
}

// Một lần kiểm tra giá (bảng price_checks)
export interface PriceCheck {
  id: number;
  alertId: string;
  price: number | null;
  inStock: boolean | null;
  outcome: 'accepted' | 'triggered' | 'pending' | 'rejected' | 'out_of_stock' | 'unreadable';
  note: string;
  latencyMs: number | null;
  checkedAt: string | null;
}

// Trạng thái kho dữ liệu & crawler (GET /api/crawler/status)
export interface CrawlerStatus {
  isRunning: boolean;
  totalProductsInDb: number;
  latestDataUpdate: string | null;
  lastRunTime: string | null;
  lastRunStats: Record<string, unknown> | null;
  hotCatalogCount: number;
}
