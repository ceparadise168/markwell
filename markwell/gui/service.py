"""GUI use-cases over the safe core — no HTTP here, so it is unit-testable.

This is *what the graphical front-end can do*: report status, run a backup
(snapshot + export) with live progress, list saved copies, load a library to
read, and reveal folders. Every device or disk operation delegates to the same
`device` / `reader` / `export` modules the CLI uses, so the GUI inherits the
identical safety guarantees: the device is read at most once per backup,
read-only, and never written; snapshots are timestamped and never overwritten.

The data-dir setting is the one fenced exception to the GUI security rule that
nothing the browser sends is used as a filesystem path: the reader may point
Markwell's data folder anywhere — typically inside an existing iCloud/Dropbox/
Drive sync folder, which is how Markwell offers cloud backup without talking
to any cloud API. That single value crosses the fence only through the layered
checks in `_validate_data_dir()` (plus a writability probe), relocation only
ever COPIES — Markwell never moves or deletes user data — and the Kobo itself
stays strictly read-only.
"""
from __future__ import annotations

import datetime
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import zipfile

from . import sample as sample_lib
from .. import __version__, config, device, reader
from ..export import build_files, build_meta, parse_formats, write_outputs
from ..reader import UnsupportedSchemaError
from ..render import json as json_render
from ..render import labels

_SNAP_GLOB = "KoboReader-*.sqlite"
_STAMP_FMT = "%Y%m%d-%H%M%S"


def default_data_dir() -> pathlib.Path:
    """Where the GUI keeps backups and exports by default.

    The CLI uses the current directory (right for a terminal); a GUI is launched
    by double-click, where that is unpredictable, so we use a stable, findable
    home-folder location the UI always shows.
    """
    return pathlib.Path.home() / "Markwell"


def detect_cloud_roots(home=None) -> list[dict]:
    """Cloud-synced folders that already exist on this machine.

    Returns ``[{"id", "label", "path"}]`` — at most one entry per provider,
    the first existing candidate winning. This powers the Settings screen's
    "put my Markwell folder in the cloud" suggestions: Markwell gets cloud
    backup by *living inside* the provider's existing sync folder, never by
    talking to an API.

    Pure read-only probing — `is_dir()` checks and directory globs; nothing
    is created, opened, or written. A module-level function (like
    `default_data_dir`) because it describes the machine, not any Service
    state. `home` is overridable for tests; the default, `pathlib.Path.home()`,
    resolves from %USERPROFILE% on Windows, so the Windows probes below are
    the documented %USERPROFILE%-relative locations.
    """
    home = pathlib.Path.home() if home is None else pathlib.Path(home)
    probes: list = []
    if sys.platform == "darwin":
        storage = home / "Library" / "CloudStorage"
        probes = [
            ("icloud", "iCloud Drive",
             [home / "Library" / "Mobile Documents" / "com~apple~CloudDocs"]),
            ("dropbox", "Dropbox",
             [home / "Dropbox"] + sorted(storage.glob("Dropbox*"))),
            ("gdrive", "Google Drive", sorted(storage.glob("GoogleDrive*"))),
            ("onedrive", "OneDrive",
             sorted(storage.glob("OneDrive*")) + [home / "OneDrive"]),
        ]
    elif sys.platform.startswith("win"):
        onedrive_env = os.environ.get("OneDrive")
        probes = [
            ("icloud", "iCloud Drive", [home / "iCloudDrive"]),
            ("dropbox", "Dropbox", [home / "Dropbox"]),
            ("gdrive", "Google Drive", [home / "Google Drive"]),
            ("onedrive", "OneDrive",
             ([pathlib.Path(onedrive_env)] if onedrive_env else [])
             + [home / "OneDrive"]),
        ]
    elif sys.platform.startswith("linux"):
        probes = [
            ("dropbox", "Dropbox", [home / "Dropbox"]),
            ("gdrive", "Google Drive", [home / "GoogleDrive"]),
            ("onedrive", "OneDrive", [home / "OneDrive"]),
        ]
    roots = []
    for cloud_id, label, candidates in probes:
        for candidate in candidates:
            if candidate.is_dir():
                roots.append({"id": cloud_id, "label": label,
                              "path": str(candidate)})
                break
    return roots


