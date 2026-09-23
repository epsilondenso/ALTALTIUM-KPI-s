# Google Calendar — Reconexión con Control de Acceso por Rol — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconstruir la pestaña "Integraciones" en Mi Perfil como punto único de conexión OAuth a Google Calendar (hoy un link roto), con acceso funcional solo para `advisor`, `manager`, `directivo`, `marketing`, y un badge/tarjeta de bloqueo permanente para `externo` en vez del 403 crudo actual.

**Architecture:** Un helper centralizado de dos funciones en `googleCalendar.service.js` decide acceso funcional y visibilidad de la pestaña; `profile.controller.js` lo consulta (con el estado de conexión leído directo de la tabla `google_tokens`, no de sesión) y lo pasa a la vista; la vista agrega una pestaña más al sistema de tabs ya existente. Un segundo punto (la ruta `/advisor/crm/calendar`, compartida con `externo`) usa el mismo helper para decidir si renderiza el calendario o una tarjeta de bloqueo.

**Tech Stack:** Node.js + Express 5, EJS (sin test runner en el proyecto — verificación vía `node --check`, `ejs.compile`, y scripts `node -e` contra la BD local, seguido de smoke test con el servidor de desarrollo corriendo).

**Nota sobre "TDD" en este proyecto:** no hay suite de tests automatizados. Cada tarea sigue el mismo ritmo (escribir el cambio → verificar de inmediato con un script o `curl` → seguir), pero las "pruebas" son scripts puntuales, no un framework instalado. No se instala ninguno nuevo — sería un cambio de alcance no pedido.

---

## Task 1: Helper de acceso — `googleCalendar.service.js`

**Files:**
- Modify: `src/services/googleCalendar.service.js:1-18` (imports/inicio) y `:237-248` (exports)

- [ ] **Step 1: Agregar el helper de roles justo después de los imports**

En `src/services/googleCalendar.service.js`, después de la línea 9 (`const pool = require('../db/pool');`), insertar:

```js

// ── Control de acceso por rol ──────────────────────────────────
// Fase 1 (jul 2026): solo estos 4 roles pueden conectar/usar Google
// Calendar. administracion, rrhh y admin quedan para una fase posterior —
// no ven la pestaña de conexión todavía (no es un bloqueo permanente,
// simplemente no les toca aún). externo sí ve la pestaña, pero con mensaje
// de bloqueo permanente (comparte sidebar/rutas con advisor).
const ROLES_CON_ACCESO_CALENDAR = new Set(['advisor', 'manager', 'directivo', 'marketing']);

function puedeUsarGoogleCalendar(role) {
  return ROLES_CON_ACCESO_CALENDAR.has(String(role || '').toLowerCase());
}

function debeVerPestanaIntegraciones(role) {
  const r = String(role || '').toLowerCase();
  return ROLES_CON_ACCESO_CALENDAR.has(r) || r === 'externo';
}
```

- [ ] **Step 2: Exportar las dos funciones nuevas**

En el bloque `module.exports` al final del archivo (línea ~237-248), agregar las dos funciones:

```js
module.exports = {
  getOAuthClient,
  getAuthUrl,
  getTokensFromCode,
  getAuthorizedClient,
  getCalendar,
  isConnected,
  listEvents,
  createEvent,
  updateEvent,
  deleteEvent,
  puedeUsarGoogleCalendar,
  debeVerPestanaIntegraciones,
};
```

- [ ] **Step 3: Verificar sintaxis**

Run: `node --check src/services/googleCalendar.service.js`
Expected: sin salida (sintaxis OK).

- [ ] **Step 4: Verificar el comportamiento para los 8 roles del sistema**

Ejecutar este script puntual (no queda en el repo, es solo para verificar):

```bash
node -e "
const calendarSvc = require('./src/services/googleCalendar.service');
const roles = ['advisor','manager','directivo','marketing','administracion','rrhh','admin','externo'];
const esperadoAcceso = { advisor:true, manager:true, directivo:true, marketing:true, administracion:false, rrhh:false, admin:false, externo:false };
const esperadoTab    = { advisor:true, manager:true, directivo:true, marketing:true, administracion:false, rrhh:false, admin:false, externo:true };
let ok = true;
for (const r of roles) {
  const acceso = calendarSvc.puedeUsarGoogleCalendar(r);
  const tab    = calendarSvc.debeVerPestanaIntegraciones(r);
  if (acceso !== esperadoAcceso[r]) { ok = false; console.log('FALLO acceso', r, '->', acceso, 'esperado', esperadoAcceso[r]); }
  if (tab !== esperadoTab[r])       { ok = false; console.log('FALLO tab', r, '->', tab, 'esperado', esperadoTab[r]); }
}
console.log(ok ? 'Los 8 roles se comportan como se espera' : 'HAY FALLOS');
"
```

Expected: `Los 8 roles se comportan como se espera`

- [ ] **Step 5: Commit (NO ejecutar todavía — el usuario pidió esperar autorización)**

No ejecutar `git add`/`git commit` en este paso. Se deja pendiente hasta que el usuario autorice explícitamente al final de todo el plan.

