import React from 'react';
import { 
  LayoutGrid, 
  Search, 
  FileEdit, 
  ShieldCheck, 
  Bookmark, 
  Settings, 
  Moon, 
  Sun, 
  HelpCircle,
  Sparkles,
  User
} from 'lucide-react';
import { NavigationTab } from '../types.ts';
import { BrandLogo } from './BrandLogo.tsx';

interface SidebarProps {
  currentTab: NavigationTab;
  onTabChange: (tab: NavigationTab) => void;
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  onOpenSettings: () => void;
  onOpenAuth: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onTabChange,
  isDarkMode,
  onToggleDarkMode,
  onOpenSettings,
  onOpenAuth,
}) => {
  const navItems = [
    { id: 'dashboard' as NavigationTab, label: 'Tổng quan', icon: LayoutGrid },
    { id: 'search' as NavigationTab, label: 'Tra cứu & Tư vấn', icon: Search },
    { id: 'compare' as NavigationTab, label: 'Thiết lập So sánh & Dự thảo', icon: FileEdit },
    { id: 'audit' as NavigationTab, label: 'Rà soát rủi ro & Đánh giá', icon: ShieldCheck },
    { id: 'saved' as NavigationTab, label: 'Kho lưu trữ & Deal', icon: Bookmark },
  ];

  return (
    <aside className="w-16 shrink-0 h-screen sticky top-0 flex flex-col items-center justify-between py-4 bg-[#f4f2ec] border-r border-stone-200/80 z-30 select-none">
      {/* Top Brand Logo */}
      <div className="flex flex-col items-center gap-6">
        <button 
          onClick={() => onTabChange('dashboard')}
          className="hover:scale-105 transition-transform"
          title="Shopping AI - Trợ lý Mua sắm Thông minh"
        >
          <BrandLogo size={40} />
        </button>

        {/* Navigation Icons Rail */}
        <nav className="flex flex-col items-center gap-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onTabChange(item.id)}
                className={`relative group w-11 h-11 rounded-xl flex items-center justify-center transition-all ${
                  isActive
                    ? 'bg-white text-stone-900 shadow-sm border border-stone-200 font-medium'
                    : 'text-stone-500 hover:text-stone-900 hover:bg-stone-200/60'
                }`}
                title={item.label}
              >
                <Icon className="w-5 h-5 stroke-[1.8]" />
                
                {/* Active Indicator Bar (like video) */}
                {isActive && (
                  <span className="absolute -left-2 top-2.5 bottom-2.5 w-1 bg-stone-900 rounded-r-full" />
                )}

                {/* Floating Tooltip */}
                <span className="absolute left-14 px-2.5 py-1 text-xs font-medium text-white bg-stone-800 rounded-md shadow-lg opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity whitespace-nowrap z-50">
                  {item.label}
                </span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Utility Icons */}
      <div className="flex flex-col items-center gap-2">
        <button
          onClick={onOpenAuth}
          className="w-10 h-10 rounded-xl flex items-center justify-center text-stone-500 hover:text-stone-900 hover:bg-stone-200/60 transition-colors"
          title="Đăng nhập / Đổi tài khoản"
        >
          <User className="w-4 h-4" />
        </button>

        <button
          onClick={onToggleDarkMode}
          className="w-10 h-10 rounded-xl flex items-center justify-center text-stone-500 hover:text-stone-900 hover:bg-stone-200/60 transition-colors"
          title={isDarkMode ? 'Chế độ sáng ấm' : 'Chế độ tối'}
        >
          {isDarkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        <button
          onClick={onOpenSettings}
          className="w-10 h-10 rounded-xl flex items-center justify-center text-stone-500 hover:text-stone-900 hover:bg-stone-200/60 transition-colors"
          title="Cài đặt & Tiêu chí mua sắm"
        >
          <Settings className="w-4 h-4" />
        </button>

        <div className="pt-2 border-t border-stone-300/70 w-8 flex justify-center">
          <div className="w-7 h-7 rounded-full bg-amber-600/10 text-amber-900 text-xs font-semibold flex items-center justify-center" title="Trạng thái hệ thống: Sẵn sàng">
            <Sparkles className="w-3.5 h-3.5 text-amber-700" />
          </div>
        </div>
      </div>
    </aside>
  );
};
