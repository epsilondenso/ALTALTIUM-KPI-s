# Recursos Digitales — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Recursos Digitales" section to /documents with a WA Business gallery — admins configure Google Drive folder IDs per product, users browse and download images as ZIP.

**Architecture:** New dedicated routes and controllers; folder IDs stored in the existing `configuracion` table; images served via the existing Drive proxy (`/media/drive/:id`); ZIP streaming via `archiver`. No new DB tables.

**Tech Stack:** Node.js v24 + Express v5, PostgreSQL (`configuracion` table), EJS + express-ejs-layouts, Tailwind CDN, Google Drive API v3 (existing service account), `archiver` npm package (already installed).

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `src/controllers/admin/recursos.controller.js` | Read/save 6 folder IDs in `configuracion` |
| Modify | `src/routes/admin.routes.js` | Mount 2 admin routes |
| Modify | `views/admin/partials/sidebar.ejs` | Add "Recursos Digitales" link |
| Create | `views/admin/recursos-digitales/config.ejs` | Admin form — 6 folder ID inputs |
| Create | `src/controllers/recursos-digitales.controller.js` | Gallery listing + ZIP download |
| Create | `src/routes/recursos-digitales.routes.js` | 5 public routes |
| Modify | `src/app.js` | Mount public routes |
| Create | `views/recursos-digitales/index.ejs` | Landing: WA Business card |
| Create | `views/recursos-digitales/wa-business.ejs` | 6 product cards |
| Create | `views/recursos-digitales/galeria.ejs` | Image gallery + ZIP form |
| Modify | `views/documents/index.ejs` | Add Recursos Digitales section at bottom |

---

### Task 1: Admin config — save and read folder IDs

**Files:**
- Create: `src/controllers/admin/recursos.controller.js`
- Modify: `src/routes/admin.routes.js` (~line 755, after documents block)
- Modify: `views/admin/partials/sidebar.ejs` (~line 113, after Documentos link)
- Create: `views/admin/recursos-digitales/config.ejs`

- [ ] **Step 1: Create the admin controller**

Create `src/controllers/admin/recursos.controller.js`:

```javascript
'use strict';

const pool = require('../../db/pool');

const WA_KEYS = [
  { slug: 'outlet',           label: 'Outlet Inmobiliario',  color: '#7a22a8', clave: 'wa_business_outlet_folder_id' },
  { slug: 'residencial',      label: 'Residencial',          color: '#1a4a6e', clave: 'wa_business_residencial_folder_id' },
  { slug: 'legal',            label: 'Soluciones Legales',   color: '#1a5c1a', clave: 'wa_business_legal_folder_id' },
  { slug: 'renova',           label: 'Renova',               color: '#b86800', clave: 'wa_business_renova_folder_id' },
  { slug: 'arquitectura',     label: 'Arquitectura',         color: '#5a5aa8', clave: 'wa_business_arquitectura_folder_id' },
  { slug: 'microinversiones', label: 'Microinversiones',     color: '#2a6060', clave: 'wa_business_microinversiones_folder_id' },
];

exports.WA_KEYS = WA_KEYS;

exports.configForm = async (req, res) => {
  try {
    const claves = WA_KEYS.map(p => p.clave);
    const { rows } = await pool.query(
      `SELECT clave, valor FROM configuracion WHERE clave = ANY($1::text[])`,
      [claves]
    );
    const valores = {};
    rows.forEach(r => { valores[r.clave] = r.valor || ''; });

    res.render('admin/recursos-digitales/config', {
      user:      req.session.user,
      productos: WA_KEYS.map(p => ({ ...p, valor: valores[p.clave] || '' })),
      toast:     req.query.toast || null,
      path:      '/admin/recursos-digitales',
    });
  } catch (err) {
    console.error('❌ GET /admin/recursos-digitales:', err);
    res.status(500).send('Error al cargar configuración.');
  }
};

exports.configSave = async (req, res) => {
  try {
    for (const prod of WA_KEYS) {
      const valor = String(req.body[prod.slug] || '').trim();
      await pool.query(
        `INSERT INTO configuracion (clave, valor, descripcion, updated_at)
         VALUES ($1, $2, $3, NOW())
         ON CONFLICT (clave) DO UPDATE SET valor = $2, updated_at = NOW()`,
        [prod.clave, valor, `Folder ID Google Drive WA Business — ${prod.label}`]
      );
    }
    res.redirect('/admin/recursos-digitales?toast=saved');
  } catch (err) {
    console.error('❌ POST /admin/recursos-digitales:', err);
    res.status(500).send('Error al guardar configuración.');
  }
};
```

- [ ] **Step 2: Mount routes in admin.routes.js**

Find the documents block in `src/routes/admin.routes.js` (look for `router.post("/documents/:id/eliminar"`). Add immediately after:

```javascript
// ============================
// Recursos Digitales
// ============================
const recursosAdminCtrl = require('../controllers/admin/recursos.controller');
router.get('/recursos-digitales',  requireRole('admin'), recursosAdminCtrl.configForm);
router.post('/recursos-digitales', requireRole('admin'), recursosAdminCtrl.configSave);
```

- [ ] **Step 3: Add sidebar link in admin sidebar**

Find in `views/admin/partials/sidebar.ejs` the Documentos `<li>` block ending with `</li>`. Add immediately after it:

```html
      <li>
        <a href="/admin/recursos-digitales"
           class="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-800/60 text-slate-300 <%= path === '/admin/recursos-digitales' ? 'bg-slate-800 text-white' : '' %>">
          <span class="inline-flex h-7 w-7 items-center justify-center rounded-full bg-teal-500/20 text-teal-300 text-xs font-semibold">
            R
          </span>
          <span>Recursos Digitales</span>
        </a>
      </li>
```

