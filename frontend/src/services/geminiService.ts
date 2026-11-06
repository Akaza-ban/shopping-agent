import { GoogleGenAI } from '@google/genai';
import { CitationItem, ClarificationQuestion, ReasoningStep, ShoppingDossier, AuditIssue, ProductItem } from '../types.ts';

// Pre-seeded database of verified Vietnamese e-commerce products
export const SAMPLE_PRODUCTS: ProductItem[] = [
  {
    id: 'prod-macbook-air-m3',
    name: 'Apple MacBook Air 13 inch M3 (16GB RAM / 512GB SSD)',
    brand: 'Apple',
    category: 'Laptop',
    currentPrice: 28490000,
    originalPrice: 32990000,
    lowestPrice90d: 27990000,
    rating: 4.9,
    reviewCount: 842,
    veracityScore: 96,
    imageUrl: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=800&auto=format&fit=crop&q=80',
    retailer: 'Apple Flagship Store (Shopee Mall / Tiki)',
    keySpecs: {
      'Vi xử lý': 'Apple M3 8-core CPU, 10-core GPU',
      'RAM': '16GB Unified Memory (Không thể nâng cấp sau này)',
      'Ổ cứng': '512GB SSD chuẩn PCIe',
      'Màn hình': '13.6 inch Liquid Retina (2560 x 1664), 500 nits, P3 wide color',
      'Pin & Sạc': 'Pin 52.6 Wh, thời lượng thực tế 14 - 16 giờ, sạc MagSafe 35W Dual',
      'Trọng lượng': '1.24 kg'
    },
    pros: [
      'Hiệu năng M3 vượt trội, tiết kiệm điện, máy chạy hoàn toàn êm ái không quạt',
      'Màn hình chuẩn màu đồ họa 100% DCI-P3, độ sáng cao',
      'Thời lượng pin thực tế đủ trọn vẹn 1-2 ngày làm việc di động',
      'Bảo hành chính hãng 12 tháng tại Apple Việt Nam (AASP)'
    ],
    cons: [
      'RAM và SSD bị hàn chết trên bo mạch, không thể nâng cấp về sau',
      'Chỉ hỗ trợ tối đa 2 màn hình ngoài khi gập nắp máy',
      'Ít cổng kết nối (chỉ 2 cổng Thunderbolt / USB-C)'
    ],
    dealExpiry: 'Còn 3 ngày (Chương trình Back to School / Sale giữa tháng)',
    inStock: true,
    warranty: '12 tháng chính hãng Apple Care / AASP toàn quốc'
  },
  {
    id: 'prod-zenbook-14-oled',
    name: 'ASUS Zenbook 14 OLED UX3405 (Intel Core Ultra 7 155H / 32GB / 1TB)',
    brand: 'ASUS',
    category: 'Laptop',
    currentPrice: 26990000,
    originalPrice: 31990000,
    lowestPrice90d: 26500000,
    rating: 4.8,
    reviewCount: 318,
    veracityScore: 92,
    imageUrl: 'https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=800&auto=format&fit=crop&q=80',
    retailer: 'ASUS Official Store / GearVN',
    keySpecs: {
      'Vi xử lý': 'Intel Core Ultra 7 155H (16 nhân, 22 luồng, tích hợp Intel AI Boost NPU)',
      'RAM': '32GB LPDDR5X 7467MHz',
      'Ổ cứng': '1TB M.2 NVMe PCIe 4.0 SSD',
      'Màn hình': '14 inch Lumina OLED 3K (2880 x 1800), 120Hz, 100% DCI-P3, HDR 600 nits',
      'Pin': '75 Wh, sử dụng thực tế 8 - 10 giờ, sạc Type-C 65W',
      'Trọng lượng': '1.2 kg'
    },
    pros: [
      'Dung lượng RAM 32GB cực lớn trong tầm giá 26 triệu, tối ưu chạy máy ảo & code nặng',
      'Màn hình 3K OLED 120Hz siêu nét, tương phản vô cực',
      'Trọng lượng siêu nhẹ chỉ 1.2 kg, vỏ nhôm nguyên khối bền chuẩn quân đội',
      'Đầy đủ cổng HDMI 2.1, USB-A và Thunderbolt 4'
    ],
    cons: [
      'Màn hình OLED gương hơi bóng khi làm việc ngoài trời nắng gắt',
      'Quạt tản nhiệt có tiếng gió nhẹ khi tải nặng liên tục'
    ],
    inStock: true,
    warranty: '24 tháng chính hãng ASUS Việt Nam'
  },
  {
    id: 'prod-thinkpad-t14s-gen5',
    name: 'Lenovo ThinkPad T14s Gen 5 (AMD Ryzen 7 PRO 8840U / 16GB / 512GB)',
    brand: 'Lenovo',
    category: 'Laptop',
    currentPrice: 25490000,
    originalPrice: 29500000,
    lowestPrice90d: 24900000,
    rating: 4.85,
    reviewCount: 195,
    veracityScore: 94,
    imageUrl: 'https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=800&auto=format&fit=crop&q=80',
    retailer: 'Lenovo Official Store / FPT Shop',
    keySpecs: {
      'Vi xử lý': 'AMD Ryzen 7 PRO 8840U (8 nhân, 16 luồng)',
      'RAM': '16GB LPDDR5X',
      'Ổ cứng': '512GB SSD M.2 PCIe Gen 4',
      'Màn hình': '14 inch WUXGA (1920 x 1200) IPS chống chói Anti-glare, 400 nits, Low Power',
      'Bàn phím': 'ThinkPad chống tràn nước huyền thoại, hành trình 1.5mm',
      'Trọng lượng': '1.24 kg'
    },
    pros: [
      'Bàn phím gõ êm nhất thế giới laptop, tối ưu cho lập trình viên và kế toán',
      'Độ bền vật lý cực cao, bảo mật vân tay + camera IR Windows Hello',
      'Màn hình nhám chống lóa làm việc ban ngày rất dịu mắt'
    ],
    cons: [
      'Độ phủ màu màn hình ở mức 100% sRGB (chưa bằng DCI-P3 của MacBook hay ASUS OLED)',
      'Thiết kế đen nhám cổ điển, ít thời trang'
    ],
    inStock: true,
    warranty: '36 tháng Premier Support tận nơi'
  }
];

