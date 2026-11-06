import React, { useEffect, useState } from 'react';
import { Database, Loader2, RefreshCw } from 'lucide-react';
import { CrawlerStatus } from '../types.ts';
import { getCrawlerStatus, parseServerDate, triggerCrawl } from '../services/agentApi.ts';
import { useAuth } from '../hooks/useAuth.tsx';
import { currentLocale, t } from '../i18n/index.tsx';

const formatWhen = (iso: string | null) =>
  iso ? parseServerDate(iso).toLocaleString(currentLocale(), { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit', year: 'numeric' }) : '—';

// Kho dữ liệu sản phẩm: số sản phẩm, lần cập nhật gần nhất, nút thu thập lại
export const DataWarehousePanel: React.FC = () => {
  const isAdmin = useAuth().user?.role === 'admin';
  const [status, setStatus] = useState<CrawlerStatus | null>(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = () =>
    getCrawlerStatus()
      .then(s => { setStatus(s); setError(''); })
      .catch(err => setError(err instanceof Error ? err.message : String(err)));

  useEffect(() => { void load(); }, []);

  // Đang thu thập ngầm -> cập nhật trạng thái mỗi 3 giây
  useEffect(() => {
    if (!status?.isRunning) return;
    const timer = setInterval(load, 3000);
    return () => clearInterval(timer);
  }, [status?.isRunning]);

  const start = async () => {
    try {
      const res = await triggerCrawl();
      setMessage(res.status === 'already_running' ? t('Đang có một đợt thu thập chạy.') : t('Đã bắt đầu thu thập, có thể mất vài phút.'));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };

  const lastRun = status?.lastRunStats as { totalProducts?: number; durationSeconds?: number; queriesCount?: number } | null;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-stone-900 font-bold">
        <Database className="w-4 h-4" /> {t('Kho dữ liệu sản phẩm')}
      </div>
      {error ? (
        <p className="text-red-700">{t('Không kết nối được backend: {error}', { error })}</p>
      ) : !status ? (
        <div className="flex items-center gap-2 text-stone-500"><Loader2 className="w-3.5 h-3.5 animate-spin" /> {t('Đang tải...')}</div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-2">
            <div className="p-3 rounded-xl bg-panel border border-stone-200">
              <div className="text-stone-500">{t('Sản phẩm trong kho')}</div>
              <div className="text-base font-bold text-stone-900">{status.totalProductsInDb.toLocaleString(currentLocale())}</div>
            </div>
            <div className="p-3 rounded-xl bg-panel border border-stone-200">
              <div className="text-stone-500">{t('Cập nhật gần nhất')}</div>
              <div className="font-semibold text-stone-900">{formatWhen(status.latestDataUpdate)}</div>
            </div>
          </div>
          <p className="text-stone-600">
            {status.isRunning
              ? t('Đang thu thập dữ liệu các mặt hàng phổ biến...')
              : lastRun?.totalProducts !== undefined
                ? t('Lần thu thập gần nhất ({when}): {products} sản phẩm từ {queries} từ khóa trong {seconds} giây.', {
                    when: formatWhen(status.lastRunTime),
                    products: lastRun.totalProducts,
                    queries: lastRun.queriesCount ?? 0,
                    seconds: Math.round(lastRun.durationSeconds ?? 0),
                  })
                : t('Chưa thu thập chủ động trong phiên chạy này của server. Danh mục phổ biến gồm {count} từ khóa.', { count: status.hotCatalogCount })}
          </p>
          {message && <p className="text-emerald-800">{message}</p>}
          {isAdmin ? (
            <button
              onClick={start}
              disabled={status.isRunning}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-stone-300 text-stone-800 font-semibold hover:bg-stone-50 disabled:text-stone-400"
            >
              {status.isRunning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
              {status.isRunning ? t('Đang thu thập...') : t('Thu thập lại dữ liệu ngay')}
            </button>
          ) : (
            <p className="text-stone-500">{t('Chỉ quản trị viên mới kích hoạt được việc thu thập lại dữ liệu.')}</p>
          )}
        </>
      )}
    </div>
  );
};
