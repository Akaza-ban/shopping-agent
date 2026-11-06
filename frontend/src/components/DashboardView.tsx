import React from 'react';
import { 
  Search, 
  ShieldCheck, 
  FileEdit, 
  UploadCloud, 
  TrendingDown, 
  Clock, 
  ExternalLink, 
  CheckCircle2, 
  AlertTriangle,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import { NavigationTab } from '../types.ts';

interface DashboardViewProps {
  onNavigate: (tab: NavigationTab) => void;
  onSelectProductForDossier?: (productId: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  onNavigate,
}) => {
  const quickActions = [
    {
      title: 'Tra cứu & Đề xuất mua sắm',
      description: 'Tìm kiếm sản phẩm theo nhu cầu thực tế, đối chiếu giá sàn và phân tích ưu nhược điểm có trích dẫn nguồn.',
      icon: Search,
      action: () => onNavigate('search'),
      badge: 'Căn cứ xác thực'
    },
    {
      title: 'Rà soát thông số & Đánh giá rủi ro',
      description: 'Phát hiện rủi ro bảo hành, lỗi phần cứng tiềm ẩn và lọc đánh giá seeding gian lận trên các sàn.',
      icon: ShieldCheck,
      action: () => onNavigate('audit'),
      badge: 'Chống seeding'
    },
    {
      title: 'Lập hồ sơ quyết định mua sắm',
      description: 'Thiết lập bảng so sánh chính thức, tổng hợp tiêu chuẩn kỹ thuật và chiến lược săn voucher tối ưu.',
      icon: FileEdit,
      action: () => onNavigate('compare'),
      badge: 'Chuẩn quy trình'
    },
    {
      title: 'Nhập link / Kiểm tra lịch sử giá',
      description: 'Dán đường dẫn sản phẩm Shopee, Lazada, Tiki hoặc hoá đơn để kiểm tra chu kỳ biến động giá 90 ngày.',
      icon: UploadCloud,
      action: () => onNavigate('search'),
      badge: 'Phân tích 90 ngày'
    }
  ];

  const statMetrics = [
    { label: 'Sản phẩm đang theo dõi', value: '12', sub: 'Trên 4 sàn chính thức', icon: Sparkles },
    { label: 'Lượt tra cứu & đối chiếu', value: '136', sub: 'Độ chính xác 98.4%', icon: Search },
    { label: 'Hồ sơ quyết định đã lập', value: '7', sub: 'Đã tối ưu cấu hình', icon: FileEdit },
    { label: 'Tiết kiệm ước tính', value: '4.850.000 ₫', sub: 'Nhờ voucher & chọn đúng thời điểm', icon: TrendingDown },
  ];

  const recentDossiers = [
    {
      id: 'dossier-1',
      title: 'Quyết định mua sắm Laptop đồ họa & Code di động',
      targetProduct: 'MacBook Air 13 M3 (16GB/512GB)',
      budget: '28.500.000 ₫',
      saving: '4.500.000 ₫',
      status: 'Đã hoàn tất đề xuất',
      date: '13/10/2026',
      safetyScore: '96%'
    },
    {
      id: 'dossier-2',
      title: 'Đối chiếu Tai nghe chống ồn khử âm văn phòng',
      targetProduct: 'Sony WH-1000XM5 vs Bose QC Ultra',
      budget: '8.000.000 ₫',
      saving: '1.200.000 ₫',
      status: 'Đang rà soát bảo hành',
      date: '11/10/2026',
      safetyScore: '91%'
    },
    {
      id: 'dossier-3',
      title: 'Robot hút bụi lau nhà tự đổ rác chung cư 95m2',
      targetProduct: 'Roborock Q Revo MaxV',
      budget: '15.000.000 ₫',
      saving: '2.100.000 ₫',
      status: 'Chờ đợt sale 15/10',
      date: '08/10/2026',
      safetyScore: '94%'
    }
  ];

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8 animate-fadeIn">
      {/* Welcome Title (matching video style: "Xin chào, Nguyễn Văn...") */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-stone-900">
          Xin chào, Nguyễn Minh Trí
        </h1>
        <p className="text-sm text-stone-600 mt-1">
          Tổng quan quyết định mua sắm thông minh, trạng thái biến động giá và các nguồn đối chiếu đã xác thực.
        </p>
      </div>

      {/* Quick Action Cards (4 cards matching video 00:15) */}
      <div>
        <div className="text-xs font-semibold uppercase tracking-wider text-stone-600 mb-3">
          Thao tác nhanh
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((item, idx) => {
            const Icon = item.icon;
            return (
              <button
                key={idx}
                onClick={item.action}
                className="group p-5 bg-white rounded-xl border border-stone-200/90 shadow-sm hover:shadow-md hover:border-stone-400 text-left transition-all duration-200 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-10 h-10 rounded-lg bg-stone-100 group-hover:bg-amber-50 group-hover:text-amber-900 text-stone-700 flex items-center justify-center transition-colors">
                      <Icon className="w-5 h-5 stroke-[1.8]" />
                    </div>
                    <span className="text-[11px] font-medium text-stone-600 group-hover:text-stone-800">
                      {item.badge}
                    </span>
                  </div>
                  <h3 className="text-sm font-semibold text-stone-900 mb-1 group-hover:text-amber-950">
                    {item.title}
                  </h3>
                  <p className="text-xs text-stone-600 line-clamp-3 leading-relaxed">
                    {item.description}
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-stone-100 flex items-center text-xs font-medium text-stone-500 group-hover:text-stone-900">
                  <span>Bắt đầu ngay</span>
                  <ArrowRight className="w-3.5 h-3.5 ml-1 group-hover:translate-x-1 transition-transform" />
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* KPI Stats Strip (matching video metrics) */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statMetrics.map((stat, idx) => (
          <div key={idx} className="p-4 bg-white rounded-xl border border-stone-200/90 shadow-sm">
            <span className="text-xs text-stone-600 font-medium">{stat.label}</span>
            <div className="text-xl lg:text-2xl font-bold text-stone-900 mt-1 font-mono tabular-nums">
              {stat.value}
            </div>
            <span className="text-[11px] text-stone-600 block mt-0.5">{stat.sub}</span>
          </div>
        ))}
      </div>

      {/* Recent Shopping Dossiers Table (like video "Tài liệu gần đây") */}
      <div className="bg-white rounded-xl border border-stone-200/90 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-stone-200/80 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-stone-900">Hồ sơ mua sắm & Quyết định gần đây</h2>
            <p className="text-xs text-stone-600 mt-0.5">Bảng đối chiếu thông số và lịch sử rà soát giá sàn</p>
          </div>
          <button 
            onClick={() => onNavigate('compare')}
            className="text-xs font-medium text-stone-700 hover:text-stone-950 flex items-center gap-1"
          >
            <span>Xem tất cả</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        <div className="divide-y divide-stone-100">
          {recentDossiers.map((item) => (
            <div 
              key={item.id}
              onClick={() => onNavigate('compare')}
              className="p-4 hover:bg-[#faf9f5] transition-colors cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-stone-100 text-stone-700 flex items-center justify-center shrink-0 mt-0.5">
                  <FileEdit className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-stone-900">{item.title}</h4>
                  <div className="flex flex-wrap items-center gap-2 mt-1 text-[11px] text-stone-600">
                    <span className="font-medium text-stone-800">{item.targetProduct}</span>
                    <span>·</span>
                    <span>Ngân sách: <strong className="text-stone-800">{item.budget}</strong></span>
                    <span>·</span>
                    <span className="text-emerald-700 font-medium">Tiết kiệm: {item.saving}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-4 shrink-0 sm:self-center">
                <div className="text-right">
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium text-stone-700 bg-stone-100 px-2 py-0.5 rounded">
                    <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                    {item.status}
                  </span>
                  <span className="block text-[10px] text-stone-600 mt-0.5">Tin cậy {item.safetyScore} · {item.date}</span>
                </div>
                <ArrowRight className="w-4 h-4 text-stone-400" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
