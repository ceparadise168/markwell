import sqlite3

import pytest


def make_kobo_db(path, wal=False):
    """Build a minimal KoboReader.sqlite with known highlights, a note,
    a dogear (no text), and a hidden highlight (both must be excluded).

    The content table carries the INTEGER VolumeIndex and ContentType=9 chapter
    rows that reader.read_books() needs for spine-order reading, mirroring a real
    Kobo DB (book rows are ContentType=6, chapter rows ContentType=9).

    With wal=True the DB is put in WAL mode and the open connection is RETURNED
    (not closed) so its uncheckpointed `-wal`/`-shm` siblings stay live on disk,
    mirroring a plugged-in Kobo; the caller owns closing it. Otherwise returns None.
    """
    conn = sqlite3.connect(str(path))
    if wal:
        conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(
        """
        CREATE TABLE content (
            ContentID TEXT, Title TEXT, Attribution TEXT,
            ContentType INTEGER, VolumeIndex INTEGER
        );
        CREATE TABLE Bookmark (
            BookmarkID TEXT, VolumeID TEXT, ContentID TEXT,
            Text TEXT, Annotation TEXT, DateCreated TEXT,
            ChapterProgress REAL, StartOffset INTEGER, Hidden TEXT, Type TEXT
        );
        """
    )
    conn.executemany(
        "INSERT INTO content (ContentID, Title, Attribution, ContentType, "
        "VolumeIndex) VALUES (?,?,?,?,?)",
        [
            ("vol-1", "Book One", "Author A", 6, None),
            ("vol-2", "Book Two: A Subtitle", "Author B, Someone Else", 6, None),
            # chapter content rows (ContentType=9) carry the spine VolumeIndex
            ("ch-a", None, None, 9, 1),
            ("ch-b", None, None, 9, 2),
            ("ch-x", None, None, 9, 1),
        ],
    )
    conn.executemany(
        "INSERT INTO Bookmark (BookmarkID, VolumeID, ContentID, Text, Annotation, "
        "DateCreated, ChapterProgress, StartOffset, Hidden, Type) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            ("b1", "vol-1", "ch-a", "First highlight", None,
             "2024-03-01T10:00:00.000", 0.1, 5, "false", "highlight"),
            ("b2", "vol-1", "ch-a", "Second highlight", None,
             "2024-03-02T10:00:00.000", 0.2, 9, "false", "highlight"),
            ("b3", "vol-1", "ch-b", "Noted passage", "My own note",
             "2024-04-01T10:00:00.000", 0.5, 2, "false", "highlight"),
            ("b4", "vol-1", "ch-b", None, None,
             "2024-04-02T10:00:00.000", 0.6, 0, "false", "dogear"),
            ("b5", "vol-1", "ch-b", "Hidden one", None,
             "2024-04-03T10:00:00.000", 0.7, 1, "true", "highlight"),
            ("b6", "vol-2", "ch-x", "Other book highlight", None,
             "2025-01-01T10:00:00.000", 0.3, 0, "false", "highlight"),
        ],
    )
    conn.commit()
    if wal:
        return conn  # keep open so -wal/-shm persist; caller closes
    conn.close()
    return None


@pytest.fixture
def kobo_db(tmp_path):
    db = tmp_path / "KoboReader.sqlite"
    make_kobo_db(db)
    return db


@pytest.fixture
def wal_kobo_db(tmp_path):
    """A WAL-mode KoboReader.sqlite with live, uncheckpointed `-wal`/`-shm`."""
    db = tmp_path / "KoboReader.sqlite"
    conn = make_kobo_db(db, wal=True)
    try:
        yield db
    finally:
        conn.close()
