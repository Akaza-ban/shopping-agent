import React from 'react';
import { X, Store } from 'lucide-react';
import { PLATFORMS } from '../services/shoppingService.ts';
import { DataWarehousePanel } from './DataWarehousePanel.tsx';
import { t } from '../i18n/index.tsx';

interface SettingsModalProps {
  isOpen: boolean;
  enabledPlatformIds: string[];
  onChangePlatforms: (ids: string[]) => void;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  enabledPlatformIds,
  onChangePlatforms,
  onClose,
}) => {
  if (!isOpen) return null;

  const toggle = (id: string, checked: boolean) =>
    onChangePlatforms(checked ? [...enabledPlatformIds, id] : enabledPlatformIds.filter(x => x !== id));

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full shadow-2xl animate-scaleUp overflow-hidden">
        <div className="p-5 border-b border-stone-200 flex items-center justify-between bg-panel">
          <div className="flex items-center gap-2">
            <Store className="w-4 h-4 text-stone-800" />
            <h3 className="text-sm font-bold text-stone-900">{t('Nguồn & kho dữ liệu')}</h3>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg hover:bg-stone-200 flex items-center justify-center text-stone-500"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-6 space-y-2 text-xs max-h-[70vh] overflow-y-auto">
          <div className="text-stone-900 font-bold pb-1">{t('Nguồn dữ liệu được phép thu thập')}</div>
          {PLATFORMS.map((p) => (
            <label key={p.id} className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-stone-50 cursor-pointer">
              <input
                type="checkbox"
                checked={enabledPlatformIds.includes(p.id)}
                onChange={(e) => toggle(p.id, e.target.checked)}
                className="rounded text-stone-900 focus:ring-stone-900"
              />
              <span className="text-stone-800 font-medium">{p.name}</span>
              <span className="text-[11px] text-stone-500">· {t(p.type)}</span>
            </label>
          ))}
          <div className="pt-4 mt-2 border-t border-stone-200">
            <DataWarehousePanel />
          </div>
        </div>

        <div className="p-4 border-t border-stone-200 bg-stone-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-stone-900 text-amber-50 rounded-xl text-xs font-semibold hover:bg-stone-800 transition-colors"
          >
            Xong
          </button>
        </div>
      </div>
    </div>
  );
};