- [ ] **Step 4: Create the admin config view**

Create directory `views/admin/recursos-digitales/` and file `config.ejs`:

```html
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap');
  .rd-admin-page { font-family: 'DM Sans', sans-serif; min-height: 100vh; background: #f8fafc; padding: 40px 28px 80px; }
  .rd-admin-inner { max-width: 680px; margin: 0 auto; }
  .rd-header { margin-bottom: 32px; }
  .rd-header h1 { font-size: 20px; font-weight: 600; color: #1a1a1a; margin-bottom: 4px; }
  .rd-header p { font-size: 13px; color: #777; line-height: 1.6; max-width: 520px; }
  .rd-card { background: #fff; border: 1px solid #e8e8e4; border-radius: 16px; padding: 28px; }
  .rd-card-title { font-size: 13px; font-weight: 600; color: #1a1a1a; margin-bottom: 24px; padding-bottom: 14px; border-bottom: 1px solid #f0f0ec; display: flex; align-items: center; gap: 8px; }
  .rd-card-title span { font-size: 10px; font-weight: 600; letter-spacing: .15em; color: #00a0a0; background: rgba(0,204,204,.08); border: .5px solid rgba(0,204,204,.2); border-radius: 100px; padding: 2px 10px; }
  .form-row { margin-bottom: 20px; }
  .form-label { display: flex; align-items: center; gap: 8px; font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #555; margin-bottom: 6px; }
  .prod-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .form-input { width: 100%; height: 42px; padding: 0 14px; background: #f7f7f5; border: 1px solid #e8e8e4; border-radius: 10px; font-size: 13px; font-family: 'DM Sans', sans-serif; color: #1a1a1a; outline: none; transition: border-color .18s, box-shadow .18s; }
  .form-input:focus { border-color: #00cccc; box-shadow: 0 0 0 3px rgba(0,204,204,.1); background: #fff; }
  .form-input::placeholder { color: #c0c0bb; }
  .form-hint { font-size: 11px; color: #aaa; margin-top: 4px; }
  .form-sep { height: 1px; background: #f0f0ec; margin: 24px 0; }
  .btn-save { height: 42px; padding: 0 24px; background: #008a8a; color: #fff; border: none; border-radius: 10px; font-size: 13px; font-weight: 600; font-family: 'DM Sans', sans-serif; cursor: pointer; display: inline-flex; align-items: center; gap: 7px; transition: background .18s; }
  .btn-save:hover { background: #006666; }
  .toast-ok { background: #f0fdf4; border: 1px solid #86efac; border-radius: 10px; padding: 12px 16px; font-size: 13px; color: #166534; margin-bottom: 24px; display: flex; align-items: center; gap: 8px; }
</style>

<div class="rd-admin-page">
  <div class="rd-admin-inner">

    <div class="rd-header">
      <h1>Recursos Digitales — Configuración</h1>
      <p>Ingresa el ID de carpeta de Google Drive para cada producto de WA Business. Las carpetas deben estar compartidas con la cuenta de servicio de Altaltium.</p>
    </div>

    <% if (toast === 'saved') { %>
      <div class="toast-ok">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        Configuración guardada correctamente.
      </div>
    <% } %>

    <form method="POST" action="/admin/recursos-digitales">
      <div class="rd-card">
        <div class="rd-card-title">
          WA Business <span>6 productos</span>
        </div>

        <% productos.forEach(p => { %>
          <div class="form-row">
            <label class="form-label">
              <span class="prod-dot" style="background:<%= p.color %>;"></span>
              <%= p.label %>
            </label>
            <input
              class="form-input"
              type="text"
              name="<%= p.slug %>"
              value="<%= p.valor %>"
              placeholder="ID de carpeta Google Drive…"
              autocomplete="off"
              spellcheck="false"
            />
            <p class="form-hint">Ej: <code>1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs</code> — el ID está en la URL de la carpeta de Drive.</p>
          </div>
        <% }) %>

        <div class="form-sep"></div>

        <button type="submit" class="btn-save">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
          Guardar configuración
        </button>
      </div>
    </form>

  </div>
</div>
```

- [ ] **Step 5: Verify admin page works**

Start the server and navigate to `http://localhost:3000/admin/recursos-digitales`. Confirm:
- Form shows 6 labeled inputs
- Save button works and redirects with `?toast=saved`
- Values persist after page reload (check DB: `SELECT clave, valor FROM configuracion WHERE clave LIKE 'wa_business%';`)

- [ ] **Step 6: Commit**

```bash
git add src/controllers/admin/recursos.controller.js src/routes/admin.routes.js views/admin/partials/sidebar.ejs views/admin/recursos-digitales/config.ejs
git commit -m "feat: admin config page for Recursos Digitales folder IDs"
```

---

### Task 2: Public controller + routes + views

**Files:**
- Create: `src/controllers/recursos-digitales.controller.js`
- Create: `src/routes/recursos-digitales.routes.js`
- Modify: `src/app.js` (mount routes before 404 handler)
- Create: `views/recursos-digitales/index.ejs`
- Create: `views/recursos-digitales/wa-business.ejs`
- Create: `views/recursos-digitales/galeria.ejs`

- [ ] **Step 1: Create the public controller**

Create `src/controllers/recursos-digitales.controller.js`:

