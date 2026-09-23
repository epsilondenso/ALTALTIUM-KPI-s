# Captura de Leads desde la Ficha Pública → CRM — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cuando un visitante de la ficha pública (`/p/:id?a=<advisorId>`) pulsa "Llamar", "WhatsApp" o "Contactar", se le pide un formulario corto (bottom sheet) y se crea/actualiza automáticamente un lead en `crm_leads`, asignado al asesor del link (o a un fallback de marketing), con notificación al asesor y su(s) manager(es).

**Architecture:** Nuevo endpoint `POST /p/:id/contacto` en `public.routes.js` → `propiedad.controller.js` → función `registrarContacto` que valida, busca duplicados, crea/actualiza el lead vía `crm.service.js` (extendiendo `createLeadEtapa1` con un flag `createdByInferred`), notifica vía `notificaciones.service.js`, y responde JSON. En el frontend (`propiedad.ejs`), 3 botones abren un bottom sheet común con CSS/JS nuevos que hacen `fetch()` al endpoint y ejecutan la acción según `intent`.

**Tech Stack:** Node.js v24, Express v5, PostgreSQL (`pg` Pool), EJS, vanilla JS/CSS.

---

## Mapa de archivos

- **Modificar:** `src/services/advisor/crm.service.js` — extender `createLeadEtapa1` con parámetro opcional `createdByInferred`.
- **Crear:** `src/services/public/contacto.service.js` — lógica de resolución de asesor, búsqueda de duplicados, creación/actualización del lead, fallback de configuración.
- **Modificar:** `src/services/notificaciones.service.js` — agregar etiqueta `lead_publico` a `_getTipoLabel`.
- **Modificar:** `src/controllers/public/propiedad.controller.js` — nuevo handler `registrarContacto`.
- **Modificar:** `src/routes/public.routes.js` — nueva ruta `POST /p/:id/contacto` con rate limiting.
- **Crear:** `src/middlewares/contactoRateLimit.js` — middleware de rate limiting en memoria.
- **Modificar:** `views/public/propiedad.ejs` — reemplazar botón único por 3 botones + bottom sheet (HTML/CSS/JS).
- **Modificar:** `CLAUDE.md` — documentar tipo de notificación `lead_publico` y endpoint nuevo.
- **SQL manual:** insertar fila en `configuracion` (clave `lead_publico_advisor_fallback_id`).

---

### Task 1: Configuración — fallback de asesor de marketing

**Files:**
- SQL manual (ejecutar en BD local y en Render vía consola/psql)

- [ ] **Step 1: Insertar la fila de configuración**

Ejecuta este SQL en la base de datos local (y luego en producción/Render):

```sql
INSERT INTO configuracion (clave, valor, descripcion)
VALUES ('lead_publico_advisor_fallback_id', '80', 'Asesor de marketing al que se asignan leads de la ficha pública sin ?a=')
ON CONFLICT (clave) DO NOTHING;
```

- [ ] **Step 2: Verificar**

```sql
SELECT * FROM configuracion WHERE clave = 'lead_publico_advisor_fallback_id';
```

Esperado: una fila con `valor = '80'`.

---

### Task 2: Extender `createLeadEtapa1` con `createdByInferred`

**Files:**
- Modify: `src/services/advisor/crm.service.js:495-571`

- [ ] **Step 1: Editar la firma y el INSERT**

Localiza la función `createLeadEtapa1` (línea 495). Cambia la firma y el valor hardcodeado de `created_by_inferred`:

```javascript
async function createLeadEtapa1(advisorId, data, createdByInferred = false) {
  const q = `
    INSERT INTO crm_leads (
      advisor_id,
      nombre, apellido, email, telefono,
      portal, mensaje, fecha, aviso, codigo_asesor,
      estado, municipio, colonia,
      tipo, operacion, precio, titulo, url_aviso,
      numero_serie,
      fecha_hora_mx,
      calle, numero_exterior, numero_interior,
      cp, portal_detalle, sitio_web, producto,
      created_by, created_by_inferred,
      created_at, updated_at
    )
    VALUES (
      $1,
      $2,$3,$4,$5,
      $6,$7,$8,$9,$10,
      $11,$12,$13,
      $14,$15,$16,$17,$18,
      $19,
      COALESCE($20, ${NOW_CDMX_SQL}),
      $21,$22,$23,
      $24,$25,$26,$27,
      $1, $28,
      NOW(), NOW()
    )
    RETURNING id
  `;
```

