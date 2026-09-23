# Reglas de Primer Contacto — Asesor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar 3 reglas de negocio para leads nuevos: (1) perfilamiento bloqueado hasta registrar llamada, (2) ventana de 5 minutos para el primer contacto sincronizada con el cron de escalación, (3) validación backend de campos requeridos.

**Architecture:** Cambios en el controller `crm.controller.js` para pasar datos al render y validar el submit; cambios en `show.ejs` para el botón condicional; cambios en `contact.ejs` para los constraints de fecha/hora y errores de validación. Sin nuevas rutas ni tablas.

**Tech Stack:** Node.js v24, Express v5, EJS, PostgreSQL (pool directo), Tailwind CDN

---

## Archivos que se modifican

| Archivo | Cambios |
|---|---|
| `src/controllers/advisor/crm.controller.js` | `leadsShow`: agregar `hasCallActivity`; `contactForm`: agregar `transferredAt`; `contactSubmit`: agregar `isFirst` + validaciones |
| `views/advisor/crm/leads/show.ejs` | Botón "Iniciar perfilamiento" condicional (activo/deshabilitado) |
| `views/advisor/crm/leads/contact.ejs` | Error banners, min/max datetime en inputs, validación JS en submit |

---

## Task 1: `hasCallActivity` en `leadsShow` (backend)

**Files:**
- Modify: `src/controllers/advisor/crm.controller.js`

Después de la línea `const activities = await crmService.listActivitiesByLead(leadId, advisorId);` (aprox línea 421), agregar el cómputo de `hasCallActivity` usando el array ya cargado (sin query extra a BD):

- [ ] **Step 1: Agregar `hasCallActivity` después de `activities` en `leadsShow`**

Localiza esta línea (aprox 421):
```javascript
const activities = await crmService.listActivitiesByLead(leadId, advisorId);
```

Agrega inmediatamente después:
```javascript
const hasCallActivity = Array.isArray(activities) &&
  activities.some(a => (a.type || '').toLowerCase() === 'llamada');
```

- [ ] **Step 2: Pasar `hasCallActivity` al render de `show.ejs`**

En el bloque `res.render('advisor/crm/leads/show', { ... })` (aprox línea 556–583), agrega `hasCallActivity` junto a las otras variables:

```javascript
return res.render('advisor/crm/leads/show', {
  title: 'Detalle de Lead',
  path: '/advisor/leads',
  user: req.session.user,
  lead,
  profile,
  activities,
  outcomes,
  inventarioMap,
  inventarioByFolio,
  stage1Locked,
  stage2Locked,
  isTransferredOut,
  transferredToName: lead.transferred_to_name || null,
  query: req.query || {},
  calendarEvents,
  userRole: req.session.user.role,
  userRolesExtra: req.session.user.roles_extra || [],
  perfilSL,
  perfilSLData,
  propertyProfile,
  propPerfilResidencialVender,
  renovaRelatoria,
  lastRenovaChange,
  asesor_nombre,
  gerente_nombre,
  transferChain,
  hasCallActivity,   // ← NUEVO
});
```

- [ ] **Step 3: Verificar en localhost**

Levanta el servidor (`node src/app.js` o `nodemon`). Entra a un lead sin actividades. Abre DevTools → Network. Busca la respuesta HTML de `/advisor/leads/:id` y verifica que `hasCallActivity` está disponible (aparecerá en el EJS renderizado, no en JSON).

---

## Task 2: Botón "Iniciar Perfilamiento" condicional (frontend `show.ejs`)

**Files:**
- Modify: `views/advisor/crm/leads/show.ejs`

El botón actual está en la línea ~627. Solo se muestra cuando `!profile && !(_isSL && perfilSLData)`. Hay que hacerlo condicional a `hasCallActivity`.

- [ ] **Step 1: Reemplazar el botón activo por lógica condicional**

Localiza este bloque (aprox línea 626–628):
```ejs
<% if (!_isDirectivoView && !_isManagerView && !_readOnlyTransferred) { %>
<a href="/advisor/leads/<%= lead.id %>/<%= _isSL ? 'perfil-soluciones-legales' : 'profile' %>" class="inline-flex items-center gap-1.5 px-4 py-2 bg-teal-600 text-white text-xs font-medium rounded-lg hover:bg-teal-700 transition-colors">Iniciar perfilamiento</a>
<% } %>
```

