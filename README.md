# Markwell

> *Mark well what you read.* Back up and export your Kobo highlights into a corpus you own.

Safely back up and export your [Kobo](https://www.kobo.com/) highlights and
notes to Markdown and JSON. Cross-platform, zero dependencies (Python standard
library only).

## Why

Your highlights and notes are the irreplaceable part of your reading. `markwell`:

- **Never writes to your device.** It opens the Kobo database read-only and copies
  it with SQLite's online-backup API.
- **Keeps every snapshot.** Backups are timestamped and never overwritten, so you
  have a full history of your reading database.
- **Gives you portable output.** Human-readable Markdown *and* a documented JSON
  file you can feed into Obsidian, Anki, Readwise, or your own scripts.

## Install

```bash
pip install markwell
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
markwell --out DIR       # output directory (default: ./output)
```

Output:

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

The device is read at most once per run and never modified. Exports are a
projection of the latest snapshot; your snapshot history preserves everything,
so re-running after un-highlighting on the device never loses old data.

## JSON format

```json
{
  "schema": "markwell/1",
  "generated": "2026-06-01",
  "source": "KoboReader-20260601-101010.sqlite",
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

## Notes & compatibility

- Tested against Kobo firmware schemas with `Bookmark` and `content` tables. If a
  firmware update changes the schema, please open an issue.
- Note (annotation) support reads `Bookmark.Annotation`; if you write notes on
  highlights, they appear under each highlight.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).
