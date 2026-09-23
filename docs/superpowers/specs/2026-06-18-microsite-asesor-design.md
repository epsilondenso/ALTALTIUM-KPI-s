# Micro-sitio Público por Asesor — Diseño

**Fecha:** 2026-06-18  
**Ruta pública:** `GET /asesor/:username`  
**Estado:** Diseño aprobado — pendiente implementación

---

## 1. Propósito

Cada asesor de Altaltium tendrá una página pública accesible sin login que muestra su perfil, catálogo de propiedades outlet disponibles y canales de contacto directo. El objetivo es generar leads orgánicos desde buscadores y redes sociales, y dar a los asesores una presencia digital propia dentro de la marca.

---

## 2. Stack y Restricciones

- **Render:** EJS + Express v5 (server-side rendering, NO SPA)
- **Estilos:** Tailwind CDN + clases CSS custom en `public/css/styles.css`
- **Fuente:** Montserrat (Google Fonts) — fallback `'Segoe UI', sans-serif`
- **Sin login requerido** — ruta completamente pública
- **Propiedades:** solo de `inventario_outlet` (tabla completa con imágenes, precios, características)
- **Imágenes:** Cloudinary (columna `imagenes_cache JSONB`)

---

## 3. Ruta y Controlador

```
GET /asesor/:username
```

- Busca el asesor por `username` en tabla `users`
- Solo muestra asesores con `is_active = true` y `role = 'advisor'`
- Si no existe o no está activo → 404
- Consulta propiedades en `inventario_outlet` donde el asesor aparece asignado y `estatus = 'disponible'`

**Archivo controlador:** `src/controllers/public/microsite.controller.js`  
**Archivo ruta:** se agrega en `src/routes/main.routes.js`

---

## 4. Diseño Visual — Tema Oscuro / Claro

### Paleta de colores

| Variable | Dark | Light |
|---|---|---|
| `--bg` | `#06090f` | `#f8fafc` |
| `--bg2` | `#0b0f1a` | `#ffffff` |
| `--bg3` | `#111827` | `#f1f5f9` |
| `--border` | `#1e2d40` | `#e2e8f0` |
| `--text` | `#f1f5f9` | `#0f172a` |
| `--muted` | `#94a3b8` | `#334155` |
| `--muted2` | `#4d6680` | `#475569` |
| `--teal` | `#0d9488` | `#0d9488` |
| `--teal-lt` | `#2dd4bf` | `#0d9488` |
| `--gold` | `#c9a84c` | `#b8860b` |

El toggle claro/oscuro se guarda en `localStorage` y se aplica vía `data-theme` en `<html>`.

### Fuente

```css
font-family: 'Gotham', 'Montserrat', 'Segoe UI', sans-serif;
```

---

## 5. Estructura de la Página (de arriba a abajo)

### 5.1 Chrome / Navbar
- **Izquierda:** Logo "Al" (teal gradient) + "Altaltium"
- **Centro:** Slogan `¡LA LLAVE DE TU FUTURO!` en uppercase, color teal, Montserrat
- **Derecha:** Toggle claro/oscuro con ícono SVG (luna / sol)
- Sticky top, `z-index: 50`

### 5.2 Hero
- Banner de fondo: gradiente corporativo `#0c3547 → #0d4f6e → #064e3b` (mismo para todos los asesores)
- Overlay oscuro hacia abajo para legibilidad
- **Avatar** circular (de `avatar_url`), borde teal, initials como fallback
- **Nombre completo** del asesor (grande)
- **Rol** y **gerencia** del asesor

### 5.3 Rating
- Estrellas `★` en dorado calculadas dinámicamente en base al desempeño CRM
- Fórmula de cálculo: pendiente definir (ver sección 9)
- Texto: `· Asesor verificado Altaltium`

### 5.4 Franja de Contacto
Tres botones principales + nota:
| Botón | Acción |
|---|---|
| Llamar | `tel:` con el teléfono del asesor |
| WhatsApp | `https://wa.me/52{telefono}` |
| Contactar | Abre modal con formulario → crea lead en CRM |

