# Bloques Horarios para 2do+ Contacto CRM — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar validación de bloques horarios para el 2do contacto en adelante en el CRM, tanto para asesores como para managers.

**Architecture:** El controller pasa `lastActivityAt` (scheduled_at de la última actividad) a la vista. La vista reemplaza el input de hora libre con un selector de bloque (6 opciones) seguido de un selector de hora dentro del bloque (slots de 30 min). El submit valida en cliente y servidor que la hora caiga en un bloque posterior al de la última actividad si es el mismo día, o cualquier bloque si es día diferente.

**Tech Stack:** Node.js/Express v5, EJS server-side rendering, Tailwind CSS, JavaScript vanilla (no frameworks)

---

## Bloques horarios (orden cronológico dentro de un día)

```
Bloque 5 → 12:00 AM – 4:00 AM   (startH: 0,  endH: 4)
Bloque 6 →  4:00 AM – 8:00 AM   (startH: 4,  endH: 8)
Bloque 1 →  8:00 AM – 12:00 PM  (startH: 8,  endH: 12)
Bloque 2 → 12:00 PM – 4:00 PM   (startH: 12, endH: 16)
Bloque 3 →  4:00 PM – 8:00 PM   (startH: 16, endH: 20)
Bloque 4 →  8:00 PM – 12:00 AM  (startH: 20, endH: 24)
```

Regla:
- **Mismo día que última actividad**: solo bloques con índice cronológico MAYOR al de la última actividad
- **Día diferente (posterior)**: todos los 6 bloques disponibles

---

## Archivos a modificar

| Archivo | Cambio |
|---|---|
| `src/controllers/advisor/crm.controller.js` | `contactForm`: pasar `lastActivityAt`; `contactSubmit`: agregar validación de bloque |
| `views/advisor/crm/leads/contact.ejs` | Agregar variable JS `LAST_ACTIVITY_AT_ISO`, selector de bloque, card de error, lógica JS |
| `src/controllers/manager/crm.controller.js` | `contactForm`: pasar `lastActivityAt`; `contactSubmit`: agregar validación de bloque |
| `views/manager/crm/leads/contact.ejs` | Mismos cambios que la vista del asesor |

---

## Task 1: Controller advisor — pasar `lastActivityAt` a la vista

**Files:**
- Modify: `src/controllers/advisor/crm.controller.js:936-962`

- [ ] **Step 1: Leer `lastActivityAt` de la primera actividad (DESC)**

En `exports.contactForm` (línea ~936), justo después de:
```javascript
const activities = await crmService.listActivitiesByLead(leadId, advisorId);
const isFirst = !activities || activities.length === 0;
```

Agregar:
```javascript
const lastAct = !isFirst ? activities[0] : null;
const lastActivityAt = lastAct
  ? (lastAct.scheduled_at || lastAct.created_at || null)
  : null;
```

- [ ] **Step 2: Pasar `lastActivityAt` al render**

En el objeto de `res.render` (línea ~948), agregar junto a `transferredAt`:
```javascript
transferredAt: transferredAt ? new Date(transferredAt).toISOString() : null,
lastActivityAt: lastActivityAt ? new Date(lastActivityAt).toISOString() : null,
```

- [ ] **Step 3: Verificar en localhost**

Abrir `http://localhost:3000/advisor/leads/<id>/contact` de un lead con actividades.
No debe haber errores en consola del servidor.

---

## Task 2: Vista advisor — agregar variable JS y card de error

**Files:**
- Modify: `views/advisor/crm/leads/contact.ejs:547-550` (bloque de variables JS al tope del `<script>`)
- Modify: `views/advisor/crm/leads/contact.ejs:186` (después del último `<% if (q && q.error ...) %>`)

- [ ] **Step 1: Agregar variable `LAST_ACTIVITY_AT_ISO` al bloque de constantes JS**

Localizar (línea ~547):
```javascript
const CALL_ONLY = <%- JSON.stringify(CALL_ONLY) %>;
const IS_FIRST_CONTACT = <%- JSON.stringify(IS_FIRST) %>;
const TRANSFERRED_AT_ISO = <%- JSON.stringify(typeof transferredAt !== 'undefined' ? transferredAt : null) %>;
const IS_EDIT = <%- JSON.stringify(isEdit) %>;
```

