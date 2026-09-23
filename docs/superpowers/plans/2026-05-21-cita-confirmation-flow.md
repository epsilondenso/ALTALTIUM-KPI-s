# Cita Confirmation Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move "Marcar como confirmada" inside the outcome modal for cita activities, fix the permissions bug, and add "Reagendar cita" as an option within that same modal.

**Architecture:** Fix a type-coercion bug in the confirm route, add `cita_status` handling to the outcome controller, remove the standalone confirm button from the activity list, and add a "¿Qué pasó con la cita?" section to the outcome modal that shows only when `data-act-type="cita"`.

**Tech Stack:** Node.js v24 + Express v5, PostgreSQL, EJS server-side rendering, Tailwind CDN, vanilla JS IIFE in show.ejs.

---

## File Map

| Action | File | What changes |
|--------|------|--------------|
| Modify | `src/routes/advisor.crm.routes.js` | Fix strict `===` to `Number()` comparison at line 285 |
| Modify | `src/controllers/advisor/crm.controller.js` | Read `cita_status` from `req.body` and either confirm the cita or force-reagendar |
| Modify | `views/advisor/crm/leads/show.ejs` | Remove `.btn-confirm-cita` button (~line 1745); add `#citaStatusSection` to modal; update modal JS IIFE |

---

### Task 1: Fix the type-coercion bug in the confirm route

**Files:**
- Modify: `src/routes/advisor.crm.routes.js:285`

**Context:** PostgreSQL returns `advisor_id` and `transferred_to` as JavaScript numbers. `req.session.user?.id` is stored as a number, but depending on how the session is serialized it might come back as a string. The strict `===` comparison fails silently when types differ, causing a false "Sin permisos" 403.

- [ ] **Step 1: Open the file**

Read `src/routes/advisor.crm.routes.js` lines 283–290.

Expected content (line 285):
```javascript
const isOwner = row.advisor_id === advisorId || row.transferred_to === advisorId;
```

- [ ] **Step 2: Apply the fix**

Replace line 285 with a coerced comparison:

```javascript
const isOwner = Number(row.advisor_id) === Number(advisorId) || Number(row.transferred_to) === Number(advisorId);
```

Full diff — change only that one line:
```diff
-    const isOwner = row.advisor_id === advisorId || row.transferred_to === advisorId;
+    const isOwner = Number(row.advisor_id) === Number(advisorId) || Number(row.transferred_to) === Number(advisorId);
```

- [ ] **Step 3: Verify no other strict comparisons exist in that function**

Search for `=== advisorId` in `src/routes/advisor.crm.routes.js`. Should only appear once (the line just fixed). If there are others in the same route handler, apply `Number()` coercion to them too.

- [ ] **Step 4: Commit**

```bash
git add src/routes/advisor.crm.routes.js
git commit -m "fix: coerce advisor_id to Number in confirm-cita permission check"
```

---

### Task 2: Handle `cita_status` in `activityOutcomeUpsert`

**Files:**
- Modify: `src/controllers/advisor/crm.controller.js:878-1064`

**Context:** When a cita's outcome modal is submitted with `cita_status=atendida`, we call the existing confirm endpoint logic inline (UPDATE `confirmed_at`). When `cita_status=reagendada`, we force `programFollowup=true` and set `rawNextType='cita'` so that the existing followup creation path handles it. This avoids duplicating the confirm-route SQL or the followup-creation logic.

`pool` is already imported at line 4 of the controller. The variable `activityId` is already defined at line 884.

- [ ] **Step 1: Read the current start of `activityOutcomeUpsert`**

Read `src/controllers/advisor/crm.controller.js` lines 878–950 to confirm `advisorId`, `activityId`, and `pool` are all in scope.

- [ ] **Step 2: Add `cita_status` block after `upsertOutcome` (between lines 909 and 911)**

Insert this block after the `notifService.notificarSupervisores(...)` try/catch (which ends around line 909) and before the material/patch block (which starts around line 916):