export const INITIAL_DOSSIER: ShoppingDossier = {
  id: 'dossier-lap-2026',
  dossierCode: '245/QĐ-SHOPPING-2026',
  title: 'QUYẾT ĐỊNH / HỒ SƠ ĐỀ XUẤT MUA SẮM LAPTOP LÀM VIỆC TỐI ƯU',
  category: 'Thiết bị công nghệ & Văn phòng',
  organization: 'Phòng Quản lý Công nghệ & Mua sắm Cá nhân',
  effectiveDate: '24/10/2026',
  signerTitle: 'Chuyên viên Tư vấn Trí tuệ Nhân tạo',
  primaryProduct: SAMPLE_PRODUCTS[0],
  alternativeProducts: [SAMPLE_PRODUCTS[1], SAMPLE_PRODUCTS[2]],
  summaryRequirement: 'Ngân sách tối đa 28 triệu đồng; Yêu cầu: mỏng nhẹ dưới 1.3kg, RAM tối thiểu 16GB, màn hình chuẩn màu sắc nét, pin trọn vẹn ngày làm việc.',
  totalBudget: 28500000,
  estimatedSavings: 4500000,
  sections: [
    {
      id: 'sec-1',
      articleNumber: 'Điều 1',
      title: 'Lựa chọn đề xuất hàng đầu (Hạng Nhất)',
      content: 'Chấp thuận đề xuất mua sắm sản phẩm **Apple MacBook Air 13 M3 (16GB RAM / 512GB SSD)** với mức giá ưu đãi hiện tại là **28.490.000 đồng** (tiết kiệm 4.500.000 đồng so với giá niêm yết 32.990.000 đồng), áp dụng từ ngày 24 tháng 10 năm 2026.',
      highlighted: true,
      highlightNote: 'Đã cập nhật theo yêu cầu chọn cấu hình 16GB RAM để đảm bảo không bị thiếu hụt bộ nhớ sau 3-5 năm sử dụng.'
    },
    {
      id: 'sec-2',
      articleNumber: 'Điều 2',
      title: 'Định nghĩa tiêu chuẩn kỹ thuật & Căn cứ đối chiếu',
      content: 'Sản phẩm được định nghĩa là máy tính xách tay đạt chuẩn [Căn cứ thông số đối chiếu: Trọng lượng 1.24kg, Màn hình Liquid Retina 500 nits, Pin 15 giờ liên tục, vi xử lý Apple M3 3nm]. Đảm bảo vượt trội 35% về hiệu suất pin so với mức trung bình của phân khúc.',
      highlighted: false
    },
    {
      id: 'sec-3',
      articleNumber: 'Điều 3',
      title: 'Phương án dự phòng & Đối trọng cạnh tranh',
      content: 'Trong trường hợp cần môi trường hệ điều hành Windows gốc hoặc cần dung lượng RAM 32GB phục vụ chạy song song máy ảo Docker, phương án thay thế số 2 là **ASUS Zenbook 14 OLED UX3405** tại mức giá **26.990.000 đồng** với bảo hành chính hãng 24 tháng.',
      highlighted: false
    },
    {
      id: 'sec-4',
      articleNumber: 'Điều 4',
      title: 'Rà soát rủi ro & Điều kiện bảo hành bắt buộc',
      content: '[Cần lưu ý: RAM và SSD của MacBook M3 bị hàn cố định, không thể nâng cấp thủ công]. Yêu cầu mua tại các gian hàng Shopee Mall / Tiki Official hoặc đại lý ủy quyền AASP (CellphoneS, TopZone, FPT) để hưởng chính sách đổi mới 30 ngày nếu phát hiện lỗi phần cứng nhà sản xuất.',
      highlighted: true,
      highlightNote: 'Cảnh báo rủi ro về khả năng nâng cấp phần cứng.'
    },
    {
      id: 'sec-5',
      articleNumber: 'Điều 5',
      title: 'Thời điểm thanh toán & Kế hoạch áp mã giảm giá',
      content: 'Khuyến nghị người dùng chốt đơn vào khung giờ [00:00 - 02:00 ngày Sale Đôi hoặc Ngày Lương Về], kết hợp voucher sàn giảm thêm 1.000.000 đồng và hoàn tiền 5% qua thẻ tín dụng liên kết để đạt mức giá đáy 27.490.000 đồng.',
      highlighted: true,
      highlightNote: 'Khuyến nghị chiến thuật săn voucher tối ưu chi phí.'
    }
  ]
};

