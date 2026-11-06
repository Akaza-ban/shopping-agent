import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Sparkles, 
  CheckCircle2, 
  RotateCw, 
  ShieldCheck, 
  FileText, 
  ExternalLink, 
  ThumbsUp, 
  AlertCircle, 
  HelpCircle, 
  X,
  ChevronRight,
  BookOpen,
  Calendar,
  Layers,
  ArrowRight
} from 'lucide-react';
import { ChatMessage, CitationItem, ClarificationQuestion, ReasoningStep } from '../types.ts';
import { SAMPLE_CITATIONS, runReasoningPipeline } from '../services/geminiService.ts';

interface SearchAssistantViewProps {
  onOpenDossier: () => void;
}

export const SearchAssistantView: React.FC<SearchAssistantViewProps> = ({
  onOpenDossier,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'msg-welcome',
      sender: 'assistant',
      content: 'Xin chào, tôi là trợ lý mua sắm AI có trích dẫn căn cứ. Tôi có thể hỗ trợ bạn tra cứu thông số kỹ thuật, đối chiếu giá sàn lịch sử từ các gian hàng chính hãng (Shopee Mall, Tiki Official, AASP), rà soát rủi ro bảo hành và lọc đánh giá seeding. Bạn muốn tìm kiếm sản phẩm nào hôm nay?',
      timestamp: 'Hôm nay',
      feedbackState: 'useful'
    }
  ]);

  const [inputQuery, setInputQuery] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeReasoning, setActiveReasoning] = useState<ReasoningStep[]>([]);
  
  // Selected citation for side drawer (matching video 01:01 - 01:06)
  const [selectedCitation, setSelectedCitation] = useState<CitationItem | null>(null);

  // Clarification questions state
  const [activeClarification, setActiveClarification] = useState<ClarificationQuestion | null>(null);
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null);
  const [customInputValue, setCustomInputValue] = useState('');

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, activeReasoning, activeClarification]);

  const promptSuggestions = [
    'Tìm laptop mỏng nhẹ cho lập trình & chỉnh ảnh dưới 28 triệu',
    'So sánh tai nghe Sony WH-1000XM5 và Bose QC Ultra',
    'Kiểm tra rủi ro bảo hành màn hình MacBook M3 khi mua trên sàn TMĐT',
    'Robot hút bụi lau nhà nào tự giặt giẻ dưới 15 triệu tốt nhất?'
  ];

  const handleSendQuery = async (queryText?: string) => {
    const text = queryText || inputQuery;
    if (!text.trim() || isProcessing) return;

    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    if (!queryText) setInputQuery('');
    setIsProcessing(true);

    // Simulate system reasoning timeline
    await runReasoningPipeline(text, (steps) => {
      setActiveReasoning(steps);
    });

    // Offer interactive clarification card (like in video 01:44)
    const clarificationCard: ClarificationQuestion = {
      id: 'clar-1',
      stepNumber: 1,
      totalSteps: 4,
      question: 'Ngân sách tối đa dự kiến của bạn cho đợt mua sắm này là bao nhiêu?',
      contextHint: 'Để trợ lý lọc cấu hình tối ưu và tránh các mẫu máy bị thiếu RAM/bộ nhớ.',
      options: [
        { id: 'opt-1', label: 'Dưới 20 triệu đồng', sublabel: 'Phân khúc văn phòng cơ bản' },
        { id: 'opt-2', label: '20 - 28 triệu đồng', sublabel: 'Phân khúc cận cao cấp (Khuyên dùng)' },
        { id: 'opt-3', label: '28 - 35 triệu đồng', sublabel: 'Phân khúc cao cấp & đồ họa chuyên nghiệp' },
        { id: 'opt-4', label: 'Tự nhập mức ngân sách cụ thể' }
      ],
      allowCustomInput: true
    };

    setActiveClarification(clarificationCard);

    // AI generated response with inline citations
    const assistantMsg: ChatMessage = {
      id: `ai-${Date.now()}`,
      sender: 'assistant',
      content: `Dựa trên kết quả đối chiếu dữ liệu sàn chính hãng và thông số kiểm thử thực tế [1]:

Đối với tầm giá dưới 28 triệu đồng, lựa chọn tối ưu hàng đầu hiện nay là **Apple MacBook Air 13 inch M3 (16GB RAM / 512GB SSD)** với mức giá sàn ghi nhận **28.490.000 ₫** [1].

**Điểm mạnh nổi bật:**
- Vi xử lý Apple M3 3nm chạy siêu mát, không quạt tản nhiệt, thời lượng pin thực tế đạt 14-16 giờ liên tục [3].
- Màn hình Liquid Retina chuẩn màu 100% DCI-P3, độ sáng 500 nits đáp ứng xuất sắc công việc đồ họa & UI/UX [2].
- Phiên bản 16GB RAM giải quyết triệt để vấn đề tràn bộ nhớ (swap memory) khi mở nhiều tab Figma và trình duyệt.

**Lưu ý rủi ro trước khi chốt đơn:**
- RAM và SSD bị hàn chết trên bo mạch (Unified Architecture), hoàn toàn không thể nâng cấp thủ công sau này.
- Chính sách bảo hành: Cần mua từ gian hàng ủy quyền AASP trên Shopee Mall / Tiki Official để đảm bảo quyền lợi đổi mới trong 30 ngày nếu phát hiện lỗi phần cứng nhà sản xuất [2].

Bạn có thể trả lời các câu hỏi làm rõ bên dưới để trợ lý hoàn thiện hồ sơ so sánh tự động hoặc chuyển sang chế độ soạn thảo dự thảo quyết định mua sắm.`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      citations: SAMPLE_CITATIONS,
      reasoningSteps: activeReasoning
    };

    setMessages(prev => [...prev, assistantMsg]);
    setIsProcessing(false);
  };

  const handleConfirmClarification = () => {
    if (!selectedOptionId && !customInputValue) return;
    
    // Progress to next step or finish
    const nextQuestion: ClarificationQuestion = {
      id: 'clar-2',
      stepNumber: 2,
      totalSteps: 4,
      question: 'Nhu cầu ưu tiên cao nhất của bạn là gì?',
      contextHint: 'Xác định trọng tâm đánh đổi giữa trọng lượng và hiệu năng tản nhiệt.',
      options: [
        { id: 'opt-weight', label: 'Trọng lượng siêu nhẹ (< 1.3kg)', sublabel: 'Thường xuyên di chuyển công tác' },
        { id: 'opt-ram', label: 'Dung lượng RAM lớn (32GB)', sublabel: 'Lập trình nhiều máy ảo, xử lý dữ liệu nặng' },
        { id: 'opt-screen', label: 'Màn hình OLED 120Hz chuẩn màu', sublabel: 'Thiết kế đồ họa & giải trí điện ảnh' }
      ]
    };

    if (activeClarification?.stepNumber === 1) {
      setActiveClarification(nextQuestion);
      setSelectedOptionId(null);
      setCustomInputValue('');
    } else {
      setActiveClarification(null);
      // Add confirmation message
      setMessages(prev => [
        ...prev,
        {
          id: `clar-confirm-${Date.now()}`,
          sender: 'assistant',
          content: 'Đã nhận đủ thông tin làm rõ! Hệ thống đã tự động đồng bộ sang **Thiết lập dự thảo quyết định mua sắm**. Bạn có thể bấm vào nút dưới đây để xem bảng so sánh song song và hồ sơ chi tiết.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    }
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)] relative overflow-hidden bg-[#faf9f5]">
      {/* Main Chat Flow Area */}
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Messages Scroll View */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 max-w-4xl mx-auto w-full">
          {/* Header indicator inside chat (like video: "Bắt đầu bằng một câu hỏi cụ thể...") */}
          {messages.length === 1 && (
            <div className="bg-white p-6 rounded-2xl border border-stone-200/90 shadow-sm text-center space-y-4">
              <div className="w-12 h-12 mx-auto rounded-xl bg-amber-50 text-amber-900 flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-amber-800" />
              </div>
              <div>
                <h2 className="text-base font-bold text-stone-900">
                  Tra cứu có kiểm chứng & Căn cứ giá sàn
                </h2>
                <p className="text-xs text-stone-600 mt-1 max-w-md mx-auto">
                  Trợ lý AI hỗ trợ bạn tra cứu thông số kỹ thuật, đối chiếu giá sàn lịch sử từ các gian hàng chính hãng (Shopee Mall, Tiki Official, AASP), rà soát rủi ro bảo hành và lọc đánh giá seeding.
                </p>
              </div>

              {/* 4 Example Prompts Grid (matching video 00:19) */}
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
            </div>
          )}

          {/* Chat Messages */}
          {messages.map((msg) => (
            <div 
              key={msg.id}
              className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div 
                className={`max-w-2xl text-xs sm:text-sm leading-relaxed p-5 rounded-2xl shadow-sm ${
                  msg.sender === 'user'
                    ? 'bg-stone-900 text-stone-100 rounded-tr-none'
                    : 'bg-white text-stone-800 border border-stone-200/90 rounded-tl-none space-y-3'
                }`}
              >
                {msg.sender === 'assistant' && (
                  <div className="flex items-center justify-between pb-2 border-b border-stone-100 text-[11px] font-semibold text-stone-500 uppercase tracking-wider">
                    <span className="flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-amber-700" />
                      Phản hồi của trợ lý mua sắm
                    </span>
                    <span className="text-stone-600 font-mono">{msg.timestamp}</span>
                  </div>
                )}

                {/* Content with rich markdown styling */}
                <div className="whitespace-pre-line">
                  {msg.content}
                </div>

                {/* Inline Citations Buttons */}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="pt-3 border-t border-stone-100 flex flex-wrap items-center gap-2">
                    <span className="text-[11px] font-medium text-stone-500 flex items-center gap-1">
                      <BookOpen className="w-3.5 h-3.5 text-stone-500" />
                      Căn cứ trích dẫn ({msg.citations.length}):
                    </span>
                    {msg.citations.map((cite) => (
                      <button
                        key={cite.id}
                        onClick={() => setSelectedCitation(cite)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-stone-700 bg-stone-100 hover:bg-amber-100 hover:text-amber-900 rounded-md border border-stone-200 transition-colors"
                      >
                        <span className="font-mono text-amber-800 font-bold">[{cite.index}]</span>
                        <span>{cite.sourceName.slice(0, 24)}...</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Feedback Row (like video: "Hữu ích / Thiếu căn cứ / Chưa chính xác") */}
                {msg.sender === 'assistant' && msg.id !== 'msg-welcome' && (
                  <div className="pt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-stone-500">
                    <span className="text-[11px]">Câu trả lời này có hữu ích không?</span>
                    <div className="flex items-center gap-1.5">
                      <button className="px-2 py-1 text-[11px] font-medium text-stone-700 hover:bg-stone-100 rounded border border-stone-200 flex items-center gap-1">
                        <ThumbsUp className="w-3 h-3 text-emerald-600" />
                        <span>Hữu ích</span>
                      </button>
                      <button className="px-2 py-1 text-[11px] font-medium text-stone-700 hover:bg-stone-100 rounded border border-stone-200 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3 text-amber-600" />
                        <span>Thiếu căn cứ</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Action button to switch to Dossier view if AI suggested it */}
              {msg.id.startsWith('clar-confirm') && (
                <button
                  onClick={onOpenDossier}
                  className="mt-3 inline-flex items-center gap-2 px-4 py-2 bg-stone-900 text-amber-50 rounded-xl text-xs font-semibold hover:bg-stone-800 shadow-sm transition-all"
                >
                  <FileText className="w-4 h-4" />
                  <span>Mở Hồ sơ so sánh song song & Dự thảo</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          ))}

          {/* Live System Reasoning Timeline (matching video 00:38 - 00:46) */}
          {isProcessing && (
            <div className="bg-white p-5 rounded-2xl border border-stone-200/90 shadow-sm space-y-3 animate-fadeIn">
              <div className="flex items-center gap-2 text-xs font-bold text-stone-800">
                <RotateCw className="w-4 h-4 text-amber-700 animate-spin" />
                <span>Tiến trình hệ thống đang xử lý</span>
              </div>
              <div className="space-y-2 pt-1">
                {activeReasoning.map((step) => (
                  <div key={step.id} className="flex items-start gap-2.5 text-xs">
                    {step.status === 'completed' && (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    )}
                    {step.status === 'running' && (
                      <div className="w-4 h-4 rounded-full border-2 border-amber-600 border-t-transparent animate-spin shrink-0 mt-0.5" />
                    )}
                    {step.status === 'pending' && (
                      <div className="w-3 h-3 rounded-full bg-stone-200 shrink-0 mt-1 mx-0.5" />
                    )}
                    <div>
                      <span className={`${step.status === 'completed' ? 'text-stone-800 font-medium' : step.status === 'running' ? 'text-amber-900 font-semibold' : 'text-stone-400'}`}>
                        {step.label}
                      </span>
                      {step.detail && (
                        <p className="text-[11px] text-stone-500 mt-0.5">{step.detail}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Interactive Clarification Card (matching video 01:44 - 02:08) */}
          {activeClarification && (
            <div className="bg-[#fcfbf9] p-5 rounded-2xl border-2 border-amber-200/80 shadow-md space-y-4 animate-slideUp">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-md bg-amber-100 text-amber-900 text-xs font-bold flex items-center justify-center">
                    {activeClarification.stepNumber}
                  </span>
                  <span className="text-xs font-bold text-stone-900">
                    Trợ lý làm rõ yêu cầu mua sắm
                  </span>
                </div>
                <span className="text-xs font-mono font-semibold text-stone-500">
                  {activeClarification.stepNumber}/{activeClarification.totalSteps}
                </span>
              </div>

              <div>
                <h3 className="text-sm font-semibold text-stone-900">
                  {activeClarification.question}
                </h3>
                {activeClarification.contextHint && (
                  <p className="text-xs text-stone-500 mt-1">
                    {activeClarification.contextHint}
                  </p>
                )}
              </div>

              {/* Options selection */}
              <div className="space-y-2">
                {activeClarification.options.map((opt) => (
                  <label
                    key={opt.id}
                    onClick={() => setSelectedOptionId(opt.id)}
                    className={`flex items-start gap-3 p-3 rounded-xl border text-xs cursor-pointer transition-all ${
                      selectedOptionId === opt.id
                        ? 'bg-white border-stone-800 shadow-sm text-stone-900 font-medium'
                        : 'bg-white/80 border-stone-200 text-stone-700 hover:bg-white hover:border-stone-300'
                    }`}
                  >
                    <input 
                      type="radio" 
                      name="clarification" 
                      checked={selectedOptionId === opt.id}
                      onChange={() => setSelectedOptionId(opt.id)}
                      className="mt-0.5 text-stone-900 focus:ring-stone-900"
                    />
                    <div className="flex-1">
                      <div className="font-semibold text-stone-900">{opt.label}</div>
                      {opt.sublabel && (
                        <div className="text-[11px] text-stone-500 mt-0.5">{opt.sublabel}</div>
                      )}
                    </div>
                  </label>
                ))}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-2 border-t border-amber-100">
                <button
                  onClick={() => setActiveClarification(null)}
                  className="text-xs font-medium text-stone-500 hover:text-stone-800"
                >
                  Bỏ qua câu này
                </button>
                <button
                  onClick={handleConfirmClarification}
                  className="px-4 py-2 bg-stone-900 text-amber-50 text-xs font-semibold rounded-lg hover:bg-stone-800 transition-colors"
                >
                  Xác nhận lựa chọn
                </button>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input Bar with Disclaimer (matching video 00:26) */}
        <div className="p-4 bg-white border-t border-stone-200/90 shrink-0">
          <div className="max-w-4xl mx-auto space-y-2">
            <div className="text-[11px] text-stone-500 flex items-center gap-1.5 justify-center">
              <ShieldCheck className="w-3.5 h-3.5 text-amber-700" />
              <span>AI có thể sai. Mọi kết quả mua sắm cần được người dùng kiểm tra lại thông số và điều kiện bảo hành trước khi thanh toán.</span>
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendQuery();
              }}
              className="flex items-center gap-2 bg-[#f8f7f4] border border-stone-300 rounded-xl p-1.5 focus-within:border-stone-800 focus-within:ring-1 focus-within:ring-stone-800 transition-all"
            >
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                placeholder="Nhập câu hỏi mua sắm, tên sản phẩm hoặc dán link Shopee, Tiki..."
                className="flex-1 px-3 py-2 text-xs sm:text-sm bg-transparent border-none outline-none text-stone-900 placeholder:text-stone-400"
                disabled={isProcessing}
              />
              <button
                type="submit"
                disabled={!inputQuery.trim() || isProcessing}
                className={`w-9 h-9 rounded-lg flex items-center justify-center transition-all ${
                  inputQuery.trim() && !isProcessing
                    ? 'bg-stone-900 text-amber-50 hover:bg-stone-800 shadow-sm'
                    : 'bg-stone-200 text-stone-400 cursor-not-allowed'
                }`}
                title="Gửi câu hỏi"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      </div>

      {/* Evidence / Citation Side Drawer (matching video 01:01 - 01:06) */}
      {selectedCitation && (
        <aside className="w-96 shrink-0 h-full bg-white border-l border-stone-200 shadow-lg flex flex-col z-30 animate-slideLeft">
          <div className="p-4 border-b border-stone-200 flex items-center justify-between bg-stone-50">
            <div className="flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-amber-800" />
              <h3 className="text-xs font-bold text-stone-900 uppercase tracking-wider">
                Chi tiết nguồn trích dẫn
              </h3>
            </div>
            <button
              onClick={() => setSelectedCitation(null)}
              className="w-7 h-7 rounded-lg hover:bg-stone-200 flex items-center justify-center text-stone-500"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="p-5 flex-1 overflow-y-auto space-y-4 text-xs leading-relaxed">
            <div>
              <span className="text-[10px] font-bold text-amber-800 uppercase tracking-wider">
                Nguồn [{selectedCitation.index}]
              </span>
              <h4 className="text-sm font-bold text-stone-900 mt-1">
                {selectedCitation.sourceName}
              </h4>
              <div className="flex items-center gap-2 mt-1 text-[11px] text-stone-500">
                <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-medium">
                  {selectedCitation.sourceType}
                </span>
                <span>·</span>
                <span>{selectedCitation.reliabilityStatus}</span>
              </div>
            </div>

            {selectedCitation.price && (
              <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-xl space-y-1">
                <span className="text-[11px] text-stone-600 block">Giá sàn ghi nhận:</span>
                <div className="text-lg font-bold text-amber-950 font-mono">
                  {selectedCitation.price}
                </div>
                {selectedCitation.officialPrice && (
                  <span className="text-[11px] text-stone-500 line-through block">
                    Giá niêm yết: {selectedCitation.officialPrice}
                  </span>
                )}
              </div>
            )}

            <div className="space-y-2">
              <span className="text-xs font-semibold text-stone-800 uppercase tracking-wider">
                Đoạn trích dẫn nguyên văn:
              </span>
              <div className="p-3.5 bg-[#fbf9f4] border border-stone-200 rounded-xl text-stone-800 italic leading-relaxed">
                "{selectedCitation.excerpt}"
              </div>
            </div>

            <div className="pt-3 border-t border-stone-200 space-y-2 text-[11px] text-stone-500">
              <div className="flex items-center justify-between">
                <span>Thời điểm kiểm tra:</span>
                <span className="font-mono text-stone-700">{selectedCitation.verifiedDate}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Hiệu lực giá:</span>
                <span className="text-emerald-700 font-medium">Đang áp dụng</span>
              </div>
            </div>

            <div className="pt-4">
              <button
                onClick={() => {
                  setSelectedCitation(null);
                  onOpenDossier();
                }}
                className="w-full py-2.5 bg-stone-900 text-amber-50 rounded-xl text-xs font-semibold hover:bg-stone-800 transition-colors flex items-center justify-center gap-1.5"
              >
                <span>Đưa căn cứ này vào Dự thảo so sánh</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </aside>
      )}
    </div>
  );
};