```javascript
    // =========================
    // 1.6) Si es actividad de tipo cita → procesar resultado de la cita
    // =========================
    const citaStatus = toStr(req.body?.cita_status || '').toLowerCase();
    if (activity.type === 'cita' && citaStatus === 'atendida') {
      try {
        await pool.query(
          `UPDATE crm_activities SET confirmed_at = NOW(), confirmed_by = $1, updated_at = NOW() WHERE id = $2`,
          [advisorId, activityId]
        );
      } catch (e) {
        console.warn('[cita] confirmar atendida failed:', e);
      }
    }
```

The `reagendada` case is handled in step 3 by intercepting the `programFollowup` / `rawNextType` logic already present in the controller.

- [ ] **Step 3: Override `programFollowup` and `rawNextType` when `cita_status=reagendada`**

Find the line (around 945) that reads:
```javascript
    const programFollowup = String(req.body?.program_followup || '').toLowerCase() === 'yes';
```

Replace the block from that line through the `rawNextType` / `rawNextSubtype` assignments (lines ~945–963) with:

```javascript
    // reagendada forces a cita followup regardless of what radios said
    let programFollowup = String(req.body?.program_followup || '').toLowerCase() === 'yes';
    if (activity.type === 'cita' && citaStatus === 'reagendada') {
      programFollowup = true;
    }
    if (!programFollowup) {
      return res.redirect(`${leadsBase(req)}/leads/${leadId}#seguimiento`);
    }

    const scheduledAtLocal = toStr(req.body?.scheduled_at || req.body?.followup_datetime || '').trim() || null;
    if (!scheduledAtLocal) {
      return res.redirect(`${leadsBase(req)}/leads/${leadId}#seguimiento`);
    }

    // If reagendada, force next type to cita
    let rawNextType    = toStr(req.body?.next_type || req.body?.next_contact_type || '').trim();
    let rawNextSubtype = toStr(req.body?.next_subtype || req.body?.next_contact_subtype || '').trim();
    if (activity.type === 'cita' && citaStatus === 'reagendada') {
      rawNextType = 'cita';
    }
```

The rest of the function (rawNextLocationType, rawNextLocationText, etc.) remains unchanged.

- [ ] **Step 4: Commit**

```bash
git add src/controllers/advisor/crm.controller.js
git commit -m "feat: handle cita_status (atendida/reagendada) in activityOutcomeUpsert"
```

---

### Task 3: Remove standalone "Marcar como confirmada" button from show.ejs

**Files:**
- Modify: `views/advisor/crm/leads/show.ejs:1739-1752`

**Context:** The button at lines 1744–1751 now moves into the outcome modal (Task 4). The "Desconfirmar" button at lines 1739–1743 and the JS `toggleConfirmCita` / click handler at lines 4483–4520 also need to go. The `toggleConfirmCita` fetch function is no longer needed since confirmation now happens server-side via the outcome form POST. "Desconfirmar" is a low-priority feature not requested — remove it now to stay clean.

- [ ] **Step 1: Read lines 1723–1755 of show.ejs**

Verify the exact EJS block around the confirm/unconfirm buttons to understand the surrounding structure before editing.

- [ ] **Step 2: Remove the confirm/unconfirm button block**

Find the following block (around lines 1728–1753) and **delete** it entirely:

```ejs
                        <% if (a.type === 'cita') { %>
                          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:4px;">
                            <% if (a.confirmed_at) { %>
                              <span ...>✓ Confirmada</span>
                              <span style="...">
                                por <%= ... %> · <%= ... %>
                              </span>
                              <button type="button" class="btn-unconfirm-cita" ...>
                                Desconfirmar
                              </button>
                            <% } else { %>
                              <button type="button" class="btn-confirm-cita" ...>
                                <svg .../>
                                Marcar como confirmada
                              </button>
                              <span ...>El cliente confirmó asistencia</span>
                            <% } %>
                          </div>
                        <% } %>
```

Keep the `confirmed_at` display (read-only badge showing it WAS confirmed) but remove the interactive buttons. The replacement read-only block is:

```ejs
                        <% if (a.type === 'cita' && a.confirmed_at) { %>
                          <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-top:4px;">
                            <span style="display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:18px;background:#f0fdf4;color:#15803d;font-size:11px;font-weight:600;border:1px solid #bbf7d0;">
                              ✓ Cita atendida
                            </span>
                            <span style="font-size:11px;color:#64748b;">
                              por <%= (a.confirmed_by_name || '').trim() || 'asesor' %> ·
                              <%= new Date(a.confirmed_at).toLocaleString('es-MX',{timeZone:'America/Mexico_City',dateStyle:'short',timeStyle:'short'}) %>
                            </span>
                          </div>
                        <% } %>
