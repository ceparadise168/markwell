import sqlite3

import pytest


def make_kobo_db(path):
    """Build a minimal KoboReader.sqlite with known highlights, a note,
    a dogear (no text), and a hidden highlight (both must be excluded)."""
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE content (
            ContentID TEXT, Title TEXT, Attribution TEXT, ContentType INTEGER
        );
        CREATE TABLE Bookmark (
            BookmarkID TEXT, VolumeID TEXT, ContentID TEXT,
            Text TEXT, Annotation TEXT, DateCreated TEXT,
            ChapterProgress REAL, StartOffset INTEGER, Hidden TEXT, Type TEXT
        );
        """
    )
    conn.executemany(
        "INSERT INTO content (ContentID, Title, Attribution, ContentType) "
        "VALUES (?,?,?,?)",
        [
            ("vol-1", "Book One", "Author A", 6),
            ("vol-2", "Book Two: A Subtitle", "Author B, Someone Else", 6),
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
    conn.close()


@pytest.fixture
def kobo_db(tmp_path):
    db = tmp_path / "KoboReader.sqlite"
    make_kobo_db(db)
    return db
