# Bandeja de Leads — Frontend 2A: Tabla + Panel Desktop + Tema

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rediseñar `views/advisor/crm/leads/index.ejs` con tabla 9 columnas, panel lateral desktop, KPIs compactos, leyenda semáforo, chips favoritos/fijados, ordenamiento por columna, paginación y tema claro/oscuro.

**Architecture:** Dentro de `<main>` todo el contenido de KPIs+filtros+tabla se mueve a una estructura `.shell` (CSS grid 2 col: `.t-col` flexible + `.p-col` 280px). La hoja `public/css/crm-leads-bandeja.css` contiene el CSS extraído del mockup v6. El script `public/js/crm-leads-bandeja.js` maneja toasts, fav/pin toggle y población del panel lateral vía `data-lead` JSON en cada `<tr>`. El backend (Plan 1) ya entrega `stats`, `idsFavoritos`, `idsFijados`, `page`, `totalPages`, `totalItems`, ordenamiento y paginación. Solo se extiende el LATERAL `last_my` en el servicio para agregar tipo de actividad y nombre del asesor.

**Tech Stack:** Node.js/Express v5, EJS (SSR), PostgreSQL `pg`, CSS vanilla (mockup v6), JS vanilla — sin dependencias nuevas.

---

## Mapa de archivos

| Archivo | Acción |
|---|---|
| `src/services/advisor/crm.service.js` | Extender LATERAL `last_my` con `type` y advisor name |
| `public/css/crm-leads-bandeja.css` | **Nuevo** — CSS extraído del mockup v6, adaptado |
| `public/js/crm-leads-bandeja.js` | **Nuevo** — toasts, fav/pin toggle, panel, tema |
| `views/advisor/crm/leads/index.ejs` | Rediseño: head wiring, helpers, KPIs, filtros, tabla 9-col, panel, paginación |

---

## Task 1: Extender LATERAL last_my en el servicio

**Files:**
- Modify: `src/services/advisor/crm.service.js:410-411` (aliases SELECT principal)
- Modify: `src/services/advisor/crm.service.js:431-440` (cuerpo del LATERAL)

- [ ] **Step 1: Verificar estado actual**

```bash
node -e "const s = require('./src/services/advisor/crm.service'); console.log('OK');"
```
Expected: `OK` (sin error de sintaxis)

- [ ] **Step 2: Agregar aliases en el SELECT principal (líneas 410–411)**

Cambiar de:
```javascript
      last_my.last_contact_summary AS last_contact_summary,
      last_my.last_contact_at AS last_contact_at,
```
A:
```javascript
      last_my.last_contact_summary AS last_contact_summary,
      last_my.last_contact_at AS last_contact_at,
      last_my.last_contact_type AS last_contact_type,
      last_my.last_contact_advisor_name AS last_contact_advisor_name,
```

- [ ] **Step 3: Extender el LATERAL (líneas 431–440)**

Cambiar de:
```javascript
    LEFT JOIN LATERAL (
      SELECT
        NULLIF(TRIM(COALESCE(a.observations,'')), '') AS last_contact_summary,
        a.created_at AS last_contact_at
      FROM crm_activities a
      WHERE a.lead_id = l.id
        AND ${lastMyAdvisorFilter}
      ORDER BY a.created_at DESC NULLS LAST, a.id DESC
      LIMIT 1
    ) last_my ON true
```
A:
```javascript
    LEFT JOIN LATERAL (
      SELECT
        NULLIF(TRIM(COALESCE(a.observations,'')), '') AS last_contact_summary,
        a.created_at AS last_contact_at,
        a.type AS last_contact_type,
        TRIM(COALESCE(au.nombre,'') || ' ' || COALESCE(au.apellidos,'')) AS last_contact_advisor_name
      FROM crm_activities a
      LEFT JOIN users au ON au.id = a.advisor_id
      WHERE a.lead_id = l.id
        AND ${lastMyAdvisorFilter}
      ORDER BY a.created_at DESC NULLS LAST, a.id DESC
      LIMIT 1
    ) last_my ON true
```

- [ ] **Step 4: Verificar sintaxis**

```bash
node -e "const s = require('./src/services/advisor/crm.service'); console.log('OK');"
```
Expected: `OK`

---

## Task 2: Crear public/css/crm-leads-bandeja.css

**Files:**
- Create: `public/css/crm-leads-bandeja.css`

El mockup v6 está en `.superpowers/brainstorm/1674-1781551972/content/opcion-b-v6.html`. El bloque `<style>` ocupa las líneas 7–483 (línea 7 = `<style>`, línea 483 = `</style>`). El CSS real es líneas 8–482.

- [ ] **Step 1: Extraer CSS del mockup (líneas 8–482) al nuevo archivo**

Leer `.superpowers/brainstorm/1674-1781551972/content/opcion-b-v6.html` líneas 8–482 con la herramienta Read y escribir el contenido en `public/css/crm-leads-bandeja.css`.

El archivo arrancará con:
```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Inter',system-ui,sans-serif;background:#f1f5f9;color:#0f172a;padding:20px;-webkit-font-smoothing:antialiased;font-size:12px;}
...
```

- [ ] **Step 2: Eliminar `padding:20px;` de la regla `body{...}`**

Usar Edit para cambiar la línea de body en el CSS de:
```css
body{font-family:'Inter',system-ui,sans-serif;background:#f1f5f9;color:#0f172a;padding:20px;-webkit-font-smoothing:antialiased;font-size:12px;}
```
A:
```css
body{font-family:'Inter',system-ui,sans-serif;background:#f1f5f9;color:#0f172a;-webkit-font-smoothing:antialiased;}
.shell{font-size:12px;}
```
(Mueve `font-size:12px` a `.shell` para no afectar el navbar/sidebar globales.)

- [ ] **Step 3: Verificar que el archivo existe y tiene las secciones clave**

```bash
grep -n "\.shell\|\.p-col\|body\.dark\|\.kpi-row\|\.legend-bar" public/css/crm-leads-bandeja.css | head -20
```
Expected: líneas con `.shell`, `.p-col`, `body.dark .kpi`, `.kpi-row`, `.legend-bar`

---

## Task 3: Crear public/js/crm-leads-bandeja.js

**Files:**
- Create: `public/js/crm-leads-bandeja.js`

- [ ] **Step 1: Escribir el archivo JS completo**