Reemplázalo con:
```ejs
<% if (!_isDirectivoView && !_isManagerView && !_readOnlyTransferred) { %>
  <% if (hasCallActivity) { %>
    <a href="/advisor/leads/<%= lead.id %>/<%= _isSL ? 'perfil-soluciones-legales' : 'profile' %>"
       class="inline-flex items-center gap-1.5 px-4 py-2 bg-teal-600 text-white text-xs font-medium rounded-lg hover:bg-teal-700 transition-colors">
      Iniciar perfilamiento
    </a>
  <% } else { %>
    <button type="button" disabled
            class="inline-flex items-center gap-1.5 px-4 py-2 bg-slate-100 text-slate-400 text-xs font-medium rounded-lg cursor-not-allowed"
            title="Registra una llamada primero">
      Iniciar perfilamiento
    </button>
    <p class="text-xs text-slate-400 mt-2">Registra una llamada primero para habilitar.</p>
  <% } %>
<% } %>
```

- [ ] **Step 2: Verificar en localhost**

Entra a un lead sin actividades → el botón debe verse gris con el texto "Registra una llamada primero". Registra una llamada desde `/contact` → vuelve al lead → el botón debe verse teal y activo.

---

## Task 3: Pasar `transferredAt` desde `contactForm` (backend)

**Files:**
- Modify: `src/controllers/advisor/crm.controller.js`

- [ ] **Step 1: Agregar `transferredAt` en `contactForm`**

Localiza este bloque en `contactForm` (aprox línea 921–941):
```javascript
const activities = await crmService.listActivitiesByLead(leadId, advisorId);
const isFirst = !activities || activities.length === 0;

const managerInfo = (typeof crmService.getManagerForAdvisor === 'function')
  ? await crmService.getManagerForAdvisor(advisorId)
  : null;

return res.render('advisor/crm/leads/contact', {
  title: isFirst ? 'Primer contacto' : 'Registrar contacto',
  path: '/advisor/leads',
  user: req.session.user,
  lead,
  profile: profile || null,
  activities,
  isFirst,
  restrictToCallOnly: onlyCall,
  managerId: managerInfo?.managerId || null,
  managerName: managerInfo?.managerName || null,
  errors: null,
  query: req.query || {},
});
```

Reemplázalo con:
```javascript
const activities = await crmService.listActivitiesByLead(leadId, advisorId);
const isFirst = !activities || activities.length === 0;

// Para la ventana de 5 min en el primer contacto
const transferredAt = isFirst
  ? (lead.transferred_at || lead.created_at || null)
  : null;

const managerInfo = (typeof crmService.getManagerForAdvisor === 'function')
  ? await crmService.getManagerForAdvisor(advisorId)
  : null;

return res.render('advisor/crm/leads/contact', {
  title: isFirst ? 'Primer contacto' : 'Registrar contacto',
  path: '/advisor/leads',
  user: req.session.user,
  lead,
  profile: profile || null,
  activities,
  isFirst,
  restrictToCallOnly: onlyCall,
  managerId: managerInfo?.managerId || null,
  managerName: managerInfo?.managerName || null,
  errors: null,
  query: req.query || {},
  transferredAt: transferredAt ? new Date(transferredAt).toISOString() : null,
});
```

- [ ] **Step 2: Verificar en localhost**

Entra a `/advisor/leads/:id/contact` en un lead nuevo. Abre DevTools → inspecciona el HTML fuente. Busca `transferredAt` en el HTML renderizado (aparecerá en el siguiente task como variable JS). Confirma que el controller no lanza errores en la consola del servidor.

---

## Task 4: Constraints de fecha/hora en `contact.ejs` (frontend)

**Files:**
- Modify: `views/advisor/crm/leads/contact.ejs`

**Parte A:** Agregar banner de errores del servidor.
**Parte B:** Agregar lógica JS de min/max y validación en submit.

- [ ] **Step 1: Agregar banner de errores del servidor**

Localiza el bloque de error `CALL_ONLY` (aprox línea 143–159):
```ejs
<% if (CALL_ONLY) { %>
  <div class="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-5">
    ...
  </div>
<% } %>
```

