# Rediseño Reporte de Estimación Comercial — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rediseñar `views/pages/reporte.ejs` con estilo ejecutivo limpio — hero teal degradado, stat-cards blancas con iconos SVG, secciones con cabeceras iconizadas, y modo PDF coherente con el nuevo lenguaje visual.

**Architecture:** Un solo archivo EJS de 1471 líneas con dos modos controlados por `esPdfBool`. El rediseño reemplaza secciones HTML/CSS en cada modo usando Edit con cadenas únicas de anclaje (los comentarios `<!-- HEADER -->`, `<!-- HERO -->`, etc.). Toda la lógica JS, los cálculos server-side de honorarios (`_honorarios`, `_pago1…`), y el sistema PDFShift se mantienen sin cambios.

**Tech Stack:** EJS (Express 5), CSS inline en `<style>`, Tailwind CDN (utilities de layout), SVG icons inline sin dependencias externas.

---

## Archivo modificado

- Modify: `views/pages/reporte.ejs` — único archivo afectado, todas las tareas son ediciones parciales de secciones identificadas por sus comentarios HTML.

---

## Task 1: Actualizar bloque `<style>` del modo web

**Files:**
- Modify: `views/pages/reporte.ejs` (sección `<style>` del modo web, aprox. líneas 538–620)

- [ ] **Step 1: Localizar el bloque `<style>` del modo web**

  En el archivo, busca el bloque que comienza con:
  ```
  <style>
    :root {
      --alt-a: #00cccc;
      --alt-b: #01cbcb;
    }
  ```
  Este bloque termina con `</style>` antes del comentario `<section class=...`.

- [ ] **Step 2: Reemplazar el bloque `<style>` completo**

  Usa Edit para reemplazar desde `<style>` hasta `</style>` (inclusive) con:

  ```html
  <style>
    :root {
      --alt-teal: #008a8a;
      --alt-cyan: #00cccc;
    }

    @page {
      size: A4;
      margin: 8mm 7mm 8mm 7mm;
    }

    #reporte-pdf {
      background: #fff;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }

    .pdf-spinner {
      animation: pdf-spin 0.9s linear infinite;
    }

    @keyframes pdf-spin {
      to { transform: rotate(360deg); }
    }

    .pdf-loading-bar {
      width: 35%;
      animation: pdf-loading-move 1.4s ease-in-out infinite;
    }

    @keyframes pdf-loading-move {
      0%   { transform: translateX(-120%); }
      50%  { transform: translateX(90%); }
      100% { transform: translateX(260%); }
    }

    .pdf-map-shell,
    #map-container {
      break-inside: avoid;
      page-break-inside: avoid;
    }

    /* Hero teal — preserva color en impresión */
    .hero-teal-card {
      background: linear-gradient(135deg, #006666 0%, #008a8a 45%, #00a3a3 100%) !important;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }

    /* Honorarios — borde teal de sección */
    .hon-section-border {
      border: 1.5px solid #b2e0e0;
      border-radius: 24px;
      overflow: hidden;
    }
    .hon-section-header {
      background: #f0fafa;
      border-bottom: 1px solid #b2e0e0;
    }

    @media print {
      .no-print { display: none !important; }

      #reporte-pdf {
        box-shadow: none !important;
        border-radius: 0 !important;
        overflow: visible !important;
      }

      #reporte-pdf > div > section,
      #reporte-pdf header,
      #seccion-honorarios-embebida,
      #layout-honorarios-normal > div,
      #layout-derechos-cobranza > div {
        break-inside: avoid;
        page-break-inside: avoid;
      }

      #reporte-pdf > div > section:last-of-type,
      #reporte-pdf > div > footer {
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
      }

      main.reporte { padding-bottom: 0 !important; }

      #reporte-pdf,
      #reporte-pdf section,
      #reporte-pdf header,
      #reporte-pdf div {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }
    }
  </style>
  ```

- [ ] **Step 3: Verificar que el servidor arranca sin errores**

  ```bash
  node -e "const app = require('./src/app'); console.log('OK')"
  ```
  Esperado: imprime `OK` sin errores.

- [ ] **Step 4: Commit**

  ```bash
  git add views/pages/reporte.ejs
  git commit -m "style: actualizar bloque CSS del reporte — hero-teal-card + hon-section-border"
  ```

---

## Task 2: Rediseñar header del modo web

**Files:**
- Modify: `views/pages/reporte.ejs` (sección `<!-- HEADER -->`)

**Contexto:** El header actual tiene el aside del asesor a la derecha. En el nuevo diseño el asesor se muestra en su propia sección más abajo; el header solo muestra meta-pills de fecha y empresa.

- [ ] **Step 1: Localizar la sección `<!-- HEADER -->`**

  Busca el comentario `<!-- HEADER -->` en el modo web (línea ~627). La sección termina antes de `<!-- HERO -->`.

- [ ] **Step 2: Reemplazar toda la sección `<!-- HEADER -->` hasta (sin incluir) `<!-- HERO -->`**

  Reemplaza desde `<!-- HEADER -->` hasta (sin incluir) `<!-- HERO -->` con:

  ```ejs
        <!-- HEADER -->
        <header class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b border-slate-200 pb-6 mb-0">
          <div class="flex items-center gap-4 min-w-0">
            <div class="h-12 w-12 md:h-14 md:w-14 rounded-2xl bg-slate-50 border border-slate-200 flex items-center justify-center overflow-hidden flex-shrink-0">
              <img
                src="<%= esPdfBool && baseUrl ? (baseUrl + '/img/logos/logo.png') : '/img/logos/logo.png' %>"
                alt="Altaltium"
                class="h-9 md:h-10 w-auto object-contain"
              />
            </div>
            <div class="min-w-0">
              <p class="text-[10px] md:text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
                Altaltium Real Estate Solutions
              </p>
              <h1 class="mt-1 text-xl md:text-2xl font-semibold tracking-tight text-slate-900">
                Reporte de Estimación Comercial
              </h1>
              <p class="mt-1 text-xs text-slate-400">
                Documento ejecutivo de referencia para análisis preliminar de valor.
              </p>
            </div>
          </div>

          <div class="flex gap-3 flex-shrink-0">
            <div class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p class="text-[10px] uppercase tracking-[0.2em] text-slate-400 mb-1">Fecha de emisión</p>
              <p class="font-semibold text-slate-800 text-sm"><%= fechaEmision %></p>
            </div>
            <div class="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p class="text-[10px] uppercase tracking-[0.2em] text-slate-400 mb-1">Empresa</p>
              <p class="font-semibold text-slate-800 text-sm"><%= datos.empresa || 'Altaltium RE' %></p>
            </div>
          </div>
        </header>

  ```