Agregar después de `IS_EDIT`:
```javascript
const LAST_ACTIVITY_AT_ISO = <%- JSON.stringify(typeof lastActivityAt !== 'undefined' ? lastActivityAt : null) %>;
```

- [ ] **Step 2: Agregar card de error `bloque_invalido`**

Localizar el último bloque de error (alrededor de línea 186):
```ejs
<% if (q && q.error === 'hora_pasada') { %>
```

Agregar ANTES de ese bloque:
```ejs
<% if (q && q.error === 'bloque_invalido') { %>
  <div class="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-5">
    <p class="text-[11px] tracking-[0.22em] text-rose-700 font-extrabold uppercase">Bloque horario no disponible</p>
    <p class="mt-1 text-sm text-rose-900 font-semibold">La hora seleccionada pertenece a un bloque ya utilizado hoy.</p>
    <p class="mt-1 text-xs text-rose-800/80">Elige un bloque horario posterior al de tu último contacto, o selecciona una fecha diferente.</p>
  </div>
<% } %>
```

---

## Task 3: Vista advisor — selector de bloque en JS (`applyDateTimeConstraints`)

**Files:**
- Modify: `views/advisor/crm/leads/contact.ejs:681-684` (bloque `else` de `applyDateTimeConstraints`)

- [ ] **Step 1: Reemplazar el bloque `else` de `applyDateTimeConstraints`**

Localizar (línea ~681):
```javascript
      } else {
        // SEGUNDO CONTACTO EN ADELANTE: fecha = hoy o futuro, hora = libre
        if (dateEl) { dateEl.min = todayCDMX; }
      }
```

