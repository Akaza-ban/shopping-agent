import React from 'react';

interface BrandLogoProps {
  className?: string;
  size?: number;
  variant?: 'light' | 'dark' | 'icon-only';
}

export const BrandLogo: React.FC<BrandLogoProps> = ({ 
  className = "w-6 h-6", 
  size,
  variant = 'icon-only'
}) => {
  return (
    <div className={`inline-flex items-center gap-2.5 ${className}`}>
      {/* Custom Shopping AI Monogram Logo */}
      <div 
        className="relative flex items-center justify-center rounded-xl bg-gradient-to-br from-stone-900 via-stone-850 to-stone-950 text-white shadow-md border border-stone-750 shrink-0"
        style={{ width: size || 40, height: size || 40 }}
      >
        <svg 
          viewBox="0 0 36 36" 
          fill="none" 
          xmlns="http://www.w3.org/2000/svg"
          className="w-[62%] h-[62%]"
        >
          {/* Shopping Tote Outline */}
          <path 
            d="M7 12C7 9.79086 8.79086 8 11 8H25C27.2091 8 29 9.79086 29 12V26C29 28.7614 26.7614 31 24 31H12C9.23858 31 7 28.7614 7 26V12Z" 
            fill="#1C1917"
            stroke="#E7E5E4" 
            strokeWidth="2.2" 
          />
          {/* Handle */}
          <path 
            d="M12 10V6.5C12 4.567 13.567 3 15.5 3H20.5C22.433 3 24 4.567 24 6.5V10" 
            stroke="#D6D3D1" 
            strokeWidth="2.2" 
            strokeLinecap="round" 
          />
          {/* Dynamic AI Compass / Sparkle in Center */}
          <path 
            d="M18 13L19.5 17.5L24 19L19.5 20.5L18 25L16.5 20.5L12 19L16.5 17.5L18 13Z" 
            fill="url(#amberGradient)" 
          />
          {/* Micro intelligence nodes */}
          <circle cx="23.5" cy="14" r="1.2" fill="#FDE68A" />
          <circle cx="12.5" cy="24" r="1.2" fill="#FDE68A" />

          <defs>
            <linearGradient id="amberGradient" x1="12" y1="13" x2="24" y2="25" gradientUnits="userSpaceOnUse">
              <stop stopColor="#F59E0B" />
              <stop offset="1" stopColor="#D97706" />
            </linearGradient>
          </defs>
        </svg>

        {/* Small golden glow indicator */}
        <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-amber-500 rounded-full border-2 border-white" />
      </div>

      {variant !== 'icon-only' && (
        <div className="flex flex-col text-left">
          <span className="font-bold tracking-tight text-sm text-stone-900 leading-tight">
            Shopping<span className="text-amber-700">AI</span>
          </span>
          <span className="text-[10px] text-stone-500 font-medium">
            Trợ lý mua sắm thông minh
          </span>
        </div>
      )}
    </div>
  );
};