---

## Task 2: Redirigir de vuelta a la pestaña Integraciones tras conectar/desconectar

**Files:**
- Modify: `src/routes/googleCalendar.routes.js:27-79`

Hoy las 4 redirecciones del flujo OAuth mandan a `/profile` sin especificar
pestaña, así que el usuario vuelve a la pestaña "Información" en vez de ver
el resultado en Integraciones.

- [ ] **Step 1: Actualizar las 4 redirecciones**

En `src/routes/googleCalendar.routes.js`:

Línea 28 (`if (error || !code)`), cambiar:
```js
    return res.redirect('/profile?calendar=error');
```
por:
```js
    return res.redirect('/profile?tab=integraciones&calendar=error');
```

Línea 57 (callback exitoso), cambiar:
```js
    req.session.calendarConnected = true;
    return res.redirect('/profile?calendar=conectado');
```
por:
```js
    req.session.calendarConnected = true;
    return res.redirect('/profile?tab=integraciones&calendar=conectado');
```

Línea 61 (catch del callback), cambiar:
```js
    console.error('[googleCalendar] callback error:', err.message);
    return res.redirect('/profile?calendar=error');
```
por:
```js
    console.error('[googleCalendar] callback error:', err.message);
    return res.redirect('/profile?tab=integraciones&calendar=error');
```

Línea 75 (disconnect exitoso), cambiar:
```js
    req.session.calendarConnected = false;
    return res.redirect('/profile?calendar=desconectado');
```
por:
```js
    req.session.calendarConnected = false;
    return res.redirect('/profile?tab=integraciones&calendar=desconectado');
```

Línea 78 (catch del disconnect), cambiar:
```js
    console.error('[googleCalendar] disconnect error:', err.message);
    return res.redirect('/profile?calendar=error');
```
por:
```js
    console.error('[googleCalendar] disconnect error:', err.message);
    return res.redirect('/profile?tab=integraciones&calendar=error');
```

- [ ] **Step 2: Verificar sintaxis**

Run: `node --check src/routes/googleCalendar.routes.js`
Expected: sin salida.

- [ ] **Step 3: Confirmar visualmente que las 4 ocurrencias quedaron consistentes**

Run: `grep -n "profile?tab=integraciones" src/routes/googleCalendar.routes.js`
Expected: 4 líneas de resultado.

---

## Task 3: Wire — `profile.controller.js`

**Files:**
- Modify: `src/controllers/profile.controller.js:1-61`

- [ ] **Step 1: Importar el servicio de calendario**

Después de la línea `const { formatPresencia } = require('../utils/presencia');`, agregar:

```js
const calendarSvc     = require('../services/googleCalendar.service');
```

- [ ] **Step 2: Calcular acceso y estado de conexión dentro de `exports.index`**

Ubicar este bloque (dentro de `exports.index`, justo antes del `Promise.allSettled`):

```js
    const [favoritosR, activityR, auditR, leadsFavR, statsR, lastSeenR] = await Promise.allSettled([
      profileService.getFavoritosByUserId(userId),
      profileService.getActivityByUserId(userId),
      profileService.getAuditByUserId(userId),
      leadFavService.getLeadsFavoritos(userId),
      pool.query(`
        SELECT
          COUNT(*) FILTER (WHERE status = 'open')                                              AS leads_activos,
          COUNT(*) FILTER (WHERE (sale_paid = true OR sale_signed = true) AND status = 'closed') AS cierres
        FROM crm_leads
        WHERE advisor_id = $1
      `, [userId]),
      pool.query('SELECT last_seen_at FROM users WHERE id = $1', [userId]),
    ]);
```

Reemplazarlo por (agrega la consulta a `google_tokens` al mismo batch, solo
si el rol tiene acceso funcional — para no gastar una query de más en
roles que ni la van a usar):

```js
    const calendarAllowed     = calendarSvc.puedeUsarGoogleCalendar(user.role);
    const calendarTabVisible  = calendarSvc.debeVerPestanaIntegraciones(user.role);

    const [favoritosR, activityR, auditR, leadsFavR, statsR, lastSeenR, calendarConnR] = await Promise.allSettled([
      profileService.getFavoritosByUserId(userId),
      profileService.getActivityByUserId(userId),
      profileService.getAuditByUserId(userId),
      leadFavService.getLeadsFavoritos(userId),
      pool.query(`
        SELECT
          COUNT(*) FILTER (WHERE status = 'open')                                              AS leads_activos,
          COUNT(*) FILTER (WHERE (sale_paid = true OR sale_signed = true) AND status = 'closed') AS cierres
        FROM crm_leads
        WHERE advisor_id = $1
      `, [userId]),
      pool.query('SELECT last_seen_at FROM users WHERE id = $1', [userId]),
      calendarAllowed ? calendarSvc.isConnected(userId) : Promise.resolve(false),
    ]);
```

- [ ] **Step 3: Leer el resultado y pasarlo a la vista**

Ubicar:

```js
    const leadsFavoritos = leadsFavR.value || [];

    return res.render('profile/index', {
```

Reemplazarlo por:

```js
    const leadsFavoritos = leadsFavR.value || [];
    const calendarConectado = calendarConnR.status === 'fulfilled' ? !!calendarConnR.value : false;

    return res.render('profile/index', {
```

Y dentro del objeto pasado a `res.render`, junto a `stats,` (última línea
antes del `});` de cierre), agregar las 3 nuevas propiedades:

```js
      stats,
      calendarAllowed,
      calendarTabVisible,
      calendarConectado,
    });
```

- [ ] **Step 4: Verificar sintaxis**

Run: `node --check src/controllers/profile.controller.js`
Expected: sin salida.

- [ ] **Step 5: Verificar el wiring completo con un req/res simulado**

Este script simula el controller sin necesidad de un servidor HTTP —
captura lo que `res.render` recibiría, usando usuarios reales de la BD
local (uno por cada rol presente):

```bash
node -e "
require('dotenv').config();
const pool = require('./src/db/pool');
const profileCtrl = require('./src/controllers/profile.controller');
(async () => {
  const roles = ['advisor','manager','administracion','externo'];
  for (const role of roles) {
    const u = await pool.query('SELECT id, role FROM users WHERE role = \$1 LIMIT 1', [role]);
    if (!u.rows.length) { console.log(role, '-> sin usuario de prueba en BD local, se omite'); continue; }
    const userId = u.rows[0].id;
    const req = { session: { user: { id: userId, role } }, query: {} };
    const res = { render: (view, locals) => {
      console.log(role, '-> calendarAllowed:', locals.calendarAllowed, '| calendarTabVisible:', locals.calendarTabVisible, '| calendarConectado:', locals.calendarConectado);
    }};
    await profileCtrl.index(req, res, (err) => { if (err) console.error(role, 'ERROR:', err.message); });
  }
  await pool.end();
})();
"
```

Expected: una línea por rol disponible en BD local, con `manager` y
`advisor` mostrando `calendarAllowed: true`, `administracion` y `externo`
mostrando `calendarAllowed: false` (y `externo` con `calendarTabVisible:
true` pese a `calendarAllowed: false`, `administracion` con ambos en
`false`).

---

## Task 4: Pestaña "Integraciones" — `views/profile/index.ejs`

**Files:**
- Modify: `views/profile/index.ejs:410` (CSS), `:593-597` (nav de tabs),
  `:673-674` (paneles), `:1176` (`switchTab`), `:1486` (fin de script)

- [ ] **Step 1: Agregar el botón de la pestaña en el nav vertical**

Ubicar (línea 593-597):

```ejs
        <button class="pf-vlink <%= tabActiva==='historial' ? 'on' : '' %>" id="tab-btn-historial" onclick="switchTab('historial')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          Historial
        </button>
      </nav>
```

Reemplazarlo por:

```ejs
        <button class="pf-vlink <%= tabActiva==='historial' ? 'on' : '' %>" id="tab-btn-historial" onclick="switchTab('historial')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
          Historial
        </button>
        <% if (calendarTabVisible) { %>
        <button class="pf-vlink <%= tabActiva==='integraciones' ? 'on' : '' %>" id="tab-btn-integraciones" onclick="switchTab('integraciones')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          Integraciones
        </button>
        <% } %>
      </nav>
```

- [ ] **Step 2: Agregar el panel de contenido**

Ubicar el bloque exacto (líneas 1099-1129 del archivo original, el cierre
del panel de Historial seguido del cierre de `<div style="min-width:0">`,
`.pf-body`, `main`, `.pf-wrap` y `.pf-page`):

```ejs
        <div id="panel-historial" class="<%= tabActiva==='historial' ? '' : 'pf-hide' %>">
          <section class="pf-sec">
            <div class="pf-sec-head">
              <span class="pf-sico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></span>
              <h2>Historial de actividad</h2>
              <span class="pf-rule"></span>
            </div>
            <% if (!activity || activity.length === 0) { %>
            <div class="pf-empty">
              <div class="pf-eico">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              </div>
              <h3>Sin actividad registrada</h3>
              <p>Aquí aparecerá tu actividad reciente en la plataforma</p>
            </div>
            <% } else { %>
            <% activity.slice(0,20).forEach(act => { %>
            <div class="pf-titem">
              <span class="pf-tdate"><%= shortDate(act.created_at) %></span>
              <div class="pf-ttxt"><%= act.action || act.descripcion || act.tipo || 'Actividad' %></div>
            </div>
            <% }) %>
            <% } %>
          </section>
        </div>

      </div><!-- /paneles -->
    </div><!-- /pf-body -->
  </main>
</div><!-- /pf-wrap -->
</div><!-- /pf-page -->
```

Reemplazarlo por (idéntico al bloque original, pero con el nuevo panel de
Integraciones insertado entre el cierre de `panel-historial` y el cierre de
`<div style="min-width:0">` — el resto de la estructura de cierre queda
exactamente igual):