- [ ] **Step 3: Verificar en navegador**

  Arranca el servidor (`node src/server.js`) y abre `/reporte?tipo=casa&valor=$3%2C200%2C000&colonia=Jardines&municipio=BJ&estado=CDMX`.  
  El header debe mostrar: logo + título + 2 meta-pills. Sin aside de asesor a la derecha.

- [ ] **Step 4: Commit**

  ```bash
  git add views/pages/reporte.ejs
  git commit -m "feat: rediseño header modo web — meta-pills, sin aside asesor"
  ```

---

## Task 3: Reemplazar hero oscuro → hero teal + agregar stats row

**Files:**
- Modify: `views/pages/reporte.ejs` (sección `<!-- HERO -->`)

**Contexto:** El hero actual es un div con `bg-gradient-to-br from-slate-900 via-slate-800 to-teal-800`. Se reemplaza por tarjeta teal con gradiente más stats-row de 4 tarjetas blancas debajo.

- [ ] **Step 1: Localizar la sección `<!-- HERO -->`**

  Busca el comentario `<!-- HERO -->`. La sección termina antes del comentario `<!-- RESUMEN + MAPA -->`.

- [ ] **Step 2: Reemplazar toda la sección `<!-- HERO -->` hasta (sin incluir) `<!-- RESUMEN + MAPA -->`**

  ```ejs
        <!-- HERO -->
        <section class="mt-5">
          <div class="hero-teal-card <%= heroRadius %> <%= heroPadding %> text-white shadow-[0_8px_32px_rgba(0,138,138,0.25)]">
            <p class="text-[10px] md:text-[11px] uppercase tracking-[0.22em] text-white/70 font-semibold mb-2">
              Valor estimado del inmueble
            </p>
            <p class="<%= heroTitleClass %> font-black leading-none mb-4">
              <%= valorPrincipal %>
            </p>
            <p class="text-[13px] md:text-[15px] text-white/80 flex items-center gap-2 mb-4">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,.85)" stroke-width="2.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
              <%= direccionCompleta || 'Dirección no disponible' %>
            </p>
            <div class="flex flex-wrap gap-2">
              <span class="inline-flex items-center rounded-full border border-white/25 bg-white/15 px-3 py-1 text-[11px] md:text-xs font-semibold text-white">
                <%= tipoBonito %>
              </span>
              <span class="inline-flex items-center rounded-full border border-white/25 bg-white/15 px-3 py-1 text-[11px] md:text-xs font-semibold text-white">
                <%= interesBonito %>
              </span>
              <span class="inline-flex items-center rounded-full border border-white/25 bg-white/15 px-3 py-1 text-[11px] md:text-xs font-semibold text-white">
                Precio estimado / m²: <%= precioM2 %>
              </span>
            </div>
          </div>
        </section>

        <!-- STATS ROW -->
        <section class="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
          <div class="bg-white border border-slate-200 rounded-[14px] p-4 text-center shadow-sm">
            <div class="mx-auto mb-2 h-8 w-8 rounded-lg bg-teal-50 flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            </div>
            <p class="text-[10px] uppercase tracking-[0.12em] text-slate-400 font-semibold">Recámaras</p>
            <p class="text-[22px] font-black text-teal-600 mt-1"><%= datos.recamaras || '—' %></p>
          </div>
          <div class="bg-white border border-slate-200 rounded-[14px] p-4 text-center shadow-sm">
            <div class="mx-auto mb-2 h-8 w-8 rounded-lg bg-teal-50 flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><path d="M4 12h16M4 12a8 8 0 0116 0"/><path d="M4 12v4a2 2 0 002 2h12a2 2 0 002-2v-4"/><line x1="8" y1="18" x2="8" y2="20"/><line x1="16" y1="18" x2="16" y2="20"/></svg>
            </div>
            <p class="text-[10px] uppercase tracking-[0.12em] text-slate-400 font-semibold">Baños</p>
            <p class="text-[22px] font-black text-teal-600 mt-1"><%= datos.sanitarios || datos.banos || '—' %></p>
          </div>
          <div class="bg-white border border-slate-200 rounded-[14px] p-4 text-center shadow-sm">
            <div class="mx-auto mb-2 h-8 w-8 rounded-lg bg-teal-50 flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
            </div>
            <p class="text-[10px] uppercase tracking-[0.12em] text-slate-400 font-semibold">Construcción</p>
            <p class="text-[22px] font-black text-teal-600 mt-1"><%= datos.construccion || '—' %> <span class="text-sm font-medium text-slate-400">m²</span></p>
          </div>
          <div class="bg-white border border-slate-200 rounded-[14px] p-4 text-center shadow-sm">
            <div class="mx-auto mb-2 h-8 w-8 rounded-lg bg-teal-50 flex items-center justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><path d="M12 22s-8-4.5-8-11.8A8 8 0 0112 2a8 8 0 018 8.2c0 7.3-8 11.8-8 11.8z"/></svg>
            </div>
            <p class="text-[10px] uppercase tracking-[0.12em] text-slate-400 font-semibold">Terreno</p>
            <p class="text-[22px] font-black text-teal-600 mt-1"><%= datos.terreno || '—' %> <span class="text-sm font-medium text-slate-400">m²</span></p>
          </div>
        </section>

  ```

- [ ] **Step 3: Verificar en navegador**

  El hero debe ser verde azulado degradado con el valor grande en blanco. Debajo, 4 tarjetas blancas con iconos teal.

- [ ] **Step 4: Commit**

  ```bash
  git add views/pages/reporte.ejs
  git commit -m "feat: hero teal degradado + stats row con iconos SVG"
  ```

