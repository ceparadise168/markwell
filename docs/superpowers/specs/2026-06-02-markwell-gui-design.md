# Markwell GUI — Design Spec

- **Date:** 2026-06-02
- **Status:** Built autonomously overnight; **pending Eric's morning acceptance review (驗收)**
- **Author:** Claude (autonomous), for Eric
- **Builds on:** `docs/superpowers/specs/2026-06-01-kobo-backup-design.md` (the CLI), which explicitly deferred a GUI to "future, demand-driven." Eric has now asked for it.

> This doc is written **before/alongside** the build to honor the design-pass-before-code
> discipline. Because Eric is asleep and explicitly authorized an autonomous overnight
> build ("DO PDCA, polish many rounds, 早上起床我再來驗收"), the interactive approval gate
> is deferred to the morning. Every non-obvious decision is recorded here with its
> rationale and the alternatives considered, so the morning review is a real gate.

---

## 1. The ask (verbatim intent)

> "GUI for non-CS-background normal e-book reader. Nice UI/UX, simple, clean, nice ops,
> no learning curve. … 要能夠很簡單的協助使用者完成安全匯出、查看、管理動作."

Three jobs, for someone who is **a book lover, not a computer person**:

1. **安全匯出 — Safe export.** Plug in the Kobo, get a safe backup + readable highlights, with zero fear of breaking the device.
2. **查看 — View.** Read and search their own highlights and notes in a calm, book-like interface.
3. **管理 — Manage.** See their backup history, where files live, and re-create exports from an older backup (the "recover a deleted highlight" story) — without any dangerous buttons.

**Audience constraint that drives everything:** no terminal, no jargon, no configuration, no learning curve. The emotional job is *reassurance* — "I won't break my Kobo, and I won't lose my highlights."

---

## 2. The hard constraint: preserve Markwell's soul

The CLI's differentiators are non-negotiable and the GUI must inherit them exactly:

| Soul property | How the GUI keeps it |
|---|---|
| **Zero runtime dependencies** (stdlib only) | Backend = stdlib `http.server`. Frontend = hand-written **vanilla HTML/CSS/JS** — no React/Vue, no bundler, no `npm`, no build step. |
| **Never writes to the device** | The GUI calls the *same* `device.snapshot()` safe core. It adds no new device access path. |
| **All-local, offline, no telemetry** | Server binds to **127.0.0.1 only**; the browser talks only to localhost; no outbound network ever. |
| **Immutable snapshot history** | Same `backups/KoboReader-<stamp>.sqlite` model. The GUI **never deletes** snapshots. |
| **Solo-maintainable** | Thin front-end over the existing core; vanilla frontend with no toolchain to rot. |

---

## 3. Tech decision: a local web app (stdlib server + vanilla web UI)

**Chosen:** A tiny local web server (`http.server`, bound to `127.0.0.1`, ephemeral port) that
serves a hand-written HTML/CSS/JS app and a small JSON API over the existing safe core. On
launch it opens the user's default browser. This is what the user experiences as "the Markwell app."

**Alternatives considered:**

- **A) `tkinter` desktop app (stdlib).** Zero deps and a native window — but tkinter cannot
  deliver the "nice, clean, modern UI/UX" Eric asked for without heroics, CJK/typography control
  is poor, and styling is dated. Rejected on UX quality.
- **B) Local web app (chosen).** Zero *Python* deps (stdlib server), and HTML/CSS/JS gives a
  genuinely beautiful, accessible, CJK-perfect, responsive UI. localhost-only preserves the
  offline/privacy soul. Reuses the core verbatim. **Best fit for "nice UI/UX" × "zero deps."**
- **C) Electron / Tauri / PyQt / Flask+React.** All break zero-dep and/or add a build toolchain
  and large install footprint. Against the project's soul. Rejected.

**Cost of B, and the mitigation:** a local server that can touch a device and the filesystem is a
small attack surface for other local processes / malicious web pages. Mitigated by a strict
security model (§7). This is acceptable and is the standard pattern for local-first apps
(Jupyter, Syncthing, etc.).

