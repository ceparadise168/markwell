# kobo-backup — Design Spec

- **Date:** 2026-06-01
- **Status:** Approved (design); pending implementation plan
- **Author:** Eric (with Claude)
- **Name:** `kobo-backup` (package import: `kobo_backup`)
- **License:** MIT

## 1. Context

A working personal tool already exists in this directory: `kobo_highlights.py` (single file, ~300 lines, stdlib-only). It:

- Takes a **consistent, read-only snapshot** of the Kobo device's `KoboReader.sqlite` using SQLite's online-backup API (touches the device once, never writes to it; timestamped, never-overwritten backups; atomic `.tmp`→rename).
- Exports per-book Markdown in reading order + an `index.md`.
- Has zero third-party dependencies.
- Currently produces 926 highlights across 14 books.

The goal is to generalize this into a **polished open-source tool for Kobo owners**, without losing the qualities that make the current tool good (the safety model, the clean exports, zero dependencies).

This is **not greenfield** — the design builds *from* the existing script, preserving its crown jewel (the snapshot safety model) and extending reach + outputs.

## 2. Decisions (locked during brainstorming)

| Axis | Decision | Rationale |
|---|---|---|
| Wedge | **Kobo-only**, polished OSS | Tightest shippable wedge; Kindle/Apple are DRM-locked, effectively separate projects. |
| Backup | **Full `KoboReader.sqlite` snapshot** (already solved) | The snapshot preserves 100% of data losslessly; "don't-lose-it" is done. |
| Export | **Highlights + notes/annotations** | The irreplaceable user-generated text content. Reading-state/collections deferred at zero data-loss risk (snapshot still keeps them). |
| Reach | **Cross-platform CLI** (`pip install`) | Fixes the #1 reach blocker (macOS-only hardcoded path). Architected so binary/GUI are later *packaging* steps, not rewrites. |
| Formats | **Markdown + JSON** | JSON makes the tool composable — the ecosystem builds integrations on a stable format instead of us maintaining N brittle ones. |
| Architecture | **Layered package** | One responsibility per module; testable; zero deps; clean seams without speculative plugin machinery. |

## 3. Scope

**In:**
- Cross-platform device detection (macOS / Windows / Linux)
- Read-only snapshot of `KoboReader.sqlite` (full backup, preserved safety model)
- Extraction of highlights **+ notes/annotations**
- Render Markdown (current output, preserved) **+ JSON** (documented, stable)
- `pip install` + `kobo-backup` console command
- Unit tests against an in-repo fixture DB
- README, LICENSE (MIT), `pyproject.toml`

**Explicitly out (not-now), all deferrable at zero data-loss risk because the snapshot preserves everything:**
- Other platforms (Kindle, Apple Books, Google Play, Nook, …)
- Rendering reading-state / progress / collections / ratings / activity
- Built-in third-party integrations (Obsidian/Notion/Readwise/Anki exporters)
- Standalone binary (PyInstaller)
- GUI app
- Formal plugin/adapter interfaces (the layered seams suffice until demand is proven)

## 4. Architecture — layered package, zero runtime deps

```
kobo_backup/
  __init__.py
  device.py      cross-platform detect + safe read-only snapshot   (the safety core)
  reader.py      the ONLY module that knows Kobo's SQLite schema → typed records
  model.py       Book / Highlight dataclasses = stable internal representation
  render/
    __init__.py
    markdown.py  model → Markdown (current output, preserved)
    json.py      model → documented JSON
  cli.py         arg parsing + orchestration
  __main__.py    `python -m kobo_backup` / console-script entry
tests/           per-module, against a tiny fixture .sqlite (incl. a notes row)
pyproject.toml   packaging → `kobo-backup` command
README.md
LICENSE
```

**Module responsibilities & interfaces:**

- `device.py` — *what:* find a connected Kobo and snapshot its DB read-only. *interface:* `detect_device() -> Path | None`, `snapshot(src: Path, backup_dir: Path) -> Path`. *depends on:* stdlib `sqlite3`, `pathlib`, platform mount conventions. Preserves the existing safety model verbatim.
- `reader.py` — *what:* the single place that knows Kobo's schema; read a snapshot into typed records. *interface:* `read_books(db: Path) -> list[Book]`. *depends on:* `model`, `sqlite3`.
- `model.py` — *what:* plain dataclasses, the stable seam everything else depends on. *interface:* `Book`, `Highlight`. *depends on:* nothing.
- `render/markdown.py`, `render/json.py` — *what:* pure functions model → text (no I/O). *interface:* `render(books: list[Book], meta) -> dict[str, str]` mapping filename → content. *depends on:* `model` only.
- `cli.py` — *what:* parse args, orchestrate detect→snapshot→read→render→write files. *depends on:* all of the above.

**Data flow (the invariant safety property):**
```
detect device → snapshot ONCE (read-only) → [local snapshot] → reader → model → renderers
```
The device is never touched more than once per run and never written to. Everything downstream reads the local snapshot.

## 5. Data model & the notes caveat

```python
@dataclass
class Highlight:
    text: str            # the highlighted passage (Bookmark.Text)
    note: str | None     # the user's own note (Bookmark.Annotation), if any
    date: str            # YYYY-MM-DD from DateCreated
    chapter_index: int   # reading-order chapter number within the book

@dataclass
class Book:
    title: str
    author: str
    volume_id: str
    highlights: list[Highlight]
```

**Caveat (must verify before claiming note support works):** the current owner's DB has **0 annotations**, so we cannot prove from real data exactly how Kobo represents a note vs. a highlight-with-note (`Bookmark.Type` vs. populated `Bookmark.Annotation`). Design defensively: select `Annotation` whenever present, include a row when `Text` **or** `Annotation` is non-empty. **Verification path:** build a fixture DB that includes a note row, and/or test against a contributor's DB that contains notes, before advertising note support.