```javascript
/* ── crm-leads-bandeja.js ── */
(function () {
  'use strict';

  // ── Tema claro/oscuro ──────────────────────────────────────
  function applyTheme(dark) {
    document.body.classList.toggle('dark', dark);
    const sun  = document.getElementById('iconSun');
    const moon = document.getElementById('iconMoon');
    const lbl  = document.getElementById('themeLabel');
    const icon = document.getElementById('themeIcon');
    if (dark) {
      if (sun)  sun.style.display  = 'none';
      if (moon) moon.style.display = 'block';
      if (lbl)  lbl.textContent    = 'Tema oscuro';
      if (icon) icon.style.background = '#1c2230';
    } else {
      if (sun)  sun.style.display  = 'block';
      if (moon) moon.style.display = 'none';
      if (lbl)  lbl.textContent    = 'Tema claro';
      if (icon) icon.style.background = '#f1f5f9';
    }
  }

  window.toggleTheme = function () {
    const isDark = document.body.classList.toggle('dark');
    applyTheme(isDark);
    try { localStorage.setItem('theme', isDark ? 'dark' : 'light'); } catch(e){}
  };

  // Restaurar al cargar (anti-flash reforzado)
  (function () {
    try {
      if (localStorage.getItem('theme') === 'dark') applyTheme(true);
    } catch(e){}
  })();

  // ── Toasts ────────────────────────────────────────────────
  var toastArea = null;

  function ensureToastArea() {
    if (toastArea) return toastArea;
    toastArea = document.querySelector('.toast-area');
    if (!toastArea) {
      toastArea = document.createElement('div');
      toastArea.className = 'toast-area';
      document.body.appendChild(toastArea);
    }
    return toastArea;
  }

  function showToast(type, name, leadId) {
    var area = ensureToastArea();
    var t = document.createElement('div');
    var isStar = type === 'star-add' || type === 'star-remove';
    var isPin  = type === 'pin-add'  || type === 'pin-remove';
    t.className = 'toast ' + (isStar ? 'toast-star' : 'toast-pin');

    var iconHtml = isStar
      ? '<svg width="13" height="13" viewBox="0 0 24 24" fill="#f59e0b" stroke="#f59e0b" stroke-width="1.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>'
      : '<svg width="13" height="13" viewBox="0 0 24 24" fill="#008a8a" stroke="#008a8a" stroke-width="1.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3" fill="#fff"/></svg>';

    var msg = type === 'star-add'    ? 'Guardado en favoritos'
            : type === 'star-remove' ? 'Quitado de favoritos'
            : type === 'pin-add'     ? 'Lead fijado · Aparece primero'
            :                          'Lead desfijado';

    t.innerHTML =
      '<div class="toast-icon ' + (isStar ? 'ti-star' : 'ti-pin') + '">' + iconHtml + '</div>' +
      '<div>' +
        '<div style="font-size:11.5px;font-weight:700;color:#0f172a;">' + msg + '</div>' +
        '<div style="font-size:9px;color:#94a3b8;margin-top:1px;">' + escHtml(name) + ' · ID ' + leadId + '</div>' +
      '</div>';

    area.appendChild(t);
    setTimeout(function () { t.classList.add('visible'); }, 10);
    setTimeout(function () {
      t.classList.remove('visible');
      setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 300);
    }, 3000);
  }

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ── Favoritos toggle ──────────────────────────────────────
  function toggleFav(btn) {
    var leadId  = btn.dataset.leadId;
    var leadName = btn.dataset.leadName || 'Lead';
    var isOn    = btn.classList.contains('star-on');

    btn.classList.toggle('star-on', !isOn);
    btn.classList.toggle('star-off', isOn);
    var row = btn.closest('tr');
    if (row) {
      var d = safeLeadData(row);
      if (d) { d.is_fav = !isOn; row.dataset.lead = JSON.stringify(d); }
    }

    fetch('/profile/leads-favoritos/' + leadId + '/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (!data.ok) {
          btn.classList.toggle('star-on', isOn);
          btn.classList.toggle('star-off', !isOn);
          return;
        }
        showToast(data.action === 'added' ? 'star-add' : 'star-remove', leadName, leadId);
      })
      .catch(function() {
        btn.classList.toggle('star-on', isOn);
        btn.classList.toggle('star-off', !isOn);
      });
  }

  // ── Fijados toggle ────────────────────────────────────────
  function togglePin(btn) {
    var leadId   = btn.dataset.leadId;
    var leadName = btn.dataset.leadName || 'Lead';
    var isOn     = btn.classList.contains('pin-on');
    var row      = btn.closest('tr');

    btn.classList.toggle('pin-on', !isOn);
    if (row) {
      row.classList.toggle('pinned', !isOn);
      var d = safeLeadData(row);
      if (d) { d.is_pinned = !isOn; row.dataset.lead = JSON.stringify(d); }
    }

    fetch('/advisor/leads/' + leadId + '/pin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (!data.ok) {
          btn.classList.toggle('pin-on', isOn);
          if (row) row.classList.toggle('pinned', isOn);
          return;
        }
        showToast(data.action === 'added' ? 'pin-add' : 'pin-remove', leadName, leadId);
      })
      .catch(function() {
        btn.classList.toggle('pin-on', isOn);
        if (row) row.classList.toggle('pinned', isOn);
      });
  }

  // ── Panel lateral ─────────────────────────────────────────
  function safeLeadData(row) {
    try { return JSON.parse(row.dataset.lead || '{}'); } catch(e) { return null; }
  }

  function populatePanel(lead) {
    var panel = document.getElementById('leadPanel');
    if (!panel) return;

    var stLabel = lead._state === 'new' ? 'Nuevo'
                : (lead._state === 'won' || lead._state === 'lost') ? 'Cierre'
                : 'Seguimiento';
    var stCls   = lead._state === 'new' ? 'st-new'
                : (lead._state === 'won' || lead._state === 'lost') ? 'st-won'
                : 'st-follow';

    var priceTxt = lead.precio ? ('$' + Number(lead.precio).toLocaleString('es-MX')) : '—';
    var opTxt    = lead.operacion
      ? (lead.operacion.charAt(0).toUpperCase() + lead.operacion.slice(1))
      : 'Sin definir';

    var createdTxt = lead.created_at
      ? new Intl.DateTimeFormat('es-MX', {
          timeZone:'America/Mexico_City', dateStyle:'medium', timeStyle:'short'
        }).format(new Date(lead.created_at))
      : '—';

    var alertHtml = '';
    if (lead.escalacion_activa) {
      alertHtml = '<div class="p-alert" style="border-color:#d97706;color:#b45309;">' +
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>' +
        '<span class="p-alert-label">Escalación activa</span>' +
        '<span class="p-alert-val">Lead sin contacto</span>' +
        '</div>';
    } else if (lead.transferred_by_role === 'marketing') {
      alertHtml = '<div class="p-alert purple">' +
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>' +
        '<span class="p-alert-label">Transferido por Marketing</span>' +
        '<span class="p-alert-val">' + escHtml(lead.transferred_by_name) + '</span>' +
        '</div>';
    }

    var detailUrl  = '/advisor/leads/' + lead.id;
    var editUrl    = '/advisor/leads/' + lead.id + '/edit';
    var waUrl      = lead.telefono ? ('https://wa.me/52' + String(lead.telefono).replace(/\D/g,'')) : '#';
    var callUrl    = lead.telefono ? ('tel:' + lead.telefono) : '#';
    var citaUrl    = '/advisor/leads/' + lead.id;

    panel.innerHTML =
      '<div class="p-head">' +
        '<div class="p-eye">Lead seleccionado · ID ' + lead.id + '</div>' +
        '<div class="p-name">' + escHtml(lead.nombre) + ' ' + escHtml(lead.apellido) + '</div>' +
        '<div class="p-chips">' +
          '<span class="st ' + stCls + '">' + stLabel + '</span>' +
          (lead.transferred_by_role === 'marketing' ? '<span class="st" style="background:#ede9fe;color:#6d28d9;">Mktg</span>' : '') +
          (lead.portal ? '<span class="st" style="background:#f8fafc;color:#64748b;">' + escHtml(lead.portal) + '</span>' : '') +
          (lead.producto ? '<span class="st" style="background:#eff6ff;color:#1d4ed8;">' + escHtml(lead.producto) + '</span>' : '') +
        '</div>' +
        (lead.telefono ? '<div class="p-contact"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13.5a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2.69h3a2 2 0 0 1 2 1.72c.12.86.3 1.7.54 2.5a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6.18 6.18l1.27-1.27a2 2 0 0 1 2.11-.45c.8.24 1.64.42 2.5.54A2 2 0 0 1 22 16.92z"/></svg>' + escHtml(lead.telefono) + '</div>' : '') +
        (lead.email ? '<div class="p-contact"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>' + escHtml(lead.email) + '</div>' : '') +
        '<div class="p-contact"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>' + priceTxt + ' · ' + opTxt + '</div>' +
        '<div class="p-contact"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>Creado: ' + createdTxt + ' CDMX</div>' +
        alertHtml +
      '</div>' +
      '<div class="p-tabs">' +
        '<div class="p-tab on" data-tab="acciones">Acciones</div>' +
        '<div class="p-tab" data-tab="historial">Historial</div>' +
        '<div class="p-tab" data-tab="perfil">Perfil</div>' +
      '</div>' +
      '<div class="p-actions" id="panelAcciones">' +
        '<div class="p-sec-label">Acciones rápidas</div>' +
        '<div class="act-grid">' +
          '<a href="' + detailUrl + '#actividad" class="act-btn primary"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>Registrar actividad</a>' +
          '<a href="' + waUrl + '" target="_blank" class="act-btn green"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>WhatsApp</a>' +
          '<a href="' + callUrl + '" class="act-btn"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13.5a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2.69h3a2 2 0 0 1 2 1.72c.12.86.3 1.7.54 2.5a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6.18 6.18l1.27-1.27a2 2 0 0 1 2.11-.45c.8.24 1.64.42 2.5.54A2 2 0 0 1 22 16.92z"/></svg>Llamar</a>' +
          '<a href="' + citaUrl + '#cita" class="act-btn"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>Agendar cita</a>' +
          '<a href="' + detailUrl + '" class="act-btn"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>Ver detalle</a>' +
          '<a href="' + editUrl + '" class="act-btn"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/></svg>Editar lead</a>' +
        '</div>' +
      '</div>' +
      '<div style="display:none;" id="panelHistorial">' +
        '<div class="p-tl">' +
          '<div class="tl-hdr">Historial del lead</div>' +
          '<div class="tl-item">' +
            '<div class="tl-dot tld-reg"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg></div>' +
            '<div class="tl-body">' +
              '<div class="tl-type">Ver historial completo</div>' +
              '<div class="tl-obs"><a href="' + detailUrl + '" style="color:#008a8a;text-decoration:none;">Abrir ficha del lead →</a></div>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div style="display:none;" id="panelPerfil">' +
        '<div class="p-tl">' +
          '<div class="tl-hdr">Perfil del lead</div>' +
          '<div class="tl-item">' +
            '<div class="tl-dot tld-reg"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></div>' +
            '<div class="tl-body">' +
              '<div class="tl-type">Ver perfil completo</div>' +
              '<div class="tl-obs"><a href="' + detailUrl + '/profile" style="color:#008a8a;text-decoration:none;">Abrir perfil →</a></div>' +
            '</div>' +
          '</div>' +
        '</div>' +
      '</div>' +
      '<div class="p-foot">América/Mexico_City</div>';

    // Tabs dentro del panel
    panel.querySelectorAll('.p-tab').forEach(function(tab) {
      tab.addEventListener('click', function() {
        panel.querySelectorAll('.p-tab').forEach(function(t) { t.classList.remove('on'); });
        tab.classList.add('on');
        var target = tab.dataset.tab;
        panel.querySelector('#panelAcciones').style.display  = target === 'acciones'  ? '' : 'none';
        panel.querySelector('#panelHistorial').style.display = target === 'historial' ? '' : 'none';
        panel.querySelector('#panelPerfil').style.display    = target === 'perfil'    ? '' : 'none';
      });
    });
  }

  // Limpia panel al cargar (estado vacío)
  function resetPanel() {
    var panel = document.getElementById('leadPanel');
    if (!panel) return;
    panel.innerHTML =
      '<div style="padding:40px 20px;text-align:center;">' +
        '<div style="font-size:11px;color:#94a3b8;line-height:1.6;">Selecciona un lead<br>para ver acciones</div>' +
      '</div>';
  }

  // ── Delegación de eventos ──────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    resetPanel();

    document.addEventListener('click', function (e) {
      // Fav button
      var favBtn = e.target.closest('[data-action="fav"]');
      if (favBtn) { e.stopPropagation(); toggleFav(favBtn); return; }

      // Pin button
      var pinBtn = e.target.closest('[data-action="pin"]');
      if (pinBtn) { e.stopPropagation(); togglePin(pinBtn); return; }

      // Row click → populate panel
      var row = e.target.closest('tr[data-lead]');
      if (row) {
        document.querySelectorAll('tr[data-lead]').forEach(function(r) { r.classList.remove('row-sel'); });
        row.classList.add('row-sel');
        var lead = safeLeadData(row);
        if (lead && lead.id) populatePanel(lead);
        return;
      }
    });

    // Auto-submit búsqueda con delay
    var inputQ = document.getElementById('inputBusqueda');
    if (inputQ) {
      var timer;
      inputQ.addEventListener('input', function () {
        clearTimeout(timer);
        timer = setTimeout(function () {
          var form = document.getElementById('filtrosForm');
          if (form) form.submit();
        }, 500);
      });
    }

    // Dropdowns de filtro
    window.toggleFiltro = function (id) {
      var dd = document.getElementById(id);
      var isOpen = dd && dd.style.display !== 'none';
      ['ddFecha','ddOrden','ddMas'].forEach(function(d) {
        var el = document.getElementById(d); if (el) el.style.display = 'none';
      });
      if (!isOpen && dd) dd.style.display = 'block';
    };

    document.addEventListener('click', function(e) {
      if (!e.target.closest('[id^="dd"]') && !e.target.closest('button[onclick^="toggleFiltro"]')) {
        ['ddFecha','ddOrden','ddMas'].forEach(function(id) {
          var el = document.getElementById(id); if (el) el.style.display = 'none';
        });
      }
    });

    window.setPreset = function(val) {
      document.getElementById('inputPreset').value = val;
      var cd = document.getElementById('customDates');
      if (cd) cd.style.display = 'none';
      document.getElementById('filtrosForm').submit();
    };
    window.toggleCustomDates = function() {
      var cd = document.getElementById('customDates');
      if (!cd) return;
      cd.style.display = cd.style.display === 'none' ? 'flex' : 'none';
      if (cd.style.display === 'flex') cd.style.flexDirection = 'column';
    };
    window.setOrden = function(val) {
      document.getElementById('inputOrden').value = val;
      document.getElementById('filtrosForm').submit();
    };
  });

})();
```

