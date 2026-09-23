# Calculadora Renova — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Activar la calculadora de comisiones Renova en el tab "Calculadora" del perfil, con toggle de traspaso 25%/75%.

**Architecture:** Cambio 100% client-side en un solo archivo EJS. Se habilita el botón deshabilitado, se reemplaza el panel "Próximamente" con la calculadora, y se agregan las funciones JS al bloque `<script>` existente.

**Tech Stack:** EJS, JavaScript vanilla, Tailwind CSS CDN

---

### Task 1: Habilitar el botón Renova

**Files:**
- Modify: `views/profile/index.ejs` (línea ~246)

- [ ] **Step 1: Localizar el botón Renova en el array de productos**

Buscar esta línea en `views/profile/index.ejs`:
```javascript
{id:'renova', icon:'🔨', label:'Renova', disabled:true},
```

- [ ] **Step 2: Quitar el flag `disabled`**

Reemplazar esa línea con:
```javascript
{id:'renova', icon:'🔨', label:'Renova'},
```
(Sin `disabled:true` ni `active:true`. El botón usará el estilo inactivo por defecto y llamará a `switchProd('renova')` normalmente.)

- [ ] **Step 3: Verificar en el navegador**

Abrir `/profile?tab=calc` y confirmar que:
- El botón 🔨 Renova ya NO tiene opacidad reducida ni cursor `not-allowed`
- Hacer click en él cambia el tab al panel `#prod-renova`

- [ ] **Step 4: Commit**

```bash
git add views/profile/index.ejs
git commit -m "feat: habilitar botón Renova en calculadora de comisiones"
```

---

### Task 2: Reemplazar el panel "Próximamente" con la calculadora

**Files:**
- Modify: `views/profile/index.ejs` (línea ~451-455)

- [ ] **Step 1: Localizar el panel actual**

Buscar este bloque en `views/profile/index.ejs`:
```html
<!-- RENOVA -->
<div id="prod-renova" class="hidden text-center py-12">
  <div class="text-4xl mb-3">🔨</div>
  <p class="text-sm font-medium text-gray-500">Próximamente</p>
  <p class="text-xs text-gray-400 mt-1">La calculadora de Renova estará disponible pronto</p>
</div>
```

- [ ] **Step 2: Reemplazarlo con la calculadora completa**

```html
<!-- RENOVA -->
<div id="prod-renova" class="hidden">

  <!-- Input monto -->
  <div class="mb-5">
    <label class="block text-sm text-gray-600 mb-2 font-medium">
      💵 Monto total de la remodelación ($)
    </label>
    <input type="text" id="rn-monto" placeholder="Ej. 500,000"
           oninput="fmtInput(this);calcRenova()"
           class="w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm
                  focus:outline-none focus:border-teal-500 transition-colors">
  </div>

  <!-- Toggle traspaso -->
  <div id="rn-toggle-wrap"
       class="bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 mb-5
              flex items-center justify-between cursor-pointer select-none"
       onclick="toggleRenovaTraspaso()">
    <div>
      <p class="text-sm font-semibold text-gray-700">↔️ ¿Fue traspasado a asesor especializado Renova?</p>
      <p class="text-xs text-gray-400 mt-0.5" id="rn-toggle-sub">Activa la división 25% / 75%</p>
    </div>
    <!-- Pill toggle -->
    <div id="rn-toggle-pill"
         class="w-11 h-6 bg-gray-300 rounded-full relative transition-colors duration-200 flex-shrink-0 ml-4">
      <div id="rn-toggle-dot"
           class="w-5 h-5 bg-white rounded-full absolute top-0.5 left-0.5
                  shadow transition-transform duration-200"></div>
    </div>
  </div>

  <!-- Resultado -->
  <div id="rn-result"
       class="hidden bg-teal-50 border border-teal-200 border-l-4 border-l-teal-500 rounded-xl p-5 mb-4">
    <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">✅ Desglose de comisión</p>
    <div id="rn-rows" class="space-y-2"></div>
  </div>

  <!-- Nota proceso completo -->
  <div class="bg-amber-50 border border-amber-200 border-l-4 border-l-amber-400 rounded-xl p-4
              flex gap-3 items-start">
    <span class="text-lg flex-shrink-0">⚠️</span>
    <p class="text-xs text-amber-800 leading-relaxed">
      Para recibir el <strong>10% completo</strong>, el asesor debe realizar el proceso completo:
      <strong>captación, proyección, dictamen y cierre de la negociación</strong>.
    </p>
  </div>

</div>
```

- [ ] **Step 3: Verificar estructura HTML en el navegador**

Abrir `/profile?tab=calc`, hacer click en 🔨 Renova y confirmar que:
- Aparece el input de monto
- Aparece el toggle (apagado por defecto, fondo gris)
- Aparece la nota ⚠️ en amarillo al fondo

- [ ] **Step 4: Commit**

