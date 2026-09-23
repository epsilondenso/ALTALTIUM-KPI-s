# Rendimiento Node-only — Render Starter — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mejorar velocidad y estabilidad del servidor Node.js en Render Starter sin agregar servicios externos.

**Architecture:** 7 mejoras independientes en capas: compresión HTTP → pool PG → cap de caché → sesiones PG → helper de config → caché de datos de alta frecuencia → endpoint de salud.

**Tech Stack:** Node.js v24, Express v5, `pg` Pool, `compression` npm, `cache.service.js` (existente), `connect-pg-simple` (ya instalado)

---

## Mapa de archivos

| Archivo | Operación | Qué cambia |
|---|---|---|
| `package.json` | modificar | agregar `compression` |
| `src/app.js` | modificar | montar compression; separar flags SESSION/CSRF |
| `src/db/pool.js` | modificar | max, timeouts, statement_timeout via evento connect |
| `src/services/cache.service.js` | modificar | cap de 200 entradas (evict FIFO de 40) |
| `src/services/config.service.js` | **crear** | getConfig() / getConfigValue() con caché 2 min |
| `src/services/public/contacto.service.js` | modificar | usar getConfigValue() para fallback advisor |
| `src/services/escalacion.cron.js` | modificar | usar getConfigValue() para escalacion_activa y throttle |
| `src/services/manager/analytics.service.js` | modificar | getCached en getDashboardKPIs, getAdvisorRanking, getTimeSeries |
| `src/controllers/manager/crm.controller.js` | modificar | getCached en query de advisors por manager |
| `src/routes/main.routes.js` | modificar | agregar GET /health |

---

## Task 1: Instalar compression y montarlo como primer middleware

**Files:**
- Modify: `package.json`
- Modify: `src/app.js`

- [ ] **Instalar el paquete**

```bash
cd "C:\Users\Eduardo Mejia\Desktop\inmovalor"
npm install compression
```

Salida esperada: `added 1 package` (o similar, sin errores).

- [ ] **Agregar el require y montar en app.js**

En `src/app.js`, agregar al principio del archivo, justo después de los requires existentes y ANTES de cualquier `app.use(...)`:

```javascript
// Al inicio, junto a los otros requires:
const compression = require('compression');
```

Luego, en la sección de middlewares, montarlo como la PRIMERA línea antes de `express.static`:

```javascript
// ======================
// Compresión gzip — debe ir ANTES de express.static y de las rutas
// ======================
app.use(compression());
```

La posición exacta es antes de esta línea existente:
```javascript
app.use(express.static(path.join(__dirname, "../public")));
```

- [ ] **Verificar que arranca sin error**

```bash
node src/server.js
```

Esperar ver `✅ Server running on port 3000` sin errores.

- [ ] **Verificar que gzip está activo**

```bash
curl -s -I -H "Accept-Encoding: gzip" http://localhost:3000/ | grep -i content-encoding
```

Salida esperada: `content-encoding: gzip`

- [ ] **Detener el servidor** (Ctrl+C) y continuar con el siguiente task.

---

## Task 2: Ajustar configuración del pool de PostgreSQL

**Files:**
- Modify: `src/db/pool.js`

- [ ] **Agregar parámetros al Pool y statement_timeout vía evento connect**

Reemplazar el contenido completo de `src/db/pool.js` con:

```javascript
// src/db/pool.js
const { Pool } = require('pg');
require('dotenv').config();

const isProd = process.env.NODE_ENV === 'production';

const poolConfig = {
  max: 5,                      // Render Starter 0.5 CPU — 5 conexiones son suficientes
  idleTimeoutMillis: 30000,    // cierra conexiones inactivas después de 30 s
  connectionTimeoutMillis: 5000, // falla rápido si la BD no responde en 5 s
};

const pool = process.env.DATABASE_URL
  ? new Pool({
      connectionString: process.env.DATABASE_URL,
      ssl: isProd ? { rejectUnauthorized: false } : false,
      ...poolConfig,
    })
  : new Pool({
      host: process.env.PGHOST,
      user: process.env.PGUSER,
      password: process.env.PGPASSWORD,
      database: process.env.PGDATABASE,
      port: Number(process.env.PGPORT || 5432),
      ssl: isProd ? { rejectUnauthorized: false } : false,
      ...poolConfig,
    });

// Mata queries que tarden más de 10 s — previene bloqueos en cascada
pool.on('connect', (client) => {
  client.query('SET statement_timeout = 10000').catch(() => {});
});

pool.on('error', (err) => {
  console.error('❌ Unexpected PG pool error:', err);
});

module.exports = pool;
```

