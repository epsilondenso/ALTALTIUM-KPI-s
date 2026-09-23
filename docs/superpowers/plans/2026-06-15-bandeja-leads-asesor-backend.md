# Bandeja de Leads del Asesor — Backend (Plan 1 de 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir las bases de backend necesarias para el rediseño de la bandeja de leads del asesor: tabla y servicio de "leads fijados", columnas adicionales en `listLeadsByAdvisor` (producto, rol de quien transfirió, fijado), búsqueda por ID, orden por columna y paginación.

**Architecture:** Se reutiliza el patrón existente de `lead_favoritos` para crear `lead_pins` + `leadPins.service.js`. La consulta SQL de `listLeadsByAdvisor` se extiende con JOINs/subqueries adicionales (sin cambiar su forma general). El ordenamiento, filtrado por favoritos/fijados y la paginación se implementan en JavaScript dentro del controlador, sobre el arreglo ya devuelto por el servicio — esto evita interferir con el filtro post-query existente por `estado` (que ya se hace en JS porque `crm_state` es una columna calculada).

**Tech Stack:** Node.js v24, Express v5, PostgreSQL (`pg`), sin framework de testing (verificación manual vía scripts Node puntuales).

**Nota:** Este es el Plan 1 de 2. El Plan 2 (vista EJS: tabla+panel, tarjetas móviles, semáforo, tema oscuro, tab "Leads fijados" en perfil) se escribirá después de completar este plan, ya que requiere referenciar el código resultante de estos cambios.

---

### Task 1: Migración — tabla `lead_pins`

**Files:**
- Create: `scripts/migration_lead_pins.js`

- [ ] **Step 1: Crear el script de migración**

```javascript
// scripts/migration_lead_pins.js
const { Pool } = require('pg');
require('dotenv').config();

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false }
});

(async () => {
  try {
    console.log('🔧 Creando tabla lead_pins...');

    await pool.query(`
      CREATE TABLE IF NOT EXISTS lead_pins (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        lead_id BIGINT NOT NULL REFERENCES crm_leads(id),
        created_at TIMESTAMPTZ DEFAULT now(),
        UNIQUE(user_id, lead_id)
      )
    `);
    console.log('✅ Tabla lead_pins creada');

    const verify = await pool.query(`
      SELECT column_name, data_type, is_nullable
      FROM information_schema.columns
      WHERE table_name = 'lead_pins'
      ORDER BY ordinal_position
    `);

    console.log('\nVerificación:');
    console.table(verify.rows);

    console.log('\n🎉 Migración completa');
  } catch (err) {
    console.error('❌ Error:', err.message);
  } finally {
    await pool.end();
  }
})();
```

- [ ] **Step 2: Ejecutar la migración**

Run: `node scripts/migration_lead_pins.js`
Expected: imprime la tabla `lead_pins` con columnas `id, user_id, lead_id, created_at` y el mensaje "🎉 Migración completa". Si la BD local (.env) es más antigua que Render, ejecutar también contra `DATABASE_URL` de Render (recordar la nota del CLAUDE.md sobre verificar estructura en producción).

- [ ] **Step 3: Commit**

```bash
git add scripts/migration_lead_pins.js
git commit -m "feat: agregar migracion de tabla lead_pins para leads fijados"
```

---

### Task 2: Servicio `leadPins.service.js`

**Files:**
- Create: `src/services/leadPins.service.js`

- [ ] **Step 1: Crear el servicio**

