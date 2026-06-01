from kobo_backup.model import Book, Highlight


def test_year_range_single_year():
    b = Book("T", "A", "v1", [Highlight("x", date="2024-01-01")])
    assert b.year_range == "2024"


def test_year_range_spans_years():
    b = Book("T", "A", "v1", [
        Highlight("x", date="2024-01-01"),
        Highlight("y", date="2026-05-01"),
    ])
    assert b.year_range == "2024–2026"  # en dash


def test_year_range_empty_when_no_dates():
    b = Book("T", "A", "v1", [Highlight("x")])
    assert b.year_range == ""