**Frontend = vanilla on purpose.** Modern CSS (custom properties, grid, system font stack) makes a
clean, elegant UI without a framework, and keeps the zero-dependency / no-build promise. It is
*more* maintainable for a solo author than a framework + bundler that needs upkeep.

---

## 4. Architecture — `gui/` is a front-end sibling of `cli.py`

The existing code names modules by **responsibility / interface type**: `device` (find+snapshot),
`reader` (the one schema-aware module), `model` (stable records), `render/` (model→text),
`cli` (command-line interface). By that convention the new package is the **graphical interface** —
the sibling of `cli` — so it is named **`gui/`**. `cli` and `gui` are two front-ends over one safe core.

```
markwell/
  device.py          detect + safe read-only snapshot      ── the safety core (unchanged)
  reader.py          the ONLY schema-aware module           ── (unchanged)
  model.py           Book / Highlight                       ── (unchanged)
  render/            model → Markdown / JSON                 ── (unchanged, reused by export)
  cli.py             command-line interface                 ── (unchanged)
  gui/               graphical interface — a local web app   ── NEW
    __init__.py
    __main__.py      `python -m markwell.gui`
    service.py       GUI use-cases over the safe core (no HTTP): status, export, snapshots, books, sample
    server.py        HTTP transport: routing, security (Host + token), static files, threading
    sample.py        in-memory sample library (public-domain titles) for empty-state / first-run
    assets/
      index.html     one page; three views (Back up / Library / History)
      style.css      the whole visual system
      app.js         vanilla view-router + fetch() calls to the API
```

**Why split `service.py` / `server.py`:** the *use-cases* (what the GUI can do) are separated from
the *transport* (HTTP). The service layer reuses `device`/`reader`/`render` and is unit-testable
with no sockets; the server is a thin shell that adds routing + security. This is the same
ports-and-adapters seam the CLI already implies, made explicit. It also signals the design
philosophy: **the safe core is reused, never reimplemented; presentation layers are thin and swappable.**

**Naming note for review:** the user-facing command is `markwell-gui` (users think "the app/GUI"),
while the implementation is a local web server. `gui/` names the *purpose* (parallel to `cli`); the
module header states it is implemented as a 127.0.0.1 web app. Flagging this purpose-vs-mechanism
split explicitly per the naming-as-philosophy rule.

### Data flow (safety invariant preserved)

```
browser (127.0.0.1)
   │  POST /api/export        GET /api/books?source=…       GET /api/snapshots
   ▼
gui/server.py  ──(Host + token check)──►  gui/service.py
                                              │
                  detect_device → snapshot ONCE (read-only) → reader → model → render → write files
```

The device is still read **at most once per export**, read-only, never written — because the GUI
calls the identical `device.snapshot()` / `reader.read_books()` the CLI uses.

---

## 5. Information architecture & screens

One window, a calm left rail with **three destinations** (matching the three jobs). Three is well
within a non-technical user's cognitive budget, and they map 1:1 to what Eric asked for.

### 5.1 Back up (安全匯出) — the home / hero screen

- A single, unmistakable primary action: **"Back up my Kobo."**
- **Device status** banner: "✓ Kobo connected" or "Plug in your Kobo with its USB cable" + Retry.
- A calm, permanent reassurance line: **"Markwell only ever *reads* your Kobo. It never changes
  anything on your device."**
- On click → live progress (Detecting → Saving a safe copy → Reading your highlights → Done),
  driven by a background thread + polling (the UI never looks frozen).
- **Success state:** "✓ Saved **926 highlights** from **14 books**." → two next steps:
  **"Read them"** (go to Library) and **"Open the folder"** (reveal files in Finder/Explorer).
- Plain language only: "safe copy," "your highlights," "folder" — never "snapshot," "SQLite,"
  "schema," "export format."

