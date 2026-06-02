/* Markwell GUI — vanilla front-end. No framework, no build step. */

"use strict";

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
  folder: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
  book: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM19 17H6"/></svg>',
  search: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>',
  back: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M15 18l-6-6 6-6"/></svg>',
  down: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 4v12m0 0 5-5m-5 5-5-5M5 18v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1"/></svg>',
  refresh: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M20 11a8 8 0 1 0-.5 4M20 5v5h-5"/></svg>',
  clock: '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/></svg>',
};

/* ---------- shared state ---------- */
const state = {
  status: null,
  source: "latest",   // 'latest' | 'sample' | a snapshot filename
  lib: null,          // cached books document for `source`
  q: "",
  fmt: null,          // user-chosen export format; survives status refreshes
};

let pollGen = 0;      // bumped on navigation to retire stale export-poll loops
let srPhase = "";     // last phase announced, so the live region doesn't repeat
let srSearchTimer;    // debounce for the search live-region announcement

function currentFmt() {
  return state.fmt || (state.status && state.status.format) || "all";
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
  }
  return state.lib;
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
  setNav(name === "book" ? "library" : name);
  const fn = routes[name];
  view.innerHTML = '<div class="wrap"><div class="route-load"><span class="spinner"></span></div></div>';
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

  const lastLine = (s.has_library && s.latest_snapshot)
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
    await api("/api/export", { method: "POST", body: { use_device: true, format: currentFmt() } });
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

/* ---------- view: Library ---------- */
async function renderLibrary() {
  await loadStatus();
  const source = state.source === "sample" ? "sample"
    : (state.status.has_library ? state.source : "latest");
  const lib = await loadLibrary(source);

  if (lib.source_kind === "empty") {
    view.innerHTML = `<div class="wrap">${emptyLibrary()}</div>`;
    wireEmptyLibrary();
    return;
  }

  const books = lib.books || [];
  const totalHl = books.reduce((n, b) => n + b.highlights.length, 0);

  view.innerHTML = `<div class="wrap">
    ${lib.source_kind === "sample" ? sampleBanner() : ""}
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
    <div class="empty" id="noMatch" hidden><p></p></div>
  </div>`;

  wireSampleBanner();
  const input = document.getElementById("q");
  input.oninput = () => { state.q = input.value; refreshGrid(); };
  refreshGrid();
  if (state.q) { input.focus(); input.setSelectionRange(input.value.length, input.value.length); }
}

function refreshGrid() {
  const books = (state.lib && state.lib.books) || [];
  const q = state.q.trim().toLowerCase();
  // most-highlighted first (mirrors the Markdown index), then title
  const matches = (q ? books.filter((b) => bookMatches(b, q)) : books.slice())
    .sort((a, b) => b.highlights.length - a.highlights.length
      || (a.title || "").localeCompare(b.title || ""));

  const grid = document.getElementById("grid");
  if (grid) grid.innerHTML = matches.map(bookCard).join("");

  const count = document.getElementById("count");
  if (count) count.textContent = q ? `${matches.length} of ${books.length} books match` : "";

  const nm = document.getElementById("noMatch");
  if (nm) {
    nm.hidden = matches.length !== 0;
    const p = nm.querySelector("p");
    if (p) p.textContent = q ? `No highlights match “${state.q}”.` : "No books yet.";
  }
  // announce results to screen readers, debounced so typing doesn't spam
  announceSearch(!q ? "" : matches.length
    ? `${matches.length} of ${books.length} books match`
    : `No highlights match ${state.q}.`);
  wireCards();
}

function bookMatches(b, q) {
  if ((b.title || "").toLowerCase().includes(q)) return true;
  if ((b.author || "").toLowerCase().includes(q)) return true;
  return b.highlights.some((h) =>
    (h.text || "").toLowerCase().includes(q) ||
    (h.note || "").toLowerCase().includes(q));
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

/* ---------- view: Book detail ---------- */
async function renderBook(arg) {
  await loadStatus();
  const source = state.source === "sample" ? "sample"
    : (state.status.has_library ? state.source : "latest");
  const lib = await loadLibrary(source);
  const book = (lib.books || [])[Number(arg)];
  if (!book) { location.hash = "#/library"; return; }

  const n = book.highlights.length;
  const span = yearSpan(book);

  // group highlights into <h2> chapter + <ul> sections (valid list semantics)
  let body = "", lastChap = null, open = false;
  book.highlights.forEach((h) => {
    if (h.chapter_index !== lastChap) {
      if (open) body += "</ul>";
      body += `<h2 class="chapter">Chapter ${esc(h.chapter_index)}</h2><ul class="hl-list">`;
      open = true;
      lastChap = h.chapter_index;
    }
    const note = h.note ? `<div class="note"><b>Your note:</b> ${esc(h.note)}</div>` : "";
    const date = h.date ? `<div class="date">${esc(h.date)}</div>` : "";
    body += `<li class="hl"><div class="text">${esc(h.text)}</div>${note}${date}</li>`;
  });
  if (open) body += "</ul>";

  view.innerHTML = `<div class="wrap">
    <a class="back" href="#/library">${ICON.back}<span>All books</span></a>
    <header class="detail-head">
      <h1>${esc(book.title)}</h1>
      ${book.author ? `<div class="by">${esc(book.author)}</div>` : ""}
      <div class="stat">${n} highlight${n === 1 ? "" : "s"} &amp; notes${span ? " · " + esc(span) : ""}</div>
    </header>
    ${body}
  </div>`;
}

/* ---------- view: History ---------- */
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
  return `<li class="snap ${sn.is_latest ? "latest" : ""}" data-name="${esc(sn.name)}">
    <span class="snap-dot">${ICON.clock}</span>
    <div class="snap-main">
      <div class="snap-date">${esc(sn.date)} ${sn.is_latest ? '<span class="pill">Newest</span>' : ""}</div>
      <div class="snap-sub">${esc(sn.age)} · ${sn.size_kb.toLocaleString()} KB</div>
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
      state.source = name; state.lib = null; state.q = "";
      location.hash = "#/library";
    };
    li.querySelector('[data-act="reexport"]').onclick = async (e) => {
      const btn = e.currentTarget;
      const orig = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span><span>Working…</span>';
      try {
        await api("/api/export", { method: "POST", body: { use_device: false, source: name, format: currentFmt() } });
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
    state.source = "sample"; state.lib = null; state.q = "";
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
    state.source = "latest"; state.lib = null; state.q = "";
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
route(false);
