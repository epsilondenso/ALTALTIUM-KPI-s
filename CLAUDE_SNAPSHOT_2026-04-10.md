# CLAUDE_SNAPSHOT — 2026-04-10
> Generado automáticamente. Refleja el estado real del código al día de hoy.
> Complementa (y en algunos puntos actualiza) el CLAUDE.md de referencia.

---

## 1. Stack y dependencias activas

```
express          ^5.1.0
ejs              ^3.1.10
express-ejs-layouts ^2.5.1
express-session  ^1.18.2
pg               ^8.16.3
bcrypt           ^6.0.0
multer           ^2.0.2
method-override  ^3.0.0
googleapis       ^171.4.0
cloudinary       ^2.9.0
node-cron        ^4.2.1
dotenv           ^17.2.3
puppeteer        ^24.39.1
@puppeteer/browsers ^2.13.0
xlsx             ^0.18.5
```

**Notas:** `puppeteer` presente (generación de PDF). `xlsx` para importación/exportación. `cloudinary` activo como servicio de imágenes alternativo a Drive.

---

## 2. Variables de entorno activas

| Variable | Propósito |
|---|---|
| `PGHOST`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `PGPORT` | BD local (dev) |
| `DATABASE_URL` | BD producción Render (siempre usar esta con SSL) |
| `DRIVE_INVENTARIO_FOLDER_ID` | Carpeta raíz de imágenes de inventario |
| `DRIVE_CONTRATOS_FOLDER_ID` | Carpeta raíz de documentos de contratos |
| `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` | Cloudinary |
| `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`, `GOOGLE_CALENDAR_REDIRECT_URI` | OAuth2 Google Calendar |
| `GOOGLE_REGISTRO_CLIENT_ID`, `GOOGLE_REGISTRO_CLIENT_SECRET`, `GOOGLE_REGISTRO_REDIRECT_URI` | OAuth2 Registro externo (Option B — mismo Client ID que Calendar) |

**Faltante en .env documentado:** `GOOGLE_SERVICE_ACCOUNT_KEY` (referenciado en CLAUDE.md para Google Drive) no aparece en .env actual. Drive funciona probablemente por otro mecanismo o variable no listada.

---

## 3. Rutas montadas en app.js (orden de montaje)

| Orden | Path | Router | Notas |
|---|---|---|---|
| 1 | `/auth` | auth.routes | Login/logout |
| 2 | `/api` | api.routes | Endpoints JSON catálogo |
| 3 | `/admin` | admin.routes | Panel admin |
| 4 | *(sin prefijo)* | manager.crm.routes | **CRÍTICO: antes de /manager** |
| 5 | `/manager` | manager.routes | Panel gerente |
| 6 | `/advisor` | advisor.routes | Panel asesor |
| 7 | `/profile` | profile.routes | Perfil de usuario |
| 8 | `/` | googleCalendar.routes | OAuth callback Calendar |
| 9 | `/alcaldias` | alcaldias.routes | Mapa alcaldías CDMX |
| 10 | `/administracion` | administracion.routes | **ANTES de mainRoutes** |
| 11 | `/registro` | registro.routes | Registro externo público |
| 12 | `/` | main.routes | Rutas públicas generales |
| 13 | *(sin prefijo)* | advisor.crm.routes | Duplicado — también en /advisor |
| 14 | `/directivo` | directivo.routes | Panel directivo |
| 15 | *(sin prefijo)* | documents.routes | `/documents`, `/documents/:slug` |
| 16 | `/_internal/maps` | _internal.map.routes | Mapas internos |
| 17 | `/_dev` | _dev.maps/pages/ubicaciones | Herramientas de desarrollo |
| 18 | `/advisor` | orgchart.routes | Organigrama (montado dos veces sobre /advisor) |
| 19 | *(sin prefijo)* | advisor.crm.routes | **⚠ Montado DOS veces** (líneas 125 y 258) |
| — | Error handler | middleware | 500 |
| — | 404 handler | middleware | catch-all |

**Inline endpoints en app.js (sin router propio):**
- `GET /estados`
- `GET /municipios/:estado`
- `GET /colonias/:estado/:municipio`
- `GET /info/:estado/:municipio/:colonia`

