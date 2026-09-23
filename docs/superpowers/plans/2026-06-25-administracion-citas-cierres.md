# Citas & Cierres — Administración — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crear la página `/administracion/citas-cierres` con un calendario FullCalendar v6 que muestra citas agendadas y cierres de todos los asesores, con sidebar de filtro y tooltip de detalle al hacer clic.

**Architecture:** Un controlador nuevo ejecuta 4 queries en paralelo (asesores, citas, firmas, firma+pago), serializa los resultados como JSON inline en la vista. FullCalendar consume el JSON y renderiza eventos color-coded. El filtro por asesor y el tooltip son 100% client-side JS.

**Tech Stack:** Node.js/Express v5, PostgreSQL, EJS, FullCalendar v6 (CDN), JavaScript vanilla

---

## Archivos

| Archivo | Acción |
|---|---|
| `src/controllers/administracion/citasCierres.controller.js` | Crear |
| `src/routes/administracion.routes.js` | Modificar — agregar ruta y require |
| `views/administracion/partials/sidebar.ejs` | Modificar — agregar link |
| `views/administracion/citas-cierres/index.ejs` | Crear |

---

### Task 1: Controlador y ruta

**Files:**
- Create: `src/controllers/administracion/citasCierres.controller.js`
- Modify: `src/routes/administracion.routes.js`

- [ ] **Step 1: Crear el controlador**

Crea el archivo `src/controllers/administracion/citasCierres.controller.js` con este contenido exacto:

```javascript
// src/controllers/administracion/citasCierres.controller.js
'use strict';

const pool = require('../../db/pool');

exports.index = async (req, res) => {
  try {
    const [asesoresR, citasR, firmasR, pagoR] = await Promise.all([

      /* 1 · Asesores activos con conteos */
      pool.query(`
        SELECT
          u.id,
          u.nombre,
          u.apellidos,
          u.username,
          u.avatar_url,
          COUNT(DISTINCT ce.id)     FILTER (WHERE ce.lead_id IS NOT NULL) AS citas_count,
          COUNT(DISTINCT l_f.id)                                           AS firma_count,
          COUNT(DISTINCT l_p.id)                                           AS pago_count
        FROM users u
        LEFT JOIN calendar_events ce ON ce.user_id = u.id AND ce.lead_id IS NOT NULL
        LEFT JOIN crm_leads l_f      ON l_f.advisor_id = u.id AND l_f.sale_signed_only = true
        LEFT JOIN crm_leads l_p      ON l_p.advisor_id  = u.id AND l_p.sale_paid = true
        WHERE u.role = 'advisor' AND u.is_active = true
        GROUP BY u.id, u.nombre, u.apellidos, u.username, u.avatar_url
        ORDER BY COALESCE(u.nombre, u.username) ASC
      `),

      /* 2 · Citas (calendar_events con lead vinculado) */
      pool.query(`
        SELECT
          ce.id,
          ce.user_id    AS advisor_id,
          ce.lead_id,
          ce.inicio,
          ce.fin,
          ce.titulo,
          u.nombre      AS asesor_nombre,
          u.apellidos   AS asesor_apellidos,
          u.avatar_url  AS asesor_avatar,
          l.nombre      AS lead_nombre,
          l.apellido    AS lead_apellido,
          l.telefono,
          l.email,
          l.portal,
          COALESCE(lp.propiedad_interes, '') AS propiedad_interes,
          a.observations                      AS cita_observaciones
        FROM calendar_events ce
        JOIN  users u      ON u.id    = ce.user_id
        JOIN  crm_leads l  ON l.id    = ce.lead_id
        LEFT JOIN crm_lead_profiles lp ON lp.lead_id = ce.lead_id
        LEFT JOIN LATERAL (
          SELECT observations
          FROM crm_activities
          WHERE lead_id = ce.lead_id AND type = 'cita'
          ORDER BY created_at DESC
          LIMIT 1
        ) a ON true
        WHERE ce.lead_id IS NOT NULL
        ORDER BY ce.inicio DESC
      `),

      /* 3 · Cierres con firma (sin pago) */
      pool.query(`
        SELECT
          l.id,
          l.advisor_id,
          l.nombre      AS lead_nombre,
          l.apellido    AS lead_apellido,
          l.telefono,
          l.email,
          l.portal,
          l.closed_at,
          u.nombre      AS asesor_nombre,
          u.apellidos   AS asesor_apellidos,
          u.avatar_url  AS asesor_avatar,
          COALESCE(lp.propiedad_interes, '') AS propiedad_interes
        FROM crm_leads l
        JOIN  users u ON u.id = l.advisor_id
        LEFT JOIN crm_lead_profiles lp ON lp.lead_id = l.id
        WHERE l.sale_signed_only = true
          AND l.closed_at IS NOT NULL
        ORDER BY l.closed_at DESC
      `),

      /* 4 · Cierres con firma y pago */
      pool.query(`
        SELECT
          l.id,
          l.advisor_id,
          l.nombre      AS lead_nombre,
          l.apellido    AS lead_apellido,
          l.telefono,
          l.email,
          l.portal,
          l.closed_at,
          u.nombre      AS asesor_nombre,
          u.apellidos   AS asesor_apellidos,
          u.avatar_url  AS asesor_avatar,
          COALESCE(lp.propiedad_interes, '') AS propiedad_interes
        FROM crm_leads l
        JOIN  users u ON u.id = l.advisor_id
        LEFT JOIN crm_lead_profiles lp ON lp.lead_id = l.id
        WHERE l.sale_paid = true
          AND l.closed_at IS NOT NULL
        ORDER BY l.closed_at DESC
      `),
    ]);

    return res.render('administracion/citas-cierres/index', {
      layout:      false,
      title:       'Citas & Cierres | Administración',
      currentPath: req.path,
      user:        req.session.user,
      asesores:    asesoresR.rows || [],
      citas:       citasR.rows    || [],
      firmas:      firmasR.rows   || [],
      pagos:       pagoR.rows     || [],
    });
  } catch (err) {
    console.error('[citasCierres] error:', err);
    return res.status(500).send('Error al cargar citas y cierres');
  }
};
```

