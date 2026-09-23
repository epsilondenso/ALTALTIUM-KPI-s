# Escalación automática — lista global Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the gerencia-based automatic lead escalation with a single global ordered list of advisors, editable from the admin panel, that the cron cycles through circularly (one full loop) before falling back to Daniel Rojas → Denisse Hansen, while recording an escalation history per advisor.

**Architecture:** A new shared service (`escalacionLista.service.js`) wraps all reads/writes of the new `escalacion_lista_global` and `escalacion_historial` tables and exposes the circular-loop calculation. The recreated `escalacion.cron.js` uses that service inside its existing transactional flow. Two existing controllers (marketing, manager) are updated to compute the correct "punto de partida" advisor when activating escalation. A new admin controller + view manage the global list and the existing on/off toggle.

**Tech Stack:** Node.js v24, Express v5, PostgreSQL (`pg`), `node-cron`, EJS.

---

## Task 1: Migration — nuevas tablas, seed y recálculo de punto de partida

**Files:**
- Create: `scripts/migration_escalacion_lista_global.js`

- [ ] **Step 1: Write the migration script**

```javascript
// scripts/migration_escalacion_lista_global.js
'use strict';
require('dotenv').config();
const pool = require('../src/db/pool');

// Orden inicial — ver docs/superpowers/specs/2026-06-11-escalacion-lista-global-design.md
const SEED_ADVISORS = [
  25, // 1. Orlando Palacios Vega
  32, // 2. Victor Manuel Garcia Bautista
  74, // 3. Laura Patricia Claudio Lucio
  11, // 4. Yolanda Rojas Aguilar
  43, // 5. Marco Antonio Salazar Vidal
  8,  // 6. Manuel Omar Moreno Zapata
  30, // 7. Carmina Priscilla Bolaños Herrera
  86, // 8. Eduardo Ramirez Arreola
  84, // 9. Patricia Nathalie Mijares Perez
  34, // 10. Domingo Infante Allende
  15, // 11. Jose Arturo Gonzalez Reyes
  58, // 12. Valentina Mariel Salgado Arias
  90, // 13. Diana Elizabeth Vivanco Galindo
  23, // 14. Johana Vanessa Arias Lara
  85, // 15. Jose Manuel Alvarez Hernandez
  77, // 16. Herlinda Marahi Ruiz Ramirez
  79, // 17. Adriana Nivon Medrano
  28, // 18. Luis Néstor Portilla Vázquez
];

async function run() {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    await client.query(`
      CREATE TABLE IF NOT EXISTS escalacion_lista_global (
        id SERIAL PRIMARY KEY,
        user_id INT NOT NULL REFERENCES users(id),
        orden INT NOT NULL,
        activo BOOLEAN DEFAULT true,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(orden),
        UNIQUE(user_id)
      );
    `);
    console.log('✅ Tabla escalacion_lista_global OK');

    await client.query(`
      CREATE TABLE IF NOT EXISTS escalacion_historial (
        id SERIAL PRIMARY KEY,
        lead_id INT NOT NULL REFERENCES crm_leads(id),
        advisor_id_anterior INT NOT NULL REFERENCES users(id),
        advisor_id_nuevo INT NOT NULL REFERENCES users(id),
        created_at TIMESTAMPTZ DEFAULT NOW()
      );
    `);
    console.log('✅ Tabla escalacion_historial OK');

    const { rows: existing } = await client.query(
      `SELECT COUNT(*)::int AS total FROM escalacion_lista_global`
    );

    if (existing[0].total === 0) {
      for (let i = 0; i < SEED_ADVISORS.length; i++) {
        await client.query(
          `INSERT INTO escalacion_lista_global (user_id, orden, activo) VALUES ($1, $2, true)`,
          [SEED_ADVISORS[i], i + 1]
        );
      }
      console.log(`✅ Seed: ${SEED_ADVISORS.length} asesores insertados en escalacion_lista_global`);
    } else {
      console.log(`ℹ️  escalacion_lista_global ya tiene ${existing[0].total} filas, no se vuelve a sembrar`);
    }

    const { rowCount } = await client.query(`
      UPDATE crm_leads
      SET escalacion_gerencia_inicio = COALESCE(
        (SELECT user_id FROM escalacion_lista_global
         WHERE user_id = crm_leads.advisor_id AND activo = true),
        (SELECT user_id FROM escalacion_lista_global
         WHERE activo = true ORDER BY orden LIMIT 1)
      )
      WHERE escalacion_activa = true AND status = 'open';
    `);
    console.log(`✅ Recalculado punto de partida para ${rowCount} lead(s) activos`);

    await client.query('COMMIT');
    console.log('✅ Migración completada');
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

- [ ] **Step 2: Run the migration against the local DB**

Run: `node scripts/migration_escalacion_lista_global.js`

Expected output (last lines):
```
✅ Tabla escalacion_lista_global OK
✅ Tabla escalacion_historial OK
✅ Seed: 18 asesores insertados en escalacion_lista_global
✅ Recalculado punto de partida para N lead(s) activos
✅ Migración completada
```

- [ ] **Step 3: Verify the seed**

Run:
```bash
node -e "require('dotenv').config(); const pool=require('./src/db/pool'); pool.query('SELECT orden,user_id,activo FROM escalacion_lista_global ORDER BY orden').then(r=>{console.log(r.rows); pool.end();})"
```

Expected: 18 rows, `orden` 1-18, `user_id` matching the seed list above, all `activo = true`.

- [ ] **Step 4: Commit**

```bash
git add scripts/migration_escalacion_lista_global.js
git commit -m "feat: agregar tablas escalacion_lista_global y escalacion_historial con seed inicial"
```

---

## Task 2: Servicio compartido `escalacionLista.service.js`

**Files:**
- Create: `src/services/escalacionLista.service.js`

- [ ] **Step 1: Write the service**

```javascript
// src/services/escalacionLista.service.js
'use strict';
const pool = require('../db/pool');

