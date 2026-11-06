import { BackendProduct, ClarificationQuestion, ComparisonResult, CrawlerStatus, PlatformPolicy, PolicyLookupResult, PolicyScenario, PriceAlert, PriceCheck, PricePoint, ProductItem } from '../types.ts';
import { currentLanguage, t } from '../i18n/index.tsx';

// Kết nối backend FastAPI + LangGraph. Đổi địa chỉ bằng VITE_API_BASE_URL trong .env.
export const API_BASE_URL = (import.meta.env?.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') || 'http://localhost:8000';

// phiên đăng nhập
const TOKEN_KEY = 'shopping-ai.auth-token';
export const AUTH_EXPIRED_EVENT = 'shopping-ai:auth-expired';

export function getToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}

export function setToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch { /* trình duyệt chặn storage: chỉ giữ trong phiên */ }
}

// Mọi lời gọi backend đi qua đây: gắn token, báo hết phiên (401) để giao diện quay về màn đăng nhập
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      ...(init.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });
  if (res.status === 401 && token) {
    setToken(null);
    window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT));
  }
  return res;
}

async function errorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    // Thông báo lỗi của máy chủ viết bằng tiếng Việt -> dịch nếu có trong bảng dịch
    if (typeof body.detail === 'string') return t(body.detail);
  } catch { /* không có JSON */ }
  return t('Backend trả về HTTP {status}', { status: res.status });
}

// chuyển đổi dữ liệu
const PLATFORM_IDS: Record<BackendProduct['platform'], string> = {
  tgdd: 'tgdd',
  dmx: 'dmx',
  tiki: 'tiki',
  'fpt-shop': 'fpt-shop',
  cellphones: 'cellphones',
};

const KNOWN_BRANDS = [
  'Apple', 'ASUS', 'Acer', 'Lenovo', 'HP', 'Dell', 'MSI', 'Gigabyte', 'Samsung', 'Xiaomi', 'OPPO', 'vivo', 'Realme',
  'Honor', 'Huawei', 'Nokia', 'Sony', 'LG', 'Panasonic', 'Toshiba', 'Electrolux', 'Aqua', 'Sharp', 'Hitachi', 'Casper',
  'TCL', 'Bose', 'JBL', 'Marshall', 'Anker', 'Soundpeats', 'Garmin', 'Philips', 'Ecovacs', 'Roborock', 'Dreame',
];
const GENERIC_WORDS = /^(laptop|điện|thoại|máy|tai|nghe|tivi|smart|loa|đồng|hồ|robot|tủ|lạnh|giặt|gaming|chính|hãng)$/i; // i18n-ignore: từ khóa để nhận diện hãng, không hiển thị

const inferBrand = (name: string) => {
  if (/\b(iphone|ipad|macbook|airpods|apple watch)\b/i.test(name)) return 'Apple';
  const known = KNOWN_BRANDS.find(b => new RegExp(`\\b${b}\\b`, 'i').test(name));
  if (known) return known;
  return name.split(/\s+/).find(w => !GENERIC_WORDS.test(w)) ?? '';
};

// "Đã bán 2,4k" -> 2400, "123 đánh giá" -> 123
const parseVolume = (label: string) => {
  const m = label.match(/(\d+(?:[.,]\d+)?)\s*(k|tr)?/i);
  if (!m) return 0;
  const n = parseFloat(m[1].replace(',', '.'));
  return Math.round(m[2]?.toLowerCase() === 'k' ? n * 1000 : m[2] ? n * 1_000_000 : n);
};

// Lý do trừ điểm của bộ xếp hạng: "Không đúng yêu cầu...", "Vượt ngân sách...", "Chưa xác minh..."
const NEGATIVE_REASON = /^(không|vượt|chưa|thiếu|ít)/i; // i18n-ignore: nhận diện lý do trừ điểm từ backend

export function toProductItem(p: BackendProduct): ProductItem {
  const reasons = p.matchReasons ?? [];
  const specs = typeof p.specs === 'object' && p.specs !== null
    ? Object.fromEntries(Object.entries(p.specs).map(([k, v]) => [k, String(v)]))
    : p.specs ? { [t('Tóm tắt')]: String(p.specs) } : {};
  return {
    id: p.id,
    name: p.name,
    brand: inferBrand(p.name),
    category: p.categoryName || p.category || '',
    currentPrice: p.currentPrice,
    originalPrice: p.originalPrice || p.currentPrice,
    rating: p.rating,
    reviewCount: parseVolume(p.reviewsCount || ''),
    reviewsLabel: p.reviewsCount,
    imageUrl: p.image,
    retailer: p.platformName,
    platformId: PLATFORM_IDS[p.platform] ?? p.platform,
    productUrl: p.externalUrl,
    matchScore: p.aiMatchScore,
    keySpecs: specs,
    pros: reasons.filter(r => !NEGATIVE_REASON.test(r)),
    cons: reasons.filter(r => NEGATIVE_REASON.test(r)),
    inStock: true,
    warranty: p.warranty,
    returnPolicy: p.returnPolicy ?? undefined,
    attributeMatch: p.attributeMatch,
    updatedAt: p.updatedAt ?? undefined,
    raw: p,
  };
}

