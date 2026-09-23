# CRM Data Integrity Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir 5 problemas de integridad y mantenibilidad detectados en la auditoría del sistema CRM de perfilamiento.

**Architecture:** Cuatro cambios de código (service, controller, 2 vistas) más una migración SQL. Ningún cambio altera el comportamiento visible para el usuario final; todos son correcciones de robustez, semántica y prevención de errores silenciosos.

**Tech Stack:** Node.js v24, Express v5, PostgreSQL (pool de `src/db.js`), EJS server-side rendering.

---

## Problemas que resuelve este plan

| # | Severidad | Descripción |
|---|---|---|
| A | CRÍTICO | Parámetros SQL `$40–$44` fuera de orden en `upsertLeadProfile` — funciona hoy pero imposible de auditar/mantener |
| B | ALTO | `_saveResVenderPropertyProfile` no incluye `created_at` en el INSERT — si la columna no tiene `DEFAULT NOW()` el primer guardado falla silenciosamente |
| C | ALTO | Columnas `arrendatario_comision_tipo` y `arrendatario_comision_valor` tienen nombres invertidos (la primera guarda el monto, la segunda el porcentaje) |
| D | ALTO | `res_v_pp` (datos de propiedad Residencial Vender) depende 100% de JS sin log de error cuando llega vacío |
| E | MEDIO | `arq_servicios_contratados` JSON parse tiene `catch(e) {}` vacío — error silencioso que en el siguiente guardado sobreescribe los servicios con `{}` |

---

## Archivos que se modifican

| Archivo | Razón |
|---|---|
| `src/services/advisor/crm.service.js:699–863` | Fix A + Fix C: reordenar params SQL + renombrar columnas arrendatario |
| `src/controllers/advisor/crm.controller.js:1927–1969` | Fix B: agregar `created_at` al INSERT |
| `src/controllers/advisor/crm.controller.js:743–748` | Fix D: log de advertencia para `res_v_pp` vacío |
| `views/advisor/crm/leads/profile.ejs:279,289,4319` | Fix C + E: actualizar pre-población arrendatario + warn en parse |
| `views/advisor/crm/leads/show.ejs:656–657` | Fix C: actualizar nombres de columna en display |
| Script SQL de migración (se ejecuta en Render) | Fix C: renombrar columnas en BD |

---

## Task 1: Migración SQL — renombrar columnas arrendatario

**Contexto:** Las columnas `arrendatario_comision_tipo` y `arrendatario_comision_valor` tienen nombres que no corresponden a lo que guardan (monto numérico y porcentaje respectivamente). `RENAME COLUMN` en PostgreSQL es instantáneo y no requiere reescribir datos.

**Files:**
- Create: `scripts/migration_rename_arrendatario_cols.sql`

- [ ] **Step 1: Crear el script de migración**

Crear el archivo `scripts/migration_rename_arrendatario_cols.sql` con este contenido exacto:

```sql
-- Renombra columnas de arrendatario que tenían nombres semánticamente invertidos.
-- arrendatario_comision_tipo  contenía el MONTO (número)
-- arrendatario_comision_valor contenía el PORCENTAJE (número)
-- Esta migración solo renombra; los datos existentes quedan intactos.

BEGIN;

ALTER TABLE crm_lead_profiles
  RENAME COLUMN arrendatario_comision_tipo  TO arrendatario_comision_monto;

ALTER TABLE crm_lead_profiles
  RENAME COLUMN arrendatario_comision_valor TO arrendatario_comision_porcentaje;

COMMIT;
```

- [ ] **Step 2: Ejecutar la migración en la BD de Render**

Conectarse a Render → pestaña "Shell" del servicio, luego:

```bash
psql $DATABASE_URL -f scripts/migration_rename_arrendatario_cols.sql
```

Salida esperada:
```
BEGIN
ALTER TABLE
ALTER TABLE
COMMIT
```

- [ ] **Step 3: Verificar la migración**

