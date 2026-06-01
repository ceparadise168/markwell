"""Render books to Markdown files. Pure: returns {filename: content}, no I/O."""
from __future__ import annotations

import re

from ..model import Book, year_span

# Windows reserved device names — unusable as a bare filename stem (any extension).
_WIN_RESERVED = {"CON", "PRN", "AUX", "NUL",
                 *(f"COM{i}" for i in range(1, 10)),
                 *(f"LPT{i}" for i in range(1, 10))}


def _cell(s):
    """Escape a table cell so a literal "|" can't break the index table row."""
    return s.replace("|", "\\|")


def _main_title(title):
    """Headline part of a title — drop the subtitle after the first colon."""
    for sep in ("：", ":"):  # fullwidth ：, then ASCII :
        if sep in title:
            return title.split(sep, 1)[0].strip()
    return title.strip()


def _first_author(author):
    return author.split(",", 1)[0].strip() if author else ""


def _stem(title, used):
    """Filesystem- and link-safe stem from a book's main title; dedup collisions."""
    name = _main_title(title) or "book"
    name = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "", name)
    name = re.sub(r"\s+", "_", name).strip("._ ")
    if len(name) > 50:
        name = name[:50].rstrip("._ ")
    name = name or "book"
    if name.split(".")[0].upper() in _WIN_RESERVED:
        name += "_"
    base, i = name, 2
    while name in used:
        name, i = f"{base}-{i}", i + 1
    used.add(name)
    return name


def _render_book(book):
    hl = book.highlights
    count = f"{len(hl)} highlight" + ("s" if len(hl) != 1 else "")
    meta = " · ".join(filter(None, [book.author, count, book.year_range]))
    blocks = [f"# {book.title}", meta]
    last_chap = None
    for h in hl:
        if h.chapter_index != last_chap:
            blocks.append(f"── ch.{h.chapter_index} ──")
            last_chap = h.chapter_index
        parts = []
        if h.text:
            parts.append(h.text)
        if h.note:
            parts.append(f"**note:** {h.note}")
        if h.date:
            parts.append(f"*↳ {h.date}*")
        blocks.append("\n>\n".join(f"> {p}" for p in parts))
    return "\n\n".join(blocks) + "\n"


def _render_index(entries, meta):
    total = sum(e["count"] for e in entries)
    all_years = [e["year"] for e in entries if e["year"]]
    span = ""
    if all_years:
        span = year_span(min(y[:4] for y in all_years), max(y[-4:] for y in all_years))
    lines = [
        "# Kobo Highlights",
        "",
        f"**{total} highlights** across **{len(entries)} books**"
        + (f" · {span}" if span else ""),
        "",
        f"Generated {meta['generated']} · source `{meta['source']}`"
        f" · markwell v{meta.get('version', '?')}",
        "",
        "| Book | Author | Highlights | Years |",
        "|---|---|--:|---|",
    ]
    for e in entries:
        lines.append(
            f"| [{_cell(e['main'])}]({e['file']}) | {_cell(e['author'])} "
            f"| {e['count']} | {e['year']} |")
    return "\n".join(lines) + "\n"


def render(books: list[Book], meta: dict) -> dict[str, str]:
    """Return {filename: markdown} for every per-book file plus index.md.

    `meta` carries {"generated": str, "source": str, "version": str}.
    """
    used = {"index"}  # reserve so a book stemmed "index" can't clobber index.md
    files = {}
    entries = []
    for book in books:
        fname = f"{_stem(book.title, used)}.md"
        files[fname] = _render_book(book)
        entries.append({
            "main": _main_title(book.title) or book.title,
            "author": _first_author(book.author),
            "count": len(book.highlights),
            "year": book.year_range,
            "file": fname,
        })
    entries.sort(key=lambda e: e["count"], reverse=True)
    files["index.md"] = _render_index(entries, meta)
    return files
