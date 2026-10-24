import React, { useState, useEffect } from 'react';
import {
  Smartphone,
  Download,
  X,
  Copy,
  Check,
  ExternalLink,
  ShieldCheck,
  Share2,
  Sparkles,
} from 'lucide-react';

interface InstallAppModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const InstallAppModal: React.FC<InstallAppModalProps> = ({ isOpen, onClose }) => {
  const [copied, setCopied] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [isStandalone, setIsStandalone] = useState(false);

  const sharedUrl = window.location.origin;

  useEffect(() => {
    // Check if running standalone
    const standalone =
      window.matchMedia('(display-mode: standalone)').matches ||
      (window.navigator as any).standalone === true;
    setIsStandalone(standalone);

    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstall);
    return () => window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
  }, []);

  if (!isOpen) return null;

  const handleInstallClick = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const choice = await deferredPrompt.userChoice;
      if (choice.outcome === 'accepted') {
        setDeferredPrompt(null);
      }
    }
  };

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(sharedUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-slate-950/80 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="install-modal-title"
    >
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-700 rounded-3xl shadow-2xl flex flex-col max-h-[92vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-4 sm:p-5 border-b border-slate-800 bg-slate-900/90 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-blue-600/20 text-blue-400 flex items-center justify-center border border-blue-500/30">
              <Smartphone className="w-4 h-4" />
            </div>
            <div>
              <h2 id="install-modal-title" className="text-sm font-bold text-white">
                Instalar en tu Celular (PWA / APK)
              </h2>
              <p className="text-[11px] text-slate-400">
                Usa la app en pantalla completa como una aplicación nativa
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            aria-label="Cerrar modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-4 text-xs flex-1">
          {/* Quick Install Button if browser supports beforeinstallprompt */}
          {deferredPrompt && !isStandalone && (
            <div className="p-4 bg-blue-950/60 border border-blue-600/60 rounded-2xl text-center space-y-2">
              <span className="text-xs font-bold text-blue-200 block">
                ¡Tu navegador permite la instalación directa con 1 toque!
              </span>
              <button
                onClick={handleInstallClick}
                className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 min-h-[44px]"
              >
                <Download className="w-4 h-4" />
                <span>Instalar Aplicación en este Dispositivo</span>
              </button>
            </div>
          )}

          {/* Android PWA Installation Steps */}
          <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 space-y-3">
            <h3 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck className="w-4 h-4" />
              <span>Paso a Paso en Celular Android (Sin descargar archivos APK desconocidos)</span>
            </h3>

            <ol className="space-y-2.5 text-slate-300 leading-relaxed text-[11px]">
              <li className="flex gap-2.5 items-start">
                <span className="w-5 h-5 rounded-full bg-slate-800 text-white font-mono font-bold flex items-center justify-center shrink-0 text-[10px]">
                  1
                </span>
                <span>
                  Abre el enlace de la app en <strong className="text-white">Google Chrome</strong> o <strong className="text-white">Samsung Internet</strong> en tu teléfono Android.
                </span>
              </li>
              <li className="flex gap-2.5 items-start">
                <span className="w-5 h-5 rounded-full bg-slate-800 text-white font-mono font-bold flex items-center justify-center shrink-0 text-[10px]">
                  2
                </span>
                <span>
                  Toca el menú de los <strong>tres puntos (⋮)</strong> en la esquina superior derecha del navegador.
                </span>
              </li>
              <li className="flex gap-2.5 items-start">
                <span className="w-5 h-5 rounded-full bg-slate-800 text-white font-mono font-bold flex items-center justify-center shrink-0 text-[10px]">
                  3
                </span>
                <span>
                  Selecciona <strong className="text-emerald-300">"Instalar aplicación"</strong> o <strong className="text-emerald-300">"Agregar a la pantalla principal"</strong>.
                </span>
              </li>
              <li className="flex gap-2.5 items-start">
                <span className="w-5 h-5 rounded-full bg-slate-800 text-white font-mono font-bold flex items-center justify-center shrink-0 text-[10px]">
                  4
                </span>
                <span>
                  ¡Listo! La app se instalará en tu pantalla de inicio con su propio icono, pantalla completa (sin barra de navegador) y funciona offline.
                </span>
              </li>
            </ol>
          </div>

          {/* App URL to open or share */}
          <div className="bg-slate-950 border border-slate-800 rounded-2xl p-3.5 space-y-2">
            <label className="text-[10px] text-slate-400 block font-semibold uppercase tracking-wider">
              Enlace de la Aplicación para tu Celular:
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={sharedUrl}
                className="flex-1 bg-slate-900 border border-slate-800 text-slate-200 text-xs rounded-xl px-3 py-2 font-mono truncate"
              />
              <button
                onClick={handleCopyUrl}
                className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-xl border border-slate-700 transition-colors flex items-center gap-1.5 shrink-0 min-h-[38px]"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copiado' : 'Copiar'}</span>
              </button>
            </div>
          </div>

          {/* Standalone APK Generator info */}
          <div className="bg-slate-950/70 border border-slate-800 rounded-2xl p-3.5 space-y-1.5 text-[11px] text-slate-400 leading-relaxed">
            <span className="text-xs font-bold text-white flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              ¿Necesitas el archivo empaquetado .APK físico?
            </span>
            <p>
              Esta app ya incluye el estándar completo de PWA (Web App Manifest + Service Worker). Si requieres un archivo <code className="text-amber-300 font-mono">.apk</code> para instalarlo vía cable USB o subir a Google Play, puedes generarlo gratis en 1 minuto en{' '}
              <a
                href="https://www.pwabuilder.com/"
                target="_blank"
                rel="noreferrer"
                className="text-blue-400 hover:underline inline-flex items-center gap-0.5"
              >
                PWABuilder.com <ExternalLink className="w-3 h-3" />
              </a>{' '}
              pegando la URL de esta aplicación.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-slate-800 bg-slate-900/90 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-xl"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
};
