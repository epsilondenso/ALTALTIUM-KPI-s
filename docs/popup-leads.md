# Sistema de Popups / Ventanas Emergentes de Leads

> **REGLA:** Cada vez que se modifique cualquier archivo listado aquí, actualizar este documento con el cambio realizado.

---

## Archivos involucrados

| Archivo | Rol |
|---|---|
| `public/js/notificaciones.js` | Frontend: lógica de popups, SSE handler, funciones de modal, listener `pageshow` |
| `src/services/notificaciones.service.js` | Backend: crear notificaciones, `replayPendientes`, push SSE |
| `src/routes/main.routes.js` | Backend: endpoint SSE `/notificaciones/stream`, endpoint `/notificaciones/replay-check` |
| `src/services/escalacion.cron.js` | Cron: genera notificaciones `lead_transferido` y `lead_expirado` |
| `views/advisor/crm/leads/show.ejs` | Vista: `#fc-overlay` + popup de primer contacto registrado |
| `views/manager/crm/leads/show.ejs` | Vista: popup de primer contacto registrado (mismo comportamiento) |
| `views/advisor/crm/leads/contact.ejs` | Vista: formulario de primer contacto |
| `views/manager/crm/leads/contact.ejs` | Vista: formulario de primer contacto (manager) |
| `src/controllers/advisor/crm.controller.js` | Redirect con `?primer_contacto=1` al guardar primer contacto |
| `src/controllers/manager/crm.controller.js` | Redirect con `?primer_contacto=1` al guardar primer contacto |
| `src/controllers/directivo/crm.controller.js` | Guard `desde_notif`/`abrir_resultado`, `urgentFirstTouch`, validación server-side (agregados jul 2026) |
| `src/routes/advisor.crm.routes.js` | Endpoint `/advisor/crm/recordatorios-pendientes` (usado por `_verificarRecordatoriosPendientes`); `POST /advisor/leads/:id/omitir` |
| `src/routes/manager.crm.routes.js` | `POST /manager/crm/leads/:id/omitir` |
| `src/routes/directivo.routes.js` | `POST /crm/:id/omitir` |
| `src/services/leadOmission.service.js` | Backend: `omitirLead()` — valida y reasigna un lead omitido al siguiente en la lista global |

---

## Excepción por usuario: exención de popups bloqueantes

**Regla de negocio (jul 2026):** los siguientes usuarios están **exentos de todo el mecanismo de popups bloqueantes de leads**:

| Usuario | ID | Razón |
|---|---|---|
| Daniel Rojas | 35 (`FALLBACK_1_ID`) | Receptor penúltimo de escalación — volumen alto de leads |
| Denisse Hansen | 7 (`FALLBACK_2_ID`) | Receptor final (FIN) de escalación — volumen alto de leads |
| Leonardo Furlong | 50 | Manager Residencial — volumen alto de leads |

Los modales bloqueantes, el bloqueo de sidebar/navbar y las reglas de "primer contacto urgente" (solo llamada, hoy, 5 min) les impedían trabajar su bandeja con fluidez. **Siguen recibiendo notificaciones normales en la campana** (badge, panel, toast) — solo se suprime la parte bloqueante/interruptiva. La exención es **por ID de usuario, no por rol** — otros managers/directivos siguen sujetos a las reglas normales.

**Mecanismo — `notifService.esExentoDePopups(userId)` (migrado a BD, jul 2026):**
```js
// src/services/notificaciones.service.js
let _popupExemptCache = new Set([FALLBACK_1_ID]); // fallback hasta el primer refresh real
function esExentoDePopups(userId) { return _popupExemptCache.has(Number(userId)); }
async function iniciarExencionPopups() {
  // crea users.suppress_lead_popups (BOOLEAN DEFAULT false) si no existe, y solo
  // en ese caso (columna recién creada) siembra Daniel Rojas = true.
  // Refresca la caché al arrancar y cada 5 min desde:
  //   SELECT id FROM users WHERE suppress_lead_popups = true
}
```
Originalmente era un `Set` hardcodeado en el código (`POPUP_EXEMPT_USER_IDS`). Se migró a la columna `users.suppress_lead_popups` porque un Set hardcodeado obliga a editar código + deploy para agregar/quitar un exento, y no había forma de que un admin lo cambiara. Ahora: **para agregar/quitar un usuario exento, hacer `UPDATE users SET suppress_lead_popups = true/false WHERE id = ...`** directamente en BD — el cambio se refleja en el servidor en como máximo 5 minutos (ciclo de refresh de la caché en memoria), sin reiniciar. `iniciarExencionPopups()` se llama una sola vez al arrancar el servidor (`src/server.js`, después de `runMigrations()`). El seed inicial de Daniel Rojas es **estrictamente de una sola vez** (se detecta por "¿la columna ya existía?", no por "¿hay algún exento activo?"): si un admin revoca su exención manualmente en BD, un reinicio del servidor **no la vuelve a sembrar**.

**Dónde se aplica:**

1. **Popups SSE bloqueantes** (`lead_transferido`, `lead_publico`, `lead_traspaso`, `lead_expirado`, `recordatorio_cita`, `recordatorio_llamada`) — `crearNotificacion()` y `replayPendientes()` etiquetan el payload con `suppress_lead_popup: true` cuando el destinatario está exento. El cliente (`notificaciones.js`, handler `onmessage` de `conectarSSE`) revisa esta bandera **antes** de decidir el modal y, si viene marcada, llama a `mostrarToast(notif)` en vez de `mostrarBurbujaNuevoLead`/`mostrarModalLeadExpirado` — sigue informado, no lo bloquea. **Solo se muestra una vez**: el toast únicamente se dispara en el push original (`notif.is_replay` falsy); en los replays (`is_replay: true`, que se repiten en cada reconexión SSE — es decir, en cada cambio de página — mientras el lead siga sin primer contacto) se omite por completo, porque para un usuario exento eso se vuelve ruido repetido. El badge/campana siguen reflejándolo siempre, independientemente del toast.

2. **`_verificarRecordatoriosPendientes`** (polling independiente del SSE, vía `GET /advisor/crm/recordatorios-pendientes`) — el endpoint agrega `suppress_lead_popup: notifService.esExentoDePopups(advisorId)` a la respuesta; el cliente lo revisa antes de llamar `mostrarBurbujaNuevoLead` para cada actividad vencida. **No afecta** el caso donde ya está en la página del lead (ahí solo abre el modal de resultado, que no es bloqueante/interruptivo de navegación — se deja igual para todos).

3. **`urgentFirstTouch`** (las reglas de "contacto urgente": solo llamada, fecha de hoy, 5 min, `#crm-nav-lock`) — en los 3 `contactForm`/`contactSubmit` (advisor/manager/directivo), se fuerza a `false` cuando `notifService.esExentoDePopups(receptorId)` es verdadero, sin importar el resultado real de `_actsAfterTransfer`.

