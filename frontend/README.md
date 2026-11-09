# ShopAI — Frontend

Giao diện React của trợ lý mua sắm. Backend nằm ở [`../backend`](../backend/README.md).

Công nghệ: React 19, TypeScript 6, Vite 8, Tailwind CSS 4, lucide-react.

## Chạy

```bash
npm install
copy .env.example .env      # VITE_API_BASE_URL: địa chỉ backend, mặc định http://localhost:8000
npm run dev                 # http://localhost:3000
```

## Lệnh kiểm tra

| Lệnh                   | Việc                                                                   |
| ---------------------- | ---------------------------------------------------------------------- |
| `npm run lint`         | ESLint: lỗi code, quy tắc React Hooks                                  |
| `npm run lint:fix`     | ESLint tự sửa những gì sửa được                                        |
| `npm run typecheck`    | Kiểm tra kiểu bằng `tsc --noEmit`                                      |
| `npm run format:check` | Kiểm tra định dạng bằng Prettier (không sửa file)                      |
| `npm run format`       | Định dạng lại bằng Prettier                                            |
| `npm run i18n:check`   | Chuỗi hiển thị đã bọc `t()` / `msg()` và đã có bản dịch tiếng Anh chưa |
| `npm run build`        | Build bản production vào `dist/`                                       |

Trước khi gửi thay đổi: `npm run lint && npm run typecheck && npm run i18n:check && npm run build`.

> Lưu ý: `npm run lint` trước đây là `tsc --noEmit`. Giờ phần kiểm tra kiểu đã chuyển sang `npm run typecheck`.

## Cấu trúc

```
src/
  main.tsx, App.tsx     điểm vào, điều hướng tab, modal
  components/           màn hình và thành phần giao diện
    chat/               thẻ sản phẩm, bảng chi tiết nguồn của khung chat
    policy/             tra cứu chính sách đổi trả, bảo hành
  hooks/                state dùng chung: đăng nhập, cài đặt, đồng bộ dữ liệu theo tài khoản, theo dõi giá
  services/agentApi.ts  gọi API backend (HTTP, SSE) và chuyển dữ liệu backend -> kiểu của giao diện
  i18n/                 t(), msg(), formatVnd(); bản dịch tiếng Anh ở en.ts
  types.ts              kiểu dữ liệu dùng chung
scripts/check-i18n.mjs  kiểm tra chuỗi chưa dịch
```

## Quy ước code

**Định dạng**

- Prettier (`.prettierrc`): nháy đơn, có dấu chấm phẩy, tối đa 120 ký tự mỗi dòng.
- Code cũ chưa được định dạng hàng loạt. Khi sửa file nào, chạy `npx prettier --write <file>` cho riêng file đó, và để thay đổi định dạng ở commit riêng nếu diff lớn.

**React và Hooks**

- Quy tắc React Hooks bắt buộc (`eslint-plugin-react-hooks`): chỉ gọi hook ở cấp cao nhất của component hoặc hook, và khai báo đủ dependency cho `useEffect` / `useMemo` / `useCallback`.
- Không gọi `setState` đồng bộ ngay trong thân `useEffect` để "chép" props vào state. Hãy tính trực tiếp lúc render, hoặc đặt lại state bằng `key`. Xem [You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect).
- Logic dùng lại ở nhiều nơi (gọi API, đồng bộ dữ liệu) đặt trong `src/hooks/`, component chỉ lo hiển thị.
- Chỉ tắt một rule bằng `// eslint-disable-next-line <rule>` kèm lý do ngay trên dòng đó. Không tắt rule trong cấu hình chỉ để lint pass.

**TypeScript**

- Không dùng `any`. Dữ liệu chưa rõ kiểu dùng `unknown` rồi kiểm tra.
- Kiểu dữ liệu dùng chung đặt trong `src/types.ts`. Dữ liệu thô từ backend có tiền tố `Backend…` và được chuyển sang kiểu của giao diện trong `services/agentApi.ts`.

**Gọi API**

- Mọi request đi qua `apiFetch` / `requestJson` trong `services/agentApi.ts` để tự gắn token và xử lý hết phiên đăng nhập (401). Không gọi `fetch` trực tiếp trong component.

**Chữ hiển thị và đa ngôn ngữ**

- Chuỗi hiển thị viết bằng tiếng Việt và bọc trong `t('...')`. Hằng số khai báo sẵn thì bọc `msg('...')`, rồi dịch bằng `t()` lúc hiển thị.
- Thêm bản dịch tiếng Anh vào `src/i18n/en.ts`. Câu có biến từ backend thì thêm regex vào `EN_PATTERNS`.
- Giá tiền dùng `formatVnd()` trong `src/i18n/index.tsx`, không tự ghép `toLocaleString() + ' ₫'`.

**Đặt tên**

- Component và file component: `PascalCase.tsx`. Hook: `useXxx.ts(x)`. Hàm xử lý sự kiện: `handleXxx`. Prop callback: `onXxx`.
- Giới hạn phải khớp backend (VD `MAX_MESSAGE_CHARS`, `MAX_COMPARE_PRODUCTS` trong `agentApi.ts`) thì ghi chú chỗ tương ứng ở backend.

## Phiên bản TypeScript

Dự án dùng TypeScript **~6.0.3**. Bản 7 (native) chưa có API JavaScript mà `typescript-eslint` cần (`typescript-eslint` hỗ trợ `>=4.8.4 <6.1.0`). Khi `typescript-eslint` hỗ trợ TypeScript 7 thì có thể nâng lên.
