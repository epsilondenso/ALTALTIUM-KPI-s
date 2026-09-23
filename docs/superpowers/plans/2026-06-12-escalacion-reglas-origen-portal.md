# Reglas de origen marketing y portal para el cron de escalación — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** El cron de escalación (`revisarEscalaciones()`, cada minuto) solo debe escalar leads cuya escalación fue activada por un usuario de marketing (`escalacion_origen_id` → role `marketing`) y cuyo `portal` no sea `'Cartera'` ni `NULL`.

**Architecture:** Cambio de una sola consulta SQL en `src/services/escalacion.cron.js`. Se agregan dos condiciones al `WHERE` existente de `revisarEscalaciones()`. No se modifica `escalarLead()`, `transferirLead()`, ni ningún otro archivo. No hay migración de esquema ni datos.

**Tech Stack:** Node.js v24, PostgreSQL (`pg`), `node-cron`.

---

## ⚠️ Antes de empezar

- **NO hacer commit hasta que el usuario lo autorice explícitamente** — instrucción permanente del usuario para esta sesión. El Task 1 incluye un paso de commit; ejecútalo solo si el usuario ya dio luz verde para ese commit específico. Si no, deja el cambio sin commitear y avisa que está listo.
- Ya existen cambios sin commitear en `src/services/escalacion.cron.js` (flag `ejecutando`) y en `src/controllers/admin/escalacion.controller.js` de una tarea anterior — **no los toques ni los deshagas**. Este plan agrega un cambio adicional encima de esos.
- El servidor local puede estar corriendo con un cron activo (`escalacion_activa` global toggle). Antes de crear leads de prueba que activen escalación real, verifica el estado del toggle (`SELECT valor FROM configuracion WHERE clave = 'escalacion_activa'`) y considera usar `ESCALACION_MODO_PRUEBA=true` o ajustar `transferred_at` manualmente como se hizo en la sesión anterior, para no disparar transferencias reales sobre leads de producción/reales.

---

### Task 1: Agregar filtros de origen-marketing y portal al cron de escalación

**Files:**
- Modify: `src/services/escalacion.cron.js:220-233`

- [ ] **Step 1: Leer el estado actual de la consulta**

Confirma que el bloque de la consulta en `revisarEscalaciones()` es exactamente:

```javascript
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
```

Si el bloque difiere (por ejemplo por el flag `ejecutando` ya aplicado alrededor), ubica este `pool.query` dentro de `revisarEscalaciones()` — debe ser el único `SELECT ... FROM crm_leads` de la función.

- [ ] **Step 2: Agregar las dos condiciones nuevas al `WHERE`**

Reemplaza el bloque completo de la consulta por:

```javascript
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

- [ ] **Step 3: Verificar que el archivo carga sin errores de sintaxis**

Run:
```
node -e "require('dotenv').config(); require('./src/services/escalacion.cron'); console.log('OK')"
```
Expected output: `OK`

- [ ] **Step 4: Validar manualmente con leads de prueba en BD local**

Esto NO requiere reiniciar el servidor si solo se valida la consulta SQL directamente (más rápido y sin riesgo de transferencias reales). Crea un script temporal `scripts/tmp_check_filtro_escalacion.js`:

```javascript
require('dotenv').config();
const pool = require('./src/db/pool');

