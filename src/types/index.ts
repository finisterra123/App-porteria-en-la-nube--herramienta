export type SystemCategory = 
  | 'all'
  | 'access_control' // MIP 1000 IP / XID / XTR / Lectores
  | 'cctv'           // Cámaras RTSP, NVR, Canales
  | 'sip_telephony'  // Citofonía SIP 2.0, PBX, Extensiones
  | 'networking'     // Switches PoE, Routers, Cableado, Puertos
  | 'relays';        // Relevadores XRE 1000, Portones, Cantoneras

export type TicketPriority = 'critica' | 'alta' | 'media' | 'baja';

export type TicketStatus = 'pending' | 'in_progress' | 'testing' | 'resolved';

export interface ChecklistItem {
  id: string;
  label: string;
  done: boolean;
}

export interface Ticket {
  id: string;
  code: string;
  title: string;
  description: string;
  projectId: string;
  projectName: string;
  location: string;
  category: SystemCategory;
  priority: TicketPriority;
  status: TicketStatus;
  assignedTo: string;
  createdAt: string;
  dueDate: string;
  slaHoursRemaining: number;
  checklist: ChecklistItem[];
  hardwareDetails?: {
    ip?: string;
    port?: number;
    devAddr?: number;
    relay?: number;
    tagHex?: string;
    rfCode?: string;
    rtspUrl?: string;
    sipExt?: string;
    apto?: string;
  };
}

export interface Project {
  id: string;
  name: string;
  client: string;
  code: string;
  status: 'en_ejecucion' | 'en_pruebas' | 'finalizado';
  progress: number;
  totalTickets: number;
  resolvedTickets: number;
  location: string;
  contactPerson: string;
  phone: string;
  updatedAt: string;
  hardwareNodes: {
    id: string;
    name: string;
    type: 'MIP 1000 IP' | 'XRE 1000' | 'Cámara RTSP' | 'Switch PoE' | 'PBX SIP';
    status: 'online' | 'warning' | 'offline';
    ip: string;
    port?: number;
  }[];
}

export interface AccessEvent {
  id: number;
  timestamp: string;
  apartment: string;
  block: string;
  user: string;
  credentialType: 'RFID TAG (XID)' | 'Control Remoto (XTR)' | 'Contraseña Teclado' | 'Comando Remoto (ASR)';
  eventType: string;
  deviceNumber: number;
  relay: number;
  plate?: string;
  isPanic: boolean;
}

export interface ResidentTemplate {
  name: string;
  categoria: number; // 0=Residente, 1=Prestador, 2=Visitante
  nivel: number;
  apto: string;
  bloco: string;
  email: string;
  tel_cel: string;
  senha_3dig: string;
  dispositivos: number[];
  placa?: string;
  modelo?: string;
  marca?: string;
  cor?: string;
}
