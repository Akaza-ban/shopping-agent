import React, { useState, useRef, useEffect, useEffectEvent } from 'react';
import {
  Send,
  Sparkles,
  CheckCircle2,
  RotateCw,
  ShieldCheck,
  ChevronRight,
  BookOpen,
  ArrowRight,
  Table2,
  ChevronDown,
  AlertTriangle,
  MessageSquarePlus,
  Square,
  RotateCcw
} from 'lucide-react';
import { ChatConversation, ChatMessage, ChatRequest, CitationItem, PolicyRequest, ProductItem, ReasoningStep } from '../types.ts';
import { getPlatformName } from '../services/shoppingService.ts';
import { ApiError, MAX_MESSAGE_CHARS, compareProducts, deleteConversation, newConversationId, streamChat } from '../services/agentApi.ts';
import { usePersistentState } from '../hooks/usePersistentState.ts';
import { useSyncedState } from '../hooks/useSyncedState.ts';
import { ComparisonTable } from './ComparisonTable.tsx';
import { ConversationList } from './ConversationList.tsx';
import { Markdown } from './Markdown.tsx';
import { PolicyDrawer } from './policy/PolicyDrawer.tsx';
import { CitationPanel } from './chat/CitationPanel.tsx';
import { ProductCard } from './chat/ProductCard.tsx';
import { currentLocale, formatVnd, msg, t, useI18n } from '../i18n/index.tsx';

interface SearchAssistantViewProps {
  userId: string;
  savedIds: string[];
  request: ChatRequest | null;
  onRequestHandled: () => void;
  onToggleSave: (product: ProductItem, sourceQuery: string) => void;
  trackedIds: string[]; // sản phẩm đang được theo dõi giá
  onTrackPrice: (product: ProductItem) => void;
  onResults: (query: string, products: ProductItem[]) => void;
  onOpenPolicy: (request?: PolicyRequest) => void;
}

const nowTime = () => new Date().toLocaleTimeString(currentLocale(), { hour: '2-digit', minute: '2-digit' });

const WELCOME_MESSAGE: ChatMessage = {
  id: 'msg-welcome',
  sender: 'assistant',
  content: msg('Xin chào, tôi là trợ lý mua sắm AI. Hãy mô tả nhu cầu của bạn (ngân sách, cấu hình, mục đích sử dụng), tôi sẽ tìm kiếm trên các sàn, lọc, so sánh và đề xuất sản phẩm phù hợp nhất.'),
  timestamp: msg('Hôm nay')
};

const MAX_CONVERSATIONS = 30;
const MAX_TITLE_LENGTH = 80;
// Mảng rỗng dùng chung: giữ nguyên tham chiếu giữa các lần render khi chưa mở đoạn chat nào
const NO_MESSAGES: ChatMessage[] = [];

const withoutRaw = (product: ProductItem): ProductItem => {
  const copy = { ...product };
  delete copy.raw;
  return copy;
};

// Tên đoạn chat = câu hỏi đầu tiên người dùng nhập (rút gọn nếu quá dài)
const makeTitle = (text: string) => {
  const clean = text.replace(/\s+/g, ' ').trim();
  return clean.length > MAX_TITLE_LENGTH ? `${clean.slice(0, MAX_TITLE_LENGTH - 1)}…` : clean;
};

const isAbort = (err: unknown) => err instanceof DOMException && err.name === 'AbortError';

// Câu thông báo cho người dùng; chi tiết kỹ thuật chỉ ghi ra console
const friendlyError = (err: unknown): string => {
  // 429 (gửi quá nhanh), 403 (không có quyền): backend đã viết sẵn câu dành cho người dùng
  if (err instanceof ApiError && (err.status === 429 || err.status === 403)) return err.message;
  // fetch thất bại (mất mạng, máy chủ không phản hồi) ném TypeError
  if (err instanceof TypeError) return t('Không kết nối được tới trợ lý. Bạn kiểm tra kết nối mạng rồi thử lại nhé.');
  return t('Trợ lý đang bận hoặc gặp sự cố tạm thời. Bạn thử lại sau ít phút nhé.');
};

