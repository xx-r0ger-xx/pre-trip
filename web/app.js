"use strict";
/* Pre-Trip — web UI. Talks to truckcfg/webapi.py through window.pywebview.api. */

// ---------------------------------------------------------------- icons
const I = {
  wheel: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.2"/><path d="M12 14.2V21M9.9 11.3 3.6 9.5M14.1 11.3l6.3-1.8"/></svg>',
  gauge: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4.5 17a8.5 8.5 0 1 1 15 0"/><path d="m12 13 4-5"/><circle cx="12" cy="13" r="1.4" fill="currentColor"/></svg>',
  twin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="5" width="7" height="14" rx="2"/><rect x="14.5" y="5" width="7" height="14" rx="2"/><path d="M10.5 10h3m-1.5-1.5L13.5 10 12 11.5M13.5 14h-3m1.5-1.5L10.5 14l1.5 1.5"/></svg>',
  layers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/><path d="m3 17.5 9 5 9-5" opacity=".5"/></svg>',
  grid: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7.5" height="7.5" rx="2"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="2"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="2"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/></svg>',
  refresh: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M20 11a8 8 0 0 0-14.3-4.9L4 8M4 4v4h4M4 13a8 8 0 0 0 14.3 4.9L20 16m0 4v-4h-4"/></svg>',
  play: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 4.5v15l12-7.5-12-7.5Z"/></svg>',
  folder: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
  seal: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9.5"/><path d="m7.5 12.5 3 3 6-6.5"/></svg>',
  warn: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3.5 2.5 20h19L12 3.5Z"/><path d="M12 10v4.5M12 17.5v.1"/></svg>',
  crit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5M12 16.5v.1"/></svg>',
  info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.5v.1"/></svg>',
  x: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6 6 18"/></svg>',
  grip: '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="9" cy="6" r="1.6"/><circle cx="15" cy="6" r="1.6"/><circle cx="9" cy="12" r="1.6"/><circle cx="15" cy="12" r="1.6"/><circle cx="9" cy="18" r="1.6"/><circle cx="15" cy="18" r="1.6"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/></svg>',
  sort: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 4v16m0 0-3-3m3 3 3-3M17 20V4m0 0-3 3m3-3 3 3"/></svg>',
  undo: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/></svg>',
  save: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 3h11l3 3v13a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V3Z"/><path d="M8 3v5h7V3M8 21v-7h8v7"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>',
  minus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M5 12h14"/></svg>',
  up: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 14 6-6 6 6"/></svg>',
  down: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 10 6 6 6-6"/></svg>',
  camera: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M4 8h3l2-3h6l2 3h3v11H4V8Z"/><circle cx="12" cy="13" r="3.5"/></svg>',
  note: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 20h4L19 9l-4-4L4 16v4Z"/></svg>',
  arrow: '<svg viewBox="0 0 60 20" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10h50"/><path d="m47 4 7 6-7 6" stroke-dasharray="none"/></svg>',
  bug: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="7" y="7" width="10" height="13" rx="5"/><path d="M9 7a3 3 0 0 1 6 0M3 13h4m10 0h4M4 7l3 2m13-2-3 2M4 19l3-2m13 2-3-2"/></svg>',
  update: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M12 3v12m0 0-4-4m4 4 4-4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/></svg>',
  box: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="m12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z"/><path d="m4 7.5 8 4.5 8-4.5M12 12v9"/></svg>',
  sliders: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M4 6h10m4 0h2M4 12h4m4 0h8M4 18h12m4 0h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/></svg>',
  leaf: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 19c0-8 5-14 15-15-1 10-7 15-15 15Z"/><path d="M5 19 13 11"/></svg>',
  pad: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M7 7h10a5 5 0 0 1 4.8 6.3l-1 3.8a2.5 2.5 0 0 1-4.3 1L14.3 16H9.7l-2.2 2.1a2.5 2.5 0 0 1-4.3-1l-1-3.8A5 5 0 0 1 7 7Z"/><path d="M7.5 10.5v3M6 12h3M15.5 11.5h.1M17.5 13h.1"/></svg>',
};

// ---------------------------------------------------------------- tiny helpers
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const GAME = { ets2: { short: "ETS2", title: "Euro Truck Simulator 2", c: "var(--ets2)" }, ats: { short: "ATS", title: "American Truck Simulator", c: "var(--ats)" } };
const other = g => (g === "ets2" ? "ats" : "ets2");
const GROUP_COL = { fixes: "#c792ea", graphics: "#ffb020", sound: "#6cb4ff", physics: "#3ddc84", ui: "#8e9aa7", interior: "#ff8a5c",
  traffic: "#4dd0e1", cargo: "#d4e157", paint: "#f06292", trailers: "#bcaaa4", trucks: "#ff6b61", maps: "#9575cd" };
const KIND = { update: ["Game updates", "#6cb4ff", I.update], mod: ["Mods", "#ffb020", I.box], loadorder: ["Load order", "#c792ea", I.layers],
  graphics: ["Graphics", "#4dd0e1", I.sliders], controls: ["Controls", "#3ddc84", I.pad], crash: ["Crashes", "#ff5147", I.bug] };
const fmtTime = iso => new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
const fmtDay = iso => new Date(iso).toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
const sizeFmt = b => (b > 1e9 ? (b / 1e9).toFixed(1) + " GB" : b > 1e6 ? (b / 1e6).toFixed(0) + " MB" : Math.max(1, Math.round(b / 1e3)) + " KB");
const same = (a, b) => a && b && a.length === b.length && a.every((x, i) => x === b[i]);
function hue(s) { let h = 0; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) % 360; return h }
const fallbackBg = name => { const h = hue(name); return `linear-gradient(135deg, hsl(${h} 45% 16%), hsl(${(h + 40) % 360} 55% 32%) 60%, hsl(${(h + 70) % 360} 60% 48%))` };
const initials = n => String(n).replace(/[^A-Za-z0-9 ]/g, " ").split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join("").toUpperCase();

// ---------------------------------------------------------------- state
const S = {
  view: "pretrip", game: "ats", dir: null, twinTab: "controls", showSame: false, sel: {}, garageFilter: "all", q: "",
  data: { mods: {}, twin: null, inspect: null, overview: null, logbook: {}, loadouts: {} },
  staged: { ets2: null, ats: null }, ov: { ets2: null, ats: null }, img: {}, selPkg: null, loSel: null, evSel: null,
  owned: ["ets2", "ats"],  // replaced at boot by the games this PC actually has
};
const twinAvailable = () => S.owned.length > 1;
try { const saved = JSON.parse(localStorage.getItem("tcm-ui") || "{}"); Object.assign(S, { view: saved.view || S.view, game: saved.game || S.game }) } catch (e) {}
const persist = () => { try { localStorage.setItem("tcm-ui", JSON.stringify({ view: S.view, game: S.game })) } catch (e) {} };

// ---------------------------------------------------------------- api bridge
const ready = new Promise(res => { if (window.pywebview?.api) res(); else window.addEventListener("pywebviewready", res) });
async function api(name, ...args) {
  await ready;
  try { return await window.pywebview.api[name](...args) }
  catch (e) { toast(String(e?.message || e).replace(/^.*?Error:\s*/, ""), "crit"); throw e }
}

// ---------------------------------------------------------------- toasts, modal, tooltip
function toast(msg, kind = "ok") {
  const col = { ok: "var(--ok)", crit: "var(--crit)", warn: "var(--warn)", info: "var(--info)" }[kind];
  const el = document.createElement("div");
  el.className = "toast"; el.style.setProperty("--tc", col);
  el.innerHTML = `<span class="ic">${{ ok: I.check, crit: I.crit, warn: I.warn, info: I.info }[kind]}</span><div>${esc(msg)}</div>`;
  $("#toasts").append(el);
  setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 400) }, kind === "crit" ? 7000 : 4200);
}
function confirmBox({ title, body, target, list, ok = "Confirm", danger = false }) {
  return new Promise(res => {
    const box = $("#modal-box");
    box.innerHTML = `<h3 class="disp">${esc(title)}</h3><p>${body}</p>
      ${target ? `<div class="target">${I.warn}<span>${target}</span></div>` : ""}
      ${list?.length ? `<div class="list">${list.map(esc).join("<br>")}</div>` : ""}
      <div class="acts"><button class="btn ghost" data-a="no">Cancel</button><button class="btn ${danger ? "danger" : "primary"}" data-a="yes">${esc(ok)}</button></div>`;
    const bg = $("#modal"); bg.classList.add("on");
    const done = v => { bg.classList.remove("on"); document.removeEventListener("keydown", key); res(v) };
    const key = e => { if (e.key === "Escape") done(false); if (e.key === "Enter") done(true) };
    document.addEventListener("keydown", key);
    box.onclick = e => { const a = e.target.closest("[data-a]")?.dataset.a; if (a) done(a === "yes") };
    bg.onclick = e => { if (e.target === bg) done(false) };
    setTimeout(() => $('[data-a="yes"]', box).focus(), 50);
  });
}
const tip = $("#tip");
document.addEventListener("mouseover", e => {
  const t = e.target.closest("[data-tip]"); if (!t) { tip.style.opacity = 0; return }
  tip.innerHTML = t.dataset.tip; tip.style.opacity = 1;
});
document.addEventListener("mousemove", e => {
  if (tip.style.opacity === "0") return;
  const x = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 10), y = Math.min(e.clientY + 16, innerHeight - tip.offsetHeight - 10);
  tip.style.left = x + "px"; tip.style.top = y + "px";
});

// ---------------------------------------------------------------- images
const imgObs = new IntersectionObserver(ents => ents.forEach(en => { if (en.isIntersecting) { imgObs.unobserve(en.target); loadImg(en.target) } }), { rootMargin: "200px" });
async function loadImg(el) {
  const { game, pkg } = el.dataset, k = game + "|" + pkg;
  if (!(k in S.img)) S.img[k] = await api("mod_image", game, pkg).catch(() => "");
  if (S.img[k]) { el.style.backgroundImage = `url("${S.img[k]}")`; el.querySelector(".init")?.remove(); if (el.classList.contains("thumb")) el.textContent = "" }
}
function hookImages(root) { $$("[data-pkg][data-game].lazy", root).forEach(el => { const k = el.dataset.game + "|" + el.dataset.pkg; if (S.img[k]) { el.style.backgroundImage = `url("${S.img[k]}")`; el.querySelector(".init")?.remove(); if (el.classList.contains("thumb")) el.textContent = "" } else imgObs.observe(el) }) }

