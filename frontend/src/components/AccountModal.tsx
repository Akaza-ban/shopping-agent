import React, { useEffect, useState } from 'react';
import { CheckCircle2, Loader2, UserRound, X } from 'lucide-react';
import { useAuth } from '../hooks/useAuth.tsx';
import { changePassword, updateProfile } from '../services/agentApi.ts';
import { passwordProblems } from './AuthView.tsx';
import { t } from '../i18n/index.tsx';

interface AccountModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const inputClass =
  'w-full px-3 py-2 border border-stone-300 rounded-xl outline-none focus:border-stone-800 focus:ring-1 focus:ring-stone-800 text-stone-900 bg-white';

// Thông tin tài khoản: đổi tên hiển thị và đổi mật khẩu
export const AccountModal: React.FC<AccountModalProps> = ({ isOpen, onClose }) => {
  const { user, setUser } = useAuth();
  const [name, setName] = useState('');
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState<'profile' | 'password' | null>(null);
  const [message, setMessage] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (isOpen && user) {
      setName(user.displayName);
      setCurrent(''); setNext(''); setConfirm('');
      setMessage(null);
    }
  }, [isOpen]);

  if (!isOpen || !user) return null;

  const run = async (kind: 'profile' | 'password', action: () => Promise<string>) => {
    setBusy(kind);
    setMessage(null);
    try {
      setMessage({ kind: 'ok', text: await action() });
    } catch (err) {
      setMessage({ kind: 'error', text: t(err instanceof Error ? err.message : String(err)) });
    } finally {
      setBusy(null);
    }
  };

  const saveName = () => run('profile', async () => {
    setUser(await updateProfile(name.trim()));
    return t('Đã cập nhật tên hiển thị.');
  });

  const newProblems = passwordProblems(next);
  const savePassword = () => run('password', async () => {
    if (newProblems.length) throw new Error(t('Mật khẩu mới cần {rules}.', { rules: newProblems.join(t(' và ')) }));
    if (next !== confirm) throw new Error(t('Mật khẩu nhập lại không khớp.'));
    await changePassword(current, next);
    setCurrent(''); setNext(''); setConfirm('');
    return t('Đã đổi mật khẩu. Các thiết bị khác đã được đăng xuất.');
  });

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-md w-full shadow-2xl animate-scaleUp overflow-hidden">
        <div className="p-5 border-b border-stone-200 flex items-center justify-between bg-panel">
          <div className="flex items-center gap-2">
            <UserRound className="w-4 h-4 text-stone-800" />
            <h3 className="text-sm font-bold text-stone-900">{t('Tài khoản')}</h3>
          </div>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-stone-200 flex items-center justify-center text-stone-500" aria-label={t('Đóng')}>
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-6 text-xs">
          <div className="space-y-1 text-stone-600">
            <div>Email: <strong className="text-stone-900">{user.email}</strong></div>
            <div>{t('Vai trò:')} <strong className="text-stone-900">{user.role === 'admin' ? t('Quản trị viên') : t('Người dùng')}</strong></div>
          </div>

          <div className="space-y-2">
            <span className="font-semibold text-stone-700">{t('Tên hiển thị')}</span>
            <div className="flex gap-2">
              <input value={name} onChange={e => setName(e.target.value)} className={inputClass} autoComplete="name" />
              <button
                onClick={saveName}
                disabled={busy !== null || name.trim().length < 2 || name.trim() === user.displayName}
                className="shrink-0 px-3 py-2 rounded-xl border border-stone-300 font-semibold text-stone-800 hover:bg-stone-50 disabled:text-stone-400"
              >
                {busy === 'profile' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : t('Lưu')}
              </button>
            </div>
          </div>

          <div className="space-y-2 pt-4 border-t border-stone-200">
            <span className="font-semibold text-stone-700">{t('Đổi mật khẩu')}</span>
            <input type="password" placeholder={t('Mật khẩu hiện tại')} value={current} onChange={e => setCurrent(e.target.value)} className={inputClass} autoComplete="current-password" />
            <input type="password" placeholder={t('Mật khẩu mới (≥ 8 ký tự, có chữ và số)')} value={next} onChange={e => setNext(e.target.value)} className={inputClass} autoComplete="new-password" />
            <input type="password" placeholder={t('Nhập lại mật khẩu mới')} value={confirm} onChange={e => setConfirm(e.target.value)} className={inputClass} autoComplete="new-password" />
            <button
              onClick={savePassword}
              disabled={busy !== null || !current || !next || !confirm}
              className="w-full inline-flex items-center justify-center gap-1.5 py-2 bg-stone-900 text-amber-50 rounded-xl font-semibold hover:bg-stone-800 disabled:bg-stone-300"
            >
              {busy === 'password' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {t('Đổi mật khẩu')}
            </button>
          </div>

          {message && (
            <div className={`flex items-start gap-2 p-3 rounded-xl border ${
              message.kind === 'ok' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-800'
            }`} role="status">
              {message.kind === 'ok' && <CheckCircle2 className="w-4 h-4 shrink-0" />}
              <span>{message.text}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
