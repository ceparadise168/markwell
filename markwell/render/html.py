"""Render the whole library to one self-contained HTML page. Pure: {filename: content}.

The "carry my library" artifact: a single file that opens anywhere, forever.
Inline CSS only, system font stacks, no <script>, no external URL of any kind —
nothing to fetch, nothing to phone home to (see SECURITY.md). Book-derived text
is untrusted and is pushed through html.escape() without exception, so reader
data can never become markup. @media print turns the page into a clean paper
edition: black on white, each book starting a fresh page.
"""
from __future__ import annotations

from html import escape  # the stdlib module — py3 absolute imports keep this file from shadowing it

from . import labels
from ..model import Book, year_span

# Same paper, ink, and teal as the GUI (gui/assets/style.css §:root), so the
# export reads as a printed edition of the app. Light tokens, then dark via
# prefers-color-scheme; the print block stays LAST in source — when printing
# from a dark-mode browser both media queries match, and source order must let
# print's black-on-white tokens win.
_CSS = """\
:root {
  color-scheme: light dark;
  --font-ui: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", "PingFang TC", "PingFang SC", "Microsoft JhengHei",
    "Noto Sans CJK TC", sans-serif;
  --font-read: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia,
    "Songti TC", "Songti SC", "Noto Serif CJK TC", "Source Han Serif", serif;
  --bg: #faf8f3;
  --surface-2: #f3efe7;
  --ink: #221f1b;
  --ink-soft: #57514a;
  --ink-faint: #6f685e;
  --line: #e8e1d5;
  --accent-ink: #205a4d;
  --accent-soft: #e4f0ec;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #15130f;
    --surface-2: #1a1713;
    --ink: #ece6dc;
    --ink-soft: #b7afa3;
    --ink-faint: #9a9286;
    --line: #322c24;
    --accent-ink: #8ad6c4;
    --accent-soft: #1d2a26;
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
body {
  margin: 0 auto;
  max-width: 42em;
  padding: clamp(28px, 6vw, 72px) clamp(20px, 5vw, 44px) 56px;
  font-family: var(--font-ui);
  font-size: 16px;
  line-height: 1.6;
  color: var(--ink);
  background: var(--bg);
  overflow-wrap: break-word;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
h1, h2 { font-family: var(--font-read); font-weight: 650; line-height: 1.25;
  letter-spacing: -.01em; text-wrap: balance; }
a { color: var(--accent-ink); text-decoration: none; }
a:hover { text-decoration: underline; text-underline-offset: 3px; }
code { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: .92em; }

/* masthead */
header { padding-bottom: 26px; border-bottom: 1px solid var(--line); }
h1 { font-size: 2.15rem; margin: 0 0 12px; }
.total { margin: 0 0 8px; color: var(--ink-soft); font-size: 1.04rem; }
.total strong { color: var(--ink); font-weight: 650; }
.stamp { margin: 0; color: var(--ink-faint); font-size: .85rem; }

/* contents */
nav { margin: 32px 0 8px; }
nav ol { margin: 0; padding-left: 1.7em; }
nav li { padding: 5px 0; }
nav li::marker { color: var(--ink-faint); font-size: .85rem; }
nav a { font-family: var(--font-read); font-size: 1.06rem; font-weight: 600; }
.toc-meta { color: var(--ink-soft); font-size: .9rem; }

/* books */
.book { margin-top: clamp(52px, 9vw, 84px); }
.book-head { padding-bottom: 18px; border-bottom: 1px solid var(--line);
  margin-bottom: 28px; }
.book h2 { font-size: 1.65rem; margin: 0 0 4px; }
.by { margin: 0; color: var(--ink-soft); font-size: 1.02rem; }
.stat { margin: 10px 0 0; color: var(--ink-faint); font-size: .88rem; }
.chapter { margin: 36px 0 20px; text-align: center; color: var(--accent-ink);
  font-size: .82rem; letter-spacing: .12em; }
blockquote { margin: 0 0 22px; padding: 2px 0 2px 20px;
  border-left: 3px solid var(--accent-soft); }
.text { margin: 0; font-family: var(--font-read); font-size: 1.13rem;
  line-height: 1.78; }
.note { margin-top: 11px; padding: 11px 14px; border-radius: 9px;
  background: var(--surface-2); font-size: .95rem; line-height: 1.65;
  color: var(--ink-soft); }
.note b { color: var(--ink); font-weight: 650; }
.date { margin: 9px 0 0; font-size: .81rem; font-style: italic;
  color: var(--ink-faint); }
footer { margin-top: clamp(52px, 9vw, 84px); padding-top: 18px;
  border-top: 1px solid var(--line); text-align: center;
  color: var(--ink-faint); font-size: .82rem; }

/* paper edition — black on white; backgrounds don't print, borders do */
@media print {
  :root { --bg: #fff; --surface-2: #fff; --ink: #000; --ink-soft: #333;
    --ink-faint: #555; --line: #999; --accent-ink: #000; --accent-soft: #999; }
  body { max-width: none; padding: 0; font-size: 11.5pt; }
  a { color: #000; text-decoration: none; }
  .book { break-before: page; page-break-before: always; }
  blockquote { break-inside: avoid; page-break-inside: avoid; }
  .note { background: none; border: 1px solid #bbb; }
}\
"""


