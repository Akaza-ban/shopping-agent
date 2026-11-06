import React, { useState } from 'react';
import { AlertTriangle, Eye, EyeOff, Languages, Loader2, Moon, Sun } from 'lucide-react';
import { BrandLogo } from './BrandLogo.tsx';
import { useAuth } from '../hooks/useAuth.tsx';
import { usePreferences } from '../hooks/usePreferences.tsx';
import { t as tr, useI18n } from '../i18n/index.tsx';

type Mode = 'login' | 'register';

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

// Cùng quy tắc với backend (services/auth_service.py) để báo lỗi ngay khi nhập
export function passwordProblems(password: string): string[] {
  const problems: string[] = [];
  if (password.length < 8) problems.push(tr('ít nhất 8 ký tự'));
  if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) problems.push(tr('có cả chữ và số'));
  return problems;
}

const Field: React.FC<{
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete: string;
  error?: string;
  hint?: string;
  trailing?: React.ReactNode;
}> = ({ label, type = 'text', value, onChange, autoComplete, error, hint, trailing }) => (
  <label className="block space-y-1.5">
    <span className="text-xs font-semibold text-stone-700">{label}</span>
    <div className={`flex items-center bg-white border rounded-xl focus-within:ring-1 transition-colors ${
      error ? 'border-red-300 focus-within:border-red-700 focus-within:ring-red-700' : 'border-stone-300 focus-within:border-stone-800 focus-within:ring-stone-800'
    }`}>
      <input
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        autoComplete={autoComplete}
        className="flex-1 min-w-0 px-3 py-2.5 text-sm bg-transparent outline-none text-stone-900 placeholder:text-stone-400"
      />
      {trailing}
    </div>
    {error ? <span className="block text-[11px] text-red-700">{error}</span> : hint ? <span className="block text-[11px] text-stone-500">{hint}</span> : null}
  </label>
);