Y agrega el valor `$28` al final del array `values` (después de `toNull(data.producto), // $27`):

```javascript
    toNull(data.producto),       // $27
    !!createdByInferred,         // $28
  ];
```

- [ ] **Step 2: Verificar que las llamadas existentes siguen funcionando**

Busca todas las llamadas a `createLeadEtapa1(` en el código:

Run: `grep -rn "createLeadEtapa1(" "c:/Users/Eduardo Mejia/Desktop/inmovalor/src"`

Expected: solo dos resultados — la definición (línea 495) y la llamada desde `src/controllers/advisor/crm.controller.js` (sin tercer argumento). Como el nuevo parámetro tiene default `false`, esa llamada sigue creando leads con `created_by_inferred = false`, igual que antes.

- [ ] **Step 3: Commit**

```bash
git add src/services/advisor/crm.service.js
git commit -m "feat: agregar parametro createdByInferred a createLeadEtapa1"
```

---

### Task 3: Servicio `contacto.service.js` — resolución de asesor y duplicados

**Files:**
- Create: `src/services/public/contacto.service.js`

- [ ] **Step 1: Crear el archivo con la función `resolverAdvisorId`**

```javascript
'use strict';

const pool = require('../../db/pool');

const FALLBACK_ADVISOR_ID_DEFAULT = 80;

// -------------------------------------------------------------
// resolverAdvisorId(advisorIdParam)
// Devuelve el advisor_id válido a usar para el lead:
// - Si advisorIdParam corresponde a un usuario activo, lo usa.
// - Si no, usa el fallback de marketing (tabla `configuracion`,
//   clave 'lead_publico_advisor_fallback_id', default 80).
// -------------------------------------------------------------
async function resolverAdvisorId(advisorIdParam) {
  const id = Number(advisorIdParam);
  if (id) {
    const { rows } = await pool.query(
      'SELECT id FROM users WHERE id = $1 AND is_active = true LIMIT 1',
      [id]
    );
    if (rows.length) return id;
  }

  const { rows: cfgRows } = await pool.query(
    `SELECT valor FROM configuracion WHERE clave = 'lead_publico_advisor_fallback_id' LIMIT 1`
  );
  const fallback = cfgRows.length ? Number(cfgRows[0].valor) : FALLBACK_ADVISOR_ID_DEFAULT;
  return fallback || FALLBACK_ADVISOR_ID_DEFAULT;
}

module.exports = {
  resolverAdvisorId,
};
```

- [ ] **Step 2: Agregar la función `buscarLeadDuplicado`**

Agrega esta función al mismo archivo, antes de `module.exports`:

```javascript
// -------------------------------------------------------------
// buscarLeadDuplicado(telefono, advisorId)
// Busca un lead 'open' con el mismo teléfono y advisor_id.
// -------------------------------------------------------------
async function buscarLeadDuplicado(telefono, advisorId) {
  const { rows } = await pool.query(
    `SELECT id FROM crm_leads
     WHERE telefono = $1 AND advisor_id = $2 AND status = 'open'
     LIMIT 1`,
    [telefono, advisorId]
  );
  return rows.length ? rows[0].id : null;
}
```

Y actualiza `module.exports`:

```javascript
module.exports = {
  resolverAdvisorId,
  buscarLeadDuplicado,
};
```

- [ ] **Step 3: Agregar la función `actualizarLeadDuplicado`**

Agrega esta función (antes de `module.exports`):

```javascript
// -------------------------------------------------------------
// actualizarLeadDuplicado(leadId, data)
// Actualiza nombre/email/mensaje de un lead existente si los
// nuevos valores no vienen vacíos.
// -------------------------------------------------------------
async function actualizarLeadDuplicado(leadId, data) {
  await pool.query(
    `UPDATE crm_leads SET
       nombre   = COALESCE(NULLIF($2, ''), nombre),
       email    = COALESCE(NULLIF($3, ''), email),
       mensaje  = COALESCE(NULLIF($4, ''), mensaje),
       updated_at = NOW()
     WHERE id = $1`,
    [leadId, data.nombre || '', data.email || '', data.mensaje || '']
  );
}
```

