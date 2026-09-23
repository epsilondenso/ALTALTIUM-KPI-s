# Cita Reagendar Fix + Otra Cita Flow — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the reagendar bug (validation blocks INSERT silently) and add the "Cita Atendida → ¿Otra cita?" flow with full presencial/videollamada fields.

**Architecture:** The controller reads a new `schedule_next_cita` field and a `isReagendarOrAtendidaOtra` flag to route reads and skip/apply extras validation. The view extends `#reagendarBlock` with conditional presencial/video sections and adds a `#atendidaOtraCitaWrap` subsection under "Cita Atendida". JS wires subtype → show/hide extras and handles the new radio path.

**Tech Stack:** Node.js v24 + Express v5, PostgreSQL, EJS, Tailwind CDN, vanilla JS IIFE.

---

## File Map

| Action | File | What changes |
|--------|------|--------------|
| Modify | `src/controllers/advisor/crm.controller.js` | New `scheduleNextCita` var; `isReagendarOrAtendidaOtra` flag; read reagendar_* extras; skip extras validation for reagendada |
| Modify | `views/advisor/crm/leads/show.ejs` (HTML) | `#atendidaOtraCitaWrap` under Atendida radio; presencial/video extras in `#reagendarBlock` |
| Modify | `views/advisor/crm/leads/show.ejs` (JS IIFE) | Refs for new elements; updated cita change handler; subtype change handler; open() reset; validation |

---

### Task 1: Controller — fix reagendar bug + support atendida+otra cita

**Files:**
- Modify: `src/controllers/advisor/crm.controller.js` (function `activityOutcomeUpsert`, lines ~911–1073)

**Context:** `activityOutcomeUpsert` already reads `citaStatus`. The bug: validation at lines 1061–1069 requires `nextLocationType`/`nextPlatform`/`nextMeetingLink` even for reagendada, which doesn't include those fields (service clones them). Fix: wrap those checks in `if (citaStatus !== 'reagendada')`. New feature: when `cita_status=atendida` + `schedule_next_cita=yes`, force the same path as reagendada (programFollowup + rawNextType).

`pool` and `toStr` already imported. `activity` object available at line 889. `citaStatus` declared at line 914.

- [ ] **Step 1: Read lines 911–930 to confirm `citaStatus` declaration location**

Verify that `citaStatus` is declared at approximately line 914 and is in scope for all changes below.

- [ ] **Step 2: Add `scheduleNextCita` and `isReagendarOrAtendidaOtra` variables**

Find the `citaStatus` declaration (line ~914):
```javascript
const citaStatus = toStr(req.body?.cita_status || '').toLowerCase();
```

Add immediately after it:
```javascript
const scheduleNextCita = toStr(req.body?.schedule_next_cita || '').toLowerCase() === 'yes';
const isReagendarOrAtendidaOtra = activity.type === 'cita' &&
  (citaStatus === 'reagendada' || (citaStatus === 'atendida' && scheduleNextCita));
```

- [ ] **Step 3: Extend `programFollowup` override**

Find the existing block (lines ~961–964):
```javascript
    let programFollowup = String(req.body?.program_followup || '').toLowerCase() === 'yes';
    if (activity.type === 'cita' && citaStatus === 'reagendada') {
      programFollowup = true;
    }
```

Replace with:
```javascript
    let programFollowup = String(req.body?.program_followup || '').toLowerCase() === 'yes';
    if (isReagendarOrAtendidaOtra) {
      programFollowup = true;
    }
```

- [ ] **Step 4: Update `scheduledAtLocal` to use reagendar fields for both paths**

Find (lines ~972–976):
```javascript
    const scheduledAtLocal = toStr(
      req.body?.scheduled_at ||
      (activity.type === 'cita' && citaStatus === 'reagendada' ? req.body?.reagendar_datetime : null) ||
      req.body?.followup_datetime || ''
    ).trim() || null;
```

Replace with:
```javascript
    const scheduledAtLocal = toStr(
      req.body?.scheduled_at ||
      (isReagendarOrAtendidaOtra ? req.body?.reagendar_datetime : null) ||
      req.body?.followup_datetime || ''
    ).trim() || null;
```

- [ ] **Step 5: Update `rawNextType` and `rawNextSubtype` overrides**