const errorMessage = (err: unknown, retry?: ChatMessage['retry']): ChatMessage => {
  console.error('[Chat]', err);
  return {
    id: `ai-err-${Date.now()}`,
    sender: 'assistant',
    content: friendlyError(err),
    timestamp: nowTime(),
    isError: true,
    retry
  };
};

// Nhãn hiển thị cho các giai đoạn `status` mà graph LangGraph phát ra
const STAGE_LABELS: Record<string, string> = {
  routing: msg('Phân tích yêu cầu bằng LLM'),
  retrieval: msg('Thu thập dữ liệu từ kho & các sàn'),
  relaxing: msg('Nới lỏng tiêu chí để tìm phương án gần nhất'),
  upsell: msg('Tìm thêm ngoài ngân sách cho đúng cấu hình'),
  parsing_link: msg('Bóc tách liên kết sản phẩm'),
  finding_deal: msg('Săn deal & mức giảm giá'),
  comparing: msg('Gọi tool so sánh'),
  synthesizing: msg('Soạn lời khuyên'),
};


// Nguồn trích dẫn = trang sản phẩm thật mà agent đã thu thập
const buildCitations = (products: ProductItem[]): CitationItem[] =>
  products.map((p, i) => ({
    id: `cite-${p.id}`,
    index: i + 1,
    sourceName: t('{name} tại {retailer}', { name: p.name, retailer: p.retailer }),
    platformId: p.platformId,
    price: formatVnd(p.currentPrice),
    officialPrice: p.originalPrice > p.currentPrice ? formatVnd(p.originalPrice) : undefined,
    excerpt: [p.warranty, p.returnPolicy, ...Object.entries(p.keySpecs).slice(0, 4).map(([k, v]) => `${k}: ${v}`)]
      .filter(Boolean)
      .join(' · '),
    verifiedDate: p.updatedAt ? new Date(p.updatedAt).toLocaleString(currentLocale()) : t('Vừa thu thập'),
    url: p.productUrl
  }));

