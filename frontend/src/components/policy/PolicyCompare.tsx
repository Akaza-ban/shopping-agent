import React from 'react';
import { ChevronRight, ExternalLink, Quote, Trophy } from 'lucide-react';
import { PlatformPolicy, PolicyExcerpt } from '../../types.ts';
import { PLATFORMS, getPlatformName } from '../../services/shoppingService.ts';
import { t } from '../../i18n/index.tsx';

// So sánh gọn: chỉ các tiêu chí quyết định, mỗi nơi bán một thẻ (điện thoại thì xếp dọc)
export const PolicyCompare: React.FC<{ policies: PlatformPolicy[] }> = ({ policies }) => {
  const maxDays = Math.max(0, ...policies.map(p => p.returnWindowDays));
  const anyFree = policies.some(p => p.freeReturn);
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {policies.map(p => {
        const bestDays = policies.length > 1 && p.returnWindowDays === maxDays;
        return (
          <div key={p.platformId} className="p-4 bg-white rounded-xl border border-stone-200 shadow-sm space-y-2.5 text-xs">
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="font-bold text-stone-900">{getPlatformName(p.platformId)}</div>
                <div className="text-[10px] text-stone-500">{t(PLATFORMS.find(x => x.id === p.platformId)?.type ?? '')}</div>
              </div>
              {p.verified === false && (
                <span className="px-1.5 py-0.5 rounded bg-amber-50 border border-amber-200 text-[10px] font-medium text-amber-800">
                  {t('Chưa đối chiếu trang gốc')}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <span className={`font-mono font-bold text-base ${bestDays ? 'text-emerald-700' : 'text-stone-900'}`}>
                {t('{days} ngày', { days: p.returnWindowDays })}
              </span>
              <span className="text-stone-500">{t('đổi trả')}</span>
              {bestDays && <Trophy className="w-3.5 h-3.5 text-emerald-700" />}
            </div>
            <Criterion label={t('Khi đổi ý')} best={anyFree && p.freeReturn}
                       value={p.freeReturn ? t('Trả hàng miễn phí') : p.refundTime ? t(p.refundTime) : t('Không / có điều kiện')} />
            <Criterion label={t('Khi lỗi nhà sản xuất')} value={t(p.defectExchange)} />
            <Criterion label={t('Bảo hành')} value={t(p.warrantyHandling)} />
          </div>
        );
      })}
    </div>
  );
};

const Criterion: React.FC<{ label: string; value: string; best?: boolean }> = ({ label, value, best }) => (
  <div>
    <div className="text-[10px] font-semibold text-stone-500 uppercase tracking-wider">{label}</div>
    <div className={`mt-0.5 ${best ? 'text-emerald-800 font-semibold' : 'text-stone-800'}`}>{value || '—'}</div>
  </div>
);

// Toàn bộ điều khoản và đoạn trích nguyên văn, thu gọn mặc định
export const PolicyDetails: React.FC<{ policies: PlatformPolicy[]; excerpts: PolicyExcerpt[] }> = ({ policies, excerpts }) => {
  const rows: { label: string; render: (p: PlatformPolicy) => React.ReactNode }[] = [
    { label: t('Thời hạn đổi trả'), render: p => t('{days} ngày', { days: p.returnWindowDays }) },
    { label: t('Trả hàng miễn phí'), render: p => (p.freeReturn ? t('Có') : t('Không / có điều kiện')) },
    { label: t('Điều kiện đổi trả'), render: p => <ul className="space-y-1">{p.returnConditions.map(c => <li key={c}>• {t(c)}</li>)}</ul> },
    { label: t('Phí vận chuyển trả hàng'), render: p => t(p.returnShippingFee) },
    { label: t('Thời gian hoàn tiền'), render: p => t(p.refundTime) },
    { label: t('Lỗi nhà sản xuất'), render: p => t(p.defectExchange) },
    { label: t('Tiếp nhận bảo hành'), render: p => t(p.warrantyHandling) },
    { label: t('Ngoại lệ cần lưu ý'), render: p => <ul className="space-y-1">{p.exceptions.map(c => <li key={c}>{t(c)}</li>)}</ul> },
    {
      label: t('Nguồn'),
      render: p => (
        <a href={p.policyUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 underline decoration-stone-300">
          {t('Trang chính sách')} <ExternalLink className="w-3 h-3" />
          <span className="text-[10px] text-stone-400 no-underline">({t('Kiểm tra: {date}', { date: p.lastChecked })})</span>
        </a>
      ),
    },
  ];
  return (
    <details className="group bg-white rounded-xl border border-stone-200 shadow-sm">
      <summary className="cursor-pointer list-none p-4 flex items-center gap-1.5 text-xs font-semibold text-stone-700 hover:text-stone-950">
        <ChevronRight className="w-4 h-4 transition-transform group-open:rotate-90" />
        {t('Xem đầy đủ chính sách')}
      </summary>
      <div className="px-4 pb-4 space-y-4">
        {policies.map(p => (
          <div key={p.platformId} className="space-y-2">
            {policies.length > 1 && <div className="text-xs font-bold text-stone-900">{getPlatformName(p.platformId)}</div>}
            <dl className="divide-y divide-stone-100 border border-stone-100 rounded-lg">
              {rows.map(r => (
                <div key={r.label} className="grid sm:grid-cols-[11rem_1fr] gap-1 sm:gap-3 p-2.5 text-xs">
                  <dt className="text-[11px] font-semibold text-stone-500">{r.label}</dt>
                  <dd className="text-stone-800">{r.render(p)}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
        {excerpts.length > 0 && (
          <div className="space-y-2">
            <div className="text-[11px] font-semibold text-stone-500 uppercase tracking-wider">{t('Trích từ trang chính sách')}</div>
            {excerpts.map(e => (
              <div key={e.id} className="flex gap-2 text-xs text-stone-700">
                <Quote className="w-3.5 h-3.5 text-stone-400 shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <span className="font-semibold text-stone-900">{getPlatformName(e.platformId)}: </span>
                  <span className="whitespace-pre-line">{t(e.text)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </details>
  );
};