// ---------------------------------------------------------------- shell
const VIEWS = {
  pretrip: { label: "Inspection", icon: I.gauge, sub: "A walk-around of your setup before you drive." },
  twin: { label: "ATS/ETS2 Sync", icon: I.twin, sub: "Keep ETS2 and ATS feeling the same: controls, graphics, ReShade and mods." },
  studio: { label: "Studio", icon: I.layers, sub: "Drag to reorder. The mod at the top wins when two mods change the same file." },
  garage: { label: "Garage", icon: I.grid, sub: "Your mods, and named loadouts you can switch between in one click." },
  logbook: { label: "Logbook", icon: I.clock, sub: "Everything that happened to your setup, with a restore point at each step." },
};
function initShell() {
  $("#logo").innerHTML = I.wheel;
  for (const [k, v] of Object.entries(VIEWS)) {
    const b = $("#nav-" + k); b.innerHTML = `${v.icon}<span>${v.label}</span>`; b.onclick = () => go(k);
  }
  $("#scrim").onclick = closeDrawer;
  const sb = $("#scenery"); sb.innerHTML = I.leaf; sb.onclick = () => setScenery(!sceneryOn); setScenery(sceneryOn);
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeDrawer();
    if (S.view === "studio" && e.altKey && S.selPkg && (e.key === "ArrowUp" || e.key === "ArrowDown")) { e.preventDefault(); nudge(S.selPkg, e.key === "ArrowUp" ? -1 : 1) }
  });
  setInterval(pollRunning, 4000);
}
async function pollRunning() {
  const r = await api("running").catch(() => null); if (!r) return;
  S.running = r;
  for (const g of S.owned) $("#lamp-" + g).classList.toggle("on", !!r[g]);
}
function usesGame(v) { return v === "studio" || v === "garage" || v === "logbook" }
function topBar() {
  const acts = $("#top-actions"); acts.innerHTML = "";
  if (usesGame(S.view) && S.owned.length === 1) {
    const b = document.createElement("span"); b.className = "gamebadge"; b.style.setProperty("--c", GAME[S.game].c); b.textContent = GAME[S.game].short;
    b.title = GAME[S.game].title; acts.append(b);
  } else if (usesGame(S.view)) {
    const seg = document.createElement("div"); seg.className = "seg";
    seg.innerHTML = ["ets2", "ats"].map(g => `<button class="${S.game === g ? "on" : ""}" data-g="${g}" style="--c:${GAME[g].c}"><span class="dot"></span>${GAME[g].short}</button>`).join("");
    seg.onclick = e => { const g = e.target.closest("[data-g]")?.dataset.g; if (g && g !== S.game) { S.game = g; persist(); render() } };
    acts.append(seg);
  }
  const rf = document.createElement("button"); rf.className = "btn ghost"; rf.innerHTML = `${I.refresh}Refresh`; rf.onclick = () => refresh();
  acts.append(rf);
}
function go(v) { closeDrawer(); S.view = v; persist(); render(); $("#scroll").scrollTop = 0 }
function render() {
  $$(".nav").forEach(b => b.classList.toggle("on", b.dataset.view === S.view));
  $("#title").textContent = VIEWS[S.view].label; $("#subtitle").textContent = VIEWS[S.view].sub;
  topBar();
  const v = $("#view"); v.classList.remove("view"); void v.offsetWidth; v.classList.add("view");
  ({ pretrip: renderPretrip, twin: renderTwin, studio: renderStudio, garage: renderGarage, logbook: renderLogbook })[S.view]();
  renderDock();
}
async function refresh() {
  S.data = { mods: {}, twin: null, inspect: null, overview: null, logbook: {}, loadouts: {} };
  S.ov = { ets2: null, ats: null };
  await Promise.all([api("mods", "ets2", true), api("mods", "ats", true)]).then(([e, a]) => { S.data.mods.ets2 = e; S.data.mods.ats = a }).catch(() => {});
  render(); toast("Reloaded from disk.", "info");
}
const skeleton = (n = 2, h = 220) => `<div style="display:grid;gap:18px;grid-template-columns:repeat(${n},1fr)">${Array.from({ length: n }, () => `<div class="skeleton" style="min-height:${h}px"></div>`).join("")}</div>`;

// ================================================================= PRE-TRIP
function gaugeSVG(frac, col) {
  const r = 46, cx = 60, cy = 60, a0 = 150, sweep = 240;
  const pt = a => [cx + r * Math.cos(a * Math.PI / 180), cy + r * Math.sin(a * Math.PI / 180)];
  const [x0, y0] = pt(a0), [x1, y1] = pt(a0 + sweep), len = 2 * Math.PI * r * sweep / 360;
  const ticks = Array.from({ length: 9 }, (_, i) => { const a = (a0 + sweep * i / 8) * Math.PI / 180; return `<line class="ticks" x1="${cx + 53 * Math.cos(a)}" y1="${cy + 53 * Math.sin(a)}" x2="${cx + 57 * Math.cos(a)}" y2="${cy + 57 * Math.sin(a)}"/>` }).join("");
  return `<svg viewBox="0 0 120 104" style="--gc:${col}">${ticks}
    <path class="track" d="M${x0} ${y0} A${r} ${r} 0 1 1 ${x1} ${y1}"/>
    <path class="val" d="M${x0} ${y0} A${r} ${r} 0 1 1 ${x1} ${y1}" stroke-dasharray="${len}" stroke-dashoffset="${len}" data-to="${len * (1 - Math.max(0, Math.min(1, frac)))}"/>
    <line class="needle" x1="60" y1="60" x2="60" y2="30" style="transform:rotate(-120deg)" data-rot="${-120 + 240 * Math.max(0, Math.min(1, frac))}"/>
    <circle class="hub" cx="60" cy="60" r="5"/></svg>`;
}
const GAUGE_GO = { mods: "Open the Studio", conflicts: "See every file overlap", drift: "Review binding changes", crash: "Open the crash details" };
function gaugeFor(key, g, game) {
  const f = g.max ? g.value / g.max : 0;
  const col = key === "mods" ? (g.value >= g.max ? "var(--ok)" : "var(--warn)")
    : key === "conflicts" ? (g.value ? "var(--info)" : "var(--ok)")
    : key === "drift" ? (g.value ? "var(--warn)" : "var(--ok)")
    : (g.text === "—" || g.value >= 7 ? "var(--ok)" : g.value >= 3 ? "var(--warn)" : "var(--crit)");
  const frac = key === "crash" && g.text === "—" ? 1 : f;
  return `<button class="gauge" data-gauge="${key}" data-g="${game}" data-tip="${GAUGE_GO[key]}">${gaugeSVG(frac, col)}<div class="n num">${esc(g.text)}</div><div class="l">${esc(g.label)}</div></button>`;
}
async function renderPretrip(rescan = false) {
  const v = $("#view");
  if (!S.data.inspect || rescan) {
    if (!S.data.inspect) v.innerHTML = skeleton(2, 440);
    const [ov, ins] = await Promise.all([api("overview"), api("inspect", Object.fromEntries(S.owned.filter(dirty).map(g => [g, S.staged[g]])))]);
    S.data.overview = ov; S.data.inspect = ins;
    if (S.view !== "pretrip") return;
  }
  const ov = S.data.overview, ins = S.data.inspect;
  const sevIcon = { crit: I.crit, warn: I.warn, info: I.info, ok: I.check };
  const sevCol = { crit: "var(--crit)", warn: "var(--warn)", info: "var(--info)", ok: "var(--ok)" };
  const total = Object.values(ins).flatMap(x => x.checks).filter(c => !c.acked && (c.sev === "crit" || c.sev === "warn")).length;
  const checkRow = (g, c, i, gi) => `<div class="check ${c.acked ? "acked" : ""}" style="--sc:${sevCol[c.sev]};animation-delay:${.15 + i * .06 + gi * .1}s">
    <span class="stripe"></span><span class="ic">${c.acked ? I.check : sevIcon[c.sev]}</span>
    <div style="min-width:0"><div class="tt">${esc(c.title)}</div>${c.detail ? `<div class="dd" title="${esc(c.detail)}">${esc(c.detail)}</div>` : ""}</div>
    <div class="acts">${c.acked ? `<button class="btn sm ghost" data-unack="${esc(c.id)}" data-g="${g}">Show again</button>` : `
      ${c.action ? `<button class="btn sm" data-do="${i}" data-g="${g}">${esc(c.action.label)} →</button>` : ""}
      ${c.ack ? `<button class="btn sm ghost" data-ack="${i}" data-g="${g}" data-tip="Hide this until something changes">${I.check}Acknowledge</button>` : ""}`}</div></div>`;
  v.innerHTML = `
    <div class="pt-head">
      <div class="grow"><div class="disp" style="font-size:22px">${total ? `${total} thing${total > 1 ? "s" : ""} to look at before you drive` : (S.owned.length > 1 ? "Both rigs are ready to roll" : "Your rig is ready to roll")}</div></div>
      <button class="btn primary" id="rescan">${I.gauge}Run inspection</button>
    </div>
    <div class="clusters">${S.owned.map((g, gi) => {
      const d = ins[g], o = ov[g];
      return `<section class="panel cluster" style="--c:${GAME[g].c}">
        <div class="glow"></div>
        <div class="cl-head"><span class="gamebadge" style="--c:${GAME[g].c}">${GAME[g].short}</span>
          <div class="grow"><h2 class="disp">${GAME[g].title}</h2><div class="meta">${o.version ? "v" + esc(o.version) : "version unknown until next launch"} · ${esc(o.profile || "no profile")} · ${d.active} of ${d.installed} mods active · ReShade ${d.reshade ? "on" : "off"}</div></div>
          <button class="btn sm" data-launch="${g}" ${o.running ? "disabled" : ""}>${I.play}${o.running ? "Running" : "Launch"}</button></div>
        <div class="gauges">${Object.entries(d.gauges).map(([k, x]) => gaugeFor(k, x, g)).join("")}</div>
        <div class="checks">${(() => {
          const all = d.checks.map((c, i) => [c, i]), open = all.filter(([c]) => !c.acked), done = all.filter(([c]) => c.acked);
          const rows = open.length ? open.map(([c, i]) => checkRow(g, c, i, gi)).join("")
            : `<div class="check" style="--sc:var(--ok)"><span class="stripe"></span><span class="ic">${I.check}</span><div><div class="tt">All clear</div><div class="dd">Nothing needs attention.</div></div><span></span></div>`;
          return rows + (done.length ? `<button class="acked-toggle" data-showacked="${g}">${S.showAcked?.[g] ? "Hide" : "Show"} ${done.length} acknowledged</button>
            ${S.showAcked?.[g] ? done.map(([c, i]) => checkRow(g, c, i, 0)).join("") : ""}` : "");
        })()}</div>
      </section>`;
    }).join("")}</div>
    ${S.owned.length === 1 ? `<div class="panel" style="margin-top:18px;padding:14px 18px;display:flex;gap:12px;align-items:center;color:var(--muted);font-size:13px">
      <span style="color:var(--faint)">${I.twin.replace("<svg", '<svg width="22" height="22"')}</span>
      <div>Only <b style="color:var(--text)">${GAME[S.owned[0]].title}</b> is on this PC. If you add ${GAME[other(S.owned[0])].title} later, <b style="color:var(--text)">ATS/ETS2 Sync</b> appears so you can keep both games' controls, graphics and ReShade in step.</div></div>` : ""}`;
  requestAnimationFrame(() => requestAnimationFrame(() => {
    $$(".gauge .val", v).forEach(p => p.style.strokeDashoffset = p.dataset.to);
    $$(".gauge .needle", v).forEach(n => n.style.transform = `rotate(${n.dataset.rot}deg)`);
  }));
  $("#rescan").onclick = async () => {
    $$(".cluster", v).forEach(c => { const s = document.createElement("div"); s.className = "sweep"; c.append(s) });
    await renderPretrip(true); toast("Inspection complete.", "ok");
  };
  v.onclick = async e => {
    const gz = e.target.closest("[data-gauge]");
    if (gz) return gaugeClick(gz.dataset.g, gz.dataset.gauge);
    const el = e.target.closest("[data-do],[data-ack],[data-unack],[data-showacked]");
    if (el) {
      const g = el.dataset.g || el.dataset.showacked, c = ins[g]?.checks[+(el.dataset.do ?? el.dataset.ack)];
      if (el.dataset.showacked) { S.showAcked = { ...S.showAcked, [g]: !S.showAcked?.[g] }; return renderPretrip() }
      if (el.dataset.unack) { await api("unack", g, el.dataset.unack); return renderPretrip(true) }
      if (el.dataset.ack !== undefined) {
        await api("ack", g, c.id, c.fp); c.acked = true;
        el.closest(".check").animate([{ opacity: 1, transform: "none" }, { opacity: 0, transform: "translateX(24px)" }], { duration: 260, easing: "ease-in" }).onfinish = () => renderPretrip();
        return toast("Acknowledged. It comes back if anything changes.", "info");
      }
      return runAction(g, c.action);
    }
    const l = e.target.closest("[data-launch]"); if (l) { api("launch", l.dataset.launch); toast(`Launching ${GAME[l.dataset.launch].title} through Steam…`, "info") }
  };
}