const FALLBACK_1_ID = 35; // Daniel Rojas (directivo)
const FALLBACK_2_ID = 7;  // Jimena Denisse Hansen — FIN ABSOLUTO

// Devuelve los user_id de la lista global activa, ordenados.
async function obtenerListaActiva() {
  const { rows } = await pool.query(
    `SELECT user_id FROM escalacion_lista_global WHERE activo = true ORDER BY orden`
  );
  return rows.map(r => r.user_id);
}

// Calcula el "punto de partida" de la vuelta circular para un advisor
// que recién recibe un lead con escalación activada.
// - Si el advisor está en la lista activa → él mismo es el punto de partida.
// - Si no está en la lista (o la lista está vacía) → el primero de la lista
//   (o null si la lista está vacía).
async function calcularPuntoDePartida(advisorId) {
  const lista = await obtenerListaActiva();
  if (lista.length === 0) return null;
  return lista.includes(Number(advisorId)) ? Number(advisorId) : lista[0];
}

// Calcula el siguiente advisor en la vuelta circular.
// - advisorActualId: quien tiene el lead y no respondió a tiempo.
// - advisorInicioId: punto de partida guardado en crm_leads.escalacion_gerencia_inicio.
// Retorna FALLBACK_1_ID si se completó la vuelta, o null si la lista está vacía.
async function obtenerSiguienteAdvisor(advisorActualId, advisorInicioId) {
  const lista = await obtenerListaActiva();
  if (lista.length === 0) return null;

  const posActual = lista.indexOf(advisorActualId);
  const posSiguiente = posActual === -1 ? 0 : (posActual + 1) % lista.length;
  const siguienteAdvisorId = lista[posSiguiente];

  if (siguienteAdvisorId === advisorInicioId) {
    return FALLBACK_1_ID;
  }
  return siguienteAdvisorId;
}

module.exports = {
  FALLBACK_1_ID,
  FALLBACK_2_ID,
  obtenerListaActiva,
  calcularPuntoDePartida,
  obtenerSiguienteAdvisor,
};
```

- [ ] **Step 2: Verify it loads and returns the seeded list**

Run:
```bash
node -e "require('dotenv').config(); const s=require('./src/services/escalacionLista.service'); s.obtenerListaActiva().then(l=>{console.log(l); process.exit(0);})"
```

Expected: `[ 25, 32, 74, 11, 43, 8, 30, 86, 84, 34, 15, 58, 90, 23, 85, 77, 79, 28 ]`

- [ ] **Step 3: Verify `obtenerSiguienteAdvisor` circular + full-loop behavior**

Run:
```bash
node -e "
require('dotenv').config();
const s=require('./src/services/escalacionLista.service');
(async () => {
  console.log('25 -> ', await s.obtenerSiguienteAdvisor(25, 25));   // esperado: 32
  console.log('28 -> ', await s.obtenerSiguienteAdvisor(28, 8));    // esperado: 25 (vuelta a la cabeza)
  console.log('43 -> ', await s.obtenerSiguienteAdvisor(43, 8));    // esperado: 35 (vuelta completa -> Daniel Rojas)
  console.log('99 -> ', await s.obtenerSiguienteAdvisor(99, 25));   // esperado: 35 (no estaba en lista, siguiente=25=inicio -> Daniel Rojas)
  process.exit(0);
})();
"
```

Expected:
```
25 ->  32
28 ->  25
43 ->  35
99 ->  35
```

- [ ] **Step 4: Commit**

```bash
git add src/services/escalacionLista.service.js
git commit -m "feat: agregar servicio escalacionLista para calculo de lista global circular"
```

---

## Task 3: Recrear `src/services/escalacion.cron.js`

**Files:**
- Create: `src/services/escalacion.cron.js`

- [ ] **Step 1: Write the cron service**

```javascript
// src/services/escalacion.cron.js
'use strict';

const cron = require('node-cron');
const pool = require('../db/pool');
const notifService = require('./notificaciones.service');
const listaService = require('./escalacionLista.service');

const MODO_PRUEBA = process.env.ESCALACION_MODO_PRUEBA === 'true';
const TIMEOUT_MINUTOS = 5;
const { FALLBACK_1_ID, FALLBACK_2_ID } = listaService;

async function getNombre(userId) {
  try {
    const { rows } = await pool.query(
      `SELECT nombre, apellidos FROM users WHERE id = $1`,
      [userId]
    );
    if (!rows.length) return `Usuario #${userId}`;
    return `${rows[0].nombre || ''} ${rows[0].apellidos || ''}`.trim() || `Usuario #${userId}`;
  } catch {
    return `Usuario #${userId}`;
  }
}

// Transfiere el lead, registra el traspaso en crm_lead_transfers y
// registra la escalación en escalacion_historial, todo en la misma transacción.
async function transferirLead(leadId, fromUserId, toUserId, nota, activarEscalacion, client) {
  if (MODO_PRUEBA) {
    console.log(`[escalacion:PRUEBA] transferirLead SIMULADO — lead ${leadId}: ${fromUserId} → ${toUserId} | escalacion_activa: ${activarEscalacion}`);
    return;
  }

  await client.query(
    `UPDATE crm_leads SET
       advisor_id     = $1,
       transferred_by = $2,
       transferred_to = $1,
       transferred_at = NOW(),
       transfer_note  = $3,
       escalacion_activa = $4,
       opened_at      = NULL,
       updated_at     = NOW()
     WHERE id = $5`,
    [toUserId, fromUserId, nota, activarEscalacion, leadId]
  );

  await client.query(
    `INSERT INTO crm_lead_transfers (
       lead_id, from_user_id, to_user_id,
       from_role, to_role, transfer_type,
       transfer_note, created_at, created_by
     ) VALUES (
       $1, $2, $3,
       (SELECT role FROM users WHERE id = $2),
       (SELECT role FROM users WHERE id = $3),
       'escalacion',
       $4, NOW(), $2
     )`,
    [leadId, fromUserId, toUserId, nota || null]
  );

  await client.query(
    `INSERT INTO escalacion_historial (lead_id, advisor_id_anterior, advisor_id_nuevo)
     VALUES ($1, $2, $3)`,
    [leadId, fromUserId, toUserId]
  );
}

