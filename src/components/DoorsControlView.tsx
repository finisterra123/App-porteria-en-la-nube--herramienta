import React, { useState, useEffect } from 'react';
import {
  KeyRound,
  Zap,
  Play,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sliders,
  Layers,
  Radio,
} from 'lucide-react';
import { MipDoor, getDefaultDoorsList, buildAsrCommand } from '../utils/mip-protocol';

interface DoorsControlViewProps {
  isMIPConnected: boolean;
  onToggleConnection: () => void;
  onShowToast: (msg: string, type?: 'success' | 'warning' | 'info') => void;
  onLogHex: (log: string) => void;
  mipIp: string;
}

export const DoorsControlView: React.FC<DoorsControlViewProps> = ({
  isMIPConnected,
  onToggleConnection,
  onShowToast,
  onLogHex,
  mipIp,
}) => {
  // Connection parameters
  const [ip, setIp] = useState(mipIp || '179.33.25.101');
  const [port, setPort] = useState('9080');
  const [login, setLogin] = useState('admin');
  const [password, setPassword] = useState('123456');
  const [headerFmt, setHeaderFmt] = useState<'bcd' | 'int_le' | 'zero'>('bcd');

  // Doors list
  const [doors, setDoors] = useState<MipDoor[]>(getDefaultDoorsList());
  const [activeDoorId, setActiveDoorId] = useState<string | null>(null);
  const [activeCountdown, setActiveCountdown] = useState<number>(0);

  // Manual RS-485 Trigger
  const [customDevAddr, setCustomDevAddr] = useState<number>(2);
  const [customRelay, setCustomRelay] = useState<number>(1);
  const [isCustomActive, setIsCustomActive] = useState(false);

  // Handle countdown for active relay
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (activeCountdown > 0) {
      timer = setTimeout(() => {
        setActiveCountdown((prev) => prev - 1);
      }, 1000);
    } else if (activeCountdown === 0 && activeDoorId) {
      setDoors((prev) =>
        prev.map((d) => (d.id === activeDoorId ? { ...d, isUnlocked: false } : d))
      );
      setActiveDoorId(null);
      setIsCustomActive(false);
      onLogHex(
        `[${new Date().toLocaleTimeString()}] Relé liberado. Contacto normalmente abierto restablecido.`
      );
    }
    return () => clearTimeout(timer);
  }, [activeCountdown, activeDoorId, onLogHex]);

  // Trigger Door Relay Action (ASR 0x18)
  const handleTriggerDoor = (door: MipDoor) => {
    const { hexCommand, log } = buildAsrCommand(door.devAddr, door.relay);

    setActiveDoorId(door.id);
    setActiveCountdown(3);
    setDoors((prev) =>
      prev.map((d) =>
        d.id === door.id
          ? { ...d, isUnlocked: true, lastTriggered: new Date().toLocaleTimeString() }
          : d
      )
    );

    onLogHex(`[${new Date().toLocaleTimeString()}] ${hexCommand} | ${log} [ABIERTO 3s]`);
    onShowToast(`🔓 ${door.name} abierta con éxito (Comando ASR 0x18).`, 'success');
  };

  // Manual Trigger
  const handleCustomTrigger = () => {
    const { hexCommand, log } = buildAsrCommand(customDevAddr, customRelay);
    setIsCustomActive(true);
    setActiveCountdown(3);
    onLogHex(`[${new Date().toLocaleTimeString()}] ${hexCommand} | ${log} [ABIERTO 3s]`);
    onShowToast(`Pulso ASR enviado a Dirección RS-485 ${customDevAddr} Relé ${customRelay}.`, 'info');
  };

  return (
    <div className="flex flex-col gap-4 pb-24">
      {/* 1. Connection Header Box */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-4 sm:p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div
              className={`w-3 h-3 rounded-full ${
                isMIPConnected
                  ? 'bg-emerald-400 shadow-sm shadow-emerald-500 animate-pulse'
                  : 'bg-red-500'
              }`}
            />
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <span>Parámetros TCP MIP 1000 IP</span>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded border font-bold ${
                  isMIPConnected
                    ? 'bg-emerald-950/80 border-emerald-800 text-emerald-300'
                    : 'bg-red-950/80 border-red-800 text-red-300'
                }`}
              >
                {isMIPConnected ? 'CONECTADO' : 'DESCONECTADO'}
              </span>
            </h2>
          </div>

          <button
            onClick={onToggleConnection}
            className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all shadow min-h-[36px] ${
              isMIPConnected
                ? 'bg-red-950/80 hover:bg-red-900 text-red-300 border border-red-800'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white'
            }`}
          >
            {isMIPConnected ? 'Desconectar' : 'Conectar al MIP'}
          </button>
        </div>

        {/* Inputs */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">IP del MIP:</label>
            <input
              type="text"
              value={ip}
              onChange={(e) => setIp(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded-lg px-2.5 py-1.5 font-mono text-xs"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Puerto:</label>
            <input
              type="text"
              value={port}
              onChange={(e) => setPort(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded-lg px-2.5 py-1.5 font-mono text-xs"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Login:</label>
            <input
              type="text"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded-lg px-2.5 py-1.5 text-xs"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Header:</label>
            <select
              value={headerFmt}
              onChange={(e) => setHeaderFmt(e.target.value as any)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded-lg px-2 py-1.5 text-xs font-mono"
            >
              <option value="bcd">bcd (Protocolo V2)</option>
              <option value="int_le">int_le</option>
              <option value="zero">zero</option>
            </select>
          </div>
        </div>
      </div>

      {/* 2. BOTONERA TÁCTIL DE TODAS LAS PUERTAS (ASR 0x18) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <KeyRound className="w-4 h-4 text-amber-400" />
              <span>Botonera de Apertura de Puertas (MIP + XRE 1000)</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Presiona para accionar inmediatamente la salida del relevador (ASR 0x18)
            </p>
          </div>
          <span className="text-xs font-mono font-bold text-blue-400 bg-blue-950 px-2 py-0.5 rounded border border-blue-800">
            {doors.length} Puertas
          </span>
        </div>

        {/* Tactical Keypad Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {doors.map((door) => {
            const isThisUnlocked = activeDoorId === door.id && activeCountdown > 0;

            return (
              <div
                key={door.id}
                className={`p-4 rounded-2xl border transition-all flex flex-col justify-between ${
                  isThisUnlocked
                    ? 'bg-emerald-950/80 border-emerald-500 shadow-xl ring-2 ring-emerald-500/40'
                    : 'bg-slate-900 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <span
                      className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border uppercase ${
                        door.type.includes('XRE')
                          ? 'bg-blue-950 text-blue-300 border-blue-800'
                          : door.type.includes('MIP')
                          ? 'bg-purple-950 text-purple-300 border-purple-800'
                          : 'bg-slate-800 text-slate-300 border-slate-700'
                      }`}
                    >
                      {door.type} · Dir {door.devAddr}
                    </span>
                    <span className="text-xs font-mono text-slate-400">
                      Relé #{door.relay}
                    </span>
                  </div>

                  <h4 className="text-sm font-bold text-white">{door.name}</h4>
                  <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">
                    {door.description}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between gap-2">
                  <span className="text-[11px] text-slate-500 font-mono">
                    {door.lastTriggered ? `Última: ${door.lastTriggered}` : 'Sin apertura'}
                  </span>

                  <button
                    onClick={() => handleTriggerDoor(door)}
                    disabled={isThisUnlocked}
                    className={`py-2 px-4 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 active:scale-95 min-h-[44px] ${
                      isThisUnlocked
                        ? 'bg-emerald-500 text-white animate-pulse'
                        : 'bg-blue-600 hover:bg-blue-500 text-white shadow-md'
                    }`}
                  >
                    <Zap className="w-4 h-4" />
                    <span>
                      {isThisUnlocked ? `ABIERTO (${activeCountdown}s)` : 'ABRIR AHORA'}
                    </span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. DISPARADOR MANUAL UNIVERSAL RS-485 (1..24, RELÉ 1..8) */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Zap className="w-3.5 h-3.5 text-yellow-400" />
            <span>Disparador Manual por Dirección RS-485 (1 al 24)</span>
          </h3>
          {isCustomActive && (
            <span className="text-[10px] font-mono text-emerald-400 font-bold animate-pulse">
              PULSO ACTIVO ({activeCountdown}s)
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 items-end">
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">
              Dirección RS-485 (1=MIP, 2..24=Módulos):
            </label>
            <input
              type="number"
              min={1}
              max={24}
              value={customDevAddr}
              onChange={(e) => setCustomDevAddr(parseInt(e.target.value, 10) || 1)}
              className="w-full bg-slate-950 border border-slate-800 text-xs font-mono text-white rounded-xl px-3 py-2"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Salida / Relé (1..8):</label>
            <input
              type="number"
              min={1}
              max={8}
              value={customRelay}
              onChange={(e) => setCustomRelay(parseInt(e.target.value, 10) || 1)}
              className="w-full bg-slate-950 border border-slate-800 text-xs font-mono text-white rounded-xl px-3 py-2"
            />
          </div>
          <button
            onClick={handleCustomTrigger}
            disabled={isCustomActive}
            className="w-full py-2 px-3 bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white text-xs font-bold rounded-xl shadow min-h-[40px] flex items-center justify-center gap-1.5 transition-all"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>{isCustomActive ? 'Accionando...' : 'Accionar Salida ASR'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
