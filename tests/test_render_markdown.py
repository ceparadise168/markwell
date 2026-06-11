from markwell.model import Book, Highlight
from markwell.render.markdown import render

META = {"generated": "2026-06-01", "source": "snap.sqlite", "version": "0.1.0"}


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
    assert "· markwell v0.1.0" in index       # version stamped in the footer


def test_markdown_dedupes_filename_collisions():
    books = [
        Book("Same: one", "A", "v1", [Highlight("x", date="2024-01-01")]),
        Book("Same: two", "B", "v2", [Highlight("y", date="2024-01-01")]),
    ]
    files = render(books, META)
    assert "Same.md" in files
    assert "Same-2.md" in files


def test_markdown_index_escapes_pipe_in_title_and_author():
    books = [Book("A|B Title", "Smith|Jones", "v1",
                  [Highlight("x", date="2024-01-01")])]
    index = render(books, META)["index.md"]
    row = next(ln for ln in index.splitlines() if ln.startswith("| ["))
    # the literal "|" is escaped, so the row still has the expected cell count
    assert "A\\|B Title" in row
    assert "Smith\\|Jones" in row
    assert row.count("|") - row.count("\\|") == 5  # 4 cells -> 5 unescaped bars


def test_markdown_reserved_windows_name_is_safe_stem():
    books = [Book("CON", "A", "v1", [Highlight("x", date="2024-01-01")])]
    files = render(books, META)
    names = set(files) - {"index.md"}
    assert names == {"CON_.md"}            # reserved name got a trailing "_"


def test_markdown_book_titled_index_does_not_clobber_index():
    books = [Book("index", "A", "v1", [Highlight("x", date="2024-01-01")])]
    files = render(books, META)
    # the real index.md survives AND the book gets its own deduped file
    assert "index.md" in files
    assert "index-2.md" in files
    assert "# Kobo Highlights" in files["index.md"]
    assert "# index" in files["index-2.md"]


def test_markdown_cjk_only_title_yields_nonempty_stable_stem():
    books = [Book("納瓦爾寶典", "作者", "v1", [Highlight("x", date="2024-01-01")])]
    files = render(books, META)
    names = sorted(set(files) - {"index.md"})
    assert len(names) == 1
    assert names[0] == "納瓦爾寶典.md"      # CJK kept verbatim, non-empty, stable


def test_markdown_en_index_total_singularizes_at_one():
    one = render([Book("One", "A", "v1", [Highlight("x", date="2024-01-01")])],
                 META)
    assert "**1 highlight** across **1 book**" in one["index.md"]
    many = render([
        Book("One", "A", "v1", [Highlight("x", date="2024-01-01"),
                                Highlight("y", date="2024-02-01")]),
        Book("Two", "B", "v2", [Highlight("z", date="2025-01-01")]),
    ], META)
    assert "**3 highlights** across **2 books**" in many["index.md"]


def test_markdown_ja_index_total_keeps_zen_against_count():
    books = [
        Book("One", "A", "v1", [Highlight("x", date="2024-01-01")]),
        Book("Two", "B", "v2", [Highlight("y", date="2025-01-01")]),
    ]
    index = render(books, {**META, "lang": "ja"})["index.md"]
    # 全 hugs the bolded count — 「全**2冊**」, not 「全 **2冊**」.
    assert "**2件のハイライト** · 全**2冊**" in index


def test_markdown_zh_tw_localizes_labels_not_highlight_text():
    books = [Book("My Book", "Jane Doe", "v1", [
        Highlight("A passage", note="my note", date="2024-01-01", chapter_index=1),
    ])]
    files = render(books, {**META, "lang": "zh-TW"})
    book_md = files["My_Book.md"]
    assert "> **筆記：** my note" in book_md
    assert "note:" not in book_md
    assert "── 第1章 ──" in book_md
    assert "> A passage" in book_md            # highlight text stays verbatim
    assert "# Kobo 書摘" in files["index.md"]  # index title localized


def test_markdown_zh_tw_index_counts_and_words():
    books = [
        Book("One", "A", "v1", [Highlight("x", date="2024-01-01"),
                                Highlight("y", date="2024-02-01")]),
        Book("Two", "B", "v2", [Highlight("z", date="2025-01-01")]),
    ]
    files = render(books, {**META, "lang": "zh-TW"})
    assert "A · 2 則劃線 · 2024" in files["One.md"]   # per-book count phrase
    index = files["index.md"]
    assert "**3 則劃線**，共 **2 本書**" in index
    assert "產生於 2026-06-01 · 來源 `snap.sqlite`" in index
    assert "| 書名 | 作者 | 劃線數 | 年份 |" in index
