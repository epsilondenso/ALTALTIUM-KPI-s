# Micro-sitio Público por Asesor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crear una página pública `/asesor/:username` que muestre el perfil del asesor, catálogo de propiedades outlet disponibles y canales de contacto que crean leads en el CRM.

**Architecture:** EJS server-side rendering con `layout: false` (sin sesión requerida). GET consulta asesor por username, obtiene propiedades de `inventario_outlet` con filtros opcionales y paginación, calcula rating CRM en base a 4 métricas de los últimos 90 días. POST de contacto reutiliza `contacto.service.js` para deduplicar leads. CSS propio con variables CSS para tema claro/oscuro gestionado por localStorage.

**Tech Stack:** Node.js v24 + Express v5, EJS (layout:false), PostgreSQL pool, Google Fonts Montserrat, CSS custom properties dark/light toggle, IntersectionObserver scroll reveal, localStorage.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `public/css/microsite.css` | Create | Variables tema, layout, cards, filtros, animaciones, responsive |
| `src/controllers/public/microsite.controller.js` | Create | GET show + calcularRating; POST registrarContacto |
| `views/public/microsite.ejs` | Create | HTML completo: chrome, hero, rating, contacto, filtros, cards, footer |
| `src/routes/public.routes.js` | Modify | Agregar GET /asesor/:username y POST /asesor/:username/contacto |
| `views/advisor/crm/partials/sidebar.ejs` | Modify | Link "Ver mi perfil público" antes del footer del sidebar |

---

### Task 1: CSS del microsite

**Files:**
- Create: `public/css/microsite.css`

- [ ] **Step 1: Crear el archivo CSS**

Crear `public/css/microsite.css` con el siguiente contenido:

```css
/* ── MICROSITE — Variables de tema ────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

[data-theme="dark"] {
  --bg:#06090f; --bg2:#0b0f1a; --bg3:#111827; --border:#1e2d40;
  --text:#f1f5f9; --text2:#e2e8f0; --muted:#94a3b8; --muted2:#4d6680;
  --teal:#0d9488; --teal-lt:#2dd4bf; --gold:#c9a84c; --card:#0d1220;
  --hero-ov:linear-gradient(to bottom,rgba(0,0,0,.35),rgba(6,9,15,.96));
  --call-bd:#1e2d40; --call-bg:rgba(255,255,255,.03); --call-clr:#cbd5e1;
  --cnt-bd:#1e2d40; --cnt-bg:rgba(255,255,255,.03); --cnt-clr:#cbd5e1;
}
[data-theme="light"] {
  --bg:#f8fafc; --bg2:#ffffff; --bg3:#f1f5f9; --border:#e2e8f0;
  --text:#0f172a; --text2:#1e293b; --muted:#334155; --muted2:#475569;
  --teal:#0d9488; --teal-lt:#0d9488; --gold:#b8860b; --card:#ffffff;
  --hero-ov:linear-gradient(to bottom,rgba(0,0,0,.08),rgba(248,250,252,.9));
  --call-bd:#cbd5e1; --call-bg:#fff; --call-clr:#334155;
  --cnt-bd:#0d9488; --cnt-bg:#f0fdfa; --cnt-clr:#0d9488;
}

/* ── BASE ─────────────────────────────────────────────────── */
html { scroll-behavior:smooth; overflow-x:hidden; max-width:100vw; }
body {
  font-family:'Montserrat','Segoe UI',sans-serif;
  background:var(--bg); color:var(--text);
  transition:background .25s,color .25s;
  overflow-x:hidden; max-width:100vw;
}

/* ── CHROME / NAVBAR ──────────────────────────────────────── */
.chrome {
  position:sticky; top:0; z-index:50;
  display:flex; align-items:center; gap:12px;
  padding:10px 20px;
  background:var(--bg2); border-bottom:1px solid var(--border);
  transition:background .25s,border-color .25s;
}
.chrome-logo { display:flex; align-items:center; gap:8px; text-decoration:none; }
.chrome-al {
  width:28px; height:28px; border-radius:8px;
  background:linear-gradient(135deg,#0d9488,#0891b2);
  display:flex; align-items:center; justify-content:center;
  font-size:13px; font-weight:700; color:#fff; flex-shrink:0;
}
.chrome-brand { font-size:14px; font-weight:700; color:var(--text); }
.chrome-slogan {
  flex:1; text-align:center;
  font-size:12px; font-weight:700; letter-spacing:.09em;
  text-transform:uppercase; color:var(--teal-lt);
}
.toggle {
  display:flex; align-items:center; gap:8px; cursor:pointer;
  padding:6px 10px; border-radius:20px;
  border:1px solid var(--border); background:var(--bg3);
  transition:border-color .2s,background .2s; flex-shrink:0;
}
.toggle:hover { border-color:var(--teal); }
.toggle-ico { width:14px; height:14px; stroke:var(--teal-lt); fill:none; stroke-width:1.8; }
.toggle-lbl { font-size:11px; color:var(--muted); font-weight:500; }
.trk { width:28px; height:16px; border-radius:8px; background:var(--teal); position:relative; transition:background .25s; }
.thb { position:absolute; top:2px; left:2px; width:12px; height:12px; border-radius:50%; background:#fff; transition:transform .25s; }
[data-theme="light"] .thb { transform:translateX(12px); }

/* ── HERO ─────────────────────────────────────────────────── */
.hero { position:relative; height:220px; overflow:hidden; }
.hero-banner { position:absolute; inset:0; background:linear-gradient(135deg,#0c3547 0%,#0d4f6e 40%,#064e3b 100%); }
.hero-ov { position:absolute; inset:0; background:var(--hero-ov); }
.hero-content { position:absolute; bottom:0; left:0; right:0; padding:20px 24px; display:flex; align-items:flex-end; gap:16px; }
.avatar-ring {
  width:76px; height:76px; border-radius:50%;
  border:3px solid var(--teal); flex-shrink:0;
  display:flex; align-items:center; justify-content:center;
  font-size:28px; font-weight:700; color:#fff; margin-bottom:-8px;
  box-shadow:0 4px 20px rgba(0,0,0,.4);
  background:linear-gradient(135deg,#0d9488,#0891b2); overflow:hidden;
}
.avatar-ring img { width:100%; height:100%; object-fit:cover; border-radius:50%; }
.hero-info { flex:1; }
.hero-role { font-size:10px; color:var(--teal-lt); letter-spacing:.12em; text-transform:uppercase; font-weight:600; margin-bottom:4px; }
.hero-name { font-size:22px; font-weight:700; color:#fff; line-height:1.1; margin-bottom:3px; }
.hero-area { font-size:11px; color:rgba(255,255,255,.55); }

/* ── RATING ───────────────────────────────────────────────── */
.rating-bar {
  background:var(--bg2); border-bottom:1px solid var(--border);
  padding:10px 24px; display:flex; align-items:center; gap:10px;
  transition:background .25s,border-color .25s;
}
.stars { color:var(--gold); font-size:16px; letter-spacing:2px; }
.rating-val { font-size:13px; font-weight:700; color:var(--text); }
.rating-badge {
  font-size:10px; color:var(--teal-lt); font-weight:600;
  background:rgba(13,148,136,.12); border:1px solid rgba(13,148,136,.25);
  padding:3px 10px; border-radius:20px; display:flex; align-items:center; gap:5px;
}

/* ── FRANJA CONTACTO ──────────────────────────────────────── */
.contact-strip {
  background:var(--bg2); border-bottom:1px solid var(--border);
  padding:14px 24px; display:flex; align-items:center; gap:10px; flex-wrap:wrap;
  transition:background .25s;
}
.btn-call,.btn-wa,.btn-contact {
  display:inline-flex; align-items:center; gap:7px;
  padding:9px 18px; border-radius:50px;
  font-size:13px; font-weight:600; cursor:pointer; text-decoration:none;
  transition:opacity .18s,transform .15s;
}
.btn-call:hover,.btn-wa:hover,.btn-contact:hover { opacity:.88; transform:translateY(-1px); }
.btn-call { border:1.5px solid var(--call-bd); background:var(--call-bg); color:var(--call-clr); }
.btn-wa { background:#22c55e; color:#fff; border:none; }
.btn-contact { border:1.5px solid var(--cnt-bd); background:var(--cnt-bg); color:var(--cnt-clr); }
.contact-note { font-size:10px; color:var(--muted2); margin-left:4px; }
.btn-ico { width:15px; height:15px; fill:none; stroke:currentColor; stroke-width:1.8; }

/* ── BADGE EMPRESA ────────────────────────────────────────── */
.company-badge {
  background:var(--bg3); border-bottom:1px solid var(--border);
  padding:10px 24px; display:flex; align-items:center; gap:10px;
  font-size:12px; color:var(--muted); transition:background .25s;
}
.company-logo {
  width:24px; height:24px; border-radius:7px;
  background:linear-gradient(135deg,#0d9488,#0891b2);
  display:flex; align-items:center; justify-content:center;
  font-size:11px; font-weight:700; color:#fff; flex-shrink:0;
}
.company-name { color:var(--teal-lt); font-weight:700; }
.verified-chip {
  margin-left:auto; display:inline-flex; align-items:center; gap:4px;
  padding:3px 10px; border-radius:20px;
  background:rgba(13,148,136,.1); border:1px solid rgba(13,148,136,.25);
  font-size:9px; color:var(--teal-lt); font-weight:700;
}

/* ── BARRA BÚSQUEDA / FILTROS ─────────────────────────────── */
.filter-section {
  background:var(--bg2); border-bottom:1px solid var(--border);
  padding:12px 24px; display:flex; align-items:center; gap:10px;
  flex-wrap:wrap; transition:background .25s;
}
.search-wrap {
  display:flex; align-items:center; gap:6px;
  background:var(--bg3); border:1px solid var(--border);
  border-radius:20px; padding:6px 14px;
  flex:0 0 auto; min-width:200px; transition:border-color .18s;
}
.search-wrap:focus-within { border-color:var(--teal); }
.search-wrap input { border:none; background:transparent; color:var(--text); font-size:12px; outline:none; width:100%; }
.search-wrap input::placeholder { color:var(--muted2); }
.search-ico { width:13px; height:13px; stroke:var(--muted2); fill:none; flex-shrink:0; }
.pills { display:flex; align-items:center; gap:6px; overflow-x:auto; scrollbar-width:none; flex:1; }
.pills::-webkit-scrollbar { display:none; }
.fwrap {
  position:relative; display:inline-flex; align-items:center; gap:4px;
  background:var(--bg3); border:1px solid var(--border);
  border-radius:20px; padding:5px 10px 5px 8px;
  cursor:pointer; transition:border-color .18s,background .18s;
  flex-shrink:0; white-space:nowrap; user-select:none;
}
.fwrap:hover { border-color:var(--teal); background:rgba(13,148,136,.06); }
.fwrap select { position:absolute; inset:0; opacity:0; cursor:pointer; width:100%; height:100%; border:none; }
.fw-ico { width:12px; height:12px; stroke:var(--muted2); fill:none; stroke-width:1.8; flex-shrink:0; }
.fw-lbl { font-size:11px; color:var(--text); font-weight:500; pointer-events:none; }
.sort-pill { border-color:rgba(13,148,136,.35); background:rgba(13,148,136,.07); }
.sort-pill .fw-lbl { color:var(--teal-lt); font-weight:600; }
.fsep { width:1px; height:22px; background:var(--border); flex-shrink:0; }

/* ── LAYOUT PRINCIPAL ─────────────────────────────────────── */
.main-wrap { display:flex; align-items:flex-start; max-width:1400px; margin:0 auto; padding:24px; gap:24px; }

/* ── SIDEBAR INFOGRAFÍAS ──────────────────────────────────── */
.infogr-sidebar { width:242px; flex-shrink:0; }
.sidebar-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; }
.sidebar-title { font-size:13px; font-weight:700; color:var(--text); }
.sidebar-link { font-size:11px; color:var(--teal-lt); text-decoration:none; }
.info-card {
  background:var(--card); border:1px solid var(--border);
  border-radius:10px; overflow:hidden; cursor:pointer; margin-bottom:8px;
  transition:transform .15s,box-shadow .15s; text-decoration:none; display:block;
}
.info-card:hover { transform:translateY(-2px); box-shadow:0 6px 20px rgba(0,0,0,.18); }
.info-thumb { height:64px; display:flex; align-items:center; justify-content:center; padding:10px; font-size:10px; font-weight:700; color:#fff; text-align:center; line-height:1.3; letter-spacing:.03em; }
.it1{background:linear-gradient(135deg,#0c3547,#0d4f6e);}
.it2{background:linear-gradient(135deg,#1a1a2e,#16213e);}
.it3{background:linear-gradient(135deg,#064e3b,#065f46);}
.it4{background:linear-gradient(135deg,#1e3a5f,#1a365d);}
.it5{background:linear-gradient(135deg,#3d1a00,#7c2d12);}
.it6{background:linear-gradient(135deg,#0f4c75,#1e3a5f);}
.it7{background:linear-gradient(135deg,#7c3a0c,#a16207);}
.it8{background:linear-gradient(135deg,#0d6b6b,#0c3b3b);}
.it9{background:linear-gradient(135deg,#312e81,#4338ca);}
.it10{background:linear-gradient(135deg,#881337,#be123c);}
.info-foot { padding:8px 10px; }
.info-name { font-size:10px; font-weight:600; color:var(--text2); line-height:1.3; }

/* ── COLUMNA PROPIEDADES ──────────────────────────────────── */
.catalog-col { flex:1; min-width:0; }
.catalog-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; }
.catalog-title { font-size:14px; font-weight:700; color:var(--text); }
.cat-count { font-size:11px; color:var(--muted); background:var(--bg3); border:1px solid var(--border); padding:3px 10px; border-radius:20px; }
.empty-state { text-align:center; padding:60px 20px; color:var(--muted); font-size:13px; }

/* ── PROPERTY CARDS ───────────────────────────────────────── */
.prop-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-bottom:24px; }
.pcard {
  background:var(--card); border:1px solid var(--border); border-radius:12px; overflow:hidden;
  opacity:0; transform:translateY(24px);
  transition:opacity .45s ease,transform .45s ease,box-shadow .2s;
}
.pcard.revealed { opacity:1; transform:translateY(0); }
.pcard.revealed:hover { transform:translateY(-3px); box-shadow:0 10px 32px rgba(0,0,0,.22); }

.cslider { position:relative; height:140px; overflow:hidden; background:var(--bg3); }
.cslider-inner { display:flex; height:100%; transition:transform .35s ease; }
.cslide { min-width:100%; height:100%; object-fit:cover; flex-shrink:0; }
.cslide-placeholder { min-width:100%; height:100%; flex-shrink:0; display:flex; align-items:center; justify-content:center; background:linear-gradient(135deg,#1e3a5f,#0c3547); }
.skel-ov {
  position:absolute; inset:0; z-index:5;
  background:linear-gradient(90deg,var(--bg3) 25%,var(--border) 50%,var(--bg3) 75%);
  background-size:1600px 100%; animation:shimmer 1.5s infinite linear;
  transition:opacity .5s ease; pointer-events:none;
}
.skel-ov.done { opacity:0; }
@keyframes shimmer { 0%{background-position:-800px 0} 100%{background-position:800px 0} }
.carrow {
  position:absolute; top:50%; transform:translateY(-50%);
  width:44px; height:44px; border-radius:50%;
  background:rgba(0,0,0,.5); border:none; color:#fff; cursor:pointer; z-index:4;
  display:flex; align-items:center; justify-content:center; transition:background .18s;
  font-size:20px; line-height:1;
}
.carrow:hover { background:rgba(0,0,0,.75); }
.carrow.lft { left:-8px; } .carrow.rgt { right:-8px; }
.cdots { position:absolute; bottom:6px; left:0; right:0; display:flex; justify-content:center; gap:5px; z-index:4; }
.cdot { width:5px; height:5px; border-radius:50%; background:rgba(255,255,255,.4); cursor:pointer; transition:background .2s; }
.cdot.active { background:#fff; }
.card-badge {
  position:absolute; top:8px; left:8px; z-index:4;
  background:rgba(13,148,136,.9); color:#fff;
  font-size:9px; font-weight:700; padding:2px 8px; border-radius:20px;
  text-transform:uppercase; letter-spacing:.06em;
}
.card-body { padding:10px 12px 12px; cursor:pointer; }
.card-tipo { font-size:9px; color:var(--muted2); text-transform:uppercase; letter-spacing:.08em; margin-bottom:3px; }
.card-title { font-size:12px; font-weight:600; color:var(--text2); line-height:1.3; margin-bottom:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.card-price { font-size:15px; font-weight:700; color:var(--teal-lt); margin-bottom:8px; }
.card-metrics { display:flex; gap:8px; flex-wrap:wrap; }
.mitem { font-size:10px; color:var(--muted2); display:flex; align-items:center; gap:4px; }
.mico { width:11px; height:11px; fill:none; stroke:currentColor; stroke-width:1.8; }
.card-btns { display:flex; gap:6px; border-top:1px solid var(--border); padding:10px 12px 12px; margin-top:0; }
.cbtn {
  flex:1; display:flex; align-items:center; justify-content:center; gap:5px;
  padding:6px 4px; border-radius:8px; border:1px solid var(--border);
  background:transparent; color:var(--muted); font-size:10px; font-weight:600;
  cursor:pointer; text-decoration:none; transition:border-color .18s,color .18s;
}
.cbtn:hover { border-color:var(--teal); color:var(--teal-lt); }
.cbtn-ico { width:11px; height:11px; fill:none; stroke:currentColor; stroke-width:1.8; }
.cbtn.wa { color:#22c55e; border-color:rgba(34,197,94,.3); }
.cbtn.wa:hover { border-color:#22c55e; background:rgba(34,197,94,.06); }

/* ── PAGINACIÓN ───────────────────────────────────────────── */
.pagination { display:flex; justify-content:center; align-items:center; gap:8px; margin-top:24px; }
.pag-btn { padding:7px 16px; border-radius:8px; border:1px solid var(--border); background:transparent; color:var(--muted); font-size:12px; font-weight:600; cursor:pointer; text-decoration:none; transition:border-color .18s,color .18s; }
.pag-btn:hover,.pag-btn.active { border-color:var(--teal); color:var(--teal-lt); }

/* ── FOOTER ───────────────────────────────────────────────── */
.site-footer { background:var(--bg2); border-top:1px solid var(--border); margin-top:40px; padding:32px 24px 24px; transition:background .25s; }
.footer-line { height:2px; border-radius:1px; background:linear-gradient(90deg,var(--gold),var(--teal-lt)); margin-bottom:24px; }
.footer-inner { max-width:1400px; margin:0 auto; display:flex; justify-content:space-between; align-items:flex-start; gap:24px; flex-wrap:wrap; }
.footer-logo-block { display:flex; flex-direction:column; gap:6px; }
.footer-logo { display:flex; align-items:center; gap:8px; }
.footer-slogan { font-size:11px; color:var(--teal-lt); font-weight:600; letter-spacing:.06em; text-transform:uppercase; }
.footer-addr { font-size:11px; color:var(--muted2); margin-top:6px; text-decoration:none; }
.footer-addr:hover { color:var(--teal-lt); }
.social-row { display:flex; gap:10px; align-items:center; }
.soc-icon { width:34px; height:34px; border-radius:8px; border:1px solid var(--border); display:flex; align-items:center; justify-content:center; color:var(--teal-lt); background:transparent; transition:border-color .18s,background .18s,transform .2s; text-decoration:none; }
.soc-icon:hover { border-color:var(--teal); background:rgba(13,148,136,.1); transform:translateY(-2px); }
.soc-icon svg { width:16px; height:16px; fill:currentColor; }
.footer-copy { max-width:1400px; margin:20px auto 0; font-size:10px; color:var(--muted2); display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
.footer-copy a { color:var(--muted2); text-decoration:none; }
.footer-copy a:hover { color:var(--teal-lt); }

/* ── FAB WHATSAPP ─────────────────────────────────────────── */
.fab-wa { position:fixed; bottom:20px; right:20px; width:48px; height:48px; border-radius:50%; background:#22c55e; color:#fff; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 16px rgba(34,197,94,.4); text-decoration:none; z-index:999; transition:transform .2s,box-shadow .2s; }
.fab-wa:hover { transform:scale(1.08); box-shadow:0 6px 24px rgba(34,197,94,.5); }
.fab-wa svg { width:24px; height:24px; fill:#fff; }

/* ── MODAL CONTACTO ───────────────────────────────────────── */
.modal-ov { position:fixed; inset:0; z-index:999; background:rgba(0,0,0,.6); display:flex; align-items:center; justify-content:center; padding:20px; opacity:0; pointer-events:none; transition:opacity .25s; }
.modal-ov.open { opacity:1; pointer-events:auto; }
.modal-box { background:var(--bg2); border:1px solid var(--border); border-radius:16px; padding:28px; width:100%; max-width:420px; position:relative; transform:scale(.95); transition:transform .25s; }
.modal-ov.open .modal-box { transform:scale(1); }
.modal-title { font-size:16px; font-weight:700; color:var(--text); margin-bottom:4px; }
.modal-sub { font-size:12px; color:var(--muted); margin-bottom:20px; }
.modal-field { margin-bottom:14px; }
.modal-label { font-size:11px; font-weight:600; color:var(--muted); margin-bottom:5px; display:block; }
.modal-input { width:100%; padding:10px 14px; border-radius:8px; border:1px solid var(--border); background:var(--bg3); color:var(--text); font-size:13px; outline:none; transition:border-color .18s; }
.modal-input:focus { border-color:var(--teal); }
.modal-submit { width:100%; padding:12px; border-radius:10px; background:var(--teal); color:#fff; border:none; font-size:13px; font-weight:700; cursor:pointer; transition:opacity .18s; margin-top:6px; }
.modal-submit:hover { opacity:.9; }
.modal-submit:disabled { opacity:.6; cursor:default; }
.modal-close { position:absolute; top:12px; right:14px; background:transparent; border:none; cursor:pointer; color:var(--muted); font-size:20px; line-height:1; }
.modal-msg { font-size:12px; color:var(--teal-lt); margin-top:10px; text-align:center; min-height:18px; }

/* ── RESPONSIVE ───────────────────────────────────────────── */
@media (max-width:1024px) {
  .prop-grid { grid-template-columns:repeat(2,1fr); }
  .infogr-sidebar { width:200px; }
}
@media (max-width:768px) {
  .main-wrap { flex-direction:column; padding:16px; gap:20px; }
  .infogr-sidebar { width:100%; }
  .info-cards { display:flex; overflow-x:auto; gap:10px; scrollbar-width:none; }
  .info-cards::-webkit-scrollbar { display:none; }
  .info-card { min-width:140px; margin-bottom:0; }
  .prop-grid { grid-template-columns:1fr; }
  .chrome-slogan { display:none; }
}
@media (max-width:480px) {
  .btn-call span,.btn-contact span { display:none; }
  .hero-name { font-size:18px; }
}

/* ── ACCESIBILIDAD ────────────────────────────────────────── */
@media (prefers-reduced-motion:reduce) {
  * { transition:none !important; animation:none !important; }
  .pcard:hover,.info-card:hover { transform:none !important; }
}
:focus-visible { outline:2px solid var(--teal-lt); outline-offset:2px; border-radius:4px; }
```