```javascript
'use strict';
const pool = require('../db/pool');

// IDs de leads fijados (para marcar 📍 en la bandeja y ordenarlos primero)
exports.getIdsFijados = async function (userId) {
  const { rows } = await pool.query(
    `SELECT lead_id FROM lead_pins WHERE user_id = $1`,
    [userId]
  );
  return rows.map(r => Number(r.lead_id));
};

// Toggle: si existe lo elimina, si no existe lo crea
exports.togglePin = async function (userId, leadId) {
  const existing = await pool.query(
    `SELECT id FROM lead_pins WHERE user_id = $1 AND lead_id = $2`,
    [userId, leadId]
  );
  if (existing.rows.length > 0) {
    await pool.query(
      `DELETE FROM lead_pins WHERE user_id = $1 AND lead_id = $2`,
      [userId, leadId]
    );
    return { action: 'removed' };
  }
  await pool.query(
    `INSERT INTO lead_pins (user_id, lead_id) VALUES ($1, $2)
     ON CONFLICT (user_id, lead_id) DO NOTHING`,
    [userId, leadId]
  );
  return { action: 'added' };
};

// Leads fijados del usuario con datos completos (para tab "Leads fijados" en perfil)
exports.getLeadsFijados = async function (userId) {
  const { rows } = await pool.query(`
    SELECT
      lp.id          AS pin_id,
      lp.lead_id,
      lp.created_at  AS pin_created_at,
      l.nombre,
      l.apellido,
      l.telefono,
      l.email,
      l.portal,
      l.status,
      l.tipo,
      l.operacion,
      CASE
        WHEN l.sale_paid = true OR (l.sale_signed = true AND l.sale_paid = true) THEN 'won'
        WHEN l.status = 'closed' AND COALESCE(l.sale_paid,false) = false AND COALESCE(l.sale_signed,false) = false THEN 'lost'
        WHEN l.transferred_to IS NOT NULL AND l.status <> 'closed' THEN 'transfer'
        WHEN EXISTS (SELECT 1 FROM crm_lead_profiles p WHERE p.lead_id = l.id) THEN 'followup'
        ELSE 'new'
      END AS crm_state
    FROM lead_pins lp
    JOIN crm_leads l ON l.id = lp.lead_id
    WHERE lp.user_id = $1
    ORDER BY lp.created_at DESC
  `, [userId]);
  return rows;
};

exports.contarFijados = async function (userId) {
  const { rows } = await pool.query(
    `SELECT COUNT(*)::int AS total FROM lead_pins WHERE user_id = $1`,
    [userId]
  );
  return rows[0]?.total || 0;
};
```

- [ ] **Step 2: Verificar que el servicio carga sin errores**

Run: `node -e "const s=require('./src/services/leadPins.service'); console.log(Object.keys(s))"`
Expected: `[ 'getIdsFijados', 'togglePin', 'getLeadsFijados', 'contarFijados' ]`

- [ ] **Step 3: Commit**

```bash
git add src/services/leadPins.service.js
git commit -m "feat: agregar servicio leadPins para leads fijados del asesor"
```

---

### Task 3: Ruta toggle de "fijar" lead

**Files:**
- Modify: `src/routes/profile.routes.js`

- [ ] **Step 1: Importar el nuevo servicio**

En `src/routes/profile.routes.js`, junto al require existente de `leadFavService` (línea 6):

```javascript
const leadFavService  = require('../services/leadFavoritos.service');
const leadPinsService = require('../services/leadPins.service');
```

- [ ] **Step 2: Agregar la ruta de toggle**

Después del bloque `// ── Leads favoritos ──...` (después de la ruta `/leads-favoritos/:leadId/nota`, antes de `// ── CRM legacy ──`), agregar:

```javascript
// ── Leads fijados ──────────────────────────────────────────────────────────

// Toggle (fijar / desfijar)
router.post('/leads-pins/:leadId/toggle', requireLogin, async (req, res) => {
  try {
    const userId = req.session.user.id;
    const leadId = req.params.leadId;
    const result = await leadPinsService.togglePin(userId, leadId);
    return res.json({ ok: true, action: result.action });
  } catch (err) {
    console.error('[leadPins] toggle:', err.message);
    return res.status(500).json({ ok: false });
  }
});
```

- [ ] **Step 3: Verificar la ruta manualmente**

Run: `npm run dev` (deja el servidor corriendo), luego en otra terminal, con sesión iniciada en el navegador, abre las herramientas de desarrollador y ejecuta en la consola del navegador (en cualquier página de `/advisor/...`):