Find the `rawNextSubtype` declaration (lines ~986–990) and the `rawNextType` override (lines ~992–994):
```javascript
let rawNextSubtype = toStr(
  req.body?.next_subtype ||
  (activity.type === 'cita' && citaStatus === 'reagendada' ? req.body?.reagendar_subtype : null) ||
  req.body?.next_contact_subtype || ''
).trim();
// If reagendada, force next type to cita
if (activity.type === 'cita' && citaStatus === 'reagendada') {
  rawNextType = 'cita';
}
```

Replace with:
```javascript
let rawNextSubtype = toStr(
  req.body?.next_subtype ||
  (isReagendarOrAtendidaOtra ? req.body?.reagendar_subtype : null) ||
  req.body?.next_contact_subtype || ''
).trim();
// Force next type to cita for reagendada or atendida+otra
if (isReagendarOrAtendidaOtra) {
  rawNextType = 'cita';
}
```

- [ ] **Step 6: Update location/platform reads to use reagendar_* fields**

Find (lines ~996–1000):
```javascript
const rawNextLocationType = toStr(req.body?.next_location_type || '').trim();
const rawNextLocationText = toStr(req.body?.next_location_text || '').trim();

const rawNextPlatform = toStr(req.body?.next_platform || '').trim();
const rawNextMeetingLink = toStr(req.body?.next_meeting_link || '').trim();
```

Replace with:
```javascript
const rawNextLocationType = toStr(
  (isReagendarOrAtendidaOtra ? req.body?.reagendar_location_type : null) ||
  req.body?.next_location_type || ''
).trim();
const rawNextLocationText = toStr(
  (isReagendarOrAtendidaOtra ? req.body?.reagendar_location_text : null) ||
  req.body?.next_location_text || ''
).trim();
const rawNextPlatform = toStr(
  (isReagendarOrAtendidaOtra ? req.body?.reagendar_platform : null) ||
  req.body?.next_platform || ''
).trim();
const rawNextMeetingLink = toStr(
  (isReagendarOrAtendidaOtra ? req.body?.reagendar_meeting_link : null) ||
  req.body?.next_meeting_link || ''
).trim();
```

- [ ] **Step 7: Skip presencial/videollamada extras validation for `reagendada`**

Find (lines ~1058–1072):
```javascript
// si es cita, subtype obligatorio
if (nextType === 'cita') {
  if (!nextSubtype) return fail();

  if (nextSubtype === 'presencial') {
    if (!nextLocationType) return fail();
    if (nextLocationType === 'otro' && (!nextLocationText || !nextLocationText.trim())) return fail();
  }

  if (nextSubtype === 'videollamada') {
    if (!nextPlatform) return fail();
    if (!nextMeetingLink || !nextMeetingLink.trim()) return fail();
  }

  // visita_inmueble: no requiere extras
}
```

Replace with:
```javascript
// si es cita, subtype obligatorio
if (nextType === 'cita') {
  if (!nextSubtype) return fail();

  // reagendada clones location/platform from parent via COALESCE — skip extras validation
  if (citaStatus !== 'reagendada') {
    if (nextSubtype === 'presencial') {
      if (!nextLocationType) return fail();
      if (nextLocationType === 'otro' && (!nextLocationText || !nextLocationText.trim())) return fail();
    }

    if (nextSubtype === 'videollamada') {
      if (!nextPlatform) return fail();
      if (!nextMeetingLink || !nextMeetingLink.trim()) return fail();
    }
  }

  // visita_inmueble: no requiere extras
}
```

- [ ] **Step 8: Commit**

```bash
git add src/controllers/advisor/crm.controller.js
git commit -m "fix: skip extras validation for reagendada; support atendida+otra cita in controller"
```

---

### Task 2: show.ejs HTML — add atendida subsection + presencial/video extras in reagendarBlock

**Files:**
- Modify: `views/advisor/crm/leads/show.ejs` lines ~2186–2236

**Context:** `#citaStatusSection` currently has two radios (atendida / reagendada) and `#reagendarBlock` with only datetime + subtype. Need to add:
1. `#atendidaOtraCitaWrap` (hidden div after the radios grid, inside `#citaStatusSection`) with "¿Deseas agendar otra cita?" + Yes/No radios
2. Inside `#reagendarBlock`, after the subtype select, add conditional presencial/video extras with unique `name="reagendar_*"` attributes

- [ ] **Step 1: Read lines 2186–2237 to confirm exact structure**

Confirm the structure: `#citaStatusSection` > radios grid > `#reagendarBlock`.

