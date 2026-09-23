# Supervisión del Asesor — Rediseño UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rediseñar `views/manager/advisors/show.ejs` para mejorar la UI/UX: eliminar botón Ver leads, workspace profesional con tarjetas de módulo, datetime picker con hora CDMX, 10 KPI cards (2×5) con % a 1 decimal, y embudo de conversión con trapezoides (igual que el advisor dashboard).

**Architecture:** Cambios principalmente en la vista EJS (`views/manager/advisors/show.ejs`) + actualización menor al `parseRange()` en `src/routes/manager.routes.js`. Sin cambios de base de datos ni nuevas rutas.

**Tech Stack:** EJS (server-side rendering), CSS inline + bloque `<style>`, Node.js/Express v5, Chart.js 4.4.1 (gráficas sin cambios)

---

## Mapa de archivos

| Archivo | Cambio |
|---|---|
| `views/manager/advisors/show.ejs` | Eliminar botón, rediseñar workspace, datetime picker, 10 KPI cards, embudo trapezoidal |
| `src/routes/manager.routes.js` | `parseRange()` caso `custom`: soportar datetime-local strings (con hora) |

---

### Task 1: Eliminar "Ver leads" del topbar + corregir pct() a 1 decimal

**Files:**
- Modify: `views/manager/advisors/show.ejs:49` — helper pct()
- Modify: `views/manager/advisors/show.ejs:67-70` — actions array en shell_start

- [ ] **Step 1: Cambiar pct() a 1 decimal**

En `views/manager/advisors/show.ejs`, línea 49, cambiar:
```javascript
  const pct = (n) => _total > 0 ? Math.round(((n || 0) / _total) * 100) : 0;
```
Por:
```javascript
  const pct = (n) => parseFloat(((n || 0) / (_total || 1) * 100).toFixed(1));
```

- [ ] **Step 2: Eliminar botón Ver leads del topbar**

En `views/manager/advisors/show.ejs`, líneas 67-70, cambiar:
```javascript
  actions: [
    { label: 'Volver', href: '/manager/advisors', primary: false },
    { label: 'Ver leads', href: `/manager/advisors/${advisor.id}/leads`, primary: true }
  ]
```
Por:
```javascript
  actions: [
    { label: 'Volver', href: '/manager/advisors', primary: false }
  ]
```

- [ ] **Step 3: Verificar en el servidor**

Navegar a `/manager/advisors/:id` y confirmar:
- El topbar solo muestra el botón "Volver" (no hay "Ver leads")
- Los porcentajes en KPI cards existentes muestran 1 decimal (ej: "12.3%")

- [ ] **Step 4: Commit**

```bash
git add views/manager/advisors/show.ejs
git commit -m "feat: remove Ver leads button + 1-decimal pct helper in advisor supervision"
```

---

### Task 2: Rediseñar sección Workspace con tarjetas de módulo

**Files:**
- Modify: `views/manager/advisors/show.ejs:73-124` — agregar CSS .ws-* al bloque `<style>`
- Modify: `views/manager/advisors/show.ejs:126-143` — reemplazar HTML del workspace

- [ ] **Step 1: Agregar CSS del workspace al bloque `<style>`**

En el bloque `<style>`, insertar justo antes de la primera regla `@media` (antes de `@media (max-width: 1100px)`):

```css
  .ws-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:4px;}
  .ws-module{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;padding:16px 12px;border:1px solid var(--line);border-radius:16px;background:#fff;text-decoration:none;color:inherit;transition:border-color .15s,box-shadow .15s,transform .12s;}
  .ws-module:hover{border-color:#0d9488;box-shadow:0 2px 16px rgba(13,148,136,.13);transform:translateY(-1px);}
  .ws-icon{width:40px;height:40px;border-radius:12px;display:flex;align-items:center;justify-content:center;flex-shrink:0;}
  .ws-label{font-size:12px;font-weight:700;text-align:center;}
  .ws-desc{font-size:11px;color:var(--muted);text-align:center;margin-top:-4px;}
  @media (max-width:760px){.ws-grid{grid-template-columns:repeat(2,1fr);}}
```

- [ ] **Step 2: Reemplazar HTML del workspace (líneas 126-143)**

Cambiar el bloque completo (desde `<!-- Workspace` hasta `</div>` de cierre del cardx, líneas 126-143) por:

```html
<!-- Workspace — módulos de supervisión -->
<div class="cardx pad" style="margin-bottom:14px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;">
    <div class="iconBox" style="background:rgba(13,148,136,.12);">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0d9488" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
    </div>
    <div>
      <h3 class="panelTitle">Módulos del asesor</h3>
      <div class="sub">Vista de supervisión — solo lectura</div>
    </div>
  </div>
  <div class="ws-grid">
    <a class="ws-module" href="/manager/advisors/<%= advisor.id %>/activity">
      <div class="ws-icon" style="background:rgba(99,102,241,.12);">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2"><path d="M3 12h4l2-7 4 14 2-7h4"/></svg>
      </div>
      <span class="ws-label" style="color:#6366f1;">Actividad</span>
      <span class="ws-desc">Registro de contactos</span>
    </a>
    <a class="ws-module" href="/manager/advisors/<%= advisor.id %>/calendar">
      <div class="ws-icon" style="background:rgba(13,148,136,.12);">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0d9488" stroke-width="2"><path d="M7 2v3m10-3v3M3 9h18"/><path d="M5 5h14a2 2 0 0 1 2 2v14H3V7a2 2 0 0 1 2-2Z"/></svg>
      </div>
      <span class="ws-label" style="color:#0d9488;">Calendario</span>
      <span class="ws-desc">Citas programadas</span>
    </a>
    <a class="ws-module" href="/manager/advisors/<%= advisor.id %>/transfers">
      <div class="ws-icon" style="background:rgba(249,115,22,.12);">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f97316" stroke-width="2"><path d="M7 7h14v6"/><path d="M17 3l4 4-4 4"/><path d="M17 17H3v-6"/><path d="M7 21l-4-4 4-4"/></svg>
      </div>
      <span class="ws-label" style="color:#f97316;">Transferencias</span>
      <span class="ws-desc">Historial de traspasos</span>
    </a>
    <a class="ws-module" href="/manager/advisors/<%= advisor.id %>/leads">
      <div class="ws-icon" style="background:rgba(139,92,246,.12);">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
      </div>
      <span class="ws-label" style="color:#8b5cf6;">Bandeja de leads</span>
      <span class="ws-desc">Todos sus leads</span>
    </a>
  </div>
</div>
```

- [ ] **Step 3: Verificar workspace**

Navegar a `/manager/advisors/:id` y confirmar:
- 4 tarjetas en cuadrícula (4×1 en desktop, 2×2 en móvil < 760px)
- Cada tarjeta: icono de color, label en color, descripción en gris
- Hover muestra borde teal con sombra y leve elevación
- Los 4 links llevan a sus rutas correctas

- [ ] **Step 4: Commit**

```bash
git add views/manager/advisors/show.ejs
git commit -m "feat: professional workspace module cards in advisor supervision"
```

---

### Task 3: Datetime picker CDMX para Personalizado (vista)

**Files:**
- Modify: `views/manager/advisors/show.ejs:73-124` — agregar CSS `.hidden`
- Modify: `views/manager/advisors/show.ejs:157-169` — reemplazar `<details>` con div+toggle
- Modify: `views/manager/advisors/show.ejs` (antes de shell_end) — JS click-outside

- [ ] **Step 1: Agregar CSS `.hidden` al bloque `<style>` (antes de `</style>`)**

Al final del bloque `<style>` (antes de `</style>`), añadir:
```css
  .hidden{display:none !important;}
```

- [ ] **Step 2: Reemplazar el `<details>` de Personalizado**

