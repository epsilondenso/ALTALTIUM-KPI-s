# Recursos Digitales — Design Spec

## Goal

Add a "Recursos Digitales" category to the existing `/documents` page. The first subcategory is "WA Business": a gallery of images per product (6 products), stored in Google Drive folders, where any authenticated user can view and download selected images as a ZIP.

## Architecture

New dedicated routes and controllers. No new DB tables — folder IDs stored in the existing `configuracion` table. Products hardcoded (slug → label). Admin configures folder IDs from a new page inside `/admin/documents`.

**New files:**
```
src/routes/recursos-digitales.routes.js
src/routes/admin.recursos.routes.js
src/controllers/recursos-digitales.controller.js
src/controllers/admin/recursos.controller.js
views/recursos-digitales/index.ejs        ← subcategory landing (WA Business card)
views/recursos-digitales/wa-business.ejs  ← 6 product cards
views/recursos-digitales/galeria.ejs      ← image gallery + ZIP download
views/admin/recursos-digitales/config.ejs ← admin folder ID form
```

**Modified files:**
- `views/documents/index.ejs` — add "Recursos Digitales" section at bottom
- `src/app.js` — mount 2 new route files

## Products (hardcoded)

```javascript
const WA_BUSINESS_PRODUCTOS = {
  outlet:           'Outlet Inmobiliario',
  residencial:      'Residencial',
  legal:            'Soluciones Legales',
  renova:           'Renova',
  arquitectura:     'Arquitectura',
  microinversiones: 'Microinversiones',
};
```

## Data Flow

### configuracion table (no new tables)

| clave | descripción |
|---|---|
| `wa_business_outlet_folder_id` | Drive folder ID for Outlet images |
| `wa_business_residencial_folder_id` | Drive folder ID for Residencial images |
| `wa_business_legal_folder_id` | Drive folder ID for Soluciones Legales images |
| `wa_business_renova_folder_id` | Drive folder ID for Renova images |
| `wa_business_arquitectura_folder_id` | Drive folder ID for Arquitectura images |
| `wa_business_microinversiones_folder_id` | Drive folder ID for Microinversiones images |

Admin saves via `INSERT ... ON CONFLICT (clave) DO UPDATE SET valor=$2`.

### Gallery page flow

1. Controller reads folder ID from `configuracion`
2. If empty → renders page with "Sin configurar" state
3. If set → calls Drive API (service account): `files.list` with `q: "'FOLDER_ID' in parents and mimeType contains 'image/' and trashed=false"`, fields: `id, name, thumbnailLink`
4. Passes array `{ id, name, thumbnailLink }` to EJS

### ZIP download flow

1. POST `/recursos-digitales/wa-business/:producto/descargar` with body `{ fileIds: ['id1','id2',...] }`
2. Controller validates: fileIds is array, max 50, all strings
3. Sets response headers: `Content-Type: application/zip`, `Content-Disposition: attachment; filename="wa-business-{producto}.zip"`
4. Uses `archiver` npm package in streaming mode: for each fileId, fetches file stream from Drive API (`files.get` with `alt: media`) and appends to archive
5. Streams directly to `res` — no temp files, memory-safe on 512MB Render

## URL Structure

**Public:**
```
GET  /recursos-digitales                                  → index.ejs (WA Business card)
GET  /recursos-digitales/wa-business                      → wa-business.ejs (6 products)
GET  /recursos-digitales/wa-business/:producto            → galeria.ejs
POST /recursos-digitales/wa-business/:producto/descargar  → ZIP stream
```

**Admin:**
```
GET  /admin/recursos-digitales        → config.ejs (6 folder ID inputs)
POST /admin/recursos-digitales        → save to configuracion table
```

## Access Control

- All public routes: require `req.session.user` (any authenticated role)
- Admin routes: `requireRole('admin')` middleware (already exists)
- `:producto` param validated against `WA_BUSINESS_PRODUCTOS` keys → 404 if invalid

## UI

### `/documents` — Recursos Digitales section
Appended after all document categories (outside the `grouped` loop). Uses a distinct teal border on the category header. Single banner card for "WA Business" showing the 6 product chips and a link to `/recursos-digitales/wa-business`.

### `/recursos-digitales` (index)
Breadcrumb: Documentos › Recursos Digitales. Hero title. Single WA Business card (same as the banner in documents). Extensible for future subcategories.

### `/recursos-digitales/wa-business`
Breadcrumb: Documentos › Recursos Digitales › WA Business. Grid of 6 product cards, each with color-coded header, product name, description, image count (from Drive listing), and link to gallery. If folder not configured → card shows "Sin configurar" badge and is not clickable.

### `/recursos-digitales/wa-business/:producto`
Breadcrumb: Documentos › Recursos Digitales › WA Business › {Producto}. Toolbar: "Seleccionar todas" toggle + "Descargar N imágenes (ZIP)" button (disabled until ≥1 selected). Grid of image cards with checkbox overlay. Each card shows `thumbnailLink` from Drive API. Download button triggers form POST with selected file IDs.

### `/admin/recursos-digitales`
Form with 6 labeled inputs (one per product, color-coded dot). Hint text per input. Save button → POST → redirect back with success flash.

## Error Handling

- Drive API unavailable → gallery shows error state ("No se pudo cargar la galería")
- Folder ID not configured → product card shows "Sin configurar", gallery shows info state
- Invalid `:producto` slug → 404
- ZIP with 0 file IDs → 400
- ZIP file fetch error → skip file, continue ZIP (partial download)
- Max 50 files per ZIP request → 400 if exceeded

## Dependencies

- `archiver` npm package (ZIP streaming) — needs `npm install archiver`
- Existing `googleapis` + `GOOGLE_SERVICE_ACCOUNT_B64` (already in use)
- Existing `configuracion` table (already in use)
- Existing `requireRole` middleware (already in use)
