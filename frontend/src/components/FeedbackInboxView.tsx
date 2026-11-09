import React, { useEffect, useEffectEvent, useState } from 'react';
import { AlertCircle, CheckCircle2, Inbox, LifeBuoy, Loader2, Mail, MessageSquarePlus, Phone, RefreshCw } from 'lucide-react';
import { FeedbackCounts, FeedbackItem, FeedbackStatus } from '../types.ts';
import { listFeedback, parseServerDate, updateFeedback } from '../services/agentApi.ts';
import { currentLocale, msg, t } from '../i18n/index.tsx';

interface FeedbackInboxViewProps {
  onCountsChange: (counts: FeedbackCounts) => void;
}

type Filter = FeedbackStatus | 'all';

const fetchFeedback = (status: Filter) => listFeedback(status === 'all' ? undefined : status);

const STATUS_META: Record<FeedbackStatus, { label: string; className: string }> = {
  new: { label: msg('Mới'), className: 'bg-amber-50 text-amber-800 ring-amber-200' },
  in_progress: { label: msg('Đang xử lý'), className: 'bg-sky-50 text-sky-700 ring-sky-200' },
  resolved: { label: msg('Đã xong'), className: 'bg-emerald-50 text-emerald-700 ring-emerald-200' },
};
const STATUSES: FeedbackStatus[] = ['new', 'in_progress', 'resolved'];

