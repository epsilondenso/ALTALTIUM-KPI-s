# Bandeja de Leads del Asesor — Rediseño y nuevas funciones

**Fecha:** 2026-06-15
**Alcance:** `views/advisor/crm/leads/index.ejs`, `src/controllers/advisor/crm.controller.js`, `src/services/advisor/crm.service.js`, `src/services/leadFavoritos.service.js` (+ nuevo servicio de leads fijados), rutas `src/routes/advisor.crm.routes.js`

## 1. Objetivo

Rediseñar la bandeja de leads del asesor (`/advisor/leads`) con un layout **Tabla + Panel lateral** (Opción B), agregar columnas informativas, diferenciar visualmente el origen de los leads "Nuevo", agregar favoritos/fijados con feedback visual, búsqueda por ID, ordenamiento por columnas, paginación, y un interruptor de tema claro/oscuro. Todo debe ser responsivo (desktop, tablet, móvil iOS/Android).

## 2. Estados visibles

Solo se muestran leads con `_state` en: **`new`, `followup`, `won`, `lost`** (agrupados visualmente como Nuevo / Seguimiento / Cierre).

`transfer_out` y `transfer_in` (Finalizado/Traspaso) **no se muestran** en la tabla ni se cuentan en los KPIs activos. Se muestran como chips de filtro deshabilitados con ícono de candado y el conteo total entre paréntesis, indicando "disponible próximamente". Los KPIs de "Finalizados" y "Traspaso" se muestran atenuados (`opacity: .4`) con el mismo candado.

Esto aplica solo a **filtrado de visualización** — no cambia el cálculo de `_state` ni ninguna lógica de negocio existente.

## 3. Layout general — Tabla + Panel lateral

- **Desktop (≥1280px):** grid de 2 columnas — tabla (flexible) + panel lateral fijo de 280px a la derecha.
- **Tablet (768–1279px):** grid de tarjetas de 2 columnas, sin panel lateral; al tocar una tarjeta se abre el panel como modal/drawer deslizante desde la derecha.
- **Móvil (<768px):** lista de tarjetas full-width (1 columna); al tocar una tarjeta se abre el panel como bottom-sheet o pantalla completa.

El panel lateral/modal contiene:
1. Encabezado: nombre, ID, badges de tipo/producto/portal, datos de contacto, precio, fecha de creación (CDMX)
2. Banner de alerta si el lead fue transferido por marketing (morado) o tiene escalación activa (ámbar)
3. Tabs: **Acciones** | **Historial** | **Perfil**
4. Tab Acciones: grid 2x3 de botones rápidos (Registrar actividad, WhatsApp, Llamar, Agendar cita, Ver detalle, Editar lead) — reutilizan los handlers/rutas existentes de `advisor/crm/leads`
5. Tab Historial: timeline cronológico completo desde el registro del lead — actividades (`crm_activities`), transferencias (`crm_lead_transfers`), eventos de escalación, todo en hora CDMX (`América/Mexico_City`) con nombre del usuario que ejecutó la acción
6. Tab Perfil: datos de perfilamiento existentes (reutiliza vista/parciales actuales de perfil de lead)

## 4. Columnas de la tabla (desktop)

En este orden:

1. **Lead** — nombre, `ID {id}`, badge de tipo (ver sección 5), botones ★ (favorito) y 📍 (fijado)
2. **Contacto** — teléfono, email
3. **Origen** — portal (`portal`)
4. **Creado** — fecha y hora de `created_at` en CDMX, formato corto (`10 jun` / `9:00 AM`). Ordenable.
5. **Precio** — `precio` + tipo de operación (`operacion`: Compra/Renta). Ordenable. Si no hay valor: `—` / "Sin definir".
6. **Producto** — badge de color según producto asociado al lead (Outlet, Residencial, Renova, Micro, Legal). Ver sección 4.1.
7. **Último contacto** — tipo de actividad + mensaje/observación (1 línea, truncado) + "hace X" + fecha CDMX completa + nombre del asesor que la registró. Ordenable por fecha de última actividad.
8. **Sin contacto** — badge semáforo con días/horas desde la última actividad (o desde `created_at`/`transferred_at` si no hay actividad). Ordenable (orden ascendente por defecto = más urgente primero).
9. **Estado** — chip Nuevo / Seguimiento / Cierre

En tablet/móvil estas columnas se reorganizan en tarjetas (ver mockup v6): nombre + badges arriba, precio + producto + último contacto + semáforo + estado abajo, botones ★/📍 a la derecha del nombre.

### 4.1 Origen del dato "Producto"

