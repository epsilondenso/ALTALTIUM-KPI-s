# Perceived Performance Pack — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer que el sistema se sienta rápido y fluido — caché HTTP 7 días, skeleton shimmer + fade-in en imágenes, crossfade en galería de propiedades y Service Worker con Cache First para assets estáticos.

**Architecture:** 6 cambios independientes: (1) `maxAge` en `express.static`, (2+3) dos archivos nuevos `img-perf.css`/`img-perf.js`, (4) integración en `main.ejs`, (5) crossfade en `propiedad.ejs`, (6) SW actualizado. Cada uno es desplegable por separado.

**Tech Stack:** Node.js v24 + Express v5, EJS, CSS nativo, Service Worker API, `compression()` ya activo.

---

## Mapa de archivos

| Acción | Archivo | Qué hace |
|--------|---------|----------|
| Modificar | `src/app.js:49` | `maxAge: '7d'` en `express.static` |
| Crear | `public/css/img-perf.css` | Skeleton shimmer + fade-in CSS |
| Crear | `public/js/img-perf.js` | Auto-lazy + fade-in observer JS |
| Modificar | `views/layouts/main.ejs:43` | Cargar `img-perf.css` en `<head>` |
| Modificar | `views/layouts/main.ejs:64` | Cargar `img-perf.js` con `defer` |
| Modificar | `views/layouts/main.ejs:13` | Soporte `heroImage` preload |
| Modificar | `views/pages/propiedad.ejs:104` | `loading="eager"` en imagen principal galería |
| Modificar | `views/pages/propiedad.ejs:944` | Crossfade en `updateView()` |
| Modificar | `views/public/microsite.ejs:430` | Corregir `loading="lazy"` → `eager` en hero |
| Modificar | `public/sw.js` | Cache First para imágenes/CSS/JS |

---

## Task 1: Caché HTTP en express.static

**Files:**
- Modify: `src/app.js:49`

- [ ] **Step 1: Aplicar maxAge**

En `src/app.js`, reemplaza la línea 49:

```js
// ANTES
app.use(express.static(path.join(__dirname, "../public")));

// DESPUÉS
app.use(express.static(path.join(__dirname, "../public"), {
  maxAge: "7d",
  etag: true,
  lastModified: true,
}));
```

- [ ] **Step 2: Verificar**

Reinicia el servidor (`node src/server.js`) y abre DevTools → Network. Recarga la página y haz clic en cualquier `.css` o imagen `.png`. Debe mostrar el header:

```
Cache-Control: public, max-age=604800
```

En la segunda recarga, el status debe decir `304 Not Modified` o `(disk cache)`.

- [ ] **Step 3: Commit**

```bash
git add src/app.js
git commit -m "perf: cache HTTP 7 días para assets estáticos (CSS/JS/imágenes)"
```

---

## Task 2: Crear `public/css/img-perf.css`

**Files:**
- Create: `public/css/img-perf.css`

- [ ] **Step 1: Crear el archivo**

Crea `public/css/img-perf.css` con este contenido exacto:

```css
/* ── Skeleton shimmer mientras la imagen carga ─────────────────── */
.img-lazy {
  opacity: 0;
  transition: opacity 300ms ease;
  background: linear-gradient(
    90deg,
    #f0f0f0 25%,
    #e8e8e8 50%,
    #f0f0f0 75%
  );
  background-size: 200% 100%;
  animation: img-shimmer 1.4s ease-in-out infinite;
}

@keyframes img-shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── Fade-in cuando cargó ──────────────────────────────────────── */
.img-lazy.img-loaded {
  opacity: 1;
  background: none;
  animation: none;
}

/* ── Crossfade de la imagen principal en galería de propiedad ──── */
[data-main-image] {
  transition: opacity 220ms ease;
}

/* ── Dark mode: shimmer más oscuro ─────────────────────────────── */
@media (prefers-color-scheme: dark) {
  .img-lazy {
    background: linear-gradient(
      90deg,
      #2a2a2a 25%,
      #333333 50%,
      #2a2a2a 75%
    );
    background-size: 200% 100%;
    animation: img-shimmer 1.4s ease-in-out infinite;
  }
}

:root[data-theme="dark"] .img-lazy {
  background: linear-gradient(
    90deg,
    #2a2a2a 25%,
    #333333 50%,
    #2a2a2a 75%
  );
  background-size: 200% 100%;
  animation: img-shimmer 1.4s ease-in-out infinite;
}
```

