import React, { useState } from 'react';
import { 
  Building2, 
  ChevronDown, 
  ShieldCheck, 
  User, 
  ExternalLink,
  Download,
  Share2,
  Check
} from 'lucide-react';
import { NavigationTab } from '../types.ts';

interface HeaderProps {
  currentTab: NavigationTab;
  onTabChange: (tab: NavigationTab) => void;
  onExportDossier?: () => void;
  user: { name: string; email: string; role: string; avatar: string } | null;
  onOpenAuth: () => void;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  onTabChange,
  onExportDossier,
  user,
  onOpenAuth,
  onLogout,
}) => {
  const [selectedOrg, setSelectedOrg] = useState('Mua sắm Cá nhân & Thiết bị Công nghệ');
  const [showOrgDropdown, setShowOrgDropdown] = useState(false);
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [copied, setCopied] = useState(false);

  const orgs = [
    'Mua sắm Cá nhân & Thiết bị Công nghệ',
    'Dự toán Thiết bị Văn phòng & Studio',
    'Gia đình & Đồ gia dụng thông minh'
  ];

  const getTabTitle = (tab: NavigationTab) => {
    switch (tab) {
      case 'dashboard':
        return 'Tổng quan & Bảng điều khiển';
      case 'search':
        return 'Tra cứu có căn cứ';
      case 'compare':
        return 'Thiết lập dự thảo quyết định mua sắm';
      case 'audit':
        return 'Không gian rà soát thông số & Đánh giá rủi ro';
      case 'saved':
        return 'Kho lưu trữ quyết định & Deal theo dõi';
      case 'settings':
        return 'Cài đặt nguồn dữ liệu & Tiêu chí';
      default:
        return '';
    }
  };

  const handleShare = () => {
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <header className="h-14 shrink-0 bg-white border-b border-stone-200/90 px-6 flex items-center justify-between z-20">
      {/* Left: Organization / Context selector (like video) */}
      <div className="flex items-center gap-4">
        <div className="relative">
          <button
            onClick={() => setShowOrgDropdown(!showOrgDropdown)}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-stone-800 bg-[#f8f7f4] hover:bg-stone-200/60 rounded-lg border border-stone-200 transition-colors"
          >
            <Building2 className="w-3.5 h-3.5 text-stone-500" />
            <span className="font-semibold">{selectedOrg}</span>
            <ChevronDown className="w-3.5 h-3.5 text-stone-400 ml-1" />
          </button>

          {showOrgDropdown && (
            <div className="absolute left-0 mt-1 w-72 bg-white rounded-xl shadow-lg border border-stone-200 py-1.5 z-50">
              <div className="px-3 py-1.5 text-[11px] font-semibold text-stone-400 uppercase tracking-wider">
                Chọn không gian mua sắm
              </div>
              {orgs.map((org) => (
                <button
                  key={org}
                  onClick={() => {
                    setSelectedOrg(org);
                    setShowOrgDropdown(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-xs transition-colors flex items-center justify-between ${
                    selectedOrg === org
                      ? 'bg-amber-50/80 text-amber-900 font-medium'
                      : 'text-stone-700 hover:bg-stone-50'
                  }`}
                >
                  <span>{org}</span>
                  {selectedOrg === org && <Check className="w-3.5 h-3.5 text-amber-700" />}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="h-4 w-[1px] bg-stone-300 hidden sm:block" />

        <div className="hidden sm:flex items-center gap-2 text-xs text-stone-500">
          <span className="font-medium text-stone-800">{getTabTitle(currentTab)}</span>
        </div>
      </div>

      {/* Right: Sources scope, Export button & User profile badge (like video) */}
      <div className="flex items-center gap-3">
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium text-emerald-800 bg-emerald-50 rounded-md border border-emerald-200/70">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>Nguồn: Sàn chính hãng & AASP</span>
        </div>

        {currentTab === 'compare' && onExportDossier && (
          <button
            onClick={onExportDossier}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-stone-800 bg-[#f6f5f1] hover:bg-stone-200 border border-stone-300 rounded-lg transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Xuất DOCX</span>
          </button>
        )}

        <button
          onClick={handleShare}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-stone-700 hover:bg-stone-100 border border-stone-200 rounded-lg transition-colors"
          title="Chia sẻ hồ sơ"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Share2 className="w-3.5 h-3.5" />}
          <span className="hidden sm:inline">{copied ? 'Đã sao chép' : 'Chia sẻ'}</span>
        </button>

        {/* User Profile Badge or Login Button */}
        {user ? (
          <div className="relative">
            <button
              onClick={() => setShowUserDropdown(!showUserDropdown)}
              className="flex items-center gap-2.5 pl-2 border-l border-stone-200 hover:opacity-80 transition-opacity"
            >
              <div className="w-8 h-8 rounded-full bg-stone-800 text-stone-100 flex items-center justify-center font-medium text-xs shadow-xs">
                {user.avatar}
              </div>
              <div className="hidden lg:flex flex-col text-left">
                <span className="text-xs font-semibold text-stone-800 leading-tight flex items-center gap-1">
                  {user.name}
                  <ChevronDown className="w-3 h-3 text-stone-400" />
                </span>
                <span className="text-[10px] text-stone-500">{user.role}</span>
              </div>
            </button>

            {showUserDropdown && (
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-stone-200 py-1.5 z-50 animate-scaleUp">
                <div className="px-3 py-2 border-b border-stone-100">
                  <div className="text-xs font-bold text-stone-900">{user.name}</div>
                  <div className="text-[11px] text-stone-500 truncate">{user.email}</div>
                </div>
                <button
                  onClick={() => {
                    setShowUserDropdown(false);
                    onOpenAuth();
                  }}
                  className="w-full text-left px-3 py-2 text-xs text-stone-700 hover:bg-stone-50 flex items-center gap-2"
                >
                  <User className="w-3.5 h-3.5 text-stone-500" />
                  <span>Đổi tài khoản khác</span>
                </button>
                <button
                  onClick={() => {
                    setShowUserDropdown(false);
                    onLogout();
                  }}
                  className="w-full text-left px-3 py-2 text-xs text-red-600 hover:bg-red-50 flex items-center gap-2 border-t border-stone-100"
                >
                  <span>Đăng xuất</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={onOpenAuth}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-stone-900 text-amber-50 rounded-lg text-xs font-semibold hover:bg-stone-800 transition-colors shadow-xs"
          >
            <User className="w-3.5 h-3.5" />
            <span>Đăng nhập</span>
          </button>
        )}
      </div>
    </header>
  );
};