```ejs
        <div id="panel-historial" class="<%= tabActiva==='historial' ? '' : 'pf-hide' %>">
          <section class="pf-sec">
            <div class="pf-sec-head">
              <span class="pf-sico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></span>
              <h2>Historial de actividad</h2>
              <span class="pf-rule"></span>
            </div>
            <% if (!activity || activity.length === 0) { %>
            <div class="pf-empty">
              <div class="pf-eico">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              </div>
              <h3>Sin actividad registrada</h3>
              <p>Aquí aparecerá tu actividad reciente en la plataforma</p>
            </div>
            <% } else { %>
            <% activity.slice(0,20).forEach(act => { %>
            <div class="pf-titem">
              <span class="pf-tdate"><%= shortDate(act.created_at) %></span>
              <div class="pf-ttxt"><%= act.action || act.descripcion || act.tipo || 'Actividad' %></div>
            </div>
            <% }) %>
            <% } %>
          </section>
        </div>

        <% if (calendarTabVisible) { %>
        <!-- ══ PANEL: INTEGRACIONES ══ -->
        <div id="panel-integraciones" class="<%= tabActiva==='integraciones' ? '' : 'pf-hide' %>">
          <section class="pf-sec">
            <div class="pf-sec-head">
              <span class="pf-sico"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg></span>
              <h2>Integraciones</h2>
              <span class="pf-rule"></span>
            </div>

            <% if (!calendarAllowed) { %>
            <!-- Rol externo: bloqueo permanente -->
            <div class="pf-int-card pf-int-locked">
              <span class="pf-int-ico">🔒</span>
              <div>
                <p class="pf-int-title">Función solo para usuarios internos</p>
                <p class="pf-int-sub">Si necesitas habilitar esta sección, contacta a Dirección General.</p>
              </div>
            </div>
            <% } else if (calendarConectado) { %>
            <!-- Conectado -->
            <div class="pf-int-card pf-int-ok">
              <span class="pf-int-ico">✓</span>
              <div>
                <p class="pf-int-title">Google Calendar conectado</p>
                <p class="pf-int-sub">Tus citas y eventos se sincronizan con tu cuenta de Google.</p>
              </div>
              <a href="/auth/google/calendar/disconnect" class="pf-int-btn pf-int-btn-danger">Desconectar</a>
            </div>
            <% } else { %>
            <!-- No conectado -->
            <div class="pf-int-card pf-int-pending">
              <span class="pf-int-ico">📅</span>
              <div>
                <p class="pf-int-title">Conecta tu Google Calendar</p>
                <p class="pf-int-sub">Sincroniza tus citas y actividades del CRM con tu cuenta de Google.</p>
              </div>
              <a href="/auth/google/calendar" class="pf-int-btn pf-int-btn-primary">Conectar Google Calendar</a>
            </div>
            <% } %>
          </section>
        </div>
        <% } %>

      </div><!-- /paneles -->
    </div><!-- /pf-body -->
  </main>
</div><!-- /pf-wrap -->
</div><!-- /pf-page -->
```

- [ ] **Step 3: Registrar la pestaña en `switchTab`**

Ubicar (línea ~1176):

```js
function switchTab(id) {
  const panels = ['perfil','calc','leads-fav','props-fav','historial'];
```

Reemplazar por:

```js
function switchTab(id) {
  const panels = ['perfil','calc','leads-fav','props-fav','historial','integraciones'];
```

(Seguro para roles sin la pestaña: el `if (!panel || !btn) return;` que ya
sigue en la función se salta silenciosamente los elementos que no existen.)

- [ ] **Step 4: Mostrar confirmación al volver del flujo OAuth**

Justo antes del `</script>` final (línea 1486), agregar:

```js

// ── Confirmación al volver de conectar/desconectar Google Calendar ──────
(function () {
  const params = new URLSearchParams(window.location.search);
  const estado = params.get('calendar');
  if (!estado) return;
  const mensajes = {
    conectado:     'Google Calendar conectado ✓',
    desconectado:  'Google Calendar desconectado',
    error:         'No se pudo completar la conexión con Google Calendar',
  };
  if (mensajes[estado]) showToast(mensajes[estado]);
  // Limpia el query param para que un refresh no vuelva a mostrar el toast
  params.delete('calendar');
  const nuevaUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
  window.history.replaceState({}, '', nuevaUrl);
})();
```

- [ ] **Step 5: Agregar el CSS de las tarjetas de Integraciones**

Justo antes de `.pf-hide{display:none !important}` (línea 410), insertar:

```css
.pf-int-card{
  display:flex;align-items:center;gap:16px;
  border:1px solid var(--pf-line);border-radius:14px;
  padding:20px 22px;background:var(--pf-surface);
}
.pf-int-ico{font-size:26px;flex-shrink:0}
.pf-int-title{font-size:14px;font-weight:700;color:var(--pf-ink);margin:0 0 4px}
.pf-int-sub{font-size:12.5px;color:var(--pf-muted);margin:0}
.pf-int-btn{
  margin-left:auto;flex-shrink:0;white-space:nowrap;
  display:inline-flex;align-items:center;gap:6px;
  border-radius:12px;padding:9px 18px;font-size:13px;font-weight:700;
  text-decoration:none;transition:opacity .15s;
}
.pf-int-btn:hover{opacity:.88}
.pf-int-btn-primary{background:var(--pf-teal);color:#fff}
.pf-int-btn-danger{background:#fff;color:#b91c1c;border:1px solid #fecaca}
.pf-int-pending{border-color:rgba(0,138,138,.25);background:var(--pf-teal-soft)}
.pf-int-ok{border-color:rgba(22,163,74,.25);background:var(--pf-green-soft)}
.pf-int-locked{border-color:#fed7aa;background:rgba(249,115,22,.06)}
```

- [ ] **Step 6: Verificar sintaxis EJS**

Run:
```bash
node -e "
const ejs = require('ejs'); const fs = require('fs');
ejs.compile(fs.readFileSync('views/profile/index.ejs','utf8'), {filename: 'views/profile/index.ejs'});
console.log('EJS OK');
"
```
Expected: `EJS OK`

- [ ] **Step 7: Renderizar los 3 estados con locals simulados**

```bash
node -e "
const ejs = require('ejs'); const fs = require('fs');
const tpl = fs.readFileSync('views/profile/index.ejs','utf8');
const base = {
  user: { id:1, nombre:'Test', apellidos:'User', role:'advisor', roles_extra:[] },
  tab: 'integraciones', presencia:{label:'',dotClass:''}, lastSeenAt:null,
  favoritos:[], activity:[], audit:[], leadsFavoritos:[], leadsFavCount:0,
  stats:{leadsActivos:0,cierres:0},
};
const casos = [
  { nombre: 'permitido + no conectado', locals: { ...base, calendarAllowed:true, calendarTabVisible:true, calendarConectado:false } },
  { nombre: 'permitido + conectado',    locals: { ...base, calendarAllowed:true, calendarTabVisible:true, calendarConectado:true } },
  { nombre: 'externo (bloqueado)',      locals: { ...base, user:{...base.user, role:'externo'}, calendarAllowed:false, calendarTabVisible:true, calendarConectado:false } },
  { nombre: 'administracion (sin tab)', locals: { ...base, user:{...base.user, role:'administracion'}, calendarAllowed:false, calendarTabVisible:false, calendarConectado:false } },
];
for (const c of casos) {
  const html = ejs.render(tpl, c.locals, { filename: 'views/profile/index.ejs' });
  const tieneTab = html.includes('tab-btn-integraciones');
  const tieneConectar = html.includes('Conectar Google Calendar');
  const tieneDesconectar = html.includes('Desconectar');
  const tieneBloqueo = html.includes('Dirección General');
  console.log(c.nombre, '-> tab:', tieneTab, '| botón conectar:', tieneConectar, '| botón desconectar:', tieneDesconectar, '| mensaje bloqueo:', tieneBloqueo);
}
"
```

Expected:
```
permitido + no conectado -> tab: true | botón conectar: true | botón desconectar: false | mensaje bloqueo: false
permitido + conectado -> tab: true | botón conectar: false | botón desconectar: true | mensaje bloqueo: false
externo (bloqueado) -> tab: true | botón conectar: false | botón desconectar: false | mensaje bloqueo: true
administracion (sin tab) -> tab: false | botón conectar: false | botón desconectar: false | mensaje bloqueo: false
```

Nota: este render usa layout:false implícito de `ejs.render` — puede fallar
si el template usa `<%- include(...) %>` a partials que dependen de rutas
relativas al motor de vistas de Express (no a `ejs.render` standalone). Si
falla por eso, usar en su lugar el Step 8 (arranque real del servidor) como
verificación primaria y anotar en el resultado que el render aislado no
aplica a esta plantilla.

---

## Task 5: Badge de candado para `externo` en el sidebar de advisor

**Files:**
- Modify: `views/advisor/crm/partials/sidebar.ejs:240-249`

- [ ] **Step 1: Agregar el candado junto al link de "Mi calendario"**

Ubicar (línea 240-249):

```ejs
    <a href="/advisor/crm/calendar" class="asb-link <%= active('/advisor/crm/calendar') ? 'asb-active' : '' %>">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/>
        <line x1="8" y1="2" x2="8" y2="6"/>
        <line x1="3" y1="10" x2="21" y2="10"/>
      </svg>
      <span class="asb-link-lbl">Mi calendario</span>
      <span id="badgeCalHoyAdvisor" class="asb-badge" style="display:none;">0</span>
    </a>
```

Reemplazarlo por:

```ejs
    <a href="/advisor/crm/calendar" class="asb-link <%= active('/advisor/crm/calendar') ? 'asb-active' : '' %>">
      <svg viewBox="0 0 24 24" fill="none" stroke-width="2">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/>
        <line x1="8" y1="2" x2="8" y2="6"/>
        <line x1="3" y1="10" x2="21" y2="10"/>
      </svg>
      <span class="asb-link-lbl">Mi calendario</span>
      <% if (typeof currentUser !== 'undefined' && currentUser && currentUser.role === 'externo') { %>
        <span title="Solo usuarios internos" style="margin-left:auto;font-size:11px;">🔒</span>
      <% } else { %>
        <span id="badgeCalHoyAdvisor" class="asb-badge" style="display:none;">0</span>
      <% } %>
    </a>
```