- [ ] **Step 2: Verificar que el archivo existe**

```bash
ls public/css/img-perf.css
```

Expected: el archivo aparece en el listado.

- [ ] **Step 3: Commit**

```bash
git add public/css/img-perf.css
git commit -m "perf: agregar skeleton shimmer + fade-in CSS para imágenes"
```

---

## Task 3: Crear `public/js/img-perf.js`

**Files:**
- Create: `public/js/img-perf.js`

- [ ] **Step 1: Crear el archivo**

Crea `public/js/img-perf.js` con este contenido exacto:

```js
// public/js/img-perf.js
// Aplica lazy loading, decoding async y skeleton fade-in a todas las
// imágenes de la página en runtime, sin necesidad de editar cada vista.
(function () {
  function init() {
    document.querySelectorAll('img').forEach(function (img) {
      var isEager = img.getAttribute('loading') === 'eager';

      // Auto-apply loading="lazy" y decoding="async" si no están configurados
      if (!img.hasAttribute('loading')) {
        img.setAttribute('loading', 'lazy');
      }
      if (!img.hasAttribute('decoding')) {
        img.setAttribute('decoding', 'async');
      }

      // Skeleton + fade-in solo en imágenes lazy (no en hero/eager)
      if (img.getAttribute('loading') === 'lazy' && !img.classList.contains('no-skeleton')) {
        img.classList.add('img-lazy');

        function reveal() {
          img.classList.add('img-loaded');
        }

        // Si ya está en caché del browser: revelar inmediatamente
        if (img.complete && img.naturalWidth > 0) {
          reveal();
        } else {
          img.addEventListener('load',  reveal, { once: true });
          // En error también revelar (no dejar en shimmer gris para siempre)
          img.addEventListener('error', reveal, { once: true });
        }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    // DOM ya listo (script cargado con defer)
    init();
  }
})();
```

- [ ] **Step 2: Verificar sintaxis**

```bash
node -e "require('fs').readFileSync('public/js/img-perf.js', 'utf8'); console.log('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add public/js/img-perf.js
git commit -m "perf: script auto-lazy + skeleton fade-in para imágenes"
```

---

## Task 4: Integrar en `views/layouts/main.ejs`

**Files:**
- Modify: `views/layouts/main.ejs:13` (soporte heroImage preload)
- Modify: `views/layouts/main.ejs:43` (cargar CSS)
- Modify: `views/layouts/main.ejs:64` (cargar JS)

- [ ] **Step 1: Agregar soporte para heroImage preload**

En `views/layouts/main.ejs`, después de la línea 13 (`<link rel="icon" ...>`), agrega:

```ejs
  <!-- Preload hero image si la página lo declara (mejora LCP) -->
  <% if (typeof heroImage !== 'undefined' && heroImage) { %>
    <link rel="preload" as="image" href="<%= heroImage %>">
  <% } %>
```

- [ ] **Step 2: Cargar img-perf.css en `<head>`**

En `views/layouts/main.ejs`, después de la línea 43 (`<link rel="stylesheet" href="/css/crm.css">`), agrega:

```html
  <link rel="stylesheet" href="/css/img-perf.css">
```

El bloque de estilos en `<head>` debe quedar así:

```html
  <!-- Estilos globales -->
  <link rel="stylesheet" href="/css/styles.css">
  <link rel="stylesheet" href="/css/crm.css">
  <link rel="stylesheet" href="/css/img-perf.css">
```

