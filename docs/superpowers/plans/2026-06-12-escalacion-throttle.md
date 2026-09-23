# Throttle temporal de escalación para el lanzamiento — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar un throttle temporal y desactivable manualmente al cron de escalación (`src/services/escalacion.cron.js`), de forma que al reactivarlo en producción no procese nada antes de una hora de arranque configurada, y después procese como máximo N leads por hora (los más antiguos primero).

**Architecture:** 3 filas nuevas en la tabla `configuracion` (`escalacion_throttle_activo`, `escalacion_throttle_desde`, `escalacion_throttle_limite`) controlan el comportamiento. `revisarEscalaciones()` las lee en cada tick, calcula cuántos leads puede procesar (basado en `escalacion_historial` de la última hora) y aplica `ORDER BY transferred_at ASC LIMIT $N` a la query de leads elegibles. Un toggle nuevo en el panel admin (mismo patrón que "Activar escalación") permite apagar el throttle manualmente sin redeploy.

**Tech Stack:** Node.js v24, `pg`, `node-cron`, EJS.

---

## ⚠️ Antes de empezar

- **NO hacer commit hasta que el usuario lo autorice explícitamente** — instrucción permanente de esta sesión. El Task 6 incluye el paso de commit; ejecútalo solo si el usuario ya dio luz verde.
- El cron de escalación está actualmente **apagado** en producción (`escalacion_activa = 'false'`) y las tablas `escalacion_lista_global` / `escalacion_historial` ya fueron creadas y sembradas en Render (18 asesores, `escalacion_historial` vacía, 965 leads con `escalacion_gerencia_inicio` recalculado). **No vuelvas a correr esa migración ni a tocar esas tablas.**
- `src/services/escalacion.cron.js` ya tiene cambios sin commitear de tareas anteriores (flag `ejecutando`, filtros de origen-marketing/portal, notificaciones `lead_expirado`). **No los toques ni los deshagas.** Este plan agrega código nuevo dentro de `revisarEscalaciones()`, que no se solapa con esos cambios.
- **Orden de despliegue importante (fuera de este plan, recordatorio para después):** primero correr `scripts/migration_escalacion_throttle.js` contra producción (crea las 3 filas de config), y **solo después** reactivar `escalacion_activa = 'true'` desde el panel admin. Si se reactiva antes de correr la migración, el cron correrá SIN throttle (porque `cfgMap.escalacion_throttle_activo` sería `undefined`, no `'true'`) durante el tiempo que falte la config.

---

### Task 1: Lógica de throttle en el cron

**Files:**
- Modify: `src/services/escalacion.cron.js:230-251`

- [ ] **Step 1: Confirmar el bloque actual**

El bloque actual entre la validación de horario laboral y la query de leads elegibles es:

```javascript
    if (!estaEnHorarioLaboral()) return;

    const { rows: leads } = await pool.query(
      `SELECT id, advisor_id, escalacion_gerencia_inicio, transferred_at
       FROM crm_leads
       WHERE escalacion_activa = true
         AND status = 'open'
         AND advisor_id != $1
         AND transferred_at < NOW() - INTERVAL '${TIMEOUT_MINUTOS} minutes'
         AND portal IS NOT NULL AND portal <> 'Cartera'
         AND EXISTS (
           SELECT 1 FROM users u
           WHERE u.id = crm_leads.escalacion_origen_id
             AND u.role = 'marketing'
         )
         AND NOT EXISTS (
           SELECT 1 FROM crm_activities a
           WHERE a.lead_id = crm_leads.id
             AND a.created_at > crm_leads.transferred_at
         )`,
      [FALLBACK_2_ID]
    );
```

- [ ] **Step 2: Insertar la lógica de throttle y modificar la query**

Reemplaza ese bloque por:

```javascript
    if (!estaEnHorarioLaboral()) return;

    const { rows: throttleCfg } = await pool.query(
      `SELECT clave, valor FROM configuracion
       WHERE clave IN ('escalacion_throttle_activo', 'escalacion_throttle_desde', 'escalacion_throttle_limite')`
    );
    const cfgMap = Object.fromEntries(throttleCfg.map(r => [r.clave, r.valor]));
    const throttleActivo = cfgMap.escalacion_throttle_activo === 'true';

    let limiteRestante = null; // null = sin límite (modo normal)

    if (throttleActivo) {
      const desde = new Date(cfgMap.escalacion_throttle_desde);
      if (new Date() < desde) return; // pausa total — aún no llega la hora de arranque

      const limite = Number(cfgMap.escalacion_throttle_limite) || 10;
      const { rows: [{ total }] } = await pool.query(
        `SELECT COUNT(*) AS total FROM escalacion_historial
         WHERE created_at > NOW() - INTERVAL '1 hour'`
      );
      limiteRestante = limite - Number(total);
      if (limiteRestante <= 0) return; // cupo de la hora ya alcanzado
    }

    const { rows: leads } = await pool.query(
      `SELECT id, advisor_id, escalacion_gerencia_inicio, transferred_at
       FROM crm_leads
       WHERE escalacion_activa = true
         AND status = 'open'
         AND advisor_id != $1
         AND transferred_at < NOW() - INTERVAL '${TIMEOUT_MINUTOS} minutes'
         AND portal IS NOT NULL AND portal <> 'Cartera'
         AND EXISTS (
           SELECT 1 FROM users u
           WHERE u.id = crm_leads.escalacion_origen_id
             AND u.role = 'marketing'
         )
         AND NOT EXISTS (
           SELECT 1 FROM crm_activities a
           WHERE a.lead_id = crm_leads.id
             AND a.created_at > crm_leads.transferred_at
         )
       ORDER BY transferred_at ASC
       LIMIT $2`,
      [FALLBACK_2_ID, limiteRestante]
    );
```

Nota: `LIMIT $2` con `limiteRestante = null` equivale a `LIMIT NULL`, que en Postgres es "sin límite" — así que cuando el throttle está desactivado (`throttleActivo = false`), la query se comporta exactamente igual que antes (solo gana un `ORDER BY transferred_at ASC`, que no cambia el conjunto de resultados, solo el orden).

- [ ] **Step 3: Verificar sintaxis**

Run:
```bash
node -e "require('dotenv').config(); require('./src/services/escalacion.cron'); console.log('OK')"
```
Expected output: `OK`

---

### Task 2: Script de migración de configuración

**Files:**
- Create: `scripts/migration_escalacion_throttle.js`

- [ ] **Step 1: Crear el script de migración**

```javascript
// scripts/migration_escalacion_throttle.js
'use strict';
require('dotenv').config();
const pool = require('../src/db/pool');

async function run() {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // "Hoy a las 19:00" en hora CDMX (CDMX usa UTC-6 fijo, sin horario de verano desde 2022)
    const hoyCDMX = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Mexico_City' });
    const desdeISO = `${hoyCDMX}T19:00:00-06:00`;

    await client.query(
      `INSERT INTO configuracion (clave, valor, descripcion, updated_at)
       VALUES
         ('escalacion_throttle_activo', 'true',
          'Throttle temporal del cron de escalacion: limita leads/hora durante el lanzamiento', NOW()),
         ('escalacion_throttle_desde', $1,
          'Fecha/hora desde la cual el cron de escalacion procesa leads bajo el throttle', NOW()),
         ('escalacion_throttle_limite', '10',
          'Maximo de leads que el cron de escalacion transfiere por hora mientras el throttle esta activo', NOW())
       ON CONFLICT (clave) DO NOTHING`,
      [desdeISO]
    );

    const { rows } = await client.query(
      `SELECT clave, valor FROM configuracion
       WHERE clave IN ('escalacion_throttle_activo', 'escalacion_throttle_desde', 'escalacion_throttle_limite')
       ORDER BY clave`
    );

    await client.query('COMMIT');
    console.log('✅ Configuración de throttle:');
    console.table(rows);
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('❌ Error en migración:', err.message);
    process.exitCode = 1;
  } finally {
    client.release();
    await pool.end();
  }
}

run();
```

- [ ] **Step 2: Verificar sintaxis**

Run:
```bash
node -e "require('./scripts/migration_escalacion_throttle.js'); console.log('OK')" --check
```
(Si ese comando da problemas por ejecutar `run()` automáticamente, basta con:)
```bash
node --check scripts/migration_escalacion_throttle.js
```
Expected output: sin salida (sintaxis válida).

**Nota:** este script NO se ejecuta como parte de este plan — se correrá manualmente contra producción al momento del despliegue, después de que el código esté desplegado (ver advertencia "Antes de empezar"). Aquí solo se crea y se valida sintácticamente.

---

