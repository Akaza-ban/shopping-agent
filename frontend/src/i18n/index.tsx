import React, { createContext, useContext, useEffect, useMemo } from 'react';
import { EN, EN_PATTERNS } from './en.ts';

/** Đa ngôn ngữ kiểu gettext: câu tiếng Việt là khóa, `en.ts` là bảng dịch. Kiểm tra: `npm run i18n:check`. */
export type Language = 'vi' | 'en';
export type Params = Record<string, string | number>;

export const LANGUAGES: { id: Language; label: string }[] = [
  { id: 'vi', label: 'Tiếng Việt' },
  { id: 'en', label: 'English' },
];

function toEnglish(text: string): string {
  if (text in EN) return EN[text];
  // Câu có biến do backend dựng sẵn
  for (const [pattern, template] of EN_PATTERNS) {
    if (pattern.test(text)) return text.replace(pattern, template);
  }
  return text;
}

export function translate(language: Language, text: string, params?: Params): string {
  const base = language === 'en' ? toEnglish(text) : text;
  return params ? base.replace(/\{(\w+)\}/g, (_, k: string) => String(params[k] ?? `{${k}}`)) : base;
}

export const localeOf = (language: Language) => (language === 'en' ? 'en-US' : 'vi-VN');

// Ngôn ngữ hiện hành cho mã ngoài component (định dạng ngày giờ, thông báo lỗi dựng sẵn).
// Đặt ở nơi ngôn ngữ thay đổi (usePreferences), trước khi giao diện render lại; không gán trong lúc render.
let current: Language = 'vi';
export const currentLanguage = () => current;
export const setCurrentLanguage = (language: Language) => {
  current = language;
};
export const t = (text: string, params?: Params) => translate(current, text, params);
// Đánh dấu chuỗi cần dịch trong hằng số (VD nhãn menu); dịch bằng t(...) lúc hiển thị
export const msg = (text: string) => text;
export const currentLocale = () => localeOf(current);
// Giá VND theo định dạng số của ngôn ngữ đang chọn (VD 25.990.000 ₫ / 25,990,000 ₫)
export const formatVnd = (amount: number) => `${Math.round(amount).toLocaleString(currentLocale())} ₫`;

interface I18nValue {
  language: Language;
  locale: string;
  t: (text: string, params?: Params) => string;
}

const I18nContext = createContext<I18nValue>({ language: 'vi', locale: 'vi-VN', t: (x, p) => translate('vi', x, p) });

export const I18nProvider: React.FC<{ language: Language; children: React.ReactNode }> = ({ language, children }) => {
  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);
  const value = useMemo<I18nValue>(
    () => ({ language, locale: localeOf(language), t: (text, params) => translate(language, text, params) }),
    [language],
  );
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
};

export const useI18n = () => useContext(I18nContext);
