import { PlatformPolicy, PolicyScenario } from '../../types.ts';
import { msg } from '../../i18n/index.tsx';

// Tình huống người mua chọn; backend dùng để hướng câu trả lời và tìm đúng đoạn trích
export const SCENARIOS: { id: PolicyScenario; label: string }[] = [
  { id: 'defect', label: msg('Máy bị lỗi') },
  { id: 'change_mind', label: msg('Đổi ý, không thích') },
  { id: 'wrong_item', label: msg('Giao sai / thiếu hàng') },
  { id: 'warranty', label: msg('Bảo hành') },
];

export interface PolicyFact {
  label: string;
  value: string;
}

// Các mục điều khoản liên quan nhất tới từng tình huống, hiện ngay dưới câu trả lời
export function keyFacts(p: PlatformPolicy, scenario: PolicyScenario | null): PolicyFact[] {
  const defect = { label: msg('Khi lỗi nhà sản xuất'), value: p.defectExchange };
  const refund = { label: msg('Phí / thời gian hoàn tiền'), value: p.refundTime };
  const shipping = { label: msg('Gửi trả hàng'), value: p.returnShippingFee };
  const warranty = { label: msg('Tiếp nhận bảo hành'), value: p.warrantyHandling };
  const byScenario: Record<PolicyScenario, PolicyFact[]> = {
    defect: [defect, warranty],
    change_mind: [refund, shipping],
    wrong_item: [shipping, defect],
    warranty: [warranty, defect],
  };
  return (scenario ? byScenario[scenario] : [defect, refund]).filter(f => f.value);
}