---

## Task 4: Actualizar datos, mapa, características y amenidades con iconos SVG

**Files:**
- Modify: `views/pages/reporte.ejs` (secciones `<!-- RESUMEN + MAPA -->`, `<!-- CARACTERÍSTICAS -->`, `<!-- AMENIDADES -->`)

- [ ] **Step 1: Actualizar cabecera de la sección "Datos del inmueble"**

  Localiza dentro de `<!-- RESUMEN + MAPA -->` el texto exacto:
  ```
                <p class="text-[10px] md:text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700">Datos del inmueble</p>
                <h2 class="mt-1 text-lg md:text-xl font-semibold text-slate-900">Resumen ejecutivo</h2>
  ```
  Reemplaza con:
  ```ejs
                <p class="text-[10px] md:text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700 flex items-center gap-1.5">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                  Datos del inmueble
                </p>
                <h2 class="mt-1 text-lg md:text-xl font-semibold text-slate-900">Resumen ejecutivo</h2>
  ```

- [ ] **Step 2: Actualizar cabecera de la sección "Referencia geográfica"**

  Localiza:
  ```
                <p class="text-[10px] md:text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700">Ubicación</p>
                <h2 class="mt-1 text-lg md:text-xl font-semibold text-slate-900">Referencia geográfica</h2>
  ```
  Reemplaza con:
  ```ejs
                <p class="text-[10px] md:text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700 flex items-center gap-1.5">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
                  Ubicación
                </p>
                <h2 class="mt-1 text-lg md:text-xl font-semibold text-slate-900">Referencia geográfica</h2>
  ```

- [ ] **Step 3: Actualizar cabecera de la sección "Características"**

  Localiza dentro de `<!-- CARACTERÍSTICAS -->`:
  ```
              <p class="text-[10px] md:text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700">Características</p>
              <h2 class="mt-1 text-lg md:text-xl font-semibold text-slate-900">Variables consideradas en la estimación</h2>
  ```
  Reemplaza con:
  ```ejs
              <p class="text-[10px] md:text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700 flex items-center gap-1.5">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>
                Características
              </p>
              <h2 class="mt-1 text-lg md:text-xl font-semibold text-slate-900">Variables consideradas en la estimación</h2>
  ```

- [ ] **Step 4: Agregar iconos SVG a cada tarjeta de características**

  La sección de características tiene 8 tarjetas. Reemplaza el bloque completo del grid `<div class="grid grid-cols-2 md:grid-cols-4 gap-3">` dentro de `<!-- CARACTERÍSTICAS -->` con:

  ```ejs
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div class="rounded-2xl border border-slate-200 bg-slate-50 <%= featureCardPadding %>">
                <div class="h-7 w-7 rounded-lg bg-teal-50 flex items-center justify-center mb-2">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                </div>
                <p class="text-[11px] uppercase tracking-[0.16em] text-slate-400">Recámaras</p>
                <p class="mt-1 <%= featureValue %> font-semibold text-slate-900"><%= datos.recamaras || '—' %></p>
              </div>

              <div class="rounded-2xl border border-slate-200 bg-slate-50 <%= featureCardPadding %>">
                <div class="h-7 w-7 rounded-lg bg-teal-50 flex items-center justify-center mb-2">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><path d="M4 12h16M4 12a8 8 0 0116 0"/><path d="M4 12v4a2 2 0 002 2h12a2 2 0 002-2v-4"/></svg>
                </div>
                <p class="text-[11px] uppercase tracking-[0.16em] text-slate-400">Baños</p>
                <p class="mt-1 <%= featureValue %> font-semibold text-slate-900"><%= datos.sanitarios || datos.banos || '—' %></p>
              </div>

              <div class="rounded-2xl border border-slate-200 bg-slate-50 <%= featureCardPadding %>">
                <div class="h-7 w-7 rounded-lg bg-teal-50 flex items-center justify-center mb-2">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                </div>
                <p class="text-[11px] uppercase tracking-[0.16em] text-slate-400">Medios baños</p>
                <p class="mt-1 <%= featureValue %> font-semibold text-slate-900"><%= (datos.medio_sanitarios ?? '—') %></p>
              </div>

              <div class="rounded-2xl border border-slate-200 bg-slate-50 <%= featureCardPadding %>">
                <div class="h-7 w-7 rounded-lg bg-teal-50 flex items-center justify-center mb-2">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><rect x="1" y="3" width="15" height="13"/><path d="M16 8h4l3 3v5h-7V8z"/></svg>
                </div>
                <p class="text-[11px] uppercase tracking-[0.16em] text-slate-400">Estacionamientos</p>
                <p class="mt-1 <%= featureValue %> font-semibold text-slate-900"><%= datos.estacionamientos || '—' %></p>
              </div>

              <div class="rounded-2xl border border-slate-200 bg-slate-50 <%= featureCardPadding %>">
                <div class="h-7 w-7 rounded-lg bg-teal-50 flex items-center justify-center mb-2">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
                </div>
                <p class="text-[11px] uppercase tracking-[0.16em] text-slate-400">Terreno</p>
                <p class="mt-1 <%= featureValue %> font-semibold text-slate-900"><%= datos.terreno || '—' %> <span class="text-xs font-medium text-slate-500">m²</span></p>
              </div>

              <div class="rounded-2xl border border-slate-200 bg-slate-50 <%= featureCardPadding %>">
                <div class="h-7 w-7 rounded-lg bg-teal-50 flex items-center justify-center mb-2">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>
                </div>
                <p class="text-[11px] uppercase tracking-[0.16em] text-slate-400">Construcción</p>
                <p class="mt-1 <%= featureValue %> font-semibold text-slate-900"><%= datos.construccion || '—' %> <span class="text-xs font-medium text-slate-500">m²</span></p>
              </div>

              <div class="rounded-2xl border border-slate-200 bg-slate-50 <%= featureCardPadding %>">
                <div class="h-7 w-7 rounded-lg bg-teal-50 flex items-center justify-center mb-2">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                </div>
                <p class="text-[11px] uppercase tracking-[0.16em] text-slate-400">Antigüedad</p>
                <p class="mt-1 <%= featureValue %> font-semibold text-slate-900">
                  <%= (datos.antiguedad !== undefined && datos.antiguedad !== '' ? datos.antiguedad : '—') %>
                  <% if (datos.antiguedad !== undefined && datos.antiguedad !== '') { %>
                    <span class="text-xs font-medium text-slate-500">años</span>
                  <% } %>
                </p>
              </div>

              <div class="rounded-2xl border border-slate-200 bg-slate-50 <%= featureCardPadding %>">
                <div class="h-7 w-7 rounded-lg bg-teal-50 flex items-center justify-center mb-2">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
                </div>
                <p class="text-[11px] uppercase tracking-[0.16em] text-slate-400">Conservación</p>
                <p class="mt-1 <%= featureValue %> font-semibold text-slate-900"><%= conservacionBonita %></p>
              </div>
            </div>
  ```

