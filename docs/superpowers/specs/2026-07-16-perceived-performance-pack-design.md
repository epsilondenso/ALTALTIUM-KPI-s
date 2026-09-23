# Perceived Performance Pack — Design Spec

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer que el sistema se sienta rápido, fluido y sin lentitud al cargar imágenes, navegar páginas o ver galerías — sin build tools ni dependencias nuevas.

**Approach:** Propuesta B — Pack de Percepción de Velocidad.

**Tech Stack:** Node.js v24 + Express v5, EJS, Tailwind CDN, `compression()` ya activo, Service Worker existente en `public/sw.js` (registrado desde `public/js/push-manager.js`).

---

## Contexto del sistema

- **102 imágenes** en `public/img/`, las más pesadas: `hero/fondo.png` (5MB), `logos/altaltium-hero.jpg` (3.4MB), `hero/altaltium_home.png` (3MB), `hero/bienvenida.png` (2.3MB), varias de documentos ~2MB cada una.
- `express.static` en `app.js` sin `maxAge` → el browser **no cachea** CSS/JS/imágenes entre páginas.
- `public/sw.js` solo maneja Web Push — no tiene estrategia de caché de assets.
- Galería desktop en `views/pages/propiedad.ejs`: la función `updateView()` hace `mainImg.src = images[idx]` de forma instantánea, sin transición de opacidad.
- La mayoría de `<img>` en vistas de documentos y catálogos ya tienen `loading="lazy"`, pero sin `decoding="async"` ni `width`/`height`.
- No existe `public/css/img-perf.css` ni `public/js/img-perf.js` — se crean en este feature.

---

## Archivos afectados

| Acción | Archivo | Responsabilidad |
|--------|---------|-----------------|
| Modificar | `src/app.js` | Agregar `maxAge: '7d'` a `express.static` |
| Crear | `public/css/img-perf.css` | Skeleton shimmer + fade-in + transición de galería |
| Crear | `public/js/img-perf.js` | Auto-apply lazy/async, fade-in observer |
| Modificar | `public/sw.js` | Cache First para imágenes/CSS/JS |
| Modificar | `views/layouts/main.ejs` | Cargar img-perf.css y img-perf.js |
| Modificar | `views/pages/propiedad.ejs` | Crossfade en `updateView()` |

---

## Sección 1 — HTTP Cache-Control

**Archivo:** `src/app.js`

**Cambio:** La llamada a `express.static` pasa de:
```js
app.use(express.static(path.join(__dirname, '../public')));
```
a:
```js
app.use(express.static(path.join(__dirname, '../public'), {
  maxAge: '7d',
  etag: true,
  lastModified: true,
}));
```

**Efecto:** Imágenes, CSS y JS se cachean 7 días en el browser. ETag garantiza revalidación correcta cuando un archivo cambia en deploy. En visitas repetidas y navegación entre páginas, estos assets se sirven **desde disco local del usuario** — cero red.

---

## Sección 2 — `public/css/img-perf.css` (nuevo)

Estilos globales para skeleton loading y fade-in de imágenes:

```css
/* Skeleton shimmer — visible mientras la imagen carga */
.img-lazy {
  opacity: 0;
  transition: opacity 300ms ease;
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: img-shimmer 1.4s infinite;
}

@keyframes img-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Cuando la imagen cargó: fade-in */
.img-lazy.img-loaded {
  opacity: 1;
  background: none;
  animation: none;
}

/* Transición de galería principal (desktop propiedad.ejs) */
[data-main-image] {
  transition: opacity 220ms ease;
}
```

---

## Sección 3 — `public/js/img-perf.js` (nuevo)

Script que aplica lazy loading automáticamente a todas las imágenes de la página y activa el fade-in al cargar.

**Responsabilidades:**
1. En `DOMContentLoaded`: encuentra todos los `<img>` sin atributo `loading` → agrega `loading="lazy"` y `decoding="async"`.
2. A todos los `<img>` que no son hero (sin `data-hero`) → agrega clase `.img-lazy`.
3. Usa `IntersectionObserver` para detectar cuándo entran al viewport.
4. Cuando una imagen entra al viewport y termina de cargar (evento `load`) → agrega `.img-loaded`.
5. Si la imagen ya estaba en caché (`complete === true`) al ejecutar el script → agrega `.img-loaded` inmediatamente.

**Pseudocódigo:**
```js
document.addEventListener('DOMContentLoaded', () => {
  const imgs = document.querySelectorAll('img:not([data-hero])');

  imgs.forEach(img => {
    // Auto-apply lazy/async si no está configurado
    if (!img.hasAttribute('loading')) img.setAttribute('loading', 'lazy');
    if (!img.hasAttribute('decoding')) img.setAttribute('decoding', 'async');

    // Fade-in skeleton
    if (!img.classList.contains('no-skeleton')) {
      img.classList.add('img-lazy');

      const reveal = () => img.classList.add('img-loaded');

      if (img.complete && img.naturalWidth > 0) {
        // Ya en caché: revelar inmediatamente
        reveal();
      } else {
        img.addEventListener('load', reveal, { once: true });
        img.addEventListener('error', reveal, { once: true }); // fallback: no quedar gris
      }
    }
  });
});
```

