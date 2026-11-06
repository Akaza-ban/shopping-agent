import { useEffect, useState } from 'react';

// State lưu vào localStorage; trình duyệt chặn storage thì chỉ dùng trong phiên hiện tại.
export function usePersistentState<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : initial;
    } catch {
      return initial;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // bỏ qua
    }
  }, [key, value]);

  return [value, setValue] as const;
}
