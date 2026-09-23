# Spec: Capa de rendimiento Node-only — Render Starter

**Fecha:** 2026-07-15
**Estado:** Aprobado
**Stack:** Node.js v24 + Express v5 + PostgreSQL (Render Starter)
**Restricción:** Sin Redis ni servicios externos adicionales

---

## Contexto

El servidor corre en Render Starter (0.5 CPU, 512 MB RAM, siempre activo). Los problemas identificados son:

1. Las respuestas HTML no se comprimen — páginas de 100–200 KB se envían sin gzip
2. El pool de PostgreSQL usa defaults de `pg` (máx 10 conexiones) — excesivo para 0.5 CPU
3. `cache.service.js` tiene un `Map` sin límite de entradas — riesgo de OOM bajo tráfico
4. Las sesiones viven en `MemoryStore` — acumulan RAM y se pierden al reiniciar
5. Datos de acceso frecuente (configuración global, equipo por manager, KPIs) se recomputan en cada request

---

## Componentes del diseño

### 1. Compresión HTTP

**Paquete:** `compression` (npm)
**Ubicación:** `src/app.js`, montado como **primer middleware**, antes de rutas y `express.static`

```javascript
const compression = require('compression');
app.use(compression());
```

- Aplica gzip a todas las respuestas de texto (HTML, JSON, CSS, JS)
- Reducción esperada: 60–80% del tamaño de respuesta
- No requiere cambios en vistas ni controladores

---

### 2. Tuning del pool de PostgreSQL

**Archivo:** `src/db/pool.js`

Parámetros a agregar en ambas ramas del `new Pool({...})`:

| Parámetro | Valor | Motivo |
|---|---|---|
| `max` | `5` | 0.5 CPU — más de 5 conexiones no agregan velocidad |
| `idleTimeoutMillis` | `30000` | Cierra conexiones inactivas en 30 s |
| `connectionTimeoutMillis` | `5000` | Falla rápido si la BD no responde |
| `statement_timeout` | `10000` | Mata queries que tarden más de 10 s |

---

### 3. Cap de entradas en `cache.service.js`

**Archivo:** `src/services/cache.service.js`

- Constante `MAX_ENTRIES = 200`
- Al hacer `_store.set()`: si `_store.size > MAX_ENTRIES`, eliminar las 40 entradas más antiguas (las primeras en el Map, que son las de inserción más temprana — Map en JS mantiene orden de inserción)
- Garantiza consumo máximo de ~10 MB de RAM para el caché
- No modifica la API pública (`getCached`, `invalidate`, `invalidatePrefix`)

---

### 4. Sesiones persistentes en PostgreSQL (independiente del CSRF)

**Archivo:** `src/app.js`

Actualmente `CSRF_Y_SESION_PERSISTENTE_ACTIVO` controla tanto CSRF como PgSession con un solo flag. Se desacopla:

```javascript
// ANTES (un solo flag controla ambos)
const CSRF_Y_SESION_PERSISTENTE_ACTIVO = false;

// DESPUÉS (flags independientes)
const SESSION_PERSISTENTE_ACTIVO = true;   // sesiones en PG — activar ya
const CSRF_ACTIVO = false;                  // CSRF sigue desactivado hasta resolver bug
```

- `sessionStore` pasa a depender de `SESSION_PERSISTENTE_ACTIVO`
- Bloque `if (CSRF_Y_SESION_PERSISTENTE_ACTIVO) { app.use(csrfProtection) }` pasa a usar `CSRF_ACTIVO`
- La tabla `session` ya existe y se crea automáticamente con `createTableIfMissing: true`
- Resultado: sesiones sobreviven deploys y reinicios; RAM del proceso queda libre

---

### 5. Nuevo `src/services/config.service.js`

Helper que envuelve la consulta a la tabla `configuracion` con `getCached`:

```javascript
const { getCached } = require('./cache.service');
const pool = require('../db/pool');

const TTL_CONFIG = 2 * 60 * 1000; // 2 min

async function getConfig() {
  return getCached('config:all', TTL_CONFIG, async () => {
    const { rows } = await pool.query(`SELECT clave, valor FROM configuracion WHERE true`);
    return Object.fromEntries(rows.map(r => [r.clave, r.valor]));
  });
}

async function getConfigValue(clave, defaultVal = null) {
  const cfg = await getConfig();
  return cfg[clave] ?? defaultVal;
}

module.exports = { getConfig, getConfigValue };
```

