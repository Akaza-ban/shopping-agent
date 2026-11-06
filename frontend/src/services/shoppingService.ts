import { Platform, PlatformPolicy } from '../types.ts';
import { msg, t } from '../i18n/index.tsx';

// Danh mục sàn cho màn "Tra cứu chính sách" và Cài đặt nguồn; chính sách lấy từ GET /api/policies.

export const PLATFORMS: Platform[] = [
  { id: 'tiki', name: 'Tiki Trading', type: msg('Sàn TMĐT') },
  { id: 'tgdd', name: msg('Thế Giới Di Động'), type: msg('Chuỗi bán lẻ') },
  { id: 'dmx', name: msg('Điện Máy Xanh'), type: msg('Chuỗi bán lẻ') },
  { id: 'fpt-shop', name: 'FPT Shop', type: msg('Chuỗi bán lẻ') },
  { id: 'cellphones', name: 'CellphoneS', type: msg('Chuỗi bán lẻ') },
];

export const getPlatformName = (platformId: string) =>
  t(PLATFORMS.find(p => p.id === platformId)?.name ?? platformId);

// Bản chính sách mới nhất từ máy chủ, dùng đồng bộ ở bảng so sánh và thẻ sản phẩm đã lưu
let policyCache: PlatformPolicy[] = [];

export const setPolicyCache = (policies: PlatformPolicy[]) => {
  policyCache = policies;
};

export const getPolicy = (platformId: string) =>
  policyCache.find(p => p.platformId === platformId);