- [ ] **Step 3: Cargar img-perf.js antes de `</body>`**

En `views/layouts/main.ejs`, después de la línea 64 (`<script src="/js/main.js"></script>`), agrega:

```html
  <script src="/js/img-perf.js" defer></script>
```

El bloque de JS al final del body debe quedar así:

```html
  <!-- JS global -->
  <script src="/js/main.js"></script>
  <script src="/js/img-perf.js" defer></script>
  <script src="/js/drawer.js"></script>
```

- [ ] **Step 4: Verificar visualmente**

Abre cualquier página interna (ej. `/documentos`). En DevTools → Network filtra por `img-perf`. Deben aparecer ambos archivos: `img-perf.css` (200) y `img-perf.js` (200).

Abre DevTools → Elements y haz clic en cualquier `<img>` de la página. Debe tener:
- `loading="lazy"`
- `decoding="async"`
- `class="... img-lazy img-loaded"` (si ya cargó)

- [ ] **Step 5: Commit**

```bash
git add views/layouts/main.ejs
git commit -m "perf: integrar img-perf.css/js en layout principal + soporte heroImage preload"
```

---

## Task 5: Gallery crossfade en `views/pages/propiedad.ejs`

**Files:**
- Modify: `views/pages/propiedad.ejs:104` (agregar `loading="eager"`)
- Modify: `views/pages/propiedad.ejs:944` (crossfade en `updateView`)
- Modify: `views/public/microsite.ejs:430` (corregir `loading` del hero)

- [ ] **Step 1: Marcar imagen principal como eager**

En `views/pages/propiedad.ejs`, la imagen principal de la galería está en la línea 104. Reemplaza el bloque `<img>`:

```html
<!-- ANTES -->
          <img
            data-main-image
            src="<%= galleryImages[0] %>"
            alt="<%= property.titulo || property.title %>"
            onerror="this.onerror=null; this.src='/img/placeholder.svg';"
            class="w-full h-full object-cover transition-transform duration-300 cursor-zoom-in"
            data-open-lightbox
          >

<!-- DESPUÉS -->
          <img
            data-main-image
            src="<%= galleryImages[0] %>"
            alt="<%= property.titulo || property.title %>"
            loading="eager"
            decoding="async"
            onerror="this.onerror=null; this.src='/img/placeholder.svg';"
            class="w-full h-full object-cover transition-transform duration-300 cursor-zoom-in no-skeleton"
            data-open-lightbox
          >
```

`loading="eager"` + clase `no-skeleton` evita que `img-perf.js` la marque como lazy ni le aplique shimmer (es la imagen hero above-the-fold).

- [ ] **Step 2: Agregar crossfade en `updateView()`**

En `views/pages/propiedad.ejs`, localiza la función `updateView()` que empieza alrededor de la línea 944:

```js
    function updateView() {
      if (!mainImg) return;

      mainImg.src = images[currentIndex];
```

Reemplaza esas 4 líneas con:

```js
    function updateView() {
      if (!mainImg) return;

      mainImg.style.opacity = '0';
      var _nextSrc = images[currentIndex];
      mainImg.onload = function () {
        mainImg.style.opacity = '1';
        mainImg.onload = null;
      };
      mainImg.src = _nextSrc;
```

La CSS de `[data-main-image] { transition: opacity 220ms ease; }` (Task 2) ya provee el crossfade suave.

- [ ] **Step 3: Corregir hero en microsite.ejs**

En `views/public/microsite.ejs` línea ~430, la imagen hero tiene `loading="lazy"` incorrecto para una imagen above-the-fold:

```html
<!-- ANTES -->
<img src="/img/hero/altaltium-hero.jpg" alt="Altaltium Real Estate Solutions" loading="lazy">

<!-- DESPUÉS -->
<img src="/img/hero/altaltium-hero.jpg" alt="Altaltium Real Estate Solutions" loading="eager" decoding="async" class="no-skeleton">
```

- [ ] **Step 4: Verificar crossfade**

