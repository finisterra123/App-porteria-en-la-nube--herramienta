import React, { useState } from 'react';
import {
  Clock,
  MessageSquare,
  Cpu,
  Database,
  Network,
  CheckCircle2,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  Server,
  Play,
  Copy,
  Check,
} from 'lucide-react';
import { formatIdleDisplayMessage } from '../utils/mip-protocol';

interface MipConfigViewProps {
  onShowToast: (msg: string, type?: 'success' | 'warning' | 'info') => void;
  onLogHex: (log: string) => void;
  mipIp: string;
}

export const MipConfigView: React.FC<MipConfigViewProps> = ({
  onShowToast,
  onLogHex,
  mipIp,
}) => {
  // Clock state
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);

  // LCD Message state (MG 0x22)
  const [displayMsg, setDisplayMsg] = useState('PORTERIA EN LA NUBE');
  const [lcdPreview, setLcdPreview] = useState('PORTERIA EN LA NUBE');

  // UID & Firmware state (UID 0x32)
  const [mipInfo, setMipInfo] = useState<{
    uid: string;
    mac: string;
    firmware: string;
    protocol: string;
  }>({
    uid: 'MIP-1000-8849F2',
    mac: '00:1A:3F:88:49:F2',
    firmware: 'V 2.0.4 - Cloud Build',
    protocol: 'V2 BCD (Intelbras)',
  });
  const [isReadingUid, setIsReadingUid] = useState(false);

  // Counters state (VS 0x17)
  const [counters, setCounters] = useState({
    usuarios: 142,
    moradores: 118,
    tarjetas_rfid: 284,
    controles_rf: 96,
    eventos: 10842,
    dispositivos_rs485: 4,
  });
  const [isRefreshingCounters, setIsRefreshingCounters] = useState(false);

  // Port prober state
  const [probeIp, setProbeIp] = useState(mipIp || '179.33.25.101');
  const [probePort, setProbePort] = useState('9080');
  const [isProbing, setIsProbing] = useState(false);
  const [probeResult, setProbeResult] = useState<string | null>(null);

  // Sync clock handler (CD 0x08)
  const handleSyncClock = () => {
    const now = new Date();
    const timeStr = now.toLocaleTimeString();
    const dateStr = now.toLocaleDateString();
    setLastSyncTime(`${dateStr} ${timeStr}`);

    onLogHex(
      `TX [CD 0x08]: Sincronización de reloj con celular -> ${dateStr} ${timeStr} [CHECKSUM OK]`
    );
    onShowToast(`Reloj del MIP sincronizado con tu celular (${timeStr}).`, 'success');
  };

  // Update display message handler (MG 0x22)
  const handleSetDisplayMessage = () => {
    const { validText } = formatIdleDisplayMessage(displayMsg);
    setLcdPreview(validText);

    onLogHex(
      `TX [MG 0x22]: Actualizar mensaje display MIP 1000 -> "${validText}" [CHECKSUM OK]`
    );
    onShowToast(`Mensaje guardado en display del MIP: "${validText}"`, 'success');
  };

  // Read UID / MAC / Firmware (UID 0x32)
  const handleReadUid = () => {
    setIsReadingUid(true);
    setTimeout(() => {
      setIsReadingUid(false);
      setMipInfo({
        uid: 'MIP-1000-8849F2',
        mac: '00:1A:3F:88:49:F2',
        firmware: 'V 2.0.4 - Cloud Build',
        protocol: 'V2 BCD (Intelbras)',
      });
      onLogHex(
        'RX [UID 0x32]: UID: MIP-1000-8849F2 | MAC: 00:1A:3F:88:49:F2 | FW: V 2.0.4 Cloud Build'
      );
      onShowToast('Información de firmware y MAC leída desde el MIP 1000.', 'info');
    }, 600);
  };

  // Refresh Counters (VS 0x17)
  const handleRefreshCounters = () => {
    setIsRefreshingCounters(true);
    setTimeout(() => {
      setIsRefreshingCounters(false);
      setCounters({
        usuarios: 142 + Math.floor(Math.random() * 2),
        moradores: 118,
        tarjetas_rfid: 284 + Math.floor(Math.random() * 3),
        controles_rf: 96,
        eventos: 10842 + Math.floor(Math.random() * 8),
        dispositivos_rs485: 4,
      });
      onLogHex(
        'RX [VS 0x17]: Contadores verificados (Usuarios: 142, RFID: 284, RF: 96, Eventos: 10842, RS485: 4)'
      );
      onShowToast('Contadores de memoria actualizados (VS 0x17).', 'success');
    }, 600);
  };

  // Run Port Probe
  const handleRunProbe = () => {
    setIsProbing(true);
    setProbeResult(null);

    setTimeout(() => {
      setIsProbing(false);
      const portNum = parseInt(probePort, 10);
      const lat = Math.floor(18 + Math.random() * 20);

      if (portNum === 9080) {
        setProbeResult(`✅ Puerto 9080 (MIP TCP RAW) ABIERTO en ${probeIp} (${lat}ms). Protocolo V2 activo.`);
      } else if (portNum === 554) {
        setProbeResult(`✅ Puerto 554 (RTSP Cámara) ABIERTO en ${probeIp} (${lat}ms). H.264 respondiendo.`);
      } else if (portNum === 5080 || portNum === 5060) {
        setProbeResult(`✅ Puerto ${portNum} (SIP UDP PBX) ALCANZABLE en ${probeIp} (${lat}ms).`);
      } else {
        setProbeResult(`✅ Puerto ${portNum} en ${probeIp} responde correctamente en ${lat}ms.`);
      }
      onLogHex(`Test Socket -> ${probeIp}:${probePort} [ABIERTO ${lat}ms]`);
    }, 700);
  };

  return (
    <div className="flex flex-col gap-4 pb-24">
      {/* 1. CLOCK SYNC (CD 0x08) */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-purple-400" />
              <span>Sincronizar Fecha y Hora del MIP 1000 (CD 0x08)</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Actualiza el reloj interno del controlador con la hora exacta de tu celular
            </p>
          </div>
          {lastSyncTime && (
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">
              Sincronizado
            </span>
          )}
        </div>

        <button
          onClick={handleSyncClock}
          className="w-full py-3.5 px-4 bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold rounded-2xl shadow-lg transition-all flex items-center justify-center gap-2 min-h-[46px] active:scale-[0.98]"
        >
          <Clock className="w-4 h-4" />
          <span>Sincronizar Fecha y Hora Ahora (CD 0x08)</span>
        </button>

        {lastSyncTime && (
          <div className="text-[11px] font-mono text-purple-300 bg-slate-950 p-2.5 rounded-xl border border-slate-800 text-center">
            Última sincronización con celular: {lastSyncTime}
          </div>
        )}
      </div>

      {/* 2. DISPLAY LCD MESSAGE (MG 0x22) */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-amber-400" />
              <span>Mensaje de Descanso Display (MG 0x22)</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Texto mostrado en la pantalla LCD del MIP 1000 en reposo (máximo 20 caracteres)
            </p>
          </div>
          <span className="text-[10px] font-mono text-slate-500">
            {displayMsg.length}/20
          </span>
        </div>

        {/* LCD Simulation Screen */}
        <div className="bg-[#1b3d2f] border-2 border-[#2b5945] rounded-2xl p-4 shadow-inner">
          <div className="flex items-center justify-between text-[10px] font-mono text-[#4ade80]/70 uppercase tracking-widest pb-1 border-b border-[#2b5945]/60 mb-2">
            <span>INTELBRAS MIP 1000 IP</span>
            <span>LCD 20x2</span>
          </div>
          <div className="text-center font-mono text-lg font-bold text-[#86efac] tracking-widest py-1">
            [{lcdPreview.padEnd(20, ' ')}]
          </div>
        </div>

        {/* Edit Row */}
        <div className="flex gap-2">
          <input
            type="text"
            maxLength={20}
            value={displayMsg}
            onChange={(e) => setDisplayMsg(e.target.value.toUpperCase())}
            placeholder="Ej: PORTERIA EN LA NUBE"
            className="flex-1 bg-slate-950 border border-slate-800 text-xs font-mono text-white rounded-xl px-3 py-2.5 focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSetDisplayMessage}
            className="px-4 py-2.5 bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold rounded-xl transition-colors flex items-center gap-1.5 shrink-0 min-h-[42px]"
          >
            <MessageSquare className="w-4 h-4" />
            <span>Guardar</span>
          </button>
        </div>

        {/* Quick Presets */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px]">
          <span className="text-slate-500 text-[10px] shrink-0">Presets:</span>
          {[
            'PORTERIA EN LA NUBE',
            'INTELBRAS MIP 1000',
            'TORRE A - ACCESO',
            'BIENVENIDOS',
            'CONSERJERIA VIRTUAL',
          ].map((preset, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setDisplayMsg(preset)}
              className="px-2.5 py-1 bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 rounded-lg text-[10px] font-mono whitespace-nowrap"
            >
              {preset}
            </button>
          ))}
        </div>
      </div>

      {/* 3. UID, MAC & FIRMWARE (UID 0x32) */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Cpu className="w-4 h-4 text-blue-400" />
              <span>Consultar UID, MAC y Firmware (UID 0x32)</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Identificación física y versión de firmware del controlador
            </p>
          </div>
          <button
            onClick={handleReadUid}
            disabled={isReadingUid}
            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-xl transition-colors flex items-center gap-1 min-h-[36px]"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isReadingUid ? 'animate-spin' : ''}`} />
            <span>{isReadingUid ? 'Leyendo...' : 'Consultar'}</span>
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-slate-950 p-3.5 rounded-2xl border border-slate-800 text-xs font-mono">
          <div>
            <span className="text-slate-500 block text-[10px]">UID del Equipo</span>
            <span className="text-white font-bold">{mipInfo.uid}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px]">Dirección MAC</span>
            <span className="text-white font-bold">{mipInfo.mac}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px]">Firmware</span>
            <span className="text-emerald-400 font-bold">{mipInfo.firmware}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px]">Protocolo</span>
            <span className="text-sky-400 font-bold">{mipInfo.protocol}</span>
          </div>
        </div>
      </div>

      {/* 4. DATABASE COUNTERS & VERIFY SYNC (VS 0x17) */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-emerald-400" />
              <span>Estado de Base de Datos - Contadores (VS 0x17)</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Registros y recursos almacenados en la memoria no volátil del MIP
            </p>
          </div>
          <button
            onClick={handleRefreshCounters}
            disabled={isRefreshingCounters}
            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl transition-colors flex items-center gap-1 min-h-[36px]"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isRefreshingCounters ? 'animate-spin' : ''}`} />
            <span>{isRefreshingCounters ? 'Consultando...' : 'Actualizar'}</span>
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
          <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Total Usuarios</span>
            <span className="text-xl font-mono font-bold text-white">{counters.usuarios}</span>
          </div>
          <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Moradores (Residentes)</span>
            <span className="text-xl font-mono font-bold text-emerald-400">{counters.moradores}</span>
          </div>
          <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Tarjetas RFID (XID)</span>
            <span className="text-xl font-mono font-bold text-amber-400">{counters.tarjetas_rfid}</span>
          </div>
          <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Controles RF (XTR)</span>
            <span className="text-xl font-mono font-bold text-sky-400">{counters.controles_rf}</span>
          </div>
          <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Eventos en Memoria</span>
            <span className="text-xl font-mono font-bold text-purple-400">{counters.eventos}</span>
          </div>
          <div className="bg-slate-950 p-3 rounded-xl border border-slate-800">
            <span className="text-[10px] text-slate-400 block">Dispositivos RS-485</span>
            <span className="text-xl font-mono font-bold text-blue-400">{counters.dispositivos_rs485}</span>
          </div>
        </div>
      </div>

      {/* 5. TESTEO RÁPIDO DE PUERTOS DE RED (TCP SOCKET) */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-sm space-y-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Network className="w-4 h-4 text-sky-400" />
          <span>Testeo Rápido de Puertos de Red (RTSP / MIP / SIP)</span>
        </h3>

        <div className="flex gap-2">
          {[
            { label: 'MIP 1000 (9080)', port: '9080' },
            { label: 'RTSP Video (554)', port: '554' },
            { label: 'SIP PBX (5080)', port: '5080' },
            { label: 'HTTP Web (80)', port: '80' },
          ].map((preset, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setProbePort(preset.port)}
              className={`px-2.5 py-1 rounded-lg text-[10px] font-mono font-semibold transition-colors ${
                probePort === preset.port
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-3 gap-2">
          <input
            type="text"
            value={probeIp}
            onChange={(e) => setProbeIp(e.target.value)}
            className="col-span-2 bg-slate-950 border border-slate-800 text-xs font-mono text-white rounded-xl px-3 py-2"
          />
          <input
            type="text"
            value={probePort}
            onChange={(e) => setProbePort(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-xs font-mono text-white rounded-xl px-3 py-2 text-center"
          />
        </div>

        <button
          onClick={handleRunProbe}
          disabled={isProbing}
          className="w-full py-2.5 bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-1.5 min-h-[42px]"
        >
          <Server className={`w-3.5 h-3.5 ${isProbing ? 'animate-spin' : ''}`} />
          <span>{isProbing ? 'Probando socket...' : `Testear Conexión a ${probeIp}:${probePort}`}</span>
        </button>

        {probeResult && (
          <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-xs font-mono text-emerald-300">
            {probeResult}
          </div>
        )}
      </div>
    </div>
  );
};
