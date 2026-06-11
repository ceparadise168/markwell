/* Markwell GUI — vanilla front-end. No framework, no build step. */

"use strict";

// Mark JS as live so the fail-open reveal CSS (html.js .reveal:not(.in)) only
// ever hides content while this script is running to reveal it again.
document.documentElement.classList.add("js");

const TOKEN = document.querySelector('meta[name="markwell-token"]').content;
const view = document.getElementById("view");
const toastEl = document.getElementById("toast");

/* Highlight/note/title text is verbatim, untrusted book content (see SECURITY.md):
   always escape before putting it in innerHTML. */
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

async function api(path, { method = "GET", body } = {}) {
  const opts = { method, headers: { "X-Markwell-Token": TOKEN } };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch (_) { /* no body */ }
  if (!res.ok) throw new Error((data && data.error) || res.statusText);
  return data;
}

let toastTimer;
function toast(msg) {
  toastEl.textContent = msg;
  toastEl.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toastEl.hidden = true; }, 2600);
}

/* ---------- motion preference (used everywhere animation is JS-driven) ----------
   The CSS @media (prefers-reduced-motion) block kills CSS transitions/animations,
   but it can NOT stop element.animate() or JS-set style.opacity / smooth scroll.
   So every JS-driven motion path consults this guard directly. */
const prefersReducedMotion = () =>
  !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);

/* ---------- day / night theme ----------
   Three states: no stored choice → OS media query governs; stored "dark"/"light"
   → [data-theme] override wins (see the source-order note in style.css).
   FOUC tradeoff (accepted, spec §F): app.js is deferred, so a user whose stored
   choice differs from their OS sees one frame of the OS theme before initTheme()
   runs. Fixing it would need a blocking inline head script — forbidden by the CSP
   (script-src 'self') — or a new theme-init.js allowlisted in the server, which is
   out of scope. The common case (no choice, or choice == OS) paints correctly. */
const THEME_KEY = "markwell-theme";

function storedTheme() {                 // -> "light" | "dark" | null
  try { return localStorage.getItem(THEME_KEY); } catch (_) { return null; }
}
function systemPrefersDark() {
  return !!(window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches);
}
function effectiveTheme() {               // what the user is actually seeing
  return storedTheme() || (systemPrefersDark() ? "dark" : "light");
}
function applyTheme(theme) {              // theme: "light" | "dark" | null (=system)
  const root = document.documentElement;
  if (theme === "light" || theme === "dark") root.setAttribute("data-theme", theme);
  else root.removeAttribute("data-theme");   // null => let the media query govern
  // Drive the toggle's icon off the *effective* theme so the correct (destination)
  // icon shows even when data-theme is unset (the system-default case).
  root.classList.toggle("is-dark", effectiveTheme() === "dark");
}
function toggleTheme() {
  const next = effectiveTheme() === "dark" ? "light" : "dark";
  try { localStorage.setItem(THEME_KEY, next); } catch (_) { /* private mode: session-only */ }
  applyTheme(next);
}
function initTheme() {
  applyTheme(storedTheme());             // null on first run -> system default, no flash
  const btn = document.getElementById("theme-toggle");
  if (btn) btn.onclick = toggleTheme;
}

/* ---------- reveal on scroll (one shared observer; fail-open with 3 safety nets) ----------
   Contract: an element is hidden ONLY when html.js + .reveal + :not(.in) all hold.
   Callers add .reveal to markup AND immediately pass those nodes here, so a partial
   render can never leave already-painted content stuck invisible. */
