# Notificación de expiración de tiempo de atención de lead — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cuando el cron de escalación reasigna un lead por falta de atención (5 min), notificar al asesor (o a Daniel Rojas en el caso del fallback) que su tiempo se venció, con un nuevo tipo de notificación `lead_expirado`.

**Architecture:** Dos bloques nuevos de `notifService.crearNotificacion()` dentro de `escalarLead()` en `src/services/escalacion.cron.js` (CASO 2 y CASO 3), más 4 entradas nuevas (`lead_expirado`) en las tablas de estilo de `public/js/notificaciones.js` para que el ícono ⏰/color naranja se muestren en panel, toast y push del Service Worker. No se modifica `transferirLead()`, constantes de fallback, ni `escalacionLista.service.js`.

**Tech Stack:** Node.js v24, `pg`, `node-cron`, JS vanilla (frontend).

---

## ⚠️ Antes de empezar

- **NO hacer commit hasta que el usuario lo autorice explícitamente** — instrucción permanente de esta sesión. El Task 3 incluye un paso de commit; ejecútalo solo si el usuario ya dio luz verde para ese commit específico.
- `src/services/escalacion.cron.js` ya tiene cambios sin commitear de tareas anteriores (flag `ejecutando`, filtros de origen-marketing/portal en `revisarEscalaciones()`). **No los toques ni los deshagas.** Este plan agrega código nuevo dentro de `escalarLead()`, que no se solapa con esos cambios.
- El lead de prueba `4940` está actualmente en monitoreo activo (escalando cada 5 minutos). Úsalo para la validación manual del Task 3 — su próximo salto, una vez aplicado este cambio, debe generar la notificación `lead_expirado`.

---

### Task 1: Notificación `lead_expirado` en CASO 2 (Daniel Rojas → Denisse Hansen)

**Files:**
- Modify: `src/services/escalacion.cron.js:123-131`

- [ ] **Step 1: Confirmar el bloque actual**

El bloque actual dentro del `if (currentUser === FALLBACK_1_ID) { ... }` (CASO 2) es:

```javascript
    if (!MODO_PRUEBA) {
      await notifService.crearNotificacion(
        FALLBACK_2_ID, 'lead_transferido',
        'Lead asignado al finalizar la cadena de escalación.',
        `/advisor/leads/${leadId}`, null
      ).catch(err => console.error(`[escalacion] Error notificando a ${FALLBACK_2_ID} para lead ${leadId}:`, err.message));
    }
    console.log(`[${horaCDMX()}] [escalacion] Lead ${leadId}: Daniel Rojas → Denisse Hansen (FIN)`);
    return;
  }
```

- [ ] **Step 2: Insertar la notificación de expiración para Daniel Rojas**

Reemplaza ese bloque por:

```javascript
    if (!MODO_PRUEBA) {
      await notifService.crearNotificacion(
        FALLBACK_2_ID, 'lead_transferido',
        'Lead asignado al finalizar la cadena de escalación.',
        `/advisor/leads/${leadId}`, null
      ).catch(err => console.error(`[escalacion] Error notificando a ${FALLBACK_2_ID} para lead ${leadId}:`, err.message));

      await notifService.crearNotificacion(
        FALLBACK_1_ID, 'lead_expirado',
        '⏰ Se venció tu tiempo para atender un lead y fue reasignado automáticamente a otro asesor.',
        '/manager/crm/leads', null
      ).catch(err => console.error(`[escalacion] Error notificando expiración a ${FALLBACK_1_ID} para lead ${leadId}:`, err.message));
    }
    console.log(`[${horaCDMX()}] [escalacion] Lead ${leadId}: Daniel Rojas → Denisse Hansen (FIN)`);
    return;
  }
```

- [ ] **Step 3: Verificar sintaxis**

Run:
```
node -e "require('dotenv').config(); require('./src/services/escalacion.cron'); console.log('OK')"
```
Expected output: `OK`

---

### Task 2: Notificación `lead_expirado` en CASO 3 (flujo normal)

**Files:**
- Modify: `src/services/escalacion.cron.js:165-175`

- [ ] **Step 1: Confirmar el bloque actual**

El bloque actual al final de `escalarLead()` (CASO 3, flujo normal) es:

```javascript
  if (!MODO_PRUEBA) {
    await notifService.crearNotificacion(
      nextUserId, 'lead_transferido',
      esFallback1
        ? `⚠️ Lead escalado al nivel directivo. Tienes ${TIMEOUT_MINUTOS} minutos para atenderlo.`
        : `⚠️ Tienes ${TIMEOUT_MINUTOS} minutos para atender este lead o será reasignado.`,
      `/advisor/leads/${leadId}`, null
    ).catch(err => console.error(`[escalacion] Error notificando a ${nextUserId} para lead ${leadId}:`, err.message));
  }

  console.log(`[${horaCDMX()}] [escalacion] Lead ${leadId}: ${nombreCurrent} → ${nombreNext}`);
```

- [ ] **Step 2: Insertar la notificación de expiración para el asesor anterior**

Reemplaza ese bloque por:

```javascript
  if (!MODO_PRUEBA) {
    await notifService.crearNotificacion(
      nextUserId, 'lead_transferido',
      esFallback1
        ? `⚠️ Lead escalado al nivel directivo. Tienes ${TIMEOUT_MINUTOS} minutos para atenderlo.`
        : `⚠️ Tienes ${TIMEOUT_MINUTOS} minutos para atender este lead o será reasignado.`,
      `/advisor/leads/${leadId}`, null
    ).catch(err => console.error(`[escalacion] Error notificando a ${nextUserId} para lead ${leadId}:`, err.message));

    await notifService.crearNotificacion(
      currentUser, 'lead_expirado',
      '⏰ Se venció tu tiempo para atender un lead y fue reasignado automáticamente a otro asesor.',
      '/advisor/leads', null
    ).catch(err => console.error(`[escalacion] Error notificando expiración a ${currentUser} para lead ${leadId}:`, err.message));
  }

  console.log(`[${horaCDMX()}] [escalacion] Lead ${leadId}: ${nombreCurrent} → ${nombreNext}`);
```

- [ ] **Step 3: Verificar sintaxis**

Run:
```
node -e "require('dotenv').config(); require('./src/services/escalacion.cron'); console.log('OK')"
```
Expected output: `OK`

---

### Task 3: Estilo `lead_expirado` en frontend + validación manual

**Files:**
- Modify: `public/js/notificaciones.js:69` (NOTIF_COLORS)
- Modify: `public/js/notificaciones.js:116` (TOAST_CFG)
- Modify: `public/js/notificaciones.js:510` (_pushToSW COLORES)
- Modify: `public/js/notificaciones.js:528` (_pushToSW LABELS)

- [ ] **Step 1: Agregar entrada en `NOTIF_COLORS`**

El bloque actual (línea 68-70):

```javascript
    lead_transferido:     { bg: '#e1f5ee', border: '#0f6e56', text: '#0f6e56', icon: '🔄' },
    lead_traspaso:        { bg: '#faeeda', border: '#854f0b', text: '#854f0b', icon: '🔀' },
    sugerencia_lead:      { bg: '#eeedfe', border: '#3c3489', text: '#3c3489', icon: '👤' },
```

Reemplázalo por:

```javascript
    lead_transferido:     { bg: '#e1f5ee', border: '#0f6e56', text: '#0f6e56', icon: '🔄' },
    lead_traspaso:        { bg: '#faeeda', border: '#854f0b', text: '#854f0b', icon: '🔀' },
    lead_expirado:        { bg: '#faeeda', border: '#854f0b', text: '#854f0b', icon: '⏰' },
    sugerencia_lead:      { bg: '#eeedfe', border: '#3c3489', text: '#3c3489', icon: '👤' },
```

- [ ] **Step 2: Agregar entrada en `TOAST_CFG`**

El bloque actual (línea 115-117):

```javascript
    lead_transferido:     { bg:'#e1f5ee', border:'#008a8a', text:'#008a8a', label:'Transferido' },
    lead_traspaso:        { bg:'#faeeda', border:'#854f0b', text:'#854f0b', label:'Traspaso' },
    recordatorio_cita:    { bg:'#faeeda', border:'#854f0b', text:'#854f0b', label:'Recordatorio' },
```

Reemplázalo por:

```javascript
    lead_transferido:     { bg:'#e1f5ee', border:'#008a8a', text:'#008a8a', label:'Transferido' },
    lead_traspaso:        { bg:'#faeeda', border:'#854f0b', text:'#854f0b', label:'Traspaso' },
    lead_expirado:        { bg:'#faeeda', border:'#854f0b', text:'#854f0b', label:'Tiempo vencido' },
    recordatorio_cita:    { bg:'#faeeda', border:'#854f0b', text:'#854f0b', label:'Recordatorio' },
```

- [ ] **Step 3: Agregar entrada en `_pushToSW` → `COLORES`**

El bloque actual (línea 507-509):

```javascript
        lead_transferido:     '#008a8a',
        lead_traspaso:        '#854f0b',
        recordatorio_cita:    '#854f0b',
```

Reemplázalo por:

```javascript
        lead_transferido:     '#008a8a',
        lead_traspaso:        '#854f0b',
        lead_expirado:        '#854f0b',
        recordatorio_cita:    '#854f0b',
```

- [ ] **Step 4: Agregar entrada en `_pushToSW` → `LABELS`**

El bloque actual (línea 525-527):

```javascript
        lead_transferido:     'Lead transferido',
        lead_traspaso:        'Traspaso de lead',
        recordatorio_cita:    '🗓️ Recordatorio de cita',
```

Reemplázalo por:

```javascript
        lead_transferido:     'Lead transferido',
        lead_traspaso:        'Traspaso de lead',
        lead_expirado:        '⏰ Tiempo vencido',
        recordatorio_cita:    '🗓️ Recordatorio de cita',
```

- [ ] **Step 5: Validación manual con el lead de prueba 4940**

El lead 4940 está en escalación activa (revisado en una sesión anterior, asesor actual con id `25`, `escalacion_activa=true`, `status='open'`). Una vez aplicados los Tasks 1-2, el próximo salto automático del cron (dentro de los siguientes ~5 minutos desde el último salto registrado en `escalacion_historial`) debe:

1. Transferir el lead al siguiente asesor en la lista circular (notificación `lead_transferido` ya existente).
2. Generar una notificación nueva `lead_expirado` para el asesor `25` (el que tenía el lead antes del salto), con `mensaje = '⏰ Se venció tu tiempo para atender un lead y fue reasignado automáticamente a otro asesor.'` y `url_accion = '/advisor/leads'`.

Para verificar, ejecuta (ajusta el `advisor_id` anterior si ya cambió desde la última revisión — consulta primero `SELECT advisor_id FROM crm_leads WHERE id = 4940`):

```bash
node -e "
require('dotenv').config();
const pool = require('./src/db/pool');
(async () => {
  const { rows } = await pool.query(
    \`SELECT user_id, tipo, mensaje, url_accion, created_at
     FROM notificaciones
     WHERE tipo = 'lead_expirado'
     ORDER BY created_at DESC LIMIT 5\`
  );
  console.log(rows);
  await pool.end();
})();
"
```

Expected: al menos una fila con `tipo='lead_expirado'`, `url_accion='/advisor/leads'`, y `user_id` igual al asesor que tenía el lead 4940 antes del salto más reciente.

- [ ] **Step 6: Commit (solo si el usuario autoriza este commit específico)**

```bash
git add src/services/escalacion.cron.js public/js/notificaciones.js
git commit -m "feat: notificar al asesor cuando vence su tiempo para atender un lead escalado"
```

---

## Self-Review

- **Cobertura del spec:**
  - Sección 1 (alcance: CASO 2 y CASO 3 notifican, CASO 1 no) → Task 1 (CASO 2) y Task 2 (CASO 3); CASO 1 no se toca. ✅
  - Sección 2 (implementación, código exacto, URLs hardcodeadas por caso) → Task 1 Step 2 y Task 2 Step 2, código idéntico al spec. ✅
  - Sección 3 (estilo frontend, 4 tablas) → Task 3 Steps 1-4, código idéntico al spec. ✅
  - Sección 4 (testing manual con lead 4940) → Task 3 Step 5. ✅
- **Placeholders:** ninguno — todo el código está completo y ejecutable.
- **Consistencia de tipos:** el `tipo` `'lead_expirado'` y los mensajes/URLs son idénticos entre Task 1, Task 2 y las entradas de estilo en Task 3.