Reemplazar con:
```javascript
      } else {
        // SEGUNDO CONTACTO EN ADELANTE: fecha = hoy o futuro, bloque horario
        if (dateEl) { dateEl.min = todayCDMX; }

        if (timeEl && !IS_EDIT) {
          // Ocultar input nativo de hora
          timeEl.style.display = 'none';
          timeEl.removeAttribute('data-required');

          const BLOQUES = [
            { id: 5, label: 'Bloque 5 — 12:00 AM a 4:00 AM',  startH: 0,  endH: 4  },
            { id: 6, label: 'Bloque 6 — 4:00 AM a 8:00 AM',   startH: 4,  endH: 8  },
            { id: 1, label: 'Bloque 1 — 8:00 AM a 12:00 PM',  startH: 8,  endH: 12 },
            { id: 2, label: 'Bloque 2 — 12:00 PM a 4:00 PM',  startH: 12, endH: 16 },
            { id: 3, label: 'Bloque 3 — 4:00 PM a 8:00 PM',   startH: 16, endH: 20 },
            { id: 4, label: 'Bloque 4 — 8:00 PM a 12:00 AM',  startH: 20, endH: 24 },
          ];

          const getBloqueIdFromHour = (h) => {
            if (h < 4)  return 5;
            if (h < 8)  return 6;
            if (h < 12) return 1;
            if (h < 16) return 2;
            if (h < 20) return 3;
            return 4;
          };

          let lastDate = null;
          let lastBloqueId = null;

          if (LAST_ACTIVITY_AT_ISO) {
            const lastDt = new Date(LAST_ACTIVITY_AT_ISO);
            lastDate = new Intl.DateTimeFormat('en-CA', {
              timeZone: 'America/Mexico_City',
              year: 'numeric', month: '2-digit', day: '2-digit'
            }).format(lastDt);
            const lastHour = parseInt(new Intl.DateTimeFormat('en-GB', {
              timeZone: 'America/Mexico_City', hour: '2-digit', hour12: false
            }).format(lastDt), 10);
            lastBloqueId = getBloqueIdFromHour(lastHour);
          }

          // --- Crear select de bloques ---
          const bloqueSelect = document.createElement('select');
          bloqueSelect.id = 'bloque-select';
          bloqueSelect.className = timeEl.className;
          bloqueSelect.setAttribute('data-required', '1');

          const defOpt = document.createElement('option');
          defOpt.value = '';
          defOpt.textContent = 'Selecciona bloque horario';
          bloqueSelect.appendChild(defOpt);

          BLOQUES.forEach(b => {
            const opt = document.createElement('option');
            opt.value = b.id;
            opt.textContent = b.label;
            bloqueSelect.appendChild(opt);
          });

          // --- Crear select de hora dentro del bloque ---
          const bloqueTimeLabel = document.createElement('label');
          bloqueTimeLabel.className = 'text-xs font-semibold text-slate-700 mt-3 block';
          bloqueTimeLabel.textContent = 'Hora dentro del bloque *';

          const bloqueTimeSelect = document.createElement('select');
          bloqueTimeSelect.id = 'bloque-time-select';
          bloqueTimeSelect.className = timeEl.className + ' mt-2';
          bloqueTimeSelect.setAttribute('data-required', '1');
          bloqueTimeSelect.style.display = 'none';

          // Poblar slots de hora (cada 30 min) para un bloque
          function populateBloqueSlots(bloqueId) {
            const b = BLOQUES.find(x => x.id === parseInt(bloqueId, 10));
            if (!b) { bloqueTimeSelect.style.display = 'none'; return; }
            bloqueTimeSelect.innerHTML = '';
            for (let h = b.startH; h < b.endH; h++) {
              [0, 30].forEach(m => {
                const hh = String(h).padStart(2, '0');
                const mm = String(m).padStart(2, '0');
                const val = `${hh}:${mm}`;
                const label = new Date(`2000-01-01T${val}:00`).toLocaleTimeString('es-MX', {
                  hour: '2-digit', minute: '2-digit', hour12: true
                });
                const opt = document.createElement('option');
                opt.value = val;
                opt.textContent = label;
                bloqueTimeSelect.appendChild(opt);
              });
            }
            bloqueTimeSelect.style.display = '';
            if (timeEl) timeEl.value = bloqueTimeSelect.value;
            syncScheduledAt();
          }

          // Calcular bloques disponibles según fecha elegida
          function getAvailableBloqueIds(selectedDate) {
            if (!lastDate || selectedDate !== lastDate) return BLOQUES.map(b => b.id);
            const lastIdx = BLOQUES.findIndex(b => b.id === lastBloqueId);
            return BLOQUES.filter((_, idx) => idx > lastIdx).map(b => b.id);
          }

          // Actualizar opciones deshabilitadas del select de bloques
          function updateBloqueOptions() {
            const selDate = normalize(dateEl?.value);
            if (!selDate) return;
            const available = getAvailableBloqueIds(selDate);
            Array.from(bloqueSelect.options).forEach(opt => {
              if (!opt.value) return;
              opt.disabled = !available.includes(parseInt(opt.value, 10));
              opt.style.color = opt.disabled ? '#94a3b8' : '';
            });
            // Si la selección actual quedó inválida, limpiar
            if (bloqueSelect.value && !available.includes(parseInt(bloqueSelect.value, 10))) {
              bloqueSelect.value = '';
              bloqueTimeSelect.style.display = 'none';
              if (timeEl) timeEl.value = '';
              syncScheduledAt();
            }
          }

          bloqueSelect.addEventListener('change', () => {
            if (!bloqueSelect.value) {
              bloqueTimeSelect.style.display = 'none';
              if (timeEl) timeEl.value = '';
              syncScheduledAt();
              return;
            }
            populateBloqueSlots(bloqueSelect.value);
          });

          bloqueTimeSelect.addEventListener('change', () => {
            if (timeEl) timeEl.value = bloqueTimeSelect.value;
            syncScheduledAt();
          });

          if (dateEl) dateEl.addEventListener('change', updateBloqueOptions);

          // Insertar en el DOM (en lugar del input de hora)
          timeEl.parentNode.insertBefore(bloqueSelect, timeEl.nextSibling);
          timeEl.parentNode.insertBefore(bloqueTimeLabel, bloqueSelect.nextSibling);
          timeEl.parentNode.insertBefore(bloqueTimeSelect, bloqueTimeLabel.nextSibling);

          // Aplicar estado inicial si ya hay fecha
          if (dateEl?.value) updateBloqueOptions();
        }
      }
```

- [ ] **Step 2: Verificar en localhost**