interface BackendTable {
  columns: string[];
  rows: { label: string; values: unknown[]; best_index: number | null }[];
}

export const toComparison = (data: { summary?: string | null; table?: BackendTable | null }): ComparisonResult | undefined =>
  data.table
    ? {
        summary: data.summary ?? '',
        columns: data.table.columns,
        rows: data.table.rows.map(r => ({ label: r.label, values: r.values.map(v => String(v ?? '—')), bestIndex: r.best_index })),
      }
    : undefined;

interface BackendClarification {
  id: string;
  field: string;
  question: string;
  context_hint?: string;
  options: { id: string; label: string; value: string }[];
  allow_custom_input?: boolean;
}

const toClarification = (c: BackendClarification): ClarificationQuestion => ({
  id: c.id,
  field: c.field,
  question: c.question,
  contextHint: c.context_hint,
  options: c.options.map(o => ({ id: o.id, label: o.label, value: o.value })),
  allowCustomInput: c.allow_custom_input ?? true,
});

// phiên chat
// Mỗi đoạn chat là một session riêng ở backend (trí nhớ hội thoại, câu hỏi làm rõ đang chờ...)
export const newConversationId = () => `chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

// Xóa lịch sử đoạn chat ở backend (tin nhắn, sản phẩm lượt trước, trạng thái làm rõ)
export async function deleteConversation(sessionId: string): Promise<void> {
  const res = await apiFetch(`/api/chat/history/${encodeURIComponent(sessionId)}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await errorDetail(res));
}

// SSE /api/chat/stream
export interface DoneInfo {
  intent: string | null;
  relaxedSearch: string | null;
  searchNotes: string[];
}

export interface ChatStreamHandlers {
  onStatus?: (stage: string, message: string) => void;
  onProducts?: (products: ProductItem[]) => void;
  onComparison?: (comparison: ComparisonResult) => void;
  onClarification?: (question: ClarificationQuestion) => void;
  onToken?: (token: string) => void;
  onSuggestions?: (suggestions: string[]) => void;
  onDone?: (info: DoneInfo) => void;
}

function dispatch(event: string, data: any, h: ChatStreamHandlers) {
  switch (event) {
    case 'status': h.onStatus?.(data.stage, data.message); break;
    case 'products': h.onProducts?.((data.items as BackendProduct[]).map(toProductItem)); break;
    case 'comparison': { const c = toComparison(data); if (c) h.onComparison?.(c); break; }
    case 'clarification': h.onClarification?.(toClarification(data)); break;
    case 'token': h.onToken?.(data.content); break;
    case 'suggestions': h.onSuggestions?.(data); break;
    case 'done': h.onDone?.({ intent: data.intent, relaxedSearch: data.relaxed_search, searchNotes: data.search_notes ?? [] }); break;
    case 'error': throw new Error(data.error || t('Lỗi không xác định từ backend'));
  }
}

export async function streamChat(
  sessionId: string,
  message: string,
  handlers: ChatStreamHandlers,
  options: { platform?: string; signal?: AbortSignal } = {}
): Promise<void> {
  const res = await apiFetch('/api/chat/stream', {
    method: 'POST',
    headers: { Accept: 'text/event-stream' },
    // language: trợ lý trả lời theo ngôn ngữ người dùng chọn trong Cài đặt
    body: JSON.stringify({ session_id: sessionId, message, platform: options.platform ?? 'all', language: currentLanguage() }),
    signal: options.signal,
  });
  if (!res.ok || !res.body) throw new Error(await errorDetail(res));

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    // sse-starlette dùng \r\n; chuẩn hóa rồi tách theo dòng trống
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
    let sep: number;
    while ((sep = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      let event = 'message';
      const dataLines: string[] = [];
      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim();
        else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''));
      }
      if (dataLines.length) dispatch(event, JSON.parse(dataLines.join('\n')), handlers);
    }
  }
}

// tool so sánh cho sản phẩm đã lưu
// comparison = undefined khi không so sánh được (VD sản phẩm khác loại); summary luôn có lời giải thích
export async function compareProducts(
  sessionId: string,
  products: ProductItem[],
): Promise<{ comparison?: ComparisonResult; summary: string }> {
  const payload = products.map(p => p.raw ?? fromProductItem(p));
  const res = await apiFetch('/api/chat/compare', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, products: payload }),
  });
  if (!res.ok) throw new Error(await errorDetail(res));
  const data = await res.json();
  return { comparison: toComparison(data), summary: data.summary ?? '' };
}

// Sản phẩm lưu từ phiên bản cũ (chưa có `raw`) -> dựng lại schema backend tối thiểu
const BACKEND_PLATFORMS = Object.fromEntries(Object.entries(PLATFORM_IDS).map(([k, v]) => [v, k]));