4. **`#fc-overlay`** (`_fcBloquear` en `views/advisor/crm/leads/show.ejs`) — Daniel ya queda exento de esto como efecto lateral de `_viewerEsSupervisor` (es manager), no por una excepción específica a su ID — no fue necesario tocar ese archivo para esta regla.

**No exento:** el modal "Primer contacto registrado" (celebratorio, `?primer_contacto=1` tras guardar) y el auto-abrir del modal de resultado cuando ya está en la página del lead — ninguno de los dos bloquea navegación ni interrumpe, así que no calificaban como "popup bloqueante".

**Verificación:** se probó `esExentoDePopups(35)` → `true` para los 6 tipos de popup; `esExentoDePopups(90)` / `esExentoDePopups(32)` → `false` (otros usuarios, incluidos otros managers, no quedan exentos). Se renderizó el HTML real de `contactForm` para Daniel (35) sobre el lead #4180 — confirmado: `IS_FIRST_CONTACT=false`, sin `#crm-nav-lock`, sin badge de urgencia — donde antes de este cambio (mismo lead, mismo usuario) daban `true`/presente/visible.

**Bug real encontrado al reprobar en producción — el Service Worker escondía el fix (jul 2026):** después de implementar la excepción de arriba, Daniel seguía viendo el modal bloqueante **incluso tras un hard-refresh (Ctrl+Shift+R)**. Causa: `public/sw.js` interceptaba **toda** ruta bajo `/js/` (incluyendo `/js/notificaciones.js`) con estrategia **Cache-First** (`CACHE_STATIC = 'altaltium-static-v2'`, nombre fijo que nunca cambiaba) — el navegador devolvía la copia cacheada de ANTES del fix sin siquiera consultar la red, y un hard-refresh normal **no invalida el caché del Service Worker** (son mecanismos independientes). El servidor sí servía el código correcto (confirmado con `curl`); el navegador nunca llegaba a pedirlo. Esto afecta a **cualquier cambio de JS/CSS futuro**, no solo a este fix — es un bug estructural del proyecto, no exclusivo de la excepción de Daniel.

**Fix (`public/sw.js` + `public/js/push-manager.js`):**
- CSS/JS propios de la app (`/js/`, `/css/`) pasaron de Cache-First a **Network-First**: siempre intenta la red primero, cae al caché solo si está offline. Los vendor estáticos que cambian poco (`/flyonui/`, Google Fonts) siguen en Cache-First.
- `CACHE_STATIC` subió a `'altaltium-static-v3'` — el `activate` del SW borra cualquier caché con nombre distinto al actual, así que el cambio de versión limpia de una vez la copia vieja de `notificaciones.js`.
- `push-manager.js`: el registro del SW ahora usa `{ updateViaCache: 'none' }` (el propio `sw.js` nunca queda cacheado por HTTP — el navegador siempre revisa si cambió) y llama `reg.update()` al cargar para forzar el chequeo de inmediato en vez de esperar al próximo ciclo natural del navegador.
- **Para el usuario:** con Network-First, un simple refresh normal (sin necesidad de Ctrl+Shift+R) ya trae el JS más reciente desde este cambio en adelante — el problema de "hard-refresh no sirve" no debería repetirse con futuros cambios de código.

---

## Tipos de notificación que disparan popup

| Tipo | Quién la recibe | Popup que muestra | Cuándo desaparece |
|---|---|---|---|
| `lead_transferido` | Asesor receptor del lead | Modal bloqueante "Tienes un nuevo lead" + botón **Atender lead** | Cuando registra primer contacto (`crm_activities` después de `transferred_at`) |
| `lead_publico` | Asesor (lead desde microsite/ficha pública) | Mismo modal bloqueante | Cuando registra primer contacto |
| `lead_traspaso` | Manager receptor de traspaso entre gerencias | Mismo modal bloqueante | Cuando registra primer contacto |
| `lead_expirado` | Asesor al que se le venció el tiempo (escalación) | Modal informativo ⏰ "Lead reasignado" + botón **Enterado** | Cuando hace click en "Enterado" → marca como leída → redirige a bandeja de leads |
| `recordatorio_cita` | Asesor (30 min antes de la cita) | Modal bloqueante de recordatorio | Al cerrar o si ya está en `/contact` |
| `recordatorio_llamada` | Asesor (30 min antes) | Modal bloqueante de recordatorio | Al cerrar o si ya está en `/contact` |

---

## Flujo completo: lead nuevo / transferido

```
1. Cron o transferencia → crearNotificacion(tipo='lead_transferido') en BD
2. Si el asesor está conectado → _pushSSE() envía la notificación en tiempo real
3. Si el asesor NO estaba conectado → al abrir cualquier página del proyecto:
     SSE conecta → replayPendientes() busca notificaciones pendientes → la reenvía
4. SSE handler en notificaciones.js recibe la notificación
5. esModalLead = true → mostrarBurbujaNuevoLead(notif) → cola _lbCola
6. _siguienteModalLead() → _mostrarModalLead(notif)
7. Guard: si ya está en /leads/:id (contact o show) → popup se omite
8. Modal aparece con nombre del lead, actor que transfirió, y botón "Atender lead"
9. Click "Atender lead" → navega a /advisor/leads/:id/contact
10. En contact.ejs: guard previene popup de nuevo (ya está en /leads/:id)
11. Asesor registra actividad en contact.ejs → crm_activities INSERT
12. Próxima carga de página → replayPendientes NOT EXISTS detecta la actividad → ya NO replay
13. Popup desaparece para siempre para ese lead
```

---

## Traspaso/transferencia con primer contacto ya registrado

**Regla de negocio:** si un lead ya tiene actividad registrada (alguien ya hizo el primer contacto) y luego se transfiere a otro asesor, el receptor **no debe ver el formulario de primer contacto** — debe caer en `show.ejs` con el modal de **registrar resultado** abierto automáticamente, porque lo que corresponde es dar seguimiento, no volver a capturar datos de un contacto inicial que ya existe.

**Aplica a `lead_transferido` Y a `lead_traspaso`.** Ambos pueden llegar a un receptor que termina en un formulario de contacto con actividad previa ya existente en el lead:
- `lead_transferido`: transferencias dentro del mismo equipo, y reasignaciones por escalación (el cron también usa este tipo).
- `lead_traspaso`: **el manager/directivo receptor se vuelve dueño directo del lead** (`transferLeadToManager` hace `advisor_id = receptorId` de inmediato, no lo deja "en espera de asignar") y **puede registrar contacto/resultado él mismo** desde `show.ejs`, exactamente igual que un asesor. El mensaje "Asígnalo a uno de tus advisors" es solo un texto sugerido — no es una restricción técnica. Corregido en jul 2026 (ver Changelog): antes solo `lead_transferido` tenía este guard, lo que causaba que un manager que recibía un lead ya contactado cayera en el formulario de "Primer contacto" en vez del modal de resultado.

