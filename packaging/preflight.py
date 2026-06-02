#!/usr/bin/env python3
"""Release artifact privacy preflight.

Walk a built release tree and fail if it contains anything that must never ship —
Kobo snapshots, exports, backups, SQLite databases, or local caches. The forbidden
definitions live in ``_forbidden.py`` so this gate and the PyInstaller spec can
never drift apart. Run it against every artifact before publishing:

    python3 packaging/preflight.py dist

Exit status is 0 when the tree is clean, 1 when anything forbidden is found, and 2
on a usage error, so it can gate a release in CI.
"""
from __future__ import annotations

import sys
from pathlib import Path

from _forbidden import forbidden_reason


def scan(root: Path):
    """Yield ``(relative_path, reason)`` for every forbidden entry under ``root``."""
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        reason = forbidden_reason(rel)
        if reason:
            yield rel, reason


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("usage: preflight.py <release-tree>", file=sys.stderr)
        return 2
    root = Path(args[0])
    if not root.exists():
        print("preflight: path does not exist: %s" % root, file=sys.stderr)
        return 2

    violations = list(scan(root))
    if violations:
        print("FAILED: %d forbidden item(s) in %s" % (len(violations), root))
        for rel, reason in violations:
            print("  %s — %s" % (rel, reason))
        return 1
    print("OK: no private data in %s" % root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
