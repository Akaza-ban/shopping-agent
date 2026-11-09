import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, LifeBuoy, Loader2, MessageSquarePlus, X } from 'lucide-react';
import type { HelpKind } from './Sidebar.tsx';
import { msg, t } from '../i18n/index.tsx';

interface HelpRequestModalProps {
  kind: HelpKind | null;
  onSubmit: (kind: HelpKind, topic: string, content: string, contact: string) => Promise<void>;
  onClose: () => void;
}

const COPY: Record<HelpKind, { title: string; icon: React.ElementType; placeholder: string; topics: string[] }> = {
  feedback: {
    title: msg('Gửi góp ý'),
    icon: MessageSquarePlus,
    placeholder: msg('Bạn muốn trợ lý cải thiện điều gì? VD: kết quả chưa đúng cấu hình, muốn thêm sàn, giao diện khó dùng...'),
    topics: [msg('Chất lượng tư vấn'), msg('Kết quả tìm kiếm'), msg('Giao diện'), msg('Tính năng mới')],
  },
  support: {
    title: msg('Yêu cầu hỗ trợ'),
    icon: LifeBuoy,
    placeholder: msg('Mô tả vấn đề bạn gặp phải và các bước để tái hiện (nếu có)...'),
    topics: [msg('Lỗi khi tìm kiếm'), msg('Không kết nối được'), msg('Sai giá / sai thông tin'), msg('Khác')],
  },
};

// Góp ý / yêu cầu hỗ trợ: gửi lên server cho quản trị viên xử lý
export const HelpRequestModal: React.FC<HelpRequestModalProps> = ({ kind, onSubmit, onClose }) => {
  if (!kind) return null;
  // key: mở lại hoặc đổi loại yêu cầu là một form mới
  return <HelpRequestForm key={kind} kind={kind} onSubmit={onSubmit} onClose={onClose} />;
};

const HelpRequestForm: React.FC<HelpRequestModalProps & { kind: HelpKind }> = ({ kind, onSubmit, onClose }) => {
  const [topic, setTopic] = useState(COPY[kind].topics[0]);
  const [content, setContent] = useState('');
  const [contact, setContact] = useState('');
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const { title, icon: Icon, placeholder, topics } = COPY[kind];

  const submit = async () => {
    if (!content.trim() || sending) return;
    setSending(true);
    setError('');
    try {
      await onSubmit(kind, topic, content.trim(), contact.trim());
      setSent(true);
    } catch (e) {
      setError(e instanceof Error && e.message ? e.message : t('Không gửi được, vui lòng thử lại.'));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl animate-scaleUp overflow-hidden">
        <div className="p-5 border-b border-stone-200 flex items-center justify-between bg-panel">
          <div className="flex items-center gap-2">
            <Icon className="w-4 h-4 text-stone-800" />
            <h3 className="text-sm font-bold text-stone-900">{t(title)}</h3>
          </div>
          <button onClick={onClose} aria-label={t('Đóng')} className="w-8 h-8 rounded-lg hover:bg-stone-200 flex items-center justify-center text-stone-500">
            <X className="w-4 h-4" />
          </button>
        </div>

        {sent ? (
          <div className="p-8 text-center space-y-3">
            <CheckCircle2 className="w-10 h-10 mx-auto text-emerald-600" />
            <p className="text-sm font-semibold text-stone-900">{t('Đã ghi nhận, cảm ơn bạn!')}</p>
            <p className="text-xs text-stone-500">{t('Quản trị viên đã nhận được nội dung và sẽ xử lý sớm.')}</p>
          </div>
        ) : (
          <div className="p-6 space-y-4 text-xs">
            <div className="flex flex-wrap gap-2">
              {topics.map(item => (
                <button
                  key={item}
                  onClick={() => setTopic(item)}
                  className={`px-3 py-1.5 rounded-full border transition-colors ${
                    topic === item ? 'bg-stone-900 text-amber-50 border-stone-900' : 'border-stone-200 text-stone-700 hover:border-stone-400'
                  }`}
                >
                  {t(item)}
                </button>
              ))}
            </div>
            <textarea
              value={content}
              onChange={e => setContent(e.target.value)}
              placeholder={t(placeholder)}
              rows={5}
              className="w-full p-3 border border-stone-300 rounded-xl outline-none focus:border-stone-800 focus:ring-1 focus:ring-stone-800 resize-none text-stone-900 placeholder:text-stone-400"
            />
            {kind === 'support' && (
              <input
                value={contact}
                onChange={e => setContact(e.target.value)}
                placeholder={t('Email hoặc số điện thoại để liên hệ lại (không bắt buộc)')}
                className="w-full px-3 py-2 border border-stone-300 rounded-xl outline-none focus:border-stone-800 focus:ring-1 focus:ring-stone-800 text-stone-900 placeholder:text-stone-400"
              />
            )}
            {error && (
              <div className="flex items-start gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700">
                <AlertCircle className="w-4 h-4 shrink-0 mt-px" />
                <span>{error}</span>
              </div>
            )}
          </div>
        )}

        <div className="p-4 border-t border-stone-200 bg-stone-50 flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-2 text-xs font-medium text-stone-600 hover:text-stone-900">
            {sent ? t('Đóng') : t('Hủy')}
          </button>
          {!sent && (
            <button
              onClick={() => void submit()}
              disabled={!content.trim() || sending}
              className="px-4 py-2 bg-stone-900 text-amber-50 rounded-xl text-xs font-semibold hover:bg-stone-800 transition-colors disabled:bg-stone-300 flex items-center gap-1.5"
            >
              {sending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {sending ? t('Đang gửi...') : t('Gửi')}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
