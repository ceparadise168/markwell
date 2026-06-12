"""Single source of truth for data that must never ship in a release artifact.

Markwell's core promise is local-first privacy, so a release must never bundle a
reader's Kobo snapshots (finished or interrupted), exports, backups, archives,
SQLite databases, or local caches. The
PyInstaller spec (input filter) and the release preflight (output scan) both import
these definitions from here — a drift between the two would be a privacy hole.

Matching is by path *component* and by file suffix, not by a root-anchored glob, so
the same rule holds whether the path is repo-relative (spec) or buried deep inside
dist/ (preflight).
"""
from __future__ import annotations

from pathlib import Path

# Directory names that must never appear anywhere in a release tree.
FORBIDDEN_DIR_NAMES = (
    ".kobo",
    "output",
    "backups",
    ".playwright-mcp",
    ".pytest_cache",
    "__pycache__",
)

# File suffixes that must never appear anywhere in a release tree. The .tmp
# variant matters: an interrupted backup leaves a complete snapshot behind as
# KoboReader-<stamp>.sqlite.tmp, which is exactly as private as the real thing.
FORBIDDEN_SUFFIXES = (
    ".sqlite",
    ".sqlite-shm",
    ".sqlite-wal",
    ".sqlite.tmp",
)

# The GUI's "pack & go" archive bundles the reader's whole library plus their
# latest snapshot — name-scoped (never bare ".zip") so release zips like
# Markwell-macOS.zip stay shippable.
_ARCHIVE_PREFIX = "markwell-archive-"
_ARCHIVE_SUFFIXES = (".zip", ".zip.tmp")


def forbidden_reason(path) -> str | None:
    """Return a short reason if ``path`` is release-forbidden, else ``None``."""
    p = Path(path)
    forbidden_dirs = set(p.parts) & set(FORBIDDEN_DIR_NAMES)
    if forbidden_dirs:
        return "forbidden path segment %r" % sorted(forbidden_dirs)[0]
    name = p.name.lower()
    for suffix in FORBIDDEN_SUFFIXES:
        if name.endswith(suffix):
            return "forbidden file type %r" % suffix
    if name.startswith(_ARCHIVE_PREFIX) and name.endswith(_ARCHIVE_SUFFIXES):
        return "forbidden file type 'Markwell archive'"
    return None
