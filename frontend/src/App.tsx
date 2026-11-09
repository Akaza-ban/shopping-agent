import { useEffect, useState } from 'react';
import { ActivityItem, ChatRequest, NavigationTab, PlatformPolicy, PolicyRequest, PriceAlert, ProductItem, SavedProduct, SearchRecord } from './types.ts';
import { HelpKind, Sidebar } from './components/Sidebar.tsx';
import { HelpRequestModal } from './components/HelpRequestModal.tsx';
import { Header } from './components/Header.tsx';
import { DashboardView } from './components/DashboardView.tsx';
import { SearchAssistantView } from './components/SearchAssistantView.tsx';
import { PolicyLookupView } from './components/policy/PolicyLookupView.tsx';
import { SavedProductsView } from './components/SavedProductsView.tsx';
import { ActivityLogView } from './components/ActivityLogView.tsx';
import { SettingsModal } from './components/SettingsModal.tsx';
import { PriceAlertsView } from './components/PriceAlertsView.tsx';
import { TrackPriceModal } from './components/TrackPriceModal.tsx';
import { PLATFORMS, getPlatformName, setPolicyCache } from './services/shoppingService.ts';
import { listFeedback, listPolicies, submitFeedback } from './services/agentApi.ts';
import { FeedbackInboxView } from './components/FeedbackInboxView.tsx';
import { Loader2 } from 'lucide-react';
import { AuthProvider, useAuth } from './hooks/useAuth.tsx';
import { PreferencesProvider, usePreferences } from './hooks/usePreferences.tsx';
import { I18nProvider, currentLocale, formatVnd, t, useI18n } from './i18n/index.tsx';
import { PreferencesModal } from './components/PreferencesModal.tsx';
import { useSyncedState } from './hooks/useSyncedState.ts';
import { AuthView } from './components/AuthView.tsx';
import { ResetPasswordView } from './components/ResetPasswordView.tsx';
import { AccountModal } from './components/AccountModal.tsx';
import { usePriceAlerts } from './hooks/usePriceAlerts.ts';

const MAX_ACTIVITIES = 200;
const MAX_HISTORY = 20;

