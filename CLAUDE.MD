# CLAUDE.md — Inmovalor / Altaltium Real Estate Solutions

## STACK Y DESPLIEGUE

- **Runtime:** Node.js v24 + Express v5
- **BD:** PostgreSQL (Render — DATABASE_URL)
- **Vistas:** EJS + express-ejs-layouts (server-side rendering, NO SPA)
- **CSS:** Tailwind CDN + public/css/styles.css
- **Deploy:** Render (plan Free, 512MB RAM)
- **Repo:** arquitectura MVC modular
- **CLAUDE.md** ya existe en la raíz del proyecto

---

## VARIABLES DE ENTORNO REQUERIDAS

```
DATABASE_URL
SESSION_SECRET
BASE_URL
GOOGLE_SERVICE_ACCOUNT_B64
GOOGLE_MAPS_API_KEY
DRIVE_INVENTARIO_FOLDER_ID
DRIVE_CONTRATOS_FOLDER_ID
CLOUDINARY_CLOUD_NAME
CLOUDINARY_API_KEY
CLOUDINARY_API_SECRET
GOOGLE_CALENDAR_CLIENT_ID
GOOGLE_CALENDAR_CLIENT_SECRET
GOOGLE_CALENDAR_REDIRECT_URI
VAPID_PUBLIC_KEY
VAPID_PRIVATE_KEY
VAPID_MAILTO
PDFSHIFT_API_KEY
```

---

## ROLES DEL SISTEMA

| Rol | Descripción |
|---|---|
| admin | Acceso total al sistema |
| manager | Gerente de equipo de asesores |
| advisor | Asesor comercial |
| directivo | Vista ejecutiva global |
| marketing | Registra y transfiere leads |
| administracion | Gestión de contratos |
| externo | Solo ve catálogo sin Lista Oro |
| rrhh | Recursos Humanos: funciones de asesor + Panel RR.HH (Comunidad, Organigrama); no cuenta como advisor en equipos/escalación |

**REGLA CRÍTICA:** Usuarios `externo` NUNCA ven propiedades con `lista = 'Lista Oro'`

---

## ESTRUCTURA DE ARCHIVOS CLAVE

```
src/
  app.js                          ← orden de middlewares CRÍTICO
  routes/
    main.routes.js
    admin.routes.js
    advisor.crm.routes.js
    manager.routes.js
    manager.crm.routes.js         ← debe montarse ANTES de manager.routes
    admin.fichas.routes.js
    rrhh.routes.js                ← Panel RR.HH (rrhh/directivo/admin)
  controllers/
    advisor/crm.controller.js
    manager/crm.controller.js
    admin/inventario.controller.js
    admin/inventarioOutlet.controller.js
    admin/inventarioSubastas.controller.js ← Subastas 2026 (solo carga masiva, sin CRUD manual)
    admin/fichas.controller.js
    admin/reportes.controller.js
    admin/calendarBackfill.controller.js  ← panel backfill Google Calendar
    marketing/crm.controller.js
    rrhh/panel.controller.js      ← Comunidad, Organigrama (BD, tabla users)
    reportes/leadOmissions.controller.js  ← reporte "Leads omitidos" (admin/manager/directivo)
  services/
    notificaciones.service.js
    recordatorios.cron.js         ← inicia todos los crons
    escalacion.cron.js            ← cron de escalación automática
    leadOmission.service.js       ← lógica de "Omitir lead" (popup)
    googleCalendar.service.js     ← OAuth + CRUD de eventos
    calendarBackfill.service.js   ← backfill de actividades históricas a Google Calendar
    calendarBackfill.cron.js
    fichas.service.js
    pdfshift.service.js
    googleDrive.service.js
    cloudinary.service.js
views/
  layouts/main.ejs
  partials/navbar.ejs
  advisor/crm/partials/sidebar.ejs
  manager/crm/partials/sidebar.ejs
  admin/partials/sidebar.ejs
  directivo/partials/sidebar.ejs
  administracion/partials/sidebar.ejs
  manager/partials/sidebar.ejs
  admin/fichas/template-outlet.ejs
  admin/reportes/index.ejs
  admin/inventario-subastas/index.ejs, importar.ejs ← Subastas 2026 (solo admin)
  pages/inventario-subastas.ejs           ← lista pública "Subastas 2026" (/inventario/subastas)
public/
  css/styles.css
  js/drawer.js                    ← drawer móvil global
  js/notificaciones.js
  img/fichas/                     ← assets para fichas PDF
```

---

## TABLAS DE BD PRINCIPALES

### users
```sql
id, nombre, apellidos, email, username, telefono,
role, gerente, is_active, manager_id, area, avatar_url
```

### inventario (tabla principal residencial)
```sql
id, folio, etapa, tipo, calle, colonia, municipio, estado, cp,
terreno, construccion, recamaras, sanitarios, estacionamientos,
costo_cesion, honorarios, costo_total, precio_publicacion,
precio_comercial, latitud, longitud, titulo, descripcion,
url_imagen, lista, imagenes_folder_id,
estudio_mercado_file_id, ficha_tecnica_file_id,
cotizacion_file_id, is_active
```

### inventario_outlet
```sql
-- mismas columnas base + imagenes, imagenes_orden,
-- imagenes_cache JSONB, google_maps, alrededores
```

### inventario_subastas (ago 2026 — Subastas 2026, remates bancarios)
```sql
id, folio TEXT, semana TEXT, tipo_inmueble TEXT, tipo_juicio TEXT,
calle TEXT, colonia TEXT, municipio TEXT, estado TEXT,
oferta_inicial NUMERIC, ingreso_subasta NUMERIC, almoneda TEXT,
dia SMALLINT, mes TEXT, anio SMALLINT, hora VARCHAR(5),
created_at, updated_at
```
Categoría de inventario separada de Outlet/Residencial — nombrado genérico a
propósito (sin el año en tabla/rutas: `/inventario/subastas`,
`/admin/inventario-subastas`) para no tener que recrear tabla/rutas cada año;
"2026" vive solo en el texto del menú/título de la página. Solo carga masiva
vía plantilla Excel desde `/admin/inventario-subastas/importar`
(`inventarioSubastas.controller.js`) — sin alta/edición manual individual
(a diferencia de Outlet/Residencial). Acceso de lectura igual que
`/inventario/hoja`: `ensureAuth + requireAdvisorLike`.

Fecha de la subasta guardada como 4 columnas separadas (no un TIMESTAMPTZ
único) — decisión explícita del usuario tras la primera versión, que sí
usaba un solo campo de fecha+hora. Detalles del esquema, todos por pedido
explícito del usuario en iteraciones posteriores:
- `mes` es **texto** ("enero".."diciembre"), no número — `normalizeMes()` en
  el controlador acepta tanto el nombre como el número 1-12 al importar y
  siempre normaliza a minúsculas; si el valor no se reconoce se guarda tal
  cual (no rechaza la fila). Como ya no es numérico, ordenar cronológicamente
  requiere un `CASE LOWER(mes) WHEN 'enero' THEN 1 ...` en el `ORDER BY`
  (duplicado en `inventarioSubastas.controller.js` y `main.routes.js`).
