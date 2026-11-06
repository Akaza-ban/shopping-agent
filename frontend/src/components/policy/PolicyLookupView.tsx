import React, { useEffect, useState } from 'react';
import { AlertCircle, MapPin, RotateCw, Search, ShieldCheck } from 'lucide-react';
import { PlatformPolicy, PolicyExcerpt, PolicyRequest, PolicyScenario, PolicyScope } from '../../types.ts';
import { PLATFORMS, getPlatformName } from '../../services/shoppingService.ts';
import { lookupPolicies } from '../../services/agentApi.ts';
import { msg, t } from '../../i18n/index.tsx';
import { SCENARIOS } from './scenarios.ts';
import { PolicyAnswer } from './PolicyAnswer.tsx';
import { PolicyCompare, PolicyDetails } from './PolicyCompare.tsx';

interface PolicyLookupViewProps {
  enabledPlatformIds: string[];
  policies: PlatformPolicy[];
  onLookup: (query: string, platformIds: string[]) => void;
  request?: PolicyRequest | null;
  onRequestHandled?: () => void;
}

const CATEGORIES = [msg('Laptop & Máy tính'), msg('Điện thoại & Máy tính bảng'), msg('Điện máy & Gia dụng'), msg('Thời trang'), msg('Mỹ phẩm')];

interface Answer {
  query: string;
  summary: string;
  sourceIds: number[];
  excerpts: PolicyExcerpt[];
  scope: PolicyScope;
  productPlatformIds: string[];
}

