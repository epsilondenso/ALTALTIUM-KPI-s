# Filtros Tipo Excel en Inventario-Hoja — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar dropdowns tipo Excel en todos los headers de la tabla de `inventario-hoja.ejs` — checkboxes para columnas de texto y rango mín/máx para columnas numéricas, con badge contador cuando el filtro está activo.

**Architecture:** Todo client-side en un único archivo EJS. Se añaden atributos `data-col` a los `<th>` para identificar columnas, se agrega CSS para los dropdowns, y se extiende la función `matches()` existente con un bloque de filtros de columna. No hay cambios al servidor.

**Tech Stack:** JavaScript vanilla (IIFE existente), CSS inline, EJS (server-side template)

---

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `views/pages/inventario-hoja.ejs` | Único archivo. 3 zonas: HTML (atributos `<th>` + `<tr>`), CSS (estilos de dropdown), JS (lógica de filtros de columna) |

---

### Task 1: Cambios HTML — atributos `data-col` en `<th>` y `data-etapa`/`data-alred`/`data-expte` en `<tr>`

**Files:**
- Modify: `views/pages/inventario-hoja.ejs` (líneas 761–788 para thead, líneas 858–868 para tr)

- [ ] **Step 1: Reemplazar el bloque `<thead><tr>` actual por la versión con `data-col`**

Localiza el bloque `<thead>` (línea ~760) y reemplaza el `<tr>` completo:

```html
          <tr>
            <th class="freeze" style="width:44px;text-align:center;">#</th>
            <th data-col="lista">Lista</th>
            <th data-col="etapa">Etapa</th>
            <th data-col="folio">ID PROP</th>
            <th data-col="tipo">Tipo</th>
            <th data-col="estatus">Estatus</th>
            <th data-col="calle">Calle</th>
            <th data-col="colonia">Colonia</th>
            <th data-col="mun">Municipio</th>
            <th data-col="estado">Estado</th>
            <th data-col="cp">C.P.</th>
            <th class="r" data-col="terreno">Terreno m²</th>
            <th class="r" data-col="cons">Constr. m²</th>
            <th class="r" data-col="rec">Rec.</th>
            <th class="r" data-col="san">Baños</th>
            <th class="r" data-col="est">Est.</th>
            <th class="r" data-col="cesion">Costo cesión</th>
            <th class="r" data-col="hon">Honorarios</th>
            <th class="r" data-col="ctotal">Costo total</th>
            <th class="r" data-col="vcom">Valor comercial</th>
            <% if (typeof showInternal !== 'undefined' && showInternal) { %>
            <th class="r" data-col="ccompra">Costo compra</th>
            <th class="r" data-col="ganancia">Ganancia</th>
            <% } %>
            <th style="text-align:center;" data-col="expte">Expte.</th>
            <th data-col="alred">Alrededores</th>
            <th>Ubicación</th>
          </tr>
```

- [ ] **Step 2: Agregar `data-etapa`, `data-alred`, `data-expte` al `<tr>` de cada fila**

Localiza el `<tr class="inv-row...">` (línea ~858). Reemplaza el bloque `<tr>` existente por:

```html
            <tr class="inv-row<%= isSan?' blocked':'' %><%= isPaq?' paquete':'' %>"
              data-folio="<%= folio %>" data-tipo="<%= tipo %>"
              data-calle="<%= calle %>" data-colonia="<%= colonia %>"
              data-municipio="<%= alc %>" data-estado="<%= estado %>" data-cp="<%= cp %>"
              data-rec="<%= rec %>" data-san="<%= san %>" data-est="<%= est %>"
              data-construccion="<%= cons %>" data-terreno="<%= terr %>"
              data-costo-total="<%= costoTot %>" data-precio-pub="<%= val %>"
              data-valor-com="<%= val %>" data-costo-cesion="<%= costoCes %>"
              data-honorarios="<%= hon %>" data-maps="<%= maps %>"
              data-lista="<%= lista %>" data-no-publicable="<%= isSan?'1':'' %>"
              data-estatus="<%= estatus %>"
              data-etapa="<%= etapa %>"
              data-alred="<%= alred %>"
              data-expte="<%= expte ? 'Con expediente' : '' %>"
              data-ccompra="<%= costoCompra %>"
              data-ganancia="<%= ganancia %>">
```