- [ ] **Step 5: Actualizar pills de amenidades con icono SVG**

  Dentro de `<!-- AMENIDADES -->`, localiza:
  ```
                  <% amenidadesBonitas.forEach(a => { %>
                    <span class="inline-flex items-center rounded-full border border-teal-100 bg-teal-50 px-3 py-1.5 text-xs font-medium text-teal-800">
                      <span class="mr-2 text-teal-600">✓</span>
                      <%= a %>
                    </span>
                  <% }) %>
  ```
  Reemplaza con:
  ```ejs
                  <% amenidadesBonitas.forEach(a => { %>
                    <span class="inline-flex items-center rounded-full border border-teal-200 bg-teal-50 px-3 py-1.5 text-xs font-medium text-teal-800">
                      <svg class="mr-1.5 flex-shrink-0" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#008a8a" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                      <%= a %>
                    </span>
                  <% }) %>
  ```

- [ ] **Step 6: Verificar en navegador**

  Cada tarjeta de características debe mostrar su icono teal encima del label. Las amenidades muestran SVG checkmark en lugar del `✓` texto.

- [ ] **Step 7: Commit**

  ```bash
  git add views/pages/reporte.ejs
  git commit -m "feat: iconos SVG en características, amenidades y cabeceras de sección"
  ```

---

## Task 5: Actualizar asesor, notas, honorarios y barra de acción

**Files:**
- Modify: `views/pages/reporte.ejs`

### 5a — Asesor: agregar avatar de iniciales e iconos de contacto

- [ ] **Step 1: Localizar el bloque del asesor**

  Busca (modo web, dentro de la sección `<section class="mt-5 grid grid-cols-1...`):
  ```
            <div class="<%= cardRadius %> border border-slate-200 bg-slate-900 text-white <%= cardPadding %> shadow-sm">
              <p class="text-[10px] md:text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-200 mb-4">
                Datos del asesor responsable
              </p>

              <div class="space-y-3">
  ```

- [ ] **Step 2: Reemplazar el bloque completo de la tarjeta del asesor**

  Reemplaza desde `<div class="<%= cardRadius %> border border-slate-200 bg-slate-900...` hasta el `</div>` que cierra esa tarjeta (antes del `<% } %>` que cierra `if (pdfShowAdvisor)`) con:

  ```ejs
            <div class="<%= cardRadius %> border border-slate-200 bg-slate-900 text-white <%= cardPadding %> shadow-sm">
              <p class="text-[10px] md:text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-200 mb-4 flex items-center gap-1.5">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                Asesor responsable
              </p>

              <div class="flex items-center gap-3 mb-4">
                <div class="h-11 w-11 rounded-full bg-slate-800 border-2 border-slate-700 flex items-center justify-center text-base font-bold text-teal-400 flex-shrink-0">
                  <%= _iniciales %>
                </div>
                <div>
                  <p class="font-semibold text-white text-base"><%= asesorNombre %></p>
                  <p class="text-[11px] text-slate-400 mt-0.5"><%= datos.empresa || 'Altaltium Real Estate Solutions' %></p>
                </div>
              </div>

              <div class="space-y-2.5">
                <div class="flex items-center gap-2.5 text-sm text-slate-300">
                  <svg class="flex-shrink-0" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.81 19.79 19.79 0 01.1 1.18 2 2 0 012.11 0h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.91 7.09a16 16 0 006 6l.45-.45a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>
                  <%= asesorTelefono %>
                </div>
                <div class="flex items-center gap-2.5 text-sm text-slate-300">
                  <svg class="flex-shrink-0" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
                  <span class="break-all"><%= asesorCorreo %></span>
                </div>
              </div>
            </div>
  ```

### 5b — Notas: agregar icono al eyebrow

- [ ] **Step 3: Actualizar eyebrow de la tarjeta de notas**

  Localiza:
  ```
            <p class="text-[10px] md:text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700 mb-4">
              Notas importantes
            </p>
  ```
  Reemplaza con:
  ```ejs
            <p class="text-[10px] md:text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700 mb-4 flex items-center gap-1.5">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              Notas importantes
            </p>
  ```

### 5c — Honorarios: envolver en contenedor con borde teal

- [ ] **Step 4: Agregar clase `hon-section-border` al contenedor de honorarios**

  Localiza la apertura del div de la sección honorarios:
  ```
          <div class="<%= cardRadius %> border border-slate-200 bg-white <%= cardPadding %> shadow-sm">
            <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-5">
              <div>
                <p class="text-[10px] md:text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700">
                  Herramienta comercial
                </p>
  ```
  Reemplaza la primera línea del div con:
  ```ejs
          <div class="hon-section-border bg-white shadow-sm">
            <div class="hon-section-header <%= cardPadding %> flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-0">
              <div>
                <p class="text-[10px] md:text-[11px] font-semibold uppercase tracking-[0.24em] text-teal-700 flex items-center gap-1.5">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>
                  Herramienta comercial
                </p>
  ```
  Luego agrega un `<div class="<%= cardPadding %>">` antes de `<% if (!pdfShowCompactHonorarios) { %>` y ciérralo antes del `</div>` que cierra el `hon-section-border`.

  **Nota para el agente:** Este step modifica la estructura anidada. Lee la sección completa de honorarios (desde `<section id="seccion-honorarios-embebida"` hasta su `</section>`) antes de editar para encontrar los puntos exactos de inserción.

