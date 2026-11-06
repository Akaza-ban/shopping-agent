import { useEffect, useRef, useState } from 'react';
import { getUserData, putUserData, UserDataKey } from '../services/agentApi.ts';

const SAVE_DELAY_MS = 800;

// Khóa localStorage cũ: dữ liệu được chuyển vào tài khoản ở lần đăng nhập đầu tiên
const LEGACY_KEYS: Partial<Record<UserDataKey, string>> = {
  conversations: 'shopping-ai.conversations',
  'saved-products': 'shopping-ai.saved-products',
  activities: 'shopping-ai.activities',
  'search-history': 'shopping-ai.search-history',
};

const readLocal = <T,>(key: string): T | undefined => {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : undefined;
  } catch {
    return undefined;
  }
};

const writeLocal = (key: string, value: unknown) => {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* đầy hoặc bị chặn */ }
};

/** State gắn với tài khoản: hiện ngay bản trên máy, tải bản máy chủ và lưu lại sau mỗi thay đổi. */
export function useSyncedState<T>(userId: string, key: UserDataKey, initial: T) {
  const cacheKey = `shopping-ai.u.${userId}.${key}`;
  const [value, setValue] = useState<T>(() => readLocal<T>(cacheKey) ?? initial);
  const [loaded, setLoaded] = useState(false);
  const skipNextSave = useRef(true);

  useEffect(() => {
    let cancelled = false;
    getUserData<T>(key)
      .then(serverValue => {
        if (cancelled) return;
        if (serverValue !== null && serverValue !== undefined) {
          skipNextSave.current = true;
          setValue(serverValue);
        } else {
          // Tài khoản chưa có dữ liệu: chuyển dữ liệu dùng trước khi có tài khoản (nếu có) rồi bỏ bản cũ
          const legacyKey = LEGACY_KEYS[key];
          const legacy = legacyKey ? readLocal<T>(legacyKey) : undefined;
          if (legacyKey && legacy !== undefined) {
            skipNextSave.current = false; // lưu ngay bản chuyển sang lên máy chủ
            setValue(legacy);
            try { localStorage.removeItem(legacyKey); } catch { /* bỏ qua */ }
          }
        }
      })
      .catch(() => undefined) // máy chủ không phản hồi: tiếp tục dùng bản trên máy
      .finally(() => !cancelled && setLoaded(true));
    return () => { cancelled = true; };
  }, [userId, key]);

  useEffect(() => {
    writeLocal(cacheKey, value);
    if (!loaded) return;
    if (skipNextSave.current) {
      skipNextSave.current = false;
      return;
    }
    const timer = setTimeout(() => { putUserData(key, value).catch(() => undefined); }, SAVE_DELAY_MS);
    return () => clearTimeout(timer);
  }, [value, loaded]);

  return [value, setValue] as const;
}
