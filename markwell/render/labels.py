"""Label tables for localized export output — every translatable string lives here.

Renderers look words up by the `lang` they find in render `meta` instead of
hardcoding English, so adding a locale means editing this file only. Highlight
text and notes are the reader's own words and are never translated; only the
scaffolding around them (titles, counts, table headers) is. Unknown or missing
langs always fall back to English rather than failing.
"""
from __future__ import annotations

# Standalone words. Every locale must carry the exact same key set — including
# both highlights_one/highlights_many even where the language has no plural
# (CJK locales simply repeat the value).
LABELS: dict[str, dict[str, str]] = {
    "en": {
        "index_title": "Kobo Highlights",
        "note_label": "note:",
        "highlights_one": "highlight",
        "highlights_many": "highlights",
        "books_word": "books",
        "generated_word": "Generated",
        "source_word": "source",
        "col_book": "Book",
        "col_author": "Author",
        "col_highlights": "Highlights",
        "col_years": "Years",
    },
    "zh-TW": {
        "index_title": "Kobo 書摘",
        "note_label": "筆記：",
        "highlights_one": "則劃線",
        "highlights_many": "則劃線",
        "books_word": "本書",
        "generated_word": "產生於",
        "source_word": "來源",
        "col_book": "書名",
        "col_author": "作者",
        "col_highlights": "劃線數",
        "col_years": "年份",
    },
    "ja": {
        "index_title": "Kobo ハイライト",
        "note_label": "メモ：",
        "highlights_one": "件のハイライト",
        "highlights_many": "件のハイライト",
        "books_word": "冊",
        "generated_word": "生成日",
        "source_word": "ソース",
        "col_book": "書名",
        "col_author": "著者",
        "col_highlights": "ハイライト数",
        "col_years": "年",
    },
    "ko": {
        "index_title": "Kobo 하이라이트",
        "note_label": "메모:",
        "highlights_one": "개 하이라이트",
        "highlights_many": "개 하이라이트",
        "books_word": "권",
        "generated_word": "생성일",
        "source_word": "소스",
        "col_book": "책",
        "col_author": "저자",
        "col_highlights": "하이라이트 수",
        "col_years": "연도",
    },
}

# Gap between a numeral and its count word: zh-TW spaces digits off CJK text
# ("5 則劃線"), while ja/ko measure words attach directly ("5件" / "5개").
_NUM_GAP = {"en": " ", "zh-TW": " ", "ja": "", "ko": ""}

# Chapter marker body. A flat template rather than an abbrev word + number,
# because zh-TW/ja wrap the number (第3章) while en prefixes and ko suffixes it.
_CHAPTER_LINE = {"en": "ch.{n}", "zh-TW": "第{n}章", "ja": "第{n}章", "ko": "{n}장"}

# The index total line, shaped around two already-formatted count phrases so
# connector words and word order live here while markup stays in the renderer.
_INDEX_TOTAL = {
    "en": "{highlights} across {books}",
    "zh-TW": "{highlights}，共 {books}",
    "ja": "{highlights} · 全{books}",  # 全 hugs the count: 「全2冊」, never 「全 2冊」
    "ko": "{highlights} · 총 {books}",
}


def _pick(table, lang):
    """Row of `table` for `lang`, with unknown/None falling back to English."""
    return table.get(lang or "en", table["en"])


def for_lang(lang: str | None) -> dict[str, str]:
    """Label table for `lang`; unknown or None falls back to English."""
    return _pick(LABELS, lang)


def chapter_line(lang: str | None, n: int) -> str:
    """Chapter marker body: "ch.3" (en), "第3章" (zh-TW/ja), "3장" (ko)."""
    return _pick(_CHAPTER_LINE, lang).format(n=n)


def highlights_phrase(lang: str | None, n: int) -> str:
    """Highlight count phrase: "1 highlight", "5 highlights", "5 則劃線"."""
    words = _pick(LABELS, lang)
    word = words["highlights_one"] if n == 1 else words["highlights_many"]
    return f"{n}{_pick(_NUM_GAP, lang)}{word}"


def books_phrase(lang: str | None, n: int) -> str:
    """Book count phrase: "1 book", "4 books", "4 本書", "4冊", "4권"."""
    words = _pick(LABELS, lang)
    word = words["books_word"]
    if n == 1 and words is LABELS["en"]:
        # English grammar, not a translatable label: CJK locales have no
        # plural, so the singular lives here instead of widening the public
        # key set that the locale-parity test guards.
        word = "book"
    return f"{n}{_pick(_NUM_GAP, lang)}{word}"


def index_total(lang: str | None, highlights: str, books: str) -> str:
    """Compose the index total line from two pre-formatted count phrases.

    The markdown renderer bolds the phrases before passing them in, so markup
    stays in the renderer while connectors and word order stay translatable.
    """
    return _pick(_INDEX_TOTAL, lang).format(highlights=highlights, books=books)