def _validate_data_dir(target) -> pathlib.Path:
    """Validate a proposed Markwell data directory; return it resolved.

    SECURITY — this is the fence around the one exception to "nothing the
    browser sends is used as a filesystem path": the reader's own data-dir
    choice. The chain, in pinned order (each failure is a ValueError whose
    short stable message doubles as an error code for the UI):

      1. expanduser, then require an absolute path -> "path must be absolute"
      2. resolve() (non-strict): symlinks are chased *before* the checks
         below, so a link cannot smuggle the data dir into a refused place
      3. refuse an existing file                   -> "path is a file"
      4. refuse anything inside a mounted Kobo     -> "path is inside the
         Kobo device". Markwell must never write to the device, so its mount
         can never host the data dir. A candidate mount
         (device._candidate_roots) counts only when it actually hosts a Kobo
         database — the same probe detect_device uses — because on Windows
         the candidates are *every* drive letter, and without that
         confirmation every Windows path would be "inside the Kobo". On
         macOS/Linux the candidates are name-matched KOBOeReader mounts,
         which the database probe merely re-confirms.

    The writability probe is deliberately NOT here: change_data_dir() probes
    before committing a user's new choice, but boot-time re-validation of a
    saved choice (resolve_data_dir) must tolerate a cloud folder that simply
    isn't mounted *yet*.
    """
    path = pathlib.Path(target).expanduser()
    if not path.is_absolute():
        raise ValueError("path must be absolute")
    resolved = path.resolve()
    if resolved.is_file():
        raise ValueError("path is a file")
    for root in device._candidate_roots():
        if not (root / device._REL_DB).is_file():
            continue  # a candidate without a Kobo DB is not a device (C:\ …)
        root_str = str(root.resolve())
        try:
            inside = os.path.commonpath([str(resolved), root_str]) == root_str
        except ValueError:  # different drive (Windows): cannot be inside
            inside = False
        if inside:
            raise ValueError("path is inside the Kobo device")
    return resolved


def resolve_data_dir(flag_value: str | None) -> pathlib.Path:
    """The data dir the server should start with.

    Precedence: an explicit --data-dir flag > the saved config choice (if it
    still passes validation) > `default_data_dir()`. The flag is taken as-is —
    whoever types a flag owns it, exactly like the CLI. The saved choice is
    re-validated at every boot because the world changes between runs (a
    folder can become a file; a saved dir can become the Kobo's mount):
    anything invalid is IGNORED with a stderr warning, never an exception — a
    stale config must not be able to wedge startup. No writability probe
    here: a cloud folder may not be mounted yet at boot, and refusing to
    start over that would lock the reader out (see _validate_data_dir).
    """
    if flag_value:
        return pathlib.Path(flag_value).expanduser()
    configured = config.load().get("data_dir")
    if configured is not None:
        try:
            if not isinstance(configured, str):
                raise ValueError("not a string")
            return _validate_data_dir(configured)
        except ValueError as exc:
            print(f"markwell: ignoring saved data_dir {configured!r} ({exc}); "
                  "using the default", file=sys.stderr)
    return default_data_dir()


def _parse_stamp(name: str):
    """'KoboReader-20260601-101010.sqlite' -> datetime, or None if unparseable."""
    stem = name[len("KoboReader-"):-len(".sqlite")] if name.startswith(
        "KoboReader-") and name.endswith(".sqlite") else ""
    try:
        return datetime.datetime.strptime(stem, _STAMP_FMT)
    except ValueError:
        return None


def _coerce_lang(lang) -> str:
    """Clamp a requested export-label language to a locale we ship.

    The value arrives from the browser, so it is untrusted input: anything that
    isn't a known locale — wrong code, wrong type, missing — silently means
    English, so a stale or hand-edited page can never wedge an export."""
    return lang if isinstance(lang, str) and lang in labels.LABELS else "en"


