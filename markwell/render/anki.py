"""Render highlights to an Anki-importable TSV. Pure: returns {filename: content}."""
from __future__ import annotations

from ..model import Book

_EM_DASH = "—"


def _field(s):
    """Replace tabs so a field can't split its row.

    reader._clean() already collapses all whitespace upstream, so tabs can't
    occur in real data — defense in depth for synthetic input.
    """
    return s.replace("\t", " ")


def render(books: list[Book], meta: dict) -> dict[str, str]:
    """Return {"anki.tsv": text}: one note per highlight as front/back/source.

    The two leading `#` directives are Anki 2.1.55+ file headers that preselect
    the tab separator and plain-text fields, making import a two-click affair.
    front = highlight text, back = the reader's note (or empty), source =
    "title — author" (just the title when the author is unknown).
    """
    lines = ["#separator:tab", "#html:false"]
    for b in books:
        source = f"{b.title} {_EM_DASH} {b.author}" if b.author else b.title
        for h in b.highlights:
            lines.append(
                "\t".join((_field(h.text), _field(h.note or ""), _field(source))))
    return {"anki.tsv": "\n".join(lines) + "\n"}