- [ ] **Step 2: Verificar que el archivo existe**

```bash
node --check public/js/crm-leads-bandeja.js
```
Expected: sin output (sin errores de sintaxis)

---

## Task 4: Cabecera del EJS — wiring CSS, JS y anti-flash

**Files:**
- Modify: `views/advisor/crm/leads/index.ejs:3-8` (bloque `<head>`)

- [ ] **Step 1: Editar `<head>` del archivo**

Cambiar de (líneas 3–8):
```html
<head>
  <meta charset="UTF-8" />
  <title>CRM · Leads</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <link rel="stylesheet" href="/css/crm-mobile.css" />
</head>
```
A:
```html
<head>
  <meta charset="UTF-8" />
  <title>CRM · Leads</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <link rel="stylesheet" href="/css/crm-mobile.css" />
  <link rel="stylesheet" href="/css/crm-leads-bandeja.css" />
  <script>
  (function(){try{if(localStorage.getItem('theme')==='dark')document.body.classList.add('dark');}catch(e){}}());
  </script>
</head>
```

- [ ] **Step 2: Agregar `<script>` antes del cierre del archivo**

Al final del archivo, antes del `</body>`, agregar:
```html
<script src="/js/crm-leads-bandeja.js" defer></script>
```

(Buscar la última línea del archivo, que termina con `</body>` o similar, y agregar la línea antes.)

- [ ] **Step 3: Verificar que los archivos CSS y JS son accesibles**

Arrancar el servidor y visitar `/advisor/leads`. En DevTools > Network verificar que `crm-leads-bandeja.css` y `crm-leads-bandeja.js` retornan HTTP 200.

---

## Task 5: Actualizar bloque de helpers EJS (líneas 780–862)

**Files:**
- Modify: `views/advisor/crm/leads/index.ejs:780-862`

