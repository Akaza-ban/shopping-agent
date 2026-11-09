import { useEffect, useEffectEvent, useRef, useState } from 'react';
import { PriceAlert, ProductItem } from '../types.ts';
import { checkAlerts, createAlert, deleteAlert, listAlerts } from '../services/agentApi.ts';

const REFRESH_MS = 5 * 60 * 1000; // đọc lại danh sách để thấy kết quả của vòng kiểm tra nền ở backend

// Danh sách theo dõi giá dùng chung cho thanh bên (huy hiệu), thẻ sản phẩm và màn Theo dõi giá
export function usePriceAlerts(onTriggered: (alert: PriceAlert) => void) {
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [loadError, setLoadError] = useState('');
  const [checkingIds, setCheckingIds] = useState<string[] | 'all' | null>(null);
  const seenTriggered = useRef<Set<string> | null>(null);

  // Báo một lần cho mỗi yêu cầu vừa đạt giá (lần tải đầu chỉ ghi nhận)
  const apply = (next: PriceAlert[]) => {
    const triggered = next.filter(a => a.status === 'triggered');
    if (seenTriggered.current) {
      triggered.filter(a => !seenTriggered.current!.has(a.id)).forEach(onTriggered);
    }
    seenTriggered.current = new Set(triggered.map(a => a.id));
    setAlerts(next);
    setLoadError('');
  };

  const refresh = () => listAlerts().then(apply).catch(err => setLoadError(err instanceof Error ? err.message : String(err)));

  // Tải khi mở và đọc lại định kỳ; refresh luôn dùng onTriggered mới nhất mà không phải đặt lại bộ hẹn giờ
  const onRefreshTick = useEffectEvent(() => {
    void refresh();
  });
  useEffect(() => {
    onRefreshTick();
    const timer = setInterval(() => onRefreshTick(), REFRESH_MS);
    return () => clearInterval(timer);
  }, []);

  const create = async (product: ProductItem, targetPrice: number) => {
    const alert = await createAlert(product, targetPrice);
    setAlerts(prev => [alert, ...prev]);
  };

  const remove = async (id: string) => {
    await deleteAlert(id);
    setAlerts(prev => prev.filter(a => a.id !== id));
  };

  const check = async (ids?: string[]) => {
    setCheckingIds(ids ?? 'all');
    try {
      apply(await checkAlerts(ids));
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : String(err));
    } finally {
      setCheckingIds(null);
    }
  };

  const alertFor = (productId: string) => alerts.find(a => a.productId === productId);

  return { alerts, loadError, checkingIds, create, remove, check, alertFor };
}