```bash
git add views/profile/index.ejs
git commit -m "feat: agregar panel calculadora Renova con toggle de traspaso"
```

---

### Task 3: Agregar funciones JavaScript de la calculadora

**Files:**
- Modify: `views/profile/index.ejs` — bloque `<script>` al final del archivo (antes del cierre `</script>`)

- [ ] **Step 1: Localizar el final del bloque `<script>`**

Buscar la última función JS del archivo, que termina así:
```javascript
  res.classList.remove('hidden');
  document.getElementById('r-rows').innerHTML = rows;
}
</script>
```

- [ ] **Step 2: Agregar las funciones Renova antes del cierre `</script>`**

Insertar este bloque justo antes de `</script>`:

```javascript

// ── Calculadora Renova ──────────────────────────────────
let renovaTraspaso = false;

function toggleRenovaTraspaso() {
  renovaTraspaso = !renovaTraspaso;
  const pill = document.getElementById('rn-toggle-pill');
  const dot  = document.getElementById('rn-toggle-dot');
  const sub  = document.getElementById('rn-toggle-sub');
  const wrap = document.getElementById('rn-toggle-wrap');
  if (renovaTraspaso) {
    pill.classList.replace('bg-gray-300', 'bg-teal-500');
    dot.style.transform = 'translateX(20px)';
    sub.textContent = 'División 25% traspasó · 75% trabajó';
    sub.classList.replace('text-gray-400', 'text-teal-600');
    wrap.classList.replace('bg-gray-50', 'bg-teal-50');
    wrap.classList.replace('border-gray-200', 'border-teal-200');
  } else {
    pill.classList.replace('bg-teal-500', 'bg-gray-300');
    dot.style.transform = 'translateX(0)';
    sub.textContent = 'Activa la división 25% / 75%';
    sub.classList.replace('text-teal-600', 'text-gray-400');
    wrap.classList.replace('bg-teal-50', 'bg-gray-50');
    wrap.classList.replace('border-teal-200', 'border-gray-200');
  }
  calcRenova();
}

function calcRenova() {
  const monto  = getRaw('rn-monto');
  const res    = document.getElementById('rn-result');
  const rows   = document.getElementById('rn-rows');
  if (!res || !rows) return;
  if (monto <= 0) { res.classList.add('hidden'); return; }

  const comTotal = monto * 0.10;
  let pagos = [];

  if (renovaTraspaso) {
    pagos = [
      { label: 'Comisión total (10%)',         monto: comTotal,        bold: true  },
      { label: '💼 Quien traspasó (25%)',       monto: comTotal * 0.25, bold: false },
      { label: '🔨 Asesor Renova (75%)',         monto: comTotal * 0.75, bold: false, highlight: true },
    ];
  } else {
    pagos = [
      { label: 'Monto de remodelación',         monto: monto,           bold: false },
      { label: 'Comisión total (10%)',           monto: comTotal,        bold: true  },
    ];
  }

  rows.innerHTML = pagos.map((p, i) => `
    <div class="flex justify-between text-sm py-2
                ${i < pagos.length - 1 ? 'border-b border-teal-100' : ''}">
      <span class="${p.bold ? 'font-medium text-gray-700' : 'text-gray-500'}">${p.label}</span>
      <span class="${p.bold || p.highlight ? 'font-semibold text-teal-600 text-base' : 'font-medium text-teal-600'}">
        ${fmt(p.monto)}
      </span>
    </div>`
  ).join('');

  res.classList.remove('hidden');
}
```

- [ ] **Step 3: Verificar el flujo completo en el navegador**

Abrir `/profile?tab=calc` → click en 🔨 Renova:

**Sin traspaso:**
1. Escribir `500000` en el campo monto
2. Confirmar que aparece el resultado: Monto `$500,000` · Comisión `$50,000`
3. El toggle se ve gris (apagado)

**Con traspaso:**
4. Click en el toggle → se pone teal (encendido)
5. Confirmar que el resultado cambia a:
   - Comisión total (10%): `$50,000`
   - Quien traspasó (25%): `$12,500`
   - Asesor Renova (75%): `$37,500`
6. Click de nuevo en el toggle → regresa al estado sin traspaso

**Otros productos:**
7. Navegar a Outlet, Micro, Legal, Residencial y verificar que siguen funcionando igual

- [ ] **Step 4: Commit final**

```bash
git add views/profile/index.ejs
git commit -m "feat: calculadora de comisiones Renova con toggle de traspaso 25/75"
```

---

## Checklist de spec coverage

| Requisito | Tarea |
|---|---|
| 10% del monto de remodelación | Task 3 — `calcRenova()` |
| Solo asesor (sin gerente) | Task 2 — no hay selector de rol |
| Nota de proceso completo obligatorio | Task 2 — bloque `⚠️` |
| Toggle traspaso 25%/75% | Task 2 (HTML) + Task 3 (JS) |
| Botón habilitado | Task 1 |
| No afecta otros productos | Task 3 Step 3 verifica regresiones |