Este bloque contiene `crmMeta`, `fmtMoneyMXN`, `fmtDateMX`, `fmtCDMX`, y luego el cálculo `counts` (lines 837–862) que es incorrecto post-paginación (solo cuenta los 20 items de la página actual en lugar del total).

- [ ] **Step 1: Reemplazar el bloque completo lines 780–862**

Cambiar de (líneas 780–862, incluye helpers + cálculo `counts`):
```ejs
    <%
      // ==========================
      // Helpers UI (Enterprise)
      // ...
      const counts = { ... };
      for (const l of items) { ... }
    %>
```
A:
```ejs
    <%
      // ── Helpers EJS ──────────────────────────────────────
      function crmMeta(state) {
        switch ((state || '').toLowerCase()) {
          case 'transfer_out':
            return { row:'border-l-4 border-slate-400 bg-slate-50/60', chip:'bg-slate-100 text-slate-600 border-slate-200', label:'Traspaso', sub: null };
          case 'transfer_in':
            return { row:'border-l-4 border-blue-500 bg-blue-50/60', chip:'bg-blue-100 text-blue-700 border-blue-200', label:'Nuevo', sub: '(Traspaso)' };
          case 'won':
            return { row:'border-l-4 border-green-600 bg-green-50/60', chip:'bg-green-100 text-green-900 border-green-200', label:'Cierre', sub: null };
          case 'lost':
            return { row:'border-l-4 border-red-500 bg-red-50/60', chip:'bg-red-100 text-red-900 border-red-200', label:'Finalizado', sub: null };
          case 'followup_transfer': case 'followup':
            return { row:'border-l-4 border-amber-500 bg-amber-50/60', chip:'bg-amber-100 text-amber-900 border-amber-200', label:'Seguimiento', sub: null };
          default:
            return { row:'border-l-4 border-blue-500 bg-blue-50/60', chip:'bg-blue-100 text-blue-900 border-blue-200', label:'Nuevo', sub: null };
        }
      }

      function fmtMoneyMXN(v) {
        if (v === null || v === undefined || v === '') return '—';
        const n = Number(v);
        if (!Number.isFinite(n)) return '—';
        return '$' + n.toLocaleString('es-MX');
      }

      function fmtDateMX(v) {
        if (!v) return '—';
        try { return new Date(v).toLocaleDateString('es-MX'); }
        catch(e) { return '—'; }
      }

      function fmtCDMX(v, mode) {
        if (!v) return null;
        try {
          const d = new Date(v);
          if (Number.isNaN(d.getTime())) return null;
          const opts = mode === 'short'
            ? { timeZone:'America/Mexico_City', dateStyle:'medium', timeStyle:'short' }
            : { timeZone:'America/Mexico_City', dateStyle:'full', timeStyle:'short' };
          return new Intl.DateTimeFormat('es-MX', opts).format(d);
        } catch(e) { return null; }
      }

      // Semáforo "Sin contacto"
      function scInfo(lead) {
        if (!lead.last_contact_at) return { cls: 'sc-none', label: '—' };
        const diffMs = Date.now() - new Date(lead.last_contact_at).getTime();
        const days = diffMs / 86400000;
        if (days < 2)  return { cls: 'sc-ok',     label: days < 1 ? 'Hoy' : 'Ayer' };
        if (days < 5)  return { cls: 'sc-warn',   label: Math.floor(days) + ' días' };
        return           { cls: 'sc-danger', label: Math.floor(days) + ' días' };
      }

      // Badge tipo lead (solo para _state === 'new')
      function tipoBadge(lead, _state) {
        if (_state !== 'new') return null;
        if (lead.escalacion_activa)
          return { cls: 'tipo-esc', label: 'Escalado' };
        if (lead.transferred_by_role === 'marketing') {
          const firstName = (lead.transferred_by_name || '').split(' ')[0] || '';
          return { cls: 'tipo-mktg', label: 'Mktg' + (firstName ? ' · ' + firstName : '') };
        }
        return { cls: 'tipo-propio', label: 'Propio' };
      }

      // Badge producto
      function prodBadge(prod) {
        const map = { outlet:'prod-outlet', residencial:'prod-residencial', renova:'prod-renova', micro:'prod-micro', legal:'prod-legal' };
        const p   = (prod || '').toLowerCase();
        return { cls: map[p] || 'prod-nd', lbl: prod || 'Sin definir' };
      }

      // SVG + clase para icono de actividad
      function lcIconSVG(type) {
        const icons = {
          call: { cls:'call', svg:'<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 13.5a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 2.69h3a2 2 0 0 1 2 1.72c.12.86.3 1.7.54 2.5a2 2 0 0 1-.45 2.11L7.91 9.91a16 16 0 0 0 6.18 6.18l1.27-1.27a2 2 0 0 1 2.11-.45c.8.24 1.64.42 2.5.54A2 2 0 0 1 22 16.92z"/></svg>' },
          chat: { cls:'chat', svg:'<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>' },
          cal:  { cls:'cal',  svg:'<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>' },
          reg:  { cls:'reg',  svg:'<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" y1="8" x2="19" y2="14"/><line x1="16" y1="11" x2="22" y2="11"/></svg>' },
          esc:  { cls:'esc',  svg:'<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#d97706" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>' },
        };
        const tmap = {
          call:'call', llamada:'call',
          whatsapp:'chat', mensaje:'chat', email:'chat', chat:'chat',
          visit:'cal', cita:'cal', visita:'cal',
          registro:'reg', asignacion:'reg', note:'reg', nota:'reg',
          escalacion:'esc',
        };
        const cls = tmap[(type||'').toLowerCase()] || 'reg';
        return icons[cls];
      }

      // Info de "Último contacto"
      function lcInfo(lead) {
        if (!lead.last_contact_at) return null;
        const icon = lcIconSVG(lead.last_contact_type || '');
        const diffMs = Date.now() - new Date(lead.last_contact_at).getTime();
        const mins = Math.floor(diffMs / 60000);
        let ago;
        if (mins < 60)         ago = 'hace ' + mins + ' min';
        else if (mins < 1440)  ago = 'hace ' + Math.floor(mins/60) + ' h';
        else                   ago = 'hace ' + Math.floor(mins/1440) + ' días';
        const sc = scInfo(lead);
        const agoCls = sc.cls === 'sc-ok' ? 'ago-ok' : sc.cls === 'sc-warn' ? 'ago-warn' : sc.cls === 'sc-danger' ? 'ago-danger' : 'ago-none';
        const metaDate = fmtCDMX(lead.last_contact_at, 'short') || '';
        return { icon, ago, agoCls, metaDate };
      }
    %>
```

- [ ] **Step 2: Verificar que el EJS carga sin error de sintaxis**

```bash
node -e "const ejs = require('ejs'); const fs = require('fs'); ejs.renderFile('views/advisor/crm/leads/index.ejs', {result:{items:[]},stats:{total:0,nuevos:0,seguimiento:0,cierres:0,finalizados:0,traspasos:0,pipeline:0,followups:0,appointments:0},kpis:{},filters:{},portales:[],idsFavoritos:[],idsFijados:[],page:1,totalPages:1,totalItems:0,user:{id:1,nombre:'Test',apellidos:'',role:'advisor'},viewMode:'advisor'}, {}, (err, html) => { if(err) console.error(err.message); else console.log('OK'); });"
```
Expected: `OK`

---

## Task 6: Reemplazar título + KPIs + leyenda (líneas 752–1007)

**Files:**
- Modify: `views/advisor/crm/leads/index.ejs:752-1007`

- [ ] **Step 1: Reemplazar el bloque completo**

Cambiar de (línea 752 `<div class="crm-desktop-filters ...` hasta línea 1007 cierre de KPIs operativos `</div>`):

