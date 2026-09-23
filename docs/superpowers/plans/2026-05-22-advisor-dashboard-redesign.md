# Advisor Dashboard Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rediseñar el dashboard del advisor con 12 KPIs en 2 filas (con emoji + valor + % del total), layout blanco, cards con bordes redondeados, y nuevas métricas de citas y cierres desde el backend.

**Architecture:** Se agrega una función `getAdvisorDashboardMetrics` al servicio que calcula en una sola query SQL las nuevas métricas (transferencias, citas, cierres desglosados). El controller llama las 3 queries en paralelo con `Promise.all`. La vista usa los nuevos datos para mostrar 2 grids de 6 KPI cards.

**Tech Stack:** Node.js v24, Express v5, PostgreSQL, EJS (server-side rendering), Tailwind CDN (clases utilitarias), CSS inline

---

## File Map

| Archivo | Cambio |
|---|---|
| `src/services/advisor/crm.service.js` | Agregar función `getAdvisorDashboardMetrics` + exportarla |
| `src/controllers/advisor/crm.controller.js` | Actualizar acción `dashboard` para llamar la nueva función en paralelo |
| `views/advisor/crm/dashboard.ejs` | Rediseño completo: CSS, KPI grid, estilos de secciones |

---

## Task 1: Agregar `getAdvisorDashboardMetrics` al servicio

**Files:**
- Modify: `src/services/advisor/crm.service.js`

Esta función hace una sola query SQL con 9 subqueries escalares para obtener todas las métricas nuevas del dashboard.

- [ ] **Step 1: Abrir el archivo y localizar el bloque de exports**

Abre `src/services/advisor/crm.service.js`. Busca la sección con el comentario `// Dashboard` alrededor de la línea 2269:

```javascript
  // Dashboard
  getDashboardKpis,
  getLeadsByDay,
  getPipelineByStatus,
  getDashboardData,
```

También localiza el final de la función `getDashboardData` (alrededor de la línea 1493):
```javascript
  return {
    kpis,
    leadsByDay,
    pipeline,
    leadsByStatus: pipeline,
    leads,
  };
}
```

- [ ] **Step 2: Agregar la función `getAdvisorDashboardMetrics` después de `getDashboardData`**

Inmediatamente después del cierre `}` de `getDashboardData` (línea ~1493), añade:

```javascript
async function getAdvisorDashboardMetrics(advisorId) {
  const id = toId(advisorId);
  const q = `
    SELECT
      (
        SELECT COUNT(*)::int FROM crm_leads
        WHERE transferred_to = $1
      ) AS transferencias_recibidas,
      (
        SELECT COUNT(*)::int FROM crm_leads
        WHERE transferred_by = $1
      ) AS traspasos_realizados,
      (
        SELECT COUNT(*)::int FROM crm_leads
        WHERE advisor_id = $1
          AND COALESCE(status,'open') = 'closed'
          AND NOT COALESCE(sale_paid, false)
          AND NOT COALESCE(sale_signed_only, false)
      ) AS finalizados_sin_venta,
      (
        SELECT COUNT(*)::int FROM crm_leads
        WHERE advisor_id = $1
          AND COALESCE(status,'open') = 'closed'
          AND COALESCE(sale_signed_only, false) = true
      ) AS cierres_firma,
      (
        SELECT COUNT(*)::int FROM crm_leads
        WHERE advisor_id = $1
          AND COALESCE(status,'open') = 'closed'
          AND COALESCE(sale_paid, false) = true
      ) AS cierres_firma_pago,
      (
        SELECT COUNT(*)::int FROM crm_leads
        WHERE advisor_id = $1
          AND COALESCE(status,'open') = 'closed'
          AND (COALESCE(sale_paid, false) OR COALESCE(sale_signed_only, false))
      ) AS total_cierres,
      (
        SELECT COUNT(*)::int FROM crm_activities a
        JOIN crm_leads l ON l.id = a.lead_id
        WHERE l.advisor_id = $1
          AND a.type = 'cita'
          AND (a.scheduled_at AT TIME ZONE 'America/Mexico_City')
              >= DATE_TRUNC('day', ${NOW_CDMX_SQL})
          AND (a.scheduled_at AT TIME ZONE 'America/Mexico_City')
              < DATE_TRUNC('day', ${NOW_CDMX_SQL}) + INTERVAL '1 day'
      ) AS citas_hoy,
      (
        SELECT COUNT(*)::int FROM crm_activities a
        JOIN crm_leads l ON l.id = a.lead_id
        WHERE l.advisor_id = $1
          AND a.type = 'cita'
      ) AS citas_agendadas,
      (
        SELECT COUNT(*)::int FROM crm_activities a
        JOIN crm_leads l ON l.id = a.lead_id
        WHERE l.advisor_id = $1
          AND a.type = 'cita'
          AND a.confirmed_at IS NOT NULL
      ) AS citas_atendidas
  `;
  const { rows } = await pool.query(q, [id]);
  const r = rows[0] || {};
  return {
    transferencias_recibidas: Number(r.transferencias_recibidas || 0),
    traspasos_realizados:     Number(r.traspasos_realizados     || 0),
    finalizados_sin_venta:    Number(r.finalizados_sin_venta    || 0),
    cierres_firma:            Number(r.cierres_firma            || 0),
    cierres_firma_pago:       Number(r.cierres_firma_pago       || 0),
    total_cierres:            Number(r.total_cierres            || 0),
    citas_hoy:                Number(r.citas_hoy               || 0),
    citas_agendadas:          Number(r.citas_agendadas          || 0),
    citas_atendidas:          Number(r.citas_atendidas          || 0),
  };
}
```

