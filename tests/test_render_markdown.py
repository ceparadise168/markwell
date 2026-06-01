from markwell.model import Book, Highlight
from markwell.render.markdown import render

META = {"generated": "2026-06-01", "source": "snap.sqlite"}


def test_markdown_renders_book_file_and_index():
    books = [Book("My Book: Sub", "Jane Doe, Co", "v1", [
        Highlight("A passage", note=None, date="2024-01-01", chapter_index=1),
        Highlight("Noted", note="my note", date="2024-02-01", chapter_index=2),
    ])]
    files = render(books, META)
    assert set(files) == {"My_Book.md", "index.md"}
    book_md = files["My_Book.md"]
    assert "# My Book: Sub" in book_md
    assert "> A passage" in book_md
    assert "> **note:** my note" in book_md
    assert "── ch.1 ──" in book_md
    assert "── ch.2 ──" in book_md
    index = files["index.md"]
    assert "[My Book](My_Book.md)" in index   # main title only (subtitle dropped)
    assert "Jane Doe" in index                # first author only


def test_markdown_dedupes_filename_collisions():
    books = [
        Book("Same: one", "A", "v1", [Highlight("x", date="2024-01-01")]),
        Book("Same: two", "B", "v2", [Highlight("y", date="2024-01-01")]),
    ]
    files = render(books, META)
    assert "Same.md" in files
    assert "Same-2.md" in files
