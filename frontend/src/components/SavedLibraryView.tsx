import React, { useState } from 'react';
import { 
  FolderArchive, 
  Search, 
  ArrowUpRight, 
  TrendingDown, 
  CheckCircle2, 
  ShieldCheck, 
  FileEdit, 
  Bell, 
  ExternalLink,
  Trash2,
  Download
} from 'lucide-react';
import { MonitoredDeal, NavigationTab } from '../types.ts';

interface SavedLibraryViewProps {
  onNavigate: (tab: NavigationTab) => void;
}

export const SavedLibraryView: React.FC<SavedLibraryViewProps> = ({
  onNavigate,
}) => {
  const [activeCategory, setActiveCategory] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  const [monitoredDeals, setMonitoredDeals] = useState<MonitoredDeal[]>([
    {
      id: 'deal-1',
      productName: 'Apple MacBook Air 13 inch M3 (16GB/512GB)',
      platform: 'Shopee Mall (Apple Flagship)',
      currentPrice: 28490000,
      targetPrice: 27500000,
      historicLow: 27990000,
      dropPercentage: 14,
      status: 'Giá chạm đáy',
      lastUpdated: '10 phút trước'
    },
    {
      id: 'deal-2',
      productName: 'ASUS Zenbook 14 OLED UX3405 (32GB/1TB)',
      platform: 'Tiki Trading',
      currentPrice: 26990000,
      targetPrice: 26000000,
      historicLow: 26500000,
      dropPercentage: 16,
      status: 'Đang giảm nhẹ',
      lastUpdated: '1 giờ trước'
    },
    {
      id: 'deal-3',
      productName: 'Sony WH-1000XM5 Chống ồn chủ động',
      platform: 'Sony Store Online (Lazada)',
      currentPrice: 6990000,
      targetPrice: 6500000,
      historicLow: 6490000,
      dropPercentage: 22,
      status: 'Chờ đợt sale',
      lastUpdated: 'Hôm qua'
    },
    {
      id: 'deal-4',
      productName: 'Robot hút bụi lau nhà Roborock Q Revo MaxV',
      platform: 'Roborock Official Store',
      currentPrice: 14990000,
      targetPrice: 14000000,
      historicLow: 13900000,
      dropPercentage: 18,
      status: 'Đang giảm nhẹ',
      lastUpdated: '3 giờ trước'
    }
  ]);

  const filteredDeals = monitoredDeals.filter(d => 
    d.productName.toLowerCase().includes(searchTerm.toLowerCase()) ||
    d.platform.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6 animate-fadeIn">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-stone-900">
            Kho lưu trữ Hồ sơ & Biến động Giá sàn
          </h1>
          <p className="text-xs sm:text-sm text-stone-500 mt-1">
            Quản lý các hồ sơ quyết định đã soạn thảo, sản phẩm đang theo dõi chu kỳ giá và nguồn đối chiếu.
          </p>
        </div>

        <button
          onClick={() => onNavigate('search')}
          className="px-4 py-2 bg-stone-900 text-amber-50 rounded-xl text-xs font-semibold hover:bg-stone-800 transition-colors shrink-0 shadow-xs"
        >
          + Thêm sản phẩm theo dõi mới
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white p-3 rounded-xl border border-stone-200/90 shadow-xs">
        <div className="flex items-center gap-2 bg-[#f8f7f4] px-3 py-1.5 rounded-lg border border-stone-200 w-full sm:w-80">
          <Search className="w-3.5 h-3.5 text-stone-400 shrink-0" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Tìm theo tên máy hoặc sàn phân phối..."
            className="w-full text-xs bg-transparent border-none outline-none text-stone-900 placeholder:text-stone-400"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {['all', 'Laptop', 'Âm thanh', 'Gia dụng'].map((cat) => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
                activeCategory === cat
                  ? 'bg-stone-900 text-amber-50'
                  : 'text-stone-600 hover:bg-stone-100'
              }`}
            >
              {cat === 'all' ? 'Tất cả danh mục' : cat}
            </button>
          ))}
        </div>
      </div>

      {/* Grid of Monitored Deals */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredDeals.map((deal) => (
          <div 
            key={deal.id}
            className="bg-white p-5 rounded-xl border border-stone-200/90 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between space-y-4"
          >
            <div>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-[11px] font-medium text-emerald-800 bg-emerald-50 border border-emerald-200/60 px-2 py-0.5 rounded">
                    {deal.platform}
                  </span>
                  <h3 className="text-sm font-bold text-stone-900 mt-2">
                    {deal.productName}
                  </h3>
                </div>
                <span className={`text-[11px] font-bold px-2 py-0.5 rounded shrink-0 ${
                  deal.status === 'Giá chạm đáy'
                    ? 'bg-amber-100 text-amber-900'
                    : 'bg-stone-100 text-stone-700'
                }`}>
                  {deal.status}
                </span>
              </div>

              {/* Price Details */}
              <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-stone-100 text-xs">
                <div>
                  <span className="text-[10px] text-stone-400 block">Giá hiện tại:</span>
                  <span className="font-mono font-bold text-stone-900 text-sm">
                    {deal.currentPrice.toLocaleString()} ₫
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-stone-400 block">Đáy 90 ngày:</span>
                  <span className="font-mono font-semibold text-emerald-700 text-sm">
                    {deal.historicLow.toLocaleString()} ₫
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-stone-400 block">Mục tiêu mua:</span>
                  <span className="font-mono font-semibold text-stone-600 text-sm">
                    {deal.targetPrice.toLocaleString()} ₫
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-stone-100 flex items-center justify-between text-xs">
              <span className="text-[11px] text-stone-400 flex items-center gap-1">
                <Bell className="w-3 h-3 text-stone-400" />
                Cập nhật {deal.lastUpdated}
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onNavigate('compare')}
                  className="px-3 py-1.5 bg-[#f6f5f1] hover:bg-stone-200 text-stone-800 font-semibold rounded-lg transition-colors flex items-center gap-1"
                >
                  <FileEdit className="w-3.5 h-3.5" />
                  <span>Mở Hồ sơ</span>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