Y actualiza `module.exports`:

```javascript
module.exports = {
  resolverAdvisorId,
  buscarLeadDuplicado,
  actualizarLeadDuplicado,
};
```

- [ ] **Step 4: Commit**

```bash
git add src/services/public/contacto.service.js
git commit -m "feat: agregar contacto.service para resolver asesor y duplicados de leads publicos"
```

---

### Task 4: Etiqueta de notificación `lead_publico`

**Files:**
- Modify: `src/services/notificaciones.service.js:92-111`

- [ ] **Step 1: Agregar la etiqueta**

En `_getTipoLabel`, agrega la entrada `lead_publico` al objeto `labels`:

```javascript
function _getTipoLabel(tipo) {
  const labels = {
    lead_nuevo:           'Nuevo lead',
    lead_editado:         'Lead editado',
    lead_perfilado:       'Perfilamiento',
    lead_contacto:        'Contacto registrado',
    lead_cierre:          'Cierre de venta',
    lead_perdido:         'Lead finalizado',
    actividad_crm:        'Actividad CRM',
    lead_transferido:     'Lead transferido',
    lead_traspaso:        'Traspaso de lead',
    lead_publico:         'Nuevo contacto — Ficha Pública',
    recordatorio_cita:    'Recordatorio de cita',
    recordatorio_llamada: 'Recordatorio de llamada',
    solicitud_contrato:   'Solicitud de contrato',
    contrato_actualizado:   'Contrato actualizado',
    nueva_propiedad:        'Nueva propiedad',
    inventario_actualizado: 'Inventario actualizado',
  };
  return labels[tipo] || 'Notificación';
}
```

- [ ] **Step 2: Commit**

```bash
git add src/services/notificaciones.service.js
git commit -m "feat: agregar etiqueta de notificacion lead_publico"
```

---

### Task 5: Middleware de rate limiting

**Files:**
- Create: `src/middlewares/contactoRateLimit.js`

- [ ] **Step 1: Crear el middleware**

```javascript
'use strict';

// -------------------------------------------------------------
// Rate limiting en memoria para POST /p/:id/contacto
// Máximo 5 solicitudes por minuto por IP.
// -------------------------------------------------------------
const WINDOW_MS = 60 * 1000;
const MAX_REQUESTS = 5;

const hits = new Map(); // ip -> [timestamps]

function contactoRateLimit(req, res, next) {
  const ip = req.ip || req.connection?.remoteAddress || 'unknown';
  const now = Date.now();

  const timestamps = (hits.get(ip) || []).filter(t => now - t < WINDOW_MS);
  if (timestamps.length >= MAX_REQUESTS) {
    return res.status(429).json({ ok: false, error: 'Demasiadas solicitudes. Intenta en un minuto.' });
  }

  timestamps.push(now);
  hits.set(ip, timestamps);
  next();
}

module.exports = contactoRateLimit;
```

- [ ] **Step 2: Commit**

```bash
git add src/middlewares/contactoRateLimit.js
git commit -m "feat: agregar rate limiting para endpoint de contacto publico"
```

---

### Task 6: Controller `registrarContacto`

**Files:**
- Modify: `src/controllers/public/propiedad.controller.js`

- [ ] **Step 1: Agregar imports al inicio del archivo**

Después de la línea `const driveSvc = require('../../services/googleDrive.service');`, agrega:

```javascript
const contactoSvc = require('../../services/public/contacto.service');
const crmService  = require('../../services/advisor/crm.service');
const notifService = require('../../services/notificaciones.service');
```

- [ ] **Step 2: Agregar función de validación de teléfono**

Después de la función `fmtMXN` (después de su línea de cierre `};`), agrega:

```javascript
const isValidTelefono = (v) => /^\d{10}$/.test(String(v || '').replace(/\D/g, ''));

const truncar = (v, max) => (v == null ? null : String(v).slice(0, max));

const INTENT_LABELS = {
  call: 'quiere que le llamen',
  whatsapp: 'contactó por WhatsApp',
  contact: 'envió un mensaje',
};

const INTENT_MENSAJE_DEFAULT = {
  call: 'Solicitó que le mostraran el teléfono del asesor.',
  whatsapp: 'Solicitó contacto por WhatsApp.',
  contact: 'Solicitó información por correo/formulario.',
};
```