Abrir `/advisor/leads/<id>/contact` de un lead con al menos 1 actividad.
Debe aparecer "Selecciona bloque horario" en lugar del input de hora.
Al seleccionar fecha y bloque, debe aparecer el selector de hora dentro del bloque.

---

## Task 4: Vista advisor — validación cliente en submit

**Files:**
- Modify: `views/advisor/crm/leads/contact.ejs:829-835` (bloque `else` de la validación submit)

- [ ] **Step 1: Reemplazar el bloque `else` de la validación de submit**

Localizar (línea ~829):
```javascript
      } else {
        // SEGUNDO CONTACTO EN ADELANTE: fecha >= hoy (no días anteriores)
        if (dateVal < todayNaive) {
          showError(`No puedes registrar contactos en días anteriores a hoy (${todayNaive.split('-').reverse().join('/')}).`);
          return;
        }
      }
```

Reemplazar con:
```javascript
      } else {
        // SEGUNDO CONTACTO EN ADELANTE
        if (dateVal < todayNaive) {
          showError(`No puedes registrar contactos en días anteriores a hoy (${todayNaive.split('-').reverse().join('/')}).`);
          return;
        }

        // Validar bloque horario
        if (LAST_ACTIVITY_AT_ISO) {
          const BLOQUES = [
            { id: 5, startH: 0,  endH: 4  },
            { id: 6, startH: 4,  endH: 8  },
            { id: 1, startH: 8,  endH: 12 },
            { id: 2, startH: 12, endH: 16 },
            { id: 3, startH: 16, endH: 20 },
            { id: 4, startH: 20, endH: 24 },
          ];
          const getBloqueFromHour = (h) => {
            if (h < 4)  return 5;
            if (h < 8)  return 6;
            if (h < 12) return 1;
            if (h < 16) return 2;
            if (h < 20) return 3;
            return 4;
          };
          const lastDt = new Date(LAST_ACTIVITY_AT_ISO);
          const lastDateStr = new Intl.DateTimeFormat('en-CA', {
            timeZone: 'America/Mexico_City',
            year: 'numeric', month: '2-digit', day: '2-digit'
          }).format(lastDt);
          const lastHour = parseInt(new Intl.DateTimeFormat('en-GB', {
            timeZone: 'America/Mexico_City', hour: '2-digit', hour12: false
          }).format(lastDt), 10);
          const lastBloqueId = getBloqueFromHour(lastHour);

          if (dateVal === lastDateStr) {
            // Mismo día: validar bloque
            const schedHour = parseInt(timeVal.split(':')[0], 10);
            const schedBloqueId = getBloqueFromHour(schedHour);
            const lastIdx = BLOQUES.findIndex(b => b.id === lastBloqueId);
            const schedIdx = BLOQUES.findIndex(b => b.id === schedBloqueId);
            if (schedIdx <= lastIdx) {
              showError('La hora seleccionada pertenece a un bloque ya utilizado hoy. Elige un bloque posterior o una fecha diferente.');
              return;
            }
          }
        }
      }
```

- [ ] **Step 2: Verificar en localhost**

1. Lead con última actividad a las 3:00 PM (Bloque 2), fecha hoy.
2. Intentar registrar nueva actividad hoy en Bloque 2 o Bloque 1 → debe mostrar error.
3. Registrar en Bloque 3 (4pm-8pm) → debe pasar.
4. Registrar en fecha de mañana, cualquier bloque → debe pasar.

---

## Task 5: Controller advisor — validación servidor en `contactSubmit`

**Files:**
- Modify: `src/controllers/advisor/crm.controller.js:1067-1073`

- [ ] **Step 1: Reemplazar el bloque `else` de validación de fecha/hora en `contactSubmit`**

Localizar (línea ~1067):
```javascript
        } else {
          // SEGUNDO CONTACTO EN ADELANTE: no puede ser fecha anterior a hoy
          if (schedDate < todayNaive) {
            console.warn(`[contactSubmit] fecha en el pasado — leadId=${leadId} sched=${schedStr} hoy=${todayNaive}`);
            return res.redirect(`${leadsBase(req)}/leads/${leadId}/contact?error=fecha_invalida`);
          }
        }
```