```javascript
'use strict';

const pool        = require('../db/pool');
const driveService = require('../services/googleDrive.service');
const archiver    = require('archiver');

const WA_PRODUCTOS = {
  outlet:           'Outlet Inmobiliario',
  residencial:      'Residencial',
  legal:            'Soluciones Legales',
  renova:           'Renova',
  arquitectura:     'Arquitectura',
  microinversiones: 'Microinversiones',
};

function folderClave(slug) {
  return `wa_business_${slug}_folder_id`;
}

async function readFolderIds(slugs) {
  const claves = slugs.map(folderClave);
  const { rows } = await pool.query(
    `SELECT clave, valor FROM configuracion WHERE clave = ANY($1::text[])`,
    [claves]
  );
  const map = {};
  rows.forEach(r => { map[r.clave] = r.valor || ''; });
  return map;
}

exports.index = (req, res) => {
  res.render('recursos-digitales/index', {
    user: req.session.user,
    path: '/recursos-digitales',
  });
};

exports.waBusiness = async (req, res) => {
  try {
    const slugs    = Object.keys(WA_PRODUCTOS);
    const folderIds = await readFolderIds(slugs);

    const productos = slugs.map(slug => ({
      slug,
      label:       WA_PRODUCTOS[slug],
      folderId:    folderIds[folderClave(slug)] || '',
      configurado: !!(folderIds[folderClave(slug)]),
      count:       0,
    }));

    // Count images per configured product (parallel)
    await Promise.all(
      productos.map(async p => {
        if (!p.folderId) return;
        try {
          const imgs = await driveService.listFolderImages(p.folderId, { limit: 200 });
          p.count = imgs.length;
        } catch { /* Drive unavailable — show 0 */ }
      })
    );

    res.render('recursos-digitales/wa-business', {
      user:      req.session.user,
      productos,
      path:      '/recursos-digitales/wa-business',
    });
  } catch (err) {
    console.error('❌ /recursos-digitales/wa-business:', err);
    res.status(500).send('Error al cargar productos.');
  }
};

exports.galeria = async (req, res) => {
  const { producto } = req.params;
  if (!WA_PRODUCTOS[producto]) {
    return res.status(404).render('pages/404', { user: req.session.user, title: '404' });
  }

  try {
    const { rows } = await pool.query(
      `SELECT valor FROM configuracion WHERE clave = $1`,
      [folderClave(producto)]
    );
    const folderId = rows[0]?.valor || '';
    const label    = WA_PRODUCTOS[producto];
    let imagenes   = [];
    let error      = null;

    if (folderId) {
      try {
        imagenes = await driveService.listFolderImages(folderId, { limit: 200 });
      } catch (e) {
        console.error('❌ Drive listFolderImages:', e.message);
        error = 'No se pudo cargar la galería desde Google Drive. Intenta de nuevo.';
      }
    }

    res.render('recursos-digitales/galeria', {
      user:     req.session.user,
      producto,
      label,
      folderId,
      imagenes,
      error,
      path:     '/recursos-digitales',
    });
  } catch (err) {
    console.error('❌ /recursos-digitales/galeria:', err);
    res.status(500).send('Error al cargar galería.');
  }
};

exports.descargarZip = async (req, res) => {
  const { producto } = req.params;
  if (!WA_PRODUCTOS[producto]) return res.status(404).send('Producto no encontrado.');

  let fileIds   = req.body.fileIds   || [];
  let fileNames = req.body.fileNames || [];
  if (!Array.isArray(fileIds))   fileIds   = fileIds   ? [fileIds]   : [];
  if (!Array.isArray(fileNames)) fileNames = fileNames ? [fileNames] : [];

  fileIds = fileIds.map(id => String(id).trim()).filter(Boolean);
  if (!fileIds.length) return res.status(400).send('No hay imágenes seleccionadas.');
  if (fileIds.length > 50) return res.status(400).send('Máximo 50 imágenes por descarga.');

  const zipName = `wa-business-${producto}.zip`;
  res.setHeader('Content-Type', 'application/zip');
  res.setHeader('Content-Disposition', `attachment; filename="${zipName}"`);

  const archive = archiver('zip', { zlib: { level: 5 } });
  archive.pipe(res);

  for (let i = 0; i < fileIds.length; i++) {
    const fileId = fileIds[i];
    const name   = (fileNames[i] || '').trim() || `imagen-${i + 1}.jpg`;
    try {
      const driveRes = await driveService.getFileStream(fileId);
      archive.append(driveRes.data, { name });
    } catch (e) {
      console.error(`⚠️ ZIP skip ${fileId}:`, e.message);
    }
  }

  await archive.finalize();
};
```

- [ ] **Step 2: Create the public routes file**

Create `src/routes/recursos-digitales.routes.js`:

```javascript
'use strict';

const express    = require('express');
const router     = express.Router();
const { ensureAuth } = require('../middlewares/auth');
const ctrl       = require('../controllers/recursos-digitales.controller');

router.get('/recursos-digitales',                                    ensureAuth, ctrl.index);
router.get('/recursos-digitales/wa-business',                        ensureAuth, ctrl.waBusiness);
router.get('/recursos-digitales/wa-business/:producto',              ensureAuth, ctrl.galeria);
router.post('/recursos-digitales/wa-business/:producto/descargar',   ensureAuth, ctrl.descargarZip);

module.exports = router;
```

- [ ] **Step 3: Mount routes in app.js**

Find the documentsRoutes block in `src/app.js`:
```javascript
const documentsRoutes = require("./routes/documents.routes");
app.use(documentsRoutes);
```

Add immediately after it:
```javascript
const recursosDigitalesRoutes = require("./routes/recursos-digitales.routes");
app.use(recursosDigitalesRoutes);
```

- [ ] **Step 4: Create views/recursos-digitales/index.ejs**