Agrega inmediatamente DESPUÉS de ese bloque (antes de `<% if (q && q.mode === 'followup') { %>`):
```ejs
<% if (q && q.error === 'tiempo_invalido') { %>
  <div class="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-5">
    <p class="text-[11px] tracking-[0.22em] text-rose-700 font-extrabold uppercase">Hora fuera de ventana</p>
    <p class="mt-1 text-sm text-rose-900 font-semibold">
      La hora debe estar entre las <%= q.min || '—' %> y las <%= q.max || '—' %> (CDMX).
    </p>
    <p class="mt-1 text-xs text-rose-800/80">
      Solo puedes registrar el primer contacto dentro de los 5 minutos siguientes a cuando recibiste el lead.
    </p>
  </div>
<% } %>

<% if (q && q.error === 'campos_requeridos') { %>
  <div class="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-5">
    <p class="text-[11px] tracking-[0.22em] text-rose-700 font-extrabold uppercase">Campos incompletos</p>
    <p class="mt-1 text-sm text-rose-900 font-semibold">Completa todos los campos requeridos.</p>
  </div>
<% } %>
```

- [ ] **Step 2: Agregar variable JS `TRANSFERRED_AT` y lógica de constraints**

Localiza esta línea en el bloque `<script>` (aprox línea 513):
```javascript
const CALL_ONLY = <%- JSON.stringify(CALL_ONLY) %>;
```

Agrega inmediatamente después:
```javascript
const IS_FIRST_CONTACT = <%- JSON.stringify(IS_FIRST) %>;
const TRANSFERRED_AT_ISO = <%- JSON.stringify(typeof transferredAt !== 'undefined' ? transferredAt : null) %>;
```

- [ ] **Step 3: Agregar función de constraints de fecha/hora**

Localiza la función `syncScheduledAt` (aprox línea 583):
```javascript
function syncScheduledAt() {
  const iso = buildCdmxIso(normalize(dateEl?.value), normalize(timeEl?.value));
  if (scheduledAtEl) scheduledAtEl.value = iso;
}
```

Agrega DESPUÉS de esa función (antes de `function syncPlatformUI`):
```javascript
// Aplica min/max en los inputs de fecha y hora para el primer contacto
function applyDateTimeConstraints() {
  if (!IS_FIRST_CONTACT || !TRANSFERRED_AT_ISO) return;

  const min = new Date(TRANSFERRED_AT_ISO);
  const max = new Date(min.getTime() + 5 * 60 * 1000);

  // Convierte a partes CDMX para los atributos HTML
  const fmtDate = (d) => new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Mexico_City', year: 'numeric', month: '2-digit', day: '2-digit'
  }).format(d);
  const fmtTime = (d) => new Intl.DateTimeFormat('en-GB', {
    timeZone: 'America/Mexico_City', hour: '2-digit', minute: '2-digit', hour12: false
  }).format(d);

  if (dateEl) {
    dateEl.min = fmtDate(min);
    dateEl.max = fmtDate(max);
  }
  // Guardar en window para validación en submit
  window._firstContactMin = min;
  window._firstContactMax = max;
}
```

- [ ] **Step 4: Llamar `applyDateTimeConstraints()` en la inicialización**

Localiza el bloque de inicialización al final del script (aprox línea 935–939):
```javascript
// init
syncModalityUI();
syncExecUI();
syncScheduledAt();
```

Agrega `applyDateTimeConstraints();` al final:
```javascript
// init
syncModalityUI();
syncExecUI();
syncScheduledAt();
applyDateTimeConstraints();
```

- [ ] **Step 5: Agregar validación de ventana en submit**

Localiza el listener de submit existente del autocomplete de propiedades (aprox línea 906–932):
```javascript
const form = document.querySelector('form');
form?.addEventListener('submit', () => {
  ...
});
```

