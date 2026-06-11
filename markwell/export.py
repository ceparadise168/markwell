"""Render books to files and write them atomically — shared by every front-end.

Both `cli.py` and `gui/` need the same two steps: turn a list of `Book`s into
named output files, then write those files without ever leaving a truncated file
or deleting something the user hand-authored. That logic lives here once so the
command-line and graphical front-ends stay byte-for-byte identical in what they
produce.
"""
from __future__ import annotations

import datetime
import json
import pathlib

from . import __version__
from .model import Book
from .render import json as json_render
from .render import markdown as md_render

_MANIFEST = ".markwell-manifest.json"


def build_meta(source: str, freshness: str, lang: str = "en") -> dict:
    """Assemble the render `meta` block both front-ends pass to the renderers.

    The renderers read exactly these keys (generated/source/source_freshness/
    version/lang); building them in one place keeps the CLI and GUI from
    drifting on the shape. `source` is the snapshot/sample name; `freshness` is
    one of "device" | "cached_snapshot" | "sample"; `lang` picks the export
    label language (Markdown only — the JSON document stays language-neutral).
    """
    return {
        "generated": datetime.date.today().isoformat(),
        "source": source,
        "source_freshness": freshness,
        "version": __version__,
        "lang": lang,
    }


def build_files(books: list[Book], meta: dict, fmt: str) -> dict[str, str]:
    """Render `books` to {filename: content} for the requested format.

    `fmt` is "md", "json", or "all". `meta` carries generated/source/
    source_freshness/version/lang, exactly as the renderers expect.
    """
    files: dict[str, str] = {}
    if fmt in ("md", "all"):
        files.update(md_render.render(books, meta))
    if fmt in ("json", "all"):
        files.update(json_render.render(books, meta))
    return files


def write_outputs(files: dict[str, str], out_dir) -> int:
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