async function escalarLead(lead) {
  const currentUser = lead.advisor_id;
  const leadId = lead.id;
  const advisorInicioId = lead.escalacion_gerencia_inicio;

  // CASO 1: el lead ya está con Denisse Hansen — fin definitivo (defensivo).
  if (currentUser === FALLBACK_2_ID) {
    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      if (!MODO_PRUEBA) {
        await client.query(`UPDATE crm_leads SET escalacion_activa = false WHERE id = $1`, [leadId]);
      }
      await client.query('COMMIT');
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
    console.log(`[escalacion] Lead ${leadId}: FIN con Denisse Hansen`);
    return;
  }

  // CASO 2: Daniel Rojas no atendió -> Denisse Hansen (fin de la cadena).
  if (currentUser === FALLBACK_1_ID) {
    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      await transferirLead(
        leadId, FALLBACK_1_ID, FALLBACK_2_ID,
        'Escalación automática: Daniel Rojas no atendió el lead en 5 minutos',
        false, client
      );
      await client.query('COMMIT');
    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }
    if (!MODO_PRUEBA) {
      await notifService.crearNotificacion(
        FALLBACK_2_ID, 'lead_transferido',
        'Lead asignado al finalizar la cadena de escalación.',
        `/advisor/leads/${leadId}`, null
      ).catch(() => {});
    }
    console.log(`[escalacion] Lead ${leadId}: Daniel Rojas → Denisse Hansen (FIN)`);
    return;
  }

  // CASO 3: flujo normal — siguiente en la lista global circular.
  const nextUserId = await listaService.obtenerSiguienteAdvisor(currentUser, advisorInicioId);
  if (!nextUserId) {
    console.log(`[escalacion] Lead ${leadId}: lista global vacía o sin activos, no se escala`);
    return;
  }

  const nombreCurrent = await getNombre(currentUser);
  const nombreNext = await getNombre(nextUserId);
  const esFallback1 = nextUserId === FALLBACK_1_ID;

  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await transferirLead(
      leadId, currentUser, nextUserId,
      `Escalación automática: ${nombreCurrent} no atendió el lead en ${TIMEOUT_MINUTOS} minutos`,
      true, client
    );
    await client.query('COMMIT');
  } catch (err) {
    await client.query('ROLLBACK');
    console.error(`[escalacion] Error transfiriendo lead ${leadId}:`, err.message);
    throw err;
  } finally {
    client.release();
  }

  if (!MODO_PRUEBA) {
    await notifService.crearNotificacion(
      nextUserId, 'lead_transferido',
      esFallback1
        ? `⚠️ Lead escalado al nivel directivo. Tienes ${TIMEOUT_MINUTOS} minutos para atenderlo.`
        : `⚠️ Tienes ${TIMEOUT_MINUTOS} minutos para atender este lead o será reasignado.`,
      `/advisor/leads/${leadId}`, null
    ).catch(() => {});
  }

  console.log(`[escalacion] Lead ${leadId}: ${nombreCurrent} → ${nombreNext}`);
}

// Lunes-Viernes 9:00-20:00, Sábado-Domingo 9:00-14:00, hora CDMX.
function estaEnHorarioLaboral() {
  const ahora = new Date();
  const fmt = new Intl.DateTimeFormat('es-MX', {
    timeZone: 'America/Mexico_City',
    weekday: 'short',
    hour: 'numeric',
    hour12: false,
  });
  const partes = fmt.formatToParts(ahora);
  const dia = partes.find(p => p.type === 'weekday')?.value;
  const hora = Number(partes.find(p => p.type === 'hour')?.value);

  const esFinDeSemana = dia === 'sáb' || dia === 'dom';
  if (esFinDeSemana) {
    return hora >= 9 && hora < 14;
  }
  return hora >= 9 && hora < 20;
}

async function revisarEscalaciones() {
  try {
    const { rows: config } = await pool.query(
      `SELECT valor, activo_desde FROM configuracion WHERE clave = 'escalacion_activa'`
    );
    if (!config.length || config[0].valor !== 'true') return;

    if (config[0].activo_desde) {
      const hoy = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Mexico_City' });
      const desde = new Date(config[0].activo_desde).toISOString().slice(0, 10);
      if (hoy < desde) return;
    }

    if (!estaEnHorarioLaboral()) return;

    const { rows: leads } = await pool.query(
      `SELECT id, advisor_id, escalacion_gerencia_inicio, transferred_at
       FROM crm_leads
       WHERE escalacion_activa = true
         AND status = 'open'
         AND advisor_id != $1
         AND transferred_at < NOW() - INTERVAL '${TIMEOUT_MINUTOS} minutes'
         AND NOT EXISTS (
           SELECT 1 FROM crm_activities a
           WHERE a.lead_id = crm_leads.id
             AND a.created_at > crm_leads.transferred_at
         )`,
      [FALLBACK_2_ID]
    );

    if (leads.length === 0) return;
    console.log(`[escalacion] ${leads.length} lead(s) para escalar`);

    for (const lead of leads) {
      await escalarLead(lead).catch(err => console.error(`[escalacion] Error lead ${lead.id}:`, err.message));
    }
  } catch (err) {
    console.error('[escalacion] Error:', err.message);
  }
}

exports.revisarEscalaciones = revisarEscalaciones;

exports.iniciar = function () {
  cron.schedule('* * * * *', revisarEscalaciones, { timezone: 'America/Mexico_City' });
  console.log(`[escalacion] Cron iniciado ✓${MODO_PRUEBA ? ' — MODO PRUEBA ACTIVO (sin transferencias reales)' : ''}`);
};
```

- [ ] **Step 2: Commit**

```bash
git add src/services/escalacion.cron.js
git commit -m "feat: recrear escalacion.cron con logica de lista global circular"
```

---

## Task 4: Iniciar el cron desde `server.js`

**Files:**
- Modify: `src/server.js`

- [ ] **Step 1: Read the current file to confirm exact content**

Current content of `src/server.js`:

```javascript
// src/server.js
const app = require('./app');
const pool = require('./db/pool');

