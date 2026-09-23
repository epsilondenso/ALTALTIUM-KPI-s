# Presencia "En Línea" de Usuarios — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mostrar un indicador visual verde/amarillo/rojo en el portal que refleje si un asesor está en línea (activo en la última hora), desconectado (última vez hace X), o nunca ha ingresado.

**Architecture:** Columna `last_seen_at TIMESTAMPTZ` en `users`, actualizada por un middleware global con throttle de 2 minutos via sesión. Un helper `formatPresencia()` convierte el timestamp a `{ dotColor, label, textColor }`. Dos partials EJS reutilizables; cada vista los incluye.

**Tech Stack:** Node.js/Express v5, PostgreSQL (`pg` pool), EJS partials

---

## Archivos a crear / modificar

| Archivo | Acción |
|---|---|
| `src/utils/presencia.js` | Nuevo — helper `formatPresencia` |
| `src/middlewares/lastSeen.js` | Nuevo — middleware throttled |
| `views/partials/presencia-dot.ejs` | Nuevo — partial del punto |
| `views/partials/presencia-label.ejs` | Nuevo — partial del texto de estado |
| `src/app.js` | Modificar — montar middleware |
| `src/controllers/directivo/asesores.controller.js` | Modificar — agregar `last_seen_at` + `presencia` |
| `views/directivo/asesores/index.ejs` | Modificar — mostrar punto y label |
| `views/directivo/asesores/show.ejs` | Modificar — mostrar punto y label |
| `src/services/manager/analytics.service.js` | Modificar — agregar `last_seen_at` al ranking |
| `views/manager/dashboard.ejs` | Modificar — mostrar punto en tabla ranking |
| `src/routes/manager.routes.js` | Modificar — `getAdvisorOwnedByManager` + pasar presencia |
| `views/manager/advisors/show.ejs` | Modificar — mostrar punto y label |
| `views/manager/leads/index.ejs` | Modificar — mostrar punto y label |
| `src/controllers/admin.controller.js` | Modificar — agregar `nombre, apellidos, last_seen_at` |
| `views/admin/users/index.ejs` | Modificar — mostrar punto y label |
| `src/controllers/profile.controller.js` | Modificar — agregar query `last_seen_at` |
| `views/profile/index.ejs` | Modificar — reemplazar dot hardcodeado, agregar label |

---

### Task 1: Migración SQL — agregar columna `last_seen_at`

**Files:**
- Modify: base de datos vía psql/Render dashboard

- [ ] **Step 1: Ejecutar la migración en la BD**

Conéctate a la BD (Render dashboard → psql, o `.env` local) y ejecuta:

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen_at);
```

- [ ] **Step 2: Verificar**

```sql
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'users' AND column_name = 'last_seen_at';
```

Resultado esperado: una fila con `last_seen_at` y `timestamp with time zone`.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: add last_seen_at column to users table"
```

---

### Task 2: Helper `formatPresencia`

**Files:**
- Create: `src/utils/presencia.js`

- [ ] **Step 1: Crear el archivo**

```javascript
// src/utils/presencia.js
'use strict';

const CDMX = 'America/Mexico_City';

function formatPresencia(last_seen_at) {
  if (!last_seen_at) {
    return {
      color: 'red',
      dotColor: '#ef4444',
      label: 'Nunca ha ingresado',
      textColor: '#ef4444',
    };
  }

  const now  = Date.now();
  const last = new Date(last_seen_at).getTime();
  const diffMs    = now - last;
  const diffMin   = diffMs / 60_000;
  const diffHours = diffMs / 3_600_000;
  const diffDays  = diffMs / 86_400_000;

  if (diffMin < 60) {
    return {
      color: 'green',
      dotColor: '#22c55e',
      label: 'En línea ahora',
      textColor: '#16a34a',
    };
  }

  // Amarillo — desconectado
  let label;
  if (diffHours < 2) {
    label = 'Última vez hace 1 hora';
  } else if (diffHours < 24) {
    label = `Última vez hace ${Math.floor(diffHours)} horas`;
  } else if (diffDays < 2) {
    const hora = new Date(last_seen_at).toLocaleTimeString('es-MX', {
      hour: '2-digit', minute: '2-digit', hour12: true, timeZone: CDMX,
    });
    label = `Última vez ayer, ${hora}`;
  } else if (diffDays < 7) {
    const dia = new Date(last_seen_at).toLocaleDateString('es-MX', {
      weekday: 'long', timeZone: CDMX,
    });
    label = `Última vez el ${dia}`;
  } else {
    const fecha = new Date(last_seen_at).toLocaleDateString('es-MX', {
      day: 'numeric', month: 'short', timeZone: CDMX,
    });
    label = `Última vez el ${fecha}`;
  }

  return {
    color: 'yellow',
    dotColor: '#eab308',
    label,
    textColor: '#a16207',
  };
}

module.exports = { formatPresencia };
```