- `hora` es texto `HH:MM` (24h). Bug real corregido: si la celda de Excel
  está formateada como hora, `xlsx` la entrega como número (fracción del
  día, ej. `0.4791666` = 11:30) en vez de texto — `horaSanitize()` ahora
  maneja ese caso además del texto plano.
- `folio`/`semana`/`tipo_inmueble`/`tipo_juicio`/`calle`/`colonia`/
  `municipio`/`estado`/`almoneda` son `TEXT` (sin límite de longitud) —
  antes eran `VARCHAR` con límites cortos y algunas filas de import reales
  superaban esos límites (texto libre de +800 caracteres), causando que
  solo se importara una fracción del archivo sin explicación clara.
- `importarProcesar` ya no traga los errores de INSERT en un simple
  contador: cuando hay filas con problemas (de validación o de base de
  datos), la respuesta **renderiza** la página de importar con
  `filaErrores` (fila + motivo real del error) en vez de redirigir con solo
  un número — necesario para diagnosticar por qué no se importa el 100%.

### crm_leads
```sql
id, nombre, apellido, email, telefono,
advisor_id, manager_id, transferred_by, transferred_to,
transferred_at, transfer_note, status, etapa,
closed_at, closed_reason, sale_amount, sale_paid,
sale_signed_only, sale_closed_at,
fecha_hora_mx, created_at, updated_at,
-- Columnas de escalación:
escalacion_activa BOOLEAN DEFAULT false,
escalacion_manager_id INT,
escalacion_origen_id INT,
escalacion_gerencia_inicio INT,
opened_at TIMESTAMPTZ
```

### crm_activities
```sql
id, lead_id, advisor_id, manager_id, type, subtype,
platform, observations, scheduled_at, created_at, updated_at,
property_id, property_folio, property_list, product,
has_ficha_tecnica, has_estudio_mercado, has_cotizacion,
needs_executive, executive_notes, action_label
```

### notificaciones
```sql
id, user_id, tipo, mensaje, url_accion, leida, created_at
```

### escalacion_orden
```sql
id, manager_id, user_id, orden, activo, created_at
UNIQUE(manager_id, orden)
```

### configuracion
```sql
clave VARCHAR(50) PRIMARY KEY,
valor TEXT,
descripcion TEXT,
activo_desde DATE,
updated_at TIMESTAMPTZ
-- Registro: escalacion_activa = 'true'/'false'
```

### Organigrama RR.HH (jul 2026 — migrado de Google Sheet a BD)
El organigrama del Panel RR.HH ahora vive directamente en `users` (antes se
leía en vivo de un Google Sheet vía `organigramaSheet.service.js` — ese
servicio y el env `ORGANIGRAMA_SHEET_ID` quedaron sin uso, el archivo se
eliminó). Columnas nuevas agregadas a `users`:
```sql
puesto     VARCHAR(150)
gerente_id INTEGER REFERENCES users(id)  -- FK real, ya no texto libre
modalidad  VARCHAR(50)                   -- Presencial / Híbrido / Remoto
horario    VARCHAR(150)
```
Reutiliza lo que ya existía: `nombre`, `apellidos`, `email`, `telefono`,
`area`, `avatar_url`, `is_active` (filtra quién aparece). El árbol se
construye en `construirArbol()` (`src/controllers/rrhh/panel.controller.js`)
usando `gerente_id` — con protección contra ciclos por si se captura mal a
mano. Solo **RRHH y admin** pueden editar (`/rrhh/organigrama/editar`,
`requireRole('rrhh','admin')`); directivo sigue viendo el organigrama pero
de solo lectura. Foto por persona vía el mismo mecanismo de Cloudinary que
usa el admin para avatares de usuario (`uploadBufferToFolder`, folder
`avatars`). Vista con avatares + tarjeta de perfil flotante al pasar el
cursor (estilo Teams) sobre la foto — componente nuevo, no había nada
reutilizable en el proyecto para esto. Se empezó vacío (sin importar datos
del Sheet anterior) — RRHH captura todo desde la nueva interfaz.
Reemplaza a las tablas eliminadas org_areas / org_people / org_people_import.

### contract_requests
```sql
id, advisor_id, lead_id, propiedad_id, tabla_propiedad,
cliente_nombre, cliente_rfc, email, email_2, email_3,
telefono, telefono_2, telefono_3,
modalidad_pago VARCHAR(10) DEFAULT '2pagos',
pago_cesion_monto, pago_cesion_pct, pago_cesion_cuando,
estatus, created_at, updated_at
```

### crm_lead_omissions (jul 2026)
```sql
id, lead_id, advisor_id, created_at
-- Auditoría de "Omitir lead" (botón en el popup de nuevo lead). INSERT-only,
-- ninguna vista del proyecto la lee salvo el reporte /reportes/leads-omitidos
-- (admin, manager, directivo). No aparece en el timeline de movimientos del
-- lead ni se muestra a otros usuarios quién omitió qué.
```

### calendar_events / calendar_backfill_errors (jul 2026)
```sql
-- calendar_events ganó la columna activity_id (INTEGER, nullable) para
-- ligar cada evento de Google Calendar a la actividad del CRM que lo generó
-- (dedup entre el sync en vivo y el backfill histórico).
calendar_backfill_errors: id, activity_id, advisor_id, error, created_at
-- Actividades que fallaron al intentar sincronizarse al backfill — evita
-- reintentar en loop infinito la misma actividad rota.
```

---

## SISTEMA DE NOTIFICACIONES (SSE)

**Archivo:** `src/services/notificaciones.service.js`

- SSE nativo Node.js — Map de conexiones por user_id
- Endpoint stream: `GET /notificaciones/stream`
- Toast: esquina inferior DERECHA, 8 segundos, animación slide derecha
- Campana en navbar con badge contador

**Tipos implementados:**
| Tipo | Destinatario |
|---|---|
| nueva_propiedad | todos excepto externo |
| inventario_actualizado | todos excepto externo |
| lead_transferido | advisor receptor |
| lead_traspaso | manager receptor |
| lead_publico | advisor (o fallback marketing) + sus managers |
| recordatorio_cita | advisor (30 min antes) |
| recordatorio_llamada | advisor (30 min antes) |
| sugerencia_lead | manager (1 día sin actividad) |
| cita_agendada | admin/directivo/administracion + gerente del asesor |
| cierre_firma | admin/directivo/administracion + gerente del asesor |
| cierre_pago | admin/directivo/administracion + gerente del asesor |

**Visibilidad por rol:**
- advisor → solo sus notificaciones
- manager → las suyas + advisors de su equipo
- directivo → todas las de la empresa
- admin → todas sin excepción
- externo → no recibe notificaciones

**Bug histórico resuelto:** `res.flush()` en `_pushSSE` para Express 5

---

## SISTEMA DE ESCALACIÓN AUTOMÁTICA DE LEADS