`lead_publico` sigue sin necesitarlo: se crea en 4 sitios (`propiedad.controller.js`, `microsite.controller.js`, `asistente/acciones.service.js` x2) y en los 4 la notificación solo se dispara en la rama de **lead genuinamente nuevo** (`else` de `if (duplicadoId)`, o `if (!duplicado)`) — si el teléfono ya existe, se actualiza el lead duplicado silenciosamente **sin notificación**. `isFirst` es siempre `true` cuando `lead_publico` se envía.

**Mecanismo:**
```
1. Popup de lead_transferido/lead_traspaso → botón "Atender lead"
2. cerrarModal(irALead) en notificaciones.js reescribe la URL:
   notif.url_accion → .../contact?desde_notif=1
3. contactForm() en el controller (advisor, manager, directivo) evalúa:
     isFirst = actividades.length === 0
     if (desde_notif === '1' && !isFirst) → redirect a
       .../:id?abrir_resultado=1
     (si isFirst === true, renderiza contact.ejs normalmente)
4. show.ejs detecta queryObj.abrir_resultado === '1' →
   <script> hace click programático en #btnOutcome →
   abre el modal "Registrar resultado" automáticamente
```

**Archivos del mecanismo:**
| Archivo | Rol |
|---|---|
| `public/js/notificaciones.js` (función `cerrarModal`, ~línea 917-936) | Agrega `?desde_notif=1` a la URL para `lead_transferido` **y `lead_traspaso`** |
| `src/controllers/advisor/crm.controller.js` (`contactForm`, ~línea 953-956) | Guard: si `desde_notif=1` y `!isFirst` → redirect a show con `abrir_resultado=1` |
| `src/controllers/manager/crm.controller.js` (`contactForm`, ~línea 658-659) | Mismo guard, lado manager |
| `src/controllers/directivo/crm.controller.js` (`contactForm`) | Mismo guard, lado directivo (agregado jul 2026 — antes no existía) |
| `views/advisor/crm/leads/show.ejs` (~línea 470) | Auto-click en `#btnOutcome` si `abrir_resultado=1` |
| `views/manager/crm/leads/show.ejs` (~línea 664) | Mismo auto-click, lado manager |
| `views/directivo/crm/show.ejs` | Mismo auto-click, lado directivo (agregado jul 2026 — antes no existía) |

**Bug corregido jul 2026 — URL de `lead_traspaso` basada en el rol equivocado:** en `src/controllers/advisor/crm.controller.js`, cuando un advisor traspasaba un lead a un manager (Escenario B de `transferSubmit`), el `url_accion` se construía con `leadsBase(req)` — que lee el rol del **remitente** (el advisor), no el del **receptor** (el manager) — produciendo `/advisor/leads/:id` en vez de `/manager/crm/leads/:id`. Como `ADVISOR_LIKE` permite a managers navegar rutas `/advisor/*` y `getLeadVisibleById` los reconoce como dueños vía `advisor_id`, la página SÍ cargaba (por eso no se veía como error obvio), pero quedaba en el namespace equivocado y — antes del fix de arriba — nunca recibía `desde_notif=1`. Corregido usando `decision.target.role` (el rol real del receptor), igual que ya hacía `directivo/crm.controller.js`.

---

## Comportamiento inescapable (diseño intencional)

El popup de `lead_transferido/lead_publico/lead_traspaso` **no puede ser esquivado**:

- Aparece al cargar **cualquier página** del proyecto (vía `replayPendientes` en cada reconexión SSE)
- Si el usuario navega a otra página → SSE reconecta → popup vuelve a aparecer
- Si el usuario usa el botón **Atrás** del navegador → el listener `pageshow` detecta la restauración desde bfcache y reconecta el SSE manualmente → popup vuelve a aparecer
- La única manera de deshacerse del popup es **registrar el primer contacto**
- El popup bloquea la tecla Escape y no tiene botón de cierre

---

## `replayPendientes(userId)` — función clave

**Archivo:** `src/services/notificaciones.service.js`

**Cuándo se ejecuta:** Cada vez que un usuario abre la conexión SSE (`/notificaciones/stream`), es decir, al cargar cualquier página del proyecto que tenga `notificaciones.js`. También disponible vía `GET /notificaciones/replay-check` (endpoint ligero para llamadas externas).

**Condiciones del query:**

Para `lead_transferido`, `lead_publico`, `lead_traspaso`:
- `user_id = userId`
- `tipo IN (...)` — incluye los 4 tipos
- `created_at > NOW() - INTERVAL '24 hours'` — ventana máxima de 24 horas
- **`leida` se ignora** — puede haberse marcado como leída al abrir el panel sin haber registrado contacto
- `l.advisor_id = $1` — el lead debe seguir asignado a este usuario (si fue escalado a otro, no replay)
- `NOT EXISTS` — no hay actividad en `crm_activities` con `created_at > transferred_at` (primer contacto no registrado)

Para `lead_expirado`:
- `leida = false` — el clic en "Enterado" la marca como leída; esa es la condición de cierre
- Sin check de actividades (el lead ya no es del asesor)

- `ORDER BY created_at DESC LIMIT 1` — solo la más reciente

**Sin ventana mínima de tiempo:** La deduplicación de popups dentro de la misma carga de página la maneja `_lbUrls` (Set en memoria). No se necesita un retardo mínimo.

**`is_replay: true`:** Los replays se marcan con este campo en el payload. El cliente lo usa para NO incrementar el badge (la notificación ya fue contada en el fetch inicial de badge).

---

## `_mostrarModalLead(notif)` — guards (cuándo NO se muestra el popup)

**Archivo:** `public/js/notificaciones.js`

### Guard 1: ya está en la página del lead (lead_transferido / lead_publico / lead_traspaso)
```javascript
// Si el usuario ya está en /leads/:id (contact o show), no mostrar popup
if (!esRec && (tipo === 'lead_transferido' || tipo === 'lead_publico' || tipo === 'lead_traspaso')) {
  var leadMatch = url_accion.match(/\/leads\/(\d+)/);
  if (leadMatch && pathname.indexOf('/leads/' + leadMatch[1]) !== -1) {
    // Omitir popup — ya está en la página correcta
  }
}
```

### Guard 2: recordatorios — ya está en contact.ejs
```javascript
if (esRec && pathname.indexOf('/contact') !== -1) {
  // Omitir popup — ya está registrando contacto
}
```

