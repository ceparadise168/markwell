import re

from markwell.model import Book, Highlight
from markwell.render.html import render

META = {"generated": "2026-06-01", "source": "snap.sqlite", "version": "0.2.0"}


def _books():
    # Book 1 chapters run [1, 1, 2] so the ornament-on-change rule is observable.
    return [
        Book("Meditations", "Marcus Aurelius", "v1", [
            Highlight("A precious privilege", date="2024-01-08", chapter_index=1),
            Highlight("Power over your mind", note="the whole book in one line",
                      date="2024-01-22", chapter_index=1),
            Highlight("Quality of your thoughts", date="2024-02-03",
                      chapter_index=2),
        ]),
        Book("Walden", "Henry David Thoreau", "v2", [
            Highlight("Live deliberately", date="2024-05-02", chapter_index=1),
        ]),
    ]


def _doc(books=None, meta=META):
    files = render(_books() if books is None else books, meta)
    assert set(files) == {"library.html"}
    assert isinstance(files["library.html"], str)
    return files["library.html"]


def test_html_is_one_self_contained_document():
    doc = _doc()
    assert doc.startswith("<!DOCTYPE html>")
    assert "<style>" in doc
    assert "<script" not in doc.lower()          # no JS, ever
    assert "http://" not in doc                  # works offline forever,
    assert "https://" not in doc                 # never phones home
    assert '<meta charset="utf-8">' in doc
    assert 'name="viewport"' in doc
    assert doc.endswith("\n") and not doc.endswith("\n\n")


def test_html_header_and_footer_carry_meta():
    doc = _doc()
    assert "Generated 2026-06-01" in doc
    assert "snap.sqlite" in doc
    assert "markwell v0.2.0 · MIT" in doc


def test_html_escapes_all_book_derived_text():
    books = [Book("<img src=x onerror=alert(1)>", "a&b", "v1", [
        Highlight("<b>bold</b>", note="<i>n</i>", date="2024-01-01"),
    ])]
    doc = _doc(books, {**META, "source": "evil<source>.sqlite"})
    assert "&lt;img" in doc                      # title escaped
    assert "a&amp;b" in doc                      # author escaped
    assert "&lt;b&gt;bold&lt;/b&gt;" in doc      # highlight text escaped
    assert "&lt;i&gt;n&lt;/i&gt;" in doc         # note escaped
    assert "evil&lt;source&gt;.sqlite" in doc    # meta source escaped
    assert "<img" not in doc                     # raw markup never survives
    assert "<i>n</i>" not in doc
    assert "<source>" not in doc


def test_html_zh_tw_locale():
    doc = _doc(meta={**META, "lang": "zh-TW"})
    assert '<html lang="zh-TW">' in doc
    assert "<title>Kobo 書摘</title>" in doc
    assert "筆記：" in doc
    assert "── 第1章 ──" in doc
    assert "note:" not in doc                    # zh-TW fully replaces en labels


def test_html_en_default_when_lang_absent():
    doc = _doc()                                 # META carries no "lang"
    assert '<html lang="en">' in doc
    assert "<title>Kobo Highlights</title>" in doc
    assert "── ch.1 ──" in doc
    assert "note:" in doc


def test_html_toc_anchors_match_sections():
    doc = _doc()
    hrefs = set(re.findall(r'href="#(book-\d+)"', doc))
    ids = set(re.findall(r'id="(book-\d+)"', doc))
    assert hrefs                                 # TOC exists
    assert hrefs == ids                          # every link lands somewhere
    assert hrefs == {"book-1", "book-2"}


def test_html_chapter_ornament_marks_changes_only():
    doc = _doc()
    first = doc[doc.index('id="book-1"'):doc.index('id="book-2"')]
    assert first.count("── ch.") == 2            # chapters [1,1,2] -> 2 ornaments
    assert first.count("── ch.1 ──") == 1
    assert first.count("── ch.2 ──") == 1
    assert doc.count("── ch.") == 3              # + one for book 2's chapter 1


def test_html_empty_library_is_valid_and_tocless():
    doc = _doc([])
    assert doc.startswith("<!DOCTYPE html>") and doc.rstrip().endswith("</html>")
    assert "<nav>" not in doc          # no TOC when there are no books
    assert "<main>" in doc             # body still well-formed
