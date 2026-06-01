# Markwell

> *Mark well what you read.* Back up and export your Kobo highlights into a corpus you own.

Safely back up and export your [Kobo](https://www.kobo.com/) highlights and
notes to Markdown and JSON. Cross-platform, zero dependencies (Python standard
library only).

## Why

Your highlights and notes are the irreplaceable part of your reading. `markwell`:

- **Never writes to your device.** It only ever *reads* the Kobo database, copying
  the file to a local snapshot. Nothing — not even SQLite housekeeping — touches
  the device.
- **Keeps every snapshot as immutable history.** Each run saves a timestamped
  `KoboReader-<stamp>.sqlite` that is never overwritten, so you accumulate a full
  history of your reading database.
- **Gives you portable output.** Human-readable Markdown *and* a documented JSON
  file you can feed into Obsidian, Anki, Readwise, or your own scripts.

The Markdown and JSON always mirror the **latest** snapshot only — they are a
fresh projection of one database, not a growing archive. So if you delete a
highlight on the device, it disappears from the next export. To recover it,
re-export from a dated snapshot:

```bash
markwell --db backups/KoboReader-<stamp>.sqlite
```

## Install

Not on PyPI yet — install from the repo:

```bash
pipx install git+https://github.com/ceparadise168/markwell.git   # isolated, recommended
pip install git+https://github.com/ceparadise168/markwell.git    # into the current environment
```

```bash
pip install markwell   # (once published)
```

## Usage

Plug in your Kobo, then:

```bash
markwell                 # snapshot the device, then export Markdown + JSON
markwell --format md     # Markdown only
markwell --format json   # JSON only
markwell --snapshot-only # just back up the database, no export
markwell --db PATH       # export from an existing snapshot (no device read)
markwell --device PATH   # Kobo mount point OR KoboReader.sqlite path (overrides auto-detect)
markwell --require-device # fail instead of falling back to the latest local snapshot
markwell --out DIR       # output directory (default: output/, relative to the current directory)
markwell --debug         # show full tracebacks on error
markwell --version       # print the version and exit
```

Progress and status messages go to **stderr**; the exported data and JSON are
written to files under `--out`. On success the tool prints the absolute path of
the output directory, so you always know exactly where the files landed.

Output (`backups/` and `output/` are created relative to the current directory):

```
backups/
└── KoboReader-YYYYMMDD-HHMMSS.sqlite   timestamped, never overwritten
output/
├── index.md            all books, counts, links
├── <book>.md           one file per book, highlights in reading order
└── highlights.json     machine-readable export (schema "markwell/1")
```

## How it works

`detect device → snapshot once (read-only) → read snapshot → Markdown + JSON`

The device is read at most once per run and never modified. The exports are a
projection of the latest snapshot only; it is the **snapshot history** that
preserves everything, so a highlight removed on the device is still recoverable
from the dated `.sqlite` it was last captured in (see [Why](#why)).

## JSON format

```json
{
  "schema": "markwell/1",
  "generator": "markwell/0.1.0",
  "generated": "2026-06-01",
  "source": "KoboReader-20260601-101010.sqlite",
  "source_freshness": "device",
  "books": [
    {
      "title": "…", "author": "…", "volume_id": "…",
      "highlights": [
        { "text": "…", "note": null, "date": "2025-03-17", "chapter_index": 4 }
      ]
    }
  ]
}
```

Fields:

- `schema` — the schema contract, `markwell/<MAJOR>` (see below).
- `generator` — the producing tool and its version, `markwell/<version>`.
- `generated` — local date (`YYYY-MM-DD`) the export was produced.
- `source` — filename of the snapshot the export was projected from.
- `source_freshness` — whether `source` came from a live `"device"` snapshot
  taken this run, or a `"cached_snapshot"` reused because no device was connected.
- `books[]` — each with `title`, `author`, `volume_id`, and `highlights[]`
  (`text`, `note`, `date`, `chapter_index`).

### Schema stability

The `/N` suffix in `schema` is the **major** version. It only bumps on a
**breaking** change (a field removed, renamed, or given a new meaning). Within a
major version, changes are **additive only** — new fields may appear, so
**consumers must ignore unknown fields** rather than failing on them. Pin to the
major (`markwell/1`) and you can rely on every documented field staying put.

### Exit codes

| Code | Meaning |
|--:|---|
| `0` | success |
| `2` | no device and no usable snapshot/source |
| `3` | database read fine, but contained no highlights or notes |
| `4` | source unreadable or its schema is unsupported |

## Notes & compatibility

- Tested against Kobo firmware schemas with `Bookmark` and `content` tables. If a
  firmware update changes the schema, please open an issue.
- Note (annotation) support reads `Bookmark.Annotation`; if you write notes on
  highlights, they appear under each highlight.
- **Exported text is verbatim and untrusted.** Highlights and notes are reproduced
  exactly as written, so treat the Markdown/JSON as *data*, not trusted markup — a
  value beginning with `=`, `+`, `-`, or `@` can be read as a formula if you import
  it into a spreadsheet/CSV, so sanitize on import if that matters. See
  [SECURITY.md](SECURITY.md).

## Development

```bash
pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the architecture invariants and house
rules, [CHANGELOG.md](CHANGELOG.md) for what's changed, and
[SECURITY.md](SECURITY.md) for how to report a vulnerability.

## License

MIT — see [LICENSE](LICENSE).
