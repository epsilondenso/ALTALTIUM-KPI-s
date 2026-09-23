# Estudio de Mercado — Fichas Outlet Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar sección "Estudio de Mercado" a las fichas outlet — hasta 5 comparables obtenidos automáticamente de Mercado Libre o capturados manualmente, gestionados desde el panel admin y renderizados como nueva página en el PDF.

**Architecture:** Nueva tabla `ficha_estudio_mercado` almacena los comparables por propiedad. Un servicio llama la API pública de Mercado Libre (sin auth). El panel admin de fichas gana un modal para gestionar comparables. El template PDF gana una nueva página que solo aparece si hay comparables guardados.

**Tech Stack:** Node.js v24 (fetch nativo), Express v5, PostgreSQL, EJS, Tailwind CDN, Mercado Libre public REST API

---

## Mapa de archivos

| Archivo | Acción | Propósito |
|---------|--------|-----------|
| DB migration | Ejecutar SQL | Nueva tabla `ficha_estudio_mercado` |
| `src/services/mercadolibre.service.js` | **Crear** | Búsqueda de comparables en ML API |
| `src/services/fichas.service.js` | **Modificar** | +2 funciones de BD: get y guardar comparables |
| `src/controllers/admin/fichas.controller.js` | **Modificar** | +3 endpoints + pasar `estudioMercado` al template |
| `src/routes/admin.fichas.routes.js` | **Modificar** | +3 rutas |
| `views/admin/fichas/index.ejs` | **Modificar** | Botón "Estudio" en tabla + modal completo |
| `views/admin/fichas/template-outlet.ejs` | **Modificar** | Nueva página 4 (condicional) |

---

## Task 1: Base de datos — tabla ficha_estudio_mercado

**Files:**
- Ejecutar SQL en la BD local (psql, DBeaver, o cualquier cliente)

- [ ] **Step 1: Crear la tabla**

Ejecutar este SQL en la base de datos local:

```sql
CREATE TABLE IF NOT EXISTS ficha_estudio_mercado (
  id            SERIAL PRIMARY KEY,
  propiedad_id  INT NOT NULL,
  orden         SMALLINT NOT NULL DEFAULT 1,
  portal        VARCHAR(80),
  titulo        TEXT,
  url           TEXT,
  precio        NUMERIC(14,2),
  area_m2       NUMERIC(10,2),
  recamaras     SMALLINT,
  sanitarios    SMALLINT,
  imagen_url    TEXT,
  notas         TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fem_propiedad ON ficha_estudio_mercado(propiedad_id);
```

- [ ] **Step 2: Verificar la tabla**

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'ficha_estudio_mercado'
ORDER BY ordinal_position;
```

Esperado: 13 columnas listadas (id, propiedad_id, orden, portal, titulo, url, precio, area_m2, recamaras, sanitarios, imagen_url, notas, created_at).

- [ ] **Step 3: Commit**

```bash
git add .
git commit -m "feat: crear tabla ficha_estudio_mercado para comparables de mercado"
```

---

## Task 2: Servicio Mercado Libre

**Files:**
- Create: `src/services/mercadolibre.service.js`

- [ ] **Step 1: Crear el archivo**

`src/services/mercadolibre.service.js`:

```javascript
'use strict';

const ML_BASE = 'https://api.mercadolibre.com';

const CATEGORY_MAP = {
  'Casa':            'MLM1472',
  'Departamento':    'MLM1473',
  'Terreno':         'MLM1500',
  'Local Comercial': 'MLM1571',
  'Bodega':          'MLM1499',
};

exports.buscarComparables = async function (municipio, estado, tipo, precioRef) {
  try {
    const cat = CATEGORY_MAP[tipo] || 'MLM1459';
    const q   = [municipio, estado].filter(Boolean).join(' ');
    const url = `${ML_BASE}/sites/MLM/search?category=${cat}&q=${encodeURIComponent(q)}&limit=6`;

    const res  = await fetch(url, { signal: AbortSignal.timeout(8000) });
    if (!res.ok) throw new Error(`ML API respondió ${res.status}`);
    const data = await res.json();

    return (data.results || []).slice(0, 6).map(item => {
      const attrs = {};
      (item.attributes || []).forEach(a => {
        attrs[a.id] = a.value_name || (a.value_struct ? a.value_struct.number : null);
      });
      return {
        portal:     'Mercado Libre',
        titulo:     item.title || '',
        url:        item.permalink || '',
        precio:     item.price || null,
        area_m2:    parseFloat(attrs['SURFACE_TOTAL']) || parseFloat(attrs['TOTAL_AREA']) || null,
        recamaras:  parseInt(attrs['BEDROOMS'])        || null,
        sanitarios: parseInt(attrs['FULL_BATHROOMS'])  || parseInt(attrs['BATHROOMS']) || null,
        imagen_url: (item.thumbnail || '').replace('I.jpg', 'O.jpg'),
        notas:      null,
      };
    });
  } catch (err) {
    console.error('[ML] Error buscando comparables:', err.message);
    return [];
  }
};
```

- [ ] **Step 2: Verificar que la API responde**

Con el servidor corriendo, abrir en navegador:
`https://api.mercadolibre.com/sites/MLM/search?category=MLM1472&q=hermosillo+sonora&limit=3`