Reemplazar con:
```javascript
        } else {
          // SEGUNDO CONTACTO EN ADELANTE
          if (schedDate < todayNaive) {
            console.warn(`[contactSubmit] fecha en el pasado — leadId=${leadId} sched=${schedStr} hoy=${todayNaive}`);
            return res.redirect(`${leadsBase(req)}/leads/${leadId}/contact?error=fecha_invalida`);
          }

          // Validar bloque horario
          const lastActForBlock = activitiesForFirst.length > 0 ? activitiesForFirst[0] : null;
          if (lastActForBlock) {
            const lastAt = lastActForBlock.scheduled_at || lastActForBlock.created_at;
            if (lastAt) {
              const fmtDateOnly = (d) => new Intl.DateTimeFormat('en-CA', {
                timeZone: 'America/Mexico_City',
                year: 'numeric', month: '2-digit', day: '2-digit'
              }).format(d);
              const getHourCdmx = (d) => parseInt(new Intl.DateTimeFormat('en-GB', {
                timeZone: 'America/Mexico_City', hour: '2-digit', hour12: false
              }).format(d), 10);
              const getBloqueFromHour = (h) => {
                if (h < 4)  return 5;
                if (h < 8)  return 6;
                if (h < 12) return 1;
                if (h < 16) return 2;
                if (h < 20) return 3;
                return 4;
              };
              const BLOQUE_ORDER = [5, 6, 1, 2, 3, 4];

              const lastDt = new Date(lastAt);
              const lastDateStr = fmtDateOnly(lastDt);

              if (schedDate === lastDateStr) {
                const lastHour = getHourCdmx(lastDt);
                const schedHour = parseInt(schedStr.slice(11, 13), 10);
                const lastBloqueId = getBloqueFromHour(lastHour);
                const schedBloqueId = getBloqueFromHour(schedHour);
                const lastIdx = BLOQUE_ORDER.indexOf(lastBloqueId);
                const schedIdx = BLOQUE_ORDER.indexOf(schedBloqueId);

                if (schedIdx <= lastIdx) {
                  console.warn(`[contactSubmit] bloque inválido — leadId=${leadId} lastBloque=${lastBloqueId} schedBloque=${schedBloqueId}`);
                  return res.redirect(`${leadsBase(req)}/leads/${leadId}/contact?error=bloque_invalido`);
                }
              }
            }
          }
        }
```

- [ ] **Step 2: Reiniciar servidor y verificar**

```
npm run dev
```

Enviar POST directamente con hora en bloque inválido (mismo día, bloque anterior).
Debe redirigir con `?error=bloque_invalido` y mostrar la card roja.

---

## Task 6: Controller manager — pasar `lastActivityAt` y validar bloque

**Files:**
- Modify: `src/controllers/manager/crm.controller.js:588-607` (contactForm)
- Modify: `src/controllers/manager/crm.controller.js:610-660` (contactSubmit)

- [ ] **Step 1: Agregar `lastActivityAt` en `contactForm` del manager**

Localizar (línea ~588):
```javascript
    const activities = await crmService.listActivitiesByLead(leadId, managerId);
    const isFirst = !activities || activities.length === 0;

    return res.render('manager/crm/leads/contact', {
```

Agregar entre esas dos líneas:
```javascript
    const lastActM = !isFirst ? activities[0] : null;
    const lastActivityAt = lastActM
      ? (lastActM.scheduled_at || lastActM.created_at || null)
      : null;
```

Y en el objeto de render agregar:
```javascript
      lastActivityAt: lastActivityAt ? new Date(lastActivityAt).toISOString() : null,
```

- [ ] **Step 2: Agregar validación de bloque en `contactSubmit` del manager**

Localizar (línea ~637 en manager/crm.controller.js):
```javascript
    await crmService.createActivity(leadId, managerId, req.body || {});
```