Agrega ANTES de ese bloque un listener de validación (que puede cancelar el submit):
```javascript
// Validación de ventana de tiempo en primer contacto
document.querySelector('form')?.addEventListener('submit', function(e) {
  if (!IS_FIRST_CONTACT || !window._firstContactMin || !window._firstContactMax) return;

  const dateVal = dateEl?.value;
  const timeVal = timeEl?.value;
  if (!dateVal || !timeVal) return; // el data-required lo manejará

  // Construir datetime CDMX → comparar con la ventana (en UTC)
  const submitted = new Date(`${dateVal}T${timeVal}:00-06:00`);
  if (isNaN(submitted.getTime())) return;

  if (submitted < window._firstContactMin || submitted > window._firstContactMax) {
    e.preventDefault();
    e.stopImmediatePropagation();

    const fmt = (d) => d.toLocaleTimeString('es-MX', {
      timeZone: 'America/Mexico_City', hour: '2-digit', minute: '2-digit'
    });

    const errId = 'datetime-window-error';
    let errEl = document.getElementById(errId);
    if (!errEl) {
      errEl = document.createElement('p');
      errEl.id = errId;
      errEl.className = 'mt-2 text-xs text-rose-600 font-semibold';
      timeEl?.closest('div')?.after(errEl);
    }
    errEl.textContent = `Hora fuera de ventana. Debe estar entre ${fmt(window._firstContactMin)} y ${fmt(window._firstContactMax)} (CDMX).`;
    dateEl?.closest('div')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    return;
  }

  // Limpiar error si existía
  document.getElementById('datetime-window-error')?.remove();
}, { capture: true }); // capture:true para ejecutar ANTES del listener de propiedades
```

- [ ] **Step 6: Verificar en localhost**

1. Entra a `/advisor/leads/:id/contact` en un lead nuevo.
2. Ingresa una hora 10 minutos antes de cuando llegó el lead → el submit debe bloquearse con error inline rojo.
3. Ingresa una hora dentro de los 5 minutos → el submit debe proceder normalmente.
4. Verifica que los atributos `min` y `max` del input `date` reflejan la fecha correcta.

---

## Task 5: Validación backend en `contactSubmit`

**Files:**
- Modify: `src/controllers/advisor/crm.controller.js`

- [ ] **Step 1: Agregar `isFirst` y validaciones en `contactSubmit`**

Localiza `exports.contactSubmit` (aprox línea 947). El bloque actual después de `getLeadVisible` es:

```javascript
// Sin perfil completo => solo permitir type=llamada (defensa en backend)
const profile = await crmService.getProfileByLeadIdForAdvisor(leadId, advisorId);
const profileComplete = profile && stage2IsLocked(profile);
const esSLSubmit = (lead.producto || '').trim() === 'Soluciones Legales';

if (!profileComplete && !esSLSubmit) {
  ...
}

await crmService.createActivity(leadId, advisorId, req.body || {});
```

Reemplaza el bloque completo de validación y createActivity por:

```javascript
// Sin perfil completo => solo permitir type=llamada (defensa en backend)
const profile = await crmService.getProfileByLeadIdForAdvisor(leadId, advisorId);
const profileComplete = profile && stage2IsLocked(profile);
const esSLSubmit = (lead.producto || '').trim() === 'Soluciones Legales';

if (!profileComplete && !esSLSubmit) {
  const type = toStr(req.body?.type || '').trim().toLowerCase();
  const allowed = ['llamada', 'call', 'phone', 'telefono', 'teléfono'];
  const isCallType = !type || allowed.some(k => type.includes(k));

  if (!isCallType) {
    return res.redirect(
      `${leadsBase(req)}/leads/${leadId}/contact?error=solo_llamada_sin_perfil`
    );
  }

  // Forzamos type=llamada por seguridad (por si el form fue alterado)
  req.body.type = 'llamada';
}

// ── Validaciones de primer contacto ──────────────────────────────────────────
const activitiesForFirst = await crmService.listActivitiesByLead(leadId, advisorId);
const isFirstSubmit = !activitiesForFirst || activitiesForFirst.length === 0;

if (isFirstSubmit) {
  const obs    = (req.body.observations  || '').trim();
  const folio  = (req.body.property_folio || '').trim();
  const sched  = (req.body.scheduled_at  || '').trim();

  // Campos requeridos
  if (!obs || !folio || !sched) {
    console.warn(`[contactSubmit] primer contacto con campos vacíos — leadId=${leadId} obs=${!!obs} folio=${!!folio} sched=${!!sched}`);
    return res.redirect(
      `${leadsBase(req)}/leads/${leadId}/contact?error=campos_requeridos`
    );
  }

  // Ventana de 5 minutos
  const transferredAt = lead.transferred_at || lead.created_at;
  if (transferredAt && sched) {
    const schedUTC = new Date(`${sched}-06:00`); // sched es naive CDMX p.ej. "2026-06-19T11:03:00"
    const minUTC   = new Date(transferredAt);
    const maxUTC   = new Date(new Date(transferredAt).getTime() + 5 * 60 * 1000);

    if (isNaN(schedUTC.getTime()) || schedUTC < minUTC || schedUTC > maxUTC) {
      const fmt = (d) => d.toLocaleTimeString('es-MX', {
        timeZone: 'America/Mexico_City', hour: '2-digit', minute: '2-digit'
      });
      console.warn(`[contactSubmit] hora fuera de ventana — leadId=${leadId} sched=${sched} min=${fmt(minUTC)} max=${fmt(maxUTC)}`);
      return res.redirect(
        `${leadsBase(req)}/leads/${leadId}/contact?error=tiempo_invalido&min=${encodeURIComponent(fmt(minUTC))}&max=${encodeURIComponent(fmt(maxUTC))}`
      );
    }
  }
}
// ─────────────────────────────────────────────────────────────────────────────

await crmService.createActivity(leadId, advisorId, req.body || {});
```