En el archivo, cambiar exactamente el bloque:
```html
    <details style="position:relative;display:inline-block;">
      <summary class="btn <%= curPeriod==='custom' ? 'btn-primary' : '' %>" style="list-style:none;cursor:pointer;">Personalizado ▾</summary>
      <form method="GET" action="/manager/advisors/<%= advisor.id %>"
            style="position:absolute;top:calc(100% + 6px);right:0;z-index:50;background:#0b1220;border:1px solid rgba(255,255,255,.14);border-radius:12px;padding:14px;display:flex;flex-direction:column;gap:8px;min-width:200px;box-shadow:0 8px 32px rgba(0,0,0,.5);">
        <input type="hidden" name="period" value="custom">
        <label style="font-size:12px;color:rgba(226,232,240,.6);">Desde</label>
        <input type="date" name="from" value="<%= from %>" style="background:#0f1a2e;border:1px solid rgba(255,255,255,.15);border-radius:8px;padding:6px 10px;color:#e2e8f0;font-size:13px;">
        <label style="font-size:12px;color:rgba(226,232,240,.6);">Hasta</label>
        <input type="date" name="to" value="<%= to %>" style="background:#0f1a2e;border:1px solid rgba(255,255,255,.15);border-radius:8px;padding:6px 10px;color:#e2e8f0;font-size:13px;">
        <button type="submit" class="btn btn-primary" style="margin-top:4px;">Aplicar</button>
      </form>
    </details>
```

Por:
```html
    <div style="position:relative;">
      <button type="button" id="customToggle" class="btn <%= curPeriod==='custom' ? 'btn-primary' : '' %>" onclick="(function(){var p=document.getElementById('customPanel');p.classList.toggle('hidden');})()">Personalizado ▾</button>
      <div id="customPanel" class="<%= curPeriod==='custom' ? '' : 'hidden' %>" style="position:absolute;top:calc(100% + 6px);right:0;z-index:50;background:#0b1220;border:1px solid rgba(255,255,255,.14);border-radius:12px;padding:16px;min-width:270px;box-shadow:0 8px 32px rgba(0,0,0,.5);">
        <form method="GET" action="/manager/advisors/<%= advisor.id %>" style="display:flex;flex-direction:column;gap:10px;">
          <input type="hidden" name="period" value="custom">
          <label style="font-size:12px;color:rgba(226,232,240,.6);">Desde (Hora CDMX)</label>
          <input type="datetime-local" name="from" value="<%= from %>" style="background:#0f1a2e;border:1px solid rgba(255,255,255,.15);border-radius:8px;padding:7px 10px;color:#e2e8f0;font-size:13px;color-scheme:dark;">
          <label style="font-size:12px;color:rgba(226,232,240,.6);">Hasta (Hora CDMX)</label>
          <input type="datetime-local" name="to" value="<%= to %>" style="background:#0f1a2e;border:1px solid rgba(255,255,255,.15);border-radius:8px;padding:7px 10px;color:#e2e8f0;font-size:13px;color-scheme:dark;">
          <button type="submit" class="btn btn-primary" style="margin-top:4px;">Aplicar</button>
        </form>
      </div>
    </div>
```

- [ ] **Step 3: Agregar JS click-outside (justo antes de `<%- include('../partials/shell_end') %>`)**

Insertar antes de la línea `<%- include('../partials/shell_end') %>` al final del archivo:

```html
<script>
  // Cierra el panel Personalizado al hacer click fuera
  document.addEventListener('click', function(e) {
    var panel = document.getElementById('customPanel');
    var toggle = document.getElementById('customToggle');
    if (!panel || panel.classList.contains('hidden')) return;
    if (!panel.contains(e.target) && e.target !== toggle) {
      panel.classList.add('hidden');
    }
  });
</script>
```

- [ ] **Step 4: Verificar datetime picker**

Navegar a `/manager/advisors/:id` y confirmar:
- El botón "Personalizado ▾" abre/cierra un panel flotante oscuro
- El panel tiene 2 campos `datetime-local` con labels "(Hora CDMX)"
- El campo acepta entrada de fecha y hora (ej: 2026-05-01T09:00)
- Al hacer click fuera del panel, se cierra
- Al presionar "Aplicar", recarga la página con `?period=custom&from=...&to=...`
- Si `curPeriod === 'custom'`, el panel aparece abierto al cargar

- [ ] **Step 5: Commit**

```bash
git add views/manager/advisors/show.ejs
git commit -m "feat: datetime-local picker with CDMX label for custom period in advisor supervision"
```

---

### Task 4: Actualizar parseRange para datetime-local (backend)

**Files:**
- Modify: `src/routes/manager.routes.js:66-69` — caso `custom` en parseRange

- [ ] **Step 1: Actualizar caso 'custom' en parseRange**

