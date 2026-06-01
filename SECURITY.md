# Security Policy

## Security model

Markwell is a local, **offline, read-only** tool:

- **It makes no network connections.** It neither phones home nor transmits your
  highlights anywhere. Everything stays on your machine.
- **It never writes to your device.** It only ever *reads* the Kobo database,
  opening it read-only and copying the file to a local snapshot. Nothing — not
  even SQLite housekeeping — touches the device.
- **It reads a personal database.** Your Kobo's `KoboReader.sqlite` contains your
  highlights, notes, and reading data. Markwell reads it, writes snapshots to
  `backups/`, and writes exports to `output/`, all on your local filesystem.
- **Zero runtime dependencies.** Markwell uses only the Python standard library,
  so there is no third-party supply chain to trust at runtime.
- **Exported content is verbatim and untrusted.** Highlight/note text and book
  metadata are reproduced exactly as they appear in the book. Filenames are
  sanitized and JSON is properly escaped, but a value beginning with `=`, `+`,
  `-`, or `@` can be interpreted as a formula by spreadsheet/CSV importers — treat
  exports as data and sanitize on import if you feed them into one.

The `backups/` and `output/` directories may contain personal reading data.
Treat them as you would any private notes; the project's `.gitignore` excludes
them so they are never committed.

## Reporting a vulnerability

Please report security issues privately rather than opening a public issue.

- Use GitHub's **"Report a vulnerability"** (Security → Advisories) on the
  repository, or
- email the maintainer at the address listed on the GitHub profile.

Include the version (`markwell --version`), your OS and Python version, and steps
to reproduce. You can expect an initial response within a few days.