- [ ] **Step 2: Verificar que el archivo existe**

```powershell
ls public/css/microsite.css
```
Expected: el archivo aparece listado.

- [ ] **Step 3: Commit**

```bash
git add public/css/microsite.css
git commit -m "feat: CSS microsite público asesor — variables tema, layout, cards, animaciones"
```

---

### Task 2: Controlador público del microsite

**Files:**
- Create: `src/controllers/public/microsite.controller.js`

- [ ] **Step 1: Crear el controlador**

Crear `src/controllers/public/microsite.controller.js`:

```javascript
'use strict';

const pool = require('../../db/pool');
const contactoSvc = require('../../services/public/contacto.service');
const notifSvc = require('../../services/notificaciones.service');

const INFOGRAFIAS = [
  { nombre: 'Proceso de Compra Outlet', thumb: 'it1', url: null },
  { nombre: '¿Qué es un Remate Bancario?', thumb: 'it2', url: null },
  { nombre: 'Beneficios de Comprar con Nosotros', thumb: 'it3', url: null },
  { nombre: 'Documentos Requeridos', thumb: 'it4', url: null },
  { nombre: 'Preguntas Frecuentes', thumb: 'it5', url: null },
  { nombre: '¿Qué es una Ejecución de Sentencia?', thumb: 'it6', url: null },
  { nombre: 'Tipos de Crédito Hipotecario', thumb: 'it7', url: null },
  { nombre: 'Guía del Comprador Primera Vez', thumb: 'it8', url: null },
  { nombre: 'Zonas con Mayor Plusvalía 2025', thumb: 'it9', url: null },
  { nombre: 'Costos Adicionales al Comprar', thumb: 'it10', url: null },
];

async function calcularRating(advisorId) {
  const { rows } = await pool.query(`
    WITH base AS (
      SELECT l.id, l.opened_at, l.transferred_at, l.etapa
      FROM crm_leads l
      WHERE l.advisor_id = $1
        AND l.created_at >= NOW() - INTERVAL '90 days'
    ),
    activs AS (
      SELECT a.lead_id, a.created_at
      FROM crm_activities a
      WHERE a.advisor_id = $1
        AND a.created_at >= NOW() - INTERVAL '90 days'
    )
    SELECT
      (SELECT COUNT(*) FROM base) AS total_leads,
      COUNT(DISTINCT a.lead_id) AS leads_atendidos,
      COUNT(a.lead_id) AS total_actividades,
      (SELECT COUNT(*) FROM base
        WHERE etapa IN ('perfilado','cotizacion','cita','negociacion','cierre')
      ) AS perfiles,
      (SELECT COUNT(*) FROM activs ac
        JOIN base b ON b.id = ac.lead_id
        WHERE ac.created_at > COALESCE(b.opened_at, b.transferred_at) + INTERVAL '1 day'
      ) AS seguimientos
    FROM base b
    LEFT JOIN activs a ON a.lead_id = b.id
  `, [advisorId]);

  const r = rows[0];
  const totalLeads = parseInt(r.total_leads || 0);
  if (totalLeads < 5) return null;

  const MAX_LEADS = 50, MAX_ACT = 200, MAX_PERFILES = 30, MAX_SEG = 40;
  const s1 = Math.min(parseInt(r.leads_atendidos || 0) / MAX_LEADS, 1);
  const s2 = Math.min(parseInt(r.total_actividades || 0) / MAX_ACT, 1);
  const s3 = Math.min(parseInt(r.perfiles || 0) / MAX_PERFILES, 1);
  const s4 = Math.min(parseInt(r.seguimientos || 0) / MAX_SEG, 1);
  const score = (s1 + s2 + s3 + s4) / 4;
  return parseFloat(Math.max(1.0, Math.min(5.0, 1.0 + score * 4.0)).toFixed(1));
}

function formatMXN(v) {
  if (!v) return null;
  const n = Number(String(v).replace(/[^0-9.-]/g, ''));
  if (!Number.isFinite(n) || n === 0) return null;
  return new Intl.NumberFormat('es-MX', {
    style: 'currency', currency: 'MXN',
    minimumFractionDigits: 0, maximumFractionDigits: 0,
  }).format(n);
}

async function show(req, res) {
  try {
    const { username } = req.params;
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const PER_PAGE = 20;
    const offset = (page - 1) * PER_PAGE;

    const q = (req.query.q || '').toString().trim();
    const tipo = (req.query.tipo || '').toString().trim();
    const municipio = (req.query.municipio || '').toString().trim();
    const sort = (req.query.sort || 'recientes').toString().trim();

    const { rows: asesorRows } = await pool.query(
      `SELECT id, nombre, apellidos, username, telefono, role, gerente, area, avatar_url
       FROM users
       WHERE username = $1 AND is_active = true AND role = 'advisor'
       LIMIT 1`,
      [username]
    );
    if (!asesorRows.length) {
      return res.status(404).render('errors/404', {
        layout: false,
        title: 'Asesor no encontrado',
      });
    }
    const asesor = asesorRows[0];

    const params = [];
    let where = `WHERE estatus = 'disponible'`;

    if (q) {
      params.push(`%${q.toLowerCase()}%`);
      where += ` AND (LOWER(municipio) LIKE $${params.length} OR LOWER(colonia) LIKE $${params.length} OR LOWER(calle) LIKE $${params.length})`;
    }
    if (tipo) {
      params.push(tipo);
      where += ` AND tipo = $${params.length}`;
    }
    if (municipio) {
      params.push(municipio);
      where += ` AND municipio = $${params.length}`;
    }

    const orderMap = {
      recientes:    'created_at DESC',
      mayor_precio: 'COALESCE(valor_comercial, costo_total) DESC NULLS LAST',
      menor_precio: 'COALESCE(valor_comercial, costo_total) ASC NULLS LAST',
    };
    const orderSql = orderMap[sort] || 'created_at DESC';

    const { rows: countRows } = await pool.query(
      `SELECT COUNT(*) AS total FROM inventario_outlet ${where}`,
      [...params]
    );
    const total = parseInt(countRows[0].total || 0);

    params.push(PER_PAGE, offset);
    const { rows: propRows } = await pool.query(`
      SELECT id, folio, tipo, etapa, estatus, calle, colonia, municipio, estado,
             construccion, recamaras, sanitarios, estacionamientos, terreno,
             costo_total, valor_comercial, imagenes_cache
      FROM inventario_outlet
      ${where}
      ORDER BY ${orderSql}
      LIMIT $${params.length - 1} OFFSET $${params.length}
    `, params);

    const propiedades = propRows.map(p => {
      let imgs = [];
      try {
        const raw = typeof p.imagenes_cache === 'string'
          ? JSON.parse(p.imagenes_cache)
          : p.imagenes_cache;
        if (Array.isArray(raw)) {
          imgs = raw.map(x => x?.url || x).filter(Boolean).slice(0, 3);
        }
      } catch (_) {}
      return {
        ...p,
        imagenes: imgs,
        precioFormatted: formatMXN(p.valor_comercial || p.costo_total),
      };
    });

    const [{ rows: municipioRows }, { rows: tipoRows }] = await Promise.all([
      pool.query(`SELECT DISTINCT municipio FROM inventario_outlet WHERE estatus = 'disponible' AND municipio IS NOT NULL ORDER BY municipio LIMIT 50`),
      pool.query(`SELECT DISTINCT tipo FROM inventario_outlet WHERE estatus = 'disponible' AND tipo IS NOT NULL ORDER BY tipo`),
    ]);

    const rating = await calcularRating(asesor.id);
    const baseUrl = `${req.protocol}://${req.get('host')}`;

    return res.render('public/microsite', {
      layout: false,
      title: `${asesor.nombre} ${asesor.apellidos || ''} — Asesor Inmobiliario | Altaltium`,
      metaDescription: `Propiedades outlet disponibles con ${asesor.nombre}. Remates bancarios y ejecuciones de sentencia en ${asesor.area || 'México'}.`,
      canonicalUrl: `${baseUrl}/asesor/${username}`,
      asesor,
      propiedades,
      total,
      page,
      totalPages: Math.ceil(total / PER_PAGE),
      municipios: municipioRows.map(r => r.municipio),
      tipos: tipoRows.map(r => r.tipo),
      rating,
      infografias: INFOGRAFIAS,
      filtros: { q, tipo, municipio, sort },
    });
  } catch (err) {
    console.error('❌ [microsite] show error:', err.message);
    return res.status(500).send('Error interno del servidor');
  }
}