- [ ] **Step 2: Add `#atendidaOtraCitaWrap` inside `#citaStatusSection` after the radios grid**

Find the closing `</div>` of the radios grid (right before `<%# datetime + subtype for reagendada`):
```html
            </div>

            <%# datetime + subtype for reagendada — shown via JS %>
            <div id="reagendarBlock" class="hidden mt-3 space-y-3">
```

Insert between them:
```html
            <%# Subsección: ¿otra cita? — visible solo cuando cita_status=atendida %>
            <div id="atendidaOtraCitaWrap" class="hidden mt-3 rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
              <div class="text-xs font-extrabold tracking-wide text-slate-500 uppercase">¿Deseas agendar otra cita?</div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label class="flex items-center gap-3 rounded-2xl border-2 border-transparent bg-slate-50 p-3 cursor-pointer hover:border-slate-300 has-[:checked]:border-slate-400">
                  <input type="radio" name="schedule_next_cita" value="no" class="h-4 w-4" checked>
                  <div>
                    <div class="font-semibold text-slate-900 text-sm">No por ahora</div>
                  </div>
                </label>
                <label class="flex items-center gap-3 rounded-2xl border-2 border-transparent bg-slate-50 p-3 cursor-pointer hover:border-teal-300 has-[:checked]:border-teal-500 has-[:checked]:bg-teal-50">
                  <input type="radio" name="schedule_next_cita" value="yes" class="h-4 w-4 accent-teal-600">
                  <div>
                    <div class="font-semibold text-slate-900 text-sm">Sí, agendar otra</div>
                  </div>
                </label>
              </div>
            </div>

```

- [ ] **Step 3: Add presencial/video extras inside `#reagendarBlock` after the subtype section**

Find the closing `</div>` of the subtype section inside `#reagendarBlock` (right before the closing `</div>` of `#reagendarBlock`):
```html
                <p id="reagendarSubtypeError" class="mt-1 text-xs text-rose-600 hidden">Selecciona la modalidad.</p>
              </div>

            </div>
```

Insert the extras sections before the final `</div>` closing `#reagendarBlock`:
```html
              <%# Presencial extras — shown via JS when reagendar_subtype = presencial %>
              <div id="reagendarPresencialWrap" class="hidden rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
                <div class="text-sm font-semibold text-slate-900">Cita presencial</div>
                <div>
                  <label class="block text-xs font-extrabold tracking-wide text-slate-500 uppercase">¿Dónde será? *</label>
                  <select
                    id="reagendar_location_type"
                    name="reagendar_location_type"
                    class="mt-2 w-full rounded-2xl border border-slate-200 bg-white p-3 text-sm text-slate-900 focus:outline-none focus:ring-4 focus:ring-amber-100 focus:border-amber-400"
                  >
                    <option value="">Selecciona…</option>
                    <option value="oficinas_altaltium">Oficinas Altaltium</option>
                    <option value="otro">Otro</option>
                  </select>
                  <p id="reagendarLocTypeError" class="mt-1 text-xs text-rose-600 hidden">Selecciona el lugar.</p>
                </div>
                <div id="reagendarLocTextWrap" class="hidden">
                  <label class="block text-xs font-extrabold tracking-wide text-slate-500 uppercase">Especifica *</label>
                  <input
                    id="reagendar_location_text"
                    name="reagendar_location_text"
                    class="mt-2 w-full rounded-2xl border border-slate-200 bg-white p-3 text-sm text-slate-900 focus:outline-none focus:ring-4 focus:ring-amber-100 focus:border-amber-400"
                    placeholder="Ej. Café X, dirección, etc."
                  />
                  <p id="reagendarLocTextError" class="mt-1 text-xs text-rose-600 hidden">Especifica el lugar.</p>
                </div>
              </div>

              <%# Videollamada extras — shown via JS when reagendar_subtype = videollamada %>
              <div id="reagendarVideoWrap" class="hidden rounded-2xl border border-slate-200 bg-white p-4 space-y-3">
                <div class="text-sm font-semibold text-slate-900">Videollamada</div>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label class="block text-xs font-extrabold tracking-wide text-slate-500 uppercase">Plataforma *</label>
                    <select
                      id="reagendar_platform"
                      name="reagendar_platform"
                      class="mt-2 w-full rounded-2xl border border-slate-200 bg-white p-3 text-sm text-slate-900 focus:outline-none focus:ring-4 focus:ring-amber-100 focus:border-amber-400"
                    >
                      <option value="">Selecciona…</option>
                      <option value="whatsapp_video">Videollamada WhatsApp</option>
                      <option value="zoom">Zoom</option>
                      <option value="google_meet">Google Meet</option>
                    </select>
                    <p id="reagendarPlatformError" class="mt-1 text-xs text-rose-600 hidden">Selecciona la plataforma.</p>
                  </div>
                  <div>
                    <label class="block text-xs font-extrabold tracking-wide text-slate-500 uppercase">Link *</label>
                    <input
                      id="reagendar_meeting_link"
                      name="reagendar_meeting_link"
                      type="url"
                      class="mt-2 w-full rounded-2xl border border-slate-200 bg-white p-3 text-sm text-slate-900 focus:outline-none focus:ring-4 focus:ring-amber-100 focus:border-amber-400"
                      placeholder="https://..."
                    />
                    <p id="reagendarMeetingError" class="mt-1 text-xs text-rose-600 hidden">Ingresa el link de la reunión.</p>
                  </div>
                </div>
              </div>
```