function fromProductItem(p: ProductItem): BackendProduct {
  const original = p.originalPrice || p.currentPrice;
  return {
    id: p.id,
    name: p.name,
    platform: (BACKEND_PLATFORMS[p.platformId] ?? 'tiki') as BackendProduct['platform'],
    platformName: p.retailer,
    aiMatchScore: p.matchScore,
    originalPrice: original,
    currentPrice: p.currentPrice,
    discountPercent: original > p.currentPrice ? Math.round((1 - p.currentPrice / original) * 100) : 0,
    rating: p.rating,
    reviewsCount: p.reviewsLabel ?? t('{count} đánh giá', { count: p.reviewCount }),
    image: p.imageUrl,
    specs: p.keySpecs,
    warranty: p.warranty,
    returnPolicy: p.returnPolicy,
    externalUrl: p.productUrl,
  };
}

// thời gian từ backend
// Backend lưu datetime.utcnow() không kèm múi giờ -> coi là UTC để hiển thị đúng giờ Việt Nam
export const parseServerDate = (iso: string) => new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await apiFetch(path, init);
  if (!res.ok) throw new Error(await errorDetail(res));
  return res.json() as Promise<T>;
}

// lịch sử giá
export const getPriceHistory = async (productId: string): Promise<PricePoint[]> =>
  (await requestJson<{ history: PricePoint[] }>(`/api/products/${encodeURIComponent(productId)}/history`)).history;

// theo dõi giá
export const listAlerts = () => requestJson<PriceAlert[]>('/api/alerts');

export const createAlert = (p: ProductItem, targetPrice: number) =>
  requestJson<PriceAlert>('/api/alerts', {
    method: 'POST',
    body: JSON.stringify({
      target_price: targetPrice,
      product: {
        id: p.id,
        name: p.name,
        platform: BACKEND_PLATFORMS[p.platformId] ?? p.platformId,
        platformName: p.retailer,
        currentPrice: p.currentPrice,
        originalPrice: p.originalPrice,
        externalUrl: p.productUrl,
        image: p.imageUrl,
      },
    }),
  });

export const deleteAlert = (id: string) => requestJson<{ deleted: boolean }>(`/api/alerts/${encodeURIComponent(id)}`, { method: 'DELETE' });

// Nhật ký các lần kiểm tra giá của một yêu cầu (mới nhất trước)
export const getAlertChecks = (id: string) =>
  requestJson<PriceCheck[]>(`/api/alerts/${encodeURIComponent(id)}/checks`);

// Đọc giá thật trên trang sản phẩm ngay; trả về toàn bộ danh sách sau cập nhật
export const checkAlerts = (alertIds?: string[]) =>
  requestJson<PriceAlert[]>('/api/alerts/check', { method: 'POST', body: JSON.stringify({ alert_ids: alertIds ?? null }) });

// kho dữ liệu & crawler
export const getCrawlerStatus = () => requestJson<CrawlerStatus>('/api/crawler/status');

export const triggerCrawl = () =>
  requestJson<{ status: string; message: string }>('/api/crawler/trigger', {
    method: 'POST',
    body: JSON.stringify({ limit_per_query: 3, force_refresh: true, background: true }),
  });

// tài khoản
export interface AuthUser {
  id: string;
  email: string;
  displayName: string;
  role: 'user' | 'admin';
  createdAt: string | null;
}

interface AuthResult { token: string; user: AuthUser }

export async function register(email: string, password: string, displayName: string): Promise<AuthUser> {
  const res = await requestJson<AuthResult>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, display_name: displayName }),
  });
  setToken(res.token);
  return res.user;
}

export async function login(email: string, password: string): Promise<AuthUser> {
  const res = await requestJson<AuthResult>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
  setToken(res.token);
  return res.user;
}

export async function logout(): Promise<void> {
  try { await apiFetch('/api/auth/logout', { method: 'POST' }); } finally { setToken(null); }
}

export const getMe = () => requestJson<AuthUser>('/api/auth/me');

export const updateProfile = (displayName: string) =>
  requestJson<AuthUser>('/api/auth/me', { method: 'PATCH', body: JSON.stringify({ display_name: displayName }) });

export const changePassword = (currentPassword: string, newPassword: string) =>
  requestJson<{ ok: boolean }>('/api/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });

// Dữ liệu cá nhân đồng bộ theo tài khoản (hội thoại, sản phẩm đã lưu, lịch sử...)
export type UserDataKey = 'conversations' | 'saved-products' | 'activities' | 'search-history' | 'preferences';

export const getUserData = async <T,>(key: UserDataKey): Promise<T | null> =>
  (await requestJson<{ value: T | null }>(`/api/auth/me/data/${key}`)).value;

export const putUserData = (key: UserDataKey, value: unknown) =>
  requestJson<{ saved: boolean }>(`/api/auth/me/data/${key}`, { method: 'PUT', body: JSON.stringify({ value }) });

// chính sách đổi trả, bảo hành
export const listPolicies = () => requestJson<PlatformPolicy[]>('/api/policies');

export const lookupPolicies = (
  query: string,
  platformIds: string[],
  category: string,
  productPlatformIds: string[] = [],
  scenario: PolicyScenario | null = null,
) =>
  requestJson<PolicyLookupResult>('/api/policies/lookup', {
    method: 'POST',
    body: JSON.stringify({
      query, platform_ids: platformIds, category, language: currentLanguage(), product_platform_ids: productPlatformIds,
      scenario,
    }),
  });
