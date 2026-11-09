import React, { useState } from 'react';
import { AlertTriangle, BadgeCheck, CheckSquare, ExternalLink, Quote, Sparkles, Square } from 'lucide-react';
import { PlatformPolicy, PolicyExcerpt, PolicyScenario } from '../../types.ts';
import { getPlatformName } from '../../services/shoppingService.ts';
import { t } from '../../i18n/index.tsx';
import { keyFacts } from './scenarios.ts';

interface PolicyAnswerProps {
  summary: string;
  sourceIds: number[];
  excerpts: PolicyExcerpt[];
  policies: PlatformPolicy[];
  scenario: PolicyScenario | null;
}

// Câu trả lời trước, chi tiết sau: kết luận + số liệu chính + căn cứ, rồi điều kiện cần chuẩn bị và lưu ý
export const PolicyAnswer: React.FC<PolicyAnswerProps> = ({ summary, sourceIds, excerpts, policies, scenario }) => {
  const [openSource, setOpenSource] = useState<number | null>(null);
  const [checked, setChecked] = useState<string[]>([]);
  // Câu trả lời mới -> đóng nguồn đang mở và bỏ các mục đã đánh dấu (tính ngay lúc render thay vì trong effect)
  const [answeredSummary, setAnsweredSummary] = useState(summary);
  if (summary !== answeredSummary) {
    setAnsweredSummary(summary);
    setOpenSource(null);
    setChecked([]);
  }

  const single = policies.length === 1 ? policies[0] : null;
  const sources = sourceIds.map(id => excerpts.find(e => e.id === id)).filter((e): e is PolicyExcerpt => !!e);
  const opened = sources.find(e => e.id === openSource);
  const toggle = (c: string) => setChecked(prev => (prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]));

  return (
    <div className="space-y-3">
      <div className="p-4 bg-emerald-50/70 border border-emerald-200 rounded-xl space-y-3">
        <div className="flex gap-2 text-sm text-emerald-950 leading-relaxed">
          <Sparkles className="w-4 h-4 text-emerald-700 shrink-0 mt-1" />
          <p className="whitespace-pre-line">{summary}</p>
        </div>

        {single && (
          <div className="flex flex-wrap gap-1.5 pl-6">
            <span className="px-2 py-0.5 rounded-full bg-white border border-emerald-200 text-[11px] font-semibold text-emerald-900">
              {t('{days} ngày đổi trả', { days: single.returnWindowDays })}
            </span>
            <span className="px-2 py-0.5 rounded-full bg-white border border-emerald-200 text-[11px] font-semibold text-emerald-900">
              {single.freeReturn ? t('Trả hàng miễn phí') : t('Trả hàng không lỗi có thể mất phí')}
            </span>
            {single.verified === false && (
              <span className="px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-[11px] font-semibold text-amber-800">
                {t('Chưa đối chiếu trang gốc')}
              </span>
            )}
          </div>
        )}

        {sources.length > 0 && (
          <div className="pl-6 space-y-2">
            <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-emerald-900">
              <span className="font-semibold">{t('Căn cứ:')}</span>
              {sources.map((e, i) => (
                <button
                  key={e.id}
                  type="button"
                  onClick={() => setOpenSource(openSource === e.id ? null : e.id)}
                  className={`px-1.5 py-0.5 rounded border transition-colors ${
                    openSource === e.id ? 'bg-emerald-800 text-white border-emerald-800' : 'bg-white border-emerald-200 hover:border-emerald-500'
                  }`}
                >
                  {getPlatformName(e.platformId)} · {t('đoạn {n}', { n: i + 1 })}
                </button>
              ))}
            </div>
            {opened && (
              <div className="p-3 bg-white rounded-lg border border-emerald-200 text-xs text-stone-700 flex gap-2">
                <Quote className="w-3.5 h-3.5 text-stone-400 shrink-0 mt-0.5" />
                <div className="min-w-0 space-y-1">
                  <p className="whitespace-pre-line">{t(opened.text)}</p>
                  {opened.url && (
                    <a href={opened.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-stone-500 hover:text-stone-900 underline decoration-stone-300">
                      {opened.title || t('Trang chính sách')} <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {single && (
        <div className="grid gap-3 md:grid-cols-2">
          <div className="p-4 bg-white rounded-xl border border-stone-200 space-y-2">
            {keyFacts(single, scenario).map(f => (
              <div key={f.label} className="text-xs">
                <div className="text-[11px] font-semibold text-stone-500 uppercase tracking-wider">{t(f.label)}</div>
                <div className="text-stone-900 mt-0.5">{t(f.value)}</div>
              </div>
            ))}
            <div className="flex items-center gap-1.5 text-[11px] text-stone-500 pt-1">
              <BadgeCheck className="w-3.5 h-3.5" />
              <a href={single.policyUrl} target="_blank" rel="noreferrer" className="underline decoration-stone-300 hover:text-stone-900">
                {t('Trang chính sách')}
              </a>
              <span>· {t('Kiểm tra: {date}', { date: single.lastChecked })}</span>
            </div>
          </div>

          {single.returnConditions.length > 0 && (
            <div className="p-4 bg-white rounded-xl border border-stone-200">
              <div className="text-[11px] font-semibold text-stone-500 uppercase tracking-wider mb-2">{t('Cần chuẩn bị')}</div>
              <ul className="space-y-1.5">
                {single.returnConditions.map(c => (
                  <li key={c}>
                    <button type="button" onClick={() => toggle(c)} className="flex items-start gap-2 text-left text-xs text-stone-800">
                      {checked.includes(c)
                        ? <CheckSquare className="w-4 h-4 text-emerald-700 shrink-0" />
                        : <Square className="w-4 h-4 text-stone-400 shrink-0" />}
                      <span className={checked.includes(c) ? 'line-through text-stone-400' : ''}>{t(c)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {single && single.exceptions.length > 0 && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-950">
          <div className="flex items-center gap-1.5 font-semibold mb-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-700" /> {t('Lưu ý')}
          </div>
          <ul className="space-y-1 pl-5 list-disc">
            {single.exceptions.map(e => <li key={e}>{t(e)}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
};