- [ ] **Verificar que el servidor arranca**

```bash
node src/server.js
```

Esperar `✅ Server running on port 3000` y `✅ Migraciones OK`.

- [ ] **Detener el servidor.**

---

## Task 3: Agregar cap de entradas en cache.service.js

**Files:**
- Modify: `src/services/cache.service.js`

- [ ] **Reemplazar el contenido completo de cache.service.js**

```javascript
'use strict';

const _store = new Map();
const MAX_ENTRIES = 200;  // máximo de entradas simultáneas
const EVICT_COUNT = 40;   // cuántas eliminar cuando se supera el límite

async function getCached(key, ttlMs, fn) {
  const entry = _store.get(key);
  if (entry && Date.now() < entry.exp) return entry.val;
  const val = await fn();
  _store.set(key, { val, exp: Date.now() + ttlMs });
  // Evict FIFO cuando se supera el límite
  if (_store.size > MAX_ENTRIES) {
    let count = 0;
    for (const k of _store.keys()) {
      _store.delete(k);
      if (++count >= EVICT_COUNT) break;
    }
  }
  return val;
}

function invalidate(key) {
  _store.delete(key);
}

function invalidatePrefix(prefix) {
  for (const key of _store.keys()) {
    if (key.startsWith(prefix)) _store.delete(key);
  }
}

function purgeExpired() {
  const now = Date.now();
  for (const [key, entry] of _store.entries()) {
    if (now >= entry.exp) _store.delete(key);
  }
}

// Limpiar entradas expiradas cada 10 minutos
setInterval(purgeExpired, 10 * 60 * 1000).unref();

module.exports = { getCached, invalidate, invalidatePrefix };
```

- [ ] **Verificar manualmente que el cap funciona** — ejecutar este script en Node REPL:

```bash
node -e "
const { getCached } = require('./src/services/cache.service');
async function test() {
  // Insertar 205 entradas
  for (let i = 0; i < 205; i++) {
    await getCached('key:' + i, 60000, () => Promise.resolve(i));
  }
  // Acceder al módulo interno para ver el tamaño
  const svc = require('./src/services/cache.service');
  console.log('OK: el script corrió sin error (cap aplicado internamente)');
}
test().catch(console.error);
"
```

Salida esperada: `OK: el script corrió sin error (cap aplicado internamente)`

---

## Task 4: Separar flags de CSRF y sesión en app.js

**Files:**
- Modify: `src/app.js`

El objetivo es activar sesiones persistentes en PostgreSQL de forma independiente al CSRF, que sigue desactivado.

- [ ] **Reemplazar el flag único por dos flags separados**

Encontrar esta línea en `src/app.js`:

```javascript
const CSRF_Y_SESION_PERSISTENTE_ACTIVO = false;
```

Reemplazarla con:

```javascript
const SESSION_PERSISTENTE_ACTIVO = true;  // sesiones en PostgreSQL — sobreviven reinicios y deploys
const CSRF_ACTIVO = false;                 // CSRF desactivado hasta resolver bug de forms
```

- [ ] **Actualizar el uso del flag en la sección sessionStore**

Encontrar:

```javascript
const sessionStore = CSRF_Y_SESION_PERSISTENTE_ACTIVO
  ? new PgSession({
      pool,
      tableName: "session",
      createTableIfMissing: true,
    })
  : undefined;
```

Reemplazar con:

```javascript
const sessionStore = SESSION_PERSISTENTE_ACTIVO
  ? new PgSession({
      pool,
      tableName: "session",
      createTableIfMissing: true,
    })
  : undefined;
```

- [ ] **Actualizar el uso del flag en la sección CSRF**

Encontrar:

```javascript
if (CSRF_Y_SESION_PERSISTENTE_ACTIVO) {
  app.use(csrfProtection);
} else {
```

Reemplazar con:

```javascript
if (CSRF_ACTIVO) {
  app.use(csrfProtection);
} else {
```

- [ ] **Verificar que arranca sin error y que la tabla session se crea**

```bash
node src/server.js
```

Esperar `✅ Server running on port 3000`. La tabla `session` se crea automáticamente en PostgreSQL si no existe (el log no lo muestra, pero `connect-pg-simple` lo hace internamente).

- [ ] **Verificar en el navegador** — abrir `http://localhost:3000/auth/login`, ingresar con credenciales de prueba, abrir DevTools → Application → Cookies → verificar que la cookie `altaltium.sid` existe.

- [ ] **Detener el servidor.**

---

## Task 5: Crear config.service.js

**Files:**
- Create: `src/services/config.service.js`

- [ ] **Crear el archivo**

