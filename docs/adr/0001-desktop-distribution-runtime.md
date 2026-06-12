# ADR-001: Desktop Distribution Runtime

Status: Accepted
Date: 2026-06-02

## Context

Markwell already has a tested Python safe core for reading Kobo data, taking
read-only snapshots, and exporting Markdown and JSON. The first desktop release
needs to let non-technical readers download, install, launch, back up, read,
search, and find exported files without installing Python or using a terminal.

The product invariant remains:

`Kobo device -> Python safe core -> localhost GUI -> ~/Markwell`

## Decision

Markwell V1 ships as a packaged Python desktop app.

PyInstaller is the first packaging tool for V1. Packaging tools are build-time
dependencies only; Markwell runtime app code remains Python standard-library
only.

V1 targets signed macOS DMG and signed Windows installer artifacts.

## Rationale

The current snapshot and export code is already tested and safety-critical. A
packaged Python app keeps that code in place while making Markwell usable for
readers who do not want a command line workflow.

PyInstaller can bundle the existing Python entrypoint and static GUI assets
without changing the local-first architecture or adding a runtime dependency to
the app code.

## Rejected

Electron is rejected for V1 because it bundles Chromium and Node for a utility
whose existing GUI already runs in the user's browser through a local server.
That increases artifact size and changes the trust surface without improving
Kobo backup safety.

## Deferred

Rust/Tauri is deferred. It may be revisited after desktop distribution is proven,
but rewriting the safe core before V1 risks breaking the read-only Kobo snapshot
guarantee.

The Chrome Extension is V2 after the signed desktop release. Its role is a Lite
viewer/importer for `highlights.json`, not the backup engine. Full Kobo backup
inside the extension and Native Messaging are out of V1 unless a later ADR
approves them.

## Consequences

- Markwell V1 keeps the Python safe core as the device and SQLite boundary.
- The packaged app starts the existing localhost GUI and writes user data under
  `~/Markwell`.
- The desktop app must expose an explicit Quit action and avoid leaving an
  invisible server running forever.
- Release artifacts must be privacy-checked so `.kobo`, `output`, `backups`,
  SQLite files, and local caches are never bundled.
- There is no telemetry, cloud sync, background daemon, or automatic update
  check in V1.

Reference: https://www.pyinstaller.org/en/stable/
