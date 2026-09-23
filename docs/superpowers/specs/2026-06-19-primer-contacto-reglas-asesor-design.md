# Spec: Reglas de primer contacto para asesor

**Fecha:** 2026-06-19
**Estado:** Aprobado
**Alcance:** Panel del asesor — lead nuevo recibido (`isFirst = true`)

---

## Contexto

Cuando un lead llega a un asesor (por transferencia de marketing o manager), el sistema tiene un cron que escala el lead automáticamente si el asesor no registra contacto en 5 minutos. Este spec define las reglas de UI y backend que refuerzan esa lógica de negocio en la interfaz del asesor.

---

## Regla 1 — Botón "Iniciar Perfilamiento" deshabilitado hasta registrar llamada

### Comportamiento
- El botón "Iniciar perfilamiento" en `show.ejs` aparece **deshabilitado** (gris, no clickeable) si el asesor no tiene al menos 1 actividad de `type = 'llamada'` registrada para ese lead.
- Una vez que existe al menos 1 llamada → el botón se activa (teal, comportamiento actual).
- Solo aplica cuando `!profile` (sin perfilamiento iniciado). Si el perfil ya existe, esta lógica no aplica.

### Cambios en backend
**Archivo:** `src/controllers/advisor/crm.controller.js` — función `showLead`

- Agregar query: `SELECT COUNT(*) FROM crm_activities WHERE lead_id = $1 AND advisor_id = $2 AND type = 'llamada'`
- Pasar `hasCallActivity` (boolean) al render de `show.ejs`

### Cambios en frontend
**Archivo:** `views/advisor/crm/leads/show.ejs`

- Donde hoy se renderiza el botón "Iniciar perfilamiento" (línea ~627):
  - Si `hasCallActivity = false`: botón `<button disabled>` gris con texto `"Registra una llamada primero"`
  - Si `hasCallActivity = true`: `<a href="...">Iniciar perfilamiento</a>` (comportamiento actual)

---

## Regla 2 — Restricción de fecha/hora en el primer contacto

### Comportamiento
- Solo aplica cuando `IS_FIRST = true` (ninguna actividad previa en el lead).
- La ventana válida es: `transferred_at ≤ scheduled_at ≤ transferred_at + 5 minutos`
  - `transferred_at`: campo `transferred_at` del lead; si es `null`, usar `created_at`
- Si el cron ya escaló el lead (lo transfirió al siguiente asesor), `getLeadVisible()` retorna `null` → el controller ya devuelve 404. No se necesita lógica adicional para este caso.

### Ejemplo
| Situación | Resultado |
|---|---|
| Lead recibido 11:00am, asesor registra a las 11:02am con hora 11:03am | ✅ Válido |
| Lead recibido 11:00am, asesor intenta registrar hora 10:58am | ❌ Rechazado (antes de llegada) |
| Lead recibido 11:00am, asesor intenta registrar hora 11:07am | ❌ Rechazado (fuera de ventana) |
| Lead recibido 11:00am, cron corrió a 11:05am y escaló | Lead ya no visible → 404 automático |

### Cambios en backend
**Archivo:** `src/controllers/advisor/crm.controller.js`

- `contactForm`: pasar `transferredAt` al view (`lead.transferred_at || lead.created_at`)
- `contactSubmit`: si `isFirst`, validar:
  ```
  scheduled_at >= transferred_at
  scheduled_at <= transferred_at + 5 minutos
  ```
  Si falla → redirect a `?error=tiempo_invalido` con mensaje: `"La hora debe estar entre HH:MM y HH:MM"`

### Cambios en frontend
**Archivo:** `views/advisor/crm/leads/contact.ejs`

- Recibir `transferredAt` del controller
- Calcular `minDatetime` y `maxDatetime` en el bloque EJS/JS
- Inputs `date` y `time`:
  - Atributo `min` = fecha/hora de `transferred_at`
  - Atributo `max` = fecha/hora de `transferred_at + 5min`
- Validación JS antes de submit: si el valor está fuera del rango → error inline bajo los campos, bloquear submit
- El error del servidor (`?error=tiempo_invalido`) también se muestra en la página

---

## Regla 3 — Campos obligatorios en primer contacto

### Campos que pasan a ser requeridos solo cuando `IS_FIRST = true`

| Campo | Input | Validación frontend | Validación backend |
|---|---|---|---|
| Fecha y hora | `date` + `time` | Ya tiene `data-required="1"` | Ya validado implícitamente |
| Tipo de contacto | `type` | Ya requerido via `CALL_ONLY` | Ya validado |
| Producto Altaltium | `property_list` | Ya tiene `data-required="1"` | Agregar check |
| Folio de propiedad | `property_folio` | Agregar `data-required="1"` condicionalmente | Agregar check |
| Observaciones (Bitácora) | `observations` | Agregar `data-required="1"` condicionalmente | Agregar check |

### Cambios en backend
**Archivo:** `src/controllers/advisor/crm.controller.js` — `contactSubmit`

- Si `isFirst` y falta alguno de: `observations`, `property_folio`, `scheduled_at` → redirect con `?error=campos_requeridos`
- Log de advertencia (no silencioso) si `scheduled_at` llega vacío

### Cambios en frontend
**Archivo:** `views/advisor/crm/leads/contact.ejs`

- Inputs `property_folio` y `observations`: agregar `data-required="1"` condicionalmente cuando `IS_FIRST`
- La función de validación JS que ya lee `data-required` los tomará automáticamente

---

## Integridad en BD

- `toNull()` en `createActivity` ya protege contra valores vacíos → sin cambio
- `scheduled_at` ya se maneja correctamente como CDMX via `buildScheduledAtInsertExpr` → sin cambio
- `UPDATE escalacion_activa = false` ya tiene `.catch()` en `contactSubmit` → sin cambio
- Se agrega log `console.warn` si `scheduled_at` es null en primer contacto (evita error silencioso)

---

## Archivos modificados

| Archivo | Tipo de cambio |
|---|---|
| `src/controllers/advisor/crm.controller.js` | Backend: query `hasCallActivity`, validaciones en `contactSubmit`, pasar `transferredAt` |
| `views/advisor/crm/leads/show.ejs` | Frontend: botón perfilamiento condicional |
| `views/advisor/crm/leads/contact.ejs` | Frontend: min/max datetime, campos requeridos condicionales |

---

## Fuera de alcance

- Manager CRM: no aplican estas reglas (solo advisor)
- Leads existentes con actividades previas: no aplican estas reglas (`isFirst = false`)
- Soluciones Legales: mantiene su lógica actual (ya excluida en `onlyCall`)
- Modo edición de actividad (`isEdit = true`): estas reglas no aplican
