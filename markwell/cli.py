"""Command-line entry point: detect → snapshot → read → render → write."""
from __future__ import annotations

import argparse
import datetime
import pathlib
import sys

from . import device, reader
from .render import json as json_render
from .render import markdown as md_render


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
    """Decide which DB to read from, snapshotting the device at most once."""
    if args.db:
        p = pathlib.Path(args.db)
        if not p.is_file():
            sys.exit(f"--db not found: {args.db}")
        return p

    dev = _device_db(args.device) if args.device else device.detect_device()
    if dev and dev.is_file():
        snap = device.snapshot(dev, args.backup_dir, stamp=stamp)
        print(f"✓ snapshot {snap.name} → {args.backup_dir}/")
        return snap

    snaps = sorted(pathlib.Path(args.backup_dir).glob("KoboReader-*.sqlite"))
    if snaps:
        print(f"⚠ device not connected — using latest snapshot {snaps[-1].name}")
        return snaps[-1]

    sys.exit("No Kobo device and no local snapshot found.\n"
             "Plug in the Kobo, or pass --db PATH to a KoboReader.sqlite.")


def _write(files, out_dir):
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")
    return len(files)


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
    ap.add_argument("--out", default="output", help="output dir (default: output)")
    ap.add_argument("--backup-dir", default="backups",
                    help="snapshot dir (default: backups)")
    args = ap.parse_args(argv)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    if args.snapshot_only:
        dev = _device_db(args.device) if args.device else device.detect_device()
        if not (dev and dev.is_file()):
            sys.exit("No Kobo device found. Plug in the Kobo.")
        snap = device.snapshot(dev, args.backup_dir, stamp=stamp)
        print(f"✓ snapshot {snap.name} → {args.backup_dir}/")
        return

    src = _resolve_source(args, stamp=stamp)
    books = reader.read_books(src)
    if not books:
        sys.exit("No highlights or notes found in the database.")

    meta = {"generated": datetime.date.today().isoformat(),
            "source": pathlib.Path(src).name}
    files = {}
    if args.format in ("md", "all"):
        files.update(md_render.render(books, meta))
    if args.format in ("json", "all"):
        files.update(json_render.render(books, meta))

    n = _write(files, args.out)
    total = sum(len(b.highlights) for b in books)
    print(f"✓ {total} highlights/notes · {len(books)} books "
          f"→ {args.out}/ ({n} files)")
    print(f"  source: {src}")