- [ ] **Step 3: Agregar el handler `registrarContacto`**

Al final del archivo (después de `exports.show = ...` y su cierre), agrega:

```javascript
exports.registrarContacto = async (req, res) => {
  try {
    const { id } = req.params;
    const advisorIdParam = req.query.a || null;
    const { nombre, telefono, email, mensaje, intent } = req.body || {};

    if (!['call', 'whatsapp', 'contact'].includes(intent)) {
      return res.status(400).json({ ok: false, error: 'Intent inválido' });
    }
    if (!nombre || !String(nombre).trim()) {
      return res.status(400).json({ ok: false, error: 'El nombre es requerido' });
    }
    if (!isValidTelefono(telefono)) {
      return res.status(400).json({ ok: false, error: 'El teléfono debe tener 10 dígitos' });
    }

    const telLimpio = String(telefono).replace(/\D/g, '');
    const nombreLimpio = truncar(String(nombre).trim(), 200);
    const emailLimpio = email ? truncar(String(email).trim(), 100) : null;
    const mensajeLimpio = mensaje && String(mensaje).trim()
      ? truncar(String(mensaje).trim(), 1000)
      : INTENT_MENSAJE_DEFAULT[intent];

    // Propiedad (para titulo, ubicación, etc.)
    const { rows: propRows } = await pool.query(
      'SELECT * FROM inventario_outlet WHERE id::text = $1 LIMIT 1',
      [id]
    );
    if (!propRows.length) {
      return res.status(404).json({ ok: false, error: 'Propiedad no encontrada' });
    }
    const p = propRows[0];

    const baseUrl = process.env.BASE_URL || `${req.protocol}://${req.get('host')}`;
    const propertyUrl = `${baseUrl}/p/${id}${advisorIdParam ? `?a=${advisorIdParam}` : ''}`;
    const direccionCompleta = [p.calle, p.colonia, p.municipio, p.estado].filter(Boolean).join(', ');

    const advisorId = await contactoSvc.resolverAdvisorId(advisorIdParam);

    const leadData = {
      nombre: nombreLimpio,
      telefono: telLimpio,
      email: emailLimpio,
      mensaje: mensajeLimpio,
      portal: 'Ficha Pública',
      sitio_web: propertyUrl,
      producto: 'Outlet',
      titulo: p.folio || direccionCompleta,
      url_aviso: propertyUrl,
      tipo: p.tipo || null,
      municipio: p.municipio || null,
      colonia: p.colonia || null,
      estado: p.estado || null,
      calle: p.calle || null,
      precio: p.costo_total || p.precio_comercial || null,
    };

    const duplicadoId = await contactoSvc.buscarLeadDuplicado(telLimpio, advisorId);

    let leadId;
    if (duplicadoId) {
      await contactoSvc.actualizarLeadDuplicado(duplicadoId, leadData);
      leadId = duplicadoId;
    } else {
      leadId = await crmService.createLeadEtapa1(advisorId, leadData, true);

      const intentLabel = INTENT_LABELS[intent];
      const mensajeNotif = `Nuevo contacto desde tu ficha pública: ${nombreLimpio} (${intentLabel})`;
      await notifService.crearNotificacion(advisorId, 'lead_publico', mensajeNotif, `/advisor/crm/leads/${leadId}`, null);
      await notifService.notificarSupervisores(advisorId, 'lead_publico', mensajeNotif, `/manager/crm/leads/${leadId}`, null);
    }

    if (intent === 'call') {
      const { rows: aRows } = await pool.query(
        'SELECT telefono FROM users WHERE id = $1 LIMIT 1',
        [advisorId]
      );
      const advisorPhone = aRows.length ? (aRows[0].telefono || '').replace(/\D/g, '') : null;
      return res.json({ ok: true, advisorPhone });
    }

    return res.json({ ok: true });
  } catch (err) {
    console.error('❌ POST /p/:id/contacto:', err);
    return res.status(500).json({ ok: false, error: 'Error interno del servidor' });
  }
};
```

- [ ] **Step 4: Commit**

```bash
git add src/controllers/public/propiedad.controller.js
git commit -m "feat: agregar registrarContacto para crear leads desde ficha publica"
```

---

### Task 7: Ruta `POST /p/:id/contacto`

**Files:**
- Modify: `src/routes/public.routes.js`

- [ ] **Step 1: Agregar la ruta**

```javascript
'use strict';

