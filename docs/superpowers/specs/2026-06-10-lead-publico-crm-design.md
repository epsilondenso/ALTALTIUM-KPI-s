# Diseño: Captura de leads desde la Ficha Pública (Outlet) → CRM

**Fecha:** 2026-06-10
**Alcance:** `views/public/propiedad.ejs`, `src/controllers/public/propiedad.controller.js`, `src/services/advisor/crm.service.js`, `src/services/notificaciones.service.js`, tabla `configuracion`, `CLAUDE.md` (tabla de tipos de notificación).

## 1. Objetivo

Cuando un visitante de la ficha pública (`/p/:id?a=<advisorId>`) quiere contactar al asesor —por teléfono, WhatsApp o mensaje— se le pide primero un formulario corto. Con esos datos se crea (o actualiza) automáticamente un lead en `crm_leads`, asignado al asesor que compartió el link (o a un asesor de marketing por defecto si el link no tiene `?a=`). El asesor y su(s) manager(es) reciben una notificación tipo campana.

## 2. Flujo de usuario (UX)

### 2.1 Botones de contacto

La ficha pública muestra tres botones, reemplazando el botón único actual "Hablar con el Asesor":

```
[ 📞 Llamar ]   [ 💬 WhatsApp ]   [ ✉️ Contactar ]
```

### 2.2 Bottom sheet único, 3 variantes

Los tres botones abren el mismo bottom sheet (panel deslizante desde abajo, estilo glass/teal de la ficha), adaptado según el botón presionado:

| | 📞 Llamar | 💬 WhatsApp | ✉️ Contactar |
|---|---|---|---|
| Campos | Nombre*, Teléfono* | Nombre*, Teléfono* | Nombre*, Teléfono*, Email (opcional), Mensaje (opcional, precargado con texto sugerido) |
| Botón final | "Mostrar teléfono" | "Continuar a WhatsApp" | "Enviar mensaje" |
| Acción tras enviar exitosamente | Revela tarjeta con nombre/foto del asesor + número + botón `tel:` | Abre `wa.me` con el mensaje (incluye `propertyUrl`, ya implementado) | Muestra confirmación: "¡Listo! El asesor {nombre} te contactará pronto." |

\* Campos requeridos. Validación: nombre no vacío, teléfono exactamente 10 dígitos.

El formulario es **obligatorio**: no hay opción de "omitir" antes de continuar con la acción elegida.

### 2.3 Flujo técnico común

1. Validación en cliente (nombre no vacío, teléfono 10 dígitos).
2. `POST /p/:id/contacto` con body `{ nombre, telefono, email, mensaje, intent }` donde `intent ∈ {'call','whatsapp','contact'}`, y `?a=<advisorId>` si está presente en la URL de la ficha.
3. El backend crea o reutiliza el lead en `crm_leads` (ver sección 3).
4. Respuesta JSON:
   - `intent='call'` → `{ ok: true, advisorPhone: '<telefono del asesor>' }`
   - `intent='whatsapp'` → `{ ok: true }`
   - `intent='contact'` → `{ ok: true }`
5. El frontend ejecuta la acción visual correspondiente.

## 3. Endpoint y lógica de creación/reutilización del lead

### 3.1 Endpoint

```
POST /p/:id/contacto
Query:  ?a=<advisorId>   (opcional, igual que la página)
Body:   { nombre, telefono, email, mensaje, intent }
```

Se monta en las rutas públicas existentes (mismo router que `GET /p/:id`).

### 3.2 Resolución del asesor destino

1. Si `?a=<id>` corresponde a un usuario activo en `users` → ese usuario es el `advisor_id` del lead.
2. Si no hay `?a=` o el id no es válido → se usa el **fallback de marketing**: se lee de la tabla `configuracion` la clave `lead_publico_advisor_fallback_id` (valor por defecto `'80'`, Aldo Granados Granados). Si la clave no existe en `configuracion`, se usa `80` como hardcode de respaldo.

### 3.3 Búsqueda de duplicados

```sql
SELECT id FROM crm_leads
WHERE telefono = $1 AND advisor_id = $2 AND status = 'open'
LIMIT 1
```

- **Si existe** → se actualiza ese lead (`nombre`, `email`, `mensaje` con los nuevos valores si vienen no vacíos; `updated_at = NOW()`). No se crea un lead nuevo y **no se envían notificaciones** (para evitar spam si el mismo visitante envía el formulario varias veces).
- **Si no existe** → se crea un nuevo lead (sección 3.4) y se envían las notificaciones (sección 4).

### 3.4 Creación del lead nuevo

Se reutiliza `createLeadEtapa1(advisorId, data)` de `src/services/advisor/crm.service.js`, con un cambio mínimo: agregar un parámetro opcional `createdByInferred` (default `false`, para no afectar las llamadas existentes desde el CRM de asesores) que se usa en la columna `created_by_inferred`. Para los leads de la ficha pública se llama con `createdByInferred = true`.

Mapeo de campos (`data` pasado a `createLeadEtapa1`):