const formatNow = () =>
  new Date().toLocaleString(currentLocale(), { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' });

export default function App() {
  return (
    <AuthProvider>
      <PreferencesProvider>
        <LocalizedApp />
      </PreferencesProvider>
    </AuthProvider>
  );
}

function LocalizedApp() {
  const { preferences } = usePreferences();
  return (
    <I18nProvider language={preferences.language}>
      <AuthGate />
    </I18nProvider>
  );
}

// Chưa đăng nhập -> màn đăng nhập/đăng ký; đã đăng nhập -> ứng dụng, dựng lại theo từng tài khoản
function AuthGate() {
  const { status, user, logout } = useAuth();
  const { t } = useI18n();
  // Mở từ link trong email đặt lại mật khẩu (?reset_token=...)
  const [resetToken, setResetToken] = useState(() => new URLSearchParams(window.location.search).get('reset_token'));
  const [notice, setNotice] = useState('');

  const leaveReset = () => {
    const url = new URL(window.location.href);
    url.searchParams.delete('reset_token');
    window.history.replaceState(null, '', url.pathname + url.search + url.hash);
    setResetToken(null);
  };

  if (resetToken) {
    return (
      <ResetPasswordView
        token={resetToken}
        onCancel={leaveReset}
        onDone={() => {
          leaveReset();
          setNotice(t('Đã đặt mật khẩu mới. Vui lòng đăng nhập lại.'));
          // Server đã thu hồi mọi phiên của tài khoản -> đăng xuất cả phiên trên trình duyệt này
          if (status === 'authenticated') void logout();
        }}
      />
    );
  }
  if (status === 'loading') {
    return (
      <div className="min-h-screen bg-canvas flex items-center justify-center text-stone-500 text-sm gap-2">
        <Loader2 className="w-4 h-4 animate-spin" /> {t('Đang kiểm tra phiên đăng nhập...')}
      </div>
    );
  }
  if (status === 'anonymous' || !user) return <AuthView notice={notice} />;
  return <ShoppingApp key={user.id} userId={user.id} isAdmin={user.role === 'admin'} />;
}

function ShoppingApp({ userId, isAdmin }: { userId: string; isAdmin: boolean }) {
  useI18n(); // dựng lại khi đổi ngôn ngữ
  const [currentTab, setCurrentTab] = useState<NavigationTab>('dashboard');
  // Cài đặt nguồn dữ liệu: cấu hình hệ thống, chỉ quản trị viên
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  // Cài đặt người dùng: giao diện, ngôn ngữ
  const [isPreferencesOpen, setIsPreferencesOpen] = useState<boolean>(false);
  const [isAccountOpen, setIsAccountOpen] = useState<boolean>(false);
  const [helpKind, setHelpKind] = useState<HelpKind | null>(null);
  const [enabledPlatformIds, setEnabledPlatformIds] = useState<string[]>(PLATFORMS.map(p => p.id));
  const [chatRequest, setChatRequest] = useState<ChatRequest | null>(null);
  // Chính sách đổi trả, bảo hành từ máy chủ (màn Tra cứu chính sách, bảng so sánh, sản phẩm đã lưu)
  const [policies, setPolicies] = useState<PlatformPolicy[]>([]);
  const [policyRequest, setPolicyRequest] = useState<PolicyRequest | null>(null);
  useEffect(() => {
    listPolicies()
      .then(list => {
        setPolicyCache(list);
        setPolicies(list);
      })
      .catch(() => undefined);
  }, []);
  // Quản trị viên: số góp ý / yêu cầu hỗ trợ mới (huy hiệu trên thanh bên), làm mới mỗi phút
  const [newFeedbackCount, setNewFeedbackCount] = useState(0);
  useEffect(() => {
    if (!isAdmin) return;
    const refresh = () => listFeedback('new').then(res => setNewFeedbackCount(res.counts.new)).catch(() => undefined);
    void refresh();
    const timer = window.setInterval(refresh, 60_000);
    return () => window.clearInterval(timer);
  }, [isAdmin]);
  // Dữ liệu cá nhân lưu theo tài khoản (đồng bộ với máy chủ, dùng được trên nhiều thiết bị)
  const [history, setHistory] = useSyncedState<SearchRecord[]>(userId, 'search-history', []);
  const [saved, setSaved] = useSyncedState<SavedProduct[]>(userId, 'saved-products', []);
  const [activities, setActivities] = useSyncedState<ActivityItem[]>(userId, 'activities', []);

  const savedIds = saved.map(s => s.product.id);
  const [trackingProduct, setTrackingProduct] = useState<ProductItem | null>(null);

  const logActivity = (item: Omit<ActivityItem, 'id' | 'timestamp'>) => {
    const entry: ActivityItem = {
      ...item,
      id: `act-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      timestamp: new Date().toISOString()
    };
    setActivities(prev => [entry, ...prev].slice(0, MAX_ACTIVITIES));
  };

  const handleToggleSave = (product: ProductItem, sourceQuery?: string) => {
    if (savedIds.includes(product.id)) {
      setSaved(prev => prev.filter(s => s.product.id !== product.id));
      logActivity({ type: 'unsave', title: t('Bỏ lưu: {name}', { name: product.name }), targetTab: 'saved' });
      return;
    }
    const query = sourceQuery || history.find(r => r.products.some(p => p.id === product.id))?.query || '';
    setSaved(prev => [{ product, sourceQuery: query, savedAt: formatNow() }, ...prev]);
    logActivity({
      type: 'save',
      title: t('Lưu sản phẩm: {name}', { name: product.name }),
      detail: `${formatVnd(product.currentPrice)} · ${getPlatformName(product.platformId)}`,
      targetTab: 'saved'
    });
  };

  const handleResults = (query: string, products: ProductItem[]) => {
    setHistory(prev => [{ id: `search-${Date.now()}`, query, timestamp: formatNow(), products }, ...prev].slice(0, MAX_HISTORY));
    logActivity({
      type: 'search',
      title: t('Tìm kiếm: "{query}"', { query }),
      detail: products[0]
        ? t('Đề xuất {count} sản phẩm · Hạng 1: {name}', { count: products.length, name: products[0].name })
        : t('Không có sản phẩm phù hợp'),
      query,
      products
    });
  };

  // Nhờ agent dùng tool so sánh trong khung chat
  const askAgentToCompare = (products: ProductItem[]) => {
    setChatRequest({ id: `req-${Date.now()}`, kind: 'compare', products });
    setCurrentTab('search');
    logActivity({
      type: 'compare',
      title: t('Nhờ AI so sánh {count} sản phẩm đã lưu', { count: products.length }),
      detail: products.map(p => p.brand).join(' · '),
      query: t('So sánh {names}', { names: products.map(p => p.brand).join(', ') }),
      products
    });
  };

  // Hiển thị lại một kết quả cũ trong khung chat
  const reopenInChat = (query: string, products: ProductItem[]) => {
    setChatRequest({ id: `req-${Date.now()}`, kind: 'restore', query, products });
    setCurrentTab('search');
  };

  const handlePolicyLookup = (query: string, platformIds: string[]) =>
    logActivity({
      type: 'policy',
      title: t('Tra cứu chính sách: "{query}"', { query }),
      detail: platformIds.map(getPlatformName).join(', '),
      targetTab: 'policy'
    });

  const handleChangePlatforms = (ids: string[]) => {
    const added = ids.filter(id => !enabledPlatformIds.includes(id));
    const removed = enabledPlatformIds.filter(id => !ids.includes(id));
    added.forEach(id => logActivity({ type: 'settings', title: t('Bật nguồn dữ liệu: {name}', { name: getPlatformName(id) }) }));
    removed.forEach(id => logActivity({ type: 'settings', title: t('Tắt nguồn dữ liệu: {name}', { name: getPlatformName(id) }) }));
    setEnabledPlatformIds(ids);
  };

  // Theo dõi giá: dữ liệu ở backend (SQLite), kiểm tra giá thật định kỳ
  const priceAlerts = usePriceAlerts((alert: PriceAlert) =>
    logActivity({
      type: 'alert',
      title: t('Đạt giá mong muốn: {name}', { name: alert.productName }),
      detail: t('{price} (mục tiêu {target}) · {platform}', { price: formatVnd(alert.lastPrice), target: formatVnd(alert.targetPrice), platform: alert.platformName }),
      targetTab: 'alerts'
    })
  );
  const trackedIds = priceAlerts.alerts.map(a => a.productId);
  const triggeredCount = priceAlerts.alerts.filter(a => a.status === 'triggered').length;

  const handleCreateAlert = async (product: ProductItem, targetPrice: number) => {
    await priceAlerts.create(product, targetPrice);
    logActivity({
      type: 'alert',
      title: t('Theo dõi giá: {name}', { name: product.name }),
      detail: t('Báo khi giá ≤ {target} (hiện tại {price})', { target: formatVnd(targetPrice), price: formatVnd(product.currentPrice) }),
      targetTab: 'alerts'
    });
  };

  // Gửi cho quản trị viên; gửi được mới ghi vào Lịch sử hoạt động (lỗi để form hiện thông báo)
  const handleHelpSubmit = async (kind: HelpKind, topic: string, content: string, contact: string) => {
    await submitFeedback(kind, topic, content, contact);
    const text = `[${t(topic)}] ${content}`;
    logActivity({
      type: 'support',
      title: kind === 'feedback' ? t('Gửi góp ý') : t('Yêu cầu hỗ trợ'),
      detail: contact ? `${text} · ${t('Liên hệ: {contact}', { contact })}` : text
    });
  };

  return (
    <div className="min-h-screen flex text-stone-900 bg-canvas">
      <Sidebar
        currentTab={currentTab}
        alertCount={triggeredCount}
        feedbackCount={newFeedbackCount}
        onTabChange={setCurrentTab}
        isAdmin={isAdmin}
        onOpenPreferences={() => setIsPreferencesOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenHelp={setHelpKind}
      />

      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        <Header
          currentTab={currentTab}
          enabledPlatformCount={enabledPlatformIds.length}
          isAdmin={isAdmin}
          onOpenSettings={() => setIsSettingsOpen(true)}
          onOpenAccount={() => setIsAccountOpen(true)}
        />

        <main className="flex-1 overflow-y-auto">
          {currentTab === 'dashboard' && (
            <DashboardView
              history={history}
              saved={saved}
              alerts={priceAlerts.alerts}
              enabledPlatformCount={enabledPlatformIds.length}
              onNavigate={setCurrentTab}
              onOpenRecord={record => reopenInChat(record.query, record.products)}
            />
          )}

          {/* Giữ màn chat luôn mount để không mất lịch sử hội thoại khi chuyển tab */}
          <div className={currentTab === 'search' ? '' : 'hidden'}>
            <SearchAssistantView
              userId={userId}
              savedIds={savedIds}
              request={chatRequest}
              onRequestHandled={() => setChatRequest(null)}
              onToggleSave={handleToggleSave}
              trackedIds={trackedIds}
              onTrackPrice={setTrackingProduct}
              onResults={handleResults}
              onOpenPolicy={request => {
                setPolicyRequest(request ?? null);
                setCurrentTab('policy');
              }}
            />
          </div>

          {currentTab === 'policy' && (
            <PolicyLookupView
              enabledPlatformIds={enabledPlatformIds}
              policies={policies}
              onLookup={handlePolicyLookup}
              request={policyRequest}
              onRequestHandled={() => setPolicyRequest(null)}
            />
          )}

          {currentTab === 'saved' && (
            <SavedProductsView
              saved={saved}
              onRemove={id => {
                const item = saved.find(s => s.product.id === id);
                if (item) handleToggleSave(item.product);
              }}
              onCompare={askAgentToCompare}
              trackedIds={trackedIds}
              onTrackPrice={setTrackingProduct}
              onGoSearch={() => setCurrentTab('search')}
            />
          )}

          {currentTab === 'alerts' && (
            <PriceAlertsView
              alerts={priceAlerts.alerts}
              loadError={priceAlerts.loadError}
              checkingIds={priceAlerts.checkingIds}
              onCheck={priceAlerts.check}
              onDelete={id => void priceAlerts.remove(id)}
              onGoSearch={() => setCurrentTab('search')}
            />
          )}

          {currentTab === 'activity' && (
            <ActivityLogView
              activities={activities}
              onReopenInChat={item => reopenInChat(item.query ?? item.title, item.products ?? [])}
              onNavigate={setCurrentTab}
              onClear={() => setActivities([])}
            />
          )}

          {currentTab === 'feedback' && isAdmin && (
            <FeedbackInboxView onCountsChange={counts => setNewFeedbackCount(counts.new)} />
          )}
        </main>
      </div>

      <TrackPriceModal
        product={trackingProduct}
        existingAlert={trackingProduct ? priceAlerts.alertFor(trackingProduct.id) : undefined}
        onCreate={handleCreateAlert}
        onDelete={priceAlerts.remove}
        onClose={() => setTrackingProduct(null)}
      />

      <HelpRequestModal kind={helpKind} onSubmit={handleHelpSubmit} onClose={() => setHelpKind(null)} />

      <AccountModal isOpen={isAccountOpen} onClose={() => setIsAccountOpen(false)} />

      <PreferencesModal isOpen={isPreferencesOpen} onClose={() => setIsPreferencesOpen(false)} />

      <SettingsModal
        isOpen={isSettingsOpen && isAdmin}
        enabledPlatformIds={enabledPlatformIds}
        onChangePlatforms={handleChangePlatforms}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  );
}
