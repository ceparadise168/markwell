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

Release artifacts must never include private or local data. The packaging config
and release preflight guard against these paths:

- `.kobo/`
- `output/`
- `backups/`
- `*.sqlite`
- `*.sqlite-shm`
- `*.sqlite-wal`
- `.playwright-mcp/`
- `.pytest_cache/`
- `__pycache__/`

Before publishing, run the release artifact privacy preflight against `dist/`
and each platform staging directory.

## Expected Smoke Test

After building, launch the app from `dist/`:

- the browser opens Markwell without requiring a terminal command;
- static GUI assets load;
- the sample library works without a connected Kobo;
- backups and exports write under `~/Markwell`;
- no private repository data appears inside `dist/`.