### Guard 3: recordatorios — modal de resultado ya abierto
Si `outcomeModal` o `outcomeMobileSheet` están visibles, encola el popup y reintenta en 5 segundos.

### Guard 4: recordatorios — ya está en show.ejs del mismo lead
Si `pathname` coincide con `/leads/:id` del lead del recordatorio, abre el modal de resultado directamente sin popup.

---

## Funciones de modal

### `mostrarBurbujaNuevoLead(notif)`
- Entrada: notificación de tipo `lead_transferido`, `lead_publico`, `lead_traspaso`, `recordatorio_*`
- Agrega a la cola `_lbCola` y llama `_siguienteModalLead()`
- Evita duplicados con `_lbUrls` (Set por `url_accion`, se resetea en cada carga de página)

### `_mostrarModalLead(notif)` (función interna)
- Construye el overlay bloqueante con:
  - Avatar + nombre del actor que transfirió (o "Escalación Automática" si no hay actor)
  - Nombre del lead
  - Datos de contacto, producto, observaciones
  - Botón **"Atender lead"** → navega a `/advisor/leads/:id/contact`
- **NO marca la notificación como leída** al navegar — la notificación permanece `leida=false`
- Botón de Escape bloqueado (no se puede cerrar con teclado)

### `mostrarModalLeadExpirado(notif)`
- Solo para tipo `lead_expirado`
- Modal naranja/ámbar con header gradiente, ícono ⏰, diseño consistente con el modal principal
- Muestra el mensaje del cron que incluye el nombre del lead
- Botón **"Enterado"**:
  1. Marca como leída (`fetch /notificaciones/:id/leer`)
  2. Cierra el modal con animación — **sin navegar a ninguna página** (antes redirigía a la bandeja de leads; se quitó en jul 2026 porque interrumpía al usuario si estaba trabajando en otra pantalla)

---

## SSE handler — decisión de qué modal mostrar

**Archivo:** `public/js/notificaciones.js` (función `conectarSSE`)

```
notif recibida vía SSE:
  → notif.is_replay === true  → NO incrementar badge (ya contado en fetch inicial)
  → tipo === 'lead_transferido' | 'lead_publico' | 'lead_traspaso' | 'recordatorio_*'
      → mostrarBurbujaNuevoLead(notif)   [modal bloqueante]
  → tipo === 'lead_expirado'
      → mostrarModalLeadExpirado(notif)  [modal informativo → redirige a bandeja]
  → cualquier otro tipo
      → mostrarToast(notif)              [toast esquina inferior derecha]
```

---

## Listener `pageshow` — bfcache

**Archivo:** `public/js/notificaciones.js`

```javascript
window.addEventListener('pageshow', function(e) {
  if (e.persisted) {
    // Página restaurada desde bfcache (botón Atrás del navegador)
    // El JS no se recargó — reconectar SSE manualmente para disparar replayPendientes
    if (_eventSource) { _eventSource.close(); _eventSource = null; }
    conectarSSE();
  }
});
```

Sin este listener, si el usuario presionaba Atrás, el navegador restauraba la página sin recargar JS ni reconectar el SSE. El popup no aparecía. Ahora sí.

---

## Notificación `lead_expirado` — generada por el cron

**Archivo:** `src/services/escalacion.cron.js`

Cuándo se genera: en los 3 CASOs donde un asesor pierde el lead por no atenderlo en 5 minutos.

**Mensaje:** `⏰ Se venció tu tiempo para atender el lead "Nombre Apellido" y fue reasignado automáticamente.`

**URL acción:** `/advisor/leads/:id` (el ID del lead que fue reasignado)

**Actor:** `null` — por eso el modal muestra "Escalación Automática"

**Al hacer clic en "Enterado":** el modal se cierra (sin redirigir a ninguna página — ver jul 2026 en el Changelog).

---

## Páginas que reciben popups (tienen notificaciones.js)

El popup aparece en **cualquier página del proyecto** donde el usuario esté logueado, porque `notificaciones.js` se incluye en:

- **Layout principal** (`views/layouts/main.ejs`) → cubre todas las vistas con layout: advisor CRM, manager CRM, admin, perfil, etc.
- **Vistas standalone** (layout: false) que lo incluyen manualmente:
  - `views/directivo/` — 14 vistas
  - `views/marketing/crm/leads/transfer.ejs`
  - `views/manager/partials/shell_end.ejs` → cubre todas las vistas del manager

---

## Popup "Primer contacto registrado"

**Cuándo aparece:** Inmediatamente después de que el asesor o manager guarda con éxito el formulario de primer contacto (`contact.ejs`).

**Cómo funciona:**
1. Controller detecta si es el primer contacto (`isFirstSubmit = actividadesPrevias.length === 0`)
2. Si es primer contacto: redirect a `show.ejs` con `?primer_contacto=1`
3. `show.ejs` detecta `queryObj.primer_contacto === '1'` e inyecta un `<script>` inline que crea el popup
4. El popup muestra dos botones: **"Ir a perfilamiento"** (redirige) y **"Ahora no"** (cierra)

**Vistas donde aparece:**
- `views/advisor/crm/leads/show.ejs` — redirige a `/advisor/leads/:id/profile`
- `views/manager/crm/leads/show.ejs` — redirige a `/manager/crm/leads/:id/profile`

**Controllers que generan el redirect:**
- `src/controllers/advisor/crm.controller.js`
- `src/controllers/manager/crm.controller.js`

**Comportamiento:** El popup solo aparece una vez por carga de página. Si el usuario recarga sin `?primer_contacto=1`, no aparece. Es intencional.

---

## Reglas críticas para futuros cambios

1. **Si se agrega un nuevo tipo de notificación que debe mostrar popup:**
   - Agregar el tipo al array en `replayPendientes` (`notificaciones.service.js`)
   - Definir si usa `leida = false` como condición de cierre (como `lead_expirado`) o `NOT EXISTS` actividades (como `lead_transferido`)
   - Agregar el tipo a `esModalLead` o crear un nuevo handler en el SSE handler (`notificaciones.js`)
   - Definir color, icono y etiqueta en los mapas de `notificaciones.js`
   - Actualizar este documento

2. **Si se cambia cuándo desaparece el popup de `lead_transferido`:**
   - Modificar el `NOT EXISTS` en `replayPendientes` (`notificaciones.service.js`)
   - La condición actual es: ninguna actividad en `crm_activities` con `created_at > transferred_at`
   - El lead debe seguir asignado al usuario (`l.advisor_id = $1`)

3. **Si se agrega una nueva vista standalone** (controller con `layout: false`):
   - Agregar manualmente `<script src="/js/notificaciones.js"></script>` antes de `</body>`
   - Sin esto, el popup no aparece en esa página y el botón Atrás no reconecta SSE