**Archivo principal:** `src/services/escalacion.cron.js`
**Servicios de lista:** `src/services/escalacionLista.service.js` (global), `src/services/escalacionListaResidencial.service.js` (Residencial)

### Cuándo se activa
1. Marketing → asesor, manager o directivo: activa `escalacion_activa = true` (único traspaso manual que la activa)
2. La propia escalación automática del cron (re-escalar al siguiente en la lista)
3. **Ningún otro traspaso manual activa el cron** — manager→asesor (de su propio equipo), asesor→manager, asesor→directivo, directivo→manager y directivo→asesor: NINGUNO activa `escalacion_activa` (regla cambiada ago 2026 — antes manager→asesor sí la activaba; ver "Cambios recientes" más abajo). `transferLead()`/`transferLeadToManager()` (usadas por todos estos traspasos) nunca tocan `escalacion_activa`.

### Condición del cron (WHERE elegibles)
```sql
escalacion_activa = true
AND status = 'open'
AND advisor_id NOT IN (7)                         -- excluye Denisse Hansen (FIN)
AND NOT (advisor_id IN (16, 62) AND producto != 'Residencial')  -- Alexandra Bohorquez, Karla Renteria solo escalan Residencial
AND transferred_at < NOW() - INTERVAL '5 minutes'
AND portal IS NOT NULL AND portal NOT IN ('Cartera', 'Referido', 'Microsite', 'Ficha Pública')  -- excluye cartera, referidos, microsite y ficha pública
AND (
  portal = 'Marketing'
  OR escalacion_origen_id IS NOT NULL            -- hoy solo lo setea el traspaso de marketing
)
AND NOT EXISTS (
  SELECT 1 FROM crm_activities a
  WHERE a.lead_id = crm_leads.id
    AND a.created_at > crm_leads.transferred_at
)
ORDER BY transferred_at DESC  -- leads más recientes primero (INTENCIONAL — prioridad a leads nuevos)
```

**Leads de registro propio (el asesor lo crea él mismo, `createLeadEtapa1`):** no necesitan exclusión explícita — esa función nunca setea `escalacion_activa`/`escalacion_origen_id` (quedan en su default), así que mientras nadie los transfiera no son elegibles. Si después un manager reasigna ese lead a otro asesor de su equipo, **ya no activa escalación** (cambio ago 2026 — antes sí la activaba).

**Cambio ago 2026 — traspasos manuales entre roles internos dejaron de activar el cron:** antes, cuando un manager transfería un lead a un asesor de su propio equipo (tanto `transferSubmit` como `asignarAdvisor` en `manager/crm.controller.js`), se activaba `escalacion_activa` explícitamente con su propio bloque de SQL (fuera de `transferLead()`). Se quitó ese bloque en ambos endpoints — ahora solo mueven el lead y (en `asignarAdvisor`) resetean `transferred_at`/`opened_at` como bookkeeping general, sin tocar campos de escalación. `assertTransferAllowed()` tiene un bug preexistente no relacionado (no corregido, fuera de alcance de este cambio): para cualquier manager que tenga su propio `manager_id` seteado — hoy Leonardo Furlong (id 50, manager Residencial), Cesar Mercado (id 33) y Alejandro Artola (id 104, área Ventas, no es manager Residencial pese a compartir `manager_id=35` con los otros dos) —, `transferSubmit` compara el `manager_id` del asesor destino contra el `manager_id` del MANAGER remitente (a quién le reporta él) en vez de contra su propio id — falla con "Solo puedes transferir a advisors de tu mismo manager." En la práctica esos managers usan `asignarAdvisor` (endpoint distinto, sin ese bug) para asignar a su equipo.

### Horario de funcionamiento
- **Lunes–Viernes:** 9:00 AM – 8:00 PM CDMX
- **Sábado–Domingo:** 9:00 AM – 2:00 PM CDMX
- Toggle OFF → no funciona independientemente del horario

### Constantes
```javascript
const TIMEOUT_MINUTOS = 5;
const FALLBACK_1_ID = 35; // Daniel Rojas — escalación final antes del FIN
const FALLBACK_2_ID = 7;  // Jimena Denisse Hansen — FIN ABSOLUTO
const EXCLUIDOS_NO_RESIDENCIAL = [16, 62]; // Alexandra Bohorquez, Karla Renteria
const MODO_PRUEBA = process.env.ESCALACION_MODO_PRUEBA === 'true'; // simula sin transferencias reales
// FALLBACK_1_ID y FALLBACK_2_ID se exportan desde escalacionLista.service.js
```

### Arquitectura de listas (BD-driven)
Los órdenes de escalación se leen de la BD en tiempo real, NO están hardcodeados en el código:

| Tabla | Propósito | Servicio |
|---|---|---|
| `escalacion_lista_global` | Lista circular única para leads no-Residencial | `escalacionLista.service.js` |
| `escalacion_lista_residencial` | Listas por manager para leads Residencial | `escalacionListaResidencial.service.js` |

**Managers Residencial:** `MANAGERS_RESIDENCIAL = [50]` — Furlong. Único por ahora
(Cesar Mercado, id 33, dejó de serlo en ago 2026 — nunca llegó a tener asesores
cargados en `escalacion_lista_residencial`, así que no hubo datos que migrar).
A futuro puede haber más de un manager Residencial.
- Cuando un manager Residencial no responde → CASO 3: escala a Daniel Rojas
- Cuando la lista de un manager Residencial se agota → retorna el `manager_id` → dispara CASO 3

**Lista global:** cuando se completa el ciclo entero → retorna `FALLBACK_1_ID` (Daniel Rojas)

### 4 CASOs en escalarLead()
```
CASO 1 (defensivo): advisor_id === FALLBACK_2_ID (Denisse Hansen)
        → escalacion_activa = false, no transfiere (ya es el FIN)

CASO 2: advisor_id === FALLBACK_1_ID (Daniel Rojas)
        → transfiere a Denisse Hansen, escalacion_activa = false
        → notifica a Denisse (lead_transferido) + notifica a Daniel (lead_expirado)

CASO 3: producto === 'Residencial' AND esManagerResidencial(currentUser)
        → transfiere a Daniel Rojas, escalacion_activa = true
        → notifica a Daniel (lead_transferido) + notifica al manager (lead_expirado)

CASO 4: flujo normal (todos los demás)
        → obtiene siguiente en lista global o lista Residencial según producto
        → si nextUserId === null → no escala (lista vacía o sin activos)
        → transfiere, notifica receptor (lead_transferido) + anterior (lead_expirado)
```

### Mecanismo de throttle (control de backlog)
Controlado por 3 claves en tabla `configuracion`:
```
escalacion_throttle_activo  'true'/'false' — activa o desactiva el throttle
escalacion_throttle_desde   timestamp ISO  — marca desde cuándo aplica
escalacion_throttle_limite  número         — máximo de leads de backlog por hora (default 20)
```

- **Frescos** (`created_at >= throttle_desde`): siempre se escalan, sin límite
- **Backlog** (`created_at < throttle_desde`): respetan el cupo `limite - historial_última_hora`
- Historial consultado en `escalacion_historial WHERE created_at > NOW() - 1h`