- [ ] **Step 3: Verificar en el navegador**

Abre `/inventario/hoja` (o la ruta que use esta vista), abre DevTools → Elements, haz clic en cualquier `<th>` de la tabla y verifica que tenga el atributo `data-col="lista"` (o el que corresponda). Haz clic en una fila y verifica que tenga `data-etapa`, `data-alred`, `data-expte`.

---

### Task 2: CSS — estilos del dropdown

**Files:**
- Modify: `views/pages/inventario-hoja.ejs` (bloque `<style>`, al final antes del cierre `</style>`)

- [ ] **Step 1: Agregar los estilos al final del bloque `<style>` existente**

Localiza la línea `input[type=hidden] { display: none !important; }` (última línea del bloque `<style>`). Agrega DESPUÉS de ella, antes del cierre `</style>`:

```css
/* ══════════════════════════════════════
   COLUMN FILTER DROPDOWNS
══════════════════════════════════════ */

/* Header clickable */
.col-th {
  position: relative;
  cursor: pointer;
}
.col-th-inner {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  width: 100%;
  pointer-events: none; /* el click lo captura el <th> */
}
.col-th-chevron {
  flex-shrink: 0;
  opacity: .35;
  transition: opacity .15s, transform .15s;
}
.col-th:hover .col-th-chevron { opacity: .75; }
.col-th.cf-active { color: #52BEC0; }
.col-th.cf-active .col-th-chevron { opacity: 1; }
.col-th.cf-open .col-th-chevron { transform: rotate(180deg); }

/* Badge contador */
.col-th-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 15px;
  height: 15px;
  border-radius: 999px;
  background: #52BEC0;
  color: #fff;
  font-size: 8px;
  font-weight: 800;
  padding: 0 3px;
  flex-shrink: 0;
  line-height: 1;
}

/* Dropdown container */
.col-drop {
  position: absolute;
  top: calc(100% + 2px);
  left: 0;
  background: #fff;
  border: 1px solid #e2e3e8;
  border-radius: 10px;
  box-shadow: 0 8px 28px rgba(0,0,0,.16);
  z-index: 300;
  min-width: 190px;
  display: none;
  color: #0d0d0d; /* reset from dark thead */
  font-weight: 400;
  letter-spacing: 0;
  text-transform: none;
}
.col-drop.open { display: block; }

/* Search */
.col-drop-search { padding: 7px 8px; border-bottom: 1px solid #f0f1f5; }
.col-drop-search input {
  width: 100%;
  border: 1px solid #e2e3e8;
  border-radius: 6px;
  padding: 5px 8px;
  font-size: 11px;
  font-family: var(--font);
  outline: none;
  color: var(--ink);
  background: var(--soft);
}
.col-drop-search input:focus {
  border-color: var(--teal);
  background: #fff;
  box-shadow: 0 0 0 2px rgba(82,190,192,.13);
}

/* Checkbox list */
.col-drop-list {
  max-height: 160px;
  overflow-y: auto;
  padding: 4px 0;
}
.col-drop-list::-webkit-scrollbar { width: 4px; }
.col-drop-list::-webkit-scrollbar-thumb { background: #cdd0da; border-radius: 99px; }

.col-drop-item {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px 10px;
  cursor: pointer;
  font-size: 11px;
  color: var(--ink);
  transition: background .1s;
  user-select: none;
}
.col-drop-item:hover { background: var(--soft); }
.col-drop-item input[type="checkbox"] {
  accent-color: var(--teal);
  flex-shrink: 0;
  cursor: pointer;
}
.col-drop-item span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Numeric range */
.col-drop-range {
  padding: 10px 10px 6px;
}
.col-drop-range-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 7px;
}
.col-drop-range-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--muted);
  display: block;
  margin-bottom: 4px;
}
.col-drop-range input[type="number"] {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 5px 8px;
  font-size: 11px;
  font-family: var(--font);
  outline: none;
  color: var(--ink);
  background: var(--soft);
}
.col-drop-range input[type="number"]:focus {
  border-color: var(--teal);
  background: #fff;
  box-shadow: 0 0 0 2px rgba(82,190,192,.13);
}

/* Footer botones */
.col-drop-foot {
  padding: 7px 8px;
  border-top: 1px solid #f0f1f5;
  display: flex;
  gap: 5px;
}
.col-drop-foot button {
  flex: 1;
  padding: 6px 0;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
  font-family: var(--font);
  border: none;
  transition: background .12s;
}
.col-drop-ok { background: var(--teal); color: #fff; }
.col-drop-ok:hover { background: var(--teal-d); }
.col-drop-cl { background: var(--soft); color: var(--muted); border: 1px solid var(--line) !important; }
.col-drop-cl:hover { background: var(--line); }
```

