# Markwell Desktop Distribution Plan

Date: 2026-06-02

## Goal

Ship Markwell V1 as signed macOS and Windows desktop apps built from the
existing Python project. A non-technical Kobo reader should be able to download,
install, launch, back up highlights, read and search them, and find exported
files without installing Python or using a terminal.

Architecture stays:

`Kobo device -> Python safe core -> localhost GUI -> ~/Markwell`

Packaging uses PyInstaller first. Runtime app code remains Python
standard-library only; packaging tools are build-time dependencies.

## Decisions

- V1 uses packaged Python.
- V1 ships signed macOS DMG and signed Windows installer artifacts.
- Electron is not used.
- Rust/Tauri is deferred until distribution is proven.
- The Chrome Extension is V2 after desktop, as a Lite viewer/importer for
  `highlights.json`, not the backup engine.
- Markwell stays local-first: no telemetry, no cloud, no background daemon, and
  no automatic update checks.
- Donation and docs links open only after explicit user clicks.

## Implementation Tasks

1. Add release decision docs.
2. Add desktop launcher lifecycle:
   - keep `markwell-gui` terminal behavior unchanged by default;
   - add desktop mode through `markwell-gui --desktop` and a
     `markwell-desktop` entrypoint;
   - add authenticated `POST /api/quit`;
   - add authenticated `POST /api/heartbeat`;
   - send a frontend heartbeat every 15 seconds;
   - show a small Quit control in the app shell;
   - in desktop mode, exit after five minutes without heartbeat when no export
     job is running;
   - never auto-exit in terminal mode.
3. Add PyInstaller release configuration:
   - optional `release = ["pyinstaller>=6,<7"]` dependency group only;
   - package the desktop launcher, not a terminal-only server;
   - bundle `markwell/gui/assets/*`;
   - exclude private/local data such as `.kobo/`, `output/`, `backups/`,
     SQLite files, `.playwright-mcp/`, `.pytest_cache/`, and `__pycache__/`.
4. Add artifact privacy preflight script and tests.
5. Add macOS DMG signing/notarization script and CI support.
6. Add Windows Inno Setup installer/signing config and CI support.
7. Add release workflow for tag and manual builds.
8. Update public docs and donation placement:
   - README desktop download first;
   - `pipx install` remains developer/power-user path;
   - trust copy says "No cloud.", "No account.", "Never writes to your Kobo.",
     and "Your highlights stay on your computer.";
   - donation is optional, secondary, and appears after value is delivered.
9. Run the manual acceptance matrix on clean macOS and Windows machines before
   publishing a V1 release.

## Manual Acceptance Matrix

### macOS

- Install DMG on a clean machine or fresh user account.
- Launch from Applications without a terminal.
- Confirm the browser opens Markwell.
- Confirm the sample library works.
- Plug in Kobo and run backup.
- Confirm `~/Markwell/backups/KoboReader-*.sqlite`,
  `~/Markwell/output/index.md`, and `~/Markwell/output/highlights.json`.
- Quit from the GUI and confirm the process exits.
- Confirm Gatekeeper shows no unknown developer warning after notarization.

### Windows

- Install signed installer on a clean Windows 11 machine.
- Launch from Start Menu without Python.
- Confirm the browser opens Markwell.
- Confirm the sample library works.
- Plug in Kobo and run backup.
- Confirm the same output structure under the user's `Markwell` folder.
- Uninstall and confirm user data remains untouched.

### Security

- API calls without token return 403.
- Bad Host header returns 403.
- `/api/open` with an invalid folder key returns 400.
- No outbound requests occur during backup.
- Exported text is escaped/rendered as data, not executable HTML.

### Release Artifact

- Run the privacy preflight.
- Inspect each platform artifact contents manually once.
- Confirm no `.kobo`, `output`, `backups`, `*.sqlite`, or local cache files are
  bundled.

## Distribution Strategy

Primary channel: GitHub Releases.

Artifacts:

- `Markwell-macOS.dmg`
- `Markwell-Windows-Setup.exe`

Core positioning:

> Back up and export your Kobo highlights into Markdown and JSON. Local-only.
> Read-only. Free.

Target communities include Kobo readers, Obsidian and Anki users, Readwise
alternatives, personal knowledge management, and local-first tools. Avoid
overclaiming firmware coverage; say Markwell is tested against current known
Kobo schemas.

## Donation Strategy

Use GitHub Sponsors, Ko-fi, or Buy Me a Coffee. Donation copy appears only after
value is delivered: successful export screen, README, release page, and
About/footer. Suggested copy:

> Markwell is free and local-first. If it helped preserve your reading notes,
> you can support development.

Donation must never block backup or export.

## Non-Negotiable Constraints

- Do not add runtime dependencies to Markwell core.
- Do not write to Kobo device.
- Do not open the Kobo DB directly with SQLite on the device.
- Do not include private data in release artifacts.
- Do not add telemetry, cloud sync, auto-update, or a background daemon.
- Do not rewrite the core in Rust/Tauri for V1.
- Do not use Electron.
- Do not make donation mandatory.