### Tablas usadas por escalación
```sql
crm_lead_transfers          -- auditoría de cada transferencia (transfer_type='escalacion')
escalacion_historial        -- registro para throttle: lead_id, advisor_id_anterior, advisor_id_nuevo, created_at
escalacion_lista_global     -- lista circular global (lectura)
escalacion_lista_residencial -- listas por manager Residencial (lectura)
```

### Cómo se detiene
- Asesor registra cualquier actividad en `crm_activities` → `escalacion_activa = false`
- Lead llega a Denisse Hansen → `escalacion_activa = false` → permanece en su bandeja
- `escalacion_gerencia_inicio` es NULL → `escalacion_activa = false` (protección anti-loop)

### Concurrencia
Flag booleano `ejecutando` en memoria evita que dos ticks corran en paralelo.
Si un tick tarda más de 1 minuto, el siguiente es omitido con log en consola.

### Toggle admin
- `GET /admin/configuracion/escalacion` → estado actual
- `POST /admin/configuracion/escalacion/toggle` → cambiar
- Toggle en sidebar del admin (teal=activo, gris=inactivo)

---

## FICHAS TÉCNICAS PDF (OUTLET)

**Generación:** PDFShift API (NO Puppeteer — causa OOM en Render 512MB)

**Rutas:**
```
GET  /admin/fichas                       panelIndex
GET  /admin/fichas/outlet/:id/datos      editarFicha (JSON)
POST /admin/fichas/outlet/:id/guardar    guardarCamposFicha
GET  /admin/fichas/outlet/:id/preview    previewOutlet
GET  /admin/fichas/outlet/:id/pdf        generarPdfOutlet
GET  /admin/fichas/outlet/:id/imagenes   listarImagenesOutlet
POST /admin/fichas/outlet/:id/orden      guardarOrdenOutlet
```

**Caché de imágenes:** Al guardar orden → sube a Cloudinary folder `fichas/outlet`
columna `imagenes_cache JSONB` en `inventario_outlet`

**Template:** `views/admin/fichas/template-outlet.ejs`
- Tipografía: Montserrat (Google Fonts)
- Paleta: blanco + #008a8a (teal)
- 3 páginas: Portada, Características, Precio Total
- Assets en `public/img/fichas/`

**PDFShift config:**
```javascript
{ use_print: true, landscape: true, format: 'A4', margin: '0' }
```

---

## FICHA PÚBLICA — CAPTURA DE LEADS

**Endpoint:** `POST /p/:id/contacto`

**Payload:**
```javascript
{ 
  nombre,      // string, nombre del contactante
  telefono,    // string
  email,       // string
  mensaje,     // string (observaciones opcionales)
  intent       // 'call' | 'whatsapp' | 'contact' — tipo de interacción
}
```

**Lógica:**
- Crea o actualiza lead en `crm_leads` asignado a:
  1. Asesor del parámetro `?a=` (si está presente)
  2. Fallback: `configuracion.lead_publico_advisor_fallback_id` (default 80)
- Si existe lead 'open' con el mismo teléfono y advisor_id, lo actualiza sin crear notificación
- Si es nuevo: notificación `lead_publico` al advisor + sus managers

---

## MICRO-SITIO PÚBLICO

**Archivo:** `src/controllers/public/microsite.controller.js`

**Por asesor:** `GET /asesor/:username` + `POST /asesor/:username/contacto`
Catálogo de `inventario_outlet` (global, no filtrado por asesor — cualquier
usuario activo con username tiene micrositio, no solo `role='advisor'`).
Hero muestra nombre/foto/rol/área del usuario; botones Llamar y WhatsApp
usan `users.telefono`. Leads se asignan directo al `advisor_id` resuelto
por `:username`, `portal: 'Microsite'`.

**General (jul 2026):** `GET /altaltium` + `POST /altaltium/contacto`
Mismo controlador y vista (`views/public/microsite.ejs`), sin duplicar
código — un sentinel `ALTALTIUM_GENERAL` en `microsite.controller.js`
sustituye la consulta a `users` por un objeto "asesor" sintético (marca
Altaltium, sin subtítulo de rol/área, teléfono fijo `5610049675` para
Llamar y WhatsApp). Los leads no se asignan a ningún username: usan
`contactoSvc.resolverAdvisorId(null)` — el mismo fallback de marketing que
ya usa la ficha pública (`configuracion.lead_publico_advisor_fallback_id`,
hoy id 80 = Aldo Granados). Si ese fallback cambia algún día, también
cambia quién recibe los leads de `/altaltium` (acoplamiento intencional,
confirmado jul 2026). `portal: 'Microsite'` → igual que cualquier otro
micrositio, estos leads quedan fuera del cron de escalación automática.

---

## REPORTES CRM (CSV)

**Ruta:** `GET /admin/reportes/leads.csv`

**Columnas del CSV (historial completo del lead):**
1. Identificación: ID, nombre, contacto, portal, propiedad, ID de publicación
   (`numero_serie` — mismo campo que "Id. de Publicación" en el form de alta de lead)
2. Registro: fecha, asesor que registró, gerente
3. Traspaso: si fue traspasado, quién, a quién, cuándo, nota
4. Seguimiento: primera actividad, total, # llamadas/citas/videos
5. Perfilamiento: si fue perfilado, cuándo
6. Última actividad: fecha y asesor
7. Cierre: estatus, razón, venta, montos, fechas
8. Días activo

**Fix de fechas:** parámetros `datetime-local` llegan como `"2026-04-11T11:23"`
se parsean con offset +6h para CDMX. `estatus` puede llegar como `'all'` o `'todos'`.

---

## RESPONSIVE MÓVIL (DRAWER)

**Archivo:** `public/js/drawer.js`

Todos los sidebars tienen drawer deslizable en móvil:
- `id="crm-sidebar"` → breakpoint 768px (md)
- `id="admin-sidebar"` → breakpoint 1024px (lg)
- Overlay oscuro cierra el drawer al tocar
- Hamburger arriba izquierda en móvil
- Escape cierra el drawer

**Sidebars actualizados:**
- `views/advisor/crm/partials/sidebar.ejs`
- `views/manager/crm/partials/sidebar.ejs`
- `views/admin/partials/sidebar.ejs`
- `views/directivo/partials/sidebar.ejs`
- `views/administracion/partials/sidebar.ejs`
- `views/manager/partials/sidebar.ejs`
- `views/advisor/crm/calendar.ejs` (sidebar inline)

**Fix overflow horizontal móvil:**
```css
html, body { overflow-x: hidden; max-width: 100vw; }
.notif-toast { max-width: min(340px, calc(100vw - 40px)); }
.notif-panel { max-width: calc(100vw - 16px); }
```

---

## ORDEN CRÍTICO EN app.js

```javascript
app.use(managerCrmRoutes)        // PRIMERO — rutas específicas
app.use('/manager', managerRoutes) // DESPUÉS — rutas generales
```
Si se invierte: `/manager/crm/leads` es interceptado por `/manager/crm/:id`

