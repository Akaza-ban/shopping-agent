export type NavigationTab = 'dashboard' | 'search' | 'compare' | 'audit' | 'saved' | 'settings';

export interface ReasoningStep {
  id: string;
  label: string;
  detail?: string;
  status: 'pending' | 'running' | 'completed';
}

export interface ClarificationOption {
  id: string;
  label: string;
  sublabel?: string;
}

export interface ClarificationQuestion {
  id: string;
  stepNumber: number;
  totalSteps: number;
  question: string;
  contextHint?: string;
  options: ClarificationOption[];
  allowCustomInput?: boolean;
  allowDatePicker?: boolean;
}

export interface CitationItem {
  id: string;
  index: number;
  sourceName: string;
  sourceType: 'Shopee Mall' | 'Lazada Flagship' | 'Tiki Official' | 'Nhà phân phối ủy quyền' | 'Đánh giá người dùng đã xác thực';
  price?: string;
  officialPrice?: string;
  excerpt: string;
  verifiedDate: string;
  url?: string;
  reliabilityStatus: 'Đã xác minh' | 'Cần kiểm tra hiệu lực' | 'Giá ưu đãi giới hạn';
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  timestamp: string;
  reasoningSteps?: ReasoningStep[];
  clarificationCard?: ClarificationQuestion;
  citations?: CitationItem[];
  feedbackState?: 'useful' | 'needs_evidence' | 'inaccurate';
}

export interface ProductItem {
  id: string;
  name: string;
  brand: string;
  category: string;
  currentPrice: number;
  originalPrice: number;
  lowestPrice90d: number;
  rating: number;
  reviewCount: number;
  veracityScore: number; // 0-100% fake review filter score
  imageUrl: string;
  retailer: string;
  keySpecs: { [key: string]: string };
  pros: string[];
  cons: string[];
  dealExpiry?: string;
  inStock: boolean;
  warranty: string;
}

export interface DossierSection {
  id: string;
  articleNumber: string;
  title: string;
  content: string;
  highlighted?: boolean;
  highlightNote?: string;
}

export interface ShoppingDossier {
  id: string;
  dossierCode: string;
  title: string;
  category: string;
  organization: string;
  effectiveDate: string;
  signerTitle: string;
  primaryProduct: ProductItem;
  alternativeProducts: ProductItem[];
  summaryRequirement: string;
  sections: DossierSection[];
  totalBudget: number;
  estimatedSavings: number;
}

export interface AuditIssue {
  id: string;
  sectionTitle: string;
  originalText: string;
  issueType: 'warning' | 'misleading' | 'policy_loophole' | 'seeding_review';
  aiObservation: string;
  evaluationReason: string;
  citationText: string;
  aiSuggestion: string;
  status: 'pending' | 'accepted' | 'kept' | 'edited';
}

export interface MonitoredDeal {
  id: string;
  productName: string;
  platform: string;
  currentPrice: number;
  targetPrice: number;
  historicLow: number;
  dropPercentage: number;
  status: 'Giá chạm đáy' | 'Đang giảm nhẹ' | 'Chờ đợt sale';
  lastUpdated: string;
}
