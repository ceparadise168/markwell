"""Plain data structures — the stable internal representation.

Renderers and the CLI depend on these and nothing else.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_EN_DASH = "–"


def year_span(lo: str, hi: str) -> str:
    """Format a low/high year pair as a span: "2024" if equal, else "2024–2025"."""
    return lo if lo == hi else f"{lo}{_EN_DASH}{hi}"


@dataclass
class Highlight:
    text: str                 # the highlighted passage
    note: str | None = None   # the reader's own note (Kobo Bookmark.Annotation), if any
    date: str = ""            # YYYY-MM-DD (from DateCreated), or "" if unknown
    chapter_index: int = 0    # reading-order chapter number within the book


@dataclass
class Book:
    title: str
    author: str
    volume_id: str
    highlights: list[Highlight] = field(default_factory=list)

    @property
    def year_range(self) -> str:
        years = sorted(h.date[:4] for h in self.highlights if h.date)
        if not years:
            return ""
        return year_span(years[0], years[-1])