- [ ] **Step 2: Agregar la ruta en `src/routes/administracion.routes.js`**

Lee el archivo. Localiza el `require` de contratos en la línea 9:
```javascript
const ctrl = require('../controllers/administracion/contratos.controller');
```

Agrega DESPUÉS:
```javascript
const citasCtrl = require('../controllers/administracion/citasCierres.controller');
```

Luego, al final del archivo (antes del `module.exports`), agrega:
```javascript
/* =========================
 * Citas & Cierres
 * ========================= */
router.get('/citas-cierres', authMw, citasCtrl.index);
```

- [ ] **Step 3: Verificar que el servidor arranca sin errores**

```bash
node -e "require('./src/controllers/administracion/citasCierres.controller'); console.log('OK')"
```

Esperado: `OK`

---

### Task 2: Link en el sidebar de administración

**Files:**
- Modify: `views/administracion/partials/sidebar.ejs`

- [ ] **Step 1: Agregar link de navegación**

Lee el archivo. Localiza el bloque de "Acceso" (alrededor de línea 140):
```html
    <p class="adm-section-label" style="margin-top:6px;">Acceso</p>
```

Agrega ANTES de ese bloque:
```html
    <p class="adm-section-label" style="margin-top:6px;">Actividad</p>
    <a class="adm-item <%= cp.startsWith('/administracion/citas-cierres') ? 'active' : '' %>"
       href="/administracion/citas-cierres">
      <span>Citas & Cierres</span>
      <small style="font-size:11px;color:rgba(226,232,240,.55);">📅</small>
    </a>

```

- [ ] **Step 2: Verificar visualmente**

Inicia el servidor y abre `/administracion` logueado como un usuario con rol `administracion`. Verifica que el link "Citas & Cierres" aparece en el sidebar y al hacer clic lleva a `/administracion/citas-cierres`.

---

### Task 3: Vista principal — Calendario + Sidebar + Tooltip

**Files:**
- Create: `views/administracion/citas-cierres/index.ejs`