async function registrarContacto(req, res) {
  try {
    const { username } = req.params;
    const { nombre, telefono, email, mensaje } = req.body || {};

    if (!nombre || !telefono) {
      return res.status(400).json({ ok: false, error: 'Nombre y teléfono son requeridos.' });
    }

    const { rows } = await pool.query(
      `SELECT id, manager_id FROM users WHERE username = $1 AND is_active = true AND role = 'advisor' LIMIT 1`,
      [username]
    );
    if (!rows.length) {
      return res.status(404).json({ ok: false, error: 'Asesor no encontrado.' });
    }

    const advisorId = rows[0].id;
    const managerId = rows[0].manager_id;
    const leadDuplicado = await contactoSvc.buscarLeadDuplicado(telefono, advisorId);

    if (leadDuplicado) {
      await contactoSvc.actualizarLeadDuplicado(leadDuplicado.id, { nombre, email, mensaje });
      return res.json({ ok: true, nuevo: false });
    }

    const { rows: leadRows } = await pool.query(
      `INSERT INTO crm_leads (nombre, telefono, email, advisor_id, status, etapa, transferred_at, opened_at)
       VALUES ($1, $2, $3, $4, 'open', 'nuevo', NOW(), NOW())
       RETURNING id`,
      [nombre.trim(), telefono.trim(), (email || '').trim() || null, advisorId]
    );
    const leadId = leadRows[0].id;

    if (mensaje && mensaje.trim()) {
      await pool.query(
        `INSERT INTO crm_activities (lead_id, advisor_id, type, observations, created_at)
         VALUES ($1, $2, 'contacto_web', $3, NOW())`,
        [leadId, advisorId, mensaje.trim()]
      );
    }

    const notifMsg = `Nuevo lead desde tu microsite: ${nombre}`;
    await notifSvc.crearNotificacion({
      userId: advisorId,
      tipo: 'lead_publico',
      mensaje: notifMsg,
      urlAccion: `/advisor/crm/leads/${leadId}`,
    });

    if (managerId) {
      await notifSvc.crearNotificacion({
        userId: managerId,
        tipo: 'lead_publico',
        mensaje: notifMsg,
        urlAccion: `/manager/crm/leads/${leadId}`,
      });
    }

    return res.json({ ok: true, nuevo: true });
  } catch (err) {
    console.error('❌ [microsite] registrarContacto error:', err.message);
    return res.status(500).json({ ok: false, error: 'Error al registrar contacto.' });
  }
}

