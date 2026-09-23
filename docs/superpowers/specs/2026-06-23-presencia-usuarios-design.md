# Spec: Indicador de Presencia "En Línea" para Usuarios

**Fecha:** 2026-06-23  
**Estado:** Aprobado  

---

## Resumen

Agregar un indicador visual de presencia (estilo WhatsApp) que muestre si un asesor está actualmente en el portal o cuándo fue su última conexión. El indicador aparece en distintas vistas según el rol del usuario que lo consulta.

---

## Comportamiento

### Regla de presencia
- Un usuario se considera **en línea** si tuvo actividad en el portal en los **últimos 60 minutos**.
- Si han pasado más de 60 minutos desde su última actividad, se considera **desconectado**.
- Si nunca ha ingresado al portal (`last_seen_at IS NULL`), se muestra un estado especial.

### Los 3 estados

| Estado | Punto | Texto | Color texto |
|---|---|---|---|
| En línea | 🟢 Verde `#22c55e` | "En línea ahora" | `#16a34a` |
| Desconectado | 🟡 Amarillo `#eab308` | "Última vez hace 3 horas" / "Última vez ayer, 4:12 PM" / "Última vez el 15 jun" | `#a16207` |
| Nunca ingresó | 🔴 Rojo `#ef4444` | "Nunca ha ingresado" | `#ef4444` |

### Formato del texto de última vez
- `< 60 min` → "En línea ahora"
- `1–23 horas` → "Última vez hace N horas" (o "hace 1 hora")
- `Ayer` → "Última vez ayer, H:MM AM/PM" (hora CDMX)
- `2–6 días` → "Última vez el lunes" (nombre del día)
- `≥ 7 días` → "Última vez el 15 jun"
- `NULL` → "Nunca ha ingresado"

### Posición visual
El punto (12×12px) se superpone sobre la esquina inferior derecha del avatar (border 2.5px blanco para separarlo del fondo). Debajo del nombre del asesor, donde antes aparecía el correo en la tabla principal, ahora aparece el texto de estado con su color correspondiente.

---

## Arquitectura

### 1. Base de datos

```sql
ALTER TABLE users ADD COLUMN last_seen_at TIMESTAMPTZ;
CREATE INDEX idx_users_last_seen ON users(last_seen_at);
```

### 2. Middleware global — `src/middlewares/lastSeen.js`

- Se monta en `src/app.js` inmediatamente después del middleware de sesión.
- En cada request con usuario autenticado (`req.session?.user?.id`):
  - Revisa `req.session._lastSeenWritten` (timestamp en ms).
  - Si han pasado más de **2 minutos** desde la última escritura (o nunca se ha escrito):
    - Ejecuta `UPDATE users SET last_seen_at = NOW() WHERE id = $1` de forma **asíncrona** (no bloquea el request con `await`).
    - Actualiza `req.session._lastSeenWritten = Date.now()`.
- Si el UPDATE falla, se loggea el error pero **nunca interrumpe el request** (try/catch silencioso).

**Carga estimada:** ~50 usuarios × (8h / 2min throttle) = ~12,000 writes/día. Negligible para PostgreSQL.

### 3. Helper — `src/utils/presencia.js`

```javascript
// Exporta: formatPresencia(last_seen_at) → { color, dotColor, label, textColor }
// color: 'green' | 'yellow' | 'red'
// dotColor: código hex del punto
// label: string en español
// textColor: código hex del texto
```

Lógica interna:
- `last_seen_at === null` → rojo
- `NOW() - last_seen_at < 60 min` → verde
- `NOW() - last_seen_at ≥ 60 min` → amarillo, con formato relativo en español (CDMX)

### 4. Queries — agregar `last_seen_at` al SELECT

En cada controlador que ya consulta `users`, agregar `u.last_seen_at` al SELECT existente. No se requieren JOINs nuevos.

Controladores afectados:
- `src/controllers/directivo/asesores.controller.js` → `asesoresIndex`, `asesorShow`
- `src/controllers/manager/dashboard.controller.js` → query del ranking
- `src/controllers/manager/` → controlador de supervisión de asesores
- `src/controllers/admin.controller.js` → query de users/index
- `src/controllers/profile.controller.js` → query del perfil propio

---

## Vistas a modificar

### Advisor
| Archivo | Cambio |
|---|---|
| `views/profile/index.ejs` | Agregar punto sobre avatar + texto de estado en la sección de perfil propio |

### Admin
| Archivo | Cambio |
|---|---|
| `views/admin/users/index.ejs` | Agregar punto sobre avatar + texto de estado en la tabla de usuarios (todas las filas, todos los roles) |

### Manager
| Archivo | Cambio |
|---|---|
| `views/manager/dashboard.ejs` | Agregar punto sobre avatar en la tabla de ranking (sección `.ranking-table`) |
| `views/manager/advisors/show.ejs` | Agregar punto + estado en el encabezado del asesor supervisado |
| `views/manager/leads/index.ejs` | Agregar punto + estado en el encabezado del asesor cuya bandeja se supervisa |

### Directivo
| Archivo | Cambio |
|---|---|
| `views/directivo/asesores/index.ejs` | Reemplazar línea de correo por texto de estado; agregar punto sobre avatar |
| `views/directivo/asesores/show.ejs` | Agregar punto + estado en el encabezado del perfil |

---

## Componente visual reutilizable

Para evitar duplicar HTML en 7 vistas, se crea un partial EJS:

**`views/partials/presencia-dot.ejs`**

Recibe variables locales: `presencia` (objeto de `formatPresencia`).  
Renderiza únicamente el punto superpuesto (se incluye dentro del `<div>` del avatar).

**`views/partials/presencia-label.ejs`**

Recibe `presencia`. Renderiza la línea de texto de estado debajo del nombre.

Uso en cada vista:
```ejs
<%- include('/partials/presencia-dot', { presencia }) %>
<%- include('/partials/presencia-label', { presencia }) %>
```

---

## Archivos nuevos / modificados

| Archivo | Tipo |
|---|---|
| `src/middlewares/lastSeen.js` | Nuevo |
| `src/utils/presencia.js` | Nuevo |
| `views/partials/presencia-dot.ejs` | Nuevo |
| `views/partials/presencia-label.ejs` | Nuevo |
| `src/app.js` | Modificado — montar middleware |
| `src/controllers/directivo/asesores.controller.js` | Modificado — agregar `last_seen_at` al SELECT + pasar `formatPresencia` |
| `src/controllers/manager/dashboard.controller.js` | Modificado — agregar `last_seen_at` al SELECT |
| `src/controllers/admin.controller.js` | Modificado — agregar `last_seen_at` al SELECT |
| `src/controllers/profile.controller.js` | Modificado — agregar `last_seen_at` al SELECT |
| `views/profile/index.ejs` | Modificado |
| `views/admin/users/index.ejs` | Modificado |
| `views/manager/dashboard.ejs` | Modificado |
| `views/manager/advisors/show.ejs` | Modificado |
| `views/manager/leads/index.ejs` | Modificado |
| `views/directivo/asesores/index.ejs` | Modificado |
| `views/directivo/asesores/show.ejs` | Modificado |

---

## Migración

La columna `last_seen_at` arranca en `NULL` para todos los usuarios existentes → aparecerán en rojo "Nunca ha ingresado" hasta que hagan su próximo login. No requiere backfill.

---

## Fuera de alcance

- Actualización en tiempo real (WebSocket/SSE) — el estado se muestra al cargar la página.
- Presencia para roles distintos a los listados (externo, marketing, administracion).
- Filtrar o ordenar la tabla por estado de presencia.
