import React, { useEffect, useState } from 'react';
import { AlertCircle, ArrowRight, ShieldCheck, X } from 'lucide-react';
import { PolicyLookupResult, PolicyRequest, PolicyScenario, ProductItem } from '../../types.ts';
import { getPlatformName } from '../../services/shoppingService.ts';
import { lookupPolicies } from '../../services/agentApi.ts';
import { t } from '../../i18n/index.tsx';
import { SCENARIOS } from './scenarios.ts';
import { PolicyAnswer } from './PolicyAnswer.tsx';

interface PolicyDrawerProps {
  product: ProductItem;
  onClose: () => void;
  onOpenFull: (request: PolicyRequest) => void;
}

// Ngăn trượt trong khung chat: chính sách của đúng nơi bán sản phẩm, không phải chuyển sang tab khác
export const PolicyDrawer: React.FC<PolicyDrawerProps> = ({ product, onClose, onOpenFull }) => {
  const [scenario, setScenario] = useState<PolicyScenario | null>(null);
  // Kết quả gắn với đúng yêu cầu đã gửi: đổi sản phẩm / tình huống -> đang tải cho tới khi có kết quả mới
  const requestKey = [product.platformId, product.name, scenario ?? ''].join('|');
  const [settled, setSettled] = useState<{ key: string; result: PolicyLookupResult | null; error: string | null } | null>(null);
  const isLoading = settled?.key !== requestKey;
  const result = isLoading ? null : settled.result;
  const error = isLoading ? null : settled.error;

  useEffect(() => {
    let cancelled = false;
    lookupPolicies(product.name, [product.platformId], 'all', [product.platformId], scenario)
      .then(r => { if (!cancelled) setSettled({ key: requestKey, result: r, error: null }); })
      .catch(err => {
        if (cancelled) return;
        const message = err instanceof Error ? err.message : t('Không tra cứu được chính sách, vui lòng thử lại.');
        setSettled({ key: requestKey, result: null, error: message });
      });
    return () => { cancelled = true; };
  }, [product.name, product.platformId, scenario, requestKey]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex justify-end" onClick={onClose}>
      <aside
        className="w-full max-w-lg h-full bg-canvas shadow-2xl overflow-y-auto animate-fadeIn"
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-label={t('Chính sách nơi bán')}
      >
        <div className="sticky top-0 z-10 bg-canvas/95 backdrop-blur border-b border-stone-200 p-4 flex items-start gap-3">
          <ShieldCheck className="w-5 h-5 text-emerald-700 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="text-sm font-bold text-stone-900">{t('Chính sách tại {platform}', { platform: getPlatformName(product.platformId) })}</div>
            <div className="text-[11px] text-stone-500 line-clamp-1">{product.name}</div>
          </div>
          <button onClick={onClose} className="p-1 rounded-md text-stone-500 hover:text-stone-900 hover:bg-stone-100" aria-label={t('Đóng')}>
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          <div className="flex flex-wrap gap-1.5">
            {SCENARIOS.map(s => (
              <button
                key={s.id}
                type="button"
                disabled={isLoading}
                onClick={() => setScenario(scenario === s.id ? null : s.id)}
                className={`px-3 py-1 text-[11px] font-semibold rounded-full border transition-colors ${
                  scenario === s.id ? 'bg-emerald-700 text-white border-emerald-700' : 'bg-white text-stone-700 border-stone-300 hover:border-stone-500'
                }`}
              >
                {t(s.label)}
              </button>
            ))}
          </div>

          {isLoading && (
            <div className="p-4 bg-white rounded-xl border border-stone-200 flex items-center gap-2.5 text-xs text-stone-700">
              <div className="w-4 h-4 rounded-full border-2 border-amber-600 border-t-transparent animate-spin shrink-0" />
              {t('Đang tra cứu chính sách...')}
            </div>
          )}

          {error && !isLoading && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-900 flex gap-2">
              <AlertCircle className="w-4 h-4 text-red-700 shrink-0 mt-0.5" />
              <p>{error}</p>
            </div>
          )}

          {result && !isLoading && !error && (
            result.policies.length > 0 ? (
              <PolicyAnswer
                summary={result.summary}
                sourceIds={result.sourceIds ?? []}
                excerpts={result.excerpts}
                policies={result.policies}
                scenario={scenario}
              />
            ) : (
              <div className="p-4 bg-white rounded-xl border border-stone-200 text-xs text-stone-600">
                {t('Chưa có dữ liệu chính sách của nơi bán này.')}
              </div>
            )
          )}

          <button
            type="button"
            onClick={() => onOpenFull({ query: product.name, productPlatformIds: [product.platformId] })}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-stone-700 hover:text-stone-950"
          >
            {t('Mở trang tra cứu đầy đủ')} <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </aside>
    </div>
  );
};
