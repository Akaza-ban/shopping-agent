import React, { useState } from 'react';
import { ArrowRight, BellRing, Bookmark, BookmarkX, History, LifeBuoy, Search, Settings, ShieldCheck, Table2, Trash2 } from 'lucide-react';
import { ActivityItem, ActivityType, NavigationTab } from '../types.ts';
import { currentLocale, msg, t } from '../i18n/index.tsx';

interface ActivityLogViewProps {
  activities: ActivityItem[];
  onReopenInChat: (item: ActivityItem) => void;
  onNavigate: (tab: NavigationTab) => void;
  onClear: () => void;
}

export const ACTIVITY_META: Record<ActivityType, { label: string; icon: React.ElementType; className: string }> = {
  search: { label: msg('Tìm kiếm'), icon: Search, className: 'bg-amber-50 text-amber-800' },
  save: { label: msg('Lưu sản phẩm'), icon: Bookmark, className: 'bg-emerald-50 text-emerald-700' },
  unsave: { label: msg('Bỏ lưu'), icon: BookmarkX, className: 'bg-stone-100 text-stone-600' },
  compare: { label: msg('So sánh'), icon: Table2, className: 'bg-sky-50 text-sky-700' },
  policy: { label: msg('Tra cứu chính sách'), icon: ShieldCheck, className: 'bg-violet-50 text-violet-700' },
  settings: { label: msg('Cài đặt'), icon: Settings, className: 'bg-stone-100 text-stone-600' },
  alert: { label: msg('Theo dõi giá'), icon: BellRing, className: 'bg-amber-50 text-amber-800' },
  support: { label: msg('Góp ý & hỗ trợ'), icon: LifeBuoy, className: 'bg-rose-50 text-rose-700' },
};

const dayLabel = (iso: string) => {
  const d = new Date(iso);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === today.toDateString()) return t('Hôm nay');
  if (d.toDateString() === yesterday.toDateString()) return t('Hôm qua');
  return d.toLocaleDateString(currentLocale(), { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' });
};

export const formatTime = (iso: string) =>
  new Date(iso).toLocaleTimeString(currentLocale(), { hour: '2-digit', minute: '2-digit' });

export const ActivityLogView: React.FC<ActivityLogViewProps> = ({ activities, onReopenInChat, onNavigate, onClear }) => {
  const [filter, setFilter] = useState<ActivityType | 'all'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [confirmClear, setConfirmClear] = useState(false);

  const term = searchTerm.toLowerCase();
  const filtered = activities.filter(a =>
    (filter === 'all' || a.type === filter) &&
    (a.title.toLowerCase().includes(term) || (a.detail ?? '').toLowerCase().includes(term))
  );

  // Nhóm theo ngày, giữ thứ tự mới nhất trước
  const groups: { label: string; items: ActivityItem[] }[] = [];
  filtered.forEach(a => {
    const label = dayLabel(a.timestamp);
    const last = groups[groups.length - 1];
    if (last && last.label === label) last.items.push(a);
    else groups.push({ label, items: [a] });
  });

  if (activities.length === 0) {
    return (
      <div className="h-[calc(100vh-3.5rem)] flex items-center justify-center p-8">
        <div className="bg-white p-8 rounded-2xl border border-stone-200 shadow-sm text-center max-w-md space-y-3">
          <div className="w-12 h-12 mx-auto rounded-xl bg-stone-100 flex items-center justify-center">
            <History className="w-6 h-6 text-stone-600" />
          </div>
          <h2 className="text-base font-bold text-stone-900">{t('Chưa có hoạt động nào')}</h2>
          <p className="text-xs text-stone-600">
            {t('Các lượt tìm kiếm, sản phẩm đã lưu, lần so sánh và tra cứu chính sách sẽ được ghi lại tại đây.')}
          </p>
          <button
            onClick={() => onNavigate('search')}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-stone-900 text-amber-50 rounded-xl text-xs font-semibold hover:bg-stone-800"
          >
            <span>{t('Bắt đầu tìm kiếm')}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-5 animate-fadeIn">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-stone-900">{t('Lịch sử hoạt động ({count})', { count: activities.length })}</h1>
          <p className="text-xs text-stone-600 mt-1">{t('Các thao tác bạn đã thực hiện trong hệ thống, mới nhất ở trên.')}</p>
        </div>
        {confirmClear ? (
          <div className="flex items-center gap-2 text-xs shrink-0">
            <span className="text-stone-600">{t('Xóa toàn bộ lịch sử?')}</span>
            <button
              onClick={() => { onClear(); setConfirmClear(false); }}
              className="px-3 py-1.5 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700"
            >
              {t('Xóa')}
            </button>
            <button
              onClick={() => setConfirmClear(false)}
              className="px-3 py-1.5 border border-stone-300 rounded-lg font-medium text-stone-700 hover:bg-stone-50"
            >
              {t('Hủy')}
            </button>
          </div>
        ) : (
          <button
            onClick={() => setConfirmClear(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-stone-300 rounded-lg text-xs font-medium text-stone-700 hover:text-red-700 hover:border-red-300 shrink-0"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>{t('Xóa lịch sử')}</span>
          </button>
        )}
      </div>

      <div className="flex flex-col md:flex-row md:items-center gap-3 bg-white p-3 rounded-xl border border-stone-200 shadow-xs">
        <div className="flex items-center gap-2 bg-inset px-3 py-1.5 rounded-lg border border-stone-200 w-full md:w-72">
          <Search className="w-3.5 h-3.5 text-stone-400 shrink-0" />
          <input
            type="text"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            placeholder={t('Tìm trong lịch sử...')}
            className="w-full text-xs bg-transparent border-none outline-none text-stone-900 placeholder:text-stone-400"
          />
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {(['all', ...Object.keys(ACTIVITY_META)] as (ActivityType | 'all')[]).map(type => (
            <button
              key={type}
              onClick={() => setFilter(type)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-colors ${
                filter === type ? 'bg-stone-900 text-amber-50' : 'text-stone-600 hover:bg-stone-100'
              }`}
            >
              {type === 'all' ? t('Tất cả') : t(ACTIVITY_META[type].label)}
            </button>
          ))}
        </div>
      </div>

      {groups.map(group => (
        <div key={group.label} className="space-y-2">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-stone-500 first-letter:uppercase">{group.label}</div>
          <div className="bg-white rounded-xl border border-stone-200 shadow-sm divide-y divide-stone-100">
            {group.items.map(a => {
              const meta = ACTIVITY_META[a.type];
              const Icon = meta.icon;
              const canReopen = (a.products && a.products.length > 0) || a.targetTab;
              return (
                <div key={a.id} className="p-4 flex items-start gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${meta.className}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-semibold text-stone-900">{a.title}</div>
                    {a.detail && <div className="text-[11px] text-stone-600 mt-0.5">{a.detail}</div>}
                    <div className="text-[10px] text-stone-400 mt-1">
                      {t(meta.label)} · <span className="font-mono">{formatTime(a.timestamp)}</span>
                    </div>
                  </div>
                  {canReopen && (
                    <button
                      onClick={() => (a.products?.length ? onReopenInChat(a) : onNavigate(a.targetTab!))}
                      className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-semibold text-stone-700 bg-inset hover:bg-stone-200 rounded-lg"
                    >
                      {t('Mở lại')} <ArrowRight className="w-3 h-3" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}

      {filtered.length === 0 && (
        <p className="text-xs text-stone-500 text-center py-6">{t('Không có hoạt động nào khớp bộ lọc.')}</p>
      )}
    </div>
  );
};
