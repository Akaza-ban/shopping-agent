import React, { useState } from 'react';
import { 
  FileText, 
  Send, 
  Sparkles, 
  Check, 
  Copy, 
  Download, 
  RotateCw, 
  ShieldAlert, 
  SlidersHorizontal,
  ChevronRight,
  Plus,
  Trash2,
  Edit3,
  Calendar,
  Layers
} from 'lucide-react';
import { ShoppingDossier, ProductItem } from '../types.ts';
import { INITIAL_DOSSIER, SAMPLE_PRODUCTS } from '../services/geminiService.ts';

interface DossierCompareViewProps {
  onOpenAudit: () => void;
}

export const DossierCompareView: React.FC<DossierCompareViewProps> = ({
  onOpenAudit,
}) => {
  const [dossier, setDossier] = useState<ShoppingDossier>(INITIAL_DOSSIER);
  const [selectedProduct, setSelectedProduct] = useState<ProductItem>(SAMPLE_PRODUCTS[0]);
  const [activeTab, setActiveTab] = useState<'editor' | 'spec_matrix'>('editor');
  
  // Left sidebar chat for modifying document
  const [chatInput, setChatInput] = useState('');
  const [isModifying, setIsModifying] = useState(false);
  const [chatHistory, setChatHistory] = useState<{ sender: 'user' | 'assistant'; text: string }[]>([
    {
      sender: 'assistant',
      text: 'Dự thảo quyết định mua sắm đã được tạo lập tự động từ kết quả tra cứu. Bạn có thể yêu cầu tôi sửa đổi bất kỳ điều khoản nào (ví dụ: "Đổi ngân sách thành 25 triệu", "Thêm ASUS Zenbook làm lựa chọn số 1").'
    }
  ]);

  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportDocx = () => {
    // Generate clean text file or simulate DOCX export
    const element = document.createElement("a");
    const file = new Blob([
      `${dossier.title}\nSố: ${dossier.dossierCode}\nNgày: ${dossier.effectiveDate}\n\n` +
      dossier.sections.map(s => `${s.articleNumber}. ${s.title}\n${s.content}\n`).join('\n')
    ], { type: 'text/plain;charset=utf-8' });
    element.href = URL.createObjectURL(file);
    element.download = `Ho_So_Mua_Sam_${dossier.dossierCode.replace(/\//g, '_')}.txt`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const handleModifyDoc = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isModifying) return;

    const userText = chatInput;
    setChatInput('');
    setChatHistory(prev => [...prev, { sender: 'user', text: userText }]);
    setIsModifying(true);

    setTimeout(() => {
      // Simulate intelligent text amendment (like in video 03:30)
      if (userText.toLowerCase().includes('asus') || userText.toLowerCase().includes('zenbook')) {
        setSelectedProduct(SAMPLE_PRODUCTS[1]);
        setDossier(prev => ({
          ...prev,
          sections: prev.sections.map(sec => {
            if (sec.articleNumber === 'Điều 1') {
              return {
                ...sec,
                title: 'Lựa chọn đề xuất hàng đầu (Hạng Nhất - Đã sửa đổi)',
                content: 'Chấp thuận đề xuất mua sắm sản phẩm **ASUS Zenbook 14 OLED UX3405 (Intel Core Ultra 7 / 32GB RAM / 1TB SSD)** với mức giá ưu đãi hiện tại là **26.990.000 đồng** (tiết kiệm 5.000.000 đồng so với giá niêm yết 31.990.000 đồng), bảo hành 24 tháng chính hãng ASUS Việt Nam.',
                highlighted: true,
                highlightNote: 'Đã cập nhật theo yêu cầu chuyển đổi sang phương án ASUS Zenbook 14 OLED có 32GB RAM.'
              };
            }
            return sec;
          })
        }));
        setChatHistory(prev => [
          ...prev, 
          { 
            sender: 'assistant', 
            text: 'Tôi đã cập nhật Điều 1 sang ASUS Zenbook 14 OLED UX3405 (32GB RAM / 1TB SSD) với giá 26.990.000 đồng và đánh dấu màu vàng đoạn vừa sửa đổi trên hồ sơ!' 
          }
        ]);
      } else {
        setDossier(prev => ({
          ...prev,
          sections: prev.sections.map(sec => {
            if (sec.articleNumber === 'Điều 1') {
              return {
                ...sec,
                content: `${sec.content} [Yêu cầu bổ sung: ${userText}]`,
                highlighted: true,
                highlightNote: `Đã áp dụng: ${userText}`
              };
            }
            return sec;
          })
        }));
        setChatHistory(prev => [
          ...prev, 
          { 
            sender: 'assistant', 
            text: `Tôi đã cập nhật nội dung "${userText}" vào văn bản và đánh dấu vị trí sửa đổi.` 
          }
        ]);
      }
      setIsModifying(false);
    }, 900);
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden bg-[#f4f2ec]">
      {/* Left Control & Amendment Pane (matching video 01:08 - 01:40) */}
      <div className="w-[380px] lg:w-[420px] shrink-0 h-full bg-white border-r border-stone-200 flex flex-col z-10 shadow-sm">
        {/* Header */}
        <div className="p-4 border-b border-stone-200 flex items-center justify-between bg-[#fbfaf6]">
          <div className="flex items-center gap-2">
            <SlidersHorizontal className="w-4 h-4 text-stone-700" />
            <h2 className="text-xs font-bold text-stone-900 uppercase tracking-wider">
              Thiết lập & Tương tác Dự thảo
            </h2>
          </div>
          <button
            onClick={onOpenAudit}
            className="text-[11px] font-medium text-amber-900 hover:text-amber-950 flex items-center gap-1"
          >
            <span>Rà soát rủi ro</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Content Tabs */}
        <div className="p-2 border-b border-stone-200 bg-stone-50 flex gap-1">
          <button
            onClick={() => setActiveTab('editor')}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              activeTab === 'editor'
                ? 'bg-white text-stone-900 shadow-sm'
                : 'text-stone-500 hover:text-stone-800'
            }`}
          >
            Trợ lý chỉnh sửa
          </button>
          <button
            onClick={() => setActiveTab('spec_matrix')}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-colors ${
              activeTab === 'spec_matrix'
                ? 'bg-white text-stone-900 shadow-sm'
                : 'text-stone-500 hover:text-stone-800'
            }`}
          >
            Ma trận thông số (3 máy)
          </button>
        </div>

        {/* Tab 1: Interactive Chat Modification Pane */}
        {activeTab === 'editor' ? (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Form Fields summary */}
            <div className="p-4 border-b border-stone-100 bg-[#faf9f5] space-y-2 text-xs">
              <div className="flex justify-between text-stone-500">
                <span>Mã hồ sơ:</span>
                <span className="font-mono font-bold text-stone-800">{dossier.dossierCode}</span>
              </div>
              <div className="flex justify-between text-stone-500">
                <span>Ngân sách dự toán:</span>
                <span className="font-mono font-bold text-stone-900">
                  {dossier.totalBudget.toLocaleString()} ₫
                </span>
              </div>
              <div className="flex justify-between text-stone-500">
                <span>Mức tiết kiệm ước tính:</span>
                <span className="font-mono font-bold text-emerald-700">
                  {dossier.estimatedSavings.toLocaleString()} ₫
                </span>
              </div>
            </div>

            {/* Chat conversation list */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {chatHistory.map((item, idx) => (
                <div 
                  key={idx}
                  className={`flex flex-col ${item.sender === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div 
                    className={`max-w-[85%] text-xs p-3 rounded-xl leading-relaxed shadow-xs ${
                      item.sender === 'user'
                        ? 'bg-stone-900 text-amber-50 rounded-tr-none'
                        : 'bg-[#fcfbf9] text-stone-800 border border-stone-200 rounded-tl-none'
                    }`}
                  >
                    {item.text}
                  </div>
                </div>
              ))}
              {isModifying && (
                <div className="flex items-center gap-2 text-xs text-amber-900 p-2 bg-amber-50 rounded-lg animate-pulse">
                  <RotateCw className="w-3.5 h-3.5 animate-spin text-amber-700" />
                  <span>Đang rà soát và cập nhật văn bản...</span>
                </div>
              )}
            </div>

            {/* Chat Input form */}
            <form 
              onSubmit={handleModifyDoc}
              className="p-3 border-t border-stone-200 bg-white"
            >
              <div className="flex items-center gap-2 bg-[#f8f7f4] border border-stone-300 rounded-xl p-1 focus-within:border-stone-800">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="VD: Đổi sang ASUS Zenbook 14 OLED, thêm bảo hành..."
                  className="flex-1 px-3 py-1.5 text-xs bg-transparent border-none outline-none text-stone-900 placeholder:text-stone-400"
                  disabled={isModifying}
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim() || isModifying}
                  className="w-8 h-8 rounded-lg bg-stone-900 text-amber-50 flex items-center justify-center hover:bg-stone-800 transition-colors disabled:bg-stone-200 disabled:text-stone-400"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </div>
            </form>
          </div>
        ) : (
          /* Tab 2: Spec Comparison Matrix */
          <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
            <h4 className="font-semibold text-stone-900 uppercase tracking-wider text-[11px]">
              Đối chiếu trực tiếp 3 cấu hình
            </h4>
            {SAMPLE_PRODUCTS.map((prod) => (
              <div 
                key={prod.id}
                onClick={() => setSelectedProduct(prod)}
                className={`p-3.5 rounded-xl border cursor-pointer transition-all ${
                  selectedProduct.id === prod.id
                    ? 'bg-amber-50/60 border-stone-800 shadow-sm'
                    : 'bg-white border-stone-200 hover:border-stone-300'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-stone-900">{prod.brand}</span>
                  <span className="font-mono font-bold text-stone-900">
                    {prod.currentPrice.toLocaleString()} ₫
                  </span>
                </div>
                <div className="font-medium text-stone-700 mt-1 line-clamp-1">
                  {prod.name}
                </div>
                <div className="mt-2 pt-2 border-t border-stone-100 grid grid-cols-2 gap-1 text-[11px] text-stone-500">
                  <div>RAM: {prod.keySpecs['RAM']?.slice(0, 15)}</div>
                  <div>Trọng lượng: {prod.keySpecs['Trọng lượng']}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Right Canvas: Live procurement dossier document (matching video 02:26 - 03:50) */}
      <div className="flex-1 h-full overflow-y-auto p-6 lg:p-10 flex flex-col items-center">
        {/* Document Action Toolbar */}
        <div className="w-full max-w-3xl mb-4 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-stone-600">
            <span className="font-medium">Nguồn mẫu:</span>
            <span className="underline decoration-stone-400">Quy chuẩn Mua sắm Doanh nghiệp & Cá nhân 2026</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-stone-200 rounded-lg text-stone-700 hover:bg-stone-50 transition-colors shadow-xs"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Đã chép' : 'Sao chép'}</span>
            </button>

            <button
              onClick={handleExportDocx}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-stone-900 text-amber-50 rounded-lg font-medium hover:bg-stone-800 transition-colors shadow-xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Xuất DOCX</span>
            </button>
          </div>
        </div>

        {/* The Formal Document Paper (Matching video exact layout) */}
        <div className="w-full max-w-3xl bg-white shadow-xl border border-stone-200/90 rounded-sm p-10 sm:p-14 space-y-8 text-stone-900 font-serif leading-relaxed">
          {/* Header of official document */}
          <div className="flex flex-col sm:flex-row justify-between items-start gap-4 pb-4 border-b border-stone-200 font-sans text-xs">
            <div>
              <div className="font-bold uppercase tracking-wider text-stone-800">
                {dossier.organization}
              </div>
              <div className="text-stone-500 mt-0.5">
                Số: {dossier.dossierCode}
              </div>
            </div>

            <div className="text-right sm:text-right">
              <div className="font-bold uppercase tracking-wider text-stone-900">
                CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
              </div>
              <div className="text-stone-700 font-medium">
                Độc lập - Tự do - Hạnh phúc
              </div>
              <div className="text-[11px] text-stone-400 mt-1 italic">
                Hà Nội, ngày {dossier.effectiveDate}
              </div>
            </div>
          </div>

          {/* Title of Document */}
          <div className="text-center space-y-2 py-4">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-stone-900 uppercase">
              QUYẾT ĐỊNH
            </h1>
            <p className="text-sm font-semibold text-stone-700 italic">
              Về việc lựa chọn cấu hình thiết bị tối ưu theo ngân sách và nhu cầu công việc
            </p>
          </div>

          {/* Basis clauses (Căn cứ...) */}
          <div className="space-y-2 text-xs sm:text-sm text-stone-700 italic border-l-2 border-stone-300 pl-4 py-1 font-sans">
            <p>Căn cứ nhu cầu sử dụng thực tế: Thiết bị mỏng nhẹ dưới 1.3kg, RAM tối thiểu 16GB, màn hình chuẩn màu DCI-P3;</p>
            <p>Căn cứ biểu đồ biến động giá sàn TMĐT 90 ngày qua từ Shopee Mall, Tiki Official và các trung tâm AASP;</p>
            <p>Căn cứ kết quả lọc đánh giá người dùng thực tế và loại trừ rủi ro seeding.</p>
          </div>

          {/* Decision Articles (Điều 1, Điều 2...) */}
          <div className="space-y-6 pt-4 text-xs sm:text-sm font-sans">
            <div className="text-center font-bold text-sm uppercase tracking-wider text-stone-800">
              QUYẾT ĐỊNH:
            </div>

            {dossier.sections.map((section) => (
              <div key={section.id} className="space-y-1.5">
                <div className="font-bold text-stone-900">
                  {section.articleNumber}. {section.title}:
                </div>
                <div 
                  className={`p-3 rounded-lg leading-relaxed ${
                    section.highlighted
                      ? 'bg-amber-100/70 border border-amber-300 text-amber-950 font-normal transition-all'
                      : 'text-stone-800'
                  }`}
                >
                  <p className="whitespace-pre-line">{section.content}</p>
                  {section.highlightNote && (
                    <span className="block mt-1 text-[11px] font-semibold text-amber-800 italic">
                      * Chú thích AI: {section.highlightNote}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Signer block (like video: "HIỆU TRƯỞNG / CHUYÊN VIÊN") */}
          <div className="pt-10 flex justify-between items-end font-sans text-xs">
            <div className="text-[11px] text-stone-500">
              <span className="font-bold block text-stone-700">Nơi nhận:</span>
              <span>- Người mua / Người duyệt ngân sách;</span><br />
              <span>- Lưu: Hồ sơ theo dõi giá.</span>
            </div>

            <div className="text-center">
              <span className="font-bold text-stone-900 block uppercase">
                {dossier.signerTitle}
              </span>
              <span className="text-[11px] text-stone-400 italic block mb-12">
                (Ký, đóng dấu điện tử)
              </span>
              <span className="font-semibold text-stone-800">
                Shopping AI Assistant Agent
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