- [ ] **Step 2: Verificar que no hay errores CSS**

Guarda el archivo, recarga la página en el navegador. La tabla debe verse igual que antes (los estilos nuevos aún no aplican porque el JS no está). No debe haber errores en DevTools → Console.

---

### Task 3: JavaScript — lógica completa de filtros de columna

**Files:**
- Modify: `views/pages/inventario-hoja.ejs` (bloque `<script>`, dentro de la IIFE existente)

El bloque `<script>` existente es una IIFE `(function(){ ... })()`. Hay que hacer 3 cambios dentro de ella:

1. Agregar `const colFilters = {}` y `CF_DEFS` cerca del inicio
2. Agregar las funciones de dropdown antes de `/* ── init ── */`
3. Modificar `matches()` para incluir los filtros de columna
4. Llamar `initColFilters()` al final

- [ ] **Step 1: Agregar `colFilters` y `CF_DEFS` después de la declaración de `rows`**

Localiza la línea (dentro del `<script>`):
```javascript
  const rows     = Array.from(document.querySelectorAll('#invBody .inv-row'));
```

Agrega INMEDIATAMENTE DESPUÉS:

```javascript
  /* ── Column filter state ── */
  const colFilters = {};
  // colFilters[key] = { type:'cat', values: Set<string> }
  //                 | { type:'num', min: number|null, max: number|null }

  const CF_DEFS = [
    { key:'lista',   attr:'data-lista',        type:'cat' },
    { key:'etapa',   attr:'data-etapa',        type:'cat' },
    { key:'folio',   attr:'data-folio',        type:'cat' },
    { key:'tipo',    attr:'data-tipo',         type:'cat' },
    { key:'estatus', attr:'data-estatus',      type:'cat' },
    { key:'calle',   attr:'data-calle',        type:'cat' },
    { key:'colonia', attr:'data-colonia',      type:'cat' },
    { key:'mun',     attr:'data-municipio',    type:'cat' },
    { key:'estado',  attr:'data-estado',       type:'cat' },
    { key:'cp',      attr:'data-cp',           type:'cat' },
    { key:'terreno', attr:'data-terreno',      type:'num' },
    { key:'cons',    attr:'data-construccion', type:'num' },
    { key:'rec',     attr:'data-rec',          type:'num' },
    { key:'san',     attr:'data-san',          type:'num' },
    { key:'est',     attr:'data-est',          type:'num' },
    { key:'cesion',  attr:'data-costo-cesion', type:'num' },
    { key:'hon',     attr:'data-honorarios',   type:'num' },
    { key:'ctotal',  attr:'data-costo-total',  type:'num' },
    { key:'vcom',    attr:'data-valor-com',    type:'num' },
    { key:'ccompra', attr:'data-ccompra',      type:'num' },
    { key:'ganancia',attr:'data-ganancia',     type:'num' },
    { key:'expte',   attr:'data-expte',        type:'cat' },
    { key:'alred',   attr:'data-alred',        type:'cat' },
  ];
```

- [ ] **Step 2: Modificar `matches()` — agregar check de filtros de columna al final**

Localiza dentro del `<script>` la función `matches(el)`. Al final, ANTES del `return true;` final, agrega:

```javascript
    /* ── column filters ── */
    for (const key in colFilters) {
      const cf  = colFilters[key];
      const def = CF_DEFS.find(d => d.key === key);
      if (!def) continue;
      const raw = (el.getAttribute(def.attr) || '').trim();
      if (cf.type === 'cat') {
        if (!cf.values.has(raw)) return false;
      } else {
        const n = raw !== '' ? Number(raw) : null;
        if (cf.min !== null && (n === null || n < cf.min)) return false;
        if (cf.max !== null && (n === null || n > cf.max)) return false;
      }
    }
```

El resultado de `matches()` debe quedar así al final:

```javascript
    /* ── column filters ── */
    for (const key in colFilters) {
      const cf  = colFilters[key];
      const def = CF_DEFS.find(d => d.key === key);
      if (!def) continue;
      const raw = (el.getAttribute(def.attr) || '').trim();
      if (cf.type === 'cat') {
        if (!cf.values.has(raw)) return false;
      } else {
        const n = raw !== '' ? Number(raw) : null;
        if (cf.min !== null && (n === null || n < cf.min)) return false;
        if (cf.max !== null && (n === null || n > cf.max)) return false;
      }
    }

    return true;
  }
```

- [ ] **Step 3: Agregar las funciones de dropdown antes de `/* ── init ── */`**

Localiza el comentario `/* ── init ── */` dentro del `<script>`. Agrega TODO lo siguiente ANTES de ese comentario:

```javascript
  /* ══════════════════════════════════════
     COLUMN FILTER DROPDOWNS
  ══════════════════════════════════════ */

  let _openDrop = null; // dropdown actualmente abierto

  function closeAllColDrops() {
    document.querySelectorAll('.col-drop.open').forEach(d => {
      d.classList.remove('open');
      d.closest('th')?.classList.remove('cf-open');
    });
    _openDrop = null;
  }

  /* Extrae valores únicos de una columna (cat) */
  function getColVals(attr) {
    return Array.from(
      new Set(rows.map(r => (r.getAttribute(attr)||'').trim()))
    ).sort((a,b) => a.localeCompare(b,'es'));
  }

  /* Construye el dropdown para una columna */
  function buildColDrop(def) {
    const drop = document.createElement('div');
    drop.className = 'col-drop';
    drop.addEventListener('click', e => e.stopPropagation());

    if (def.type === 'cat') {
      const vals = getColVals(def.attr);

      /* ─ Buscador ─ */
      const searchWrap = document.createElement('div');
      searchWrap.className = 'col-drop-search';
      const si = document.createElement('input');
      si.placeholder = 'Buscar…';
      si.addEventListener('input', () => {
        const q = si.value.trim().toLowerCase();
        drop.querySelectorAll('.col-drop-item').forEach(it => {
          const isAll = it.dataset.all === '1';
          const txt   = (it.querySelector('span')?.textContent || '').toLowerCase();
          it.style.display = (isAll || !q || txt.includes(q)) ? '' : 'none';
        });
      });
      searchWrap.appendChild(si);
      drop.appendChild(searchWrap);

      /* ─ Lista ─ */
      const list = document.createElement('div');
      list.className = 'col-drop-list';

      /* "(Todos)" item */
      const allItem = makeColItem('(Todos)', true);
      allItem.dataset.all = '1';
      allItem.querySelector('input').addEventListener('change', e => {
        list.querySelectorAll('input[data-val]').forEach(cb => { cb.checked = e.target.checked; });
      });
      list.appendChild(allItem);

      vals.forEach(v => {
        const it = makeColItem(v || '—', true);
        it.querySelector('input').dataset.val = v;
        it.querySelector('input').addEventListener('change', () => {
          const cbs  = Array.from(list.querySelectorAll('input[data-val]'));
          const all  = cbs.every(cb => cb.checked);
          list.querySelector('input').checked = all;
        });
        list.appendChild(it);
      });
      drop.appendChild(list);

      /* Pre-seleccionar si hay filtro activo */
      const active = colFilters[def.key];
      if (active && active.type === 'cat') {
        list.querySelectorAll('input[data-val]').forEach(cb => {
          cb.checked = active.values.has(cb.dataset.val);
        });
        const all = Array.from(list.querySelectorAll('input[data-val]')).every(cb => cb.checked);
        list.querySelector('input').checked = all;
      }

    } else {
      /* ─ Rango numérico ─ */
      const range = document.createElement('div');
      range.className = 'col-drop-range';
      const row = document.createElement('div');
      row.className = 'col-drop-range-row';

      const makeRangeInput = (role, placeholder) => {
        const wrap = document.createElement('div');
        const lbl  = document.createElement('label');
        lbl.className   = 'col-drop-range-label';
        lbl.textContent = role === 'min' ? 'Mínimo' : 'Máximo';
        const inp = document.createElement('input');
        inp.type = 'number'; inp.placeholder = placeholder; inp.dataset.role = role;
        const active = colFilters[def.key];
        if (active && active.type === 'num') {
          if (role === 'min' && active.min !== null) inp.value = active.min;
          if (role === 'max' && active.max !== null) inp.value = active.max;
        }
        wrap.appendChild(lbl); wrap.appendChild(inp);
        return wrap;
      };

      row.appendChild(makeRangeInput('min', '0'));
      row.appendChild(makeRangeInput('max', 'Sin límite'));
      range.appendChild(row);
      drop.appendChild(range);
    }

    drop.appendChild(makeColFoot(def));
    return drop;
  }

  function makeColItem(label, checked) {
    const div = document.createElement('div');
    div.className = 'col-drop-item';
    const cb  = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = checked;
    const sp  = document.createElement('span');
    sp.textContent = label;
    div.appendChild(cb); div.appendChild(sp);
    div.addEventListener('click', e => {
      if (e.target !== cb) { cb.checked = !cb.checked; cb.dispatchEvent(new Event('change')); }
    });
    return div;
  }

  function makeColFoot(def) {
    const foot  = document.createElement('div');
    foot.className = 'col-drop-foot';

    const okBtn = document.createElement('button');
    okBtn.className   = 'col-drop-ok';
    okBtn.textContent = '✓ OK';
    okBtn.addEventListener('click', () => {
      applyColFilter(def);
      updateThBadge(def.key);
      closeAllColDrops();
      apply();
    });

    const clBtn = document.createElement('button');
    clBtn.className   = 'col-drop-cl';
    clBtn.textContent = 'Limpiar';
    clBtn.addEventListener('click', () => {
      delete colFilters[def.key];
      updateThBadge(def.key);
      closeAllColDrops();
      apply();
    });

    foot.appendChild(okBtn); foot.appendChild(clBtn);
    return foot;
  }

  function applyColFilter(def) {
    const drop = document.querySelector(`th[data-col="${def.key}"] .col-drop`);
    if (!drop) return;

    if (def.type === 'cat') {
      const allVals = Array.from(drop.querySelectorAll('input[data-val]'));
      const checked = allVals.filter(cb => cb.checked).map(cb => cb.dataset.val);
      if (checked.length === 0 || checked.length === allVals.length) {
        delete colFilters[def.key];
      } else {
        colFilters[def.key] = { type: 'cat', values: new Set(checked) };
      }
    } else {
      const minEl = drop.querySelector('input[data-role="min"]');
      const maxEl = drop.querySelector('input[data-role="max"]');
      const min   = minEl?.value !== '' ? Number(minEl.value) : null;
      const max   = maxEl?.value !== '' ? Number(maxEl.value) : null;
      if (min === null && max === null) {
        delete colFilters[def.key];
      } else {
        colFilters[def.key] = { type: 'num', min, max };
      }
    }
  }

  function updateThBadge(key) {
    const th = document.querySelector(`th[data-col="${key}"]`);
    if (!th) return;
    const existing = th.querySelector('.col-th-badge');
    if (existing) existing.remove();

    if (!colFilters[key]) {
      th.classList.remove('cf-active');
      return;
    }
    th.classList.add('cf-active');

    const badge = document.createElement('span');
    badge.className = 'col-th-badge';
    const f = colFilters[key];
    badge.textContent = f.type === 'cat' ? f.values.size : '1';

    const inner = th.querySelector('.col-th-inner');
    const chevron = inner?.querySelector('.col-th-chevron');
    if (inner && chevron) inner.insertBefore(badge, chevron);
    else if (inner) inner.appendChild(badge);
  }

  /* Inicializa todos los <th data-col> */
  function initColFilters() {
    const ths = document.querySelectorAll('table.sht thead th[data-col]');
    ths.forEach(th => {
      const key = th.getAttribute('data-col');
      const def = CF_DEFS.find(d => d.key === key);
      if (!def) return;

      /* Wrap existing text in .col-th-inner */
      const inner = document.createElement('div');
      inner.className = 'col-th-inner';
      Array.from(th.childNodes).forEach(n => inner.appendChild(n));

      /* Chevron SVG */
      const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
      svg.setAttribute('viewBox','0 0 24 24');
      svg.setAttribute('fill','none');
      svg.setAttribute('stroke','currentColor');
      svg.setAttribute('stroke-width','2.5');
      svg.setAttribute('class','col-th-chevron');
      svg.setAttribute('width','8');
      svg.setAttribute('height','8');
      svg.innerHTML = '<path d="M6 9l6 6 6-6"/>';
      inner.appendChild(svg);
      th.appendChild(inner);

      /* Dropdown (built fresh each open for up-to-date values) */
      th.classList.add('col-th');

      th.addEventListener('click', e => {
        e.stopPropagation();
        const alreadyOpen = th.classList.contains('cf-open');
        closeAllColDrops();
        if (alreadyOpen) return;

        /* Build & attach dropdown */
        const existing = th.querySelector('.col-drop');
        if (existing) existing.remove();
        const drop = buildColDrop(def);
        th.appendChild(drop);

        drop.classList.add('open');
        th.classList.add('cf-open');
        _openDrop = drop;

        /* Focus search if category */
        if (def.type === 'cat') {
          const si = drop.querySelector('.col-drop-search input');
          if (si) setTimeout(() => si.focus(), 50);
        }
      });
    });

    document.addEventListener('click', closeAllColDrops);
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && _openDrop) closeAllColDrops();
    });
  }
```

