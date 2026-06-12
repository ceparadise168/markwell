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
- **UI strings — including all translations — reach the page only through
  `textContent` and attribute setters, never `innerHTML`**, so the locale
  dictionary can never become a markup-injection vector.
- **Nothing the browser sends is used as a filesystem path or shell command**,
  with one fenced exception — the Settings "custom path" field, where you point
  Markwell's data folder somewhere of your choosing. The suggested cloud
  folders and the home-folder default are resolved entirely server-side; only
  that custom value crosses, and it must pass a validation fence: absolute-only
  → symlink-resolved → never a file → never inside a connected Kobo → a
  writability probe. Changing folders only ever **copies** — the old folder is
  left untouched; Markwell has no code path that deletes user data. "Open
  folder" can only reveal Markwell's own data directories, via an argument list
  (never a shell). It still **never writes to your Kobo.**
- **A saved folder choice is re-validated at every launch** — including the
  Kobo check, against whatever device is plugged in now — and ignored with a
  warning if it no longer passes. The `--data-dir` command-line flag is exempt
  by design: whoever types a flag owns it, exactly like the CLI.
- **Settings live in `~/.markwell/config.json`** — it holds only the folder
  path, never a secret, and is stored outside the data folder, so it is never
  swept into a cloud-synced library.
- **Symlinks are never followed** when archiving or relocating your library —
  and Markwell never creates any — so a link planted in a synced folder cannot
  pull outside content into an archive you share.
- **Archives are named to the second and written atomically** — a half-written
  ZIP is never left behind for cloud sync to spread; a second archive within
  the same second replaces the first.
- It makes **no network connections** and runs only while you keep it open.

## Reporting a vulnerability

Please report security issues privately rather than opening a public issue.

- Use GitHub's **"Report a vulnerability"** (Security → Advisories) on the
  repository, or
- email the maintainer at the address listed on the GitHub profile.

Include the version (`markwell --version`), your OS and Python version, and steps
to reproduce. You can expect an initial response within a few days.
