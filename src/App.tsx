import React, { useState } from 'react';
import { NavigationTab } from './types.ts';
import { Sidebar } from './components/Sidebar.tsx';
import { Header } from './components/Header.tsx';
import { DashboardView } from './components/DashboardView.tsx';
import { SearchAssistantView } from './components/SearchAssistantView.tsx';
import { DossierCompareView } from './components/DossierCompareView.tsx';
import { AuditReviewView } from './components/AuditReviewView.tsx';
import { SavedLibraryView } from './components/SavedLibraryView.tsx';
import { SettingsModal } from './components/SettingsModal.tsx';
import { AuthView } from './components/AuthView.tsx';

export default function App() {
  const [currentTab, setCurrentTab] = useState<NavigationTab>('dashboard');
  const [isDarkMode, setIsDarkMode] = useState<boolean>(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [isAuthViewOpen, setIsAuthViewOpen] = useState<boolean>(false);

  // User state
  const [user, setUser] = useState<{
    name: string;
    email: string;
    role: string;
    avatar: string;
  } | null>({
    name: 'Nguyễn Minh Trí',
    email: 'vuminhtri1104@gmail.com',
    role: 'Chuyên viên mua sắm',
    avatar: 'NT'
  });

  const toggleDarkMode = () => {
    setIsDarkMode(!isDarkMode);
  };

  const handleLoginSuccess = (loggedInUser: { name: string; email: string; role: string; avatar: string }) => {
    setUser(loggedInUser);
    setIsAuthViewOpen(false);
  };

  const handleLogout = () => {
    setUser(null);
    setIsAuthViewOpen(true);
  };

  const handleExportDossier = () => {
    const el = document.createElement('a');
    const content = `QUYẾT ĐỊNH MUA SẮM THÔNG MINH - SHOPPING AI AGENT\nNgày: 24/10/2026\nSản phẩm đề xuất: Apple MacBook Air 13 M3 16GB/512GB\nGiá tốt nhất: 28.490.000 ₫\nNguồn: Shopee Mall & Tiki Official`;
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    el.href = URL.createObjectURL(blob);
    el.download = `Ho_so_mua_sam_245_QD_SHOPPING.txt`;
    document.body.appendChild(el);
    el.click();
    document.body.removeChild(el);
  };

  return (
    <div className={`min-h-screen flex text-stone-900 ${isDarkMode ? 'dark bg-stone-950 text-stone-100' : 'bg-[#faf9f5]'}`}>
      {/* Slim Icon Navigation Rail (Inspired by Legolas AI) */}
      <Sidebar
        currentTab={currentTab}
        onTabChange={setCurrentTab}
        isDarkMode={isDarkMode}
        onToggleDarkMode={toggleDarkMode}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenAuth={() => setIsAuthViewOpen(true)}
      />

      {/* Main Workspace Frame */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        {/* Top Header with Context / Organization selector & User badge */}
        <Header
          currentTab={currentTab}
          onTabChange={setCurrentTab}
          onExportDossier={handleExportDossier}
          user={user}
          onOpenAuth={() => setIsAuthViewOpen(true)}
          onLogout={handleLogout}
        />

        {/* Viewport Router */}
        <main className="flex-1 overflow-y-auto">
          {currentTab === 'dashboard' && (
            <DashboardView
              onNavigate={setCurrentTab}
            />
          )}

          {currentTab === 'search' && (
            <SearchAssistantView
              onOpenDossier={() => setCurrentTab('compare')}
            />
          )}

          {currentTab === 'compare' && (
            <DossierCompareView
              onOpenAudit={() => setCurrentTab('audit')}
            />
          )}

          {currentTab === 'audit' && (
            <AuditReviewView />
          )}

          {currentTab === 'saved' && (
            <SavedLibraryView
              onNavigate={setCurrentTab}
            />
          )}
        </main>
      </div>

      {/* Login & Register Fullscreen Modal View (matching video 00:13) */}
      {isAuthViewOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <AuthView
            onLoginSuccess={handleLoginSuccess}
            onCancel={() => setIsAuthViewOpen(false)}
          />
        </div>
      )}

      {/* Global Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  );
}
