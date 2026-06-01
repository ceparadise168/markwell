"""Render books to a single JSON document. Pure: returns {filename: content}."""
from __future__ import annotations

import json

from ..model import Book

SCHEMA = "markwell/1"


def render(books: list[Book], meta: dict) -> dict[str, str]:
    """Return {"highlights.json": text} following the documented schema."""
    doc = {
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
    return {"highlights.json": json.dumps(doc, ensure_ascii=False, indent=2) + "\n"}
