/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { Header } from './components/Header';
import { BottomNav, ActiveToolTab } from './components/BottomNav';
import { DoorsControlView } from './components/DoorsControlView';
import { MipConfigView } from './components/MipConfigView';
import { SipTestingView } from './components/SipTestingView';
import { CamerasTestingView } from './components/CamerasTestingView';
import { CredentialsView } from './components/CredentialsView';
import { InstallAppModal } from './components/InstallAppModal';
import { CheckCircle2, AlertTriangle, Info, Terminal, ChevronDown, ChevronUp } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState<ActiveToolTab>('doors');
  const [isMIPConnected, setIsMIPConnected] = useState(true);
  const [mipIp, setMipIp] = useState('179.33.25.101');
  const [isInstallModalOpen, setIsInstallModalOpen] = useState(false);

  // Shared Hexadecimal Protocol Console Stream (from Python script)
  const [hexLogs, setHexLogs] = useState<string[]>([
    'Consola Hexadecimal Protocolo V2 (MIP 1000 IP) - Inicializada.',
    'RX [VS 0x17]: Conexión establecida con 179.33.25.101:9080 [Header: BCD].',
    'RX [VS 0x17]: 4 módulos RS-485 activos (XRE #1 Dir 2, XRE #2 Dir 3, XPE Dir 4).',
  ]);
  const [isConsoleExpanded, setIsConsoleExpanded] = useState(false);

  // In-app toast feedback
  const [toastMessage, setToastMessage] = useState<{
    text: string;
    type: 'success' | 'warning' | 'info';
  } | null>(null);

  const showToast = (text: string, type: 'success' | 'warning' | 'info' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => {
      setToastMessage(null);
    }, 3200);
  };

  const handleLogHex = (log: string) => {
    setHexLogs((prev) => [log, ...prev.slice(0, 40)]);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* 1. Header with Requested Branding */}
      <Header
        isMIPConnected={isMIPConnected}
        onToggleConnection={() => {
          setIsMIPConnected(!isMIPConnected);
          const newStatus = !isMIPConnected;
          handleLogHex(
            newStatus
              ? `[${new Date().toLocaleTimeString()}] TCP CONNECT: Conectado a ${mipIp}:9080 [OK]`
              : `[${new Date().toLocaleTimeString()}] TCP DISCONNECT: Sesión cerrada con el MIP 1000 IP.`
          );
          showToast(
            newStatus
              ? 'Conectado al controlador MIP 1000 IP.'
              : 'MIP 1000 IP desconectado.',
            newStatus ? 'success' : 'info'
          );
        }}
        mipIp={mipIp}
        onOpenInstallModal={() => setIsInstallModalOpen(true)}
      />

      {/* 2. Main Tool Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-3 sm:p-5 lg:p-6 pb-40">
        {activeTab === 'doors' && (
          <DoorsControlView
            isMIPConnected={isMIPConnected}
            onToggleConnection={() => setIsMIPConnected(!isMIPConnected)}
            onShowToast={showToast}
            onLogHex={handleLogHex}
            mipIp={mipIp}
          />
        )}

        {activeTab === 'config' && (
          <MipConfigView
            onShowToast={showToast}
            onLogHex={handleLogHex}
            mipIp={mipIp}
          />
        )}

        {activeTab === 'sip' && <SipTestingView />}

        {activeTab === 'cameras' && (
          <CamerasTestingView
            onTriggerDoorRelay={(devAddr, relay) => {
              handleLogHex(
                `TX [ASR 0x18]: Apertura de portón asociado bajo cámara -> Dir RS-485 ${devAddr} Relé ${relay}`
              );
              showToast(`Comando ASR enviado a Dir RS-485 ${devAddr} Relé ${relay}. Puerta abierta 3s.`, 'success');
            }}
            onShowToast={showToast}
          />
        )}

        {activeTab === 'credentials' && <CredentialsView />}
      </main>

      {/* 3. Live Protocol Hex Console (Footer pinned above nav bar, just like in Python script) */}
      <aside
        aria-label="Consola de Tramas Hexadecimales"
        className="fixed bottom-16 left-0 right-0 z-30 bg-slate-950/95 border-t border-slate-800 backdrop-blur-md transition-all shadow-2xl"
      >
        <div className="max-w-7xl mx-auto px-3 sm:px-4 py-1.5 flex items-center justify-between text-xs border-b border-slate-900">
          <div className="flex items-center gap-2 text-slate-400 font-mono text-[11px]">
            <Terminal className="w-3.5 h-3.5 text-emerald-400" />
            <span className="font-bold text-slate-300">Consola Hexadecimal (TX/RX Protocolo V2)</span>
            <span className="text-slate-600">·</span>
            <span className="text-[10px] text-emerald-400 truncate max-w-[180px] sm:max-w-md">
              {hexLogs[0] || 'En espera de tramas...'}
            </span>
          </div>

          <button
            onClick={() => setIsConsoleExpanded(!isConsoleExpanded)}
            className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white px-2 py-0.5 rounded transition-colors"
          >
            <span>{isConsoleExpanded ? 'Ocultar' : 'Ver Registro'}</span>
            {isConsoleExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
          </button>
        </div>

        {isConsoleExpanded && (
          <div className="max-w-7xl mx-auto p-3 font-mono text-[11px] text-emerald-400 space-y-1 max-h-40 overflow-y-auto">
            {hexLogs.map((log, index) => (
              <div key={index} className="leading-tight truncate">
                {log}
              </div>
            ))}
          </div>
        )}
      </aside>

      {/* 4. In-App Toast Notification */}
      {toastMessage && (
        <div
          className={`fixed top-16 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 rounded-xl shadow-2xl flex items-center gap-2 text-xs font-semibold backdrop-blur-md transition-all animate-in fade-in slide-in-from-top-3 ${
            toastMessage.type === 'warning'
              ? 'bg-red-950 border border-red-700 text-red-200'
              : toastMessage.type === 'info'
              ? 'bg-blue-950 border border-blue-700 text-blue-200'
              : 'bg-emerald-950 border border-emerald-700 text-emerald-200'
          }`}
        >
          {toastMessage.type === 'warning' ? (
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
          ) : toastMessage.type === 'info' ? (
            <Info className="w-4 h-4 text-blue-400 shrink-0" />
          ) : (
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* 5. Install App Modal */}
      <InstallAppModal
        isOpen={isInstallModalOpen}
        onClose={() => setIsInstallModalOpen(false)}
      />

      {/* 6. Fixed Mobile Bottom Navigation */}
      <BottomNav activeTab={activeTab} onChangeTab={(tab) => setActiveTab(tab)} />
    </div>
  );
}