- [ ] **Step 2: Verificar sintaxis EJS**

Run:
```bash
node -e "
const ejs = require('ejs'); const fs = require('fs');
ejs.compile(fs.readFileSync('views/advisor/crm/partials/sidebar.ejs','utf8'), {filename: 'views/advisor/crm/partials/sidebar.ejs'});
console.log('EJS OK');
"
```
Expected: `EJS OK`

- [ ] **Step 3: Confirmar que `active(...)` y demás helpers usados en el partial siguen intactos (no se rompió nada del entorno del partial)**

Run: `grep -n "function active" views/advisor/crm/partials/sidebar.ejs`
Expected: al menos 1 resultado (la función sigue definida arriba en el mismo archivo, sin tocar).

---

## Task 6: Quitar el 403 crudo para `externo` en `/advisor/crm/calendar`

**Files:**
- Modify: `src/routes/main.routes.js:1322-1348`

- [ ] **Step 1: Importar el servicio de calendario en main.routes.js**

Ubicar la línea:
```js
const { getAsesorDelMes } = require('../services/asesorMes.service');
```
(ya modificada en un trabajo previo para incluir `getCached` justo debajo —
verificar con `grep -n "getCached\|asesorMes.service" src/routes/main.routes.js`
cuál es el estado exacto antes de editar). Agregar, junto a los demás
requires de servicios cerca de la línea 31 (`const crmService =
require('../services/advisor/crm.service');`):

```js
const calendarSvc = require('../services/googleCalendar.service');
```

- [ ] **Step 2: Cambiar el middleware y agregar la rama restringida**

Ubicar el handler completo:

```js
router.get('/advisor/crm/calendar', ensureAuth, requireRole('advisor'), async (req, res) => {
  try {
    const user = req.session?.user;
    if (!user) return res.redirect('/auth/login');

    const role = (user.role || '').toLowerCase();
    // Respeta tu lógica existente: advisor y externo entran como advisor
    const isAdvisorLike = (r) => ['advisor', 'externo'].includes(r);
    if (!isAdvisorLike(role)) return res.redirect('/home');

    const [appointments, notes] = await Promise.all([
      crmService.listCalendarAppointmentsByAdvisor(user.id),
      calendarController.getNotesForAdvisor(user.id),
    ]);

    return res.render('advisor/crm/calendar', {
      layout: false,
      title: 'Calendario',
      user,
      appointments,
      notes,
      tz: 'America/Mexico_City',
      path: '/advisor/crm/calendar'
    });
  } catch (err) {
    console.error('❌ Error calendar route:', err);
    return res.status(500).render('error', { message: 'Error al cargar el calendario' });
  }
});
```

Reemplazarlo por (cambia el middleware de `requireRole('advisor')` a
`requireAdvisorLike`, que ya permite `externo` y `administracion` además de
advisor/marketing/rrhh/manager/directivo/admin por jerarquía; agrega la
rama `restringido`):

```js
router.get('/advisor/crm/calendar', ensureAuth, requireAdvisorLike, async (req, res) => {
  try {
    const user = req.session?.user;
    if (!user) return res.redirect('/auth/login');

    const role = (user.role || '').toLowerCase();
    // Respeta tu lógica existente: advisor y externo entran como advisor
    const isAdvisorLike = (r) => ['advisor', 'externo'].includes(r);
    if (!isAdvisorLike(role)) return res.redirect('/home');

    // externo comparte esta ruta con advisor pero no tiene acceso funcional
    // a Google Calendar (fase 1) — se renderiza la misma vista con la
    // tarjeta de bloqueo en vez de un 403 crudo.
    const restringido = !calendarSvc.puedeUsarGoogleCalendar(role);

    const [appointments, notes] = restringido
      ? [[], []]
      : await Promise.all([
          crmService.listCalendarAppointmentsByAdvisor(user.id),
          calendarController.getNotesForAdvisor(user.id),
        ]);

    return res.render('advisor/crm/calendar', {
      layout: false,
      title: 'Calendario',
      user,
      appointments,
      notes,
      tz: 'America/Mexico_City',
      path: '/advisor/crm/calendar',
      restringido,
    });
  } catch (err) {
    console.error('❌ Error calendar route:', err);
    return res.status(500).render('error', { message: 'Error al cargar el calendario' });
  }
});
```

- [ ] **Step 3: Verificar sintaxis**

Run: `node --check src/routes/main.routes.js`
Expected: sin salida.

- [ ] **Step 4: Confirmar que `requireAdvisorLike` ya estaba importado (no debe hacer falta agregarlo)**

Run: `grep -n "requireAdvisorLike" src/routes/main.routes.js`
Expected: al menos 2 resultados (el import y este nuevo uso).

---