**Nota de diseño:** El atributo `data-hero` en imágenes hero previene el skeleton (para que no haya flash en imágenes above-the-fold que se cargan rápido). El atributo `no-skeleton` clase permite optar fuera del efecto en casos específicos (avatares pequeños, iconos).

---

## Sección 4 — Gallery Crossfade (`views/pages/propiedad.ejs`)

**Problema actual:** La función `updateView()` hace `mainImg.src = images[currentIndex]` (línea ~947) — swap instantáneo, se ve como un parpadeo brusco.

**Cambio:** Wrappear el swap con fade de opacidad:

```js
function updateView() {
  if (!mainImg) return;

  // Crossfade: ocultar → cambiar src → mostrar al cargar
  mainImg.style.opacity = '0';
  const nextSrc = images[currentIndex];
  mainImg.onload = function () {
    mainImg.style.opacity = '1';
    mainImg.onload = null;
  };
  mainImg.src = nextSrc;

  // ... resto sin cambios (counter, thumbs, flechas)
}
```

La CSS en `img-perf.css` ya incluye `[data-main-image] { transition: opacity 220ms ease; }` que hace el crossfade suave.

**Importante:** La imagen principal hero ya tiene `loading="eager"` y el atributo `data-main-image`. El script `img-perf.js` no agrega skeleton a imágenes con `data-hero`, pero `[data-main-image]` sí recibe la transición CSS vía selector en la hoja de estilos.

---

## Sección 5 — Service Worker actualizado (`public/sw.js`)

El SW actual solo maneja Web Push. Se amplia con **Cache First** para assets estáticos.

**Estrategias por tipo de recurso:**

| URL pattern | Estrategia | Justificación |
|-------------|-----------|---------------|
| `/img/`, `/css/`, `/js/`, `/flyonui/` | **Cache First** | Assets versionados en deploy; cambios = nuevo nombre de caché |
| `res.cloudinary.com`, `drive.google.com/thumbnail` | **Cache First** (max 50 entradas) | CDN externo; imágenes de propiedades no cambian frecuentemente |
| Todo lo demás (HTML, API) | **Network First** | Contenido dinámico; siempre fresco |

**Cache versioning:**
```js
const CACHE_STATIC = 'altaltium-static-v2';
const CACHE_IMAGES = 'altaltium-images-v1';
```

En `activate`, el SW borra cachés con nombres distintos (limpeza automática tras deploy).

**Pre-cache en install** (assets críticos):
```js
const PRECACHE_URLS = [
  '/css/flyonui.css',
  '/css/styles.css',
  '/css/img-perf.css',
  '/js/main.js',
  '/js/img-perf.js',
  '/img/icon-192.png',
  '/img/badge-72.png',
  '/img/placeholder.svg',
];
```

**El SW no pre-cachea las imágenes hero** (muy pesadas para el install) — se cachean al primer fetch.

**Nota:** El SW ya está registrado en `public/js/push-manager.js` — no se toca el registro. Solo se reemplaza la lógica interna de `sw.js`. La funcionalidad de Web Push (evento `push`, `notificationclick`) se conserva íntegra.

---

## Sección 6 — Integración en `views/layouts/main.ejs`

**En `<head>`:** agregar hoja de estilos:
```html
<link rel="stylesheet" href="/css/img-perf.css">
```

**Antes de `</body>`:** agregar script:
```html
<script src="/js/img-perf.js" defer></script>
```

El atributo `defer` garantiza que el script no bloquea el parsing del HTML y se ejecuta después de que el DOM esté listo.

**Hero preload** (imágenes above-the-fold): agregar condicional para que páginas puedan declarar su hero:
```ejs
<% if (typeof heroImage !== 'undefined' && heroImage) { %>
  <link rel="preload" as="image" href="<%= heroImage %>">
<% } %>
```

Las páginas que usan hero declaran la variable antes del layout (vía `res.render`), p.ej.:
- `welcome.ejs` / home → `heroImage: '/img/hero/altaltium_home.png'`
- `catalogo.ejs` → `heroImage: '/img/hero/bienvenida.png'`

---

## Lo que NO cambia

- No se modifica `push-manager.js` — el registro del SW sigue igual
- No se compilan imágenes a WebP — sin build tools
- No se toca Tailwind CDN — fuera de alcance
- No se modifican las 150 vistas EJS — `img-perf.js` aplica `lazy`/`async` automáticamente en runtime
- El `compression()` (gzip) ya está activo — no se toca

---

## Criterios de éxito

1. Al recargar la página por segunda vez, las imágenes aparecen **instantáneamente** (caché HTTP + SW)
2. Al navegar por la galería de propiedad, la imagen principal hace **crossfade suave** en lugar de parpadear
3. Las imágenes fuera del viewport no aparecen en la pestaña Network del inspector hasta que el usuario scrollea hacia ellas
4. Las imágenes muestran un **shimmer gris animado** mientras cargan, sin espacio en blanco
5. El Service Worker en DevTools muestra las cachés `altaltium-static-v2` e `altaltium-images-v1` pobladas