4. **NO marcar la notificación como leída al hacer click en "Atender lead"** — es intencional. El popup debe volver a aparecer si el asesor navega sin registrar primer contacto.

5. **Si se agrega un nuevo tipo cuyo `url_accion` pueda apuntar a un lead con actividad previa**, replicar el patrón `desde_notif=1` → `abrir_resultado=1` de la sección "Traspaso/transferencia con primer contacto ya registrado". No asumir que basta con agregarlo a `esModalLead`: sin este guard, el receptor vería el formulario de primer contacto sobre un lead que ya fue contactado.

6. **Al construir `url_accion` de una notificación, usar SIEMPRE el rol del RECEPTOR, nunca el del remitente.** El bug de jul 2026 (ver Changelog) ocurrió porque `leadsBase(req)` lee `req.session.user.role` (quien envía) para construir la URL de a dónde debe ir *el otro usuario*. Si el destino puede ser un rol distinto al del remitente (p. ej. advisor → manager), derivar la URL del rol real del destinatario (`decision.target.role`, como ya hace `directivo/crm.controller.js`), no de una función que solo conoce al remitente.

---

## Botón "Omitir lead" (popup de `lead_transferido`)

**Regla de negocio (jul 2026):** en el popup de "Tienes un nuevo lead" (`lead_transferido`), el asesor/manager/directivo receptor puede omitirlo — el lead pasa de inmediato al siguiente en la lista global de escalación, exactamente con el mismo orden/reglas que la escalación automática por timeout.

**Alcance:**
- Solo `lead_transferido` (no `lead_publico` ni `lead_traspaso`).
- Aplica tanto a leads Outlet/global como a **Residencial** — `escalarLead()` ya distingue sola qué lista usar (`producto === 'Residencial'` → lista por gerencia de `escalacionListaResidencial.service.js`; cualquier otro producto → lista global).
- Si la lista global se agota, sigue la **misma cadena de respaldo** que la escalación normal (Daniel Rojas → Denisse Hansen).
- Pide **confirmación** antes de ejecutarse ("¿Seguro? Pasará al siguiente asesor en la lista").

**Auditoría:** cada omisión inserta una fila en `crm_lead_omissions (lead_id, advisor_id, created_at)`. No aparece en el timeline de movimientos del lead (`crm_lead_transfers`/`escalacion_historial` siguen mostrando el genérico "Escalación automática...", sin distinguir que fue una omisión manual — intencional, para no exponer frente a otros usuarios quién omitió qué). Desde jul 2026 sí existe un **reporte dedicado** que lee esta tabla — ver sección siguiente.

**Reporte "Leads omitidos" (jul 2026):** página de estadística sobre `crm_lead_omissions`, visible solo para **admin, manager y directivo** (nunca para advisor/marketing/externo/etc.).
- `src/controllers/reportes/leadOmissions.controller.js` — controlador compartido; decide alcance según rol: admin/directivo ven toda la empresa, manager ve solo su equipo (`u.manager_id = él` o él mismo).
- Vistas separadas por rol (mismo patrón que el resto del proyecto — sin sidebar/shell compartido entre roles): `views/admin/reportes/lead-omissions.ejs`, `views/manager/reportes/lead-omissions.ejs` (usa `shell_start`/`shell_end`), `views/directivo/reportes/lead-omissions.ejs`.
- Rutas: `GET /admin/reportes/leads-omitidos`, `GET /manager/reportes/leads-omitidos`, `GET /directivo/reportes/leads-omitidos` — cada una protegida por el `requireRole`/`router.use(requireRole(...))` ya existente en su router.
- Contenido: total de omisiones, tabla "por asesor" (nombre, rol, total, última vez) y tabla "actividad reciente" — paginada, **20 por página** (`?page=N`, con controles Anterior/Siguiente y "Página X de Y · Z en total"), con columnas: fecha, asesor, **ID del lead, nombre del lead, producto, precio, dirección completa** (calle, número ext./int., colonia, municipio, estado, CP armados en un solo string).
- Agregado al sidebar de los 3 roles.
- Responsive móvil: las 3 vistas envuelven sus tablas en scroll horizontal (`overflow-x:auto` + texto sin wrap) dado que ahora tienen 7 columnas; padding/tipografía se reducen en pantallas ≤640px y la paginación se centra.
- Verificado renderizando las 3 vistas contra datos reales de la BD local (incluye las pruebas del propio usuario al probar "Omitir lead" — Esteban Quito Rojo aparece con sus omisiones reales) y probando la paginación con 25 registros sintéticos (20 en página 1, 11 en página 2, limpiados después).

**Mecanismo:**
- `escalarLead(lead, opts = {})` (`src/services/escalacion.cron.js`) ahora **retorna** `{ transferido, nextUserId?, motivo }` en cada punto de salida (cambio aditivo — el cron sigue ignorando el valor de retorno, sin cambio de comportamiento). Se exporta (`exports.escalarLead`) para reutilizarse fuera del tick del cron. Acepta `opts.origen = 'omitido'` para distinguir una omisión manual de un timeout real (ver notificación `lead_omitido` abajo).
- `src/services/leadOmission.service.js` — `omitirLead(leadId, advisorId)`: valida que el lead exista, que siga asignado a ese usuario y que no tenga actividad registrada tras `transferred_at` (mismo criterio que `transferirLead`); si el lead nunca tuvo `escalacion_gerencia_inicio` (asignación fuera del flujo normal), lo calcula igual que lo haría marketing al activar escalación por primera vez. Llama a `escalarLead(lead, { origen: 'omitido' })` y registra la auditoría.
- Rutas: `POST /advisor/leads/:id/omitir`, `POST /manager/crm/leads/:id/omitir`, `POST /directivo/crm/:id/omitir` — las 3 llaman al mismo servicio.
- Frontend (`public/js/notificaciones.js`, `_mostrarModalLead`): botón "Omitir lead" con confirmación inline (Cancelar / Sí, omitir). La URL del POST se deriva de `notif.url_accion` (no del rol) para ir siempre al mismo namespace donde "Atender lead" ya funciona para ese usuario — evita reconstruir la URL con lógica de rol duplicada y propensa a los mismos bugs de namespace documentados arriba. Al confirmar exitosamente, cierra el modal sin navegar (`cerrarModal(false)`) y pasa al siguiente popup en cola si hay alguno.