**Nota debajo:** "Respuesta en menos de 5 min · Sin compromiso"

### 5.5 Badge de Verificación
- Paloma azul estilo Facebook (SVG)
- Texto: "Asesor certificado de **Altaltium · Real Estate Solutions**"

### 5.6 Barra de Búsqueda + Filtros (Pills)
- **Buscador:** campo de texto con ícono lupa, busca por zona/municipio/colonia
- **Pills de filtro** con ícono SVG propio cada uno:
  - Tipo, Estado, Municipio, Precio, Recámaras, Baños, Estac., Terreno m², Construcc.
- **Sort pill** separado con divisor vertical: Recientes / Mayor Precio / Menor Precio / etc.
- En móvil: pills con scroll horizontal, scrollbar oculto

### 5.7 Cuerpo Principal (2 columnas)

#### Columna izquierda — Sidebar de Infografías (242px desktop)
- Header: "Infografías" + "Ver todas →"
- 10 infografías como tarjetas clickeables (click = abrir/descargar PDF)
- Sin botón "Descargar" — la tarjeta completa es el CTA
- En móvil: carrusel horizontal

**Infografías incluidas:**
1. Proceso de Compra Outlet Inmobiliario
2. ¿Qué es un Remate Bancario?
3. Beneficios de Comprar con Nosotros
4. Documentos Requeridos
5. Preguntas Frecuentes
6. ¿Qué es una Ejecución de Sentencia?
7. Tipos de Crédito Hipotecario
8. Guía del Comprador Primera Vez
9. Zonas con Mayor Plusvalía 2025
10. Costos Adicionales al Comprar

*(Las infografías son archivos PDF/imagen estáticos en Google Drive o Cloudinary)*

#### Columna derecha — Catálogo de Propiedades
- Header: "Propiedades disponibles" + badge contador
- **Grid:** 3 col desktop → 2 col tablet (≤1024px) → 1 col móvil (≤768px)
- **20 propiedades por página** con paginación
- Cada card contiene:
  - Slider de imágenes (3 fotos de Cloudinary) con flechas 44×44px y dots
  - Badge de tipo (Casa / Depto / Terreno)
  - Tipo de operación (Ejecución de sentencia / Remate bancario)
  - Título / ubicación
  - Precio con formato `$XXX,XXX`
  - Métricas con SVG: m², recámaras, baños, estacionamientos
  - 3 botones: Llamar | WhatsApp | Contactar
  - Click en la card → abre `/p/:id` (ficha pública existente)

### 5.8 Footer
- Línea decorativa degradada (gold → teal)
- **Izquierda:** Logo Altaltium + "La Llave de Tu Futuro" + dirección (link a Google Maps)
- **Derecha:** Íconos redes sociales (teal rounded squares SVG outline): Facebook, Instagram, YouTube, TikTok, Sitio Web
- © 2026 · Todos los derechos reservados · Términos y Condiciones · Política de Privacidad

### 5.9 FAB WhatsApp
- Botón flotante verde fijo `bottom: 20px; right: 20px`
- `48px` diámetro, abre WhatsApp del asesor

---

## 6. Animaciones

| Animación | Implementación | Timing |
|---|---|---|
| Scroll reveal cards | `IntersectionObserver` + clase `.revealed`, stagger 60ms por card | `opacity + translateY(24px) → 0`, 450ms ease |
| Skeleton shimmer en sliders | Overlay con `@keyframes shimmer`, se retira escalonado al cargar imagen | 500ms base + 120ms por card |
| Count-up en contador de resultados | JS setInterval, 0 → N en ~1s | 35ms por tick |
| Hover cards | `translateY(-3px)` | 200ms |
| Hover infografías | `translateY(-2px)` | 150ms |
| Hover social icons | `translateY(-2px)` | 200ms |
| Toggle tema | `background + color` | 250ms |
| `prefers-reduced-motion` | Desactiva todas las transiciones | CSS media query |
| `scroll-behavior: smooth` | En `html` | nativo |

---

## 7. Accesibilidad (WCAG AA)

