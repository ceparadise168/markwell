# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **Renamed the project `kobo-backup` → Markwell** (the CLI, package, and module
  are now `markwell`).
- **Snapshots are now a true zero-touch file copy of the device database.** The
  device DB is only ever read; nothing — not even SQLite housekeeping — writes to
  the device, so "Never writes to your device" is now literally true.
- **Highlights are now emitted in true spine reading order** rather than the
  database's row order.
- **Dates are rendered in your local time zone** instead of raw UTC.
- **Status and progress messages now go to stderr;** the exported data and JSON
  go to files. This keeps `--format json` pipelines clean.
- **`--device` is now assertive:** when given, it is used as specified instead of
  being treated as a hint alongside auto-detection.
- **`output/` is documented as relative to the current working directory,** and
  the tool prints the **absolute path** of the output directory on success.

### Added

- **`--require-device` flag** — fail instead of silently falling back to the
  latest local snapshot when no device is connected.
- **`--debug` flag** — show full tracebacks on error.
- **`--version` flag** — print the version and exit.
- **Distinct exit codes** — `0` success, `2` no device/source, `3` no highlights,
  `4` unreadable or unsupported schema.
- **JSON `source_freshness` field** — `"device"` for a snapshot taken this run,
  `"cached_snapshot"` for a reused local snapshot, signalling stale exports.
- **JSON `generator` field** — `"markwell/<version>"`, identifying the producing
  tool and version.
- **Schema-stability contract** in the docs — `schema` is `markwell/<MAJOR>`,
  additive-only within a major, and consumers must ignore unknown fields.
- **Schema-error handling** — an unreadable or unsupported source DB now fails
  cleanly with exit code `4` instead of an opaque traceback.
- Project docs: `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`, and a GitHub
  Actions CI workflow.

[Unreleased]: https://github.com/ceparadise168/markwell/commits/main