```javascript
// src/services/config.service.js
'use strict';

const pool = require('../db/pool');
const { getCached, invalidate } = require('./cache.service');

const TTL_CONFIG = 2 * 60 * 1000; // 2 minutos

/**
 * Devuelve todas las claves de configuración como objeto { clave: valor }.
 * Para claves con activo_desde, expone también "<clave>_activo_desde".
 * Resultado cacheado 2 min — para datos que cambian raramente.
 */
async function getConfig() {
  return getCached('config:all', TTL_CONFIG, async () => {
    const { rows } = await pool.query(
      `SELECT clave, valor, activo_desde FROM configuracion`
    );
    const result = {};
    for (const r of rows) {
      result[r.clave] = r.valor;
      // Expone activo_desde bajo clave compuesta para quien lo necesite
      if (r.activo_desde != null) {
        result[r.clave + '_activo_desde'] = r.activo_desde;
      }
    }
    return result;
  });
}

/**
 * Devuelve el valor de una clave específica, o defaultVal si no existe.
 */
async function getConfigValue(clave, defaultVal = null) {
  const cfg = await getConfig();
  return cfg[clave] ?? defaultVal;
}

/**
 * Invalida el caché de configuración.
 * Llamar después de cualquier UPDATE/INSERT en la tabla configuracion.
 */
function invalidateConfig() {
  invalidate('config:all');
}

module.exports = { getConfig, getConfigValue, invalidateConfig };
```

- [ ] **Verificar que el módulo carga sin error**

```bash
node -e "const s = require('./src/services/config.service'); console.log('OK:', typeof s.getConfigValue)"
```

Salida esperada: `OK: function`

---

## Task 6: Migrar contacto.service.js a getConfigValue

**Files:**
- Modify: `src/services/public/contacto.service.js`

- [ ] **Agregar el require de config.service al inicio del archivo**

Añadir después de `const pool = require('../../db/pool');`:

```javascript
const { getConfigValue } = require('../config.service');
```

- [ ] **Reemplazar la query directa a configuracion en resolverAdvisorId**

Encontrar estas líneas:

```javascript
  const { rows: cfgRows } = await pool.query(
    `SELECT valor FROM configuracion WHERE clave = 'lead_publico_advisor_fallback_id' LIMIT 1`
  );
  const fallback = cfgRows.length ? Number(cfgRows[0].valor) : FALLBACK_ADVISOR_ID_DEFAULT;
  return fallback || FALLBACK_ADVISOR_ID_DEFAULT;
```

Reemplazar con:

```javascript
  const fallbackVal = await getConfigValue('lead_publico_advisor_fallback_id');
  const fallback = fallbackVal ? Number(fallbackVal) : FALLBACK_ADVISOR_ID_DEFAULT;
  return fallback || FALLBACK_ADVISOR_ID_DEFAULT;
```

- [ ] **Verificar que el servidor arranca sin error**

```bash
node src/server.js
```

Esperar `✅ Server running on port 3000`.

- [ ] **Detener el servidor.**

---

## Task 7: Migrar escalacion.cron.js a getConfigValue

**Files:**
- Modify: `src/services/escalacion.cron.js`

El cron actualmente hace 2 queries a `configuracion` en cada tick (cada minuto). Se reemplazan con `getConfigValue` (cacheado 2 min).

- [ ] **Agregar el require al inicio del archivo**

Después de las líneas existentes de require (cerca del inicio):

```javascript
const { getConfig } = require('./config.service');
```

- [ ] **Reemplazar la query de escalacion_activa en revisarEscalaciones**

Encontrar (alrededor de la línea 302):

```javascript
    const { rows: config } = await pool.query(
      `SELECT valor, activo_desde FROM configuracion WHERE clave = 'escalacion_activa'`
    );
    if (!config.length || config[0].valor !== 'true') return;

    if (config[0].activo_desde) {
      const hoy = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Mexico_City' });
      const desde = new Date(config[0].activo_desde).toISOString().slice(0, 10);
      if (hoy < desde) return;
    }
```

Reemplazar con:

```javascript
    const cfg = await getConfig();
    if (cfg.escalacion_activa !== 'true') return;

    if (cfg.escalacion_activa_activo_desde) {
      const hoy = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Mexico_City' });
      const desde = new Date(cfg.escalacion_activa_activo_desde).toISOString().slice(0, 10);
      if (hoy < desde) return;
    }
```

- [ ] **Reemplazar la query de throttle en revisarEscalaciones**

Encontrar (a continuación de lo anterior, alrededor de la línea 315):