Esperado: JSON con campo `results` conteniendo propiedades. Si aparecen resultados, el servicio funcionará igual.

- [ ] **Step 3: Commit**

```bash
git add src/services/mercadolibre.service.js
git commit -m "feat: servicio buscarComparables via Mercado Libre public API"
```

---

## Task 3: Queries en fichas.service.js

**Files:**
- Modify: `src/services/fichas.service.js`

- [ ] **Step 1: Agregar las dos funciones al final del archivo**

Al final de `src/services/fichas.service.js` (después de la última línea `exports.localImageToBase64Pub = localImageToBase64;`), agregar:

```javascript
// ── Estudio de Mercado ────────────────────────────────────────────────────

exports.getEstudioMercado = async function (propiedadId) {
  const { rows } = await pool.query(
    `SELECT id, orden, portal, titulo, url, precio,
            area_m2, recamaras, sanitarios, imagen_url, notas
     FROM ficha_estudio_mercado
     WHERE propiedad_id = $1
     ORDER BY orden ASC`,
    [propiedadId]
  );
  return rows;
};

exports.guardarEstudioMercado = async function (propiedadId, comparables) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await client.query(
      'DELETE FROM ficha_estudio_mercado WHERE propiedad_id = $1',
      [propiedadId]
    );
    for (let i = 0; i < comparables.length; i++) {
      const c = comparables[i];
      if (!c.titulo && !c.url) continue;
      await client.query(
        `INSERT INTO ficha_estudio_mercado
           (propiedad_id, orden, portal, titulo, url, precio,
            area_m2, recamaras, sanitarios, imagen_url, notas)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)`,
        [
          propiedadId,
          i + 1,
          c.portal     ? String(c.portal).slice(0, 80)   : null,
          c.titulo     ? String(c.titulo).slice(0, 500)   : null,
          c.url        ? String(c.url).slice(0, 1000)     : null,
          c.precio     ? parseFloat(c.precio)             : null,
          c.area_m2    ? parseFloat(c.area_m2)            : null,
          c.recamaras  ? parseInt(c.recamaras)            : null,
          c.sanitarios ? parseInt(c.sanitarios)           : null,
          c.imagen_url ? String(c.imagen_url).slice(0, 1000) : null,
          c.notas      ? String(c.notas).slice(0, 500)   : null,
        ]
      );
    }
    await client.query('COMMIT');
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
};
```

- [ ] **Step 2: Commit**

```bash
git add src/services/fichas.service.js
git commit -m "feat: queries getEstudioMercado y guardarEstudioMercado"
```

---

## Task 4: Controller y Routes

**Files:**
- Modify: `src/controllers/admin/fichas.controller.js`
- Modify: `src/routes/admin.fichas.routes.js`

- [ ] **Step 1: Agregar require de mlService al controller**

En `src/controllers/admin/fichas.controller.js`, después de las 3 líneas de `require` existentes al inicio del archivo:

```javascript
const mlService   = require('../../services/mercadolibre.service');
```

- [ ] **Step 2: Pasar estudioMercado en previewOutlet**

En la función `exports.previewOutlet`, reemplazar:

```javascript
    return res.render('admin/fichas/template-outlet', {
      layout: false, propiedad, assets,
      coordenadas, numeroExterior, precioFormateado, googleMapsKey,
    });
```

Por:

```javascript
    const estudioMercado = await fichasService.getEstudioMercado(req.params.id);

    return res.render('admin/fichas/template-outlet', {
      layout: false, propiedad, assets,
      coordenadas, numeroExterior, precioFormateado, googleMapsKey,
      estudioMercado,
    });
```

