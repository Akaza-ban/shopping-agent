import React from 'react';
import { Bookmark, BookmarkCheck, ExternalLink, Star, Trophy } from 'lucide-react';
import { ComparisonResult, ProductItem } from '../types.ts';
import { getPlatformName, getPolicy } from '../services/shoppingService.ts';
import { currentLocale, t } from '../i18n/index.tsx';

interface ComparisonTableProps {
  products: ProductItem[];
  savedIds: string[];
  onToggleSave: (product: ProductItem) => void;
  comparison?: ComparisonResult; // bảng do tool so sánh của backend tạo (ưu tiên dùng nếu có)
}

const rowLabel = 'p-2.5 text-[10px] font-semibold text-stone-600 uppercase tracking-wider bg-panel align-top w-28 sticky left-0';
const cell = 'p-2.5 align-top text-[11px] text-stone-800 border-l border-stone-100 min-w-40';

const ProductHeader: React.FC<{ products: ProductItem[]; savedIds: string[]; onToggleSave: (p: ProductItem) => void }> = ({
  products, savedIds, onToggleSave
}) => (
  <thead>
    <tr className="border-b border-stone-200">
      <th className={rowLabel} />
      {products.map((p, i) => {
        const isSaved = savedIds.includes(p.id);
        return (
          <th key={p.id} className="p-2.5 text-left align-top border-l border-stone-100 min-w-40">
            <div className="flex items-start gap-2">
              {p.imageUrl && <img src={p.imageUrl} alt={p.name} className="w-10 h-10 rounded-md object-cover shrink-0" />}
              <div className="space-y-0.5">
                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-stone-500 uppercase">
                  {i === 0 && <Trophy className="w-3 h-3 text-amber-600" />}
                  {t('Hạng {rank}', { rank: i + 1 })}
                </span>
                <div className="text-[11px] font-bold text-stone-900 leading-snug">{p.name}</div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onToggleSave(p)}
                    className={`inline-flex items-center gap-1 text-[10px] font-semibold ${
                      isSaved ? 'text-amber-800' : 'text-stone-600 hover:text-stone-900'
                    }`}
                  >
                    {isSaved ? <BookmarkCheck className="w-3 h-3" /> : <Bookmark className="w-3 h-3" />}
                    {isSaved ? t('Đã lưu') : t('Lưu')}
                  </button>
                  {p.productUrl && (
                    <a href={p.productUrl} target="_blank" rel="noreferrer" className="inline-flex items-center gap-0.5 text-[10px] font-semibold text-stone-600 hover:text-stone-900">
                      Xem <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            </div>
          </th>
        );
      })}
    </tr>
  </thead>
);

// Kết quả của tool "so sánh sản phẩm" mà agent gọi, hiển thị ngay trong tin nhắn chat
export const ComparisonTable: React.FC<ComparisonTableProps> = ({ products, savedIds, onToggleSave, comparison }) => {
  // Bảng của backend: cột theo đúng thứ tự sản phẩm agent trả về, ô tốt nhất mỗi hàng được tô xanh
  if (comparison && comparison.columns.length === products.length) {
    return (
      <div className="border border-stone-200 rounded-xl overflow-x-auto bg-white">
        <table className="w-full border-collapse">
          <ProductHeader products={products} savedIds={savedIds} onToggleSave={onToggleSave} />
          <tbody className="divide-y divide-stone-100">
            {comparison.rows.map(row => (
              <tr key={row.label}>
                <td className={rowLabel}>{row.label}</td>
                {row.values.map((v, i) => (
                  <td key={i} className={`${cell} ${row.bestIndex === i ? 'bg-emerald-50/70 text-emerald-900 font-semibold' : ''}`}>
                    {v}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  const specKeys = Array.from(new Set(products.flatMap(p => Object.keys(p.keySpecs))));
  const lowestPrice = Math.min(...products.map(p => p.currentPrice));
  const topMatch = Math.max(...products.map(p => p.matchScore));

  return (
    <div className="border border-stone-200 rounded-xl overflow-x-auto bg-white">
      <table className="w-full border-collapse">
        <ProductHeader products={products} savedIds={savedIds} onToggleSave={onToggleSave} />
        <tbody className="divide-y divide-stone-100">
          <tr>
            <td className={rowLabel}>{t('Phù hợp')}</td>
            {products.map(p => (
              <td key={p.id} className={cell}>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1.5 bg-stone-100 rounded-full overflow-hidden">
                    <div className="h-full bg-emerald-600" style={{ width: `${p.matchScore}%` }} />
                  </div>
                  <span className={`font-mono font-bold ${p.matchScore === topMatch ? 'text-emerald-700' : 'text-stone-700'}`}>
                    {p.matchScore}%
                  </span>
                </div>
              </td>
            ))}
          </tr>
          <tr>
            <td className={rowLabel}>{t('Giá')}</td>
            {products.map(p => (
              <td key={p.id} className={cell}>
                <div className={`font-mono font-bold ${p.currentPrice === lowestPrice ? 'text-emerald-700' : 'text-stone-900'}`}>
                  {p.currentPrice.toLocaleString(currentLocale())} ₫
                </div>
                <div className="font-mono text-[10px] text-stone-400 line-through">{p.originalPrice.toLocaleString(currentLocale())} ₫</div>
                {p.currentPrice === lowestPrice && <div className="text-[10px] font-semibold text-emerald-700">{t('Giá thấp nhất')}</div>}
              </td>
            ))}
          </tr>
          <tr>
            <td className={rowLabel}>{t('Đánh giá')}</td>
            {products.map(p => (
              <td key={p.id} className={cell}>
                <span className="inline-flex items-center gap-1">
                  <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
                  <strong>{p.rating > 0 ? p.rating : '—'}</strong>
                  <span className="text-stone-500">({p.reviewsLabel ?? p.reviewCount})</span>
                </span>
              </td>
            ))}
          </tr>
          <tr>
            <td className={rowLabel}>{t('Nơi bán')}</td>
            {products.map(p => (
              <td key={p.id} className={cell}>
                <div className="font-medium">{p.retailer}</div>
                <div className="text-[10px] text-stone-500">{getPlatformName(p.platformId)}</div>
              </td>
            ))}
          </tr>

          {specKeys.map(key => (
            <tr key={key}>
              <td className={rowLabel}>{key}</td>
              {products.map(p => (
                <td key={p.id} className={cell}>{p.keySpecs[key] ?? <span className="text-stone-400">—</span>}</td>
              ))}
            </tr>
          ))}

          <tr>
            <td className={rowLabel}>{t('Ưu điểm')}</td>
            {products.map(p => (
              <td key={p.id} className={cell}>
                <ul className="space-y-0.5">{p.pros.length ? p.pros.map((x, i) => <li key={i} className="text-emerald-800">+ {x}</li>) : <li className="text-stone-400">—</li>}</ul>
              </td>
            ))}
          </tr>
          <tr>
            <td className={rowLabel}>{t('Nhược điểm')}</td>
            {products.map(p => (
              <td key={p.id} className={cell}>
                <ul className="space-y-0.5">{p.cons.length ? p.cons.map((x, i) => <li key={i} className="text-red-700">− {x}</li>) : <li className="text-stone-400">—</li>}</ul>
              </td>
            ))}
          </tr>
          <tr>
            <td className={rowLabel}>{t('Bảo hành')}</td>
            {products.map(p => <td key={p.id} className={cell}>{p.warranty}</td>)}
          </tr>
          <tr>
            <td className={rowLabel}>{t('Đổi trả')}</td>
            {products.map(p => {
              const policy = getPolicy(p.platformId);
              return (
                <td key={p.id} className={cell}>
                  {p.returnPolicy ? (
                    <span>{p.returnPolicy}</span>
                  ) : policy ? (
                    <div className="space-y-0.5">
                      <div className="font-semibold">
                        {t('{days} ngày', { days: policy.returnWindowDays })}{policy.freeReturn && <span className="text-emerald-700"> {t('· miễn phí')}</span>}
                      </div>
                      <div className="text-[10px] text-stone-600">{t(policy.defectExchange)}</div>
                    </div>
                  ) : (
                    <span className="text-stone-400">{t('Chưa có dữ liệu')}</span>
                  )}
                </td>
              );
            })}
          </tr>
          <tr>
            <td className={rowLabel} />
            {products.map(p => (
              <td key={p.id} className={cell}>
                <a
                  href={p.productUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 px-2.5 py-1 bg-stone-900 text-amber-50 rounded-md text-[10px] font-semibold hover:bg-stone-800"
                >
                  {t('Xem tại sàn')} <ExternalLink className="w-3 h-3" />
                </a>
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  );
};
