import React, { useState } from 'react';
import { X, Check, ShieldCheck, Sliders, Bell, Store } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [platforms, setPlatforms] = useState({
    shopeeMall: true,
    tikiTrading: true,
    lazadaFlagship: true,
    aaspOfficial: true,
  });

  const [riskFilters, setRiskFilters] = useState({
    hardwareUpgradability: true,
    fakeReviewSeeding: true,
    warrantyConditions: true,
    priceTrendAlert: true
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl animate-scaleUp overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-stone-200 flex items-center justify-between bg-[#fbfaf6]">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-stone-800" />
            <h3 className="text-sm font-bold text-stone-900">
              Cài đặt Tiêu chí & Nguồn Dữ liệu Mua sắm
            </h3>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-stone-200 flex items-center justify-center text-stone-500"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-6 text-xs leading-relaxed max-h-[70vh] overflow-y-auto">
          {/* Section 1: Platforms */}
          <div className="space-y-3">
            <span className="font-bold text-stone-900 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <Store className="w-3.5 h-3.5 text-stone-700" />
              Nguồn sàn TMĐT được phép trích xuất:
            </span>
            <div className="space-y-2">
              {[
                { key: 'shopeeMall', label: 'Shopee Mall (Gian hàng chính hãng có tem đỏ)' },
                { key: 'tikiTrading', label: 'Tiki Trading / Tiki Official phân phối trực tiếp' },
                { key: 'lazadaFlagship', label: 'Lazada Flagship Store (LazMall)' },
                { key: 'aaspOfficial', label: 'Đại lý ủy quyền Apple AASP (CellphoneS, TopZone, FPT)' },
              ].map((item) => (
                <label key={item.key} className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-stone-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={platforms[item.key as keyof typeof platforms]}
                    onChange={(e) => setPlatforms({ ...platforms, [item.key]: e.target.checked })}
                    className="rounded text-stone-900 focus:ring-stone-900"
                  />
                  <span className="text-stone-800">{item.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Section 2: Risk Filters */}
          <div className="space-y-3 pt-3 border-t border-stone-200">
            <span className="font-bold text-stone-900 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
              Bộ lọc cảnh báo rủi ro tự động:
            </span>
            <div className="space-y-2">
              {[
                { key: 'hardwareUpgradability', label: 'Cảnh báo linh kiện hàn chết (RAM, SSD onboard không thể nâng cấp)' },
                { key: 'fakeReviewSeeding', label: 'Tự động phát hiện và loại trừ đánh giá seeding gian lận' },
                { key: 'warrantyConditions', label: 'Kiểm tra ngoại lệ bảo hành điểm chết màn hình và seal hộp' },
                { key: 'priceTrendAlert', label: 'Cảnh báo khi giá đang cao hơn mức đáy lịch sử 90 ngày' },
              ].map((item) => (
                <label key={item.key} className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-stone-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={riskFilters[item.key as keyof typeof riskFilters]}
                    onChange={(e) => setRiskFilters({ ...riskFilters, [item.key]: e.target.checked })}
                    className="rounded text-stone-900 focus:ring-stone-900"
                  />
                  <span className="text-stone-800">{item.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-stone-200 bg-stone-50 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-stone-900 text-amber-50 rounded-xl text-xs font-semibold hover:bg-stone-800 transition-colors"
          >
            Lưu cài đặt
          </button>
        </div>
      </div>
    </div>
  );
};