- [ ] **Step 3: Pasar estudioMercado en generarPdfOutlet**

En la función `exports.generarPdfOutlet`, después de la línea:

```javascript
    const googleMapsKey    = process.env.GOOGLE_MAPS_API_KEY || '';
```

Agregar:

```javascript
    const estudioMercado = await fichasService.getEstudioMercado(req.params.id);
```

Y en el `req.app.render(...)` dentro de `generarPdfOutlet`, reemplazar:

```javascript
      req.app.render('admin/fichas/template-outlet', {
        layout: false, propiedad, assets,
        coordenadas, numeroExterior, precioFormateado, googleMapsKey,
      }, (err, rendered) => {
```

Por:

```javascript
      req.app.render('admin/fichas/template-outlet', {
        layout: false, propiedad, assets,
        coordenadas, numeroExterior, precioFormateado, googleMapsKey,
        estudioMercado,
      }, (err, rendered) => {
```

- [ ] **Step 4: Agregar los 3 nuevos endpoints al final del controller**

Al final de `src/controllers/admin/fichas.controller.js`:

```javascript
// ── Estudio de Mercado ────────────────────────────────────────────────────

exports.getEstudioMercado = async (req, res) => {
  try {
    const comparables = await fichasService.getEstudioMercado(req.params.id);
    return res.json({ ok: true, comparables });
  } catch (err) {
    console.error('[fichas] getEstudioMercado:', err.message);
    return res.status(500).json({ ok: false, error: err.message });
  }
};

exports.buscarSugerenciasML = async (req, res) => {
  try {
    const propiedad = await fichasService.getOutletParaFicha(req.params.id);
    if (!propiedad) return res.status(404).json({ ok: false, error: 'No encontrada' });
    const sugerencias = await mlService.buscarComparables(
      propiedad.municipio,
      propiedad.estado,
      propiedad.tipo,
      propiedad.costo_total
    );
    return res.json({ ok: true, sugerencias });
  } catch (err) {
    console.error('[fichas] buscarSugerenciasML:', err.message);
    return res.status(500).json({ ok: false, error: err.message });
  }
};

exports.guardarEstudioMercado = async (req, res) => {
  try {
    const { comparables } = req.body;
    if (!Array.isArray(comparables)) {
      return res.status(400).json({ ok: false, error: 'comparables debe ser array' });
    }
    await fichasService.guardarEstudioMercado(req.params.id, comparables.slice(0, 5));
    return res.json({ ok: true });
  } catch (err) {
    console.error('[fichas] guardarEstudioMercado:', err.message);
    return res.status(500).json({ ok: false, error: err.message });
  }
};
```

- [ ] **Step 5: Agregar las 3 rutas**

En `src/routes/admin.fichas.routes.js`, antes de `module.exports = router;`:

```javascript
router.get('/admin/fichas/outlet/:id/estudio-mercado',             authAdmin, ctrl.getEstudioMercado);
router.get('/admin/fichas/outlet/:id/estudio-mercado/sugerencias', authAdmin, ctrl.buscarSugerenciasML);
router.post('/admin/fichas/outlet/:id/estudio-mercado',            authAdmin, ctrl.guardarEstudioMercado);
```

- [ ] **Step 6: Verificar rutas**

Con el servidor corriendo (`npm run dev`), abrir:
`http://localhost:3000/admin/fichas/outlet/1/estudio-mercado`

Esperado: `{"ok":true,"comparables":[]}` (vacío, tabla sin datos aún).

- [ ] **Step 7: Commit**

```bash
git add src/controllers/admin/fichas.controller.js src/routes/admin.fichas.routes.js
git commit -m "feat: endpoints estudio-mercado y sugerencias ML en fichas controller"
```

---

## Task 5: UI Admin — Modal de Estudio de Mercado

**Files:**
- Modify: `views/admin/fichas/index.ejs`

- [ ] **Step 1: Agregar botón "Estudio" en la tabla**

Buscar el bloque de botones en la fila outlet (alrededor de donde aparece `abrirModalFicha`):

```html
                  <button onclick="abrirModalFicha(<%= p.id %>, '<%= (p.folio || '').replace(/'/g, '') %>')"
```

Agregar este botón ANTES del de "Ficha PDF":

```html
                  <button onclick="abrirModalEstudio(<%= p.id %>, '<%= (p.folio || '').replace(/'/g, '') %>')"
                          class="px-2.5 py-1.5 text-xs border border-teal-300 text-teal-700 rounded-lg
                                 hover:bg-teal-50 transition-colors">
                    Estudio
                  </button>
```

