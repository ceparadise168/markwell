"""Find a connected Kobo and snapshot its database without touching the device.

A Kobo normally runs its DB in WAL mode, so the on-device KoboReader.sqlite has
live `-wal`/`-shm` siblings. We never open the device DB directly (that would
create/rewrite those files and fail on a read-only mount). Instead we *copy* the
main file and any `-wal`/`-shm` siblings into a local staging dir, open the copy
so SQLite replays the WAL, then back that up into the snapshot. Snapshots are
timestamped and never overwritten; a failed backup never clobbers an existing one.
"""
from __future__ import annotations

import getpass
import glob
import os
import pathlib
import shutil
import sqlite3
import string
import sys
import tempfile

_REL_DB = pathlib.Path(".kobo") / "KoboReader.sqlite"


def _candidate_roots() -> list[pathlib.Path]:
    """Likely Kobo mount points, per platform."""
    if sys.platform == "darwin":
        return [pathlib.Path(p) for p in glob.glob("/Volumes/KOBOeReader*")]
    if sys.platform.startswith("linux"):
        try:
            user = getpass.getuser()
        except Exception:  # no passwd entry / no USER env — don't crash detection
            user = None
        roots = [pathlib.Path(f"/media/{user}/KOBOeReader"),
                 pathlib.Path(f"/run/media/{user}/KOBOeReader")] if user else []
        roots += [pathlib.Path(p) for p in glob.glob("/media/*/KOBOeReader")]
        roots += [pathlib.Path(p) for p in glob.glob("/mnt/*/KOBOeReader")]
        return roots
    if sys.platform.startswith("win"):
        # Skip A:/B: (legacy floppy letters) and only probe drives that exist.
        return [pathlib.Path(f"{c}:/") for c in string.ascii_uppercase[2:]
                if os.path.exists(f"{c}:/")]
    return []


def detect_device() -> pathlib.Path | None:
    """Return the path to a connected Kobo's KoboReader.sqlite, or None."""
    for root in _candidate_roots():
        db = root / _REL_DB
        if db.is_file():
            return db
    return None


def _verify_snapshot(path: pathlib.Path) -> None:
    """Raise if `path` is not a sound Kobo snapshot (integrity + Bookmark table)."""
    uri = path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise sqlite3.DatabaseError("snapshot failed integrity_check")
        if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='Bookmark'"
        ).fetchone() is None:
            raise sqlite3.DatabaseError("snapshot is missing the Bookmark table")
    finally:
        conn.close()


def snapshot(src, backup_dir, *, stamp) -> pathlib.Path:
    """Snapshot the device DB to a timestamped local file; return its path.

    Reads the device only via file copy (no SQLite handle on the device, so it
    works on read-only mounts and never creates `-wal`/`-shm` there): the main
    file and any `-wal`/`-shm` siblings are copied into a local staging dir, the
    copy is opened so the WAL replays, and that is backed up into the snapshot.

    `stamp` is a 'YYYYmmdd-HHMMSS' string, passed in so callers own the clock.
    The snapshot is verified, written to a .tmp, and atomically renamed on success.
    """
    src = pathlib.Path(src)
    backup_dir = pathlib.Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / f"KoboReader-{stamp}.sqlite"
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.unlink(missing_ok=True)

    # Staging lives under backup_dir so the final replace() is a same-filesystem
    # rename. mkdtemp keeps concurrent snapshots from colliding.
    stage = pathlib.Path(tempfile.mkdtemp(prefix=".stage-", dir=backup_dir))
    try:
        staged = stage / "KoboReader.sqlite"
        shutil.copy2(src, staged)
        for suffix in ("-wal", "-shm"):
            sibling = pathlib.Path(str(src) + suffix)
            if sibling.exists():
                shutil.copy2(sibling, pathlib.Path(str(staged) + suffix))

        source = sqlite3.connect(str(staged))  # local copy: WAL replays on open
        try:
            # Fold the WAL into the main file and drop WAL mode so the snapshot
            # is a single self-contained file (no -wal/-shm siblings to manage).
            source.execute("PRAGMA journal_mode=DELETE")
            snap = sqlite3.connect(str(tmp))
            try:
                source.backup(snap)
            finally:
                snap.close()
        finally:
            source.close()

        _verify_snapshot(tmp)
        tmp.replace(dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return dest
