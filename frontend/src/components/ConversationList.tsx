import React, { useState } from 'react';
import { Loader2, Plus, Trash2 } from 'lucide-react';
import { ChatConversation } from '../types.ts';
import { t } from '../i18n/index.tsx';

interface ConversationListProps {
  conversations: ChatConversation[];
  activeId: string | null;
  busyId: string | null; // đoạn chat đang chờ agent trả lời: không cho chuyển / xóa
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
}

// Danh sách hội thoại tư vấn; tên mỗi hội thoại là câu hỏi đầu tiên người dùng nhập
export const ConversationList: React.FC<ConversationListProps> = ({
  conversations, activeId, busyId, onSelect, onCreate, onDelete
}) => {
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const sorted = [...conversations].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));

  return (
    <aside className="hidden md:flex w-64 shrink-0 h-full flex-col bg-white border-r border-stone-200">
      <div className="h-12 shrink-0 flex items-center justify-between pl-4 pr-2 border-b border-stone-200">
        <span className="text-[11px] font-bold text-stone-500 uppercase tracking-wider">{t('Hội thoại')}</span>
        <button
          onClick={onCreate}
          disabled={!!busyId}
          className="w-8 h-8 rounded-md flex items-center justify-center text-stone-500 hover:text-stone-900 hover:bg-stone-100 transition-colors disabled:opacity-40 disabled:hover:bg-transparent"
          title={t('Hội thoại mới')}
          aria-label={t('Hội thoại mới')}
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {sorted.map(c => {
          const isActive = c.id === activeId;
          const isBusy = c.id === busyId;
          const locked = !!busyId && !isBusy;

          if (confirmId === c.id) {
            return (
              <div key={c.id} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-50 border border-red-200">
                <span className="flex-1 text-xs font-medium text-red-900">{t('Xóa hội thoại này?')}</span>
                <button onClick={() => setConfirmId(null)} className="text-[11px] font-medium text-stone-600 hover:text-stone-900">
                  {t('Hủy')}
                </button>
                <button
                  onClick={() => { setConfirmId(null); onDelete(c.id); }}
                  className="text-[11px] font-semibold text-red-700 hover:text-red-900"
                >
                  {t('Xóa')}
                </button>
              </div>
            );
          }

          return (
            <div
              key={c.id}
              onClick={() => !locked && onSelect(c.id)}
              title={c.title}
              className={`group flex items-center gap-1 px-3 py-2.5 rounded-lg transition-colors ${
                isActive ? 'bg-stone-100 ring-1 ring-stone-200' : 'hover:bg-stone-50'
              } ${locked ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
            >
              <span className={`flex-1 min-w-0 truncate text-[13px] ${isActive ? 'font-semibold text-stone-900' : 'font-medium text-stone-700'}`}>
                {c.title}
              </span>
              {isBusy ? (
                <Loader2 className="w-3.5 h-3.5 shrink-0 text-stone-400 animate-spin" />
              ) : (
                <button
                  onClick={e => { e.stopPropagation(); setConfirmId(c.id); }}
                  disabled={locked}
                  className="shrink-0 p-1 -mr-1 rounded text-stone-400 opacity-0 group-hover:opacity-100 focus:opacity-100 hover:text-red-700 transition-opacity"
                  title={t('Xóa hội thoại')}
                  aria-label={t('Xóa hội thoại')}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
};