const express  = require('express');
const router   = express.Router();
const propCtrl = require('../controllers/public/propiedad.controller');
const contactoRateLimit = require('../middlewares/contactoRateLimit');

// Página pública de propiedad — accesible sin login
// ?a=advisorId para identificar qué asesor compartió el link
router.get('/p/:id', propCtrl.show);

// Registro de contacto (Llamar / WhatsApp / Contactar) → crea/actualiza lead en CRM
router.post('/p/:id/contacto', express.json(), contactoRateLimit, propCtrl.registrarContacto);

module.exports = router;
```

- [ ] **Step 2: Verificar que `express.json()` no rompe nada**

Esta ruta usa `express.json()` localmente para no afectar el resto de la app (que puede tener su propio parser configurado distinto en `app.js`). Run: `grep -n "express.json\|bodyParser" "c:/Users/Eduardo Mejia/Desktop/inmovalor/src/app.js"` para confirmar que no hay conflicto (si ya existe un `express.json()` global, el middleware local es redundante pero inofensivo).

- [ ] **Step 3: Commit**

```bash
git add src/routes/public.routes.js
git commit -m "feat: agregar ruta POST /p/:id/contacto"
```

---

### Task 8: Frontend — 3 botones + bottom sheet

**Files:**
- Modify: `views/public/propiedad.ejs`

- [ ] **Step 1: Localizar el botón actual de WhatsApp**

Busca el bloque del botón "Hablar con un asesor" / `wa-btn` (alrededor de la línea 700-715, según el contexto de la sesión anterior). Reemplázalo por los 3 botones:

```html
<div class="contact-buttons" style="display:flex;gap:10px;flex-wrap:wrap;">
  <button type="button" class="contact-btn contact-btn-call" onclick="openContactSheet('call')">
    📞 Llamar
  </button>
  <button type="button" class="contact-btn contact-btn-wa" onclick="openContactSheet('whatsapp')">
    💬 WhatsApp
  </button>
  <button type="button" class="contact-btn contact-btn-contact" onclick="openContactSheet('contact')">
    ✉️ Contactar
  </button>
