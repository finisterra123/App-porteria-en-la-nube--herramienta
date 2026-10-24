/**
 * MIP 1000 IP & SIP Testing Utility Functions
 * Based on Intelbras Protocol V2 and SIP RFC 3261
 */

export interface MipDoor {
  id: string;
  name: string;
  devAddr: number; // 1 = MIP, 2..24 = RS-485 (XRE, XPE, XLT)
  relay: number;   // 1..8
  type: 'MIP Placa Base' | 'XRE 1000 Plus' | 'XPE 1000' | 'XLT 1000';
  description: string;
  isUnlocked: boolean;
  lastTriggered?: string;
}

export interface MipInfo {
  uid: string;
  mac: string;
  firmware: string;
  connected: boolean;
  ip: string;
  port: number;
}

export interface SipProbeResult {
  ok: boolean;
  statusCode: number;
  responseLine: string;
  sipAlgDetected: boolean;
  details: string;
  localIp: string;
  localPort: number;
}

/**
 * Generates the list of available doors from the MIP 1000 IP and its configured RS-485 modules.
 */
export function getDefaultDoorsList(): MipDoor[] {
  return [
    {
      id: 'door-mip-1',
      name: 'Puerta Peatonal Principal',
      devAddr: 1,
      relay: 1,
      type: 'MIP Placa Base',
      description: 'Cantonera eléctrica en lobby principal',
      isUnlocked: false,
    },
    {
      id: 'door-mip-2',
      name: 'Puerta de Emergencia / Esclusa',
      devAddr: 1,
      relay: 2,
      type: 'MIP Placa Base',
      description: 'Electroimán 600 lbs esclusa peatonal',
      isUnlocked: false,
    },
    {
      id: 'door-xre1-1',
      name: 'Portón Vehicular Entrada (XRE #1)',
      devAddr: 2,
      relay: 1,
      type: 'XRE 1000 Plus',
      description: 'Motor corredera vehicular - Módulo RS-485 Dir 2',
      isUnlocked: false,
    },
    {
      id: 'door-xre1-2',
      name: 'Baliza y Semáforo Vehicular (XRE #1)',
      devAddr: 2,
      relay: 2,
      type: 'XRE 1000 Plus',
      description: 'Luz estroboscópica y aviso acústico de apertura',
      isUnlocked: false,
    },
    {
      id: 'door-xre2-1',
      name: 'Barrera Vehicular Salida (XRE #2)',
      devAddr: 3,
      relay: 1,
      type: 'XRE 1000 Plus',
      description: 'Talanquera rápida de salida - Módulo RS-485 Dir 3',
      isUnlocked: false,
    },
    {
      id: 'door-xre2-2',
      name: 'Talanquera Parqueadero Visitantes (XRE #2)',
      devAddr: 3,
      relay: 2,
      type: 'XRE 1000 Plus',
      description: 'Control de acceso a bahías de visitantes',
      isUnlocked: false,
    },
    {
      id: 'door-xpe-1',
      name: 'Portón Peatonal Secundario (XPE)',
      devAddr: 4,
      relay: 1,
      type: 'XPE 1000',
      description: 'Portero electrónico exterior - Dir 4',
      isUnlocked: false,
    },
  ];
}

/**
 * Builds the simulated protocol payload for ASR (Accionar Salida Remota - 0x18).
 */
export function buildAsrCommand(devAddr: number, outNum: number): { hexCommand: string; log: string } {
  const addrHex = devAddr.toString(16).padStart(2, '0').toUpperCase();
  const outHex = outNum.toString(16).padStart(2, '0').toUpperCase();
  // Frame format: STX(0x02) + CMD(0x18) + DEV_ADDR + OUT_NUM + CHECKSUM + ETX(0x03)
  const hex = `02 18 ${addrHex} ${outHex} 00 03`;
  const target = devAddr === 1 ? 'MIP 1000 IP Placa Base' : `Módulo RS-485 Dir ${devAddr}`;
  return {
    hexCommand: hex,
    log: `TX [ASR 0x18]: Accionando ${target} -> Salida/Relé ${outNum}`,
  };
}

/**
 * Validates and formats display message (MG 0x22) for MIP 1000 (max 20 chars).
 */
export function formatIdleDisplayMessage(message: string): { validText: string; isTruncated: boolean } {
  const clean = message.trim().toUpperCase();
  if (clean.length > 20) {
    return { validText: clean.slice(0, 20), isTruncated: true };
  }
  return { validText: clean || 'INTELBRAS MIP 1000', isTruncated: false };
}

/**
 * Analyzes simulated SIP response to detect SIP ALG NAT manipulation.
 */
export function analyzeSipAlgResponse(
  responseRaw: string,
  localIp: string,
  localPort: number
): { sipAlgDetected: boolean; explanation: string } {
  // If the local IP & port were rewritten inside the Via / Contact headers by the router, ALG is active.
  const hasLocalEndpoint = responseRaw.includes(`${localIp}:${localPort}`) || responseRaw.includes(localIp);
  const viaAltered = !hasLocalEndpoint && responseRaw.toLowerCase().includes('via: sip/2.0/udp');

  if (viaAltered) {
    return {
      sipAlgDetected: true,
      explanation:
        '⚠️ INDICIO DE SIP ALG ACTIVO: El router de la portería modificó las cabeceras Via/Contact locales. Esto suele provocar llamadas mudas o fallas de timbrado en la portería en la nube.',
    };
  }

  return {
    sipAlgDetected: false,
    explanation:
      '✅ SIP ALG NO DETECTADO: Las cabeceras SIP se mantuvieron íntegras sin reescritura por NAT. Configuración óptima para VoIP.',
  };
}
