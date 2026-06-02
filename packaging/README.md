# Markwell Desktop Packaging

Markwell V1 is packaged from the existing Python safe core. Packaging tools are
build-time only; the installed app code remains Python standard-library only.

## Install Release Tools

```bash
python -m pip install -e ".[release]"
```

## Build the Desktop App

```bash
pyinstaller packaging/pyinstaller/markwell-desktop.spec --clean --noconfirm
```

The PyInstaller spec packages `markwell.desktop`, which starts the existing GUI
server in desktop lifecycle mode. It does not package the raw terminal-only
server entrypoint.

## Bundled Data

The spec includes `markwell/gui/assets/*` so the browser UI loads from the
packaged app.

Release artifacts must never include private or local data — a reader's Kobo
snapshots, exports, backups, SQLite databases, or local caches. The forbidden
directory names and file suffixes are defined once in `packaging/_forbidden.py`;
both the PyInstaller spec (input filter) and the release preflight (output scan)
import from it so they can never drift apart.

## Release Privacy Preflight

Before publishing, scan `dist/` and each platform staging directory:

```bash
python3 packaging/preflight.py dist
```

It exits 0 when the tree is clean, 1 when anything forbidden is found (printing
each offender), and 2 on a usage error — so it can gate a release in CI.

## Expected Smoke Test

After building, launch the app from `dist/`:

- the browser opens Markwell without requiring a terminal command;
- static GUI assets load;
- the sample library works without a connected Kobo;
- backups and exports write under `~/Markwell`;
- no private repository data appears inside `dist/`.
