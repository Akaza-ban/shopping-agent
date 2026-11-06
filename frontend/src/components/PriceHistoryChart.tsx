import React, { useEffect, useRef, useState } from 'react';
import { PricePoint } from '../types.ts';
import { parseServerDate } from '../services/agentApi.ts';
import { currentLocale, t } from '../i18n/index.tsx';

interface PriceHistoryChartProps {
  points: PricePoint[];
  targetPrice?: number; // vẽ đường tham chiếu "giá mong muốn"
  height?: number;
}

const formatVnd = (n: number) => `${Math.round(n).toLocaleString(currentLocale())} ₫`;
// Nhãn trục gọn: "27,5tr" (tiếng Việt) / "27.5M" (tiếng Anh)
const formatShort = (n: number) =>
  n >= 1_000_000
    ? t('{n}tr', { n: (n / 1_000_000).toLocaleString(currentLocale(), { maximumFractionDigits: 1 }) })
    : `${Math.round(n / 1000)}k`;
const formatDate = (d: Date) => d.toLocaleDateString(currentLocale(), { day: '2-digit', month: '2-digit' });
const formatDateTime = (d: Date) => d.toLocaleString(currentLocale(), { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit', year: 'numeric' });

const PAD = { top: 12, right: 12, bottom: 22, left: 44 };

// Biểu đồ bậc thang: giá giữ nguyên tới mốc thay đổi kế tiếp
export const PriceHistoryChart: React.FC<PriceHistoryChartProps> = ({ points, targetPrice, height = 160 }) => {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(480);
  const [hover, setHover] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(240, entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const data = points.map(p => ({ ...p, date: parseServerDate(p.recordedAt) })).sort((a, b) => a.date.getTime() - b.date.getTime());
  const prices = data.map(d => d.price);
  const min = Math.min(...prices), max = Math.max(...prices);

  if (data.length < 2) {
    return (
      <div className="text-[11px] text-stone-500 p-3 bg-panel border border-stone-200 rounded-lg">
        {data.length === 0
          ? t('Chưa có dữ liệu lịch sử giá cho sản phẩm này.')
          : <>{t('Mới có 1 mốc giá:')} <strong className="text-stone-800">{formatVnd(data[0].price)}</strong> ({formatDate(data[0].date)}). {t('Biểu đồ sẽ hiện khi giá thay đổi.')}</>}
      </div>
    );
  }

  // Kéo đường tới hiện tại với giá cuối cùng
  const now = new Date();
  const t0 = data[0].date.getTime();
  const t1 = Math.max(now.getTime(), data[data.length - 1].date.getTime() + 1);
  const lo = Math.min(min, targetPrice ?? min) * 0.97;
  const hi = Math.max(max, targetPrice ?? max) * 1.02;
  const innerW = width - PAD.left - PAD.right;
  const innerH = height - PAD.top - PAD.bottom;
  const x = (t: number) => PAD.left + ((t - t0) / (t1 - t0)) * innerW;
  const y = (v: number) => PAD.top + (1 - (v - lo) / (hi - lo)) * innerH;

  let path = `M${x(t0)},${y(data[0].price)}`;
  for (const d of data.slice(1)) path += ` H${x(d.date.getTime())} V${y(d.price)}`;
  path += ` H${x(t1)}`;

  const ticks = [lo + (hi - lo) * 0.15, (lo + hi) / 2, hi - (hi - lo) * 0.15];

  const onMove = (e: React.MouseEvent<SVGRectElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const at = t0 + ((e.clientX - rect.left) / rect.width) * (t1 - t0);
    // mốc có hiệu lực tại thời điểm `at` = mốc cuối cùng trước `at`
    let idx = 0;
    data.forEach((d, i) => { if (d.date.getTime() <= at) idx = i; });
    setHover(idx);
  };

  const hovered = hover !== null ? data[hover] : null;
  const hoverX = hovered ? x(hovered.date.getTime()) : 0;

  return (
    <div className="space-y-1.5">
      <div ref={wrapRef} className="relative">
        <svg width={width} height={height} role="img" aria-label={t('Lịch sử giá: thấp nhất {min}, cao nhất {max}', { min: formatVnd(min), max: formatVnd(max) })}>
          {ticks.map(v => (
            <g key={v}>
              <line x1={PAD.left} x2={width - PAD.right} y1={y(v)} y2={y(v)} className="stroke-stone-200" strokeWidth={1} />
              <text x={PAD.left - 6} y={y(v)} textAnchor="end" dominantBaseline="middle" className="fill-stone-500 text-[10px]">
                {formatShort(v)}
              </text>
            </g>
          ))}

          {targetPrice !== undefined && (
            <g>
              <line x1={PAD.left} x2={width - PAD.right} y1={y(targetPrice)} y2={y(targetPrice)} className="stroke-stone-500" strokeWidth={1} strokeDasharray="4 3" />
              <text x={width - PAD.right} y={y(targetPrice) - 4} textAnchor="end" className="fill-stone-600 text-[10px] font-medium">
                {t('Giá mong muốn {price}', { price: formatShort(targetPrice) })}
              </text>
            </g>
          )}

          <path d={path} fill="none" className="stroke-amber-700" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />

          <text x={PAD.left} y={height - 6} className="fill-stone-500 text-[10px]">{formatDate(data[0].date)}</text>
          <text x={width - PAD.right} y={height - 6} textAnchor="end" className="fill-stone-500 text-[10px]">{t('Hôm nay')}</text>

          {hovered && (
            <g pointerEvents="none">
              <line x1={hoverX} x2={hoverX} y1={PAD.top} y2={PAD.top + innerH} className="stroke-stone-400" strokeWidth={1} />
              <circle cx={hoverX} cy={y(hovered.price)} r={4.5} className="fill-amber-700 stroke-white" strokeWidth={2} />
            </g>
          )}

          {/* Vùng bắt chuột lớn hơn đường vẽ */}
          <rect
            x={PAD.left} y={PAD.top} width={innerW} height={innerH} fill="transparent"
            onMouseMove={onMove} onMouseLeave={() => setHover(null)}
          />
        </svg>

        {hovered && (
          <div
            className="absolute pointer-events-none px-2 py-1 rounded-md bg-stone-900 text-stone-50 text-[11px] shadow-md whitespace-nowrap"
            style={{ left: Math.min(Math.max(hoverX - 60, 0), width - 130), top: 0 }}
          >
            <div className="font-semibold">{formatVnd(hovered.price)}</div>
            <div className="opacity-80">{t('từ {date}', { date: formatDateTime(hovered.date) })}</div>
          </div>
        )}
      </div>

      <div className="flex items-center justify-between text-[11px] text-stone-500">
        <span>{t('Thấp nhất')} <strong className="text-stone-800">{formatVnd(min)}</strong> {t('· Cao nhất')} <strong className="text-stone-800">{formatVnd(max)}</strong> · {t('{count} mốc', { count: data.length })}</span>
        <button onClick={() => setShowTable(!showTable)} className="font-medium text-stone-600 hover:text-stone-900 underline underline-offset-2">
          {showTable ? t('Ẩn bảng') : t('Xem bảng')}
        </button>
      </div>

      {showTable && (
        <table className="w-full text-[11px] border border-stone-200 rounded-lg overflow-hidden">
          <thead className="bg-panel text-stone-600">
            <tr><th className="p-1.5 text-left font-semibold">{t('Thời điểm')}</th><th className="p-1.5 text-right font-semibold">{t('Giá bán')}</th></tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {[...data].reverse().map(d => (
              <tr key={d.recordedAt}><td className="p-1.5 text-stone-700">{formatDateTime(d.date)}</td><td className="p-1.5 text-right font-mono text-stone-900">{formatVnd(d.price)}</td></tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