const PORT = process.env.PORT || 3000;

async function runMigrations() {
  try {
    await pool.query(`ALTER TABLE crm_lead_property_profiles ADD COLUMN IF NOT EXISTS locales_detalle TEXT`);
    await pool.query(`ALTER TABLE crm_lead_property_profiles ADD COLUMN IF NOT EXISTS notas_regularizacion TEXT`);
    console.log('✅ Migraciones OK (crm_lead_property_profiles)');
  } catch (e) {
    console.error('⚠️  Error en migraciones de arranque:', e.message);
  }
}

app.listen(PORT, async () => {
  console.log(`✅ Server running on port ${PORT}`);
  await runMigrations();
});
```

- [ ] **Step 2: Add the escalation cron require + start call**

```javascript
// src/server.js
const app = require('./app');
const pool = require('./db/pool');
const escalacionCron = require('./services/escalacion.cron');

const PORT = process.env.PORT || 3000;

async function runMigrations() {
  try {
    await pool.query(`ALTER TABLE crm_lead_property_profiles ADD COLUMN IF NOT EXISTS locales_detalle TEXT`);
    await pool.query(`ALTER TABLE crm_lead_property_profiles ADD COLUMN IF NOT EXISTS notas_regularizacion TEXT`);
    console.log('✅ Migraciones OK (crm_lead_property_profiles)');
  } catch (e) {
    console.error('⚠️  Error en migraciones de arranque:', e.message);
  }
}

app.listen(PORT, async () => {
  console.log(`✅ Server running on port ${PORT}`);
  await runMigrations();
  escalacionCron.iniciar();
});
```

- [ ] **Step 3: Verify the server boots and the cron logs its start message**

Run: `node src/server.js` (stop with Ctrl+C after confirming the log line)

Expected output includes:
```
✅ Server running on port 3000
✅ Migraciones OK (crm_lead_property_profiles)
[escalacion] Cron iniciado ✓
```

- [ ] **Step 4: Commit**

```bash
git add src/server.js
git commit -m "feat: iniciar cron de escalacion automatica al arrancar el servidor"
```

---

## Task 5: Controlador admin para configuración de escalación

**Files:**
- Create: `src/controllers/admin/escalacion.controller.js`

- [ ] **Step 1: Write the controller**

```javascript
// src/controllers/admin/escalacion.controller.js
'use strict';

const pool = require('../../db/pool');

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

exports.toggleEscalacion = async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT valor FROM configuracion WHERE clave = 'escalacion_activa'`
    );
    const actual = rows[0]?.valor === 'true';
    const nuevo  = actual ? 'false' : 'true';

    await pool.query(
      `INSERT INTO configuracion (clave, valor, descripcion, updated_at)
       VALUES ('escalacion_activa', $1, 'Escalación automática de leads activa/inactiva', NOW())
       ON CONFLICT (clave) DO UPDATE SET valor = $1, updated_at = NOW()`,
      [nuevo]
    );

    const actor = req.session?.user?.nombre || req.session?.user?.username || 'admin';
    console.log(`[config] Escalación automática: ${nuevo === 'true' ? 'ACTIVADA' : 'DESACTIVADA'} por ${actor}`);

    res.redirect('/admin/configuracion/escalacion-lista');
  } catch (err) {
    console.error('❌ POST /admin/configuracion/escalacion/toggle:', err);
    res.status(500).send('Error al cambiar el estado de escalación.');
  }
};

exports.mover = async (req, res) => {
  const { id, direccion } = req.body;
  const client = await pool.connect();
  try {
    const { rows: actualRows } = await client.query(
      `SELECT id, orden FROM escalacion_lista_global WHERE id = $1`,
      [id]
    );
    if (!actualRows.length) return res.redirect('/admin/configuracion/escalacion-lista');
    const actual = actualRows[0];

    const cmp = direccion === 'arriba' ? '<' : '>';
    const ord = direccion === 'arriba' ? 'DESC' : 'ASC';
    const { rows: adyacenteRows } = await client.query(
      `SELECT id, orden FROM escalacion_lista_global WHERE orden ${cmp} $1 ORDER BY orden ${ord} LIMIT 1`,
      [actual.orden]
    );
    if (!adyacenteRows.length) return res.redirect('/admin/configuracion/escalacion-lista');
    const adyacente = adyacenteRows[0];

    await client.query('BEGIN');
    await client.query(`UPDATE escalacion_lista_global SET orden = -1 WHERE id = $1`, [actual.id]);
    await client.query(`UPDATE escalacion_lista_global SET orden = $1 WHERE id = $2`, [actual.orden, adyacente.id]);
    await client.query(`UPDATE escalacion_lista_global SET orden = $1 WHERE id = $2`, [adyacente.orden, actual.id]);
    await client.query('COMMIT');

    res.redirect('/admin/configuracion/escalacion-lista');
  } catch (err) {
    await client.query('ROLLBACK');
    console.error('❌ POST /admin/configuracion/escalacion-lista/mover:', err);
    res.status(500).send('Error al mover el asesor.');
  } finally {
    client.release();
  }
};

exports.toggleActivo = async (req, res) => {
  try {
    await pool.query(`UPDATE escalacion_lista_global SET activo = NOT activo WHERE id = $1`, [req.body.id]);
    res.redirect('/admin/configuracion/escalacion-lista');
  } catch (err) {
    console.error('❌ POST /admin/configuracion/escalacion-lista/toggle:', err);
    res.status(500).send('Error al cambiar el estado del asesor.');
  }
};

exports.agregar = async (req, res) => {
  try {
    const userId = parseInt(req.body.user_id, 10);
    if (!userId) return res.redirect('/admin/configuracion/escalacion-lista');

    const { rows } = await pool.query(
      `SELECT COALESCE(MAX(orden), 0) + 1 AS siguiente FROM escalacion_lista_global`
    );
    await pool.query(
      `INSERT INTO escalacion_lista_global (user_id, orden, activo) VALUES ($1, $2, true)`,
      [userId, rows[0].siguiente]
    );
    res.redirect('/admin/configuracion/escalacion-lista');
  } catch (err) {
    console.error('❌ POST /admin/configuracion/escalacion-lista/agregar:', err);
    res.status(500).send('Error al agregar el asesor.');
  }
};

exports.quitar = async (req, res) => {
  try {
    await pool.query(`DELETE FROM escalacion_lista_global WHERE id = $1`, [req.body.id]);
    res.redirect('/admin/configuracion/escalacion-lista');
  } catch (err) {
    console.error('❌ POST /admin/configuracion/escalacion-lista/quitar:', err);
    res.status(500).send('Error al quitar el asesor.');
  }
};
```