// gauges always lead somewhere, whatever has been acknowledged
function gaugeClick(g, key) {
  if (key === "mods") return runAction(g, { kind: "view", view: "studio" });
  if (key === "drift") return reviewDrift(g);
  if (key === "crash") return runAction(g, { kind: "view", view: "logbook" });
  const list = S.data.inspect[g].overlaps, box = $("#modal-box"), bg = $("#modal");
  box.innerHTML = `<h3 class="disp">File overlaps in ${GAME[g].short}</h3>
    <p>${list.length ? "When two active mods change the same file, the one higher in the load order wins. That's normal for add-ons and patches. Open a mod to see exactly which files it wins and loses." : "No two active mods change the same file."}</p>
    ${list.length ? `<div class="drift">${list.map((o, i) => `<div class="ovpair"><span class="ov win">▲</span>
      <div style="min-width:0"><div><b>${esc(o.winner_name)}</b> <span style="color:var(--muted)">wins over</span> <b>${esc(o.loser_name)}</b></div>
      <div class="mono" style="font-size:11px;color:var(--faint);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(o.sample[0] || "")}</div></div>
      <span class="mono" style="color:var(--muted)" data-tip="Shared files">${o.count}</span><button class="btn sm" data-ovi="${i}">See files →</button></div>`).join("")}</div>` : ""}
    <div class="acts"><button class="btn ghost" data-a="close">Close</button></div>`;
  bg.classList.add("on");
  const close = () => bg.classList.remove("on");
  bg.onclick = e => { if (e.target === bg) close() };
  box.onclick = e => {
    if (e.target.closest('[data-a="close"]')) return close();
    const b = e.target.closest("[data-ovi]"); if (!b) return;
    close(); runAction(g, { kind: "mod", package: list[+b.dataset.ovi].winner });
  };
}

async function runAction(g, a) {
  if (!a) return;
  S.game = g; persist();
  if (a.kind === "view") return go(a.view);
  if (a.kind === "autosort") { S.pending = { autosort: true }; return go("studio") }
  if (a.kind === "mod") { S.pending = { drawer: a.package }; return go("studio") }
  if (a.kind === "drift") return reviewDrift(g);
}
async function reviewDrift(g) {
  const d = await api("drift", g);
  if (!d.rows.length) { toast("Nothing changed since the last snapshot.", "info"); S.data.inspect = null; return renderPretrip() }
  const box = $("#modal-box"), bg = $("#modal");
  box.innerHTML = `<h3 class="disp">${d.rows.length} binding${d.rows.length > 1 ? "s" : ""} changed in ${GAME[g].short}</h3>
    <p>Compared with the snapshot from <b style="color:var(--text)">${esc(fmtTime(d.snapshot.created))}</b> (${esc(d.snapshot.label)}). If you made these changes, keep them. If the game or an update reset your controls, restore the old ones.</p>
    <div class="drift">${d.rows.map(r => `<div class="dr"><span class="mono">${esc(r.name)}</span><span class="was">${esc(r.before)}</span><span class="arr">→</span><span class="now">${esc(r.after)}</span></div>`).join("")}</div>
    <div class="acts"><button class="btn ghost" data-a="no">Decide later</button><button class="btn danger" data-a="restore">${I.undo}Restore old bindings</button><button class="btn primary" data-a="keep">${I.check}Keep new bindings</button></div>`;
  bg.classList.add("on");
  const choice = await new Promise(res => { box.onclick = e => { const a = e.target.closest("[data-a]")?.dataset.a; if (a) res(a) }; bg.onclick = e => { if (e.target === bg) res("no") } });
  bg.classList.remove("on");
  if (choice === "keep") toast(await api("snapshot", g, "reviewed-kept"), "ok");
  else if (choice === "restore") toast(await api("restore", g, "snapshot", d.snapshot.id), "ok");
  else return;
  S.data.inspect = null; S.data.logbook[g] = null; S.data.twin = null; renderPretrip();
}