- [ ] **Step 4: Commit**

```bash
git add views/advisor/crm/leads/show.ejs
git commit -m "feat: add atendida otra-cita subsection + presencial/video extras in reagendarBlock"
```

---

### Task 3: show.ejs JS — wire new elements, update handlers and validation

**Files:**
- Modify: `views/advisor/crm/leads/show.ejs` (outcome modal IIFE, lines ~2760–3160)

**Context:** The IIFE currently has refs for cita section elements (lines ~2819–2826) and a `document.addEventListener('change', ...)` handler for `cita_status` radios (lines ~3027–3038). Need to:
1. Add refs for 8 new elements
2. Update the `cita_status` change handler: atendida → show `#atendidaOtraCitaWrap`; reagendada → hide it
3. Add `schedule_next_cita` radio change handler
4. Add `reagendar_subtype` change handler to show/hide presencial/video extras
5. Update `open()` to reset all new elements
6. Update `btnSave` validation for atendida+otra path

- [ ] **Step 1: Add refs after existing cita refs (after line ~2826)**

Find:
```javascript
const citaStatusErr     = document.getElementById('citaStatusError');
```

Add immediately after:
```javascript
// ===== Atendida otra cita + reagendar extras =====
const atendidaOtraCitaWrap  = document.getElementById('atendidaOtraCitaWrap');
const schedNextRadios       = () => Array.from(document.querySelectorAll('input[name="schedule_next_cita"]'));
const reagendarPresWrap     = document.getElementById('reagendarPresencialWrap');
const reagendarLocType      = document.getElementById('reagendar_location_type');
const reagendarLocTypeErr   = document.getElementById('reagendarLocTypeError');
const reagendarLocTextWrap  = document.getElementById('reagendarLocTextWrap');
const reagendarLocText      = document.getElementById('reagendar_location_text');
const reagendarLocTextErr   = document.getElementById('reagendarLocTextError');
const reagendarVideoWrap    = document.getElementById('reagendarVideoWrap');
const reagendarPlatform     = document.getElementById('reagendar_platform');
const reagendarPlatformErr  = document.getElementById('reagendarPlatformError');
const reagendarMeeting      = document.getElementById('reagendar_meeting_link');
const reagendarMeetingErr   = document.getElementById('reagendarMeetingError');
```

- [ ] **Step 2: Add helper `syncReagendarExtras()`**

After the refs block, add this function (place it near the other helper functions, before `open()`):

```javascript
function syncReagendarExtras() {
  const st = reagendarSubtype?.value || '';
  const isPres = st === 'presencial';
  const isVid  = st === 'videollamada';
  show(reagendarPresWrap, isPres);
  show(reagendarVideoWrap, isVid);
  if (!isPres) {
    if (reagendarLocType) reagendarLocType.value = '';
    if (reagendarLocText) reagendarLocText.value = '';
    show(reagendarLocTextWrap, false);
  } else {
    show(reagendarLocTextWrap, reagendarLocType?.value === 'otro');
  }
  if (!isVid) {
    if (reagendarPlatform) reagendarPlatform.value = '';
    if (reagendarMeeting) reagendarMeeting.value = '';
  }
}
```

- [ ] **Step 3: Replace the existing `cita_status` change handler**