- [ ] **Step 2: Commit**

```bash
git add src/controllers/admin/escalacion.controller.js
git commit -m "feat: agregar controlador admin para lista global de escalacion"
```

---

## Task 6: Rutas admin para escalación

**Files:**
- Modify: `src/routes/admin.routes.js:757-763`

- [ ] **Step 1: Add the new routes after the "Recursos Digitales" block**

Current content at lines 757-763:

```javascript
// ============================
// Recursos Digitales
// ============================
const recursosAdminCtrl = require('../controllers/admin/recursos.controller');
router.get('/recursos-digitales',  requireRole('admin'), recursosAdminCtrl.configForm);
router.post('/recursos-digitales', requireRole('admin'), recursosAdminCtrl.configSave);

```

Replace with:

```javascript
// ============================
// Recursos Digitales
// ============================
const recursosAdminCtrl = require('../controllers/admin/recursos.controller');
router.get('/recursos-digitales',  requireRole('admin'), recursosAdminCtrl.configForm);
router.post('/recursos-digitales', requireRole('admin'), recursosAdminCtrl.configSave);

// ============================
// Escalación automática — lista global
// ============================
const escalacionAdminCtrl = require('../controllers/admin/escalacion.controller');

router.get('/configuracion/escalacion-lista',          requireRole('admin'), escalacionAdminCtrl.vista);
router.post('/configuracion/escalacion/toggle',        requireRole('admin'), escalacionAdminCtrl.toggleEscalacion);
router.post('/configuracion/escalacion-lista/mover',   requireRole('admin'), escalacionAdminCtrl.mover);
router.post('/configuracion/escalacion-lista/toggle',  requireRole('admin'), escalacionAdminCtrl.toggleActivo);
router.post('/configuracion/escalacion-lista/agregar', requireRole('admin'), escalacionAdminCtrl.agregar);
router.post('/configuracion/escalacion-lista/quitar',  requireRole('admin'), escalacionAdminCtrl.quitar);

```

- [ ] **Step 2: Commit**

```bash
git add src/routes/admin.routes.js
git commit -m "feat: agregar rutas admin para configuracion de escalacion y lista global"
```

---

## Task 7: Vista admin — lista global de escalación

**Files:**
- Create: `views/admin/escalacion/lista.ejs`

- [ ] **Step 1: Write the view**

