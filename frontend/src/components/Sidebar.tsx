import React from 'react';
import {
  LayoutGrid,
  MessageSquareText,
  ShieldCheck,
  Bookmark,
  History,
  Settings,
  MessageSquarePlus,
  LifeBuoy,
  BellRing,
  PanelLeftClose,
  PanelLeftOpen,
  Database,
  Inbox
} from 'lucide-react';
import { NavigationTab } from '../types.ts';
import { BrandLogo } from './BrandLogo.tsx';
import { usePersistentState } from '../hooks/usePersistentState.ts';
import { msg, useI18n } from '../i18n/index.tsx';

export type HelpKind = 'feedback' | 'support';

interface SidebarProps {
  currentTab: NavigationTab;
  alertCount: number; // số sản phẩm đã đạt giá mong muốn
  feedbackCount: number; // quản trị viên: số góp ý / yêu cầu hỗ trợ mới
  onTabChange: (tab: NavigationTab) => void;
  isAdmin: boolean;
  onOpenPreferences: () => void; // Cài đặt người dùng: giao diện, ngôn ngữ
  onOpenSettings: () => void;    // Cài đặt nguồn dữ liệu: chỉ quản trị viên
  onOpenHelp: (kind: HelpKind) => void;
}

const NAV_ITEMS: { id: NavigationTab; label: string; icon: React.ElementType }[] = [
  { id: 'dashboard', label: msg('Tổng quan'), icon: LayoutGrid },
  { id: 'search', label: msg('Tư vấn mua sắm'), icon: MessageSquareText },
  { id: 'policy', label: msg('Tra cứu bảo hành & đổi trả'), icon: ShieldCheck },
  { id: 'saved', label: msg('Sản phẩm đã lưu'), icon: Bookmark },
  { id: 'alerts', label: msg('Theo dõi giá'), icon: BellRing },
  { id: 'activity', label: msg('Lịch sử hoạt động'), icon: History },
];

// Nút của thanh bên: thu gọn thì chỉ còn icon, tên hiện dưới dạng tooltip
const SidebarButton: React.FC<{
  icon: React.ElementType;
  label: string;
  collapsed: boolean;
  active?: boolean;
  badge?: number;
  bold?: boolean;
  onClick: () => void;
}> = ({ icon: Icon, label, collapsed, active, badge, bold, onClick }) => (
  <button
    onClick={onClick}
    title={collapsed ? label : undefined}
    className={`relative group w-full flex items-center gap-3 rounded-lg transition-colors ${
      collapsed ? 'justify-center h-11' : 'px-3 h-11'
    } ${
      active
        ? 'bg-amber-50 text-amber-900 ring-1 ring-amber-200'
        : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'
    }`}
  >
    <Icon className="w-5 h-5 shrink-0 stroke-[1.8]" />
    {!collapsed && (
      <span className={`flex-1 text-left text-[13px] truncate ${active || bold ? 'font-semibold' : 'font-medium'}`}>{label}</span>
    )}
    {!!badge && (
      <span
        className={`min-w-5 h-5 px-1.5 rounded-full bg-amber-600 text-white text-[10px] font-bold flex items-center justify-center ${
          collapsed ? 'absolute top-0.5 right-1.5 min-w-4 h-4 px-1 text-[9px]' : ''
        }`}
      >
        {badge}
      </span>
    )}
    {collapsed && (
      <span className="absolute left-full ml-3 px-2.5 py-1 text-xs font-medium text-white bg-stone-800 rounded-md shadow-lg opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity whitespace-nowrap z-50">
        {label}
      </span>
    )}
  </button>
);

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  alertCount,
  feedbackCount,
  onTabChange,
  isAdmin,
  onOpenPreferences,
  onOpenSettings,
  onOpenHelp,
}) => {
  const { t } = useI18n();
  const [collapsed, setCollapsed] = usePersistentState<boolean>('shopping-ai.sidebar-collapsed', false);
  const ToggleIcon = collapsed ? PanelLeftOpen : PanelLeftClose;

  return (
    <aside
      className={`${collapsed ? 'w-[72px]' : 'w-64'} shrink-0 h-screen sticky top-0 flex flex-col bg-white text-stone-700 border-r border-stone-200 z-30 select-none transition-[width] duration-200`}
    >
      {/* Logo + tên hệ thống + nút thu gọn */}
      <div className={`h-16 shrink-0 flex items-center border-b border-stone-200 ${collapsed ? 'flex-col justify-center gap-1 px-2 h-auto py-3' : 'justify-between px-4'}`}>
        <button onClick={() => onTabChange('dashboard')} className="flex items-center gap-2.5 min-w-0" title="Shopping AI">
          <BrandLogo size={32} />
          {!collapsed && <span className="text-[15px] font-bold text-stone-900 tracking-tight truncate">Shopping AI</span>}
        </button>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-8 h-8 shrink-0 rounded-md flex items-center justify-center text-stone-500 hover:text-stone-900 hover:bg-stone-100 transition-colors"
          title={collapsed ? t('Mở rộng thanh bên') : t('Thu gọn thanh bên')}
        >
          <ToggleIcon className="w-4 h-4" />
        </button>
      </div>

      {/* Chức năng chính */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1.5">
        {NAV_ITEMS.map(item => (
          <SidebarButton
            key={item.id}
            icon={item.icon}
            label={t(item.label)}
            collapsed={collapsed}
            active={currentTab === item.id}
            badge={item.id === 'alerts' ? alertCount : undefined}
            onClick={() => onTabChange(item.id)}
          />
        ))}
        {isAdmin && (
          <SidebarButton
            icon={Inbox}
            label={t('Góp ý & hỗ trợ')}
            collapsed={collapsed}
            active={currentTab === 'feedback'}
            badge={feedbackCount}
            onClick={() => onTabChange('feedback')}
          />
        )}
      </nav>

      {/* Trợ giúp & hỗ trợ */}
      <div className="shrink-0 border-t border-stone-200 px-3 pt-4 pb-3 space-y-1">
        {!collapsed && (
          <div className="px-3 pb-2 text-[10px] font-bold text-stone-500 uppercase tracking-wider">{t('Trợ giúp & hỗ trợ')}</div>
        )}
        <SidebarButton icon={MessageSquarePlus} label={t('Gửi góp ý')} collapsed={collapsed} bold onClick={() => onOpenHelp('feedback')} />
        <SidebarButton icon={LifeBuoy} label={t('Yêu cầu hỗ trợ')} collapsed={collapsed} bold onClick={() => onOpenHelp('support')} />
        <SidebarButton icon={Settings} label={t('Cài đặt')} collapsed={collapsed} onClick={onOpenPreferences} />
        {isAdmin && (
          <SidebarButton icon={Database} label={t('Cài đặt nguồn dữ liệu')} collapsed={collapsed} onClick={onOpenSettings} />
        )}
      </div>

      {/* Khẩu hiệu */}
      {!collapsed && (
        <div className="shrink-0 border-t border-stone-200 p-3">
          <div className="px-3 py-3 rounded-lg border border-stone-200 bg-panel text-[11px] leading-relaxed text-stone-600">
            {t('Tìm kiếm có căn cứ.')}<br />
            {t('So sánh minh bạch.')}<br />
            {t('Đề xuất có trách nhiệm.')}
          </div>
        </div>
      )}
    </aside>
  );
};