### 5d — Barra de acción: actualizar botón PDF a teal + icono de descarga

- [ ] **Step 5: Actualizar botón "Descargar reporte en PDF"**

  Localiza:
  ```
          <button
            type="button"
            id="btn-descargar-pdf"
            onclick="descargarPDF(this)"
            class="inline-flex items-center justify-center rounded-full bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-70 disabled:cursor-not-allowed"
          >
            Descargar reporte en PDF
          </button>
  ```
  Reemplaza con:
  ```ejs
          <button
            type="button"
            id="btn-descargar-pdf"
            onclick="descargarPDF(this)"
            class="inline-flex items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-semibold text-white transition disabled:opacity-70 disabled:cursor-not-allowed shadow-[0_4px_12px_rgba(0,138,138,0.3)]"
            style="background:#008a8a;"
            onmouseover="this.style.background='#007070'" onmouseout="this.style.background='#008a8a'"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Descargar reporte en PDF
          </button>
  ```

- [ ] **Step 6: Actualizar botón "Volver" — agregar icono de flecha**

  Localiza:
  ```
        <button
          type="button"
          onclick="window.history.back()"
          class="inline-flex items-center justify-center rounded-full border border-slate-300 bg-white px-6 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
        >
          ← Volver a la estimación
        </button>
  ```
  Reemplaza con:
  ```ejs
        <button
          type="button"
          onclick="window.history.back()"
          class="inline-flex items-center justify-center gap-2 rounded-full border border-slate-300 bg-white px-6 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          Volver a la estimación
        </button>
  ```

- [ ] **Step 7: Verificar en navegador**

  - Asesor: avatar de iniciales circulares + iconos de teléfono/correo
  - Sección honorarios: borde teal con cabecera mint
  - Botón PDF: color teal con icono de descarga
  - Botón Volver: icono de flecha

- [ ] **Step 8: Commit**

  ```bash
  git add views/pages/reporte.ejs
  git commit -m "feat: asesor con avatar + iconos, honorarios border teal, botones actualizados"
  ```

---

## Task 6: Rediseñar bloque de modo PDF completo

**Files:**
- Modify: `views/pages/reporte.ejs` (bloque `<% if (esPdfBool) { %>` hasta `<% } else { %>`, aprox. líneas 178–509)

**Contexto:** Reemplaza todo el bloque del modo PDF (estilos CSS del PDF + HTML del layout) con un diseño coherente al nuevo lenguaje visual: header, barra de valor teal, y layouts de 2/3 columnas.

- [ ] **Step 1: Localizar el bloque completo del modo PDF**

  El bloque comienza en:
  ```
    <% if (esPdfBool) { %>
    <%/* ═══════════════════════════════════════════════════════════
        NUEVO LAYOUT PDF — A4 portrait, paleta #008a8a
  ```
  Y termina en la línea que contiene `<% } else { %>` (el else del modo web).