```html
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Serif+Display:ital@0;1&display=swap');
  .rd-page { font-family: 'DM Sans', sans-serif; min-height: 100vh; background: #f8fafc; }
  .rd-hero { background: #0b1e1e; position: relative; overflow: hidden; padding: 40px 28px; }
  .rd-hero::before { content: ''; position: absolute; inset: 0; background: linear-gradient(135deg,rgba(11,30,30,.75) 0%,rgba(15,46,46,.65) 100%); z-index: 0; }
  .rd-hero-inner { max-width: 900px; margin: 0 auto; position: relative; z-index: 1; }
  .rd-hero-tag { display: inline-flex; align-items: center; gap: 6px; background: rgba(82,190,192,.14); border: .5px solid rgba(82,190,192,.3); color: #52BEC0; font-size: 9px; font-weight: 600; letter-spacing: .2em; padding: 4px 12px; border-radius: 100px; margin-bottom: 12px; }
  .rd-hero-title { font-family: 'DM Serif Display', serif; font-size: clamp(22px,4vw,34px); color: #fff; line-height: 1.2; margin-bottom: 8px; }
  .rd-hero-title em { font-style: italic; color: #52BEC0; }
  .rd-hero-sub { font-size: 12px; color: rgba(255,255,255,.35); line-height: 1.75; max-width: 440px; }
  .rd-body { max-width: 900px; margin: 0 auto; padding: 44px 28px 80px; }
  .breadcrumb { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #aaa; margin-bottom: 36px; }
  .breadcrumb a { color: #00a0a0; text-decoration: none; font-weight: 500; }
  .breadcrumb a:hover { text-decoration: underline; }
  .breadcrumb-sep { color: #ddd; }
  .subcat-card { background: #fff; border: 1px solid #e8e8e4; border-radius: 18px; overflow: hidden; text-decoration: none; color: inherit; display: flex; transition: box-shadow .2s, border-color .2s; }
  .subcat-card:hover { box-shadow: 0 12px 32px rgba(0,204,204,.1); border-color: #a8f0f0; }
  .subcat-accent { width: 6px; background: linear-gradient(180deg,#00cccc 0%,#008a8a 100%); flex-shrink: 0; }
  .subcat-body { padding: 24px 28px; flex: 1; }
  .subcat-eyebrow { font-size: 9px; font-weight: 600; letter-spacing: .2em; color: #00a0a0; text-transform: uppercase; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; }
  .subcat-title { font-size: 18px; font-weight: 600; color: #1a1a1a; margin-bottom: 6px; }
  .subcat-desc { font-size: 13px; color: #777; line-height: 1.5; margin-bottom: 18px; }
  .subcat-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 20px; }
  .subcat-chip { font-size: 11px; font-weight: 500; padding: 4px 12px; background: #f4f4f0; border: 1px solid #e8e8e4; border-radius: 100px; color: #555; }
  .subcat-cta { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; color: #00cccc; }
  .subcat-cta svg { transition: transform .18s; }
  .subcat-card:hover .subcat-cta svg { transform: translateX(4px); }
  .subcat-visual { width: 200px; flex-shrink: 0; background: linear-gradient(135deg,#0b1e1e,#003333 60%,#004444); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; padding: 24px; }
  .subcat-icon { width: 52px; height: 52px; background: rgba(0,204,204,.12); border: .5px solid rgba(0,204,204,.25); border-radius: 50%; display: flex; align-items: center; justify-content: center; }
  .subcat-icon svg { width: 24px; height: 24px; stroke: #00cccc; fill: none; stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
  .subcat-count { font-size: 28px; font-weight: 700; color: #fff; line-height: 1; }
  .subcat-count-lbl { font-size: 10px; color: rgba(255,255,255,.35); letter-spacing: .1em; text-transform: uppercase; text-align: center; }
  @media(max-width:640px) { .subcat-visual { display: none; } .subcat-accent { width: 100%; height: 5px; } .subcat-card { flex-direction: column; } }
</style>

<div class="rd-page">
  <div class="rd-hero">
    <div class="rd-hero-inner">
      <div class="rd-hero-tag">Recursos Digitales · Altaltium</div>
      <h1 class="rd-hero-title">Material visual para<br><em>comunicación digital</em></h1>
      <p class="rd-hero-sub">Imágenes y recursos listos para usar en tus canales digitales, organizados por producto.</p>
    </div>
  </div>

  <div class="rd-body">
    <div class="breadcrumb">
      <a href="/documents">Documentos</a>
      <span class="breadcrumb-sep">›</span>
      <span>Recursos Digitales</span>
    </div>

    <a class="subcat-card" href="/recursos-digitales/wa-business">
      <div class="subcat-accent"></div>
      <div class="subcat-body">
        <div class="subcat-eyebrow">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.81 19.79 19.79 0 01.01 1.17 2 2 0 012 .01h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 14.9v2.02z"/></svg>
          WA Business
        </div>
        <h2 class="subcat-title">Imágenes por Producto</h2>
        <p class="subcat-desc">Material visual listo para compartir en WhatsApp Business. Selecciona el producto y descarga las imágenes que necesitas.</p>
        <div class="subcat-chips">
          <span class="subcat-chip">Outlet Inmobiliario</span>
          <span class="subcat-chip">Residencial</span>
          <span class="subcat-chip">Soluciones Legales</span>
          <span class="subcat-chip">Renova</span>
          <span class="subcat-chip">Arquitectura</span>
          <span class="subcat-chip">Microinversiones</span>
        </div>
        <span class="subcat-cta">Explorar galería
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        </span>
      </div>
      <div class="subcat-visual">
        <div class="subcat-icon">
          <svg viewBox="0 0 24 24"><path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
        </div>
        <div class="subcat-count">6</div>
        <div class="subcat-count-lbl">Productos</div>
      </div>
    </a>
  </div>
</div>
```