export const SAMPLE_AUDIT_ISSUES: AuditIssue[] = [
  {
    id: 'issue-1',
    sectionTitle: 'Mục 4: ĐIỀU KIỆN ĐỔI TRẢ & BẢO HÀNH GIAN HÀNG',
    originalText: 'Hỗ trợ đổi trả miễn phí trong 7 ngày đầu. Sau thời gian này, quý khách vui lòng liên hệ trung tâm bảo hành hãng tại Hà Nội hoặc TP.HCM (chi phí vận chuyển khách tự chi trả).',
    issueType: 'policy_loophole',
    aiObservation: 'Chính sách ghi "đổi trả miễn phí trong 7 ngày" nhưng thiếu điều khoản về tình trạng seal mở hộp hoặc lỗi điểm chết màn hình dưới 3 điểm.',
    evaluationReason: 'Tiêu chuẩn bảo hành Apple Việt Nam yêu cầu từ 3-5 điểm chết sáng/tối mới được bảo hành. Gian hàng không cam kết đổi mới 1:1 nếu dưới 3 điểm chết.',
    citationText: 'Chính sách bảo hành TTBH Apple AASP 2026 & Quy định hoàn hàng Shopee Mall',
    aiSuggestion: 'Yêu cầu người bán xác nhận bằng văn bản qua chat: "Cam kết 1 đổi 1 ngay tại lúc nhận hàng nếu có bất kỳ điểm chết màn hình hoặc móp méo thân vỏ".',
    status: 'pending'
  },
  {
    id: 'issue-2',
    sectionTitle: 'Mục 2: THÔNG SỐ RAM & KHẢ NĂNG NÂNG CẤP',
    originalText: 'Cấu hình tiêu chuẩn 16GB RAM tốc độ cao, hỗ trợ đa nhiệm mượt mà cho mọi tác vụ đồ họa và lập trình trong tương lai.',
    issueType: 'misleading',
    aiObservation: 'Gian hàng không nêu rõ RAM là Unified Memory gắn liền trên SoC, người dùng dễ hiểu nhầm có thể gắn thêm thanh RAM thứ hai.',
    evaluationReason: 'Tránh trường hợp khách hàng mua phiên bản 8GB với kỳ vọng tự nâng cấp sau này.',
    citationText: 'Tài liệu kiến trúc phần cứng Apple Silicon M3',
    aiSuggestion: 'Bổ sung chú thích rõ ràng: "RAM hàn chết trên chip, đã chọn đúng phiên bản 16GB để sử dụng lâu dài 4-5 năm."',
    status: 'pending'
  },
  {
    id: 'issue-3',
    sectionTitle: 'Mục 6: PHÂN TÍCH CHẤT LƯỢNG ĐÁNH GIÁ (REVIEW VERACITY)',
    originalText: 'Sản phẩm có 842 đánh giá 5 sao. Tuy nhiên phát hiện 18% lượt đánh giá xuất hiện trong vòng 48 giờ sau khi mở bán với nội dung ngắn cụt ngủn.',
    issueType: 'seeding_review',
    aiObservation: 'Có dấu hiệu seeding đánh giá trong tuần đầu ra mắt từ các tài khoản mới tạo.',
    evaluationReason: 'Hệ thống đã lọc bỏ 152 đánh giá đáng ngờ, chỉ tổng hợp 690 đánh giá từ người mua thực tế có kèm hình ảnh unbox và hoá đơn VAT.',
    citationText: 'Thuật toán phát hiện Seeding Review v2.4 (Shopping AI Engine)',
    aiSuggestion: 'Chỉ đọc nhóm đánh giá 3-4 sao để nhìn rõ các nhược điểm thực tế như viền màn hình dễ bám vân tay và nhiệt độ khi render video.',
    status: 'pending'
  }
];