- [ ] **Step 3: Exportar la función**

En el bloque de exports, dentro de la sección `// Dashboard` (alrededor de la línea 2272), agrega `getAdvisorDashboardMetrics`:

```javascript
  // Dashboard
  getDashboardKpis,
  getLeadsByDay,
  getPipelineByStatus,
  getDashboardData,
  getAdvisorDashboardMetrics,
```

- [ ] **Step 4: Verificar que el servidor arranca sin errores de sintaxis**

Ejecuta en la terminal (ajusta el comando según tu entorno local):

```bash
node -e "require('./src/services/advisor/crm.service.js'); console.log('OK');"
```

Expected: `OK` (sin stack traces)

- [ ] **Step 5: Commit**

```bash
git add src/services/advisor/crm.service.js
git commit -m "feat: add getAdvisorDashboardMetrics query for new dashboard KPIs"
```

---

## Task 2: Actualizar el controller para pasar las nuevas métricas

**Files:**
- Modify: `src/controllers/advisor/crm.controller.js`

La acción `dashboard` actualmente hace 2 await secuenciales. La cambiamos a `Promise.all` con 3 queries en paralelo para mejor rendimiento, y pasamos `metrics` a la vista.

- [ ] **Step 1: Localizar la acción `dashboard` en el controller**

Abre `src/controllers/advisor/crm.controller.js`. Busca (alrededor de la línea 133):

```javascript
exports.dashboard = async (req, res) => {
  try {
    const advisorId = requireAdvisorId(req);
    if (!advisorId) return res.redirect('/auth/login');

    const data = await crmService.getDashboardData(advisorId);
    const leadsWithState = await crmService.listLeadsByAdvisor(advisorId);

    return res.render('advisor/crm/dashboard', {
      title: 'Dashboard CRM',
      path: '/advisor/crm',
      user: req.session.user,
      ...data,
      leads: Array.isArray(leadsWithState)
        ? leadsWithState
        : (Array.isArray(data?.leads) ? data.leads : []),
    });
  } catch (error) {
    return safeRenderError(res, error, 'Error cargando dashboard');
  }
};
```

- [ ] **Step 2: Reemplazar con la versión paralela que incluye `metrics`**

Reemplaza el bloque `exports.dashboard` completo por:

```javascript
exports.dashboard = async (req, res) => {
  try {
    const advisorId = requireAdvisorId(req);
    if (!advisorId) return res.redirect('/auth/login');

    const [data, leadsWithState, metrics] = await Promise.all([
      crmService.getDashboardData(advisorId),
      crmService.listLeadsByAdvisor(advisorId),
      crmService.getAdvisorDashboardMetrics(advisorId),
    ]);

    return res.render('advisor/crm/dashboard', {
      title: 'Dashboard CRM',
      path: '/advisor/crm',
      user: req.session.user,
      ...data,
      leads: Array.isArray(leadsWithState)
        ? leadsWithState
        : (Array.isArray(data?.leads) ? data.leads : []),
      metrics,
    });
  } catch (error) {
    return safeRenderError(res, error, 'Error cargando dashboard');
  }
};
```

- [ ] **Step 3: Verificar sintaxis**

```bash
node -e "require('./src/controllers/advisor/crm.controller.js'); console.log('OK');"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/controllers/advisor/crm.controller.js
git commit -m "feat: pass dashboard metrics to view in parallel queries"
```

---

## Task 3: Rediseñar `dashboard.ejs` — CSS y KPI grid

**Files:**
- Modify: `views/advisor/crm/dashboard.ejs`

Esta es la tarea más grande. Se reemplaza el bloque `<style>`, se actualizan las variables del scriptblock, y se sustituye la sección de KPI cards (7 tarjetas → 2 filas de 6).

- [ ] **Step 1: Actualizar la variable `citasHoy` en el scriptblock de EJS**

Abre `views/advisor/crm/dashboard.ejs`. Busca la línea (alrededor de la 55):

```javascript
  const citasHoy       = safeNum((typeof kpi !== 'undefined' && kpi?.citas) || (typeof kpis !== 'undefined' && kpis?.appointments) || 0);
```

Reemplázala por:

```javascript
  const citasHoy = safeNum(
    (typeof metrics !== 'undefined' && metrics?.citas_hoy) ||
    (typeof kpi !== 'undefined' && kpi?.citas) ||
    (typeof kpis !== 'undefined' && kpis?.appointments) || 0
  );
```

Esto hace que `citasHoy` tome el valor correcto (citas programadas para HOY) del nuevo `metrics` cuando esté disponible, con fallback al valor anterior.

- [ ] **Step 2: Reemplazar el bloque `<style>` completo**

Busca el bloque que empieza en `<style>` (línea ~88) y termina en `</style>` (línea ~141). Reemplázalo por:

```html
<style>
  @keyframes fadeUp { from{opacity:0;transform:translateY(10px);}to{opacity:1;transform:translateY(0);} }
  @keyframes barIn  { from{width:0 !important;} }
  .dash-wrap *  { box-sizing:border-box; }
  .dash-wrap    { font-family:'DM Sans',system-ui,sans-serif; background:#fff; padding:24px 28px; }
  .d-card       { background:#fff; border:1px solid #f1f5f9; border-radius:16px; box-shadow:0 1px 3px rgba(0,0,0,.05); padding:14px; }
  .kpi-row      { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:16px; margin-bottom:16px; }
  .kpi-card     { padding:20px; transition:all .15s ease; cursor:default; }
  .kpi-card:hover{ box-shadow:0 4px 14px rgba(0,0,0,.09); border-bottom:2px solid #0d9488; }
  .kpi          { animation:fadeUp .35s ease both; }
  .kpi:nth-child(1){animation-delay:.04s} .kpi:nth-child(2){animation-delay:.08s}
  .kpi:nth-child(3){animation-delay:.12s} .kpi:nth-child(4){animation-delay:.16s}
  .kpi:nth-child(5){animation-delay:.20s} .kpi:nth-child(6){animation-delay:.24s}
  .k-lbl  { font-size:9px; letter-spacing:.15em; text-transform:uppercase; font-weight:600; color:#94a3b8; }
  .k-val  { font-size:26px; font-weight:600; line-height:1.1; margin:4px 0 2px; color:#1e293b; font-variant-numeric:tabular-nums; }
  .kpi-big{ font-size:30px; font-weight:700; line-height:1; margin:8px 0 4px; font-variant-numeric:tabular-nums; }
  .kpi-pct{ font-size:11px; font-weight:600; }
  .k-sub  { font-size:10px; color:#94a3b8; margin-top:5px; }
  .k-mono { font-size:9px; font-family:monospace; font-weight:600; }
  .charts-row { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:16px; }
  .s-lbl  { font-size:9px; letter-spacing:.15em; text-transform:uppercase; font-weight:600; color:#94a3b8; }
  .s-ttl  { font-size:13px; font-weight:600; color:#1e293b; margin-top:2px; margin-bottom:12px; }
  .sec-sep{ border-left:3px solid #0d9488; padding-left:10px; margin-bottom:16px; }
  .leg-row{ display:flex; align-items:center; justify-content:space-between; margin-bottom:5px; }
  .leg-dot{ width:7px; height:7px; border-radius:50%; flex-shrink:0; }
  .tips-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; }
  .tip-card  { border-radius:16px; border:1px solid #f1f5f9; border-left:4px solid #0d9488; padding:16px; background:#fff; animation:fadeUp .4s ease both; box-shadow:0 1px 3px rgba(0,0,0,.04); }
  .tip-card:nth-child(1){animation-delay:.32s} .tip-card:nth-child(2){animation-delay:.36s}
  .tip-card:nth-child(3){animation-delay:.40s} .tip-card:nth-child(4){animation-delay:.44s}
  .tip-card:nth-child(5){animation-delay:.48s} .tip-card:nth-child(6){animation-delay:.52s}
  .tip-icon { width:30px; height:30px; border-radius:8px; display:flex; align-items:center; justify-content:center; margin-bottom:10px; }
  .tip-cat  { font-size:9px; letter-spacing:.14em; text-transform:uppercase; font-weight:600; margin-bottom:4px; }
  .tip-ttl  { font-size:12px; font-weight:600; color:#1e293b; margin-bottom:4px; line-height:1.35; }
  .tip-txt  { font-size:11px; color:#64748b; line-height:1.5; }
  .tip-pill { display:inline-flex; align-items:center; margin-top:8px; font-size:9px; font-weight:600; border-radius:99px; padding:2px 8px; }
  .h-accent   { width:3px; height:24px; background:#0d9488; border-radius:99px; }
  .conv-badge { display:inline-flex; align-items:center; gap:5px; font-size:11px; font-weight:600; border-radius:99px; padding:3px 10px; border:0.5px solid; }
  .funnel-svg-wrap { display:flex; flex-direction:column; gap:4px; padding:8px 0; }
  .funnel-row      { display:flex; align-items:center; min-height:42px; }
  .funnel-pct-label{ width:44px; text-align:right; padding-right:10px; font-size:14px; font-weight:700; color:#1e293b; flex-shrink:0; }
  .funnel-band     { height:38px; clip-path:polygon(0 0, 100% 0, calc(100% - 10px) 100%, 10px 100%); transition:width .4s cubic-bezier(.4,0,.2,1), opacity .2s; }
  .funnel-band:hover { opacity:.85; }
  .funnel-info  { padding-left:14px; flex:1; min-width:0; }
  .fnnl-label   { font-size:13px; font-weight:600; color:#1e293b; }
  .fnnl-desc    { font-size:11px; color:#94a3b8; margin-top:2px; }
  .fnnl-desc strong{ color:#0d9488; }
  @media(max-width:1200px){.kpi-row{grid-template-columns:repeat(3,minmax(0,1fr));}}
  @media(max-width:860px){.kpi-row{grid-template-columns:repeat(2,minmax(0,1fr));}.charts-row{grid-template-columns:1fr;}.tips-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}
  @media(max-width:560px){.kpi-row{grid-template-columns:repeat(2,minmax(0,1fr));}.tips-grid{grid-template-columns:1fr;}}
</style>
```

- [ ] **Step 3: Reemplazar el bloque `<!-- KPI CARDS -->` completo**

Busca desde el comentario `<!-- KPI CARDS -->` (línea ~186) hasta el cierre del `</div>` de ese bloque (línea ~268, justo antes de `<!-- EMBUDO + DISTRIBUCIÓN`). Reemplaza ese bloque entero por:

```html
  <!-- KPI CARDS: 2 filas de 6 -->
  <%
    const _m = (typeof metrics !== 'undefined' && metrics) ? metrics : {};
    const _tot = counts.total;
    const _pctOf = function(n) { return _tot > 0 ? Math.round((safeNum(n) / _tot) * 100) : 0; };
    const _pctTxt = function(n) { return _tot > 0 ? _pctOf(n) + '% del total' : '—'; };
    const _pctClr = function(n) { return safeNum(n) > 0 ? '#0d9488' : '#cbd5e1'; };
  %>

  <!-- Fila 1: Estado de leads -->
  <div class="kpi-row">

    <div class="d-card kpi-card kpi">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="font-size:18px;">👥</span>
        <span class="k-lbl">Total leads</span>
      </div>
      <div class="kpi-big" style="color:#1e293b;"><%= counts.total %></div>
      <div class="kpi-pct" style="color:#94a3b8;">base · 100%</div>
    </div>

    <div class="d-card kpi-card kpi" style="border-top:3px solid #38bdf8;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="font-size:18px;">✨</span>
        <span class="k-lbl" style="color:#0369a1;">Nuevos</span>
      </div>
      <div class="kpi-big" style="color:#0369a1;"><%= counts.new %></div>
      <div class="kpi-pct" style="color:<%= _pctClr(counts.new) %>;"><%= _pctTxt(counts.new) %></div>
    </div>

    <div class="d-card kpi-card kpi" style="border-top:3px solid #fbbf24;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="font-size:18px;">🔄</span>
        <span class="k-lbl" style="color:#b45309;">En seguimiento</span>
      </div>
      <div class="kpi-big" style="color:#b45309;"><%= counts.followup %></div>
      <div class="kpi-pct" style="color:<%= _pctClr(counts.followup) %>;"><%= _pctTxt(counts.followup) %></div>
    </div>

    <div class="d-card kpi-card kpi" style="border-top:3px solid #a78bfa;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="font-size:18px;">📥</span>
        <span class="k-lbl" style="color:#6d28d9;">Transf. recibidas</span>
      </div>
      <div class="kpi-big" style="color:#6d28d9;"><%= safeNum(_m.transferencias_recibidas) %></div>
      <div class="kpi-pct" style="color:<%= _pctClr(_m.transferencias_recibidas) %>;"><%= _pctTxt(_m.transferencias_recibidas) %></div>
    </div>

    <div class="d-card kpi-card kpi" style="border-top:3px solid #cbd5e1;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="font-size:18px;">📤</span>
        <span class="k-lbl">Traspasos realizados</span>
      </div>
      <div class="kpi-big" style="color:#475569;"><%= safeNum(_m.traspasos_realizados) %></div>
      <div class="kpi-pct" style="color:<%= _pctClr(_m.traspasos_realizados) %>;"><%= _pctTxt(_m.traspasos_realizados) %></div>
    </div>

    <div class="d-card kpi-card kpi" style="border-top:3px solid #fca5a5;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="font-size:18px;">❌</span>
        <span class="k-lbl" style="color:#b91c1c;">Finalizados sin venta</span>
      </div>
      <div class="kpi-big" style="color:#b91c1c;"><%= safeNum(_m.finalizados_sin_venta) %></div>
      <div class="kpi-pct" style="color:<%= _pctClr(_m.finalizados_sin_venta) %>;"><%= _pctTxt(_m.finalizados_sin_venta) %></div>
    </div>

  </div>

  <!-- Fila 2: Actividad y ventas -->
  <div class="kpi-row" style="margin-bottom:24px;">

    <div class="d-card kpi-card kpi" style="border-top:3px solid #a78bfa;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="font-size:18px;">📅</span>
        <span class="k-lbl" style="color:#6d28d9;">Citas hoy</span>
      </div>
      <div class="kpi-big" style="color:#5b21b6;"><%= citasHoy %></div>
      <div class="kpi-pct" style="color:<%= _pctClr(citasHoy) %>;"><%= _pctTxt(citasHoy) %></div>
    </div>

    <div class="d-card kpi-card kpi" style="border-top:3px solid #67e8f9;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="font-size:18px;">🗓️</span>
        <span class="k-lbl" style="color:#0e7490;">Citas agendadas</span>
      </div>
      <div class="kpi-big" style="color:#0e7490;"><%= safeNum(_m.citas_agendadas) %></div>
      <div class="kpi-pct" style="color:<%= _pctClr(_m.citas_agendadas) %>;"><%= _pctTxt(_m.citas_agendadas) %></div>
    </div>

    <div class="d-card kpi-card kpi" style="border-top:3px solid #86efac;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="font-size:18px;">✅</span>
        <span class="k-lbl" style="color:#15803d;">Citas atendidas</span>
      </div>
      <div class="kpi-big" style="color:#15803d;"><%= safeNum(_m.citas_atendidas) %></div>
      <div class="kpi-pct" style="color:<%= _pctClr(_m.citas_atendidas) %>;"><%= _pctTxt(_m.citas_atendidas) %></div>
    </div>

    <div class="d-card kpi-card kpi" style="border-top:3px solid #fde68a;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="font-size:18px;">✍️</span>
        <span class="k-lbl" style="color:#b45309;">Cierres con firma</span>
      </div>
      <div class="kpi-big" style="color:#b45309;"><%= safeNum(_m.cierres_firma) %></div>
      <div class="kpi-pct" style="color:<%= _pctClr(_m.cierres_firma) %>;"><%= _pctTxt(_m.cierres_firma) %></div>
    </div>

    <div class="d-card kpi-card kpi" style="border-top:3px solid #86efac;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="font-size:18px;">💰</span>
        <span class="k-lbl" style="color:#15803d;">Cierres firma y pago</span>
      </div>
      <div class="kpi-big" style="color:#15803d;"><%= safeNum(_m.cierres_firma_pago) %></div>
      <div class="kpi-pct" style="color:<%= _pctClr(_m.cierres_firma_pago) %>;"><%= _pctTxt(_m.cierres_firma_pago) %></div>
    </div>

    <div class="d-card kpi-card kpi" style="border-top:3px solid #4ade80;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="font-size:18px;">🏆</span>
        <span class="k-lbl" style="color:#166534;">Total cierres</span>
      </div>
      <div class="kpi-big" style="color:#166534;"><%= safeNum(_m.total_cierres) %></div>
      <div class="kpi-pct" style="color:<%= _pctClr(_m.total_cierres) %>;"><%= _pctTxt(_m.total_cierres) %></div>
    </div>

  </div>
```