- [ ] **Step 5: Create views/recursos-digitales/wa-business.ejs**

```html
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Serif+Display:ital@0;1&display=swap');
  .wa-page { font-family: 'DM Sans', sans-serif; min-height: 100vh; background: #f8fafc; padding: 44px 28px 80px; }
  .wa-inner { max-width: 1100px; margin: 0 auto; }
  .breadcrumb { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #aaa; margin-bottom: 32px; }
  .breadcrumb a { color: #00a0a0; text-decoration: none; font-weight: 500; }
  .breadcrumb a:hover { text-decoration: underline; }
  .breadcrumb-sep { color: #ddd; }
  .wa-hero { margin-bottom: 36px; }
  .wa-hero h1 { font-family: 'DM Serif Display', serif; font-size: 28px; color: #1a1a1a; margin-bottom: 6px; }
  .wa-hero h1 em { font-style: italic; color: #008a8a; }
  .wa-hero p { font-size: 13px; color: #888; max-width: 500px; line-height: 1.6; }
  .prod-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; }
  .prod-card { background: #fff; border: 1px solid #e8e8e4; border-radius: 16px; overflow: hidden; text-decoration: none; color: inherit; display: flex; flex-direction: column; transition: transform .18s, box-shadow .18s, border-color .18s; }
  .prod-card:hover:not(.disabled) { transform: translateY(-3px); box-shadow: 0 14px 36px rgba(0,0,0,.08); border-color: #a8f0f0; }
  .prod-card.disabled { cursor: default; opacity: .6; }
  .prod-hdr { height: 88px; display: flex; align-items: center; justify-content: center; position: relative; }
  .prod-hdr svg { width: 30px; height: 30px; stroke: rgba(255,255,255,.35); fill: none; stroke-width: 1.3; stroke-linecap: round; stroke-linejoin: round; }
  .prod-hdr-lbl { position: absolute; bottom: 10px; left: 14px; font-size: 9px; font-weight: 600; letter-spacing: .18em; color: rgba(255,255,255,.4); text-transform: uppercase; }
  .prod-body { padding: 16px 18px 18px; flex: 1; display: flex; flex-direction: column; }
  .prod-name { font-size: 14px; font-weight: 600; color: #1a1a1a; margin-bottom: 4px; }
  .prod-sub { font-size: 12px; color: #888; margin-bottom: 14px; line-height: 1.4; flex: 1; }
  .prod-footer { display: flex; align-items: center; justify-content: space-between; }
  .prod-count { font-size: 11px; color: #aaa; display: flex; align-items: center; gap: 4px; }
  .prod-count svg { width: 12px; height: 12px; stroke: currentColor; fill: none; stroke-width: 2; stroke-linecap: round; }
  .prod-cta { font-size: 11px; font-weight: 600; color: #00cccc; display: flex; align-items: center; gap: 3px; }
  .prod-cta svg { width: 11px; height: 11px; stroke: currentColor; fill: none; stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round; transition: transform .18s; }
  .prod-card:hover:not(.disabled) .prod-cta svg { transform: translateX(3px); }
  .badge-nc { font-size: 10px; padding: 2px 8px; background: #f4f4f0; border: 1px solid #e8e8e4; border-radius: 100px; color: #aaa; }
</style>

<div class="wa-page">
  <div class="wa-inner">

    <div class="breadcrumb">
      <a href="/documents">Documentos</a>
      <span class="breadcrumb-sep">›</span>
      <a href="/recursos-digitales">Recursos Digitales</a>
      <span class="breadcrumb-sep">›</span>
      <span>WA Business</span>
    </div>

    <div class="wa-hero">
      <h1>WA <em>Business</em></h1>
      <p>Selecciona un producto para ver y descargar las imágenes disponibles para WhatsApp.</p>
    </div>

    <%
      const PROD_COLORS = {
        outlet:           { bg: 'linear-gradient(135deg,#1a0533,#4a1278)', icon: 'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z M9 22V12h6v10' },
        residencial:      { bg: 'linear-gradient(135deg,#0a1e2e,#1a4a6e)', icon: 'M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z M9 22V12h6v10' },
        legal:            { bg: 'linear-gradient(135deg,#0d2a0d,#1a5c1a)', icon: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z' },
        renova:           { bg: 'linear-gradient(135deg,#2a1a00,#7a4800)', icon: 'M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15' },
        arquitectura:     { bg: 'linear-gradient(135deg,#1a1a2e,#3a3a6e)', icon: 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4' },
        microinversiones: { bg: 'linear-gradient(135deg,#0d1a2a,#1a4040)', icon: 'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z' },
      };
      const PROD_DESCS = {
        outlet:           'Propiedades con condiciones y precios exclusivos.',
        residencial:      'Proyectos residenciales nuevos y desarrollo habitacional.',
        legal:            'Servicios jurídicos y asesoría legal inmobiliaria.',
        renova:           'Remodelación y renovación de inmuebles.',
        arquitectura:     'Proyectos y servicios de diseño arquitectónico.',
        microinversiones: 'Oportunidades de inversión accesibles.',
      };
    %>

    <div class="prod-grid">
      <% productos.forEach(p => { %>
        <% const style = PROD_COLORS[p.slug] || { bg: 'linear-gradient(135deg,#1a1a1a,#333)', icon: 'M4 16l4.586-4.586a2 2 0 012.828 0L16 16' }; %>
        <% if (p.configurado) { %>
          <a class="prod-card" href="/recursos-digitales/wa-business/<%= p.slug %>">
        <% } else { %>
          <div class="prod-card disabled">
        <% } %>
            <div class="prod-hdr" style="background:<%= style.bg %>;">
              <svg viewBox="0 0 24 24"><path d="<%= style.icon %>"/></svg>
              <span class="prod-hdr-lbl"><%= p.slug %></span>
            </div>
            <div class="prod-body">
              <p class="prod-name"><%= p.label %></p>
              <p class="prod-sub"><%= PROD_DESCS[p.slug] || '' %></p>
              <div class="prod-footer">
                <% if (p.configurado) { %>
                  <span class="prod-count">
                    <svg viewBox="0 0 24 24"><path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14"/></svg>
                    <%= p.count %> imagen<%= p.count !== 1 ? 'es' : '' %>
                  </span>
                  <span class="prod-cta">Ver
                    <svg viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                  </span>
                <% } else { %>
                  <span class="badge-nc">Sin configurar</span>
                <% } %>
              </div>
            </div>
        <% if (p.configurado) { %>
          </a>
        <% } else { %>
          </div>
        <% } %>
      <% }) %>
    </div>

  </div>
</div>
```