```html
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap');
  .esc-admin-page { font-family: 'DM Sans', sans-serif; min-height: 100vh; background: #f8fafc; padding: 40px 28px 80px; }
  .esc-admin-inner { max-width: 720px; margin: 0 auto; }
  .esc-header { margin-bottom: 32px; }
  .esc-header h1 { font-size: 20px; font-weight: 600; color: #1a1a1a; margin-bottom: 4px; }
  .esc-header p { font-size: 13px; color: #777; line-height: 1.6; max-width: 560px; }
  .esc-card { background: #fff; border: 1px solid #e8e8e4; border-radius: 16px; padding: 28px; margin-bottom: 24px; }
  .esc-card-title { font-size: 13px; font-weight: 600; color: #1a1a1a; margin-bottom: 18px; padding-bottom: 14px; border-bottom: 1px solid #f0f0ec; display: flex; align-items: center; justify-content: space-between; gap: 8px; }
  .esc-toggle-btn { height: 36px; padding: 0 18px; border: none; border-radius: 10px; font-size: 12px; font-weight: 600; font-family: 'DM Sans', sans-serif; cursor: pointer; }
  .esc-toggle-on { background: #008a8a; color: #fff; }
  .esc-toggle-off { background: #e8e8e4; color: #555; }
  .esc-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .esc-table th { text-align: left; font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #888; padding: 8px 10px; border-bottom: 1px solid #f0f0ec; }
  .esc-table td { padding: 10px 10px; border-bottom: 1px solid #f5f5f3; vertical-align: middle; }
  .esc-table tr:last-child td { border-bottom: none; }
  .esc-pos { display: inline-flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 50%; background: rgba(0,138,138,.1); color: #008a8a; font-weight: 600; font-size: 12px; }
  .esc-inactivo { color: #bbb; }
  .esc-btn-icon { width: 28px; height: 28px; border: 1px solid #e8e8e4; border-radius: 8px; background: #fff; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; font-size: 13px; line-height: 1; color: #555; }
  .esc-btn-icon:hover { background: #f7f7f5; }
  .esc-btn-quitar { color: #dc2626; border-color: #fecaca; }
  .esc-btn-toggle { font-size: 11px; font-weight: 600; padding: 0 10px; height: 28px; border-radius: 8px; border: 1px solid #e8e8e4; background: #fff; cursor: pointer; }
  .esc-actions { display: flex; gap: 6px; align-items: center; }
  .esc-add-row { display: flex; gap: 10px; margin-top: 18px; }
  .esc-select { flex: 1; height: 40px; padding: 0 12px; background: #f7f7f5; border: 1px solid #e8e8e4; border-radius: 10px; font-size: 13px; font-family: 'DM Sans', sans-serif; color: #1a1a1a; outline: none; }
  .esc-btn-add { height: 40px; padding: 0 20px; background: #008a8a; color: #fff; border: none; border-radius: 10px; font-size: 13px; font-weight: 600; font-family: 'DM Sans', sans-serif; cursor: pointer; }
  .esc-btn-add:hover { background: #006666; }
  .esc-empty { font-size: 13px; color: #999; padding: 12px 0; }
</style>

<div class="esc-admin-page">
  <div class="esc-admin-inner">

    <div class="esc-header">
      <h1>Escalación automática de leads</h1>
      <p>La lista global define el orden en que se reasignan los leads sin contacto. El cron recorre la lista de forma circular antes de caer al fallback final.</p>
    </div>

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
      <div class="esc-card-title">Lista global de asesores</div>

      <% if (lista.length === 0) { %>
        <p class="esc-empty">No hay asesores en la lista global. Agrega al menos uno para que el cron pueda escalar.</p>
      <% } else { %>
        <table class="esc-table">
          <thead>
            <tr>
              <th style="width:48px;">Pos.</th>
              <th>Asesor</th>
              <th style="width:90px;">Activo</th>
              <th style="width:140px;">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <% lista.forEach((item, i) => { %>
              <tr class="<%= item.activo ? '' : 'esc-inactivo' %>">
                <td><span class="esc-pos"><%= item.orden %></span></td>
                <td><%= item.nombre %> <%= item.apellidos %></td>
                <td>
                  <form method="POST" action="/admin/configuracion/escalacion-lista/toggle">
                    <input type="hidden" name="id" value="<%= item.id %>" />
                    <button type="submit" class="esc-btn-toggle">
                      <%= item.activo ? 'Activo' : 'Inactivo' %>
                    </button>
                  </form>
                </td>
                <td>
                  <div class="esc-actions">
                    <form method="POST" action="/admin/configuracion/escalacion-lista/mover">
                      <input type="hidden" name="id" value="<%= item.id %>" />
                      <input type="hidden" name="direccion" value="arriba" />
                      <button type="submit" class="esc-btn-icon" <%= i === 0 ? 'disabled' : '' %>>↑</button>
                    </form>
                    <form method="POST" action="/admin/configuracion/escalacion-lista/mover">
                      <input type="hidden" name="id" value="<%= item.id %>" />
                      <input type="hidden" name="direccion" value="abajo" />
                      <button type="submit" class="esc-btn-icon" <%= i === lista.length - 1 ? 'disabled' : '' %>>↓</button>
                    </form>
                    <form method="POST" action="/admin/configuracion/escalacion-lista/quitar">
                      <input type="hidden" name="id" value="<%= item.id %>" />
                      <button type="submit" class="esc-btn-icon esc-btn-quitar">✕</button>
                    </form>
                  </div>
                </td>
              </tr>
            <% }) %>
          </tbody>
        </table>
      <% } %>

      <% if (disponibles.length > 0) { %>
        <form method="POST" action="/admin/configuracion/escalacion-lista/agregar" class="esc-add-row">
          <select name="user_id" class="esc-select">
            <% disponibles.forEach(u => { %>
              <option value="<%= u.id %>"><%= u.nombre %> <%= u.apellidos %></option>
            <% }) %>
          </select>
          <button type="submit" class="esc-btn-add">Agregar a la lista</button>
        </form>
      <% } %>
    </div>

  </div>
</div>
```

- [ ] **Step 2: Verify the view renders**

Run: `node src/server.js`, log in as an admin user, navigate to `/admin/configuracion/escalacion-lista`.

Expected: page renders with the 18 seeded advisors in order, the toggle button shows "Desactivada" (or whatever `configuracion.escalacion_activa` currently holds), and a select to add remaining advisors.

- [ ] **Step 3: Commit**

```bash
git add views/admin/escalacion/lista.ejs
git commit -m "feat: agregar vista admin para lista global de escalacion"
```

---

## Task 8: Enlace en el sidebar del admin

**Files:**
- Modify: `views/admin/partials/sidebar.ejs:114-122`

- [ ] **Step 1: Add a new menu item after "Recursos Digitales"**

Current content at lines 114-122:

```html
      <li>
        <a href="/admin/recursos-digitales"
           class="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-800/60 text-slate-300 <%= path === '/admin/recursos-digitales' ? 'bg-slate-800 text-white' : '' %>">
          <span class="inline-flex h-7 w-7 items-center justify-center rounded-full bg-teal-500/20 text-teal-300 text-xs font-semibold">
            R
          </span>
          <span>Recursos Digitales</span>
        </a>
      </li>
```

Replace with:

```html
      <li>
        <a href="/admin/recursos-digitales"
           class="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-800/60 text-slate-300 <%= path === '/admin/recursos-digitales' ? 'bg-slate-800 text-white' : '' %>">
          <span class="inline-flex h-7 w-7 items-center justify-center rounded-full bg-teal-500/20 text-teal-300 text-xs font-semibold">
            R
          </span>
          <span>Recursos Digitales</span>
        </a>
      </li>
      <li>
        <a href="/admin/configuracion/escalacion-lista"
           class="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-800/60 text-slate-300 <%= path === '/admin/configuracion/escalacion-lista' ? 'bg-slate-800 text-white' : '' %>">
          <span class="inline-flex h-7 w-7 items-center justify-center rounded-full bg-teal-500/20 text-teal-300 text-xs font-semibold">
            E
          </span>
          <span>Escalación de leads</span>
        </a>
      </li>
```

- [ ] **Step 2: Verify the link appears and highlights when active**

Reload `/admin/configuracion/escalacion-lista` as admin — the "Escalación de leads" item should be highlighted (white text, dark background).

- [ ] **Step 3: Commit**

```bash
git add views/admin/partials/sidebar.ejs
git commit -m "feat: agregar enlace de escalacion de leads al sidebar admin"
```

---

## Task 9: Actualizar `marketing/crm.controller.js` — punto de partida correcto

**Files:**
- Modify: `src/controllers/marketing/crm.controller.js:7-10` and `:130-143`

- [ ] **Step 1: Add the require for the shared service**

Current content at lines 7-10:

```javascript
const crmService   = require('../../services/advisor/crm.service');
const notifService = require('../../services/notificaciones.service');
const advisorCtrl  = require('../advisor/crm.controller');
const pool         = require('../../db/pool');
```