```
    <div class="crm-desktop-filters flex flex-col lg:flex-row ...>
      ...
    </div>   <!-- fin crm-desktop-filters 752-778 -->
    
    <!-- KPIs (líneas 864-971) -->
    ...
    <!-- KPIs Operativos (líneas 973-1007) -->
    ...
```

A:

```ejs
    <!-- ═══ NUEVO LAYOUT DESKTOP ═══ -->
    <div class="shell">
      <div class="t-col">

        <!-- Encabezado -->
        <div class="t-head">
          <div>
            <div class="t-eyebrow">CRM · Leads</div>
            <div class="t-title">Bandeja de leads</div>
          </div>
          <div style="display:flex;gap:8px;align-items:center;">
            <% if (!_isDirectivoView) { %>
            <a href="/advisor/leads/new" class="t-new-btn">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Nuevo lead
            </a>
            <% } %>
            <a href="<%= _hrefDashboard() %>" style="font-size:11px;color:#64748b;text-decoration:none;padding:6px 10px;border:0.5px solid #e5e7eb;border-radius:8px;background:#fff;">Dashboard</a>
          </div>
        </div>

        <!-- KPI row compacto usando stats.* (totales reales, no paginados) -->
        <div class="kpi-row">
          <div class="kpi">
            <div class="kpi-l">Total</div>
            <div class="kpi-v teal"><%= stats.total %></div>
            <div class="kpi-s">Activos</div>
          </div>
          <div class="kpi">
            <div class="kpi-l">Nuevos</div>
            <div class="kpi-v blue"><%= stats.nuevos %></div>
            <div class="kpi-s">Sin contacto</div>
          </div>
          <div class="kpi">
            <div class="kpi-l">Seguim.</div>
            <div class="kpi-v amber"><%= stats.seguimiento %></div>
            <div class="kpi-s">En gestión</div>
          </div>
          <div class="kpi">
            <div class="kpi-l">Cierres</div>
            <div class="kpi-v emerald"><%= stats.cierres %></div>
            <div class="kpi-s">Vendidos</div>
          </div>
          <div class="kpi dim">
            <div class="kpi-l">Final.</div>
            <div class="kpi-v"><%= stats.finalizados %></div>
            <div class="kpi-s">Ocultos</div>
            <div class="kpi-lock"><svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></div>
          </div>
          <div class="kpi dim">
            <div class="kpi-l">Traspaso</div>
            <div class="kpi-v"><%= stats.traspasos %></div>
            <div class="kpi-s">Ocultos</div>
            <div class="kpi-lock"><svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg></div>
          </div>
        </div>

        <!-- Leyenda semáforo + tipo de nuevo -->
        <div class="legend-bar">
          <div class="legend-row">
            <span class="legend-label">Sin contacto</span>
            <div class="legend-items">
              <span class="li"><span class="li-dot dot-ok"></span>Hoy o ayer</span>
              <span class="li"><span class="li-dot dot-warn"></span>2 – 4 días</span>
              <span class="li"><span class="li-dot dot-danger"></span>5 días o más</span>
              <span class="li"><span class="li-dot dot-none"></span>Sin registro</span>
            </div>
          </div>
          <div style="height:1px;background:#f1f5f9;"></div>
          <div class="legend-row">
            <span class="legend-label">Tipo de nuevo</span>
            <div class="legend-items">
              <span class="li"><span class="li-badge badge-propio">Propio</span>Registrado por ti</span>
              <span class="li"><span class="li-badge badge-mktg">Mktg</span>Desde marketing</span>
              <span class="li"><span class="li-badge badge-esc">Escalado</span>Escalación automática</span>
            </div>
          </div>
        </div>
```

- [ ] **Step 2: Verificar EJS sin error** (mismo comando de Task 5 Step 2)

---

## Task 7: Reemplazar barra de filtros (líneas 1009–1188)

**Files:**
- Modify: `views/advisor/crm/leads/index.ejs:1009-1188`

- [ ] **Step 1: Reemplazar barra de filtros**

Cambiar de (líneas 1009–1188, desde `qWith` helper + form hasta fin del script inline):