- [ ] **Step 4: Actualizar el div contenedor de embudo + distribución**

Busca la línea (alrededor de la 271) que tiene:
```html
  <!-- EMBUDO + DISTRIBUCIÓN (2 columnas iguales) -->
  <div style="display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px;margin-bottom:12px;" class="dash-2col">
```

Reemplaza ese `<div` de apertura por:
```html
  <!-- EMBUDO + DISTRIBUCIÓN -->
  <div class="charts-row">
```

Nota: el div de cierre `</div>` al final de esa sección (antes de `<!-- ACTIVIDAD RECIENTE -->`) no cambia.

- [ ] **Step 5: Actualizar la card del embudo — quitar padding inline, usar clase**

Busca la línea:
```html
    <div class="d-card">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:4px;flex-wrap:wrap;gap:6px;">
```
(es la primera `<div class="d-card">` dentro del bloque embudo+distribución)

Reemplaza esa línea de apertura de card:
```html
    <div class="d-card" style="padding:20px;">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:4px;flex-wrap:wrap;gap:6px;">
```

Haz lo mismo para la card de distribución (la segunda `<div class="d-card">` en ese bloque):
```html
    <div class="d-card" style="padding:20px;">
      <div class="s-lbl">Distribución</div>
```

- [ ] **Step 6: Actualizar la card de actividad reciente**

Busca:
```html
  <div class="d-card" style="margin-bottom:12px;">
    <div class="s-lbl">Actividad reciente</div>
```