- [ ] **Step 6: Create views/recursos-digitales/galeria.ejs**

```html
<style>
  @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Serif+Display:ital@0;1&display=swap');
  .gal-page { font-family: 'DM Sans', sans-serif; min-height: 100vh; background: #f8fafc; padding: 44px 28px 80px; }
  .gal-inner { max-width: 1100px; margin: 0 auto; }
  .breadcrumb { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #aaa; margin-bottom: 32px; }
  .breadcrumb a { color: #00a0a0; text-decoration: none; font-weight: 500; }
  .breadcrumb a:hover { text-decoration: underline; }
  .breadcrumb-sep { color: #ddd; }
  .gal-hero { margin-bottom: 28px; }
  .gal-hero h1 { font-family: 'DM Serif Display', serif; font-size: 26px; color: #1a1a1a; margin-bottom: 6px; }
  .gal-hero h1 em { font-style: italic; color: #008a8a; }
  .gal-hero p { font-size: 13px; color: #888; max-width: 500px; line-height: 1.6; }
  .gal-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 24px; flex-wrap: wrap; }
  .btn-sel-all { height: 36px; padding: 0 16px; background: #f4f4f0; border: 1px solid #e8e8e4; border-radius: 9px; font-size: 12px; font-weight: 500; cursor: pointer; font-family: 'DM Sans', sans-serif; color: #555; transition: background .18s; }
  .btn-sel-all:hover { background: #e8e8e4; }
  .btn-dl { height: 36px; padding: 0 18px; background: #0a0a0a; color: #fff; border: none; border-radius: 9px; font-size: 12px; font-weight: 600; cursor: pointer; font-family: 'DM Sans', sans-serif; display: inline-flex; align-items: center; gap: 6px; transition: background .18s, opacity .18s; opacity: .35; pointer-events: none; }
  .btn-dl.active { opacity: 1; background: #008a8a; pointer-events: auto; }
  .sel-count { font-size: 12px; color: #888; margin-left: auto; }
  .gal-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(175px, 1fr)); gap: 10px; }
  .img-card { position: relative; border-radius: 12px; overflow: hidden; cursor: pointer; border: 2.5px solid transparent; transition: border-color .15s, transform .15s; background: #e8e8e4; }
  .img-card:hover { transform: translateY(-2px); }
  .img-card.selected { border-color: #00cccc; }
  .img-card img { width: 100%; height: 140px; object-fit: cover; display: block; }
  .img-overlay { position: absolute; inset: 0; background: rgba(0,0,0,0); transition: background .15s; }
  .img-card.selected .img-overlay { background: rgba(0,204,204,.12); }
  .img-card:hover .img-overlay { background: rgba(0,0,0,.12); }
  .img-check { position: absolute; top: 8px; right: 8px; width: 22px; height: 22px; border-radius: 50%; background: #fff; border: 2px solid #ddd; display: flex; align-items: center; justify-content: center; transition: all .15s; }
  .img-card.selected .img-check { background: #00cccc; border-color: #00cccc; }
  .img-check svg { width: 11px; height: 11px; stroke: #fff; fill: none; stroke-width: 2.5; stroke-linecap: round; stroke-linejoin: round; opacity: 0; transition: opacity .15s; }
  .img-card.selected .img-check svg { opacity: 1; }
  .img-name { position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(transparent, rgba(0,0,0,.55)); padding: 20px 10px 7px; font-size: 10px; color: #fff; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .state-box { text-align: center; padding: 64px 24px; }
  .state-ico { width: 52px; height: 52px; background: #f0f0ec; border-radius: 14px; display: flex; align-items: center; justify-content: center; margin: 0 auto 18px; }
  .state-ico svg { width: 22px; height: 22px; stroke: #bbb; fill: none; stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
  .state-box h3 { font-size: 16px; font-weight: 500; color: #1a1a1a; margin-bottom: 6px; }
  .state-box p { font-size: 13px; color: #888; max-width: 340px; margin: 0 auto; line-height: 1.6; }
  .nota { background: #fffbeb; border: 1px solid #fde68a; border-radius: 10px; padding: 12px 16px; font-size: 12px; color: #92400e; margin-top: 32px; display: flex; gap: 8px; align-items: flex-start; }
  .nota svg { width: 15px; height: 15px; stroke: currentColor; fill: none; stroke-width: 1.8; stroke-linecap: round; flex-shrink: 0; margin-top: 1px; }
</style>

<div class="gal-page">
  <div class="gal-inner">

    <div class="breadcrumb">
      <a href="/documents">Documentos</a>
      <span class="breadcrumb-sep">›</span>
      <a href="/recursos-digitales">Recursos Digitales</a>
      <span class="breadcrumb-sep">›</span>
      <a href="/recursos-digitales/wa-business">WA Business</a>
      <span class="breadcrumb-sep">›</span>
      <span><%= label %></span>
    </div>

    <div class="gal-hero">
      <h1>WA Business — <em><%= label %></em></h1>
      <p>Selecciona las imágenes que quieres descargar. Puedes elegir individualmente o descargar todas de una vez.</p>
    </div>

    <% if (!folderId) { %>
      <div class="state-box">
        <div class="state-ico"><svg viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div>
        <h3>Galería no configurada</h3>
        <p>El administrador aún no ha configurado la carpeta de Google Drive para este producto.</p>
      </div>

    <% } else if (error) { %>
      <div class="state-box">
        <div class="state-ico"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div>
        <h3>Error al cargar</h3>
        <p><%= error %></p>
      </div>

    <% } else if (!imagenes.length) { %>
      <div class="state-box">
        <div class="state-ico"><svg viewBox="0 0 24 24"><path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg></div>
        <h3>Sin imágenes</h3>
        <p>La carpeta de Drive aún no tiene imágenes. Agrega imágenes a la carpeta y recarga la página.</p>
      </div>

    <% } else { %>
      <form id="dlForm" method="POST" action="/recursos-digitales/wa-business/<%= producto %>/descargar">
        <div class="gal-toolbar">
          <button type="button" class="btn-sel-all" id="btnSelAll">Seleccionar todas</button>
          <button type="submit" class="btn-dl" id="btnDl">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Descargar seleccionadas
          </button>
          <span class="sel-count" id="selCount">0 seleccionadas</span>
        </div>

        <div class="gal-grid" id="galGrid">
          <% imagenes.forEach(img => { %>
            <div class="img-card"
                 data-id="<%= img.id %>"
                 data-name="<%= img.name %>"
                 onclick="toggleImg(this)">
              <img src="<%= img.url %>" alt="<%= img.name %>" loading="lazy" onerror="this.style.opacity='.3'"/>
              <div class="img-overlay"></div>
              <div class="img-check">
                <svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
              </div>
              <div class="img-name"><%= img.name %></div>
            </div>
          <% }) %>
        </div>

        <div class="nota">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          Las imágenes se descargan directamente desde Google Drive en un archivo ZIP. Puede tardar unos segundos dependiendo de la cantidad seleccionada.
        </div>
      </form>
    <% } %>

  </div>
</div>

<script>
(function() {
  function updateToolbar() {
    const sel = document.querySelectorAll('#galGrid .img-card.selected');
    const n   = sel.length;
    const countEl = document.getElementById('selCount');
    const btnDl   = document.getElementById('btnDl');
    if (countEl) countEl.textContent = n + ' seleccionada' + (n !== 1 ? 's' : '');
    if (btnDl) {
      btnDl.classList.toggle('active', n > 0);
      btnDl.textContent = n > 0
        ? `Descargar ${n} imagen${n !== 1 ? 'es' : ''} (ZIP)`
        : 'Descargar seleccionadas';
    }
  }

  window.toggleImg = function(card) {
    card.classList.toggle('selected');
    updateToolbar();
  };

  const btnSelAll = document.getElementById('btnSelAll');
  if (btnSelAll) {
    btnSelAll.addEventListener('click', function() {
      const cards      = document.querySelectorAll('#galGrid .img-card');
      const allSel     = Array.from(cards).every(c => c.classList.contains('selected'));
      cards.forEach(c => c.classList.toggle('selected', !allSel));
      btnSelAll.textContent = allSel ? 'Seleccionar todas' : 'Deseleccionar todas';
      updateToolbar();
    });
  }

  const dlForm = document.getElementById('dlForm');
  if (dlForm) {
    dlForm.addEventListener('submit', function() {
      // Remove any previous hidden inputs
      dlForm.querySelectorAll('input[name="fileIds[]"], input[name="fileNames[]"]').forEach(el => el.remove());
      // Append selected file IDs and names
      document.querySelectorAll('#galGrid .img-card.selected').forEach(card => {
        const idInput   = document.createElement('input');
        idInput.type    = 'hidden';
        idInput.name    = 'fileIds';
        idInput.value   = card.dataset.id;
        dlForm.appendChild(idInput);

        const nameInput  = document.createElement('input');
        nameInput.type   = 'hidden';
        nameInput.name   = 'fileNames';
        nameInput.value  = card.dataset.name;
        dlForm.appendChild(nameInput);
      });
    });
  }
})();
</script>
```

