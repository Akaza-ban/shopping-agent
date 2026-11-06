import React from 'react';
import { Clock, Languages, Monitor, Moon, Settings, Sun, X } from 'lucide-react';
import { ThemeMode, usePreferences } from '../hooks/usePreferences.tsx';
import { LANGUAGES, msg, useI18n } from '../i18n/index.tsx';

interface PreferencesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const THEME_OPTIONS: { id: ThemeMode; label: string; icon: React.ElementType }[] = [
  { id: 'light', label: msg('Sáng'), icon: Sun },
  { id: 'dark', label: msg('Tối'), icon: Moon },
  { id: 'auto', label: msg('Tự động theo giờ'), icon: Clock },
];

const optionClass = (active: boolean) =>
  `flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl border text-xs font-semibold transition-colors ${
    active ? 'border-stone-800 bg-stone-900 text-amber-50' : 'border-stone-300 text-stone-700 hover:bg-stone-50'
  }`;

const timeInputClass =
  'px-2.5 py-1.5 border border-stone-300 rounded-lg outline-none focus:border-stone-800 focus:ring-1 focus:ring-stone-800 text-stone-900 bg-white font-mono';

// Cài đặt người dùng: chỉ thiết lập lõi của hệ thống (giao diện, ngôn ngữ), lưu theo tài khoản
export const PreferencesModal: React.FC<PreferencesModalProps> = ({ isOpen, onClose }) => {
  const { preferences, theme, update } = usePreferences();
  const { t } = useI18n();
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl animate-scaleUp overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="p-5 border-b border-stone-200 flex items-center justify-between bg-panel">
          <div className="flex items-center gap-2">
            <Settings className="w-4 h-4 text-stone-800" />
            <h3 className="text-sm font-bold text-stone-900">{t('Cài đặt')}</h3>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-stone-200 flex items-center justify-center text-stone-500" aria-label={t('Đóng')}>
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-6 text-xs">
          <section className="space-y-3">
            <div className="flex items-center gap-2 font-semibold text-stone-800">
              <Monitor className="w-4 h-4" /> {t('Giao diện')}
            </div>
            <div className="flex gap-2" role="radiogroup" aria-label={t('Giao diện')}>
              {THEME_OPTIONS.map(opt => {
                const Icon = opt.icon;
                const active = preferences.themeMode === opt.id;
                return (
                  <button key={opt.id} role="radio" aria-checked={active} onClick={() => update({ themeMode: opt.id })} className={optionClass(active)}>
                    <Icon className="w-3.5 h-3.5" /> {t(opt.label)}
                  </button>
                );
              })}
            </div>
            {preferences.themeMode === 'auto' && (
              <div className="p-3 rounded-xl border border-stone-200 bg-panel space-y-2">
                <div className="flex flex-wrap items-center gap-2 text-stone-700">
                  <span>{t('Giao diện tối từ')}</span>
                  <input type="time" value={preferences.darkFrom} onChange={e => e.target.value && update({ darkFrom: e.target.value })}
                    className={timeInputClass} aria-label={t('Giờ bắt đầu giao diện tối')} />
                  <span>{t('đến')}</span>
                  <input type="time" value={preferences.darkTo} onChange={e => e.target.value && update({ darkTo: e.target.value })}
                    className={timeInputClass} aria-label={t('Giờ kết thúc giao diện tối')} />
                </div>
                <p className="text-stone-500">
                  {t('Hiện đang dùng giao diện {theme}.', { theme: theme === 'dark' ? t('tối') : t('sáng') })}
                </p>
              </div>
            )}
          </section>

          <section className="space-y-3 pt-5 border-t border-stone-200">
            <div className="flex items-center gap-2 font-semibold text-stone-800">
              <Languages className="w-4 h-4" /> {t('Ngôn ngữ')}
            </div>
            <div className="flex gap-2" role="radiogroup" aria-label={t('Ngôn ngữ')}>
              {LANGUAGES.map(lang => {
                const active = preferences.language === lang.id;
                return (
                  <button key={lang.id} role="radio" aria-checked={active} onClick={() => update({ language: lang.id })} className={optionClass(active)}>
                    {lang.label}
                  </button>
                );
              })}
            </div>
            <p className="text-stone-500">
              {t('Áp dụng cho giao diện và câu trả lời của trợ lý. Tên và thông số sản phẩm giữ nguyên như trên sàn.')}
            </p>
          </section>

          <p className="pt-4 border-t border-stone-200 text-stone-500">
            {t('Cài đặt được lưu theo tài khoản và áp dụng trên mọi thiết bị.')}
          </p>
        </div>
      </div>
    </div>
  );
};