`crm_leads` no tiene columna de producto. Se deriva así:
- Se toma el campo `product` de la **actividad más reciente** (`crm_activities.product`) registrada para ese lead.
- Si no existe ninguna actividad con `product` definido → badge gris "Sin definir" (`prod-nd`).
- Esto se resuelve con una subquery/LEFT JOIN LATERAL en `listLeadsByAdvisor`, sin cambios de esquema.

## 5. Diferenciación de leads "Nuevo"

Para leads con `_state = 'new'`, se muestra un badge adicional bajo el nombre:

| Tipo | Condición | Badge |
|---|---|---|
| **Propio** | `transferred_by IS NULL` (el asesor lo registró) | Azul, ícono persona — "Propio" |
| **Marketing** | `transferred_by` corresponde a un usuario con `role = 'marketing'` | Morado, ícono red — "Mktg · {nombre}" |
| **Escalado** | `escalacion_activa = true` | Ámbar parpadeante, ícono rayo — "Escalado" |

**Detección de marketing:** se agrega un `LEFT JOIN users u_transfer ON u_transfer.id = l.transferred_by` y se selecciona `u_transfer.role AS transferred_by_role` en `listLeadsByAdvisor`.

**Detección de escalación:** se agrega `escalacion_activa` al SELECT de `listLeadsByAdvisor` (actualmente no se selecciona). El badge se muestra si `escalacion_activa = true`, independientemente del `_state` calculado, pero solo es visualmente relevante combinado con `_state = 'new'`.

Si un lead cumple más de una condición (caso raro), prioridad: Escalado > Marketing > Propio.

## 6. Semáforo — leyenda visual

Encima de la barra de filtros, una tira fija con dos filas (colapsable en móvil a un bloque compacto de 2 líneas):

**Fila 1 — "Sin contacto":**
- 🟢 Verde (`sc-ok`): hoy o ayer
- 🟡 Amarillo (`sc-warn`): 2–4 días
- 🔴 Rojo (`sc-danger`): 5+ días
- ⚪ Gris (`sc-none`): sin registro previo de contacto

**Fila 2 — "Tipo de lead nuevo":** muestra los 3 badges de la sección 5 con su significado.

## 7. Búsqueda y filtros

- El campo de búsqueda (`q`) ahora también compara contra el ID del lead. Si el texto ingresado es numérico (con o sin prefijo `#`), se incluye `l.id = <numero>` en el `WHERE` (con `OR` respecto a las condiciones de texto existentes).
- Placeholder actualizado: "Nombre, teléfono, email, ID…" con hint `ej. #421`.
- Se agregan dos chips de filtro rápido:
  - **Favoritos** — filtra por `l.id IN (idsFavoritos)`
  - **Fijados** — filtra por `l.id IN (idsFijados)`
- El resto de filtros existentes (fecha, orden, portal, operación, con_actividad, con_perfil, chips de estado) se mantienen sin cambios funcionales, solo reestilizados.

## 8. Ordenamiento por columnas

Clic en encabezado de columna ordenable (Lead, Creado, Precio, Último contacto, Sin contacto) alterna asc/desc y recarga la página con `orden_campo` y `orden_dir` como query params. Mapeo de columnas a expresiones SQL `ORDER BY`:

| Columna | Expresión |
|---|---|
| Lead | `l.nombre, l.apellido` |
| Creado | `l.created_at` |
| Precio | `l.precio` (NULLS LAST) |
| Último contacto | `last_contact_at` (NULLS LAST) |
| Sin contacto | `COALESCE(last_contact_at, l.transferred_at, l.created_at)` |

Default: `Sin contacto ASC` (más urgente primero), igual que hoy.

## 9. Paginación

- 20 leads por página (constante `PAGE_SIZE = 20`).
- Query param `page` (default 1).
- Se agrega `COUNT(*)` (misma condición WHERE, sin LIMIT/OFFSET) para calcular total de páginas.
- Controles: anterior / números de página / siguiente, estilo del mockup v6. Se muestran en la parte inferior de la tabla (desktop) y al final de la lista de tarjetas (móvil/tablet).

## 10. Favoritos (★)

Ya existe infraestructura (`lead_favoritos`, `leadFavoritos.service.js`, ruta de toggle en `profile.routes.js`). Se reutiliza:

- Botón ★ en cada fila/tarjeta. Estado ON = relleno amarillo (`#f59e0b`), OFF = contorno gris.
- Click → POST AJAX al endpoint existente de toggle favorito → respuesta JSON `{ok, action}`.
- Al confirmar `action: 'added'`, se muestra un **toast** (esquina inferior derecha en desktop, parte superior en móvil) con animación slide-in: ícono estrella + "Guardado en favoritos" + nombre del lead. Auto-dismiss 3s.
- Al quitar (`action: 'removed'`), toast equivalente "Quitado de favoritos" (sin animación de pulso).
- El chip "Favoritos · N" en filtros usa `idsFavoritos.length`.
- Esta función ya está visible en `profile/index.ejs` (tab "Leads favoritos") — sin cambios ahí, solo se agrega el control visual en la bandeja.