Esta es la vista completa. Crea el directorio `views/administracion/citas-cierres/` y el archivo `index.ejs` con el siguiente contenido:

- [ ] **Step 1: Crear `views/administracion/citas-cierres/index.ejs`**

```ejs
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title><%= title || 'Citas & Cierres' %></title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="stylesheet" href="/css/styles.css" />
  <link href="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.css" rel="stylesheet" />
  <script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.15/index.global.min.js"></script>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: system-ui, sans-serif; background: #f1f5f9; color: #1e293b; }

    .page-shell { display: flex; padding-top: 56px; min-height: 100vh; }

    /* ── Sidebar asesores ── */
    .cc-sidebar {
      width: 270px;
      flex-shrink: 0;
      background: #fff;
      border-right: 1px solid #e2e8f0;
      height: calc(100vh - 56px);
      overflow-y: auto;
      position: sticky;
      top: 56px;
      padding: 16px 14px;
    }
    .cc-sidebar-title {
      font-size: 10px;
      font-weight: 700;
      letter-spacing: .15em;
      text-transform: uppercase;
      color: #94a3b8;
      padding: 0 4px 8px;
      border-bottom: 1px solid #f1f5f9;
      margin-bottom: 8px;
    }
    .cc-asesor-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 6px;
      border-radius: 10px;
      cursor: pointer;
      transition: background .1s;
      user-select: none;
    }
    .cc-asesor-item:hover { background: #f8fafc; }
    .cc-asesor-item input[type="checkbox"] { accent-color: #008a8a; flex-shrink: 0; }
    .cc-av {
      width: 30px; height: 30px; border-radius: 50%;
      background: #ccfbf1; color: #0d9488;
      font-size: 11px; font-weight: 800;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0; overflow: hidden;
    }
    .cc-av img { width: 100%; height: 100%; object-fit: cover; }
    .cc-asesor-name { font-size: 12px; font-weight: 600; color: #0f172a; flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .cc-badges { display: flex; gap: 3px; flex-shrink: 0; }
    .cc-b { display: inline-flex; align-items: center; justify-content: center; min-width: 16px; height: 16px; border-radius: 99px; font-size: 9px; font-weight: 700; padding: 0 3px; }
    .cc-b-cita { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
    .cc-b-firma { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
    .cc-b-pago  { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }

    /* ── Leyenda ── */
    .cc-legend { margin-top: 16px; padding-top: 12px; border-top: 1px solid #f1f5f9; }
    .cc-legend-title { font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: #94a3b8; margin-bottom: 8px; }
    .cc-legend-item { display: flex; align-items: center; gap: 7px; font-size: 11.5px; color: #475569; margin-bottom: 6px; }
    .cc-legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

    /* ── Calendario ── */
    .cc-main { flex: 1; min-width: 0; padding: 20px 24px; }
    .cc-cal-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; flex-wrap: wrap; gap: 10px; }
    .cc-cal-title { font-size: 18px; font-weight: 700; color: #0f172a; }
    .cc-cal-sub { font-size: 12px; color: #64748b; margin-top: 2px; }
    #cc-calendar { background: #fff; border-radius: 14px; border: 1px solid #e2e8f0; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.05); }

    /* FullCalendar overrides */
    .fc .fc-toolbar-title { font-size: 15px; font-weight: 700; color: #0f172a; }
    .fc .fc-button { font-size: 12px; font-weight: 600; }
    .fc .fc-button-primary { background: #008a8a; border-color: #008a8a; }
    .fc .fc-button-primary:hover { background: #007070; border-color: #007070; }
    .fc .fc-button-primary:not(:disabled).fc-button-active { background: #005f5f; border-color: #005f5f; }
    .fc .fc-daygrid-event { border-radius: 4px; font-size: 11px; font-weight: 600; padding: 1px 4px; cursor: pointer; }
    .fc .fc-event-title { overflow: hidden; text-overflow: ellipsis; }
    .fc th { font-size: 11px; font-weight: 700; color: #64748b; }

    /* ── Tooltip ── */
    #cc-tooltip {
      position: fixed;
      z-index: 1000;
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      box-shadow: 0 12px 40px rgba(0,0,0,.16);
      width: 320px;
      max-width: 95vw;
      display: none;
      overflow: hidden;
    }
    .tt-head { padding: 12px 14px; border-bottom: 3px solid #3b82f6; display: flex; align-items: center; gap: 8px; }
    .tt-head-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
    .tt-head-label { font-size: 13px; font-weight: 800; color: #0f172a; flex: 1; }
    .tt-head-badge { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 99px; white-space: nowrap; }
    .tt-close { width: 24px; height: 24px; border-radius: 6px; border: 1px solid #e2e8f0; background: #f8fafc; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 12px; color: #64748b; flex-shrink: 0; }
    .tt-close:hover { background: #e2e8f0; }
    .tt-body { padding: 12px 14px; }
    .tt-asesor { display: flex; align-items: center; gap: 8px; background: #f8fafc; border-radius: 8px; padding: 7px 10px; margin-bottom: 10px; }
    .tt-av { width: 28px; height: 28px; border-radius: 50%; background: #ccfbf1; color: #0d9488; font-size: 11px; font-weight: 800; display: flex; align-items: center; justify-content: center; flex-shrink: 0; overflow: hidden; }
    .tt-av img { width: 100%; height: 100%; object-fit: cover; }
    .tt-av-name { font-size: 12px; font-weight: 700; color: #0f172a; }
    .tt-av-role { font-size: 10px; color: #64748b; }
    .tt-row { display: flex; align-items: flex-start; gap: 8px; padding: 5px 0; border-bottom: 1px solid #f1f5f9; }
    .tt-row:last-child { border-bottom: none; }
    .tt-lbl { font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: .05em; width: 88px; flex-shrink: 0; padding-top: 1px; }
    .tt-val { font-size: 11.5px; color: #0f172a; font-weight: 500; flex: 1; line-height: 1.4; word-break: break-word; }
    .tt-obs { background: #f8fafc; border-left: 3px solid #008a8a; border-radius: 0 6px 6px 0; padding: 7px 10px; margin-top: 8px; font-size: 11px; color: #475569; line-height: 1.5; }
    .tt-obs-lbl { font-size: 9px; font-weight: 700; color: #008a8a; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 3px; }
  </style>
</head>
<body>
  <%- include('../../partials/navbar') %>

  <div class="page-shell">
    <%- include('../partials/sidebar', {
      currentPath: currentPath,
      user: user,
      u: user
    }) %>

    <!-- ── Sidebar asesores ── -->
    <div class="cc-sidebar">
      <div class="cc-sidebar-title">Asesores activos</div>

      <% asesores.forEach(a => {
        const nombre = ((a.nombre || '') + (a.apellidos ? ' ' + a.apellidos : '')).trim() || a.username || '?';
        const inicial = nombre.charAt(0).toUpperCase();
      %>
        <label class="cc-asesor-item">
          <input type="checkbox" checked data-advisor-id="<%= a.id %>" class="cc-advisor-cb" />
          <div class="cc-av">
            <% if (a.avatar_url) { %>
              <img src="<%= a.avatar_url %>" alt="<%= inicial %>">
            <% } else { %>
              <%= inicial %>
            <% } %>
          </div>
          <span class="cc-asesor-name" title="<%= nombre %>"><%= nombre %></span>
          <div class="cc-badges">
            <% if (Number(a.citas_count) > 0) { %>
              <span class="cc-b cc-b-cita" title="Citas"><%= a.citas_count %></span>
            <% } %>
            <% if (Number(a.firma_count) > 0) { %>
              <span class="cc-b cc-b-firma" title="Firmas"><%= a.firma_count %></span>
            <% } %>
            <% if (Number(a.pago_count) > 0) { %>
              <span class="cc-b cc-b-pago" title="Firma+Pago"><%= a.pago_count %></span>
            <% } %>
          </div>
        </label>
      <% }) %>

      <div class="cc-legend">
        <div class="cc-legend-title">Leyenda</div>
        <div class="cc-legend-item">
          <div class="cc-legend-dot" style="background:#3b82f6;"></div>
          <span>Cita agendada</span>
        </div>
        <div class="cc-legend-item">
          <div class="cc-legend-dot" style="background:#16a34a;"></div>
          <span>Cierre con firma</span>
        </div>
        <div class="cc-legend-item">
          <div class="cc-legend-dot" style="background:#d97706;"></div>
          <span>Firma + Pago</span>
        </div>
      </div>
    </div>

    <!-- ── Contenido principal ── -->
    <div class="cc-main">
      <div class="cc-cal-header">
        <div>
          <h1 class="cc-cal-title">Citas & Cierres</h1>
          <p class="cc-cal-sub">Todos los asesores · Vista ejecutiva administración</p>
        </div>
      </div>

      <div id="cc-calendar"></div>
    </div>
  </div>

  <!-- ── Tooltip ── -->
  <div id="cc-tooltip">
    <div class="tt-head" id="tt-head">
      <div class="tt-head-dot" id="tt-dot"></div>
      <span class="tt-head-label" id="tt-label"></span>
      <span class="tt-head-badge" id="tt-badge"></span>
      <div class="tt-close" id="tt-close">✕</div>
    </div>
    <div class="tt-body" id="tt-body"></div>
  </div>

  <script>
  (function () {
    'use strict';

    const TZ = 'America/Mexico_City';

    /* ── Serializar eventos desde EJS ── */
    const ALL_EVENTS = [];

    /* Citas */
    <%- JSON.stringify(citas) %>.forEach(c => {
      const nombre = (c.lead_nombre || '') + (c.lead_apellido ? ' ' + c.lead_apellido : '');
      const asesor = (c.asesor_nombre || '') + (c.asesor_apellidos ? ' ' + c.asesor_apellidos : '');
      const fechaCDMX = c.inicio
        ? new Date(c.inicio).toLocaleString('es-MX', { timeZone: TZ, day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
        : '—';
      ALL_EVENTS.push({
        id: 'cita-' + c.id,
        title: 'Cita · ' + (nombre.trim() || '—'),
        start: c.inicio,
        end:   c.fin || undefined,
        backgroundColor: '#eff6ff',
        borderColor:     '#3b82f6',
        textColor:       '#1d4ed8',
        extendedProps: {
          tipo:              'cita',
          advisor_id:        c.advisor_id,
          lead_nombre:       nombre.trim() || '—',
          asesor_nombre:     asesor.trim() || '—',
          asesor_avatar:     c.asesor_avatar || null,
          telefono:          c.telefono || '—',
          email:             c.email || '—',
          portal:            c.portal || '—',
          propiedad_interes: c.propiedad_interes || '—',
          fecha_cdmx:        fechaCDMX,
          cita_observaciones: c.cita_observaciones || '',
        }
      });
    });

    /* Cierres con firma */
    <%- JSON.stringify(firmas) %>.forEach(f => {
      const nombre = (f.lead_nombre || '') + (f.lead_apellido ? ' ' + f.lead_apellido : '');
      const asesor = (f.asesor_nombre || '') + (f.asesor_apellidos ? ' ' + f.asesor_apellidos : '');
      const fechaCDMX = f.closed_at
        ? new Date(f.closed_at).toLocaleString('es-MX', { timeZone: TZ, day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
        : '—';
      ALL_EVENTS.push({
        id: 'firma-' + f.id,
        title: 'Firma · ' + (nombre.trim() || '—'),
        start: f.closed_at ? f.closed_at.toString().slice(0, 10) : undefined,
        allDay: true,
        backgroundColor: '#f0fdf4',
        borderColor:     '#16a34a',
        textColor:       '#15803d',
        extendedProps: {
          tipo:              'firma',
          advisor_id:        f.advisor_id,
          lead_nombre:       nombre.trim() || '—',
          asesor_nombre:     asesor.trim() || '—',
          asesor_avatar:     f.asesor_avatar || null,
          telefono:          f.telefono || '—',
          email:             f.email || '—',
          portal:            f.portal || '—',
          propiedad_interes: f.propiedad_interes || '—',
          fecha_cdmx:        fechaCDMX,
        }
      });
    });

    /* Cierres con firma y pago */
    <%- JSON.stringify(pagos) %>.forEach(p => {
      const nombre = (p.lead_nombre || '') + (p.lead_apellido ? ' ' + p.lead_apellido : '');
      const asesor = (p.asesor_nombre || '') + (p.asesor_apellidos ? ' ' + p.asesor_apellidos : '');
      const fechaCDMX = p.closed_at
        ? new Date(p.closed_at).toLocaleString('es-MX', { timeZone: TZ, day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
        : '—';
      ALL_EVENTS.push({
        id: 'pago-' + p.id,
        title: 'Firma+Pago · ' + (nombre.trim() || '—'),
        start: p.closed_at ? p.closed_at.toString().slice(0, 10) : undefined,
        allDay: true,
        backgroundColor: '#fef3c7',
        borderColor:     '#d97706',
        textColor:       '#92400e',
        extendedProps: {
          tipo:              'firma_pago',
          advisor_id:        p.advisor_id,
          lead_nombre:       nombre.trim() || '—',
          asesor_nombre:     asesor.trim() || '—',
          asesor_avatar:     p.asesor_avatar || null,
          telefono:          p.telefono || '—',
          email:             p.email || '—',
          portal:            p.portal || '—',
          propiedad_interes: p.propiedad_interes || '—',
          fecha_cdmx:        fechaCDMX,
        }
      });
    });

    /* ── Estado de filtro por asesor ── */
    const hiddenAdvisors = new Set();

    function visibleEvents() {
      return ALL_EVENTS.filter(e => !hiddenAdvisors.has(e.extendedProps.advisor_id));
    }

    /* ── FullCalendar ── */
    const calendarEl = document.getElementById('cc-calendar');
    const calendar = new FullCalendar.Calendar(calendarEl, {
      locale:      'es',
      timeZone:    TZ,
      initialView: 'dayGridMonth',
      height:      'auto',
      buttonText:  { today: 'Hoy', month: 'Mes', week: 'Semana', day: 'Día', list: 'Lista' },
      headerToolbar: {
        left:   'prev,next today',
        center: 'title',
        right:  'dayGridMonth,timeGridWeek,listMonth'
      },
      events: (info, success) => success(visibleEvents()),
      eventClick: (info) => {
        info.jsEvent.stopPropagation();
        showTooltip(info.event, info.jsEvent);
      },
    });
    calendar.render();

    /* ── Checkboxes de asesor ── */
    document.querySelectorAll('.cc-advisor-cb').forEach(cb => {
      cb.addEventListener('change', () => {
        const id = Number(cb.dataset.advisorId);
        if (cb.checked) hiddenAdvisors.delete(id);
        else            hiddenAdvisors.add(id);
        calendar.refetchEvents();
      });
    });

    /* ── Tooltip ── */
    const tooltip  = document.getElementById('cc-tooltip');
    const ttHead   = document.getElementById('tt-head');
    const ttDot    = document.getElementById('tt-dot');
    const ttLabel  = document.getElementById('tt-label');
    const ttBadge  = document.getElementById('tt-badge');
    const ttBody   = document.getElementById('tt-body');
    const ttClose  = document.getElementById('tt-close');

    function showTooltip(event, jsEvent) {
      const p = event.extendedProps;

      /* Colores según tipo */
      const META = {
        cita:      { label: 'Cita agendada',    badge: '📅 Cita',       borderColor: '#3b82f6', badgeBg: '#eff6ff', badgeColor: '#1d4ed8', dotBg: '#3b82f6' },
        firma:     { label: 'Cierre con firma',  badge: '✓ Firmado',     borderColor: '#16a34a', badgeBg: '#f0fdf4', badgeColor: '#15803d', dotBg: '#16a34a' },
        firma_pago:{ label: 'Firma + Pago',      badge: '✓ Firma+Pago',  borderColor: '#d97706', badgeBg: '#fef3c7', badgeColor: '#92400e', dotBg: '#d97706' },
      };
      const m = META[p.tipo] || META.cita;

      /* Header */
      ttHead.style.borderBottomColor = m.borderColor;
      ttDot.style.background         = m.dotBg;
      ttLabel.textContent            = m.label;
      ttBadge.textContent            = m.badge;
      ttBadge.style.background       = m.badgeBg;
      ttBadge.style.color            = m.badgeColor;

      /* Avatar del asesor */
      const inicialAsesor = (p.asesor_nombre || '?').charAt(0).toUpperCase();
      const avatarHtml = p.asesor_avatar
        ? `<img src="${p.asesor_avatar}" alt="${inicialAsesor}" style="width:100%;height:100%;object-fit:cover;">`
        : inicialAsesor;

      /* Body */
      const row = (lbl, val) =>
        `<div class="tt-row"><span class="tt-lbl">${lbl}</span><span class="tt-val">${val || '—'}</span></div>`;

      let html = `
        <div class="tt-asesor">
          <div class="tt-av">${avatarHtml}</div>
          <div>
            <div class="tt-av-name">${p.asesor_nombre || '—'}</div>
            <div class="tt-av-role">Asesor comercial</div>
          </div>
        </div>
        ${row('Lead', p.lead_nombre)}
        ${row('Fecha', p.fecha_cdmx)}
        ${row('Portal', p.portal)}
        ${row('Propiedad', p.propiedad_interes)}
        ${row('Teléfono', p.telefono)}
        ${row('Correo', p.email)}
      `;

      if (p.tipo === 'firma')      html += row('Tipo cierre', '✓ Firmó contrato');
      if (p.tipo === 'firma_pago') html += row('Tipo cierre', '✓ Firmó y pagó');

      if (p.tipo === 'cita' && p.cita_observaciones) {
        html += `<div class="tt-obs">
          <div class="tt-obs-lbl">Observaciones de la cita</div>
          ${p.cita_observaciones}
        </div>`;
      }

      ttBody.innerHTML = html;

      /* Posicionamiento */
      tooltip.style.display = 'block';
      const rect   = tooltip.getBoundingClientRect();
      const W      = window.innerWidth;
      const H      = window.innerHeight;
      let left = jsEvent.clientX + 12;
      let top  = jsEvent.clientY - 10;
      if (left + 340 > W) left = jsEvent.clientX - 340;
      if (top  + rect.height > H) top = H - rect.height - 10;
      if (top < 10) top = 10;
      if (left < 10) left = 10;
      tooltip.style.left = left + 'px';
      tooltip.style.top  = top  + 'px';
    }

    function closeTooltip() { tooltip.style.display = 'none'; }

    ttClose.addEventListener('click', closeTooltip);
    document.addEventListener('click', (e) => {
      if (!tooltip.contains(e.target)) closeTooltip();
    });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeTooltip(); });

  })();
  </script>

  <script src="/js/drawer.js"></script>
</body>
</html>
```

