from markwell.model import Book, Highlight
from markwell.render.anki import render

META = {"generated": "2026-06-01", "source": "snap.sqlite", "version": "0.1.0"}


def _books():
    return [
        Book("原子習慣", "James Clear", "v1", [
            Highlight("微小的改變", note="複利效應", date="2024-01-01", chapter_index=1),
            Highlight("plain passage", note=None, date="2024-02-01", chapter_index=2),
        ]),
        Book("No Author", "", "v2", [Highlight("alone", date="2025-01-01")]),
    ]


def test_anki_filename_and_header_directives():
    files = render(_books(), META)
    assert set(files) == {"anki.tsv"}
    lines = files["anki.tsv"].splitlines()
    assert lines[0] == "#separator:tab"
    assert lines[1] == "#html:false"


def test_anki_one_line_per_highlight_two_tabs_each():
    out = render(_books(), META)["anki.tsv"]
    assert out.endswith("\n")
    lines = out.splitlines()
    assert len(lines) == 2 + 3  # directives + one line per highlight, across books
    for line in lines[2:]:
        assert line.count("\t") == 2


def test_anki_front_back_source_fields():
    lines = render(_books(), META)["anki.tsv"].splitlines()
    assert lines[2] == "微小的改變\t複利效應\t原子習慣 — James Clear"  # CJK verbatim
    assert lines[3] == "plain passage\t\t原子習慣 — James Clear"      # note None → ""
    assert lines[4] == "alone\t\tNo Author"  # author-less → source is title only


def test_anki_tab_in_field_is_space_replaced():
    # upstream reader._clean() means tabs can't occur in real data;
    # the renderer stays defensive for synthetic input anyway
    books = [Book("T\tabbed", "A", "v1",
                  [Highlight("has\ttab", note="no\tte", date="2024-01-01")])]
    line = render(books, META)["anki.tsv"].splitlines()[2]
    assert line == "has tab\tno te\tT abbed — A"
    assert line.count("\t") == 2