### 5.2 Library (查看) — read & search

- A grid of **book cards**: title, author, highlight count, year span. Sorted by most-highlighted
  (mirrors the Markdown index).
- A single **search box** filters across all books/highlights live.
- Click a card → **book detail**: highlights in true reading order, grouped by chapter, each with
  its note (if any) and date. Reading-grade typography, generous whitespace, **CJK-perfect** font
  stack (real data is Chinese). Feels like a reading app, not a database table.
- Empty state (no backups yet): a friendly nudge to back up, **plus "Explore a sample library"**
  so a first-time user (and the morning reviewer, whose `backups/` is empty) can see the View
  immediately, with zero device required and zero real data.

### 5.3 History (管理) — backups & files, safely

- A timeline of **saved copies** (snapshots): date, relative age ("today", "3 days ago"), size,
  and which one the Library is currently showing.
- **"Re-create highlights from this copy"** on any older snapshot → re-runs export from that
  snapshot (the documented recover-a-deleted-highlight story), then refreshes the Library.
- **Where your files live:** the data folder path, shown plainly, with **"Open folder."**
- Advanced (collapsed): export format (Markdown / JSON / both — default both). No other knobs.
- **No delete.** Snapshots are immutable history; the GUI never destroys them. If a user truly
  wants to remove one, they do it themselves in their file manager (one click via "Open folder").
  This is a deliberate safety choice, consistent with the CLI's never-overwrite model.

---

## 6. Data location (a deliberate divergence from the CLI)

The CLI writes `backups/` and `output/` **relative to the current working directory** — correct for
a developer in a terminal. A GUI is launched by double-click / a desktop shortcut, where CWD is
unpredictable, so files would land somewhere the user can never find.

**Decision:** the GUI defaults its data folder to **`~/Markwell/`** (with `backups/` and `output/`
inside), shows that path prominently, and offers "Open folder." Overridable with `--data-dir`.

- Rejected `~/Documents/Markwell` — "Documents" can be localized/cloud-synced; `~/Markwell` is
  predictable and unambiguous on every platform.
- The path is always visible, so there is never any mystery about where things are.

---

## 7. Security model (this is part of "safe")

A localhost server that snapshots a device and writes files must not be drivable by other local
processes or a malicious web page. Mitigations, all stdlib:

1. **Bind `127.0.0.1` only** (never `0.0.0.0`); **ephemeral port** (`port 0`) to avoid collisions.
2. **Per-launch secret token.** Generated with `secrets.token_urlsafe()` at startup, embedded in
   the served page. Every `/api/*` request must carry it (`X-Markwell-Token`); otherwise 403.
   This blocks CSRF and any other-origin / other-process caller that doesn't have the token.
3. **Host-header allowlist** (`127.0.0.1:<port>` / `localhost:<port>`) → blocks DNS-rebinding.
4. **Same-origin only** — no CORS headers are sent, so browsers block cross-origin reads.
5. **"Open folder" takes no path from the client** — it can only reveal the known data/backups/
   output dirs. No arbitrary-path or shell-string execution anywhere (arg-list subprocess only).
6. **No network egress, no telemetry** — consistent with `SECURITY.md`.

The server is also **single-user/local** and shuts down cleanly; it is meant to be opened, used,
and closed, not left running as a daemon.

---

## 8. Accessibility & polish (the repo already cares — see the AX commit)

- Semantic HTML landmarks, one `<h1>` per view, labeled controls, visible focus rings.
- Full keyboard operation (tab order, Enter/Esc, search shortcut). Screen-reader live-region for
  export progress and results.
- Color contrast ≥ WCAG AA; respects `prefers-color-scheme` (light/dark) and
  `prefers-reduced-motion`.
- CJK-aware font stack and line-height; never clip or break CJK text.
- Responsive down to a small window; works at 200% zoom.

---

## 9. Testing

- **Service layer** (no sockets): status with/without a snapshot; export end-to-end against the
  fixture DB; snapshot listing; book JSON shape; sample library shape. Reuses/extends `conftest`.