```javascript
fetch('/profile/leads-pins/1/toggle', { method: 'POST', headers: {'Content-Type':'application/json'} })
  .then(r => r.json()).then(console.log)
```

Expected: `{ ok: true, action: 'added' }` la primera vez y `{ ok: true, action: 'removed' }` si se ejecuta de nuevo (sustituir `1` por un ID de lead real del asesor logueado).

- [ ] **Step 4: Commit**

```bash
git add src/routes/profile.routes.js
git commit -m "feat: agregar ruta toggle para fijar/desfijar leads"
```

---

### Task 4: Extender `listLeadsByAdvisor` — producto, rol de transferencia, fijado y búsqueda por ID

**Files:**
- Modify: `src/services/advisor/crm.service.js:315-419`

- [ ] **Step 1: Extender la búsqueda por texto (`filters.q`) para incluir búsqueda por ID**

Ubicar en `src/services/advisor/crm.service.js` (línea 315-319):

```javascript
  if (filters.q && filters.q.trim()) {
    params.push('%' + filters.q.trim() + '%');
    const n = params.length;
    extraWhere.push(`(l.nombre ILIKE $${n} OR l.apellido ILIKE $${n} OR l.telefono ILIKE $${n} OR l.email ILIKE $${n} OR l.portal ILIKE $${n} OR l.colonia ILIKE $${n} OR l.municipio ILIKE $${n})`);
  }
```

Reemplazar por:

```javascript
  if (filters.q && filters.q.trim()) {
    const qTrim = filters.q.trim();
    params.push('%' + qTrim + '%');
    const n = params.length;
    const idMatch = qTrim.match(/^#?(\d+)$/);
    if (idMatch) {
      params.push(Number(idMatch[1]));
      const ni = params.length;
      extraWhere.push(`(l.nombre ILIKE $${n} OR l.apellido ILIKE $${n} OR l.telefono ILIKE $${n} OR l.email ILIKE $${n} OR l.portal ILIKE $${n} OR l.colonia ILIKE $${n} OR l.municipio ILIKE $${n} OR l.id = $${ni})`);
    } else {
      extraWhere.push(`(l.nombre ILIKE $${n} OR l.apellido ILIKE $${n} OR l.telefono ILIKE $${n} OR l.email ILIKE $${n} OR l.portal ILIKE $${n} OR l.colonia ILIKE $${n} OR l.municipio ILIKE $${n})`);
    }
  }
```

- [ ] **Step 2: Agregar columnas `transferred_by_role`, `producto` e `is_pinned` al SELECT**

Ubicar el final del bloque SELECT (líneas 402-403):

```javascript
      last_my.last_contact_summary AS last_contact_summary,
      last_my.last_contact_at AS last_contact_at

    FROM crm_leads l
```

Reemplazar por:

```javascript
      last_my.last_contact_summary AS last_contact_summary,
      last_my.last_contact_at AS last_contact_at,

      u_transfer.role AS transferred_by_role,
      prod_lat.producto AS producto,
      EXISTS (
        SELECT 1 FROM lead_pins lp WHERE lp.lead_id = l.id AND lp.user_id = $1
      ) AS is_pinned

    FROM crm_leads l

    LEFT JOIN users u_transfer ON u_transfer.id = l.transferred_by

    LEFT JOIN LATERAL (
      SELECT a.product AS producto
      FROM crm_activities a
      WHERE a.lead_id = l.id AND a.product IS NOT NULL AND a.product <> ''
      ORDER BY a.created_at DESC NULLS LAST, a.id DESC
      LIMIT 1
    ) prod_lat ON true
```

- [ ] **Step 3: Verificar que la consulta sigue funcionando**

Run:
```bash
node -e "const pool=require('./src/db/pool'); const s=require('./src/services/advisor/crm.service'); s.listLeadsByAdvisor(80, {}).then(r => { console.log('total:', r.length); console.log(r[0] && { id: r[0].id, producto: r[0].producto, transferred_by_role: r[0].transferred_by_role, is_pinned: r[0].is_pinned }); pool.end(); }).catch(e => { console.error(e); pool.end(); })"
```
(sustituir `80` por un `advisor_id` real que tenga leads)

