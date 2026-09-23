# Advisor Dashboard UI/UX Redesign — Spec

## Objetivo

Rediseñar el dashboard del panel de advisor (`views/advisor/crm/dashboard.ejs`) para mejorar el espaciado, jerarquía visual y legibilidad. La información actual está muy comprimida; el objetivo es una presentación profesional con fondo blanco, cards limpias, y KPIs ampliados que incluyen porcentajes de conversión.

---

## Cambios en el backend

### Nuevas métricas necesarias

El controller `src/controllers/advisor/crm.controller.js` (acción `dashboard`) debe pasar las siguientes métricas adicionales a la vista, ya sea calculándolas en el service o en el controller mismo:

| Variable | Descripción | Fuente |
|---|---|---|
| `transferencias_recibidas` | Leads donde `transferred_to = advisorId` (recibidos de otro) | `crm_leads` |
| `citas_hoy` | Actividades tipo cita con `scheduled_at::date = NOW()::date` y `advisor_id = $1` | `crm_activities` |
| `citas_agendadas` | Total actividades tipo cita del advisor (todos los tiempos) | `crm_activities` |
| `citas_atendidas` | Citas con `type = 'cita' AND confirmed_at IS NOT NULL` | `crm_activities` |
| `cierres_firma` | Leads cerrados con `sale_signed_only = true` | `crm_leads` |
| `cierres_firma_pago` | Leads cerrados con `sale_paid = true` | `crm_leads` |
| `total_cierres` | Leads donde `status='closed' AND (sale_signed_only OR sale_paid)` — usa OR para evitar doble conteo | `crm_leads` |
| `finalizados_sin_venta` | Leads con `status = 'closed' AND NOT sale_paid AND NOT sale_signed_only` | `crm_leads` |
| `traspasos_realizados` | Leads donde `transferred_by = advisorId` (traspasos manuales) | `crm_leads` |
| `total_leads` | Total de leads del advisor (open + closed) | `crm_leads` |

> Nota: `citas_agendadas`, `citas_atendidas` y `citas_hoy` requieren una nueva query SQL a `crm_activities`. El resto se puede derivar del array `leads` que ya se trae en `listLeadsByAdvisor`.

### Cómo determinar el tipo de cita en `crm_activities`

- `type = 'cita'` identifica actividades de cita (confirmado en código)
- `confirmed_at IS NOT NULL` indica que la cita fue atendida/confirmada
- `subtype` en citas indica el tipo de ubicación (`'presencial'`, etc.), no el estado de asistencia
- `citas_hoy`: `type = 'cita' AND scheduled_at::date = CURRENT_DATE AT TIME ZONE 'America/Mexico_City'`

---

## Layout general

- **Fondo:** `bg-white` para el contenedor principal (actualmente `bg-gray-100`)
- **Padding exterior:** `px-6 py-6` (actualmente `padding: 24px 28px` inline)
- **Espacio entre secciones:** `mb-6`
- **Separadores de sección:** label `text-xs uppercase tracking-widest text-gray-400` + línea `border-b border-gray-100 mb-4`
- **Cards:** `bg-white rounded-xl shadow-sm border border-gray-100`

---

## Sección 1: KPI Cards (2 filas de 6)

### Estructura de la grid

```html
<!-- Fila 1: Estado de leads -->
<div class="grid grid-cols-6 gap-4 mb-4">
  <!-- 6 cards -->
</div>
<!-- Fila 2: Actividad y ventas -->
<div class="grid grid-cols-6 gap-4">
  <!-- 6 cards -->
</div>
```

### Fila 1 — Estado de leads

| Pos | Emoji | Título | Valor | % conversión |
|---|---|---|---|---|
| 1 | 👥 | Total leads | `total_leads` | — (es la base, no se muestra %) |
| 2 | ✨ | Nuevos | `counts.new` | `(new / total) * 100` |
| 3 | 🔄 | En seguimiento | `counts.followup` | `(followup / total) * 100` |
| 4 | 📥 | Transferencias recibidas | `transferencias_recibidas` | `(recv / total) * 100` |
| 5 | 📤 | Traspasos realizados | `traspasos_realizados` | `(traspasos / total) * 100` |
| 6 | ❌ | Finalizados sin venta | `finalizados_sin_venta` | `(fin / total) * 100` |