## 11. Fijados (📍) — nueva función

Nueva tabla y servicio análogos a favoritos:

```sql
CREATE TABLE lead_pins (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  lead_id BIGINT NOT NULL REFERENCES crm_leads(id),
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, lead_id)
);
```

Nuevo servicio `src/services/leadPins.service.js` con las mismas funciones que `leadFavoritos.service.js` (sin campo `nota`): `getIdsFijados`, `togglePin`, `getLeadsFijados`, `contarFijados`.

Nueva ruta de toggle: `POST /advisor/leads/:id/pin` (análoga a la de favoritos).

**Comportamiento:**
- Botón 📍 en cada fila/tarjeta. Estado ON = relleno teal (`#008a8a`/borde `#00ffff`), OFF = contorno gris.
- Los leads fijados se muestran **primero** en la bandeja (ORDER BY adicional: `is_pinned DESC` antepuesto al orden de columna activo), con un borde izquierdo distintivo (teal) en la fila/tarjeta.
- Toast al fijar: ícono pin + "Lead fijado" + "Aparece primero en tu bandeja". Toast al desfijar: "Lead desfijado".
- Chip "Fijados · N" en filtros usa `idsFijados.length`.
- **Página de perfil** (`profile/index.ejs`): se agrega una tab "Leads fijados" (ícono 📍), análoga a la tab "Leads favoritos" existente — mismo patrón de renderizado, usando `leadPinsService.getLeadsFijados()`.

## 12. Tema claro/oscuro

- Interruptor flotante fijo (esquina superior derecha de la bandeja) con ícono sol/luna y pill animada.
- Alcance: **solo esta vista** (`advisor/crm/leads/index.ejs`), no es un cambio global del sitio.
- Implementación: clase `dark` en el elemento contenedor de la página + bloque CSS `body.dark .selector{...}` (o contenedor equivalente) definiendo la paleta oscura para: shell, tabla, panel, tarjetas móviles/tablet, badges, toasts, chips, KPIs.
- Preferencia persistida en `localStorage` (`theme: 'dark'|'light'`), aplicada al cargar la página vía script inline antes de pintar (evita flash de tema incorrecto).
- Color de acento de botones primarios: `#00ffff` con texto oscuro (`#0f172a`) en ambos temas (según aprobación previa).

## 13. Compatibilidad y dispositivos

- CSS puro + JS vanilla (sin dependencias nuevas), Tailwind CDN existente se mantiene para el resto de la página.
- Botones táctiles mínimo 28×28px en móvil/tablet.
- Tabla desktop con `overflow-x:auto` para pantallas entre 1024–1279px.
- Probado visualmente en: Chrome/Edge Windows, Safari macOS/iOS, Chrome Android — sin APIs específicas de plataforma.

## 14. Fuera de alcance (futuro)

- Habilitar visualización de leads Finalizado/Traspaso en esta bandeja (sección 2).
- Flujo visual de "quién tuvo el lead / quién lo tiene / quién sigue" en escalación inter-gerencias (se muestra solo el badge "Escalado" + evento en historial si está disponible).
- Edición de "Producto" desde la bandeja (es de solo lectura, derivado de actividades).
- Tema oscuro global del sitio.

## 15. Resumen de cambios por archivo

| Archivo | Cambio |
|---|---|
| `src/services/advisor/crm.service.js` | `listLeadsByAdvisor`: agregar columnas (`escalacion_activa`, `transferred_by_role`, `producto` vía subquery), búsqueda por ID, ordenamiento por columna, paginación (`LIMIT`/`OFFSET` + `COUNT`), `ORDER BY is_pinned DESC` |
| `src/controllers/advisor/crm.controller.js` | `leadsIndex`: leer nuevos query params (`page`, `orden_campo`, `orden_dir`, filtros favoritos/fijados), obtener `idsFijados`, pasar `totalPages`/`page` a la vista |
| `src/services/leadPins.service.js` | **Nuevo** — análogo a `leadFavoritos.service.js` sin `nota` |
| `src/routes/advisor.crm.routes.js` | Nueva ruta `POST /advisor/leads/:id/pin` |
| Migración SQL | Nueva tabla `lead_pins` |
| `views/advisor/crm/leads/index.ejs` | Rediseño completo según mockup v6: layout tabla+panel, columnas, semáforo, badges de tipo, favoritos/fijados, búsqueda por ID, orden por columna, paginación, tema claro/oscuro |
| `views/profile/index.ejs` | Nueva tab "Leads fijados" análoga a "Leads favoritos" |