Find the existing handler (lines ~3027–3038):
```javascript
    // Cita status radio change handler
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

Replace with:
```javascript
    // Cita status radio change handler
    document.addEventListener('change', function(e) {
      const r = e.target.closest('input[name="cita_status"]');
      if (r) {
        const val = r.value;
        const isReagendar = val === 'reagendada';
        const isAtendida  = val === 'atendida';
        // Show atendida subsection only for atendida
        show(atendidaOtraCitaWrap, isAtendida);
        // Show reagendar block for reagendada; for atendida, only if "sí" is checked
        const wantsOtra = isAtendida && (schedNextRadios().find(rr => rr.checked)?.value === 'yes');
        show(reagendarBlock, isReagendar || wantsOtra);
        if (citaStatusErr) citaStatusErr.classList.add('hidden');
        // Reset fields when hiding
        if (!isReagendar && !wantsOtra) {
          if (reagendarDt) reagendarDt.value = '';
          if (reagendarSubtype) reagendarSubtype.value = '';
          syncReagendarExtras();
        }
        // Reset atendida subsection when switching away
        if (!isAtendida) {
          schedNextRadios().forEach(rr => { if (rr.value === 'no') rr.checked = true; });
        }
        return;
      }

      // schedule_next_cita radio change
      const sn = e.target.closest('input[name="schedule_next_cita"]');
      if (sn) {
        const wantsOtra = sn.value === 'yes';
        show(reagendarBlock, wantsOtra);
        if (!wantsOtra) {
          if (reagendarDt) reagendarDt.value = '';
          if (reagendarSubtype) reagendarSubtype.value = '';
          syncReagendarExtras();
        }
        return;
      }

      // reagendar_subtype change → show/hide presencial/video extras
      if (e.target === reagendarSubtype) {
        syncReagendarExtras();
        return;
      }

      // reagendar_location_type change → show/hide location text
      if (e.target === reagendarLocType) {
        show(reagendarLocTextWrap, reagendarLocType.value === 'otro');
        if (reagendarLocType.value !== 'otro' && reagendarLocText) reagendarLocText.value = '';
        return;
      }
    });
```

- [ ] **Step 4: Update `open()` reset to clear new elements**

Find the reset block inside `open()`:
```javascript
  if (citaStatusSection) {
    citaStatusSection.classList.toggle('hidden', !isCita());
    document.querySelectorAll('input[name="cita_status"]').forEach(r => { r.checked = false; });
    if (reagendarBlock) reagendarBlock.classList.add('hidden');
    if (reagendarDt) reagendarDt.value = '';
    if (reagendarSubtype) reagendarSubtype.value = '';
    if (citaStatusErr) citaStatusErr.classList.add('hidden');
    if (reagendarDtErr) reagendarDtErr.classList.add('hidden');
    if (reagendarSubErr) reagendarSubErr.classList.add('hidden');
  }
```

Replace with:
```javascript
  if (citaStatusSection) {
    citaStatusSection.classList.toggle('hidden', !isCita());
    document.querySelectorAll('input[name="cita_status"]').forEach(r => { r.checked = false; });
    // Reset atendida subsection
    show(atendidaOtraCitaWrap, false);
    schedNextRadios().forEach(rr => { if (rr.value === 'no') rr.checked = true; });
    // Reset reagendar block
    if (reagendarBlock) reagendarBlock.classList.add('hidden');
    if (reagendarDt) reagendarDt.value = '';
    if (reagendarSubtype) reagendarSubtype.value = '';
    syncReagendarExtras();
    // Clear errors
    if (citaStatusErr) citaStatusErr.classList.add('hidden');
    if (reagendarDtErr) reagendarDtErr.classList.add('hidden');
    if (reagendarSubErr) reagendarSubErr.classList.add('hidden');
    if (reagendarLocTypeErr) reagendarLocTypeErr.classList.add('hidden');
    if (reagendarLocTextErr) reagendarLocTextErr.classList.add('hidden');
    if (reagendarPlatformErr) reagendarPlatformErr.classList.add('hidden');
    if (reagendarMeetingErr) reagendarMeetingErr.classList.add('hidden');
  }
