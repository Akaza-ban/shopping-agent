import React, { useState } from 'react';
import { ArrowRight, BellRing, Bookmark, ExternalLink, Search, Sparkles, Star, Trash2 } from 'lucide-react';
import { ProductItem, SavedProduct } from '../types.ts';
import { getPlatformName, getPolicy } from '../services/shoppingService.ts';
import { currentLocale, t } from '../i18n/index.tsx';

interface SavedProductsViewProps {
  saved: SavedProduct[];
  onRemove: (productId: string) => void;
  onCompare: (products: ProductItem[]) => void;
  trackedIds: string[]; // sản phẩm đang được theo dõi giá
  onTrackPrice: (product: ProductItem) => void;
  onGoSearch: () => void;
}

export const SavedProductsView: React.FC<SavedProductsViewProps> = ({ saved, onRemove, onCompare, trackedIds, onTrackPrice, onGoSearch }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const term = searchTerm.toLowerCase();
  const filtered = saved.filter(s =>
    s.product.name.toLowerCase().includes(term) ||
    s.product.brand.toLowerCase().includes(term) ||
    s.sourceQuery.toLowerCase().includes(term)
  );
  const selectedProducts = saved.filter(s => selectedIds.includes(s.product.id)).map(s => s.product);

  const toggleSelect = (id: string) =>
    setSelectedIds(prev => (prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]));

  const handleRemove = (id: string) => {
    setSelectedIds(prev => prev.filter(x => x !== id));
    onRemove(id);
  };

  if (saved.length === 0) {
    return (
      <div className="h-[calc(100vh-3.5rem)] flex items-center justify-center p-8">
        <div className="bg-white p-8 rounded-2xl border border-stone-200 shadow-sm text-center max-w-md space-y-3">
          <div className="w-12 h-12 mx-auto rounded-xl bg-stone-100 flex items-center justify-center">
            <Bookmark className="w-6 h-6 text-stone-600" />
          </div>
          <h2 className="text-base font-bold text-stone-900">{t('Chưa có sản phẩm nào được lưu')}</h2>
          <p className="text-xs text-stone-600">
            {t('Bấm "Lưu sản phẩm" trên các đề xuất của trợ lý hoặc trong bảng so sánh để lưu lại xem sau.')}
          </p>
          <button
            onClick={onGoSearch}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-stone-900 text-amber-50 rounded-xl text-xs font-semibold hover:bg-stone-800"
          >
            <span>{t('Bắt đầu tìm kiếm')}</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto space-y-5 animate-fadeIn">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-stone-900">{t('Sản phẩm đã lưu ({count})', { count: saved.length })}</h1>
          <p className="text-xs text-stone-600 mt-1">
            {t('Các sản phẩm bạn đã lưu từ đề xuất của AI. Chọn từ 2 sản phẩm trở lên để nhờ AI so sánh trong khung chat.')}
          </p>
        </div>
        <button
          onClick={() => onCompare(selectedProducts)}
          disabled={selectedProducts.length < 2}
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-stone-900 text-amber-50 rounded-xl text-xs font-semibold hover:bg-stone-800 disabled:bg-stone-300 shrink-0"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>{t('Nhờ AI so sánh ({count})', { count: selectedProducts.length })}</span>
        </button>
      </div>

      <div className="flex items-center gap-2 bg-white px-3 py-2 rounded-xl border border-stone-200 shadow-xs w-full sm:w-96">
        <Search className="w-3.5 h-3.5 text-stone-400 shrink-0" />
        <input
          type="text"
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          placeholder={t('Tìm theo tên, hãng hoặc câu tìm kiếm...')}
          className="w-full text-xs bg-transparent border-none outline-none text-stone-900 placeholder:text-stone-400"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map(({ product: p, sourceQuery, savedAt }) => {
          const policy = getPolicy(p.platformId);
          const selected = selectedIds.includes(p.id);
          return (
            <div
              key={p.id}
              className={`bg-white rounded-xl border shadow-sm flex flex-col transition-all ${
                selected ? 'border-stone-800 ring-1 ring-stone-800' : 'border-stone-200 hover:shadow-md'
              }`}
            >
              <div className="p-4 flex gap-3">
                <img src={p.imageUrl} alt={p.name} className="w-20 h-20 rounded-lg object-cover shrink-0" />
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="text-xs font-bold text-stone-900 line-clamp-2">{p.name}</h3>
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={() => toggleSelect(p.id)}
                      className="mt-0.5 rounded text-stone-900 focus:ring-stone-900 shrink-0"
                      title={t('Chọn để so sánh')}
                    />
                  </div>
                  <div className="text-[11px] text-stone-500">{p.retailer} · {getPlatformName(p.platformId)}</div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-sm text-stone-900">{p.currentPrice.toLocaleString(currentLocale())} ₫</span>
                    <span className="flex items-center gap-0.5 text-[11px] text-stone-600">
                      <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
                      {p.rating > 0 ? p.rating : t('Chưa có đánh giá')}
                    </span>
                  </div>
                </div>
              </div>

              <div className="px-4 pb-3 grid grid-cols-2 gap-2 text-[11px]">
                <div className="p-2 bg-stone-50 rounded-lg">
                  <span className="text-stone-500 block">{t('Bảo hành')}</span>
                  <span className="font-medium text-stone-800">{p.warranty}</span>
                </div>
                <div className="p-2 bg-stone-50 rounded-lg">
                  <span className="text-stone-500 block">{t('Đổi trả')}</span>
                  <span className="font-medium text-stone-800">
                    {p.returnPolicy ?? (policy ? `${t('{days} ngày', { days: policy.returnWindowDays })}${policy.freeReturn ? t(', miễn phí') : ''}` : t('Chưa có dữ liệu'))}
                  </span>
                </div>
              </div>

              <div className="px-4 pb-3 text-[11px] text-stone-500 space-y-0.5">
                {sourceQuery && <div className="line-clamp-1">{t('Từ tìm kiếm:')} <span className="italic text-stone-700">"{sourceQuery}"</span></div>}
                <div>{t('Lưu lúc {time}', { time: savedAt })} · {t('Phù hợp {score}%', { score: p.matchScore })}</div>
              </div>

              <div className="mt-auto px-4 py-3 border-t border-stone-100 flex items-center justify-between text-xs">
                <button
                  onClick={() => handleRemove(p.id)}
                  className="inline-flex items-center gap-1 text-stone-500 hover:text-red-700 font-medium"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  {t('Bỏ lưu')}
                </button>
                <button
                  onClick={() => onTrackPrice(p)}
                  className={`inline-flex items-center gap-1 font-medium ${trackedIds.includes(p.id) ? 'text-amber-800' : 'text-stone-600 hover:text-stone-900'}`}
                >
                  <BellRing className="w-3.5 h-3.5" />
                  {trackedIds.includes(p.id) ? t('Đang theo dõi') : t('Theo dõi giá')}
                </button>
                <a
                  href={p.productUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-inset hover:bg-stone-200 text-stone-800 font-semibold rounded-lg"
                >
                  {t('Xem tại sàn')} <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <p className="text-xs text-stone-500 text-center py-6">{t('Không có sản phẩm nào khớp với "{term}".', { term: searchTerm })}</p>
      )}
    </div>
  );
};
