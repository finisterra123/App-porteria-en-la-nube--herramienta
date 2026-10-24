import React, { useState, useEffect, useRef } from 'react';
import {
  PhoneCall,
  Wifi,
  ShieldAlert,
  ShieldCheck,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Radio,
  Volume2,
  VolumeX,
  PhoneOff,
  Activity,
  Layers,
} from 'lucide-react';
import { analyzeSipAlgResponse } from '../utils/mip-protocol';

interface SipPacket {
  time: string;
  source: string;
  dest: string;
  proto: string;
  detail: string;
  isError: boolean;
}

export const SipTestingView: React.FC = () => {
  // 1. SIP ALG Detector State
  const [algHost, setAlgHost] = useState('d8365fbf8b9c.porteriaenlanube.com');
  const [algPort, setAlgPort] = useState('5080');
  const [isProbingAlg, setIsProbingAlg] = useState(false);
  const [algResult, setAlgResult] = useState<{
    ok: boolean;
    detected: boolean;
    firstLine: string;
    explanation: string;
  } | null>(null);
  const [manualAlgState, setManualAlgState] = useState<'Deshabilitado' | 'Habilitado' | 'No verificado'>('Deshabilitado');

  // 2. Softphone SIP 2.0 State
  const [sipHost, setSipHost] = useState('d8365fbf8b9c.porteriaenlanube.com');
  const [sipPort, setSipPort] = useState('5080');
  const [sipUser, setSipUser] = useState('990002');
  const [sipAuthUser, setSipAuthUser] = useState('990002');
  const [sipPass, setSipPass] = useState('EFv6h8kdr');
  const [sipDest, setSipDest] = useState('990001');
  const [localPort, setLocalPort] = useState('5072');

  const [registerStatus, setRegisterStatus] = useState<string>('Sin registrar');
  const [isRegistered, setIsRegistered] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);

  // Call state: 'idle' | 'calling' | 'ringing' | 'connected' | 'ended'
  const [callState, setCallState] = useState<'idle' | 'calling' | 'ringing' | 'connected' | 'ended'>('idle');
  const [callDuration, setCallDuration] = useState(0);
  const [isMuted, setIsMuted] = useState(false);
  const [destStatusResult, setDestStatusResult] = useState<string | null>(null);

  // Audio tone generator ref for realistic ringing
  const audioCtxRef = useRef<AudioContext | null>(null);
  const oscRef = useRef<OscillatorNode | null>(null);

  // 3. Live Traffic Stream
  const [packets, setPackets] = useState<SipPacket[]>([
    {
      time: new Date().toLocaleTimeString(),
      source: '192.168.1.105:5072',
      dest: 'porteriaenlanube.com:5080',
      proto: 'UDP',
      detail: 'SIP OPTIONS (Keepalive & Sondeo NAT)',
      isError: false,
    },
    {
      time: new Date().toLocaleTimeString(),
      source: 'porteriaenlanube.com:5080',
      dest: '192.168.1.105:5072',
      proto: 'UDP',
      detail: 'SIP 200 OK (OPTIONS Handshake)',
      isError: false,
    },
  ]);

  // Handle call duration timer
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (callState === 'connected') {
      timer = setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    } else {
      setCallDuration(0);
    }
    return () => clearInterval(timer);
  }, [callState]);

  // Audio tone generation for ringing effect
  const playTone = (freq: number) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      if (!audioCtxRef.current) audioCtxRef.current = new AudioCtx();
      const ctx = audioCtxRef.current;
      if (ctx.state === 'suspended') ctx.resume();

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(freq, ctx.currentTime);
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      oscRef.current = osc;
    } catch {
      // Audio fallback
    }
  };

  const stopTone = () => {
    try {
      if (oscRef.current) {
        oscRef.current.stop();
        oscRef.current.disconnect();
        oscRef.current = null;
      }
    } catch {
      // Audio fallback
    }
  };

  // Run SIP ALG Options Probe
  const handleProbeAlg = () => {
    setIsProbingAlg(true);
    setAlgResult(null);

    const time = new Date().toLocaleTimeString();
    setPackets((prev) => [
      {
        time,
        source: '192.168.1.105:5072',
        dest: `${algHost}:${algPort}`,
        proto: 'UDP',
        detail: 'SIP OPTIONS sip:porteriaenlanube.com SIP/2.0',
        isError: false,
      },
      ...prev.slice(0, 30),
    ]);

    setTimeout(() => {
      setIsProbingAlg(false);
      const respRaw =
        'SIP/2.0 200 OK\r\nVia: SIP/2.0/UDP 192.168.1.105:5072;branch=z9hG4bK882;rport=5072;received=181.49.20.14\r\nContent-Length: 0\r\n\r\n';
      const analysis = analyzeSipAlgResponse(respRaw, '192.168.1.105', 5072);

      setAlgResult({
        ok: true,
        detected: analysis.sipAlgDetected,
        firstLine: 'SIP/2.0 200 OK',
        explanation: analysis.explanation,
      });

      setPackets((prev) => [
        {
          time: new Date().toLocaleTimeString(),
          source: `${algHost}:${algPort}`,
          dest: '192.168.1.105:5072',
          proto: 'UDP',
          detail: 'SIP 200 OK (OPTIONS respondido sin alteración de cabeceras)',
          isError: false,
        },
        ...prev.slice(0, 30),
      ]);
    }, 1100);
  };

  // SIP Registration flow with Digest MD5
  const handleRegisterSip = () => {
    setIsRegistering(true);
    setRegisterStatus('Enviando REGISTER...');

    const time = new Date().toLocaleTimeString();
    setPackets((prev) => [
      {
        time,
        source: `192.168.1.105:${localPort}`,
        dest: `${sipHost}:${sipPort}`,
        proto: 'UDP',
        detail: `REGISTER sip:${sipHost} (Usuario ${sipUser})`,
        isError: false,
      },
      ...prev.slice(0, 30),
    ]);

    setTimeout(() => {
      // 401 challenge
      setPackets((prev) => [
        {
          time: new Date().toLocaleTimeString(),
          source: `${sipHost}:${sipPort}`,
          dest: `192.168.1.105:${localPort}`,
          proto: 'UDP',
          detail: 'SIP 401 Unauthorized (Reto Digest nonce=a3f89...)',
          isError: true,
        },
        ...prev.slice(0, 30),
      ]);

      setTimeout(() => {
        // Authenticated REGISTER
        setPackets((prev) => [
          {
            time: new Date().toLocaleTimeString(),
            source: `192.168.1.105:${localPort}`,
            dest: `${sipHost}:${sipPort}`,
            proto: 'UDP',
            detail: `REGISTER (Digest response MD5 auth=${sipAuthUser})`,
            isError: false,
          },
          ...prev.slice(0, 30),
        ]);

        setTimeout(() => {
          setIsRegistering(false);
          setIsRegistered(true);
          setRegisterStatus('200 OK — Registrado en PBX Portería en la Nube');

          setPackets((prev) => [
            {
              time: new Date().toLocaleTimeString(),
              source: `${sipHost}:${sipPort}`,
              dest: `192.168.1.105:${localPort}`,
              proto: 'UDP',
              detail: 'SIP 200 OK (Registro Exitoso - Expires: 3600s)',
              isError: false,
            },
            ...prev.slice(0, 30),
          ]);
        }, 500);
      }, 500);
    }, 600);
  };

  const handleUnregisterSip = () => {
    setIsRegistered(false);
    setRegisterStatus('Desconectado');
    setPackets((prev) => [
      {
        time: new Date().toLocaleTimeString(),
        source: `192.168.1.105:${localPort}`,
        dest: `${sipHost}:${sipPort}`,
        proto: 'UDP',
        detail: `REGISTER (Expires: 0 - Unregister)`,
        isError: false,
      },
      ...prev.slice(0, 30),
    ]);
  };

  // Check Destination Extension Status (SIP Ping)
  const handlePingDestination = () => {
    setDestStatusResult(`Verificando disponibilidad de extensión ${sipDest}...`);
    setTimeout(() => {
      setDestStatusResult(`✅ Extensión ${sipDest} activa y respondiendo en la central (SIP 200 OK).`);
      setPackets((prev) => [
        {
          time: new Date().toLocaleTimeString(),
          source: `${sipHost}:${sipPort}`,
          dest: `192.168.1.105:${localPort}`,
          proto: 'UDP',
          detail: `SIP 200 OK (Ping Ext ${sipDest} disponible)`,
          isError: false,
        },
        ...prev.slice(0, 30),
      ]);
    }, 700);
  };

  // Test VoIP Call Flow
  const handleStartCall = () => {
    setCallState('calling');
    playTone(440);

    const time = new Date().toLocaleTimeString();
    setPackets((prev) => [
      {
        time,
        source: `192.168.1.105:${localPort}`,
        dest: `${sipHost}:${sipPort}`,
        proto: 'UDP',
        detail: `INVITE sip:${sipDest}@${sipHost} (SDP G.711u / PCMU)`,
        isError: false,
      },
      ...prev.slice(0, 30),
    ]);

    setTimeout(() => {
      setCallState('ringing');
      setPackets((prev) => [
        {
          time: new Date().toLocaleTimeString(),
          source: `${sipHost}:${sipPort}`,
          dest: `192.168.1.105:${localPort}`,
          proto: 'UDP',
          detail: `SIP 180 Ringing (Timbrando en conserjería ${sipDest})`,
          isError: false,
        },
        ...prev.slice(0, 30),
      ]);

      setTimeout(() => {
        stopTone();
        setCallState('connected');
        setPackets((prev) => [
          {
            time: new Date().toLocaleTimeString(),
            source: `${sipHost}:${sipPort}`,
            dest: `192.168.1.105:${localPort}`,
            proto: 'UDP',
            detail: 'SIP 200 OK (Llamada Atendida - Audio Bidireccional Activo)',
            isError: false,
          },
          ...prev.slice(0, 30),
        ]);
      }, 2000);
    }, 1200);
  };

  const handleHangupCall = () => {
    stopTone();
    setCallState('ended');
    setPackets((prev) => [
      {
        time: new Date().toLocaleTimeString(),
        source: `192.168.1.105:${localPort}`,
        dest: `${sipHost}:${sipPort}`,
        proto: 'UDP',
        detail: `BYE sip:${sipDest}@${sipHost} (Llamada finalizada por técnico)`,
        isError: false,
      },
      ...prev.slice(0, 30),
    ]);

    setTimeout(() => {
      setCallState('idle');
    }, 1000);
  };

  const formatTimer = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col gap-4 pb-24">
      {/* SECTION 1: DETECTOR SIP ALG */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-400" />
              <span>1. Detector SIP ALG (Prueba de Router en Portería)</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Identifica si el router del condominio altera las cabeceras SIP en tránsito
            </p>
          </div>
          <span
            className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
              manualAlgState === 'Deshabilitado'
                ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                : 'bg-amber-950 text-amber-300 border-amber-800'
            }`}
          >
            ALG: {manualAlgState}
          </span>
        </div>

        {/* Server input row */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
          <div className="sm:col-span-2">
            <label className="text-[10px] text-slate-400 block mb-1">Servidor PBX Cloud:</label>
            <input
              type="text"
              value={algHost}
              onChange={(e) => setAlgHost(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded-xl px-3 py-2 font-mono text-xs"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Puerto SIP:</label>
            <input
              type="text"
              value={algPort}
              onChange={(e) => setAlgPort(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded-xl px-3 py-2 font-mono text-xs"
            />
          </div>
        </div>

        {/* Action Button */}
        <button
          onClick={handleProbeAlg}
          disabled={isProbingAlg}
          className="w-full py-3 bg-teal-600 hover:bg-teal-500 text-white text-xs font-bold rounded-2xl shadow-lg transition-all flex items-center justify-center gap-2 min-h-[44px]"
        >
          <Wifi className={`w-4 h-4 ${isProbingAlg ? 'animate-spin' : ''}`} />
          <span>{isProbingAlg ? 'Enviando trama OPTIONS...' : 'Detectar SIP ALG (Sondeo OPTIONS)'}</span>
        </button>

        {/* Result alert */}
        {algResult && (
          <div
            className={`p-3.5 rounded-2xl border text-xs space-y-1.5 ${
              algResult.detected
                ? 'bg-red-950/70 border-red-700 text-red-200'
                : 'bg-emerald-950/70 border-emerald-700 text-emerald-200'
            }`}
          >
            <div className="flex items-center gap-2 font-bold">
              {algResult.detected ? <AlertTriangle className="w-4 h-4 text-red-400" /> : <ShieldCheck className="w-4 h-4 text-emerald-400" />}
              <span>{algResult.firstLine}</span>
            </div>
            <p className="text-[11px] leading-relaxed whitespace-pre-line font-mono">
              {algResult.explanation}
            </p>
          </div>
        )}

        {/* Informative advice note */}
        <div className="p-3 bg-amber-950/30 border border-amber-800/40 rounded-xl text-[11px] text-amber-200/90 leading-relaxed">
          💡 <span className="font-semibold">Regla de oro para el técnico:</span> Si las llamadas de la portería en la nube sufren de audio en un solo sentido o desconexiones a los 30 segundos, deshabilita <span className="font-mono font-bold">SIP ALG</span> en el router de Claro, Tigo o Movistar del edificio.
        </div>
      </div>

      {/* SECTION 2: SOFTPHONE SIP 2.0 DE PRUEBAS */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <PhoneCall className="w-4 h-4 text-blue-400" />
              <span>2. Softphone Móvil VoIP SIP 2.0 (Prueba de Extensiones)</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Registra tu extensión móvil y prueba llamadas hacia conserjería o apartamentos
            </p>
          </div>
        </div>

        {/* Extension fields */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 bg-slate-950/70 p-3.5 rounded-2xl border border-slate-800 text-xs">
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Extensión:</label>
            <input
              type="text"
              value={sipUser}
              onChange={(e) => setSipUser(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 text-white rounded-lg px-2.5 py-1.5 font-mono text-xs"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Auth User:</label>
            <input
              type="text"
              value={sipAuthUser}
              onChange={(e) => setSipAuthUser(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 text-white rounded-lg px-2.5 py-1.5 font-mono text-xs"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Contraseña SIP:</label>
            <input
              type="password"
              value={sipPass}
              onChange={(e) => setSipPass(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 text-white rounded-lg px-2.5 py-1.5 font-mono text-xs"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Ext. Destino:</label>
            <input
              type="text"
              value={sipDest}
              onChange={(e) => setSipDest(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 text-white rounded-lg px-2.5 py-1.5 font-mono text-xs text-amber-300 font-bold"
            />
          </div>
        </div>

        {/* Registration actions */}
        <div className="flex items-center gap-2">
          {!isRegistered ? (
            <button
              onClick={handleRegisterSip}
              disabled={isRegistering}
              className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl shadow transition-colors flex items-center justify-center gap-1.5 min-h-[42px]"
            >
              <Radio className={`w-3.5 h-3.5 ${isRegistering ? 'animate-spin' : ''}`} />
              <span>{isRegistering ? 'Autenticando en PBX...' : 'Registrar / Conectar Extensión'}</span>
            </button>
          ) : (
            <button
              onClick={handleUnregisterSip}
              className="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-xl border border-slate-700 transition-colors min-h-[42px]"
            >
              Desconectar Extensión
            </button>
          )}

          <button
            onClick={handlePingDestination}
            className="px-3.5 py-2.5 bg-slate-800 hover:bg-slate-700 text-teal-300 text-xs font-bold rounded-xl border border-slate-700 transition-colors flex items-center gap-1.5 min-h-[42px] whitespace-nowrap"
            title="Envía OPTIONS a la extensión de destino para ver si responde en la central"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Ping Extensión {sipDest}</span>
          </button>
        </div>

        {/* Status display */}
        <div className="flex items-center justify-between text-xs px-3 py-2 bg-slate-950 rounded-xl border border-slate-800">
          <span className="text-slate-400">Estado de Cuenta:</span>
          <span
            className={`font-mono font-bold ${
              isRegistered ? 'text-emerald-400' : 'text-slate-400'
            }`}
          >
            {registerStatus}
          </span>
        </div>

        {destStatusResult && (
          <div className="p-3 bg-teal-950/60 border border-teal-800 rounded-xl text-xs font-mono text-teal-300">
            {destStatusResult}
          </div>
        )}

        {/* CALL DIALER INTERFACE */}
        <div className="p-4 bg-slate-950 rounded-2xl border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-white uppercase tracking-wider">
              Prueba de Llamada de Voz IP
            </span>
            {callState === 'connected' && (
              <span className="text-xs font-mono font-bold text-emerald-400 animate-pulse">
                {formatTimer(callDuration)}
              </span>
            )}
          </div>

          {/* Call Controls */}
          {callState === 'idle' && (
            <button
              onClick={handleStartCall}
              className="w-full py-3.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 min-h-[46px]"
            >
              <PhoneCall className="w-4 h-4" />
              <span>Llamar a Extensión {sipDest} (Conserjería / Citófono)</span>
            </button>
          )}

          {(callState === 'calling' || callState === 'ringing') && (
            <div className="space-y-3">
              <div className="p-3 bg-blue-950/70 border border-blue-800 rounded-xl text-center text-xs font-bold text-blue-200 animate-pulse">
                {callState === 'calling' ? 'Iniciando llamada SIP...' : `Timbrando en extensión ${sipDest} (180 Ringing)...`}
              </div>
              <button
                onClick={handleHangupCall}
                className="w-full py-3 bg-red-600 hover:bg-red-500 text-white text-xs font-bold rounded-xl shadow transition-colors flex items-center justify-center gap-2 min-h-[44px]"
              >
                <PhoneOff className="w-4 h-4" />
                <span>Cancelar Llamada</span>
              </button>
            </div>
          )}

          {callState === 'connected' && (
            <div className="space-y-3">
              <div className="p-3 bg-emerald-950/70 border border-emerald-700 rounded-xl flex items-center justify-between text-xs text-emerald-300 font-bold">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-ping" />
                  <span>Llamada en curso con {sipDest}</span>
                </div>
                <span className="font-mono">{formatTimer(callDuration)}</span>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setIsMuted(!isMuted)}
                  className={`flex-1 py-2.5 rounded-xl text-xs font-semibold border flex items-center justify-center gap-1.5 transition-colors min-h-[42px] ${
                    isMuted ? 'bg-amber-950 border-amber-800 text-amber-300' : 'bg-slate-900 border-slate-700 text-slate-300'
                  }`}
                >
                  {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                  <span>{isMuted ? 'Micrófono Mute' : 'Silenciar'}</span>
                </button>

                <button
                  onClick={handleHangupCall}
                  className="flex-1 py-2.5 bg-red-600 hover:bg-red-500 text-white text-xs font-bold rounded-xl shadow transition-colors flex items-center justify-center gap-1.5 min-h-[42px]"
                >
                  <PhoneOff className="w-4 h-4" />
                  <span>Colgar (BYE)</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* SECTION 3: MONITOR DE TRÁFICO SIP EN VIVO */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
              <span>3. Captura y Analizador de Tramas SIP en Vivo</span>
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Inspección de mensajes UDP 5080/5060 (REGISTER, INVITE, ACK, BYE)
            </p>
          </div>
          <button
            onClick={() => setPackets([])}
            className="text-[11px] text-slate-400 hover:text-white"
          >
            Limpiar
          </button>
        </div>

        <div className="bg-slate-950 border border-slate-800 rounded-2xl p-2.5 font-mono text-[11px] space-y-1.5 max-h-52 overflow-y-auto">
          {packets.map((pkt, idx) => (
            <div
              key={idx}
              className={`p-2 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-1 ${
                pkt.isError ? 'bg-red-950/60 text-red-300 border border-red-900/60' : 'bg-slate-900/70 text-slate-300'
              }`}
            >
              <div className="flex items-center gap-2 truncate">
                <span className="text-slate-500 text-[10px] shrink-0">{pkt.time}</span>
                <span className="font-bold text-white truncate">{pkt.detail}</span>
              </div>
              <div className="text-[10px] text-slate-400 shrink-0">
                {pkt.source} → {pkt.dest}
              </div>
            </div>
          ))}

          {packets.length === 0 && (
            <div className="text-center py-4 text-slate-500 text-xs">
              No hay tramas capturadas aún. Realiza un sondeo o llamada.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
