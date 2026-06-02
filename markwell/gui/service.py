"""GUI use-cases over the safe core — no HTTP here, so it is unit-testable.

This is *what the graphical front-end can do*: report status, run a backup
(snapshot + export) with live progress, list saved copies, load a library to
read, and reveal folders. Every device or disk operation delegates to the same
`device` / `reader` / `export` modules the CLI uses, so the GUI inherits the
identical safety guarantees: the device is read at most once per backup,
read-only, and never written; snapshots are timestamped and never overwritten.
"""
from __future__ import annotations

import datetime
import pathlib
import sqlite3
import subprocess
import sys
import threading

from . import sample as sample_lib
from .. import __version__, device, reader
from ..export import build_files, write_outputs
from ..reader import UnsupportedSchemaError
from ..render import json as json_render

_SNAP_GLOB = "KoboReader-*.sqlite"
_STAMP_FMT = "%Y%m%d-%H%M%S"


def default_data_dir() -> pathlib.Path:
    """Where the GUI keeps backups and exports by default.

    The CLI uses the current directory (right for a terminal); a GUI is launched
    by double-click, where that is unpredictable, so we use a stable, findable
    home-folder location the UI always shows.
    """
    return pathlib.Path.home() / "Markwell"


def _today() -> str:
    return datetime.date.today().isoformat()


def _parse_stamp(name: str):
    """'KoboReader-20260601-101010.sqlite' -> datetime, or None if unparseable."""
    stem = name[len("KoboReader-"):-len(".sqlite")] if name.startswith(
        "KoboReader-") and name.endswith(".sqlite") else ""
    try:
        return datetime.datetime.strptime(stem, _STAMP_FMT)
    except ValueError:
        return None


def _fmt_when(when: datetime.datetime) -> str:
    """A friendly local timestamp, built without platform-specific strftime
    codes (%-d / %-I are glibc/BSD-only and crash on Windows)."""
    hour12 = ((when.hour - 1) % 12) + 1
    return f"{when:%b} {when.day}, {when.year} · {hour12}:{when.minute:02d} {when:%p}"


def _human_age(when: datetime.datetime, now: datetime.datetime) -> str:
    """A friendly relative age: 'just now', 'today', 'yesterday', 'N days ago'."""
    if when is None:
        return ""
    delta = now - when
    secs = delta.total_seconds()
    if secs < 90:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)} minutes ago"
    days = (now.date() - when.date()).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    if days < 365:
        return f"{days // 30} months ago"
    return f"{days // 365} years ago"


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

    def __init__(self, data_dir, fmt: str = "all") -> None:
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
        """Saved copies, newest first, described in plain language."""
        snaps = self._snapshots()
        latest = snaps[-1] if snaps else None
        now = datetime.datetime.now()
        rows = []
        for p in reversed(snaps):
            when = _parse_stamp(p.name)
            try:
                size = p.stat().st_size
            except OSError:
                size = 0
            rows.append({
                "name": p.name,
                "date": _fmt_when(when) if when else p.name,
                "age": _human_age(when, now),
                "size_kb": round(size / 1024),
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
            doc = json_render.document(sample_lib.library(), {
                "generated": _today(), "source": "sample",
                "source_freshness": "sample", "version": __version__})
            doc["source_kind"] = "sample"
            doc["source_name"] = "Sample library"
            return doc

        path = self._resolve_source(source)
        if path is None:
            return {"schema": "markwell/1", "books": [], "source_kind": "empty",
                    "source_name": None}
        books = reader.read_books(path)
        doc = json_render.document(books, {
            "generated": _today(), "source": path.name,
            "source_freshness": "cached_snapshot", "version": __version__})
        doc["source_kind"] = "snapshot"
        doc["source_name"] = path.name
        return doc

    # --- commands ------------------------------------------------------------

    def start_export(self, use_device: bool = True, source=None, fmt=None) -> bool:
        """Begin a backup in the background. Returns False if one is running."""
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
            args=(use_device, source, fmt or self.fmt),
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

    def _run_export(self, use_device: bool, source, fmt: str) -> None:
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
            meta = {"generated": _today(), "source": src.name,
                    "source_freshness": freshness, "version": __version__}
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