## Task 7: Tarjeta de bloqueo + aviso de conexión en `advisor/crm/calendar.ejs`

**Files:**
- Modify: `views/advisor/crm/calendar.ejs:26-56`

- [ ] **Step 1: Envolver el contenido principal en la lógica condicional**

Ubicar el bloque completo (línea 26-56):

```ejs
<main class="px-6 py-6 pb-24 md:pb-6">
      <div class="max-w-6xl mx-auto">
        <div class="flex items-center justify-between gap-4 mb-4">
          <div>
            <h1 class="text-2xl font-bold">Calendario</h1>
            <p class="text-sm text-slate-500">Tus actividades programadas y notas por día.</p>
          </div>
          <button id="btnNewNote" class="px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold">
            + Nueva nota
          </button>
        </div>

        <!-- Leyenda / info -->
        <div class="flex items-center gap-3 mb-4 flex-wrap">
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#2563eb"></span><span class="text-xs text-slate-500">Llamada</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#16a34a"></span><span class="text-xs text-slate-500">WhatsApp</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#d97706"></span><span class="text-xs text-slate-500">Correo</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#0891b2"></span><span class="text-xs text-slate-500">Cita</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#7c3aed"></span><span class="text-xs text-slate-500">Cita videollamada</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#0d9488"></span><span class="text-xs text-slate-500">Cita presencial</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#ea580c"></span><span class="text-xs text-slate-500">Visita inmueble</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#15803d"></span><span class="text-xs text-slate-500">Cita atendida</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#b45309"></span><span class="text-xs text-slate-500">Cita reagendada</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full bg-yellow-600"></span><span class="text-xs text-slate-500">Nota personal</span></div>
        </div>

        <div class="rounded-2xl border border-slate-200 bg-white shadow-sm p-4">
          <div id="calendar"></div>
        </div>
      </div>
```

Reemplazarlo por:

```ejs
<main class="px-6 py-6 pb-24 md:pb-6">
      <div class="max-w-6xl mx-auto">
<% if (typeof restringido !== 'undefined' && restringido) { %>
        <!-- Tarjeta de acceso restringido (rol externo, fase 1) -->
        <div style="background:rgba(249,115,22,.06);border:1px solid #fed7aa;border-radius:14px;padding:24px 28px;display:flex;align-items:center;gap:16px;">
          <span style="font-size:28px;">🔒</span>
          <div>
            <p style="font-size:14px;font-weight:700;color:#9a3412;margin:0 0 4px;">Función solo para usuarios internos</p>
            <p style="font-size:13px;color:#c2410c;margin:0;">Si necesitas habilitar esta sección, contacta a Dirección General.</p>
          </div>
        </div>
<% } else { %>
        <div class="flex items-center justify-between gap-4 mb-4">
          <div>
            <h1 class="text-2xl font-bold">Calendario</h1>
            <p class="text-sm text-slate-500">Tus actividades programadas y notas por día.</p>
          </div>
          <button id="btnNewNote" class="px-4 py-2 rounded-xl bg-teal-600 hover:bg-teal-700 text-white text-sm font-semibold">
            + Nueva nota
          </button>
        </div>

  <% if (!(typeof calendarConnected !== 'undefined' && calendarConnected === true)) { %>
        <div style="background:#f0fdfa;border:1px solid #99f6e4;border-radius:14px;padding:20px 24px;display:flex;align-items:center;gap:16px;margin-bottom:16px;">
          <span style="font-size:26px;">📅</span>
          <div>
            <p style="font-size:14px;font-weight:700;color:#0f766e;margin:0 0 4px;">Conecta tu Google Calendar</p>
            <p style="font-size:13px;color:#0d9488;margin:0 0 10px;">Vincula tu cuenta desde tu perfil para sincronizar tus citas.</p>
            <a href="/profile?tab=integraciones" style="display:inline-flex;align-items:center;gap:6px;border-radius:12px;background:#0d9488;color:#fff;padding:8px 16px;font-size:13px;font-weight:600;text-decoration:none;">Ir a conectar →</a>
          </div>
        </div>
  <% } %>

        <!-- Leyenda / info -->
        <div class="flex items-center gap-3 mb-4 flex-wrap">
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#2563eb"></span><span class="text-xs text-slate-500">Llamada</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#16a34a"></span><span class="text-xs text-slate-500">WhatsApp</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#d97706"></span><span class="text-xs text-slate-500">Correo</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#0891b2"></span><span class="text-xs text-slate-500">Cita</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#7c3aed"></span><span class="text-xs text-slate-500">Cita videollamada</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#0d9488"></span><span class="text-xs text-slate-500">Cita presencial</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#ea580c"></span><span class="text-xs text-slate-500">Visita inmueble</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#15803d"></span><span class="text-xs text-slate-500">Cita atendida</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#b45309"></span><span class="text-xs text-slate-500">Cita reagendada</span></div>
          <div class="flex items-center gap-1.5"><span class="inline-block w-2.5 h-2.5 rounded-full bg-yellow-600"></span><span class="text-xs text-slate-500">Nota personal</span></div>
        </div>

        <div class="rounded-2xl border border-slate-200 bg-white shadow-sm p-4">
          <div id="calendar"></div>
        </div>
<% } %>
      </div>
```