Agregar ANTES de esa línea:
```javascript
    // Validar bloque horario para 2do+ contacto
    {
      const activitiesM = await crmService.listActivitiesByLead(leadId, managerId);
      const isFirstM = !activitiesM || activitiesM.length === 0;
      const schedStr = (req.body?.scheduled_at || '').trim().slice(0, 19);

      if (!isFirstM && schedStr) {
        const fmtCdmxNaive = (d) => {
          const dd = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Mexico_City', year: 'numeric', month: '2-digit', day: '2-digit' }).format(d);
          const tt = new Intl.DateTimeFormat('en-GB', { timeZone: 'America/Mexico_City', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }).format(d);
          return `${dd}T${tt}`;
        };
        const fmtDateOnly = (d) => fmtCdmxNaive(d).slice(0, 10);
        const getHourCdmx = (d) => parseInt(new Intl.DateTimeFormat('en-GB', {
          timeZone: 'America/Mexico_City', hour: '2-digit', hour12: false
        }).format(d), 10);
        const getBloqueFromHour = (h) => {
          if (h < 4) return 5; if (h < 8) return 6;
          if (h < 12) return 1; if (h < 16) return 2;
          if (h < 20) return 3; return 4;
        };
        const BLOQUE_ORDER = [5, 6, 1, 2, 3, 4];

        const lastActM = activitiesM[0];
        const lastAt = lastActM.scheduled_at || lastActM.created_at;
        if (lastAt) {
          const lastDt = new Date(lastAt);
          const schedDate = schedStr.slice(0, 10);
          const lastDateStr = fmtDateOnly(lastDt);

          if (schedDate === lastDateStr) {
            const lastHour = getHourCdmx(lastDt);
            const schedHour = parseInt(schedStr.slice(11, 13), 10);
            const lastBloqueId = getBloqueFromHour(lastHour);
            const schedBloqueId = getBloqueFromHour(schedHour);
            const lastIdx = BLOQUE_ORDER.indexOf(lastBloqueId);
            const schedIdx = BLOQUE_ORDER.indexOf(schedBloqueId);

            if (schedIdx <= lastIdx) {
              console.warn(`[manager contactSubmit] bloque inválido — leadId=${leadId}`);
              return res.redirect(`/manager/crm/leads/${leadId}/contact?error=bloque_invalido`);
            }
          }
        }
      }
    }
```

---

## Task 7: Vista manager — mismos cambios que la vista advisor

**Files:**
- Modify: `views/manager/crm/leads/contact.ejs`

- [ ] **Step 1: Agregar `LAST_ACTIVITY_AT_ISO` al bloque de variables JS**

Localizar el bloque `<script>` donde están las constantes JS en la vista manager (buscar `IS_FIRST` o `CALL_ONLY`).
Agregar:
```javascript
const LAST_ACTIVITY_AT_ISO = <%- JSON.stringify(typeof lastActivityAt !== 'undefined' ? lastActivityAt : null) %>;
```

- [ ] **Step 2: Agregar card de error `bloque_invalido`**

Agregar la misma card que en la vista advisor (Task 2, Step 2) en el área de cards de error de la vista manager.

- [ ] **Step 3: Agregar lógica de bloque selector en `applyDateTimeConstraints`**

Copiar exactamente el bloque `else` implementado en Task 3 Step 1 en la misma función de la vista manager.

- [ ] **Step 4: Agregar validación cliente en submit**

Copiar exactamente el bloque `else` implementado en Task 4 Step 1 en la función de submit de la vista manager.

- [ ] **Step 5: Verificar en localhost**

Abrir `/manager/crm/leads/<id>/contact` con un lead que tenga actividades.
Mismo comportamiento que la vista advisor: selector de bloque, validación al cambiar fecha, error en submit inválido.

---

## Pruebas manuales de aceptación

| Escenario | Resultado esperado |
|---|---|
| Lead sin actividades (1er contacto) | No aparece selector de bloques; flujo normal |
| 2do contacto, misma fecha, bloque anterior | Error "Bloque horario no disponible" |
| 2do contacto, misma fecha, mismo bloque | Error "Bloque horario no disponible" |
| 2do contacto, misma fecha, bloque posterior | Permite guardar |
| 2do contacto, fecha diferente, cualquier bloque | Permite guardar |
| Última actividad en Bloque 4 (8pm-12am), misma fecha | Ningún bloque disponible hoy |
| POST directo con bloque inválido (bypass cliente) | Servidor redirige con `?error=bloque_invalido` |
