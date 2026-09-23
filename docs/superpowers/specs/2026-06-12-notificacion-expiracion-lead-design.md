# Notificación de expiración de tiempo de atención de lead — Diseño

**Fecha:** 2026-06-12
**Rama:** pruebas-cron

## 1. Alcance

Se agrega un nuevo tipo de notificación **`lead_expirado`**, enviada al asesor
que **pierde** un lead por no atenderlo dentro de los 5 minutos
(`TIMEOUT_MINUTOS`), cada vez que el cron de escalación
(`escalarLead()` en `src/services/escalacion.cron.js`) ejecuta un salto real:

- **CASO 3** (flujo normal — el más común): el asesor actual no atendió el
  lead a tiempo → se le notifica a él mismo, con link a `/advisor/leads`.
- **CASO 2** (Daniel Rojas no atendió → pasa a Denisse Hansen, fin de la
  cadena): se notifica a Daniel Rojas, con link a `/manager/crm/leads`.
- **CASO 1** (el lead ya está con Denisse Hansen, solo se apaga
  `escalacion_activa`, no hay traspaso real): **NO** se notifica — no hay
  pérdida del lead, sigue siendo suyo.

**Mensaje:**
`⏰ Se venció tu tiempo para atender un lead y fue reasignado automáticamente a otro asesor.`

No incluye nombre del lead.

## 2. Implementación

Se agrega una llamada a `notifService.crearNotificacion()` en dos puntos de
`escalarLead()` (`src/services/escalacion.cron.js`), justo después de la
transferencia exitosa y de la notificación `lead_transferido` existente.

**CASO 2** (Daniel Rojas no atendió → Denisse Hansen), después de la
notificación existente a `FALLBACK_2_ID` (línea ~128):

```javascript
if (!MODO_PRUEBA) {
  await notifService.crearNotificacion(
    FALLBACK_1_ID, 'lead_expirado',
    '⏰ Se venció tu tiempo para atender un lead y fue reasignado automáticamente a otro asesor.',
    '/manager/crm/leads', null
  ).catch(err => console.error(`[escalacion] Error notificando expiración a ${FALLBACK_1_ID} para lead ${leadId}:`, err.message));
}
```

**CASO 3** (flujo normal), después de la notificación existente a
`nextUserId` (línea ~172):

```javascript
if (!MODO_PRUEBA) {
  await notifService.crearNotificacion(
    currentUser, 'lead_expirado',
    '⏰ Se venció tu tiempo para atender un lead y fue reasignado automáticamente a otro asesor.',
    '/advisor/leads', null
  ).catch(err => console.error(`[escalacion] Error notificando expiración a ${currentUser} para lead ${leadId}:`, err.message));
}
```

No se requiere lookup de rol en tiempo real: los 18 miembros de
`escalacion_lista_global` son siempre `role='advisor'` (su URL es
`/advisor/leads`), y `FALLBACK_1_ID` (Daniel Rojas) es siempre
`role='manager'` (su URL es `/manager/crm/leads`). Ambos casos quedan
hardcodeados según el caso del `if`, sin queries adicionales.

No se modifica `transferirLead()`, las constantes de fallback, ni
`escalacionLista.service.js`.

## 3. Estilo frontend

`public/js/notificaciones.js` ya tiene un fallback `'default'` (campana 🔔,
teal `#008a8a`) que funcionaría sin cambios. Para mejorar la UX, se agrega
`lead_expirado` con paleta naranja de alerta (⏰, mismo esquema que
`recordatorio_cita`/`lead_traspaso`) en las 3 tablas existentes:

```javascript
// NOTIF_COLORS (línea ~69)
lead_expirado: { bg: '#faeeda', border: '#854f0b', text: '#854f0b', icon: '⏰' },

// TOAST_CFG (línea ~118)
lead_expirado: { bg:'#faeeda', border:'#854f0b', text:'#854f0b', label:'Tiempo vencido' },

// _pushToSW COLORES (línea ~510)
lead_expirado: '#854f0b',

// _pushToSW LABELS (línea ~528)
lead_expirado: '⏰ Tiempo vencido',
```

## 4. Testing

Sin tests automatizados nuevos — cambio pequeño y bien acotado, igual que la
mejora anterior de filtros del cron. Validación manual:

1. Verificar sintaxis: `node -e "require('dotenv').config(); require('./src/services/escalacion.cron'); console.log('OK')"`
2. Usar el lead de prueba 4940 (en curso de monitoreo): el siguiente salto que
   ocurra después de aplicar este cambio debe generar, además de la
   notificación `lead_transferido` al nuevo asesor, una notificación
   `lead_expirado` al asesor anterior con el mensaje y link `/advisor/leads`
   esperados — verificar en tabla `notificaciones`.
3. Verificar visualmente en el navbar/panel del asesor que perdió el lead:
   ícono ⏰, color naranja, toast con label "Tiempo vencido".
