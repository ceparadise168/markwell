import sqlite3

import pytest

from markwell.reader import UnsupportedSchemaError, read_books

# These tests build their own KoboReader.sqlite rather than using the shared
# `kobo_db` fixture, because reading order now depends on the content table's
# INTEGER VolumeIndex (spine position) and ContentType=9 chapter rows — schema
# the minimal fixture omits.


def _build(path, *, content, bookmarks, with_volume_index=True):
    """Write a KoboReader.sqlite. `content` and `bookmarks` are row tuples.

    content rows: (ContentID, Title, Attribution, ContentType, VolumeIndex)
    bookmark rows: (BookmarkID, VolumeID, ContentID, Text, Annotation,
                    DateCreated, ChapterProgress, StartOffset, Hidden)
    With with_volume_index=False the VolumeIndex column is omitted entirely,
    mirroring older firmware (and exercising the missing-column path).
    """
    conn = sqlite3.connect(str(path))
    vi_col = ", VolumeIndex INTEGER" if with_volume_index else ""
    conn.executescript(
        f"""
        CREATE TABLE content (
            ContentID TEXT, Title TEXT, Attribution TEXT, ContentType INTEGER{vi_col}
        );
        CREATE TABLE Bookmark (
            BookmarkID TEXT, VolumeID TEXT, ContentID TEXT,
            Text TEXT, Annotation TEXT, DateCreated TEXT,
            ChapterProgress REAL, StartOffset INTEGER, Hidden TEXT
        );
        """
    )
    if with_volume_index:
        conn.executemany(
            "INSERT INTO content (ContentID, Title, Attribution, ContentType, "
            "VolumeIndex) VALUES (?,?,?,?,?)", content)
    else:
        conn.executemany(
            "INSERT INTO content (ContentID, Title, Attribution, ContentType) "
            "VALUES (?,?,?,?)", [c[:4] for c in content])
    conn.executemany(
        "INSERT INTO Bookmark (BookmarkID, VolumeID, ContentID, Text, Annotation, "
        "DateCreated, ChapterProgress, StartOffset, Hidden) VALUES (?,?,?,?,?,?,?,?,?)",
        bookmarks)
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def spine_db(tmp_path):
    """Book with a chapter whose ContentID sorts lexically OPPOSITE its spine
    position: ch-10 (VolumeIndex 2) must come AFTER ch-2 (VolumeIndex 10) is
    wrong — spine order is ch-2 first. Lexical order would put 'ch-10' first.
    """
    db = tmp_path / "KoboReader.sqlite"
    _build(
        db,
        content=[
            ("vol-1", "Book One", "Author A", 6, None),
            # chapter content rows (ContentType=9) carry the spine VolumeIndex
            ("ch-2", None, None, 9, 2),     # earlier in spine
            ("ch-10", None, None, 9, 10),   # later in spine, but sorts first lexically
            ("vol-2", "Book Two: A Subtitle", "Author B, Someone Else", 6, None),
            ("ch-x", None, None, 9, 1),
        ],
        bookmarks=[
            # inserted in spine order; ContentIDs sort the opposite way
            ("b-2", "vol-1", "ch-2", "From chapter two", None,
             "2024-03-01T10:00:00.000", 0.1, 5, "false"),
            ("b-10", "vol-1", "ch-10", "From chapter ten", None,
             "2024-03-02T10:00:00.000", 0.2, 9, "false"),
            ("b-x", "vol-2", "ch-x", "Other book highlight", None,
             "2025-01-01T10:00:00.000", 0.3, 0, "false"),
        ],
    )
    return db


def test_reading_order_is_spine_not_lexical(spine_db):
    books = read_books(spine_db)
    one = books[0]
    # ch-2 (VolumeIndex 2) before ch-10 (VolumeIndex 10), despite 'ch-10' < 'ch-2'
    assert [h.text for h in one.highlights] == [
        "From chapter two", "From chapter ten"]
    # chapter_index follows the corrected spine sequence
    assert [h.chapter_index for h in one.highlights] == [1, 2]


def test_volume_index_null_falls_back_to_contentid_order(tmp_path):
    db = tmp_path / "KoboReader.sqlite"
    _build(
        db,
        content=[
            ("vol-1", "Book One", "Author A", 6, None),
            # no ContentType=9 rows -> VolumeIndex subquery is NULL for both chaps
        ],
        bookmarks=[
            ("b1", "vol-1", "ch-a", "Alpha", None,
             "2024-03-01T10:00:00.000", 0.1, 5, "false"),
            ("b2", "vol-1", "ch-b", "Beta", None,
             "2024-03-02T10:00:00.000", 0.2, 9, "false"),
        ],
    )
    books = read_books(db)
    # falls back to ContentID text order: ch-a before ch-b
    assert [h.text for h in books[0].highlights] == ["Alpha", "Beta"]
    assert [h.chapter_index for h in books[0].highlights] == [1, 2]


