"""Find a connected Kobo and snapshot its database safely.

The device DB is opened READ-ONLY and copied via SQLite's online-backup API
(consistent even with an active WAL). Snapshots are timestamped and never
overwritten; a failed backup never clobbers an existing snapshot.
"""
from __future__ import annotations

import getpass
import glob
import pathlib
import sqlite3
import string
import sys

_REL_DB = pathlib.Path(".kobo") / "KoboReader.sqlite"


def _candidate_roots():
    """Likely Kobo mount points, per platform."""
    if sys.platform == "darwin":
        return [pathlib.Path("/Volumes/KOBOeReader")]
    if sys.platform.startswith("linux"):
        user = getpass.getuser()
        roots = [
            pathlib.Path(f"/media/{user}/KOBOeReader"),
            pathlib.Path(f"/run/media/{user}/KOBOeReader"),
        ]
        roots += [pathlib.Path(p) for p in glob.glob("/media/*/KOBOeReader")]
        roots += [pathlib.Path(p) for p in glob.glob("/mnt/*/KOBOeReader")]
        return roots
    if sys.platform.startswith("win"):
        return [pathlib.Path(f"{c}:/") for c in string.ascii_uppercase]
    return []


def detect_device():
    """Return the path to a connected Kobo's KoboReader.sqlite, or None."""
    for root in _candidate_roots():
        db = root / _REL_DB
        if db.is_file():
            return db
    return None


def snapshot(src, backup_dir, *, stamp):
    """Snapshot the device DB read-only to a timestamped local file; return its path.

    `stamp` is a 'YYYYmmdd-HHMMSS' string, passed in so callers own the clock.
    Writes to a .tmp and atomically renames on success.
    """
    backup_dir = pathlib.Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / f"KoboReader-{stamp}.sqlite"
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.unlink(missing_ok=True)

    src_uri = pathlib.Path(src).resolve().as_uri() + "?mode=ro"
    try:
        source = sqlite3.connect(src_uri, uri=True)
        try:
            snap = sqlite3.connect(str(tmp))
            try:
                source.backup(snap)
            finally:
                snap.close()
        finally:
            source.close()
        tmp.replace(dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return dest