// ================================================================= TWIN RIGS
async function renderTwin() {
  const v = $("#view");
  if (!S.data.twin) { v.innerHTML = skeleton(1, 420); S.data.twin = await api("twin"); if (S.view !== "twin") return }
  const t = S.data.twin;
  if (!t.available) { v.innerHTML = `<div class="panel insync"><div class="seal" style="color:var(--faint);background:none">${I.twin}</div><div class="disp" style="font-size:24px">ATS/ETS2 Sync needs both games</div><div style="color:var(--muted)">Install Euro Truck Simulator 2 and American Truck Simulator to compare and sync them.</div></div>`; return }
  if (!S.dir) { const c = t.changed; S.dir = c.ats && c.ets2 && c.ets2 > c.ats ? "ets2" : "ats" }
  const src = S.dir, dst = other(src);
  const counts = {
    controls: t.controls.length, graphics: t.graphics.filter(r => !r.same).length,
    reshade: t.reshade.rows.filter(r => r.ets2 !== r.ats).length + (t.reshade[src].installed !== t.reshade[dst].installed ? 1 : 0),
    mods: t.mods.pairs.length,
  };
  const newer = t.changed.ats > t.changed.ets2 ? "ats" : "ets2";
  v.innerHTML = `
    <div class="twin-head">
      <div class="panel dir">
        <span class="caps">Copy from</span>
        <div class="seg" id="dirseg">${["ats", "ets2"].map(g => `<button class="${src === g ? "on" : ""}" data-d="${g}" style="--c:${GAME[g].c}"><span class="dot"></span>${GAME[g].short} → ${GAME[other(g)].short}</button>`).join("")}</div>
        <span class="arrow" style="color:${GAME[src].c}">${I.arrow}</span>
        <span class="gamebadge" style="--c:${GAME[dst].c}">${GAME[dst].short}</span>
      </div>
      <div class="grow" style="color:var(--muted);font-size:13px">Controls last changed: <b style="color:var(--text)">${GAME.ats.short}</b> ${fmtTime(t.changed.ats)} · <b style="color:var(--text)">${GAME.ets2.short}</b> ${fmtTime(t.changed.ets2)} — ${GAME[newer].short} is newer.</div>
      <div id="twin-action"></div>
    </div>
    <div class="panel" style="padding:4px 16px 16px">
      <div class="tabs">${[["controls", "Controls", I.pad], ["graphics", "Graphics", I.sliders], ["reshade", "ReShade", I.camera], ["mods", "Mods", I.box]].map(([k, l]) =>
        `<button class="tab ${S.twinTab === k ? "on" : ""}" data-tab="${k}">${l}<span class="count ${k !== "mods" && counts[k] ? "hot" : ""}">${counts[k]}</span></button>`).join("")}
        <span class="grow"></span>${S.twinTab === "graphics" || S.twinTab === "reshade" ? `<button class="chip-btn ${S.showSame ? "on" : ""}" id="showsame" style="align-self:center">Show matching</button>` : ""}</div>
      <div id="twin-body"></div>
    </div>`;
  $("#dirseg").onclick = e => { const d = e.target.closest("[data-d]")?.dataset.d; if (d) { S.dir = d; S.sel = {}; renderTwin() } };
  $$(".tab", v).forEach(b => b.onclick = () => { S.twinTab = b.dataset.tab; renderTwin() });
  $("#showsame") && ($("#showsame").onclick = () => { S.showSame = !S.showSame; renderTwin() });
  const body = $("#twin-body"), sel = S.sel[S.twinTab] ||= new Set();
  const inSync = what => `<div class="insync"><div class="seal">${I.seal}</div><div class="disp" style="font-size:24px">${what} match</div><div style="color:var(--muted)">ETS2 and ATS are identical here. Nothing to sync.</div></div>`;
  const grid = (rows, keyOf, labelOf, secOf) => {
    let last = null;
    return `<div class="twin-grid"><div class="h"></div><div class="h">Setting</div><div class="h" style="color:${GAME[src].c}">${GAME[src].short} · source</div><div class="h"></div><div class="h" style="color:${GAME[dst].c}">${GAME[dst].short} · will be overwritten</div>
      ${rows.map(r => {
        const k = keyOf(r), diff = r[src] !== r[dst], s = secOf?.(r);
        const head = s && s !== last ? (last = s, `<div class="sec">${esc(s)}</div>`) : "";
        return head + `<div class="c">${diff ? `<button class="cb ${sel.has(k) ? "on" : ""}" data-k="${esc(k)}" aria-label="Select ${esc(labelOf(r))}">${I.check}</button>` : ""}</div>
          <div class="c ${diff ? "" : "same"}" title="${esc(k)}">${esc(labelOf(r))}</div>
          <div class="c src ${diff ? "" : "same"}">${esc(r[src] ?? "—")}</div>
          <div class="c spine ${diff ? "go" : ""}">${diff ? "→" : "="}</div>
          <div class="c dst ${diff ? "diff" : "same"}">${esc(r[dst] ?? "—")}</div>`;
      }).join("")}</div>`;
  };
  let action = null;
  if (S.twinTab === "controls") {
    body.innerHTML = t.controls.length ? grid(t.controls, r => r.name, r => r.name) : inSync("All mapped controls");
    action = t.controls.length && { n: sel.size || t.controls.length, label: sel.size ? `Copy ${sel.size} selected` : `Sync all ${t.controls.length} bindings`,
      run: () => api("sync_controls", src, dst, sel.size ? [...sel] : null), what: "controls.sii bindings", list: (sel.size ? [...sel] : t.controls.map(r => r.name)) };
  } else if (S.twinTab === "graphics") {
    const rows = t.graphics.filter(r => S.showSame || !r.same);
    body.innerHTML = rows.length ? grid(rows, r => r.key, r => r.label, r => r.section) : inSync("All graphics settings");
    const d = t.graphics.filter(r => !r.same);
    action = d.length && { label: sel.size ? `Copy ${sel.size} selected` : `Sync all ${d.length} settings`,
      run: () => api("sync_graphics", src, dst, sel.size ? [...sel] : null), what: "config.cfg graphics settings (a backup is kept)", list: (sel.size ? [...sel] : d.map(r => r.label)) };
  } else if (S.twinTab === "reshade") {
    const rs = t.reshade, rows = rs.rows.filter(r => S.showSame || r.ets2 !== r.ats);
    const card = g => `<div class="panel rs-card" style="background:var(--glass-lo)"><div class="row"><span class="gamebadge" style="--c:${GAME[g].c}">${GAME[g].short}</span><b class="grow">${rs[g].installed ? "ReShade installed" : "Not installed"}</b>${rs[g].installed ? '<span class="tag ok">active</span>' : '<span class="tag">off</span>'}</div>
      <div style="margin-top:10px">${Object.entries(rs[g].files).map(([f, ok]) => `<div class="file"><span>${esc(f)}</span><span style="color:${ok ? "var(--ok)" : "var(--faint)"}">${ok ? "✓" : "—"}</span></div>`).join("")}</div>
      <div class="fx">${rs[g].effects.map(e => `<span class="tag info">${esc(e)}</span>`).join("") || '<span style="color:var(--faint)">No effects</span>'}</div></div>`;
    body.innerHTML = `<div class="rs-cards" style="margin-top:6px">${card(src)}${card(dst)}</div>` + (rows.length ? grid(rows, r => r.key, r => r.key) : inSync("Preset values"));
    const diffs = counts.reshade;
    action = rs[src].installed && diffs && { label: `Copy ReShade to ${GAME[dst].short}`, run: () => api("sync_reshade", src, dst), what: "dxgi.dll, ReShade.ini, the preset and shaders", list: null };
  } else {
    const m = t.mods;
    body.innerHTML = `<div class="pairs" style="margin-top:8px">${m.pairs.map(p => `<div class="pair">
        <div class="m"><span class="tag ${p[src].active ? "ok" : ""}">${p[src].active ? "on" : "off"}</span><span class="nm">${esc(p[src].name)}</span></div>
        <div class="link ${p.exact ? "" : "approx"}" data-tip="${p.exact ? "Same mod in both games" : "Probably the same mod (similar name)"}">${p.exact ? "=" : "≈"}</div>
        <div class="m"><span class="tag ${p[dst].active ? "ok" : ""}">${p[dst].active ? "on" : "off"}</span><span class="nm">${esc(p[dst].name)}</span></div></div>`).join("")}</div>
      <div class="only">${[src, dst].map(g => `<div><div class="caps" style="color:${GAME[g].c}">Only in ${GAME[g].short}</div><ul>${m.only[g].map(n => `<li>${esc(n)}</li>`).join("") || "<li>Nothing</li>"}</ul></div>`).join("")}</div>
      <p style="color:var(--muted);font-size:12.5px;margin:16px 0 0">Mods are separate downloads for each game, so they're matched by name and shown here, not copied.</p>`;
  }
  body.onclick = e => { const b = e.target.closest(".cb"); if (!b) return; const k = b.dataset.k; sel.has(k) ? sel.delete(k) : sel.add(k); renderTwin() };
  const holder = $("#twin-action");
  if (action) {
    holder.innerHTML = `<button class="btn primary" id="twin-go">${I.twin}${esc(action.label)} → ${GAME[dst].short}</button>`;
    $("#twin-go").onclick = async () => {
      const ok = await confirmBox({ title: `${action.label} to ${GAME[dst].short}?`, ok: `Overwrite ${GAME[dst].short}`,
        body: `Copies from <b>${GAME[src].title}</b> into <b>${GAME[dst].title}</b>.`,
        target: `${GAME[dst].short}'s ${action.what} will be replaced.`, list: action.list });
      if (!ok) return;
      const msg = await action.run();
      toast(msg, "ok"); S.data.twin = null; S.data.inspect = null; S.sel = {}; renderTwin();
    };
  } else holder.innerHTML = `<span class="tag ok" style="padding:8px 10px">${I.check.replace("<svg", '<svg width="12" height="12"')} In sync</span>`;
}