- [ ] **Step 2: Verificar en localhost — campos requeridos**

1. Abre `/advisor/leads/:id/contact` en un lead nuevo.
2. Deja `observations` vacío y envía el form (temporalmente quita `data-required` del input en DevTools para bypasear el frontend).
3. Debe redirigir a `?error=campos_requeridos` y mostrar el banner rojo de "Campos incompletos".

- [ ] **Step 3: Verificar en localhost — ventana de tiempo**

1. Abre `/advisor/leads/:id/contact` en un lead nuevo.
2. Cambia la hora en DevTools para estar fuera de la ventana (p.ej. 1 hora después de `transferred_at`).
3. Modifica el hidden `scheduled_at` directamente en DevTools y envía.
4. Debe redirigir a `?error=tiempo_invalido&min=HH:MM&max=HH:MM` y mostrar el banner con la ventana correcta.

- [ ] **Step 4: Verificar logs del servidor**

Con un submit fuera de ventana, la consola del servidor (`server.out` o terminal) debe mostrar:
```
[contactSubmit] hora fuera de ventana — leadId=X sched=2026-06-19T12:00:00 min=11:00 max=11:05
```
No debe haber errores sin manejar ni stack traces.

---

## Task 6: Smoke test integral

- [ ] **Step 1: Flujo completo — lead nuevo sin llamada**

1. Entra a un lead con `status = 'open'` sin actividades.
2. En la página del lead (`show.ejs`): el botón "Iniciar perfilamiento" debe verse **gris** con texto "Registra una llamada primero".
3. Haz clic en el botón → debe estar deshabilitado (no navega).

- [ ] **Step 2: Flujo completo — registrar llamada dentro de ventana**

1. En el mismo lead, haz clic en "Registrar contacto".
2. La página de contacto debe mostrar: tipo forzado a "Llamada" (si no hay perfil).
3. Ingresa fecha/hora dentro de los 5 min de `transferred_at`, llena todos los campos, guarda.
4. Regresa al lead: el botón "Iniciar perfilamiento" ahora debe estar **teal y activo**.
5. Haz clic → navega a `/advisor/leads/:id/profile` correctamente.

- [ ] **Step 3: Flujo completo — hora fuera de ventana bloqueada en frontend**

1. En un lead nuevo, entra a contacto.
2. Ingresa una hora fuera de la ventana → el submit debe bloquearse con error inline.
3. Modifica la hora a dentro de la ventana → el submit procede.

- [ ] **Step 4: Verificar que leads con actividades existentes no se ven afectados**

1. Entra a un lead que ya tiene actividades registradas (no es `isFirst`).
2. Registra un contacto con cualquier hora → debe funcionar sin restricción de ventana.
3. El botón "Iniciar perfilamiento" (si aplica) debe verse activo.