def _total_line(books, lang):
    """The edition's one-line summary: counts bolded, reading-years span after.

    Mirrors the markdown index — the two exports must tell the same story.
    Markup wraps the phrases here while connector words and word order stay in
    labels.index_total (its documented contract).
    """
    total = sum(len(b.highlights) for b in books)
    line = labels.index_total(
        lang,
        f"<strong>{escape(labels.highlights_phrase(lang, total))}</strong>",
        f"<strong>{escape(labels.books_phrase(lang, len(books)))}</strong>")
    years = [b.year_range for b in books if b.year_range]
    if years:
        span = year_span(min(y[:4] for y in years), max(y[-4:] for y in years))
        line += f" · {escape(span)}"
    return line


def _toc(books, lang):
    lines = ["<nav>", "<ol>"]
    for i, b in enumerate(books, 1):
        count = labels.highlights_phrase(lang, len(b.highlights))
        tail = " — ".join(filter(None, [escape(b.author), escape(count)]))
        lines.append(f'<li><a href="#book-{i}">{escape(b.title)}</a>'
                     f'<span class="toc-meta"> — {tail}</span></li>')
    lines += ["</ol>", "</nav>"]
    return lines


def _section(book, i, lang, words):
    lines = [f'<section class="book" id="book-{i}">', '<div class="book-head">',
             f"<h2>{escape(book.title)}</h2>"]
    if book.author:
        lines.append(f'<p class="by">{escape(book.author)}</p>')
    stat = " · ".join(filter(None, [
        labels.highlights_phrase(lang, len(book.highlights)), book.year_range]))
    lines += [f'<p class="stat">{escape(stat)}</p>', "</div>"]
    last_chap = None
    for h in book.highlights:
        if h.chapter_index != last_chap:
            lines.append(f'<p class="chapter">── '
                         f'{escape(labels.chapter_line(lang, h.chapter_index))}'
                         f' ──</p>')
            last_chap = h.chapter_index
        lines.append("<blockquote>")
        if h.text:
            lines.append(f'<p class="text">{escape(h.text)}</p>')
        if h.note:
            lines.append(f'<div class="note"><b>{escape(words["note_label"])}</b>'
                         f" {escape(h.note)}</div>")
        if h.date:
            lines.append(f'<p class="date">{escape(h.date)}</p>')
        lines.append("</blockquote>")
    lines.append("</section>")
    return lines


def render(books: list[Book], meta: dict) -> dict[str, str]:
    """Return {"library.html": text}: the library as one offline document.

    Document order is reading order: the TOC lists books exactly as their
    sections follow (anchors #book-1..#book-N by input position) — a linear
    edition never reorders its own contents. Every interpolated value is
    escaped, even our own labels, so nothing here needs a trust judgment.
    """
    lang = meta.get("lang")
    words = labels.for_lang(lang)
    out = [
        "<!DOCTYPE html>",
        f'<html lang="{escape(lang or "en")}">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(words['index_title'])}</title>",
        "<style>",
        _CSS,
        "</style>",
        "</head>",
        "<body>",
        "<header>",
        f"<h1>{escape(words['index_title'])}</h1>",
        f'<p class="total">{_total_line(books, lang)}</p>',
        f'<p class="stamp">{escape(words["generated_word"])} '
        f"{escape(meta['generated'])} · {escape(words['source_word'])} "
        f"<code>{escape(meta['source'])}</code> · "
        f"markwell v{escape(meta.get('version', '?'))}</p>",
        "</header>",
    ]
    if books:
        out += _toc(books, lang)
    out.append("<main>")
    for i, b in enumerate(books, 1):
        out += _section(b, i, lang, words)
    out += [
        "</main>",
        f"<footer>markwell v{escape(meta.get('version', '?'))} · MIT</footer>",
        "</body>",
        "</html>",
    ]
    return {"library.html": "\n".join(out) + "\n"}
