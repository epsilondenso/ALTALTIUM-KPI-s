# Rediseño Reporte de Estimación Comercial — Design Spec

## Decisiones de diseño aprobadas

- **Dirección:** Ejecutivo limpio — fondo blanco, acentos teal (#008a8a / #00cccc)
- **Hero:** Tarjeta teal con gradiente (006666→008a8a→00a3a3), valor en blanco grande, stats debajo en tarjetas blancas con iconos SVG
- **Alcance:** Rediseño completo — ambos modos `esPdf: false` (web) y `esPdf: true` (PDF)

---

## Modo Web (`esPdf: false`)

### Estructura de secciones

1. **Barra superior de marca** — 4px, gradiente teal (ya existe, se mantiene)
2. **Header** — Logo + título + subtítulo a la izquierda; meta-pills (fecha, empresa) a la derecha. Asesor en header eliminado (se mueve a su propia sección abajo).
3. **Hero teal** — `background: linear-gradient(135deg, #006666, #008a8a, #00a3a3)`, `border-radius: 20px`, `box-shadow`. Contiene: eyebrow, valor grande, dirección con icono pin, pills de tipo/segmento/precio m².
4. **Stats row** — 4 tarjetas blancas con icono SVG teal + label + valor grande teal: Recámaras, Baños, Construcción, Terreno.
5. **Datos + Mapa** — grid 2 columnas: tabla de datos del inmueble izquierda, mapa Google Maps iframe derecha.
6. **Características** — grid 8 tarjetas con icono SVG individual por campo (recámaras, baños, medios baños, estacionamientos, construcción, terreno, antigüedad, conservación).
7. **Amenidades** — pills teal con icono checkmark. Oculta si no hay amenidades.
8. **Asesor + Notas** — 2 columnas: tarjeta oscura (slate-900) con avatar de iniciales, nombre, teléfono, correo; tarjeta blanca con texto de disclaimer.
9. **Honorarios** — sección colapsable. Cuando visible: encabezado con borde teal, 3 inputs (tipo, valor bloqueado, cesión), botón calcular, 2 tarjetas de resultados (descripción + parcialidades con barra total teal), 2 métricas grandes (ganancia % + costo de compra %).
10. **Barra de acción** (no-print) — Volver ← / Calcular honorarios (teal outline) / Descargar PDF (teal sólido con icono descarga).
11. **Footer** — copyright centrado.

### Iconos SVG (inline, stroke, sin dependencias externas)

| Campo | Icono |
|---|---|
| Casa/inmueble | `<path d="M3 9l9-7 9 7v11..."/>` |
| Recámaras | casa simple |
| Baños | bañera |
| Construcción | grid/plano |
| Terreno | área |
| Ubicación | pin de mapa |
| Teléfono | auricular |
| Correo | sobre |
| Antigüedad | reloj |
| Conservación | estrella |
| Checkmark amenidades | `<polyline points="20 6 9 17 4 12"/>` |
| Descarga PDF | flecha abajo + línea base |
| Honorarios | signo $ |

---

## Modo PDF (`esPdf: true`)

Layout A4 portrait, una hoja, paleta idéntica.

### Sin honorarios (3 columnas)
- Col 1: datos del inmueble + características (grid 2×2) + asesor
- Col 2: mapa estático grande (Google Static Maps API)
- Col 3: disclaimer + precio m² + conservación

### Con honorarios (2 columnas)
- Col izquierda: datos + características + mapa pequeño + asesor
- Col derecha: calculadora honorarios compacta (descripción + parcialidades + barra total + ganancia/costo)

### Header PDF
Logo + empresa + "Reporte de estimación comercial" a la izquierda; fecha de emisión a la derecha. Separador `hr` teal 2px debajo.

### Barra de valor PDF
Fondo `#f0fafa`, borde izquierdo 3px teal, valor en `#008a8a` 22px bold, dirección debajo, pills a la derecha.

---

## Preservar sin cambios

- Lógica JavaScript: `descargarPDF()`, `abrirHonorariosEmbebidos()`, `ocultarHonorariosEmbebidos()`, honorarios API
- Cálculos server-side EJS de honorarios (`_honorarios`, `_pago1`, `_pago2`, etc.)
- Parámetros de query string (`include_honorarios`, `tipo_honorarios`, `precio_cesion_honorarios`)
- Mapa iframe (web) y Static Maps (PDF)
- Variables EJS: `datos`, `usuario`, `esPdf`, `googleMapsKey`, `baseUrl`
- `<style>` con `@page`, `@media print`, animaciones del overlay de carga