**Aliases:**
- `GET /logout` → `/auth/logout`
- `POST /logout` → `/auth/logout` (307)
- `GET /catalogo-mapa` → `/catalogo/mapa`
- `GET /catalogo-mixto` → `/catalogo/mixto`
- `GET /mapa-calor` → `/mapas`

---

## 4. Módulos implementados — Estado actual

### 4.1 Inventario Outlet (`inventario_outlet`)
**Estado: ✅ Producción**
- CRUD completo: `/admin/inventario-outlet`
- Catálogo público con filtros de fuente [Todas/Outlet/Residencial]
- Importación CSV: `/admin/inventario-outlet/importar`
- Reglas de completitud, badge Santander, badge expediente
- lat/lng extraídas de google_maps con regex

### 4.2 Inventario Residencial (`inventario_residencial`)
**Estado: ✅ Producción**
- CRUD: `/admin/inventario-residencial`
- Pestañas: Altaltium, Consignación, Preventas, Bancos, Rentas
- Importación CSV disponible

### 4.3 Catálogo público
**Estado: ✅ Producción**
- 3 vistas: lista (`/catalogo`), mapa (`/catalogo/mapa`), mixto (`/catalogo/mixto`)
- Fuentes combinadas Outlet + Residencial
- Pins: teal (outlet), naranja (residencial)
- Filtro Lista Oro para externos

### 4.4 CRM Comercial
**Estado: ✅ Producción + mejoras recientes**

**Nuevas funcionalidades (no en CLAUDE.md):**
- Estado `followup_transfer` — leads traspasados con actividad registrada
- Prioridad de `crm_state` reordenada: `won`/`lost` tienen precedencia sobre traspaso recibido
- Modal animado de confirmación en show.ejs (advisor, manager, directivo) — detecta query params `?accion=...`
- Parámetro `?accion=contacto_registrado|venta_cerrada|lead_finalizado|lead_traspasado` en redirects de controladores

**Flujo de leads actualizado (CASE WHEN):**
1. `transferred_by = advisor_id` → `transfer`
2. `status = closed` + venta → `won`
3. `status = closed` sin venta → `lost`
4. `transferred_to IS NOT NULL` + actividad/perfil → `followup_transfer`
5. `transferred_to IS NOT NULL` → `transfer`
6. Tiene actividad o perfil → `followup`
7. Default → `new`

**crmMeta() — 6 estados visuales:**
| Estado | Borde | Chip | Label |
|---|---|---|---|
| `new` | blue-500 | blue-100 | Nuevo |
| `followup` | amber-500 | amber-100 | Seguimiento |
| `followup_transfer` | amber-500 | amber-100 | Seguimiento |
| `transfer` | slate-400 | slate-100 | Traspaso |
| `won` | green-600 | green-100 | Cierre |
| `lost` | red-500 | red-100 | Finalizado |

### 4.5 Solicitud de Contrato
**Estado: ✅ Producción**
- Flujo completo en advisor, manager y directivo
- 2 pasos: formulario de datos + subida de documentos a Drive
- Panel de administración en `/administracion/solicitudes`
- Expedientes digitales en `/administracion/expedientes/:id`
- Subida de contrato PDF firmado por rol administración

### 4.6 Panel Administración (`rol: administracion`)
**Estado: ✅ Producción**
- Dashboard, listado de solicitudes, detalle, cambio de estatus
- Generación de PDF con Puppeteer
- Subida de contrato PDF firmado
- Expediente digital

### 4.7 Notificaciones SSE
**Estado: ✅ Producción**
- Tabla `notificaciones`
- Endpoint `/notificaciones/stream`
- `res.flush()` en Express 5

### 4.8 Google Calendar
**Estado: ✅ Producción**
- OAuth2 por rol (advisor, manager, directivo)
- Calendario propio + vista de disponibilidad del equipo
- FullCalendar 6.1.9 en vistas de disponibilidad

### 4.9 Sistema de Documentos (`documents`)
**Estado: ✅ Implementado (nuevo — NO en CLAUDE.md)**