Replace with:

```javascript
const crmService     = require('../../services/advisor/crm.service');
const notifService   = require('../../services/notificaciones.service');
const advisorCtrl    = require('../advisor/crm.controller');
const pool           = require('../../db/pool');
const escalacionLista = require('../../services/escalacionLista.service');
```

- [ ] **Step 2: Replace the escalation activation block**

Current content at lines 130-143:

```javascript
    // Activar escalación
    if (targetManagerId) {
      pool.query(
        `UPDATE crm_leads SET
           escalacion_activa          = true,
           escalacion_manager_id      = $1,
           escalacion_origen_id       = $2,
           escalacion_gerencia_inicio = $1,
           opened_at                  = NULL,
           transferred_at             = NOW()
         WHERE id = $3`,
        [targetManagerId, req.session.user.id, leadId]
      ).catch(err => console.error('[escalacion] activar marketing:', err.message));
    }
```

Replace with:

```javascript
    // Activar escalación
    if (targetManagerId) {
      const advisorInicioId = await escalacionLista.calcularPuntoDePartida(targetUserId);
      pool.query(
        `UPDATE crm_leads SET
           escalacion_activa          = true,
           escalacion_origen_id       = $1,
           escalacion_gerencia_inicio = $2,
           opened_at                  = NULL,
           transferred_at             = NOW()
         WHERE id = $3`,
        [req.session.user.id, advisorInicioId, leadId]
      ).catch(err => console.error('[escalacion] activar marketing:', err.message));
    }
```

- [ ] **Step 3: Commit**

```bash
git add src/controllers/marketing/crm.controller.js
git commit -m "fix: calcular punto de partida de lista global al activar escalacion desde marketing"
```

---

## Task 10: Actualizar `manager/crm.controller.js` — punto de partida correcto

**Files:**
- Modify: `src/controllers/manager/crm.controller.js:4-7` and `:866-877`

- [ ] **Step 1: Add the require for the shared service**

Current content at lines 4-7:

```javascript
const pool           = require('../../db/pool');
const crmService     = require('../../services/advisor/crm.service');
const notifService   = require('../../services/notificaciones.service');
const leadFavService = require('../../services/leadFavoritos.service');
```

Replace with:

```javascript
const pool           = require('../../db/pool');
const crmService     = require('../../services/advisor/crm.service');
const notifService   = require('../../services/notificaciones.service');
const leadFavService = require('../../services/leadFavoritos.service');
const escalacionLista = require('../../services/escalacionLista.service');
```

- [ ] **Step 2: Replace the escalation activation block**

Current content at lines 866-877:

```javascript
      // Activar escalación automática al asignar a asesor
      pool.query(
        `UPDATE crm_leads SET
           escalacion_activa          = true,
           escalacion_manager_id      = $1,
           escalacion_origen_id       = $1,
           escalacion_gerencia_inicio = $1,
           opened_at                  = NULL,
           transferred_at             = NOW()
         WHERE id = $2`,
        [managerId, leadId]
      ).catch(err => console.error('[escalacion] activar manager transfer:', err.message));
```

Replace with:

```javascript
      // Activar escalación automática al asignar a asesor
      const advisorInicioId = await escalacionLista.calcularPuntoDePartida(decision.target.id);
      pool.query(
        `UPDATE crm_leads SET
           escalacion_activa          = true,
           escalacion_origen_id       = $1,
           escalacion_gerencia_inicio = $2,
           opened_at                  = NULL,
           transferred_at             = NOW()
         WHERE id = $3`,
        [managerId, advisorInicioId, leadId]
      ).catch(err => console.error('[escalacion] activar manager transfer:', err.message));
```

- [ ] **Step 3: Commit**

```bash
git add src/controllers/manager/crm.controller.js
git commit -m "fix: calcular punto de partida de lista global al activar escalacion desde manager"
```

---

## Task 11: Pruebas manuales end-to-end (BD local)

**Files:**
- Create: `scripts/test_escalacion_local.js` (temporal, para validar el flujo — no se commitea)

- [ ] **Step 1: Find a real lead id and two adjacent advisors to use for the test**

Run:
```bash
node -e "require('dotenv').config(); const pool=require('./src/db/pool'); pool.query(\"SELECT id, advisor_id, status FROM crm_leads WHERE status='open' LIMIT 1\").then(r=>{console.log(r.rows); pool.end();})"
```

Note the `id` returned — call it `<LEAD_ID>`. (If no open lead exists, create one manually via the marketing/advisor UI first.)

- [ ] **Step 2: Write a script that exercises caso 2 (flujo normal), caso 5 (vuelta completa) y caso 6 (Daniel Rojas → Denisse)**

