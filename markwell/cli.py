"""Command-line entry point: detect → snapshot → read → render → write."""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sqlite3
import sys

from . import __version__, device, reader
from .reader import UnsupportedSchemaError
from .render import json as json_render
from .render import markdown as md_render

_MANIFEST = ".markwell-manifest.json"


def _device_db(spec):
    """Resolve a --device value to a KoboReader.sqlite path.

    Accepts either the Kobo mount root (we append .kobo/KoboReader.sqlite) or a
    direct path to a KoboReader.sqlite file.
    """
    p = pathlib.Path(spec)
    if p.is_dir():
        return p / ".kobo" / "KoboReader.sqlite"
    return p


def _resolve_source(args, *, stamp):
    """Decide which DB to read from, snapshotting the device at most once.

    Returns (path, freshness) where freshness is "device" for a snapshot taken
    this run or "cached_snapshot" for a fallback to an existing local snapshot.
    """
    if args.db:
        p = pathlib.Path(args.db)
        if not p.is_file():
            print(f"--db not found: {args.db}", file=sys.stderr)
            sys.exit(2)
        return p, "cached_snapshot"

    if args.device:
        dev = _device_db(args.device)
        if not dev.is_file():
            print(f"--device path has no KoboReader.sqlite: {dev}", file=sys.stderr)
            sys.exit(2)
    else:
        dev = device.detect_device()

    if dev and dev.is_file():
        snap = device.snapshot(dev, args.backup_dir, stamp=stamp)
        print(f"✓ snapshot {snap.name} → {args.backup_dir}/", file=sys.stderr)
        return snap, "device"

    if args.require_device:
        print("No Kobo device connected (--require-device).", file=sys.stderr)
        sys.exit(2)

    snaps = sorted(pathlib.Path(args.backup_dir).glob("KoboReader-*.sqlite"))
    if snaps:
        print(f"⚠ device not connected — using latest snapshot {snaps[-1].name}",
              file=sys.stderr)
        return snaps[-1], "cached_snapshot"

    print("No Kobo device and no local snapshot found.\n"
          "Plug in the Kobo, or pass --db PATH to a KoboReader.sqlite.",
          file=sys.stderr)
    sys.exit(2)


def _write(files, out_dir):
    """Write files atomically and prune stale Markwell-generated outputs.

    Each file is written to name+".tmp" then replaced into place, so a crash
    mid-export never leaves a truncated file. A manifest of the names Markwell
    generated is kept in the output dir; on the next run, only files recorded in
    the prior manifest that are no longer generated are removed — files Markwell
    never wrote (e.g. the user's own .md notes) are left untouched.
    """
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        dest = out / name
        tmp = dest.with_name(dest.name + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(dest)

    manifest = out / _MANIFEST
    try:
        prior = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        prior = []
    if not isinstance(prior, list):  # corrupt/unexpected manifest -> delete nothing
        prior = []
    for name in prior:
        if not isinstance(name, str):
            continue
        if name in files or name == _MANIFEST:
            continue
        stale = out / name
        if stale.is_file():
            stale.unlink()
    manifest.write_text(
        json.dumps(sorted(files), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return len(files)


def _run(args):
    """Do the actual work; main() wraps this for clean error handling."""
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    if args.snapshot_only:
        if args.device:
            dev = _device_db(args.device)
            if not dev.is_file():
                print(f"--device path has no KoboReader.sqlite: {dev}",
                      file=sys.stderr)
                sys.exit(2)
        else:
            dev = device.detect_device()
        if not (dev and dev.is_file()):
            print("No Kobo device found. Plug in the Kobo.", file=sys.stderr)
            sys.exit(2)
        snap = device.snapshot(dev, args.backup_dir, stamp=stamp)
        print(f"✓ snapshot {snap.name} → {args.backup_dir}/", file=sys.stderr)
        return

    src, freshness = _resolve_source(args, stamp=stamp)
    books = reader.read_books(src)
    if not books:
        print("No highlights or notes found in the database.", file=sys.stderr)
        sys.exit(3)

    meta = {"generated": datetime.date.today().isoformat(),
            "source": pathlib.Path(src).name,
            "source_freshness": freshness,
            "version": __version__}
    files = {}
    if args.format in ("md", "all"):
        files.update(md_render.render(books, meta))
    if args.format in ("json", "all"):
        files.update(json_render.render(books, meta))

    n = _write(files, args.out)
    total = sum(len(b.highlights) for b in books)
    print(f"✓ {total} highlights/notes · {len(books)} books "
          f"→ {args.out}/ ({n} files)", file=sys.stderr)
    print(f"  source: {src}", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="markwell",
        description="Safely back up and export Kobo highlights and notes.")
    ap.add_argument("--format", choices=["md", "json", "all"], default="all",
                    help="what to export (default: all)")
    ap.add_argument("--snapshot-only", action="store_true",
                    help="snapshot the device and exit (no export)")
    ap.add_argument("--db", help="export from a snapshot (skips device read)")
    ap.add_argument("--device", help="Kobo mount point or KoboReader.sqlite path (overrides auto-detection)")
    ap.add_argument("--require-device", action="store_true",
                    help="fail if no live device is found (never fall back to a snapshot)")
    ap.add_argument("--out", default="output", help="output dir (default: output)")
    ap.add_argument("--backup-dir", default="backups",
                    help="snapshot dir (default: backups)")
    ap.add_argument("--debug", action="store_true",
                    help="show full tracebacks instead of clean error messages")
    ap.add_argument("--version", action="version", version=f"markwell {__version__}")
    args = ap.parse_args(argv)

    try:
        _run(args)
    except UnsupportedSchemaError as e:
        if args.debug:
            raise
        print(e, file=sys.stderr)
        sys.exit(4)
    except sqlite3.DatabaseError as e:
        if args.debug:
            raise
        print(f"Could not read the Kobo database (corrupt or unreadable): {e}",
              file=sys.stderr)
        sys.exit(4)
    except (OSError, sqlite3.Error) as e:
        if args.debug:
            raise
        print(f"Kobo disconnected during backup — reconnect and retry ({e})",
              file=sys.stderr)
        sys.exit(4)