### Task 3: Controlador admin — leer config y nuevo toggle

**Files:**
- Modify: `src/controllers/admin/escalacion.controller.js`

- [ ] **Step 1: Confirmar el bloque actual de `vista()`**

El bloque actual (líneas 6-38) obtiene `lista`, `cfg` (solo `escalacion_activa`) y `disponibles`, y renderiza:

```javascript
exports.vista = async (req, res) => {
  try {
    const { rows: lista } = await pool.query(`
      SELECT elg.id, elg.user_id, elg.orden, elg.activo,
             u.nombre, u.apellidos
      FROM escalacion_lista_global elg
      JOIN users u ON u.id = elg.user_id
      ORDER BY elg.orden
    `);

    const { rows: cfg } = await pool.query(
      `SELECT valor FROM configuracion WHERE clave = 'escalacion_activa'`
    );

    const { rows: disponibles } = await pool.query(`
      SELECT id, nombre, apellidos FROM users
      WHERE role = 'advisor' AND is_active = true
        AND id NOT IN (SELECT user_id FROM escalacion_lista_global)
      ORDER BY nombre
    `);

    res.render('admin/escalacion/lista', {
      user: req.session.user,
      path: '/admin/configuracion/escalacion-lista',
      lista,
      activa: cfg[0]?.valor === 'true',
      disponibles,
    });
  } catch (err) {
    console.error('❌ GET /admin/configuracion/escalacion-lista:', err);
    res.status(500).send('Error al cargar la lista de escalación.');
  }
};
```

- [ ] **Step 2: Agregar la lectura de configuración del throttle**

Reemplaza ese bloque por:

```javascript
exports.vista = async (req, res) => {
  try {
    const { rows: lista } = await pool.query(`
      SELECT elg.id, elg.user_id, elg.orden, elg.activo,
             u.nombre, u.apellidos
      FROM escalacion_lista_global elg
      JOIN users u ON u.id = elg.user_id
      ORDER BY elg.orden
    `);

    const { rows: cfg } = await pool.query(
      `SELECT valor FROM configuracion WHERE clave = 'escalacion_activa'`
    );

    const { rows: throttleCfg } = await pool.query(
      `SELECT clave, valor FROM configuracion
       WHERE clave IN ('escalacion_throttle_activo', 'escalacion_throttle_desde', 'escalacion_throttle_limite')`
    );
    const throttleMap = Object.fromEntries(throttleCfg.map(r => [r.clave, r.valor]));

    const { rows: disponibles } = await pool.query(`
      SELECT id, nombre, apellidos FROM users
      WHERE role = 'advisor' AND is_active = true
        AND id NOT IN (SELECT user_id FROM escalacion_lista_global)
      ORDER BY nombre
    `);

    res.render('admin/escalacion/lista', {
      user: req.session.user,
      path: '/admin/configuracion/escalacion-lista',
      lista,
      activa: cfg[0]?.valor === 'true',
      throttleActivo: throttleMap.escalacion_throttle_activo === 'true',
      throttleDesde: throttleMap.escalacion_throttle_desde || null,
      throttleLimite: throttleMap.escalacion_throttle_limite || null,
      disponibles,
    });
  } catch (err) {
    console.error('❌ GET /admin/configuracion/escalacion-lista:', err);
    res.status(500).send('Error al cargar la lista de escalación.');
  }
};
```

- [ ] **Step 3: Agregar la función `toggleThrottle`**

Al final del archivo, después de `exports.toggleEscalacion` (línea 63), agrega:

```javascript
exports.toggleThrottle = async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT valor FROM configuracion WHERE clave = 'escalacion_throttle_activo'`
    );
    const actual = rows[0]?.valor === 'true';
    const nuevo  = actual ? 'false' : 'true';

    await pool.query(
      `INSERT INTO configuracion (clave, valor, descripcion, updated_at)
       VALUES ('escalacion_throttle_activo', $1,
               'Throttle temporal del cron de escalacion: limita leads/hora durante el lanzamiento', NOW())
       ON CONFLICT (clave) DO UPDATE SET valor = $1, updated_at = NOW()`,
      [nuevo]
    );

    const actor = req.session?.user?.nombre || req.session?.user?.username || 'admin';
    console.log(`[config] Throttle de escalación: ${nuevo === 'true' ? 'ACTIVADO' : 'DESACTIVADO'} por ${actor}`);

    res.redirect('/admin/configuracion/escalacion-lista');
  } catch (err) {
    console.error('❌ POST /admin/configuracion/escalacion-throttle/toggle:', err);
    res.status(500).send('Error al cambiar el estado del throttle.');
  }
};
```

- [ ] **Step 4: Verificar sintaxis**

Run:
```bash
node --check src/controllers/admin/escalacion.controller.js
```
Expected output: sin salida (sintaxis válida).

---

### Task 4: Ruta nueva para el toggle del throttle

**Files:**
- Modify: `src/routes/admin.routes.js:769-774`

- [ ] **Step 1: Confirmar el bloque actual**

```javascript
router.get('/configuracion/escalacion-lista',          requireRole('admin'), escalacionAdminCtrl.vista);
router.post('/configuracion/escalacion/toggle',        requireRole('admin'), escalacionAdminCtrl.toggleEscalacion);
router.post('/configuracion/escalacion-lista/mover',   requireRole('admin'), escalacionAdminCtrl.mover);
router.post('/configuracion/escalacion-lista/toggle',  requireRole('admin'), escalacionAdminCtrl.toggleActivo);
router.post('/configuracion/escalacion-lista/agregar', requireRole('admin'), escalacionAdminCtrl.agregar);
router.post('/configuracion/escalacion-lista/quitar',  requireRole('admin'), escalacionAdminCtrl.quitar);
```

- [ ] **Step 2: Agregar la ruta del throttle**

Reemplaza ese bloque por:

```javascript
router.get('/configuracion/escalacion-lista',          requireRole('admin'), escalacionAdminCtrl.vista);
router.post('/configuracion/escalacion/toggle',        requireRole('admin'), escalacionAdminCtrl.toggleEscalacion);
router.post('/configuracion/escalacion-throttle/toggle', requireRole('admin'), escalacionAdminCtrl.toggleThrottle);
router.post('/configuracion/escalacion-lista/mover',   requireRole('admin'), escalacionAdminCtrl.mover);
router.post('/configuracion/escalacion-lista/toggle',  requireRole('admin'), escalacionAdminCtrl.toggleActivo);
router.post('/configuracion/escalacion-lista/agregar', requireRole('admin'), escalacionAdminCtrl.agregar);
router.post('/configuracion/escalacion-lista/quitar',  requireRole('admin'), escalacionAdminCtrl.quitar);
```

- [ ] **Step 3: Verificar sintaxis**

Run:
```bash
node --check src/routes/admin.routes.js
```
Expected output: sin salida (sintaxis válida).

---

### Task 5: Tarjeta del toggle en la vista admin

**Files:**
- Modify: `views/admin/escalacion/lista.ejs:39-49`

- [ ] **Step 1: Confirmar el bloque actual**

```html
    <div class="esc-card">
      <div class="esc-card-title">
        Estado del cron
        <form method="POST" action="/admin/configuracion/escalacion/toggle">
          <button type="submit" class="esc-toggle-btn <%= activa ? 'esc-toggle-on' : 'esc-toggle-off' %>">
            <%= activa ? 'Activada' : 'Desactivada' %>
          </button>
        </form>
      </div>
      <p style="font-size:12px;color:#999;">Cuando está desactivada, el cron no transfiere ningún lead, sin importar el horario.</p>
    </div>
```

- [ ] **Step 2: Agregar la tarjeta del throttle justo debajo**

Reemplaza ese bloque por:

```html
    <div class="esc-card">
      <div class="esc-card-title">
        Estado del cron
        <form method="POST" action="/admin/configuracion/escalacion/toggle">
          <button type="submit" class="esc-toggle-btn <%= activa ? 'esc-toggle-on' : 'esc-toggle-off' %>">
            <%= activa ? 'Activada' : 'Desactivada' %>
          </button>
        </form>
      </div>
      <p style="font-size:12px;color:#999;">Cuando está desactivada, el cron no transfiere ningún lead, sin importar el horario.</p>
    </div>

    <div class="esc-card">
      <div class="esc-card-title">
        Modo controlado (lanzamiento)
        <form method="POST" action="/admin/configuracion/escalacion-throttle/toggle">
          <button type="submit" class="esc-toggle-btn <%= throttleActivo ? 'esc-toggle-on' : 'esc-toggle-off' %>">
            <%= throttleActivo ? 'Activado' : 'Desactivado' %>
          </button>
        </form>
      </div>
      <% if (throttleDesde) {
        const desdeFmt = new Intl.DateTimeFormat('es-MX', {
          timeZone: 'America/Mexico_City', day: '2-digit', month: '2-digit',
          hour: '2-digit', minute: '2-digit', hour12: false,
        }).format(new Date(throttleDesde));
      %>
        <p style="font-size:12px;color:#999;">Límite: <%= throttleLimite %> leads/hora · desde <%= desdeFmt %></p>
      <% } %>
      <p style="font-size:12px;color:#999;">Mientras esté activado, el cron procesa como máximo <%= throttleLimite %> leads por hora (los más antiguos primero) y nada antes de la hora de inicio. Desactívalo cuando el backlog inicial ya se haya drenado.</p>
    </div>
