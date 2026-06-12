"""Render highlights to one flat CSV table. Pure: returns {filename: content}."""
from __future__ import annotations

import csv  # the stdlib module — py3 absolute imports keep this file from shadowing it
import io

from ..model import Book

# Excel sniffs encoding from a leading BOM; without one it decodes UTF-8 CJK as
# mojibake — the #1 trap for our non-technical CJK users. BOM-averse consumers
# (pandas, Notion) strip it silently, so prepending costs nothing.
_BOM = "﻿"

# Stable machine-facing identifiers for Notion/Excel field mapping —
# deliberately not localized.
_HEADER = ["title", "author", "chapter_index", "date", "text", "note", "volume_id"]


def render(books: list[Book], meta: dict) -> dict[str, str]:
    """Return {"highlights.csv": text}: RFC 4180, one row per highlight."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")  # RFC 4180 line endings
    writer.writerow(_HEADER)
    for b in books:
        for h in b.highlights:
            writer.writerow([b.title, b.author, h.chapter_index, h.date,
                             h.text, h.note or "", b.volume_id])
    return {"highlights.csv": _BOM + buf.getvalue()}