**Notificación `lead_omitido` (distinta de `lead_expirado`):** cuando la reasignación fue disparada por "Omitir lead" (no por timeout del cron), quien pierde el lead recibe un tipo de notificación distinto — `lead_omitido` en vez de `lead_expirado` — con un mensaje neutral ("El lead 'X' fue asignado a otro asesor. Lamentamos que no hayas podido atenderlo esta vez.") en vez de "Se venció tu tiempo...". Nuevo popup `mostrarModalLeadOmitido()` (clon de `mostrarModalLeadExpirado` con tono gris/neutral en vez de rojo, imagen `/img/juan/JuanResignado.png`, sin la tarjeta de "consejo: registra en 5 minutos" que no aplica a una decisión deliberada). Mismo ciclo de vida que `lead_expirado`: se cierra marcando `leida=true` vía "Entendido", sin navegar a ninguna página; agregado a `TIPOS_POPUP_LEAD` (exención de popups) y a la ventana de replay de 24h en `replayPendientes()`.

**Bug real encontrado al reprobar con el usuario en local (dos capas):**
1. Un lead asignado por una vía que nunca activa escalación (p. ej. asignación directa desde admin, no marketing ni el cron) llega con `escalacion_gerencia_inicio = NULL` y `escalacion_activa = false`. `escalarLead()` ya se detiene defensivamente cuando `escalacion_gerencia_inicio` es NULL (evita loops infinitos), así que "Omitir" fallaba con un error genérico para cualquier lead que nunca hubiera pasado por el flujo normal de escalación. Fix en `leadOmission.service.js`: si `escalacion_gerencia_inicio` es NULL, se calcula y persiste con `calcularPuntoDePartida(advisor_id)` (global o Residencial según el producto — misma función que ya usan marketing/manager al activar escalación por primera vez) antes de llamar a `escalarLead()`.
2. Al reprobar con el lead real (Residencial, asesor sin pertenecer a ninguna lista de gerencia Residencial), `calcularPuntoDePartida()` regresó `null` porque el asesor actual no está ni en la lista de Furlong ni en la de Mercado — y el fix anterior bloqueaba con otro error genérico. Pero `escalacionListaResidencial.service.js`'s `obtenerSiguienteAdvisor()` **ya resuelve exactamente este caso sin necesitar un punto de partida real**: si el asesor actual no pertenece a ninguna gerencia, manda el lead directo a Daniel Rojas (mismo comportamiento que tendría la escalación automática). Fix: para Residencial, si `calcularPuntoDePartida` da `null`, se usa el propio `advisor_id` como placeholder (su valor nunca se consulta en esa rama) y se deja que `escalarLead()` mande el lead a Daniel Rojas normalmente. Para la lista global, `null` sigue bloqueando (ahí sí significa "la lista está completamente vacía", un caso genuinamente sin a quién mandarlo).

**Verificación:** se probó `omitirLead()` contra la BD local con leads reales de prueba: (1) Outlet con escalación activa — siguiente en la lista global; (2) Residencial con escalación activa — siguiente en la lista de su gerencia (Mercado); (3) Residencial con `escalacion_gerencia_inicio` NULL pero asesor sí en una lista — calculó el punto de partida y reasignó bien; (4) el caso real reportado — Residencial, `escalacion_gerencia_inicio` NULL, asesor que NO pertenece a ninguna lista Residencial — fue correctamente a Daniel Rojas. Los 4 insertaron su fila de auditoría con el asesor y lead correctos. Casos de rechazo verificados: lead que ya no pertenece al usuario, lead con actividad ya registrada — devuelven `ok:false` con mensaje claro y no tocan nada en BD.

---

## Changelog

**Jul 2026 — "Enterado"/"Entendido" ya no navega a la bandeja:** en `mostrarModalLeadExpirado` y `mostrarModalLeadOmitido`, el botón de cierre marcaba la notificación como leída y además hacía `window.location.href` a la bandeja de leads — si el usuario estaba trabajando en otra pantalla, lo sacaba de ahí sin que lo pidiera. Se quitó la navegación; el botón ahora solo marca como leída y cierra el popup.

**Jul 2026 — Exención extendida a Leonardo Furlong (id=50):**
- Manager Residencial con volumen alto de leads — misma razón que Daniel y Denisse.
- Solo BD: `UPDATE users SET suppress_lead_popups = true WHERE id = 50;` (ejecutado en Render).
- Sin cambios de código — el caché lo toma en ≤5 min.

**Jul 2026 — Exención extendida a Denisse Hansen (`FALLBACK_2_ID = 7`):**
- Misma razón que Daniel Rojas: receptor final de la cadena, volumen alto de leads.
- Cambios en código (`notificaciones.service.js`): importa `FALLBACK_2_ID`, fallback en memoria incluye a ambos, seed de columna nueva siembra a ambos.
- Cambio en BD (ejecutar manualmente en Render): `UPDATE users SET suppress_lead_popups = true WHERE id = 7;`
- Sin cambios en `notificaciones.js` ni en ninguna vista — el mecanismo ya existente funciona igual para cualquier usuario con el flag activo.

**Jul 2026 — Revisión con skill `code-review` sobre notificaciones/popups/excepción Daniel Rojas (10 fixes):**
Se corrió `code-review` a esfuerzo "high" sobre el diff acumulado de este tema (16 archivos) buscando bugs, errores silenciosos y pérdida de datos. Se reportaron y corrigieron 10 hallazgos:
1. **URL de traspaso rota** (`manager.routes.js`, 2 sitios): dos `lead_traspaso` usaban `/manager/crm/${leadId}` en vez de `/manager/crm/leads/${leadId}` — sin `/leads/` no matchea ninguna ruta (404) cuando `notificaciones.js` le agrega `/contact?desde_notif=1`.
2. **Web Push saltado por SSE en otro dispositivo** (`notificaciones.service.js`, `_pushWebPush`): ver corrección arriba en la sección de deduplicación — bug real de meses atrás, no solo desactualización de este doc.
3. **Condición de carrera en `crearNotificacion`** (`notificaciones.service.js`): el guard anti-duplicado de 30 min era SELECT-luego-INSERT sin transacción — dos llamadas simultáneas (p. ej. el cron de escalación disparando en dos ticks solapados) podían crear duplicados. Ahora usa un cliente dedicado con `BEGIN`/`pg_advisory_xact_lock(hashtext(...))`/`COMMIT` por clave `user_id|tipo|mensaje|url`, atómico y sin bloquear notificaciones no relacionadas.
4. **Falta índice para el guard anti-duplicado**: se agregó `idx_notif_dedup ON notificaciones (user_id, tipo, created_at DESC)` en `recordatorio.cron.js` (mismo lugar donde ya se creaba `idx_notif_no_leidas`).
5. **Badge/panel desincronizados para manager/directivo/admin**: el panel mostraba como "no leídas" notificaciones de todo el equipo que nunca contaban para el badge (`contarNoLeidas` solo cuenta filas propias) — visualmente parecía que había más pendientes de lo que decía la campana. Ahora las filas ajenas (de otros miembros del equipo) siempre se muestran como leídas en el panel de manager/directivo/admin.
6. **Actualización prematura de UI en `marcarLeida`** (`notificaciones.js`): la clase `notif-item-leida` se aplicaba de forma síncrona antes de confirmar la respuesta del servidor — si el POST fallaba, el ítem quedaba visualmente marcado como leído sin estarlo en BD. Se movió dentro del `.then()`, junto al decremento del badge.
7. **Texto contradictorio en el badge de urgencia** (3 vistas `contact.ejs`): el badge decía "Primer contacto" incluso cuando el título de la página decía "Registrar contacto" (`IS_FIRST=false`, `urgentFirstTouch=true` — ver Causa 6 más abajo). Ahora el badge usa `IS_FIRST` para elegir el texto, igual que el título.
8. **Caché stale de documentos de Drive en el Service Worker** (`public/sw.js`): `/media/drive/:id` estaba en el matcher Cache-First de imágenes, pero ese endpoint también sirve PDFs (fichas técnicas, contratos) bajo la misma forma de URL — si el archivo de Drive se reemplazaba (mismo id, contenido nuevo), quien ya lo tenía cacheado seguía viendo la versión vieja indefinidamente. Se sacó de la estrategia Cache-First (el servidor ya fija `Cache-Control` correcto por tipo real) y se subió `CACHE_IMAGES` a `v2` para purgar lo ya atrapado.
9. **Excepción de Daniel Rojas hardcodeada en código**: ver sección "Excepción por usuario" arriba — migrada a columna `users.suppress_lead_popups` con caché en memoria refrescada cada 5 min.
10. **Bloque `#crm-nav-lock` duplicado en 3 archivos**: el CSS+HTML+JS del candado de sidebar (~140 líneas idénticas en `advisor/crm/leads/contact.ejs`, `manager/crm/leads/contact.ejs`, `directivo/crm/contact.ejs`) se extrajo a `views/partials/crm-nav-lock.ejs`, incluido con `<%- include(...) %>` en los 3 archivos. Sin cambio de comportamiento — mismo HTML/JS generado, ahora en un solo lugar para editar.