export const PolicyLookupView: React.FC<PolicyLookupViewProps> = ({ enabledPlatformIds, policies: initialPolicies, onLookup, request, onRequestHandled }) => {
  const availablePlatforms = PLATFORMS.filter(p => enabledPlatformIds.includes(p.id));

  const [query, setQuery] = useState('');
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [scenario, setScenario] = useState<PolicyScenario | null>(null);
  const [deselectedIds, setDeselectedIds] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [policies, setPolicies] = useState<PlatformPolicy[]>(initialPolicies);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => setPolicies(prev => (prev.length ? prev : initialPolicies)), [initialPolicies]);

  const activeIds = enabledPlatformIds.filter(id => !deselectedIds.includes(id));
  // Đã xác định nơi bán -> chỉ hiện chính sách của nơi bán; chưa tra cứu -> các nền tảng đang chọn
  const shownIds = answer && !showAll ? answer.scope.platformIds : activeIds;
  const shownPolicies = policies.filter(p => shownIds.includes(p.platformId));

  const togglePlatform = (id: string) =>
    setDeselectedIds(prev => (prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]));

  const runLookup = async (lookupQuery: string, productPlatformIds: string[], nextScenario: PolicyScenario | null) => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await lookupPolicies(lookupQuery, activeIds, category, productPlatformIds, nextScenario);
      onLookup(lookupQuery, result.scope.platformIds);
      setPolicies(prev => {
        const merged = prev.map(p => result.policies.find(r => r.platformId === p.platformId) ?? p);
        return [...merged, ...result.policies.filter(r => !prev.some(p => p.platformId === r.platformId))];
      });
      setAnswer({
        query: lookupQuery, summary: result.summary, sourceIds: result.sourceIds ?? [], excerpts: result.excerpts,
        scope: result.scope, productPlatformIds,
      });
      setShowAll(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('Không tra cứu được chính sách, vui lòng thử lại.'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleLookup = (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading || activeIds.length === 0) return;
    runLookup(query.trim() || category, [], scenario);
  };

  // Đổi tình huống: tra lại ngay với câu hỏi và nơi bán đang xem
  const chooseScenario = (next: PolicyScenario) => {
    const value = scenario === next ? null : next;
    setScenario(value);
    if (isLoading || activeIds.length === 0) return;
    runLookup(answer?.query ?? (query.trim() || category), answer?.productPlatformIds ?? [], value);
  };

  useEffect(() => {
    if (!request) return;
    setQuery(request.query);
    runLookup(request.query, request.productPlatformIds, scenario);
    onRequestHandled?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request]);

  const names = (ids: string[]) => ids.map(getPlatformName).join(', ');
  const scopeText = (s: PolicyScope): string => {
    switch (s.kind) {
      case 'product':
        return t('Chính sách của nơi bán các sản phẩm đã gợi ý: {platforms}.', { platforms: names(s.platformIds) });
      case 'link':
        return t('Link thuộc {platform}: áp dụng chính sách của {platform}.', { platform: names(s.platformIds) });
      case 'catalog':
        return t('Sản phẩm này đang bán ở: {platforms}. Chỉ hiển thị chính sách của các nơi bán này.', {
          platforms: s.platformIds.map(id => `${getPlatformName(id)} (${s.matches[id]?.example ?? ''})`).join('; '),
        });
      case 'unknown_link':
        return t('Chưa nhận diện được nơi bán của link này. Hãy dán link Tiki, Thế Giới Di Động, Điện Máy Xanh, FPT Shop hoặc CellphoneS.');
      default:
        return t('Không tìm thấy sản phẩm trong kho dữ liệu nên đang so sánh chung các nền tảng đã chọn. Hãy kiểm tra chính sách của đúng nơi bạn mua.');
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto space-y-5 animate-fadeIn">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-stone-900">{t('Tra cứu chính sách bảo hành & đổi trả')}</h1>
        <p className="text-xs text-stone-600 mt-1">
          {t('Nhập sản phẩm hoặc dán link, chọn tình huống của bạn để biết nơi bán xử lý thế nào.')}
        </p>
      </div>

      <form onSubmit={handleLookup} className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row gap-2">
          <div className="flex-1 flex items-center gap-2 bg-inset px-3 py-2 rounded-lg border border-stone-300 focus-within:border-stone-800">
            <Search className="w-4 h-4 text-stone-400 shrink-0" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder={t('Tên sản phẩm hoặc link (VD: MacBook Air M3, iPhone 16...)')}
              className="w-full text-xs sm:text-sm bg-transparent border-none outline-none text-stone-900 placeholder:text-stone-400"
              disabled={isLoading}
            />
          </div>
          <select
            value={category}
            onChange={e => setCategory(e.target.value)}
            className="px-3 py-2 text-xs bg-inset border border-stone-300 rounded-lg text-stone-800 outline-none focus:border-stone-800"
            disabled={isLoading}
          >
            {CATEGORIES.map(c => <option key={c} value={c}>{t(c)}</option>)}
          </select>
          <button
            type="submit"
            disabled={isLoading || activeIds.length === 0}
            className="px-4 py-2 bg-stone-900 text-amber-50 rounded-lg text-xs font-semibold hover:bg-stone-800 transition-colors flex items-center justify-center gap-1.5 disabled:bg-stone-300"
          >
            {isLoading ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <ShieldCheck className="w-3.5 h-3.5" />}
            <span>{isLoading ? t('Đang tra cứu...') : t('Tra cứu bằng AI')}</span>
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-medium text-stone-500 mr-1">{t('Tình huống:')}</span>
          {SCENARIOS.map(s => (
            <button
              type="button"
              key={s.id}
              onClick={() => chooseScenario(s.id)}
              disabled={isLoading}
              className={`px-3 py-1 text-[11px] font-semibold rounded-full border transition-colors ${
                scenario === s.id ? 'bg-emerald-700 text-white border-emerald-700' : 'bg-white text-stone-700 border-stone-300 hover:border-stone-500'
              }`}
            >
              {t(s.label)}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-medium text-stone-500 mr-1">{t('Nền tảng:')}</span>
          {availablePlatforms.map(p => {
            const active = activeIds.includes(p.id);
            return (
              <button
                type="button"
                key={p.id}
                onClick={() => togglePlatform(p.id)}
                className={`px-2.5 py-1 text-[11px] font-semibold rounded-md border transition-colors ${
                  active ? 'bg-stone-900 text-amber-50 border-stone-900' : 'bg-white text-stone-600 border-stone-200 hover:border-stone-400'
                }`}
              >
                {p.name}
              </button>
            );
          })}
          {availablePlatforms.length === 0 && (
            <span className="text-[11px] text-stone-500">{t('Chưa bật nền tảng nào trong Cài đặt nguồn dữ liệu.')}</span>
          )}
        </div>
      </form>

      {isLoading && (
        <div className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm flex items-center gap-2.5 text-xs text-stone-700">
          <div className="w-4 h-4 rounded-full border-2 border-amber-600 border-t-transparent animate-spin shrink-0" />
          {t('Đang xác định nơi bán và tra cứu chính sách...')}
        </div>
      )}

      {error && !isLoading && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-xs text-red-900 flex gap-2">
          <AlertCircle className="w-4 h-4 text-red-700 shrink-0 mt-0.5" />
          <p>{error}</p>
        </div>
      )}

      {answer && !isLoading && (
        <div className={`p-3 rounded-xl border text-xs flex items-start gap-2 ${
          answer.scope.kind === 'compare' || answer.scope.kind === 'unknown_link'
            ? 'bg-amber-50 border-amber-200 text-amber-950'
            : 'bg-white border-stone-200 text-stone-800'
        }`}>
          <MapPin className="w-4 h-4 shrink-0 mt-0.5 text-stone-500" />
          <p className="flex-1">{scopeText(answer.scope)}</p>
          {answer.scope.kind !== 'compare' && (
            <button type="button" onClick={() => setShowAll(v => !v)} className="shrink-0 font-medium text-stone-600 hover:text-stone-950 underline decoration-stone-300">
              {showAll ? t('Chỉ xem nơi bán') : t('Xem tất cả nền tảng')}
            </button>
          )}
        </div>
      )}

      {answer && answer.summary && !isLoading && !showAll && (
        <PolicyAnswer
          summary={answer.summary}
          sourceIds={answer.sourceIds}
          excerpts={answer.excerpts}
          policies={shownPolicies}
          scenario={scenario}
        />
      )}

      {shownPolicies.length > 0 ? (
        <>
          {(shownPolicies.length > 1 || !answer || showAll) && (
            <div className="space-y-2">
              {!answer && <div className="text-xs font-semibold text-stone-700">{t('Tổng quan chính sách các nền tảng')}</div>}
              <PolicyCompare policies={shownPolicies} />
            </div>
          )}
          <PolicyDetails policies={shownPolicies} excerpts={answer && !showAll ? answer.excerpts : []} />
        </>
      ) : (
        !isLoading && (
          <div className="p-8 bg-white rounded-xl border border-stone-200 text-center text-xs text-stone-500">
            {t('Chọn ít nhất một nền tảng để xem chính sách.')}
          </div>
        )
      )}

      <p className="text-[11px] text-stone-500">
        {t('Chính sách có thể thay đổi theo ngành hàng, từng gian hàng và chương trình khuyến mãi. Hãy đối chiếu trang chính sách gốc trước khi mua.')}
      </p>
    </div>
  );
};