- [ ] **Step 2: Agregar el modal HTML**

Inmediatamente antes del cierre del último `</div>` del archivo (o antes de `</body>` si existe), agregar el modal completo:

```html
<!-- ═══════════════════ MODAL ESTUDIO DE MERCADO ═══════════════════ -->
<div id="modal-estudio" class="fixed inset-0 z-50 hidden">
  <div class="absolute inset-0 bg-black/50" onclick="cerrarModalEstudio()"></div>
  <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2
              bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh]
              overflow-y-auto flex flex-col">

    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 sticky top-0 bg-white z-10">
      <div>
        <h2 class="text-base font-semibold text-gray-900">Estudio de Mercado</h2>
        <p id="estudio-folio" class="text-xs text-gray-400 mt-0.5"></p>
      </div>
      <button onclick="cerrarModalEstudio()"
              class="text-gray-400 hover:text-gray-600 text-2xl font-light leading-none">&times;</button>
    </div>

    <!-- Tabs -->
    <div class="flex border-b border-gray-200 px-6">
      <button id="tab-guardados" onclick="cambiarTab('guardados')"
              class="py-3 px-4 text-sm font-medium border-b-2 border-teal-600 text-teal-600 -mb-px">
        Comparables
      </button>
      <button id="tab-ml" onclick="cambiarTab('ml')"
              class="py-3 px-4 text-sm font-medium border-b-2 border-transparent text-gray-500
                     hover:text-gray-700 -mb-px ml-2">
        Buscar en Mercado Libre
      </button>
    </div>

    <!-- Panel: Comparables guardados -->
    <div id="panel-guardados" class="p-6">
      <p class="text-xs text-gray-400 mb-4">
        Hasta 5 comparables. El título y URL son requeridos para guardar cada fila.
        Las filas vacías se ignoran al guardar.
      </p>
      <div id="filas-comparables" class="space-y-3"></div>
      <button onclick="guardarEstudio()"
              class="mt-5 w-full py-2.5 bg-teal-600 text-white rounded-xl text-sm font-medium
                     hover:bg-teal-700 transition-colors cursor-pointer">
        Guardar comparables
      </button>
      <p id="estudio-msg" class="text-xs text-center mt-2 hidden"></p>
    </div>

    <!-- Panel: Sugerencias ML -->
    <div id="panel-ml" class="p-6 hidden">
      <div class="flex items-center justify-between mb-4">
        <p class="text-xs text-gray-500">
          Busca propiedades similares en Mercado Libre según municipio y tipo de la propiedad.
          Haz clic en "Usar" para copiarla a los comparables.
        </p>
        <button onclick="buscarML()"
                class="px-4 py-2 bg-amber-500 text-white rounded-xl text-sm font-medium
                       hover:bg-amber-600 transition-colors whitespace-nowrap ml-4 cursor-pointer">
          Buscar ahora
        </button>
      </div>
      <div id="ml-loading" class="text-center py-8 text-gray-400 text-sm hidden">Buscando en Mercado Libre...</div>
      <div id="ml-resultados" class="space-y-3"></div>
    </div>

  </div>
</div>
```

- [ ] **Step 3: Agregar el bloque JavaScript**

Al final del archivo, agregar un bloque `<script>` con todo el JS del modal:

```html
<script>
// ── Estudio de Mercado ──────────────────────────────────────────────────
let estudioId   = null;
let estudioRows = [];

function abrirModalEstudio(id, folio) {
  estudioId = id;
  document.getElementById('modal-estudio').classList.remove('hidden');
  document.getElementById('estudio-folio').textContent = 'Folio: ' + folio;
  document.getElementById('estudio-msg').classList.add('hidden');
  cambiarTab('guardados');
  cargarComparables();
}

function cerrarModalEstudio() {
  document.getElementById('modal-estudio').classList.add('hidden');
  estudioId = null;
}

function cambiarTab(tab) {
  document.getElementById('panel-guardados').classList.toggle('hidden', tab !== 'guardados');
  document.getElementById('panel-ml').classList.toggle('hidden', tab !== 'ml');
  const activo   = 'py-3 px-4 text-sm font-medium border-b-2 border-teal-600 text-teal-600 -mb-px';
  const inactivo = 'py-3 px-4 text-sm font-medium border-b-2 border-transparent text-gray-500 hover:text-gray-700 -mb-px ml-2';
  document.getElementById('tab-guardados').className = tab === 'guardados' ? activo : inactivo.replace(' ml-2','');
  document.getElementById('tab-ml').className        = tab === 'ml'        ? activo + ' ml-2' : inactivo;
}

async function cargarComparables() {
  try {
    const res  = await fetch('/admin/fichas/outlet/' + estudioId + '/estudio-mercado');
    const data = await res.json();
    estudioRows = data.comparables || [];
    while (estudioRows.length < 5) estudioRows.push({});
    renderFilas();
  } catch (e) {
    console.error('[estudio] cargarComparables:', e);
  }
}

function escHtml(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function renderFilas() {
  const cont = document.getElementById('filas-comparables');
  cont.innerHTML = '';
  estudioRows.slice(0, 5).forEach(function(c, i) {
    cont.insertAdjacentHTML('beforeend',
      '<div class="border border-gray-200 rounded-xl p-4 bg-gray-50">' +
        '<div class="text-xs font-semibold text-teal-700 mb-3">Comparable #' + (i + 1) + '</div>' +
        '<div class="grid grid-cols-2 gap-2 mb-2">' +
          '<div>' +
            '<label class="block text-xs text-gray-500 mb-1">Portal</label>' +
            '<input class="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:border-teal-500"' +
                   ' placeholder="Mercado Libre, Inmuebles24..."' +
                   ' value="' + escHtml(c.portal || '') + '"' +
                   ' onchange="estudioRows[' + i + '].portal=this.value">' +
          '</div>' +
          '<div>' +
            '<label class="block text-xs text-gray-500 mb-1">Precio (MXN)</label>' +
            '<input type="number" class="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:border-teal-500"' +
                   ' placeholder="1500000"' +
                   ' value="' + escHtml(c.precio || '') + '"' +
                   ' onchange="estudioRows[' + i + '].precio=this.value">' +
          '</div>' +
        '</div>' +
        '<div class="mb-2">' +
          '<label class="block text-xs text-gray-500 mb-1">Título / Descripción</label>' +
          '<input class="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:border-teal-500"' +
                 ' placeholder="Casa en venta en Col. Centro..."' +
                 ' value="' + escHtml(c.titulo || '') + '"' +
                 ' onchange="estudioRows[' + i + '].titulo=this.value">' +
        '</div>' +
        '<div class="mb-2">' +
          '<label class="block text-xs text-gray-500 mb-1">URL</label>' +
          '<input type="url" class="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:border-teal-500"' +
                 ' placeholder="https://..."' +
                 ' value="' + escHtml(c.url || '') + '"' +
                 ' onchange="estudioRows[' + i + '].url=this.value">' +
        '</div>' +
        '<div class="grid grid-cols-3 gap-2">' +
          '<div>' +
            '<label class="block text-xs text-gray-500 mb-1">m² construcción</label>' +
            '<input type="number" class="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:border-teal-500"' +
                   ' placeholder="120" value="' + escHtml(c.area_m2 || '') + '"' +
                   ' onchange="estudioRows[' + i + '].area_m2=this.value">' +
          '</div>' +
          '<div>' +
            '<label class="block text-xs text-gray-500 mb-1">Recámaras</label>' +
            '<input type="number" min="0" max="20" class="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:border-teal-500"' +
                   ' placeholder="3" value="' + escHtml(c.recamaras || '') + '"' +
                   ' onchange="estudioRows[' + i + '].recamaras=this.value">' +
          '</div>' +
          '<div>' +
            '<label class="block text-xs text-gray-500 mb-1">Baños</label>' +
            '<input type="number" min="0" max="20" class="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-xs focus:outline-none focus:border-teal-500"' +
                   ' placeholder="2" value="' + escHtml(c.sanitarios || '') + '"' +
                   ' onchange="estudioRows[' + i + '].sanitarios=this.value">' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  });
}

async function buscarML() {
  const loading = document.getElementById('ml-loading');
  const res     = document.getElementById('ml-resultados');
  loading.classList.remove('hidden');
  res.innerHTML = '';
  try {
    const r    = await fetch('/admin/fichas/outlet/' + estudioId + '/estudio-mercado/sugerencias');
    const data = await r.json();
    loading.classList.add('hidden');
    if (!data.ok || !data.sugerencias || !data.sugerencias.length) {
      res.innerHTML = '<p class="text-sm text-gray-400 text-center py-4">Sin resultados para esta propiedad en Mercado Libre.</p>';
      return;
    }
    data.sugerencias.forEach(function(s) {
      const precio = s.precio ? '$' + Math.round(s.precio).toLocaleString('es-MX') : '—';
      const m2     = s.area_m2 ? s.area_m2 + ' m²' : '';
      const rec    = s.recamaras ? s.recamaras + ' rec' : '';
      const ban    = s.sanitarios ? s.sanitarios + ' baños' : '';
      const img    = s.imagen_url
        ? '<img src="' + escHtml(s.imagen_url) + '" class="w-20 h-16 object-cover rounded-lg flex-shrink-0" onerror="this.style.display=\'none\'">'
        : '';
      const tags   = [precio, m2, rec, ban].filter(Boolean).map(function(t) {
        return '<span>' + escHtml(t) + '</span>';
      }).join('');
      res.insertAdjacentHTML('beforeend',
        '<div class="flex gap-3 border border-gray-200 rounded-xl p-3 bg-white items-start">' +
          img +
          '<div class="flex-1 min-w-0">' +
            '<p class="text-xs font-medium text-gray-900 mb-1 line-clamp-2">' + escHtml(s.titulo) + '</p>' +
            '<div class="flex flex-wrap gap-2 text-xs text-gray-500 [&>span:first-child]:text-teal-700 [&>span:first-child]:font-semibold">' + tags + '</div>' +
          '</div>' +
          '<button onclick=\'usarSugerencia(' + JSON.stringify(s).replace(/'/g, '&#39;') + ')\'' +
                  ' class="px-3 py-1.5 bg-teal-600 text-white rounded-lg text-xs font-medium hover:bg-teal-700 transition-colors flex-shrink-0 cursor-pointer">' +
            'Usar' +
          '</button>' +
        '</div>'
      );
    });
  } catch (e) {
    loading.classList.add('hidden');
    res.innerHTML = '<p class="text-sm text-red-400 text-center py-4">Error al buscar. Verifica tu conexión e intenta de nuevo.</p>';
  }
}

function usarSugerencia(s) {
  const libre = estudioRows.findIndex(function(r) { return !r.titulo && !r.url; });
  const idx   = libre >= 0 ? libre : 4;
  estudioRows[idx] = Object.assign({}, s);
  cambiarTab('guardados');
  renderFilas();
}

async function guardarEstudio() {
  const btn = document.querySelector('#panel-guardados button[onclick="guardarEstudio()"]');
  const msg = document.getElementById('estudio-msg');
  btn.disabled = true;
  btn.textContent = 'Guardando...';
  try {
    const r = await fetch('/admin/fichas/outlet/' + estudioId + '/estudio-mercado', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ comparables: estudioRows }),
    });
    const data = await r.json();
    msg.classList.remove('hidden');
    if (data.ok) {
      msg.textContent = '✓ Comparables guardados correctamente';
      msg.className   = 'text-xs text-center mt-2 text-teal-600';
    } else {
      msg.textContent = 'Error: ' + (data.error || 'desconocido');
      msg.className   = 'text-xs text-center mt-2 text-red-500';
    }
  } catch (e) {
    msg.classList.remove('hidden');
    msg.textContent = 'Error de red. Intenta de nuevo.';
    msg.className   = 'text-xs text-center mt-2 text-red-500';
  } finally {
    btn.disabled    = false;
    btn.textContent = 'Guardar comparables';
  }
}
</script>
```

