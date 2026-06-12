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

## Releases

Releases are tag-driven and preflight-gated; desktop artifacts land in a
**draft** GitHub release for review before anything goes public.

1. Check that `version` in `pyproject.toml` matches the tag you are about to
   cut (`0.2.0` → `v0.2.0`), then push the tag:

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

2. `.github/workflows/release.yml` builds the desktop app on macOS and
   Windows, runs `packaging/preflight.py dist` on each build tree (**hard
   gate** — any private data fails the job before anything is zipped or
   uploaded), packages the artifacts, and attaches them to a **draft** release.

3. Eric reviews the draft — artifacts and release notes — and clicks
   **Publish release**.

4. Publishing the release triggers `.github/workflows/publish-pypi.yml`, which
   builds the sdist + wheel, preflights `dist/` and the unpacked wheel,
   sanity-imports the installed wheel, and uploads to PyPI via Trusted
   Publishing.

### Artifact-name contract

The release assets must be named exactly:

- `Markwell-macOS.zip` — the `Markwell.app` bundle, zipped with `ditto` so
  symlinks and execute bits survive;
- `Markwell-Windows.zip` — the onedir `Markwell/` folder (`Markwell.exe`
  inside).

The landing site downloads them via
`https://github.com/ceparadise168/markwell/releases/latest/download/Markwell-macOS.zip`
(and `…/Markwell-Windows.zip`). Renaming an asset silently breaks those links.

Note: GitHub's `macos-latest` runners are Apple Silicon, so the macOS zip is an
arm64 build; Intel Macs are not covered by this artifact.

### One-time PyPI setup — Trusted Publisher (Eric 手動, one-time)

PyPI is told to trust this repository's workflow; no API token exists anywhere.
Because the `markwell` project does not exist on PyPI until the first upload,
register a **pending** publisher:

1. pypi.org → log in → **Account settings → Publishing → Add a new pending
   publisher** (GitHub tab):
   - PyPI project name: `markwell`
   - Owner: `ceparadise168`
   - Repository: `markwell`
   - Workflow name: `publish-pypi.yml`
   - Environment: *leave blank* (the workflow does not declare one; filling
     this in would make publishing fail)
2. The first successful publish creates the project and attaches the
   publisher; afterwards it is managed under pypi.org → project `markwell` →
   **Publishing**.

### Unsigned artifacts (decision 2026-06-11)

The desktop zips are **unsigned** for now; signing/notarization is revisited
when the project has traction. First-launch instructions for readers:

- **macOS**: right-click `Markwell.app` → **Open** → Open. On newer macOS
  (Sequoia and later) the right-click override is gone: launch once, then
  System Settings → Privacy & Security → **Open Anyway**.
- **Windows**: SmartScreen shows "Windows protected your PC" — click
  **More info → Run anyway**.