def test_groups_notes_and_excludes_dogear_and_hidden(tmp_path):
    db = tmp_path / "KoboReader.sqlite"
    _build(
        db,
        content=[
            ("vol-1", "Book One", "Author A", 6, None),
            ("ch-a", None, None, 9, 1),
            ("ch-b", None, None, 9, 2),
            ("vol-2", "Book Two: A Subtitle", "Author B, Someone Else", 6, None),
            ("ch-x", None, None, 9, 1),
        ],
        bookmarks=[
            ("b1", "vol-1", "ch-a", "First highlight", None,
             "2024-03-01T10:00:00.000", 0.1, 5, "false"),
            ("b2", "vol-1", "ch-a", "Second highlight", None,
             "2024-03-02T10:00:00.000", 0.2, 9, "false"),
            ("b3", "vol-1", "ch-b", "Noted passage", "My own note",
             "2024-04-01T10:00:00.000", 0.5, 2, "false"),
            ("b4", "vol-1", "ch-b", None, None,  # dogear: excluded
             "2024-04-02T10:00:00.000", 0.6, 0, "false"),
            ("b5", "vol-1", "ch-b", "Hidden one", None,  # hidden: excluded
             "2024-04-03T10:00:00.000", 0.7, 1, "true"),
            ("b6", "vol-2", "ch-x", "Other book highlight", None,
             "2025-01-01T10:00:00.000", 0.3, 0, "false"),
        ],
    )
    books = read_books(db)
    assert [b.title for b in books] == ["Book One", "Book Two: A Subtitle"]
    one = books[0]
    assert one.author == "Author A"
    assert [h.text for h in one.highlights] == [
        "First highlight", "Second highlight", "Noted passage"]
    assert len(one.highlights) == 3  # dogear + hidden excluded
    assert [h.chapter_index for h in one.highlights] == [1, 1, 2]
    noted = [h for b in books for h in b.highlights if h.note]
    assert len(noted) == 1
    assert noted[0].note == "My own note"
    assert noted[0].text == "Noted passage"


def test_one_row_per_bookmark_despite_duplicate_chapter_row(tmp_path):
    db = tmp_path / "KoboReader.sqlite"
    _build(
        db,
        content=[
            ("vol-1", "Book One", "Author A", 6, None),
            ("ch-a", None, None, 9, 1),
            ("ch-a", None, None, 9, 1),  # duplicate chapter row -> must NOT fan out
        ],
        bookmarks=[
            ("b1", "vol-1", "ch-a", "Only once", None,
             "2024-03-01T10:00:00.000", 0.1, 5, "false"),
        ],
    )
    books = read_books(db)
    assert len(books) == 1
    assert [h.text for h in books[0].highlights] == ["Only once"]


def test_date_utc_converted_to_local(tmp_path):
    """DateCreated is stored UTC; the exported date is the machine's LOCAL date."""
    import datetime as dt
    import os
    import time
    db = tmp_path / "KoboReader.sqlite"
    _build(
        db,
        content=[("vol-1", "Book One", "Author A", 6, None),
                 ("ch-a", None, None, 9, 1)],
        bookmarks=[
            ("b1", "vol-1", "ch-a", "Late night highlight", None,
             "2024-03-17T23:30:00.000", 0.1, 5, "false"),  # 23:30 UTC
        ],
    )
    # Portable (every OS): the exported date must equal that instant localized to
    # this machine — proving the value is parsed AS UTC and converted, not sliced.
    expected = (dt.datetime(2024, 3, 17, 23, 30, tzinfo=dt.timezone.utc)
                .astimezone().date().isoformat())
    assert read_books(db)[0].highlights[0].date == expected

    # Deterministic UTC+8 rollover where we can pin a non-UTC zone (POSIX only):
    # 23:30 UTC is 07:30 the NEXT day in UTC+8. time.tzset() is absent on Windows.
    if not hasattr(time, "tzset"):
        return
    saved = os.environ.get("TZ")
    try:
        os.environ["TZ"] = "Asia/Taipei"
        time.tzset()
        assert read_books(db)[0].highlights[0].date == "2024-03-18"
    finally:
        if saved is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = saved
        time.tzset()


def test_bad_date_yields_empty_string(tmp_path):
    db = tmp_path / "KoboReader.sqlite"
    _build(
        db,
        content=[("vol-1", "Book One", "Author A", 6, None),
                 ("ch-a", None, None, 9, 1)],
        bookmarks=[
            ("b1", "vol-1", "ch-a", "Has a weird date", None,
             "not-a-real-date", 0.1, 5, "false"),
        ],
    )
    books = read_books(db)
    assert books[0].highlights[0].date == ""


def test_unsupported_schema_when_bookmark_table_missing(tmp_path):
    db = tmp_path / "KoboReader.sqlite"
    conn = sqlite3.connect(str(db))
    # content exists, but no Bookmark table -> the query must surface a clear error
    conn.executescript(
        "CREATE TABLE content (ContentID TEXT, Title TEXT, "
        "Attribution TEXT, ContentType INTEGER, VolumeIndex INTEGER);")
    conn.commit()
    conn.close()
    with pytest.raises(UnsupportedSchemaError) as excinfo:
        read_books(db)
    assert "firmware version" in str(excinfo.value)
