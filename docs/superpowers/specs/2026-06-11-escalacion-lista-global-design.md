# Escalación automática: lista global de transferencia

## Contexto

El sistema de escalación automática de leads (`src/services/escalacion.cron.js`) actualmente
transfiere leads sin contacto entre asesores siguiendo el orden de su gerencia
(tabla `escalacion_orden`, agrupada por `manager_id`), y al agotarse una gerencia
salta a la siguiente gerencia del mismo grupo (Grupo A: 32→8→34, Grupo B: 33↔50),
sin volver a la gerencia de inicio.

Este esquema basado en gerencias se reemplaza por **una sola lista global de
asesores**, administrada manualmente desde el panel admin y actualizada cada
semana. El cron ahora recorre esa lista circularmente, dando una vuelta completa
antes de caer al fallback final (Daniel Rojas → Denisse Hansen).

## Objetivo

1. Reemplazar la lógica de escalación por gerencias con una lista global única y
   ordenada de asesores.
2. La lista es editable desde el panel admin (reordenar con flechas ↑↓, activar/
   desactivar, agregar/quitar asesores) — pensada para actualizarse cada semana.
3. Registrar un historial de cada escalación automática, para poder medir qué
   asesores pierden leads por no registrar contacto a tiempo.

## Fuera de alcance

- No se modifican las reglas de activación de `escalacion_activa` (marketing→
  asesor/manager, manager→asesor de su equipo activan; advisor↔advisor o
  manager↔manager no activan).
- No se modifican el horario laboral (L-V 9-20h, S-D 9-14h CDMX), el timeout de
  5 minutos, ni el toggle global `configuracion.escalacion_activa`.
- No se elimina la tabla `escalacion_orden` ni las columnas
  `escalacion_manager_id` en `crm_leads` — quedan sin uso, no se borran.
- No se construye un reporte/vista para `escalacion_historial` en esta fase;
  solo se registran los datos para uso futuro.
- No se agregan pruebas automatizadas (el proyecto no usa framework de testing).

## Modelo de datos

### Nueva tabla: `escalacion_lista_global`

```sql
CREATE TABLE escalacion_lista_global (
  id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(id),
  orden INT NOT NULL,
  activo BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(orden)
);
```

- Una fila por asesor en la lista global, ordenada por `orden` (1..N).
- `activo = false` permite pausar a un asesor sin reacomodar el resto del orden
  ni eliminarlo de la lista.
- El cron solo considera filas con `activo = true`, ordenadas por `orden`.

### Seed inicial

Insertar los 18 asesores en el orden dado, posiciones 1-18:

```
1. Orlando Palacios Vega       (25)
2. Victor Manuel Garcia Bautista (32)
3. Laura Patricia Claudio Lucio (74)
4. Yolanda Rojas Aguilar       (11)
5. Marco Antonio Salazar Vidal (43)
6. Manuel Omar Moreno Zapata    (8)
7. Carmina Priscilla Bolaños Herrera (30)
8. Eduardo Ramirez Arreola     (86)
9. Patricia Nathalie Mijares Perez (84)
10. Domingo Infante Allende    (34)
11. Jose Arturo Gonzalez Reyes (15)
12. Valentina Mariel Salgado Arias (58)
13. Diana Elizabeth Vivanco Galindo (90)
14. Johana Vanessa Arias Lara  (23)
15. Jose Manuel Alvarez Hernandez (85)
16. Herlinda Marahi Ruiz Ramirez (77)
17. Adriana Nivon Medrano       (79)
18. Luis Néstor Portilla Vázquez (28)
```

### Nueva tabla: `escalacion_historial`