```javascript
// scripts/test_escalacion_local.js
'use strict';
require('dotenv').config();
const pool = require('../src/db/pool');
const { revisarEscalaciones } = require('../src/services/escalacion.cron');

const LEAD_ID = Number(process.argv[2]);
if (!LEAD_ID) {
  console.error('Uso: node scripts/test_escalacion_local.js <LEAD_ID>');
  process.exit(1);
}

async function setLead(advisorId, inicioId) {
  await pool.query(
    `UPDATE crm_leads SET
       advisor_id = $1,
       escalacion_activa = true,
       escalacion_gerencia_inicio = $2,
       status = 'open',
       transferred_at = NOW() - INTERVAL '6 minutes'
     WHERE id = $3`,
    [advisorId, inicioId, LEAD_ID]
  );
}

async function leerLead() {
  const { rows } = await pool.query(
    `SELECT advisor_id, escalacion_activa, escalacion_gerencia_inicio FROM crm_leads WHERE id = $1`,
    [LEAD_ID]
  );
  return rows[0];
}

async function ultimoHistorial() {
  const { rows } = await pool.query(
    `SELECT advisor_id_anterior, advisor_id_nuevo FROM escalacion_historial
     WHERE lead_id = $1 ORDER BY id DESC LIMIT 1`,
    [LEAD_ID]
  );
  return rows[0];
}

async function activarToggle() {
  await pool.query(
    `INSERT INTO configuracion (clave, valor, descripcion, updated_at)
     VALUES ('escalacion_activa', 'true', 'test', NOW())
     ON CONFLICT (clave) DO UPDATE SET valor = 'true', updated_at = NOW()`
  );
}

(async () => {
  await activarToggle();

  // Caso 2: flujo normal — Orlando (25) -> Victor Garcia (32)
  await setLead(25, 25);
  await revisarEscalaciones();
  console.log('Caso 2 (Orlando -> Victor):', await leerLead(), await ultimoHistorial());

  // Caso 5: vuelta completa — Marco Salazar (43, pos 5) con punto de partida Omar Moreno (8, pos 6)
  // siguiente = Omar Moreno (8) == inicio -> debe ir a Daniel Rojas (35)
  await setLead(43, 8);
  await revisarEscalaciones();
  console.log('Caso 5 (Marco Salazar -> Daniel Rojas):', await leerLead(), await ultimoHistorial());

  // Caso 6: Daniel Rojas (35) -> Denisse Hansen (7), escalacion_activa pasa a false
  await setLead(35, 8);
  await revisarEscalaciones();
  console.log('Caso 6 (Daniel Rojas -> Denisse):', await leerLead(), await ultimoHistorial());

  await pool.end();
})();
```

- [ ] **Step 3: Run the test**

Run: `node scripts/test_escalacion_local.js <LEAD_ID>`

Expected output:
```
Caso 2 (Orlando -> Victor): { advisor_id: 32, escalacion_activa: true, escalacion_gerencia_inicio: 25 } { advisor_id_anterior: 25, advisor_id_nuevo: 32 }
Caso 5 (Marco Salazar -> Daniel Rojas): { advisor_id: 35, escalacion_activa: true, escalacion_gerencia_inicio: 8 } { advisor_id_anterior: 43, advisor_id_nuevo: 35 }
Caso 6 (Daniel Rojas -> Denisse): { advisor_id: 7, escalacion_activa: false, escalacion_gerencia_inicio: 8 } { advisor_id_anterior: 35, advisor_id_nuevo: 7 }
```

If `ESCALACION_MODO_PRUEBA=true` is set in the environment, the queries log `[escalacion:PRUEBA] ... SIMULADO` instead and `crm_leads`/`escalacion_historial` are not modified — unset it (or don't set it) for this test.

- [ ] **Step 4: Caso 7 — lista vacía no escala**

Run:
```bash
node -e "
require('dotenv').config();
const pool=require('./src/db/pool');
const { revisarEscalaciones } = require('./src/services/escalacion.cron');
(async () => {
  await pool.query('UPDATE escalacion_lista_global SET activo = false');
  await pool.query(\"UPDATE crm_leads SET advisor_id=25, escalacion_activa=true, escalacion_gerencia_inicio=25, status='open', transferred_at = NOW() - INTERVAL '6 minutes' WHERE id = $1\", [process.argv[2]]);
  await revisarEscalaciones();
  const { rows } = await pool.query('SELECT advisor_id, escalacion_activa FROM crm_leads WHERE id = $1', [process.argv[2]]);
  console.log('Caso 7 (lista vacia):', rows[0]);
  await pool.query('UPDATE escalacion_lista_global SET activo = true');
  await pool.end();
})();
" <LEAD_ID>
```

Expected: `Caso 7 (lista vacia): { advisor_id: 25, escalacion_activa: true }` — el lead no se movió.

- [ ] **Step 5: Caso 9 — panel admin**

With the server running (`node src/server.js`) and logged in as admin, go to `/admin/configuracion/escalacion-lista` and verify:
- Click "Activada"/"Desactivada" toggles `configuracion.escalacion_activa` (refresh shows the new state).
- Click ↑ on the 2nd row swaps it with the 1st row's position.
- Click "Activo" on a row toggles it to "Inactivo" and the row dims.
- Selecting an advisor from the dropdown and clicking "Agregar a la lista" adds it at the end (next `orden`).
- Click ✕ on a row removes it from the table.

- [ ] **Step 6: Restore test lead state and remove the temporary test script**

Run:
```bash
node -e "require('dotenv').config(); const pool=require('./src/db/pool'); pool.query(\"UPDATE crm_leads SET escalacion_activa = false WHERE id = \$1\", [process.argv[1]]).then(()=>pool.end())" <LEAD_ID>
```

Run (PowerShell):
```powershell
Remove-Item scripts\test_escalacion_local.js -Confirm:$false
```

(No commit for this task — it's verification only.)

---

## Self-Review Notes

- **Spec coverage:** Tablas `escalacion_lista_global` y `escalacion_historial` + seed (Task 1), reuso de `escalacion_gerencia_inicio` y migración de leads activos (Task 1), `obtenerSiguienteAdvisor` con vuelta completa (Task 2/3), registro de historial dentro de la transacción (Task 3), eliminación de `GRUPO_A/B` y lectura/escritura de `escalacion_manager_id` (Task 3, 9, 10), cron sin el filtro temporal `id = 2308` (Task 3), panel admin con las 5 rutas y acciones especificadas (Task 5-8), cálculo de punto de partida al activar desde marketing/manager (Task 9-10), pruebas manuales cubriendo los casos 2, 5, 6, 7 y 9 del spec (Task 11).
- **Out of scope respetado:** no se recrea `recordatorios.cron.js` ni sus crons de citas/llamadas/leads-sin-actividad/purga; no se elimina `escalacion_orden` ni las columnas `escalacion_manager_id`.
- **Consistencia de tipos:** `escalacionLista.service.js` exporta `obtenerListaActiva`, `calcularPuntoDePartida`, `obtenerSiguienteAdvisor`, `FALLBACK_1_ID`, `FALLBACK_2_ID` — usados con los mismos nombres en Tasks 3, 9 y 10. `escalacion.cron.js` exporta `iniciar` (Task 4) y `revisarEscalaciones` (Task 11).