| Columna `crm_leads` | Valor |
|---|---|
| `advisor_id` | resuelto en 3.2 |
| `nombre` | del formulario |
| `telefono` | del formulario (10 dígitos) |
| `email` | del formulario (puede ser `null`) |
| `mensaje` | del formulario; si viene vacío, texto generado según `intent`: <br>• `call` → "Solicitó que le mostraran el teléfono del asesor." <br>• `whatsapp` → "Solicitó contacto por WhatsApp." <br>• `contact` → "Solicitó información por correo/formulario." |
| `portal` | `'Ficha Pública'` |
| `sitio_web` | `propertyUrl` (el link completo `/p/:id?a=...`) |
| `producto` | `'Outlet'` |
| `titulo` | `p.folio` o, si no existe, `direccionCompleta` |
| `url_aviso` | `propertyUrl` |
| `tipo` | `p.tipo` (si existe) |
| `municipio`, `colonia`, `estado`, `calle` | de la propiedad (`p.*`), si existen |
| `precio` | `p.costo_total` o `p.precio_comercial`, si existen |

Las demás columnas no listadas (`apellido`, `fecha`, `aviso`, `codigo_asesor`, `numero_serie`, `numero_exterior`, `numero_interior`, `cp`, `portal_detalle`, `fecha_hora_mx`) quedan `null`/default, igual que en el flujo manual del CRM.

`status` y `etapa` no se asignan explícitamente — usan el default de la tabla (`status = 'open'`), igual que `createLeadEtapa1` actual.

`escalacion_activa` queda en su valor por defecto (`false`), consistente con la regla documentada: leads que no son traspaso manager→advisor no activan escalación.

`crm_lead_transfers`: se mantiene el insert existente dentro de `createLeadEtapa1` (registro de creación con `to_user_id = advisor_id`, `transfer_type = 'creacion'`).

## 4. Notificaciones

Solo se envían cuando se **crea un lead nuevo** (no en actualizaciones de duplicados).

```javascript
const intentLabel = { call: 'quiere que le llamen', whatsapp: 'contactó por WhatsApp', contact: 'envió un mensaje' }[intent];
const mensajeNotif = `Nuevo contacto desde tu ficha pública: ${nombre} (${intentLabel})`;

// Al asesor (o fallback de marketing)
await notifService.crearNotificacion(advisorId, 'lead_publico', mensajeNotif, `/advisor/crm/leads/${leadId}`, null);

// A los managers del asesor
await notifService.notificarSupervisores(advisorId, 'lead_publico', mensajeNotif, `/manager/crm/leads/${leadId}`, null);
```

### 4.1 Nuevo tipo de notificación

Se agrega `lead_publico` a la tabla de tipos de notificación en `CLAUDE.md`:

| Tipo | Destinatario |
|---|---|
| `lead_publico` | advisor (o fallback de marketing) + sus manager(es) |

`_getTipoLabel` en `notificaciones.service.js` debe incluir una etiqueta para `lead_publico` (ej. "Nuevo contacto — Ficha Pública").

## 5. Manejo de errores

- **Validación backend** (nombre vacío o teléfono inválido): responde `400 { ok:false, error:'...' }`. El frontend muestra el error dentro del bottom sheet sin cerrarlo.
- **Error de BD al crear/actualizar el lead**: responde `500`, mensaje loggeado con `console.error` (mismo patrón que `propiedad.controller.js`). El frontend reacciona según `intent`:
  - `call` → muestra igual el teléfono del asesor (ya disponible en `advisor.telefono`, renderizado server-side, no depende de este endpoint).
  - `whatsapp` → abre igual el link de `wa.me` (ya construido server-side como `waUrl`).
  - `contact` → única modalidad 100% dependiente del backend; muestra "No pudimos registrar tu mensaje. Intenta por WhatsApp o llamada."

## 6. Seguridad / anti-spam

- **Rate limiting** por IP en `POST /p/:id/contacto`: máximo 5 solicitudes por minuto, implementado con un middleware simple en memoria (Map IP → timestamps), sin dependencias nuevas (apto para instancia única Render Free).
- **Sanitización de longitud**: `nombre` máx. 200 caracteres, `email` máx. 100, `mensaje` máx. 1000. Se truncan antes de guardar.
- Sin captcha por ahora (YAGNI; se puede agregar si hay spam real).

## 7. Testing

Prueba manual en local (`npm start`), sin tests automatizados (el proyecto no tiene suite configurada):

1. Abrir `/p/:id?a=<advisorId>` con un asesor real de la BD local. Probar los 3 botones y verificar que cada uno crea un registro en `crm_leads` con `advisor_id` correcto.
2. Abrir `/p/:id` sin `?a=` → verificar que el lead se asigna al fallback (`lead_publico_advisor_fallback_id`, default 80 / Aldo Granados).
3. Enviar el formulario dos veces con el mismo teléfono y mismo asesor → verificar que se actualiza el mismo `id` en `crm_leads` (no se duplica), y que solo la primera vez se generan notificaciones.
4. Verificar notificación campana en sesión del asesor y de su(s) manager(es) tras la creación inicial.
5. Verificar que en `intent='call'` se muestra el teléfono incluso si se simula un error 500 en el endpoint (fallback en frontend).
6. Verificar rate limiting: más de 5 envíos en un minuto desde la misma IP → respuesta de error controlada (no 500 sin manejar).

## 8. Cambios de configuración

- Nueva fila en tabla `configuracion`:
  ```sql
  INSERT INTO configuracion (clave, valor, descripcion)
  VALUES ('lead_publico_advisor_fallback_id', '80', 'Asesor de marketing al que se asignan leads de la ficha pública sin ?a=')
  ON CONFLICT (clave) DO NOTHING;
  ```
- Actualización de `CLAUDE.md`: tabla de tipos de notificación (agregar `lead_publico`) y, opcionalmente, documentar el nuevo endpoint `POST /p/:id/contacto` en la sección de rutas públicas.