Expected: imprime `total: N` (N > 0) y un objeto con las claves `id`, `producto` (string o `null`), `transferred_by_role` (string o `null`), `is_pinned` (`true`/`false`) — sin errores SQL.

- [ ] **Step 4: Commit**

```bash
git add src/services/advisor/crm.service.js
git commit -m "feat: agregar producto, transferred_by_role e is_pinned a listLeadsByAdvisor y busqueda por ID"
```

---

### Task 5: Controlador `leadsIndex` — filtros rápidos, orden por columna, fijados primero y paginación

**Files:**
- Modify: `src/controllers/advisor/crm.controller.js:9` (import)
- Modify: `src/controllers/advisor/crm.controller.js:196-266` (función `leadsIndex`)

- [ ] **Step 1: Importar el servicio de fijados**

En `src/controllers/advisor/crm.controller.js`, junto a la línea 9:

```javascript
const leadFavService  = require('../../services/leadFavoritos.service');
const leadPinsService = require('../../services/leadPins.service');
```

- [ ] **Step 2: Agregar nuevos parámetros al objeto `filters`**

Ubicar el objeto `filters` dentro de `leadsIndex` (líneas 196-207):

```javascript
    const filters = {
      q:            String(req.query.q || '').trim(),
      desde:        String(req.query.desde || '').trim(),
      hasta:        String(req.query.hasta || '').trim(),
      orden:        req.query.orden === 'asc' ? 'asc' : 'desc',
      estado:       String(req.query.estado || 'all').trim(),
      operacion:    String(req.query.operacion || '').trim(),
      portal:       String(req.query.portal || '').trim(),
      con_actividad: String(req.query.con_actividad || '').trim(),
      con_perfil:   String(req.query.con_perfil || '').trim(),
      preset:       String(req.query.preset || '').trim(),
    };
```

Reemplazar por:

```javascript
    const filters = {
      q:            String(req.query.q || '').trim(),
      desde:        String(req.query.desde || '').trim(),
      hasta:        String(req.query.hasta || '').trim(),
      orden:        req.query.orden === 'asc' ? 'asc' : 'desc',
      estado:       String(req.query.estado || 'all').trim(),
      operacion:    String(req.query.operacion || '').trim(),
      portal:       String(req.query.portal || '').trim(),
      con_actividad: String(req.query.con_actividad || '').trim(),
      con_perfil:   String(req.query.con_perfil || '').trim(),
      preset:       String(req.query.preset || '').trim(),
      page:         Math.max(1, parseInt(req.query.page, 10) || 1),
      orden_campo:  String(req.query.orden_campo || '').trim(),
      orden_dir:    req.query.orden_dir === 'asc' ? 'asc' : 'desc',
      fav:          req.query.fav === '1',
      fijado:       req.query.fijado === '1',
    };
```

- [ ] **Step 3: Aplicar filtros rápidos, orden por columna, fijados primero y paginación**

Ubicar el bloque donde se obtienen los leads y se construye `result` (líneas 224-226):

```javascript
    const leads = await crmService.listLeadsByAdvisor(advisorId, filters);
    const kpis  = await crmService.getLeadsKpisByAdvisor(advisorId);
    const result = { items: Array.isArray(leads) ? leads : [] };
```

Reemplazar por:

```javascript
    const leads = await crmService.listLeadsByAdvisor(advisorId, filters);
    const kpis  = await crmService.getLeadsKpisByAdvisor(advisorId);

    const idsFavoritosForFilter = await leadFavService.getIdsFavoritos(advisorId).catch(() => []);
    const idsFijados = await leadPinsService.getIdsFijados(advisorId).catch(() => []);

    let pageableLeads = Array.isArray(leads) ? leads : [];

    if (filters.fav) {
      pageableLeads = pageableLeads.filter(l => idsFavoritosForFilter.includes(Number(l.id)));
    }
    if (filters.fijado) {
      pageableLeads = pageableLeads.filter(l => idsFijados.includes(Number(l.id)));
    }

    const ORDER_FIELDS = {
      lead: l => `${l.nombre || ''} ${l.apellido || ''}`.trim().toLowerCase(),
      creado: l => l.created_at ? new Date(l.created_at).getTime() : 0,
      precio: l => (l.precio != null ? Number(l.precio) : -Infinity),
      ultimo_contacto: l => (l.last_contact_at ? new Date(l.last_contact_at).getTime() : -Infinity),
      sin_contacto: l => {
        const ref = l.last_contact_at || l.transferred_at || l.created_at;
        return ref ? new Date(ref).getTime() : -Infinity;
      },
    };

    if (filters.orden_campo && ORDER_FIELDS[filters.orden_campo]) {
      const getKey = ORDER_FIELDS[filters.orden_campo];
      const dir = filters.orden_dir === 'asc' ? 1 : -1;
      pageableLeads = [...pageableLeads].sort((a, b) => {
        const ka = getKey(a), kb = getKey(b);
        if (ka < kb) return -1 * dir;
        if (ka > kb) return 1 * dir;
        return 0;
      });
    }

    // Leads fijados siempre primero (orden estable, preserva el orden anterior dentro de cada grupo)
    pageableLeads = [...pageableLeads].sort((a, b) => (b.is_pinned === true ? 1 : 0) - (a.is_pinned === true ? 1 : 0));

    const PAGE_SIZE = 20;
    const totalItems = pageableLeads.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
    const currentPage = Math.min(filters.page, totalPages);
    const pageItems = pageableLeads.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

    const result = { items: pageItems };
```

- [ ] **Step 4: Pasar las nuevas variables a la vista**

Ubicar el `return res.render(...)` de `leadsIndex` (líneas 255-266):

```javascript
    return res.render('advisor/crm/leads/index', {
      title: 'Bandeja de Leads',
      path: '/advisor/leads',
      user: req.session.user,
      result,
      stats,
      kpis,
      leads,
      filters,
      portales: portalesRows.map(r => r.portal),
      idsFavoritos,
    });
```

Reemplazar por:

```javascript
    return res.render('advisor/crm/leads/index', {
      title: 'Bandeja de Leads',
      path: '/advisor/leads',
      user: req.session.user,
      result,
      stats,
      kpis,
      leads: pageItems,
      filters,
      portales: portalesRows.map(r => r.portal),
      idsFavoritos,
      idsFijados,
      page: currentPage,
      totalPages,
      totalItems,
    });
```

- [ ] **Step 5: Verificar en el navegador**

Run: `npm run dev`, luego abrir `/advisor/leads` con sesión de asesor iniciada.

Expected: la página carga sin errores 500 y muestra los leads como antes (el comportamiento visual no cambia todavía — los cambios de vista van en el Plan 2). Probar también `/advisor/leads?q=421` (con un ID real de 3 dígitos) y confirmar que no rompe la búsqueda existente, y `/advisor/leads?page=2` no debe causar error aunque la página 2 esté vacía.

- [ ] **Step 6: Commit**

```bash
git add src/controllers/advisor/crm.controller.js
git commit -m "feat: agregar filtros de favoritos/fijados, orden por columna y paginacion a leadsIndex"
```

---

## Siguientes pasos

Con este backend listo, el **Plan 2** cubrirá:
- Rediseño de `views/advisor/crm/leads/index.ejs` (tabla + panel lateral, columnas Creado/Precio/Producto, semáforo, badges Propio/Marketing/Escalado, botones ★/📍 con toasts, orden por encabezado, paginación visual, tarjetas móviles/tablet, tema claro/oscuro)
- Tab "Leads fijados" en `views/profile/index.ejs`

Ese plan se escribirá leyendo el resultado de este Plan 1 y el archivo `index.ejs` actual completo, ya que requiere referencias de código exactas sección por sección.
