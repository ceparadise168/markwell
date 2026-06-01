#!/usr/bin/env python3
"""Export all Kobo highlights to per-book Markdown files.

Safety model: the device is touched at most once per run — to take a consistent
local snapshot via SQLite's online backup API (read-only on the source). Every
export then reads from that local snapshot, never directly from the device.

    backups/
    └── KoboReader-YYYYMMDD-HHMMSS.sqlite   timestamped, never overwritten
    output/
    ├── index.md          all books, counts, links
    └── <book>.md         one file per book, highlights in reading order

No third-party dependencies — Python 3 standard library only.

Usage:
    python3 kobo_highlights.py                 # snapshot device (if plugged in), then export
    python3 kobo_highlights.py --backup-only    # just snapshot the device, no export
    python3 kobo_highlights.py --db PATH        # export from a specific snapshot (no device read)
    python3 kobo_highlights.py --out DIR         # write somewhere other than ./output
"""

import argparse
import pathlib
import re
import sqlite3
import sys
from collections import OrderedDict
from datetime import date, datetime

# Live device DB — only ever read once, to take a snapshot.
DEVICE_DB = "/Volumes/KOBOeReader/.kobo/KoboReader.sqlite"

# Local snapshots live here: timestamped, never overwritten.
BACKUP_DIR = pathlib.Path(__file__).resolve().parent / "backups"

# Older manual copy of the device tree, used as a last-resort fallback.
LEGACY_SNAPSHOT = "./.kobo/KoboReader.sqlite"

EN_DASH = "–"  # – used for year ranges


def backup_device_db(src=DEVICE_DB):
    """Snapshot the live device DB to a timestamped local file.

    Uses SQLite's online backup API: the source is opened read-only and copied
    into a single consistent .sqlite (handles WAL automatically). Writes to a
    .tmp first and renames on success, so a failed backup never clobbers an
    existing snapshot. Returns the snapshot path.
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = BACKUP_DIR / f"KoboReader-{stamp}.sqlite"
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

    size_kb = dest.stat().st_size / 1024
    print(f"✓ snapshot {dest.name} ({size_kb:.0f} KB) → {BACKUP_DIR}/")
    return dest


def latest_snapshot():
    """Most recent local snapshot, or None."""
    snaps = sorted(BACKUP_DIR.glob("KoboReader-*.sqlite"))
    return snaps[-1] if snaps else None


def resolve_source(explicit):
    """Decide which database to export from, without ever reading the device twice.

    --db PATH      → that file (no device read)
    device present → take a fresh snapshot, export from it
    else snapshot  → newest local snapshot
    else legacy    → ./.kobo/KoboReader.sqlite
    else           → exit with guidance
    """
    if explicit:
        p = pathlib.Path(explicit)
        if not p.is_file():
            sys.exit(f"--db not found: {explicit}")
        return p

    if pathlib.Path(DEVICE_DB).is_file():
        return backup_device_db(DEVICE_DB)

    snap = latest_snapshot()
    if snap:
        print(f"⚠ device not connected — using latest snapshot {snap.name}")
        return snap

    legacy = pathlib.Path(LEGACY_SNAPSHOT)
    if legacy.is_file():
        print(f"⚠ device not connected — using legacy copy {legacy}")
        return legacy

    sys.exit("No Kobo device and no local snapshot found.\n"
             "Plug in the Kobo, or pass --db PATH to a KoboReader.sqlite.")


def fetch_highlights(db_path):
    """Read every text highlight, joined to its book, in reading order."""
    uri = pathlib.Path(db_path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT b.VolumeID   AS vid,
                   c.Title      AS title,
                   c.Attribution AS author,
                   b.Text       AS text,
                   b.DateCreated AS created,
                   b.ContentID  AS chap
            FROM Bookmark b
            LEFT JOIN content c ON b.VolumeID = c.ContentID
            WHERE b.Type = 'highlight'
              AND b.Text IS NOT NULL
              AND TRIM(b.Text) <> ''
              AND COALESCE(b.Hidden, 0) NOT IN (1, '1', 'true', 'TRUE')
            ORDER BY b.VolumeID, b.ContentID, b.ChapterProgress, b.StartOffset
        """).fetchall()
    finally:
        conn.close()
    return rows


def main_title(title):
    """The headline part of a title — drop the subtitle after the first colon."""
    if not title:
        return ""
    for sep in ("：", ":"):  # fullwidth ：, then ASCII :
        if sep in title:
            return title.split(sep, 1)[0].strip()
    return title.strip()


def first_author(author):
    return author.split(",", 1)[0].strip() if author else ""


def fmt_date(created):
    """'2024-03-17T10:10:53.000' -> '2024-03-17'; missing -> ''."""
    return created[:10] if created else ""