- **Security:** requests without the token → 403; bad `Host` → 403; `127.0.0.1` bind asserted.
- **Server smoke:** start on an ephemeral port, `GET /` 200, `GET /api/status` shape.
- All tests use **synthetic data only** — never Eric's real highlights, and nothing personal is
  ever committed (screenshots in this repo are from the sample library).

---

## 10. Scope

**In (tonight):** launch + auto-open browser; secure local server; Back up screen with live
progress + result; Library grid + search + book detail (reading order, chapters, notes, dates,
CJK); History (snapshots, re-create from a copy, show path, open folder); sample mode; empty /
loading / error / success states; accessibility pass; tests; `markwell-gui` entry point +
`python -m markwell.gui`; this design doc + a PDCA iteration log + sample-data screenshots.

**Out (not now):** packaged double-click installer (PyInstaller) — the real "no terminal" endgame,
but a separate packaging effort; UI internationalization (strings are centralized so a 中文 toggle
is a cheap follow-up); editing/among/deleting highlights; cloud sync; multi-device. None of these
are needed to satisfy the three jobs, and per "不確定不加" they are deferred until asked.

---

## 11. 5-lens design pass

- **Product.** The CLI already nails *safe + portable*; its ceiling is *reachability* for
  non-technical readers. The GUI removes the terminal — the single biggest adoption blocker named
  in the original spec — without compromising the safety model. The hero flow is one button; the
  reassurance copy targets the real emotion (fear of breaking the device / losing highlights).
- **Ops.** Zero new dependencies → no new supply-chain or CVE surface. Vanilla frontend → no build
  toolchain to rot. Same firmware-schema risk as the CLI, concentrated in `reader.py` (unchanged).
  The server is local, ephemeral, and self-closing — nothing to operate. Solo-maintainable.
- **UX.** Three destinations = the three jobs. Defaults that just work; advanced knobs hidden.
  Plain language; permanent safety reassurance; never-frozen progress; always-visible file
  location; friendly empty/error states; sample mode so the value is visible before plugging in.
  Accessible and CJK-perfect.
- **Architecture.** `gui/` is a thin presentation sibling of `cli.py`; `service.py`/`server.py`
  separate use-cases from transport; the safe core (`device`/`reader`/`render`) is reused verbatim,
  never duplicated. The seam is honest and testable; nothing speculative is added.
- **Business.** Free/OSS; success = a Kobo-owning book lover can back up and read their highlights
  with zero fear and zero terminal. Cost = maintenance, kept low by zero-dep + vanilla + tight
  scope. Reputation upside: a genuinely kind, safe tool.

---

## 12. PDCA plan (overnight)

- **Plan:** this doc.
- **Do:** build the skeleton + each screen.
- **Check:** run the server; drive it with Playwright for real screenshots; fan out a multi-
  dimensional review (UX/visual, accessibility, security, code-quality, copy/tone, cross-platform)
  via a workflow; collect prioritized findings; run the test suite.
- **Act:** fix findings, polish, re-screenshot. Repeat for several rounds.
- Each round is recorded in `docs/superpowers/specs/2026-06-02-markwell-gui-pdca-log.md`.

---

## 13. Open questions for the morning (the real gate)

1. **UI language.** Shipped English (OSS lingua franca) with CJK-perfect *content* and centralized
   strings. Want a 中文 toggle now, or as a follow-up?
2. **Data folder default `~/Markwell`** — good, or prefer `~/Documents/Markwell` / something else?
3. **Launch ergonomics.** Tonight: `markwell-gui` / `python -m markwell.gui`. Want me to pursue a
   true double-click app (PyInstaller) next?
4. **Sample library** — keep it as a permanent first-run feature, or strip it once you've reviewed?
5. **Commit/branch.** Built on a local `feat/gui` branch, **not pushed** (your call, per the hard
   rule). Want it merged / pushed, or kept local?