module.exports = { show, registrarContacto };
```

- [ ] **Step 2: Verificar sintaxis**

```bash
node -e "require('./src/controllers/public/microsite.controller.js'); console.log('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/controllers/public/microsite.controller.js
git commit -m "feat: controlador microsite público asesor — GET show + calcularRating + POST contacto"
```

---

### Task 3: Vista EJS del microsite

**Files:**
- Create: `views/public/microsite.ejs`

- [ ] **Step 1: Crear la vista**

Crear `views/public/microsite.ejs`:

```html
<!DOCTYPE html>
<html lang="es" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title><%= title %></title>
  <meta name="description" content="<%= metaDescription %>">
  <link rel="canonical" href="<%= canonicalUrl %>">
  <meta property="og:title" content="<%= title %>">
  <meta property="og:description" content="<%= metaDescription %>">
  <% if (asesor.avatar_url) { %><meta property="og:image" content="<%= asesor.avatar_url %>"><% } %>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/microsite.css">
</head>
<body>

<!-- CHROME -->
<header class="chrome">
  <a href="/" class="chrome-logo">
    <div class="chrome-al">Al</div>
    <span class="chrome-brand">Altaltium</span>
  </a>
  <div class="chrome-slogan">¡LA LLAVE DE TU FUTURO!</div>
  <button class="toggle" onclick="toggleTheme()" aria-label="Cambiar tema">
    <svg id="ico-moon" class="toggle-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
      <path d="M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79z"/>
    </svg>
    <svg id="ico-sun" class="toggle-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" style="display:none">
      <circle cx="12" cy="12" r="5"/>
      <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
    <span id="tlbl" class="toggle-lbl">Oscuro</span>
    <div class="trk"><div class="thb"></div></div>
  </button>
</header>

<!-- HERO -->
<section class="hero">
  <div class="hero-banner"></div>
  <div class="hero-ov"></div>
  <div class="hero-content">
    <div class="avatar-ring">
      <% if (asesor.avatar_url) { %>
        <img src="<%= asesor.avatar_url %>" alt="<%= asesor.nombre %>" loading="lazy">
      <% } else { %>
        <%= String(asesor.nombre || 'A').charAt(0).toUpperCase() %><%= String(asesor.apellidos || '').charAt(0).toUpperCase() %>
      <% } %>
    </div>
    <div class="hero-info">
      <div class="hero-role">Asesor Comercial · Outlet Inmobiliario</div>
      <div class="hero-name"><%= asesor.nombre %> <%= asesor.apellidos || '' %></div>
      <div class="hero-area"><%= [asesor.gerente ? 'Gerencia ' + asesor.gerente : '', asesor.area || ''].filter(Boolean).join(' · ') %></div>
    </div>
  </div>
</section>

<!-- RATING -->
<% if (rating !== null) { %>
<div class="rating-bar">
  <% const fullStars = Math.floor(rating); const half = (rating - fullStars) >= 0.5; %>
  <span class="stars" aria-label="<%= rating %> de 5 estrellas">
    <% for(let i=0;i<5;i++){%><%= i<fullStars?'★':(i===fullStars&&half?'★':'☆') %><% } %>
  </span>
  <span class="rating-val"><%= rating %></span>
  <span class="rating-badge">
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
    Asesor verificado Altaltium
  </span>
</div>
<% } %>

<!-- FRANJA CONTACTO -->
<div class="contact-strip">
  <a href="tel:+52<%= asesor.telefono %>" class="btn-call" aria-label="Llamar">
    <svg class="btn-ico" viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 1.27h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.96a16 16 0 0 0 6.09 6.09l.96-.96a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7a2 2 0 0 1 1.72 2.02z"/></svg>
    <span>Llamar</span>
  </a>
  <a href="https://wa.me/52<%= asesor.telefono %>?text=Hola%20<%= encodeURIComponent(asesor.nombre) %>%2C%20vi%20tu%20perfil%20en%20Altaltium" target="_blank" rel="noopener" class="btn-wa" aria-label="WhatsApp">
    <svg class="btn-ico" viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M11.998 0C5.373 0 .001 5.373.001 11.998a11.952 11.952 0 0 0 1.7 6.115L0 24l6.013-1.58A11.948 11.948 0 0 0 11.998 24C18.623 24 24 18.627 24 12.002 24 5.372 18.624 0 11.998 0zm0 21.937a9.947 9.947 0 0 1-5.116-1.409l-.366-.217-3.797.996 1.013-3.696-.24-.38A9.96 9.96 0 0 1 2.041 12c0-5.495 4.463-9.958 9.957-9.958 5.494 0 9.957 4.463 9.957 9.958 0 5.495-4.463 9.937-9.957 9.937z"/></svg>
    WhatsApp
  </a>
  <button class="btn-contact" onclick="abrirModal()" aria-label="Formulario de contacto">
    <svg class="btn-ico" viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
    <span>Contactar</span>
  </button>
  <span class="contact-note">Respuesta en menos de 5 min · Sin compromiso</span>
</div>