```

- [ ] **Step 3: Remove the JS handler for `.btn-confirm-cita` / `.btn-unconfirm-cita`**

Find and delete lines 4483–4520 (the `toggleConfirmCita` function and the `document.addEventListener('click', ...)` block that references `.btn-confirm-cita` and `.btn-unconfirm-cita`):

```javascript
  function toggleConfirmCita(leadId, actId, unconfirm) { ... }

  document.addEventListener('click', function(e) {
    var confirmBtn   = e.target.closest('.btn-confirm-cita');
    var unconfirmBtn = e.target.closest('.btn-unconfirm-cita');
    if (confirmBtn) { ... }
    if (unconfirmBtn) { ... }
  });
```

Delete the entire block from `function toggleConfirmCita` through the closing `});` of the click listener.

- [ ] **Step 4: Commit**

```bash
git add views/advisor/crm/leads/show.ejs
git commit -m "refactor: remove standalone confirm-cita button — now handled inside outcome modal"
```

---

### Task 4: Add "¿Qué pasó con la cita?" section to outcome modal HTML

**Files:**
- Modify: `views/advisor/crm/leads/show.ejs:2205-2460`

**Context:** The outcome modal already has a 2-column grid (`grid-cols-1 lg:grid-cols-2`) at line 2207. We insert a new full-width section (outside the 2-column grid, above the material block) that is hidden by default and only shown when `data-act-type="cita"`. It contains two large radio buttons: "Cita Atendida" and "Reagendar cita". When "Reagendar" is selected, we also show a datetime input for the new appointment.

- [ ] **Step 1: Read lines 2205–2220 of show.ejs**

Confirm the `<form id="outcomeForm">` structure and the start of the `.grid` div.

- [ ] **Step 2: Insert the `#citaStatusSection` block**

After the `<div class="px-6 py-6 space-y-5 overflow-y-auto" ...>` opening div (line 2206) and **before** the `<div class="grid grid-cols-1 lg:grid-cols-2 gap-5">` (line 2207), insert:

```html
          <%# ── Sección solo visible cuando la actividad es CITA ── %>
          <div id="citaStatusSection" class="hidden rounded-2xl border border-teal-200 bg-teal-50 p-5 space-y-4">
            <div class="text-sm font-semibold text-slate-900">¿Qué pasó con la cita?</div>
            <p id="citaStatusError" class="text-xs text-rose-600 hidden">Selecciona una opción para continuar.</p>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label class="flex items-center gap-3 rounded-2xl border-2 border-transparent bg-white p-4 cursor-pointer hover:border-teal-300 has-[:checked]:border-teal-500 has-[:checked]:bg-teal-50">
                <input type="radio" name="cita_status" value="atendida" class="h-4 w-4 accent-teal-600">
                <div>
                  <div class="font-semibold text-slate-900">Cita Atendida</div>
                  <div class="text-xs text-slate-500">El cliente asistió a la cita.</div>
                </div>
              </label>

              <label class="flex items-center gap-3 rounded-2xl border-2 border-transparent bg-white p-4 cursor-pointer hover:border-amber-300 has-[:checked]:border-amber-400 has-[:checked]:bg-amber-50">
                <input type="radio" name="cita_status" value="reagendada" class="h-4 w-4 accent-amber-500">
                <div>
                  <div class="font-semibold text-slate-900">Reagendar cita</div>
                  <div class="text-xs text-slate-500">Hay que agendar una nueva fecha.</div>
                </div>
              </label>
            </div>

            <%# datetime + subtype for reagendada — shown via JS %>
            <div id="reagendarBlock" class="hidden mt-3 space-y-3">
              <div>
                <label class="block text-xs font-extrabold tracking-wide text-slate-500 uppercase">Nueva fecha y hora (CDMX) *</label>
                <input
                  id="reagendar_datetime"
                  name="followup_datetime"
                  type="datetime-local"
                  class="mt-2 w-full rounded-2xl border border-slate-200 bg-white p-3 text-sm text-slate-900 focus:outline-none focus:ring-4 focus:ring-amber-100 focus:border-amber-400"
                />
                <p id="reagendarDtError" class="mt-1 text-xs text-rose-600 hidden">Selecciona la nueva fecha y hora.</p>
              </div>

              <div>
                <label class="block text-xs font-extrabold tracking-wide text-slate-500 uppercase">Modalidad *</label>
                <select
                  id="reagendar_subtype"
                  name="next_contact_subtype"
                  class="mt-2 w-full rounded-2xl border border-slate-200 bg-white p-3 text-sm text-slate-900 focus:outline-none focus:ring-4 focus:ring-amber-100 focus:border-amber-400"
                >
                  <option value="">Selecciona…</option>
                  <option value="presencial">Presencial</option>
                  <option value="videollamada">Videollamada</option>
                  <option value="visita_inmueble">Visita al inmueble</option>
                </select>
                <p id="reagendarSubtypeError" class="mt-1 text-xs text-rose-600 hidden">Selecciona la modalidad.</p>
              </div>
            </div>
          </div>
```