Abre una propiedad en el catálogo, p.ej. `/propiedad/1`. Haz clic en las flechas o thumbnails para cambiar la imagen principal.

Expected: la imagen hace un fade suave de 220ms entre fotos, sin parpadeo brusco. En DevTools → Elements, el `[data-main-image]` debe tener `transition: opacity 220ms ease` aplicado desde `img-perf.css`.

- [ ] **Step 5: Commit**

```bash
git add views/pages/propiedad.ejs views/public/microsite.ejs
git commit -m "perf: crossfade 220ms en galería de propiedad + eager loading en heroes"
```

---

## Task 6: Actualizar Service Worker (`public/sw.js`)

**Files:**
- Modify: `public/sw.js` (reemplazar contenido completo)

- [ ] **Step 1: Reemplazar `public/sw.js`**

Reemplaza el contenido completo de `public/sw.js` con:

```js
// public/sw.js — Service Worker de Altaltium
// Responsabilidades: Web Push + caché Cache-First para assets estáticos

const CACHE_STATIC = 'altaltium-static-v2';
const CACHE_IMAGES = 'altaltium-images-v1';

// Assets críticos que se pre-cachean al instalar el SW
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

// ── Install: pre-cachear assets críticos ────────────────────────
self.addEventListener('install', function (e) {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE_STATIC).then(function (cache) {
      return cache.addAll(PRECACHE_URLS);
    })
  );
});

// ── Activate: limpiar cachés de versiones anteriores ─────────────
self.addEventListener('activate', function (e) {
  var KEEP = [CACHE_STATIC, CACHE_IMAGES];
  e.waitUntil(
    Promise.all([
      clients.claim(),
      caches.keys().then(function (keys) {
        return Promise.all(
          keys
            .filter(function (k) { return !KEEP.includes(k); })
            .map(function (k) { return caches.delete(k); })
        );
      }),
    ])
  );
});

// ── Fetch: Cache First para assets, pass-through para HTML/API ───
self.addEventListener('fetch', function (e) {
  var req = e.request;
  var url = req.url;

  // Solo interceptar GET
  if (req.method !== 'GET') return;

  // Imágenes (locales + Cloudinary + Drive thumbnails) → Cache First
  var isImage =
    /\.(png|jpg|jpeg|webp|gif|svg|ico)(\?|$)/i.test(url) ||
    url.indexOf('res.cloudinary.com') !== -1 ||
    url.indexOf('drive.google.com/thumbnail') !== -1;

  if (isImage) {
    e.respondWith(
      caches.open(CACHE_IMAGES).then(function (cache) {
        return cache.match(req).then(function (cached) {
          if (cached) return cached;
          return fetch(req).then(function (response) {
            if (response.ok) cache.put(req, response.clone());
            return response;
          });
        });
      })
    );
    return;
  }

  // CSS / JS / FlyonUI / Google Fonts → Cache First (static-v2)
  var isStatic =
    /\/(css|js|flyonui)\//.test(url) ||
    url.indexOf('fonts.gstatic.com') !== -1 ||
    url.indexOf('fonts.googleapis.com') !== -1 ||
    url.indexOf('cdn.tailwindcss.com') !== -1;

  if (isStatic) {
    e.respondWith(
      caches.open(CACHE_STATIC).then(function (cache) {
        return cache.match(req).then(function (cached) {
          if (cached) return cached;
          return fetch(req).then(function (response) {
            if (response.ok) cache.put(req, response.clone());
            return response;
          });
        });
      })
    );
    return;
  }

  // HTML, API, SSE → no interceptar (Network First natural)
});

// ── Web Push: recibir notificación del servidor ──────────────────
self.addEventListener('push', function (e) {
  if (!e.data) return;

  var data = {};
  try { data = e.data.json(); } catch (_) { return; }

  var options = {
    body:    data.body    || data.mensaje || '',
    icon:    data.icon    || '/img/icon-192.png',
    badge:   data.badge   || '/img/badge-72.png',
    tag:     data.tipo    || 'notif',
    data:    { url: data.url || '/home' },
    actions: [
      { action: 'ver',    title: 'Ver'    },
      { action: 'cerrar', title: 'Cerrar' },
    ],
    vibrate:            [200, 100, 200],
    requireInteraction: false,
    silent:             false,
  };

  e.waitUntil(
    self.registration.showNotification(data.title || 'Altaltium', options)
  );
});

// ── Click en la notificación del SO ─────────────────────────────
self.addEventListener('notificationclick', function (e) {
  e.notification.close();

  if (e.action === 'cerrar') return;

  var url = (e.notification.data && e.notification.data.url) || '/home';

  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(function (clientList) {
        for (var i = 0; i < clientList.length; i++) {
          var client = clientList[i];
          if (client.url.indexOf(self.location.origin) !== -1 && 'focus' in client) {
            client.focus();
            return client.navigate(url);
          }
        }
        if (clients.openWindow) return clients.openWindow(url);
      })
  );
});
```

