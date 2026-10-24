import test from 'node:test';
import assert from 'node:assert/strict';
import {
  moveTicketStatus,
  filterTickets,
  calculateProjectStats,
  detectPanicAnomalies,
  calculateWeeklyDistribution,
  generateTicketReportCsv,
} from './ticket-rules.ts';
import { Ticket, Project, AccessEvent } from '../types';

const mockTickets: Ticket[] = [
  {
    id: 't-1',
    code: 'TK-101',
    title: 'Falla en lectura de TAG RFID Peatonal',
    description: 'El torniquete norte no reconoce los llaveros XID nuevos.',
    projectId: 'p-1',
    projectName: 'Torre Residencial Altos del Roble',
    location: 'Acceso Peatonal Principal',
    category: 'access_control',
    priority: 'alta',
    status: 'pending',
    assignedTo: 'Carlos Mendoza',
    createdAt: '2026-10-23 08:30',
    dueDate: '2026-10-23 18:00',
    slaHoursRemaining: 6,
    checklist: [
      { id: 'c1', label: 'Verificar bus RS-485', done: false },
      { id: 'c2', label: 'Probar lectura con comando 0x1C', done: false },
    ],
  },
  {
    id: 't-2',
    code: 'TK-102',
    title: 'Cámara RTSP Canal 2 sin señal de video',
    description: 'Pérdida intermitente de paquetes en puerto 554.',
    projectId: 'p-1',
    projectName: 'Torre Residencial Altos del Roble',
    location: 'Sótano 1 - Bahía 4',
    category: 'cctv',
    priority: 'critica',
    status: 'in_progress',
    assignedTo: 'Andrés Gil',
    createdAt: '2026-10-23 09:15',
    dueDate: '2026-10-23 13:00',
    slaHoursRemaining: 1,
    checklist: [],
  },
  {
    id: 't-3',
    code: 'TK-103',
    title: 'Citofonía SIP no timbra extensión 990001',
    description: 'Error 408 timeout al enviar INVITE desde portería.',
    projectId: 'p-2',
    projectName: 'Parque Empresarial Conecta',
    location: 'Recepción Central',
    category: 'sip_telephony',
    priority: 'media',
    status: 'resolved',
    assignedTo: 'Carlos Mendoza',
    createdAt: '2026-10-22 14:00',
    dueDate: '2026-10-23 12:00',
    slaHoursRemaining: 0,
    checklist: [],
  },
];

const mockProjects: Project[] = [
  {
    id: 'p-1',
    name: 'Torre Residencial Altos del Roble',
    client: 'Constructora Bolívar',
    code: 'PRJ-ALTOS',
    status: 'en_ejecucion',
    progress: 0,
    totalTickets: 0,
    resolvedTickets: 0,
    location: 'Calle 127 # 19-45',
    contactPerson: 'Ing. Mateo Rivas',
    phone: '+57 310 456 7890',
    updatedAt: '2026-10-23',
    hardwareNodes: [],
  },
  {
    id: 'p-2',
    name: 'Parque Empresarial Conecta',
    client: 'Inversiones Global',
    code: 'PRJ-CONECTA',
    status: 'en_ejecucion',
    progress: 0,
    totalTickets: 0,
    resolvedTickets: 0,
    location: 'Av. El Dorado # 68C-61',
    contactPerson: 'Dra. Elena Silva',
    phone: '+57 320 890 1234',
    updatedAt: '2026-10-23',
    hardwareNodes: [],
  },
];

test('moveTicketStatus updates ticket status and sets SLA to 0 if resolved', () => {
  const updated = moveTicketStatus(mockTickets, 't-1', 'resolved');
  const target = updated.find((t) => t.id === 't-1');
  assert.equal(target?.status, 'resolved');
  assert.equal(target?.slaHoursRemaining, 0);

  // Other tickets remain untouched
  const untouched = updated.find((t) => t.id === 't-2');
  assert.equal(untouched?.status, 'in_progress');
});

test('filterTickets filters by category and search term correctly', () => {
  // Category filter
  const cctvTickets = filterTickets(mockTickets, { category: 'cctv' });
  assert.equal(cctvTickets.length, 1);
  assert.equal(cctvTickets[0].code, 'TK-102');

  // Search filter
  const searchResults = filterTickets(mockTickets, { search: 'citofonía' });
  assert.equal(searchResults.length, 1);
  assert.equal(searchResults[0].code, 'TK-103');

  // Priority filter
  const critTickets = filterTickets(mockTickets, { priority: 'critica' });
  assert.equal(critTickets.length, 1);
  assert.equal(critTickets[0].code, 'TK-102');

  // Project filter
  const p2Tickets = filterTickets(mockTickets, { projectId: 'p-2' });
  assert.equal(p2Tickets.length, 1);
  assert.equal(p2Tickets[0].code, 'TK-103');
});

test('calculateProjectStats calculates ticket progress percentage', () => {
  const calculated = calculateProjectStats(mockProjects, mockTickets);
  const p1 = calculated.find((p) => p.id === 'p-1');
  const p2 = calculated.find((p) => p.id === 'p-2');

  // p-1 has 2 tickets, 0 resolved -> 0%
  assert.equal(p1?.totalTickets, 2);
  assert.equal(p1?.resolvedTickets, 0);
  assert.equal(p1?.progress, 0);

  // p-2 has 1 ticket, 1 resolved -> 100%
  assert.equal(p2?.totalTickets, 1);
  assert.equal(p2?.resolvedTickets, 1);
  assert.equal(p2?.progress, 100);
});

test('detectPanicAnomalies flags panic events and nocturnal hours', () => {
  const events: AccessEvent[] = [
    {
      id: 1,
      timestamp: '23/10/2026 14:20:00',
      apartment: '101',
      block: 'A',
      user: 'Juan Pérez',
      credentialType: 'RFID TAG (XID)',
      eventType: 'Acceso Permitido',
      deviceNumber: 1,
      relay: 1,
      isPanic: false,
    },
    {
      id: 2,
      timestamp: '23/10/2026 02:45:10', // nocturnal 02:45
      apartment: '204',
      block: 'B',
      user: 'María Gómez',
      credentialType: 'Contraseña Teclado',
      eventType: 'Coacción / Pánico',
      deviceNumber: 2,
      relay: 1,
      isPanic: true,
    },
  ];

  const analysis = detectPanicAnomalies(events);
  assert.equal(analysis.panicCount, 1);
  assert.equal(analysis.nocturnalCount, 1);
  assert.match(analysis.summary, /ALERTA CRÍTICA/);
});

test('generateTicketReportCsv formats semicolon-delimited CSV correctly', () => {
  const csv = generateTicketReportCsv(mockTickets);
  assert.ok(csv.includes('Código;Título;Proyecto;Ubicación'));
  assert.ok(csv.includes('TK-101;'));
  assert.ok(csv.includes('TK-102;'));
});