**Tabla:** `documents`

**Schema:**
```sql
id SERIAL PRIMARY KEY, slug TEXT UNIQUE NOT NULL,
title TEXT, description TEXT, category TEXT, type TEXT,
drive_file_id TEXT, thumbnail_id TEXT, external_url TEXT,
youtube_id TEXT, asset_path TEXT, size_bytes BIGINT,
tags TEXT[], featured BOOLEAN, activo BOOLEAN,
roles_acceso TEXT[], updated_at TIMESTAMPTZ
```

**Rutas públicas** (sin prefijo, `ensureAuth`):
- `GET /documents` — listado filtrado por `rol = ANY(roles_acceso)`
- `GET /documents/:slug` — detalle con check 403
- `GET /documents/:slug/download` — descarga/redirect

**Rutas admin** (`/admin/documents`):
- `GET /admin/documents` — listado con filtros (q, categoria, tipo, rol) + KPIs
- `GET /admin/documents/nuevo` + `POST`
- `GET /admin/documents/:id/editar` + `POST`
- `POST /admin/documents/:id/eliminar` — soft delete (`activo = false`)

**Lógica de thumbnail:** `doc.thumbnail` (BD) → `drive.google.com/thumbnail?id=drive_file_id&sz=w400` → placeholder

**Migración:** `node scripts/migrate-documents.js` (idempotente, ON CONFLICT DO NOTHING)
**56 documentos migrados.** 8 categorías: Manuales, Contrato, Alianzas, Links Útiles, Academy Altaltium, Productos/Servicios, Formatos, Ecosistema Altaltium.

### 4.10 Registro Externo (`/registro`)
**Estado: ✅ Implementado (nuevo — NO en CLAUDE.md)**

- Página pública de registro para asesores externos e inmobiliarias
- OAuth2 Google (mismo Client ID que Calendar, distinto redirect URI — Opción B)
- Tabla `registro_externo` en BD
- `ON CONFLICT (google_id) DO UPDATE` para re-registros
- Sesión temporal `req.session.registroTemp` preserva datos del formulario durante OAuth round-trip
- Vista de gracias en `/registro/gracias`

**Servicio:** `src/services/googleRegistro.service.js` — independiente del Calendar service

### 4.11 Dashboard Directivo
**Estado: ✅ Producción**
- KPIs con filtros de período: `?preset=30d|7d|mtd|qtd|ytd|custom`
- Ranking de gerentes, embudo de conversión, gráfica Chart.js
- Consejos estratégicos dinámicos

### 4.12 Reportes Admin
**Estado: ✅ Producción + mejoras recientes**
- CSV de leads con filtros
- **Nuevo:** filtros de fecha cambiados a `type="datetime-local"` (antes `type="date"`)
- WHERE usa `fecha_hora_mx >= $n::timestamptz` con offset `-06:00` (CST fijo)
- `?fecha_desde` y `?fecha_hasta` preservados en re-render del formulario

### 4.13 Disponibilidad del equipo
**Estado: ✅ Producción (manager y directivo)**
- FullCalendar 6.1.9 con eventos de Google Calendar del equipo
- Feed JSON: `GET /directivo/equipo/disponibilidad/feed`
- `GET /manager/equipo/disponibilidad` — vista manager

### 4.14 Organigrama
**Estado: ✅ Producción**
- `GET /advisor/orgchart`
- Vista: `views/advisor/crm/orgchart.ejs`

### 4.15 Módulo de Alcaldías
**Estado: ✅ Producción**
- `/alcaldias` — listado
- `/alcaldias/:id` — detalle con mapa

### 4.16 Perfil de Usuario
**Estado: ✅ Producción**
- `/profile` — vista y edición con Cloudinary para avatar

---

## 5. Servicios y controladores

