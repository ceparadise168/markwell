# Markwell Community Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Markwell as a launch-ready open-source product for zh-TW/ja/ko/en Kobo readers: fully localized GUI, five export formats, quote review + share cards, cloud-folder backup, OSS launch pack, and a Cloudflare Pages landing site — zero paid APIs, zero new runtime deps.

**Architecture:** Backend emits data + stable codes; the frontend owns all presentation (i18n, dates). New export formats are pure renderers behind a registry. Share cards are client-side Canvas. Cloud backup = guided data-dir relocation into the user's existing sync folder (copy, never move). Spec: `docs/superpowers/specs/2026-06-11-community-release-design.md` (blessed 2026-06-11).

**Tech Stack:** Python stdlib only (runtime), hand-written HTML/CSS/JS (no build step), pytest, GitHub Actions, PyInstaller (build-time), Cloudflare Pages (static).

**Execution rules (every task):**
- TDD: failing test → minimal implementation → green. Run `python3 -m pytest -q` (full suite) before every commit; all green, no skips added.
- Minimal diffs, match surrounding style/docstring density. Never violate: stdlib-only runtime; never write to device; no network at runtime; `reader.py` is the only schema-aware module; renderers stay pure; `markwell/1` JSON schema untouched.
- Commit after each task with the message given. Sub-agents run on Fable 5, max effort.
- Locale set everywhere: `en`, `zh-TW`, `ja`, `ko` (BCP 47, case-sensitive). English is the canonical source; translations must be natural, not machine-literal. zh-TW uses Taiwan reading-community vocabulary (劃線/書摘/筆記/備份).

---

## Phase 1 — i18n foundation

### Task 1: Render-layer label tables + localized Markdown + CLI `--lang`

**Files:**
- Create: `markwell/render/labels.py`
- Modify: `markwell/render/markdown.py`, `markwell/export.py` (`build_meta`), `markwell/cli.py`
- Test: create `tests/test_labels.py`; modify `tests/test_render_markdown.py`, `tests/test_cli.py`

**Contract:** `labels.py` exposes `LABELS: dict[str, dict[str, str]]` and `def for_lang(lang: str | None) -> dict[str, str]` (unknown/None → en). Keys (exact, complete):
`index_title, note_label, highlights_one, highlights_many, books_word, generated_word, source_word, col_book, col_author, col_highlights, col_years, chapter_abbrev`.
en values = the strings currently hardcoded in `markdown.py` ("Kobo Highlights", "note:", "highlight", "highlights", "books", "Generated", "source", "Book", "Author", "Highlights", "Years", "ch."). zh-TW/ja/ko: natural translations (zh-TW: 書摘總覽/筆記：/則劃線/…/第 N 章 style via `chapter_abbrev` kept as prefix token, e.g. "第{n}章" is NOT the shape — keep `── ch.{n} ──` shape: `chapter_abbrev` is the "ch." token, zh-TW "第", rendered as `── 第{n}章 ──`? **Pinned:** keep renderer line shape `── {chapter_label} ──` where labels.py provides `chapter_line(lang, n) -> str` helper returning "ch.{n}" / "第{n}章" / "第{n}章" (ja) / "{n}장" (ko)).
`build_meta(source, freshness, lang="en")` adds `"lang": lang` to meta. `markdown.render` reads `meta.get("lang")`.

- [ ] **Step 1: Failing tests** — in `tests/test_labels.py`:

```python
from markwell.render import labels

def test_all_locales_share_exact_key_set():
    key_sets = {loc: set(d) for loc, d in labels.LABELS.items()}
    assert set(key_sets) == {"en", "zh-TW", "ja", "ko"}
    base = key_sets["en"]
    for loc, keys in key_sets.items():
        assert keys == base, f"{loc} drifted: {keys ^ base}"

def test_unknown_lang_falls_back_to_english():
    assert labels.for_lang("fr") == labels.LABELS["en"]
    assert labels.for_lang(None) == labels.LABELS["en"]

def test_chapter_line_per_locale():
    assert labels.chapter_line("en", 3) == "ch.3"
    assert labels.chapter_line("zh-TW", 3) == "第3章"
    assert labels.chapter_line("ko", 3) == "3장"
```

In `tests/test_render_markdown.py` add: rendering with `meta={"lang": "zh-TW", ...}` produces `筆記：` instead of `note:` and `── 第1章 ──`; index title localized; **highlight text itself verbatim**. In `tests/test_cli.py`: `--lang zh-TW` flows through (assert generated md contains 筆記： when a note exists); invalid `--lang xx` exits 2 (argparse choices).
- [ ] **Step 2: Run; verify new tests fail** (`python3 -m pytest tests/test_labels.py -q` → import error).
- [ ] **Step 3: Implement** labels.py; thread `meta["lang"]` through markdown.py (labels looked up once at top of `render()`; pass into `_render_book`/`_render_index`); add `--lang` (argparse `choices=["en","zh-TW","ja","ko"]`, default "en") in cli.py; `build_meta` gains `lang` param (default "en" — GUI callers updated in Task 3).
- [ ] **Step 4: Full suite green.**
- [ ] **Step 5: Commit** `feat(i18n): localized export labels (md) + --lang flag`