const formatTime = (iso: string | null) =>
  iso ? parseServerDate(iso).toLocaleString(currentLocale(), { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit', year: 'numeric' }) : '—';

// Quản trị viên: hộp thư góp ý / yêu cầu hỗ trợ của người dùng
export const FeedbackInboxView: React.FC<FeedbackInboxViewProps> = ({ onCountsChange }) => {
  const [filter, setFilter] = useState<Filter>('new');
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [counts, setCounts] = useState<FeedbackCounts>({ new: 0, in_progress: 0, resolved: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const applyResult = (res: Awaited<ReturnType<typeof listFeedback>>) => {
    setItems(res.items);
    setCounts(res.counts);
    onCountsChange(res.counts);
  };
  const showError = (e: unknown) => setError(e instanceof Error ? e.message : t('Không tải được danh sách.'));

  // Tải lại theo bộ lọc đang chọn (nút Làm mới, sau khi đổi trạng thái)
  const load = async () => {
    setLoading(true);
    setError('');
    try {
      applyResult(await fetchFeedback(filter));
    } catch (e) {
      showError(e);
    } finally {
      setLoading(false);
    }
  };

  // Tải theo bộ lọc mỗi khi đổi bộ lọc; bỏ kết quả của bộ lọc cũ nếu về muộn
  const onFilterLoaded = useEffectEvent(applyResult);
  const onFilterFailed = useEffectEvent(showError);
  useEffect(() => {
    let cancelled = false;
    fetchFeedback(filter)
      .then(res => { if (!cancelled) onFilterLoaded(res); })
      .catch(e => { if (!cancelled) onFilterFailed(e); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [filter]);

  const changeFilter = (next: Filter) => {
    if (next === filter) return;
    setFilter(next);
    setLoading(true);
    setError('');
  };

  // Đổi trạng thái: tải lại để danh sách theo bộ lọc và số đếm luôn khớp server
  const handleUpdate = async (id: string, changes: { status?: FeedbackStatus; admin_note?: string }) => {
    await updateFeedback(id, changes);
    if (changes.status) await load();
    else setItems(prev => prev.map(i => (i.id === id ? { ...i, adminNote: changes.admin_note ?? i.adminNote } : i)));
  };

  const total = counts.new + counts.in_progress + counts.resolved;
  const filters: { id: Filter; label: string; count: number }[] = [
    { id: 'new', label: t('Mới'), count: counts.new },
    { id: 'in_progress', label: t('Đang xử lý'), count: counts.in_progress },
    { id: 'resolved', label: t('Đã xong'), count: counts.resolved },
    { id: 'all', label: t('Tất cả'), count: total },
  ];

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto space-y-5 animate-fadeIn">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-stone-900">{t('Góp ý & hỗ trợ')}</h1>
          <p className="text-xs text-stone-600 mt-1">{t('Góp ý và yêu cầu hỗ trợ người dùng gửi tới quản trị viên, mới nhất ở trên.')}</p>
        </div>
        <button
          onClick={() => void load()}
          disabled={loading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-stone-300 rounded-lg text-xs font-medium text-stone-700 hover:bg-stone-50 disabled:opacity-60 shrink-0"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          {t('Làm mới')}
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {filters.map(f => (
          <button
            key={f.id}
            onClick={() => changeFilter(f.id)}
            className={`px-3 py-1.5 rounded-full border text-xs transition-colors ${
              filter === f.id ? 'bg-stone-900 text-amber-50 border-stone-900' : 'border-stone-200 text-stone-700 hover:border-stone-400 bg-white'
            }`}
          >
            {f.label} <span className={filter === f.id ? 'text-amber-200' : 'text-stone-400'}>({f.count})</span>
          </button>
        ))}
      </div>

      {error && (
        <div className="flex items-start gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 mt-px" />
          <span>{error}</span>
        </div>
      )}

      {loading && items.length === 0 ? (
        <div className="flex items-center justify-center gap-2 py-16 text-xs text-stone-500">
          <Loader2 className="w-4 h-4 animate-spin" /> {t('Đang tải...')}
        </div>
      ) : items.length === 0 ? (
        <div className="bg-white p-10 rounded-2xl border border-stone-200 text-center space-y-2">
          <Inbox className="w-8 h-8 mx-auto text-stone-400" />
          <p className="text-sm font-semibold text-stone-800">{t('Không có yêu cầu nào')}</p>
          <p className="text-xs text-stone-500">{t('Góp ý và yêu cầu hỗ trợ mới của người dùng sẽ hiện ở đây.')}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map(item => <FeedbackCard key={item.id} item={item} onUpdate={handleUpdate} />)}
        </div>
      )}
    </div>
  );
};

const FeedbackCard: React.FC<{
  item: FeedbackItem;
  onUpdate: (id: string, changes: { status?: FeedbackStatus; admin_note?: string }) => Promise<void>;
}> = ({ item, onUpdate }) => {
  const [note, setNote] = useState(item.adminNote);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const isSupport = item.kind === 'support';
  const KindIcon = isSupport ? LifeBuoy : MessageSquarePlus;

  // Ghi chú trên server đổi (VD sau khi lưu) -> hiện bản mới; tính ngay lúc render thay vì trong effect
  const [syncedNote, setSyncedNote] = useState(item.adminNote);
  if (item.adminNote !== syncedNote) {
    setSyncedNote(item.adminNote);
    setNote(item.adminNote);
  }

  const run = async (changes: { status?: FeedbackStatus; admin_note?: string }) => {
    setBusy(true);
    setError('');
    setSaved(false);
    try {
      await onUpdate(item.id, changes);
      if (changes.admin_note !== undefined) setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : t('Không lưu được, vui lòng thử lại.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-stone-200 p-5 space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md font-semibold ${isSupport ? 'bg-rose-50 text-rose-700' : 'bg-violet-50 text-violet-700'}`}>
          <KindIcon className="w-3.5 h-3.5" />
          {isSupport ? t('Yêu cầu hỗ trợ') : t('Góp ý')}
        </span>
        {item.topic && <span className="px-2 py-0.5 rounded-md bg-stone-100 text-stone-700">{t(item.topic)}</span>}
        <span className={`px-2 py-0.5 rounded-md ring-1 font-medium ${STATUS_META[item.status].className}`}>{t(STATUS_META[item.status].label)}</span>
        <span className="ml-auto text-stone-500">{formatTime(item.createdAt)}</span>
      </div>

      <p className="text-sm text-stone-900 whitespace-pre-wrap break-words">{item.content}</p>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-stone-600">
        <span className="font-medium text-stone-800">{item.userName || t('Người dùng')}</span>
        {item.userEmail && (
          <a href={`mailto:${item.userEmail}`} className="inline-flex items-center gap-1 hover:text-stone-900">
            <Mail className="w-3.5 h-3.5" /> {item.userEmail}
          </a>
        )}
        {item.contact && (
          <span className="inline-flex items-center gap-1">
            <Phone className="w-3.5 h-3.5" /> {t('Liên hệ: {contact}', { contact: item.contact })}
          </span>
        )}
      </div>

      <div className="pt-3 border-t border-stone-100 space-y-2">
        <textarea
          value={note}
          onChange={e => { setNote(e.target.value); setSaved(false); }}
          placeholder={t('Ghi chú nội bộ (người dùng không thấy)...')}
          rows={2}
          maxLength={2000}
          className="w-full p-2.5 border border-stone-200 rounded-xl outline-none focus:border-stone-800 focus:ring-1 focus:ring-stone-800 resize-none text-xs text-stone-900 placeholder:text-stone-400"
        />
        <div className="flex flex-wrap items-center gap-2 text-xs">
          {STATUSES.filter(s => s !== item.status).map(s => (
            <button
              key={s}
              disabled={busy}
              onClick={() => void run({ status: s })}
              className="px-3 py-1.5 border border-stone-300 rounded-lg font-medium text-stone-700 hover:bg-stone-50 disabled:opacity-60"
            >
              {t('Chuyển sang: {status}', { status: t(STATUS_META[s].label) })}
            </button>
          ))}
          <button
            disabled={busy || note.trim() === item.adminNote}
            onClick={() => void run({ admin_note: note })}
            className="px-3 py-1.5 bg-stone-900 text-amber-50 rounded-lg font-semibold hover:bg-stone-800 disabled:bg-stone-300"
          >
            {t('Lưu ghi chú')}
          </button>
          {busy && <Loader2 className="w-3.5 h-3.5 animate-spin text-stone-500" />}
          {saved && <span className="inline-flex items-center gap-1 text-emerald-700"><CheckCircle2 className="w-3.5 h-3.5" /> {t('Đã lưu')}</span>}
          {error && <span className="text-red-600">{error}</span>}
        </div>
      </div>
    </div>
  );
};
