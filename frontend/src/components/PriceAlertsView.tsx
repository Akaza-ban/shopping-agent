import React, { useState } from 'react';
import { BellRing, CheckCircle2, ExternalLink, ImageOff, LineChart, Loader2, RefreshCw, Trash2, Eye, AlertTriangle, PackageX, Hourglass, ListChecks } from 'lucide-react';
import { PriceAlert, PriceCheck, PricePoint } from '../types.ts';
import { getAlertChecks, getPriceHistory, parseServerDate } from '../services/agentApi.ts';
import { currentLocale, formatVnd, msg, t } from '../i18n/index.tsx';
import { PriceHistoryChart } from './PriceHistoryChart.tsx';

interface PriceAlertsViewProps {
  alerts: PriceAlert[];
  loadError: string;
  checkingIds: string[] | 'all' | null; // đang kiểm tra giá
  onCheck: (ids?: string[]) => void;
  onDelete: (id: string) => void;
  onGoSearch: () => void;
}

const formatOptionalVnd = (n: number | null | undefined) => (n ? formatVnd(n) : '—');
const formatWhen = (iso: string | null) =>
  iso ? parseServerDate(iso).toLocaleString(currentLocale(), { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' }) : t('chưa kiểm tra');

const StatusBadge: React.FC<{ status: PriceAlert['status'] }> = ({ status }) =>
  status === 'triggered' ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
      <CheckCircle2 className="w-3.5 h-3.5" /> {t('Đã đạt giá mong muốn')}
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-stone-100 text-stone-700 border border-stone-200">
      <Eye className="w-3.5 h-3.5" /> {t('Đang theo dõi')}
    </span>
  );

const CHECK_OUTCOME: Record<PriceCheck['outcome'], { label: string; className: string }> = {
  accepted: { label: msg('Ghi nhận giá'), className: 'text-stone-700' },
  triggered: { label: msg('Đạt giá'), className: 'text-emerald-800' },
  pending: { label: msg('Chờ xác nhận'), className: 'text-amber-800' },
  rejected: { label: msg('Bỏ qua giá'), className: 'text-red-700' },
  out_of_stock: { label: msg('Hết hàng'), className: 'text-red-700' },
  unreadable: { label: msg('Không đọc được'), className: 'text-stone-500' },
};

// Nhãn phụ theo kết quả guardrails của lần đọc gần nhất
const ConditionBadges: React.FC<{ alert: PriceAlert }> = ({ alert }) => (
  <>
    {alert.inStock === false && (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-red-50 text-red-800 border border-red-200">
        <PackageX className="w-3.5 h-3.5" /> {t('Hết hàng')}
      </span>
    )}
    {alert.status === 'watching' && alert.pendingPrice != null && (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-900 border border-amber-200"
        title={t('Giá đọc được biến động bất thường; hệ thống chờ lần đọc sau khớp mới ghi nhận')}>
        <Hourglass className="w-3.5 h-3.5" /> {t('Chờ xác nhận giá {price}', { price: formatOptionalVnd(alert.pendingPrice) })}
      </span>
    )}
  </>
);

const CheckLog: React.FC<{ checks: PriceCheck[] | null }> = ({ checks }) => {
  if (checks === null) {
    return <div className="flex items-center gap-2 text-[11px] text-stone-500"><Loader2 className="w-3.5 h-3.5 animate-spin" /> {t('Đang tải nhật ký...')}</div>;
  }
  if (checks.length === 0) return <p className="text-[11px] text-stone-500">{t('Chưa có lần kiểm tra nào.')}</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px]">
        <thead>
          <tr className="text-left text-stone-500 border-b border-stone-100">
            <th className="py-1 pr-3 font-medium">{t('Thời điểm')}</th>
            <th className="py-1 pr-3 font-medium">{t('Kết quả')}</th>
            <th className="py-1 pr-3 font-medium">{t('Giá đọc được')}</th>
            <th className="py-1 font-medium">{t('Ghi chú')}</th>
          </tr>
        </thead>
        <tbody>
          {checks.map(c => (
            <tr key={c.id} className="border-b border-stone-50 align-top">
              <td className="py-1 pr-3 font-mono whitespace-nowrap text-stone-600">{formatWhen(c.checkedAt)}</td>
              <td className={`py-1 pr-3 font-semibold whitespace-nowrap ${CHECK_OUTCOME[c.outcome]?.className ?? ''}`}>
                {CHECK_OUTCOME[c.outcome] ? t(CHECK_OUTCOME[c.outcome].label) : c.outcome}
              </td>
              <td className="py-1 pr-3 font-mono whitespace-nowrap">{formatOptionalVnd(c.price)}</td>
              <td className="py-1 text-stone-600">{c.note || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const AlertRow: React.FC<{
  alert: PriceAlert;
  checking: boolean;
  onCheck: () => void;
  onDelete: () => void;
}> = ({ alert, checking, onCheck, onDelete }) => {
  const [history, setHistory] = useState<PricePoint[] | null>(null);
  const [open, setOpen] = useState(false);
  const [checks, setChecks] = useState<PriceCheck[] | null>(null);
  const [logOpen, setLogOpen] = useState(false);
  const gap = alert.lastPrice - alert.targetPrice;

  const toggleHistory = async () => {
    const next = !open;
    setOpen(next);
    if (next) setHistory(await getPriceHistory(alert.productId).catch(() => []));
  };

  const toggleLog = async () => {
    const next = !logOpen;
    setLogOpen(next);
    if (next) {
      setChecks(null);
      setChecks(await getAlertChecks(alert.id).catch(() => []));
    }
  };

  return (
    <div className={`bg-white border rounded-2xl p-4 space-y-3 ${alert.status === 'triggered' ? 'border-emerald-200' : 'border-stone-200'}`}>
      <div className="flex gap-3">
        {alert.image ? (
          <img src={alert.image} alt={alert.productName} className="w-16 h-16 rounded-lg object-contain bg-white shrink-0" />
        ) : (
          <div className="w-16 h-16 rounded-lg bg-stone-100 flex items-center justify-center text-stone-400 shrink-0"><ImageOff className="w-5 h-5" /></div>
        )}
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-start justify-between gap-2">
            <a href={alert.productUrl} target="_blank" rel="noreferrer" className="text-sm font-semibold text-stone-900 hover:underline line-clamp-2">
              {alert.productName}
            </a>
            <div className="flex flex-wrap justify-end gap-1">
              <StatusBadge status={alert.status} />
              <ConditionBadges alert={alert} />
            </div>
          </div>
          <div className="text-[11px] text-stone-500">{alert.platformName || alert.platform} · {t('Kiểm tra lần cuối: {when}', { when: formatWhen(alert.lastCheckedAt) })}</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px]">
            <div><div className="text-stone-500">{t('Giá mong muốn')}</div><div className="font-mono font-bold text-stone-900">{formatOptionalVnd(alert.targetPrice)}</div></div>
            <div><div className="text-stone-500">{t('Giá gần nhất')}</div><div className="font-mono font-bold text-stone-900">{formatOptionalVnd(alert.lastPrice)}</div></div>
            <div><div className="text-stone-500">{t('Thấp nhất đã thấy')}</div><div className="font-mono text-stone-800">{formatOptionalVnd(alert.lowestPrice)}</div></div>
            <div><div className="text-stone-500">{t('Lúc bắt đầu')}</div><div className="font-mono text-stone-800">{formatOptionalVnd(alert.initialPrice)}</div></div>
          </div>
          {alert.status === 'watching' && gap > 0 && (
            <div className="text-[11px] text-stone-600">{t('Còn cách mức mong muốn')} <strong className="text-stone-900">{formatOptionalVnd(gap)}</strong></div>
          )}
          {alert.lastNote && (
            <div className={`text-[11px] flex items-start gap-1 ${alert.status === 'triggered' ? 'text-emerald-800' : 'text-stone-600'}`}>
              {alert.status !== 'triggered' && <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-px" />}
              {alert.lastNote}
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-stone-100 text-[11px] font-semibold">
        <button onClick={toggleHistory} className="inline-flex items-center gap-1 text-stone-700 hover:text-stone-950">
          <LineChart className="w-3.5 h-3.5" /> {open ? t('Ẩn lịch sử giá') : t('Lịch sử giá')}
        </button>
        <button onClick={toggleLog} className="inline-flex items-center gap-1 text-stone-700 hover:text-stone-950">
          <ListChecks className="w-3.5 h-3.5" /> {logOpen ? t('Ẩn nhật ký kiểm tra') : t('Nhật ký kiểm tra')}
        </button>
        {alert.status === 'watching' && (
          <button onClick={onCheck} disabled={checking} className="inline-flex items-center gap-1 text-stone-700 hover:text-stone-950 disabled:text-stone-400">
            {checking ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />} {t('Kiểm tra giá ngay')}
          </button>
        )}
        <a href={alert.productUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-stone-700 hover:text-stone-950">
          {t('Xem tại sàn')} <ExternalLink className="w-3 h-3" />
        </a>
        <button onClick={onDelete} className="ml-auto inline-flex items-center gap-1 text-stone-500 hover:text-red-700">
          <Trash2 className="w-3.5 h-3.5" /> {t('Bỏ theo dõi')}
        </button>
      </div>

      {open && (
        history === null
          ? <div className="flex items-center gap-2 text-[11px] text-stone-500"><Loader2 className="w-3.5 h-3.5 animate-spin" /> {t('Đang tải lịch sử giá...')}</div>
          : <PriceHistoryChart points={history} targetPrice={alert.targetPrice} />
      )}
      {logOpen && <CheckLog checks={checks} />}
    </div>
  );
};

export const PriceAlertsView: React.FC<PriceAlertsViewProps> = ({ alerts, loadError, checkingIds, onCheck, onDelete, onGoSearch }) => {
  const watching = alerts.filter(a => a.status === 'watching').length;
  const triggered = alerts.length - watching;

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-stone-900">{t('Theo dõi giá')}</h1>
          <p className="text-xs text-stone-600 mt-1">
            {alerts.length
              ? t('{watching} sản phẩm đang theo dõi · {triggered} sản phẩm đã đạt giá mong muốn', { watching, triggered })
              : t('Nhận thông báo khi sản phẩm bạn quan tâm giảm xuống mức giá mong muốn.')}
          </p>
        </div>
        {watching > 0 && (
          <button
            onClick={() => onCheck()}
            disabled={checkingIds !== null}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-stone-900 text-amber-50 rounded-xl text-xs font-semibold hover:bg-stone-800 disabled:bg-stone-300"
          >
            {checkingIds === 'all' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
            {t('Kiểm tra tất cả ngay')}
          </button>
        )}
      </div>

      {loadError && (
        <div className="p-3 rounded-xl border border-red-200 bg-red-50 text-xs text-red-800 flex items-start gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" /> {t('Không tải được danh sách theo dõi giá: {error}', { error: loadError })}
        </div>
      )}

      {alerts.length === 0 && !loadError ? (
        <div className="bg-white border border-stone-200 rounded-2xl p-8 text-center space-y-3">
          <div className="w-12 h-12 mx-auto rounded-xl bg-stone-100 flex items-center justify-center text-stone-600"><BellRing className="w-6 h-6" /></div>
          <h2 className="text-sm font-bold text-stone-900">{t('Chưa theo dõi sản phẩm nào')}</h2>
          <p className="text-xs text-stone-600 max-w-md mx-auto">
            {t('Bấm "Theo dõi giá" trên thẻ sản phẩm mà trợ lý đề xuất hoặc trong mục Sản phẩm đã lưu, rồi chọn mức giá bạn muốn mua.')}
          </p>
          <button onClick={onGoSearch} className="px-4 py-2 bg-stone-900 text-amber-50 rounded-xl text-xs font-semibold hover:bg-stone-800">
            {t('Bắt đầu tìm kiếm')}
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {[...alerts]
            .sort((a, b) => Number(b.status === 'triggered') - Number(a.status === 'triggered'))
            .map(a => (
              <AlertRow
                key={a.id}
                alert={a}
                checking={checkingIds === 'all' || (Array.isArray(checkingIds) && checkingIds.includes(a.id))}
                onCheck={() => onCheck([a.id])}
                onDelete={() => onDelete(a.id)}
              />
            ))}
        </div>
      )}
    </div>
  );
};