Reemplaza por:
```html
  <div class="d-card" style="padding:20px;margin-bottom:16px;">
    <div class="s-lbl">Actividad reciente</div>
```

- [ ] **Step 7: Actualizar sección de recomendaciones — header y quitar border-color de tip-cards**

**7a.** Busca:
```html
  <div style="margin-bottom:10px;">
    <div class="s-lbl">Recomendaciones</div>
    <div class="s-ttl">Tips para mejorar tus resultados hoy</div>
  </div>
  <div class="tips-grid">
```
Reemplaza por:
```html
  <div style="margin-bottom:12px;border-left:3px solid #0d9488;padding-left:10px;">
    <div class="s-lbl">Recomendaciones</div>
    <div class="s-ttl">Tips para mejorar tus resultados hoy</div>
  </div>
  <div class="tips-grid">
```

**7b.** Hay 6 tip-cards en el archivo. Todas tienen `style="border-color:#xxxxx;"`. El CSS nuevo del `.tip-card` ya maneja los bordes (teal izquierdo). Los `style="border-color:..."` inline tienen mayor especificidad y sobreescribirían el borde teal izquierdo.

Busca cada una de las 6 ocurrencias del patrón `<div class="tip-card" style="border-color:` y elimina el atributo `style="border-color:#xxxxx;"` dejando solo `<div class="tip-card">`.

Las 6 líneas a modificar tienen estos colores originales: `#bae6fd`, `#fde68a`, `#ddd6fe`, `#bbf7d0`, `#fed7aa`, `#e9d5ff`. Elimina el `style` completo de cada una, dejando:
```html
<div class="tip-card">
```

- [ ] **Step 8: Verificar que el servidor renderiza el dashboard sin errores**

Inicia el servidor:
```bash
node src/app.js
```

Abre en el navegador: `http://localhost:3000/advisor/crm`

Verifica:
1. No hay error 500 en la consola
2. Se ven 12 KPI cards en 2 filas de 6
3. Cada card muestra emoji, nombre, número y porcentaje
4. El fondo de la página es blanco
5. Las cards tienen bordes redondeados y sombra sutil

- [ ] **Step 9: Commit**

```bash
git add views/advisor/crm/dashboard.ejs
git commit -m "feat: redesign advisor dashboard — 12 KPI cards in 2 rows with emoji and conversion %"
```

---

## Task 4: Push a rama `pruebas-cron`

- [ ] **Step 1: Verificar que estás en la rama correcta**

```bash
git branch --show-current
```

Expected: `pruebas-cron`

Si no estás en `pruebas-cron`:
```bash
git checkout pruebas-cron
```

- [ ] **Step 2: Push**

```bash
git push origin pruebas-cron
```

Expected: Los 3 commits aparecen en Render para deploy.

---

## Notas técnicas para el implementador

**`NOW_CDMX_SQL`** es una constante ya definida en el servicio (línea ~77):
```javascript
const NOW_CDMX_SQL = `TIMEZONE('America/Mexico_City', NOW())`;
```
Se puede usar directamente en el template SQL de `getAdvisorDashboardMetrics` porque la función está en el mismo archivo.

**`toId()`** es una función helper del mismo archivo que hace cast a número entero. Ya se usa en todas las demás funciones del servicio.

**`pool`** es la instancia de PostgreSQL ya importada al inicio del archivo. No requiere ningún import adicional.

**`confirmed_at`** en `crm_activities`: se establece con `SET confirmed_at = NOW()` cuando el asesor marca una cita como "atendida" desde el panel CRM. Si es `NULL`, la cita no ha sido confirmada.

**`sale_signed_only`** y **`sale_paid`**: ambas columnas existen en `crm_leads`. Un lead puede tener `sale_signed_only = true` cuando cerró solo con firma (primer pago), y `sale_paid = true` cuando ya completó el pago total.

**Directivo view mode**: El dashboard también se usa cuando un directivo observa el panel de un asesor (`/directivo/asesores/:id/dashboard`). La variable `viewMode = 'directivo'` y `viewingAdvisor` se pasan desde ese controller. Las métricas del backend siguen siendo del `advisorId` correcto.