- [ ] **Step 2: Verificar manualmente (opcional, en node REPL)**

```bash
node -e "
const { formatPresencia } = require('./src/utils/presencia');
console.log(formatPresencia(null));                      // rojo
console.log(formatPresencia(new Date()));                // verde
console.log(formatPresencia(new Date(Date.now() - 2*3600*1000))); // amarillo 2h
"
```

Salida esperada: tres objetos con `color` `red`, `green`, `yellow` respectivamente.

- [ ] **Step 3: Commit**

```bash
git add src/utils/presencia.js
git commit -m "feat: add formatPresencia helper utility"
```

---

### Task 3: Middleware `lastSeen`

**Files:**
- Create: `src/middlewares/lastSeen.js`

- [ ] **Step 1: Crear el middleware**

```javascript
// src/middlewares/lastSeen.js
'use strict';

const pool = require('../db/pool');

const THROTTLE_MS = 2 * 60 * 1000; // 2 minutos

module.exports = function lastSeen(req, res, next) {
  const userId = req.session?.user?.id;
  if (userId) {
    const now  = Date.now();
    const last = req.session._lastSeenWritten || 0;
    if (now - last > THROTTLE_MS) {
      req.session._lastSeenWritten = now;
      pool.query('UPDATE users SET last_seen_at = NOW() WHERE id = $1', [userId])
        .catch(err => console.error('[lastSeen] UPDATE error:', err?.message));
    }
  }
  next();
};
```

- [ ] **Step 2: Commit**

```bash
git add src/middlewares/lastSeen.js
git commit -m "feat: add lastSeen middleware with 2-minute throttle"
```

---

### Task 4: Montar middleware en `app.js`

**Files:**
- Modify: `src/app.js`

- [ ] **Step 1: Agregar el require y el `app.use`**

En `src/app.js`, localiza el bloque de middleware global (alrededor de la línea 77, después de `app.use(attachCurrentUser)`). Agrega las dos líneas marcadas con `// +`:

```javascript
// ======================
// Middleware global (tuyo)
// ======================
const { attachCurrentUser } = require("./middlewares/auth.middleware");
app.use(attachCurrentUser);

// + Presencia: actualiza last_seen_at en BD con throttle 2 min
const lastSeenMiddleware = require("./middlewares/lastSeen");  // +
app.use(lastSeenMiddleware);                                    // +
```

- [ ] **Step 2: Verificar que el servidor arranca sin errores**

```bash
node src/server.js
```

Debe imprimir el mensaje de inicio normal sin errores. Ctrl+C para detener.

- [ ] **Step 3: Commit**

```bash
git add src/app.js
git commit -m "feat: mount lastSeen middleware globally in app.js"
```

---

### Task 5: Partials EJS reutilizables

**Files:**
- Create: `views/partials/presencia-dot.ejs`
- Create: `views/partials/presencia-label.ejs`

- [ ] **Step 1: Crear `presencia-dot.ejs`**

Este partial renderiza únicamente el punto de color. Debe ir DENTRO del `<div>` del avatar (el div wrapper debe tener `position:relative`).

Acepta dos variables locales:
- `presencia` — objeto de `formatPresencia`
- `dotSize` — (opcional) clase Tailwind de tamaño, default `'w-3 h-3'` (12px). Para el perfil usar `'w-5 h-5'`.

```ejs
<%
  /* views/partials/presencia-dot.ejs
     Variables: presencia {dotColor}, dotSize (opcional, default 'w-3 h-3') */
  const _dotSize = typeof dotSize !== 'undefined' ? dotSize : 'w-3 h-3';
%>
<div class="absolute bottom-0.5 right-0.5 <%= _dotSize %> rounded-full border-2 border-white"
     style="background:<%= presencia.dotColor %>"></div>
```

- [ ] **Step 2: Crear `presencia-label.ejs`**

Renderiza la línea de texto de estado debajo del nombre.

