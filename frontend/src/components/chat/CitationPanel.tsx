import React from 'react';
import { BookOpen, ExternalLink, X } from 'lucide-react';
import { CitationItem } from '../../types.ts';
import { getPlatformName } from '../../services/shoppingService.ts';
import { t } from '../../i18n/index.tsx';

// Bảng bên phải: chi tiết một nguồn được trợ lý trích dẫn (giá ghi nhận, đoạn thu thập, link gốc)
export const CitationPanel: React.FC<{ citation: CitationItem; onClose: () => void }> = ({ citation, onClose }) => (
  <aside className="w-96 shrink-0 h-full bg-white border-l border-stone-200 shadow-lg flex flex-col z-30 animate-slideLeft">
    <div className="p-4 border-b border-stone-200 flex items-center justify-between bg-stone-50">
      <div className="flex items-center gap-2">
        <BookOpen className="w-4 h-4 text-amber-800" />
        <h3 className="text-xs font-bold text-stone-900 uppercase tracking-wider">{t('Chi tiết nguồn')}</h3>
      </div>
      <button
        onClick={onClose}
        aria-label={t('Đóng')}
        className="w-7 h-7 rounded-lg hover:bg-stone-200 flex items-center justify-center text-stone-500"
      >
        <X className="w-4 h-4" />
      </button>
    </div>

    <div className="p-5 flex-1 overflow-y-auto space-y-4 text-xs leading-relaxed">
      <div>
        <span className="text-[10px] font-bold text-amber-800 uppercase tracking-wider">{t('Nguồn [{index}]', { index: citation.index })}</span>
        <h4 className="text-sm font-bold text-stone-900 mt-1">{citation.sourceName}</h4>
        <span className="inline-block mt-1 px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 text-[11px] font-medium">
          {getPlatformName(citation.platformId)}
        </span>
      </div>

      {citation.price && (
        <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-xl space-y-1">
          <span className="text-[11px] text-stone-600 block">{t('Giá ghi nhận:')}</span>
          <div className="text-lg font-bold text-amber-950 font-mono">{citation.price}</div>
          {citation.officialPrice && (
            <span className="text-[11px] text-stone-500 line-through block">{t('Giá niêm yết: {price}', { price: citation.officialPrice })}</span>
          )}
        </div>
      )}

      <div className="space-y-2">
        <span className="text-xs font-semibold text-stone-800">{t('Nội dung thu thập được:')}</span>
        <div className="p-3.5 bg-panel border border-stone-200 rounded-xl text-stone-800 italic">
          "{citation.excerpt}"
        </div>
      </div>

      <div className="pt-3 border-t border-stone-200 flex items-center justify-between text-[11px] text-stone-500">
        <span>{t('Thời điểm thu thập:')}</span>
        <span className="font-mono text-stone-700">{citation.verifiedDate}</span>
      </div>

      {citation.url && (
        <a
          href={citation.url}
          target="_blank"
          rel="noreferrer"
          className="w-full py-2.5 bg-stone-900 text-amber-50 rounded-xl text-xs font-semibold hover:bg-stone-800 transition-colors flex items-center justify-center gap-1.5"
        >
          <span>{t('Mở trang gốc')}</span>
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      )}
    </div>
  </aside>
);
