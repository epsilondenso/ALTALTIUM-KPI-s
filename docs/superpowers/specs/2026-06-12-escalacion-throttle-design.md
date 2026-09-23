# Throttle temporal de escalación para el lanzamiento — Diseño

**Fecha:** 2026-06-12
**Rama:** pruebas-cron

## 1. Problema

Al desplegar las correcciones recientes del cron de escalación (`src/services/escalacion.cron.js`) a producción, podría existir un backlog de leads con `escalacion_activa = true` cuyo `transferred_at` ya venció hace tiempo. Si el cron arranca normalmente (revisión cada minuto, sin límite de leads por tick), todos esos leads se escalarían de golpe en los primeros minutos — generando un volumen alto de transferencias y notificaciones simultáneas ("colapso").

## 2. Alcance

Se agrega un **mecanismo temporal de throttle** que:

1. **Pausa total** del cron de escalación hasta una hora de arranque definida (hoy viernes 12/06/2026, 19:00 hora CDMX). Ningún lead — ni los que ya cumplen las reglas de escalación ahora, ni los que se vayan activando entre el deploy y las 19:00 — se transfiere antes de esa hora.
2. **A partir de las 19:00 CDMX**, el cron procesa como máximo **10 leads por hora** (ventana móvil de 60 minutos), priorizando los que llevan más tiempo esperando (`transferred_at` más antiguo primero).
3. Todas las reglas y horarios existentes (horario laboral L-V 9-20h / S-D 9-14h, toggle general `escalacion_activa`, orden de escalación por gerencia, fallbacks Daniel Rojas → Denisse Hansen) **siguen aplicando sin cambios** — el throttle es una capa adicional, no un reemplazo.
4. Es **temporal**: se desactiva con un **toggle manual** en el panel admin (similar al toggle existente "Activar escalación"), cuando se confirme que el backlog inicial ya se drenó. No hay desactivación automática.

**No se modifica:** `transferirLead()`, `escalarLead()`, las constantes de fallback, `escalacionLista.service.js`, ni las columnas de `crm_leads`.

## 3. Configuración (tabla `configuracion`)

Tres filas nuevas, mismo patrón que `escalacion_activa`:

| clave | valor inicial | descripción |
|---|---|---|
| `escalacion_throttle_activo` | `'true'` | toggle manual — mientras sea `'true'`, se aplica el throttle |
| `escalacion_throttle_desde` | `'2026-06-12 19:00:00-06'` | timestamp a partir del cual el cron empieza a procesar leads |
| `escalacion_throttle_limite` | `'10'` | máximo de transferencias reales por ventana móvil de 60 min |

## 4. Lógica en `revisarEscalaciones()`

`src/services/escalacion.cron.js` — después de las validaciones actuales (`escalacion_activa`, `activo_desde`, horario laboral) y antes de ejecutar la query de leads elegibles:

```javascript
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
```

La query que obtiene los leads elegibles se modifica para agregar:

```sql
ORDER BY transferred_at ASC
LIMIT $N
```

donde `$N` es `limiteRestante` (un número) si el throttle está activo, o `null` si no — `LIMIT NULL` en Postgres equivale a sin límite, por lo que el modo normal (throttle desactivado) queda exactamente igual al comportamiento actual.

**Conteo de la ventana móvil:** se basa en `escalacion_historial`, que ya registra cada transferencia real hecha por `transferirLead()` (tanto CASO 2 como CASO 3 de `escalarLead()`). CASO 1 (lead ya con Denisse Hansen) no inserta en `escalacion_historial` y tampoco aparece en la query de leads elegibles (ya excluido por `advisor_id != FALLBACK_2_ID`), así que no afecta el conteo.

## 5. Panel admin

**Vista:** `views/admin/escalacion/lista.ejs` — nueva tarjeta debajo de "Estado del cron", mismo estilo (`esc-card`, `esc-toggle-btn`):

```
┌─────────────────────────────────────────────────┐
│ Modo controlado (lanzamiento)        [Activado]  │
│ Límite: 10 leads/hora · desde 12/06 19:00         │
│ Mientras esté activado, el cron procesa máx. 10   │
│ leads por hora (los más antiguos primero).        │
│ Desactívalo cuando el backlog esté drenado.        │
└─────────────────────────────────────────────────┘
```

Los valores de límite y hora de arranque se muestran formateados a partir de `escalacion_throttle_limite` y `escalacion_throttle_desde`.

**Controlador (`src/controllers/admin/escalacion.controller.js`):**
- `vista()` se modifica para incluir en la consulta de `configuracion` las 3 claves nuevas y pasarlas a la plantilla.
- Nueva función `toggleThrottle`, copia del patrón de `toggleEscalacion` pero sobre la clave `escalacion_throttle_activo` (INSERT ... ON CONFLICT DO UPDATE).

**Rutas (`src/routes/admin.routes.js`):**
```javascript
router.post('/configuracion/escalacion-throttle/toggle', requireRole('admin'), escalacionAdminCtrl.toggleThrottle);
```
Junto a las demás rutas de escalación (línea ~770), protegida igual con `requireRole('admin')`.

## 6. Script de migración

`scripts/migration_escalacion_throttle.js`, mismo patrón que `scripts/migration_escalacion_lista_global.js`:

- Inserta las 3 filas de `configuracion` con `ON CONFLICT (clave) DO NOTHING` (idempotente — seguro re-ejecutarlo).
- `escalacion_throttle_desde` se calcula como **hoy a las 19:00 hora CDMX**, en el momento en que se ejecuta el script — por lo que debe correrse cerca de la hora del deploy, no con mucha anticipación.
- Se ejecuta una sola vez contra producción (Render):
  ```bash
  node scripts/migration_escalacion_throttle.js
  ```

## 7. Testing

Sin tests automatizados nuevos — cambio acotado y temporal, igual que las mejoras anteriores del cron. Validación manual:

1. Verificar sintaxis: `node -e "require('dotenv').config(); require('./src/services/escalacion.cron'); console.log('OK')"`
2. Correr la migración y confirmar las 3 filas en `configuracion`.
3. Antes de las 19:00: confirmar en logs que `revisarEscalaciones()` retorna temprano (pausa total) aunque haya leads vencidos.
4. Después de las 19:00: confirmar que como máximo 10 transferencias ocurren por hora, en orden de `transferred_at` ascendente (verificar en `escalacion_historial`).
5. Verificar visualmente en `/admin/configuracion/escalacion-lista` que la tarjeta nueva muestra el estado correcto y que el botón de toggle apaga/enciende `escalacion_throttle_activo`.
6. Apagar el toggle manualmente y confirmar que el cron vuelve al comportamiento sin límite (sin reiniciar el servidor).