(async () => {
  // 1. Buscar un usuario marketing y un usuario manager existentes para las pruebas
  const { rows: marketingUsers } = await pool.query(
    `SELECT id, nombre FROM users WHERE role = 'marketing' AND is_active = true LIMIT 1`
  );
  const { rows: managerUsers } = await pool.query(
    `SELECT id, nombre FROM users WHERE role = 'manager' AND is_active = true LIMIT 1`
  );
  console.log('Usuario marketing de prueba:', marketingUsers[0]);
  console.log('Usuario manager de prueba:', managerUsers[0]);

  const marketingId = marketingUsers[0].id;
  const managerId = managerUsers[0].id;

  // 2. Crear 3 leads de prueba con distintos escenarios
  //    A: origen marketing + portal Inmuebles24 -> DEBE aparecer en el filtro
  //    B: origen marketing + portal Cartera      -> NO debe aparecer
  //    C: origen manager   + portal Inmuebles24  -> NO debe aparecer
  const { rows: inserted } = await pool.query(
    `INSERT INTO crm_leads
       (nombre, apellido, telefono, advisor_id, status, escalacion_activa,
        escalacion_origen_id, escalacion_gerencia_inicio, portal,
        transferred_at, created_at, updated_at)
     VALUES
       ('PRUEBA FILTRO A', 'Marketing-Inmuebles24', '0000000001', $2, 'open', true, $1, $2, 'Inmuebles24', NOW() - INTERVAL '6 minutes', NOW(), NOW()),
       ('PRUEBA FILTRO B', 'Marketing-Cartera',     '0000000002', $2, 'open', true, $1, $2, 'Cartera',     NOW() - INTERVAL '6 minutes', NOW(), NOW()),
       ('PRUEBA FILTRO C', 'Manager-Inmuebles24',   '0000000003', $2, 'open', true, $3, $2, 'Inmuebles24', NOW() - INTERVAL '6 minutes', NOW(), NOW())
     RETURNING id, apellido`,
    [marketingId, managerId, managerId]
  );
  console.log('Leads creados:', inserted);

  // 3. Ejecutar la consulta del cron (con los filtros nuevos) y mostrar cuáles aplican
  const { rows: elegibles } = await pool.query(
    `SELECT id, apellido FROM crm_leads
     WHERE escalacion_activa = true
       AND status = 'open'
       AND advisor_id != $1
       AND transferred_at < NOW() - INTERVAL '5 minutes'
       AND portal IS NOT NULL AND portal <> 'Cartera'
       AND EXISTS (
         SELECT 1 FROM users u
         WHERE u.id = crm_leads.escalacion_origen_id AND u.role = 'marketing'
       )
       AND NOT EXISTS (
         SELECT 1 FROM crm_activities a
         WHERE a.lead_id = crm_leads.id AND a.created_at > crm_leads.transferred_at
       )
       AND id = ANY($2)`,
    [7, inserted.map(r => r.id)]
  );
  console.log('Leads que pasan el filtro (debe ser SOLO "Marketing-Inmuebles24"):', elegibles);

  // 4. Limpieza
  await pool.query(`DELETE FROM crm_leads WHERE id = ANY($1)`, [inserted.map(r => r.id)]);
  console.log('Leads de prueba eliminados.');

  await pool.end();
})().catch(err => { console.error(err); process.exit(1); });
```

Run:
```
node scripts/tmp_check_filtro_escalacion.js
```

Expected output: la lista `elegibles` contiene **únicamente** el lead `Marketing-Inmuebles24` (escenario A). Los escenarios B (Cartera) y C (origen manager) no deben aparecer.

> Nota: `advisor_id != $1` usa `$1 = 7` (FALLBACK_2_ID, Denisse Hansen) — los 3 leads de prueba usan `managerId` como `advisor_id`, que no debe ser 7 (si por coincidencia el manager de prueba tiene id 7, cambia el `advisor_id` de los 3 INSERTs a otro id de advisor activo).

- [ ] **Step 5: Borrar el script temporal**

```
del scripts\tmp_check_filtro_escalacion.js
```

(El script ya borra los leads de prueba en su Step 4; este paso solo limpia el archivo temporal del repo.)

- [ ] **Step 6: Commit (solo si el usuario autoriza este commit específico)**

```bash
git add src/services/escalacion.cron.js
git commit -m "feat: cron de escalacion solo procesa leads de origen marketing sin portal Cartera"
```

---

## Self-Review

- **Cobertura del spec:**
  - Regla 1 (origen marketing) → Step 2, `EXISTS (... role = 'marketing')`. ✅
  - Regla 2 (portal ≠ Cartera, no NULL) → Step 2, `portal IS NOT NULL AND portal <> 'Cartera'`. ✅
  - Regla 3 (sin contacto del advisor) → ya existente, sin cambios. ✅
  - Regla 4 (3 días estancado) → explícitamente fuera de alcance, no requiere tarea. ✅
  - Casos límite (NULL origen, NULL portal, origen manager, leads en curso, fallbacks) → cubiertos por el comportamiento natural de la consulta (Step 2) y validados en Step 4 (escenarios A/B/C). ✅
- **Placeholders:** ninguno — todo el código está completo y ejecutable.
- **Consistencia:** nombres de columnas (`escalacion_origen_id`, `portal`, `escalacion_activa`, `transferred_at`) coinciden con el spec y con el esquema confirmado de `crm_leads`.
