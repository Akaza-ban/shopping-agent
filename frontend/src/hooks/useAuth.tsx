import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  AUTH_EXPIRED_EVENT,
  AuthUser,
  getMe,
  getToken,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  setToken,
} from '../services/agentApi.ts';

type AuthStatus = 'loading' | 'anonymous' | 'authenticated';

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: AuthUser) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUserState] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>(getToken() ? 'loading' : 'anonymous');

  // Có token từ lần trước -> hỏi backend xem phiên còn hiệu lực không
  useEffect(() => {
    if (!getToken()) return;
    getMe()
      .then(u => { setUserState(u); setStatus('authenticated'); })
      .catch(() => { setToken(null); setStatus('anonymous'); });
  }, []);

  // Backend trả 401 ở bất kỳ lời gọi nào -> quay về màn đăng nhập
  useEffect(() => {
    const onExpired = () => { setUserState(null); setStatus('anonymous'); };
    window.addEventListener(AUTH_EXPIRED_EVENT, onExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, onExpired);
  }, []);

  const value: AuthContextValue = {
    status,
    user,
    login: async (email, password) => {
      setUserState(await apiLogin(email, password));
      setStatus('authenticated');
    },
    register: async (email, password, displayName) => {
      setUserState(await apiRegister(email, password, displayName));
      setStatus('authenticated');
    },
    logout: async () => {
      await apiLogout().catch(() => undefined);
      setUserState(null);
      setStatus('anonymous');
    },
    setUser: setUserState,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth phải dùng bên trong AuthProvider'); // i18n-ignore: lỗi cho lập trình viên
  return ctx;
}