def sanitize_filename(title, used):
    """Filesystem- and link-safe stem derived from the book's main title."""
    name = main_title(title) or "book"
    name = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "", name)  # strip unsafe chars
    name = re.sub(r"\s+", "_", name).strip("._ ")       # spaces -> _, trim
    if len(name) > 50:
        name = name[:50].rstrip("._ ")
    name = name or "book"
    base, i = name, 2
    while name in used:                                  # dedupe collisions
        name, i = f"{base}-{i}", i + 1
    used.add(name)
    return name


def group_by_book(rows):
    """Group ordered rows by book; tag each highlight with a reading-order chapter no."""
    books = OrderedDict()
    for r in rows:
        book = books.setdefault(r["vid"], {
            "title": r["title"] or r["vid"],
            "author": (r["author"] or "").strip(),
            "highlights": [],
            "_prev_chap": None,
            "_chap_n": 0,
        })
        if r["chap"] != book["_prev_chap"]:
            book["_chap_n"] += 1
            book["_prev_chap"] = r["chap"]
        book["highlights"].append({
            "text": re.sub(r"\s+", " ", r["text"]).strip(),  # collapse to one line
            "date": fmt_date(r["created"]),
            "chap_n": book["_chap_n"],
        })
    return books


def year_range(highlights):
    years = [h["date"][:4] for h in highlights if h["date"]]
    if not years:
        return ""
    lo, hi = min(years), max(years)
    return lo if lo == hi else f"{lo}{EN_DASH}{hi}"


def render_book(book):
    """Build the Markdown for a single book file."""
    hl = book["highlights"]
    yr = year_range(hl)
    count = f"{len(hl)} highlight" + ("s" if len(hl) != 1 else "")
    meta = " · ".join(filter(None, [book["author"], count, yr]))
    blocks = [f"# {book['title']}", meta]

    last_chap = None
    for h in hl:
        if h["chap_n"] != last_chap:
            blocks.append(f"── ch.{h['chap_n']} ──")
            last_chap = h["chap_n"]
        quote = f"> {h['text']}"
        if h["date"]:
            quote += f"\n>\n> *↳ {h['date']}*"
        blocks.append(quote)
    return "\n\n".join(blocks) + "\n"


def render_index(meta, source, generated):
    total = sum(b["count"] for b in meta)
    all_years = [y for b in meta for y in (b["year"],) if y]
    span = ""
    if all_years:
        lo = min(y[:4] for y in all_years)
        hi = max(y[-4:] for y in all_years)
        span = lo if lo == hi else f"{lo}{EN_DASH}{hi}"

    lines = [
        "# Kobo Highlights",
        "",
        f"**{total} highlights** across **{len(meta)} books**"
        + (f" · {span}" if span else ""),
        "",
        f"Generated {generated} · source `{source}`",
        "",
        "| Book | Author | Highlights | Years |",
        "|---|---|--:|---|",
    ]
    for b in meta:
        lines.append(
            f"| [{b['main']}]({b['file']}) | {b['author']} | {b['count']} | {b['year']} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Export Kobo highlights to Markdown.")
    ap.add_argument("--db", help="export from a specific snapshot (skips device read)")
    ap.add_argument("--backup-only", action="store_true",
                    help="snapshot the device and exit (no export)")
    ap.add_argument("--out", default="output", help="output directory (default: output)")
    args = ap.parse_args()

    if args.backup_only:
        if not pathlib.Path(DEVICE_DB).is_file():
            sys.exit(f"No Kobo device found at {DEVICE_DB}. Plug in the Kobo.")
        backup_device_db(DEVICE_DB)
        return

    db_path = resolve_source(args.db)
    rows = fetch_highlights(db_path)
    if not rows:
        sys.exit("No highlights found in the database.")

    books = group_by_book(rows)
    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    used, index_meta = set(), []
    for book in books.values():
        stem = sanitize_filename(book["title"], used)
        (out_dir / f"{stem}.md").write_text(render_book(book), encoding="utf-8")
        index_meta.append({
            "main": main_title(book["title"]) or book["title"],
            "author": first_author(book["author"]),
            "count": len(book["highlights"]),
            "year": year_range(book["highlights"]),
            "file": f"{stem}.md",
        })

    index_meta.sort(key=lambda b: b["count"], reverse=True)
    (out_dir / "index.md").write_text(
        render_index(index_meta, db_path, date.today().isoformat()), encoding="utf-8")

    total = sum(b["count"] for b in index_meta)
    print(f"✓ {total} highlights · {len(index_meta)} books "
          f"→ {out_dir}/ ({len(index_meta) + 1} files)")
    print(f"  source: {db_path}")


if __name__ == "__main__":
    main()