- [ ] **Step 4: Verificar el modal completo**

1. Iniciar servidor (`npm run dev`)
2. Ir a `http://localhost:3000/admin/fichas`
3. Hacer clic en "Estudio" de cualquier propiedad → modal debe abrirse
4. Las 5 filas deben aparecer vacías
5. Cambiar a "Buscar en Mercado Libre" → clic "Buscar ahora" → esperar resultados
6. Clic "Usar" en un resultado → debe llenar la primera fila disponible
7. Clic "Guardar comparables" → debe mostrar mensaje verde "✓ Comparables guardados correctamente"
8. Cerrar y volver a abrir el modal de la misma propiedad → los datos deben persistir

- [ ] **Step 5: Commit**

```bash
git add views/admin/fichas/index.ejs
git commit -m "feat: modal de estudio de mercado en panel admin de fichas"
```

---

## Task 6: PDF Template — página Estudio de Mercado

**Files:**
- Modify: `views/admin/fichas/template-outlet.ejs`

La nueva página solo se renderiza si `estudioMercado.length > 0`. Aparece después de las 3 páginas existentes.

- [ ] **Step 1: Agregar la página al final del template**

Al final de `views/admin/fichas/template-outlet.ejs`, antes de `</body>`, agregar:

```html
<% if (typeof estudioMercado !== 'undefined' && estudioMercado && estudioMercado.length > 0) { %>
<!-- ══════════════════ PÁGINA 4: ESTUDIO DE MERCADO ══════════════════ -->
<div class="page" style="background:#0a0a0a;display:flex;flex-direction:column;">

  <!-- Header -->
  <div style="background:#008a8a;padding:40px 80px 30px;display:flex;align-items:center;justify-content:space-between;">
    <div>
      <div style="color:rgba(255,255,255,0.7);font-size:13px;letter-spacing:3px;text-transform:uppercase;font-weight:300;margin-bottom:8px;">
        Análisis Comparativo
      </div>
      <div style="color:#fff;font-size:38px;font-weight:700;letter-spacing:-0.5px;">
        Estudio de Mercado
      </div>
    </div>
    <div style="text-align:right;">
      <div style="color:rgba(255,255,255,0.7);font-size:13px;letter-spacing:2px;text-transform:uppercase;font-weight:300;">
        Propiedad
      </div>
      <div style="color:#fff;font-size:22px;font-weight:600;margin-top:4px;">
        <%= propiedad.folio %>
      </div>
      <div style="color:rgba(255,255,255,0.6);font-size:14px;margin-top:2px;">
        <%= [propiedad.colonia, propiedad.municipio].filter(Boolean).join(', ') %>
      </div>
    </div>
  </div>

  <!-- Tabla de comparables -->
  <div style="flex:1;padding:36px 80px;overflow:hidden;">
    <table style="width:100%;border-collapse:collapse;font-size:16px;">
      <thead>
        <tr style="border-bottom:2px solid #008a8a;">
          <th style="padding:12px 16px 12px 0;text-align:left;color:#008a8a;font-size:12px;letter-spacing:2px;text-transform:uppercase;font-weight:600;width:38%;">
            Propiedad comparable
          </th>
          <th style="padding:12px 16px;text-align:left;color:#008a8a;font-size:12px;letter-spacing:2px;text-transform:uppercase;font-weight:600;width:14%;">
            Portal
          </th>
          <th style="padding:12px 16px;text-align:right;color:#008a8a;font-size:12px;letter-spacing:2px;text-transform:uppercase;font-weight:600;width:18%;">
            Precio
          </th>
          <th style="padding:12px 16px;text-align:center;color:#008a8a;font-size:12px;letter-spacing:2px;text-transform:uppercase;font-weight:600;width:10%;">
            m²
          </th>
          <th style="padding:12px 16px;text-align:center;color:#008a8a;font-size:12px;letter-spacing:2px;text-transform:uppercase;font-weight:600;width:10%;">
            Rec.
          </th>
          <th style="padding:12px 16px;text-align:center;color:#008a8a;font-size:12px;letter-spacing:2px;text-transform:uppercase;font-weight:600;width:10%;">
            Baños
          </th>
        </tr>
      </thead>
      <tbody>
        <% estudioMercado.forEach(function(c, i) { %>
        <tr style="border-bottom:1px solid rgba(255,255,255,0.07);<%= i % 2 === 0 ? 'background:rgba(255,255,255,0.03);' : '' %>">
          <td style="padding:16px 16px 16px 0;color:#ffffff;font-size:14px;font-weight:500;line-height:1.4;">
            <%= c.titulo || '—' %>
          </td>
          <td style="padding:16px;color:rgba(255,255,255,0.55);font-size:13px;">
            <%= c.portal || '—' %>
          </td>
          <td style="padding:16px;text-align:right;color:#00cccc;font-size:16px;font-weight:600;">
            <% if (c.precio) { %>$<%= Number(c.precio).toLocaleString('es-MX') %><% } else { %>—<% } %>
          </td>
          <td style="padding:16px;text-align:center;color:rgba(255,255,255,0.8);font-size:14px;">
            <%= c.area_m2 ? (c.area_m2 + ' m²') : '—' %>
          </td>
          <td style="padding:16px;text-align:center;color:rgba(255,255,255,0.8);font-size:14px;">
            <%= c.recamaras || '—' %>
          </td>
          <td style="padding:16px;text-align:center;color:rgba(255,255,255,0.8);font-size:14px;">
            <%= c.sanitarios || '—' %>
          </td>
        </tr>
        <% }) %>
      </tbody>
    </table>

    <!-- Fila de la propiedad actual (referencia) -->
    <div style="margin-top:28px;padding:22px 24px;background:rgba(0,138,138,0.12);border:1.5px solid rgba(0,138,138,0.4);border-radius:12px;display:flex;align-items:center;gap:48px;">
      <div style="flex:1;min-width:0;">
        <div style="color:#008a8a;font-size:11px;letter-spacing:2px;text-transform:uppercase;margin-bottom:5px;font-weight:600;">
          Nuestra propiedad (referencia)
        </div>
        <div style="color:#fff;font-size:16px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
          <%= [propiedad.calle, propiedad.colonia, propiedad.municipio].filter(Boolean).join(', ') %>
        </div>
      </div>
      <div style="text-align:center;flex-shrink:0;">
        <div style="color:rgba(255,255,255,0.5);font-size:11px;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;">Precio</div>
        <div style="color:#00cccc;font-size:22px;font-weight:700;"><%= precioFormateado %></div>
      </div>
      <% if (propiedad.construccion) { %>
      <div style="text-align:center;flex-shrink:0;">
        <div style="color:rgba(255,255,255,0.5);font-size:11px;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;">m²</div>
        <div style="color:#fff;font-size:20px;font-weight:600;"><%= propiedad.construccion %> m²</div>
      </div>
      <% } %>
      <% if (propiedad.recamaras) { %>
      <div style="text-align:center;flex-shrink:0;">
        <div style="color:rgba(255,255,255,0.5);font-size:11px;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;">Rec.</div>
        <div style="color:#fff;font-size:20px;font-weight:600;"><%= propiedad.recamaras %></div>
      </div>
      <% } %>
      <% if (propiedad.sanitarios) { %>
      <div style="text-align:center;flex-shrink:0;">
        <div style="color:rgba(255,255,255,0.5);font-size:11px;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px;">Baños</div>
        <div style="color:#fff;font-size:20px;font-weight:600;"><%= propiedad.sanitarios %></div>
      </div>
      <% } %>
    </div>
  </div>

  <!-- Footer -->
  <div style="padding:18px 80px;border-top:1px solid rgba(255,255,255,0.08);display:flex;align-items:center;justify-content:space-between;">
    <div style="color:rgba(255,255,255,0.3);font-size:12px;letter-spacing:1px;font-weight:500;">
      ALTALTIUM REAL ESTATE SOLUTIONS
    </div>
    <div style="color:rgba(255,255,255,0.25);font-size:11px;">
      Comparativas obtenidas de portales inmobiliarios públicos con fines informativos
    </div>
  </div>

</div>
<% } %>
```