def _reveal(path: pathlib.Path) -> bool:
    """Open a folder in the OS file manager; return whether it launched.

    Path is always a known dir we own — never anything supplied by the browser —
    and no shell is involved. A missing opener (e.g. no `xdg-open` on a minimal
    Linux box) raises OSError, which we report as a clean False instead of
    crashing the request thread."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif sys.platform.startswith("win"):
            import os
            os.startfile(str(path))  # type: ignore[attr-defined]  # Windows-only
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
        return True
    except OSError:
        return False


class ExportJob:
    """State of one in-flight or finished backup, polled by the browser.

    state: idle | running | done | error
    phase: detecting | snapshotting | reading | rendering | done
    """

    def __init__(self) -> None:
        self.state = "idle"
        self.phase = ""
        self.message = ""
        self.result: dict | None = None
        self.error: str | None = None

    def as_dict(self) -> dict:
        return {
            "state": self.state,
            "phase": self.phase,
            "message": self.message,
            "result": self.result,
            "error": self.error,
        }


class Service:
    """The GUI's operations against one data directory."""

    def __init__(self, data_dir, fmt: str = "md,json,html") -> None:
        # Curated default for non-technical users: the readable trio. csv and
        # anki are opt-in — a spreadsheet and a flashcard deck appearing
        # unasked would read as clutter, not value.
        self.data_dir = pathlib.Path(data_dir).expanduser()
        self.backup_dir = self.data_dir / "backups"
        self.out_dir = self.data_dir / "output"
        self.fmt = fmt
        self._job = ExportJob()
        self._lock = threading.Lock()

    # --- queries -------------------------------------------------------------

    def _snapshots(self) -> list[pathlib.Path]:
        if not self.backup_dir.is_dir():
            return []
        return sorted(self.backup_dir.glob(_SNAP_GLOB))

    def status(self) -> dict:
        snaps = self._snapshots()
        dev = device.detect_device()
        return {
            "device_connected": bool(dev and dev.is_file()),
            "snapshot_count": len(snaps),
            "latest_snapshot": snaps[-1].name if snaps else None,
            "has_library": bool(snaps),
            "data_dir": str(self.data_dir),
            "backup_dir": str(self.backup_dir),
            "output_dir": str(self.out_dir),
            "format": self.fmt,
            "version": __version__,
        }

    def snapshot_list(self) -> list[dict]:
        """Saved copies, newest first, as data for the browser to present.

        `stamp` is the snapshot's ISO 8601 local timestamp, or None when the
        filename doesn't carry one (e.g. a hand-renamed copy). Dates, ages and
        sizes are formatted by the frontend in the reader's own locale — no
        presentation text is built here.
        """
        snaps = self._snapshots()
        latest = snaps[-1] if snaps else None
        rows = []
        for p in reversed(snaps):
            when = _parse_stamp(p.name)
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            rows.append({
                "name": p.name,
                "stamp": when.isoformat() if when else None,
                "size_bytes": size,
                "is_latest": p == latest,
            })
        return rows

    def _resolve_source(self, source) -> pathlib.Path | None:
        """Map a source token to a snapshot path. None/'latest' -> newest.

        A specific name must exactly match an existing snapshot (so the browser
        can never point us at an arbitrary path)."""
        snaps = self._snapshots()
        if not snaps:
            return None
        if source in (None, "", "latest"):
            return snaps[-1]
        for p in snaps:
            if p.name == source:
                return p
        return None

    def library(self, source=None) -> dict:
        """A books document (schema markwell/1 + a `source_kind` hint) to read.

        source='sample' -> the built-in sample library; None/'latest' -> newest
        snapshot; a snapshot filename -> that copy; nothing available -> empty.
        """
        if source == "sample":
            doc = json_render.document(sample_lib.library(),
                                       build_meta("sample", "sample"))
            doc["source_kind"] = "sample"
            doc["source_name"] = "Sample library"
            return doc

        path = self._resolve_source(source)
        if path is None:
            return {"schema": "markwell/1", "books": [], "source_kind": "empty",
                    "source_name": None}
        books = reader.read_books(path)
        doc = json_render.document(books,
                                   build_meta(path.name, "cached_snapshot"))
        doc["source_kind"] = "snapshot"
        doc["source_name"] = path.name
        return doc

    # --- commands ------------------------------------------------------------

    def start_export(self, use_device: bool = True, source=None, fmt=None,
                     lang="en") -> bool:
        """Begin a backup in the background. Returns False if one is running.

        `lang` picks the exported files' label language (the browser sends the
        reader's UI language so files match what they see on screen); unknown
        or missing values silently mean English. `fmt` follows the same
        silent-coerce philosophy: it is untrusted browser input with teeth —
        unclamped, an unknown format would render zero files and
        `write_outputs` would then prune every previously exported file as
        stale. Anything `parse_formats` rejects — unknown id, wrong type,
        missing — means the service's configured default, never an error;
        anything it accepts is canonicalized to a comma string."""
        try:
            fmt = ",".join(parse_formats(fmt))
        except ValueError:
            fmt = self.fmt
        with self._lock:
            if self._job.state == "running":
                return False
            self._job = ExportJob()
            self._job.state = "running"
            self._job.phase = "detecting" if use_device else "reading"
            self._job.message = ("Looking for your Kobo…" if use_device
                                 else "Reading your highlights…")
        thread = threading.Thread(
            target=self._run_export,
            args=(use_device, source, fmt, _coerce_lang(lang)),
            daemon=True)
        thread.start()
        return True

    def export_status(self) -> dict:
        with self._lock:
            return self._job.as_dict()

    def _set(self, **fields) -> None:
        with self._lock:
            for key, value in fields.items():
                setattr(self._job, key, value)

    def _run_export(self, use_device: bool, source, fmt: str, lang: str) -> None:
        try:
            if use_device:
                self._set(phase="detecting", message="Looking for your Kobo…")
                dev = device.detect_device()
                if not (dev and dev.is_file()):
                    self._set(state="error", error="no_device", message=(
                        "No Kobo found. Plug it in with the USB cable and "
                        "unlock it, then try again."))
                    return
                self._set(phase="snapshotting",
                          message="Saving a safe copy of your Kobo…")
                stamp = datetime.datetime.now().strftime(_STAMP_FMT)
                src = device.snapshot(dev, self.backup_dir, stamp=stamp)
                freshness = "device"
            else:
                src = self._resolve_source(source)
                if src is None:
                    self._set(state="error", error="no_source",
                              message="That saved copy could not be found.")
                    return
                freshness = "cached_snapshot"

            self._set(phase="reading", message="Reading your highlights…")
            books = reader.read_books(src)
            if not books:
                self._set(state="error", error="empty", message=(
                    "No highlights or notes were found in this Kobo. "
                    "Highlight something on the device and try again."))
                return

            self._set(phase="rendering", message="Preparing your files…")
            meta = build_meta(src.name, freshness, lang=lang)
            files = build_files(books, meta, fmt)
            write_outputs(files, self.out_dir)

            total = sum(len(b.highlights) for b in books)
            self._set(state="done", phase="done", message="All done.", result={
                "books": len(books),
                "highlights": total,
                "source": src.name,
                "freshness": freshness,
                "output_dir": str(self.out_dir),
                "files": len(files),
            })
        except UnsupportedSchemaError:
            self._set(state="error", error="schema", message=(
                "Markwell couldn't read the highlights — this looks like a newer "
                "Kobo than Markwell knows about yet. Your saved copy was kept, so "
                "nothing is lost." if use_device else
                "This saved copy is in a format Markwell doesn't recognize yet."))
        except sqlite3.DatabaseError:
            self._set(state="error", error="unreadable", message=(
                "Markwell couldn't read your Kobo — it may have been unplugged or "
                "busy. Reconnect it and try again." if use_device else
                "This saved copy could not be read — it may be damaged. Try a "
                "different saved copy, or back up your Kobo again."))
        except Exception as exc:  # last-resort: never crash the server thread
            self._set(state="error", error="unexpected",
                      message=f"Something unexpected went wrong: {exc}")

    def open_folder(self, which: str = "data") -> bool:
        """Reveal one of our known folders. `which` is data | backups | output."""
        target = {
            "data": self.data_dir,
            "backups": self.backup_dir,
            "output": self.out_dir,
        }.get(which)
        if target is None:
            return False
        target.mkdir(parents=True, exist_ok=True)
        _reveal(target)
        return True

    # --- settings & archive ----------------------------------------------------

    def change_data_dir(self, target) -> dict:
        """Relocate the data dir to `target` by COPYING — never move or delete.

        SECURITY: `target` ultimately comes from the browser — the one fenced
        exception to "nothing the browser sends is used as a filesystem
        path". It must pass `_validate_data_dir`'s chain, then mkdir + a
        writability probe (either failing -> ValueError "path is not
        writable" — mkdir failing IS a way of not being writable).

        Copy-only relocation: existing snapshots (backups/KoboReader-*.sqlite)
        and the whole output/ tree are copied over, skipping any name already
        present at the destination — so a retry never re-copies and NEVER
        overwrites a destination file — and the old folder is left exactly as
        it was. The reader deletes the old copy themselves, if and when they
        choose; Markwell has no code path that deletes user data.

        Concurrency: refused while an export runs, and the directory switch
        happens under the job lock, so a running export always sees one
        consistent set of directories. An export that slips in *during* the
        copy makes the final switch raise the same RuntimeError; the files
        already copied are harmless and a retry skips them.
        """
        with self._lock:
            if self._job.state == "running":
                raise RuntimeError("export running")
        resolved = _validate_data_dir(target)
        try:
            resolved.mkdir(parents=True, exist_ok=True)
            # Probe with a real file: mkdir alone can succeed where writes
            # would fail (read-only remount, quota). Auto-removed on close.
            with tempfile.NamedTemporaryFile(dir=str(resolved)):
                pass
        except OSError:
            raise ValueError("path is not writable")

        old_data = self.data_dir
        old_backup, old_out = self.backup_dir, self.out_dir
        new_backup, new_out = resolved / "backups", resolved / "output"

        copied_snapshots = 0
        if old_backup.is_dir():
            new_backup.mkdir(parents=True, exist_ok=True)
            for snap in sorted(old_backup.glob(_SNAP_GLOB)):
                dest = new_backup / snap.name
                if dest.exists():
                    continue
                shutil.copy2(snap, dest)
                copied_snapshots += 1

        copied_outputs = 0
        if old_out.is_dir():
            # sorted() materializes the walk BEFORE the first copy, so a
            # target nested under the old tree can never re-discover (and
            # endlessly re-copy) its own fresh copies.
            for src in sorted(p for p in old_out.rglob("*") if p.is_file()):
                dest = new_out / src.relative_to(old_out)
                if dest.exists():
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                copied_outputs += 1

        with self._lock:
            if self._job.state == "running":
                raise RuntimeError("export running")
            self.data_dir = resolved
            self.backup_dir = new_backup
            self.out_dir = new_out
        config.save({**config.load(), "data_dir": str(resolved)})
        return {"old": str(old_data), "new": str(resolved),
                "copied_snapshots": copied_snapshots,
                "copied_outputs": copied_outputs}

    def make_archive(self) -> dict:
        """Bundle the library into one ZIP for sharing or cold storage.

        Contents: every file under output/ (arcname ``output/<rel>``) plus
        the LATEST snapshot only (arcname ``backups/<name>``) — the freshest
        complete pair, not a growing pile of history. The zip is written to
        the data-dir ROOT, not under output/ or backups/, so the output walk
        and the KoboReader-*.sqlite glob can never sweep an old archive into
        a new one. Read-only with respect to user data: sources are only
        read, never moved or deleted.
        """
        with self._lock:
            if self._job.state == "running":
                raise RuntimeError("export running")
        snaps = self._snapshots()
        latest = snaps[-1] if snaps else None
        out_files = []
        if self.out_dir.is_dir():
            out_files = sorted(p for p in self.out_dir.rglob("*")
                               if p.is_file())
        if latest is None and not out_files:
            raise ValueError("nothing to archive")
        stamp = datetime.datetime.now().strftime(_STAMP_FMT)
        name = f"Markwell-archive-{stamp}.zip"
        path = self.data_dir / name
        files = 0
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            for src in out_files:
                zf.write(src,
                         "output/" + src.relative_to(self.out_dir).as_posix())
                files += 1
            if latest is not None:
                zf.write(latest, "backups/" + latest.name)
                files += 1
        return {"name": name, "path": str(path), "files": files}
