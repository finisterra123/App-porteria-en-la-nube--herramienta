import React from 'react';
import { Shield, Wifi, WifiOff, RefreshCw } from 'lucide-react';

interface HeaderProps {
  isMIPConnected: boolean;
  onToggleConnection: () => void;
  mipIp: string;
  onOpenInstallModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  isMIPConnected,
  onToggleConnection,
  mipIp,
  onOpenInstallModal,
}) => {
  return (
    <header className="sticky top-0 z-30 bg-slate-900 border-b border-slate-800 text-white px-3 sm:px-4 py-2.5 shadow-md">
      <div className="max-w-7xl mx-auto flex items-center justify-between gap-3">
        {/* Brand Zone with Requested Name */}
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20 text-white font-bold shrink-0">
            <Shield className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="text-xs sm:text-sm font-bold tracking-tight text-white truncate">
                herramienta Mip 1000 ip
              </h1>
              <span className="hidden xs:inline-block text-[10px] font-semibold text-emerald-400 bg-emerald-950/80 border border-emerald-800/80 rounded px-1.5 py-0.2 shrink-0 font-mono">
                V2.0
              </span>
            </div>
            <p className="text-[10px] text-blue-400 font-semibold truncate">
              by ING Ricardo Rodriguez
            </p>
          </div>
        </div>

        {/* Connection Control, Install App Button & Status Badge */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          {/* Install / APK button */}
          <button
            onClick={onOpenInstallModal}
            className="flex items-center gap-1 px-2.5 py-1.5 bg-blue-600/90 hover:bg-blue-500 text-white text-xs font-bold rounded-lg shadow-sm border border-blue-500 transition-all active:scale-95 min-h-[34px]"
            title="Instalar en tu celular o generar APK"
          >
            <span>📲</span>
            <span className="hidden xs:inline">Instalar / APK</span>
          </button>

          <div className="flex items-center gap-1.5 bg-slate-950 px-2 py-1 rounded-lg border border-slate-800 text-[11px] font-mono">
            <span
              className={`w-2 h-2 rounded-full shrink-0 ${
                isMIPConnected
                  ? 'bg-emerald-400 shadow-sm shadow-emerald-500 animate-pulse'
                  : 'bg-red-500'
              }`}
            />
            <span
              className={`font-bold ${
                isMIPConnected ? 'text-emerald-400' : 'text-red-400'
              }`}
            >
              {isMIPConnected ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>

          <button
            onClick={onToggleConnection}
            className={`flex items-center gap-1 p-2 sm:px-2.5 sm:py-1.5 text-xs font-bold rounded-lg border transition-all active:scale-95 shadow-sm min-h-[34px] ${
              isMIPConnected
                ? 'bg-red-950/80 border-red-800 text-red-300 hover:bg-red-900'
                : 'bg-emerald-600 border-emerald-500 text-white hover:bg-emerald-500'
            }`}
            title={isMIPConnected ? 'Desconectar del MIP' : 'Conectar al MIP 1000 IP'}
            aria-label={isMIPConnected ? 'Desconectar' : 'Conectar'}
          >
            {isMIPConnected ? <WifiOff className="w-3.5 h-3.5" /> : <Wifi className="w-3.5 h-3.5" />}
            <span className="hidden md:inline">{isMIPConnected ? 'Desconectar' : 'Conectar'}</span>
          </button>
        </div>
      </div>
    </header>
  );
};