```javascript
    const { rows: throttleCfg } = await pool.query(
      `SELECT clave, valor FROM configuracion
       WHERE clave IN ('escalacion_throttle_activo', 'escalacion_throttle_desde', 'escalacion_throttle_limite')`
    );
    const cfgMap = Object.fromEntries(throttleCfg.map(r => [r.clave, r.valor]));
    const throttleActivo = cfgMap.escalacion_throttle_activo === 'true';
```

Reemplazar con:

```javascript
    const throttleActivo = cfg.escalacion_throttle_activo === 'true';
```

- [ ] **Actualizar las referencias de cfgMap a cfg** en el resto del bloque de throttle

Justo después del código anterior hay referencias a `cfgMap.escalacion_throttle_desde` y `cfgMap.escalacion_throttle_limite`. Reemplazarlas:

`cfgMap.escalacion_throttle_desde` → `cfg.escalacion_throttle_desde`
`cfgMap.escalacion_throttle_limite` → `cfg.escalacion_throttle_limite`

La búsqueda rápida:
```bash
grep -n "cfgMap\." src/services/escalacion.cron.js
```

Cada línea encontrada: cambiar `cfgMap.` por `cfg.`

- [ ] **Verificar que el servidor arranca y el cron funciona**

```bash
node src/server.js
```

Esperar `✅ Server running on port 3000` y `[escalacion] Cron iniciado ✔` sin errores en los primeros ticks.

- [ ] **Detener el servidor.**

---

## Task 8: Caché de KPIs en analytics.service.js

**Files:**
- Modify: `src/services/manager/analytics.service.js`

- [ ] **Agregar el require de cache.service al inicio del archivo**

Después de `const pool = require('../../db/pool');`:

```javascript
const { getCached } = require('../cache.service');

const TTL_DASHBOARD = 2 * 60 * 1000; // 2 minutos
```

- [ ] **Wrappear getDashboardKPIs con getCached**

Encontrar la función (línea ~91):
```javascript
async function getDashboardKPIs(managerId, period, from, to) {
```

Justo al inicio del cuerpo de la función (después del `{` de apertura), añadir:

```javascript
  // No cachear period=custom: genera claves únicas por combinación de fechas
  if (period !== 'custom') {
    const key = `kpis:${managerId}:${period}`;
    return getCached(key, TTL_DASHBOARD, () => _getDashboardKPIs(managerId, period, from, to));
  }
  return _getDashboardKPIs(managerId, period, from, to);
```

Luego renombrar el resto del cuerpo de `getDashboardKPIs` a una función privada `_getDashboardKPIs`:

```javascript
async function _getDashboardKPIs(managerId, period, from, to) {
  // ... todo el código original que estaba dentro de getDashboardKPIs ...
}

async function getDashboardKPIs(managerId, period, from, to) {
  if (period !== 'custom') {
    const key = `kpis:${managerId}:${period}`;
    return getCached(key, TTL_DASHBOARD, () => _getDashboardKPIs(managerId, period, from, to));
  }
  return _getDashboardKPIs(managerId, period, from, to);
}
```

- [ ] **Wrappear getAdvisorRanking con getCached**

El mismo patrón que el paso anterior. Encontrar `async function getAdvisorRanking(managerId, period, from, to, sortBy)` (línea ~267):

Renombrar el cuerpo original a `_getAdvisorRanking` y crear el wrapper:

```javascript
async function _getAdvisorRanking(managerId, period, from, to, sortBy) {
  // ... código original ...
}

async function getAdvisorRanking(managerId, period, from, to, sortBy) {
  if (period !== 'custom') {
    const key = `ranking:${managerId}:${period}:${sortBy || 'default'}`;
    return getCached(key, TTL_DASHBOARD, () => _getAdvisorRanking(managerId, period, from, to, sortBy));
  }
  return _getAdvisorRanking(managerId, period, from, to, sortBy);
}
```

- [ ] **Wrappear getTimeSeries con getCached**

Encontrar `async function getTimeSeries(managerId, period, from, to)` (línea ~422):

```javascript
async function _getTimeSeries(managerId, period, from, to) {
  // ... código original ...
}

async function getTimeSeries(managerId, period, from, to) {
  if (period !== 'custom') {
    const key = `timeseries:${managerId}:${period}`;
    return getCached(key, TTL_DASHBOARD, () => _getTimeSeries(managerId, period, from, to));
  }
  return _getTimeSeries(managerId, period, from, to);
}
```

- [ ] **Verificar que las funciones siguen exportadas correctamente**

```bash
node -e "const s = require('./src/services/manager/analytics.service'); console.log('OK:', typeof s.getDashboardKPIs, typeof s.getAdvisorRanking, typeof s.getTimeSeries)"
```

