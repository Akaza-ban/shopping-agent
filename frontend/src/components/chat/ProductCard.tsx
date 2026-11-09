import React from 'react';
import { BellRing, Bookmark, BookmarkCheck, ExternalLink, ImageOff, ShieldCheck, Star } from 'lucide-react';
import { ProductItem } from '../../types.ts';
import { getPlatformName } from '../../services/shoppingService.ts';
import { formatVnd, t } from '../../i18n/index.tsx';

// Kết quả đối chiếu thông số bắt buộc (VD: GPU) với trang chi tiết sản phẩm
const AttributeBadge: React.FC<{ product: ProductItem }> = ({ product }) => {
  const status = Object.values(product.attributeMatch ?? {});
  if (!status.length) return null;
  if (status.includes('mismatch')) {
    return <span className="text-[10px] font-semibold text-red-800 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded">{t('Không đúng cấu hình yêu cầu')}</span>;
  }
  if (status.every(v => v === 'verified')) {
    return <span className="text-[10px] font-semibold text-emerald-800 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded">{t('Đúng cấu hình yêu cầu')}</span>;
  }
  return <span className="text-[10px] font-semibold text-stone-600 bg-stone-50 border border-stone-200 px-1.5 py-0.5 rounded">{t('Chưa xác minh cấu hình')}</span>;
};

export const ProductCard: React.FC<{
  product: ProductItem;
  rank: number;
  isSaved: boolean;
  onToggleSave: () => void;
  isTracked: boolean;
  onTrackPrice: () => void;
  onOpenPolicy: () => void;
}> = ({ product, rank, isSaved, onToggleSave, isTracked, onTrackPrice, onOpenPolicy }) => (
  <div className="flex gap-3 p-3 bg-panel border border-stone-200 rounded-xl">
    <div className="relative shrink-0">
      {product.imageUrl ? (
        <img src={product.imageUrl} alt={product.name} className="w-20 h-20 rounded-lg object-contain bg-white overflow-hidden text-[0px]" loading="lazy" />
      ) : (
        <div className="w-20 h-20 rounded-lg bg-stone-100 flex items-center justify-center text-stone-400">
          <ImageOff className="w-5 h-5" />
        </div>
      )}
      <span className="absolute -top-1.5 -left-1.5 w-6 h-6 rounded-full bg-stone-900 text-amber-50 text-[11px] font-bold flex items-center justify-center">
        {rank}
      </span>
    </div>
    <div className="flex-1 min-w-0 space-y-1">
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-xs font-bold text-stone-900 line-clamp-2">{product.name}</h4>
        <span className="shrink-0 text-[11px] font-bold text-emerald-800 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded">
          {t('Phù hợp {score}%', { score: product.matchScore })}
        </span>
      </div>
      <div className="text-[11px] text-stone-500">
        {product.retailer} · {getPlatformName(product.platformId)}
      </div>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="font-mono font-bold text-stone-900">{formatVnd(product.currentPrice)}</span>
        {product.originalPrice > product.currentPrice && (
          <span className="font-mono text-[11px] text-stone-400 line-through">{formatVnd(product.originalPrice)}</span>
        )}
        <span className="flex items-center gap-0.5 text-[11px] text-stone-600">
          <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
          {product.rating > 0 ? product.rating : t('Chưa có đánh giá')}
          {product.reviewsLabel && product.rating > 0 ? ` (${product.reviewsLabel})` : ''}
        </span>
        <AttributeBadge product={product} />
      </div>
      {(product.pros[0] || product.cons[0]) && (
        <div className="text-[11px] text-stone-600">
          {product.pros[0] && <span className="text-emerald-700">+ {product.pros[0]}</span>}
          {product.pros[0] && product.cons[0] && <span className="mx-1.5 text-stone-300">|</span>}
          {product.cons[0] && <span className="text-red-700">− {product.cons[0]}</span>}
        </div>
      )}
      {(product.warranty || product.returnPolicy) && (
        <div className="text-[11px] text-stone-500 line-clamp-1">
          <ShieldCheck className="inline w-3 h-3 mr-0.5 text-emerald-700" />
          {[product.warranty, product.returnPolicy].filter(Boolean).join(' · ')}
        </div>
      )}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSave}
          className={`inline-flex items-center gap-1 text-[11px] font-semibold ${
            isSaved ? 'text-amber-800' : 'text-stone-700 hover:text-stone-950'
          }`}
        >
          {isSaved ? <BookmarkCheck className="w-3.5 h-3.5" /> : <Bookmark className="w-3.5 h-3.5" />}
          {isSaved ? t('Đã lưu') : t('Lưu sản phẩm')}
        </button>
        <button
          onClick={onTrackPrice}
          className={`inline-flex items-center gap-1 text-[11px] font-semibold ${isTracked ? 'text-amber-800' : 'text-stone-700 hover:text-stone-950'}`}
        >
          <BellRing className="w-3.5 h-3.5" />
          {isTracked ? t('Đang theo dõi giá') : t('Theo dõi giá')}
        </button>
        <button onClick={onOpenPolicy} className="inline-flex items-center gap-1 text-[11px] font-semibold text-stone-700 hover:text-stone-950">
          <ShieldCheck className="w-3.5 h-3.5" />
          {t('Chính sách')}
        </button>
        <a
          href={product.productUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-[11px] font-medium text-stone-700 hover:text-stone-950"
        >
          {t('Xem tại sàn')} <ExternalLink className="w-3 h-3" />
        </a>
      </div>
    </div>
  </div>
);
