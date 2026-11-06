import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { getUserData, putUserData } from '../services/agentApi.ts';
import { useAuth } from './useAuth.tsx';
import { Language } from '../i18n/index.tsx';

/** Cài đặt người dùng (giao diện, ngôn ngữ): lưu trên máy và đồng bộ theo tài khoản khi đã đăng nhập. */
export type ThemeMode = 'light' | 'dark' | 'auto';
export type Theme = 'light' | 'dark';

export interface Preferences {
  themeMode: ThemeMode;
  darkFrom: string; // "HH:MM" — chế độ tự động: tối từ giờ này...
  darkTo: string;   // ...đến giờ này (có thể qua nửa đêm)
  language: Language;
}

const STORAGE_KEY = 'shopping-ai.preferences';
const LEGACY_THEME_KEY = 'shopping-ai.theme';
const SAVE_DELAY_MS = 600;

const defaults = (): Preferences => {
  let themeMode: ThemeMode = 'auto';
  try {
    const legacy = localStorage.getItem(LEGACY_THEME_KEY); // lựa chọn sáng / tối trước khi có cài đặt
    if (legacy) themeMode = JSON.parse(legacy) === 'dark' ? 'dark' : 'light';
  } catch { /* bỏ qua */ }
  const browserLang = typeof navigator !== 'undefined' && !navigator.language?.toLowerCase().startsWith('vi') ? 'en' : 'vi';
  return { themeMode, darkFrom: '18:00', darkTo: '06:00', language: browserLang };
};

const readLocal = (): Preferences => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...defaults(), ...(JSON.parse(raw) as Partial<Preferences>) };
  } catch { /* bỏ qua */ }
  return defaults();
};

const minutes = (hhmm: string) => {
  const [h, m] = hhmm.split(':').map(Number);
  return (h || 0) * 60 + (m || 0);
};

/** Chế độ tự động: tối trong khoảng [darkFrom, darkTo), khoảng có thể vắt qua nửa đêm. */
export function isDarkAt(date: Date, darkFrom: string, darkTo: string): boolean {
  const now = date.getHours() * 60 + date.getMinutes();
  const from = minutes(darkFrom);
  const to = minutes(darkTo);
  if (from === to) return false;
  return from < to ? now >= from && now < to : now >= from || now < to;
}

interface PreferencesValue {
  preferences: Preferences;
  theme: Theme; // giao diện đang áp dụng
  update: (patch: Partial<Preferences>) => void;
  toggleTheme: () => void; // lối tắt trên thanh tiêu đề: chuyển sang sáng / tối cố định
}

const PreferencesContext = createContext<PreferencesValue | null>(null);

export const PreferencesProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const [preferences, setPreferences] = useState<Preferences>(readLocal);
  const [clock, setClock] = useState(() => new Date());
  const syncedFor = useRef<string | null>(null); // tài khoản đã tải cài đặt từ máy chủ
  const dirty = useRef(false);

  // Chế độ tự động: kiểm tra lại mỗi phút
  useEffect(() => {
    if (preferences.themeMode !== 'auto') return;
    const timer = setInterval(() => setClock(new Date()), 60_000);
    return () => clearInterval(timer);
  }, [preferences.themeMode]);

  const theme: Theme =
    preferences.themeMode === 'auto'
      ? (isDarkAt(clock, preferences.darkFrom, preferences.darkTo) ? 'dark' : 'light')
      : preferences.themeMode;

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences)); } catch { /* bỏ qua */ }
  }, [preferences]);

  // Đăng nhập: lấy cài đặt của tài khoản; tài khoản chưa có thì lưu cài đặt đang dùng trên máy lên
  useEffect(() => {
    if (!user) {
      syncedFor.current = null;
      return;
    }
    let cancelled = false;
    getUserData<Partial<Preferences>>('preferences')
      .then(server => {
        if (cancelled) return;
        if (server && !dirty.current) setPreferences(prev => ({ ...prev, ...server }));
        else putUserData('preferences', preferences).catch(() => undefined);
      })
      .catch(() => undefined)
      .finally(() => { if (!cancelled) syncedFor.current = user.id; });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  // Thay đổi sau khi đã đồng bộ -> lưu lên tài khoản (gộp các thay đổi liên tiếp)
  useEffect(() => {
    if (!user || syncedFor.current !== user.id || !dirty.current) return;
    const timer = setTimeout(() => {
      putUserData('preferences', preferences).catch(() => undefined);
      dirty.current = false;
    }, SAVE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [preferences, user]);

  const value = useMemo<PreferencesValue>(() => ({
    preferences,
    theme,
    update: patch => {
      dirty.current = true;
      setPreferences(prev => ({ ...prev, ...patch }));
    },
    toggleTheme: () => {
      dirty.current = true;
      setPreferences(prev => ({ ...prev, themeMode: theme === 'dark' ? 'light' : 'dark' }));
    },
  }), [preferences, theme]);

  return <PreferencesContext.Provider value={value}>{children}</PreferencesContext.Provider>;
};

export function usePreferences(): PreferencesValue {
  const ctx = useContext(PreferencesContext);
  if (!ctx) throw new Error('usePreferences phải nằm trong PreferencesProvider'); // i18n-ignore: lỗi cho lập trình viên
  return ctx;
}