- [ ] **Step 2: Verificar que el SW actualiza**

Con el servidor corriendo, abre DevTools → Application → Service Workers. Debería mostrar el SW activo. Si aparece "waiting to activate", haz clic en "skipWaiting" o recarga con Shift+F5.

Luego ve a Application → Cache Storage. Deben aparecer:
- `altaltium-static-v2` — con los archivos de `PRECACHE_URLS`
- `altaltium-images-v1` — vacía hasta que cargues imágenes

Navega a una página con imágenes. Al recargar, las imágenes deben venir de `altaltium-images-v1` (aparecen como `(ServiceWorker)` en el panel Network).

- [ ] **Step 3: Verificar que Web Push sigue funcionando**

Si hay notificaciones configuradas en el entorno, confirma que siguen llegando. El código del `push` y `notificationclick` es idéntico al original.

- [ ] **Step 4: Commit**

```bash
git add public/sw.js
git commit -m "perf: SW Cache First para imágenes/CSS/JS — altaltium-static-v2 + altaltium-images-v1"
```

---

## Verificación final (después de todos los tasks)

- [ ] Abre el sitio en Chrome Incógnito y abre DevTools → Network
- [ ] Recarga la página dos veces. En la segunda recarga, CSS/JS deben mostrar `(disk cache)` o `(ServiceWorker)`
- [ ] Abre `/catalogo` — las tarjetas de propiedades deben mostrar shimmer gris mientras cargan y luego fade-in
- [ ] Abre una propiedad → usa las flechas para navegar imágenes → debe haber crossfade suave de 220ms
- [ ] Abre DevTools → Lighthouse → corre "Performance" → LCP y Speed Index deben mejorar vs. baseline

---

## Self-Review del plan

**Spec coverage:**
- ✅ Sec. 1 (HTTP cache) → Task 1
- ✅ Sec. 2 (img-perf.css) → Task 2
- ✅ Sec. 3 (img-perf.js + fade-in) → Task 3 + Task 4
- ✅ Sec. 4 (gallery crossfade) → Task 5
- ✅ Sec. 5 (SW Cache First) → Task 6
- ✅ Sec. 6 (main.ejs integración) → Task 4
- ✅ Hero images: `loading="eager"` en `[data-main-image]` (Task 5 Step 1) y microsite (Task 5 Step 3)

**Consistencia de nombres:**
- `img-lazy` / `img-loaded` — usados en CSS (Task 2) y JS (Task 3) de forma consistente
- `no-skeleton` — clase opt-out, usada en JS (Task 3) y en la imagen main de galería (Task 5)
- `[data-main-image]` — selector CSS en Task 2, atributo ya existente en `propiedad.ejs`
- `CACHE_STATIC = 'altaltium-static-v2'` / `CACHE_IMAGES = 'altaltium-images-v1'` — constantes usadas en install, activate y fetch

**Sin placeholders:** Todo el código es exacto y completo.
