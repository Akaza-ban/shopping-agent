import React, { useState } from 'react';
import { 
  KeyRound, 
  Mail, 
  Lock, 
  User, 
  ArrowRight, 
  Check, 
  Eye, 
  EyeOff, 
  ShieldCheck, 
  Sparkles,
  Building2
} from 'lucide-react';
import { BrandLogo } from './BrandLogo.tsx';

interface AuthViewProps {
  onLoginSuccess: (user: { name: string; email: string; role: string; avatar: string }) => void;
  onCancel?: () => void;
}

export const AuthView: React.FC<AuthViewProps> = ({ onLoginSuccess, onCancel }) => {
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('vuminhtri1104@gmail.com');
  const [password, setPassword] = useState('demo123456');
  const [fullName, setFullName] = useState('Nguyễn Minh Trí');
  const [organization, setOrganization] = useState('Mua sắm Cá nhân & Thiết bị Công nghệ');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg('');

    if (!email || !password) {
      setErrorMsg('Vui lòng nhập đầy đủ Email và Mật khẩu.');
      return;
    }

    if (authMode === 'register' && !fullName) {
      setErrorMsg('Vui lòng nhập họ và tên của bạn.');
      return;
    }

    setIsLoading(true);

    setTimeout(() => {
      setIsLoading(false);
      onLoginSuccess({
        name: authMode === 'register' ? fullName : (email.includes('tri') ? 'Nguyễn Minh Trí' : 'Chuyên viên Mua sắm'),
        email: email,
        role: 'Chuyên viên mua sắm',
        avatar: (authMode === 'register' ? fullName : 'Nguyễn Minh Trí').split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
      });
    }, 600);
  };

  const handleQuickDemo = (demoType: 'expert' | 'manager') => {
    if (demoType === 'expert') {
      setEmail('vuminhtri1104@gmail.com');
      setPassword('securePass2026');
      setFullName('Nguyễn Minh Trí');
    } else {
      setEmail('manager@shopping-agent.vn');
      setPassword('managerPass2026');
      setFullName('Trần Thị Thảo');
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 sm:p-6 bg-[#faf9f5] relative overflow-hidden">
      {/* Subtle decorative background textures */}
      <div className="absolute inset-0 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:24px_24px] opacity-60 pointer-events-none" />

      <div className="max-w-md w-full relative z-10 animate-fadeIn">
        {/* Header Icon / Branding */}
        <div className="text-center mb-6">
          <div className="flex justify-center mb-3">
            <BrandLogo size={52} />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-stone-900">
            {authMode === 'login' ? 'Đăng nhập' : 'Tạo tài khoản mới'}
          </h1>
          <p className="text-xs text-stone-600 mt-1.5 max-w-sm mx-auto">
            {authMode === 'login' 
              ? 'Đăng nhập để sử dụng không gian làm việc mua sắm, đối chiếu giá sàn và rà soát rủi ro.'
              : 'Đăng ký tài khoản để bắt đầu theo dõi deal, rà soát thông số và lập hồ sơ mua hàng.'}
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-2xl border border-stone-200/90 shadow-xl p-6 sm:p-8 space-y-5">
          {/* Quick Demo Autofill Pill (for quick evaluation) */}
          <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-xl space-y-1.5">
            <div className="flex items-center justify-between text-[11px] font-bold text-amber-900 uppercase tracking-wider">
              <span className="flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-amber-700" />
                Tài khoản trải nghiệm nhanh:
              </span>
            </div>
            <div className="flex items-center gap-2 pt-1">
              <button
                type="button"
                onClick={() => handleQuickDemo('expert')}
                className="flex-1 py-1.5 px-2 bg-white hover:bg-amber-100/60 border border-amber-300 rounded-lg text-[11px] font-medium text-stone-800 transition-colors text-center"
              >
                Chuyên viên Minh Trí
              </button>
              <button
                type="button"
                onClick={() => handleQuickDemo('manager')}
                className="flex-1 py-1.5 px-2 bg-white hover:bg-amber-100/60 border border-amber-300 rounded-lg text-[11px] font-medium text-stone-800 transition-colors text-center"
              >
                Quản lý mua sắm
              </button>
            </div>
          </div>

          {errorMsg && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 font-medium animate-slideUp">
              {errorMsg}
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            {authMode === 'register' && (
              <>
                <div className="space-y-1.5">
                  <label className="font-semibold text-stone-800 block">Họ và tên</label>
                  <div className="relative">
                    <User className="w-4 h-4 text-stone-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Nguyễn Văn A"
                      required
                      className="w-full pl-9 pr-3 py-2.5 bg-[#f8f7f4] border border-stone-300 rounded-xl focus:bg-white focus:border-stone-900 outline-none text-stone-900 font-medium transition-all"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="font-semibold text-stone-800 block">Tổ chức / Nhóm mua sắm</label>
                  <div className="relative">
                    <Building2 className="w-4 h-4 text-stone-400 absolute left-3 top-2.5" />
                    <input
                      type="text"
                      value={organization}
                      onChange={(e) => setOrganization(e.target.value)}
                      placeholder="Mua sắm Cá nhân & Công nghệ"
                      className="w-full pl-9 pr-3 py-2.5 bg-[#f8f7f4] border border-stone-300 rounded-xl focus:bg-white focus:border-stone-900 outline-none text-stone-900 font-medium transition-all"
                    />
                  </div>
                </div>
              </>
            )}

            {/* Email Field (matching video: "owner@demo.vn") */}
            <div className="space-y-1.5">
              <label className="font-semibold text-stone-800 block">Email</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-stone-400 absolute left-3 top-2.5" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="vuminhtri1104@gmail.com"
                  required
                  className="w-full pl-9 pr-3 py-2.5 bg-[#f8f7f4] border border-stone-300 rounded-xl focus:bg-white focus:border-stone-900 outline-none text-stone-900 font-medium transition-all"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="font-semibold text-stone-800">Mật khẩu</label>
                {authMode === 'login' && (
                  <button 
                    type="button" 
                    className="text-[11px] text-stone-600 hover:text-stone-900 font-medium"
                    onClick={() => alert('Liên kết đặt lại mật khẩu đã được gửi đến email của bạn.')}
                  >
                    Quên mật khẩu?
                  </button>
                )}
              </div>
              <div className="relative">
                <Lock className="w-4 h-4 text-stone-400 absolute left-3 top-2.5" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  required
                  className="w-full pl-9 pr-10 py-2.5 bg-[#f8f7f4] border border-stone-300 rounded-xl focus:bg-white focus:border-stone-900 outline-none text-stone-900 font-medium transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-stone-400 hover:text-stone-600"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Remember Me Checkbox */}
            {authMode === 'login' && (
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="remember"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="rounded text-stone-900 focus:ring-stone-900 cursor-pointer"
                />
                <label htmlFor="remember" className="text-stone-600 cursor-pointer select-none">
                  Ghi nhớ đăng nhập trên thiết bị này
                </label>
              </div>
            )}

            {/* Submit Button (matching video: "Đăng nhập") */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 bg-stone-900 hover:bg-stone-800 text-amber-50 rounded-xl font-bold text-xs uppercase tracking-wider transition-all shadow-md flex items-center justify-center gap-2 disabled:bg-stone-400"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-amber-300 border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <span>{authMode === 'login' ? 'Đăng nhập' : 'Tạo tài khoản'}</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {/* Divider (matching video: "hoặc") */}
          <div className="relative flex items-center justify-center my-4">
            <div className="border-t border-stone-200 w-full" />
            <span className="bg-white px-3 text-[11px] font-medium text-stone-600 absolute uppercase">
              hoặc
            </span>
          </div>

          {/* Continue with Google (matching video 00:13: "Tiếp tục với Google") */}
          <button
            type="button"
            onClick={() => {
              setIsLoading(true);
              setTimeout(() => {
                setIsLoading(false);
                onLoginSuccess({
                  name: 'Nguyễn Minh Trí',
                  email: 'vuminhtri1104@gmail.com',
                  role: 'Chuyên viên mua sắm',
                  avatar: 'NT'
                });
              }, 400);
            }}
            className="w-full py-2.5 bg-white hover:bg-stone-50 border border-stone-300 rounded-xl font-semibold text-xs text-stone-700 transition-colors flex items-center justify-center gap-2.5 shadow-xs"
          >
            <svg className="w-4 h-4" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
            <span>Tiếp tục với Google</span>
          </button>

          {/* Toggle between Login and Register (matching video 00:13: "Chưa có tài khoản? Đăng ký") */}
          <div className="pt-2 text-center text-xs text-stone-600">
            {authMode === 'login' ? (
              <p>
                Chưa có tài khoản?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode('register');
                    setErrorMsg('');
                  }}
                  className="font-bold text-stone-900 hover:underline ml-1"
                >
                  Đăng ký ngay
                </button>
              </p>
            ) : (
              <p>
                Đã có tài khoản?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode('login');
                    setErrorMsg('');
                  }}
                  className="font-bold text-stone-900 hover:underline ml-1"
                >
                  Đăng nhập
                </button>
              </p>
            )}
          </div>
        </div>

        {/* Back to app if opened from inside */}
        {onCancel && (
          <div className="mt-4 text-center">
            <button
              onClick={onCancel}
              className="text-xs text-stone-600 hover:text-stone-900 font-medium"
            >
              ← Quay lại bảng làm việc
            </button>
          </div>
        )}

        {/* Security badge at bottom */}
        <div className="mt-6 flex items-center justify-center gap-1.5 text-[11px] text-stone-600">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-700" />
          <span>Bảo mật dữ liệu cá nhân & Không lưu mật khẩu theo chuẩn mã hóa AES-256</span>
        </div>
      </div>
    </div>
  );
};