```ejs
<%
  /* views/partials/presencia-label.ejs
     Variables: presencia {label, textColor} */
%>
<div class="text-[11px] leading-tight mt-0.5" style="color:<%= presencia.textColor %>"><%= presencia.label %></div>
```

- [ ] **Step 3: Commit**

```bash
git add views/partials/presencia-dot.ejs views/partials/presencia-label.ejs
git commit -m "feat: add presencia-dot and presencia-label EJS partials"
```

---

### Task 6: Directivo — lista de asesores

**Files:**
- Modify: `src/controllers/directivo/asesores.controller.js`
- Modify: `views/directivo/asesores/index.ejs`

- [ ] **Step 1: Agregar `formatPresencia` al controlador y `last_seen_at` al SELECT**

En `src/controllers/directivo/asesores.controller.js`, al inicio del archivo, agrega el require:

```javascript
// Al inicio, después de los otros requires:
const { formatPresencia } = require('../../utils/presencia');
```

En la función `asesoresIndex`, localiza el SELECT de `asesores` (línea ~36). Agrega `u.last_seen_at` al SELECT:

```sql
-- Cambio: agregar u.last_seen_at a la lista de columnas del SELECT de users u
SELECT
  u.id,
  u.nombre,
  u.apellidos,
  u.username,
  u.email,
  u.telefono,
  u.avatar_url,
  u.is_active,
  u.manager_id,
  u.last_seen_at,   -- NUEVA LÍNEA
  COALESCE(m.nombre || ' ' || COALESCE(m.apellidos,''), m.username, '—') AS manager_name,
  ...  (resto igual)
```

Después de obtener `rows: asesores`, mapea para agregar `presencia`:

```javascript
// Localiza: return res.render('directivo/asesores/index', {
// Justo antes, agrega:
const asesoresConPresencia = asesores.map(a => ({
  ...a,
  presencia: formatPresencia(a.last_seen_at),
}));
```

Y cambia el render para pasar `asesoresConPresencia`:

```javascript
return res.render('directivo/asesores/index', {
  layout:      false,
  title:       'Asesores | Directivo | Altaltium',
  currentPath: req.path,
  currentUser: req.session.user,
  user:        req.session.user,
  asesores:    asesoresConPresencia,   // <- cambiado
  managers:    managers || [],
  q,
  manager_id:  managerFilter,
});
```

- [ ] **Step 2: Modificar la vista `views/directivo/asesores/index.ejs`**

Localiza el bloque del avatar dentro del `forEach` (alrededor de la línea 85). El wrapper del avatar actualmente es:

```html
<div class="shrink-0 w-9 h-9 rounded-full overflow-hidden bg-teal-100 flex items-center justify-center text-teal-700 font-bold text-sm">
```

Reemplaza ese bloque completo (avatar + nombre/email) por:

```html
<div class="flex items-center gap-3 min-w-0">
  <!-- Avatar con punto de presencia -->
  <div class="relative shrink-0 w-9 h-9">
    <div class="w-9 h-9 rounded-full overflow-hidden bg-teal-100 flex items-center justify-center text-teal-700 font-bold text-sm">
      <% if (a.avatar_url) { %>
        <img src="<%= a.avatar_url %>" alt="<%= initial %>"
             class="w-full h-full object-cover"
             onerror="this.style.display='none';this.parentNode.querySelector('.av-fallback').style.display='flex'">
        <span class="av-fallback hidden w-full h-full items-center justify-center"><%= initial %></span>
      <% } else { %>
        <%= initial %>
      <% } %>
    </div>
    <%- include('../../partials/presencia-dot', { presencia: a.presencia }) %>
  </div>
  <!-- Nombre + estado de presencia -->
  <div class="min-w-0">
    <div class="font-semibold text-slate-900 truncate"><%= fullName %></div>
    <%- include('../../partials/presencia-label', { presencia: a.presencia }) %>
  </div>
</div>
```

- [ ] **Step 3: Verificar en el navegador**

Inicia el servidor y abre `/directivo/asesores`. Debes ver:
- Punto verde sobre el avatar de los usuarios que ingresaron recientemente
- Punto rojo para usuarios que nunca han ingresado (todos al inicio, ya que `last_seen_at = NULL`)
- Texto de estado debajo del nombre en lugar del correo

- [ ] **Step 4: Commit**

```bash
git add src/controllers/directivo/asesores.controller.js views/directivo/asesores/index.ejs
git commit -m "feat: add presencia indicator to directivo asesores list"
```