export const AuthView: React.FC = () => {
  const { login, register } = useAuth();
  const { theme, toggleTheme, preferences, update } = usePreferences();
  const { t } = useI18n();
  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [serverError, setServerError] = useState('');

  const isRegister = mode === 'register';
  const errors = {
    email: !EMAIL_RE.test(email.trim()) ? t('Email không hợp lệ.') : '',
    displayName: isRegister && displayName.trim().length < 2 ? t('Tên hiển thị cần ít nhất 2 ký tự.') : '',
    password: !password
      ? t('Vui lòng nhập mật khẩu.')
      : isRegister && passwordProblems(password).length
        ? t('Mật khẩu cần {rules}.', { rules: passwordProblems(password).join(t(' và ')) })
        : '',
    confirm: isRegister && confirm !== password ? t('Mật khẩu nhập lại không khớp.') : '',
  };
  const hasErrors = Object.values(errors).some(Boolean);
  const show = (field: keyof typeof errors) => (submitted ? errors[field] : '');

  const switchMode = (next: Mode) => {
    setMode(next);
    setSubmitted(false);
    setServerError('');
    setConfirm('');
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setServerError('');
    if (hasErrors) return;
    setBusy(true);
    try {
      if (isRegister) await register(email.trim(), password, displayName.trim());
      else await login(email.trim(), password);
    } catch (err) {
      setServerError(t(err instanceof Error ? err.message : String(err)));
    } finally {
      setBusy(false);
    }
  };

  const eye = (
    <button
      type="button"
      onClick={() => setShowPassword(!showPassword)}
      className="px-3 text-stone-500 hover:text-stone-900"
      title={showPassword ? t('Ẩn mật khẩu') : t('Hiện mật khẩu')}
      aria-label={showPassword ? t('Ẩn mật khẩu') : t('Hiện mật khẩu')}
    >
      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
    </button>
  );

  return (
    <div className="min-h-screen bg-canvas flex flex-col">
      <div className="flex justify-end gap-2 p-4">
        {/* Chưa đăng nhập vẫn đổi được ngôn ngữ; lựa chọn được lưu vào tài khoản sau khi đăng nhập */}
        <button
          onClick={() => update({ language: preferences.language === 'vi' ? 'en' : 'vi' })}
          className="h-9 px-3 rounded-md flex items-center gap-1.5 text-xs font-semibold text-stone-600 hover:text-stone-900 hover:bg-stone-100 border border-stone-200"
          title={t('Ngôn ngữ')}
        >
          <Languages className="w-4 h-4" /> {preferences.language === 'vi' ? 'English' : 'Tiếng Việt'}
        </button>
        <button
          onClick={toggleTheme}
          className="w-9 h-9 rounded-md flex items-center justify-center text-stone-600 hover:text-stone-900 hover:bg-stone-100 border border-stone-200"
          title={theme === 'dark' ? t('Chuyển sang giao diện sáng') : t('Chuyển sang giao diện tối')}
          aria-label={theme === 'dark' ? t('Chuyển sang giao diện sáng') : t('Chuyển sang giao diện tối')}
        >
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>
      </div>

      <div className="flex-1 flex items-center justify-center px-4 pb-16">
        <div className="w-full max-w-md space-y-6">
          <div className="text-center space-y-3">
            <div className="flex justify-center"><BrandLogo size={48} /></div>
            <div>
              <h1 className="text-xl font-bold text-stone-900">Shopping AI</h1>
              <p className="text-sm text-stone-600 mt-1">{t('Trợ lý mua sắm thông minh: tìm kiếm có căn cứ, so sánh minh bạch.')}</p>
            </div>
          </div>

          <div className="bg-white border border-stone-200 rounded-2xl shadow-sm p-6 space-y-5">
            <div className="grid grid-cols-2 gap-1 p-1 bg-stone-100 rounded-xl" role="tablist">
              {(['login', 'register'] as Mode[]).map(m => (
                <button
                  key={m}
                  role="tab"
                  aria-selected={mode === m}
                  onClick={() => switchMode(m)}
                  className={`py-2 rounded-lg text-xs font-semibold transition-colors ${
                    mode === m ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-600 hover:text-stone-900'
                  }`}
                >
                  {m === 'login' ? t('Đăng nhập') : t('Đăng ký')}
                </button>
              ))}
            </div>

            <form onSubmit={submit} className="space-y-4" noValidate>
              {isRegister && (
                <Field label={t('Tên hiển thị')} value={displayName} onChange={setDisplayName} autoComplete="name" error={show('displayName')} />
              )}
              <Field label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" error={show('email')} />
              <Field
                label={t('Mật khẩu')}
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={setPassword}
                autoComplete={isRegister ? 'new-password' : 'current-password'}
                error={show('password')}
                hint={isRegister ? t('Ít nhất 8 ký tự, có cả chữ và số.') : undefined}
                trailing={eye}
              />
              {isRegister && (
                <Field
                  label={t('Nhập lại mật khẩu')}
                  type={showPassword ? 'text' : 'password'}
                  value={confirm}
                  onChange={setConfirm}
                  autoComplete="new-password"
                  error={show('confirm')}
                />
              )}

              {serverError && (
                <div className="flex items-start gap-2 p-3 rounded-xl border border-red-200 bg-red-50 text-xs text-red-800" role="alert">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{serverError}</span>
                </div>
              )}

              <button
                type="submit"
                disabled={busy}
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 bg-stone-900 text-amber-50 rounded-xl text-sm font-semibold hover:bg-stone-800 transition-colors disabled:bg-stone-400"
              >
                {busy && <Loader2 className="w-4 h-4 animate-spin" />}
                {isRegister ? t('Tạo tài khoản') : t('Đăng nhập')}
              </button>
            </form>

            <p className="text-center text-xs text-stone-600">
              {isRegister ? t('Đã có tài khoản?') : t('Chưa có tài khoản?')}{' '}
              <button onClick={() => switchMode(isRegister ? 'login' : 'register')} className="font-semibold text-amber-800 hover:text-amber-950">
                {isRegister ? t('Đăng nhập') : t('Đăng ký ngay')}
              </button>
            </p>
          </div>

          <p className="text-center text-[11px] text-stone-500">
            {t('Hội thoại, sản phẩm đã lưu và yêu cầu theo dõi giá được lưu theo tài khoản, dùng được trên mọi thiết bị.')}
          </p>
        </div>
      </div>
    </div>
  );
};