## 6. CLI surface (evolves today's flags)

```
kobo-backup                       # detect device → snapshot → md + json   (default)
kobo-backup --format md|json|all  # default: all
kobo-backup --snapshot-only       # just back up the device, no export
kobo-backup --db PATH             # export from an existing snapshot, no device read
kobo-backup --device PATH         # override auto-detection
kobo-backup --out DIR             # output dir, default ./output
```

Mapping from the current script: `--backup-only` → `--snapshot-only`; `--db`, `--out` preserved; new `--format`, `--device`.

## 7. Cross-platform device detection (the #1 reach fix)

Probe per-OS mount roots for `.kobo/KoboReader.sqlite`:

- **macOS:** `/Volumes/KOBOeReader`
- **Linux:** `/media/$USER/KOBOeReader`, `/run/media/$USER/KOBOeReader`, `/mnt/*`
- **Windows:** enumerate drive letters, match the `KOBOeReader` volume label

`--device PATH` always overrides detection. Clear, actionable message when no device and no snapshot is found.

## 8. Output formats

- **Markdown:** preserve the current rendering (per-book files in reading order, chapter separators, dates, `index.md`). Add the user's `note` beneath the highlighted passage when present.
- **JSON:** documented, versioned, stable contract — the composability surface:

```json
{
  "schema": "kobo-backup/1",
  "generated": "2026-06-01",
  "source": "KoboReader-20260601-101010.sqlite",
  "books": [
    {
      "title": "…", "author": "…", "volume_id": "…",
      "highlights": [
        {"text": "…", "note": null, "date": "2025-03-17", "chapter_index": 4}
      ]
    }
  ]
}
```

## 9. Safety model (preserved verbatim)

- Device DB opened **read-only** (`file:…?mode=ro`), copied via SQLite online-backup API (handles WAL consistently).
- Snapshots written to a `.tmp` then atomically renamed; a failed backup never clobbers an existing snapshot.
- Snapshots are **timestamped and never overwritten**.
- The device is read **at most once per run**.

## 10. Re-run semantics

- **Snapshots = append-only history** (timestamped, never overwritten).
- **`output/` = a pure projection of the latest snapshot**, regenerated each run.
- Consequence: un-highlighting on the device changes a future export but never loses history — older highlights remain in older snapshots. Documented in README.

## 11. Testing

- Per-module unit tests against a tiny **in-repo fixture `KoboReader.sqlite`** built in a test fixture, including at least one **note row** so note-handling is genuinely exercised.
- Cover: detection (mocked mount roots), snapshot safety (read-only, atomic, no-overwrite), reader extraction (highlights, notes, ordering, chapter grouping), both renderers.
- TDD: write the failing test first per the project workflow.

## 12. Packaging & distribution

- **Zero runtime dependencies** (stdlib only) — kept as a deliberate differentiator: no CVE/dependency churn, trivial future binary packaging.
- `pyproject.toml` with a `kobo-backup` console-script entry point.
- Python 3 (target a reasonable floor, e.g. 3.9+; confirm during implementation).

## 13. 5-lens design pass

- **Product:** wins on *safety + zero-config + dual MD/JSON*, not on being "another exporter." Existing Kobo exporters (calibre plugins, etc.) exist — the edge is the rigorous read-only model and zero install friction.
- **Ops:** solo-maintainable. Zero deps = no dependency-security churn. Top risk = **Kobo firmware schema drift** → defensive queries + tests + a documented "tested against firmware X" note. README sets issue-triage expectations for a broad audience.
- **UX:** plug in → `kobo-backup` → snapshot + md + json, no config. Crisp "device not found" guidance. CLI ceiling for non-technical users is acknowledged and deferred to a future binary.
- **Architecture:** `model.py` is the stable seam; reader and renderers isolated; extension latent, not pre-built (honors "加易移難, 需求確定再加").
- **Business:** free/OSS → reputation + a genuinely useful personal tool, not revenue. Success = it serves the owner + gets used/contributed to. Cost = maintenance time → kept low by tight scope.

## 14. Privacy / git (must handle before any public push)

This working directory currently contains **personal and sensitive data** that must never enter a public repo:

- `.kobo/` — full device dump incl. `KoboReader.sqlite`, `device.salt.conf`, `certificates/`, `webstorage/`
- `output/` — personal highlights
- `backups/` — personal snapshots
- any `*.sqlite*`

The repo must track **only** source/tests/docs/README/LICENSE/pyproject. A `.gitignore` excluding the above is a precondition of `git init` → commit → (eventually) push. **Pushing to a public remote is an outward-facing, hard-to-reverse action and must be done deliberately by Eric.**

## 15. Open questions / verification needed

1. **Note representation** — verify `Bookmark.Type` / `Annotation` semantics against a DB that actually contains notes (§5).
2. **Python version floor** — confirm minimum supported (e.g. 3.9+).
3. **Windows volume-label detection** — confirm the detection approach on a real Windows mount.
4. **Final name/license** — proceeding with `kobo-backup` + MIT unless overridden.

## 16. Phased roadmap

- **v1 (this plan):** cross-platform CLI, snapshot + highlights/notes → MD + JSON, tests, packaging, docs.
- **Not now (future, demand-driven):** downloadable binary; GUI; reading-state/collections rendering; built-in integrations; other platforms.

## 17. Success criteria

- A Kobo owner on macOS/Windows/Linux can `pip install` and run one command to get a safe snapshot + Markdown + JSON of their highlights and notes, with zero config and zero dependencies.
- The snapshot safety model is preserved exactly.
- Note support is verified against real note data before being advertised.
- No personal data is ever committed to the repo.