### Controladores
```
admin.controller.js                  — controlador legacy admin
admin/documents.controller.js        — CRUD documentos admin (nuevo)
admin/inventario.controller.js       — inventario legacy
admin/inventarioOutlet.controller.js — inventario outlet
admin/inventarioResidencial.controller.js
admin/leads.controller.js            — gestión leads admin
admin/reportes.controller.js         — CSV reportes
administracion/contratos.controller.js — solicitudes + expedientes
advisor/calendar.controller.js       — Google Calendar (compartido con manager/directivo)
advisor/crm.controller.js            — CRM advisor + acciones compartidas
alcaldias.controller.js
auth.controller.js
directivo/crm.controller.js
directivo/directivo.controller.js    — dashboard + leads de solo lectura
inventarioResidencial.controller.js  — controlador alternativo residencial
manager.controller.js                — legacy
manager/crm.controller.js
pages.controller.js                  — páginas públicas
profile.controller.js
registro.controller.js               — registro externo OAuth2 (nuevo)
```

### Servicios
```
activityLog.service.js               — log de actividad
advisor/crm.service.js               — servicio CRM central (compartido todos los roles)
asesorMes.service.js                 — ranking asesor del mes
cloudinary.service.js                — upload de imágenes
googleCalendar.service.js            — integración Calendar API
googleDrive.service.js               — integración Drive API
googleRegistro.service.js            — OAuth2 registro externo (nuevo)
inventory.service.js                 — servicio inventario
notificaciones.service.js            — SSE + tabla notificaciones
profile.service.js                   — perfil de usuario
recordatorios.cron.js                — cron de recordatorios con node-cron
```

### Middlewares
```
activityLogger.js    — logger de actividad HTTP
auth.js              — ensureAuth, requireRole
auth.middleware.js   — attachCurrentUser (global, inyecta res.locals.currentUser)
ownership.js         — verificación de propiedad de recursos
requireAdmin.js      — shorthand para requireRole('admin')
```

---

## 6. Vistas — estructura

```
views/
├── admin/
│   ├── documents/        form.ejs, index.ejs           (NUEVO)
│   ├── inventario/       edit, index, new
│   ├── inventario-outlet/ edit, importar, index, new
│   ├── inventario-residencial/ importar, index
│   ├── leads/            editar, index, show
│   ├── partials/         sidebar.ejs
│   ├── reportes/         index.ejs
│   ├── ubicaciones/      edit, index, new
│   └── users/            dashboard, edit, index, new
├── administracion/
│   ├── expedientes/      show.ejs
│   ├── partials/         sidebar.ejs
│   └── solicitudes/      index.ejs, show.ejs
├── advisor/crm/
│   ├── leads/            contact, edit, index, new, profile, show, transfer
│   ├── partials/         sidebar.ejs
│   ├── calendar.ejs, dashboard.ejs, orgchart.ejs
│   └── contratos/        index.ejs, show.ejs
├── directivo/
│   ├── crm/              contact, edit, index, new, profile, show, transfer
│   ├── equipo/           disponibilidad.ejs
│   ├── leads/            index.ejs, show.ejs
│   └── partials/         sidebar.ejs
├── documents/            index.ejs, show.ejs
├── layouts/              auth.ejs, main.ejs
├── manager/
│   ├── crm/leads/        contact, edit, index, new, profile, show, transfer
│   ├── crm/              index, nuevo, partials/sidebar, show, transferir
│   ├── equipo/           disponibilidad.ejs
│   ├── partials/         shell_start, shell_end, sidebar, topbar
│   └── advisors/         edit, index, new, show
├── pages/                catalogo, catalogo-mapa, catalogo-mixto, comparar,
│                         estimaciones, home, honorarios, inventario-hoja,
│                         inventario-residencial*, mapa-calor, productos,
│                         propiedad, registro, registro-gracias, reporte*,
│                         welcome, 404
├── partials/             footer.ejs, navbar.ejs
├── profile/              index.ejs
└── shared/               contract-docs.ejs, contract-form.ejs
```

---

## 7. Diferencias con CLAUDE.md — cosas nuevas no documentadas

