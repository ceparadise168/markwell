# Markwell Community Release — Design

Date: 2026-06-11
Status: **blessed by Eric 2026-06-11** (with amendments: unsigned launch; no
donations until real costs appear, but track downloads and keep maintainer
contact visible; watermark default-on; no zh-CN; NEW landing site on Eric's
Cloudflare domain — see §3.7 and §6)
Scope: turn Markwell from a polished private tool into a launchable open-source
product for the global Kobo community (zh-TW / ja / ko / en, mostly
non-technical), with multi-format export, cloud-folder backup, share cards,
and quote review — all with zero paid third-party APIs and zero new runtime
dependencies.

---

## 1. Review findings (current state)

**What is genuinely strong (keep, do not touch):**

- Safe core is excellent: zero-touch device reads (file-copy + WAL replay,
  never an SQLite handle on the device), verified snapshots, atomic writes,
  manifest-based pruning that never deletes user-authored files.
- Architecture invariants are clean and documented: `reader.py` is the only
  schema-aware module; `model.py` is the stable representation; renderers are
  pure `{filename: content}`; CLI/GUI share one export layer.
- GUI security posture is far above typical local-server apps: 127.0.0.1 only,
  per-launch token, Host allow-list, CSP, no CORS, body caps, no
  browser-supplied paths.
- 79 tests green; CI on 3 OS × 3 Python; release privacy preflight exists;
  git history contains no private data (verified 2026-06-11).
- The GUI design is calm and book-like, and CJK already renders beautifully.

**Brutal-honest gaps versus the stated goal:**

1. **The product is English-only while the target audience is mostly CJK and
   non-technical.** Every GUI string, every backend status message, every
   export label (`note:`, `Kobo Highlights`, index table headers), dates
   (`Jun 1, 2026 · 4:01 PM`), and the README are English. This is the single
   biggest contradiction in the project today.
2. **It is not actually open-source yet.** The repo is private; `feat/gui`
   (10 commits, including the entire GUI) has never been pushed. Community
   value today: zero.
3. **"Own your reading assets" is only half-delivered.** md + json covers
   Obsidian/scripts. There is no CSV (Excel/Notion people), no Anki path
   (spaced-repetition readers — a huge overlap with "review quotes"), no
   single-file HTML (the "carry/share my whole library" artifact).
4. **No cloud story.** Non-technical users lose laptops. The free,
   no-API answer (data dir inside iCloud/Dropbox/Drive sync folder) needs a
   first-class, guided UX — today `--data-dir` is a CLI flag they will never
   find.
5. **No share/review loop.** The hero quote in Library is a seed of it, but
   there is no quote-card generator and no dedicated review surface. These are
   the features that make a community tool spread.