// ================================================================= STUDIO (load order)
async function modsData(g) {
  if (!S.data.mods[g]) S.data.mods[g] = await api("mods", g);
  return S.data.mods[g];
}
const order = g => S.staged[g] || S.data.mods[g]?.order || [];
const dirty = g => !!S.staged[g] && !same(S.staged[g], S.data.mods[g]?.order);
function stage(g, next, flash) {
  S.staged[g] = next; S.flash = flash; S.data.inspect = null;  // Inspection re-checks the unsaved order next time
  clearTimeout(S.ovT); S.ovT = setTimeout(async () => { S.ov[g] = await api("overlaps_for", g, next); if (S.view === "studio" && S.game === g) paintStudio(false) }, 120);
  if (S.view === "studio") paintStudio(true); else if (S.view === "garage") paintGarage(); renderDock();
}
function nudge(pkg, d) {
  const g = S.game, o = [...order(g)], i = o.indexOf(pkg), j = i + d;
  if (i < 0 || j < 0 || j >= o.length) return;
  [o[i], o[j]] = [o[j], o[i]]; stage(g, o, pkg);
}
async function renderStudio() {
  const v = $("#view"); const g = S.game;
  if (!S.data.mods[g]) v.innerHTML = skeleton(2, 480);
  await modsData(g); if (S.view !== "studio" || S.game !== g) return;
  v.innerHTML = `
    <div class="row wrap" style="margin-bottom:16px;gap:12px">
      <label class="search">${I.search}<input id="q" placeholder="Filter mods" value="${esc(S.q)}"></label>
      <div class="studio-legend grow">${S.data.mods[g].groups.map(x => `<span style="--gcol:${GROUP_COL[x.key]}"><i></i>${esc(x.title)}</span>`).join("")}</div>
      <button class="btn" id="autosort">${I.sort}Auto-sort</button>
    </div>
    <div class="studio">
      <section class="panel" id="libcol"><div class="col-head"><h3 class="disp">Library</h3><span class="tag" id="libn"></span><span class="grow"></span><span class="caps">Drag in to activate</span></div><div class="list lib-list" id="lib"></div></section>
      <section class="panel" id="actcol"><div class="col-head"><h3 class="disp">Active load order</h3><span class="tag" id="actn"></span><span class="grow"></span><span class="caps">▲ Top wins</span></div><div class="list" id="act"></div></section>
    </div>`;
  $("#q").oninput = e => { S.q = e.target.value; paintStudio(false) };
  $("#autosort").onclick = async () => {
    const rec = await api("recommend", g, order(g));
    if (same(rec, order(g))) { toast("Already follows the groups and every author's notes.", "info"); return }
    const moved = rec.filter((p, i) => order(g)[i] !== p).length;
    stage(g, rec, "__all"); toast(`Auto-sorted: ${moved} position(s) changed. Review, then save.`, "ok");
  };
  wireDnD(); paintStudio(false);
  const pend = S.pending; S.pending = null;
  if (pend?.autosort) $("#autosort").click();
  if (pend?.drawer) { S.selPkg = pend.drawer; paintStudio(false); openDrawer(g, pend.drawer) }
}
function flip(container, fn) {
  const before = new Map($$("[data-pkg]", container).map(el => [el.dataset.pkg + el.dataset.where, el.getBoundingClientRect()]));
  fn();
  $$("[data-pkg]", container).forEach(el => {
    const b = before.get(el.dataset.pkg + el.dataset.where); if (!b) return;
    const a = el.getBoundingClientRect(), dy = b.top - a.top;
    if (Math.abs(dy) > 1) el.animate([{ transform: `translateY(${dy}px)` }, { transform: "none" }], { duration: 420, easing: "cubic-bezier(.2,.8,.2,1)" });
  });
}
function ovFor(g, pkg) { return (S.ov[g] || S.data.mods[g].overlaps || {})[pkg] || [] }
function itemHTML(g, m, pos) {
  const ov = ovFor(g, m.package), wins = ov.filter(o => o.wins).reduce((a, o) => a + o.count, 0), loses = ov.filter(o => !o.wins).reduce((a, o) => a + o.count, 0);
  const col = GROUP_COL[m.group] || "#8e9aa7";
  const tipOv = ov.map(o => `${o.wins ? "▲ wins over" : "▼ loses to"} <b>${esc(S.data.mods[g].mods[o.other]?.name || o.other)}</b> · ${o.count} files`).join("<br>");
  return `<div class="item ${S.selPkg === m.package ? "sel" : ""} ${S.flash === m.package || S.flash === "__all" ? "moved" : ""}" draggable="true" data-pkg="${esc(m.package)}" data-where="act" style="--gcol:${col}" tabindex="0">
    <span class="grip">${I.grip}</span><span class="pos">${pos}</span>
    <span class="thumb lazy" data-game="${g}" data-pkg="${esc(m.package)}" style="--tg:${fallbackBg(m.name)}">${esc(initials(m.name))}</span>
    <div style="min-width:0"><div class="nm">${esc(m.name)}</div><div class="mt">
      <span class="tag">${m.source === "workshop" ? "Workshop" : m.source === "missing" ? "missing" : "Local"}</span>
      ${m.compat === "outdated" ? '<span class="tag warn">Outdated</span>' : ""}${m.missing ? '<span class="tag crit">Not installed</span>' : ""}
      ${m.version ? `<span>v${esc(m.version)}</span>` : ""}
      ${m.placement ? `<span class="note" data-tip="<b>Author's note</b><br>${esc(m.notes?.[0] || m.placement)}">${I.note.replace("<svg", '<svg width="11" height="11"')}${esc(m.placement.length > 36 ? m.placement.slice(0, 34) + "…" : m.placement)}</span>` : ""}
    </div></div>
    <div class="side">
      ${wins ? `<span class="ov win" data-tip="${esc(tipOv)}">▲ ${wins}</span>` : ""}${loses ? `<span class="ov lose" data-tip="${esc(tipOv)}">▼ ${loses}</span>` : ""}
      <button class="mini" data-act="up" aria-label="Move up">${I.up}</button><button class="mini" data-act="down" aria-label="Move down">${I.down}</button><button class="mini" data-act="off" aria-label="Deactivate">${I.minus}</button>
    </div></div>`;
}
function paintStudio(animate) {
  const g = S.game, d = S.data.mods[g]; if (!d || S.view !== "studio") return;
  const act = $("#act"), lib = $("#lib"), q = S.q.toLowerCase(), o = order(g);
  const match = m => !q || (m.name + " " + (m.author || "")).toLowerCase().includes(q);
  const paint = () => {
    let last = null, pos = 0;
    act.innerHTML = o.map(p => {
      const m = d.mods[p]; pos++; if (!m || !match(m)) return "";
      const head = m.group !== last ? (last = m.group, `<div class="lane-h" style="--gcol:${GROUP_COL[m.group] || "#8e9aa7"}">${esc(m.group_title)}</div>`) : "";
      return head + itemHTML(g, m, pos);
    }).join("") || `<div class="empty"><div class="big disp">No active mods</div>Drag mods in from the library.</div>`;
    const inactive = Object.values(d.mods).filter(m => !m.missing && !o.includes(m.package) && match(m)).sort((a, b) => a.name.localeCompare(b.name));
    lib.innerHTML = inactive.map(m => `<div class="item lib" draggable="true" data-pkg="${esc(m.package)}" data-where="lib">
      <span class="thumb lazy" data-game="${g}" data-pkg="${esc(m.package)}" style="--tg:${fallbackBg(m.name)}">${esc(initials(m.name))}</span>
      <div style="min-width:0"><div class="nm">${esc(m.name)}</div><div class="mt"><span class="tag">${m.source === "workshop" ? "Workshop" : "Local"}</span>${m.compat === "outdated" ? '<span class="tag warn">Outdated</span>' : ""}<span>${esc(m.group_title)}</span></div></div>
      <button class="mini" data-act="on" aria-label="Activate">${I.plus}</button></div>`).join("") || `<div class="empty">Every installed mod is active.</div>`;
    $("#libn").textContent = inactive.length; $("#actn").textContent = o.length;
    hookImages(act); hookImages(lib);
  };
  animate ? flip($("#view"), paint) : paint();
  S.flash = null;
}
function wireDnD() {
  const act = $("#act"), lib = $("#lib"), line = document.createElement("div"); line.className = "drop-line";
  let drag = null;
  const g = () => S.game;
  document.querySelector(".studio").addEventListener("dragstart", e => {
    const it = e.target.closest("[data-pkg]"); if (!it) return;
    drag = { pkg: it.dataset.pkg, from: it.dataset.where }; e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", drag.pkg);
    requestAnimationFrame(() => it.classList.add("dragging"));
  });
  document.querySelector(".studio").addEventListener("dragend", e => { e.target.closest("[data-pkg]")?.classList.remove("dragging"); line.remove(); drag = null });
  const indexAt = y => { const items = $$('.item[data-where="act"]', act).filter(el => el.dataset.pkg !== drag?.pkg); for (const el of items) { const r = el.getBoundingClientRect(); if (y < r.top + r.height / 2) return el } return null };
  act.addEventListener("dragover", e => { if (!drag) return; e.preventDefault(); const before = indexAt(e.clientY); before ? act.insertBefore(line, before.previousElementSibling?.classList.contains("lane-h") ? before.previousElementSibling : before) : act.append(line) });
  act.addEventListener("dragleave", e => { if (!act.contains(e.relatedTarget)) line.remove() });
  act.addEventListener("drop", e => {
    e.preventDefault(); if (!drag) return;
    const before = indexAt(e.clientY), o = order(g()).filter(p => p !== drag.pkg);
    const at = before ? o.indexOf(before.dataset.pkg) : o.length; o.splice(at, 0, drag.pkg);
    line.remove(); stage(g(), o, drag.pkg);
  });
  lib.addEventListener("dragover", e => { if (drag?.from === "act") { e.preventDefault(); $("#libcol").style.boxShadow = "0 0 0 2px var(--crit), 0 0 30px rgba(255,81,71,.25)" } });
  lib.addEventListener("dragleave", () => $("#libcol").style.boxShadow = "");
  lib.addEventListener("drop", e => { e.preventDefault(); $("#libcol").style.boxShadow = ""; if (drag?.from === "act") stage(g(), order(g()).filter(p => p !== drag.pkg)) });
  document.querySelector(".studio").addEventListener("click", e => {
    const it = e.target.closest("[data-pkg]"); if (!it) return;
    const a = e.target.closest("[data-act]")?.dataset.act, p = it.dataset.pkg;
    if (a === "up" || a === "down") { S.selPkg = p; return nudge(p, a === "up" ? -1 : 1) }
    if (a === "off") return stage(g(), order(g()).filter(x => x !== p));
    if (a === "on") return stage(g(), [p, ...order(g())], p);
    S.selPkg = p; $$(".item.sel").forEach(x => x.classList.remove("sel")); it.classList.add("sel"); openDrawer(g(), p);
  });
}