export const SearchAssistantView: React.FC<SearchAssistantViewProps> = ({
  userId,
  savedIds,
  request,
  onRequestHandled,
  onToggleSave,
  trackedIds,
  onTrackPrice,
  onResults,
  onOpenPolicy,
}) => {
  useI18n(); // dựng lại khi đổi ngôn ngữ
  // Hội thoại lưu theo tài khoản; hội thoại đang mở là lựa chọn riêng của từng thiết bị
  const [conversations, setConversations] = useSyncedState<ChatConversation[]>(userId, 'conversations', []);
  const [activeId, setActiveId] = usePersistentState<string | null>(`shopping-ai.u.${userId}.active-conversation`, null);
  // Đoạn chat đang chờ agent trả lời (khóa chuyển / xóa đoạn chat trong lúc stream)
  const [busyId, setBusyId] = useState<string | null>(null);
  const isProcessing = busyId !== null;

  const [inputQuery, setInputQuery] = useState('');
  const [activeReasoning, setActiveReasoning] = useState<ReasoningStep[]>([]);
  // Sản phẩm đang mở ngăn chính sách nơi bán
  const [policyProduct, setPolicyProduct] = useState<ProductItem | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<CitationItem | null>(null);
  const [dismissedClarifications, setDismissedClarifications] = useState<Record<string, boolean>>({});

  const activeConversation = conversations.find(c => c.id === activeId) ?? null;
  const messages = activeConversation?.messages ?? NO_MESSAGES;
  const lastMessage = messages[messages.length - 1];
  // Câu hỏi làm rõ của lượt cuối (lưu cùng tin nhắn nên vẫn hiện khi mở lại đoạn chat)
  const activeClarification =
    !isProcessing && lastMessage?.sender === 'assistant' && lastMessage.clarification && !dismissedClarifications[lastMessage.id]
      ? lastMessage.clarification
      : null;

  const createConversation = (title: string): string => {
    const now = new Date().toISOString();
    const conv: ChatConversation = { id: newConversationId(), title: makeTitle(title), createdAt: now, updatedAt: now, messages: [] };
    setConversations(prev => [conv, ...prev].slice(0, MAX_CONVERSATIONS));
    setActiveId(conv.id);
    return conv.id;
  };

  const updateMessages = (convId: string, updater: (msgs: ChatMessage[]) => ChatMessage[]) =>
    setConversations(prev =>
      prev.map(c => (c.id === convId ? { ...c, messages: updater(c.messages), updatedAt: new Date().toISOString() } : c))
    );

  const handleCreateConversation = () => {
    if (isProcessing) return;
    setActiveId(null);
    setInputQuery('');
    setSelectedCitation(null);
  };

  const handleSelectConversation = (id: string) => {
    if (isProcessing) return;
    setActiveId(id);
    setSelectedCitation(null);
  };

  const handleDeleteConversation = (id: string) => {
    if (id === busyId) return;
    setConversations(prev => prev.filter(c => c.id !== id));
    if (id === activeId) setActiveId(null);
    // Xóa cả trí nhớ phiên ở backend; nếu backend đang tắt thì chỉ xóa trên trình duyệt
    deleteConversation(id).catch(() => undefined);
  };
  // Trạng thái ẩn/hiện bảng so sánh do người dùng bấm, ghi đè giá trị mặc định của tin nhắn
  const [tableToggles, setTableToggles] = useState<Record<string, boolean>>({});

  const chatEndRef = useRef<HTMLDivElement>(null);
  const handledRequestIds = useRef<Set<string>>(new Set());
  // Yêu cầu đang chạy, để nút Dừng huỷ được (rời màn hình chat cũng huỷ luôn)
  const abortRef = useRef<AbortController | null>(null);
  useEffect(() => () => abortRef.current?.abort(), []);

  const startRequest = () => {
    const controller = new AbortController();
    abortRef.current = controller;
    return controller;
  };
  const finishRequest = (controller: AbortController) => {
    if (abortRef.current === controller) abortRef.current = null;
  };
  const handleStop = () => abortRef.current?.abort();

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, activeReasoning, activeClarification]);

  // Xử lý yêu cầu gửi từ màn khác (Đã lưu, Tổng quan, Lịch sử)
  const handleIncomingRequest = useEffectEvent((request: ChatRequest) => {
    handledRequestIds.current.add(request.id);
    onRequestHandled();

    if (request.kind === 'restore') {
      const convId = createConversation(request.query);
      updateMessages(convId, prev => [
        ...prev,
        {
          id: `restore-${Date.now()}`,
          sender: 'assistant',
          content: t('Kết quả trước đó cho **"{query}"**: {count} sản phẩm đã được xếp hạng.', { query: request.query, count: request.products.length }),
          timestamp: nowTime(),
          products: request.products,
          query: request.query,
          showPolicyAction: true
        }
      ]);
      return;
    }

    void handleCompareProducts(request.products);
  });

  useEffect(() => {
    if (!request || isProcessing || handledRequestIds.current.has(request.id)) return;
    handleIncomingRequest(request);
  }, [request, isProcessing]);

  const handleCompareProducts = async (products: ProductItem[]) => {
    const question = t('So sánh giúp tôi: {names}', { names: products.map(p => p.name).join('; ') });
    const convId = createConversation(question);
    updateMessages(convId, prev => [...prev, { id: `usr-${Date.now()}`, sender: 'user', content: question, timestamp: nowTime() }]);
    setBusyId(convId);
    setActiveReasoning([{ id: 'step-compare', label: t(STAGE_LABELS.comparing), status: 'running', detail: t('{count} sản phẩm: {names}', { count: products.length, names: products.map(p => p.brand || p.name).join(', ') }) }]);
    const controller = startRequest();

    try {
      const { comparison, summary } = await compareProducts(convId, products, controller.signal);
      updateMessages(convId, prev => [
        ...prev,
        {
          id: `ai-cmp-${Date.now()}`,
          sender: 'assistant',
          // Không có bảng = không so sánh được (VD sản phẩm khác loại): chỉ hiện lời giải thích, không nói là đã so sánh
          content: comparison
            ? `${t('Tôi đã so sánh {count} sản phẩm theo giá, cấu hình, bảo hành và chính sách đổi trả.', { count: products.length })}\n\n${summary}`
            : summary,
          timestamp: nowTime(),
          products,
          comparison,
          showProductCards: !comparison,
          comparisonOpen: !!comparison,
          showPolicyAction: !!comparison
        }
      ]);
    } catch (err) {
      const reply: ChatMessage = isAbort(err)
        ? { id: `ai-cmp-${Date.now()}`, sender: 'assistant', content: '', timestamp: nowTime(), stopped: true }
        : errorMessage(err);
      updateMessages(convId, prev => [...prev, reply]);
    } finally {
      finishRequest(controller);
      setBusyId(null);
      setActiveReasoning([]);
    }
  };

  const promptSuggestions = [
    t('Tìm laptop mỏng nhẹ cho lập trình & chỉnh ảnh dưới 28 triệu'),
    t('Laptop gaming dưới 30 triệu có RTX 4070'),
    t('So sánh tai nghe Sony WH-1000XM5 và Bose QC Ultra'),
    t('Robot hút bụi lau nhà tự giặt giẻ dưới 15 triệu')
  ];

  // displayText: chữ hiện trong bong bóng chat khi khác câu gửi đi (VD nhãn mức ngân sách đã dịch)
  // isRetry: gửi lại câu hỏi cuối, thay câu trả lời lỗi / đã dừng thay vì thêm tin nhắn người dùng mới
  const handleSendQuery = async (queryText?: string, displayText?: string, isRetry = false) => {
    const text = queryText || inputQuery;
    if (!text.trim() || isProcessing) return;
    const shown = displayText || text;

    // Câu hỏi đầu tiên của đoạn chat mới trở thành tên đoạn chat
    const convId = activeConversation?.id ?? createConversation(shown);
    if (isRetry) {
      // Bỏ câu trả lời lỗi / dang dở sau câu hỏi cuối của người dùng
      updateMessages(convId, prev => {
        const lastUser = prev.map(m => m.sender).lastIndexOf('user');
        return prev.slice(0, lastUser + 1);
      });
    } else {
      updateMessages(convId, prev => [...prev, { id: `usr-${Date.now()}`, sender: 'user', content: shown, timestamp: nowTime() }]);
    }
    if (!queryText) setInputQuery('');
    setBusyId(convId);
    const controller = startRequest();
    const retry = { query: text, display: displayText };

    // Tin nhắn của agent được dựng dần theo từng sự kiện SSE
    const draft: ChatMessage = { id: `ai-${Date.now()}`, sender: 'assistant', content: '', timestamp: nowTime(), query: text };
    const upsert = () => {
      const snapshot = { ...draft };
      updateMessages(convId, prev => (prev.some(m => m.id === snapshot.id) ? prev.map(m => (m.id === snapshot.id ? snapshot : m)) : [...prev, snapshot]));
    };
    const steps: ReasoningStep[] = [];

    try {
      await streamChat(convId, text, {
        onStatus: (stage, message) => {
          steps.forEach(st => { st.status = 'completed'; });
          steps.push({ id: `step-${steps.length + 1}`, label: t(STAGE_LABELS[stage] ?? stage), detail: message && t(message), status: 'running' });
          setActiveReasoning(steps.map(st => ({ ...st })));
        },
        onProducts: products => {
          // Bỏ bản gốc backend để đoạn chat lưu trong localStorage gọn hơn (tool so sánh tự dựng lại khi cần)
          draft.products = products.map(withoutRaw);
          draft.showPolicyAction = true;
          upsert();
        },
        onComparison: comparison => {
          draft.comparison = comparison;
          upsert();
        },
        onClarification: question => {
          draft.clarification = question;
        },
        onToken: token => {
          draft.content += token;
          upsert();
        },
        onSuggestions: suggestions => {
          draft.suggestions = suggestions;
        },
        onDone: info => {
          draft.notes = info.searchNotes;
        }
      }, { signal: controller.signal });
      if (!draft.content && !draft.products) {
        draft.content = t('Tôi chưa có câu trả lời cho yêu cầu này. Bạn thử diễn đạt lại giúp tôi nhé.');
      }
      upsert();
      if (draft.products?.length) onResults(text, draft.products);
    } catch (err) {
      if (isAbort(err)) {
        // Người dùng bấm Dừng: giữ phần đã nhận được, bỏ câu hỏi làm rõ / gợi ý của lượt dang dở
        draft.stopped = true;
        draft.retry = retry;
        draft.clarification = undefined;
        draft.suggestions = undefined;
        upsert();
        if (draft.products?.length) onResults(text, draft.products);
      } else {
        // Giữ phần đã nhận được (nếu có), thêm thông báo lỗi
        updateMessages(convId, prev => [...prev.filter(m => m.id !== draft.id || m.content || m.products), errorMessage(err, retry)]);
      }
    } finally {
      finishRequest(controller);
      setBusyId(null);
      setActiveReasoning([]);
    }
  };

  const handleRetry = (retry: NonNullable<ChatMessage['retry']>) => void handleSendQuery(retry.query, retry.display, true);

  // Bỏ qua = bảo trợ lý tìm luôn với thông tin đang có; tin nhắn cũ không có skipValue thì chỉ ẩn thẻ
  const handleSkipClarification = () => {
    const skip = activeClarification?.skipValue;
    if (skip) {
      void handleSendQuery(skip, t('Bỏ qua, tìm luôn'));
    } else if (lastMessage) {
      setDismissedClarifications(prev => ({ ...prev, [lastMessage.id]: true }));
    }
  };

  const lastAssistantId = [...messages].reverse().find(m => m.sender === 'assistant')?.id;

  return (
    <div className="flex h-[calc(100vh-3.5rem)] relative overflow-hidden bg-canvas">
      <ConversationList
        conversations={conversations}
        activeId={activeId}
        busyId={busyId}
        onSelect={handleSelectConversation}
        onCreate={handleCreateConversation}
        onDelete={handleDeleteConversation}
      />

      <div className="flex-1 flex flex-col h-full overflow-hidden min-w-0">
        {/* Màn hình hẹp: chọn đoạn chat bằng menu thả xuống */}
        <div className="md:hidden flex items-center gap-2 px-4 py-2 bg-white border-b border-stone-200">
          <select
            value={activeId ?? ''}
            onChange={e => (e.target.value ? handleSelectConversation(e.target.value) : handleCreateConversation())}
            disabled={isProcessing}
            className="flex-1 min-w-0 text-xs bg-stone-50 border border-stone-200 rounded-lg px-2 py-1.5"
          >
            <option value="">{t('Hội thoại mới')}</option>
            {conversations.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
          <button
            onClick={handleCreateConversation}
            disabled={isProcessing}
            className="shrink-0 p-2 rounded-lg bg-stone-900 text-amber-50 disabled:bg-stone-300"
            title={t('Hội thoại mới')}
          >
            <MessageSquarePlus className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 max-w-4xl mx-auto w-full">
          {messages.length === 0 && (
            <div className="bg-white p-6 rounded-2xl border border-stone-200/90 shadow-sm text-center space-y-4">
              <div className="w-12 h-12 mx-auto rounded-xl bg-amber-50 text-amber-900 flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-amber-800" />
              </div>
              <div>
                <h2 className="text-base font-bold text-stone-900">{t('Mô tả nhu cầu mua sắm của bạn')}</h2>
                <p className="text-xs text-stone-600 mt-1 max-w-md mx-auto">
                  {t('Trợ lý sẽ phân tích yêu cầu, thu thập dữ liệu từ các sàn thương mại điện tử, lọc và xếp hạng sản phẩm phù hợp.')}
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left pt-2">
                {promptSuggestions.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendQuery(prompt)}
                    className="p-3 bg-stone-50 hover:bg-stone-100/90 border border-stone-200/80 rounded-xl text-xs text-stone-700 hover:text-stone-900 transition-all flex items-start justify-between group"
                  >
                    <span>{prompt}</span>
                    <ChevronRight className="w-4 h-4 text-stone-400 group-hover:text-stone-700 shrink-0 mt-0.5 ml-2" />
                  </button>
                ))}
              </div>

              <button
                onClick={() => onOpenPolicy()}
                className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-900 hover:text-amber-950"
              >
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>{t('Hoặc tra cứu chính sách bảo hành, đổi trả giữa các sàn')}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {[{ ...WELCOME_MESSAGE, content: t(WELCOME_MESSAGE.content), timestamp: t(WELCOME_MESSAGE.timestamp) }, ...messages].map((msg) => {
            const hasProducts = !!msg.products && msg.products.length > 0;
            const tableOpen = tableToggles[msg.id] ?? !!msg.comparisonOpen;
            const citations = msg.citations ?? (hasProducts && msg.sender === 'assistant' ? buildCitations(msg.products!) : []);
            return (
            <div key={msg.id} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
              <div
                className={`${hasProducts ? 'w-full max-w-3xl' : 'max-w-2xl w-fit'} min-w-0 text-xs sm:text-sm leading-relaxed p-5 rounded-2xl shadow-sm ${
                  msg.sender === 'user'
                    ? 'bg-stone-900 text-stone-100 rounded-tr-none'
                    : 'bg-white text-stone-800 border border-stone-200/90 rounded-tl-none space-y-3'
                }`}
              >
                {msg.sender === 'assistant' && (
                  <div className="flex items-center justify-between pb-2 border-b border-stone-100 text-[11px] font-semibold text-stone-500 uppercase tracking-wider">
                    <span className="flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-amber-700" />
                      {t('Trợ lý mua sắm')}
                    </span>
                    <span className="text-stone-600 font-mono">{msg.timestamp}</span>
                  </div>
                )}

                {msg.sender === 'assistant' ? (
                  <div className={msg.isError ? 'flex gap-2 text-red-800' : ''}>
                    {msg.isError && <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />}
                    {msg.content && <Markdown text={msg.content} />}
                    {msg.stopped && (
                      <div className={`flex items-center gap-1.5 text-[11px] italic text-stone-500 ${msg.content ? 'mt-2' : ''}`}>
                        <Square className="w-3 h-3" />
                        {t('Đã dừng trả lời')}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="whitespace-pre-line">{msg.content}</div>
                )}

                {msg.notes && msg.notes.length > 0 && (
                  <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-xl text-[11px] text-stone-700 space-y-1">
                    <div className="flex items-center gap-1 font-semibold text-amber-900">
                      <AlertTriangle className="w-3.5 h-3.5" /> {t('Lưu ý về dữ liệu')}
                    </div>
                    <ul className="list-disc pl-4 space-y-0.5">
                      {msg.notes.map((n, i) => <li key={i} className="whitespace-pre-line">{t(n)}</li>)}
                    </ul>
                  </div>
                )}

                {hasProducts && msg.showProductCards !== false && (
                  <div className="pt-1 space-y-2">
                    <span className="text-[11px] font-semibold text-stone-500 uppercase tracking-wider">
                      {t('Sản phẩm đề xuất ({count})', { count: msg.products!.length })}
                    </span>
                    {msg.products!.map((p, i) => (
                      <ProductCard
                        key={p.id}
                        product={p}
                        rank={i + 1}
                        isSaved={savedIds.includes(p.id)}
                        onToggleSave={() => onToggleSave(p, msg.query ?? '')}
                        isTracked={trackedIds.includes(p.id)}
                        onTrackPrice={() => onTrackPrice(p)}
                        onOpenPolicy={() => setPolicyProduct(p)}
                      />
                    ))}
                  </div>
                )}

                {hasProducts && msg.products!.length > 1 && (
                  <div className="space-y-2">
                    <button
                      onClick={() => setTableToggles(prev => ({ ...prev, [msg.id]: !tableOpen }))}
                      className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-stone-700 hover:text-stone-950"
                    >
                      <Table2 className="w-3.5 h-3.5" />
                      <span>{tableOpen ? t('Ẩn bảng so sánh') : t('Xem bảng so sánh chi tiết')}</span>
                      <ChevronDown className={`w-3.5 h-3.5 transition-transform ${tableOpen ? 'rotate-180' : ''}`} />
                    </button>
                    {tableOpen && (
                      <ComparisonTable
                        products={msg.products!}
                        comparison={msg.comparison}
                        savedIds={savedIds}
                        onToggleSave={p => onToggleSave(p, msg.query ?? '')}
                      />
                    )}
                  </div>
                )}

                {citations.length > 0 && (
                  <div className="pt-3 border-t border-stone-100 flex flex-wrap items-center gap-2">
                    <span className="text-[11px] font-medium text-stone-500 flex items-center gap-1">
                      <BookOpen className="w-3.5 h-3.5 text-stone-500" />
                      {t('Nguồn ({count}):', { count: citations.length })}
                    </span>
                    {citations.map((cite) => (
                      <button
                        key={cite.id}
                        onClick={() => setSelectedCitation(cite)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-stone-700 bg-stone-100 hover:bg-amber-100 hover:text-amber-900 rounded-md border border-stone-200 transition-colors"
                      >
                        <span className="font-mono text-amber-800 font-bold">[{cite.index}]</span>
                        <span>{getPlatformName(cite.platformId)}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {msg.id === lastAssistantId && !isProcessing && !activeClarification && msg.suggestions && msg.suggestions.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {msg.suggestions.map(sug => (
                    <button
                      key={sug}
                      onClick={() => handleSendQuery(sug)}
                      className="px-3 py-1.5 bg-white border border-stone-200 rounded-full text-[11px] text-stone-700 hover:border-stone-400 hover:text-stone-950 transition-colors"
                    >
                      {sug}
                    </button>
                  ))}
                </div>
              )}

              {msg.retry && msg.id === lastMessage?.id && !isProcessing && (
                <button
                  onClick={() => handleRetry(msg.retry!)}
                  className="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-stone-300 rounded-full text-[11px] font-semibold text-stone-800 hover:border-stone-500 hover:text-stone-950 transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  {t('Thử lại')}
                </button>
              )}

              {msg.showPolicyAction && (
                <button
                  onClick={() => onOpenPolicy(msg.products?.length ? {
                    query: msg.query ?? '',
                    productPlatformIds: [...new Set(msg.products.map(p => p.platformId))],
                  } : undefined)}
                  className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-white border border-stone-300 text-stone-800 rounded-xl text-xs font-semibold hover:bg-stone-50 shadow-sm transition-all"
                >
                  <ShieldCheck className="w-4 h-4 text-emerald-700" />
                  <span>{t('Tra cứu chính sách bảo hành & đổi trả các sàn')}</span>
                </button>
              )}
            </div>
            );
          })}

          {isProcessing && activeReasoning.length === 0 && (
            <div className="inline-flex items-center gap-2 px-4 py-2.5 bg-white rounded-2xl border border-stone-200/90 shadow-sm text-xs text-stone-600 animate-fadeIn">
              <RotateCw className="w-3.5 h-3.5 text-amber-700 animate-spin" />
              <span>{t('Đang trả lời...')}</span>
            </div>
          )}

          {isProcessing && activeReasoning.length > 0 && (
            <div className="bg-white p-5 rounded-2xl border border-stone-200/90 shadow-sm space-y-3 animate-fadeIn">
              <div className="flex items-center gap-2 text-xs font-bold text-stone-800">
                <RotateCw className="w-4 h-4 text-amber-700 animate-spin" />
                <span>{t('Tiến trình của agent')}</span>
              </div>
              <div className="space-y-2 pt-1">
                {activeReasoning.map((step) => (
                  <div key={step.id} className="flex items-start gap-2.5 text-xs">
                    {step.status === 'completed' && <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />}
                    {step.status === 'running' && (
                      <div className="w-4 h-4 rounded-full border-2 border-amber-600 border-t-transparent animate-spin shrink-0 mt-0.5" />
                    )}
                    {step.status === 'pending' && <div className="w-3 h-3 rounded-full bg-stone-200 shrink-0 mt-1 mx-0.5" />}
                    <div>
                      <span className={step.status === 'completed' ? 'text-stone-800 font-medium' : step.status === 'running' ? 'text-amber-900 font-semibold' : 'text-stone-400'}>
                        {step.label}
                      </span>
                      {step.detail && <p className="text-[11px] text-stone-500 mt-0.5">{step.detail}</p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeClarification && (
            <div className="bg-panel p-5 rounded-2xl border-2 border-amber-200/80 shadow-md space-y-4 animate-slideUp">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-stone-900">{t('Làm rõ nhu cầu để xếp hạng chính xác hơn')}</span>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-stone-900">{activeClarification.question}</h3>
                {activeClarification.contextHint && (
                  <p className="text-xs text-stone-500 mt-1">{activeClarification.contextHint}</p>
                )}
              </div>

              {/* Bấm một lựa chọn là gửi luôn; lựa chọn "cứ tìm" nằm ở nút Bỏ qua bên dưới */}
              <div className="flex flex-wrap gap-2">
                {activeClarification.options
                  .filter(opt => opt.value !== activeClarification.skipValue)
                  .map(opt => (
                    <button
                      key={opt.id}
                      onClick={() => void handleSendQuery(opt.value, opt.label)}
                      className="px-3.5 py-2 rounded-xl border border-stone-200 bg-white text-xs font-semibold text-stone-800 hover:border-stone-800 hover:bg-white shadow-sm transition-all"
                    >
                      {opt.label}
                    </button>
                  ))}
              </div>

              {activeClarification.allowCustomInput && (
                <p className="text-[11px] text-stone-500">{t('Hoặc gõ câu trả lời của bạn vào ô chat bên dưới (VD: "tầm 18 triệu, dùng để học lập trình").')}</p>
              )}

              <div className="flex items-center justify-end pt-2 border-t border-amber-100">
                <button onClick={handleSkipClarification} className="text-xs font-medium text-stone-500 hover:text-stone-800">
                  {t('Bỏ qua, tìm luôn')}
                </button>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        <div className="p-4 bg-white border-t border-stone-200/90 shrink-0">
          <div className="max-w-4xl mx-auto space-y-2">
            <div className="text-[11px] text-stone-500 flex items-center gap-1.5 justify-center">
              <ShieldCheck className="w-3.5 h-3.5 text-amber-700" />
              <span>{t('AI có thể sai. Hãy kiểm tra lại thông số, giá và điều kiện bảo hành trước khi thanh toán.')}</span>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendQuery();
              }}
              className="flex items-center gap-2 bg-inset border border-stone-300 rounded-xl p-1.5 focus-within:border-stone-800 focus-within:ring-1 focus-within:ring-stone-800 transition-all"
            >
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                maxLength={MAX_MESSAGE_CHARS}
                placeholder={t('VD: Laptop gaming dưới 30 triệu, RTX 4070, chơi game nặng...')}
                className="flex-1 px-3 py-2 text-xs sm:text-sm bg-transparent border-none outline-none text-stone-900 placeholder:text-stone-400"
                disabled={isProcessing}
              />
              {inputQuery.length > MAX_MESSAGE_CHARS * 0.9 && (
                <span className={`text-[11px] font-mono shrink-0 ${inputQuery.length >= MAX_MESSAGE_CHARS ? 'text-red-600' : 'text-stone-400'}`}>
                  {inputQuery.length}/{MAX_MESSAGE_CHARS}
                </span>
              )}
              {isProcessing ? (
                <button
                  type="button"
                  onClick={handleStop}
                  className="w-9 h-9 rounded-lg flex items-center justify-center bg-stone-900 text-amber-50 hover:bg-stone-800 shadow-sm transition-all"
                  title={t('Dừng trả lời')}
                  aria-label={t('Dừng trả lời')}
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!inputQuery.trim()}
                  className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all ${
                    inputQuery.trim()
                      ? 'bg-stone-900 text-amber-50 hover:bg-stone-800 shadow-sm'
                      : 'bg-stone-200 text-stone-400 cursor-not-allowed'
                  }`}
                  title={t('Gửi')}
                  aria-label={t('Gửi')}
                >
                  <Send className="w-4 h-4" />
                </button>
              )}
            </form>
          </div>
        </div>
      </div>

      {selectedCitation && <CitationPanel citation={selectedCitation} onClose={() => setSelectedCitation(null)} />}

      {policyProduct && (
        <PolicyDrawer
          product={policyProduct}
          onClose={() => setPolicyProduct(null)}
          onOpenFull={request => {
            setPolicyProduct(null);
            onOpenPolicy(request);
          }}
        />
      )}
    </div>
  );
};