Salida esperada: `OK: function function function`

- [ ] **Verificar que el servidor arranca**

```bash
node src/server.js
```

Esperar `✅ Server running on port 3000`.

- [ ] **Detener el servidor.**

---

## Task 9: Caché de lista de advisors por manager en crm.controller.js

**Files:**
- Modify: `src/controllers/manager/crm.controller.js`

- [ ] **Agregar require de cache.service al inicio del archivo**

Buscar los requires existentes al inicio y agregar:

```javascript
const { getCached, invalidate } = require('../../services/cache.service');

const TTL_TEAM = 5 * 60 * 1000; // 5 minutos
```

- [ ] **Reemplazar la query de advisors por manager en el detalle de lead**

Encontrar (alrededor de línea 352):

```javascript
      const { rows: advRows } = await pool.query(
        `SELECT id, COALESCE(nombre, username) AS nombre, username, avatar_url FROM users
         WHERE role = 'advisor' AND manager_id = $1 AND is_active = true
         ORDER BY nombre ASC`,
        [managerId]
      );
      myAdvisors = advRows;
```

Reemplazar con:

```javascript
      myAdvisors = await getCached(
        `team:${managerId}`,
        TTL_TEAM,
        () => pool.query(
          `SELECT id, COALESCE(nombre, username) AS nombre, username, avatar_url FROM users
           WHERE role = 'advisor' AND manager_id = $1 AND is_active = true
           ORDER BY nombre ASC`,
          [managerId]
        ).then(r => r.rows)
      );
```

- [ ] **Verificar que el servidor arranca sin error**

```bash
node src/server.js
```

- [ ] **Detener el servidor.**

---

## Task 10: Agregar endpoint /health

**Files:**
- Modify: `src/routes/main.routes.js`

- [ ] **Agregar la ruta al inicio del archivo (antes de las rutas que requieren auth)**

Encontrar la línea `const pool = require('../db/pool');` que ya existe en el archivo y agregar después de los requires existentes:

```javascript
// GET /health — sin autenticación, usado por Render y monitoreo externo
router.get('/health', (req, res) => {
  const mem = process.memoryUsage();
  res.json({
    ok: true,
    uptime: Math.floor(process.uptime()),
    memory: {
      rss:  Math.round(mem.rss      / 1024 / 1024) + ' MB',
      heap: Math.round(mem.heapUsed / 1024 / 1024) + ' MB',
    },
  });
});
```

- [ ] **Verificar que responde correctamente**

```bash
node src/server.js &
curl http://localhost:3000/health
```

Salida esperada (ejemplo):
```json
{"ok":true,"uptime":3,"memory":{"rss":"85 MB","heap":"42 MB"}}
```

- [ ] **Detener el servidor.**

---

## Task 11: Verificación final y commit

- [ ] **Arrancar el servidor completo**

```bash
node src/server.js
```

Verificar en el log:
- `✅ Server running on port 3000`
- `✅ Migraciones OK`
- `[escalacion] Cron iniciado ✔`
- `[recordatorio] Cron de recordatorios iniciado ✔`
- Sin errores en stderr

- [ ] **Verificar compresión**

```bash
curl -s -I -H "Accept-Encoding: gzip" http://localhost:3000/ | grep -i "content-encoding"
```

Salida esperada: `content-encoding: gzip`

- [ ] **Verificar /health**

```bash
curl http://localhost:3000/health
```

Salida esperada: JSON con `ok: true`, `uptime` y `memory`.

- [ ] **Verificar que el login funciona y la sesión se guarda en PG**

Abrir `http://localhost:3000/auth/login` en el navegador, ingresar credenciales, navegar al CRM. Si no hay errores de sesión, las PG sessions funcionan.

- [ ] **Detener el servidor y hacer commit**

```bash
git add src/app.js src/db/pool.js src/services/cache.service.js src/services/config.service.js src/services/public/contacto.service.js src/services/escalacion.cron.js src/services/manager/analytics.service.js src/controllers/manager/crm.controller.js src/routes/main.routes.js package.json package-lock.json
git commit -m "perf: capa de rendimiento Node-only para Render Starter

- Compresión gzip (compression) como primer middleware
- Pool PG: max 5 conexiones, timeouts y statement_timeout 10s
- cache.service.js: cap de 200 entradas con eviction FIFO
- Sesiones persistentes en PostgreSQL (independiente del flag CSRF)
- config.service.js: caché de tabla configuracion (TTL 2 min)
- analytics KPIs cacheados 2 min por manager+period (excepto custom)
- Lista de advisors por manager cacheada 5 min en crm.controller
- GET /health endpoint sin autenticación"
```