Los controllers que hoy hacen `pool.query('SELECT valor FROM configuracion WHERE clave = $1', [x])` migran a `getConfigValue(x)`.

**Controladores candidatos a migrar** (los que más consultan `configuracion`):
- `src/services/escalacion.cron.js` — consulta `escalacion_activa`, `escalacion_throttle_*`
- `src/controllers/public/propiedad.controller.js` — `lead_publico_advisor_fallback_id`
- `src/controllers/public/microsite.controller.js` — `wa_business_outlet_folder_id` (ya está dentro del getCached de infografías, se mantiene así)

---

### 6. Caché de lista de equipo por manager

**Archivo:** `src/controllers/manager/crm.controller.js` (y cualquier controller que liste advisors del manager)

```javascript
const { getCached } = require('../../services/cache.service');
const TTL_TEAM = 5 * 60 * 1000; // 5 min

const advisors = await getCached(
  `team:${managerId}`,
  TTL_TEAM,
  () => pool.query(`SELECT id, nombre, apellidos FROM users WHERE manager_id = $1 AND is_active = true`, [managerId])
    .then(r => r.rows)
);
```

- TTL de 5 min: los cambios de equipo (alta/baja de advisors) se reflejan en máximo 5 min
- Invalidación explícita al cambiar `is_active` o `manager_id` de un user: `invalidate('team:' + managerId)`

---

### 7. Caché de KPIs del dashboard manager

**Archivo:** `src/services/manager/analytics.service.js`

Wrappear las 3 funciones de analytics en `getCached`:

```javascript
// Clave: dashboard:<managerId>:<period>:<from>:<to>
// TTL: 2 min
// EXCEPCIÓN: period === 'custom' NO se cachea (rango arbitrario = infinitas claves)
```

- `getDashboardKPIs`, `getAdvisorRanking`, `getTimeSeries` son queries de agregado sobre `crm_leads` y `crm_activities` — costosas y el resultado es aceptablemente "2 min desfasado"
- Custom period se excluye porque generaría claves únicas por cada combinación de fechas

---

### 8. Endpoint `/health`

**Archivo:** `src/routes/main.routes.js`

```javascript
router.get('/health', (req, res) => {
  const mem = process.memoryUsage();
  res.json({
    ok: true,
    uptime: Math.floor(process.uptime()),
    memory: {
      rss: Math.round(mem.rss / 1024 / 1024) + ' MB',
      heap: Math.round(mem.heapUsed / 1024 / 1024) + ' MB',
    },
  });
});
```

- No requiere autenticación (Render lo llama desde su infraestructura)
- Útil también para verificar manualmente el estado del servidor

---

## Archivos modificados / creados

| Archivo | Operación | Descripción |
|---|---|---|
| `package.json` | modificar | agregar `compression` en dependencies |
| `src/app.js` | modificar | compresión + separar flags SESSION/CSRF |
| `src/db/pool.js` | modificar | parámetros del pool |
| `src/services/cache.service.js` | modificar | cap de 200 entradas |
| `src/services/config.service.js` | **crear** | helper getConfig() con caché |
| `src/services/escalacion.cron.js` | modificar | usar getConfigValue() |
| `src/controllers/public/propiedad.controller.js` | modificar | usar getConfigValue() |
| `src/routes/main.routes.js` | modificar | agregar /health |
| `src/services/manager/analytics.service.js` | modificar | caché de KPIs |
| `src/controllers/manager/crm.controller.js` | modificar | caché de lista de equipo |

---

## Lo que NO cambia

- Lógica de escalación automática
- Sistema de notificaciones SSE
- CRM de advisor y marketing
- Vistas EJS
- Sistema de contratos
- CSRF (sigue desactivado)

---

## Orden de implementación

1. `compression` + `pool.js` — cambios de infraestructura, sin riesgo
2. `cache.service.js` cap — modificación no-breaking
3. Separar flags SESSION/CSRF en `app.js`
4. Crear `config.service.js` y migrar los 2 controllers candidatos
5. Caché de KPIs en analytics.service.js
6. Caché de equipo en manager crm controller
7. Endpoint `/health`