(El resto del archivo —modales, `<script>`— no cambia. Ya es seguro: el
script existente ya hace `if (!calendarEl) { console.error(...); return;
}` y usa `btnNewNote?.addEventListener`, así que no truena si esos
elementos no existen en la rama `restringido`.)

- [ ] **Step 2: Verificar sintaxis EJS**

Run:
```bash
node -e "
const ejs = require('ejs'); const fs = require('fs');
ejs.compile(fs.readFileSync('views/advisor/crm/calendar.ejs','utf8'), {filename: 'views/advisor/crm/calendar.ejs'});
console.log('EJS OK');
"
```
Expected: `EJS OK`

---

## Task 8: Verificación final integral

**Files:** ninguno nuevo — valida el conjunto de las Tasks 1-7.

- [ ] **Step 1: Sintaxis de todos los archivos JS tocados**

```bash
for f in \
  src/services/googleCalendar.service.js \
  src/routes/googleCalendar.routes.js \
  src/controllers/profile.controller.js \
  src/routes/main.routes.js; do
  node --check "$f" || echo "FALLO: $f"
done
echo "listo"
```
Expected: `listo` sin ningún `FALLO`.

- [ ] **Step 2: Sintaxis de todas las vistas EJS tocadas**

```bash
node -e "
const ejs = require('ejs'); const fs = require('fs');
const archivos = [
  'views/profile/index.ejs',
  'views/advisor/crm/partials/sidebar.ejs',
  'views/advisor/crm/calendar.ejs',
];
for (const f of archivos) {
  ejs.compile(fs.readFileSync(f,'utf8'), {filename: f});
  console.log('OK:', f);
}
"
```
Expected: 3 líneas `OK:`.

- [ ] **Step 3: Reiniciar el servidor local y confirmar `/health`**

El servidor ya corre con `nodemon` en background (detecta los cambios de
archivo solo). Esperar el auto-restart y confirmar:

```bash
sleep 4
curl -s -o /dev/null -w "health: HTTP %{http_code}\n" http://localhost:3000/health
```
Expected: `health: HTTP 200`

- [ ] **Step 4: Smoke test de `/advisor/crm/calendar` sin sesión (debe redirigir a login, no 500)**

```bash
curl -s -o /dev/null -w "sin sesión: HTTP %{http_code}\n" http://localhost:3000/advisor/crm/calendar
```
Expected: `sin sesión: HTTP 302` (redirect a `/auth/login`, comportamiento
sin cambios — `ensureAuth` sigue primero en la cadena de middlewares).

- [ ] **Step 5: Confirmar en BD local que `google_tokens` sigue con su estructura esperada (no se tocó el esquema)**

```bash
node -e "
require('dotenv').config();
const pool = require('./src/db/pool');
(async () => {
  const t = await pool.query(\"SELECT column_name FROM information_schema.columns WHERE table_name='google_tokens' ORDER BY ordinal_position\");
  console.log('Columnas:', t.rows.map(r => r.column_name).join(', '));
  await pool.end();
})();
"
```
Expected: la misma lista de columnas de antes de empezar (`id, user_id,
access_token, refresh_token, token_type, expiry_date, scope, calendar_id,
connected_at, updated_at`) — confirma que ningún paso tocó el esquema.

- [ ] **Step 6: Reporte final al usuario (sin commit todavía)**

No ejecutar `git add`/`git commit`/`git push` — el usuario pidió esperar
autorización explícita antes de comitear. Reportar al usuario que la
implementación está lista para revisión manual en el navegador (login como
advisor/manager/directivo/marketing para ver la pestaña funcional, como
externo para ver el bloqueo, como administracion para confirmar que la
pestaña no aparece) y que el commit queda pendiente de su autorización.

---

## Resumen de archivos tocados

| Archivo | Cambio |
|---|---|
| `src/services/googleCalendar.service.js` | + 2 funciones de acceso por rol |
| `src/routes/googleCalendar.routes.js` | 4 redirects ahora incluyen `tab=integraciones` |
| `src/controllers/profile.controller.js` | calcula y pasa `calendarAllowed`/`calendarTabVisible`/`calendarConectado` |
| `views/profile/index.ejs` | nueva pestaña "Integraciones" (botón + panel + CSS + toast al volver de OAuth) |
| `views/advisor/crm/partials/sidebar.ejs` | candado 🔒 junto a "Mi calendario" para `externo` |
| `src/routes/main.routes.js` | `/advisor/crm/calendar` ya no da 403 a `externo`, renderiza tarjeta restringida |
| `views/advisor/crm/calendar.ejs` | tarjeta restringida + aviso "conecta tu calendario" (nuevo, no existía) |

**Sin cambios:** backend OAuth (`googleCalendar.service.js` más allá del
helper, rutas de conexión/desconexión), páginas de calendario de
manager/directivo, esquema de BD.
