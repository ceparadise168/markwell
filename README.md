# Markwell

**English** · [中文（台灣）](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md)

> *Mark well what you read.* Back up and export your Kobo highlights into a corpus you own.

[![Website](https://img.shields.io/badge/Website-markwell.page-2e7d6b)](https://markwell.page)
[![CI](https://github.com/ceparadise168/markwell/actions/workflows/ci.yml/badge.svg)](https://github.com/ceparadise168/markwell/actions/workflows/ci.yml)
[![Downloads](https://img.shields.io/github/downloads/ceparadise168/markwell/total)](https://github.com/ceparadise168/markwell/releases)
[![PyPI](https://img.shields.io/pypi/v/markwell)](https://pypi.org/project/markwell/)
[![PyPI downloads](https://img.shields.io/pypi/dm/markwell)](https://pypistats.org/packages/markwell)

Safely back up, read, and export your [Kobo](https://www.kobo.com/) highlights
and notes — readable pages in your browser, plus Markdown, JSON, CSV, Anki
flashcards, and a printable HTML library. Everything stays on your computer:
no account, no cloud service, no network connections. Cross-platform, zero
dependencies (Python standard library only).

![The Library view: your books as cards, every highlight searchable](docs/screenshots/03-library.png)

## Get Markwell

Download the app for your computer from the
[latest release](https://github.com/ceparadise168/markwell/releases/latest):

- **macOS** — [`Markwell-macOS.zip`](https://github.com/ceparadise168/markwell/releases/latest/download/Markwell-macOS.zip)
- **Windows** — [`Markwell-Windows.zip`](https://github.com/ceparadise168/markwell/releases/latest/download/Markwell-Windows.zip)

Unzip it and open the app: Markwell opens in your web browser, running
entirely on your own computer.

<details>
<summary><strong>If your computer hesitates at first launch</strong> — the download is unsigned</summary>

Markwell is free software and the downloads carry no code-signing
certificate, so your operating system asks for one extra confirmation the
first time:

- **macOS (Sonoma / macOS 14 and earlier)** — right-click (or Control-click)
  **Markwell** and choose **Open**, then click **Open** in the dialog. macOS
  remembers your answer, so this is only needed once.
- **macOS (Sequoia / macOS 15 and later)** — the right-click route is gone:
  open **Markwell** once (it will be blocked), then go to **System Settings →
  Privacy & Security** and click **Open Anyway**.
- **Windows** — when the SmartScreen window appears, click **More info**,
  then **Run anyway**.

If you'd rather not run an unsigned binary, install the Python package below
instead — the same app, with no bundled executable.

</details>

Prefer the command line? Markwell is also a Python package (Python 3.9+):

```bash
pipx install markwell    # or: pip install markwell
markwell                 # the command-line tool
markwell-gui             # the same app the desktop download runs
```

### Uninstall

Don't like it? Remove it any time — Markwell installs nothing in the
background: no service, no account, no registry entries, and never a network
connection.

- **macOS / Windows** — move **Markwell** (the app you unzipped) to the Trash
  or Recycle Bin. Nothing is left behind.
- **Python package** — `pipx uninstall markwell` (or `pip uninstall markwell`).

Your library and snapshots live in a separate folder (`~/Markwell` by default,
shown under **Settings**), so uninstalling never touches them. Want a clean
sweep? Delete that folder, plus the small settings folder `~/.markwell/` —
both are ordinary folders you fully control.

## Why

Your highlights and notes are the irreplaceable part of your reading. Markwell:

- **Never writes to your device.** It only ever *reads* the Kobo database, copying
  the file to a local snapshot. Nothing — not even SQLite housekeeping — touches
  the device.
- **Keeps every snapshot as immutable history.** Each run saves a timestamped
  `KoboReader-<stamp>.sqlite` that is never overwritten, so you accumulate a full
  history of your reading database.
- **Gives you portable output.** Human-readable Markdown, a documented JSON
  file, CSV for spreadsheets, Anki flashcards, and a self-contained HTML
  library — feed them into Obsidian, Anki, Excel, Readwise, or your own scripts.

The exports always mirror the **latest** snapshot only — they are a fresh
projection of one database, not a growing archive. So if you delete a
highlight on the device, it disappears from the next export. To recover it,
re-export from a dated snapshot:

```bash
markwell --db backups/KoboReader-<stamp>.sqlite
```

## The app (no terminal needed)

The desktop downloads above open straight into the app; from a terminal, it is:

```bash
markwell-gui          # or:  python3 -m markwell.gui
```

It opens in your web browser and lets you, in plain language:

- **Back up** — one button snapshots your Kobo and turns your highlights into
  readable pages, with live progress and a clear result.
- **Library** — read and search your highlights and notes in a calm, book-like
  view (one file per book, in reading order, with your notes).
- **Review** — each day brings back one line from your highlights, with a
  shuffle and a per-book filter.
- **History** — see every saved copy, re-create your files from an older one, and
  open the folder where everything lives.
- **Settings** — choose where your library lives (a cloud folder, if you like)
  and pack everything into a single ZIP archive.

![The Back up view: one button, a clear promise, live progress](docs/screenshots/01-backup.png)

It uses the same safe core as the command line, so it **never writes to your
Kobo**. The app is purely local: it serves only to `127.0.0.1`, makes no network
connections, and requires a per-launch token on every request (see
[`SECURITY.md`](SECURITY.md)). Files default to `~/Markwell` — move them from
**Settings**, or pass `--data-dir` — and the app always shows you where they
are. It needs only the Python standard library — no extra dependencies, no
build step.

## Review & share cards

Each day the **Review** view brings back one line from your own highlights —
the same line until tomorrow — with a shuffle and a per-book filter when you
want more. And any highlight can become a **share card**: an image in three
sizes and three styles, with CJK-aware typography and an optional watermark.
Cards are drawn on a local canvas; nothing leaves your machine.

![The Review view: one line a day, returning from your own highlights](docs/screenshots/11-review.png)

![A book's highlights in reading order, with your notes beneath](docs/screenshots/04-book-detail.png)

## Your data, your languages

The whole interface speaks **English, 繁體中文, 日本語, and 한국어** — switch
languages from the sidebar; the choice is remembered. Exports are localized
too: the scaffolding of the Markdown and HTML files — titles, counts, table
headers — is written in your language. The app passes your interface language
along automatically; the command line takes `--lang en|zh-TW|ja|ko`. Your
highlights and notes themselves are always verbatim, never translated.

CSV and Anki column headers (and JSON keys) deliberately stay English: they
are machine-facing identifiers, and tools like Notion or Anki map fields by
those exact names — translating them would break every import recipe.

## Back up to your cloud

Everything Markwell saves lives in one ordinary folder. Open **Settings**, pick
iCloud Drive, Google Drive, Dropbox, or OneDrive, and Markwell copies your
library there — nothing is ever deleted, and Markwell itself never uploads a
byte: your cloud app syncs the folder like any other. The same screen can pack
everything into a single ZIP archive. Step-by-step instructions — including
moving to a new computer — are in the [cloud backup guide](docs/cloud-backup.md).

## Command line

Plug in your Kobo, then:

```bash
markwell                 # snapshot the device, then export every format
markwell --format md     # one format: md, json, csv, anki, or html
markwell --format md,csv # any comma list of those ("all" = every format)
markwell --lang ja       # language for export labels: en, zh-TW, ja, ko
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
├── highlights.json     machine-readable export (schema "markwell/1")
├── highlights.csv      one row per highlight, for Excel / Numbers / Notion
├── anki.tsv            flashcards ready to import into Anki
└── library.html        the whole library as a single self-contained page
```

## How it works

`detect device → snapshot once (read-only) → read snapshot → render the chosen formats`

The device is read at most once per run and never modified. The exports are a
projection of the latest snapshot only; it is the **snapshot history** that
preserves everything, so a highlight removed on the device is still recoverable
from the dated `.sqlite` it was last captured in (see [Why](#why)).

## JSON format

```json
{
  "schema": "markwell/1",
  "generator": "markwell/0.2.0",
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

## Maintainer

Built and maintained by Eric Tu ([@ceparadise168](https://github.com/ceparadise168))
— hi@markwell.page. Markwell is free, with no donations accepted for now —
if it helped you preserve your reading, star the repo and share a quote card.

## Acknowledgments

Markwell exists because **Kobo** keeps your highlights in an open, accessible
format — a standard SQLite database you can read straight off the device over
USB — and takes a refreshingly reader- and developer-friendly approach. Thank
you to Kobo and [@kobolabs](https://github.com/kobolabs).

## License

MIT — see [LICENSE](LICENSE).