let _io = null;
function revealAll(nodes) {
  const list = Array.from(nodes || []);
  if (!list.length) return;
  // reduced motion or no IntersectionObserver -> reveal immediately, no animation
  if (prefersReducedMotion() || !("IntersectionObserver" in window)) {
    list.forEach((n) => n.classList.add("reveal", "in"));
    return;
  }
  list.forEach((n) => n.classList.add("reveal"));
  if (!_io) {
    _io = new IntersectionObserver((ents) => {
      ents.forEach((en) => {
        if (en.isIntersecting) { en.target.classList.add("in"); _io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -6% 0px" });
  }
  list.forEach((n, i) => {
    n.style.transitionDelay = (Math.min(i, 8) * 55) + "ms";
    _io.observe(n);
  });
  // net 1: anything already on screen reveals next frame
  requestAnimationFrame(() => list.forEach((n) => {
    if (n.getBoundingClientRect().top < innerHeight * 0.96) { n.classList.add("in"); _io.unobserve(n); }
  }));
  // net 2: nothing ever stays hidden, even if the observer never fires
  setTimeout(() => list.forEach((n) => {
    if (!n.classList.contains("in")) { n.classList.add("in"); _io.unobserve(n); }
  }), 1600);
}

/* ---------- reading progress bar + scroll-to-top FAB ----------
   One passive scroll listener, attached ONCE at startup. Each view opts into the
   behaviours it wants via setScrollContext(); route() resets them to off so the
   bar/FAB never linger on a view that didn't ask for them. The reading bar lives
   at #read-progress (NOT #progress — that id belongs to the Back-up export box). */
const scrollFx = { progressOn: false, fabOn: false };

function setScrollContext({ progress = false, fab = false } = {}) {
  scrollFx.progressOn = progress;
  scrollFx.fabOn = fab;
  const pbar = document.getElementById("read-progress");
  if (pbar) {
    pbar.classList.toggle("show", progress);
    if (!progress) pbar.style.width = "0";
  }
  const fabEl = document.getElementById("to-top");
  if (fabEl) fabEl.classList.remove("show");   // re-evaluated on the sync below / next scroll
  updateScrollFx();                             // sync immediately for an already-scrolled view
}
function updateScrollFx() {
  const st = window.scrollY || document.documentElement.scrollTop;
  if (scrollFx.progressOn) {
    const h = document.documentElement.scrollHeight - window.innerHeight;
    const pbar = document.getElementById("read-progress");
    if (pbar) pbar.style.width = h > 0 ? (100 * st / h) + "%" : "0";
  }
  const fab = document.getElementById("to-top");
  if (fab) fab.classList.toggle("show", scrollFx.fabOn && st > 620);
}
function initScrollToTop() {
  const fab = document.getElementById("to-top");
  if (fab) fab.onclick = () =>
    window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? "auto" : "smooth" });
}
// Exactly one scroll listener for the whole app (attached at module load, never
// per-route, so it can't leak). It reads scrollFx flags set by setScrollContext.
window.addEventListener("scroll", updateScrollFx, { passive: true });

async function openFolder(dir) {
  try {
    const d = await api("/api/open", { method: "POST", body: { dir } });
    toast(d && d.ok ? "Opened your folder."
      : "Couldn't open the folder — you can find it in History.");
  } catch (_) {
    toast("Couldn't open the folder — you can find it in History.");
  }
}

const ICON = {
  check: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M5 13l4 4L19 7"/></svg>',
  copy: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>',
  folder: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
  book: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM19 17H6"/></svg>',
  search: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>',
  back: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M15 18l-6-6 6-6"/></svg>',
  down: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 4v12m0 0 5-5m-5 5-5-5M5 18v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1"/></svg>',
  refresh: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M20 11a8 8 0 1 0-.5 4M20 5v5h-5"/></svg>',
  clock: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/></svg>',
};

let heartbeatTimer;

async function sendHeartbeat() {
  try { await api("/api/heartbeat", { method: "POST" }); }
  catch (_) { /* server may already be shutting down */ }
}

async function quitApp() {
  const btn = document.getElementById("quit-app");
  if (btn) btn.disabled = true;
  clearInterval(heartbeatTimer);
  try {
    await api("/api/quit", { method: "POST" });
    toast("Markwell is quitting.");
    view.innerHTML = `<div class="wrap"><div class="empty">
      <h2>Markwell has quit</h2>
      <p>You can close this browser tab.</p>
    </div></div>`;
  } catch (_) {
    if (btn) btn.disabled = false;
    heartbeatTimer = setInterval(sendHeartbeat, 15000);
    toast("Could not quit Markwell from here.");
  }
}

/* ---------- shared state ---------- */
const state = {
  status: null,
  source: "latest",   // 'latest' | 'sample' | a snapshot filename
  lib: null,          // cached books document for `source`
  flat: null,         // flat highlight index for `lib` (hero + search); rebuilt with lib
  q: "",
  fmt: null,          // user-chosen export format; survives status refreshes
  jumpTo: null,       // {bookIdx, hlIdx} hand-off: hero/search → renderBook scrolls+flashes
};

let pollGen = 0;      // bumped on navigation to retire stale export-poll loops
let srPhase = "";     // last phase announced, so the live region doesn't repeat
let srSearchTimer;    // debounce for the search live-region announcement

function currentFmt() {
  return state.fmt || (state.status && state.status.format) || "all";
}

/* Which of Markwell's four export languages matches the reader, sent with every
   export so the files' labels match the screen. Temporary inline derivation —
   Task 4 centralizes locale state and replaces this helper. */
function exportLang() {
  let raw = null;
  try { raw = localStorage.getItem("markwell-locale"); } catch (_) { /* private mode */ }
  raw = raw || navigator.language || "en";
  if (/^zh/i.test(raw)) return "zh-TW";
  if (/^ja/i.test(raw)) return "ja";
  if (/^ko/i.test(raw)) return "ko";
  return "en";
}

/* Which library source a view should load: an explicit 'sample' stays sample;
   otherwise the current source if one exists, else the newest ('latest'). Shared
   by renderLibrary and renderBook so the two can never resolve to different
   sources (both call loadStatus() first, so state.status is populated). */
function resolveSource() {
  return state.source === "sample" ? "sample"
    : (state.status.has_library ? state.source : "latest");
}

/* Switch the active library source: drop the cached doc (forces loadLibrary to
   refetch AND rebuild state.flat) and clear any search. Every "open this source"
   control goes through here so the reset stays in one place. */
function switchSource(src) {
  state.source = src;
  state.lib = null;
  state.q = "";
}

function announceSearch(text) {
  clearTimeout(srSearchTimer);
  srSearchTimer = setTimeout(() => {
    const el = document.getElementById("search-sr");
    if (el) el.textContent = text;
  }, 700);
}

async function loadStatus() {
  state.status = await api("/api/status");
  const v = document.getElementById("version");
  if (v && state.status.version) v.textContent = "v" + state.status.version;
}

async function loadLibrary(source) {
  if (!state.lib || state.source !== source) {
    state.source = source;
    state.lib = await api("/api/books?source=" + encodeURIComponent(source));
    // stamp a stable index once so cards can route without an O(n) scan per render
    (state.lib.books || []).forEach((b, i) => { b._idx = i; });
    // flatten every highlight once for the hero + highlight search. Tied to the
    // same cache guard, so any path that sets state.lib = null rebuilds both.
    state.flat = buildFlatIndex(state.lib.books);
  }
  return state.lib;
}

/* Flatten books[].highlights[] into one searchable/sampleable list. Each entry
   keeps the (bookIdx, hlIdx) coordinates the reader uses for its anchor ids, so a
   click in the hero or in search results can jump straight to the source line.
   hlIdx is the index into book.highlights[] as received — the SAME array, in the
   SAME order, that renderBook iterates to build id="hl-{bookIdx}-{hlIdx}". Neither
   path may sort highlights, or the jump breaks. */
function buildFlatIndex(books) {
  const flat = [];
  (books || []).forEach((b) => {
    (b.highlights || []).forEach((h, hlIdx) => {
      const text = h.text || "", note = h.note || "";
      flat.push({
        text,
        note,
        date: h.date || "",
        bookIdx: b._idx,
        hlIdx,
        bookTitle: b.title || "",
        chapterIndex: h.chapter_index,
        // lowercased text+note haystack, precomputed once so search doesn't
        // re-lowercase the whole corpus on every keystroke (see highlightMatches)
        hay: (text + " " + note).toLowerCase(),
      });
    });
  });
  return flat;
}

/* Hand-off used by the hero book-link and every search result. renderBook
   (book view) reads state.jumpTo, scrolls the matching anchor into view + flashes
   it, then clears it. If the book/anchor is gone it degrades to "open at top". */
function jumpToHighlight(bookIdx, hlIdx) {
  state.jumpTo = { bookIdx, hlIdx };
  location.hash = "#/book/" + bookIdx;
}

/* ---------- router ---------- */
const routes = {
  backup: renderBackup,
  library: renderLibrary,
  book: renderBook,
  history: renderHistory,
};

function parseHash() {
  const raw = location.hash.replace(/^#\/?/, "");
  const [name, arg] = raw.split("/");
  return [name || "backup", arg];
}

function setNav(name) {
  document.querySelectorAll(".nav a").forEach((a) => {
    a.setAttribute("aria-current", a.dataset.route === name ? "page" : "false");
  });
}

async function route(focusMain) {
  const [name, arg] = parseHash();
  // Unknown fragments (e.g. the "#view" skip-link target) must NOT re-render the
  // app or retire a running backup's poll loop — just move focus to the content.
  if (!Object.prototype.hasOwnProperty.call(routes, name)) {
    if (focusMain) view.focus();
    return;
  }
  pollGen++;  // a real view change retires the poll loop from the view we're leaving
  // Each view starts at the top with no atmosphere chrome; views opt back in
  // (the book view turns the reading bar + FAB on in a later slice). This runs
  // AFTER pollGen++ so the poll-retirement above is untouched, and is skipped on
  // the unknown-fragment branch above so the skip-link doesn't yank the scroll.
  setScrollContext({ progress: false, fab: false });
  window.scrollTo({ top: 0, behavior: "auto" });
  setNav(name === "book" ? "library" : name);
  const fn = routes[name];
  view.innerHTML = '<div class="wrap"><div class="route-load" role="status" aria-label="Loading…"><span class="spinner" aria-hidden="true"></span></div></div>';
  try {
    await fn(arg);
  } catch (err) {
    console.error(err);
    showError();
  }
  // Move focus to the new view only on user navigation (announces the new
  // content to screen readers); on first load, leave focus at the top so the
  // initial Tab reaches the skip-link → nav naturally.
  if (focusMain) view.focus();
}

window.addEventListener("hashchange", () => route(true));

/* ---------- view: Back up ---------- */
function deviceBanner(s) {
  if (s.device_connected) {
    return `<div class="banner ok"><span class="dot"></span>
      <span><b>Kobo connected.</b> Ready to back up.</span></div>`;
  }
  return `<div class="banner warn"><span class="dot"></span>
    <span><b>No Kobo detected.</b> Plug it in with the USB cable and unlock it.</span>
    <button class="btn banner-act" id="retry">Check again</button></div>`;
}

async function renderBackup() {
  await loadStatus();
  const s = state.status;
  const job = await api("/api/export/status");

  const lastLine = s.has_library
    ? `<p class="hero-last">Your latest saved copy is ready to read in your Library.</p>`
    : "";

  view.innerHTML = `<div class="wrap">
    ${deviceBanner(s)}
    <section class="panel hero">
      <h1>Back up your Kobo</h1>
      <p>Save a copy of everything you've highlighted, and turn it into pages you
         can read and keep — forever, on your own computer.</p>
      <button class="btn btn-primary btn-lg" id="backup-btn">
        ${ICON.down}<span>Back up my Kobo</span></button>
      <p class="hero-note">Markwell only reads your Kobo — it never changes anything
         on it. Nothing ever leaves your computer.</p>
      <p id="sr-status" class="sr-only" role="status" aria-live="polite" aria-atomic="true"></p>
      <div id="progress"></div>
      ${lastLine}
    </section>
  </div>`;

  const retry = document.getElementById("retry");
  if (retry) retry.onclick = () => renderBackup();
  document.getElementById("backup-btn").onclick = startBackup;

  if (job.state === "running") pollExport();
}

async function startBackup() {
  const btn = document.getElementById("backup-btn");
  btn.disabled = true;
  srPhase = "";
  try {
    await api("/api/export", { method: "POST", body: { use_device: true, format: currentFmt(), lang: exportLang() } });
    pollExport();
  } catch (err) {
    btn.disabled = false;
    document.getElementById("progress").innerHTML =
      `<div class="inline-msg err" tabindex="-1">${esc(err.message)}</div>`;
    const sr = document.getElementById("sr-status");
    if (sr) sr.textContent = err.message;
  }
}

const PHASES = [
  ["detecting", "Finding your Kobo"],
  ["snapshotting", "Saving a safe copy"],
  ["reading", "Reading your highlights"],
  ["rendering", "Preparing your files"],
];

async function pollExport(gen) {
  if (gen === undefined) gen = pollGen;
  if (gen !== pollGen) return;        // a newer navigation retired this loop
  let job;
  try { job = await api("/api/export/status"); }
  catch (_) { return; }
  if (gen !== pollGen) return;        // bail if we navigated during the await
  renderProgress(job);
  if (job.state === "running") {
    setTimeout(() => pollExport(gen), 500);
  } else if (job.state === "done") {
    state.lib = null;                 // library changed — drop cache
    try { await loadStatus(); } catch (_) { /* status refresh is best-effort */ }
  }
}

function renderProgress(job) {
  const box = document.getElementById("progress");
  if (!box) return;
  // While a backup is running or finished, the call-to-action, the device
  // banner and the "latest copy" hint step aside so the steps / result stand alone.
  const btn = document.getElementById("backup-btn");
  const note = document.querySelector(".hero-note");
  const last = document.querySelector(".hero-last");
  const banner = document.querySelector(".banner");
  const sr = document.getElementById("sr-status");
  const busy = job.state === "running" || job.state === "done";
  if (btn) { btn.style.display = busy ? "none" : ""; btn.disabled = job.state === "running"; }
  if (note) note.style.display = busy ? "none" : "";
  if (last) last.style.display = busy ? "none" : "";
  if (banner) banner.style.display = busy ? "none" : "";

  if (job.state === "error") {
    box.innerHTML = `<div class="inline-msg err" tabindex="-1">${esc(job.message)}</div>`;
    if (sr) sr.textContent = job.message;
    const el = box.querySelector(".inline-msg.err");
    if (el) el.focus();
    return;
  }

  if (job.state === "done" && job.result) {
    const r = job.result;
    const books = `${r.books} book${r.books === 1 ? "" : "s"}`;
    box.innerHTML = `<div class="result" tabindex="-1">
      <div class="success-mark">${ICON.check}</div>
      <div class="big">${r.highlights.toLocaleString()}</div>
      <div class="big-sub">highlights &amp; notes saved from ${books}</div>
      <div class="btn-row center">
        <a class="btn btn-primary" href="#/library">${ICON.book}<span>Read them</span></a>
        <button class="btn" id="open-out">${ICON.folder}<span>Open the folder</span></button>
      </div></div>`;
    document.getElementById("open-out").onclick = () => openFolder("output");
    if (sr) sr.textContent = `Done. ${r.highlights} highlights and notes saved from ${books}.`;
    const res = box.querySelector(".result");
    if (res) res.focus();
    return;
  }

  // running — announce only on phase change, so the 500ms poll doesn't repeat
  const activeIdx = PHASES.findIndex((p) => p[0] === job.phase);
  if (sr && activeIdx >= 0 && job.phase !== srPhase) {
    srPhase = job.phase;
    sr.textContent = PHASES[activeIdx][1] + "…";
  }
  box.innerHTML = `<ul class="steps" aria-hidden="true">` + PHASES.map((p, i) => {
    const cls = i < activeIdx ? "done" : i === activeIdx ? "active" : "";
    const mark = i < activeIdx ? `<span class="tick">${ICON.check}</span>`
      : i === activeIdx ? `<span class="spinner"></span>`
      : `<span class="tick"></span>`;
    return `<li class="${cls}">${mark}<span>${p[1]}</span></li>`;
  }).join("") + `</ul>`;
}

/* ---------- resurface-a-line hero ----------
   Picks a "punchy, complete" line to revisit; a green highlighter sweep falls on
   the opening clause. Hero quote + reshuffle are <button>s (keyboard-reachable,
   aria-labelled). The fade on reshuffle is gated by prefers-reduced-motion. */
const HERO_MIN = 16, HERO_MAX = 80;

function heroPool(flat) {
  // prefer short, single-line entries; fall open to the whole set so the hero is
  // never empty just because every line is long/multiline.
  const pool = (flat || []).filter((h) => {
    const t = h.text;
    return t && t.indexOf("\n") < 0 && t.length >= HERO_MIN && t.length <= HERO_MAX;
  });
  return pool.length ? pool : (flat || []);
}

let _heroCur = null;   // remember the current pick so reshuffle doesn't repeat it
function pickHero(pool) {
  if (!pool.length) return null;
  let h, guard = 0;
  do { h = pool[Math.floor(Math.random() * pool.length)]; guard++; }
  while (h === _heroCur && pool.length > 1 && guard < 20);
  _heroCur = h;
  return h;
}

/* Green marker on the opening clause. esc() (escapes & < > " ') is applied to BOTH
   the marked head and the remainder before they're joined; the only literal HTML we
   inject is the .marker-em wrapper we control — so untrusted text can never break out. */
function markEmphasis(text) {
  const t = text || "";
  if (t.length <= 46) return `<span class="marker-em">${esc(t)}</span>`;
  let head;
  const cjk = t.match(/^[^。！？；]*[。！？；]/);     // first CJK clause, if any
  if (cjk && cjk[0].length <= 52) head = cjk[0];
  else {
    const en = t.match(/^.{20,52}?[.!?](?=\s|$)/);   // else an en sentence in-window
    head = en ? en[0] : t.slice(0, 42);              // else just the opening words
  }
  return `<span class="marker-em">${esc(head)}</span>${esc(t.slice(head.length))}`;
}

function heroMetaInner(h) {
  return `<button class="hero-book" type="button" data-bookidx="${h.bookIdx}" data-hlidx="${h.hlIdx}"
            aria-label="Open ${esc(h.bookTitle)} at this highlight">${esc(h.bookTitle)}</button>${
    h.date ? `<span class="hero-sep" aria-hidden="true"></span><span class="hero-date">${esc(h.date)}</span>` : ""}`;
}

function heroHTML(h) {
  // The quote text itself is the hero's primary content, so the hero-quote button
  // carries NO aria-label — its accessible name is computed from the quote, and a
  // screen-reader user hears the line (not a generic action label). aria-describedby
  // adds the "press to show another" affordance without masking the quote, and keeps
  // it distinct from the reshuffle control (which owns the "Show another" label).
  return `<div class="hero-line reveal" id="hero">
    <p class="hero-eyebrow">From your highlights · a line to revisit</p>
    <button class="hero-quote" id="hero-quote" type="button" aria-describedby="hero-hint">
      <span class="hero-q">${markEmphasis(h.text)}</span>
    </button>
    <span id="hero-hint" class="sr-only">Press to show another highlight.</span>
    <div class="hero-meta">${heroMetaInner(h)}</div>
    <button class="reshuffle" id="reshuffle" type="button" aria-label="Show another highlight">
      ${ICON.refresh}<span>Another line</span>
    </button>
    <span id="hero-sr" class="sr-only" role="status" aria-live="polite" aria-atomic="true"></span>
  </div>`;
}

function wireHeroBook() {
  const b = document.querySelector("#hero .hero-book");
  if (b) b.onclick = () => jumpToHighlight(Number(b.dataset.bookidx), Number(b.dataset.hlidx));
}
function wireHero() {
  const reshuffle = () => {
    const next = pickHero(heroPool(state.flat));
    if (!next) return;
    const box = document.getElementById("hero");
    const apply = () => {
      const q = document.querySelector("#hero .hero-q");
      const meta = document.querySelector("#hero .hero-meta");
      if (q) q.innerHTML = markEmphasis(next.text);
      if (meta) meta.innerHTML = heroMetaInner(next);
      wireHeroBook();   // re-attach: the book button was just re-rendered
      // announce the new line so AT users perceive the reshuffle (the quote text
      // is the content; the in-place innerHTML swap is otherwise silent)
      const sr = document.getElementById("hero-sr");
      if (sr) sr.textContent = next.text;
    };
    if (prefersReducedMotion() || !box) { apply(); return; }
    box.style.transition = "opacity var(--dur-mid)";
    box.style.opacity = "0";
    // delay is conditional so a reduced-motion pref detected after this click
    // collapses immediately instead of holding the update behind a dead timer
    setTimeout(() => { apply(); box.style.opacity = "1"; }, prefersReducedMotion() ? 0 : 200);
  };
  const q = document.getElementById("hero-quote");
  const r = document.getElementById("reshuffle");
  if (q) q.onclick = reshuffle;
  if (r) r.onclick = reshuffle;
  wireHeroBook();
}

function maybeRenderHero() {
  const slot = document.getElementById("hero-slot");
  if (!slot) return;
  // shown only when there's no active query AND there is at least one highlight
  if (state.q.trim() || !(state.flat && state.flat.length)) { slot.innerHTML = ""; return; }
  const h = pickHero(heroPool(state.flat));
  if (!h) { slot.innerHTML = ""; return; }
  slot.innerHTML = heroHTML(h);
  wireHero();
  revealAll(slot.querySelectorAll(".reveal"));
}

/* ---------- highlight-level search (hybrid) ----------
   AND-match every term across text + note. Term highlighting escapes the FULL
   untrusted string first, then wraps matches in <mark> over the ALREADY-ESCAPED
   string — so a line containing <script> or </mark> is inert (it became
   &lt;script&gt; / &lt;/mark&gt; before any <mark> was inserted). */
const SEARCH_CAP = 200;

function searchTerms(q) {
  return q.toLowerCase().split(/\s+/).filter(Boolean);
}
function highlightMatches(flat, terms) {
  return (flat || []).filter((h) => terms.every((t) => h.hay.includes(t)));
}
/* Find term matches on the RAW (unescaped) text, then emit esc(segment) around
   <mark>esc(match)</mark>. Matching on the raw string avoids corrupting HTML
   entities (the old approach escaped first, so searching "amp" split "&amp;"
   into "&<mark>amp</mark>;"). XSS-safety is preserved: every emitted run of book
   content passes through esc(); the only literal HTML is the <mark> we control. */
function markTerms(text, terms) {
  const src = String(text == null ? "" : text);
  const parts = terms.map((t) => t && t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).filter(Boolean);
  if (!parts.length) return esc(src);
  const re = new RegExp("(" + parts.join("|") + ")", "gi");
  let out = "", last = 0, m;
  while ((m = re.exec(src)) !== null) {
    out += esc(src.slice(last, m.index)) + "<mark>" + esc(m[0]) + "</mark>";
    last = m.index + m[0].length;
    if (m.index === re.lastIndex) re.lastIndex++;   // guard against a zero-width match
  }
  return out + esc(src.slice(last));
}

function renderSearchResults(q) {
  const terms = searchTerms(q);
  const hits = highlightMatches(state.flat || [], terms);
  const results = document.getElementById("results");
  const count = document.getElementById("count");
  if (!results) return;
  results.hidden = false;

  if (!hits.length) {
    results.innerHTML = `<div class="empty results-empty" tabindex="-1">
      <p class="big">No highlights match “${esc(q)}”.</p>
      <p>Try a different word, or clear the search to return to your books.
         Markwell searches the words inside your highlights and notes — not book titles.</p>
    </div>`;
    if (count) count.textContent = "";
    announceSearch(`No highlights match ${q}.`);
    return;
  }

  const shown = hits.slice(0, SEARCH_CAP);
  const rows = shown.map((h) => {
    // surface the note line only when the match was actually in the note, so a
    // searcher who remembers a word from their own annotation can see why this
    // row matched (the empty-state copy promises Markwell searches notes too).
    const noteHit = h.note && terms.some((t) => h.note.toLowerCase().includes(t));
    const note = noteHit
      ? `<div class="rnote"><b>Your note:</b> ${markTerms(h.note, terms)}</div>` : "";
    return `
    <button class="search-result" type="button" data-bookidx="${h.bookIdx}" data-hlidx="${h.hlIdx}"
            aria-label="Open ${esc(h.bookTitle)} at this highlight">
      <div class="rtext">${markTerms(h.text, terms)}</div>${note}
      <div class="rmeta"><span class="rb">${esc(h.bookTitle)}</span>${
        h.date ? `<span class="sep" aria-hidden="true"></span><span>${esc(h.date)}</span>` : ""}</div>
    </button>`;
  }).join("");

  const more = hits.length > SEARCH_CAP
    ? `<p class="results-more">Showing the first ${SEARCH_CAP} of ${hits.length.toLocaleString()} matches — type a more specific word to narrow them.</p>`
    : "";

  results.innerHTML = rows + more;
  if (count) count.textContent =
    `${hits.length.toLocaleString()} highlight${hits.length === 1 ? "" : "s"} match`;
  announceSearch(`${hits.length} highlight${hits.length === 1 ? "" : "s"} match ${q}.`);

  results.querySelectorAll(".search-result").forEach((el) => {
    el.onclick = () => jumpToHighlight(Number(el.dataset.bookidx), Number(el.dataset.hlidx));
  });
}

/* ---------- view: Library ---------- */
async function renderLibrary() {
  await loadStatus();
  const lib = await loadLibrary(resolveSource());

  if (lib.source_kind === "empty") {
    view.innerHTML = `<div class="wrap">${emptyLibrary()}</div>`;
    wireEmptyLibrary();
    return;
  }

  const books = lib.books || [];
  const totalHl = books.reduce((n, b) => n + b.highlights.length, 0);

  view.innerHTML = `<div class="wrap">
    ${lib.source_kind === "sample" ? sampleBanner() : ""}
    <div id="hero-slot"></div>
    <h1 class="page-title">Your library</h1>
    <p class="page-sub">${books.length} book${books.length === 1 ? "" : "s"} ·
       ${totalHl.toLocaleString()} highlights &amp; notes</p>
    <div class="toolbar">
      <div class="search">${ICON.search}
        <input type="search" id="q" placeholder="Search your highlights…"
               aria-label="Search your highlights" value="${esc(state.q)}">
      </div>
      <span class="count-note" id="count"></span>
    </div>
    <span id="search-sr" class="sr-only" role="status" aria-live="polite" aria-atomic="true"></span>
    <div class="grid" id="grid"></div>
    <div class="results" id="results" hidden></div>
  </div>`;

  wireSampleBanner();
  const input = document.getElementById("q");
  input.oninput = () => { state.q = input.value; refreshGrid(); };
  maybeRenderHero();   // fills #hero-slot iff no query and the library has highlights
  refreshGrid();       // branches: no query → book grid; query → highlight results
  if (state.q) { input.focus(); input.setSelectionRange(input.value.length, input.value.length); }
}

/* The hybrid switch. No query → the book grid (the original behaviour). A query →
   hide grid + hero and show highlight-level results. The function name stays
   refreshGrid since it's the #q input handler target; only its job widened. */
function refreshGrid() {
  const q = state.q.trim();
  const grid = document.getElementById("grid");
  const results = document.getElementById("results");
  const heroSlot = document.getElementById("hero-slot");

  if (!q) {
    if (results) { results.hidden = true; results.innerHTML = ""; }
    if (grid) grid.hidden = false;
    renderBookGrid();
    // restore the hero once when the query clears (don't reshuffle on every keystroke)
    if (heroSlot && !heroSlot.children.length) maybeRenderHero();
    setScrollContext({ progress: false, fab: false });   // no long-scroll FAB on the grid
    return;
  }
  if (heroSlot) heroSlot.innerHTML = "";
  if (grid) { grid.hidden = true; grid.innerHTML = ""; }
  renderSearchResults(q);
  // a broad term can list up to SEARCH_CAP rows — offer the scroll-to-top FAB
  // (but not the reading-progress bar, which tracks a book's reading position)
  setScrollContext({ progress: false, fab: true });
}

/* The no-query book grid: every book, most-highlighted first (mirrors the Markdown
   index), then title. Book-level filtering is gone — search is highlight-level now
   (spec §C), so the grid no longer narrows while typing. */
function renderBookGrid() {
  const books = (state.lib && state.lib.books) || [];
  const sorted = books.slice().sort((a, b) =>
    b.highlights.length - a.highlights.length
    || (a.title || "").localeCompare(b.title || ""));
  const grid = document.getElementById("grid");
  if (grid) grid.innerHTML = sorted.map(bookCard).join("");
  const count = document.getElementById("count");
  if (count) count.textContent = "";   // count is meaningful only while searching
  announceSearch("");
  wireCards();
}

function yearSpan(b) {
  const ys = b.highlights.map((h) => (h.date || "").slice(0, 4)).filter(Boolean).sort();
  if (!ys.length) return "";
  return ys[0] === ys[ys.length - 1] ? ys[0] : ys[0] + "–" + ys[ys.length - 1];
}

function bookCard(b) {
  const n = b.highlights.length;
  const span = yearSpan(b);
  return `<button class="book-card" data-idx="${b._idx}">
    <div class="bc-title">${esc(b.title)}</div>
    ${b.author ? `<div class="bc-author">${esc(b.author)}</div>` : ""}
    <div class="bc-meta"><span class="bc-count">${n}</span>
      <span>highlight${n === 1 ? "" : "s"}</span>${span ? `<span>· ${esc(span)}</span>` : ""}</div>
  </button>`;
}

function wireCards() {
  document.querySelectorAll(".book-card").forEach((el) => {
    el.onclick = () => { location.hash = "#/book/" + el.dataset.idx; };
  });
}

/* ---------- view: Book detail ----------
   Each highlight is a <li id="hl-{bookIdx}-{hlIdx}"> where hlIdx is the running
   index across the WHOLE book.highlights array — the exact coordinate the flat
   index (buildFlatIndex) stamps, so a hero/search click can jump straight here.
   Per-highlight copy buttons reveal on hover/focus; the book closes on an
   ornament + a way back. After render we wire copy, reveal, turn the reading bar
   + FAB on, then honour any pending jump (scroll + flash). */
async function renderBook(arg) {
  await loadStatus();
  const lib = await loadLibrary(resolveSource());
  const bookIdx = Number(arg);
  const book = (lib.books || [])[bookIdx];
  if (!book) { location.hash = "#/library"; return; }

  const n = book.highlights.length;
  const span = yearSpan(book);

  // group highlights into <h2> chapter + <ul> sections (valid list semantics)
  let body = "", lastChap = null, open = false;
  book.highlights.forEach((h, hlIdx) => {
    if (h.chapter_index !== lastChap) {
      if (open) body += "</ul>";
      body += `<h2 class="chapter">Chapter ${esc(h.chapter_index)}</h2><ul class="hl-list">`;
      open = true;
      lastChap = h.chapter_index;
    }
    const note = h.note ? `<div class="note"><b>Your note:</b> ${esc(h.note)}</div>` : "";
    const date = h.date ? `<span class="date">${esc(h.date)}</span>` : "";
    body += `<li class="hl reveal" id="hl-${bookIdx}-${hlIdx}">
      <div class="text">${esc(h.text)}</div>${note}
      <div class="hl-foot">
        ${date}
        <button class="copy" type="button" aria-label="Copy this highlight" data-hlidx="${hlIdx}">${ICON.copy}<span>Copy</span></button>
      </div>
    </li>`;
  });
  if (open) body += "</ul>";

  // a warm close: an ornament, a count, and a way back to the shelf
  const endMsg = n === 1
    ? "That's the only highlight from this book."
    : `That's every highlight from this book — ${n} in all.`;
  const endBlock = `<div class="book-end">
    <div class="orn" aria-hidden="true">❊ ❊ ❊</div>
    <p class="be-msg">${endMsg}</p>
    <a class="btn" href="#/library">${ICON.back}<span>Back to your library</span></a>
  </div>`;

  view.innerHTML = `<div class="wrap">
    <a class="back" href="#/library">${ICON.back}<span>All books</span></a>
    <header class="detail-head">
      <h1>${esc(book.title)}</h1>
      ${book.author ? `<div class="by">${esc(book.author)}</div>` : ""}
      <div class="stat">${n} highlight${n === 1 ? "" : "s"} &amp; notes${span ? " · " + esc(span) : ""}</div>
    </header>
    ${body}${endBlock}
  </div>`;

  wireCopyButtons(book);
  revealAll(view.querySelectorAll(".hl.reveal"));
  setScrollContext({ progress: true, fab: true });   // reading bar + FAB on for this view
  consumeJumpTo(bookIdx);                             // scroll + flash if we arrived via a jump
}

/* ---------- per-highlight copy ----------
   Copies "the line, a blank line, then —《title》". Prefers the async Clipboard
   API; falls back to a hidden <textarea> + execCommand; if even that fails, a warm
   toast tells the reader to select + copy by hand (never a silent failure or throw).
   Untrusted text never reaches innerHTML here — the payload is written to the
   clipboard as a plain string; only our own ICON markup is ever set on the button. */
function copyPayload(text, title) {
  return `${text}\n\n—《${title}》`;
}
function fallbackCopy(s) {
  const ta = document.createElement("textarea");
  ta.value = s;
  ta.setAttribute("readonly", "");
  ta.style.position = "fixed";
  ta.style.top = "-1000px";
  ta.style.opacity = "0";
  document.body.appendChild(ta);
  ta.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch (_) { ok = false; }
  document.body.removeChild(ta);
  return ok;
}
function wireCopyButtons(book) {
  const title = book.title || "";
  view.querySelectorAll(".copy").forEach((btn) => {
    btn.onclick = () => {
      const h = book.highlights[Number(btn.dataset.hlidx)];
      if (!h) return;
      const payload = copyPayload(h.text || "", title);
      const done = () => copiedFeedback(btn);
      const fail = () => {
        if (fallbackCopy(payload)) done();
        else toast("Couldn't copy — you can select the text and copy it manually.");
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(payload).then(done).catch(fail);
      } else {
        fail();
      }
    };
  });
}
function copiedFeedback(btn) {
  btn.classList.add("done");
  btn.innerHTML = `${ICON.check}<span>Copied</span>`;   // our own markup only
  toast("Highlight copied.");                            // existing role=status toast announces it
  setTimeout(() => {
    if (btn.isConnected) { btn.classList.remove("done"); btn.innerHTML = `${ICON.copy}<span>Copy</span>`; }
  }, 1800);
}

/* ---------- jump consumption (hero / search → reader anchor) ----------
   One-shot: clear state.jumpTo no matter what, so a later direct navigation to the
   same book opens at the top. Forces the target .reveal element visible BEFORE
   scrolling (so we never scroll to an opacity:0 node), then centres + flashes it.
   Missing book/anchor or a stale jump degrades to "open at top" — never an error. */
function consumeJumpTo(bookIdx) {
  const jt = state.jumpTo;
  state.jumpTo = null;
  if (!jt || jt.bookIdx !== bookIdx) return;
  const target = document.getElementById(`hl-${bookIdx}-${jt.hlIdx}`);
  if (!target) return;
  target.classList.add("in");   // ensure revealed before we scroll to it
  const behavior = prefersReducedMotion() ? "auto" : "smooth";
  // let the just-set innerHTML settle a frame, then scroll + flash
  requestAnimationFrame(() => {
    target.scrollIntoView({ block: "center", behavior });
    flashHighlight(target);
  });
}
function flashHighlight(node) {
  // JS-driven animation bypasses the reduced-motion CSS block, so guard here too
  if (prefersReducedMotion() || typeof node.animate !== "function") return;
  // End on the page background, NOT 'transparent': WebKit interpolates a green rgba
  // toward transparent (= rgba(0,0,0,0)) through premultiplied black, flashing dark
  // mid-fade. The .hl element's resting background already is var(--bg), so this
  // settles invisibly while keeping the fade green throughout.
  node.animate(
    [{ backgroundColor: "var(--marker)" }, { backgroundColor: "var(--bg)" }],
    { duration: 1500, easing: "ease-out" });
}

/* ---------- view: History ----------
   The backend ships data for each saved copy (an ISO `stamp`, a byte size);
   the browser owns all presentation, via Intl in the reader's own locale.
   The stamp is offset-less ISO, which `new Date()` parses as LOCAL time — on
   purpose, since server and browser are the same machine — so never append
   "Z" or otherwise convert it to UTC. */
function fmtStamp(stampIso) {
  const d = new Date(stampIso);
  if (isNaN(d)) return "";
  return new Intl.DateTimeFormat(undefined,
    { dateStyle: "medium", timeStyle: "short" }).format(d);
}

/* Relative age ("2 days ago", "昨天") in the largest sensible unit; anything
   under 90s reads as "now". numeric:"auto" lets locales say yesterday/昨天.
   Round FIRST, then promote when the rounded value reaches the next unit, so
   23.7h is "yesterday" (never "24 hours ago") and 11.7mo is "last year". */
function relAge(stampIso) {
  const then = new Date(stampIso);
  if (isNaN(then) || typeof Intl.RelativeTimeFormat !== "function") return "";
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  const secs = (then - Date.now()) / 1000;   // negative = in the past
  if (Math.abs(secs) < 90) return rtf.format(0, "second");               // "now"
  const mins = Math.round(secs / 60);
  if (Math.abs(mins) < 60) return rtf.format(mins, "minute");
  const hours = Math.round(secs / 3600);
  if (Math.abs(hours) < 24) return rtf.format(hours, "hour");
  const days = Math.round(secs / 86400);
  if (Math.abs(days) < 30) return rtf.format(days, "day");
  const months = Math.round(secs / 2592000);
  if (Math.abs(months) < 12) return rtf.format(months, "month");
  return rtf.format(Math.round(secs / 31536000), "year");
}

async function renderHistory() {
  await loadStatus();
  const s = state.status;
  const data = await api("/api/snapshots");
  const snaps = data.snapshots || [];

  const list = snaps.length
    ? `<ul class="snap-list">${snaps.map(snapRow).join("")}</ul>`
    : `<div class="empty" style="padding:30px 0">
         <p>No saved copies yet. Back up your Kobo to create your first one.</p>
         <div class="btn-row center"><a class="btn btn-primary" href="#/backup">${ICON.down}<span>Back up now</span></a></div>
       </div>`;

  view.innerHTML = `<div class="wrap">
    <h1 class="page-title">History</h1>
    <p class="page-sub">Every saved copy is kept forever and never overwritten, so
       nothing you've highlighted can be lost.</p>

    <section class="panel">
      <p class="eyebrow">Where your files live</p>
      <div class="path-row">
        <span class="path-chip">${esc(s.data_dir)}</span>
        <button class="btn" id="open-data">${ICON.folder}<span>Open folder</span></button>
      </div>
      <details class="advanced">
        <summary>Export options</summary>
        <p class="count-note" style="margin:10px 0 0">Choose which kinds of files to create when you back up.</p>
        <div class="fmt-row" id="fmt" role="group" aria-label="Which files to create">
          ${fmtChip("all", "Both", currentFmt())}
          ${fmtChip("md", "Readable text", currentFmt())}
          ${fmtChip("json", "A data file", currentFmt())}
        </div>
      </details>
    </section>

    <section class="panel">
      <p class="eyebrow">Saved copies (${snaps.length})</p>
      ${list}
    </section>
  </div>`;

  document.getElementById("open-data").onclick = () => openFolder("data");
  wireSnapActions();
  wireFmt();
}

function snapRow(sn) {
  const date = (sn.stamp && fmtStamp(sn.stamp)) || sn.name;  // no stamp -> the filename
  const age = sn.stamp ? relAge(sn.stamp) : "";
  const size = Math.round((sn.size_bytes || 0) / 1024).toLocaleString() + " KB";
  return `<li class="snap ${sn.is_latest ? "latest" : ""}" data-name="${esc(sn.name)}">
    <span class="snap-dot">${ICON.clock}</span>
    <div class="snap-main">
      <div class="snap-date">${esc(date)} ${sn.is_latest ? '<span class="pill">Newest</span>' : ""}</div>
      <div class="snap-sub">${age ? esc(age) + " · " : ""}${esc(size)}</div>
    </div>
    <div class="snap-acts">
      <button class="btn" data-act="view">${ICON.book}<span>Read</span></button>
      <button class="btn" data-act="reexport">${ICON.refresh}<span>Re-create files</span></button>
    </div>
  </li>`;
}

function wireSnapActions() {
  document.querySelectorAll(".snap").forEach((li) => {
    const name = li.dataset.name;
    li.querySelector('[data-act="view"]').onclick = () => {
      switchSource(name);
      location.hash = "#/library";
    };
    li.querySelector('[data-act="reexport"]').onclick = async (e) => {
      const btn = e.currentTarget;
      const orig = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span><span>Working…</span>';
      try {
        await api("/api/export", { method: "POST", body: { use_device: false, source: name, format: currentFmt(), lang: exportLang() } });
        const job = await waitForExport();
        if (job.state === "done") {
          btn.innerHTML = ICON.check + "<span>Re-created ✓</span>";
          toast("Files re-created from this saved copy.");
        } else {
          btn.innerHTML = orig;
          toast(job.message || "Could not re-create files.");
        }
      } catch (err) {
        btn.innerHTML = orig;
        toast(err.message || "Could not re-create files.");
      }
      btn.disabled = false;
      // revert the confirmation label after a moment (keep the section in place)
      setTimeout(() => { if (btn.isConnected) btn.innerHTML = orig; }, 4000);
    };
  });
}

function waitForExport() {
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const job = await api("/api/export/status");
        if (job.state === "running") setTimeout(tick, 400);
        else resolve(job);
      } catch (err) {
        reject(err);
      }
    };
    tick();
  });
}