</div>
```

- [ ] **Step 2: Agregar el CSS del bottom sheet y los botones**

Agrega este bloque CSS dentro del `<style>` existente, antes del cierre `</style>`:

```css
.contact-btn{flex:1;min-width:110px;padding:12px 16px;border:none;border-radius:10px;font-weight:700;font-size:14px;cursor:pointer;transition:transform 150ms,box-shadow 150ms;}
.contact-btn:active{transform:scale(0.97);}
.contact-btn-call{background:#16302c;color:#4ddbd6;border:1px solid rgba(0,184,184,0.4);}
.contact-btn-wa{background:linear-gradient(90deg,#25D366,#1ebe5d);color:#06120f;}
.contact-btn-contact{background:linear-gradient(90deg,var(--teal),var(--teal2));color:#06120f;}

.contact-sheet-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:200;display:none;}
.contact-sheet-overlay.open{display:block;}
.contact-sheet{position:fixed;left:0;right:0;bottom:0;background:var(--card-bg,#16302c);border-top:1px solid rgba(0,184,184,0.4);border-radius:18px 18px 0 0;padding:20px;z-index:201;transform:translateY(100%);transition:transform 250ms ease;max-height:85vh;overflow-y:auto;}
.contact-sheet.open{transform:translateY(0);}
.contact-sheet-handle{width:36px;height:4px;background:rgba(255,255,255,0.2);border-radius:2px;margin:0 auto 14px;}
.contact-sheet h3{font-size:14px;font-weight:700;letter-spacing:.08em;color:var(--teal,#4ddbd6);margin-bottom:12px;}
.contact-sheet label{display:block;font-size:12px;color:#a9c5c2;margin-bottom:4px;}
.contact-sheet input,.contact-sheet textarea{width:100%;background:#0d1f1c;border:1px solid rgba(0,184,184,0.25);border-radius:8px;padding:10px;font-size:14px;color:#e6f5f3;margin-bottom:12px;box-sizing:border-box;}
.contact-sheet textarea{resize:vertical;min-height:70px;}
.contact-sheet-submit{width:100%;padding:12px;border:none;border-radius:10px;font-weight:700;font-size:14px;cursor:pointer;background:linear-gradient(90deg,var(--teal),var(--teal2));color:#06120f;}
.contact-sheet-submit:disabled{opacity:0.5;cursor:not-allowed;}
.contact-sheet-error{color:#ff8080;font-size:12px;margin-bottom:8px;display:none;}
.contact-sheet-error.show{display:block;}
.contact-sheet-result{display:none;text-align:center;padding:16px 0;}
.contact-sheet-result.show{display:block;}
.contact-sheet-result .phone-number{font-size:22px;font-weight:700;color:var(--teal,#4ddbd6);margin:10px 0;}
.contact-sheet-result a.tel-link{display:inline-block;margin-top:8px;padding:10px 20px;border-radius:10px;background:linear-gradient(90deg,var(--teal),var(--teal2));color:#06120f;font-weight:700;text-decoration:none;}
```

- [ ] **Step 3: Agregar el HTML del bottom sheet**

Justo antes del cierre `</body>`, agrega:

```html
<div id="contact-sheet-overlay" class="contact-sheet-overlay" onclick="closeContactSheet()"></div>
<div id="contact-sheet" class="contact-sheet">
  <div class="contact-sheet-handle"></div>
  <h3 id="contact-sheet-title">TUS DATOS DE CONTACTO</h3>
  <div id="contact-sheet-error" class="contact-sheet-error"></div>

  <div id="contact-sheet-form">
    <label for="cs-nombre">Nombre completo</label>
    <input type="text" id="cs-nombre" placeholder="Tu nombre"/>

    <label for="cs-telefono">Teléfono (10 dígitos)</label>
    <input type="tel" id="cs-telefono" placeholder="55XXXXXXXX" maxlength="10"/>

    <div id="cs-extra-fields" style="display:none;">
      <label for="cs-email">Email (opcional)</label>
      <input type="email" id="cs-email" placeholder="tu@email.com"/>

      <label for="cs-mensaje">Mensaje</label>
      <textarea id="cs-mensaje"></textarea>
    </div>

    <button id="contact-sheet-submit" class="contact-sheet-submit" onclick="submitContactSheet()" disabled>Continuar</button>
  </div>

  <div id="contact-sheet-result" class="contact-sheet-result"></div>
</div>
```

- [ ] **Step 4: Agregar el JS del bottom sheet**

Dentro del `<script>` existente (donde está `changePhoto` y el swipe), agrega al final:

```javascript
// Bottom sheet de contacto
let currentIntent = null;
const propertyId = <%= JSON.stringify(p.id) %>;
const advisorIdQS = <%= JSON.stringify(advisor ? (req.query.a || null) : null) %>;
const waUrlSheet = <%= JSON.stringify(waUrl) %>;
const propertyUrlSheet = <%= JSON.stringify(ogUrl) %>;
const advisorNombreSheet = <%= JSON.stringify(advisor ? advisor.nombre : 'el asesor') %>;

const SHEET_CONFIG = {
  call:     { title: 'TUS DATOS DE CONTACTO', submitLabel: 'Mostrar teléfono', extraFields: false },
  whatsapp: { title: 'TUS DATOS DE CONTACTO', submitLabel: 'Continuar a WhatsApp', extraFields: false },
  contact:  { title: 'ENVIAR MENSAJE', submitLabel: 'Enviar mensaje', extraFields: true },
};

function openContactSheet(intent) {
  currentIntent = intent;
  const cfg = SHEET_CONFIG[intent];

  document.getElementById('contact-sheet-title').textContent = cfg.title;
  document.getElementById('contact-sheet-submit').textContent = cfg.submitLabel;
  document.getElementById('cs-extra-fields').style.display = cfg.extraFields ? 'block' : 'none';
  document.getElementById('contact-sheet-error').classList.remove('show');
  document.getElementById('contact-sheet-form').style.display = 'block';
  document.getElementById('contact-sheet-result').classList.remove('show');
  document.getElementById('contact-sheet-result').innerHTML = '';

  if (cfg.extraFields) {
    document.getElementById('cs-mensaje').value =
      `Hola, me interesa la propiedad ${<%- JSON.stringify(p.folio || `#${p.id}`) %>} en ${<%- JSON.stringify(p.calle || '') %>}, ${<%- JSON.stringify(p.colonia || '') %>}. ¿Me pueden dar más información?`;
  }

  validateContactForm();
  document.getElementById('contact-sheet-overlay').classList.add('open');
  document.getElementById('contact-sheet').classList.add('open');
}

function closeContactSheet() {
  document.getElementById('contact-sheet-overlay').classList.remove('open');
  document.getElementById('contact-sheet').classList.remove('open');
}

function validateContactForm() {
  const nombre = document.getElementById('cs-nombre').value.trim();
  const telefono = document.getElementById('cs-telefono').value.trim();
  const valid = nombre.length > 0 && /^\d{10}$/.test(telefono);
  document.getElementById('contact-sheet-submit').disabled = !valid;
}

document.getElementById('cs-nombre').addEventListener('input', validateContactForm);
document.getElementById('cs-telefono').addEventListener('input', validateContactForm);

async function submitContactSheet() {
  const nombre = document.getElementById('cs-nombre').value.trim();
  const telefono = document.getElementById('cs-telefono').value.trim();
  const email = document.getElementById('cs-email').value.trim();
  const mensaje = document.getElementById('cs-mensaje').value.trim();
  const errorEl = document.getElementById('contact-sheet-error');
  const submitBtn = document.getElementById('contact-sheet-submit');

  errorEl.classList.remove('show');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Enviando...';

  let result = null;
  try {
    const qs = advisorIdQS ? `?a=${advisorIdQS}` : '';
    const resp = await fetch(`/p/${propertyId}/contacto${qs}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nombre, telefono, email, mensaje, intent: currentIntent }),
    });
    result = await resp.json();
    if (!resp.ok || !result.ok) {
      if (resp.status === 400 || resp.status === 429) {
        errorEl.textContent = result.error || 'Ocurrió un error, intenta de nuevo.';
        errorEl.classList.add('show');
        submitBtn.disabled = false;
        submitBtn.textContent = SHEET_CONFIG[currentIntent].submitLabel;
        return;
      }
      result = null; // error 500: continuar con fallback visual
    }
  } catch (e) {
    result = null; // error de red: continuar con fallback visual
  }

  document.getElementById('contact-sheet-form').style.display = 'none';
  const resultEl = document.getElementById('contact-sheet-result');
  resultEl.classList.add('show');

  if (currentIntent === 'call') {
    const phone = (result && result.advisorPhone) ? result.advisorPhone : null;
    if (phone) {
      resultEl.innerHTML = `
        <p>Comunícate con ${advisorNombreSheet}</p>
        <div class="phone-number">${phone}</div>
        <a class="tel-link" href="tel:${phone}">Llamar ahora</a>`;
    } else {
      resultEl.innerHTML = `<p>No pudimos obtener el teléfono. Intenta por WhatsApp.</p>`;
    }
  } else if (currentIntent === 'whatsapp') {
    if (waUrlSheet) {
      window.open(waUrlSheet, '_blank');
    }
    resultEl.innerHTML = `<p>Abriendo WhatsApp...</p>`;
    closeContactSheet();
  } else {
    resultEl.innerHTML = `<p>¡Listo! ${advisorNombreSheet} te contactará pronto.</p>`;
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add views/public/propiedad.ejs
git commit -m "feat: agregar 3 botones de contacto y bottom sheet en ficha publica"
```

---

### Task 9: Documentación — `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Agregar el tipo de notificación a la tabla existente**

En la sección `## SISTEMA DE NOTIFICACIONES (SSE)`, agrega una fila a la tabla "Tipos implementados":

```markdown
| lead_publico | advisor (o fallback marketing) + sus managers |
```

- [ ] **Step 2: Documentar el endpoint nuevo**

En la sección `## ESTRUCTURA DE ARCHIVOS CLAVE` o cerca de las rutas públicas, agrega una nota:

```markdown
### Ficha pública — captura de leads
`POST /p/:id/contacto` — recibe `{ nombre, telefono, email, mensaje, intent }`
(`intent`: `call` | `whatsapp` | `contact`), crea/actualiza lead en `crm_leads`
asignado al asesor del `?a=` o al fallback (`configuracion.lead_publico_advisor_fallback_id`, default 80).
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: documentar tipo lead_publico y endpoint POST /p/:id/contacto"
```

---

### Task 10: Verificación manual en local

**Files:**
- Ninguno (solo pruebas)

- [ ] **Step 1: Reiniciar el servidor local**

```bash
PID=$(netstat -ano | grep ":3000 " | grep LISTENING | head -1 | awk '{print $5}')
taskkill //F //PID $PID
cd "c:/Users/Eduardo Mejia/Desktop/inmovalor" && (npm start > /tmp/server.log 2>&1 &)
sleep 4
```

- [ ] **Step 2: Probar el flujo "Contactar" con un asesor real (?a=)**

Abre en el navegador: `http://localhost:3000/p/<id-de-propiedad-outlet>?a=<advisor-id-real>`

1. Clic en "✉️ Contactar" → llenar Nombre + Teléfono (10 dígitos) + Mensaje → "Enviar mensaje".
2. Verificar mensaje de confirmación "¡Listo! ... te contactará pronto."
3. Verificar en BD:

```sql
SELECT id, advisor_id, nombre, telefono, mensaje, portal, producto, created_by_inferred
FROM crm_leads ORDER BY id DESC LIMIT 1;
```

Esperado: `advisor_id` = el asesor del `?a=`, `created_by_inferred = true`, `portal = 'Ficha Pública'`.

- [ ] **Step 3: Probar duplicado (mismo teléfono, mismo asesor)**

Repetir el envío con el mismo teléfono y mismo `?a=`. Verificar que **no se crea una segunda fila** (mismo `id` de lead, `updated_at` cambia).

- [ ] **Step 4: Probar sin `?a=` (fallback)**

Abre `http://localhost:3000/p/<id-de-propiedad-outlet>` (sin `?a=`), repetir el flujo de "Contactar" con un teléfono nuevo. Verificar:

```sql
SELECT advisor_id FROM crm_leads ORDER BY id DESC LIMIT 1;
```

Esperado: `advisor_id = 80` (o el valor configurado en `configuracion`).

- [ ] **Step 5: Probar "📞 Llamar"**

Con `?a=<advisor-id-real>` (que tenga `telefono` no nulo en `users`), clic en "📞 Llamar" → llenar Nombre + Teléfono → "Mostrar teléfono". Verificar que aparece el número del asesor y el botón "Llamar ahora" (`tel:`).

- [ ] **Step 6: Probar "💬 WhatsApp"**

Clic en "💬 WhatsApp" → llenar Nombre + Teléfono → "Continuar a WhatsApp". Verificar que se abre una nueva pestaña a `wa.me` con el mensaje, y que el lead se creó/actualizó igual que los otros casos.

- [ ] **Step 7: Verificar notificaciones**

Inicia sesión como el asesor del `?a=` usado en el Step 2 (otra pestaña/navegador) y revisa la campana de notificaciones: debe aparecer "Nuevo contacto desde tu ficha pública: ... (envió un mensaje)" con link a `/advisor/crm/leads/<id>`. Repite con el manager de ese asesor.

- [ ] **Step 8: Probar rate limiting**

Enviar el formulario 6 veces seguidas en menos de un minuto (mismo navegador). La 6ª solicitud debe responder con error 429 / mensaje "Demasiadas solicitudes. Intenta en un minuto." sin romper la UI.

---

## Self-Review (completado durante la escritura del plan)

- **Cobertura del spec:** Sección 2 (UX) → Task 8. Sección 3 (endpoint/lógica) → Tasks 2,3,6,7. Sección 4 (notificaciones) → Tasks 4,6. Sección 5 (errores) → Task 6 + Task 8 Step 4 (fallbacks de `call`/`whatsapp`/`contact`). Sección 6 (seguridad) → Task 5 (rate limit) y Task 6 (truncado de longitud). Sección 7 (testing) → Task 10. Sección 8 (configuración) → Task 1, Task 9.
- **Placeholders:** ninguno — todos los pasos incluyen código completo.
- **Consistencia de nombres:** `resolverAdvisorId`, `buscarLeadDuplicado`, `actualizarLeadDuplicado` (contacto.service.js) se usan con esos mismos nombres en Task 6. `createLeadEtapa1(advisorId, leadData, true)` coincide con la nueva firma de Task 2. `intent` (`call`/`whatsapp`/`contact`) consistente entre frontend (Task 8) y backend (Task 6).