```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'crm_lead_profiles'
  AND column_name IN (
    'arrendatario_hay_comision',
    'arrendatario_comision_monto',
    'arrendatario_comision_porcentaje'
  )
ORDER BY column_name;
```

Resultado esperado: 3 filas con los nuevos nombres. Si aparece `arrendatario_comision_tipo` o `arrendatario_comision_valor`, la migración no corrió.

- [ ] **Step 4: Commit del script**

```bash
git add scripts/migration_rename_arrendatario_cols.sql
git commit -m "fix(db): renombrar arrendatario_comision_tipo/_valor a _monto/_porcentaje"
```

---

## Task 2: Fix A + C en crm.service.js — reordenar params y actualizar nombres de columna

**Contexto:** La función `upsertLeadProfile` tiene dos problemas en la misma zona:
1. Los parámetros `$40–$44` aparecen antes de `$22` en el VALUES, aunque ambos son correctos para PostgreSQL. Se reordena para que sea `$1…$47` secuencial.
2. Las columnas `arrendatario_comision_tipo` y `arrendatario_comision_valor` se renombraron en Task 1; aquí se actualizan las referencias en código.

**Files:**
- Modify: `src/services/advisor/crm.service.js:699–863`

- [ ] **Step 1: Reemplazar el bloque SQL + values en `upsertLeadProfile`**

Localizar desde la línea `const q = \`` (línea ~699) hasta el cierre `];` del array values (línea ~863). Reemplazar **todo** ese bloque con:

```javascript
  const q = `
    INSERT INTO crm_lead_profiles (
      lead_id,
      zona_interes, motivo, motivo_otro, urgencia,
      tipo_cliente, propiedad_interes, interes_principal,
      objeciones, notas_llamada, rango_edad,

      budget_mode,
      credit_status, credit_source,
      credit_other_text, credit_bank_name,
      credit_personal_amount, credit_institution_name,
      own_amount,
      mix_own_amount, mix_credit_amount,
      mix_credit_status, mix_credit_source, mix_credit_bank,
      mix_credit_institution, mix_credit_other,

      is_complete,
      producto,
      broker_comision, broker_monto, broker_porcentaje,
      tipo_arrendamiento,
      propiedad_interes_2, propiedad_interes_2_id,
      propiedad_interes_3, propiedad_interes_3_id,
      disponibilidad_inversion, rendimiento_esperado, proyecto_interes,
      arq_servicios_contratados,
      rol_arrendatario, arrendatario_hay_comision,
      arrendatario_comision_monto, arrendatario_comision_porcentaje,
      tipo_servicio, objetivo_negociacion,
      propiedad_interes_id,
      created_at, updated_at
    )
    VALUES (
      $1,
      $2,$3,$4,$5,
      $6,$7,$8,
      $9,$10,$11,
      $12,
      $13,$14,
      $15,$16,
      $17,$18,
      $19,
      $20,$21,
      $22,$23,$24,$25,$26,
      $27,
      $28,$29,$30,$31,$32,$33,$34,$35,$36,
      $37,$38,$39,
      $40,
      $41,$42,$43,$44,
      $45,$46,
      $47,
      NOW(), NOW()
    )
    ON CONFLICT (lead_id)
    DO UPDATE SET
      zona_interes = EXCLUDED.zona_interes,
      motivo = EXCLUDED.motivo,
      motivo_otro = EXCLUDED.motivo_otro,
      urgencia = EXCLUDED.urgencia,
      tipo_cliente = EXCLUDED.tipo_cliente,
      propiedad_interes = EXCLUDED.propiedad_interes,
      interes_principal = EXCLUDED.interes_principal,
      objeciones = EXCLUDED.objeciones,
      notas_llamada = EXCLUDED.notas_llamada,
      rango_edad = EXCLUDED.rango_edad,

      budget_mode = EXCLUDED.budget_mode,
      credit_status = EXCLUDED.credit_status,
      credit_source = EXCLUDED.credit_source,
      credit_other_text = EXCLUDED.credit_other_text,
      credit_bank_name = EXCLUDED.credit_bank_name,
      credit_personal_amount = EXCLUDED.credit_personal_amount,
      credit_institution_name = EXCLUDED.credit_institution_name,
      own_amount = EXCLUDED.own_amount,
      mix_own_amount = EXCLUDED.mix_own_amount,
      mix_credit_amount = EXCLUDED.mix_credit_amount,
      mix_credit_status = EXCLUDED.mix_credit_status,
      mix_credit_source = EXCLUDED.mix_credit_source,
      mix_credit_bank = EXCLUDED.mix_credit_bank,
      mix_credit_institution = EXCLUDED.mix_credit_institution,
      mix_credit_other = EXCLUDED.mix_credit_other,

      is_complete = EXCLUDED.is_complete,
      producto             = EXCLUDED.producto,
      broker_comision      = EXCLUDED.broker_comision,
      broker_monto         = EXCLUDED.broker_monto,
      broker_porcentaje    = EXCLUDED.broker_porcentaje,
      tipo_arrendamiento   = EXCLUDED.tipo_arrendamiento,
      propiedad_interes_2  = EXCLUDED.propiedad_interes_2,
      propiedad_interes_2_id = EXCLUDED.propiedad_interes_2_id,
      propiedad_interes_3  = EXCLUDED.propiedad_interes_3,
      propiedad_interes_3_id = EXCLUDED.propiedad_interes_3_id,
      disponibilidad_inversion      = EXCLUDED.disponibilidad_inversion,
      rendimiento_esperado          = EXCLUDED.rendimiento_esperado,
      proyecto_interes              = EXCLUDED.proyecto_interes,
      arq_servicios_contratados     = EXCLUDED.arq_servicios_contratados,
      rol_arrendatario              = EXCLUDED.rol_arrendatario,
      arrendatario_hay_comision     = EXCLUDED.arrendatario_hay_comision,
      arrendatario_comision_monto        = EXCLUDED.arrendatario_comision_monto,
      arrendatario_comision_porcentaje   = EXCLUDED.arrendatario_comision_porcentaje,
      tipo_servicio                 = EXCLUDED.tipo_servicio,
      objetivo_negociacion          = EXCLUDED.objetivo_negociacion,
      propiedad_interes_id          = EXCLUDED.propiedad_interes_id,
      updated_at = NOW()
    RETURNING lead_id
  `;

  const values = [
    toId(leadId),                    // $1

    toNull(data.zona_interes),       // $2
    toNull(data.motivo),             // $3
    toNull(data.motivo_otro),        // $4
    toNull(data.urgencia),           // $5

    toNull(data.tipo_cliente),       // $6
    toNull(data.propiedad_interes),  // $7
    toNull(data.interes_principal),  // $8

    toNull(data.objeciones),         // $9
    toNull(data.notas_llamada),      // $10
    toNull(data.rango_edad),         // $11

    budget_mode,                     // $12
    credit_status,                   // $13
    credit_source,                   // $14
    credit_other_text,               // $15
    credit_bank_name,                // $16
    credit_personal_amount,          // $17
    credit_institution_name,         // $18
    own_amount,                      // $19
    mix_own_amount,                  // $20
    mix_credit_amount,               // $21

    mix_credit_status,               // $22
    mix_credit_source,               // $23
    mix_credit_bank,                 // $24
    mix_credit_institution,          // $25
    mix_credit_other,                // $26

    toBool(data.is_complete),                                                              // $27
    toNull(data.producto),                                                                 // $28
    toBool(data.broker_comision),                                                          // $29
    data.broker_monto      ? Number(data.broker_monto.toString().replace(/[^\d.]/g,''))      || null : null, // $30
    data.broker_porcentaje ? Number(data.broker_porcentaje.toString().replace(/[^\d.]/g,'')) || null : null, // $31
    toNull(data.tipo_arrendamiento),                                                       // $32
    toNull(data.propiedad_interes_2),                                                      // $33
    toId(data.propiedad_interes_2_id),                                                     // $34
    toNull(data.propiedad_interes_3),                                                      // $35
    toId(data.propiedad_interes_3_id),                                                     // $36
    toNull(data.disponibilidad_inversion),                                                 // $37
    toNull(data.rendimiento_esperado),                                                     // $38
    toNull(data.proyecto_interes),                                                         // $39
    toNull(data.arq_servicios_contratados),                                                // $40
    toNull(data.rol_arrendatario),                                                         // $41
    (data.arrendatario_comision === 'true' ? 'true' : null),                               // $42
    data.arrendatario_monto
      ? Number(String(data.arrendatario_monto).replace(/[^\d.]/g,'')) || null
      : null,                                                                               // $43
    data.arrendatario_porcentaje
      ? Number(String(data.arrendatario_porcentaje).replace(/[^\d.]/g,'')) || null
      : null,                                                                               // $44
    toNull(data.tipo_servicio),                                                            // $45
    toNull(data.objetivo_negociacion),                                                     // $46
    toId(data.propiedad_interes_id),                                                       // $47
  ];
```