- [ ] **Step 7: Verify navigation works**

Start the server. Navigate:
1. `http://localhost:3000/recursos-digitales` → should show WA Business card
2. `http://localhost:3000/recursos-digitales/wa-business` → should show 6 product cards (all "Sin configurar" until admin saves folder IDs)
3. Configure a real folder ID in admin, then click the product card → gallery should load images

- [ ] **Step 8: Commit**

```bash
git add src/controllers/recursos-digitales.controller.js src/routes/recursos-digitales.routes.js src/app.js views/recursos-digitales/index.ejs views/recursos-digitales/wa-business.ejs views/recursos-digitales/galeria.ejs
git commit -m "feat: public routes and views for Recursos Digitales gallery"
```

---

### Task 3: Add Recursos Digitales section to /documents page

**Files:**
- Modify: `views/documents/index.ejs` (before the closing `</div>` of `.docs-body`)

- [ ] **Step 1: Add the Recursos Digitales section**

In `views/documents/index.ejs`, find the closing `</div>` of `.docs-body` (the line right before `</main>`):

```html
  </div>
</main>
```

Insert the new section before `</div>`:

```html
    <%# ══ RECURSOS DIGITALES ══ %>
    <% if (!hasFilters) { %>
      <section style="margin-bottom:50px;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:18px;padding-bottom:14px;border-bottom:2px solid #00cccc;">
          <div style="width:34px;height:34px;background:linear-gradient(135deg,#003333,#006666);border-radius:9px;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#00cccc" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
          </div>
          <h2 style="font-size:15px;font-weight:600;color:#1a1a1a;margin:0;">Recursos Digitales</h2>
          <span style="font-size:10px;font-weight:600;letter-spacing:.1em;color:#00cccc;background:rgba(0,204,204,.08);border:.5px solid rgba(0,204,204,.2);border-radius:100px;padding:3px 10px;">NUEVO</span>
          <span style="font-size:11px;color:#888;background:#f0f0ec;border-radius:100px;padding:2px 10px;margin-left:2px;">1 subcategoría</span>
        </div>

        <a href="/recursos-digitales/wa-business"
           style="background:#fff;border:1px solid #e8e8e4;border-radius:18px;overflow:hidden;display:flex;text-decoration:none;color:inherit;transition:box-shadow .2s,border-color .2s;"
           onmouseover="this.style.boxShadow='0 12px 32px rgba(0,204,204,.1)';this.style.borderColor='#a8f0f0';"
           onmouseout="this.style.boxShadow='';this.style.borderColor='#e8e8e4';">
          <div style="width:6px;background:linear-gradient(180deg,#00cccc 0%,#008a8a 100%);flex-shrink:0;"></div>
          <div style="padding:22px 26px;flex:1;">
            <div style="font-size:9px;font-weight:600;letter-spacing:.2em;color:#00a0a0;text-transform:uppercase;margin-bottom:8px;display:flex;align-items:center;gap:6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07A19.5 19.5 0 013.07 9.81 19.79 19.79 0 01.01 1.17 2 2 0 012 .01h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L6.09 7.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 14.9v2.02z"/></svg>
              WA Business
            </div>
            <div style="font-size:17px;font-weight:600;color:#1a1a1a;margin-bottom:6px;">Imágenes por Producto</div>
            <div style="font-size:13px;color:#777;line-height:1.5;margin-bottom:16px;">Material visual listo para WhatsApp Business. Selecciona el producto y descarga las imágenes que necesitas.</div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:18px;">
              <% ['Outlet Inmobiliario','Residencial','Soluciones Legales','Renova','Arquitectura','Microinversiones'].forEach(chip => { %>
                <span style="font-size:11px;font-weight:500;padding:4px 12px;background:#f4f4f0;border:1px solid #e8e8e4;border-radius:100px;color:#555;"><%= chip %></span>
              <% }) %>
            </div>
            <span style="display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:600;color:#00cccc;">
              Explorar galería
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
            </span>
          </div>
          <div style="width:190px;flex-shrink:0;background:linear-gradient(135deg,#0b1e1e,#003333 60%,#004444);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;padding:24px;">
            <div style="width:52px;height:52px;background:rgba(0,204,204,.12);border:.5px solid rgba(0,204,204,.25);border-radius:50%;display:flex;align-items:center;justify-content:center;">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#00cccc" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
            </div>
            <div style="font-size:28px;font-weight:700;color:#fff;line-height:1;">6</div>
            <div style="font-size:10px;color:rgba(255,255,255,.35);letter-spacing:.1em;text-transform:uppercase;text-align:center;">Productos</div>
          </div>
        </a>
      </section>
    <% } %>
```