function fmtChip(val, label, current) {
  return `<button class="chip-toggle" data-fmt="${val}" aria-pressed="${current === val}">${label}</button>`;
}
function wireFmt() {
  document.querySelectorAll("#fmt .chip-toggle").forEach((c) => {
    c.onclick = () => {
      document.querySelectorAll("#fmt .chip-toggle").forEach((x) =>
        x.setAttribute("aria-pressed", "false"));
      c.setAttribute("aria-pressed", "true");
      state.fmt = c.dataset.fmt;  // persists across status refreshes (see currentFmt)
      toast("Your next backup will use this.");
    };
  });
}

/* ---------- empty / sample / error ---------- */
function emptyLibrary() {
  return `<div class="empty">
    <div class="art"><svg viewBox="0 0 64 64" aria-hidden="true" focusable="false"><path d="M10 14h18l4 4h22v34H10z"/><path d="M20 30h24M20 38h24M20 46h14"/></svg></div>
    <h2>Your library is waiting</h2>
    <p>Back up your Kobo to fill it with your own highlights — or take a look
       around with a sample library first.</p>
    <div class="btn-row center">
      <a class="btn btn-primary" href="#/backup">${ICON.down}<span>Back up my Kobo</span></a>
      <button class="btn" id="try-sample">${ICON.book}<span>Explore a sample library</span></button>
    </div>
  </div>`;
}
function wireEmptyLibrary() {
  const b = document.getElementById("try-sample");
  if (b) b.onclick = () => {
    switchSource("sample");
    renderLibrary();
  };
}

function sampleBanner() {
  return `<div class="sample-banner">
    <span>${ICON.book}</span>
    <span><b>Sample library.</b> This is example data so you can see how Markwell looks.</span>
    <div class="btn-row">
      <a class="btn" href="#/backup">Back up my Kobo</a>
      <button class="btn btn-ghost" id="exit-sample">Exit sample</button>
    </div>
  </div>`;
}
function wireSampleBanner() {
  const b = document.getElementById("exit-sample");
  if (b) b.onclick = () => {
    switchSource("latest");
    renderLibrary();
  };
}

function showError() {
  view.innerHTML = `<div class="wrap"><div class="empty">
    <h2>Markwell hit a snag</h2>
    <p>Something went wrong loading this view. Your highlights and saved copies
       are safe — try reloading.</p>
    <div class="btn-row center"><button class="btn" id="reload-btn">Reload</button></div>
  </div></div>`;
  const b = document.getElementById("reload-btn");
  if (b) b.onclick = () => location.reload();
}

/* ---------- start ---------- */
const quitButton = document.getElementById("quit-app");
if (quitButton) quitButton.onclick = quitApp;
initTheme();
initScrollToTop();
sendHeartbeat();
heartbeatTimer = setInterval(sendHeartbeat, 15000);
route(false);
