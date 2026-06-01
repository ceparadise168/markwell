from markwell.reader import read_books


def test_read_books_groups_and_orders(kobo_db):
    books = read_books(kobo_db)
    assert [b.title for b in books] == ["Book One", "Book Two: A Subtitle"]
    one = books[0]
    assert one.author == "Author A"
    assert [h.text for h in one.highlights] == [
        "First highlight", "Second highlight", "Noted passage",
    ]
    assert len(one.highlights) == 3  # dogear + hidden excluded


def test_read_books_captures_notes(kobo_db):
    books = read_books(kobo_db)
    noted = [h for b in books for h in b.highlights if h.note]
    assert len(noted) == 1
    assert noted[0].note == "My own note"
    assert noted[0].text == "Noted passage"


def test_read_books_chapter_indexing(kobo_db):
    books = read_books(kobo_db)
    assert [h.chapter_index for h in books[0].highlights] == [1, 1, 2]