- [ ] **Step 2: Verificar en el navegador**

1. Abre `/administracion/citas-cierres` logueado como usuario con rol `administracion`
2. Verifica que el sidebar izquierdo muestra la lista de asesores con sus badges
3. Verifica que el calendario carga con eventos azules (citas), verdes (firmas) y ámbar (firma+pago)
4. Haz clic en un evento — debe aparecer el tooltip con la info del lead
5. Verifica que desmarcar un asesor en el sidebar oculta sus eventos del calendario
6. Presiona Escape o clic fuera del tooltip para cerrarlo
7. Verifica la leyenda al final del sidebar

---

## Verificación final

- [ ] `/administracion/citas-cierres` carga sin errores para rol `administracion`
- [ ] Sidebar de administración tiene link "Citas & Cierres" con estado activo correcto
- [ ] Calendario muestra los 3 tipos de eventos con colores correctos
- [ ] Checkboxes del sidebar filtran eventos del calendario
- [ ] Tooltip muestra: asesor, nombre lead, fecha CDMX, portal, propiedad, teléfono, correo
- [ ] Citas muestran bloque de observaciones si existen
- [ ] Cierres muestran tipo de cierre (firma / firma+pago)
- [ ] Cerrar tooltip con ✕, clic fuera, o Escape
- [ ] Sin errores en consola del navegador