A:
```ejs
        <%
        function qWith(extra) {
          const base = Object.assign({}, filters || {}, extra);
          return '?' + Object.entries(base)
            .filter(([,v]) => v !== '' && v !== null && v !== undefined && v !== false)
            .map(([k,v]) => encodeURIComponent(k) + '=' + encodeURIComponent(v))
            .join('&');
        }
        const _f = filters || {};
        %>

        <!-- Barra de búsqueda + dropdowns -->
        <form method="GET" action="" id="filtrosForm">
          <div class="f-row">
            <div class="f-search">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#b4bfcc" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input type="text" name="q" id="inputBusqueda" value="<%= _f.q || '' %>"
                     placeholder="Nombre, teléfono, email, ID…"
                     autocomplete="off"
                     style="background:none;border:none;outline:none;flex:1;font-size:11.5px;color:#0f172a;font-family:inherit;">
              <span class="f-hint">ej. #421</span>
            </div>

            <!-- Fecha -->
            <div style="position:relative;">
              <button type="button" class="f-btn <%= _f.desde ? 'on' : '' %>" onclick="toggleFiltro('ddFecha')">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                Fecha
              </button>
              <div id="ddFecha" style="display:none;position:absolute;top:calc(100% + 4px);left:0;z-index:99;background:#fff;border:0.5px solid #d1d5db;border-radius:10px;padding:8px;min-width:210px;box-shadow:0 4px 12px rgba(0,0,0,.08);">
                <div onclick="setPreset('hoy')"  style="padding:7px 10px;font-size:12px;border-radius:6px;cursor:pointer;background:<%= _f.preset==='hoy'?'#e1f5ee':'transparent' %>">Hoy</div>
                <div onclick="setPreset('7d')"   style="padding:7px 10px;font-size:12px;border-radius:6px;cursor:pointer;background:<%= _f.preset==='7d'?'#e1f5ee':'transparent' %>">Últimos 7 días</div>
                <div onclick="setPreset('30d')"  style="padding:7px 10px;font-size:12px;border-radius:6px;cursor:pointer;background:<%= _f.preset==='30d'?'#e1f5ee':'transparent' %>">Últimos 30 días</div>
                <div style="height:0.5px;background:#e5e7eb;margin:4px 0;"></div>
                <div onclick="toggleCustomDates()" style="padding:7px 10px;font-size:12px;border-radius:6px;cursor:pointer;">Fecha personalizada</div>
                <div id="customDates" style="display:<%= (_f.desde && !_f.preset)?'flex':'none' %>;flex-direction:column;gap:6px;padding:8px 10px;">
                  <label style="font-size:11px;color:#6b7280;">Desde</label>
                  <input type="datetime-local" name="desde" value="<%= _f.desde || '' %>" style="font-size:12px;border:0.5px solid #d1d5db;border-radius:6px;padding:4px 8px;">
                  <label style="font-size:11px;color:#6b7280;">Hasta</label>
                  <input type="datetime-local" name="hasta" value="<%= _f.hasta || '' %>" style="font-size:12px;border:0.5px solid #d1d5db;border-radius:6px;padding:4px 8px;">
                  <button type="submit" style="padding:5px;background:#008a8a;color:#fff;border:none;border-radius:6px;font-size:12px;cursor:pointer;">Aplicar</button>
                </div>
                <input type="hidden" name="preset" id="inputPreset" value="<%= _f.preset || '' %>">
              </div>
            </div>

            <!-- Antigüedad -->
            <div style="position:relative;">
              <button type="button" class="f-btn <%= _f.orden==='asc'?'on':'' %>" onclick="toggleFiltro('ddOrden')">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 5 5 12"/></svg>
                Reciente
              </button>
              <div id="ddOrden" style="display:none;position:absolute;top:calc(100% + 4px);left:0;z-index:99;background:#fff;border:0.5px solid #d1d5db;border-radius:10px;padding:8px;min-width:190px;box-shadow:0 4px 12px rgba(0,0,0,.08);">
                <div onclick="setOrden('desc')" style="padding:7px 10px;font-size:12px;border-radius:6px;cursor:pointer;background:<%= _f.orden!=='asc'?'#e1f5ee':'transparent' %>;">Más reciente primero</div>
                <div onclick="setOrden('asc')"  style="padding:7px 10px;font-size:12px;border-radius:6px;cursor:pointer;background:<%= _f.orden==='asc'?'#e1f5ee':'transparent' %>;">Más antiguo primero</div>
                <input type="hidden" name="orden" id="inputOrden" value="<%= _f.orden || 'desc' %>">
              </div>
            </div>

            <!-- Más filtros -->
            <div style="position:relative;">
              <% const _nMas = [_f.operacion,_f.portal,_f.con_actividad,_f.con_perfil].filter(Boolean).length; %>
              <button type="button" class="f-btn <%= _nMas>0?'on':'' %>" onclick="toggleFiltro('ddMas')">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="14" y2="12"/><line x1="4" y1="18" x2="10" y2="18"/></svg>
                Filtros<% if (_nMas>0) { %> · <%= _nMas %><% } %>
              </button>
              <div id="ddMas" style="display:none;position:absolute;top:calc(100% + 4px);right:0;z-index:99;background:#fff;border:0.5px solid #d1d5db;border-radius:10px;padding:12px;min-width:280px;box-shadow:0 4px 12px rgba(0,0,0,.08);">
                <div style="font-size:10px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;">Actividad</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:10px;">
                  <label style="display:flex;align-items:center;gap:6px;font-size:12px;padding:6px 8px;border:0.5px solid #e5e7eb;border-radius:6px;cursor:pointer;"><input type="radio" name="con_actividad" value="si" <%= _f.con_actividad==='si'?'checked':'' %>> Con actividad</label>
                  <label style="display:flex;align-items:center;gap:6px;font-size:12px;padding:6px 8px;border:0.5px solid #e5e7eb;border-radius:6px;cursor:pointer;"><input type="radio" name="con_actividad" value="no" <%= _f.con_actividad==='no'?'checked':'' %>> Sin actividad</label>
                </div>
                <div style="font-size:10px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;">Perfilamiento</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:10px;">
                  <label style="display:flex;align-items:center;gap:6px;font-size:12px;padding:6px 8px;border:0.5px solid #e5e7eb;border-radius:6px;cursor:pointer;"><input type="radio" name="con_perfil" value="si" <%= _f.con_perfil==='si'?'checked':'' %>> Con perfil</label>
                  <label style="display:flex;align-items:center;gap:6px;font-size:12px;padding:6px 8px;border:0.5px solid #e5e7eb;border-radius:6px;cursor:pointer;"><input type="radio" name="con_perfil" value="no" <%= _f.con_perfil==='no'?'checked':'' %>> Sin perfil</label>
                </div>
                <div style="font-size:10px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;">Origen</div>
                <select name="portal" style="width:100%;padding:6px 8px;font-size:12px;border:0.5px solid #e5e7eb;border-radius:6px;margin-bottom:10px;">
                  <option value="">Todos los portales</option>
                  <% (portales||[]).forEach(p => { %><option value="<%= p %>" <%= _f.portal===p?'selected':'' %>><%= p %></option><% }); %>
                </select>
                <div style="font-size:10px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;">Tipo de operación</div>
                <select name="operacion" style="width:100%;padding:6px 8px;font-size:12px;border:0.5px solid #e5e7eb;border-radius:6px;margin-bottom:12px;">
                  <option value="">Todas</option>
                  <option value="compra" <%= _f.operacion==='compra'?'selected':'' %>>Compra</option>
                  <option value="renta"  <%= _f.operacion==='renta'?'selected':'' %>>Renta</option>
                  <option value="inversion" <%= _f.operacion==='inversion'?'selected':'' %>>Inversión</option>
                </select>
                <button type="submit" style="width:100%;padding:7px;background:#008a8a;color:#fff;border:none;border-radius:6px;font-size:13px;font-weight:500;cursor:pointer;">Aplicar filtros</button>
              </div>
            </div>

            <a href="?" style="font-size:11px;color:#94a3b8;text-decoration:none;padding:6px 4px;">✕</a>
          </div>

          <!-- Chips de estado + favoritos + fijados -->
          <div class="chip-row">
            <a href="<%= qWith({estado:'all', page:1}) %>" class="s-chip <%= (!_f.estado||_f.estado==='all')?'on':'off' %>">Todos · <%= totalItems %></a>
            <a href="<%= qWith({estado:'new', page:1}) %>" class="s-chip <%= _f.estado==='new'?'on':'off' %>">Nuevo · <%= stats.nuevos %></a>
            <a href="<%= qWith({estado:'followup', page:1}) %>" class="s-chip <%= _f.estado==='followup'?'on':'off' %>">Seguimiento · <%= stats.seguimiento %></a>
            <a href="<%= qWith({estado:'won', page:1}) %>" class="s-chip <%= _f.estado==='won'?'on':'off' %>">Cierre · <%= stats.cierres %></a>
            <a href="<%= qWith({fav:'1', estado:'all', page:1}) %>" class="s-chip fav <%= _f.fav?'on':'' %>">
              <svg width="8" height="8" viewBox="0 0 24 24" fill="#f59e0b" stroke="#f59e0b" stroke-width="1.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
              Favoritos · <%= (idsFavoritos||[]).length %>
            </a>
            <a href="<%= qWith({fijado:'1', estado:'all', page:1}) %>" class="s-chip pin <%= _f.fijado?'on':'' %>">
              <svg width="8" height="8" viewBox="0 0 24 24" fill="#008a8a" stroke="#008a8a" stroke-width="1.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3" fill="#fff"/></svg>
              Fijados · <%= (idsFijados||[]).length %>
            </a>
            <span class="s-chip locked">
              <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              Finalizado (<%= stats.finalizados %>) · próximamente
            </span>
            <span class="s-chip locked">
              <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              Traspaso (<%= stats.traspasos %>) · próximamente
            </span>
            <input type="hidden" name="estado" value="<%= _f.estado||'all' %>">
            <input type="hidden" name="orden_campo" value="<%= _f.orden_campo||'sin_contacto' %>">
            <input type="hidden" name="orden_dir"   value="<%= _f.orden_dir||'asc' %>">
          </div>
        </form>
```

- [ ] **Step 2: Verificar EJS sin error** (mismo comando de Task 5 Step 2)

---

## Task 8: Reemplazar tabla, agregar panel y paginación (líneas 1190–1436)

**Files:**
- Modify: `views/advisor/crm/leads/index.ejs:1190-1436`

Este es el paso más grande. Reemplaza el contenido desde el encabezado de la tabla hasta el cierre del script `toggleLeadFav`.

- [ ] **Step 1: Reemplazar bloque completo (líneas 1190–1436)**

Cambiar de:
```
    <!-- Table -->
    <div class="mt-6 bg-white rounded-2xl ...">
      ...
    </div>

<script>
function toggleLeadFav(...) { ... }
</script>
```