// drawer
function openDrawer(g, pkg) {
  const d = S.data.mods[g], m = d.mods[pkg], ov = ovFor(g, pkg), on = order(g).includes(pkg);
  const dr = $("#drawer");
  dr.innerHTML = `<div class="hero lazy" data-game="${g}" data-pkg="${esc(pkg)}" style="--tg:${fallbackBg(m.name)}"><button class="btn sm close" id="dclose">${I.x}</button><h2 class="disp">${esc(m.name)}</h2></div>
    <div class="body">
      <div class="row wrap"><span class="gamebadge" style="--c:${GAME[g].c}">${GAME[g].short}</span>${on ? `<span class="tag ok">Active · #${order(g).indexOf(pkg) + 1}</span>` : '<span class="tag">Inactive</span>'}
        ${m.compat === "outdated" ? '<span class="tag warn">Not marked for this version</span>' : m.compat === "ok" ? '<span class="tag ok">Compatible</span>' : ""}
        <span class="tag" style="background:color-mix(in srgb, ${GROUP_COL[m.group]} 18%, transparent);color:${GROUP_COL[m.group]}">${esc(m.group_title)}</span></div>
      <dl class="kv"><dt>Author</dt><dd>${esc(m.author || "—")}</dd><dt>Version</dt><dd>${esc(m.version || "—")}</dd><dt>Source</dt><dd>${m.source === "workshop" ? `Steam Workshop · ${esc(m.workshop_id)}` : esc(m.source)}</dd>
        <dt>Size</dt><dd>${m.size ? sizeFmt(m.size) : "—"}</dd><dt>Game files</dt><dd>${m.files ?? "unreadable package"}</dd><dt>Grouped by</dt><dd>${esc(m.why || "")}</dd></dl>
      ${m.notes?.length ? `<div><div class="caps" style="margin-bottom:8px">Author's load-order notes</div>${m.notes.map(n => `<div class="quote">${esc(n)}</div>`).join("")}${m.placement ? `<div style="color:var(--muted);font-size:12px;margin-top:6px">Auto-sort reads this as: <b style="color:var(--amber)">${esc(m.placement)}</b></div>` : ""}</div>` : ""}
      ${ov.length ? `<div><div class="caps" style="margin-bottom:8px">Shares files with</div><div class="ovlist">${ov.map(o => `<div class="ovrow"><span class="ov ${o.wins ? "win" : "lose"}">${o.wins ? "▲ wins" : "▼ loses"}</span><div style="min-width:0"><div style="font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(d.mods[o.other]?.name || o.other)}</div><div class="mono" style="font-size:11px;color:var(--faint);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(o.sample[0] || "")}</div></div><span class="mono" style="color:var(--muted)">${o.count}</span></div>`).join("")}</div></div>` : ""}
      ${m.description ? `<div><div class="caps" style="margin-bottom:8px">Description</div><div class="desc">${esc(m.description)}</div></div>` : ""}
      <div class="row"><button class="btn ${on ? "" : "primary"}" id="dtoggle">${on ? I.minus + "Deactivate" : I.plus + "Activate"}</button><button class="btn ghost" id="dfolder">${I.folder}Mod folder</button></div>
    </div>`;
  dr.classList.add("open"); dr.setAttribute("aria-hidden", "false"); $("#scrim").classList.add("on");
  hookImages(dr);
  $("#dclose").onclick = closeDrawer;
  $("#dfolder").onclick = () => api("open_folder", g, "mods");
  $("#dtoggle").onclick = () => { stage(g, on ? order(g).filter(x => x !== pkg) : [pkg, ...order(g)], pkg); openDrawer(g, pkg) };
}
function closeDrawer() { $("#drawer").classList.remove("open"); $("#drawer").setAttribute("aria-hidden", "true"); $("#scrim").classList.remove("on") }

// dock: unsaved load order
function renderDock() {
  const dock = $("#dock"), g = S.owned.find(dirty);
  if (!g) { dock.classList.remove("show"); return }
  const base = S.data.mods[g].order, now = S.staged[g];
  const added = now.filter(p => !base.includes(p)).length, removed = base.filter(p => !now.includes(p)).length, moved = now.filter((p, i) => base.includes(p) && base.indexOf(p) !== i).length;
  dock.innerHTML = `<span class="pulse"></span><span class="gamebadge" style="--c:${GAME[g].c}">${GAME[g].short}</span>
    <div><b>Unsaved load order</b><div style="color:var(--muted);font-size:12px">${[added && `${added} added`, removed && `${removed} removed`, moved && `${moved} moved`].filter(Boolean).join(" · ") || "reordered"}</div></div>
    <button class="btn ghost" id="discard">${I.undo}Discard</button><button class="btn primary" id="save">${I.save}Save to ${GAME[g].short}</button>`;
  dock.classList.add("show");
  $("#discard").onclick = () => { S.staged[g] = null; S.ov[g] = null; S.flash = "__all"; S.data.inspect = null; render() };
  $("#save").onclick = async () => {
    const msg = await api("save_order", g, S.staged[g]);
    toast(msg, "ok"); S.data.mods[g] = null; S.staged[g] = null; S.ov[g] = null; S.data.inspect = null; await modsData(g); render();
  };
}

// ================================================================= GARAGE
async function renderGarage() {
  const v = $("#view"), g = S.game;
  if (!S.data.mods[g]) v.innerHTML = skeleton(3, 260);
  await modsData(g);
  S.data.loadouts[g] = await api("loadouts", g);
  if (S.view !== "garage" || S.game !== g) return;
  v.innerHTML = `<div class="panel loadouts" id="lobar"></div>
    <div class="row wrap" style="margin-bottom:16px;gap:12px"><label class="search">${I.search}<input id="gq" placeholder="Search mods" value="${esc(S.q)}"></label>
      <div class="filters grow" id="gf">${[["all", "All"], ["on", "Active"], ["off", "Inactive"], ["outdated", "Outdated"]].map(([k, l]) => `<button class="chip-btn ${S.garageFilter === k ? "on" : ""}" data-f="${k}">${l}</button>`).join("")}</div></div>
    <div class="gallery" id="gal"></div>`;
  $("#gq").oninput = e => { S.q = e.target.value; paintGarage() };
  $("#gf").onclick = e => { const f = e.target.closest("[data-f]")?.dataset.f; if (f) { S.garageFilter = f; $$("#gf .chip-btn").forEach(b => b.classList.toggle("on", b.dataset.f === f)); paintGarage() } };
  paintLoadouts(); paintGarage();
}
function paintLoadouts() {
  const g = S.game, los = S.data.loadouts[g] || {}, bar = $("#lobar"); if (!bar) return;
  const cur = order(g), selected = S.loSel && los[S.loSel];
  bar.innerHTML = `<span class="caps" style="margin-right:6px">Loadouts</span>
    ${Object.entries(los).map(([n, lo]) => { const match = same(lo.order.map(x => x[0]), cur);
      return `<button class="lo ${S.loSel === n ? "on" : ""}" data-lo="${esc(n)}">${match ? `<span style="color:var(--ok)">●</span>` : ""}${esc(n)}<span class="n">${lo.order.length}</span></button>` }).join("")}
    <span class="lo-input"><input id="loname" placeholder="Save current as…" maxlength="40"><button class="btn sm primary" id="losave">${I.plus}Save</button></span>
    ${selected ? (() => { const want = selected.order.map(x => x[0]), on = want.filter(p => !cur.includes(p)), off = cur.filter(p => !want.includes(p)), name = p => S.data.mods[g].mods[p]?.name || selected.order.find(x => x[0] === p)?.[1] || p;
      return `<div style="flex-basis:100%;display:flex;gap:12px;align-items:center;margin-top:10px;padding-top:12px;border-top:1px solid var(--line)">
        <div class="grow" style="font-size:13px;color:var(--muted)">${on.length || off.length ? `Switching to <b style="color:var(--text)">${esc(S.loSel)}</b> turns on ${on.length ? on.map(p => `<b style="color:var(--ok)">${esc(name(p))}</b>`).join(", ") : "nothing"} and turns off ${off.length ? off.map(p => `<b style="color:var(--crit)">${esc(name(p))}</b>`).join(", ") : "nothing"}${!on.length && !off.length ? "" : ""}.` : `<b style="color:var(--text)">${esc(S.loSel)}</b> has the same mods as now${same(want, cur) ? "" : " in a different order"}.`}</div>
        <button class="btn ghost sm" id="lodel">${I.x}Delete</button><button class="btn primary" id="loapply" ${same(want, cur) ? "disabled" : ""}>${I.play}Apply loadout</button></div>` })() : ""}`;
  bar.onclick = async e => {
    const lo = e.target.closest("[data-lo]")?.dataset.lo; if (lo) { S.loSel = S.loSel === lo ? null : lo; paintLoadouts(); return }
    if (e.target.closest("#losave")) {
      const n = $("#loname").value.trim(); if (!n) { $("#loname").focus(); toast("Give the loadout a name first.", "warn"); return }
      S.data.loadouts[g] = await api("save_loadout", g, n, order(g)); S.loSel = n; paintLoadouts(); toast(`Saved loadout “${n}”.`, "ok");
    }
    if (e.target.closest("#lodel")) { if (await confirmBox({ title: `Delete “${S.loSel}”?`, body: "Only the saved list is deleted. Your mods and profile aren't touched.", ok: "Delete", danger: true })) { S.data.loadouts[g] = await api("delete_loadout", g, S.loSel); S.loSel = null; paintLoadouts() } }
    if (e.target.closest("#loapply")) {
      if (!await confirmBox({ title: `Apply “${S.loSel}” to ${GAME[g].short}?`, body: "Your profile's active mod list is replaced with this loadout.", target: `${GAME[g].short}'s current load order is backed up first and can be restored from the Logbook.`, ok: "Apply loadout" })) return;
      toast(await api("apply_loadout", g, S.loSel), "ok"); S.data.mods[g] = null; S.staged[g] = null; S.data.inspect = null; renderGarage();
    }
  };
  $("#loname").onkeydown = e => { if (e.key === "Enter") $("#losave").click() };
}
function paintGarage() {
  const g = S.game, d = S.data.mods[g], gal = $("#gal"); if (!d || !gal) return;
  const o = order(g), q = S.q.toLowerCase();
  const list = Object.values(d.mods).filter(m => !m.missing)
    .filter(m => S.garageFilter === "all" || (S.garageFilter === "on" ? o.includes(m.package) : S.garageFilter === "off" ? !o.includes(m.package) : m.compat === "outdated"))
    .filter(m => !q || (m.name + " " + (m.author || "")).toLowerCase().includes(q))
    .sort((a, b) => { const ia = o.indexOf(a.package), ib = o.indexOf(b.package); return (ia < 0) - (ib < 0) || (ia - ib) || a.name.localeCompare(b.name) });
  gal.innerHTML = list.map((m, i) => { const pos = o.indexOf(m.package), on = pos >= 0;
    return `<article class="card ${on ? "" : "off"}" style="animation-delay:${Math.min(i, 14) * .035}s">
      <div class="img lazy" data-game="${g}" data-pkg="${esc(m.package)}" style="--tg:${fallbackBg(m.name)}"><span class="init">${esc(initials(m.name))}</span></div>
      ${on ? `<span class="badge-pos num">#${pos + 1}</span>` : ""}<span class="src tag">${m.source === "workshop" ? "Workshop" : "Local"}</span>
      <div class="c"><div class="nm" title="${esc(m.name)}">${esc(m.name)}</div><div class="by">${esc(m.author || "Unknown author")}${m.version ? ` · v${esc(m.version)}` : ""}</div>
        <div class="row"><span class="tag" style="background:color-mix(in srgb, ${GROUP_COL[m.group]} 16%, transparent);color:${GROUP_COL[m.group]}">${esc(m.group_title)}</span>${m.compat === "outdated" ? '<span class="tag warn">Outdated</span>' : ""}<span class="grow"></span>
          <button class="toggle ${on ? "on" : ""}" data-tg="${esc(m.package)}" aria-label="${on ? "Deactivate" : "Activate"} ${esc(m.name)}"></button></div></div></article>` }).join("")
    || `<div class="empty" style="grid-column:1/-1"><div class="big disp">Nothing here</div>No mods match this filter.</div>`;
  hookImages(gal);
  gal.onclick = e => { const t = e.target.closest("[data-tg]"); if (!t) return; const p = t.dataset.tg, cur = order(g); stage(g, cur.includes(p) ? cur.filter(x => x !== p) : [p, ...cur], p); paintLoadouts() };
}

// ================================================================= LOGBOOK
async function renderLogbook() {
  const v = $("#view"), g = S.game;
  if (!S.data.logbook[g]) { v.innerHTML = skeleton(1, 200) + '<div style="height:18px"></div>' + skeleton(2, 360); S.data.logbook[g] = await api("logbook", g); await modsData(g) }
  if (S.view !== "logbook" || S.game !== g) return;
  const d = S.data.logbook[g], evs = d.events;
  const times = evs.map(e => +new Date(e.time)), now = Date.now();
  const t0 = Math.min(...times, now - 864e5), t1 = now + (now - t0) * .03, x = t => ((t - t0) / (t1 - t0) * 100).toFixed(2);
  const lanes = Object.keys(KIND).filter(k => evs.some(e => e.kind === k));
  const ticks = Array.from({ length: 7 }, (_, i) => t0 + (t1 - t0) * i / 6);
  let lastDay = null;
  v.innerHTML = `
    <section class="panel tl-wrap"><div class="tl" id="tl">
      ${lanes.map(k => `<div class="lane" style="--kc:${KIND[k][1]}"><div class="ln"><i></i>${KIND[k][0]}</div><div class="tr">${evs.map((e, i) => e.kind !== k ? "" :
        `<span class="pin ${S.evSel === i ? "on" : ""}" data-ev="${i}" style="left:${x(+new Date(e.time))}%;--kc:${KIND[k][1]};animation-delay:${.02 * i}s" data-tip="<b>${esc(e.title)}</b><br><span style='color:var(--muted)'>${esc(fmtTime(e.time))}</span>${e.detail ? "<br>" + esc(e.detail) : ""}"></span>`).join("")}</div></div>`).join("")}
      <div class="axis"><span></span><div class="tk">${ticks.map(t => `<span style="left:${x(t)}%">${new Date(t).toLocaleString(undefined, t1 - t0 < 5 * 864e5 ? { month: "short", day: "numeric", hour: "numeric" } : { month: "short", day: "numeric" })}</span>`).join("")}</div></div>
      <div class="now" style="left:calc(120px + (100% - 120px) * ${x(now) / 100})"></div>
    </div></section>
    <div class="log-grid">
      <section class="panel events" id="evlist">${evs.map((e, i) => { const day = fmtDay(e.time), head = day !== lastDay ? (lastDay = day, `<div class="day">${esc(day)}</div>`) : "";
        return head + `<div class="ev ${S.evSel === i ? "on" : ""}" id="ev-${i}" style="--kc:${KIND[e.kind][1]}"><span class="ico">${KIND[e.kind][2]}</span>
          <div style="min-width:0"><div class="tt">${esc(e.title)}</div><div class="dd">${esc(e.detail || "")}</div></div>
          <div class="row"><span class="tm">${new Date(e.time).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}</span>${e.restore ? `<button class="btn sm" data-restore="${i}">${I.undo}Restore</button>` : ""}</div></div>` }).join("") || '<div class="empty">No history yet.</div>'}</section>
      <div style="display:grid;gap:18px">
        <section class="panel crash" id="crash"></section>
        <section class="panel finder" id="finder"></section>
        <section class="panel" style="padding:16px 18px;display:flex;gap:12px;align-items:center"><div class="grow"><b>Controls snapshot</b><div style="color:var(--muted);font-size:12.5px">Save a restore point of ${GAME[g].short}'s bindings now.</div></div><button class="btn" id="snap">${I.camera}Take snapshot</button></section>
      </div>
    </div>`;
  paintCrash(g); paintFinder(g);
  $("#tl").onclick = e => { const p = e.target.closest("[data-ev]"); if (!p) return; S.evSel = +p.dataset.ev; $$(".pin.on,.ev.on").forEach(x => x.classList.remove("on")); p.classList.add("on"); const row = $("#ev-" + S.evSel); row.classList.add("on"); row.scrollIntoView({ behavior: "smooth", block: "center" }) };
  $("#evlist").onclick = async e => {
    const b = e.target.closest("[data-restore]"); if (!b) return; const ev = evs[+b.dataset.restore];
    if (!await confirmBox({ title: `Restore ${GAME[g].short} to this point?`, body: `<b>${esc(ev.title)}</b> · ${esc(fmtTime(ev.time))}`, target: `${GAME[g].short}'s current ${ev.kind === "controls" ? "bindings" : ev.kind === "graphics" ? "config.cfg" : "load order"} is backed up first, so this can be undone too.`, ok: "Restore" })) return;
    toast(await api("restore", g, ev.restore.type, ev.restore.id), "ok"); S.data.logbook[g] = null; S.data.mods[g] = null; S.data.inspect = null; S.data.twin = null; renderLogbook();
  };
  $("#snap").onclick = async () => { toast(await api("snapshot", g, "manual"), "ok"); S.data.logbook[g] = null; S.data.inspect = null; renderLogbook() };
}
function paintCrash(g) {
  const c = S.data.logbook[g].crash, el = $("#crash");
  if (!c.present) { el.innerHTML = `<div class="row"><span class="gamebadge" style="--c:var(--ok)">OK</span><div><b>No crash on record</b><div style="color:var(--muted);font-size:12.5px">${GAME[g].short} has no game.crash.txt.</div></div></div>`; return }
  const kindCol = { game: "info", windows: "", steam: "", addon: "warn" };
  el.innerHTML = `<div class="row wrap"><div class="grow"><div class="caps" style="color:${c.acked ? "var(--muted)" : "var(--crit)"}">Last crash${c.acked ? " · reviewed" : ""}</div><div class="big" style="margin-top:6px">${esc(fmtTime(c.time))}</div></div><span class="tag">${esc(c.build)}</span>
      ${c.acked ? `<span class="tag ok">Reviewed</span>` : `<button class="btn sm" id="crash-ack">${I.check}Mark as reviewed</button>`}</div>
    <div style="font-size:13px">${esc(c.summary)}</div>
    <div><div class="caps" style="margin-bottom:6px">Call stack modules</div><div class="stack">${c.modules.map(m => `<span class="tag ${kindCol[m.kind]}" data-tip="${m.kind === "addon" ? "Not part of the game: ReShade, a plugin or an overlay" : m.kind === "game" ? "Ships with the game" : m.kind === "steam" ? "Steam client / overlay" : "Windows system file"}">${esc(m.name)}</span>`).join("")}</div></div>
    ${c.suspects.length ? `<div><div class="caps" style="margin-bottom:6px;color:var(--warn)">Mods named in the error log</div>${c.suspects.map(s => `<div class="quote"><b>${esc(s.name)}</b><div class="mono" style="font-size:11px;color:var(--muted)">${esc(s.lines[0])}</div></div>`).join("")}</div>` : `<div style="color:var(--muted);font-size:12.5px">No mod file is named in game.log's errors. If it keeps crashing, the crash finder below narrows it down.</div>`}
    ${c.log_errors.length ? `<div><div class="caps" style="margin-bottom:6px">Errors in game.log</div><div class="logbox">${c.log_errors.map(l => `<span class="e">${esc(l)}</span>`).join("\n")}</div></div>` : ""}`;
  $("#crash-ack") && ($("#crash-ack").onclick = async () => { await api("ack", g, "crash", c.time); c.acked = true; S.data.inspect = null; paintCrash(g); toast("Crash marked as reviewed. Inspection only flags it again if the game crashes again.", "ok") });
}
function paintFinder(g) {
  const st = S.data.logbook[g].bisect, el = $("#finder"), names = st?.names || {};
  const nm = p => esc(names[p] || S.data.mods[g]?.mods[p]?.name || p);
  if (!st) {
    el.innerHTML = `<div class="row"><span style="color:var(--info)">${I.bug}</span><b class="disp" style="font-size:20px">Crash finder</b></div>
      <div style="color:var(--muted);font-size:13px">Can't tell which mod crashes the game? The finder switches off half your active mods. You launch and drive for a minute, then tell it whether the game crashed. Each round halves the suspects, so ${S.data.mods[g]?.order?.length ? Math.ceil(Math.log2(Math.max(2, S.data.mods[g].order.length))) : "a few"} rounds finds the culprit. Your original order comes back when it finishes.</div>
      <div><button class="btn" id="bstart">${I.play}Start crash finder</button></div>`;
    $("#bstart").onclick = async () => {
      if (!await confirmBox({ title: `Start the crash finder for ${GAME[g].short}?`, body: "Half of your active mods get switched off for the first test.", target: `Close ${GAME[g].short} first. Your load order is backed up and restored when you finish or stop.`, ok: "Start" })) return;
      S.data.logbook[g].bisect = null; await api("bisect_start", g); S.data.logbook[g] = null; S.data.mods[g] = null; renderLogbook();
    };
    return;
  }
  const total = st.original.length, rounds = Math.ceil(Math.log2(Math.max(2, total)));
  if (st.culprit !== undefined && st.culprit !== null && !st.testing.length) {
    el.innerHTML = `<b class="disp" style="font-size:20px">Found it</b><div class="pills"><span class="pill culprit">${nm(st.culprit)}</span></div><div style="color:var(--muted);font-size:13px">Your original load order is back. Disable or update this mod in the Studio.</div>`;
    return;
  }
  const on = new Set(st.testing), clear = new Set(st.cleared);
  el.innerHTML = `<div class="row"><span style="color:var(--info)">${I.bug}</span><b class="disp grow" style="font-size:20px">Crash finder · round ${st.round}</b><span class="tag info">${st.suspects.length} suspects</span></div>
    <div class="rounds">${Array.from({ length: rounds }, (_, i) => `<i class="${i < st.round - 1 ? "done" : ""}"></i>`).join("")}</div>
    <div style="font-size:13px">Launch ${GAME[g].short}, load your save and drive for a minute. Did it crash?</div>
    <div class="pills">${st.original.map(([p]) => `<span class="pill ${on.has(p) ? "on" : clear.has(p) ? "clear" : ""}" data-tip="${on.has(p) ? "On for this test" : clear.has(p) ? "Cleared: not the cause" : "Off for this test"}">${nm(p)}</span>`).join("")}</div>
    <div class="row wrap"><button class="btn danger" data-b="1">${I.bug}It crashed</button><button class="btn" data-b="0" style="border-color:rgba(61,220,132,.4);color:var(--ok)">${I.check}It ran fine</button><span class="grow"></span><button class="btn ghost" data-b="stop">${I.x}Stop & restore</button></div>`;
  el.onclick = async e => {
    const b = e.target.closest("[data-b]")?.dataset.b; if (b === undefined) return;
    if (b === "stop") toast(await api("bisect_stop", g), "ok");
    else { const r = await api("bisect_report", g, b === "1"); if (r.culprit && !r.testing.length) { S.data.logbook[g] = null; await renderLogbook(); S.data.logbook[g].bisect = r; paintFinder(g); toast(`Culprit found: ${nm(r.culprit)}`, "warn"); return } }
    S.data.logbook[g] = null; S.data.mods[g] = null; renderLogbook();
  };
}

// ---------------------------------------------------------------- backdrop: Golden Hour road
// True 1/z perspective: screen y = horizon + span * NEAR / z and every lateral offset shrinks by the same factor,
// so dashes, trees and leaf litter all travel straight down the road toward the driver. Scenery can be switched off
// (rail toggle), which leaves just the road.
const SCENE = {
  sky: ["#1a1220", "#4a2a2c", "#a4502c", "#f0a040"], glow: "rgba(255,200,110,.45)", hills: ["#3a2224", "#2a181c"],
  ground: ["#2a1d14", "#3a2a1c"], verge: "#4a3420", fog: "#c47a44",
  palette: ["#e0541e", "#f0922e", "#f4c242", "#b8301f", "#d8702a"], pine: "#2c4630", trunk: "#3a2618", rim: .55,
};
const hexRGB = h => h.startsWith("rgb") ? h.match(/\d+/g).slice(0, 3).map(Number) : [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
const mixC = (a, b, t) => { const A = hexRGB(a), B = hexRGB(b); return `rgb(${A.map((v, i) => Math.round(v + (B[i] - v) * t)).join(",")})` };
const clamp01 = v => Math.max(0, Math.min(1, v));
function seeded(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296) }
let sceneryOn = true;
try { sceneryOn = localStorage.getItem("tcm-scenery") !== "off" } catch (e) {}

function startRoad() {
  const cv = $("#road"), ctx = cv.getContext("2d"), still = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const NEAR = 12, FAR = 320, PERIOD = 10, DASH = 3.6, SPEED = 26, r = seeded(4242), sc = SCENE;
  let W = 0, H = 0, dist = 0, last = performance.now();
  const size = () => { const d = Math.min(devicePixelRatio || 1, 2); W = cv.clientWidth; H = cv.clientHeight; cv.width = W * d; cv.height = H * d; ctx.setTransform(d, 0, 0, d, 0, 0) };
  size(); addEventListener("resize", size);
  const pick = () => sc.palette[Math.floor(r() * sc.palette.length)];
  const hills = [0, 1].map(l => Array.from({ length: 61 }, (_, i) => .03 + .045 * (l ? .6 : 1) * (Math.sin(i * .5 + l * 2 + r()) * .5 + .5) + r() * .012));
  const trees = [];
  for (const side of [-1, 1]) for (let i = 0; i < 44; i++) {
    const kind = r(), bush = kind < .32;
    trees.push({ z: (FAR / 44) * i + r() * 6, side, bush, pine: !bush && kind > .82, u: bush ? 1.38 + r() * .9 : 1.75 + r() * 2.8,
      h: bush ? .55 + r() * .45 : 2.0 + r() * 1.6, col: pick(),
      blobs: Array.from({ length: bush ? 3 : 6 }, () => bush ? [r() * .7, 0, .16 + r() * .16] : [(r() - .5) * 1.05, (r() - .5) * .7, .42 + r() * .3]) });
  }
  const litter = Array.from({ length: 90 }, () => ({ z: NEAR + r() * FAR, side: r() < .5 ? -1 : 1, u: 1.02 + r() * .32, c: pick() }));
  const leaves = Array.from({ length: 55 }, () => ({ x: r() * 1.2, y: r(), s: 2.5 + r() * 3.5, v: .02 + r() * .05, w: r() * 6, c: pick() }));

  const frame = now => {
    const dt = Math.min(.05, (now - last) / 1000); last = now;
    if (!still) dist += dt * SPEED;
    const hy = H * .42, span = H - hy, cx = 88 + (W - 88) / 2, half = Math.min(W * .30, 640);
    const k = z => NEAR / z, y = z => hy + span * k(z), X = (u, z) => cx + u * half * k(z), fogAt = kk => 1 - clamp01((kk - .03) / .4);
    ctx.clearRect(0, 0, W, H);
    const road = () => {
      ctx.beginPath(); ctx.moveTo(cx - 1, hy); ctx.lineTo(cx + 1, hy); ctx.lineTo(X(1, NEAR), H); ctx.lineTo(X(-1, NEAR), H); ctx.closePath();
    };
    if (sceneryOn) {
      // sky, sun, hills
      const sky = ctx.createLinearGradient(0, 0, 0, hy); sc.sky.forEach((c, i) => sky.addColorStop(i / (sc.sky.length - 1), c));
      ctx.fillStyle = sky; ctx.fillRect(0, 0, W, hy + 1);
      const glow = ctx.createRadialGradient(cx, hy, 0, cx, hy, W * .6); glow.addColorStop(0, sc.glow); glow.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = glow; ctx.fillRect(0, 0, W, hy + 2);
      const sx = cx + W * .18, sy = hy - H * .05, sun = ctx.createRadialGradient(sx, sy, 0, sx, sy, H * .09);
      sun.addColorStop(0, "rgba(255,236,190,.95)"); sun.addColorStop(.4, "rgba(255,200,120,.5)"); sun.addColorStop(1, "rgba(255,180,90,0)");
      ctx.fillStyle = sun; ctx.fillRect(0, 0, W, hy);
      hills.forEach((pts, l) => { ctx.fillStyle = sc.hills[l]; ctx.beginPath(); ctx.moveTo(0, hy); pts.forEach((p, i) => ctx.lineTo(i / (pts.length - 1) * W, hy - p * H * (l ? .75 : 1))); ctx.lineTo(W, hy); ctx.closePath(); ctx.fill() });
      // ground and leafy verges
      const gr = ctx.createLinearGradient(0, hy, 0, H); gr.addColorStop(0, sc.fog); gr.addColorStop(.12, sc.ground[0]); gr.addColorStop(1, sc.ground[1]);
      ctx.fillStyle = gr; ctx.fillRect(0, hy, W, span);
      for (const s of [-1, 1]) { ctx.fillStyle = sc.verge; ctx.beginPath(); ctx.moveTo(cx, hy); ctx.lineTo(X(s * 1.32, NEAR), H); ctx.lineTo(X(s, NEAR), H); ctx.closePath(); ctx.fill() }
    }
    // light grey asphalt, white edges, amber centre dashes
    const as = ctx.createLinearGradient(0, hy, 0, H);
    as.addColorStop(0, sceneryOn ? mixC("#2a2f36", sc.fog, .45) : "rgba(60,66,74,0)"); as.addColorStop(.35, "#3b4148"); as.addColorStop(1, "#5d636b");
    ctx.fillStyle = as; road(); ctx.fill();
    for (const s of [-1, 1]) { ctx.fillStyle = "rgba(235,240,245,.55)"; ctx.beginPath(); ctx.moveTo(cx + s * .4, hy); ctx.lineTo(X(s * .985, NEAR), H); ctx.lineTo(X(s * .945, NEAR), H); ctx.closePath(); ctx.fill() }
    const off = dist % PERIOD;
    for (let z0 = NEAR - off; z0 < FAR; z0 += PERIOD) {
      const a = Math.max(z0, NEAR), b = z0 + DASH; if (b <= NEAR) continue;
      const wa = .022 * half * k(a), wb = .022 * half * k(b);
      ctx.fillStyle = `rgba(255,176,32,${(.85 * clamp01((y(a) - hy) / span * 3)).toFixed(3)})`;
      ctx.beginPath(); ctx.moveTo(cx - wa, y(a)); ctx.lineTo(cx + wa, y(a)); ctx.lineTo(cx + wb, y(b)); ctx.lineTo(cx - wb, y(b)); ctx.closePath(); ctx.fill();
    }
    if (sceneryOn) {
      for (const l of litter) {
        const z = ((l.z - dist) % FAR + FAR) % FAR + NEAR * .9, kk = k(z), s = Math.max(.6, 3.4 * kk);
        ctx.fillStyle = mixC(l.c, sc.fog, fogAt(kk) * .9); ctx.fillRect(X(l.side * l.u, z) - s / 2, y(z) - s / 3, s, s * .6);
      }
      const list = trees.map(t => ({ t, z: ((t.z - dist) % FAR + FAR) % FAR + NEAR * .95 })).sort((p, q) => q.z - p.z);
      for (const { t, z } of list) {
        const kk = k(z), bx = X(t.side * t.u, z), by = y(z), s = half * kk;
        if (bx < -s * 2 || bx > W + s * 2) continue;
        const shade = fogAt(kk) * .88, C = c => mixC(c, sc.fog, shade), th = t.h * s;
        if (t.bush) {
          ctx.fillStyle = C(mixC(t.col, "#1a1208", .3));
          for (const [dx, , rr] of t.blobs) { const R = rr * s; ctx.beginPath(); ctx.arc(bx + t.side * dx * s, by - R * .7, R, 0, Math.PI * 2); ctx.fill() }
          continue;
        }
        ctx.fillStyle = C(sc.trunk); ctx.fillRect(bx - .05 * s, by - th * .3, .1 * s, th * .3);
        if (t.pine) {
          ctx.fillStyle = C(sc.pine);
          for (let i = 0; i < 3; i++) { const w = (.62 - i * .14) * s, top = by - th * (.3 + i * .22) - th * .34; ctx.beginPath(); ctx.moveTo(bx, top); ctx.lineTo(bx + w, top + th * .42); ctx.lineTo(bx - w, top + th * .42); ctx.closePath(); ctx.fill() }
          continue;
        }
        const cy = by - th * .62;
        ctx.fillStyle = C(t.col);
        for (const [dx, dy, rr] of t.blobs) { ctx.beginPath(); ctx.arc(bx + dx * s, cy + dy * s, rr * s, 0, Math.PI * 2); ctx.fill() }
        ctx.globalAlpha = sc.rim * (1 - shade); ctx.fillStyle = C("#ffd28a");
        for (const [dx, dy, rr] of t.blobs.slice(0, 2)) { ctx.beginPath(); ctx.arc(bx + dx * s - rr * s * .15, cy + dy * s - rr * s * .25, rr * s * .55, 0, Math.PI * 2); ctx.fill() }
        ctx.globalAlpha = 1;
      }
      // falling leaves
      for (const l of leaves) {
        if (!still) { l.y += l.v * dt * 1.4; l.x -= l.v * dt * .6; l.w += dt * 3; if (l.y > 1.05) { l.y = -.05; l.x = Math.random() * 1.2 } }
        ctx.save(); ctx.translate((l.x + Math.sin(l.w) * .01) * W, l.y * H); ctx.rotate(l.w);
        ctx.fillStyle = l.c; ctx.globalAlpha = .75; ctx.fillRect(-l.s, -l.s / 2, l.s * 2, l.s); ctx.restore();
      }
      // vignette and a darker band behind the page header keep text readable
      const v = ctx.createRadialGradient(cx, H * .55, Math.min(W, H) * .35, cx, H * .55, Math.max(W, H) * .8);
      v.addColorStop(0, "rgba(0,0,0,0)"); v.addColorStop(1, "rgba(0,0,0,.45)"); ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
      const top = ctx.createLinearGradient(0, 0, 0, H * .3); top.addColorStop(0, "rgba(6,8,12,.55)"); top.addColorStop(1, "rgba(6,8,12,0)");
      ctx.fillStyle = top; ctx.fillRect(0, 0, W, H * .3);
    }
  };
  if (still) { frame(performance.now()); addEventListener("resize", () => frame(performance.now())); S.redrawRoad = () => frame(performance.now()); return }
  let lastDraw = 0;
  const loop = now => { if (!document.hidden && now - lastDraw > 28) { lastDraw = now; frame(now) } else last = now; requestAnimationFrame(loop) };
  requestAnimationFrame(loop);
}
function setScenery(on) {
  sceneryOn = on;
  try { localStorage.setItem("tcm-scenery", on ? "on" : "off") } catch (e) {}
  const b = $("#scenery"); if (b) { b.classList.toggle("on", on); b.setAttribute("aria-pressed", String(on)); b.dataset.tip = on ? "Scenery on · click for a plain road" : "Scenery off · click for fall scenery" }
  S.redrawRoad?.();
}

// ---------------------------------------------------------------- boot
(async () => {
  startRoad();
  initShell();
  const games = await api("games");
  S.owned = ["ets2", "ats"].filter(g => games[g].owned);
  if (!S.owned.length) {
    $(".main").innerHTML = `<div class="empty" style="margin:auto;max-width:520px"><div class="seal" style="color:var(--amber)">${I.wheel}</div>
      <div class="big disp" style="font-size:30px">No truck sims found</div>
      <div>Pre-Trip looks for Euro Truck Simulator 2 or American Truck Simulator in your Steam libraries and a profile in Documents. Install one, launch it once, then reopen this app.</div></div>`;
    $$(".nav, .lamp").forEach(el => el.hidden = true); return;
  }
  if (!S.owned.includes(S.game)) S.game = S.owned[0];
  for (const g of ["ets2", "ats"]) $("#lamp-" + g).hidden = !S.owned.includes(g);
  $("#nav-twin").hidden = !twinAvailable();
  if (S.view === "twin" && !twinAvailable()) S.view = "pretrip";
  render();
})();
