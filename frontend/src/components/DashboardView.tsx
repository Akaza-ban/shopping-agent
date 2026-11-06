import React from 'react';
import { ArrowRight, BellRing, Bookmark, History, MessageSquareText, Search, ShieldCheck, Store, Table2 } from 'lucide-react';
import { NavigationTab, PriceAlert, SavedProduct, SearchRecord } from '../types.ts';
import { getPlatformName } from '../services/shoppingService.ts';
import { currentLocale, t } from '../i18n/index.tsx';
import { useAuth } from '../hooks/useAuth.tsx';

interface DashboardViewProps {
  history: SearchRecord[];
  saved: SavedProduct[];
  alerts: PriceAlert[];
  enabledPlatformCount: number;
  onNavigate: (tab: NavigationTab) => void;
  onOpenRecord: (record: SearchRecord) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  history,
  saved,
  alerts,
  enabledPlatformCount,
  onNavigate,
  onOpenRecord,
}) => {
  const displayName = useAuth().user?.displayName?.trim();
  const quickActions = [
    {
      title: t('Tư vấn mua sắm'),
      description: t('Mô tả nhu cầu bằng ngôn ngữ tự nhiên, AI tìm kiếm trên các sàn, lọc và đề xuất sản phẩm phù hợp.'),
      icon: MessageSquareText,
      tab: 'search' as NavigationTab
    },
    {
      title: t('Tra cứu bảo hành & đổi trả'),
      description: t('So sánh thời hạn, điều kiện đổi trả và cách tiếp nhận bảo hành giữa các sàn, chuỗi bán lẻ.'),
      icon: ShieldCheck,
      tab: 'policy' as NavigationTab
    },
    {
      title: t('Sản phẩm đã lưu'),
      description: t('Xem lại các sản phẩm đã lưu từ đề xuất của AI và nhờ AI so sánh giữa chúng.'),
      icon: Bookmark,
      tab: 'saved' as NavigationTab
    },
    {
      title: t('Lịch sử hoạt động'),
      description: t('Xem lại các lượt tìm kiếm, sản phẩm đã lưu, tra cứu chính sách đã thực hiện.'),
      icon: History,
      tab: 'activity' as NavigationTab
    }
  ];

  const stats = [
    { label: t('Lượt tìm kiếm'), value: history.length, sub: t('Lưu tối đa 20 lượt gần nhất'), icon: Search },
    { label: t('Sản phẩm đã đề xuất'), value: history.reduce((n, r) => n + r.products.length, 0), sub: t('Sau khi lọc & xếp hạng'), icon: Table2 },
    { label: t('Sản phẩm đã lưu'), value: saved.length, sub: t('Lưu theo tài khoản'), icon: Bookmark },
    { label: t('Đang theo dõi giá'), value: alerts.filter(a => a.status === 'watching').length, sub: t('{count} sản phẩm đã đạt giá mong muốn', { count: alerts.filter(a => a.status === 'triggered').length }), icon: BellRing },
    { label: t('Nền tảng nguồn'), value: enabledPlatformCount, sub: t('Đang bật thu thập'), icon: Store },
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-fadeIn">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-stone-900">
          {displayName ? t('Xin chào, {name}', { name: displayName }) : t('Xin chào')}
        </h1>
        <p className="text-sm text-stone-600 mt-1">
          {t('Tổng quan hoạt động tìm kiếm, sản phẩm đã lưu và nguồn dữ liệu của trợ lý mua sắm.')}
        </p>
      </div>

      <div>
        <div className="text-xs font-semibold uppercase tracking-wider text-stone-600 mb-3">{t('Thao tác nhanh')}</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.tab}
                onClick={() => onNavigate(item.tab)}
                className="group p-5 bg-white rounded-xl border border-stone-200/90 shadow-sm hover:shadow-md hover:border-stone-400 text-left transition-all duration-200 flex flex-col justify-between"
              >
                <div>
                  <div className="w-10 h-10 mb-4 rounded-lg bg-stone-100 group-hover:bg-amber-50 group-hover:text-amber-900 text-stone-700 flex items-center justify-center transition-colors">
                    <Icon className="w-5 h-5 stroke-[1.8]" />
                  </div>
                  <h3 className="text-sm font-semibold text-stone-900 mb-1 group-hover:text-amber-950">{item.title}</h3>
                  <p className="text-xs text-stone-600 line-clamp-3 leading-relaxed">{item.description}</p>
                </div>
                <div className="mt-4 pt-3 border-t border-stone-100 flex items-center text-xs font-medium text-stone-500 group-hover:text-stone-900">
                  <span>{t('Mở')}</span>
                  <ArrowRight className="w-3.5 h-3.5 ml-1 group-hover:translate-x-1 transition-transform" />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {stats.map((stat) => (
          <div key={stat.label} className="p-4 bg-white rounded-xl border border-stone-200/90 shadow-sm">
            <span className="text-xs text-stone-600 font-medium">{stat.label}</span>
            <div className="text-2xl font-bold text-stone-900 mt-1 font-mono tabular-nums">{stat.value}</div>
            <span className="text-[11px] text-stone-600 block mt-0.5">{stat.sub}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Lượt tìm kiếm gần đây */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-stone-200/90 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-stone-200/80 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-stone-900">{t('Tìm kiếm gần đây')}</h2>
              <p className="text-xs text-stone-600 mt-0.5">{t('Bấm vào một lượt tìm kiếm để mở lại kết quả trong khung chat')}</p>
            </div>
            <button
              onClick={() => onNavigate('activity')}
              className="text-xs font-medium text-stone-700 hover:text-stone-950 flex items-center gap-1 shrink-0"
            >
              <span>{t('Lịch sử hoạt động')}</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          {history.length === 0 ? (
            <div className="p-8 text-center space-y-3">
              <p className="text-xs text-stone-500">{t('Chưa có lượt tìm kiếm nào.')}</p>
              <button
                onClick={() => onNavigate('search')}
                className="inline-flex items-center gap-1.5 px-4 py-2 bg-stone-900 text-amber-50 rounded-xl text-xs font-semibold hover:bg-stone-800"
              >
                <span>{t('Bắt đầu tìm kiếm')}</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="divide-y divide-stone-100">
              {history.slice(0, 5).map((record) => {
                const top = record.products[0];
                return (
                  <button
                    key={record.id}
                    onClick={() => onOpenRecord(record)}
                    className="w-full p-4 hover:bg-canvas transition-colors text-left flex items-center justify-between gap-4"
                  >
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-stone-100 text-stone-700 flex items-center justify-center shrink-0 mt-0.5">
                        <Search className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <h4 className="text-xs font-semibold text-stone-900 truncate">{record.query}</h4>
                        {top && (
                          <div className="flex flex-wrap items-center gap-x-2 mt-1 text-[11px] text-stone-600">
                            <span>{t('Hạng 1:')} <strong className="text-stone-800">{top.name}</strong></span>
                            <span>·</span>
                            <span className="font-mono">{top.currentPrice.toLocaleString(currentLocale())} ₫</span>
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <div className="text-right text-[11px] text-stone-500">
                        <div>{t('{count} sản phẩm', { count: record.products.length })}</div>
                        <div className="font-mono">{record.timestamp}</div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-stone-400" />
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Sản phẩm đã lưu gần đây */}
        <div className="bg-white rounded-xl border border-stone-200/90 shadow-sm overflow-hidden">
          <div className="p-5 border-b border-stone-200/80 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-stone-900">{t('Đã lưu gần đây')}</h2>
            {saved.length > 0 && (
              <button
                onClick={() => onNavigate('saved')}
                className="text-xs font-medium text-stone-700 hover:text-stone-950 flex items-center gap-1"
              >
                <span>{t('Xem tất cả')}</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            )}
          </div>

          {saved.length === 0 ? (
            <p className="p-8 text-center text-xs text-stone-500">{t('Chưa lưu sản phẩm nào.')}</p>
          ) : (
            <div className="divide-y divide-stone-100">
              {saved.slice(0, 4).map(({ product: p }) => (
                <div key={p.id} className="p-3 flex items-center gap-3">
                  <img src={p.imageUrl} alt={p.name} className="w-10 h-10 rounded-lg object-cover shrink-0" />
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-stone-900 truncate">{p.name}</div>
                    <div className="text-[11px] text-stone-500">
                      <span className="font-mono text-stone-800">{p.currentPrice.toLocaleString(currentLocale())} ₫</span> · {getPlatformName(p.platformId)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