A:
```ejs
        <!-- Tabla de 9 columnas -->
        <div class="t-wrap">
          <table>
            <thead>
              <tr>
                <%
                const _oc = _f.orden_campo || 'sin_contacto';
                const _od = _f.orden_dir   || 'asc';
                function sortLink(campo) {
                  const dir = (_oc === campo && _od === 'asc') ? 'desc' : 'asc';
                  return qWith({ orden_campo: campo, orden_dir: dir, page: 1 });
                }
                function sortArrow(campo) {
                  if (_oc !== campo) return '↕';
                  return _od === 'asc' ? '↑' : '↓';
                }
                %>
                <th style="width:15%"><a href="<%= sortLink('lead') %>" style="text-decoration:none;color:inherit;">Lead <span class="s"><%= sortArrow('lead') %></span></a></th>
                <th style="width:9%">Contacto</th>
                <th style="width:5%">Origen</th>
                <th style="width:7%"><a href="<%= sortLink('creado') %>" style="text-decoration:none;color:inherit;">Creado <span class="s"><%= sortArrow('creado') %></span></a></th>
                <th style="width:7%"><a href="<%= sortLink('precio') %>" style="text-decoration:none;color:inherit;">Precio <span class="s"><%= sortArrow('precio') %></span></a></th>
                <th style="width:7%">Producto</th>
                <th style="width:28%"><a href="<%= sortLink('ultimo_contacto') %>" style="text-decoration:none;color:inherit;">Último contacto <span class="s"><%= sortArrow('ultimo_contacto') %></span></a></th>
                <th style="width:8%"><a href="<%= sortLink('sin_contacto') %>" style="text-decoration:none;color:inherit;">Sin cont. <span class="s"><%= sortArrow('sin_contacto') %></span></a></th>
                <th style="width:9%">Estado</th>
              </tr>
            </thead>
            <tbody>
            <% (result.items || []).forEach(lead => {
                 const currentUserId    = user && user.id;
                 const isTransferredOut = lead.transferred_by == currentUserId;
                 const baseState        = lead.crm_state || 'new';
                 let _state;
                 if (baseState === 'won' || baseState === 'lost') {
                   _state = baseState;
                 } else if (isTransferredOut) {
                   _state = 'transfer_out';
                 } else if (lead.transferred_to != null && !isTransferredOut && baseState === 'new') {
                   _state = 'transfer_in';
                 } else {
                   _state = baseState;
                 }

                 // Solo mostrar new/followup/followup_transfer/won/lost
                 if (_state === 'transfer_out' || _state === 'transfer_in') return;

                 const sc   = scInfo(lead);
                 const tipo = tipoBadge(lead, _state);
                 const pb   = prodBadge(lead.producto);
                 const lc   = lcInfo(lead);
                 const isFav    = (idsFavoritos||[]).includes(Number(lead.id));
                 const isPinned = !!lead.is_pinned;

                 let trClass = '';
                 if (isPinned) trClass += ' pinned';
                 if (_state === 'new' && lead.escalacion_activa) trClass += ' sel-esc';
                 else if (_state === 'new' && lead.transferred_by_role === 'marketing') trClass += ' sel-mktg';

                 const stCls = _state === 'new' ? 'st-new'
                             : (_state === 'won' || _state === 'lost') ? 'st-won'
                             : 'st-follow';
                 const stLbl = _state === 'new' ? 'Nuevo'
                             : (_state === 'won' || _state === 'lost') ? 'Cierre'
                             : 'Seguimiento';

                 const leadData = JSON.stringify({
                   id: lead.id,
                   nombre: lead.nombre || '',
                   apellido: lead.apellido || '',
                   telefono: lead.telefono || '',
                   email: lead.email || '',
                   precio: lead.precio || null,
                   operacion: lead.operacion || '',
                   portal: lead.portal || '',
                   created_at: lead.created_at || null,
                   _state,
                   transferred_by_role: lead.transferred_by_role || '',
                   transferred_by_name: lead.transferred_by_name || '',
                   escalacion_activa: !!lead.escalacion_activa,
                   is_pinned: isPinned,
                   is_fav: isFav,
                   producto: lead.producto || '',
                   last_contact_type: lead.last_contact_type || '',
                   last_contact_at: lead.last_contact_at || null,
                   last_contact_summary: lead.last_contact_summary || '',
                   last_contact_advisor_name: lead.last_contact_advisor_name || '',
                 }).replace(/"/g, '&quot;');
            %>
              <tr class="<%= trClass %>" data-lead="<%= leadData %>">
                <!-- Col 1: Lead -->
                <td>
                  <div class="lead-cell">
                    <div class="lead-top">
                      <span class="ln"><%= lead.nombre %> <%= lead.apellido %></span>
                    </div>
                    <div class="lm">ID <%= lead.id %><% if (lead.portal) { %> · <%= lead.portal %><% } %></div>
                    <% if (tipo) { %>
                    <div class="tipo <%= tipo.cls %>"<% if(tipo.cls==='tipo-esc'){%> style="animation:pulse 2s infinite;"<%}%>>
                      <% if (tipo.cls === 'tipo-propio') { %><svg width="7" height="7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                      <% } else if (tipo.cls === 'tipo-mktg') { %><svg width="7" height="7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                      <% } else { %><svg width="7" height="7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                      <% } %>
                      <%= tipo.label %>
                    </div>
                    <% } %>
                    <div class="lead-actions">
                      <div class="icon-btn <%= isFav ? 'star-on' : '' %>"
                           data-action="fav"
                           data-lead-id="<%= lead.id %>"
                           data-lead-name="<%= lead.nombre %> <%= lead.apellido %>"
                           title="<%= isFav ? 'Quitar de favoritos' : 'Agregar a favoritos' %>">
                        <% if (isFav) { %>
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="#f59e0b" stroke="#f59e0b" stroke-width="1.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                        <% } else { %>
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
                        <% } %>
                      </div>
                      <div class="icon-btn <%= isPinned ? 'pin-on' : '' %>"
                           data-action="pin"
                           data-lead-id="<%= lead.id %>"
                           data-lead-name="<%= lead.nombre %> <%= lead.apellido %>"
                           title="<%= isPinned ? 'Desfijar' : 'Fijar lead' %>">
                        <% if (isPinned) { %>
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="#008a8a" stroke="#008a8a" stroke-width="1.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3" fill="#fff"/></svg>
                        <% } else { %>
                          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#d1d5db" stroke-width="1.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3" fill="none"/></svg>
                        <% } %>
                      </div>
                    </div>
                  </div>
                </td>

                <!-- Col 2: Contacto -->
                <td>
                  <div style="font-size:10.5px;color:#374151;font-weight:500;"><%= lead.telefono || '—' %></div>
                  <% if (lead.email) { %><div style="font-size:8.5px;color:#94a3b8;"><%= lead.email %></div><% } %>
                </td>

                <!-- Col 3: Origen -->
                <td><span style="font-size:9.5px;color:#64748b;"><%= lead.portal || '—' %></span></td>

                <!-- Col 4: Creado -->
                <td>
                  <%
                  const _createdFmt = fmtCDMX(lead.created_at, 'short');
                  const _createdParts = _createdFmt ? _createdFmt.split(',') : ['—'];
                  %>
                  <div class="fc-main"><%= _createdParts[0] || '—' %></div>
                  <% if (_createdParts[1]) { %><div class="fc-sub"><%= _createdParts[1].trim() %></div><% } %>
                </td>

                <!-- Col 5: Precio -->
                <td>
                  <div class="precio-val"><%= fmtMoneyMXN(lead.precio) %></div>
                  <div class="precio-sub"><%= lead.operacion ? (lead.operacion.charAt(0).toUpperCase()+lead.operacion.slice(1)) : 'Sin definir' %></div>
                </td>

                <!-- Col 6: Producto -->
                <td><span class="prod-badge <%= pb.cls %>"><%= pb.lbl %></span></td>

                <!-- Col 7: Último contacto -->
                <td>
                  <% if (lc) { %>
                  <div class="lc">
                    <div class="lc-top">
                      <div class="lc-icon <%= lc.icon.cls %>"><%- lc.icon.svg %></div>
                      <span class="lc-type"><%= lead.last_contact_type || 'Actividad' %></span>
                      <span class="lc-ago <%= lc.agoCls %>"><%= lc.ago %></span>
                    </div>
                    <% if (lead.last_contact_summary) { %>
                    <div class="lc-msg"><%= lead.last_contact_summary %></div>
                    <% } %>
                    <div class="lc-meta">
                      <svg width="7" height="7" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                      <%= lc.metaDate %><% if (lead.last_contact_advisor_name) { %> · <%= lead.last_contact_advisor_name %><% } %>
                    </div>
                  </div>
                  <% } else { %>
                  <span style="font-size:9.5px;color:#94a3b8;">Sin actividad</span>
                  <% } %>
                </td>

                <!-- Col 8: Sin contacto -->
                <td><span class="sc-badge <%= sc.cls %>"><%= sc.label %></span></td>

                <!-- Col 9: Estado -->
                <td><span class="st <%= stCls %>"><%= stLbl %></span></td>
              </tr>
            <% }); %>
            </tbody>
          </table>
        </div>

        <!-- Estado vacío -->
        <% if (!(result.items||[]).filter(l => { const uid=user&&user.id; const out=l.transferred_by==uid; const base=l.crm_state||'new'; const s=base==='won'||base==='lost'?base:out?'transfer_out':l.transferred_to!=null&&!out&&base==='new'?'transfer_in':base; return s!=='transfer_out'&&s!=='transfer_in'; }).length) { %>
        <div style="padding:40px;text-align:center;">
          <h3 style="font-size:14px;font-weight:600;color:#0f172a;margin-bottom:8px;">Aún no tienes leads</h3>
          <p style="font-size:12px;color:#64748b;">Crea tu primer registro para iniciar el pipeline.</p>
          <% if (!_isDirectivoView) { %>
          <a href="/advisor/leads/new" class="t-new-btn" style="margin-top:16px;display:inline-flex;">+ Nuevo lead</a>
          <% } %>
        </div>
        <% } %>

        <!-- Paginación -->
        <% if (totalPages > 1) { %>
        <div class="pag">
          <span class="pag-info">Mostrando <%= ((page-1)*20)+1 %> – <%= Math.min(page*20, totalItems) %> de <%= totalItems %> leads</span>
          <div class="pag-btns">
            <a href="<%= qWith({page: page-1}) %>" class="pb <%= page<=1 ? 'dis' : '' %>">
              <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
            </a>
            <% for(let p=Math.max(1,page-2); p<=Math.min(totalPages,page+2); p++) { %>
              <a href="<%= qWith({page:p}) %>" class="pb <%= p===page?'on':'' %>"><%= p %></a>
            <% } %>
            <a href="<%= qWith({page: page+1}) %>" class="pb <%= page>=totalPages ? 'dis' : '' %>">
              <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
            </a>
          </div>
        </div>
        <% } %>

      </div><!-- fin .t-col -->

      <!-- Panel lateral desktop -->
      <div class="p-col" id="leadPanel">
        <div style="padding:40px 20px;text-align:center;">
          <div style="font-size:11px;color:#94a3b8;line-height:1.6;">Selecciona un lead<br>para ver acciones</div>
        </div>
      </div>

    </div><!-- fin .shell -->
```