En `src/routes/manager.routes.js`, cambiar exactamente:
```javascript
    case 'custom':
      rangeFrom = from ? new Date(from + 'T00:00:00') : new Date(now.getTime() - 7*24*60*60*1000);
      rangeTo   = to   ? new Date(to   + 'T23:59:59') : now;
      days = Math.ceil((rangeTo - rangeFrom) / 86400000) || 7;
      break;
```
Por:
```javascript
    case 'custom': {
      // Soporta date-only "YYYY-MM-DD" y datetime-local "YYYY-MM-DDTHH:MM"
      // Interpreta siempre como hora CDMX (UTC-6, suficiente para rangos diarios)
      const toCDMX = (s, endOfDay) => {
        if (!s) return null;
        const base = s.includes('T') ? s + ':00' : s + (endOfDay ? 'T23:59:59' : 'T00:00:00');
        return new Date(base + '-06:00');
      };
      rangeFrom = toCDMX(from, false) || new Date(now.getTime() - 7*24*60*60*1000);
      rangeTo   = toCDMX(to,   true)  || now;
      days = Math.ceil((rangeTo - rangeFrom) / 86400000) || 7;
      break;
    }
```

- [ ] **Step 2: Verificar parseRange**

Probar en el servidor con `?period=custom&from=2026-05-01T09:00&to=2026-05-27T18:00`:
- La página `/manager/advisors/:id` carga sin errores 500
- Las gráficas de tendencia muestran el rango correcto (aprox. 26 días)
- Probar también con solo fecha (`?period=custom&from=2026-05-01&to=2026-05-27`) — sigue funcionando

- [ ] **Step 3: Commit**

```bash
git add src/routes/manager.routes.js
git commit -m "fix: parseRange custom case handles datetime-local strings with CDMX offset"
```

---

### Task 5: Rediseñar KPI cards — 10 tarjetas en 2 filas de 5

**Files:**
- Modify: `views/manager/advisors/show.ejs:73-124` — agregar CSS `.kpiGrid5`, `.kpiCard5`
- Modify: `views/manager/advisors/show.ejs:265-447` — reemplazar 3 filas de 4 por 2 filas de 5

- [ ] **Step 1: Agregar CSS kpiGrid5 y kpiCard5 al bloque `<style>`**

Después de la regla `.kpiCard[data-tone="slate"] .iconBox{...}`, insertar:

```css
  .kpiGrid5{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;}
  .kpiCard5{padding:14px;border:1px solid var(--line);border-radius:18px;background:#fff;box-shadow:var(--shadow);}
  .kpiCard5 .row{display:flex;justify-content:space-between;gap:8px;}
  .kpiCard5 .label{color:var(--muted);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.03em;}
  .kpiCard5 .value{font-weight:950;font-size:22px;margin-top:6px;line-height:1;}
  .kpiCard5 .pct-line{font-size:11px;color:rgba(226,232,240,.45);margin-top:3px;}
  .kpiCard5 .hint{color:var(--muted);font-size:11px;margin-top:6px;}
  .kpiCard5[data-tone="teal"]   .iconBox{background:rgba(0,204,204,.12);}
  .kpiCard5[data-tone="green"]  .iconBox{background:rgba(34,197,94,.12);}
  .kpiCard5[data-tone="red"]    .iconBox{background:rgba(239,68,68,.12);}
  .kpiCard5[data-tone="purple"] .iconBox{background:rgba(168,85,247,.12);}
  .kpiCard5[data-tone="orange"] .iconBox{background:rgba(249,115,22,.12);}
  .kpiCard5[data-tone="slate"]  .iconBox{background:rgba(100,116,139,.12);}
  @media (max-width:1200px){.kpiGrid5{grid-template-columns:repeat(3,1fr);}}
  @media (max-width:760px){.kpiGrid5{grid-template-columns:repeat(2,1fr);}}
  @media (max-width:480px){.kpiGrid5{grid-template-columns:1fr;}}
```

- [ ] **Step 2: Reemplazar el bloque de KPIs en `.main` (desde el comentario `<!-- KPIs + Charts + Workspace -->` hasta antes de los `<!-- Charts -->`)**

Reemplazar desde `<!-- KPIs + Charts + Workspace -->` `<div class="main">` hasta (sin incluir) `<div style="height:12px;"></div>` + `<!-- Charts -->` por el siguiente bloque. Es decir, reemplazar las 3 filas de `<div class="grid12">` con kpiCards y sus spacers:

Reemplazar exactamente:
```html
  <!-- KPIs + Charts + Workspace -->
  <div class="main">
    <!-- KPIs — fila 1: Pipeline -->
    <div class="grid12">
```
(y todo lo que sigue hasta `<div style="height:12px;"></div>` antes de `<!-- Charts -->`)

Por:
```html
  <!-- KPIs + Charts -->
  <div class="main">
    <!-- KPIs fila 1: Total, Nuevos, Seguimiento, Actividades, Estancados -->
    <div class="kpiGrid5">

      <div class="kpiCard5" data-tone="blue">
        <div class="row">
          <div>
            <div class="label">Total leads</div>
            <div class="value"><%= s.leads_total ?? 0 %></div>
            <div class="hint">Base total del asesor</div>
          </div>
          <div class="iconBox" title="Total" style="flex-shrink:0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M4 4h16v10a4 4 0 0 1-4 4h-3l-1 2h-2l-1-2H8a4 4 0 0 1-4-4V4Z" stroke="currentColor" stroke-width="2"/></svg>
          </div>
        </div>
      </div>

      <div class="kpiCard5" data-tone="slate">
        <div class="row">
          <div>
            <div class="label">Nuevos</div>
            <div class="value"><%= s.leads_nuevos ?? 0 %></div>
            <div class="pct-line"><%= pct(s.leads_nuevos) %>% del total</div>
            <div class="hint">Sin contacto previo</div>
          </div>
          <div class="iconBox" title="Nuevos" style="flex-shrink:0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M12 22c5.5 0 10-4.5 10-10S17.5 2 12 2 2 6.5 2 12s4.5 10 10 10Z" stroke="currentColor" stroke-width="2"/><path d="M12 8v4" stroke="currentColor" stroke-width="2"/><path d="M12 16h.01" stroke="currentColor" stroke-width="2"/></svg>
          </div>
        </div>
      </div>

      <div class="kpiCard5" data-tone="teal">
        <div class="row">
          <div>
            <div class="label">En seguimiento</div>
            <div class="value"><%= s.leads_seguimiento ?? 0 %></div>
            <div class="pct-line"><%= pct(s.leads_seguimiento) %>% del total</div>
            <div class="hint">Activos con actividad</div>
          </div>
          <div class="iconBox" title="Seguimiento" style="flex-shrink:0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M12 2v3m0 14v3M2 12h3m14 0h3" stroke="currentColor" stroke-width="2"/><path d="M12 7a5 5 0 1 0 5 5" stroke="currentColor" stroke-width="2"/></svg>
          </div>
        </div>
      </div>

      <div class="kpiCard5" data-tone="slate">
        <div class="row">
          <div>
            <div class="label">Actividades</div>
            <div class="value"><%= s.actividades_total ?? 0 %></div>
            <div class="pct-line" style="color:#0f766e;font-weight:600;"><%= s.leads_total > 0 ? (s.actividades_total / s.leads_total).toFixed(1) : '0.0' %> por lead</div>
            <div class="hint">Total de interacciones</div>
          </div>
          <div class="iconBox" title="Actividades" style="flex-shrink:0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M3 12h4l2-7 4 14 2-7h4" stroke="currentColor" stroke-width="2"/></svg>
          </div>
        </div>
      </div>

      <div class="kpiCard5" data-tone="red">
        <div class="row">
          <div>
            <div class="label">Estancados</div>
            <div class="value"><%= s.estancados ?? 0 %></div>
            <div class="pct-line"><%= pct(s.estancados) %>% del total</div>
            <div class="hint">Sin actividad +1 día</div>
          </div>
          <div class="iconBox" title="Estancados" style="flex-shrink:0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M12 9v4" stroke="currentColor" stroke-width="2"/><path d="M12 17h.01" stroke="currentColor" stroke-width="2"/><path d="M10.3 4.2 2.6 18a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0Z" stroke="currentColor" stroke-width="2"/></svg>
          </div>
        </div>
      </div>

    </div>

    <div style="height:10px;"></div>

    <!-- KPIs fila 2: Citas agend., Citas atend., Cierre firma, Firma+pago, Finalizados -->
    <div class="kpiGrid5">

      <div class="kpiCard5" data-tone="purple">
        <div class="row">
          <div>
            <div class="label">Citas agendadas</div>
            <div class="value"><%= s.citas_agendadas ?? 0 %></div>
            <div class="pct-line"><%= pct(s.citas_agendadas) %>% del total</div>
            <div class="hint">Reuniones programadas</div>
          </div>
          <div class="iconBox" title="Citas agendadas" style="flex-shrink:0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M7 2v3m10-3v3M3 9h18" stroke="currentColor" stroke-width="2"/><path d="M5 5h14a2 2 0 0 1 2 2v14H3V7a2 2 0 0 1 2-2Z" stroke="currentColor" stroke-width="2"/></svg>
          </div>
        </div>
      </div>

      <div class="kpiCard5" data-tone="purple">
        <div class="row">
          <div>
            <div class="label">Citas atendidas</div>
            <div class="value"><%= s.citas_atendidas ?? 0 %></div>
            <div class="pct-line"><%= pct(s.citas_atendidas) %>% del total</div>
            <div class="hint">Asistidas por cliente</div>
          </div>
          <div class="iconBox" title="Citas atendidas" style="flex-shrink:0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M7 2v3m10-3v3M3 9h18" stroke="currentColor" stroke-width="2"/><path d="M5 5h14a2 2 0 0 1 2 2v14H3V7a2 2 0 0 1 2-2Z" stroke="currentColor" stroke-width="2"/><path d="M9 14l2 2 4-4" stroke="currentColor" stroke-width="2"/></svg>
          </div>
        </div>
      </div>

      <div class="kpiCard5" data-tone="green">
        <div class="row">
          <div>
            <div class="label">Cierre con firma</div>
            <div class="value"><%= s.cierre_firma ?? 0 %></div>
            <div class="pct-line"><%= pct(s.cierre_firma) %>% del total</div>
            <div class="hint">Firmó, pendiente pago</div>
          </div>
          <div class="iconBox" title="Cierre firma" style="flex-shrink:0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" stroke="currentColor" stroke-width="2"/><path d="M9 13l2 2 4-4" stroke="currentColor" stroke-width="2"/></svg>
          </div>
        </div>
      </div>

      <div class="kpiCard5" data-tone="green">
        <div class="row">
          <div>
            <div class="label">Firma + pago</div>
            <div class="value"><%= s.cierre_firma_pago ?? 0 %></div>
            <div class="pct-line"><%= pct(s.cierre_firma_pago) %>% del total</div>
            <div class="hint">Conv. pagada: <strong><%= convPaid %>%</strong></div>
          </div>
          <div class="iconBox" title="Cierre pagado" style="flex-shrink:0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M12 1v22" stroke="currentColor" stroke-width="2"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7H14a3.5 3.5 0 0 1 0 7H6" stroke="currentColor" stroke-width="2"/></svg>
          </div>
        </div>
      </div>

      <div class="kpiCard5" data-tone="slate">
        <div class="row">
          <div>
            <div class="label">Sin venta</div>
            <div class="value"><%= s.finalizados_sin_venta ?? 0 %></div>
            <div class="pct-line"><%= pct(s.finalizados_sin_venta) %>% del total</div>
            <div class="hint">Conv. cierre: <strong><%= convClose %>%</strong></div>
          </div>
          <div class="iconBox" title="Finalizados" style="flex-shrink:0;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M20 6 9 17l-5-5" stroke="currentColor" stroke-width="2"/></svg>
          </div>
        </div>
      </div>

    </div>

    <div style="height:12px;"></div>
```