```

- [ ] **Step 5: Update `btnSave` cita validation**

Find the existing cita validation block (lines ~3074–3099):
```javascript
        // ===== Validate cita section =====
        if (isCita()) {
          const selectedCitaStatus = Array.from(document.querySelectorAll('input[name="cita_status"]')).find(r => r.checked)?.value || '';
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

Replace with:
```javascript
        // ===== Validate cita section =====
        if (isCita()) {
          const selectedCitaStatus = Array.from(document.querySelectorAll('input[name="cita_status"]')).find(r => r.checked)?.value || '';
          if (!selectedCitaStatus) {
            citaStatusErr && citaStatusErr.classList.remove('hidden');
            ok = false;
          } else {
            citaStatusErr && citaStatusErr.classList.add('hidden');
          }

          const schedNext = schedNextRadios().find(rr => rr.checked)?.value || 'no';
          const isReagendar = selectedCitaStatus === 'reagendada';
          const isAtendidaOtra = selectedCitaStatus === 'atendida' && schedNext === 'yes';

          if (isReagendar || isAtendidaOtra) {
            // Validate datetime
            const dtVal = (reagendarDt?.value || '').trim();
            if (!dtVal) {
              reagendarDtErr && reagendarDtErr.classList.remove('hidden');
              ok = false;
            } else {
              reagendarDtErr && reagendarDtErr.classList.add('hidden');
            }
            // Validate subtype
            const stVal = (reagendarSubtype?.value || '').trim();
            if (!stVal) {
              reagendarSubErr && reagendarSubErr.classList.remove('hidden');
              ok = false;
            } else {
              reagendarSubErr && reagendarSubErr.classList.add('hidden');
            }
            // For atendida+otra: also validate presencial/video extras
            if (isAtendidaOtra && stVal) {
              if (stVal === 'presencial') {
                const lt = (reagendarLocType?.value || '').trim();
                if (!lt) {
                  reagendarLocTypeErr && reagendarLocTypeErr.classList.remove('hidden');
                  ok = false;
                } else {
                  reagendarLocTypeErr && reagendarLocTypeErr.classList.add('hidden');
                }
                if (lt === 'otro') {
                  const txt = (reagendarLocText?.value || '').trim();
                  if (!txt) {
                    reagendarLocTextErr && reagendarLocTextErr.classList.remove('hidden');
                    ok = false;
                  } else {
                    reagendarLocTextErr && reagendarLocTextErr.classList.add('hidden');
                  }
                }
              }
              if (stVal === 'videollamada') {
                const plt = (reagendarPlatform?.value || '').trim();
                if (!plt) {
                  reagendarPlatformErr && reagendarPlatformErr.classList.remove('hidden');
                  ok = false;
                } else {
                  reagendarPlatformErr && reagendarPlatformErr.classList.add('hidden');
                }
                const lnk = (reagendarMeeting?.value || '').trim();
                if (!lnk) {
                  reagendarMeetingErr && reagendarMeetingErr.classList.remove('hidden');
                  ok = false;
                } else {
                  reagendarMeetingErr && reagendarMeetingErr.classList.add('hidden');
                }
              }
            }
          }
        }
```

- [ ] **Step 6: Commit**

```bash
git add views/advisor/crm/leads/show.ejs
git commit -m "feat: wire atendida otra-cita JS + reagendar extras show/hide and validation"
```

---

## Self-Review

### Spec coverage
- [x] Reagendar bug fix → Task 1 Step 7 skips extras validation when `reagendada`
- [x] New cita appears in show.ejs after reagendar → `createFollowupFromActivity` INSERT (already correct once validation passes)
- [x] Previous cita info cloned → `COALESCE` in SQL clones platform/location/property from parent
- [x] Atendida → otra cita flow → Tasks 1+2+3
- [x] Fecha/hora + modalidad + propiedad (auto) for otra cita → Task 2 + controller clones property

### Type consistency
- `isReagendarOrAtendidaOtra`: declared at Task 1 Step 2, used in Steps 3–7 — consistent
- `reagendar_*` field names: HTML `name` attrs in Task 2 match controller reads in Task 1 Step 6
- `syncReagendarExtras()`: defined in Task 3 Step 2, called in Steps 3 and 4 — consistent
- `schedNextRadios()`: arrow function returning live NodeList — safe to call multiple times

### Edge cases
- User selects "Cita Atendida" then "No por ahora" → `programFollowup` stays false → only saves outcome + `confirmed_at` → no followup created ✓
- User selects "Reagendar" with `visita_inmueble` → extras validation skipped (reagendada) → service clones location=null from parent (which may also be null — acceptable) ✓
- `#atendidaOtraCitaWrap` resets to "No" on every `open()` → clean state ✓