### Task 2: Sample library — add ja + ko books, fix 道德經 order

**Files:** Modify: `markwell/gui/sample.py`; Test: modify `tests/test_gui.py` (or wherever sample is asserted — check `grep -rn "sample" tests/`)

- [ ] **Step 1: Failing test:** sample library contains exactly 6 books; one with `author == "夏目漱石"` (title 草枕, 3–4 highlights from the famous opening 「山路を登りながら、こう考えた。智に働けば角が立つ。情に棹させば流される。意地を通せば窮屈だ。とかくに人の世は住みにくい。」 split into separate highlights with one Japanese note), one with `author == "김소월"` (title 진달래꽃, 3 highlights from the 1925 poem, one Korean note). 道德經 highlights' `chapter_index` list must be sorted ascending (1, 33, 64, 78).
- [ ] **Step 2: Run; fails.**
- [ ] **Step 3: Implement** (public-domain text only: 夏目漱石 d.1916, 草枕 1906; 김소월 d.1934, 진달래꽃 1925 — both PD worldwide. Reorder 道德經 entries 64 before 78. Keep docstring's PD statement updated to name all authors).
- [ ] **Step 4: Full suite green.**  - [ ] **Step 5: Commit** `feat(gui): ja/ko sample books + fix 道德經 chapter order`

### Task 3: Backend emits data, not English — snapshot list + meta lang

**Files:** Modify: `markwell/gui/service.py` (`snapshot_list`, `_run_export` meta, `library`), `markwell/gui/assets/app.js` (history rendering only, minimal); Test: `tests/test_gui.py`

**Contract:** `snapshot_list()` rows become `{"name", "stamp", "size_bytes", "is_latest"}` where `stamp` is ISO 8601 local naive (`when.isoformat()`) or `None` if unparseable. Delete `_fmt_when` / `_human_age` (presentation moves to browser `Intl`). Service gains `lang` no — **locale never enters the backend**; instead `library()`/`_run_export` pass the service's existing `fmt`; `build_meta` lang is supplied per-request: `/api/export` body and `/api/books` query gain optional `lang` (validated against the 4 codes, default "en") so exported md/html files match the UI language. `start_export(..., lang="en")` threads it to `build_meta`.

- [ ] **Step 1: Failing tests:** snapshot_list returns `stamp`/`size_bytes` and no `date`/`age` keys; `start_export(..., lang="zh-TW")` produces output md containing `筆記：` (use existing fake-device fixtures in `tests/conftest.py`); invalid lang in API body → server falls back "en" (server test in Step 3 covers 400-free behavior — pin: **silently coerce unknown → "en"**, never error).
- [ ] **Step 2: Run; fails.**
- [ ] **Step 3: Implement** backend; update `app.js` history view to format `stamp` via `new Intl.DateTimeFormat(undefined, {dateStyle:"medium", timeStyle:"short"})` and relative age via `Intl.RelativeTimeFormat` helper `relAge(stampIso, nowDate) -> string` (≤90s "just now" equivalent handled by RelativeTimeFormat seconds/minutes/days switch; KB-size from `size_bytes`). Temporary English literals here are fine — Task 5 sweeps them into `t()`.
- [ ] **Step 4: Full suite green.**  - [ ] **Step 5: Commit** `refactor(gui): backend emits data/codes; browser owns formatting`

### Task 4: i18n.js infrastructure + language switcher + parity test

**Files:**
- Create: `markwell/gui/assets/i18n.js`
- Modify: `markwell/gui/assets/index.html` (script tag BEFORE app.js; switcher in topbar), `markwell/gui/server.py` (`_STATIC` add `"/i18n.js"`), `markwell/gui/assets/style.css` (switcher styling, matches existing tokens)
- Test: create `tests/test_gui_i18n.py`

**Contract:** `i18n.js` must begin (after a comment header) with exactly `const I18N =` followed by a **strict-JSON** object literal then `;` — machine-checkable from Python. Shape: `{"en": {...}, "zh-TW": {...}, "ja": {...}, "ko": {...}}`, flat string keys, `{param}` placeholders. Then plain JS:
`function t(key, params)` (active-locale lookup → en fallback → key itself; `{x}` substitution), `function detectLocale()` (`localStorage["markwell-locale"]` → exact match `navigator.language` → prefix match zh→zh-TW/ja/ko → "en"), `function setLocale(loc)` (persists, sets `document.documentElement.lang`, dispatches `markwell:locale` event), `function localeNames()` → `{"en":"English","zh-TW":"中文（台灣）","ja":"日本語","ko":"한국어"}`. Switcher UI: a `<select>` in the topbar next to the theme toggle, always visible, native names, `aria-label` via t(). On change: `setLocale` + re-route (app.js listens for `markwell:locale` and re-renders current view — wire in Task 5; for now switcher only persists + sets lang attr).

- [ ] **Step 1: Failing test** `tests/test_gui_i18n.py`:

```python
import json, pathlib, re

ASSETS = pathlib.Path("markwell/gui/assets")

def _dicts():
    src = (ASSETS / "i18n.js").read_text(encoding="utf-8")
    start = src.index("const I18N =") + len("const I18N =")
    end = src.index("};", start) + 1
    return json.loads(src[start:end])

def test_locales_present_and_keys_in_parity():
    d = _dicts()
    assert set(d) == {"en", "zh-TW", "ja", "ko"}
    base = set(d["en"])
    assert base, "en dictionary must not be empty"
    for loc, table in d.items():
        assert set(table) == base, f"{loc} drift: {set(table) ^ base}"
        assert all(isinstance(v, str) and v.strip() for v in table.values())

def test_every_t_key_used_in_js_exists_in_en():
    d = _dicts()
    used = set()
    for name in ("app.js", "i18n.js"):
        src = (ASSETS / name).read_text(encoding="utf-8")
        used |= set(re.findall(r"""(?<![\w.])t\(\s*["']([\w.-]+)["']""", src))
    missing = used - set(d["en"])
    assert not missing, f"t() keys missing from en dict: {missing}"
```

(Second test passes trivially until Task 5 adds `t()` calls — that is fine; it guards forever after.) Also: served-asset test mirroring the existing `/app.js` test for `/i18n.js` (200, correct content-type, requires no token — static is public like app.js).
- [ ] **Step 2: Run; fails** (file absent).
- [ ] **Step 3: Implement** i18n.js (start with ~12 chrome keys: nav.backup, nav.library, nav.history, nav.review (reserved), footer.safety, switcher.label, theme.toggle, quit.label, quit.confirm, toast.copied, toast.copy_failed, app.tagline — en + 3 translations), index.html switcher + script order, server `_STATIC`, css.
- [ ] **Step 4: Full suite green.**  - [ ] **Step 5: Commit** `feat(gui): i18n infrastructure + visible language switcher`

### Task 5: Full string extraction — app.js speaks four languages

**Files:** Modify: `markwell/gui/assets/app.js` (every user-visible literal → `t()`), `markwell/gui/assets/i18n.js` (all keys ×4 locales), `markwell/gui/assets/index.html` (static chrome via `data-i18n` + an applier in i18n.js)
**Test:** `tests/test_gui_i18n.py` parity tests (already enforce); add a regex guard test: `app.js` contains no English sentence literals in toast()/innerHTML template hot spots — pragmatic check: assert `t(` call count ≥ 60 in app.js.

- [ ] **Step 1:** Inventory every user-facing string in app.js (toasts, empty states, hero meta, search labels/aria, backup page copy, progress PHASES list, error-code → message map for `no_device/no_source/empty/schema/unreadable/unexpected` and phases `detecting/snapshotting/reading/rendering/done`, history rows, buttons, aria-labels, `document.title`). Build the error/phase translation maps keyed by backend codes (from Task 3). Date strings already via Intl.
- [ ] **Step 2:** Write keys into i18n.js (en first, then zh-TW/ja/ko — natural phrasing; e.g. en "No Kobo found. Plug it in with the USB cable and unlock it, then try again." → zh-TW 「找不到 Kobo。請用 USB 線接上並解鎖後再試一次。」). Re-render current view on `markwell:locale` event (call `route(false)` + re-apply `data-i18n` chrome).
- [ ] **Step 3: Run parity + t()-coverage tests; full suite green.** Manually sanity-load GUI once (`python3 -m markwell.gui --no-browser` + curl `/` 200).
- [ ] **Step 4: Commit** `feat(gui): full UI localization (en/zh-TW/ja/ko)`

**Phase 1 gate:** full suite green; GUI loads in zh-TW via switcher; exports from GUI carry localized labels. Code-review subagent pass on Phase 1 diff before Phase 2.

---

## Phase 2 — Export formats

### Task 6: CSV renderer

**Files:** Create `markwell/render/csv.py`; modify `markwell/export.py` (registry — see Task 9; for now just the module); Test: create `tests/test_render_csv.py`

**Contract:** `render(books, meta) -> {"highlights.csv": text}`. Text = `﻿` (BOM, so Excel opens CJK correctly) + RFC 4180 CSV via stdlib `csv` into `io.StringIO` with `lineterminator="\r\n"`. Header row (English identifiers, pinned): `title,author,chapter_index,date,text,note,volume_id`. One row per highlight; `note` empty string when None. No row limit.

- [ ] **Step 1: Failing tests:** output starts with BOM; header exact; row count = total highlights; a text containing `"`, `,`, newline is quoted/escaped per csv module; CJK text round-trips via `csv.reader(io.StringIO(out.lstrip("﻿")))`.
- [ ] **Step 2: Run; fails.**  - [ ] **Step 3: Implement** (~30 lines, mirror json.py docstring style).
- [ ] **Step 4: Suite green.**  - [ ] **Step 5: Commit** `feat(export): CSV renderer (UTF-8 BOM, RFC 4180)`

### Task 7: Anki TSV renderer

**Files:** Create `markwell/render/anki.py`; Test: create `tests/test_render_anki.py`

**Contract:** `render(books, meta) -> {"anki.tsv": text}`. First two lines exactly `#separator:tab` and `#html:false`. Then one line per highlight: `front \t back \t source` where front = highlight text; back = note or "" ; source = `f"{title} — {author}"` (author may be empty → just title). Fields must contain no tabs/newlines — guaranteed upstream by `reader._clean` (whitespace collapsed); renderer still defensively `.replace("\t", " ")`.

- [ ] **Step 1: Failing tests:** directives first; line count = 2 + highlights; tab count per line == 2; CJK preserved.
- [ ] **Step 2–5:** fail → implement → green → **Commit** `feat(export): Anki-importable TSV renderer`

### Task 8: Single-file HTML library renderer

**Files:** Create `markwell/render/html.py`; Test: create `tests/test_render_html.py`

**Contract:** `render(books, meta) -> {"library.html": text}`. One self-contained document: inline `<style>` only (visual language borrowed from the GUI: serif display titles, paper/ink palette, the `── 第N章 ──` chapter ornaments), **no `<script>`, no external URLs** (fonts = system stacks). Structure: header (localized index title via `labels.for_lang(meta.get("lang"))`, generated date, source name, total counts) → TOC (anchor links `#book-N`, title + author + count) → per-book sections (blockquote per highlight, note styled distinctly with localized note label, date small) → footer ("markwell vX · MIT"). ALL book text/notes/titles/authors through `html.escape()`. Print-friendly (`@media print` page-break before sections). `<html lang="{meta lang}">`.

- [ ] **Step 1: Failing tests:** contains `<style>` and not `<script>`; **no `http://`/`https://` substrings**; a malicious title `<img src=x onerror=alert(1)>` appears only escaped (`&lt;img`); zh-TW meta lang → 筆記： label + `lang="zh-TW"`; anchors resolve (every TOC href has matching id); ends with single trailing newline.
- [ ] **Step 2–5:** fail → implement → green → **Commit** `feat(export): self-contained printable HTML library`

### Task 9: Format registry + CLI comma-list + GUI format options

**Files:** Modify: `markwell/export.py` (FORMATS registry + `parse_formats`), `markwell/cli.py` (`--format`), `markwell/gui/service.py` (default GUI fmt), `markwell/gui/server.py` (validate fmt tokens from body), `markwell/gui/assets/app.js` + `index.html` + `i18n.js` (Backup "格式選項" disclosure: checkboxes md/json/html on, csv/anki off, one-line localized descriptions, persisted to localStorage), README.md usage block; Test: modify `tests/test_export.py`, `tests/test_cli.py`, `tests/test_gui.py`

**Contract:** `FORMATS = {"md": md_render.render, "json": json_render.render, "csv": csv_render.render, "anki": anki_render.render, "html": html_render.render}` (insertion order = output order). `parse_formats(spec: str | Iterable[str]) -> list[str]`: accepts "all" → all five; comma string "md,csv" (spaces tolerated, dedup, order = FORMATS order); iterable passthrough with validation; unknown id → `ValueError("unknown format: X (choose from md, json, csv, anki, html or all)")`. `build_files` calls it. CLI `--format` keeps argparse type=str, validated via parse_formats with exit 2 + the same message on error; default stays `"all"` (**now five formats — CHANGELOG-noted**). GUI default = `"md,json,html"` (server `--format` default changes; `/api/export` body fmt validated by parse_formats, invalid → 400 `{"error": "unknown format"}`).

- [ ] **Step 1: Failing tests:** parse_formats cases (all / comma / dedup / unknown raises); CLI `--format md,csv` writes exactly index.md+per-book md+highlights.csv and prunes others via manifest (existing manifest behavior — assert json absent after a md,csv run following an all run); GUI default fmt produces library.html but not anki.tsv; bad fmt POST → 400.
- [ ] **Step 2–5:** fail → implement (including the GUI disclosure UI with `t()` keys ×4 locales) → green → **Commit** `feat(export): format registry, comma-list --format, GUI format options`

**Phase 2 gate:** suite green; `markwell --db <fixture> --format all --lang zh-TW` writes 5 formats with localized md/html. Code-review pass.

---

## Phase 3 — Review view + share cards

### Task 10: Review view (今日一句 + 隨機複習)

**Files:** Modify: `markwell/gui/assets/app.js` (route `#/review`, nav item), `index.html` (nav entry), `i18n.js` (keys ×4), `style.css`; Test: `tests/test_gui_i18n.py` parity auto-covers; add static-route test only if new assets.

**Contract:** Route `#/review`: requires a library (else the existing empty-state pattern with sample CTA). Pool = all highlights with non-empty text (notes-only rows excluded from quotes). **Today's quote:** index = `djb2(dayKey + "|" + fingerprint) % pool.length` where `dayKey` = local `YYYY-MM-DD`, `fingerprint` = `${books.length}:${totalHighlights}`, djb2 pinned:

```js
function djb2(str) { let h = 5381; for (let i = 0; i < str.length; i++) { h = ((h << 5) + h + str.charCodeAt(i)) >>> 0; } return h; }
```

**Another (換一句):** uniform random over a shuffle-bag (no repeats until pool exhausted, then reshuffle; bag resets when filter changes). Book filter = `<select>` (All books + each title). Quote card shows text, note (if any, styled like book view), title — author, date; actions row: Copy (reuse `copyPayload`), Share card (opens Task 11 modal), Read in book (`jumpToHighlight`). All strings via `t()` ×4 locales. Daily quote stable across reloads same day (test by eye; logic is pure and tiny).

- [ ] **Steps:** implement → parity tests + suite green → manual load check → **Commit** `feat(gui): Review view — daily quote + shuffle + filters`

### Task 11: Canvas share-card generator

**Files:** Create: `markwell/gui/assets/cards.js`; Modify: `index.html` (script tag + modal container), `server.py` (`_STATIC` `/cards.js`), `app.js` (openCardModal(highlight, book) glue), `i18n.js` (keys ×4), `style.css` (modal); check `packaging/pyinstaller/markwell-desktop.spec` bundles `assets/*` by glob (it does — verify; if explicit list, add i18n.js/cards.js).
**Test:** static-route test for `/cards.js`; parity test auto-covers keys; canvas itself is browser-verified in Task 24 (Playwright screenshot).

**Contract (cards.js):**
- `SIZES = {square: [1080,1080], story: [1080,1920], wide: [1200,630]}`; `STYLES = {paper, ink, spotlight}` (paper: warm paper bg + ink text, ink: near-black bg + paper text, spotlight: deep-teal gradient + paper text — pull hex values from style.css custom properties to stay on-brand).
- `wrapQuote(ctx, text, maxWidth) -> string[]`: tokenize so CJK chars (regex `[　-鿿豈-﫿぀-ヿ가-힯]`) break anywhere; Latin runs break on spaces; measure via `ctx.measureText`.
- `fitFontSize(ctx, text, box) -> px`: binary search 18–72px so wrapped lines fit the content box (same spirit as the existing hero auto-fit).
- `drawCard(canvas, opts)` where opts = `{text, note, title, author, date, style, size, showNote, watermark, locale}`: bg → quote (auto-fit, hanging quote mark ornament) → optional note (smaller, distinct) → footer `title — author` → watermark bottom-right `Made with Markwell` 13px 40% opacity **only when `watermark` true (default true, toggle in modal)**. Long quotes: if even 18px overflows, hard-truncate with "…" and the modal shows a localized hint ("圖卡適合較短的佳句").
- Modal: live preview (canvas, re-drawn on any option change), size segmented control, style segmented control, note toggle (only when note exists), watermark toggle, actions: **Download PNG** (`canvas.toBlob` → `a[download=markwell-card.png]` + objectURL+revoke), **Copy image** (`navigator.clipboard.write([new ClipboardItem({"image/png": blob})])`, feature-detected, fallback toast pointing to Download), **Share** (`navigator.canShare({files})`-gated, hidden when unsupported). Esc/backdrop closes; focus-trapped (match existing a11y patterns).
- Fonts: same family stacks as style.css (system CJK). No CSP change needed (canvas + blob download don't hit CSP directives in use); if Copy fails in some browser, the toast fallback covers it.

- [ ] **Steps:** static test fails → implement → suite green → **Commit** `feat(gui): canvas share cards (3 sizes, 3 styles, CJK-aware)`

### Task 12: Card entry points everywhere they belong

**Files:** Modify: `markwell/gui/assets/app.js` — Share button beside the existing per-highlight Copy (book detail), on the hero quote, and in Review (Task 10 already wired); `i18n.js` aria/labels ×4.
- [ ] **Steps:** wire → parity + suite green → manual check all three entry points open the modal with the right quote → **Commit** `feat(gui): share-card entry points (book view, hero, review)`

**Phase 3 gate:** suite green; manual: zh-TW locale → Review → open card → download PNG works in Chromium (Playwright check acceptable). Code-review pass.

---

## Phase 4 — Cloud-folder backup & portability

### Task 13: Config module

**Files:** Create `markwell/config.py`; Test: create `tests/test_config.py`

**Contract:** `config_path() -> Path` = `Path(os.environ.get("MARKWELL_CONFIG_DIR", "~/.markwell")).expanduser() / "config.json"`. `load() -> dict` (missing/corrupt/non-dict → `{}`). `save(cfg: dict) -> None` (mkdir parents, write tmp + `os.replace` atomic, `ensure_ascii=False`, trailing newline). Only known key today: `"data_dir": str`.

- [ ] **Step 1: Failing tests:** round-trip; corrupt file → `{}`; missing → `{}`; env override respected (monkeypatch `MARKWELL_CONFIG_DIR` to tmp_path); atomicity (tmp file gone after save).
- [ ] **Step 2–5:** fail → implement (~40 lines) → green → **Commit** `feat: config module (~/.markwell/config.json)`

### Task 14: Service — cloud-root detection, data-dir change, ZIP archive

**Files:** Modify: `markwell/gui/service.py`; Test: create `tests/test_service_settings.py`, `tests/test_archive.py`

**Contract:**
- `detect_cloud_roots() -> list[dict]`: probe, per platform, **existing dirs only** → `[{"id": "icloud"|"dropbox"|"gdrive"|"onedrive", "label": "iCloud Drive"|"Dropbox"|"Google Drive"|"OneDrive", "path": str}]`. Probe lists (pinned): macOS — `~/Library/Mobile Documents/com~apple~CloudDocs`, `~/Dropbox`, `~/Library/CloudStorage/Dropbox*`(glob), `~/Library/CloudStorage/GoogleDrive*`, `~/Library/CloudStorage/OneDrive*`, `~/OneDrive`; Windows — `%USERPROFILE%/iCloudDrive`, `%USERPROFILE%/Dropbox`, env `OneDrive`, `%USERPROFILE%/Google Drive`; Linux — `~/Dropbox`, `~/GoogleDrive`, `~/OneDrive`. First match per id wins. Pure read-only probing.
- `change_data_dir(self, target: str | Path) -> dict`: refuse while a job is running (`RuntimeError("export running")` → server maps 409). Validation order (pinned): expanduser → must be absolute (`ValueError("path must be absolute")`) → `resolve()` → must not be an existing **file** → **must not be inside any Kobo mount**: for every root in `device._candidate_roots()` reject if `os.path.commonpath([resolved, root.resolve()]) == str(root.resolve())` (guard try/except ValueError for different drives) → mkdir(parents=True, exist_ok=True) → writability probe (`tempfile.TemporaryFile(dir=...)` try/except → `ValueError("not writable")`). Then **copy, never move**: every `backups/KoboReader-*.sqlite` → `<new>/backups/` (skip names already present), every file under `output/` → `<new>/output/` (same skip). Switch `self.data_dir/backup_dir/out_dir`, persist via `config.save({"data_dir": str(resolved)})`. Return `{"old": str, "new": str, "copied_snapshots": int, "copied_outputs": int}` — old data untouched.
- `make_archive(self) -> dict`: zip `output/**` (arcname `output/...`) + latest snapshot only (arcname `backups/<name>`) into `<data_dir>/Markwell-archive-<YYYYmmdd-HHMMSS>.zip` (ZIP_DEFLATED). Nothing to archive → `ValueError("nothing to archive")`. Returns `{"name", "path", "files": int}`.

- [ ] **Step 1: Failing tests** (use tmp_path service fixtures from conftest patterns): change copies & old files remain; refuses non-absolute, file target, path under a fake kobo root (monkeypatch `device._candidate_roots`), while running (set `_job.state="running"`); config written; archive zip contains output files + exactly one snapshot, named correctly; empty service → ValueError.
- [ ] **Step 2–5:** fail → implement → green → **Commit** `feat(gui): data-dir relocation (copy-only) + zip archive service`

### Task 15: Server endpoints for settings + archive

**Files:** Modify: `markwell/gui/server.py`; Test: create `tests/test_server_settings.py` (follow existing test_gui.py HTTP harness pattern)

**Contract:**
- `GET /api/settings` → `{"data_dir", "backup_dir", "output_dir", "cloud_roots": detect_cloud_roots(), "config_path": str}`.
- `POST /api/settings/data-dir` body `{"choice": "<id>"}` **or** `{"choice": "custom", "path": "<abs>"}`: choice id → that root's path + `/Markwell`; custom → the given path through full validation. Maps service errors: running → 409; ValueError → 400 with the message; success → the report dict. **Server-side: `default_data_dir()` is always offered client-side as "home" choice id too.**
- `POST /api/archive` → 200 report or 400 ("nothing to archive") / 409 (running). Token + Host rules identical to every `/api/*` (the existing decorators/checks path — no special-casing).
- Update module docstring + SECURITY.md note happens in Task 17.

- [ ] **Step 1: Failing tests:** no token → 403 (both new POSTs); unknown choice → 400; custom relative path → 400; happy path with tmp dirs → dirs switched (assert via follow-up `/api/settings`); archive 200 then file exists; archive while running → 409.
- [ ] **Step 2–5:** fail → implement → green → **Commit** `feat(gui): settings + archive endpoints (fenced path validation)`

### Task 16: Settings UI + archive button

**Files:** Modify: `app.js` (route `#/settings`, gear icon in topbar OR nav — **pinned: nav item, icon gear, label t("nav.settings")**), `index.html`, `i18n.js` (×4), `style.css`; History view gains "打包帶走" archive button.

**Contract:** Settings view: current folder card (path + Open folder button) → "Keep my library in a cloud folder" section: radio list of detected roots (one-click, shows resulting `<root>/Markwell` path) + Home default + Advanced disclosure with custom absolute-path text input → primary button "Move my library here" with confirm dialog that **states copy-not-move + where old data stays**; on success: localized report toast/panel (N snapshots, M files copied; old data still at X) + Open new folder button. Archive: button on History + Settings → success panel with file name + Open folder. All errors surface the localized message for the 400/409 codes. Every string `t()` ×4.

- [ ] **Steps:** implement → parity + suite green → manual zh-TW walkthrough with tmp data dir → **Commit** `feat(gui): Settings view — cloud folder flow + archive`

### Task 17: SECURITY.md update + adversarial review of the new surface

**Files:** Modify: `SECURITY.md`, `markwell/gui/server.py` docstring; no behavior change expected unless findings.

- [ ] **Step 1:** SECURITY.md: amend "Nothing the browser sends is used as a filesystem path" to document the single fenced exception (settings data-dir), its validation chain, copy-only semantics, and the config file location. Honest, specific.
- [ ] **Step 2 (red-team, fresh subagent):** adversarially attack Task 14/15 code: `..` traversal, symlinked targets (resolve() handles — verify), Windows UNC/drive edge (`commonpath` ValueError guard), writing into a mounted Kobo via symlink inside a cloud root, TOCTOU between validate and copy, huge-output copy DoS (acceptable: user-initiated, local), config poisoning (`config.json` with path into Kobo mount → **load-time validation too**: server start must re-validate config data_dir with the same fence, falling back to default + stderr warning). Fix every confirmed finding with tests.
- [ ] **Step 3:** suite green → **Commit** `docs(security)+fix: document fenced data-dir exception; harden per red-team`

**Phase 4 gate:** suite green; config load-fence test exists; code-review pass.

---

## Phase 5 — OSS launch pack

### Task 18: Version 0.2.0, CHANGELOG, CONTRIBUTING, in-app About

**Files:** Modify: `markwell/__init__.py` (`__version__ = "0.2.0"`), `pyproject.toml`, `CHANGELOG.md` (move Unreleased → `## [0.2.0] - 2026-06-XX` with all phase entries; new Unreleased stub), `CONTRIBUTING.md` (+ i18n rules: every UI string through `t()`, locale files key-parity enforced by test, en is canonical; + renderer how-to: pure render(books, meta), register in FORMATS, BOM/escaping notes), `app.js`/`index.html`/`i18n.js` footer About line (version · open source · MIT · GitHub link `https://github.com/ceparadise168/markwell` — user-initiated link only).
- [ ] **Steps:** implement → suite green (test_package version assertions — check `tests/test_package.py` expectations) → **Commit** `chore: 0.2.0 — changelog, contributing (i18n/renderer rules), in-app About`

### Task 19: Issue forms + PR template

**Files:** Create `.github/ISSUE_TEMPLATE/bug_report.yml`, `.github/ISSUE_TEMPLATE/schema_report.yml`, `.github/ISSUE_TEMPLATE/feature_request.yml`, `.github/ISSUE_TEMPLATE/config.yml` (blank_issues_enabled: false, contact link → Discussions if enabled later, else docs), `.github/PULL_REQUEST_TEMPLATE.md`.

**Contract:** bug_report: dropdown OS, input `markwell --version` output, input Kobo model + firmware (Settings → Device information), textarea steps, checkbox "I removed personal data from any logs/screenshots". schema_report (the #1 expected class): explains exit code 4 / "newer Kobo than Markwell knows", asks firmware version + model + **the error text only** (explicitly: do NOT attach KoboReader.sqlite — it contains your reading data; maintainer may follow up with safe queries). feature_request: problem/solution/alternatives. PR template: checklist of the non-negotiables (stdlib-only, never writes to device, no network, reader.py only schema module, renderers pure, tests added, locales key-parity green). All English (GitHub UI standard), one zh-TW courtesy line on top of each: 「可以用中文回報，沒問題。」(+ja/ko equivalents).
- [ ] **Steps:** create → `python3 -c "import yaml"`? **No** — pyyaml isn't stdlib; validate YAML by GitHub's schema knowledge + careful syntax; suite green (untouched) → **Commit** `docs(github): issue forms (incl. schema reports) + PR template`

### Task 20: Release + PyPI workflows

**Files:** Create `.github/workflows/release.yml`, `.github/workflows/publish-pypi.yml`; modify `packaging/README.md` (how releases run + Eric's one-time PyPI trusted-publisher setup note).

**Contract:** `release.yml`: `on: push: tags: ["v*"]` + `workflow_dispatch`. Matrix `[macos-latest, windows-latest]`: setup Python 3.13 → `pip install -e ".[release]"` → `pyinstaller packaging/pyinstaller/markwell-desktop.spec` → **`python packaging/preflight.py dist` (hard gate)** → zip/rename per platform (`Markwell-macOS.zip` containing the .app, `Markwell-Windows.zip` containing the exe dir — match what the spec emits; inspect the spec in-task) → `softprops/action-gh-release@v2` draft release attach. `publish-pypi.yml`: `on: release: types [published]`; build sdist+wheel (`python -m build` via pipx in CI), `pypa/gh-action-pypi-publish@release/v1` with `permissions: id-token: write` (Trusted Publishing — no secrets; packaging/README documents the one-time PyPI-side registration Eric does).
- [ ] **Steps:** write → `gh workflow view` not available pre-push; validate by careful review + actionlint if available locally (`command -v actionlint || true`) → suite green → **Commit** `ci: tag-triggered release build (preflight-gated) + PyPI trusted publishing`

### Task 21: READMEs ×4 + cloud-backup guides ×4 + maintainer docs

**Files:** Modify `README.md`; Create `README.zh-TW.md`, `README.ja.md`, `README.ko.md`, `docs/cloud-backup.md`, `docs/cloud-backup.zh-TW.md`, `docs/cloud-backup.ja.md`, `docs/cloud-backup.ko.md`, `docs/maintainer-stats.md`.

**Contract:** README.md top: language line `**English** · [中文（台灣）](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md)` + badges (CI status, `https://img.shields.io/github/downloads/ceparadise168/markwell/total`, `https://img.shields.io/pypi/v/markwell` + `pypi/dm` once published) + refreshed feature list (5 formats, Review, share cards, cloud folder, 4 languages) + download section FIRST (desktop zips from latest release + "how to open unsigned app" per OS) + pipx for developers + **Maintainer section**: "Built and maintained by Eric Tu ([@ceparadise168](https://github.com/ceparadise168)) — ceparadise168@gmail.com. No donations — if Markwell helped you, star the repo and share a card." Translations: full, natural, not literal; usage/CLI blocks stay English commands with localized prose. cloud-backup guides: per-provider steps (iCloud/Dropbox/Google Drive/OneDrive) using the Settings flow + "new computer restore" walkthrough. maintainer-stats.md: the exact commands —

```bash
gh api repos/ceparadise168/markwell/releases --jq '.[].assets[] | [.name, .download_count] | @tsv'
pipx run pypistats recent markwell
```

plus Cloudflare Web Analytics dashboard pointer.
- [ ] **Steps:** write (en canonical first, then 3 translations — translation quality bar: a native reader should not detect machine flavor) → cross-link check (every file links the other three) → suite green → **Commit** `docs: four-language READMEs, cloud guides, maintainer stats`

### Task 22: Screenshot refresh (Playwright)

**Files:** Replace/add under `docs/screenshots/` (en set refresh + `zh-tw/` subset: library, book detail, review, share-card modal, settings).
- [ ] **Steps:** `python3 -m markwell.gui --no-browser --data-dir <tmp>` → Playwright MCP: sample library, capture the matrix at 1280×860 light theme (+1 dark) per existing naming; zh-TW captures via switcher → optimize PNGs if `pngquant` absent skip → update README image refs → **Commit** `docs: refresh screenshots (en + zh-TW, new views)`

**Phase 5 gate:** suite green on CI matrix locally simulated (`python3 -m pytest -q` on 3.9 if available via `uv python` else note), preflight on a real local PyInstaller build run once macOS-side. Code-review pass.

---

## Phase 6 — Landing site (Cloudflare Pages)

### Task 23: Static site ×4 locales + deploy guide

**Files:** Create `site/index.html` (en), `site/zh-tw/index.html`, `site/ja/index.html`, `site/ko/index.html`, `site/site.css`, `site/_headers`, `site/DEPLOY.md`; reuse `docs/screenshots/*` copies under `site/img/` (only sample-data shots).

**Contract:** Per page: hero (app name, one-line promise, the three trust statements: No cloud · No account · Never writes to your Kobo — localized), 2–3 screenshots, download buttons → `https://github.com/ceparadise168/markwell/releases/latest/download/Markwell-macOS.zip` / `Markwell-Windows.zip` (names must match Task 20 artifacts), "prefer the command line? `pipx install markwell`", unsigned-app how-to (collapsible per OS), FAQ links to GitHub issues/schema form, footer: maintainer contact + GitHub + MIT. Visible language switcher (plain links ×4) top-right. OG tags (title/description/image per locale, image = library screenshot absolute path placeholder `https://MARKWELL_SITE_ORIGIN/img/og.png`), `canonical`/`hreflang` blocks present with `MARKWELL_SITE_ORIGIN` placeholder. `_headers`: `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, basic CSP for a static page. No JS at all (pure HTML/CSS — switcher is links). DEPLOY.md: ① Cloudflare Pages → connect repo, build command none, output dir `site/` ② attach custom domain ③ search-replace `MARKWELL_SITE_ORIGIN` → real origin (one sed line provided) ④ toggle Web Analytics ⑤ verify download links after first public release exists. Steps ①②④ are Eric's (his Cloudflare account).
- [ ] **Steps:** build pages (shared CSS, visual language = product: paper/ink/teal) → `python3 -m http.server -d site` manual look ×4 locales → suite green (untouched) → **Commit** `feat(site): four-language landing site + Cloudflare Pages deploy guide`

---

## Final verification — Task 24 (no new code)

- [ ] Full suite green; run once with `-p no:cacheprovider` clean.
- [ ] `python3 packaging/preflight.py dist` against a fresh local PyInstaller build → OK.
- [ ] Playwright manual matrix: each locale (en/zh-TW/ja/ko): backup page copy, library + search, review + card download, settings flow, history archive — no English leakage in any non-en locale (grep the DOM text for sentinel English strings).
- [ ] Spec-vs-reality audit: walk `2026-06-11-community-release-design.md` §3 bullet-by-bullet; list any drift; fix or document.
- [ ] `git log --all --name-only --diff-filter=A | grep -iE "\.kobo/|^output/|^backups/|\.sqlite"` still clean.
- [ ] Summarize for Eric: what shipped, what is one-button (flip public, tag v0.2.0, PyPI trusted-publisher registration, Cloudflare Pages connect + domain + analytics), download-stats how-to.

**Explicitly Eric-manual (never executed by agents):** repo → public; `git push`; creating the GitHub release tag; PyPI publisher registration; Cloudflare Pages project/domain/analytics; any announcement posts.
