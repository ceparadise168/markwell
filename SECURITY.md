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

## The local GUI app (`markwell-gui`)

The optional graphical app runs a small local web server so your browser can be
the interface. It is hardened to stay private to your machine:

- **Binds `127.0.0.1` only**, on an automatically chosen free port — it is never
  reachable from the network.
- **Every `/api/*` request requires a per-launch secret token** embedded in the
  page, so other programs or web pages on your machine can't drive it (CSRF).
- **The `Host` header is allow-listed** to `127.0.0.1`/`localhost`, blocking
  DNS-rebinding attacks.
- **No CORS headers are sent**, so browsers refuse cross-origin reads, and a
  **Content-Security-Policy** backs up the escaping of (untrusted) book text.
- **Nothing the browser sends is used as a filesystem path or shell command** —
  "Open folder" can only reveal Markwell's own data directories, via an argument
  list (never a shell). It still **never writes to your Kobo.**
- It makes **no network connections** and runs only while you keep it open.

## Reporting a vulnerability

Please report security issues privately rather than opening a public issue.

- Use GitHub's **"Report a vulnerability"** (Security → Advisories) on the
  repository, or
- email the maintainer at the address listed on the GitHub profile.

Include the version (`markwell --version`), your OS and Python version, and steps
to reproduce. You can expect an initial response within a few days.