- [ ] **Step 2: Verify it shows on /documents**

Navigate to `http://localhost:3000/documents`. Scroll to the bottom — "Recursos Digitales" section should appear with the WA Business card. The section should be hidden when filters are active (the `if (!hasFilters)` guard).

- [ ] **Step 3: Commit**

```bash
git add views/documents/index.ejs
git commit -m "feat: add Recursos Digitales section to /documents page"
```

---

### Task 4: Final push

- [ ] **Step 1: End-to-end test**

1. Go to `/admin/recursos-digitales`, enter a real Google Drive folder ID for "Residencial" (a folder shared with the service account), save.
2. Go to `/documents` → scroll to Recursos Digitales → click the WA Business card.
3. On `/recursos-digitales/wa-business` → Residencial card should show image count.
4. Click Residencial → gallery loads thumbnails.
5. Select 2–3 images → "Descargar X imágenes (ZIP)" button activates.
6. Click download → browser downloads a `.zip` file with the selected images.

- [ ] **Step 2: Push to remote**

```bash
git push origin pruebas-cron
```

---

## Self-Review

### Spec coverage
- [x] Recursos Digitales category in /documents → Task 3
- [x] WA Business subcategory page with 6 products → Task 2 (wa-business.ejs)
- [x] Gallery per product with Drive images → Task 2 (galeria.ejs + controller)
- [x] Admin configures folder IDs from /admin/documents area → Task 1
- [x] Download all or selected as ZIP → Task 2 (descargarZip + galeria.ejs JS)
- [x] All roles can access → ensureAuth (no role restriction beyond auth)
- [x] folder ID empty → "Sin configurar" state → Task 2 step 5
- [x] Drive unavailable → error state → Task 2 controller galeria()
- [x] Max 50 images per ZIP → Task 2 controller descargarZip()
- [x] invalid :producto → 404 → Task 2 controller galeria()

### Type consistency
- `folderClave(slug)` used consistently in both controllers
- `imagenes` array from `listFolderImages` has `{ id, name, url }` — all three used in galeria.ejs
- `fileIds` / `fileNames` arrays: form appends them with the same name, controller reads them with the same name
- `configurado` boolean on product objects: read in wa-business.ejs to toggle card state

### Placeholder scan
- No TBD, TODO, or vague steps found
- All code blocks are complete and runnable