---

## CRM MANAGER

**Archivo:** `src/controllers/manager/crm.controller.js`
**Rutas:** `src/routes/manager.crm.routes.js`

Mismas funciones que advisor CRM:
registrar leads, lista, detalle, actividades, perfil, editar,
transferir, cerrar con y sin venta.

### Flujo de traspaso entre gerencias
1. Advisor solicita traspaso → lead va al manager origen
2. Manager origen elige manager destino → notifica con `lead_traspaso`
3. Manager destino abre lead → asigna a su advisor
4. Advisor destino recibe `lead_transferido`

**Lead traspasado:** queda en bandeja como "Traspasado" (solo lectura)
mostrando nombre del manager destino + fecha CDMX

---

## CALCULADORA DE COMISIONES (PERFIL)

**Vista:** `views/profile/index.ejs` — Tab "Calculadora"

Productos: Outlet, Micro, Legal, Residencial, Renova

| Producto | Modalidades |
|---|---|
| Outlet | 1 pago, 2 pagos (75/25), 3 pagos sin Cesión |
| Soluciones Legales | Asesor (5%), Gerente (2%) |
| Prestación servicios | "(10 días post-firma)" en selector |

---

## CRONS ACTIVOS

**Archivo:** `src/services/recordatorios.cron.js` — inicia todos

| Cron | Schedule | Función |
|---|---|---|
| Recordatorios | cada 15 min | Citas/llamadas próximas 30 min → notifica advisor |
| Leads sin actividad | 9 AM CDMX diario | Sin actividad 1 día → notifica manager |
| Escalación | cada 1 min | Revisa leads sin contacto → escala |

---

## NOTAS DE DESARROLLO

### Mi perfil
- Nuevo en programación
- Prefiero: explicación después de cada cambio
- Plan Mode: explorar → aprobar → ejecutar
- No hacer deploy hasta aprobar el plan
- Ver mockups visuales antes de implementar

### Reglas importantes
- **TODAS las páginas del proyecto deben tener navbar y footer.**
  - Páginas que usan el layout `main.ejs` (express-ejs-layouts) → lo heredan automáticamente.
  - Páginas standalone (con su propio `<!DOCTYPE html>`) → deben incluir manualmente:
    ```ejs
    <%- include('ruta/relativa/a/partials/navbar') %>
    <%- include('ruta/relativa/a/partials/footer') %>
    ```
    Y antes de `</body>`: `main.js`, `drawer.js`, `flyonui.js`, y `notificaciones.js` (si el usuario está logueado).
- `manager_id` siempre consultar directo en BD, NO desde `req.session.user`
- `req.session.user` contiene: id, nombre, apellidos, email, username,
  telefono, role, gerente, is_active, manager_id, area, avatar_url
- BD local (.env) es más antigua que Render (DATABASE_URL)
  → siempre verificar estructura en producción

### Bugs históricos resueltos
- `pdfShowAdvisor = !esPdfBool` → advisor aparece en PDF
- `res.flush()` en `_pushSSE` para Express 5
- `manager_id` desde sesión desactualizado → consultar BD
- Orden rutas POST: `leer-todas` debe ir ANTES de `:id/leer`
- `managerCrmRoutes` debe montarse ANTES de `managerRoutes`
- `transferirLead` en crm.service.js faltaba → TypeError en producción
- Puppeteer eliminado (OOM 512MB) → reemplazado por PDFShift

---

## PENDIENTES EN ORDEN DE PRIORIDAD

1. **Fichas técnicas:** template residencial, páginas 4-8 outlet
2. **Mapa en PDF:** página 7 usa placeholder (URL google_maps sin coordenadas válidas)
3. **Resultados de actividades en CSV:** tabla `crm_activity_outcomes`
4. **Entorno local:** configurar nodemon para no depender de deploy
5. **Mejoras CRM:** advisor y manager
6. **Mejoras dashboards y reportes gerenciales**
7. **Vistas duplicadas advisor/manager CRM:** refactorizar a partial compartido
8. **Errores silenciosos en `show.ejs` (advisor):** varios `?error=` que redirigen a esta página (`finalizar_regla_incompleta`, `perfilamiento_requerido`, `stage2_not_complete`) no muestran ningún mensaje al usuario — solo `stage1_not_confirmed` está manejado. El usuario queda redirigido sin saber por qué falló la acción.
9. **Bug preexistente en `assertTransferAllowed()`:** para managers de Residencial con `manager_id` propio seteado (33, 50, 104), `transferSubmit` del manager compara mal el `manager_id` del destino — ver nota en "SISTEMA DE ESCALACIÓN AUTOMÁTICA DE LEADS". No corregido (fuera de alcance del cambio de ago 2026 que lo encontró); en la práctica se usa `asignarAdvisor` como alternativa que no tiene el bug.

---

## CAMBIOS RECIENTES (Abril 2026)

### Escalación automática
- managers insertados como orden 1 en sus propias gerencias (IDs: 8, 32, 33, 34, 50)
- Victor Garcia (32): agregados José Manuel (85), Patricia (84), Herlinda (77) en posiciones 9, 10, 11
- escalarLead() refactorizada con transacciones BEGIN/COMMIT en los 3 casos
- transferirLead() acepta parámetro opcional client para transacciones

### Seguridad
- SESSION_SECRET: eliminado fallback débil — servidor falla con error claro si no está definida
- /debug/drive-images protegido con requireRole('admin')
- 6 rutas protegidas con requireAdvisorLike: /estimaciones, /productos,
  /honorarios, /inventario/hoja, /media/drive/:id
- /advisor/crm/calendar protegido con requireRole('advisor')

### Base de datos
- Índice idx_outlet_estatus creado en inventario_outlet(estatus)
- Cron de purga semanal: lunes 3am CDMX — borra sugerencia_lead leídas > 7 días

### Responsive móvil — bugs corregidos
- Bug #1: admin-hamburger cambiado de crm-hamburger a crm-hamburger-lg
  (era invisible en tablets 768–1023px)
- Bug #2: admin-sidebar cambiado a position fixed + drawer-sidebar-lg
- Bug #3: drawer.js agregado en 17 archivos (directivo x12, administracion x4, manager shell_end)
- Bug #3: sidebars directivo, administracion, manager cambiados de sticky a fixed
- CSS global: #admin-sidebar ~ main { margin-left: 256px } en @media (min-width: 1024px)
- manager/crm/leads/index.ejs: agregado min-w-0 para evitar desbordamiento en móvil

### Visibilidad columna Lista
- inventario-outlet/index.ejs: columna lista visible solo para
  admin, manager, directivo, administracion, marketing
- inventario-hoja.ejs: columna lista + filtro dinámico por lista
  visible solo para admin, manager, directivo, administracion, marketing

### Documentos
- Marketing agregado a roles_acceso en 62 documentos de la biblioteca

### CSS nuevas clases
- .crm-hamburger-lg: mismo estilo que crm-hamburger, oculto en ≥1024px
- .crm-overlay-lg: overlay para breakpoint lg

---