<!-- BADGE EMPRESA -->
<div class="company-badge">
  <div class="company-logo">Al</div>
  <span>Asesor certificado de <strong class="company-name">Altaltium · Real Estate Solutions</strong></span>
  <div class="verified-chip">
    <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
    Verificado
  </div>
</div>

<!-- BARRA FILTROS -->
<form method="GET" id="filter-form">
<div class="filter-section">
  <div class="search-wrap">
    <svg class="search-ico" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" fill="none"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    <input type="text" name="q" value="<%= filtros.q %>" placeholder="Buscar zona, municipio..." aria-label="Buscar propiedades" oninput="debounceSubmit()">
  </div>
  <div class="pills">
    <div class="fwrap">
      <svg class="fw-ico" viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
      <span class="fw-lbl"><%= filtros.tipo || 'Tipo' %></span>
      <select name="tipo" onchange="this.form.submit()" aria-label="Filtrar por tipo">
        <option value="">Todos los tipos</option>
        <% tipos.forEach(t => { %><option value="<%= t %>" <%= filtros.tipo === t ? 'selected' : '' %>><%= t %></option><% }); %>
      </select>
    </div>
    <div class="fwrap">
      <svg class="fw-ico" viewBox="0 0 24 24"><circle cx="12" cy="10" r="3"/><path d="M12 2a8 8 0 0 1 8 8c0 5.25-8 14-8 14S4 15.25 4 10a8 8 0 0 1 8-8z"/></svg>
      <span class="fw-lbl"><%= filtros.municipio || 'Municipio' %></span>
      <select name="municipio" onchange="this.form.submit()" aria-label="Filtrar por municipio">
        <option value="">Todos los municipios</option>
        <% municipios.forEach(m => { %><option value="<%= m %>" <%= filtros.municipio === m ? 'selected' : '' %>><%= m %></option><% }); %>
      </select>
    </div>
    <div class="fsep"></div>
    <div class="fwrap sort-pill">
      <svg class="fw-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/></svg>
      <span class="fw-lbl">Ordenar</span>
      <select name="sort" onchange="this.form.submit()" aria-label="Ordenar resultados">
        <option value="recientes" <%= filtros.sort === 'recientes' ? 'selected' : '' %>>Más recientes</option>
        <option value="mayor_precio" <%= filtros.sort === 'mayor_precio' ? 'selected' : '' %>>Mayor precio</option>
        <option value="menor_precio" <%= filtros.sort === 'menor_precio' ? 'selected' : '' %>>Menor precio</option>
      </select>
    </div>
  </div>
</div>
</form>

<!-- CUERPO PRINCIPAL -->
<div class="main-wrap">

  <!-- Sidebar infografías -->
  <aside class="infogr-sidebar">
    <div class="sidebar-header">
      <span class="sidebar-title">Infografías</span>
      <a href="#" class="sidebar-link">Ver todas →</a>
    </div>
    <div class="info-cards">
      <% infografias.forEach(inf => { %>
      <a class="info-card" href="<%= inf.url || '#' %>" <%= inf.url ? 'target="_blank" rel="noopener"' : 'onclick="return false"' %>>
        <div class="info-thumb <%= inf.thumb %>"><%= inf.nombre %></div>
        <div class="info-foot"><div class="info-name"><%= inf.nombre %></div></div>
      </a>
      <% }); %>
    </div>
  </aside>

  <!-- Columna propiedades -->
  <div class="catalog-col">
    <div class="catalog-header">
      <span class="catalog-title">Propiedades disponibles</span>
      <span class="cat-count" id="result-count"><%= total %> resultados</span>
    </div>

    <% if (!propiedades.length) { %>
    <div class="empty-state">Este asesor no tiene propiedades disponibles en este momento.</div>
    <% } else { %>
    <div class="prop-grid">
      <% propiedades.forEach((p, i) => { %>
      <article class="pcard" data-idx="<%= i %>">
        <div class="cslider" id="slider-<%= p.id %>">
          <div class="cslider-inner" id="slides-<%= p.id %>">
            <% if (p.imagenes.length > 0) { %>
              <% p.imagenes.forEach(img => { %>
              <img class="cslide" src="<%= img %>" alt="<%= p.tipo || 'Propiedad' %> en <%= p.municipio || '' %>" loading="lazy">
              <% }); %>
            <% } else { %>
              <div class="cslide-placeholder">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
              </div>
            <% } %>
          </div>
          <span class="card-badge"><%= p.tipo || 'Propiedad' %></span>
          <% if (p.imagenes.length > 1) { %>
          <button class="carrow lft" onclick="slideCard('<%= p.id %>', -1)" aria-label="Imagen anterior">‹</button>
          <button class="carrow rgt" onclick="slideCard('<%= p.id %>', 1)" aria-label="Imagen siguiente">›</button>
          <div class="cdots">
            <% p.imagenes.forEach((_, di) => { %><div class="cdot <%= di===0?'active':'' %>" id="dot-<%= p.id %>-<%= di %>"></div><% }); %>
          </div>
          <% } %>
        </div>
        <div class="card-body" onclick="window.open('/p/<%= p.id %>','_blank')">
          <div class="card-tipo"><%= p.etapa || 'Ejecución de sentencia' %></div>
          <div class="card-title"><%= [p.colonia, p.municipio, p.estado].filter(Boolean).join(', ') || p.calle || 'Sin ubicación' %></div>
          <% if (p.precioFormatted) { %><div class="card-price"><%= p.precioFormatted %></div><% } %>
          <div class="card-metrics">
            <% if (p.construccion) { %><span class="mitem"><svg class="mico" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/></svg><%= p.construccion %> m²</span><% } %>
            <% if (p.recamaras) { %><span class="mitem"><svg class="mico" viewBox="0 0 24 24"><path d="M2 7h20v10H2zM2 7V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v2"/></svg><%= p.recamaras %> rec.</span><% } %>
            <% if (p.sanitarios) { %><span class="mitem"><svg class="mico" viewBox="0 0 24 24"><path d="M3 14h18v2a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4v-2z"/></svg><%= p.sanitarios %> baños</span><% } %>
          </div>
        </div>
        <div class="card-btns">
          <a href="tel:+52<%= asesor.telefono %>" class="cbtn" aria-label="Llamar">
            <svg class="cbtn-ico" viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.6 1.27h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.96a16 16 0 0 0 6.09 6.09l.96-.96a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7a2 2 0 0 1 1.72 2.02z"/></svg>
            Llamar
          </a>
          <a href="https://wa.me/52<%= asesor.telefono %>" target="_blank" rel="noopener" class="cbtn wa" aria-label="WhatsApp">
            <svg class="cbtn-ico" viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M11.998 0C5.373 0 .001 5.373.001 11.998a11.952 11.952 0 0 0 1.7 6.115L0 24l6.013-1.58A11.948 11.948 0 0 0 11.998 24C18.623 24 24 18.627 24 12.002 24 5.372 18.624 0 11.998 0zm0 21.937a9.947 9.947 0 0 1-5.116-1.409l-.366-.217-3.797.996 1.013-3.696-.24-.38A9.96 9.96 0 0 1 2.041 12c0-5.495 4.463-9.958 9.957-9.958 5.494 0 9.957 4.463 9.957 9.958 0 5.495-4.463 9.937-9.957 9.937z"/></svg>
            WhatsApp
          </a>
          <button class="cbtn" onclick="abrirModal()" aria-label="Contactar">
            <svg class="cbtn-ico" viewBox="0 0 24 24"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
            Contactar
          </button>
        </div>
      </article>
      <% }); %>
    </div>

    <% if (totalPages > 1) { %>
    <nav class="pagination" aria-label="Páginas">
      <% if (page > 1) { %><a href="?page=<%= page-1 %>&q=<%= encodeURIComponent(filtros.q) %>&tipo=<%= encodeURIComponent(filtros.tipo) %>&municipio=<%= encodeURIComponent(filtros.municipio) %>&sort=<%= filtros.sort %>" class="pag-btn">← Anterior</a><% } %>
      <% for(let pg=Math.max(1,page-2);pg<=Math.min(totalPages,page+2);pg++){%><a href="?page=<%= pg %>&q=<%= encodeURIComponent(filtros.q) %>&tipo=<%= encodeURIComponent(filtros.tipo) %>&municipio=<%= encodeURIComponent(filtros.municipio) %>&sort=<%= filtros.sort %>" class="pag-btn <%= pg===page?'active':'' %>"><%= pg %></a><%}%>
      <% if (page < totalPages) { %><a href="?page=<%= page+1 %>&q=<%= encodeURIComponent(filtros.q) %>&tipo=<%= encodeURIComponent(filtros.tipo) %>&municipio=<%= encodeURIComponent(filtros.municipio) %>&sort=<%= filtros.sort %>" class="pag-btn">Siguiente →</a><% } %>
    </nav>
    <% } %>
    <% } %>
  </div>