```

- [ ] **Step 3: Verificación visual**

Esta vista requiere que `throttleActivo`, `throttleDesde` y `throttleLimite` existan en el contexto de render — ya quedaron agregados en el Task 3. No hay forma de "correr" un `.ejs` aislado; la verificación real es visual (Task 6, Step 2).

---

### Task 6: Verificación end-to-end y commit

**Files:** (ninguno nuevo — solo verificación de los 5 tasks anteriores)

- [ ] **Step 1: Verificar que el servidor levanta sin errores**

Run:
```bash
node -e "require('dotenv').config(); require('./src/app'); console.log('app cargada OK')"
```
Expected: no debe lanzar excepciones al cargar `app.js` (las rutas y controladores se registran sin errores de sintaxis ni `require` rotos). Si `app.js` arranca un servidor HTTP real, usa Ctrl+C después de ver el log de arranque, o usa `node --check` por archivo como alternativa más segura:
```bash
node --check src/services/escalacion.cron.js
node --check src/controllers/admin/escalacion.controller.js
node --check src/routes/admin.routes.js
node --check views/admin/escalacion/lista.ejs 2>/dev/null || true
```
(El último comando puede fallar porque `node --check` no entiende EJS — está bien, es solo informativo.)

- [ ] **Step 2: Verificación visual en local**

Con el servidor local corriendo y sesión de `admin`:
1. Ir a `/admin/configuracion/escalacion-lista`.
2. Confirmar que aparece la nueva tarjeta "Modo controlado (lanzamiento)".
3. Como en local no existen las filas de `configuracion` del throttle (solo se crean en producción vía Task 2), la tarjeta debe mostrar el botón en estado "Desactivado" (gris) y **sin** la línea de "Límite: ... · desde ...", solo el texto explicativo general. Confirmar que no haya error 500 ni traza de `undefined` visible en la página.
4. Click en el botón del throttle: debe crear la fila `escalacion_throttle_activo = 'true'` en `configuracion` (vía `ON CONFLICT DO UPDATE`/INSERT) y el botón debe pasar a "Activado" (teal). Click otra vez para dejarlo en "Desactivado" y no contaminar el estado local.

- [ ] **Step 3: Commit (solo si el usuario autoriza este commit específico)**

```bash
git add src/services/escalacion.cron.js scripts/migration_escalacion_throttle.js src/controllers/admin/escalacion.controller.js src/routes/admin.routes.js views/admin/escalacion/lista.ejs
git commit -m "feat: throttle temporal de escalacion (10 leads/hora con toggle manual)"
```

---

## Self-Review

- **Cobertura del spec:**
  - Sección 3 (config en `configuracion`) → Task 2. ✅
  - Sección 4 (lógica en `revisarEscalaciones()`, pausa total + ventana móvil + ORDER BY/LIMIT) → Task 1. ✅
  - Sección 5 (panel admin: controlador, ruta, vista) → Tasks 3, 4, 5. ✅
  - Sección 6 (script de migración idempotente) → Task 2. ✅
  - Sección 7 (testing manual) → Task 6. ✅
- **Placeholders:** ninguno — todo el código está completo y ejecutable.
- **Consistencia de tipos/nombres:** `escalacion_throttle_activo`, `escalacion_throttle_desde`, `escalacion_throttle_limite`, `throttleActivo`, `throttleDesde`, `throttleLimite`, `toggleThrottle` son consistentes entre Tasks 1, 2, 3, 4 y 5.
- **Orden de despliegue:** documentado en "Antes de empezar" — correr Task 2 (migración) en producción ANTES de reactivar `escalacion_activa`.