## CAMBIOS RECIENTES (Julio 2026)

### Google Calendar — acceso, sincronización y backfill
- Acceso por rol (Fase 1): solo advisor, manager, directivo, marketing pueden conectar/usar Google Calendar. admin/administracion/rrhh sin pestaña todavía; externo ve pestaña con bloqueo permanente. Helpers en `googleCalendar.service.js`: `puedeUsarGoogleCalendar(role)`, `debeVerPestanaIntegraciones(role)`.
- Sincronización automática CRM → Google Calendar para toda actividad con `scheduled_at` (llamada, cita, whatsapp, mensaje — correo queda fuera). Dos puntos de creación de actividad enganchados: `createActivity()` y `createFollowupFromActivity()` (este último se le olvidó al primer intento — bug real, encontrado buscando los 2 sitios de `INSERT INTO crm_activities`).
- Backfill de actividades históricas: cron nuevo (`calendarBackfill.cron.js`, apagado por default), panel en `/admin/configuracion/calendar-backfill`. Dedup vía `calendar_events.activity_id`.
- Sincronización en reversa (Google Calendar → `calendario.ejs`): endpoint `GET /advisor/crm/calendar/eventos-google`, filtra los eventos que el CRM ya creó.
- 3 bugs reales corregidos: desfase de 6h en fechas (`new Date()` interpretado como hora del servidor), `createFollowupFromActivity` sin enganchar el sync, fechas inválidas mandadas a la API de Google desde el endpoint de reversa (FullCalendar no siempre manda RFC3339 válido).
- Se eliminó el botón manual "Agendar en Calendar" (creaba el evento directo en Google sin pasar por `crm_activities`, por eso no aparecía en el calendario interno) junto a su modal, JS y endpoint `crearEventoDesdeLead`.

### Botón "Omitir lead" + reporte de omisiones
Ver `docs/popup-leads.md` para el detalle completo (mecanismo, notificación `lead_omitido`, imagen `JuanResignado.png`, tabla `crm_lead_omissions`, reporte `/reportes/leads-omitidos` con paginación de 20 y columnas ID lead/producto/precio/dirección).

### Cron de escalación
- Excluye también leads con `portal = 'Microsite'` o `'Ficha Pública'` (antes solo `'Cartera'`).
- Leads de registro propio (`createLeadEtapa1`) no necesitaron cambio de código — ya quedan fuera del cron por default (`escalacion_activa` nunca se activa ahí) mientras nadie los transfiera; confirmado que ese es el comportamiento deseado (si un manager los reasigna después, sí aplican las reglas normales).

### Panel de administración
- Se eliminó la página vieja "Panel de administración" (`views/admin/users/dashboard.ejs`, gráficas de inventario/operaciones vacías). `GET /admin` ahora redirige directo a `/admin/users` (Dashboard de usuarios).
- Sidebar admin: Backfill de calendario, Anuncios, Popups de leads, Expedientes y Leads Parqueados visibles solo para el usuario id=2 (José Eduardo Mejía García) — el resto de admins ve un menú más corto.
- Dashboard de usuarios (`/admin/users`) agrupado por área (Ventas, Residencial, Marketing, etc.), orden alfabético, con contador dinámico por sección sincronizado con los filtros existentes (tab activos/inactivos, A-Z, búsqueda).

### Responsive móvil (segunda pasada)
- Panel de backfill de calendario, calendario CRM (toolbar de FullCalendar, modales, banners), tarjeta de integraciones del perfil, y las 3 vistas del reporte "Leads omitidos" (tablas con scroll horizontal + texto sin wrap dado que crecieron a 7 columnas).

### Regla "Finalizar lead (sin venta)": mínimo 2 contactos
El asesor debe haber registrado al menos 2 contactos (cualquier tipo de actividad — llamada, cita, mensaje) con el lead. No importa la fecha ni el horario en que se registraron. Lógica centralizada en `crmService.canFinalizeLead(leadId, advisorId)` (`src/services/advisor/crm.service.js`), usada por `advisor/crm.controller.js`, `manager/crm.controller.js` (evaluada sobre `lead.advisor_id`, no sobre el manager que da click) y `directivo/asesores.controller.js`. `marketing/crm.controller.js` reexporta el `leadClose` de advisor directo, así que queda cubierto sin cambio adicional.

- **Regla anterior (hasta jul 2026):** exigía 3 días calendario distintos + 3 bloques horarios distintos (mañana/tarde/noche CDMX), contados por separado sobre llamadas. Se simplificó a un conteo simple de contactos.
- **Excepción:** el usuario Daniel Rojas (id 35) está siempre exento — puede finalizar cualquier lead propio sin cumplir la regla, sin importar qué tan reciente sea.
- **Switch admin:** `configuracion.finalizar_lead_regla_activa` — si está en `'false'`, la regla no aplica a nadie (default: activa si la clave no existe). Toggle en `/admin/configuracion/popups` (tarjeta arriba de la tabla), junto con la gestión de popups de leads — esa página completa (no solo el switch) ahora está restringida por ruta a un solo usuario, no solo oculta en sidebar: `requireJoseEduardo` en `admin.routes.js` (id=2, José Eduardo Mejía García) devuelve 403 a cualquier otro admin que entre por URL directa.
- **Validación también en servidor:** antes la regla solo se aplicaba ocultando el botón en la UI — `POST /advisor|manager/.../close` no revalidaba nada, así que un POST directo podía cerrar cualquier lead sin cumplirla. Ahora los 3 endpoints (`advisor`, `manager`, `marketing` vía advisor) llaman `canFinalizeLead` antes de cerrar; si falla, redirige con `?error=finalizar_regla_incompleta` — aunque ese query param todavía no se muestra en pantalla en `show.ejs` (pendiente, ver sección de Pendientes).
- El botón en el panel "Mi CRM" de manager (`views/manager/crm/leads/show.ejs`) estaba con `canFinalizeLead` fijo en `false` desde antes (nunca se calculaba) — quedó habilitado con el valor real. Relevante porque usuarios con rol `directivo` pueden tener acceso de manager vía `roles_extra` (ej. Daniel Rojas) y usar ese panel para sus propios leads.
- `src/routes/manager.routes.js` (vista de supervisión de un lead de un asesor) tenía una TERCERA copia de esta regla, inline y desincronizada (solo contaba días distintos, sin el bloque horario, sin la excepción de Daniel Rojas ni el switch admin) — se reemplazó por una llamada directa a `crmService.canFinalizeLead`.