### Fila 2 — Actividad y ventas

| Pos | Emoji | Título | Valor | % conversión |
|---|---|---|---|---|
| 1 | 📅 | Citas hoy | `citas_hoy` | `(hoy / total) * 100` |
| 2 | 🗓️ | Citas agendadas | `citas_agendadas` | `(agend / total) * 100` |
| 3 | ✅ | Citas atendidas | `citas_atendidas` | `(atend / total) * 100` |
| 4 | ✍️ | Cierres con firma | `cierres_firma` | `(firma / total) * 100` |
| 5 | 💰 | Cierres firma y pago | `cierres_firma_pago` | `(firmapago / total) * 100` |
| 6 | 🏆 | Total cierres | `total_cierres` | `(total_c / total) * 100` |

### Diseño de cada card

```
┌────────────────────────────┐
│  ✨  Nuevos                │  ← emoji + label (text-xs text-gray-500)
│                            │
│         24                 │  ← text-3xl font-bold text-gray-800
│     21% del total          │  ← text-sm font-medium text-teal-600
└────────────────────────────┘
```

- Padding: `p-5`
- Hover: `hover:shadow-md hover:border-b-2 hover:border-teal-500 transition-all`
- Si `total_leads = 0`: mostrar `—` en lugar del porcentaje
- Si valor = 0: porcentaje en `text-gray-300`, si > 0: `text-teal-600`

---

## Sección 2: Gráficas

### Layout

```
┌─────────────────────────┬──────────────────────────┐
│  Embudo de conversión   │  Distribución de leads   │
│  (barras horizontales)  │  (donut chart)           │
│  col-span-1             │  col-span-1              │
└─────────────────────────┴──────────────────────────┘
┌──────────────────────────────────────────────────────┐
│         Actividad reciente (línea, ancho completo)   │
└──────────────────────────────────────────────────────┘
```

- Grid `grid-cols-2 gap-4 mb-6` para las 2 primeras
- Actividad reciente: `w-full mb-6`
- Cards: `bg-white rounded-xl shadow-sm border border-gray-100 p-6`
- Título de cada card: `text-sm font-semibold text-gray-700 uppercase tracking-wide` con `border-l-4 border-teal-500 pl-3 mb-4`

### Embudo de conversión

Mantiene las barras horizontales actuales. Los pasos del embudo:
1. Total leads (100%)
2. Nuevos
3. En seguimiento
4. Citas agendadas
5. Cierres con firma
6. Cierres firma y pago

### Donut de distribución

Mantiene la gráfica actual. Tooltip ya muestra porcentaje (implementado en sesión previa).

### Actividad reciente

Mantiene la gráfica de línea actual sin cambios funcionales.

---

## Sección 3: Tips / Recomendaciones

- Grid `grid-cols-3 gap-4`
- Cards con `border-l-4 border-teal-500`
- Padding `p-4`
- Sin cambios en el contenido de los tips

---

## Archivos a modificar

| Archivo | Cambios |
|---|---|
| `views/advisor/crm/dashboard.ejs` | Rediseño completo del layout y KPIs |
| `src/controllers/advisor/crm.controller.js` | Agregar nuevas métricas al dashboard |
| `src/services/advisor/crm.service.js` | Nueva función o queries para citas y cierres desglosados |

---

## Criterios de aceptación

1. El dashboard muestra 12 KPI cards en 2 filas de 6, cada una con emoji, valor numérico y porcentaje de conversión respecto al total de leads.
2. Las gráficas de embudo y distribución están en la misma fila (2 columnas iguales), y la de actividad reciente ocupa el ancho completo debajo.
3. El fondo general es blanco, las cards tienen `rounded-xl shadow-sm border border-gray-100`.
4. Los porcentajes se muestran en teal si el valor > 0, gris si = 0.
5. Si `total_leads = 0`, no se muestran porcentajes (evitar división por cero).
6. El layout es responsive: en móvil las cards colapsan a `grid-cols-2` o `grid-cols-1`.
