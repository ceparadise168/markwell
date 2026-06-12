# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-12

### Changed

- **Renamed the project `kobo-backup` → Markwell** (the CLI, package, and module
  are now `markwell`).
- **Snapshots are now a true zero-touch file copy of the device database.** The
  device DB is only ever read; nothing — not even SQLite housekeeping — writes to
  the device, so "Never writes to your device" is now literally true.
- **Highlights are now emitted in true spine reading order** rather than the
  database's row order.
- **Dates are rendered in your local time zone** instead of raw UTC.
- **Status and progress messages now go to stderr;** the exported data and JSON
  go to files. This keeps `--format json` pipelines clean.
- **`--device` is now assertive:** when given, it is used as specified instead of
  being treated as a hint alongside auto-detection.
- **`output/` is documented as relative to the current working directory,** and
  the tool prints the **absolute path** of the output directory on success.
- **`--format all` now means all five formats** (`md`, `json`, `csv`, `anki`,
  `html`), in the format registry's canonical order.
- **The GUI's default export selection is now `md,json,html`** (it was `all`,
  which at the time meant Markdown + JSON).
- **The GUI backend now emits raw data and message codes; the browser owns all
  presentation.** Dates, relative ages, and sizes are formatted in the reader's
  locale, and the snapshot-list payload shape changed accordingly (`stamp` is
  an ISO 8601 timestamp, or `null` when the filename carries none, instead of
  pre-formatted English text).
- **The sample 道德經 book's highlights now follow chapter order.**

### Added

- **A graphical app (`markwell-gui` / `python -m markwell.gui`).** A local,
  offline web app for non-technical readers to safely **back up**, **read &
  search**, and **manage** their Kobo highlights — no terminal, no learning curve.
  It reuses the same safe core (never writes to the device) and adds zero runtime
  dependencies (Python standard library + hand-written HTML/CSS/JS). Hardened to
  stay local: binds `127.0.0.1` only, requires a per-launch token on every
  request, allow-lists the `Host` header, sends a Content-Security-Policy, and
  makes no network connections (see `SECURITY.md`).
- **Full GUI localization — English, 繁體中文, 日本語, 한국어.** Every string in
  the interface goes through the locale dictionary, and a language switcher
  sits in the sidebar; the choice persists across sessions.
- **Localized export labels and a CLI `--lang` flag** (`en`, `zh-TW`, `ja`,
  `ko`). The scaffolding of Markdown and HTML exports — titles, counts, table
  headers — is written in the chosen language (the GUI passes your interface
  language automatically); your highlight and note text is always verbatim,
  never translated.
- **Three new export formats behind a format registry:** **CSV** (UTF-8 BOM,
  RFC 4180), **Anki-importable TSV**, and a **self-contained printable HTML
  library**. `--format` now also accepts a comma list (`md,csv`), and the GUI
  grew matching per-format options.
- **Review view** — a daily quote drawn from your own highlights, with shuffle
  and a per-book filter.
- **Share cards** — turn a highlight into an image from the book view or the
  hero quote: three sizes, three styles, CJK-aware typography, and a watermark
  toggle. Cards are drawn on a local canvas; nothing leaves your machine.
- **Settings view: move your library into a cloud-synced folder** — a guided,
  copy-only relocation (the old folder is never deleted) — plus a one-click ZIP
  archive of all your data. The chosen location persists in
  `~/.markwell/config.json`.
- **Japanese and Korean sample books** (草枕 and 진달래꽃) join the built-in
  sample library.
- **`--require-device` flag** — fail instead of silently falling back to the
  latest local snapshot when no device is connected.
- **`--debug` flag** — show full tracebacks on error.
- **`--version` flag** — print the version and exit.
- **Distinct exit codes** — `0` success, `2` no device/source, `3` no highlights,
  `4` unreadable or unsupported schema.
- **JSON `source_freshness` field** — `"device"` for a snapshot taken this run,
  `"cached_snapshot"` for a reused local snapshot, signalling stale exports.
- **JSON `generator` field** — `"markwell/<version>"`, identifying the producing
  tool and version.
- **Schema-stability contract** in the docs — `schema` is `markwell/<MAJOR>`,
  additive-only within a major, and consumers must ignore unknown fields.
- **Schema-error handling** — an unreadable or unsupported source DB now fails
  cleanly with exit code `4` instead of an opaque traceback.
- Project docs: `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`, and a GitHub
  Actions CI workflow.

### Security

- **The data directory chosen in Settings is fenced.** A custom location is
  fully validated before use and re-validated on every boot; if the saved
  choice has become unsafe, Markwell warns on stderr and falls back to the
  default.
- **Symlinks are never followed** when copying your library or building a ZIP
  archive, and archives are written atomically — a half-written archive can
  never be picked up by a cloud-sync client.
- Expanded `SECURITY.md` to document the data-dir fence and the archive
  behavior.

[Unreleased]: https://github.com/ceparadise168/markwell/commits/main
[0.2.0]: https://github.com/ceparadise168/markwell/releases/tag/v0.2.0