```sql
CREATE TABLE escalacion_historial (
  id SERIAL PRIMARY KEY,
  lead_id INT NOT NULL REFERENCES crm_leads(id),
  advisor_id_anterior INT NOT NULL REFERENCES users(id),
  advisor_id_nuevo INT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

- Se inserta una fila cada vez que el cron transfiere automáticamente un lead.
- `advisor_id_anterior` = quien tenía el lead y no registró contacto.
- `advisor_id_nuevo` = a quién se transfirió (puede ser otro asesor de la lista,
  Daniel Rojas o Denisse Hansen).
- Permite calcular estadísticas por periodo (ej. cuántas veces perdió leads cada
  asesor en una semana dada).

### Reuso de columna existente: `crm_leads.escalacion_gerencia_inicio`

Esta columna (INT) ya existe y dejaba de usarse al quitar el concepto de
gerencia. Se reutiliza para guardar el **`user_id` del asesor que marca el
"punto de partida" de la vuelta circular** para ese lead (ver lógica del cron).
No requiere cambio de esquema.

`escalacion_manager_id` deja de usarse (no se borra, queda sin lectura/escritura).

## Lógica del cron (`src/services/escalacion.cron.js`)

### Sin cambios

- Frecuencia: cada 1 minuto.
- Verificación de horario laboral (L-V 9-20h, S-D 9-14h CDMX) y toggle
  `configuracion.escalacion_activa`.
- Condición SQL para detectar leads a escalar:
  ```sql
  WHERE escalacion_activa = true
    AND status = 'open'
    AND advisor_id != 7
    AND transferred_at < NOW() - INTERVAL '5 minutes'
    AND NOT EXISTS (
      SELECT 1 FROM crm_activities a
      WHERE a.lead_id = crm_leads.id
      AND a.created_at > crm_leads.transferred_at
    )
  ```
- Reglas de activación de `escalacion_activa` (marketing→asesor/manager,
  manager→asesor de su equipo).
- Fallback final: Daniel Rojas (35) → 5 min sin contacto → Denisse Hansen (7) →
  `escalacion_activa = false`, fin definitivo.
- Transacciones `BEGIN/COMMIT` en cada caso de escalación.

### Al activarse la escalación (primera vez para un lead)

Cuando se activa `escalacion_activa = true` (marketing→asesor/manager o
manager→asesor de su equipo), se calcula y guarda el punto de partida de la
vuelta circular en `escalacion_gerencia_inicio`:

```javascript
const { rows } = await client.query(
  `SELECT user_id FROM escalacion_lista_global WHERE activo = true ORDER BY orden`
);

let advisorInicioId = advisorActualId; // advisor al que se transfirió originalmente
if (rows.length > 0) {
  const posInicio = rows.findIndex(r => r.user_id === advisorActualId);
  if (posInicio === -1) {
    advisorInicioId = rows[0].user_id; // si no está en la lista, el punto de partida es el primero (Orlando)
  }
}
// guardar advisorInicioId en crm_leads.escalacion_gerencia_inicio
```

### Función `obtenerSiguienteAdvisor` (reemplaza la lógica de gerencias/grupos)

```javascript
async function obtenerSiguienteAdvisor(advisorActualId, advisorInicioId, client) {
  const { rows } = await client.query(
    `SELECT user_id FROM escalacion_lista_global WHERE activo = true ORDER BY orden`
  );

  if (rows.length === 0) return null; // sin lista configurada → no escala

  const posActual = rows.findIndex(r => r.user_id === advisorActualId);
  const posSiguiente = posActual === -1 ? 0 : (posActual + 1) % rows.length;
  const siguienteAdvisorId = rows[posSiguiente].user_id;

  // si el siguiente coincide con el punto de partida, ya se dio la vuelta completa
  if (siguienteAdvisorId === advisorInicioId) {
    return FALLBACK_1_ID; // 35, Daniel Rojas
  }

  return siguienteAdvisorId;
}
```

Comportamiento resultante:

- **Advisor actual SÍ está en la lista**: pasa a la siguiente posición
  (circular, módulo N).
- **Advisor actual NO está en la lista** (caso borde, ej. recibió el lead
  directo fuera de la lista): el "siguiente" es la posición 1 (Orlando). Si esa
  posición coincide con `advisorInicioId`, cae directo a Daniel Rojas (caso
  límite con lista de 1 elemento).
- **Se completa la vuelta** (el siguiente calculado == `advisorInicioId`): en
  vez de transferir de nuevo al punto de partida, va a Daniel Rojas (35).
- **Lista vacía o sin elementos activos**: `obtenerSiguienteAdvisor` retorna
  `null` y el cron no escala ese lead (lo deja igual, sin error).

### Registro de historial

Dentro de la misma transacción del `UPDATE` que mueve el lead:

```javascript
await client.query(
  `INSERT INTO escalacion_historial (lead_id, advisor_id_anterior, advisor_id_nuevo)
   VALUES ($1, $2, $3)`,
  [lead.id, advisorActualId, siguienteAdvisorId]
);
```

Esto aplica también cuando el destino es Daniel Rojas o Denisse Hansen (quedan
registrados como `advisor_id_nuevo` igual que cualquier otro).

### Lo que se elimina del código actual

- Constantes `GRUPO_A`, `GRUPO_B`.
- Toda la lógica de "siguiente gerencia" / "sin regresar a la gerencia de
  inicio" basada en `escalacion_orden` y `manager_id`.
- Lectura/escritura de `escalacion_manager_id`.

## Panel admin: lista global

Nueva vista en la sección de configuración del admin (junto al toggle de
escalación existente).

### Vista

`GET /admin/configuracion/escalacion-lista`

Muestra una tabla con los asesores de `escalacion_lista_global` ordenados por
`orden`:

| Posición | Asesor | Activo | Acciones |
|---|---|---|---|
| 1 | Orlando Palacios Vega | ✅ | ↑ ↓ Quitar |
| 2 | Victor Manuel Garcia Bautista | ✅ | ↑ ↓ Quitar |
| ... | ... | ... | ... |

Más un selector para "Agregar asesor" (dropdown de usuarios `role='advisor'`
que no estén ya en la lista).

### Rutas

```
GET  /admin/configuracion/escalacion-lista          → renderiza la vista
POST /admin/configuracion/escalacion-lista/mover    → { id, direccion: 'arriba'|'abajo' }
                                                        intercambia `orden` con la fila adyacente