### Registrar contacto: horario libre (eliminado el sistema de "bloques horarios")
Hasta jul 2026, al registrar el 2do contacto en adelante de un lead (o al agendar un seguimiento desde "Registrar resultado"), si la fecha coincidía con el día de la última actividad, el sistema exigía que la hora cayera en un bloque horario posterior (6 bloques de 4h cubriendo el día completo: 12-4am, 4-8am, 8am-12pm, 12-4pm, 4-8pm, 8pm-12am). Esto existía tanto en servidor (`?error=bloque_invalido`) como en cliente (selector de "Bloque horario" en vez de un time picker libre, en `contact.ejs`). Se eliminó por completo — el horario ahora es libre, sin restricción alguna respecto a la última actividad, tanto para el 1er contacto (que ya tenía sus propias reglas de ventana de 5 min) en adelante. Cambios en:
- `src/controllers/advisor/crm.controller.js` y `src/controllers/manager/crm.controller.js` — quitada la validación de bloque en `contactSubmit` y en `activityOutcomeUpsert` (seguimiento).
- `views/advisor/crm/leads/contact.ejs` y `views/manager/crm/leads/contact.ejs` — quitado el selector de bloque + su validación de submit + el banner de error `bloque_invalido`.
- `views/advisor/crm/leads/show.ejs` y `views/manager/crm/leads/show.ejs` — `_fuMinHourSameDay()` (usada por el modal "Registrar resultado" de escritorio y el sheet móvil) ahora siempre regresa `0`, sin importar la actividad de referencia.
- La restricción de **fecha** (no registrar en días pasados) NO se tocó — sigue vigente, solo se quitó la restricción de **hora**.

### Bandeja de leads: cierres y firmas distintos + KPIs rotos
`crm_leads` tiene `sale_paid` y `sale_signed_only` como flags independientes, pero el estado calculado `crm_state` (usado en `crmService.listLeadsByAdvisor` y `getPipelineByStatus`) solo distinguía `won` (pagado) vs `lost` (cualquier otro cierre) — un lead cerrado con "Solo firmó" se etiquetaba como perdido. Se agregó un estado `signed` distinto en ambos CASE de SQL.
- **Bug de arquitectura en la bandeja de asesor:** `leadsIndex` siempre pedía el dataset con `estado:'all'`, y el propio servicio ya excluía won/lost de ese dataset antes de que el controlador pudiera filtrar por el estado real pedido — pedir el chip "Ganados" o "Perdidos" siempre devolvía vacío. Nueva opción `includeClosed` en `listLeadsByAdvisor` para que el controlador pida el dataset completo sin ese recorte previo.
- `stats.cierres` (ganados) y `stats.firmas` (solo firmó) ahora se calculan y se muestran en KPIs + chips (móvil y escritorio) en `views/advisor/crm/leads/index.ejs` y `views/manager/crm/leads/index.ejs` (comparten `crm-mobile.css`/`crm-leads-bandeja.css`).
- De paso, corregidos: `stats.total` en manager/directivo (usaba `kpis.total`, que nunca existió — siempre daba 0) y `stats.traspasos` en advisor (hardcodeado en 0 en la vista).
- Etiqueta de `won` cambiada de "Finalizado" a "Cierre" (antes ganados y perdidos decían literalmente lo mismo, solo distinguibles por color).
- **Pendiente (no tocado):** `views/admin/leads/index.ejs`, `views/directivo/leads/index.ejs`, `views/manager/leads/index.ejs`, `views/directivo/crm/index.ejs` y `views/advisor/crm/dashboard.ejs` también leen `crm_state` con su propia lógica `won`/`lost` — con `signed` ahora en juego, un lead solo-firmado les puede llegar con un valor de estado que esas vistas no esperan.

### Ficha pública: asesor correcto según el micrositio de origen
Las tarjetas del catálogo en `microsite.ejs` abrían `/p/:id` sin `?a=<advisorId>` — por eso cualquier lead que entraba desde el micrositio de un asesor específico caía siempre en el fallback de marketing (hoy Aldo Granados, id 80) en vez de asignarse al dueño real del micrositio. Corregido: la tarjeta agrega `?a=<asesor.id>` cuando `asesor.id` existe (no aplica al micrositio general `/altaltium`, que intencionalmente sigue sin asesor específico).

También en `propiedad.controller.js`: `GET /p/:id` solo resolvía teléfono/asesor para el botón de WhatsApp cuando `?a=` era válido — si faltaba o el asesor no existía, el JS de la vista caía en un placeholder roto hardcodeado (`521XXXXXXXXXX`, literal, nunca reemplazado) que WhatsApp rechazaba. Ahora usa `contactoSvc.resolverAdvisorId()` (mismo fallback que ya usa el POST de contacto) para siempre resolver un asesor real; el fallback del JS en caso extremo ahora es el número general de Altaltium (`56 1004 9675`) en vez del placeholder.

### Citas & Cierres — tipo de cita en la tarjeta + notificaciones
- **Tarjeta del calendario:** los controladores (`administracion/citasCierres.controller.js` y `manager/citasCierres.controller.js`) ahora traen `subtype`, `location_type` y `location_text`; la tarjeta muestra una fila "Tipo de cita" con la modalidad seleccionada (Videollamada / Presencial / Visita al inmueble; presencial agrega la ubicación: "Presencial · Oficinas Altaltium" o el lugar capturado). Helper `citaModalidad(c)` en ambas vistas.
- **Notificaciones (campana + toast):** 3 tipos nuevos — `cita_agendada`, `cierre_firma`, `cierre_pago` — vía `notifService.notificarCitasCierres({ tipo, leadId, advisorId })`. Se disparan desde el SERVICIO (`crm.service.js`), no desde los controladores, para cubrir advisor/manager/directivo/marketing de una vez: `createActivity` y `createFollowupFromActivity` (cuando `type='cita'` con `scheduled_at`), `closeSalePaid` (pago) y `closeSaleSigned` (firma, solo si el UPDATE afectó fila). Destinatarios: admin/directivo/administracion (url `/administracion/citas-cierres`) + el gerente del asesor (url `/manager/citas-cierres`), excluyendo al propio actor. Solo toast + campana (`suppressPopup: true`), nunca modal bloqueante — caen en el `else { mostrarToast }` genérico, que ya es responsive.
- **Filtro por tipo en la campana:** el rol `administracion` filtra la campana/badge por lista de tipos (`getNotificaciones` + `contarNoLeidas`) — se agregaron los 3 tipos nuevos a esa lista para que sí aparezcan. admin/directivo (ven todo) y manager (ven equipo) no filtran por tipo.
- Nota: directivo/admin ven todas las notificaciones de la empresa, así que la copia dirigida al gerente (url `/manager/...`) puede aparecerles como una 2ª entrada del mismo evento (distinta url = no se deduplica). Aceptado: ambos enlaces son destinos válidos.