- [ ] **Step 2: Reemplazar todo el bloque del modo PDF**

  Reemplaza desde `<% if (esPdfBool) { %>` hasta (sin incluir) `<% } else { %>` con:

  ```ejs
    <% if (esPdfBool) { %>
    <style>
      @page { size: A4; margin: 8mm 10mm; }
      .pdf-root {
        font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
        color: #0f172a; background: #ffffff;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        font-size: 11px; line-height: 1.4;
      }
      .pdf-section { break-inside: avoid; page-break-inside: avoid; }
      .pdf-divider { height: 2px; background: #008a8a; border: none; margin: 0; }
      .pdf-label { font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; color: #6b7280; }
      .pdf-teal { color: #008a8a; }
      .pdf-pill {
        display: inline-block; background: #f0fafa; border: 1px solid #b2e0e0;
        color: #007070; font-size: 9px; font-weight: 600;
        padding: 2px 8px; border-radius: 999px;
        text-transform: uppercase; letter-spacing: 0.08em;
      }
      .pdf-card {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px;
        break-inside: avoid; page-break-inside: avoid;
      }
      .pdf-avatar {
        width: 32px; height: 32px; min-width: 32px;
        background: #f0fafa; border: 1.5px solid #b2e0e0; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 12px; font-weight: 700; color: #008a8a;
      }
      .pdf-total-bar {
        background: #008a8a; border-radius: 6px; color: #ffffff;
        break-inside: avoid; page-break-inside: avoid;
      }
      .pdf-map-img { width: 100%; object-fit: cover; border-radius: 6px; display: block; border: 1px solid #e2e8f0; }
      .pdf-map-fallback {
        background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        text-align: center; padding: 8px;
      }
      .pdf-table { width: 100%; border-collapse: collapse; font-size: 10.5px; }
      .pdf-table td { padding: 3.5px 0; }
      .pdf-table tr:not(:last-child) td { border-bottom: 1px solid #f1f5f9; }
      .pdf-section-title {
        font-size: 10px; font-weight: 700; text-transform: uppercase;
        letter-spacing: 0.1em; color: #008a8a;
        margin-bottom: 5px; padding-bottom: 3px; border-bottom: 1.5px solid #f0fafa;
      }
      /* Hero teal para PDF */
      .pdf-hero {
        background: linear-gradient(135deg, #006666 0%, #008a8a 45%, #00a3a3 100%) !important;
        border-radius: 8px; color: #ffffff; padding: 12px 14px; margin-bottom: 10px;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }
      .pdf-hero-val { font-size: 22px; font-weight: 900; line-height: 1.1; color: #fff; }
      .pdf-hero-lbl { font-size: 8px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.14em; color: rgba(255,255,255,.75); margin-bottom: 3px; }
      .pdf-stat-card {
        background: #fff; border: 1px solid #e2e8f0; border-radius: 6px;
        padding: 6px 8px; text-align: center;
        break-inside: avoid;
      }
      .pdf-stat-val { font-size: 15px; font-weight: 800; color: #008a8a; margin-top: 1px; }
    </style>

    <div class="pdf-root">

      <%/* ── HEADER ── */%>
      <header class="pdf-section" style="display:flex;align-items:flex-start;justify-content:space-between;padding-bottom:10px;margin-bottom:8px;">
        <div style="display:flex;align-items:center;gap:10px;">
          <img src="<%= baseUrl %>/img/logos/logo.png" alt="Logo"
            style="height:36px;width:auto;object-fit:contain;"
            onerror="this.style.display='none'" />
          <div>
            <div style="font-size:13px;font-weight:700;color:#0f172a;"><%= datos.empresa || 'Altaltium Real Estate Solutions' %></div>
            <div style="font-size:9px;color:#6b7280;margin-top:1px;">Reporte de estimación comercial · Documento ejecutivo</div>
          </div>
        </div>
        <div style="text-align:right;flex-shrink:0;">
          <div class="pdf-label">Fecha de emisión</div>
          <div style="font-size:11px;font-weight:600;color:#0f172a;margin-top:2px;"><%= fechaEmision %></div>
        </div>
      </header>
      <hr class="pdf-divider" style="margin-bottom:10px;" />

      <%/* ── HERO TEAL ── */%>
      <div class="pdf-hero pdf-section" style="display:flex;align-items:flex-start;justify-content:space-between;gap:10px;">
        <div style="min-width:0;">
          <div class="pdf-hero-lbl">Valor estimado del inmueble</div>
          <div class="pdf-hero-val"><%= valorPrincipal %></div>
          <div style="font-size:9px;color:rgba(255,255,255,.8);margin-top:4px;display:flex;align-items:center;gap:3px;">
            <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,.85)" stroke-width="2.5"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>
            <%= direccionCompleta || 'Dirección no disponible' %>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;gap:3px;align-items:flex-end;flex-shrink:0;">
          <span class="pdf-pill"><%= tipoBonito %></span>
          <span class="pdf-pill"><%= interesBonito %></span>
        </div>
      </div>

      <%/* ── STATS ROW ── */%>
      <div class="pdf-section" style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-bottom:10px;">
        <div class="pdf-stat-card">
          <div class="pdf-label">Recámaras</div>
          <div class="pdf-stat-val"><%= datos.recamaras || '—' %></div>
        </div>
        <div class="pdf-stat-card">
          <div class="pdf-label">Baños</div>
          <div class="pdf-stat-val"><%= datos.sanitarios || datos.banos || '—' %></div>
        </div>
        <div class="pdf-stat-card">
          <div class="pdf-label">Construcción</div>
          <div class="pdf-stat-val"><%= datos.construccion || '—' %> <span style="font-size:9px;font-weight:500;color:#6b7280;">m²</span></div>
        </div>
        <div class="pdf-stat-card">
          <div class="pdf-label">Terreno</div>
          <div class="pdf-stat-val"><%= datos.terreno || '—' %> <span style="font-size:9px;font-weight:500;color:#6b7280;">m²</span></div>
        </div>
      </div>

      <%/* ── CUERPO ── */%>
      <% if (includeHonorarios) { %>

      <%/* — 2 columnas: izquierda inmueble+mapa+asesor | derecha honorarios — */%>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;align-items:start;">

        <%/* COL IZQUIERDA */%>
        <div style="display:flex;flex-direction:column;gap:8px;">

          <div class="pdf-card pdf-section" style="padding:10px 12px;">
            <div class="pdf-label pdf-teal" style="margin-bottom:6px;">Datos del inmueble</div>
            <table class="pdf-table">
              <tr><td style="color:#6b7280;">Tipo</td><td style="font-weight:600;text-align:right;"><%= tipoBonito %></td></tr>
              <tr><td style="color:#6b7280;">Segmento</td><td style="font-weight:600;text-align:right;"><%= interesBonito %></td></tr>
              <tr><td style="color:#6b7280;">Colonia</td><td style="font-weight:600;text-align:right;"><%= datos.colonia || 'N/D' %></td></tr>
              <tr><td style="color:#6b7280;">Municipio / Alcaldía</td><td style="font-weight:600;text-align:right;"><%= datos.municipio || 'N/D' %></td></tr>
              <tr><td style="color:#6b7280;">Estado</td><td style="font-weight:600;text-align:right;"><%= datos.estado || 'N/D' %></td></tr>
              <tr><td style="color:#6b7280;">Código postal</td><td style="font-weight:600;text-align:right;"><%= datos.cp || 'N/D' %></td></tr>
            </table>
          </div>

          <div class="pdf-card pdf-section" style="padding:8px 10px;">
            <div class="pdf-label pdf-teal" style="margin-bottom:5px;">Ubicación geográfica</div>
            <% if (googleMapsKey && _pdfAddr.trim()) { %>
              <img class="pdf-map-img" style="height:80px;"
                src="https://maps.googleapis.com/maps/api/staticmap?center=<%= encodeURIComponent(_pdfAddr) %>&zoom=16&size=600x150&maptype=roadmap&markers=color:0x008a8a%7C<%= encodeURIComponent(_pdfAddr) %>&key=<%= googleMapsKey %>"
                alt="Mapa de ubicación"
                onerror="this.style.display='none';this.nextElementSibling.style.display='flex';" />
              <div class="pdf-map-fallback" style="display:none;height:60px;">
                <div class="pdf-label pdf-teal">Ubicación de referencia</div>
                <div style="font-size:10px;color:#1e293b;margin-top:2px;"><%= _pdfAddr.replace(', Mexico','') %></div>
              </div>
            <% } else { %>
              <div class="pdf-map-fallback" style="height:60px;">
                <div class="pdf-label pdf-teal">Ubicación de referencia</div>
                <div style="font-size:10px;color:#1e293b;margin-top:2px;"><%= _pdfAddr.replace(', Mexico','') || direccionCompleta %></div>
              </div>
            <% } %>
          </div>

          <div class="pdf-card pdf-section" style="padding:10px 12px;">
            <div class="pdf-label pdf-teal" style="margin-bottom:7px;">Asesor responsable</div>
            <div style="display:flex;align-items:center;gap:10px;">
              <div class="pdf-avatar"><%- _iniciales %></div>
              <div style="flex:1;min-width:0;">
                <div style="font-size:12px;font-weight:700;color:#0f172a;"><%= asesorNombre %></div>
                <div style="font-size:10px;color:#475569;margin-top:1px;"><%= datos.empresa || 'Altaltium Real Estate Solutions' %></div>
                <div style="font-size:10px;color:#64748b;margin-top:2px;"><%= asesorTelefono %> &nbsp;·&nbsp; <%= asesorCorreo %></div>
              </div>
            </div>
          </div>

        </div><%/* /COL IZQUIERDA */%>

        <%/* COL DERECHA — Honorarios */%>
        <div class="pdf-card pdf-section" style="padding:12px;display:flex;flex-direction:column;gap:10px;">

          <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
            <div class="pdf-label pdf-teal">Calculadora de honorarios</div>
            <span style="background:#f0fafa;border:1.5px solid #008a8a;color:#007070;font-size:9px;font-weight:700;padding:2px 8px;border-radius:999px;text-transform:uppercase;letter-spacing:0.1em;white-space:nowrap;"><%= _tipoLabel %></span>
          </div>

          <div>
            <div class="pdf-section-title">Descripción</div>
            <table class="pdf-table">
              <tr><td style="color:#6b7280;">Valor comercial</td><td style="font-weight:600;text-align:right;"><%= _fmt(_val) %></td></tr>
              <tr><td style="color:#6b7280;">Valor judicial</td><td style="font-weight:600;text-align:right;"><%= _fmt(_valorJudicial) %></td></tr>
              <tr><td style="color:#6b7280;">Honorarios</td><td style="font-weight:700;text-align:right;color:#008a8a;"><%= _fmt(_honorarios) %></td></tr>
              <tr><td style="color:#6b7280;">Cesión de derechos</td><td style="font-weight:600;text-align:right;"><%= _fmt(_pago2) %></td></tr>
            </table>
          </div>

          <div>
            <div class="pdf-section-title">Parcialidades</div>
            <table class="pdf-table">
              <tr>
                <td><div style="font-weight:500;color:#0f172a;">1er Pago (75%)</div><div style="font-size:9px;color:#94a3b8;">Propuesta Legal</div></td>
                <td style="font-weight:600;text-align:right;color:#0f172a;vertical-align:middle;"><%= _fmt(_pago1) %></td>
              </tr>
              <tr>
                <td><div style="font-weight:500;color:#0f172a;">2do Pago</div><div style="font-size:9px;color:#94a3b8;">Cesión de Derechos</div></td>
                <td style="font-weight:600;text-align:right;color:#0f172a;vertical-align:middle;"><%= _fmt(_pago2) %></td>
              </tr>
              <tr>
                <td><div style="font-weight:500;color:#0f172a;">3er Pago (25%)</div><div style="font-size:9px;color:#94a3b8;">Entrega</div></td>
                <td style="font-weight:600;text-align:right;color:#0f172a;vertical-align:middle;"><%= _fmt(_pago3) %></td>
              </tr>
            </table>
          </div>

          <div class="pdf-total-bar" style="padding:8px 12px;display:flex;align-items:center;justify-content:space-between;">
            <span style="font-size:11px;font-weight:600;">Precio Total Estimado</span>
            <span style="font-size:13px;font-weight:800;"><%= _fmt(_precioTotal) %></span>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
            <div style="background:#f0fafa;border:1px solid #b2e0e0;border-radius:6px;padding:7px 10px;text-align:center;">
              <div class="pdf-label pdf-teal">Ganancia</div>
              <div style="font-size:16px;font-weight:800;color:#008a8a;margin-top:2px;"><%= _pct(_ganancia) %></div>
            </div>
            <div style="background:#f0fafa;border:1px solid #b2e0e0;border-radius:6px;padding:7px 10px;text-align:center;">
              <div class="pdf-label pdf-teal">Costo de compra</div>
              <div style="font-size:16px;font-weight:800;color:#008a8a;margin-top:2px;"><%= _pct(_costoCompra) %></div>
            </div>
          </div>

        </div><%/* /COL DERECHA */%>

      </div><%/* /2 columnas */%>

      <% } else { %>

      <%/* — 3 columnas: datos+asesor | mapa grande | extras — */%>
      <div style="display:grid;grid-template-columns:1fr 1.2fr 0.8fr;gap:10px;align-items:start;">

        <%/* COL 1 */%>
        <div style="display:flex;flex-direction:column;gap:8px;">

          <div class="pdf-card pdf-section" style="padding:10px 12px;">
            <div class="pdf-label pdf-teal" style="margin-bottom:6px;">Datos del inmueble</div>
            <table class="pdf-table">
              <tr><td style="color:#6b7280;">Tipo</td><td style="font-weight:600;text-align:right;"><%= tipoBonito %></td></tr>
              <tr><td style="color:#6b7280;">Segmento</td><td style="font-weight:600;text-align:right;"><%= interesBonito %></td></tr>
              <tr><td style="color:#6b7280;">Colonia</td><td style="font-weight:600;text-align:right;"><%= datos.colonia || 'N/D' %></td></tr>
              <tr><td style="color:#6b7280;">Municipio</td><td style="font-weight:600;text-align:right;"><%= datos.municipio || 'N/D' %></td></tr>
              <tr><td style="color:#6b7280;">Estado</td><td style="font-weight:600;text-align:right;"><%= datos.estado || 'N/D' %></td></tr>
              <tr><td style="color:#6b7280;">CP</td><td style="font-weight:600;text-align:right;"><%= datos.cp || 'N/D' %></td></tr>
            </table>
          </div>

          <div class="pdf-card pdf-section" style="padding:10px 12px;">
            <div class="pdf-label pdf-teal" style="margin-bottom:7px;">Asesor responsable</div>
            <div style="display:flex;align-items:center;gap:8px;">
              <div class="pdf-avatar"><%- _iniciales %></div>
              <div style="flex:1;min-width:0;">
                <div style="font-size:11.5px;font-weight:700;color:#0f172a;"><%= asesorNombre %></div>
                <div style="font-size:9.5px;color:#475569;"><%= datos.empresa || 'Altaltium Real Estate Solutions' %></div>
                <div style="font-size:9.5px;color:#64748b;margin-top:2px;"><%= asesorTelefono %></div>
                <div style="font-size:9.5px;color:#64748b;"><%= asesorCorreo %></div>
              </div>
            </div>
          </div>

        </div><%/* /COL 1 */%>

        <%/* COL 2: Mapa grande */%>
        <div class="pdf-card pdf-section" style="padding:10px;">
          <div class="pdf-label pdf-teal" style="margin-bottom:6px;">Ubicación geográfica</div>
          <% if (googleMapsKey && _pdfAddr.trim()) { %>
            <img class="pdf-map-img" style="height:200px;"
              src="https://maps.googleapis.com/maps/api/staticmap?center=<%= encodeURIComponent(_pdfAddr) %>&zoom=16&size=600x400&maptype=roadmap&markers=color:0x008a8a%7C<%= encodeURIComponent(_pdfAddr) %>&key=<%= googleMapsKey %>"
              alt="Mapa de ubicación"
              onerror="this.style.display='none';this.nextElementSibling.style.display='flex';" />
            <div class="pdf-map-fallback" style="display:none;height:120px;">
              <div class="pdf-label pdf-teal">Ubicación de referencia</div>
              <div style="font-size:10.5px;color:#1e293b;margin-top:3px;"><%= _pdfAddr.replace(', Mexico','') %></div>
            </div>
          <% } else { %>
            <div class="pdf-map-fallback" style="height:120px;">
              <div class="pdf-label pdf-teal">Ubicación de referencia</div>
              <div style="font-size:10.5px;color:#1e293b;margin-top:3px;"><%= _pdfAddr.replace(', Mexico','') || direccionCompleta %></div>
            </div>
          <% } %>
        </div><%/* /COL 2 */%>

        <%/* COL 3: Extras */%>
        <div style="display:flex;flex-direction:column;gap:8px;">
          <div class="pdf-card pdf-section" style="padding:12px;background:#f0fafa;border-color:#b2e0e0;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#008a8a;margin-bottom:6px;">Referencia comercial preliminar</div>
            <div style="font-size:9.5px;color:#475569;line-height:1.5;">Esta estimación no constituye un avalúo profesional ni una oferta vinculante.</div>
          </div>
          <div class="pdf-card pdf-section" style="padding:10px 12px;">
            <div class="pdf-label pdf-teal" style="margin-bottom:4px;">Precio por m²</div>
            <div style="font-size:16px;font-weight:800;color:#008a8a;"><%= precioM2 %></div>
            <div style="font-size:9px;color:#94a3b8;margin-top:2px;">Referencia estimada</div>
          </div>
          <div class="pdf-card pdf-section" style="padding:10px 12px;">
            <div class="pdf-label pdf-teal" style="margin-bottom:4px;">Conservación</div>
            <div style="font-size:11.5px;font-weight:600;color:#0f172a;"><%= conservacionBonita %></div>
          </div>
        </div><%/* /COL 3 */%>

      </div><%/* /3 columnas */%>

      <% } %><%/* /if includeHonorarios */%>

      <%/* ── FOOTER ── */%>
      <div class="pdf-section" style="margin-top:10px;padding-top:8px;border-top:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:flex-end;">
        <div style="font-size:8.5px;color:#94a3b8;max-width:70%;line-height:1.4;">
          La presente estimación constituye una referencia comercial preliminar. No sustituye un avalúo profesional emitido por perito valuador, ni representa una oferta vinculante de compra, venta, financiamiento o comercialización.
        </div>
        <div style="font-size:9px;font-weight:600;color:#008a8a;text-align:right;flex-shrink:0;">
          © <%= datos.empresa || 'Altaltium Real Estate Solutions' %> <%= new Date().getFullYear() %>
        </div>
      </div>

    </div><%/* /pdf-root */%>

  ```