POST /admin/configuracion/escalacion-lista/toggle   → { id } → activa/desactiva
POST /admin/configuracion/escalacion-lista/agregar  → { user_id } → inserta al final
                                                        (orden = MAX(orden) + 1)
POST /admin/configuracion/escalacion-lista/quitar   → { id } → elimina la fila
                                                        (no reacomoda los demás `orden`,
                                                        solo deja un hueco que no afecta
                                                        la lectura por estar ordenada)
```

Cada acción guarda de inmediato (sin botón "Guardar" general), igual que el
toggle de escalación existente.

## Manejo de errores y casos borde

- **Lista vacía o sin activos**: el cron no escala ningún lead afectado, sin
  error ni excepción.
- **Advisor actual no está en la lista**: se trata como si su posición fuera
  la anterior a la posición 1, por lo que el siguiente calculado es la posición
  1 (Orlando).
- **Vuelta completa**: detectada comparando el siguiente calculado contra
  `escalacion_gerencia_inicio` (punto de partida guardado al activar la
  escalación).
- **Fallback final**: Daniel Rojas (35) → 5 min sin contacto → Denisse Hansen
  (7) → `escalacion_activa = false`, fin. Sin cambios respecto al
  comportamiento actual.
- **Errores de conexión/BD**: el cron mantiene su try/catch existente; loguea
  y reintenta en el siguiente minuto.
- **Transacciones**: `UPDATE crm_leads` + `INSERT escalacion_historial` +
  notificación, todo en el mismo `BEGIN/COMMIT`.

## Migración

1. Crear tablas `escalacion_lista_global` y `escalacion_historial`.
2. Seed de `escalacion_lista_global` con los 18 asesores en el orden dado
   (sección "Seed inicial").
3. **Recalcular el punto de partida para leads ya activos**: los leads con
   `escalacion_activa = true` tienen actualmente `escalacion_gerencia_inicio`
   poblado con un id de gerencia viejo (ej. `35`), que no corresponde a ningún
   `user_id` de `escalacion_lista_global`. Si se deja así, esos leads nunca
   detectarían "vuelta completa" y seguirían escalando indefinidamente sin
   llegar al fallback. Para evitarlo, se corre un `UPDATE` único antes de
   desplegar, aplicando la misma regla que usa el cron al activarse:

   ```sql
   UPDATE crm_leads
   SET escalacion_gerencia_inicio = COALESCE(
     (SELECT user_id FROM escalacion_lista_global
      WHERE user_id = crm_leads.advisor_id AND activo = true),
     (SELECT user_id FROM escalacion_lista_global
      WHERE activo = true ORDER BY orden LIMIT 1)
   )
   WHERE escalacion_activa = true AND status = 'open';
   ```

## Pruebas (manuales, antes de desplegar)

1. Seed de `escalacion_lista_global` con los 18 asesores.
2. Crear lead de prueba: `escalacion_activa = true`, `transferred_at` hace 6
   minutos, `advisor_id = 25` (Orlando), `escalacion_gerencia_inicio = 25`.
   Correr el cron → debe pasar a Victor García (32), insertar fila en
   `escalacion_historial` (25 → 32), generar notificación.
3. Probar `advisor_id` fuera de la lista (ej. 99), `escalacion_gerencia_inicio = 25`
   (Orlando como punto de partida) → debe ir a Orlando (25). Como
   `25 == escalacion_gerencia_inicio`, en realidad debe ir directo a Daniel
   Rojas (35) — validar este caso límite específicamente.
4. Probar el último de la lista (Néstor Portilla, 28) con punto de partida
   distinto (ej. Omar Moreno, 8) → debe pasar a Orlando (25, posición 1).
5. Probar la vuelta completa: punto de partida Omar Moreno (8), advisor actual
   Marco Salazar (43, posición 5, justo antes de Omar) → el siguiente
   calculado es Omar Moreno (8) == punto de partida → debe ir a Daniel Rojas
   (35).
6. Probar Daniel Rojas (35) sin contacto en 5 min → debe ir a Denisse Hansen
   (7) y `escalacion_activa = false`.
7. Probar lista vacía / todos `activo = false` → el cron no debe escalar ni
   lanzar error.
8. Verificar que registrar una actividad en `crm_activities` detiene la
   escalación (`escalacion_activa = false`) sin importar la posición actual.
9. Verificar panel admin: mover ↑/↓, activar/desactivar, agregar y quitar
   asesores — cada acción se refleja de inmediato en `escalacion_lista_global`.