- [ ] **Step 3: Verificar KPI cards**

Navegar a `/manager/advisors/:id` y confirmar:
- Se muestran exactamente 10 KPI cards en 2 filas de 5
- Fila 1: Total leads, Nuevos, En seguimiento, Actividades, Estancados
- Fila 2: Citas agendadas, Citas atendidas, Cierre con firma, Firma+pago, Sin venta
- Cada card (excepto Total leads y Actividades) muestra porcentaje con 1 decimal
- Actividades muestra "X.X por lead" en verde en lugar de %
- Total leads muestra solo el valor y el hint
- Responsive: 3 columnas en < 1200px, 2 columnas en < 760px, 1 columna en < 480px

- [ ] **Step 4: Commit**

```bash
git add views/manager/advisors/show.ejs
git commit -m "feat: redesign KPI cards — 10 cards (2x5) with 1-decimal pct in advisor supervision"
```

---

### Task 6: Reemplazar embudo de barras con embudo de trapezoides

**Files:**
- Modify: `views/manager/advisors/show.ejs:237-262` — reemplazar embudo progress-bar

- [ ] **Step 1: Reemplazar la sección del embudo (líneas 237-262)**

Cambiar exactamente el bloque:
```html
    <!-- Embudo de conversión -->
    <div style="margin-top:14px;border-top:1px solid var(--line);padding-top:14px;">
      <h3 class="panelTitle">Embudo de conversión</h3>
      <div class="sub">Del total de leads a cierre con pago</div>
      <%
        const funnelSteps = [
          { label: 'Total leads',      val: s.leads_total        || 0, color: '#ef4444', barPct: 100 },
          { label: 'Citas agendadas',  val: s.citas_agendadas    || 0, color: '#f97316', barPct: pct(s.citas_agendadas) },
          { label: 'Citas atendidas',  val: s.citas_atendidas    || 0, color: '#eab308', barPct: pct(s.citas_atendidas) },
          { label: 'Cierre con firma', val: s.cierre_firma       || 0, color: '#22c55e', barPct: pct(s.cierre_firma) },
          { label: 'Firma + pago',     val: s.cierre_firma_pago  || 0, color: '#0d9488', barPct: pct(s.cierre_firma_pago) },
        ];
      %>
      <div style="margin-top:12px;display:grid;gap:9px;">
        <% funnelSteps.forEach(step => { %>
          <div>
            <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:3px;">
              <span style="color:var(--muted);font-weight:500;"><%= step.label %></span>
              <span style="font-weight:700;color:#e2e8f0;"><%= step.val %>&nbsp;<span style="color:var(--muted);font-weight:400;"><%= step.barPct %>%</span></span>
            </div>
            <div style="height:7px;border-radius:999px;background:rgba(255,255,255,.07);overflow:hidden;">
              <div style="height:100%;width:<%= step.val > 0 ? Math.max(step.barPct, 4) : 0 %>%;background:<%= step.color %>;border-radius:999px;"></div>
            </div>
          </div>
        <% }) %>
      </div>
    </div>
```

