"""Render books to a single JSON document. Pure: returns {filename: content}."""
from __future__ import annotations

import json

from ..model import Book

SCHEMA = "markwell/1"


def document(books: list[Book], meta: dict) -> dict:
    """Return the schema-`markwell/1` document as a plain dict.

    Separated from `render()` so in-process consumers (e.g. the GUI, which feeds
    the same shape to the browser) can use the data without re-parsing JSON text.
    """
    return {
        "schema": SCHEMA,
        "generated": meta["generated"],
        "source": meta["source"],
        "source_freshness": meta.get("source_freshness"),
        "generator": f"markwell/{meta.get('version', '?')}",
        "books": [
            {
                "title": b.title,
                "author": b.author,
                "volume_id": b.volume_id,
                "highlights": [
                    {
                        "text": h.text,
                        "note": h.note,
                        "date": h.date,
                        "chapter_index": h.chapter_index,
                    }
                    for h in b.highlights
                ],
            }
            for b in books
        ],
    }


def render(books: list[Book], meta: dict) -> dict[str, str]:
    """Return {"highlights.json": text} following the documented schema."""
    text = json.dumps(document(books, meta), ensure_ascii=False, indent=2) + "\n"
    return {"highlights.json": text}
