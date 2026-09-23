# Reglas de origen y portal para el cron de escalación — Diseño

**Fecha:** 2026-06-12
**Rama:** pruebas-cron

## 1. Alcance

Se modifica el cron de escalación automática (`revisarEscalaciones()` en
`src/services/escalacion.cron.js`, corre cada minuto) para que **solo escale
leads que cumplan estas reglas**, además de las condiciones existentes:

1. La escalación fue activada por un usuario de **marketing** (vía la
   columna `escalacion_origen_id`).
2. El `portal` (Portal de Origen) del lead **no es `'Cartera'`** y no es
   `NULL`. Cualquier otro portal (Inmuebles24, MercadoLibre, RedesSociales,
   Cambaceo, Referido, Marketing, Otros, Ficha Pública, Sitio Web, etc.) es
   candidato.
3. El advisor actual no ha registrado contacto desde que recibió el lead
   (regla ya existente: `NOT EXISTS crm_activities` posteriores a
   `transferred_at`).

Una cuarta regla propuesta originalmente — "lead estancado más de 3 días sin
contacto ni perfilamiento" — **queda fuera de este cambio**. Es un mecanismo
distinto (no usa el flag `escalacion_activa` ni el timeout de 5 minutos) y se
diseñará por separado si se decide implementar.

Este cambio aplica **hacia adelante**, para todos los leads (no solo los 412
que quedaron en pausa en una limpieza anterior). Si esos 412 leads se
reactivan en el futuro, el cron ya aplicará este filtro automáticamente.

## 2. Implementación

Se agregan dos condiciones al `WHERE` de la consulta de elegibilidad en
`revisarEscalaciones()` ([escalacion.cron.js:220-233](../../../src/services/escalacion.cron.js#L220-L233)):

```sql
SELECT id, advisor_id, escalacion_gerencia_inicio, transferred_at
FROM crm_leads
WHERE escalacion_activa = true
  AND status = 'open'
  AND advisor_id != $1
  AND transferred_at < NOW() - INTERVAL '5 minutes'
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
```

No se modifica `escalarLead()`, `transferirLead()`, las constantes de
fallback ni el comportamiento de `escalacion_lista_global`. No se requiere
migración de esquema ni de datos: `escalacion_origen_id` y `portal` ya
existen y están poblados en `crm_leads`.

## 3. Casos límite y comportamiento

- **`escalacion_origen_id` NULL** (leads activados antes de que existiera
  esta columna, o por flujos antiguos): no cumplen la regla 1 → el cron los
  ignora. Quedan con `escalacion_activa=true` sin avanzar.
- **`portal` NULL**: no cumplen la regla 2 → el cron los ignora, mismo
  comportamiento que el caso anterior.
- **Leads activados por un manager** (`escalacion_origen_id` apunta a un
  usuario con `role='manager'`): no cumplen la regla 1 → el cron los ignora.
  **Decisión:** se dejan tal cual (`escalacion_activa` permanece en `true`
  pero sin efecto). No se hace limpieza activa del flag para estos casos —
  cambio mínimo, sin riesgo de apagar flags por error.
- **Leads ya en curso en la cadena de escalación** (con saltos previos): si
  su `escalacion_origen_id` es de marketing y su `portal` no es Cartera,
  siguen escalando normalmente sin interrupciones, porque ambos valores no
  cambian entre saltos.
- **Fallbacks (Daniel Rojas → Denisse Hansen)**: `CASO 1` y `CASO 2` de
  `escalarLead()` no vuelven a pasar por este `WHERE` — un lead que entró
  cumpliendo las reglas sigue su curso hasta el fallback final sin volver a
  evaluarse.

## 4. Testing

Cambio de una sola consulta SQL, sin lógica nueva en JS — no requiere unit
tests nuevos. Validación manual recomendada en BD local (sin afectar
producción), reutilizando el patrón de leads de prueba de la sesión anterior:

1. Confirmar que la consulta con los 2 filtros nuevos devuelve un subconjunto
   razonable de los leads `escalacion_activa=true` actuales (hoy son 0; se
   puede simular con un lead de prueba).
2. Lead de prueba con `escalacion_origen_id` de un usuario marketing y
   `portal <> 'Cartera'` → debe escalar normalmente.
3. Mismo lead pero con `portal = 'Cartera'` → el cron NO debe tomarlo.
4. Lead de prueba con `escalacion_origen_id` de un manager → el cron NO debe
   tomarlo.
