"""Read a Kobo snapshot into typed records.

This is the ONLY module that knows Kobo's SQLite schema. If a firmware update
changes a table or column, adapt it here and nowhere else.
"""
from __future__ import annotations

import datetime
import pathlib
import re
import sqlite3
from collections import OrderedDict

from .model import Book, Highlight


class UnsupportedSchemaError(Exception):
    """Raised when this Kobo DB lacks a table/column the query needs."""


# Highlights and notes (rows with text OR an annotation), joined to their book,
# in EPUB spine order. Dogears have neither, so they are naturally excluded.
#
# Reading order is the chapter's INTEGER VolumeIndex (spine position), found on
# the chapter content row (ContentType=9) whose ContentID equals the bookmark's.
# A correlated subquery (not a JOIN) fetches it so a duplicated chapter row can
# never fan a bookmark into multiple output rows; MIN() collapses any duplicate.
# VolumeIndex IS NULL (e.g. older firmware) falls back to ContentID text order.
_CHAP_INDEX = """(SELECT MIN(ch.VolumeIndex) FROM content ch
                   WHERE ch.ContentID = b.ContentID AND ch.ContentType = 9)"""
_QUERY = f"""
    SELECT b.VolumeID    AS vid,
           c.Title       AS title,
           c.Attribution AS author,
           b.Text        AS text,
           b.Annotation  AS note,
           b.DateCreated AS created,
           b.ContentID   AS chap
    FROM Bookmark b
    LEFT JOIN content c ON b.VolumeID = c.ContentID
    WHERE COALESCE(b.Hidden, 0) NOT IN (1, '1', 'true', 'TRUE')
      AND ( (b.Text       IS NOT NULL AND TRIM(b.Text)       <> '')
         OR (b.Annotation IS NOT NULL AND TRIM(b.Annotation) <> '') )
    ORDER BY b.VolumeID,
             CASE WHEN {_CHAP_INDEX} IS NULL THEN 1 ELSE 0 END,
             {_CHAP_INDEX},
             b.ContentID, b.ChapterProgress, b.StartOffset
"""


def _clean(s):
    """Collapse whitespace to single spaces; '' for falsy input."""
    return re.sub(r"\s+", " ", s).strip() if s else ""


def _fmt_date(created):
    """Kobo stores DateCreated as UTC; render the LOCAL calendar date.

    '2024-03-17T10:10:53.000' (UTC) -> local 'YYYY-MM-DD'. Falsy or
    non-ISO input -> '' (the date is then simply omitted downstream).
    """
    if not created:
        return ""
    try:
        return (datetime.datetime
                .strptime(created[:19], "%Y-%m-%dT%H:%M:%S")
                .replace(tzinfo=datetime.timezone.utc)
                .astimezone().date().isoformat())
    except ValueError:
        return ""


def read_books(db_path) -> list[Book]:
    """Read highlights/notes from a snapshot, grouped by book in reading order."""
    uri = pathlib.Path(db_path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        try:
            rows = conn.execute(_QUERY).fetchall()
        except sqlite3.OperationalError as e:
            raise UnsupportedSchemaError(
                f"This KoboReader.sqlite is missing a table or column markwell "
                f"needs ({e}). Please file an issue with your Kobo firmware "
                f"version.") from e
    finally:
        conn.close()

    books = OrderedDict()
    chap_state = {}  # vid -> (prev_chap_content_id, chapter_number)
    for r in rows:
        vid = r["vid"]
        if vid not in books:
            books[vid] = Book(
                title=(r["title"] or vid),
                author=(r["author"] or "").strip(),
                volume_id=vid,
            )
            chap_state[vid] = (None, 0)
        prev_chap, chap_n = chap_state[vid]
        if r["chap"] != prev_chap:
            chap_n += 1
            chap_state[vid] = (r["chap"], chap_n)
        books[vid].highlights.append(Highlight(
            text=_clean(r["text"]),
            note=_clean(r["note"]) or None,
            date=_fmt_date(r["created"]),
            chapter_index=chap_n,
        ))
    return list(books.values())