- [ ] **Step 2: Verificar el conteo de parámetros**

Contar que:
- El array `values` tiene exactamente **47 entradas** (de `$1` a `$47`)
- El VALUES clause usa `$1` a `$47` en orden estrictamente creciente
- No hay `$40,$41,$42,$43,$44` antes de `$22` en el nuevo código

- [ ] **Step 3: Commit**

```bash
git add src/services/advisor/crm.service.js
git commit -m "fix(crm-service): reordenar params SQL $1-$47 y renombrar cols arrendatario_comision"
```

---

## Task 3: Fix B en crm.controller.js — agregar `created_at` a `_saveResVenderPropertyProfile`

**Contexto:** El INSERT en `_saveResVenderPropertyProfile` (línea ~1927) incluye `updated_at` como `NOW()` pero omite `created_at`. Si la columna `created_at` de la tabla `crm_lead_property_profiles_residencial` no tiene `DEFAULT NOW()`, el primer INSERT fallará y los datos de la propiedad se perderán silenciosamente.

**Files:**
- Modify: `src/controllers/advisor/crm.controller.js:1927–1934`

- [ ] **Step 1: Agregar `created_at` al INSERT**

Localizar la función `_saveResVenderPropertyProfile` (~línea 1918). Reemplazar el bloque del INSERT SQL:

**Antes:**
```javascript
  await pool.query(`
    INSERT INTO crm_lead_property_profiles_residencial
      (lead_id, tipo_propiedad, uso_suelo, antiguedad,
       calle, numero_exterior, numero_interior, cp, colonia, municipio, estado,
       chars_recamaras, chars_banos, chars_medio_banos, chars_estacionamientos,
       edificio_num_deptos, edificio_niveles, edificio_locales, edificio_num_locales,
       terreno_m2, construccion_m2, amenidades, updated_at)
    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,NOW())
    ON CONFLICT (lead_id) DO UPDATE SET