Por:
```html
    <!-- Embudo de conversión — trapezoides -->
    <div style="margin-top:14px;border-top:1px solid var(--line);padding-top:14px;">
      <h3 class="panelTitle">Embudo de conversión</h3>
      <div class="sub">Del total de leads a cierre con pago</div>
      <%
        function _fp(v, p) { return p > 0 ? parseFloat((v / p * 100).toFixed(1)) : 0.0; }
        const _tf  = s.leads_total       || 0;
        const _caf = s.citas_agendadas   || 0;
        const _ctf = s.citas_atendidas   || 0;
        const _cff = s.cierre_firma      || 0;
        const _cfp = s.cierre_firma_pago || 0;
        const funnelSteps = [
          { icon:'👥', label:'Total leads',      sub:'Base de cartera',       val:_tf,  pct:'100.0%',               bandClr:'#ef4444', iconBg:'rgba(239,68,68,.18)',   txtClr:'#ef4444', clip:'polygon(0% 0%, 100% 0%, 93% 100%, 7% 100%)' },
          { icon:'🗓️', label:'Citas agendadas',  sub:'Del total de leads',    val:_caf, pct:_fp(_caf,_tf)+'%',      bandClr:'#f97316', iconBg:'rgba(249,115,22,.18)',  txtClr:'#f97316', clip:'polygon(7% 0%, 93% 0%, 86% 100%, 14% 100%)' },
          { icon:'✅', label:'Citas atendidas',  sub:'De citas agendadas',    val:_ctf, pct:_fp(_ctf,_caf)+'%',     bandClr:'#3b82f6', iconBg:'rgba(59,130,246,.18)',  txtClr:'#3b82f6', clip:'polygon(14% 0%, 86% 0%, 79% 100%, 21% 100%)' },
          { icon:'✍️', label:'Cierre con firma', sub:'De citas atendidas',    val:_cff, pct:_fp(_cff,_ctf)+'%',     bandClr:'#10b981', iconBg:'rgba(16,185,129,.18)', txtClr:'#10b981', clip:'polygon(21% 0%, 79% 0%, 72% 100%, 28% 100%)' },
          { icon:'💰', label:'Firma y pago',     sub:'De cierres con firma',  val:_cfp, pct:_fp(_cfp,_cff)+'%',     bandClr:'#8b5cf6', iconBg:'rgba(139,92,246,.18)', txtClr:'#8b5cf6', clip:'polygon(28% 0%, 72% 0%, 65% 100%, 35% 100%)' },
        ];
      %>
      <div style="margin-top:12px;display:flex;align-items:flex-start;gap:0;">
        <div style="flex:0 0 44%;min-width:0;">
          <% funnelSteps.forEach(function(fs) { %>
          <div style="height:50px;position:relative;">
            <div style="position:absolute;inset:0;background:<%= fs.bandClr %>;clip-path:<%= fs.clip %>;"></div>
            <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;z-index:1;">
              <span style="font-size:12px;font-weight:700;color:#fff;text-shadow:0 1px 3px rgba(0,0,0,.45);letter-spacing:-.01em;"><%= fs.pct %></span>
            </div>
          </div>
          <% }); %>
        </div>
        <div style="flex:1;min-width:0;padding-left:10px;">
          <% funnelSteps.forEach(function(fs) { %>
          <div style="height:50px;display:flex;align-items:center;gap:6px;">
            <div style="width:30px;height:30px;border-radius:50%;background:<%= fs.iconBg %>;border:1px solid rgba(255,255,255,.1);display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0;"><%= fs.icon %></div>
            <div style="flex:1;min-width:0;">
              <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:<%= fs.txtClr %>;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"><%= fs.label %></div>
              <div style="font-size:9px;color:rgba(226,232,240,.45);margin-top:1px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"><%= fs.sub %></div>
            </div>
            <div style="font-size:17px;font-weight:700;color:<%= fs.bandClr %>;font-variant-numeric:tabular-nums;flex-shrink:0;"><%= fs.val %></div>
          </div>
          <% }); %>
        </div>
      </div>
    </div>
```