6. **Launch infrastructure missing:** no issue templates (schema reports are
   the #1 expected issue class), no FUNDING, no release/PyPI workflow, no
   localized READMEs, sample 道德經 chapters render out of order (78 → 64).
7. **Unsigned binaries** will trigger Gatekeeper/SmartScreen warnings at
   exactly the non-technical audience we target (decision for Eric, §6).

---

## 2. Goal & non-goals

**Goal:** a Kobo reader in Taipei, Tokyo, Seoul, or Toronto — who has never
opened a terminal — can download Markwell, see it in their language, back up
their highlights safely, read/search/review them, export to the formats their
tools speak, keep everything synced in their own cloud folder, and share a
beautiful quote card — all offline, free, no account.

**Non-goals (v1, explicit):**

- Push notifications (Eric deferred to a later phase).
- OAuth/WebDAV cloud APIs, any network connection at runtime (invariant).
- CLI message i18n (CLI audience is technical; exports themselves ARE
  localized — that is what non-technical users see).
- `.apkg` builder, EPUB export, auto-update, telemetry (never), zh-CN README
  (cheap to add on request — see §6).
- Buying code-signing certs (decided: launch unsigned, revisit at traction).
- Donations (decided: none until real costs — server or signing fees —
  appear; no FUNDING.yml now, per "don't add what hasn't happened").

---

## 3. Design

### 3.1 i18n architecture (Phase 1)

Principle: **backend produces data and stable codes; the frontend owns all
presentation.** This sharpens an existing boundary instead of inventing one.

- **Locales:** `en`, `zh-TW`, `ja`, `ko`. Auto-detect from
  `navigator.language` (region-aware, fallback chain → `en`), persist override
  in `localStorage`, and a **persistent, visible language switcher in the
  topbar** (native names: 中文（台灣）/ 日本語 / 한국어 / English) — per the
  "exploration controls stay visible" convention.
- **Frontend:** one hand-written `assets/i18n.js` (no build step): locale
  dictionaries + `t(key, params)`; `document.documentElement.lang` follows the
  active locale; dates/relative ages via `Intl.DateTimeFormat` /
  `Intl.RelativeTimeFormat` (free, correct, per-locale).
- **Backend de-Englishing:** `snapshot_list()` returns `name`, `stamp`
  (ISO 8601 or null), `size_bytes`, `is_latest` — the GUI formats. Export-job
  responses keep stable `phase`/`error` codes (already exist); the GUI
  translates codes; the English `message` remains only as a fallback for
  `unexpected` errors. `/api/*` is a private same-version contract
  (token-gated), so this is a clean break, not an API break. **The
  `markwell/1` JSON export schema is untouched.**
- **Localized exports:** Markdown + HTML renderers take an optional
  `meta["lang"]` and localize *labels only* (`note:` → `筆記：`, index title,
  table headers, "Generated"). Highlight text is always verbatim. GUI passes
  its locale; CLI gains `--lang` (default `en`). CSV/TSV/JSON headers and keys
  stay English — they are machine-facing identifiers (Notion/Anki field
  mapping breaks if translated); rationale documented in README.
- **Sample library:** add one Japanese and one Korean public-domain book —
  夏目漱石《草枕》(d. 1916) and 김소월《진달래꽃》(pub. 1925, d. 1934) — both
  safely public domain worldwide, so every target-language reader sees their
  own script on first launch. Fix 道德經 chapter order (64 before 78).

### 3.2 Export formats (Phase 2)

New pure renderers, same contract (`render(books, meta) -> {filename: content}`):

- **`render/csv.py` → `highlights.csv`** — RFC 4180, one row per highlight
  (`title, author, chapter_index, date, text, note, volume_id`), **UTF-8 with
  BOM** so Excel opens CJK correctly (the #1 trap for our audience). Formula
  injection stays handled per the existing documented stance (verbatim data +
  SECURITY.md caveat).
- **`render/anki.py` → `anki.tsv`** — Anki file-header directives
  (`#separator:tab`, `#html:false`, `#columns:…`) so import is two clicks:
  front = highlight, back = note, source = "title — author". A short
  per-locale how-to in the docs.
- **`render/html.py` → `library.html`** — one self-contained, printable,
  no-JS HTML file of the whole library (inline CSS reusing the app's visual
  tokens, localized labels). This is the "carry / share / print my corpus"
  artifact and works forever, everywhere, offline.
- **Plumbing:** `export.FORMATS` registry; `build_files()` accepts a list of
  format ids; CLI `--format` accepts a comma list (`md,csv`); `all` now means
  all five (CHANGELOG-noted, pre-1.0). GUI Backup gains a format options
  disclosure: default checked **md + json + html**; csv + anki opt-in with
  one-line descriptions (keeps the default output folder un-cluttered for
  non-technical users while making power formats discoverable).

### 3.3 Review view — 隨機複習 (Phase 3)

New top-level nav item **Review**: a calm daily-quote surface.

- **Today's quote:** deterministic pick seeded by (local date + library
  fingerprint) — stable all day, changes tomorrow.
- **"Another" shuffle** (no repeats until the pool is exhausted), optional
  filter by book.
- Per-quote actions: Copy · Share card (§3.4) · "Read in book" (reuses the
  existing `jumpToHighlight` deep-link).
- Empty states reuse the sample-library pattern. **No streaks, no
  gamification** — this product is calm on purpose.

### 3.4 Share cards (Phase 3)

Fully client-side via Canvas 2D — zero Python deps, zero new attack surface,
works offline:

- Entry points: Review view, book-detail highlights, hero.
- Modal with live preview; options: **size** (1:1 1080², 9:16 1080×1920,
  16:9 1200×630), **style** (Paper / Ink / Spotlight — mirroring app themes),
  include-note toggle, watermark toggle (default per Eric, §6).
- Typography: auto-fit font size (binary search, like the existing hero);
  CJK-aware wrapping (break-anywhere for CJK runs, word-boundary for Latin);
  footer "書名 — 作者"; graceful cap for very long quotes (cards are for
  名言佳句, the UI says so).
- Output: **Download PNG** + **Copy image** (ClipboardItem) +
  `navigator.share` where available. System CJK font stacks (no bundled
  fonts; keeps artifacts small).

### 3.5 Cloud-folder backup & portability (Phase 4)

The free, no-API, non-technical answer: **put the Markwell folder inside the
cloud folder you already have.**

- New **Settings** surface showing the current data folder, with a guided
  "Keep my library in a cloud folder" flow: the backend probes (read-only)
  for existing sync roots — iCloud Drive, Dropbox, Google Drive, OneDrive
  (macOS `~/Library/CloudStorage/*` + classic paths; Windows env-var paths;
  Linux equivalents) — and offers the ones found as **one-click choices**
  (target becomes `<cloud>/Markwell`), plus an advanced free-path field.
- On change: **copy** snapshots + outputs to the new location (never
  move/delete; report what was copied and where the old data still lives),
  persist to `~/.markwell/config.json` (`--data-dir` flag > config > default),
  switch the live service, reveal the new folder.
- **Security note (the one deliberate invariant change):** today "nothing the
  browser sends is used as a filesystem path". Settings introduces exactly one
  fenced exception: the data-dir endpoint prefers server-offered tokens (no
  free path at all), and a free path is absolute-resolved, validated
  (exists/creatable, writable, **never inside a Kobo mount**, never a file),
  and used only to create the dir and copy Markwell's own files into it.
  SECURITY.md documents this honestly. This is the highest-risk item in the
  plan and gets a dedicated adversarial review pass in execution.
- **ZIP archive:** one click → `Markwell-archive-<stamp>.zip` (exports + the
  latest snapshot; not all history, for size) written into the data dir +
  revealed — the ad-hoc "take everything with me" path.
- `docs/cloud-backup.md` guide (all four locales): iCloud / Dropbox / Google
  Drive / OneDrive, with the "restore on a new computer" story.

### 3.6 Open-source launch pack (Phase 5)

- **READMEs:** `README.md` (en, canonical) + `README.zh-TW.md` +
  `README.ja.md` + `README.ko.md`, cross-linked at the top; refreshed
  screenshots (Review + share card + settings); trust copy per the existing
  distribution plan ("No cloud. No account. Never writes to your Kobo.");
  **download-count badges** (shields.io GitHub-releases total + PyPI monthly)
  as public, verifiable adoption proof; a **Maintainer section** with Eric's
  contact (GitHub @ceparadise168 + email) — donations deliberately absent
  until real costs appear.
- **Download stats (no telemetry, ever):** the app stays zero-network. Counts
  come from sources that exist anyway — GitHub Releases per-asset
  `download_count` (landing-page buttons deep-link release assets, so every
  download is counted), PyPI public stats (pypistats), and Cloudflare Web
  Analytics (cookieless, dashboard toggle) for site visits. A short
  `docs/maintainer-stats.md` records the `gh api` / pypistats one-liners so
  the numbers are always one command away.
- **.github/:** issue forms — bug report (asks OS, `markwell --version`, Kobo
  firmware), **dedicated "unsupported schema" report form** (our #1 expected
  community issue; asks for firmware version + the preflight-safe details we
  need), feature request; PR template (reminds of the non-negotiable
  invariants). No FUNDING.yml for now (decided).
- **In-app About:** the GUI footer gains a tiny About line — version, "open
  source · MIT", maintainer link to the site/GitHub. User-initiated links
  only; the app still never makes a network request itself.
- **Workflows:** `release.yml` — on tag: build PyInstaller artifacts
  (macOS + Windows), **run the privacy preflight as a hard gate**, attach to a
  draft GitHub Release; `publish-pypi.yml` — PyPI Trusted Publishing (free, no
  long-lived secrets).
- **Housekeeping:** CHANGELOG entries; version → `0.2.0`; CONTRIBUTING gains
  the i18n string rules (every UI string goes through `t()`; locale files must
  stay in sync) and renderer-registry how-to.
- **Final verification:** full test suite, preflight on a real build, GUI
  manual pass in all four locales, security re-review of the settings
  endpoint, screenshots refresh.

**Going public (repo flip, PyPI publish, community announcements) stays a
manual Eric action** — outward-facing and irreversible; everything will be
ready so it is one button.

### 3.7 Landing site — Cloudflare Pages (Phase 6)

Most non-technical readers will never visit a GitHub repo. A small static
site is the front door; Eric already has a Cloudflare domain + hosting.

- **Tech:** hand-written static HTML/CSS in `site/` in this repo (no
  framework, no build step — same philosophy as the GUI assets, shares its
  visual language). Cloudflare Pages serves the directory as-is.
- **Content (per locale — `/` en, `/zh-tw/`, `/ja/`, `/ko/`):** hero with the
  one-line promise in the reader's language; the three trust statements; 2–3
  screenshots (library, book view, share card); **download buttons
  deep-linking GitHub `releases/latest/download/<asset>`** (auto-newest, and
  every click lands in GitHub's download counts); a "prefer
  pipx/PyPI?" line for technical users; per-OS "how to open an unsigned app"
  note; footer with maintainer contact + GitHub link. Visible language
  switcher on every page (same convention as the app).
- **Analytics:** Cloudflare Web Analytics — cookieless, GDPR-clean, enabled
  by a dashboard toggle (zero code in v1; CF injects the beacon for Pages).
- **SEO niceties:** OG/social-preview tags ship; `canonical`/`hreflang` are
  included with the final origin filled in at deploy (deploy guide step,
  since the exact domain is Eric's to connect).
- **Deploy guide:** `site/DEPLOY.md` — connect repo to Cloudflare Pages
  (output dir `site/`), attach the domain, flip on Web Analytics. **Creating
  the Pages project, attaching the domain, and enabling analytics are Eric's
  manual steps** (his Cloudflare account); everything else is committed and
  ready.

---

## 4. Five-lens design pass

**Product.** The wedge sharpens from "backup tool" to "the safe, beautiful,
local home for your Kobo reading assets — in your language". Readwise charges
monthly and speaks English; Markwell is free, local, CJK-first. Every Phase
1–4 feature serves the same loop: own it (backup) → use it (read/search/
review/export) → spread it (cards, localized READMEs). No feature requires a
server, an account, or an API key.

**Ops.** Zero new runtime dependencies (canvas work is the browser's; zip and
csv are stdlib). No services to run. GitHub Actions free tier covers CI +
releases. Support load is shaped by the schema-report issue form (turns "it
broke" into actionable firmware reports). The preflight hard-gates private
data out of artifacts. Risk concentration: the settings endpoint (§3.5) —
mitigated by token-choice-first design + dedicated red-team pass.

**UX.** Non-technical CJK users get: their language on first launch
(auto-detect + visible switcher), a curated default export set, cloud backup
as "pick the folder you already have" (one click when detected), share/review
as joy not chores, and not a single destructive operation anywhere (changing
data dir copies, never moves; archives add, never replace). Error language
stays human ("Plug in the Kobo with the USB cable and unlock it") — now in
four languages.

**Architecture.** All existing invariants survive untouched: reader stays the
only schema-aware module; renderers stay pure (three new ones join two);
CLI/GUI keep sharing one export layer; the JSON schema contract is unchanged.
The i18n move *strengthens* the layering (backend → data/codes, frontend →
presentation). Exactly one invariant is consciously amended (browser-supplied
data-dir) with a fenced, validated, documented design. Stdlib-only holds.

**Business.** Cost to run: $0 (no paid APIs; Cloudflare Pages and GitHub
Actions free tiers). Growth loop: share-card watermark + four-language
READMEs + PyPI discoverability + a real front-door site on Eric's domain.
No donations until real costs appear (decided); the asset being built instead
is a **publicly verifiable maintainer track record** — download badges,
release history, community issue handling — with Eric's contact on every
surface. Launch does not wait on code signing (decided: unsigned).

---

## 5. Execution plan (sub-agents)

Per Eric: implementation via sub-agents on **Fable 5, max effort**, after
bless. Each task = TDD (tests first where testable), minimal diffs, code
review between tasks, full suite green before the next phase. Phases are
sequential (later UI strings depend on the i18n system); tasks within a phase
parallelize where independent.

| Phase | Tasks | Key risk watched |
|---|---|---|
| 1 i18n | backend data-shape; i18n.js + switcher; localized md/html labels + `--lang`; sample ja/ko + 道德經 order fix | locale dict drift → CONTRIBUTING rule + test that locales share keys |
| 2 formats | csv; anki tsv; html renderer; format registry + CLI/GUI plumbing | Excel CJK (BOM test); `all` semantics change documented |
| 3 review + cards | Review view; canvas card generator + CJK wrapping; entry points | long-quote layout; clipboard API fallbacks |
| 4 cloud + portability | settings + data-dir flow + config; zip archive; cloud guide ×4 locales | the fenced path-validation endpoint (adversarial pass) |
| 5 launch pack | READMEs ×4 + badges + maintainer contact; issue forms/PR template; release + PyPI workflows; maintainer-stats doc; in-app About; CHANGELOG + 0.2.0; final verification | preflight gate wired into release; screenshots current |
| 6 landing site | `site/` static pages ×4 locales; download deep-links; OG tags; DEPLOY.md for Cloudflare Pages | copy parity across locales; unsigned-app guidance per OS |

Done means: suite green on CI matrix, preflight clean on a real artifact,
manual GUI pass in 4 locales, all docs cross-linked, site ready to connect,
repo one-button-ready for Eric to flip public.

---

## 6. Decisions — resolved by Eric, 2026-06-11

1. **Code signing: launch unsigned.** Per-locale "how to open" instructions
   ship (right-click → Open / SmartScreen → More info → Run anyway); revisit
   when traction justifies the cost. pipx/PyPI path unaffected.
2. **Donations: not now.** No FUNDING.yml, no donate UI. Open it only when
   real costs (server, signing fees) appear. Instead: **download counts are
   tracked** (GitHub Releases asset counts + PyPI stats + Cloudflare Web
   Analytics — all free, none of them telemetry in the app) as the public
   record of the project's reach, and **maintainer contact stays visible**
   (README Maintainer section, site footer, in-app About).
3. **Share-card watermark: default ON** (small "Made with Markwell"), 
   one-click off.
4. **zh-CN: not in v1.** zh-TW first; the i18n system makes zh-CN a
   dictionary-file PR when the community asks.
5. **Landing site: yes** (Eric's amendment) — static site in `site/`,
   deployed on Eric's Cloudflare domain via Pages; Pages project + domain
   attach + analytics toggle are Eric's manual steps.
