import React, { useState } from 'react';
import { 
  ShieldCheck, 
  AlertTriangle, 
  CheckCircle2, 
  RotateCw, 
  FileText, 
  ExternalLink, 
  Download, 
  X, 
  Check, 
  Sliders, 
  Eye,
  Info,
  Sparkles
} from 'lucide-react';
import { AuditIssue } from '../types.ts';
import { SAMPLE_AUDIT_ISSUES } from '../services/geminiService.ts';

export const AuditReviewView: React.FC = () => {
  const [issues, setIssues] = useState<AuditIssue[]>(SAMPLE_AUDIT_ISSUES);
  const [selectedIssueId, setSelectedIssueId] = useState<string>(SAMPLE_AUDIT_ISSUES[0].id);
  const [isAuditing, setIsAuditing] = useState(false);
  const [auditProgressSteps, setAuditProgressSteps] = useState<string[]>([]);
  const [showPreviewModal, setShowPreviewModal] = useState(false);

  const activeIssue = issues.find(i => i.id === selectedIssueId) || issues[0];

  const handleRunAudit = () => {
    setIsAuditing(true);
    setAuditProgressSteps(['Đang thu thập thông số kỹ thuật & đánh giá gian hàng...']);

    setTimeout(() => {
      setAuditProgressSteps(prev => [...prev, 'Đang đối chiếu chính sách bảo hành TTBH AASP Việt Nam...']);
    }, 600);

    setTimeout(() => {
      setAuditProgressSteps(prev => [...prev, 'Phát hiện 18% lượt đánh giá cụt ngủn nghi vấn seeding...']);
    }, 1200);

    setTimeout(() => {
      setAuditProgressSteps(prev => [...prev, 'Tổng hợp checklist 3 điểm rủi ro cần làm rõ...']);
      setIsAuditing(false);
    }, 1800);
  };

  const handleUpdateStatus = (issueId: string, status: 'accepted' | 'kept' | 'edited') => {
    setIssues(prev => prev.map(issue => {
      if (issue.id === issueId) {
        return { ...issue, status };
      }
      return issue;
    }));
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden bg-[#faf9f5]">
      {/* Left Sidebar: Upload / Configuration & Progress checklist (matching video 04:05 - 04:15) */}
      <div className="w-80 shrink-0 h-full bg-white border-r border-stone-200 flex flex-col z-10 shadow-xs">
        <div className="p-4 border-b border-stone-200 bg-[#fcfbf9]">
          <h2 className="text-xs font-bold text-stone-900 uppercase tracking-wider flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-700" />
            Cấu hình Không gian Rà soát
          </h2>
        </div>

        <div className="p-4 flex-1 overflow-y-auto space-y-5 text-xs">
          {/* Target input */}
          <div className="space-y-1.5">
            <label className="font-semibold text-stone-800">1. Sản phẩm / Link cần rà soát</label>
            <div className="p-3 bg-stone-50 border border-stone-200 rounded-xl space-y-1">
              <span className="font-bold text-stone-900 block">
                Apple MacBook Air 13 M3
              </span>
              <span className="text-[11px] text-stone-500 block truncate">
                shopee.vn/apple-flagship-store-macbook-air-m3-16gb-512gb
              </span>
            </div>
          </div>

          {/* Verification sources */}
          <div className="space-y-2">
            <label className="font-semibold text-stone-800">2. Nguồn đối chiếu pháp lý & kỹ thuật</label>
            <div className="space-y-1.5">
              {[
                { label: 'Quy chuẩn bảo hành Apple Care / AASP', checked: true },
                { label: 'Chính sách hoàn tiền Shopee Mall 100%', checked: true },
                { label: 'Kho 842 đánh giá người dùng thực tế', checked: true },
                { label: 'Biểu đồ biến động giá 90 ngày', checked: true },
              ].map((src, idx) => (
                <label key={idx} className="flex items-center gap-2 p-2 rounded-lg hover:bg-stone-50 cursor-pointer">
                  <input 
                    type="checkbox" 
                    defaultChecked={src.checked}
                    className="text-stone-900 focus:ring-stone-900 rounded"
                  />
                  <span className="text-stone-700">{src.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Action button */}
          <button
            onClick={handleRunAudit}
            disabled={isAuditing}
            className="w-full py-2.5 bg-stone-900 text-amber-50 rounded-xl font-semibold hover:bg-stone-800 transition-colors flex items-center justify-center gap-2 shadow-xs disabled:bg-stone-300"
          >
            {isAuditing ? (
              <>
                <RotateCw className="w-3.5 h-3.5 animate-spin" />
                <span>Đang rà soát dữ liệu...</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Chạy rà soát lại bằng AI</span>
              </>
            )}
          </button>

          {/* Live Progress steps (matching video 04:10) */}
          {auditProgressSteps.length > 0 && (
            <div className="p-3 bg-stone-50 border border-stone-200 rounded-xl space-y-2">
              <div className="text-[11px] font-bold text-stone-700 uppercase tracking-wider flex items-center gap-1">
                <RotateCw className={`w-3 h-3 ${isAuditing ? 'animate-spin text-amber-600' : 'text-emerald-600'}`} />
                <span>Tiến trình rà soát:</span>
              </div>
              <div className="space-y-1.5">
                {auditProgressSteps.map((st, i) => (
                  <div key={i} className="flex items-start gap-1.5 text-[11px] text-stone-600">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                    <span>{st}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Center: Audit Metrics & Document with Highlights (matching video 04:19 - 04:29) */}
      <div className="flex-1 h-full overflow-y-auto p-6 flex flex-col gap-6">
        {/* Top Header of Center pane: 4 KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="p-3.5 bg-white rounded-xl border border-stone-200 shadow-xs">
            <span className="text-[11px] text-stone-500 font-medium block">Số tiêu chí rà soát</span>
            <span className="text-xl font-bold font-mono text-stone-900 mt-1 block">14 tiêu chí</span>
            <span className="text-[10px] text-emerald-700 font-medium">100% hoàn thành</span>
          </div>
          <div className="p-3.5 bg-white rounded-xl border border-stone-200 shadow-xs">
            <span className="text-[11px] text-stone-500 font-medium block">Điểm cần làm rõ</span>
            <span className="text-xl font-bold font-mono text-amber-700 mt-1 block">3 nội dung</span>
            <span className="text-[10px] text-amber-700 font-medium">Bảo hành & RAM</span>
          </div>
          <div className="p-3.5 bg-white rounded-xl border border-stone-200 shadow-xs">
            <span className="text-[11px] text-stone-500 font-medium block">Cảnh báo thông số</span>
            <span className="text-xl font-bold font-mono text-stone-900 mt-1 block">1 cảnh báo</span>
            <span className="text-[10px] text-stone-500 font-medium">Không thể nâng cấp</span>
          </div>
          <div className="p-3.5 bg-white rounded-xl border border-stone-200 shadow-xs">
            <span className="text-[11px] text-stone-500 font-medium block">Độ tin cậy gian hàng</span>
            <span className="text-xl font-bold font-mono text-emerald-800 mt-1 block">92 / 100</span>
            <span className="text-[10px] text-emerald-700 font-medium">Gian hàng chính hãng</span>
          </div>
        </div>

        {/* Toolbar: Preview Report Button */}
        <div className="flex items-center justify-between">
          <div className="text-xs text-stone-600">
            <span>Bấm vào từng đoạn văn bản được highlight màu xanh để xem chi tiết rà soát và đề xuất của AI.</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowPreviewModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-stone-300 rounded-lg text-xs font-semibold text-stone-800 hover:bg-stone-50 shadow-xs transition-colors"
            >
              <Eye className="w-3.5 h-3.5 text-stone-600" />
              <span>Preview báo cáo rà soát</span>
            </button>
          </div>
        </div>

        {/* Scanned Document Canvas with Highlighted Sections (matching video 04:25) */}
        <div className="bg-white rounded-xl border border-stone-200/90 shadow-sm p-8 max-w-3xl mx-auto w-full space-y-6 text-stone-900 font-serif leading-relaxed text-xs sm:text-sm">
          <div className="text-center pb-4 border-b border-stone-200 font-sans">
            <h3 className="font-bold uppercase tracking-wider text-sm sm:text-base text-stone-900">
              CHÍNH SÁCH BẢO HÀNH & THÔNG SỐ SẢN PHẨM MUA SẮM
            </h3>
            <p className="text-xs text-stone-500 mt-1">
              Phiên bản đối chiếu: 2.0 | Nguồn trích xuất: Shopee Mall & TTBH AASP Việt Nam
            </p>
          </div>

          {/* Section 1 */}
          <div className="space-y-2 font-sans">
            <h4 className="font-bold text-xs uppercase text-stone-800">1. MỤC ĐÍCH & PHẠM VI ÁP DỤNG</h4>
            <p className="text-stone-700 leading-relaxed">
              Áp dụng cho dòng sản phẩm Apple MacBook Air 13 M3 phân phối chính hãng mã SA/A. Đảm bảo quyền lợi khách hàng về bảo hành phần cứng và đổi mới sản phẩm nếu phát sinh lỗi kỹ thuật.
            </p>
          </div>

          {/* Section 2 (Highlighted interactive issue #2) */}
          <div className="space-y-2 font-sans">
            <h4 className="font-bold text-xs uppercase text-stone-800">2. THÔNG SỐ RAM & PHẦN CỨNG</h4>
            <div 
              onClick={() => setSelectedIssueId('issue-2')}
              className={`p-3 rounded-lg border cursor-pointer transition-all ${
                selectedIssueId === 'issue-2'
                  ? 'bg-sky-50 border-sky-400 text-sky-950 shadow-xs'
                  : 'bg-sky-50/50 border-sky-200 hover:bg-sky-100/60'
              }`}
            >
              <p className="font-medium">
                {issues[1].originalText}
              </p>
              <div className="mt-1 text-[11px] font-semibold text-sky-800 flex items-center gap-1">
                <Info className="w-3 h-3" />
                <span>Nhấp để xem cảnh báo AI về cấu hình RAM hàn chết</span>
              </div>
            </div>
          </div>

          {/* Section 3 */}
          <div className="space-y-2 font-sans">
            <h4 className="font-bold text-xs uppercase text-stone-800">3. PHƯƠNG THỨC GIAO NHẬN</h4>
            <p className="text-stone-700 leading-relaxed">
              Đồng kiểm ngoại quan lúc nhận hàng. Khách hàng được phép mở hộp kiểm tra móp méo bên ngoài trước khi ký nhận bưu tá.
            </p>
          </div>

          {/* Section 4 (Highlighted interactive issue #1) */}
          <div className="space-y-2 font-sans">
            <h4 className="font-bold text-xs uppercase text-stone-800">4. THỜI HẠN BẢO HÀNH & ĐỔI TRẢ</h4>
            <div 
              onClick={() => setSelectedIssueId('issue-1')}
              className={`p-3 rounded-lg border cursor-pointer transition-all ${
                selectedIssueId === 'issue-1'
                  ? 'bg-sky-50 border-sky-400 text-sky-950 shadow-xs'
                  : 'bg-sky-50/50 border-sky-200 hover:bg-sky-100/60'
              }`}
            >
              <p className="font-medium">
                {issues[0].originalText}
              </p>
              <div className="mt-1 text-[11px] font-semibold text-sky-800 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3 text-amber-700" />
                <span>Nhấp để xem phân tích kẽ hở điều kiện đổi trả</span>
              </div>
            </div>
          </div>

          {/* Section 6 (Highlighted interactive issue #3) */}
          <div className="space-y-2 font-sans">
            <h4 className="font-bold text-xs uppercase text-stone-800">5. TỔNG HỢP ĐÁNH GIÁ NGƯỜI DÙNG</h4>
            <div 
              onClick={() => setSelectedIssueId('issue-3')}
              className={`p-3 rounded-lg border cursor-pointer transition-all ${
                selectedIssueId === 'issue-3'
                  ? 'bg-sky-50 border-sky-400 text-sky-950 shadow-xs'
                  : 'bg-sky-50/50 border-sky-200 hover:bg-sky-100/60'
              }`}
            >
              <p className="font-medium">
                {issues[2].originalText}
              </p>
              <div className="mt-1 text-[11px] font-semibold text-sky-800 flex items-center gap-1">
                <Sparkles className="w-3 h-3 text-amber-700" />
                <span>Nhấp để xem kết quả phân tích lọc seeding đánh giá</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Sidebar: Active Issue Inspector Card (matching video 04:30 - 04:45) */}
      <div className="w-96 shrink-0 h-full bg-white border-l border-stone-200 flex flex-col z-10 shadow-xs">
        <div className="p-4 border-b border-stone-200 bg-[#fcfbf9] flex items-center justify-between">
          <span className="text-[11px] font-bold text-amber-800 uppercase tracking-wider">
            Chi tiết rà soát AI
          </span>
          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-900">
            {activeIssue.status === 'accepted' ? 'Đã chấp nhận' : 'Cần xử lý'}
          </span>
        </div>

        <div className="p-5 flex-1 overflow-y-auto space-y-4 text-xs leading-relaxed">
          {/* Issue Title */}
          <div>
            <h3 className="font-bold text-stone-900 text-sm leading-snug">
              {activeIssue.sectionTitle}
            </h3>
            <p className="text-[11px] text-stone-500 mt-1">
              Phát hiện bởi: Shopping AI Risk Auditor
            </p>
          </div>

          {/* AI Observation */}
          <div className="p-3 bg-stone-50 border border-stone-200 rounded-xl space-y-1">
            <span className="text-[11px] font-bold text-stone-700 block uppercase tracking-wider">
              Nhận xét AI:
            </span>
            <p className="text-stone-800 font-medium">
              {activeIssue.aiObservation}
            </p>
          </div>

          {/* Reason for evaluation */}
          <div className="space-y-1">
            <span className="text-[11px] font-bold text-stone-500 uppercase tracking-wider">
              Lý do đánh giá rủi ro:
            </span>
            <p className="text-stone-700">
              {activeIssue.evaluationReason}
            </p>
          </div>

          {/* Citation */}
          <div className="p-2.5 bg-amber-50/70 border border-amber-200 rounded-lg space-y-1">
            <span className="text-[10px] font-bold text-amber-800 uppercase tracking-wider block">
              Căn cứ đối chiếu:
            </span>
            <p className="text-[11px] text-stone-700 italic">
              {activeIssue.citationText}
            </p>
          </div>

          {/* AI Suggestion */}
          <div className="p-3 bg-emerald-50/80 border border-emerald-200 rounded-xl space-y-1">
            <span className="text-[11px] font-bold text-emerald-900 uppercase tracking-wider block flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-emerald-700" />
              Gợi ý xử lý tối ưu từ AI:
            </span>
            <p className="text-emerald-950 font-medium">
              {activeIssue.aiSuggestion}
            </p>
          </div>

          {/* Interactive Action Buttons (matching video 04:39 - 04:42) */}
          <div className="pt-2 space-y-2">
            <button
              onClick={() => handleUpdateStatus(activeIssue.id, 'accepted')}
              className={`w-full py-2.5 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors ${
                activeIssue.status === 'accepted'
                  ? 'bg-emerald-700 text-white'
                  : 'bg-stone-900 text-amber-50 hover:bg-stone-800'
              }`}
            >
              <Check className="w-4 h-4" />
              <span>{activeIssue.status === 'accepted' ? 'Đã chấp nhận gợi ý' : 'Chấp nhận gợi ý'}</span>
            </button>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => handleUpdateStatus(activeIssue.id, 'kept')}
                className="py-2 border border-stone-200 hover:bg-stone-100 rounded-lg text-stone-700 font-medium transition-colors"
              >
                Giữ nguyên
              </button>
              <button
                onClick={() => handleUpdateStatus(activeIssue.id, 'edited')}
                className="py-2 border border-stone-200 hover:bg-stone-100 rounded-lg text-stone-700 font-medium transition-colors"
              >
                Tự chỉnh sửa
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Preview Modal (matching video 04:49 - 04:54) */}
      {showPreviewModal && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl animate-scaleUp">
            <div className="p-5 border-b border-stone-200 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-stone-900">
                  Preview Báo cáo Rà soát Rủi ro & Thông số
                </h3>
                <p className="text-xs text-stone-500">
                  Tổng hợp các cảnh báo trước khi tiến hành thanh toán
                </p>
              </div>
              <button 
                onClick={() => setShowPreviewModal(false)}
                className="w-8 h-8 rounded-lg hover:bg-stone-100 flex items-center justify-center text-stone-500"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-6 flex-1 overflow-y-auto space-y-4 text-xs leading-relaxed">
              <div className="p-4 bg-stone-50 border border-stone-200 rounded-xl space-y-2">
                <span className="font-bold text-stone-900 block text-xs">Tóm tắt đánh giá:</span>
                <p className="text-stone-700">
                  Sản phẩm <strong>Apple MacBook Air 13 M3</strong> có chất lượng phần cứng vượt trội, bảo hành chính hãng đầy đủ. Tuy nhiên người mua cần lưu ý 2 điểm: (1) RAM hàn chết không thể nâng cấp, bắt buộc chọn bản 16GB; (2) Chính sách đổi trả 7 ngày cần xác nhận trực tiếp với gian hàng về điều kiện điểm chết màn hình.
                </p>
              </div>

              <div className="space-y-3">
                <span className="font-bold text-stone-900 block uppercase tracking-wider text-[11px]">
                  Danh sách hạng mục đã rà soát:
                </span>
                {issues.map((iss, i) => (
                  <div key={iss.id} className="p-3.5 border border-stone-200 rounded-xl space-y-1.5">
                    <div className="flex items-center justify-between font-semibold text-stone-900">
                      <span>{i + 1}. {iss.sectionTitle}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${iss.status === 'accepted' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-900'}`}>
                        {iss.status === 'accepted' ? 'Đã khắc phục' : 'Cần lưu ý'}
                      </span>
                    </div>
                    <p className="text-stone-600">{iss.aiObservation}</p>
                    <div className="text-[11px] text-emerald-800 font-medium">
                      → Gợi ý: {iss.aiSuggestion}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-4 border-t border-stone-200 flex items-center justify-end gap-2 bg-stone-50">
              <button
                onClick={() => setShowPreviewModal(false)}
                className="px-4 py-2 border border-stone-300 rounded-lg text-xs font-medium text-stone-700 hover:bg-white"
              >
                Đóng
              </button>
              <button
                onClick={() => {
                  setShowPreviewModal(false);
                  alert('Báo cáo rà soát đã được chuẩn bị xong để đính kèm vào hồ sơ quyết định!');
                }}
                className="px-4 py-2 bg-stone-900 text-amber-50 rounded-lg text-xs font-semibold hover:bg-stone-800"
              >
                Áp dụng vào Hồ sơ quyết định
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
