import React, { useState } from 'react';
import {
  KeyRound,
  Radio,
  Search,
  User,
  Plus,
  Save,
  CheckCircle2,
  Trash2,
  Sparkles,
  Car,
  Shield,
  Layers,
} from 'lucide-react';
import { RESIDENT_TEMPLATES } from '../data/mockData';

interface RegisteredResident {
  id: number;
  name: string;
  apto: string;
  bloco: string;
  tagHex: string;
  rfCode?: string;
  plate?: string;
  category: string;
  devices: number[];
}

export const CredentialsView: React.FC = () => {
  // Capture states
  const [capturedTag, setCapturedTag] = useState('');
  const [capturedRf, setCapturedRf] = useState('');
  const [capturedRfTs, setCapturedRfTs] = useState<number>(0);
  const [isReadingTag, setIsReadingTag] = useState(false);
  const [isReadingRf, setIsReadingRf] = useState(false);

  // Search resident state
  const [searchApto, setSearchApto] = useState('101');
  const [searchResults, setSearchResults] = useState<RegisteredResident[]>([
    {
      id: 1,
      name: 'Carolina Herrera',
      apto: '101',
      bloco: 'A',
      tagHex: 'A3F82C10',
      rfCode: '',
      plate: '',
      category: 'Residente Peatonal',
      devices: [1, 2, 3],
    },
    {
      id: 2,
      name: 'Mauricio Peña',
      apto: '205',
      bloco: 'B',
      tagHex: 'B441D990',
      rfCode: '98AF10',
      plate: 'ABC123',
      category: 'Residente Vehicular',
      devices: [1, 2, 3, 4, 5],
    },
  ]);

  // New Resident Form
  const [uid, setUid] = useState('0'); // 0 = automatic
  const [name, setName] = useState('Nuevo Residente');
  const [apto, setApto] = useState('102');
  const [bloco, setBloco] = useState('A');
  const [cel, setCel] = useState('3001234567');
  const [senha3, setSenha3] = useState('123');
  const [plate, setPlate] = useState('');
  const [selectedDevices, setSelectedDevices] = useState<number[]>([1, 2, 3]);

  const [notification, setNotification] = useState<string | null>(null);

  // Trigger Tag Read (0x1C)
  const handleReadTag = () => {
    setIsReadingTag(true);
    setNotification(null);
    setTimeout(() => {
      setIsReadingTag(false);
      const hex = Math.floor(Math.random() * 0xffffffff)
        .toString(16)
        .toUpperCase()
        .padStart(8, '0');
      setCapturedTag(hex);
      setNotification(`TAG RFID leído en antena del MIP: ${hex}`);
    }, 800);
  };

  // Trigger RF Read (0x26)
  const handleReadRf = () => {
    setIsReadingRf(true);
    setNotification(null);
    setTimeout(() => {
      setIsReadingRf(false);
      const hex = Math.floor(Math.random() * 0xffffff)
        .toString(16)
        .toUpperCase()
        .padStart(6, '0');
      const ts = Math.floor(Date.now() / 1000) % 100000;
      setCapturedRf(hex);
      setCapturedRfTs(ts);
      setNotification(`Control Remoto XTR detectado: ${hex} (Timestamp: ${ts})`);
    }, 800);
  };

  // Apply template
  const handleApplyTemplate = (tplKey: string) => {
    const tpl = RESIDENT_TEMPLATES[tplKey];
    if (tpl) {
      setName(tpl.name);
      setApto(tpl.apto);
      setBloco(tpl.bloco);
      setSenha3(tpl.senha_3dig);
      setSelectedDevices(tpl.dispositivos);
      setPlate(tpl.placa || '');
      setNotification(`Plantilla "${tplKey}" cargada en el formulario.`);
    }
  };

  // Toggle device permission
  const handleToggleDevice = (devNum: number) => {
    if (selectedDevices.includes(devNum)) {
      setSelectedDevices(selectedDevices.filter((d) => d !== devNum));
    } else {
      setSelectedDevices([...selectedDevices, devNum].sort((a, b) => a - b));
    }
  };

  // Save new user
  const handleSaveResident = (e: React.FormEvent) => {
    e.preventDefault();
    const newRes: RegisteredResident = {
      id: Math.floor(10 + Math.random() * 90),
      name,
      apto,
      bloco,
      tagHex: capturedTag || 'SIN-TAG',
      rfCode: capturedRf || undefined,
      plate: plate || undefined,
      category: plate ? 'Residente Vehicular' : 'Residente Peatonal',
      devices: selectedDevices,
    };

    setSearchResults([newRes, ...searchResults]);
    setNotification(`✅ Residente ${name} (Apto ${apto}) sincronizado en memoria del MIP 1000 con éxito.`);
    setCapturedTag('');
    setCapturedRf('');
  };

  return (
    <div className="flex flex-col gap-4 pb-24">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-sm space-y-2">
        <h2 className="text-sm font-bold text-white flex items-center gap-2">
          <KeyRound className="w-4 h-4 text-amber-400" />
          <span>Gestión de Credenciales RFID, Controles RF & Residentes</span>
        </h2>
        <p className="text-xs text-slate-400">
          Enrola rápidamente llaveros XID (0x1C) y controles XTR (0x26) directamente desde tu celular
        </p>
      </div>

      {notification && (
        <div className="p-3.5 bg-emerald-950/70 border border-emerald-800 rounded-2xl text-xs font-mono text-emerald-300">
          {notification}
        </div>
      )}

      {/* CREDENTIAL CAPTURE CARDS (0x1C & 0x26) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Tag RFID 0x1C */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-white flex items-center gap-1.5">
              <Radio className="w-4 h-4 text-amber-400" />
              Lector TAG RFID (0x1C)
            </span>
            <span className="text-[10px] font-mono text-amber-300 bg-amber-950 px-2 py-0.5 rounded border border-amber-800">
              MIP Antena
            </span>
          </div>

          <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 text-center font-mono text-sm font-bold text-amber-300">
            {capturedTag || '--- SIN LECTURA ---'}
          </div>

          <button
            onClick={handleReadTag}
            disabled={isReadingTag}
            className="w-full py-2.5 bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold rounded-xl transition-colors flex items-center justify-center gap-1.5 min-h-[42px]"
          >
            <Radio className={`w-3.5 h-3.5 ${isReadingTag ? 'animate-spin' : ''}`} />
            <span>{isReadingTag ? 'Acercando TAG a antena...' : 'Capturar TAG en MIP (0x1C)'}</span>
          </button>
        </div>

        {/* Control RF 0x26 */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-white flex items-center gap-1.5">
              <Car className="w-4 h-4 text-blue-400" />
              Lector Control RF (0x26)
            </span>
            <span className="text-[10px] font-mono text-blue-300 bg-blue-950 px-2 py-0.5 rounded border border-blue-800">
              Receptor XTR
            </span>
          </div>

          <div className="p-2.5 bg-slate-950 rounded-xl border border-slate-800 text-center font-mono text-sm font-bold text-blue-300">
            {capturedRf ? `${capturedRf} (TS: ${capturedRfTs})` : '--- SIN LECTURA ---'}
          </div>

          <button
            onClick={handleReadRf}
            disabled={isReadingRf}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-xl transition-colors flex items-center justify-center gap-1.5 min-h-[42px]"
          >
            <Radio className={`w-3.5 h-3.5 ${isReadingRf ? 'animate-spin' : ''}`} />
            <span>{isReadingRf ? 'Presione botón del control...' : 'Capturar Control RF (0x26)'}</span>
          </button>
        </div>
      </div>

      {/* QUICK RESIDENT ENROLLMENT FORM */}
      <form
        onSubmit={handleSaveResident}
        className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-sm space-y-4"
      >
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <User className="w-4 h-4 text-purple-400" />
            Asignación y Alta de Residente en MIP 1000
          </h3>
          <span className="text-[10px] text-slate-400">ID 0 = Auto-asignar</span>
        </div>

        {/* Template Buttons */}
        <div>
          <span className="text-[10px] text-slate-400 block mb-1">Cargar Plantilla Rápida:</span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {Object.keys(RESIDENT_TEMPLATES).map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => handleApplyTemplate(key)}
                className="p-2 rounded-xl bg-slate-950 hover:bg-slate-800 border border-slate-800 text-xs font-semibold text-slate-300 transition-colors text-left truncate"
              >
                {key}
              </button>
            ))}
          </div>
        </div>

        {/* Form Fields */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Nombre Completo:</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded-lg px-2.5 py-1.5"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Apartamento:</label>
            <input
              type="text"
              required
              value={apto}
              onChange={(e) => setApto(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded-lg px-2.5 py-1.5 font-bold"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Bloque / Torre:</label>
            <input
              type="text"
              value={bloco}
              onChange={(e) => setBloco(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded-lg px-2.5 py-1.5"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Clave Teclado (3 dígitos):</label>
            <input
              type="text"
              maxLength={3}
              value={senha3}
              onChange={(e) => setSenha3(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded-lg px-2.5 py-1.5 font-mono text-center"
            />
          </div>
        </div>

        {/* Vehicle plate if applicable */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs">
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Placa Vehicular (Opcional):</label>
            <input
              type="text"
              value={plate}
              onChange={(e) => setPlate(e.target.value.toUpperCase())}
              placeholder="Ej: ABC123"
              className="w-full bg-slate-950 border border-slate-800 text-white font-mono rounded-lg px-2.5 py-1.5 uppercase"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">Celular / Teléfono:</label>
            <input
              type="text"
              value={cel}
              onChange={(e) => setCel(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-white rounded-lg px-2.5 py-1.5"
            />
          </div>
        </div>

        {/* 24 RS-485 Supported Devices Selector (Direct from Python script) */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-bold text-white flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-blue-400" />
              Dispositivos Liberados RS-485 (24 soportados por MIP 1000):
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              {selectedDevices.length} seleccionados
            </span>
          </div>

          <div className="grid grid-cols-6 sm:grid-cols-12 gap-1.5 p-2.5 bg-slate-950 rounded-xl border border-slate-800">
            {Array.from({ length: 24 }, (_, i) => i + 1).map((d) => {
              const isChecked = selectedDevices.includes(d);
              return (
                <button
                  key={d}
                  type="button"
                  onClick={() => handleToggleDevice(d)}
                  className={`py-1.5 text-center rounded text-[11px] font-mono font-bold transition-colors ${
                    isChecked
                      ? 'bg-blue-600 text-white shadow-sm'
                      : 'bg-slate-900 text-slate-500 hover:text-slate-300'
                  }`}
                  title={`Dispositivo ${d}`}
                >
                  D{d}
                </button>
              );
            })}
          </div>
        </div>

        {/* Save button */}
        <button
          type="submit"
          className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-2xl shadow-lg transition-all flex items-center justify-center gap-2 min-h-[44px]"
        >
          <Save className="w-4 h-4" />
          <span>Enviar y Sincronizar Residente en MIP 1000</span>
        </button>
      </form>

      {/* SEARCH RESIDENTS REGISTERED IN MIP 1000 */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-5 shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
            <Search className="w-3.5 h-3.5 text-blue-400" />
            Residentes Cadastrados en Sitio ({searchResults.length})
          </h3>
        </div>

        <div className="space-y-2">
          {searchResults.map((res) => (
            <div
              key={res.id}
              className="p-3 bg-slate-950 rounded-2xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white">{res.name}</span>
                  <span className="text-slate-600">·</span>
                  <span className="text-[11px] text-blue-400 font-bold">
                    Apto {res.apto} ({res.bloco})
                  </span>
                  {res.plate && (
                    <span className="font-mono text-[10px] bg-slate-800 text-amber-300 px-1.5 py-0.2 rounded border border-slate-700">
                      {res.plate}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-1 font-mono">
                  <span>TAG: <span className="text-emerald-300">{res.tagHex}</span></span>
                  {res.rfCode && <span>RF: <span className="text-sky-300">{res.rfCode}</span></span>}
                  <span>Permisos: [{res.devices.map((d) => `D${d}`).join(', ')}]</span>
                </div>
              </div>

              <span className="text-[10px] uppercase font-bold text-slate-400 self-end sm:self-center">
                {res.category}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
