import { Ticket, TicketStatus, SystemCategory, TicketPriority, Project, AccessEvent } from '../types';

/**
 * Updates a ticket's status and adjusts completion metadata.
 */
export function moveTicketStatus(tickets: Ticket[], ticketId: string, newStatus: TicketStatus): Ticket[] {
  return tickets.map((t) => {
    if (t.id === ticketId) {
      return {
        ...t,
        status: newStatus,
        slaHoursRemaining: newStatus === 'resolved' ? 0 : t.slaHoursRemaining,
      };
    }
    return t;
  });
}

/**
 * Filter tickets by category, search query, priority, and project.
 */
export function filterTickets(
  tickets: Ticket[],
  filters: {
    category?: SystemCategory;
    search?: string;
    priority?: TicketPriority | 'all';
    projectId?: string;
  }
): Ticket[] {
  const { category = 'all', search = '', priority = 'all', projectId = 'all' } = filters;
  const query = search.trim().toLowerCase();

  return tickets.filter((t) => {
    // Category check
    if (category !== 'all' && t.category !== category) {
      return false;
    }

    // Priority check
    if (priority !== 'all' && t.priority !== priority) {
      return false;
    }

    // Project check
    if (projectId !== 'all' && t.projectId !== projectId) {
      return false;
    }

    // Search query check (title, code, location, assignedTo, description)
    if (query) {
      const match =
        t.code.toLowerCase().includes(query) ||
        t.title.toLowerCase().includes(query) ||
        t.location.toLowerCase().includes(query) ||
        t.assignedTo.toLowerCase().includes(query) ||
        t.projectName.toLowerCase().includes(query) ||
        t.description.toLowerCase().includes(query);
      if (!match) return false;
    }

    return true;
  });
}

/**
 * Recalculates project progress percentage and ticket counts dynamically.
 */
export function calculateProjectStats(projects: Project[], tickets: Ticket[]): Project[] {
  return projects.map((p) => {
    const projectTickets = tickets.filter((t) => t.projectId === p.id);
    const total = projectTickets.length;
    const resolved = projectTickets.filter((t) => t.status === 'resolved').length;
    const progress = total === 0 ? 100 : Math.round((resolved / total) * 100);

    return {
      ...p,
      totalTickets: total,
      resolvedTickets: resolved,
      progress,
    };
  });
}

/**
 * Analyzes access events to detect panic alarms and nocturnal activity anomalies (01:00 - 04:00 AM)
 * extracted from the MIP 1000 Python script AI logic.
 */
export function detectPanicAnomalies(events: AccessEvent[]): {
  totalEvents: number;
  panicCount: number;
  nocturnalCount: number;
  summary: string;
} {
  let panicCount = 0;
  let nocturnalCount = 0;

  for (const ev of events) {
    if (ev.isPanic) {
      panicCount++;
    }

    // Check time for nocturnal window (01:00 to 04:00 AM)
    const timePart = ev.timestamp.split(' ')[1];
    if (timePart) {
      const hour = parseInt(timePart.split(':')[0], 10);
      if (hour >= 1 && hour <= 4) {
        nocturnalCount++;
      }
    }
  }

  let summary = 'Parámetros dentro de la normalidad operativa.';
  if (panicCount > 0) {
    summary = `ALERTA CRÍTICA: Se detectaron ${panicCount} evento(s) de pánico o coacción.`;
  } else if (nocturnalCount > 5) {
    summary = `PRECAUCIÓN: Alto volumen de accesos nocturnos (${nocturnalCount} eventos entre 01:00 y 04:00).`;
  }

  return {
    totalEvents: events.length,
    panicCount,
    nocturnalCount,
    summary,
  };
}

/**
 * Computes frequency per day of the week for historical bar charts.
 */
export function calculateWeeklyDistribution(events: AccessEvent[]): Record<string, number> {
  const dayNames = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
  const counts: Record<string, number> = {
    'Lun': 0, 'Mar': 0, 'Mié': 0, 'Jue': 0, 'Vie': 0, 'Sáb': 0, 'Dom': 0
  };

  for (const ev of events) {
    // Expected format: DD/MM/YYYY HH:MM:SS or ISO
    try {
      let date: Date;
      if (ev.timestamp.includes('/')) {
        const [datePart] = ev.timestamp.split(' ');
        const [d, m, y] = datePart.split('/');
        date = new Date(parseInt(y, 10), parseInt(m, 10) - 1, parseInt(d, 10));
      } else {
        date = new Date(ev.timestamp);
      }

      if (!isNaN(date.getTime())) {
        const dayName = dayNames[date.getDay()];
        if (counts[dayName] !== undefined) {
          counts[dayName]++;
        }
      }
    } catch {
      // Continue on parse error
    }
  }

  return counts;
}

/**
 * Generates an Excel-compatible CSV string for tickets.
 */
export function generateTicketReportCsv(tickets: Ticket[]): string {
  const headers = [
    'Código',
    'Título',
    'Proyecto',
    'Ubicación',
    'Categoría',
    'Prioridad',
    'Estado',
    'Técnico Asignado',
    'Fecha Creación',
    'SLA Restante (h)',
  ];

  const rows = tickets.map((t) => [
    t.code,
    `"${t.title.replace(/"/g, '""')}"`,
    `"${t.projectName.replace(/"/g, '""')}"`,
    `"${t.location.replace(/"/g, '""')}"`,
    t.category,
    t.priority,
    t.status,
    `"${t.assignedTo.replace(/"/g, '""')}"`,
    t.createdAt,
    t.slaHoursRemaining,
  ]);

  return [headers.join(';'), ...rows.map((r) => r.join(';'))].join('\r\n');
}

/**
 * Generates an Excel-compatible CSV string for events.
 */
export function generateEventsReportCsv(events: AccessEvent[]): string {
  const headers = ['ID', 'Fecha y Hora', 'Apto', 'Bloque', 'Usuario', 'Medio de Acceso', 'Evento', 'Dispositivo', 'Rele', 'Placa', 'Alerta Pánico'];
  const rows = events.map((ev) => [
    ev.id,
    ev.timestamp,
    ev.apartment,
    ev.block,
    `"${ev.user.replace(/"/g, '""')}"`,
    `"${ev.credentialType}"`,
    `"${ev.eventType.replace(/"/g, '""')}"`,
    ev.deviceNumber,
    ev.relay,
    ev.plate || '-',
    ev.isPanic ? 'SI' : 'NO',
  ]);

  return [headers.join(';'), ...rows.map((r) => r.join(';'))].join('\r\n');
}