export const SAMPLE_CITATIONS: CitationItem[] = [
  {
    id: 'cite-1',
    index: 1,
    sourceName: 'Apple Flagship Store trên Shopee Mall',
    sourceType: 'Shopee Mall',
    price: '28.490.000 ₫',
    officialPrice: '32.990.000 ₫',
    excerpt: 'MacBook Air 13 M3 16GB/512GB Space Gray chính hãng SA/A. Bảo hành 12 tháng tại các trung tâm Apple ủy quyền. Hỗ trợ trả góp 0%, freeship toàn quốc.',
    verifiedDate: '13/10/2026 - Kiểm tra cách đây 12 phút',
    reliabilityStatus: 'Đã xác minh'
  },
  {
    id: 'cite-2',
    index: 2,
    sourceName: 'Tiki Trading - Phân phối chính thức',
    sourceType: 'Tiki Official',
    price: '28.690.000 ₫',
    officialPrice: '32.990.000 ₫',
    excerpt: 'Cam kết 100% hàng chính hãng Apple Việt Nam. Đổi trả trong 30 ngày nếu phát hiện lỗi phần cứng nhà sản xuất. Giao nhanh 2h tại TP.HCM & Hà Nội.',
    verifiedDate: '13/10/2026 - Kiểm tra cách đây 25 phút',
    reliabilityStatus: 'Đã xác minh'
  },
  {
    id: 'cite-3',
    index: 3,
    sourceName: 'Diễn đàn Công nghệ & Người dùng thực tế (Voz / Tinhte)',
    sourceType: 'Đánh giá người dùng đã xác thực',
    excerpt: 'Tổng hợp từ 45 bài đánh giá sau 3 tháng sử dụng: Máy xử lý mượt các file Figma 150 frames, build code Next.js nhanh gấp đôi M1, pin đạt 14 tiếng lướt web và gõ tài liệu.',
    verifiedDate: 'Tháng 10/2026',
    reliabilityStatus: 'Đã xác minh'
  }
];

// Helper to simulate progressive system reasoning timeline (matches video "Tiến trình hệ thống")
export async function runReasoningPipeline(
  query: string,
  onStepUpdate: (steps: ReasoningStep[]) => void
): Promise<void> {
  const steps: ReasoningStep[] = [
    { id: 'step-1', label: 'Đang phân tích câu hỏi & bối cảnh nhu cầu...', status: 'running' },
    { id: 'step-2', label: 'Hiểu yêu cầu: Trích xuất ngân sách, thông số kỹ thuật và thương hiệu', status: 'pending' },
    { id: 'step-3', label: 'Đang tra cứu giá sàn & thông số kỹ thuật từ các nguồn chính hãng...', status: 'pending' },
    { id: 'step-4', label: 'Hệ thống đang quét kho dữ liệu Shopee Mall, Tiki Official, đại lý ủy quyền...', status: 'pending' },
    { id: 'step-5', label: 'Rà soát rủi ro, lọc đánh giá ảo & tổng hợp báo cáo căn cứ...', status: 'pending' }
  ];

  onStepUpdate([...steps]);
  await new Promise(r => setTimeout(r, 600));

  steps[0].status = 'completed';
  steps[0].detail = 'Phân loại: Tìm kiếm & so sánh thiết bị công nghệ';
  steps[1].status = 'running';
  onStepUpdate([...steps]);
  await new Promise(r => setTimeout(r, 700));

  steps[1].status = 'completed';
  steps[1].detail = `Từ khóa: "${query.slice(0, 45)}..."`;
  steps[2].status = 'running';
  onStepUpdate([...steps]);
  await new Promise(r => setTimeout(r, 800));

  steps[2].status = 'completed';
  steps[2].detail = 'Đối chiếu 3 mẫu laptop bán chạy nhất phân khúc 25 - 30 triệu';
  steps[3].status = 'running';
  onStepUpdate([...steps]);
  await new Promise(r => setTimeout(r, 750));

  steps[3].status = 'completed';
  steps[3].detail = 'Đã quét 4 nhà bán lẻ ủy quyền, phát hiện mức giá thấp nhất: 28.490.000 ₫';
  steps[4].status = 'running';
  onStepUpdate([...steps]);
  await new Promise(r => setTimeout(r, 650));

  steps[4].status = 'completed';
  steps[4].detail = 'Đã đối chiếu 3 nguồn trích dẫn & kiểm tra rủi ro bảo hành';
  onStepUpdate([...steps]);
}