- Flechas del slider: `44×44px` mínimo con `aria-label="Imagen anterior/siguiente"`
- Input búsqueda: `aria-label="Buscar propiedades"`
- Botones solo-ícono: `aria-label` en cada uno
- Focus rings visibles: `outline: 2px solid var(--teal-lt); outline-offset: 2px`
- Contraste modo claro: `--muted` `#334155`, `--muted2` `#475569` (ratio ≥ 4.5:1)
- `prefers-reduced-motion`: desactiva animaciones CSS

---

## 8. Formulario de Contacto (Modal)

Al hacer clic en "Contactar":
- Modal con campos: Nombre, Teléfono, Email (opcional), Mensaje (opcional)
- `POST /p/:id/contacto` (endpoint existente) adaptado o nuevo endpoint `POST /asesor/:username/contacto`
- Payload: `{ nombre, telefono, email, mensaje, intent: 'contact' }`
- Lógica: crea lead en `crm_leads` asignado al asesor del microsite
- Si ya existe lead 'open' con ese teléfono + advisor_id → actualiza sin duplicar
- Notificación `lead_publico` al asesor y sus managers
- Respuesta al usuario: "¡Gracias! El asesor te contactará pronto."

---

## 9. Cálculo de Rating

La calificación (1.0–5.0 estrellas) se calcula en el controlador con base en 4 métricas CRM ponderadas, consultadas en los últimos 90 días:

| Métrica | Tabla/columna | Peso |
|---|---|---|
| Leads atendidos (al menos 1 actividad registrada) | `crm_activities.lead_id` distintos | 25% |
| Total de actividades registradas | `COUNT(crm_activities)` | 25% |
| Perfiles completados (`etapa >= 'perfilado'`) | `crm_leads.etapa` | 25% |
| Seguimientos dados (actividades después del día 1 por lead) | actividades con `created_at > lead.opened_at + 1 day` | 25% |

**Normalización:** cada métrica se normaliza contra el máximo del equipo (gerencia) para obtener un score 0–1, luego se promedia y se escala a 1.0–5.0.

**Mínimo para mostrar rating:** el asesor debe tener al menos 5 leads para que el rating sea visible; si tiene menos, se omiten las estrellas.

---

## 10. Responsive

| Breakpoint | Cambios |
|---|---|
| ≤1024px (tablet) | Grid 2 col, sidebar 200px |
| ≤768px (móvil) | Layout apilado, sidebar horizontal scroll, grid 1 col, slogan oculto en navbar |
| ≤480px | Texto de botones Llamar/Contactar oculto (solo ícono) |

---

## 11. SEO Básico

```html
<title>{nombre_asesor} — Asesor Inmobiliario | Altaltium</title>
<meta name="description" content="Propiedades outlet disponibles con {nombre_asesor}. Remates bancarios y ejecuciones de sentencia en {municipio}.">
<meta property="og:image" content="{avatar_url}">
```

---

## 12. Archivos a Crear / Modificar

| Archivo | Acción |
|---|---|
| `src/controllers/public/microsite.controller.js` | Crear |
| `src/routes/main.routes.js` | Agregar ruta `GET /asesor/:username` |
| `views/public/microsite.ejs` | Crear |
| `views/public/microsite-contact-modal.ejs` | Crear (o inline en microsite.ejs) |
| `public/css/styles.css` | Agregar variables CSS del tema y clases del microsite |

---

## 13. Decisiones Confirmadas

| Decisión | Resolución |
|---|---|
| Rating CRM | Calculado con 4 métricas ponderadas (ver sección 9). Mínimo 5 leads para mostrarlo. |
| Infografías | PDFs estáticos en Google Drive (folder fijo). URLs hardcodeadas en la vista o en un array en el controlador. |
| Link en CRM | Agregar "Ver mi perfil público" en el sidebar del advisor CRM (`views/advisor/crm/partials/sidebar.ejs`) |
| Sin propiedades | Mostrar sección vacía con leyenda: "Este asesor no tiene propiedades disponibles en este momento." |
| URL | `/asesor/:username` — sin cambios |
| Visibilidad | **Solo asesores activos** (`is_active = true` y `role = 'advisor'`). Cualquier otro caso → 404. |