- [ ] **Step 2: Verificar preview con comparables**

1. Asegurarse de haber guardado al menos 1 comparable (Task 5)
2. Abrir `http://localhost:3000/admin/fichas/outlet/{id}/preview` con la propiedad que tiene comparables
3. Desplazarse hasta el final — debe aparecer la página 4 "Estudio de Mercado"
4. La tabla de comparables debe verse con fondo oscuro, texto blanco, precios en teal
5. La fila de "Nuestra propiedad (referencia)" debe aparecer abajo con borde teal
6. Verificar que en una propiedad SIN comparables, la página 4 NO aparece

- [ ] **Step 3: Commit**

```bash
git add views/admin/fichas/template-outlet.ejs
git commit -m "feat: página estudio de mercado en template PDF outlet (página 4 condicional)"
```

---

## Checklist de verificación final

Antes de solicitar aprobación para subir a producción:

- [ ] La tabla `ficha_estudio_mercado` existe en la BD local
- [ ] El botón "Estudio" aparece en cada fila de la tabla outlet
- [ ] El modal se abre y cierra correctamente
- [ ] Las 5 filas de comparables aparecen (vacías al inicio)
- [ ] "Buscar en Mercado Libre" devuelve resultados reales de ML
- [ ] "Usar" copia un resultado a la primera fila disponible
- [ ] "Guardar" persiste en BD y muestra confirmación
- [ ] Reabrir el modal muestra los datos guardados
- [ ] El preview HTML muestra la página 4 cuando hay comparables
- [ ] El preview HTML NO muestra página 4 cuando no hay comparables
- [ ] Los precios se formatean correctamente en el PDF