- [ ] **Step 3: Also add a hidden input `next_contact_type` for reagendada**

Inside `#reagendarBlock`, after the subtype select, add:

```html
              <input type="hidden" name="next_contact_type" value="cita" id="reagendarTypeForcedHidden">
```

This ensures the controller reads `next_contact_type=cita` when reagendada is selected without relying solely on the JS override in the controller.

- [ ] **Step 4: Commit**

```bash
git add views/advisor/crm/leads/show.ejs
git commit -m "feat: add cita status section (atendida/reagendada) to outcome modal HTML"
```

---

### Task 5: Update modal JS to show/hide `#citaStatusSection` and validate it

**Files:**
- Modify: `views/advisor/crm/leads/show.ejs:2722-3051` (the outcome modal IIFE)

**Context:** The IIFE starts at line 2722. `btnOutcome` already has `data-act-type="<%= pendingActivityType %>"`. The `open()` function at line 2925 needs to show/hide `#citaStatusSection`. The `btnSave` click listener at line 2984 needs to validate the cita section before submitting.

- [ ] **Step 1: Read lines 2722–2740 of show.ejs**

Confirm where `activityId` and `btnOutcome` are referenced so we can read `data-act-type`.

- [ ] **Step 2: Add cita-section refs at the top of the IIFE**

After the existing ref declarations (around line 2783 where `nextErr` and `nextCitaErr` are declared), add:

```javascript
// ===== Cita status section =====
const citaStatusSection = document.getElementById('citaStatusSection');
const citaStatusRadios  = () => Array.from(document.querySelectorAll('input[name="cita_status"]'));
const reagendarBlock    = document.getElementById('reagendarBlock');
const reagendarDt       = document.getElementById('reagendar_datetime');
const reagendarDtErr    = document.getElementById('reagendarDtError');
const reagendarSubtype  = document.getElementById('reagendar_subtype');
const reagendarSubErr   = document.getElementById('reagendarSubtypeError');
const citaStatusErr     = document.getElementById('citaStatusError');
```

- [ ] **Step 3: Add `actType` variable and `isCita()` helper**

Right after the `activityId` line (line 2729):

```javascript
const actType = (btnOutcome.getAttribute('data-act-type') || '').toLowerCase();
const isCita  = () => actType === 'cita';
```

- [ ] **Step 4: Update the `open()` function to show/hide `#citaStatusSection`**

The current `open()` function (line 2925) is:
```javascript
const open = () => {
  modal.classList.remove('hidden');
  modal.classList.add('flex');
  notesErr && notesErr.classList.add('hidden');
  followupErr && followupErr.classList.add('hidden');
  applyMaterialAndExecState(activityId);
  resetNextFields();
  syncNextUI();
};
```

Replace it with:

```javascript
const open = () => {
  modal.classList.remove('hidden');
  modal.classList.add('flex');
  notesErr && notesErr.classList.add('hidden');
  followupErr && followupErr.classList.add('hidden');

  // Show/hide cita section
  if (citaStatusSection) {
    citaStatusSection.classList.toggle('hidden', !isCita());
    // reset cita radios
    citaStatusRadios().forEach(r => { r.checked = false; });
    if (reagendarBlock) reagendarBlock.classList.add('hidden');
    if (reagendarDt) reagendarDt.value = '';
    if (reagendarSubtype) reagendarSubtype.value = '';
  }

  // When cita, hide the generic followup block (followup created via reagendar section)
  if (isCita()) {
    const followupSection = document.querySelector('.rounded-2xl.border.border-slate-200.bg-slate-50.p-5:has(#followupBlock)');
    if (followupSection) followupSection.classList.add('hidden');
  }

  applyMaterialAndExecState(activityId);
  resetNextFields();
  syncNextUI();
};
```

- [ ] **Step 5: Wire reagendar radio → show/hide `#reagendarBlock`**

After the `radios.forEach(r => r.addEventListener('change', refreshFollowupUI));` line (around 2966), add:

```javascript
// Cita status radios
document.addEventListener('change', function(e) {
  const r = e.target.closest('input[name="cita_status"]');
  if (!r) return;
  const isReagendar = r.value === 'reagendada';
  if (reagendarBlock) reagendarBlock.classList.toggle('hidden', !isReagendar);
  if (citaStatusErr) citaStatusErr.classList.add('hidden');
  if (!isReagendar) {
    if (reagendarDt) reagendarDt.value = '';
    if (reagendarSubtype) reagendarSubtype.value = '';
  }
});
```

- [ ] **Step 6: Add validation for cita section in the `btnSave` click listener**

In the `btnSave` click handler (starting around line 2984), after the `let ok = true;` line and before `if (!ok) return; form.submit();`, add cita validation:

```javascript
        // ===== Validate cita section =====
        if (isCita()) {
          const selectedCitaStatus = citaStatusRadios().find(r => r.checked)?.value || '';
          if (!selectedCitaStatus) {
            citaStatusErr && citaStatusErr.classList.remove('hidden');
            ok = false;
          } else {
            citaStatusErr && citaStatusErr.classList.add('hidden');
          }
          if (selectedCitaStatus === 'reagendada') {
            const dtVal = (reagendarDt?.value || '').trim();
            if (!dtVal) {
              reagendarDtErr && reagendarDtErr.classList.remove('hidden');
              ok = false;
            } else {
              reagendarDtErr && reagendarDtErr.classList.add('hidden');
            }
            const stVal = (reagendarSubtype?.value || '').trim();
            if (!stVal) {
              reagendarSubErr && reagendarSubErr.classList.remove('hidden');
              ok = false;
            } else {
              reagendarSubErr && reagendarSubErr.classList.add('hidden');
            }
          }
        }
```

- [ ] **Step 7: Commit**

```bash
git add views/advisor/crm/leads/show.ejs
git commit -m "feat: show/hide cita status section in outcome modal JS + validation"
```

---

## Self-Review Checklist

### Spec coverage
- [x] "Sin permisos" bug → Task 1 fixes type coercion
- [x] Button inside outcome modal → Tasks 4+5 add it there
- [x] Only for CITA → `isCita()` / `activity.type === 'cita'` checks
- [x] "Cita Atendida" saves `confirmed_at` → Task 2 step 2
- [x] "Reagendar cita" creates new cita activity → Task 2 step 3 forces `program_followup=true` + `next_contact_type=cita`
- [x] Remove standalone button → Task 3

### Type consistency
- `citaStatus` (string): read in controller step 2, consumed in controller step 3
- `cita_status` (form field): matches `name="cita_status"` in Task 4
- `followup_datetime` (form field): `#reagendar_datetime` uses `name="followup_datetime"` to match what the controller already reads at line 953
- `next_contact_subtype`: `#reagendar_subtype` uses `name="next_contact_subtype"` matching controller line 963
- `next_contact_type=cita`: hidden input added in Task 4 step 3 + controller override in Task 2 step 3

### Edge cases
- If cita was already confirmed (`a.confirmed_at` set): the modal still shows but user must still select "Atendida"; a second confirm write is a no-op (idempotent UPDATE).
- `#reagendarTypeForcedHidden` sends `next_contact_type=cita` even if JS didn't run.
- When `cita_status=reagendada` without `followup_datetime`: controller already silently redirects without creating followup (line ~955).