---

### Task 7: Directivo — perfil de asesor

**Files:**
- Modify: `src/controllers/directivo/asesores.controller.js`
- Modify: `views/directivo/asesores/show.ejs`

- [ ] **Step 1: Agregar `last_seen_at` al SELECT de `asesorShow`**

En `src/controllers/directivo/asesores.controller.js`, en la función `asesorShow` (línea ~137), agrega `u.last_seen_at` al SELECT:

```sql
SELECT
  u.*,
  u.last_seen_at,   -- ya incluido por u.* pero verificar que no se omita
  COALESCE(m.nombre || ' ' || COALESCE(m.apellidos,''), m.username, '—') AS manager_name,
  m.email AS manager_email
FROM users u
LEFT JOIN users m ON m.id = u.manager_id
WHERE u.id = $1 AND u.role = 'advisor'
LIMIT 1
```

> Nota: `u.*` ya incluye `last_seen_at`. Solo verificar que no haya un SELECT explícito de columnas que lo excluya.

Antes del `res.render`, calcula la presencia:

```javascript
const presencia = formatPresencia(asesor.last_seen_at);

return res.render('directivo/asesores/show', {
  // ... resto igual ...
  asesor,
  presencia,   // NUEVA
  // ...
});
```

- [ ] **Step 2: Modificar `views/directivo/asesores/show.ejs`**

Localiza la cabecera del asesor (línea ~33). Actualmente muestra:
```html
<h1 class="text-2xl font-semibold text-slate-900 mt-1"><%= nombre %></h1>
<p class="text-sm text-slate-500 mt-1">
  Gerente: <span class="font-semibold text-slate-700"><%= A.manager_name || '—' %></span>
  · <%= A.email || '—' %>
</p>
```

Agrega el indicador de presencia. Reemplaza ese bloque por:

```html
<div class="flex items-center gap-3 mt-1 mb-1">
  <div class="relative">
    <% if (A.avatar_url) { %>
      <img src="<%= A.avatar_url %>" class="w-12 h-12 rounded-full object-cover border-2 border-white shadow-sm">
    <% } else { %>
      <div class="w-12 h-12 rounded-full bg-teal-100 flex items-center justify-center text-teal-700 font-bold text-lg border-2 border-white shadow-sm">
        <%= nombre.charAt(0).toUpperCase() %>
      </div>
    <% } %>
    <%- include('../../partials/presencia-dot', { presencia, dotSize: 'w-3.5 h-3.5' }) %>
  </div>
  <div>
    <h1 class="text-2xl font-semibold text-slate-900"><%= nombre %></h1>
    <div class="flex items-center gap-3 mt-0.5 flex-wrap">
      <span class="text-sm text-slate-500">Gerente: <span class="font-semibold text-slate-700"><%= A.manager_name || '—' %></span></span>
      <span class="text-slate-300">·</span>
      <%- include('../../partials/presencia-label', { presencia }) %>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Verificar en el navegador**

Abre `/directivo/asesores/:id` (cualquier asesor). Verifica que el encabezado muestre avatar con punto de color y el estado de presencia.

- [ ] **Step 4: Commit**

```bash
git add src/controllers/directivo/asesores.controller.js views/directivo/asesores/show.ejs
git commit -m "feat: add presencia indicator to directivo asesor profile"
```

---

### Task 8: Manager — ranking en dashboard

**Files:**
- Modify: `src/services/manager/analytics.service.js`
- Modify: `views/manager/dashboard.ejs`

- [ ] **Step 1: Agregar `last_seen_at` al CTE `base` en `getAdvisorRanking`**

En `src/services/manager/analytics.service.js`, función `getAdvisorRanking` (línea ~242). El CTE `base` actualmente selecciona:

```sql
WITH base AS (
  SELECT
    u.id AS advisor_id,
    u.nombre, u.apellidos, u.email, u.avatar_url, u.role,
    u.is_active AS advisor_activo
  FROM users u
  WHERE u.id = ANY($1::bigint[])
),
```

Agrega `u.last_seen_at`:

```sql
WITH base AS (
  SELECT
    u.id AS advisor_id,
    u.nombre, u.apellidos, u.email, u.avatar_url, u.role,
    u.is_active AS advisor_activo,
    u.last_seen_at                          -- NUEVA LÍNEA
  FROM users u
  WHERE u.id = ANY($1::bigint[])
),
```

También agrega `b.last_seen_at` al SELECT del CTE `stats` (busca la línea donde se selecciona `b.advisor_id, b.nombre, b.apellidos, ...`):

```sql
stats AS (
  SELECT
    b.advisor_id,
    b.nombre, b.apellidos, b.email, b.avatar_url, b.role,
    b.advisor_activo,
    b.last_seen_at,                         -- NUEVA LÍNEA
    ...
```

- [ ] **Step 2: Agregar `formatPresencia` en `dashboard.controller.js`**

En `src/controllers/manager/dashboard.controller.js`, agrega el require al inicio:

```javascript
const { formatPresencia } = require('../../utils/presencia');
```

En `showDashboard`, después de obtener `ranking`, mapea para agregar `presencia`:

```javascript
const rankingConPresencia = (ranking || []).map(a => ({
  ...a,
  presencia: formatPresencia(a.last_seen_at),
}));
```

En el `res.render`, cambia `ranking` por `rankingConPresencia`:

```javascript
res.render('manager/dashboard', {
  // ...
  ranking: rankingConPresencia,   // <- cambiado
  // ...
});
```

- [ ] **Step 3: Modificar `views/manager/dashboard.ejs` — tabla de ranking**

Localiza el bloque del avatar dentro del forEach del ranking (línea ~442):

```html
<div class="avatar-cell">
  <div class="avatar-img">
    <% if (a.avatar_url) { %>
      <img src="<%= a.avatar_url %>" alt="<%= a.nombre %>" onerror="this.style.display='none'">
    <% } else { %>
      <%= initials.toUpperCase() %>
    <% } %>
  </div>
  <span><%= a.nombre %> <%= a.apellidos %></span>
</div>
```

Reemplaza por:

```html
<div class="avatar-cell">
  <div style="position:relative;flex-shrink:0">
    <div class="avatar-img">
      <% if (a.avatar_url) { %>
        <img src="<%= a.avatar_url %>" alt="<%= a.nombre %>" onerror="this.style.display='none'">
      <% } else { %>
        <%= initials.toUpperCase() %>
      <% } %>
    </div>
    <div style="position:absolute;bottom:0;right:0;width:9px;height:9px;border-radius:50%;border:2px solid white;background:<%= a.presencia.dotColor %>"></div>
  </div>
  <span><%= a.nombre %> <%= a.apellidos %></span>
</div>
```

> Nota: El ranking usa CSS inline (no Tailwind) por coherencia con el estilo existente de esa vista. El punto es 9px para no saturar la tabla densa.

- [ ] **Step 4: Agregar estilo `position:relative` al `.avatar-img` en el mismo archivo**

En el bloque `<style>` del dashboard (busca `.avatar-img{`):

```css
.avatar-img{width:28px;height:28px;border-radius:50%;background:#0f766e;color:#fff;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;flex-shrink:0;overflow:hidden}
```

No es necesario cambiar nada aquí — el wrapper externo (`div style="position:relative"`) maneja el posicionamiento del punto.

- [ ] **Step 5: Verificar en el navegador**

Abre `/manager/dashboard`. La tabla de ranking debe mostrar un pequeño punto de color sobre cada avatar.

- [ ] **Step 6: Commit**

```bash
git add src/services/manager/analytics.service.js src/controllers/manager/dashboard.controller.js views/manager/dashboard.ejs
git commit -m "feat: add presencia indicator to manager dashboard ranking"
```

---

### Task 9: Manager — supervisión del asesor (show)

**Files:**
- Modify: `src/routes/manager.routes.js`
- Modify: `views/manager/advisors/show.ejs`

- [ ] **Step 1: Agregar `last_seen_at` a `getAdvisorOwnedByManager`**

En `src/routes/manager.routes.js`, función `getAdvisorOwnedByManager` (línea ~21):

```javascript
async function getAdvisorOwnedByManager(advisorId, managerId) {
  const { rows } = await pool.query(
    `SELECT id, nombre, apellidos, username, telefono, email, role,
            is_active, area, avatar_url, manager_id, created_at,
            last_seen_at                                              -- NUEVA LÍNEA
     FROM users
     WHERE id = $1 AND role = 'advisor' AND manager_id = $2
     LIMIT 1`,
    [advisorId, managerId]
  );
  return rows[0] || null;
}
```

- [ ] **Step 2: Pasar `presencia` al render de `advisors/show`**

En el mismo archivo, localiza `return res.render("manager/advisors/show", {` (línea ~406). Agrega:

```javascript
// Al inicio del archivo agregar:
const { formatPresencia } = require('../utils/presencia');

// En el render:
return res.render("manager/advisors/show", {
  layout: false,
  title: "Supervisión · Advisor | Altaltium",
  advisor,
  presencia: formatPresencia(advisor.last_seen_at),   // NUEVA LÍNEA
  currentUser,
  currentPath: req.path,
  stats: { ...stats, conversion_close, conversion_paid, score },
  charts,
  last_activity_at,
  period: range,
  from: req.query.from || '',
  to: req.query.to || '',
});
```

- [ ] **Step 3: Modificar `views/manager/advisors/show.ejs`**

Localiza el bloque `.avRow` con la clase `.av` (alrededor de la línea 130 en el `<style>` y usada más abajo en el HTML). Busca en el HTML del archivo el uso de `.avRow` y `.av`:

```html
<div class="avRow">
  <div class="av">
    <% if (advisor.avatar_url) { %><img src="..."><% } else { %><%= initials(fullName) %><% } %>
  </div>
  ...
</div>
```

Reemplaza por (agrega wrapper `position:relative` y el punto):

```html
<div class="avRow">
  <div style="position:relative;flex-shrink:0">
    <div class="av">
      <% if (advisor.avatar_url) { %>
        <img src="<%= advisor.avatar_url %>" alt="<%= fullName %>">
      <% } else { %>
        <%= initials(fullName) %>
      <% } %>
    </div>
    <div style="position:absolute;bottom:1px;right:1px;width:13px;height:13px;border-radius:50%;border:2.5px solid white;background:<%= presencia.dotColor %>"></div>
  </div>
  <div>
    <div class="big"><%= fullName %></div>
    <div class="small" style="color:<%= presencia.textColor %>"><%= presencia.label %></div>
  </div>
</div>
```

- [ ] **Step 4: Verificar en el navegador**

Abre `/manager/advisors/:id`. El encabezado del asesor debe mostrar el punto y el texto de presencia.

- [ ] **Step 5: Commit**

```bash
git add src/routes/manager.routes.js views/manager/advisors/show.ejs
git commit -m "feat: add presencia indicator to manager advisor supervision"
```

---

### Task 10: Manager — bandeja de leads del asesor supervisado

**Files:**
- Modify: `views/manager/leads/index.ejs`

> El objeto `advisor` ya llega con `last_seen_at` gracias al cambio en `getAdvisorOwnedByManager` (Task 9). Solo falta pasar `presencia` al render y usarlo en la vista.

- [ ] **Step 1: Agregar `presencia` al render de `/advisors/:id/leads`**

En `src/routes/manager.routes.js`, localiza `return res.render("manager/leads/index", {` (línea ~787). Agrega:

```javascript
return res.render("manager/leads/index", {
  layout: false,
  advisor,
  presencia: formatPresencia(advisor.last_seen_at),   // NUEVA LÍNEA
  // ... resto igual ...
});
```

- [ ] **Step 2: Modificar `views/manager/leads/index.ejs`**

Localiza donde se muestra la información del asesor en el encabezado de la vista (busca `fullName` o `advisor.nombre` en el HTML). Normalmente hay un bloque tipo:

```html
<div class="avRow">
  <div class="av">...</div>
  <div>
    <div class="big"><%= fullName %></div>
    <div class="small">...</div>
  </div>
</div>
```

Aplica el mismo patrón de Task 9 — wrapper `position:relative`, punto superpuesto, y label de presencia en `.small`:

```html
<div class="avRow">
  <div style="position:relative;flex-shrink:0">
    <div class="av">
      <% if (advisor.avatar_url) { %>
        <img src="<%= advisor.avatar_url %>" alt="<%= fullName %>">
      <% } else { %>
        <%= initials(fullName) %>
      <% } %>
    </div>
    <div style="position:absolute;bottom:1px;right:1px;width:13px;height:13px;border-radius:50%;border:2.5px solid white;background:<%= presencia.dotColor %>"></div>
  </div>
  <div>
    <div class="big"><%= fullName %></div>
    <div class="small" style="color:<%= presencia.textColor %>"><%= presencia.label %></div>
  </div>
</div>
```

- [ ] **Step 3: Verificar en el navegador**

Abre `/manager/advisors/:id/leads`. El encabezado del asesor debe mostrar el indicador.

- [ ] **Step 4: Commit**

```bash
git add src/routes/manager.routes.js views/manager/leads/index.ejs
git commit -m "feat: add presencia indicator to manager advisor leads bandeja"
```

---

### Task 11: Admin — panel de usuarios

**Files:**
- Modify: `src/controllers/admin.controller.js`
- Modify: `views/admin/users/index.ejs`

- [ ] **Step 1: Agregar `nombre, apellidos, last_seen_at` al SELECT de `usersIndex`**

En `src/controllers/admin.controller.js`, función `usersIndex` (línea ~38). El SELECT actual es:

```javascript
const baseSQL = `
  SELECT id, username, email, role, is_active, area, gerente, avatar_url, created_at
  FROM users
`;
```

Cambia a:

```javascript
const baseSQL = `
  SELECT id, nombre, apellidos, username, email, role,
         is_active, area, gerente, avatar_url, created_at, last_seen_at
  FROM users
`;
```

- [ ] **Step 2: Agregar `formatPresencia` al controlador**

Al inicio de `src/controllers/admin.controller.js`:

```javascript
// Al inicio del archivo:
const { formatPresencia } = require('../utils/presencia');
```

En `usersIndex`, antes del `res.render`, mapea los usuarios:

```javascript
const usersConPresencia = rows.map(u => ({
  ...u,
  presencia: formatPresencia(u.last_seen_at),
}));

return res.render("admin/users/index", {
  users: usersConPresencia,   // <- cambiado
  currentUser: res.locals.currentUser,
  q,
});
```

- [ ] **Step 3: Modificar `views/admin/users/index.ejs`**

Busca en la vista donde se itera sobre `users` y se muestra el avatar/nombre de cada usuario (busca `u.avatar_url` o `u.username` en el HTML de la tabla).

Localiza el bloque del avatar/nombre de usuario. Agrega el wrapper `relative`, el punto, y el label. Ejemplo del patrón (adapta al HTML existente):

```html
<!-- Dentro del forEach de users -->
<td class="px-4 py-3">
  <div class="flex items-center gap-3">
    <div class="relative w-8 h-8 flex-shrink-0">
      <% if (u.avatar_url) { %>
        <img src="<%= u.avatar_url %>" class="w-8 h-8 rounded-full object-cover">
      <% } else { %>
        <div class="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center text-teal-700 font-bold text-xs">
          <%= ((u.nombre||u.username||'?')[0]).toUpperCase() %>
        </div>
      <% } %>
      <div class="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border-2 border-white"
           style="background:<%= u.presencia.dotColor %>"></div>
    </div>
    <div>
      <div class="font-medium text-sm text-slate-900">
        <%= ((u.nombre||'') + ' ' + (u.apellidos||'')).trim() || u.username %>
      </div>
      <div class="text-[11px]" style="color:<%= u.presencia.textColor %>"><%= u.presencia.label %></div>
    </div>
  </div>
</td>
```

- [ ] **Step 4: Verificar en el navegador**

Abre `/admin/users`. La tabla de usuarios debe mostrar punto y estado de presencia en cada fila.

- [ ] **Step 5: Commit**

```bash
git add src/controllers/admin.controller.js views/admin/users/index.ejs
git commit -m "feat: add presencia indicator to admin users panel"
```

---

### Task 12: Perfil propio del asesor

**Files:**
- Modify: `src/controllers/profile.controller.js`
- Modify: `views/profile/index.ejs`

- [ ] **Step 1: Leer `last_seen_at` en el controlador de perfil**

En `src/controllers/profile.controller.js`, agrega el require al inicio:

```javascript
const { formatPresencia } = require('../utils/presencia');
```

En la función `exports.index`, el `Promise.allSettled` ya incluye varias queries. Agrega una query más para `last_seen_at`:

```javascript
const [favoritosR, activityR, auditR, leadsFavR, statsR, lastSeenR] = await Promise.allSettled([
  profileService.getFavoritosByUserId(userId),
  profileService.getActivityByUserId(userId),
  profileService.getAuditByUserId(userId),
  leadFavService.getLeadsFavoritos(userId),
  pool.query(`
    SELECT
      COUNT(*) FILTER (WHERE status = 'open') AS leads_activos,
      COUNT(*) FILTER (WHERE (sale_paid = true OR sale_signed = true) AND status = 'closed') AS cierres
    FROM crm_leads
    WHERE advisor_id = $1
  `, [userId]),
  pool.query('SELECT last_seen_at FROM users WHERE id = $1', [userId]),  // NUEVA
]);

const lastSeenAt = lastSeenR.value?.rows?.[0]?.last_seen_at || null;
const presencia  = formatPresencia(lastSeenAt);
```

Pasa `presencia` al render:

```javascript
return res.render('profile/index', {
  title:          'Mi perfil',
  user,
  tab,
  presencia,          // NUEVA
  favoritos:      favoritosR.value || [],
  activity:       activityR.value  || [],
  audit:          auditR.value     || [],
  leadsFavoritos,
  stats,
});
```

- [ ] **Step 2: Modificar `views/profile/index.ejs`**

Localiza el bloque del avatar con el dot hardcodeado (línea ~44):

```html
<div class="flex-shrink-0 relative">
  <% if (user.avatar_url) { %>
  <img src="<%= user.avatar_url %>"
       class="w-20 h-20 rounded-full border-4 border-white object-cover shadow-sm">
  <% } else { %>
  <div class="w-20 h-20 rounded-full border-4 border-white bg-teal-100 flex items-center justify-center shadow-sm">
    <span class="text-2xl font-semibold text-teal-700"><%= iniciales %></span>
  </div>
  <% } %>
  <div class="absolute -bottom-1 -right-1 w-5 h-5 bg-green-400 rounded-full border-2 border-white"></div>
</div>
```

Reemplaza el dot hardcodeado (`bg-green-400`) con el dinámico:

```html
<div class="flex-shrink-0 relative">
  <% if (user.avatar_url) { %>
  <img src="<%= user.avatar_url %>"
       class="w-20 h-20 rounded-full border-4 border-white object-cover shadow-sm">
  <% } else { %>
  <div class="w-20 h-20 rounded-full border-4 border-white bg-teal-100 flex items-center justify-center shadow-sm">
    <span class="text-2xl font-semibold text-teal-700"><%= iniciales %></span>
  </div>
  <% } %>
  <%- include('../partials/presencia-dot', { presencia, dotSize: 'w-5 h-5' }) %>
</div>
```

Luego, en la sección de info del perfil (debajo del nombre), agrega el label de presencia. Busca la línea que sigue al `<h1>` con el nombre y agrega:

```html
<h1 class="text-xl font-semibold text-gray-900">
  <%= safe(user.nombre) %> <%= safe(user.apellidos) %>
</h1>
<!-- NUEVO: estado de presencia -->
<div class="mt-1">
  <%- include('../partials/presencia-label', { presencia }) %>
</div>
```

- [ ] **Step 3: Verificar en el navegador**

Inicia sesión como asesor y abre `/profile`. El avatar debe mostrar el punto dinámico (verde, ya que el middleware acaba de actualizar `last_seen_at`) y el texto "En línea ahora" debajo del nombre.

- [ ] **Step 4: Commit**

```bash
git add src/controllers/profile.controller.js views/profile/index.ejs
git commit -m "feat: add dynamic presencia indicator to user profile page"
```

---

## Verificación final

- [ ] Iniciar sesión como **asesor** → abrir `/profile` → punto verde, texto "En línea ahora"
- [ ] Iniciar sesión como **manager** → abrir `/manager/dashboard` → puntos en ranking
- [ ] Como **manager** → abrir `/manager/advisors/:id` → punto y texto en encabezado
- [ ] Como **manager** → abrir `/manager/advisors/:id/leads` → punto y texto en encabezado
- [ ] Como **directivo** → abrir `/directivo/asesores` → puntos en toda la tabla (rojos si nadie ha loggeado aún)
- [ ] Como **directivo** → abrir `/directivo/asesores/:id` → punto en perfil
- [ ] Como **admin** → abrir `/admin/users` → puntos en toda la tabla
- [ ] Cerrar sesión 70+ minutos → el punto debe cambiar de verde a amarillo (verificar haciendo UPDATE manual en BD)

```sql
-- Test: simular usuario offline (forzar last_seen_at a 2h atrás)
UPDATE users SET last_seen_at = NOW() - INTERVAL '2 hours' WHERE id = <tu_id>;
-- Recargar la página donde aparece ese usuario → debe mostrar amarillo
```

- [ ] **Commit final de verificación**

```bash
git add -A
git commit -m "feat: presence indicator complete — all views updated"
```