| # | Qué | Estado |
|---|---|---|
| 1 | **Sistema de documentos** (`documents` table + rutas + admin CRUD) | ✅ Implementado |
| 2 | **Registro externo** (`/registro` + OAuth2 + tabla `registro_externo`) | ✅ Implementado |
| 3 | **Estado `followup_transfer`** en CRM (traspaso + actividad) | ✅ Implementado |
| 4 | **Modal de confirmación de acciones** en show.ejs (3 roles) | ✅ Implementado |
| 5 | **Filtros datetime-local** en reportes admin (antes type="date") | ✅ Implementado |
| 6 | **Filtros de búsqueda** en admin/documents/index (q, categoria, tipo, rol) | ✅ Implementado |
| 7 | **Cloudinary** como servicio activo (`cloudinary.service.js`) | ✅ Activo |
| 8 | **Puppeteer** para generación de PDF | ✅ Activo |
| 9 | **xlsx** para importación de inventario | ✅ Activo |
| 10 | **Expedientes digitales** (`/administracion/expedientes/:id`) | ✅ Activo |
| 11 | **Subida de contrato PDF** por administración | ✅ Activo |
| 12 | **Organigrama** (`/advisor/orgchart`) | ✅ Activo |
| 13 | **activityLogger middleware** + `activityLog.service.js` | ✅ Activo |
| 14 | **asesorMes.service.js** — ranking asesor del mes | ✅ Activo |
| 15 | **recordatorios.cron.js** — cron con node-cron | ✅ Activo |
| 16 | **calendar_events tabla** — eventos Google Calendar en BD local | ✅ Activo |

---

## 8. Advertencias y observaciones técnicas

### ⚠ advisor.crm.routes montado dos veces
En `app.js` líneas 124-125 y 257-258:
```js
app.use(advisorCrmRoutes);   // línea ~125
// ...
app.use(require('./routes/advisor.crm.routes')); // línea ~258
```
Doble montaje puede causar ejecución duplicada de handlers. Verificar si es intencional.

### ⚠ GOOGLE_SERVICE_ACCOUNT_KEY no está en .env
CLAUDE.md la documenta como variable crítica para Google Drive. El archivo `.env` actual no la incluye. Puede estar en el entorno de Render directamente.

### ⚠ Tablas LEGACY no eliminadas (por diseño)
`inventario` e `inventario_lista` — mantener hasta autorización explícita per CLAUDE.md.

### ⚠ `src/data/documents.data.js` aún existe
El array original de 56 documentos sigue en disco aunque ya no se usa en producción (reemplazado por PostgreSQL). Solo se usa en el script de migración `scripts/migrate-documents.js`.

### ℹ Offset de zona horaria CST fijo
Los filtros de reportes usan `-06:00` fijo (CST). No maneja horario de verano CDT (`-05:00`). Aceptable según decisión de diseño documentada.

### ℹ `src/controllers/inventarioResidencial.controller.js`
Existe un controlador alternativo en la raíz de controllers además del que está en `admin/`. Verificar cuál está activo.

---

## 9. Tablas de BD activas (estado confirmado)

| Tabla | Estado | Notas |
|---|---|---|
| `inventario_outlet` | ✅ Activo | Principal para catálogo outlet |
| `inventario_residencial` | ✅ Activo | |
| `inventario` | 🔒 Legacy | No eliminar |
| `inventario_lista` | 🔒 Legacy | No eliminar |
| `crm_leads` | ✅ Activo | |
| `crm_activities` | ✅ Activo | |
| `crm_activity_outcomes` | ✅ Activo | |
| `crm_lead_profiles` | ✅ Activo | |
| `crm_calendar_notes` | ✅ Activo | |
| `contract_requests` | ✅ Activo | |
| `notificaciones` | ✅ Activo | SSE |
| `users` | ✅ Activo | |
| `org_areas` | ✅ Activo | |
| `org_people` | ✅ Activo | |
| `ubicaciones` | ✅ Activo | |
| `user_favoritos` | ✅ Activo | |
| `anuncios` | ✅ Activo | |
| `documents` | ✅ Activo | **NUEVO** — sistema de documentos |
| `registro_externo` | ✅ Activo | **NUEVO** — registro de asesores externos |
| `calendar_events` | ✅ Activo | **NUEVO** — eventos Google Calendar en BD |

---

*Snapshot generado: 2026-04-10 | Rama: main*
