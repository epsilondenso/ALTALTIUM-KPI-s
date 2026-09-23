# Cita Outcome: Reagendar Fix + "Atendida → Otra Cita" Flow

## Goal

Fix the bug where "Reagendar cita" silently fails (no new activity created), and add a "¿Agendar otra cita?" flow after confirming a cita as attended.

## Architecture

Two independent changes share the same UI building block (`#reagendarBlock`):

1. **Reagendar bug fix** — the controller skips location/platform validation when `cita_status=reagendada` because `createFollowupFromActivity` already clones those values from the parent activity via `COALESCE`.

2. **Atendida → otra cita** — when the user selects "Cita Atendida" a new sub-section appears asking "¿Deseas agendar otra cita?" (No/Sí). If Sí, `#reagendarBlock` is shown with the full cita form (datetime + subtype + conditional extras). Property is cloned from parent automatically.

## Data Flow

### Reagendar path

```
Form: cita_status=reagendada, reagendar_datetime=X, reagendar_subtype=Y
Controller: programFollowup forced true, rawNextType forced 'cita'
Controller: skip presencial/videollamada extras validation
createFollowupFromActivity: INSERT cloning platform/location/property from parent
Result: new crm_activities row appears in show.ejs activity list
```

### Atendida → otra cita path

```
Form: cita_status=atendida, schedule_next_cita=yes,
      reagendar_datetime=X, reagendar_subtype=Y,
      [next_location_type / next_location_text if presencial]
      [next_platform / next_meeting_link if videollamada]
Controller: confirmed_at set on parent activity
Controller: programFollowup forced true, rawNextType forced 'cita'
Controller: full presencial/videollamada validation applies
createFollowupFromActivity: INSERT cloning property from parent; subtype/platform/location from form
Result: new crm_activities row + confirmed badge on parent
```

### No data loss guarantees

- `createFollowupFromActivity` uses `COALESCE(NULLIF($n::text,''), a.field)` — if form value is null/empty, DB value is used
- `property_id`, `property_folio`, `property_list`, `property_folio` always cloned from parent (no form fields)
- `confirmed_at` UPDATE is wrapped in try/catch — failure is non-fatal; outcome is already saved before it runs

## Components

### `src/controllers/advisor/crm.controller.js`

- Read `schedule_next_cita` from `req.body`
- Force `programFollowup=true` when `atendida + schedule_next_cita=yes`
- Force `rawNextType='cita'` when `atendida + schedule_next_cita=yes`
- Skip presencial/videollamada extras validation when `reagendada` only

### `views/advisor/crm/leads/show.ejs` — HTML

- Inside `#citaStatusSection`, under the "Cita Atendida" label, add `#atendidaOtraCitaWrap` (hidden by default):
  - Label: "¿Deseas agendar otra cita?"
  - Two radios: `name="schedule_next_cita"` value `no` (default checked) / `yes`
- Extend `#reagendarBlock` with conditional extras:
  - `#reagendarPresencialWrap` — location_type select + optional location_text (shown when presencial)
  - `#reagendarVideoWrap` — platform select + meeting_link input (shown when videollamada)
- Add error paragraphs for new fields

### `views/advisor/crm/leads/show.ejs` — JS

- Show `#atendidaOtraCitaWrap` when cita_status = atendida
- Show `#reagendarBlock` when: reagendada OR (atendida + schedule_next_cita=yes)
- Wire subtype change → show/hide presencial/video extras inside `#reagendarBlock`
- Validation: extras required for atendida+otra; optional (not validated) for reagendada

## Constraints

- Stage-2 gate (`stage2IsLocked`) applies to both paths — reagendada and atendida+otra both require completed perfilamiento to schedule a cita
- `citaStatus` is declared before `schedule_next_cita` checks — both in scope together
- `#reagendarBlock` is shared between both paths — no duplicate HTML
- No new routes or services needed