**Jul 2026 — `lead_traspaso` con primer contacto ya registrado (bug real, reportado con lead #4180):**
- **Síntoma:** un manager recibía un lead vía `lead_traspaso` que ya tenía actividad registrada por el advisor anterior; al hacer clic en "Atender lead" terminaba en el formulario de "Primer contacto" en vez del modal de "Registrar resultado".
- **Causa 1 (URL equivocada):** `advisor/crm.controller.js` construía el `url_accion` del `lead_traspaso` con `leadsBase(req)` (rol del remitente advisor) en vez del rol del receptor, generando `/advisor/leads/:id` en vez de `/manager/crm/leads/:id`. Corregido usando `decision.target.role`.
- **Causa 2 (guard incompleto):** el guard `desde_notif=1` → `abrir_resultado=1` solo cubría `lead_transferido`. Se extendió a `lead_traspaso` en `cerrarModal()` (`notificaciones.js`) porque se confirmó con datos reales que el manager/directivo receptor de un traspaso se vuelve dueño directo del lead y puede trabajarlo igual que un advisor — la documentación anterior de este archivo afirmaba lo contrario (que "el manager solo asigna, nunca contacta"); esa afirmación era incorrecta y quedó corregida arriba.
- **Causa 3 (guard faltante en directivo):** `directivo/crm.controller.js` nunca tuvo el guard `desde_notif`/`abrir_resultado`, ni `directivo/crm/show.ejs` el auto-click de `#btnOutcome`. Se agregaron ambos, replicando el patrón de advisor/manager.
- **Causa 4 (LA REAL, encontrada al reprobar con el usuario en producción — un CUARTO mecanismo, independiente del popup SSE):** `views/advisor/crm/leads/show.ejs` tiene su **propio overlay bloqueante** (`#fc-overlay`, "Registra el primer contacto") con una condición `_fcBloquear` **totalmente aparte** del guard `desde_notif`/`isFirst` de `contactForm`. Esta condición decide si mostrar el overlay usando `_isManagerView`/`_isDirectivoView`, que dependen de la variable `viewMode` — pero `viewMode` **solo se setea en la ruta de "supervisión" `/manager/leads/:id`** (manager viendo de solo lectura el lead de SU asesor). Cuando un manager/directivo es el **dueño real** del lead (`advisor_id` le pertenece, típicamente tras un traspaso) y llega a `/advisor/leads/:id` directamente — posible porque `ADVISOR_LIKE` permite el acceso — `viewMode` nunca se define, `_isManagerView`/`_isDirectivoView` quedan en `false`, y el overlay se dispara igual que para un asesor genuino, **sin importar si el guard `abrir_resultado` ya lo habría llevado correctamente al modal de resultado.** El overlay se renderiza siempre al cargar la página, independientemente de query params. Fix: se agregó `_viewerEsSupervisor` (basado en `user.role` real de sesión, no en `viewMode`) a la condición de `_fcBloquear` (`views/advisor/crm/leads/show.ejs`, bloque "Bloqueo de primer contacto"). El comportamiento para asesores genuinos (incluyendo la regla intencional de "actividades de asesores anteriores no cuentan" en traspasos advisor→advisor) **no cambió**.
- **Causa 5 (QUINTA causa, encontrada al reprobar de nuevo — con las 4 anteriores corregidas, la página cargaba bien pero SIN NINGÚN botón de acción):** en el lead #4180 real, el asesor anterior (Jose Arturo) **ya había registrado el resultado de su única actividad** antes de traspasar (`hasPendingOutcome = false` — no hay nada pendiente que abrir, así que el auto-click de `#btnOutcome` no encontraba el botón, correctamente, y no pasaba nada visible). El problema es que el botón alternativo, **"Registrar contacto"**, estaba condicionado a `activitiesCount === 0` en las 3 vistas (`advisor/crm/leads/show.ejs`, `manager/crm/leads/show.ejs`, `directivo/crm/show.ejs`) — es decir, solo aparecía si el lead **nunca** había tenido actividad. Con 1 actividad ya cerrada y ninguna pendiente, **ningún botón de acción se mostraba**: ni "Registrar resultado" (correcto, nada pendiente) ni "Registrar contacto" (bug — bloqueado sin motivo). Este estado ("actividades > 0, pero todas cerradas, sin seguimiento programado") es precisamente lo que deja un traspaso cuando el asesor anterior cierra su llamada y decide escalar en vez de agendar el siguiente contacto — no es exclusivo de este lead. Fix: la condición cambió de `activitiesCount === 0` a `!hasPendingOutcome` en las 3 vistas (la primera implica la segunda, así que es un ensanchamiento seguro, no un cambio de comportamiento existente). Además, el script de `abrir_resultado=1` ahora muestra un aviso flotante autocontenido ("Este lead ya tiene contacto registrado — continúa el seguimiento cuando quieras") cuando no hay `#btnOutcome` que abrir, en vez de no hacer nada visible.
- **Verificación:** se probó invocando directamente los controllers (sin HTTP) contra el lead real #4180 en la BD local, por ambas rutas (manager namespace correcto y advisor namespace de una notificación vieja en caché) — en ambos casos: `#fc-overlay` ausente, `#btnOutcome` ausente (correcto, nada pendiente), botón "Registrar contacto" presente y apuntando al namespace correcto (`/manager/crm/leads/4180/contact` o `/advisor/leads/4180/contact` según la ruta), aviso flotante incluido. Control de no-regresión: un lead real con actividad genuinamente pendiente (#4815) sigue mostrando `#btnOutcome` normalmente.
- **Causa 6 (SEXTA causa — al llegar al formulario "Registrar contacto" de la Causa 5, no aplicaba ninguna de las restricciones de urgencia de un lead nuevo):** `isFirst` en `contactForm` (los 3 controllers) se calculaba como "¿el lead tiene ALGUNA actividad, de cualquier dueño, alguna vez?" — para el lead #4180 eso da `false` (si tiene 1, la de Jose Arturo), así que el formulario se comportaba como "contacto de seguimiento": selector de bloque horario libre, cualquier fecha futura, sin bloqueo de sidebar/navbar. Pero el manager **nunca había contactado personalmente** este lead — para él es, en la práctica, su primer contacto real, y debía cumplir las mismas reglas que un lead genuinamente nuevo. Se separaron dos conceptos que antes vivían en una sola bandera `isFirst`:
  - **`isFirst`** (sin cambios): "¿alguien, alguna vez, contactó este lead?" — sigue controlando el título ("Primer contacto" vs "Registrar contacto"), las secciones opcionales Material/Soporte (`<% if (!IS_FIRST) %>`) y `propertiesLocked` (folio bloqueado de solo lectura). Estos se mantienen intactos porque el lead **sí** tiene historial — es lo que el usuario pidió dejar igual ("lo demás se deja").
  - **`urgentFirstTouch`** (nuevo): "¿el RECEPTOR actual ya registró una actividad después del último traspaso?" — mismo criterio que `_fcBloquear` en show.ejs (`_actsAfterTransfer`). Cuando es `true`, se activan las reglas de urgencia: `CALL_ONLY` (solo llamada), la fecha queda fija a hoy y la hora limitada a los próximos 5 minutos desde `lead.transferred_at` (en vez del selector de bloques horarios), y `LOCK_NAV` bloquea clics en sidebar/navbar hasta guardar el formulario (mecanismo `#crm-nav-lock`, que además **no existía en absoluto** en `manager/crm/leads/contact.ejs` ni en `directivo/crm/contact.ejs` — se agregó ahí por primera vez, replicado de advisor).
  - `isFirst` implica `urgentFirstTouch` siempre (0 actividades ⇒ ninguna después del traspaso tampoco), así que es un superconjunto seguro: todo lo que antes calificaba como "primer contacto" urgente lo sigue siendo.
  - Se aplicó también server-side en `contactSubmit` (los 3 controllers): la validación de fecha/hoy/5-min ahora usa `urgentFirstTouchSubmit` (mismo criterio) en vez de `isFirstSubmit`, para que el servidor rechace lo mismo que el formulario restringe visualmente. `directivo/crm.controller.js` nunca había tenido esta validación server-side en absoluto — se agregó.
  - **Layout:** la tarjeta "Bitácora / Observaciones del contacto" se movió de la columna derecha a la izquierda (justo después de "Agenda") en las 3 vistas — antes dejaba un hueco grande bajo la columna izquierda (una sola tarjeta corta) mientras la derecha acumulaba Propiedad + Material + Soporte.
  - **Verificación:** se renderizó el HTML real de `/manager/crm/leads/4180/contact` para el manager 35 — confirmado simultáneamente: título "Registrar contacto" (no "Primer contacto"), badge de urgencia visible, `#crm-nav-lock` presente, Material/Soporte visibles, folio bloqueado, `IS_FIRST_CONTACT=true` y `CALL_ONLY=true` en el JS. Control de no-regresión con un lead real donde el manager ya tenía actividad propia tras su traspaso (#883): `IS_FIRST_CONTACT=false`, sin `#crm-nav-lock`, sin badge de urgencia. Orden de secciones (Agenda → Bitácora → Propiedad) confirmado sin duplicados.

**Jul 2026 — Deduplicación y paginación de notificaciones** (afecta `notificaciones.service.js`, `notificaciones.js`, `main.routes.js`; no cambia el comportamiento de los popups en sí, documentado por tocar archivos de esta tabla):
- `crearNotificacion` ahora tiene guard anti-duplicado de 30 min (mismo `user_id`+`tipo`+`mensaje`+`url`) — si el cron reintenta crear la misma notificación (p. ej. `lead_expirado` reenviado en cada tick), regresa el id existente en vez de insertar y re-empujar. `replayPendientes` no se ve afectado: no inserta, solo reenvía filas ya existentes.
- ~~Web Push ya no se envía si el usuario tiene una conexión SSE activa~~ — **corregido en la revisión de jul 2026 (ver Changelog más abajo):** esa condición comparaba contra el registro global de conexiones (`conexiones.has(userId)`), no contra el dispositivo que recibía el push. Un usuario con la app abierta en PC (SSE activo) nunca recibía push en el celular, aunque el celular no tuviera SSE. Ahora Web Push siempre se envía a todas las suscripciones del usuario; no depende del estado de SSE en ningún dispositivo.
- El panel de notificaciones (campana) ahora pagina de 20 en 20 y deduplica copias de broadcasts para manager/directivo/admin. Los **popups de lead siguen sin paginar** — `replayPendientes` siempre trae 1 registro (`LIMIT 1`), sin cambios.
- `marcarLeida` ahora usa `keepalive: true` en el cliente para que el POST sobreviva a la navegación inmediata — relevante para el botón "Enterado" de `lead_expirado`, que marca leída y redirige en el mismo click.

5. **`replayPendientes` solo toma 1 notificación** (`LIMIT 1`, `ORDER BY created_at DESC`). Si hay pendientes de múltiples tipos, prioriza la más reciente.

6. **La ventana de replay es hasta 24 horas** hacia atrás, sin mínimo. Fuera de 24 horas, la notificación no se reproduce aunque el lead siga sin contacto.

7. **`leida` no es condición para `lead_transferido/lead_publico/lead_traspaso`** — el panel de notificaciones puede marcarlas como leídas al abrirlas. La verdadera condición de "ya atendido" es que haya una actividad después de `transferred_at`.
