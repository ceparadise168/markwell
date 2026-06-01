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
device → snapshot → reader → model → render (markdown / json) → cli writes files
```

- **`reader.py` is the *only* schema-aware module.** It is the single place that
  knows Kobo's SQLite table and column names. If a firmware update changes the
  schema, adapt `reader.py` — and nowhere else.
- **`model.py` is the stable internal representation** (`Book`, `Highlight`).
  Renderers and the CLI depend on these plain data structures, not on SQL.
- **The renderers are pure:** `render(books, meta)` returns
  `{filename: content}` and performs no I/O. The CLI owns all filesystem writes.

Keeping schema knowledge confined to `reader.py` is what lets the rest of the
codebase stay firmware-agnostic; please preserve that boundary.

## Tests

Add or update tests for any behavior you change. The test suite lives in
`tests/` and mirrors the module layout (`test_reader.py`, `test_device.py`,
`test_render_json.py`, and so on).
