# Spec: Vista de Citas y Cierres para Administración

**Fecha:** 2026-06-25
**Estado:** Aprobado

---

## Resumen

Nueva página en el panel de `administracion` (`/administracion/citas-cierres`) que permite a los usuarios con rol `administracion` visualizar todas las citas agendadas y cierres (con firma / con firma y pago) de todos los asesores activos, en un calendario tipo Google Calendar con sidebar de filtro por asesor.

---

## Layout — Opción C: Sidebar + Calendario principal

```
┌─ Sidebar (280px) ──────────────┬─ Calendario (full) ────────────────┐
│ ASESORES ACTIVOS               │  ← Junio 2026 →   [Mes|Sem|Día]   │
│ ☑ Victor García  4🔵 2🟢 1🟡  │  [eventos color-coded]             │
│ ☑ Johana Vanessa 2🔵           │                                    │
│ ☑ Luis Alberto   6🔵 1🟢       │  Click evento → Tooltip            │
│ ☑ Remedios Díaz  —             │                                    │
│                                │                                    │
│ LEYENDA                        │                                    │
│ 🔵 Cita agendada               │                                    │
│ 🟢 Cierre con firma            │                                    │
│ 🟡 Firma + Pago                │                                    │
└────────────────────────────────┴────────────────────────────────────┘
```

---

## Datos del calendario

### Fuente 1: Citas agendadas (color azul `#3b82f6`)

- **Origen:** tabla `calendar_events` JOIN `crm_leads` JOIN `users` (asesor) JOIN `crm_activities` (type='cita', mismo lead)
- **Fecha del evento:** columna `inicio` de `calendar_events` (con timezone CDMX)
- **Solo eventos con `lead_id` no nulo** (las citas deben estar vinculadas a un lead)
- **Título en calendario:** `"Cita · {nombre del lead}"`

### Fuente 2: Cierres con firma (color verde `#16a34a`)

- **Origen:** `crm_leads` WHERE `sale_signed_only = true` AND `closed_at IS NOT NULL`
- **Fecha del evento:** `closed_at`
- **Título en calendario:** `"Firma · {nombre del lead}"`

### Fuente 3: Cierres con firma y pago (color ámbar `#d97706`)

- **Origen:** `crm_leads` WHERE `sale_paid = true` AND `closed_at IS NOT NULL`
- **Fecha del evento:** `closed_at`
- **Título en calendario:** `"Firma+Pago · {nombre del lead}"`

---

## Sidebar — Lista de asesores

- Muestra **todos los usuarios activos con role = 'advisor'**
- Cada asesor tiene un **checkbox** (marcado por defecto)
- Desmarcar un asesor oculta sus eventos en el calendario (filtro client-side)
- Badge de conteos junto a cada asesor:
  - 🔵 N citas (total de `calendar_events` con lead vinculado)
  - 🟢 N firmas (total de `sale_signed_only = true`)
  - 🟡 N firma+pago (total de `sale_paid = true`)

---

## Tooltip al hacer clic en un evento

Aparece posicionado cerca del evento. Se cierra al hacer clic fuera o presionar Escape.

### Para eventos de tipo Cita:
- Encabezado con color azul y badge "📅 Cita"
- Avatar + nombre del asesor
- Nombre completo del lead
- Fecha y hora del evento (formato CDMX: `Jue 26 Jun 2026, 10:00 AM`)
- Portal de origen del lead
- Propiedad de interés (folio + lista)
- Teléfono y correo del lead
- Bloque de observaciones de la actividad `crm_activities` (tipo='cita' vinculada al evento)

### Para eventos de tipo Cierre con firma:
- Encabezado con color verde y badge "✓ Firmado"
- Avatar + nombre del asesor
- Nombre completo del lead
- Fecha y hora de cierre (CDMX)
- Portal de origen
- Propiedad de interés
- Teléfono y correo
- Tipo: "✓ Firmó contrato"

### Para eventos de tipo Firma+Pago:
- Igual que Cierre con firma pero encabezado ámbar y badge "✓ Firma + Pago"
- Tipo: "✓ Firmó y pagó"

---

## Arquitectura técnica

### Archivos a crear/modificar

| Archivo | Acción |
|---|---|
| `src/controllers/administracion/citasCierres.controller.js` | **Nuevo** |
| `src/routes/administracion.routes.js` | **Modificar** — agregar `GET /citas-cierres` |
| `views/administracion/citas-cierres/index.ejs` | **Nuevo** |
| `views/administracion/partials/sidebar.ejs` | **Modificar** — agregar link de navegación |

### Controlador

`GET /administracion/citas-cierres` — ejecuta 4 queries en paralelo (`Promise.all`):

