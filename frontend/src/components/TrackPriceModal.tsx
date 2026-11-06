import React, { useEffect, useState } from 'react';
import { BellRing, Loader2, X } from 'lucide-react';
import { PriceAlert, PricePoint, ProductItem } from '../types.ts';
import { getPriceHistory } from '../services/agentApi.ts';
import { PriceHistoryChart } from './PriceHistoryChart.tsx';
import { currentLocale, t } from '../i18n/index.tsx';

interface TrackPriceModalProps {
  product: ProductItem | null;
  existingAlert?: PriceAlert;
  onCreate: (product: ProductItem, targetPrice: number) => Promise<void>;
  onDelete: (alertId: string) => Promise<void>;
  onClose: () => void;
}

const DISCOUNT_PRESETS = [5, 10, 15, 20];
const formatVnd = (n: number) => `${Math.round(n).toLocaleString(currentLocale())} ₫`;
// Làm tròn xuống bội số 10.000 đ cho dễ đọc
const roundPrice = (n: number) => Math.floor(n / 10_000) * 10_000;

export const TrackPriceModal: React.FC<TrackPriceModalProps> = ({ product, existingAlert, onCreate, onDelete, onClose }) => {
  const [history, setHistory] = useState<PricePoint[] | null>(null);
  const [historyError, setHistoryError] = useState('');
  const [target, setTarget] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!product) return;
    setHistory(null);
    setHistoryError('');
    setError('');
    setTarget(String(existingAlert?.targetPrice ?? roundPrice(product.currentPrice * 0.9)));
    getPriceHistory(product.id).then(setHistory).catch(err => {
      setHistory([]);
      setHistoryError(err instanceof Error ? err.message : String(err));
    });
  }, [product?.id]);

  if (!product) return null;
  const targetValue = Number(target.replace(/\D/g, ''));
  const valid = targetValue > 0 && targetValue < product.currentPrice;

  const submit = async () => {
    if (!valid) return;
    setSaving(true);
    setError('');
    try {
      await onCreate(product, targetValue);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-xl w-full shadow-2xl animate-scaleUp overflow-hidden">
        <div className="p-5 border-b border-stone-200 flex items-center justify-between bg-panel">
          <div className="flex items-center gap-2 min-w-0">
            <BellRing className="w-4 h-4 text-stone-800 shrink-0" />
            <h3 className="text-sm font-bold text-stone-900 truncate">{t('Theo dõi giá')}</h3>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-stone-200 flex items-center justify-center text-stone-500">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-5 text-xs max-h-[75vh] overflow-y-auto">
          <div>
            <div className="text-sm font-semibold text-stone-900 line-clamp-2">{product.name}</div>
            <div className="text-stone-500 mt-0.5">
              {product.retailer} · {t('Giá hiện tại')} <strong className="text-stone-900">{formatVnd(product.currentPrice)}</strong>
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-[11px] font-semibold text-stone-600 uppercase tracking-wider">{t('Lịch sử giá')}</div>
            {history === null ? (
              <div className="flex items-center gap-2 text-stone-500"><Loader2 className="w-3.5 h-3.5 animate-spin" /> {t('Đang tải...')}</div>
            ) : historyError ? (
              <div className="text-stone-500">{t('Không tải được lịch sử giá ({error}).', { error: historyError })}</div>
            ) : (
              <PriceHistoryChart points={history} targetPrice={valid ? targetValue : undefined} />
            )}
          </div>

          {existingAlert ? (
            <div className="p-3 rounded-xl border border-amber-200 bg-amber-50 text-amber-900 flex items-center justify-between gap-3">
              <span>
                {existingAlert.status === 'triggered' ? t('Đã đạt giá mong muốn') : t('Đang theo dõi')}: {t('báo khi giá ≤')} <strong>{formatVnd(existingAlert.targetPrice)}</strong>
              </span>
              <button
                onClick={async () => { await onDelete(existingAlert.id); onClose(); }}
                className="shrink-0 text-[11px] font-semibold text-red-700 hover:text-red-900"
              >
                {t('Bỏ theo dõi')}
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-[11px] font-semibold text-stone-600 uppercase tracking-wider">{t('Báo cho tôi khi giá xuống')}</div>
              <div className="flex flex-wrap gap-2">
                {DISCOUNT_PRESETS.map(pct => {
                  const value = roundPrice(product.currentPrice * (1 - pct / 100));
                  return (
                    <button
                      key={pct}
                      onClick={() => setTarget(String(value))}
                      className={`px-3 py-1.5 rounded-full border transition-colors ${
                        targetValue === value ? 'bg-stone-900 text-amber-50 border-stone-900' : 'border-stone-200 text-stone-700 hover:border-stone-400'
                      }`}
                    >
                      −{pct}% · {formatVnd(value)}
                    </button>
                  );
                })}
              </div>
              <label className="flex items-center gap-2">
                <span className="text-stone-600 shrink-0">{t('Hoặc nhập giá:')}</span>
                <input
                  value={targetValue ? targetValue.toLocaleString(currentLocale()) : ''}
                  onChange={e => setTarget(e.target.value)}
                  inputMode="numeric"
                  className="flex-1 px-3 py-2 border border-stone-300 rounded-xl outline-none focus:border-stone-800 focus:ring-1 focus:ring-stone-800 font-mono text-stone-900"
                />
                <span className="text-stone-500">₫</span>
              </label>
              {!valid && target && <p className="text-red-700">{t('Giá mong muốn phải thấp hơn giá hiện tại.')}</p>}
              <p className="text-stone-500">
                {t('Hệ thống đọc giá trên trang sản phẩm định kỳ (mặc định mỗi 6 giờ) và đánh dấu khi giá xuống tới mức này.')}{' '}
                {t('Bạn cũng có thể bấm "Kiểm tra giá ngay" trong mục Theo dõi giá.')}
              </p>
              {error && <p className="text-red-700">{t('Không tạo được: {error}', { error })}</p>}
            </div>
          )}
        </div>

        {!existingAlert && (
          <div className="p-4 border-t border-stone-200 bg-stone-50 flex justify-end gap-2">
            <button onClick={onClose} className="px-4 py-2 text-xs font-medium text-stone-600 hover:text-stone-900">{t('Hủy')}</button>
            <button
              onClick={submit}
              disabled={!valid || saving}
              className="inline-flex items-center gap-1.5 px-4 py-2 bg-stone-900 text-amber-50 rounded-xl text-xs font-semibold hover:bg-stone-800 transition-colors disabled:bg-stone-300"
            >
              {saving && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {t('Theo dõi giá')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