- [ ] **Step 4: Llamar `initColFilters()` al final de la IIFE**

Localiza el comentario `/* ── init ── */` y la llamada `apply();` al final del script. Agrega `initColFilters();` DESPUÉS de `apply()`:

```javascript
  /* ── init ── */
  apply();
  initColFilters();
```

- [ ] **Step 5: Verificar en el navegador**

1. Guarda el archivo y recarga `/inventario/hoja`
2. Haz clic en el header **"Lista"** → debe aparecer el dropdown con checkboxes mostrando los valores únicos de la columna Lista (ej. "Lista Oro", "Santander")
3. Desmarca "Lista Oro" → clic en **OK** → la tabla debe ocultar las propiedades Lista Oro. El badge teal debe aparecer en el header con "1"
4. Haz clic en el header **"Terreno m²"** → debe aparecer el dropdown con dos inputs numéricos (Mínimo / Máximo)
5. Ingresa un mínimo de 100 → OK → la tabla filtra correctamente
6. Verifica que el badge sea "1" en el header numérico activo
7. Haz clic en cualquier otro header → el dropdown anterior debe cerrarse
8. Presiona **Escape** → el dropdown activo debe cerrarse
9. Clic fuera de la tabla → el dropdown activo debe cerrarse
10. Verifica que los filtros de columna se combinan con los del toolbar (ej. filtra por Estado en toolbar Y por Tipo en header)

---

## Verificación final

- [ ] Todos los headers (excepto `#` y `Ubicación`) muestran dropdown al hacer clic
- [ ] Checkboxes para columnas de texto, rango numérico para columnas de números
- [ ] Badge teal con contador aparece cuando hay filtro activo
- [ ] Click fuera / Escape cierra el dropdown
- [ ] Solo un dropdown abierto a la vez
- [ ] Los filtros de columna se combinan con búsqueda, Estado, Municipio, Colonia, Lista del toolbar y drawer avanzado
- [ ] El botón "Limpiar" del dropdown quita el filtro de esa columna y remueve el badge
- [ ] La exportación CSV sigue funcionando con las filas filtradas
- [ ] Sin errores en la consola del navegador