- [ ] **Step 3: Verificar que el servidor arranca sin errores EJS**

  ```bash
  node -e "const app = require('./src/app'); console.log('OK')"
  ```
  Esperado: `OK` sin errores de template.

- [ ] **Step 4: Verificar PDF descargado**

  1. Arranca servidor: `node src/server.js`
  2. Ve a `/estimaciones`, llena el wizard con datos de prueba, llega al reporte
  3. Presiona "Descargar reporte en PDF"
  4. Verifica que el PDF muestre: header con logo, barra teal 2px, hero teal con valor, stats row de 4 tarjetas, y columnas de datos/mapa

- [ ] **Step 5: Commit**

  ```bash
  git add views/pages/reporte.ejs
  git commit -m "feat: rediseño completo modo PDF — hero teal, stats row, layout coherente con modo web"
  ```

---

## Verificación final

- [ ] Abrir `/estimaciones` → llenar wizard → verificar `/reporte` se ve con hero teal, stats row, iconos en características
- [ ] Presionar "Calcular honorarios" → sección aparece con borde teal, inputs y resultados
- [ ] Presionar "Descargar reporte en PDF" → PDF A4 portrait con hero teal, stats y columnas de datos
- [ ] Verificar PDF con honorarios: llenar cesión de derechos → descargar → columna derecha muestra calculadora
- [ ] Verificar en móvil (DevTools): layout responsive, sin overflow horizontal
- [ ] Commit final si hay ajustes menores pendientes

---

## Notas para el agente implementador

1. **Lee el archivo completo antes de editar** — el archivo tiene 1471 líneas con EJS. Los comentarios HTML (`<!-- HEADER -->`, `<!-- HERO -->`, etc.) son los anclas de referencia para cada sección.
2. **No cambies** la lógica JS (funciones `descargarPDF`, `abrirHonorariosEmbebidos`, `honorariosApi`), los cálculos EJS de honorarios (`_honorarios`, `_val`, `_pago1…`), ni las variables de modo (`esPdfBool`, `shellMaxWidth`, `cardRadius`, etc.).
3. **El `_iniciales` ya existe** definido en el bloque de helpers EJS (líneas ~164-167). No lo redefinas.
4. **Task 5c (honorarios)** requiere leer la sección completa antes de editar — la estructura anidada de divs es compleja. Usa Edit con old_string suficientemente largo para ser único.
5. Si un Edit falla por old_string no único, usa más contexto circundante como parte del old_string.
