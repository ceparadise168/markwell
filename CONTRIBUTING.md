# Contributing to Markwell

Thanks for helping improve Markwell. This is a small, deliberately simple tool;
the guidelines below keep it that way.

## Development setup

```bash
pip install -e ".[dev]"   # editable install plus the test dependency (pytest)
pytest                    # run the test suite
```

Python 3.9 or newer is required.

## Project rules

These are non-negotiable; PRs that break them won't be merged.

- **Zero runtime dependencies.** Markwell uses the Python **standard library
  only** (`argparse`, `sqlite3`, `json`, `re`, `pathlib`, `datetime`, `shutil`,
  `os`, `glob`, `getpass`, `string`, `dataclasses`, `collections`, `logging`).
  Do not add a third-party runtime package. Test-only tooling belongs in the
  `dev` optional-dependency group.
- **Python >= 3.9.** Any module that uses `X | Y` type hints must start with
  `from __future__ import annotations`.
- **Read-only, offline, zero-touch.** Markwell must never write to the device
  and must make no network connections. See [SECURITY.md](SECURITY.md).
- **Minimal, focused diffs.** Match the surrounding style and docstring density.
  Don't refactor unrelated code or add speculative features.

## Architecture invariant

The data flow is:

```
device → snapshot → reader → model → render (format registry) → cli / gui write files
```

- **`reader.py` is the *only* schema-aware module.** It is the single place that
  knows Kobo's SQLite table and column names. If a firmware update changes the
  schema, adapt `reader.py` — and nowhere else.
- **`model.py` is the stable internal representation** (`Book`, `Highlight`).
  Renderers and the front-ends depend on these plain data structures, not on SQL.
- **The renderers are pure:** `render(books, meta)` returns
  `{filename: content}` and performs no I/O. The front-ends (the CLI and the
  GUI service) own all filesystem writes.

Keeping schema knowledge confined to `reader.py` is what lets the rest of the
codebase stay firmware-agnostic; please preserve that boundary.

## Adding an export format

`export.FORMATS` is the single source of what Markwell can export. To add a
format:

1. **Write a pure renderer** in `markwell/render/`: `render(books, meta) ->
   {filename: content}`, no I/O. Follow the escaping and encoding patterns of
   the existing modules (RFC 4180 quoting and the UTF-8 BOM in `csv.py`, HTML
   escaping in `html.py`, tab-safe field flattening in `anki.py`).
2. **Register it** — one line in `export.FORMATS`. Insertion order is the
   canonical display and output order everywhere.
3. **Mirror it in the GUI** — add the id to `FORMAT_IDS` in `app.js`, and add
   the `fmt.<id>` / `fmt.<id>_desc` copy to **all four** locales in `i18n.js`.
   A parity test holds the GUI mirror to the Python registry, so skipping this
   step fails the suite instead of surfacing as a missing checkbox in someone's
   browser.

## Localization (i18n)

- **Every GUI string goes through `t()` with a literal key.** No hardcoded
  English in the JS, and no dynamically built keys — the tests scan the
  sources for literal keys and for known-English sentinels.
- **The locale dictionaries in `i18n.js` stay in exact key parity** across
  `en`, `zh-TW`, `ja`, and `ko`. A key added to one is added to all four;
  tests enforce this.
- **`en` is the canonical source.** English copy lives in the dictionary like
  every other language — never invent English strings in code.
- **Exports localize labels only.** Titles, counts, and table headers come from
  `markwell/render/labels.py`; the reader's highlight and note text is
  verbatim — never translated.
- **A new locale is a dictionary PR:** a full key set in `i18n.js`, a full
  label table in `labels.py`, and a mention in the README. No code changes —
  unknown locales already fall back to English.

## Tests

Add or update tests for any behavior you change. The test suite lives in
`tests/` and mirrors the module layout (`test_reader.py`, `test_device.py`,
`test_render_json.py`, and so on).