### Citas & Cierres — calendario: bugs de zona horaria y layout
- **GERENTE/PRODUCTO en la tarjeta:** el join usaba `a.manager_id` (columna que ningún formulario llena, siempre NULL) en vez de `u.manager_id` (el gerente real del asesor); PRODUCTO usaba `a.product` (tampoco lo llena ningún formulario) — ahora `COALESCE(l.producto, a.product)`, igual que el patrón ya usado en `crm.service.js`.
- **Firmas/pagos mostraban un día adelantado:** el `start` de esos eventos (allDay) se calculaba con `closed_at.toString().slice(0, 10)`, que toma el día calendario en UTC — un cierre registrado entre 18:00 y 23:59 CDMX aparecía al día siguiente. Fix: `cdmxDateStr()` usa `toLocaleDateString('en-CA', {timeZone: TZ})`.
- **Última columna (sábado) se cortaba** al colapsar/expandir el sidebar — FullCalendar solo recalcula su ancho en el evento `resize` de la ventana, no cuando el contenedor cambia de tamaño por una transición CSS. Fix: `ResizeObserver` sobre `.cc-cal-card` que llama `calendar.updateSize()`.
- **Hora de la cita en el calendario no coincidía con la del tooltip** (ej. calendario mostraba "20:30", el tooltip "02:30 p.m." para el mismo evento — desfase de exactamente 6h, el offset UTC↔CDMX). Causa real: FullCalendar **core** (el bundle `fullcalendar@6.1.15/index.global.min.js` solo, sin plugin) no soporta de verdad zonas horarias con nombre IANA — acepta `timeZone: 'America/Mexico_City'` sin lanzar error, pero la hora mostrada en cada evento se queda en UTC crudo; el tooltip sí mostraba bien porque se calcula aparte con `Intl`/`toLocaleString`, que sí soporta IANA nativo. Confirmado reproduciendo el bug en aislado y verificando el fix contra la plantilla real renderizada con datos de prueba (headless Chrome + CDP). Fix: agregar `moment.js` + `moment-timezone.js` (con datos) + el plugin `@fullcalendar/moment-timezone` vía CDN, y registrarlo con `plugins: [FullCalendar.MomentTimezone.default]` en el `new FullCalendar.Calendar(...)` de ambas vistas.

---

## CAMBIOS RECIENTES (Agosto 2026)

### Subastas 2026 (nueva categoría de inventario)
- Nueva tabla `inventario_subastas` (remates bancarios) — solo carga masiva vía
  Excel/CSV desde `/admin/inventario-subastas/importar`
  (`inventarioSubastas.controller.js`), sin formulario manual de alta a
  diferencia de Outlet/Residencial. Migración: `scripts/migration_inventario_subastas.js`.
- Acceso público de lectura igual que `/inventario/hoja`: `ensureAuth +
  requireAdvisorLike` en `/inventario/subastas` (`main.routes.js`).
- Nombrado genérico a propósito (sin el año en tabla/rutas) — "2026" solo
  aparece como texto en el menú y el título de la página, para no tener que
  recrear tabla/rutas cada año.
- Menú "Inventario" del navbar: "Inventario Outlet" ahora abre un submenú
  flyout (desktop, se abre al pasar el cursor) con "Inventario Outlet" y
  "Subastas 2026" — primer submenú anidado del proyecto, no había precedente
  de flyout ni de acordeón en `navbar.ejs` ni en ningún sidebar. En móvil,
  sin acordeón nuevo: se agregó como link indentado adyacente a "Inventario
  Outlet" (sin JS extra).
- Fecha de la subasta guardada como 4 columnas separadas `dia`/`mes`/`anio` +
  `hora` (no un solo `TIMESTAMPTZ`) — la primera versión sí usaba un solo
  campo de fecha+hora, se revirtió a pedido explícito del usuario. `mes` en
  particular es **texto** ("agosto", no `8`) tras un segundo pedido — ver
  detalle completo en `### inventario_subastas` arriba (normalización,
  `ORDER BY` con `CASE`, bug de `hora` con celdas de Excel formateadas como
  hora, y columnas de texto ampliadas a `TEXT` porque el Excel real del
  usuario traía valores más largos de lo que permitían los `VARCHAR`
  originales — causaba que solo se importara una fracción del archivo).
- **Interfaz igualada a Inventario Outlet (segunda iteración, a pedido
  explícito):** `views/pages/inventario-subastas.ejs` pasó de ser una versión
  simplificada a un clon del formato de `inventario-hoja.ejs` — mismo header
  con badges (actualizado/total/confidencial), mismo toolbar (búsqueda +
  Estado/Municipio/Colonia en cascada + botones Filtros/Limpiar/CSV), misma
  tabla con columna `#` congelada y **filtros por columna** (dropdown por
  header: ordenar A-Z/Z-A + checklist de valores para columnas de texto,
  rango min/máx para `oferta_inicial`/`ingreso_subasta`), mismo drawer de
  filtros avanzados (adaptado: Tipo de inmueble / Tipo de juicio / Almoneda +
  rangos de oferta e ingreso, en vez de los campos de Outlet como
  recámaras/baños/superficie que no aplican aquí), y exportar a CSV. No se
  clonó el concepto "en paquete" de Outlet (agrupar varias propiedades bajo
  un precio conjunto) por no existir en Subastas. No hay funcionalidad de
  arrastrar/reordenar columnas en `inventario-hoja.ejs` tampoco (se había
  asumido que sí existía al planear la v1; no es real, así que no había nada
  que clonar ahí). La ruta pública en `main.routes.js` ahora también calcula
  `lastUpdated` y una URL de Google Maps por dirección (`GoogleMapsFinal`,
  mismo fallback que usa `/inventario/hoja` cuando no hay coordenadas
  propias) para alimentar esos mismos elementos visuales.
- La página admin (`views/admin/inventario-subastas/index.ejs`) usa el mismo
  shell y el mismo `admin/partials/sidebar.ejs` que `/admin/inventario-outlet`
  — confirmado con una comparación directa del HTML renderizado.
- **Homologación de municipios en el filtro Estado→Municipio→Colonia:** los
  datos de carga masiva traen el mismo municipio capturado de formas
  distintas (ej. "Tlanepantla" / "Tlanepantla De Baz" / "Distrito De
  Tlanepantla", o "Ecatepec" / "Ecatepec De Morelos") — `municipioCanonical()`
  en `inventario-subastas.ejs` (mismo patrón que ya existía para homologar
  nombres de estado con `canonical()`/`ESTADOS_MX`) los agrupa a un solo
  nombre canónico vía un mapa `MUNICIPIO_ALIASES` explícito + un respaldo
  genérico que recorta el sufijo ", <estado>" repetido al final. Solo aplica
  a la cascada de filtros — la columna "Municipio" de la tabla y el CSV
  siguen mostrando el dato crudo tal cual se importó. Cuando el mismo nombre
  de municipio existe en dos estados distintos (ej. "Benito Juárez" en CDMX
  y en Quintana Roo), la opción del filtro se etiqueta con el estado
  ("Benito Juárez (Ciudad de México)") y la opción lleva el estado real
  adjunto (no solo en la etiqueta) para que el filtro no mezcle ambos
  municipios homónimos aunque `norm()` les quite el acento a los dos por
  igual. Filas sin estado o sin municipio capturado ya no generan opciones
  fantasma "—" en los dropdowns. **No** se intenta corregir filas donde el
  `estado` mismo parece mal capturado (ej. una propiedad de Cancún guardada
  con `estado='Campeche'`, o municipios de Edomex guardados con
  `estado='Guanajuato'`) — eso es un error de captura en el Excel original,
  no una variante de nombre, y corregirlo silenciosamente ocultaría el error
  real; se dejó tal cual para que se corrija en el origen.