</div>

<!-- FOOTER -->
<footer class="site-footer">
  <div class="footer-line"></div>
  <div class="footer-inner">
    <div class="footer-logo-block">
      <div class="footer-logo"><div class="chrome-al">Al</div><span class="chrome-brand">Altaltium</span></div>
      <div class="footer-slogan">La Llave de Tu Futuro</div>
      <a href="https://maps.google.com/?q=Altaltium+Real+Estate+Mexico" target="_blank" rel="noopener" class="footer-addr">Real Estate Solutions · México</a>
    </div>
    <div class="social-row">
      <a href="#" target="_blank" rel="noopener" class="soc-icon" aria-label="Facebook"><svg viewBox="0 0 24 24"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg></a>
      <a href="#" target="_blank" rel="noopener" class="soc-icon" aria-label="Instagram"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg></a>
      <a href="#" target="_blank" rel="noopener" class="soc-icon" aria-label="YouTube"><svg viewBox="0 0 24 24"><path d="M22.54 6.42a2.78 2.78 0 0 0-1.95-1.96C18.88 4 12 4 12 4s-6.88 0-8.59.46A2.78 2.78 0 0 0 1.46 6.42 29 29 0 0 0 1 12a29 29 0 0 0 .46 5.58A2.78 2.78 0 0 0 3.41 19.6C5.12 20 12 20 12 20s6.88 0 8.59-.46a2.78 2.78 0 0 0 1.95-1.95A29 29 0 0 0 23 12a29 29 0 0 0-.46-5.58z"/><polygon points="9.75 15.02 15.5 12 9.75 8.98 9.75 15.02"/></svg></a>
      <a href="#" target="_blank" rel="noopener" class="soc-icon" aria-label="TikTok"><svg viewBox="0 0 24 24"><path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 0 0-.79-.05 6.34 6.34 0 0 0-6.34 6.34 6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.33-6.34V8.69a8.16 8.16 0 0 0 4.77 1.52V6.77a4.85 4.85 0 0 1-1-.08z"/></svg></a>
    </div>
  </div>
  <div class="footer-copy">
    <span>© 2026 Altaltium · Todos los derechos reservados</span>
    <a href="#">Términos y Condiciones</a>
    <a href="#">Política de Privacidad</a>
  </div>
</footer>

<!-- FAB WHATSAPP -->
<a href="https://wa.me/52<%= asesor.telefono %>" target="_blank" rel="noopener" class="fab-wa" aria-label="WhatsApp">
  <svg viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M11.998 0C5.373 0 .001 5.373.001 11.998a11.952 11.952 0 0 0 1.7 6.115L0 24l6.013-1.58A11.948 11.948 0 0 0 11.998 24C18.623 24 24 18.627 24 12.002 24 5.372 18.624 0 11.998 0zm0 21.937a9.947 9.947 0 0 1-5.116-1.409l-.366-.217-3.797.996 1.013-3.696-.24-.38A9.96 9.96 0 0 1 2.041 12c0-5.495 4.463-9.958 9.957-9.958 5.494 0 9.957 4.463 9.957 9.958 0 5.495-4.463 9.937-9.957 9.937z"/></svg>
</a>

<!-- MODAL CONTACTO -->
<div class="modal-ov" id="modal-contacto" role="dialog" aria-modal="true" aria-labelledby="modal-titulo">
  <div class="modal-box">
    <button class="modal-close" onclick="cerrarModal()" aria-label="Cerrar">×</button>
    <div class="modal-title" id="modal-titulo">Contactar a <%= asesor.nombre %></div>
    <div class="modal-sub">Te responderemos en menos de 5 minutos</div>
    <div class="modal-field"><label class="modal-label" for="c-nombre">Nombre *</label><input class="modal-input" id="c-nombre" type="text" placeholder="Tu nombre completo" required></div>
    <div class="modal-field"><label class="modal-label" for="c-tel">Teléfono *</label><input class="modal-input" id="c-tel" type="tel" placeholder="Tu número de teléfono" required></div>
    <div class="modal-field"><label class="modal-label" for="c-email">Email (opcional)</label><input class="modal-input" id="c-email" type="email" placeholder="tu@email.com"></div>
    <div class="modal-field"><label class="modal-label" for="c-msg">Mensaje (opcional)</label><textarea class="modal-input" id="c-msg" rows="3" placeholder="¿En qué te podemos ayudar?" style="resize:vertical"></textarea></div>
    <button class="modal-submit" id="modal-btn" onclick="enviarContacto()">Enviar mensaje</button>
    <div class="modal-msg" id="modal-msg"></div>
  </div>
</div>

<script>
(function(){
  var saved=localStorage.getItem('altaltium-theme')||'dark';
  document.documentElement.setAttribute('data-theme',saved);
  updateToggleUI(saved);
})();
function toggleTheme(){
  var curr=document.documentElement.getAttribute('data-theme')||'dark';
  var next=curr==='dark'?'light':'dark';
  document.documentElement.setAttribute('data-theme',next);
  localStorage.setItem('altaltium-theme',next);
  updateToggleUI(next);
}
function updateToggleUI(theme){
  var moon=document.getElementById('ico-moon');
  var sun=document.getElementById('ico-sun');
  var lbl=document.getElementById('tlbl');
  if(theme==='dark'){moon.style.display='';sun.style.display='none';if(lbl)lbl.textContent='Oscuro';}
  else{moon.style.display='none';sun.style.display='';if(lbl)lbl.textContent='Claro';}
}

var sliderIdx={};
function slideCard(id,dir){
  var inner=document.getElementById('slides-'+id);
  if(!inner)return;
  var slides=inner.children;
  var n=slides.length;
  if(!n)return;
  sliderIdx[id]=((sliderIdx[id]||0)+dir+n)%n;
  inner.style.transform='translateX(-'+(sliderIdx[id]*100)+'%)';
  for(var i=0;i<n;i++){
    var d=document.getElementById('dot-'+id+'-'+i);
    if(d)d.classList.toggle('active',i===sliderIdx[id]);
  }
}

(function(){
  document.querySelectorAll('.cslider').forEach(function(sl,i){
    var sk=document.createElement('div');sk.className='skel-ov';sl.appendChild(sk);
    setTimeout(function(){sk.classList.add('done');},500+i*120);
  });
})();

(function(){
  var cards=document.querySelectorAll('.pcard');
  if(!('IntersectionObserver' in window)){cards.forEach(function(c){c.classList.add('revealed');});return;}
  var obs=new IntersectionObserver(function(entries){
    entries.forEach(function(entry){
      if(entry.isIntersecting){
        var card=entry.target;var idx=parseInt(card.dataset.idx||0);
        setTimeout(function(){card.classList.add('revealed');},idx*60);
        obs.unobserve(card);
      }
    });
  },{threshold:0.08});
  cards.forEach(function(c,i){c.dataset.idx=i;obs.observe(c);});
})();

