import React, { useEffect, useState } from 'react';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { AuthLayout, ErrorBox, Field, PasswordToggle, SubmitButton, passwordProblems } from './AuthView.tsx';
import { checkResetLink, resetPassword } from '../services/agentApi.ts';
import { useI18n } from '../i18n/index.tsx';

interface ResetPasswordViewProps {
  token: string;
  onDone: () => void;   // đặt mật khẩu mới thành công
  onCancel: () => void; // về màn đăng nhập
}

// Mở từ link trong email (?reset_token=...): kiểm tra link rồi cho đặt mật khẩu mới
export const ResetPasswordView: React.FC<ResetPasswordViewProps> = ({ token, onDone, onCancel }) => {
  const { t } = useI18n();
  const [link, setLink] = useState<{ valid: boolean; email: string | null } | null>(null);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [serverError, setServerError] = useState('');

  useEffect(() => {
    checkResetLink(token).then(setLink).catch(() => setLink({ valid: false, email: null }));
  }, [token]);

  const errors = {
    password: passwordProblems(password).length
      ? t('Mật khẩu cần {rules}.', { rules: passwordProblems(password).join(t(' và ')) })
      : '',
    confirm: confirm !== password ? t('Mật khẩu nhập lại không khớp.') : '',
  };
  const show = (field: keyof typeof errors) => (submitted ? errors[field] : '');

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setServerError('');
    if (errors.password || errors.confirm) return;
    setBusy(true);
    try {
      await resetPassword(token, password);
      onDone();
    } catch (err) {
      setServerError(t(err instanceof Error ? err.message : String(err)));
    } finally {
      setBusy(false);
    }
  };

  const back = (
    <button onClick={onCancel} className="inline-flex items-center gap-1 text-xs font-semibold text-amber-800 hover:text-amber-950">
      <ArrowLeft className="w-3.5 h-3.5" /> {t('Quay lại đăng nhập')}
    </button>
  );

  return (
    <AuthLayout>
      <div className="bg-white border border-stone-200 rounded-2xl shadow-sm p-6 space-y-5">
        <div className="space-y-1">
          <h2 className="text-base font-bold text-stone-900">{t('Đặt mật khẩu mới')}</h2>
          {link?.email && <p className="text-xs text-stone-600">{t('Tài khoản: {email}', { email: link.email })}</p>}
        </div>

        {link === null ? (
          <div className="flex items-center justify-center gap-2 py-6 text-xs text-stone-500">
            <Loader2 className="w-4 h-4 animate-spin" /> {t('Đang kiểm tra link...')}
          </div>
        ) : !link.valid ? (
          <ErrorBox>{t('Link đặt lại mật khẩu không hợp lệ hoặc đã hết hạn. Vui lòng yêu cầu link mới.')}</ErrorBox>
        ) : (
          <form onSubmit={submit} className="space-y-4" noValidate>
            <Field
              label={t('Mật khẩu mới')}
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={setPassword}
              autoComplete="new-password"
              error={show('password')}
              hint={t('Ít nhất 8 ký tự, có cả chữ và số.')}
              trailing={<PasswordToggle visible={showPassword} onToggle={() => setShowPassword(!showPassword)} />}
            />
            <Field
              label={t('Nhập lại mật khẩu')}
              type={showPassword ? 'text' : 'password'}
              value={confirm}
              onChange={setConfirm}
              autoComplete="new-password"
              error={show('confirm')}
            />
            {serverError && <ErrorBox>{serverError}</ErrorBox>}
            <p className="text-[11px] text-stone-500">{t('Sau khi đổi, tài khoản sẽ được đăng xuất khỏi mọi thiết bị.')}</p>
            <SubmitButton busy={busy}>{t('Đặt mật khẩu mới')}</SubmitButton>
          </form>
        )}
        {back}
      </div>
    </AuthLayout>
  );
};
