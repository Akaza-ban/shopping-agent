import React, { useEffect, useRef, useState } from 'react';
import { ChevronDown, LogOut, Moon, Store, Sun, UserRound } from 'lucide-react';
import { NavigationTab } from '../types.ts';
import { useAuth } from '../hooks/useAuth.tsx';
import { usePreferences } from '../hooks/usePreferences.tsx';
import { msg, useI18n } from '../i18n/index.tsx';

interface HeaderProps {
  currentTab: NavigationTab;
  enabledPlatformCount: number;
  isAdmin: boolean;
  onOpenSettings: () => void; // cài đặt nguồn dữ liệu (quản trị viên)
  onOpenAccount: () => void;
}

const TAB_TITLES: Record<NavigationTab, string> = {
  dashboard: msg('Tổng quan'),
  search: msg('Tư vấn mua sắm'),
  policy: msg('Tra cứu bảo hành & đổi trả'),
  saved: msg('Sản phẩm đã lưu'),
  alerts: msg('Theo dõi giá'),
  activity: msg('Lịch sử hoạt động'),
  feedback: msg('Góp ý & hỗ trợ'),
};

const initials = (name: string) =>
  name.trim().split(/\s+/).slice(-2).map(w => w[0]?.toUpperCase() ?? '').join('') || '?';

// Avatar + menu tài khoản (thông tin, đăng xuất)
const UserMenu: React.FC<{ onOpenAccount: () => void }> = ({ onOpenAccount }) => {
  const { user, logout } = useAuth();
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', close);
    document.addEventListener('keydown', esc);
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc); };
  }, [open]);

  if (!user) return null;
  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-lg hover:bg-stone-100 transition-colors"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <span className="w-7 h-7 rounded-full bg-amber-100 text-amber-900 text-[11px] font-bold flex items-center justify-center">
          {initials(user.displayName)}
        </span>
        <span className="hidden sm:block max-w-32 truncate text-xs font-semibold text-stone-800">{user.displayName}</span>
        <ChevronDown className="w-3.5 h-3.5 text-stone-500" />
      </button>

      {open && (
        <div role="menu" className="absolute right-0 mt-2 w-60 bg-white border border-stone-200 rounded-xl shadow-lg py-1.5 z-40 animate-fadeIn">
          <div className="px-3.5 py-2 border-b border-stone-100">
            <div className="text-xs font-semibold text-stone-900 truncate">{user.displayName}</div>
            <div className="text-[11px] text-stone-500 truncate">{user.email}</div>
            {user.role === 'admin' && <div className="mt-1 text-[10px] font-semibold text-amber-800">{t('Quản trị viên')}</div>}
          </div>
          <button
            role="menuitem"
            onClick={() => { setOpen(false); onOpenAccount(); }}
            className="w-full flex items-center gap-2 px-3.5 py-2 text-xs text-stone-700 hover:bg-stone-50"
          >
            <UserRound className="w-3.5 h-3.5" /> {t('Tài khoản & mật khẩu')}
          </button>
          <button
            role="menuitem"
            onClick={() => { setOpen(false); void logout(); }}
            className="w-full flex items-center gap-2 px-3.5 py-2 text-xs text-red-700 hover:bg-red-50"
          >
            <LogOut className="w-3.5 h-3.5" /> {t('Đăng xuất')}
          </button>
        </div>
      )}
    </div>
  );
};

export const Header: React.FC<HeaderProps> = ({ currentTab, enabledPlatformCount, isAdmin, onOpenSettings, onOpenAccount }) => {
  const { theme, toggleTheme } = usePreferences();
  const { t } = useI18n();
  const themeLabel = theme === 'dark' ? t('Chuyển sang giao diện sáng') : t('Chuyển sang giao diện tối');
  return (
    <header className="h-14 shrink-0 bg-white border-b border-stone-200/90 px-6 flex items-center justify-between z-20">
      <span className="text-sm font-semibold text-stone-800">{t(TAB_TITLES[currentTab])}</span>

      <div className="flex items-center gap-2">
        {/* Nguồn dữ liệu là cấu hình hệ thống: chỉ quản trị viên thấy */}
        {isAdmin && (
          <button
            onClick={onOpenSettings}
            className="flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium text-emerald-800 bg-emerald-50 hover:bg-emerald-100 rounded-md border border-emerald-200/70 transition-colors"
            title={t('Cài đặt nguồn dữ liệu')}
          >
            <Store className="w-3.5 h-3.5 text-emerald-600" />
            <span>{t('Nguồn dữ liệu: {count} nền tảng', { count: enabledPlatformCount })}</span>
          </button>
        )}
        <button
          onClick={toggleTheme}
          className="w-8 h-8 rounded-md flex items-center justify-center text-stone-600 hover:text-stone-900 hover:bg-stone-100 border border-stone-200 transition-colors"
          title={themeLabel}
          aria-label={themeLabel}
        >
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
        <div className="w-px h-6 bg-stone-200 mx-1" />
        <UserMenu onOpenAccount={onOpenAccount} />
      </div>
    </header>
  );
};
