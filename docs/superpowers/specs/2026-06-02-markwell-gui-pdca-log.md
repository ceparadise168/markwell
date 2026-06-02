# Markwell GUI — PDCA Iteration Log

Overnight build for Eric. Each round = Plan → Do → Check → Act. Newest round on top
of the "rounds" section. Acceptance review (驗收) is in the morning.

> How to try it (no install needed, from the repo root):
> `python3 -m markwell.gui` — opens the app in your browser. Add `--data-dir .` to use
> this folder, or just plug in your Kobo and click **Back up my Kobo**. `Ctrl+C` to stop.

---

## Status snapshot

- **Build:** complete and working end-to-end (verified in a real browser against real SQLite).
- **Tests:** 64 passing (`python3 -m pytest -q`) — 46 pre-existing + 18 new (GUI + export).
- **Branch:** `feat/gui`, local only, **not pushed** (Eric's call).
- **No personal data** committed; all screenshots use the built-in sample / test fixture.

---

## Round 1 — build + first visual pass (self-review)

**Plan.** Local web app (stdlib server + vanilla HTML/CSS/JS), three jobs (Back up /
Library / History), reusing the safe core. See the design spec.

**Do.** Built `markwell/gui/` (`service.py`, `server.py`, `sample.py`, assets), extracted
the shared render+atomic-write core into `markwell/export.py` (so CLI & GUI are identical),
added `markwell-gui` entry point + `python -m markwell.gui`, wrote the test suite.

**Check.** Ran the server live; drove it with a real browser (Playwright) across every
screen + state; captured screenshots (`docs/screenshots/`); ran the test suite; smoke-tested
the security boundary with `curl`.

Verified working:
- Token injected into the page; `/api/*` returns **403 without the token**, 200 with it.
- Foreign `Host` header → **403** (DNS-rebinding guard).
- Sample library renders (incl. CJK 道德經) — proves the View pipeline.
- Library reads **real SQLite snapshots** (fixture books shown with dogear/hidden correctly excluded).
- "Re-create files" runs a real export through the browser → wrote `index.md`, per-book `.md`,
  `highlights.json` (schema `markwell/1`).
- Responsive: sidebar collapses to an icon top-bar on narrow windows.

**Act — issues found in the screenshots and fixed this round:**
1. Sidebar safety text wrapped one word per line — text nodes were becoming separate flex
   items. Wrapped the message in a `<span>`.
2. Anchor-styled buttons (`<a class="btn">`) showed a link underline. Added
   `text-decoration: none` to `.btn`.
3. During progress/success the big call-to-action button and the stale "latest copy" line
   stayed visible. Now hidden while a backup is running or finished.
4. Progress steps were left-aligned under a centered hero. Centered the steps block.
5. Added a reassuring sub-line under the hero button ("Takes a few seconds · Nothing ever
   leaves your computer").

---

## Round 2 — multi-dimensional adversarial review

**Plan.** Fan out 6 independent reviewers (UX, accessibility, security, code-quality,
copy/tone, cross-platform) via a workflow; adversarially verify each finding against the
project constraints to drop false positives; act on the confirmed list, P0 first.

**Check.** The workflow (50 agents) raised **44 findings**; after adversarial verification
**39 were confirmed real** (1 P0, 8 P1, 17 P2, 13 P3). Notably, **three independent
reviewers** flagged the same Windows-only `strftime` crash — high signal.

**Act — fixed this round (essentially all 39):**

P0
- **Screen readers heard nothing during the core backup flow.** Added a polite `aria-live`
  status region that announces each phase and the final result; move focus to the result/
  error; mark the visual step list `aria-hidden`.

P1
- **Search to zero results showed a blank void** — both render paths now converge on a
  persistent "No highlights match …" block + a live result count.
- **Dark-theme primary button failed contrast** (2.43:1) → darkened the dark accent to
  ~5.0:1; nudged faint text over AA in both themes.
- **Icon-only nav had no accessible name** → `aria-label` per link; on narrow screens the
  labels now stack under the icons instead of disappearing.
- **Focus was dropped after async actions / on success** → focus the result region; the
  re-create action now updates its button in place (no page reset).
- **Windows crash: `%-d`/`%-I` strftime** → portable date builder (`_fmt_when`) + a test.
- **A corrupt/old snapshot crashed the request thread** → API handlers now map backend
  errors to friendly JSON (422/500) the UI can show; + a test.

P2 (selection)
- Device banner now hides during progress/success (no self-contradiction).
- Library is sorted most-highlighted-first (matches the Markdown index).
- Book detail uses real list semantics (`<h2>` chapter + `<ul>/<li>`).
- **Content-Security-Policy** added; removed the one inline handler so `script-src 'self'`
  holds. POST bodies are drained before any reject (keep-alive can't desync).
- `_reveal`/`open_folder` handle a missing opener (e.g. no `xdg-open`) without crashing;
  `detect_device` guards `getpass.getuser()`.
- **Wired the export-format toggle through to the server** (it was a no-op control before);
  relabelled chips to "Both / Readable text / A data file"; kinder, jargon-free error copy.
- `waitForExport()` can no longer hang forever if a poll throws.

P3 (selection)
- Decorative SVGs `aria-hidden`; `chapter_index` now escaped (closing the last XSS gap);
  documented the local-server threat model in `SECURITY.md`; `do_HEAD` no longer runs a
  device probe; friendly catch-all error screen; O(n²) card lookup removed; open-folder
  toasts on success/failure; re-export error copy no longer says "reconnect the device"
  when no device is involved.

**Deliberately not changed:**
- The primary "Back up my Kobo" button stays fully enabled when no device is detected
  (clicking gives a kind "plug it in" message) — disabling the one hero action read as more
  confusing than the friendly error. Noted for Eric.

**Re-verified after fixes:** 67 tests pass; zero browser console errors/warnings; CSP active
and not blocking; live screenshots refreshed (incl. dark mode, narrow, and no-match).

---

## Round 3 — regression + fresh-eyes verification

**Plan.** The Round 2 fixes included a large `app.js`/`server.py` rewrite — exactly what
introduces regressions. Plus a self keyboard-nav smoke test. Then a lean 3-agent workflow
(regression / security / UX-a11y) focused on *regressions and remaining real issues*.

**Check.** I keyboard-tested first and caught a focus-order bug myself; the workflow then
raised **12, confirmed 11 (8 regressions)**. The headline: the **format toggle was still
broken** — two reviewers independently found that `loadStatus()` replaces `state.status`
wholesale on every navigation, so the choice reset before the hero backup ran. (My Round-2
"it works" check only passed because I didn't navigate between choosing and re-exporting.)

**Act — fixed:**
- **Self-found (keyboard):** `route()` moved focus to `<main>` even on first load, so the
  first Tab skipped the skip-link/nav. Now focus moves only on user navigation; first Tab
  reaches skip-link → nav. Verified live (Tab/Enter walk).
- **P1 — format toggle reset on navigation:** the chosen format now lives in a persistent
  `state.fmt` (not the replaced `state.status`); `currentFmt()` reads it; History chips
  render from it. **Verified live:** pick JSON → navigate to Backup → `currentFmt()` is still
  `"json"`. (And confirmed a JSON-only re-export writes only `highlights.json`, pruning `.md`.)
- **P2 — search no-match hidden from screen readers / count spam:** `#count` is now a plain
  visual label; a debounced sr-only live region announces results once typing settles; the
  no-match message is in the accessibility tree. Verified live.
- **P2 — keep-alive desync via `Transfer-Encoding: chunked`:** rejected and connection closed.
- **P3 — malformed `Content-Length` crashed the thread:** parsed defensively → clean `400`.
  (Both framing cases now covered by tests.)
- **P3 — zombie/duplicate export-poll loops** after navigating away: a `pollGen` token retires
  stale loops on navigation.
- **P3 — live region re-announced the same phase every 500ms:** guarded on phase change.

**Deliberately not changed (noted for Eric):**
- **"Chapter N" in the reading view** labels `reader.py`'s reading-order counter, which isn't
  guaranteed to equal the book's printed chapter number when only some chapters are
  highlighted. Kept as-is because it matches the shipped CLI/Markdown export (`ch.N`) and the
  documented model meaning; changing the export's visible content is a CLI decision for you.

**Re-verified:** 69 tests pass; zero console errors; format persistence, keyboard nav, and
search a11y confirmed in a live browser.