```

**Después:**
```javascript
  await pool.query(`
    INSERT INTO crm_lead_property_profiles_residencial
      (lead_id, tipo_propiedad, uso_suelo, antiguedad,
       calle, numero_exterior, numero_interior, cp, colonia, municipio, estado,
       chars_recamaras, chars_banos, chars_medio_banos, chars_estacionamientos,
       edificio_num_deptos, edificio_niveles, edificio_locales, edificio_num_locales,
       terreno_m2, construccion_m2, amenidades, created_at, updated_at)
    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,NOW(),NOW())
    ON CONFLICT (lead_id) DO UPDATE SET
```

El resto del ON CONFLICT DO UPDATE no cambia.

- [ ] **Step 2: Commit**

```bash
git add src/controllers/advisor/crm.controller.js
git commit -m "fix(crm-controller): agregar created_at al INSERT de residencial vender property profile"
```

---

## Task 4: Fix D en crm.controller.js — log de advertencia para `res_v_pp` vacío

**Contexto:** Si JavaScript falla en el cliente, el campo oculto `res_v_pp` llega vacío al servidor y los datos de la propiedad (recámaras, baños, dirección, etc.) se pierden silenciosamente. Agregar un `console.warn` en el servidor permite detectar este caso en los logs de Render.

**Files:**
- Modify: `src/controllers/advisor/crm.controller.js:743–748`

- [ ] **Step 1: Agregar log de advertencia**

Localizar el bloque de guardado de Residencial Vender (~línea 743). Reemplazar:

**Antes:**
```javascript
    // Si el lead es Residencial Vender, persistir perfil de la propiedad
    if ((lead.producto || '').trim() === 'Residencial' &&
        (lead.operacion || '').toLowerCase().trim() === 'vender') {
      try { await _saveResVenderPropertyProfile(leadId, req.body || {}); }
      catch (e) { console.error('[profileSave] residencial vender property profile:', e.message); }
    }
```

**Después:**
```javascript
    // Si el lead es Residencial Vender, persistir perfil de la propiedad
    if ((lead.producto || '').trim() === 'Residencial' &&
        (lead.operacion || '').toLowerCase().trim() === 'vender') {
      const rvPp = (req.body || {}).res_v_pp;
      if (!rvPp || rvPp === '{}' || rvPp === '') {
        console.warn(`[profileSave] lead ${leadId}: res_v_pp vacío — JS del cliente puede no haber corrido`);
      }
      try { await _saveResVenderPropertyProfile(leadId, req.body || {}); }
      catch (e) { console.error('[profileSave] residencial vender property profile:', e.message); }
    }
```

- [ ] **Step 2: Commit**

```bash
git add src/controllers/advisor/crm.controller.js
git commit -m "fix(crm-controller): agregar warn cuando res_v_pp llega vacío en Residencial Vender"
```

---

## Task 5: Fix C en profile.ejs — actualizar pre-población arrendatario

**Contexto:** El formulario pre-popula los campos de monto y porcentaje de arrendatario leyendo las columnas antiguas `arrendatario_comision_tipo` y `arrendatario_comision_valor`. Tras la migración SQL (Task 1), la BD devuelve esas mismas columnas con los nombres nuevos. Actualizar las referencias en el formulario.

**Files:**
- Modify: `views/advisor/crm/leads/profile.ejs:279,289`

- [ ] **Step 1: Actualizar pre-población del campo monto arrendatario (línea ~279)**

Localizar el input `name="arrendatario_monto"`. Reemplazar el atributo `value`:

**Antes:**
```ejs
value="<%= profile?.arrendatario_comision_tipo ? Number(profile.arrendatario_comision_tipo).toLocaleString('es-MX') : '' %>"
```

**Después:**
```ejs
value="<%= profile?.arrendatario_comision_monto ? Number(profile.arrendatario_comision_monto).toLocaleString('es-MX') : '' %>"
```

- [ ] **Step 2: Actualizar pre-población del campo porcentaje arrendatario (línea ~289)**

Localizar el input `name="arrendatario_porcentaje"`. Reemplazar el atributo `value`:

**Antes:**
```ejs
value="<%= profile?.arrendatario_comision_valor || '' %>"
```

**Después:**
```ejs
value="<%= profile?.arrendatario_comision_porcentaje || '' %>"
```

- [ ] **Step 3: Fix E — agregar console.warn en catch de arq_servicios (línea ~4319)**

Localizar:
```javascript
      try { arqServicios = JSON.parse(arqServiciosHidden.value) || {}; } catch(e) {}
```

Reemplazar con:
```javascript
      try { arqServicios = JSON.parse(arqServiciosHidden.value) || {}; } catch(e) {
        console.warn('[arq_servicios] JSON malformado, se inicia vacío:', e.message);
        arqServicios = {};
      }
```

- [ ] **Step 4: Commit**

```bash
git add views/advisor/crm/leads/profile.ejs
git commit -m "fix(profile): actualizar pre-población arrendatario a nuevos nombres de columna + warn arq JSON"
```

---

## Task 6: Fix C en show.ejs — actualizar display arrendatario

**Contexto:** Show.ejs muestra el monto y porcentaje de comisión del arrendatario leyendo las columnas antiguas. Actualizar a los nuevos nombres.

**Files:**
- Modify: `views/advisor/crm/leads/show.ejs:656–657`

- [ ] **Step 1: Actualizar columna monto (línea ~656)**

Localizar:
```ejs
<% if (_arrComision && profile.arrendatario_comision_tipo) { %><div>...$<%= Number(profile.arrendatario_comision_tipo).toLocaleString('es-MX') %>...
```

Reemplazar `arrendatario_comision_tipo` por `arrendatario_comision_monto` en esa línea (aparece dos veces):

**Antes:**
```ejs
<% if (_arrComision && profile.arrendatario_comision_tipo) { %><div><p class="text-xs text-slate-400 uppercase tracking-wide font-medium mb-1">Monto comisión arrend.</p><p class="text-sm text-slate-800 bg-slate-50 rounded-md px-2 py-1.5 border border-slate-100 min-h-[30px]">$<%= Number(profile.arrendatario_comision_tipo).toLocaleString('es-MX') %></p></div><% } %>
```

**Después:**
```ejs
<% if (_arrComision && profile.arrendatario_comision_monto) { %><div><p class="text-xs text-slate-400 uppercase tracking-wide font-medium mb-1">Monto comisión arrend.</p><p class="text-sm text-slate-800 bg-slate-50 rounded-md px-2 py-1.5 border border-slate-100 min-h-[30px]">$<%= Number(profile.arrendatario_comision_monto).toLocaleString('es-MX') %></p></div><% } %>
```

- [ ] **Step 2: Actualizar columna porcentaje (línea ~657)**

**Antes:**
```ejs
<% if (_arrComision && profile.arrendatario_comision_valor) { %><div><p class="text-xs text-slate-400 uppercase tracking-wide font-medium mb-1">Porcentaje comisión arrend.</p><p class="text-sm text-slate-800 bg-slate-50 rounded-md px-2 py-1.5 border border-slate-100 min-h-[30px]"><%= profile.arrendatario_comision_valor %>%</p></div><% } %>
```

**Después:**
```ejs
<% if (_arrComision && profile.arrendatario_comision_porcentaje) { %><div><p class="text-xs text-slate-400 uppercase tracking-wide font-medium mb-1">Porcentaje comisión arrend.</p><p class="text-sm text-slate-800 bg-slate-50 rounded-md px-2 py-1.5 border border-slate-100 min-h-[30px]"><%= profile.arrendatario_comision_porcentaje %>%</p></div><% } %>
```

- [ ] **Step 3: Commit**

```bash
git add views/advisor/crm/leads/show.ejs
git commit -m "fix(show): actualizar display arrendatario_comision a nuevos nombres de columna"
```

---

## Task 7: Push a main y verificación

- [ ] **Step 1: Push a main**

```bash
git push origin main
```

- [ ] **Step 2: Verificar en Render**

Esperar que Render detecte el push y haga deploy (~2 min en plan Free). En los logs de Render buscar:
- Que **no aparezca** `column "arrendatario_comision_tipo" does not exist` (confirma migración exitosa)
- Que **no aparezca** `[profileSave] residencial vender property profile: ...` (confirma que created_at funciona)

- [ ] **Step 3: Prueba funcional rápida**

1. Abrir un lead con producto **Arrendamiento**, rol arrendatario, con comisión activada
2. Guardar → ir a show.ejs → confirmar que aparecen monto y porcentaje
3. Volver a profile → confirmar que los campos se pre-populan correctamente

---

## Resumen de integridad post-fix

| Problema | Estado después del plan |
|---|---|
| Params SQL fuera de orden | ✅ Secuencial $1–$47 |
| `created_at` faltante en Residencial Vender | ✅ Incluido en INSERT |
| Columnas arrendatario con nombres invertidos | ✅ Renombradas en BD y código |
| `res_v_pp` vacío sin detección | ✅ Log de advertencia en servidor |
| `arq_servicios` parse silencioso | ✅ Warn visible en consola del navegador |