También remover el bloque `<script>function toggleLeadFav...</script>` (líneas 1419–1436 en el original) — ya no se necesita, el JS está en `crm-leads-bandeja.js`.

- [ ] **Step 2: Agregar theme-toggle button justo antes del `.shell`**

Insertar antes de `<div class="shell">`:
```ejs
        <!-- Toggle de tema -->
        <button class="theme-toggle" id="themeToggle" onclick="toggleTheme()" title="Cambiar tema">
          <div class="theme-toggle-icon" id="themeIcon">
            <svg id="iconSun" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
            <svg id="iconMoon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2.5" style="display:none;"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
          </div>
          <span class="theme-toggle-label" id="themeLabel">Tema claro</span>
          <div class="theme-pill" id="themePill"></div>
        </button>

        <!-- Toast area -->
        <div class="toast-area" id="toastArea"></div>
```

- [ ] **Step 3: Verificar que el EJS renderiza sin error**

```bash
node -e "const ejs = require('ejs'); const fs = require('fs'); ejs.renderFile('views/advisor/crm/leads/index.ejs', {result:{items:[]},stats:{total:0,nuevos:0,seguimiento:0,cierres:0,finalizados:0,traspasos:0,pipeline:0,followups:0,appointments:0},kpis:{},filters:{estado:'all',orden:'desc',orden_campo:'sin_contacto',orden_dir:'asc'},portales:[],idsFavoritos:[],idsFijados:[],page:1,totalPages:1,totalItems:0,user:{id:1,nombre:'Test',apellidos:'',role:'advisor'},viewMode:'advisor'}, {}, (err, html) => { if(err) console.error(err.message); else console.log('OK ' + html.length + ' chars'); });"
```
Expected: `OK NNNNN chars` (sin error)

- [ ] **Step 4: Verificar en browser**

Arrancar el servidor (`node src/app.js` o equivalente), abrir `/advisor/leads` y verificar:
1. La tabla muestra 9 columnas con encabezados ordenables
2. Clic en fila → panel derecho se puebla con nombre, contacto, tabs Acciones/Historial/Perfil
3. Botón ★ → toast "Guardado en favoritos" / "Quitado de favoritos"
4. Botón 📍 → toast "Lead fijado" / "Lead desfijado"
5. Toggle sol/luna → body.dark se agrega, colores cambian, preferencia persiste al recargar
6. KPI row muestra los totales reales (no los 20 items de la página)
7. Chips Favoritos y Fijados muestran el conteo correcto y filtran al hacer clic
8. Paginación aparece si hay más de 20 leads y navega correctamente

---

## Self-Review

**Spec coverage:**

| Sección spec | Task que lo implementa |
|---|---|
| §2 — Solo new/followup/won/lost visibles | Task 8 (`if (_state==='transfer_out'…) return`) |
| §3 — Layout .shell desktop | Task 6+8 (.shell/.t-col/.p-col) |
| §4 — 9 columnas en orden correcto | Task 8 (thead + tbody) |
| §4.1 — Producto desde actividad | Task 1 (LATERAL prod_lat ya en Plan 1) |
| §5 — Badges tipo Propio/Mktg/Escalado | Task 5 (`tipoBadge`) + Task 8 (`.tipo.*`) |
| §6 — Leyenda semáforo 2 filas | Task 6 (.legend-bar) |
| §7 — Búsqueda por ID (#421) | Implementado en Plan 1 (servicio) |
| §7 — Chips Favoritos y Fijados | Task 7 (.chip-row `fav`/`pin`) |
| §8 — Ordenamiento por columna | Task 7 (hidden inputs) + Task 8 (th → sortLink) |
| §9 — Paginación 20/página | Task 8 (.pag + controles) |
| §10 — Toggle favorito con toast | Task 3 (JS) |
| §11 — Toggle fijado con toast + pinned first | Task 3 (JS) + CSS `.pinned` |
| §12 — Tema claro/oscuro + localStorage | Task 3 (JS) + Task 4 (anti-flash) + Task 8 (button) |

**Placeholder scan:** Ningún "TBD" o "TODO" encontrado.

**Type consistency:** `scInfo`, `tipoBadge`, `prodBadge`, `lcIconSVG`, `lcInfo` definidos en Task 5 y usados en Task 8. `qWith` definido en Task 7 y usado en Task 8 (están en el mismo bloque EJS — Task 7 va antes de Task 8 en el archivo). `sortLink`/`sortArrow` definidos dentro del `<thead>` en Task 8. `populatePanel`/`toggleFav`/`togglePin` definidos en Task 3 y usados vía delegación de eventos.

---

**Plan completo y guardado.** Dos opciones de ejecución:

**1. Subagent-Driven (recomendado)** — un subagente fresco por task, revisión spec + calidad entre tasks

**2. Inline Execution** — ejecución en esta sesión con checkpoints de revisión

**¿Cuál prefieres?**