(function(){
  var el=document.getElementById('result-count');if(!el)return;
  var target=parseInt(el.textContent)||0;if(target<=1)return;
  var current=0;var step=Math.max(1,Math.ceil(target/30));
  var timer=setInterval(function(){
    current=Math.min(current+step,target);
    el.textContent=current+' resultados';
    if(current>=target)clearInterval(timer);
  },35);
})();

function abrirModal(){document.getElementById('modal-contacto').classList.add('open');document.getElementById('c-nombre').focus();}
function cerrarModal(){document.getElementById('modal-contacto').classList.remove('open');}
document.getElementById('modal-contacto').addEventListener('click',function(e){if(e.target===this)cerrarModal();});
document.addEventListener('keydown',function(e){if(e.key==='Escape')cerrarModal();});

async function enviarContacto(){
  var nombre=document.getElementById('c-nombre').value.trim();
  var telefono=document.getElementById('c-tel').value.trim();
  var email=document.getElementById('c-email').value.trim();
  var mensaje=document.getElementById('c-msg').value.trim();
  var msg=document.getElementById('modal-msg');
  var btn=document.getElementById('modal-btn');
  if(!nombre||!telefono){msg.style.color='#ef4444';msg.textContent='Nombre y teléfono son requeridos.';return;}
  btn.disabled=true;btn.textContent='Enviando...';msg.textContent='';
  try{
    var resp=await fetch(window.location.pathname+'/contacto',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({nombre,telefono,email,mensaje,intent:'contact'}),
    });
    var data=await resp.json();
    if(data.ok){msg.style.color='var(--teal-lt)';msg.textContent='¡Gracias! El asesor te contactará pronto.';btn.textContent='Enviado ✓';setTimeout(cerrarModal,2500);}
    else{msg.style.color='#ef4444';msg.textContent=data.error||'Error al enviar.';btn.disabled=false;btn.textContent='Enviar mensaje';}
  }catch(_){msg.style.color='#ef4444';msg.textContent='Error de red. Intenta de nuevo.';btn.disabled=false;btn.textContent='Enviar mensaje';}
}

var debounceTimer;
function debounceSubmit(){clearTimeout(debounceTimer);debounceTimer=setTimeout(function(){document.getElementById('filter-form').submit();},500);}
</script>
</body>
</html>
```

- [ ] **Step 2: Verificar que el archivo existe**

```powershell
ls views/public/microsite.ejs
```
Expected: el archivo aparece listado.

- [ ] **Step 3: Commit**

```bash
git add views/public/microsite.ejs
git commit -m "feat: vista EJS microsite público asesor"
```

---

### Task 4: Rutas públicas

**Files:**
- Modify: `src/routes/public.routes.js`

- [ ] **Step 1: Reemplazar el contenido del archivo con las rutas agregadas**

El archivo completo `src/routes/public.routes.js` debe quedar así:

```javascript
'use strict';

const express  = require('express');
const router   = express.Router();
const propCtrl = require('../controllers/public/propiedad.controller');
const micrositeCtrl = require('../controllers/public/microsite.controller');
const contactoRateLimit = require('../middlewares/contactoRateLimit');

// Página pública de propiedad
router.get('/p/:id', propCtrl.show);
router.post('/p/:id/contacto', express.json(), contactoRateLimit, propCtrl.registrarContacto);

// Micro-sitio público por asesor
router.get('/asesor/:username', micrositeCtrl.show);
router.post('/asesor/:username/contacto', express.json(), contactoRateLimit, micrositeCtrl.registrarContacto);

module.exports = router;
```

- [ ] **Step 2: Verificar carga sin errores**

```bash
node -e "require('./src/routes/public.routes.js'); console.log('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/routes/public.routes.js
git commit -m "feat: rutas GET/POST /asesor/:username para microsite público"
```

---

### Task 5: Link en sidebar del asesor

**Files:**
- Modify: `views/advisor/crm/partials/sidebar.ejs`

- [ ] **Step 1: Agregar el link antes del footer del sidebar**

En `views/advisor/crm/partials/sidebar.ejs`, agregar el siguiente bloque **justo antes** de la línea `<!-- Footer -->` (que corresponde a `<div style="padding: 12px 12px; border-top: 1px solid rgba(255,255,255,0.07);">`):

```html
    <!-- Ver mi perfil público -->
    <% if (typeof currentUser !== 'undefined' && currentUser && currentUser.username) { %>
    <a href="/asesor/<%= currentUser.username %>" target="_blank" rel="noopener"
       style="display:flex; align-items:center; gap:8px; padding:7px 10px; border-radius:8px; margin-bottom:2px; text-decoration:none; transition: background .15s; background: transparent; border: 1px solid transparent;"
       onmouseover="this.style.background='rgba(13,148,136,0.08)'"
       onmouseout="this.style.background='transparent'">
      <span style="width:26px; height:26px; border-radius:7px; display:flex; align-items:center; justify-content:center; flex-shrink:0; background:rgba(255,255,255,0.05);">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#0d9488" stroke-width="2">
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
          <polyline points="15 3 21 3 21 9"/>
          <line x1="10" y1="14" x2="21" y2="3"/>
        </svg>
      </span>
      <span style="font-size:12px; font-weight:500; color:#2dd4bf;">Ver mi perfil público</span>
    </a>
    <% } %>

```

- [ ] **Step 2: Commit**

```bash
git add views/advisor/crm/partials/sidebar.ejs
git commit -m "feat: link Ver mi perfil público en sidebar advisor CRM"
```

---

### Task 6: Verificación integral

- [ ] **Step 1: Iniciar servidor**

```bash
npm start
```
Expected: sin errores, servidor escucha en el puerto configurado.

- [ ] **Step 2: Verificar 404 con username inválido**

Abrir en navegador: `http://localhost:PORT/asesor/usuario-inexistente`

Expected: respuesta 404.

- [ ] **Step 3: Verificar microsite con asesor real**

Obtener un username real de un asesor activo:
```bash
node -e "const p=require('./src/db/pool'); p.query(\"SELECT username FROM users WHERE is_active=true AND role='advisor' LIMIT 1\").then(r=>console.log(r.rows[0])).catch(e=>console.error(e))"
```

Abrir `http://localhost:PORT/asesor/[username-obtenido]`

Expected:
- Chrome con logo Altaltium, slogan teal, toggle luna/sol
- Hero con avatar o iniciales, nombre completo, gerencia
- Rating visible (si tiene ≥5 leads en 90 días) o sección omitida
- Tres botones de contacto (Llamar, WhatsApp, Contactar)
- Badge "Asesor certificado de Altaltium · Real Estate Solutions"
- Barra de filtros con pills de Tipo, Municipio y Ordenar
- Grid de propiedades con skeleton shimmer y scroll reveal
- Footer con línea degradada, redes sociales

- [ ] **Step 4: Verificar toggle de tema**

Hacer click en el toggle. Expected: página cambia entre oscuro y claro. Recargar: el tema persiste.

- [ ] **Step 5: Verificar modal de contacto**

Hacer click en "Contactar". Llenar nombre (`Test`) y teléfono (`5512345678`). Hacer click en "Enviar mensaje".

Expected: respuesta `{ ok: true }` y texto "¡Gracias! El asesor te contactará pronto."

Verificar que se creó el lead:
```bash
node -e "const p=require('./src/db/pool'); p.query(\"SELECT id,nombre,telefono,status FROM crm_leads WHERE telefono='5512345678' ORDER BY id DESC LIMIT 1\").then(r=>console.log(r.rows)).catch(e=>console.error(e))"
```

- [ ] **Step 6: Verificar link en sidebar del asesor**

Iniciar sesión como asesor, navegar a `/advisor/crm`.

Expected: sidebar muestra "Ver mi perfil público" con ícono externo y texto teal. Hacer click: abre el microsite en nueva pestaña.

- [ ] **Step 7: Verificar responsive**

Reducir la ventana a 768px. Expected: layout apilado, infografías en scroll horizontal, grid de 1 columna.

Reducir a 375px. Expected: slogan del navbar oculto, texto de botones "Llamar" y "Contactar" oculto (solo íconos).