- [ ] **Step 2: Verificar el embudo**

Navegar a `/manager/advisors/:id` y confirmar:
- El panel izquierdo muestra 5 etapas en forma de trapezoides decrecientes
- Colores: rojo → naranja → azul → verde → violeta
- Los porcentajes muestran 1 decimal (ej: "12.5%")
- El % de cada etapa es relativo al paso anterior (no al total):
  - "100.0%" en Total leads
  - "X.X%" en Citas agendadas = citas_agendadas / leads_total
  - "X.X%" en Citas atendidas = citas_atendidas / citas_agendadas
  - "X.X%" en Cierre con firma = cierre_firma / citas_atendidas
  - "X.X%" en Firma y pago = cierre_firma_pago / cierre_firma
- Los valores numéricos aparecen a la derecha de cada etapa

- [ ] **Step 3: Commit final**

```bash
git add views/manager/advisors/show.ejs
git commit -m "feat: trapezoid conversion funnel with 1-decimal pct in advisor supervision"
```

---

## Self-Review

**1. Cobertura del spec:**
- ✅ Eliminar botón Ver leads → Task 1
- ✅ Workspace profesional con módulos → Task 2
- ✅ Personalizado con datetime y hora CDMX → Task 3 + Task 4
- ✅ 10 KPI cards con % a 1 decimal → Task 5
- ✅ Embudo trapezoidal en panel izquierdo con 1 decimal → Task 6
- ✅ Secciones leads+actividad, pipeline, citas por día, cierres por día sin cambios

**2. Scan de placeholders:** Ningún TBD ni TODO en el plan.

**3. Consistencia de tipos:**
- `pct()` modificado en Task 1, usado en Tasks 5 y 6
- `_fp()` definida dentro del bloque EJS en Task 6 (no hay conflicto con `pct()`)
- `funnelSteps` en Task 6 reemplaza `funnelSteps` (progress-bar) que se elimina — mismo nombre, sin conflicto
- `kpiCard5` en CSS Task 5 y HTML Task 5 son consistentes
- `ws-module`, `ws-grid`, `ws-icon`, `ws-label`, `ws-desc` definidas en CSS Task 2 y usadas en HTML Task 2

**4. Gaps detectados:** Ninguno.