1. **Asesores activos con conteos:**
```sql
SELECT
  u.id, u.nombre, u.apellidos, u.username, u.avatar_url,
  COUNT(DISTINCT ce.id) FILTER (WHERE ce.lead_id IS NOT NULL) AS citas_count,
  COUNT(DISTINCT l_firma.id) AS firma_count,
  COUNT(DISTINCT l_pago.id) AS pago_count
FROM users u
LEFT JOIN calendar_events ce ON ce.user_id = u.id AND ce.lead_id IS NOT NULL
LEFT JOIN crm_leads l_firma ON l_firma.advisor_id = u.id AND l_firma.sale_signed_only = true
LEFT JOIN crm_leads l_pago  ON l_pago.advisor_id  = u.id AND l_pago.sale_paid = true
WHERE u.role = 'advisor' AND u.is_active = true
GROUP BY u.id
ORDER BY COALESCE(u.nombre, u.username) ASC
```

2. **Citas (calendar_events):**
```sql
SELECT
  ce.id, ce.user_id AS advisor_id, ce.lead_id, ce.inicio, ce.fin, ce.titulo,
  u.nombre AS asesor_nombre, u.apellidos AS asesor_apellidos, u.avatar_url,
  l.nombre AS lead_nombre, l.apellido AS lead_apellido,
  l.telefono, l.email, l.portal,
  -- Propiedad de interés (del perfil del lead si existe)
  COALESCE(lp.propiedad_interes, '') AS propiedad_interes,
  -- Observaciones de la actividad de cita vinculada
  a.observations AS cita_observaciones, a.scheduled_at AS cita_fecha
FROM calendar_events ce
JOIN users u ON u.id = ce.user_id
JOIN crm_leads l ON l.id = ce.lead_id
LEFT JOIN crm_lead_profiles lp ON lp.lead_id = ce.lead_id
LEFT JOIN crm_activities a ON a.lead_id = ce.lead_id AND a.type = 'cita'
  AND a.created_at = (
    SELECT MAX(a2.created_at) FROM crm_activities a2
    WHERE a2.lead_id = ce.lead_id AND a2.type = 'cita'
  )
WHERE ce.lead_id IS NOT NULL
ORDER BY ce.inicio DESC
```

3. **Cierres con firma:**
```sql
SELECT
  l.id, l.advisor_id, l.nombre AS lead_nombre, l.apellido AS lead_apellido,
  l.telefono, l.email, l.portal, l.closed_at,
  u.nombre AS asesor_nombre, u.apellidos AS asesor_apellidos, u.avatar_url,
  COALESCE(lp.propiedad_interes, '') AS propiedad_interes
FROM crm_leads l
JOIN users u ON u.id = l.advisor_id
LEFT JOIN crm_lead_profiles lp ON lp.lead_id = l.id
WHERE l.sale_signed_only = true AND l.closed_at IS NOT NULL
ORDER BY l.closed_at DESC
```

4. **Cierres con firma y pago:**
```sql
SELECT
  l.id, l.advisor_id, l.nombre AS lead_nombre, l.apellido AS lead_apellido,
  l.telefono, l.email, l.portal, l.closed_at,
  u.nombre AS asesor_nombre, u.apellidos AS asesor_apellidos, u.avatar_url,
  COALESCE(lp.propiedad_interes, '') AS propiedad_interes
FROM crm_leads l
JOIN users u ON u.id = l.advisor_id
LEFT JOIN crm_lead_profiles lp ON lp.lead_id = l.id
WHERE l.sale_paid = true AND l.closed_at IS NOT NULL
ORDER BY l.closed_at DESC
```

Los 4 resultados se pasan a la vista como variables EJS. Los eventos se serializan como JSON inline en un `<script>` para que FullCalendar los consuma sin AJAX.

### Vista `index.ejs`

- Usa el layout existente de administración (include sidebar + shell)
- FullCalendar v6 via CDN (igual que `views/advisor/crm/calendar.ejs`)
- Sidebar con checkboxes por asesor generado con EJS
- JS inline maneja:
  - Inicialización de FullCalendar con los eventos pre-cargados
  - Filtrado por asesor (checkbox → toggle visibility de eventos)
  - `eventClick` → posicionar y mostrar tooltip con datos del evento
  - Click fuera / Escape → cerrar tooltip

### Colores de eventos
| Tipo | Color fondo | Color borde |
|---|---|---|
| Cita | `#eff6ff` | `#3b82f6` |
| Firma | `#f0fdf4` | `#16a34a` |
| Firma+Pago | `#fef3c7` | `#d97706` |

---

## Sidebar de administración — link nuevo

Agregar en `views/administracion/partials/sidebar.ejs`:
```
📅 Citas & Cierres → /administracion/citas-cierres
```

---

## Fuera de alcance

- Crear, editar o eliminar citas desde esta vista (solo lectura)
- Filtro por rango de fechas (el calendario tiene su propia navegación)
- Exportar a CSV
- Notificaciones en tiempo real
