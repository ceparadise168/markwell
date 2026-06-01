# kobo-backup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generalize the personal `kobo_highlights.py` script into an open-source, cross-platform, zero-dependency CLI that safely snapshots a Kobo and exports highlights + notes to Markdown and JSON.

**Architecture:** A small layered Python package `kobo_backup/` — `device` (cross-platform detect + read-only snapshot), `reader` (the only schema-aware module), `model` (dataclasses = stable seam), `render/{markdown,json}` (pure functions), `cli` (orchestration). Data flows detect → snapshot once (read-only) → read snapshot → model → render → write.

**Tech Stack:** Python 3.9+, standard library only (no runtime deps), `pytest` for tests, `pyproject.toml`/setuptools for packaging.

**Spec:** `docs/superpowers/specs/2026-06-01-kobo-backup-design.md`

**Execution notes:**
- Run all commands from the repo root (`/Users/erictu/kobo`). Tests import `kobo_backup`, which works after Task 1's `pip install -e ".[dev]"`.
- End every commit message with the repo's trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.
- `kobo_highlights.py` stays in place as a reference until Task 9 removes it (it remains in git history).
- Never `git add` personal data — `.gitignore` already excludes `.kobo/`, `output/`, `backups/`, `*.sqlite*`.

---

### Task 1: Project skeleton + packaging

**Files:**
- Create: `kobo_backup/__init__.py`
- Create: `kobo_backup/render/__init__.py`
- Create: `pyproject.toml`
- Test: `tests/test_package.py`

- [ ] **Step 1: Write the failing test**

`tests/test_package.py`:
```python
def test_package_imports_with_version():
    import kobo_backup
    assert kobo_backup.__version__ == "0.1.0"
```

- [ ] **Step 2: Create the package files**

`kobo_backup/__init__.py`:
```python
"""kobo-backup — safely back up and export Kobo highlights and notes."""

__version__ = "0.1.0"
```

`kobo_backup/render/__init__.py`:
```python
"""Renderers: pure functions from the model to output files."""
```

`pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=61"]
build-backend = "setuptools.build_meta"

[project]
name = "kobo-backup"
version = "0.1.0"
description = "Safely back up and export your Kobo highlights and notes to Markdown and JSON."
readme = "README.md"
requires-python = ">=3.9"
license = { text = "MIT" }
authors = [{ name = "Eric Tu" }]
keywords = ["kobo", "ebook", "highlights", "annotations", "backup"]
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Topic :: Utilities",
]

[project.optional-dependencies]
dev = ["pytest>=7"]

[project.scripts]
kobo-backup = "kobo_backup.cli:main"

[tool.setuptools.packages.find]
include = ["kobo_backup*"]
```

- [ ] **Step 3: Install the package (editable) with dev deps**

Run: `python3 -m pip install -e ".[dev]"`
Expected: ends with `Successfully installed kobo-backup-0.1.0` (and `pytest` if not already present).

Note: `[project.scripts]` references `kobo_backup.cli:main`, which doesn't exist until Task 7. That's fine for install — the entry point is only resolved when the `kobo-backup` command runs, not at install time.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m pytest tests/test_package.py -v`
Expected: PASS — `test_package_imports_with_version`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml kobo_backup/ tests/test_package.py
git commit -m "build: scaffold kobo_backup package + pyproject"
```

---

### Task 2: `model.py` — Book / Highlight dataclasses

**Files:**
- Create: `kobo_backup/model.py`
- Test: `tests/test_model.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_model.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kobo_backup.model'`.

- [ ] **Step 3: Write the implementation**

`kobo_backup/model.py`:
```python
"""Plain data structures — the stable internal representation.

Renderers and the CLI depend on these and nothing else.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_EN_DASH = "–"


@dataclass
class Highlight:
    text: str                 # the highlighted passage
    note: str | None = None   # the reader's own note (Kobo Bookmark.Annotation), if any
    date: str = ""            # YYYY-MM-DD (from DateCreated), or "" if unknown
    chapter_index: int = 0    # reading-order chapter number within the book


@dataclass
class Book:
    title: str
    author: str
    volume_id: str
    highlights: list[Highlight] = field(default_factory=list)

    @property
    def year_range(self) -> str:
        years = sorted(h.date[:4] for h in self.highlights if h.date)
        if not years:
            return ""
        lo, hi = years[0], years[-1]
        return lo if lo == hi else f"{lo}{_EN_DASH}{hi}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_model.py -v`
Expected: PASS — 3 passed.

- [ ] **Step 5: Commit**

```bash
git add kobo_backup/model.py tests/test_model.py
git commit -m "feat: add Book/Highlight model with year_range"
```

---

### Task 3: `reader.py` — schema-aware extraction + test fixture

**Files:**
- Create: `tests/conftest.py`
- Create: `kobo_backup/reader.py`
- Test: `tests/test_reader.py`

- [ ] **Step 1: Create the shared test fixture**

`tests/conftest.py`:
```python
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
```

- [ ] **Step 2: Write the failing tests**

`tests/test_reader.py`:
```python
from kobo_backup.reader import read_books


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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_reader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kobo_backup.reader'`.

- [ ] **Step 4: Write the implementation**

`kobo_backup/reader.py`:
```python
"""Read a Kobo snapshot into typed records.

This is the ONLY module that knows Kobo's SQLite schema. If a firmware update
changes a table or column, adapt it here and nowhere else.
"""
from __future__ import annotations

import pathlib
import re
import sqlite3
from collections import OrderedDict

from .model import Book, Highlight

# Highlights and notes (rows with text OR an annotation), joined to their book,
# in reading order. Dogears have neither, so they are naturally excluded.
_QUERY = """
    SELECT b.VolumeID    AS vid,
           c.Title       AS title,
           c.Attribution AS author,
           b.Text        AS text,
           b.Annotation  AS note,
           b.DateCreated AS created,
           b.ContentID   AS chap
    FROM Bookmark b
    LEFT JOIN content c ON b.VolumeID = c.ContentID
    WHERE COALESCE(b.Hidden, 0) NOT IN (1, '1', 'true', 'TRUE')
      AND ( (b.Text       IS NOT NULL AND TRIM(b.Text)       <> '')
         OR (b.Annotation IS NOT NULL AND TRIM(b.Annotation) <> '') )
    ORDER BY b.VolumeID, b.ContentID, b.ChapterProgress, b.StartOffset
"""


def _clean(s):
    """Collapse whitespace to single spaces; '' for falsy input."""
    return re.sub(r"\s+", " ", s).strip() if s else ""


def _fmt_date(created):
    """'2024-03-17T10:10:53.000' -> '2024-03-17'; falsy -> ''."""
    return created[:10] if created else ""


def read_books(db_path):
    """Read highlights/notes from a snapshot, grouped by book in reading order."""
    uri = pathlib.Path(db_path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(_QUERY).fetchall()
    finally:
        conn.close()

    books = OrderedDict()
    chap_state = {}  # vid -> (prev_chap_content_id, chapter_number)
    for r in rows:
        vid = r["vid"]
        if vid not in books:
            books[vid] = Book(
                title=(r["title"] or vid),
                author=(r["author"] or "").strip(),
                volume_id=vid,
            )
            chap_state[vid] = (None, 0)
        prev_chap, chap_n = chap_state[vid]
        if r["chap"] != prev_chap:
            chap_n += 1
            chap_state[vid] = (r["chap"], chap_n)
        books[vid].highlights.append(Highlight(
            text=_clean(r["text"]),
            note=_clean(r["note"]) or None,
            date=_fmt_date(r["created"]),
            chapter_index=chap_n,
        ))
    return list(books.values())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_reader.py -v`
Expected: PASS — 3 passed.

- [ ] **Step 6: Commit**

```bash
git add kobo_backup/reader.py tests/conftest.py tests/test_reader.py
git commit -m "feat: read highlights+notes from snapshot, excluding dogears/hidden"
```

---

### Task 4: `render/markdown.py`

**Files:**
- Create: `kobo_backup/render/markdown.py`
- Test: `tests/test_render_markdown.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_render_markdown.py`:
```python
from kobo_backup.model import Book, Highlight
from kobo_backup.render.markdown import render

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_render_markdown.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kobo_backup.render.markdown'`.

- [ ] **Step 3: Write the implementation**

`kobo_backup/render/markdown.py`:
```python
"""Render books to Markdown files. Pure: returns {filename: content}, no I/O."""
from __future__ import annotations

import re

from ..model import Book

_EN_DASH = "–"


def _main_title(title):
    """Headline part of a title — drop the subtitle after the first colon."""
    for sep in ("：", ":"):  # fullwidth ：, then ASCII :
        if sep in title:
            return title.split(sep, 1)[0].strip()
    return title.strip()


def _first_author(author):
    return author.split(",", 1)[0].strip() if author else ""


def _stem(title, used):
    """Filesystem- and link-safe stem from a book's main title; dedup collisions."""
    name = _main_title(title) or "book"
    name = re.sub(r'[/\\:*?"<>|\x00-\x1f]', "", name)
    name = re.sub(r"\s+", "_", name).strip("._ ")
    if len(name) > 50:
        name = name[:50].rstrip("._ ")
    name = name or "book"
    base, i = name, 2
    while name in used:
        name, i = f"{base}-{i}", i + 1
    used.add(name)
    return name


def _render_book(book):
    hl = book.highlights
    count = f"{len(hl)} highlight" + ("s" if len(hl) != 1 else "")
    meta = " · ".join(filter(None, [book.author, count, book.year_range]))
    blocks = [f"# {book.title}", meta]
    last_chap = None
    for h in hl:
        if h.chapter_index != last_chap:
            blocks.append(f"── ch.{h.chapter_index} ──")
            last_chap = h.chapter_index
        parts = []
        if h.text:
            parts.append(h.text)
        if h.note:
            parts.append(f"**note:** {h.note}")
        if h.date:
            parts.append(f"*↳ {h.date}*")
        blocks.append("\n>\n".join(f"> {p}" for p in parts))
    return "\n\n".join(blocks) + "\n"


def _render_index(entries, meta):
    total = sum(e["count"] for e in entries)
    all_years = [e["year"] for e in entries if e["year"]]
    span = ""
    if all_years:
        lo = min(y[:4] for y in all_years)
        hi = max(y[-4:] for y in all_years)
        span = lo if lo == hi else f"{lo}{_EN_DASH}{hi}"
    lines = [
        "# Kobo Highlights",
        "",
        f"**{total} highlights** across **{len(entries)} books**"
        + (f" · {span}" if span else ""),
        "",
        f"Generated {meta['generated']} · source `{meta['source']}`",
        "",
        "| Book | Author | Highlights | Years |",
        "|---|---|--:|---|",
    ]
    for e in entries:
        lines.append(
            f"| [{e['main']}]({e['file']}) | {e['author']} | {e['count']} | {e['year']} |")
    return "\n".join(lines) + "\n"


def render(books, meta):
    """Return {filename: markdown} for every per-book file plus index.md.

    `meta` carries {"generated": str, "source": str}.
    """
    used = set()
    files = {}
    entries = []
    for book in books:
        fname = f"{_stem(book.title, used)}.md"
        files[fname] = _render_book(book)
        entries.append({
            "main": _main_title(book.title) or book.title,
            "author": _first_author(book.author),
            "count": len(book.highlights),
            "year": book.year_range,
            "file": fname,
        })
    entries.sort(key=lambda e: e["count"], reverse=True)
    files["index.md"] = _render_index(entries, meta)
    return files
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_render_markdown.py -v`
Expected: PASS — 2 passed.

- [ ] **Step 5: Commit**

```bash
git add kobo_backup/render/markdown.py tests/test_render_markdown.py
git commit -m "feat: render books to Markdown (with notes) + index"
```

---

### Task 5: `render/json.py`

**Files:**
- Create: `kobo_backup/render/json.py`
- Test: `tests/test_render_json.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_render_json.py`:
```python
import json

from kobo_backup.model import Book, Highlight
from kobo_backup.render.json import render

META = {"generated": "2026-06-01", "source": "snap.sqlite"}


def test_json_render_schema_and_content():
    books = [Book("T", "A", "v1", [
        Highlight("x", note="n", date="2024-01-01", chapter_index=1),
    ])]
    files = render(books, META)
    assert set(files) == {"highlights.json"}
    doc = json.loads(files["highlights.json"])
    assert doc["schema"] == "kobo-backup/1"
    assert doc["generated"] == "2026-06-01"
    assert doc["source"] == "snap.sqlite"
    hl = doc["books"][0]["highlights"][0]
    assert hl == {"text": "x", "note": "n", "date": "2024-01-01", "chapter_index": 1}


def test_json_preserves_unicode():
    books = [Book("納瓦爾寶典", "A", "v1",
                  [Highlight("測試", date="2025-01-01")])]
    files = render(books, META)
    assert "納瓦爾寶典" in files["highlights.json"]  # not \uXXXX escaped
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_render_json.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kobo_backup.render.json'`.

- [ ] **Step 3: Write the implementation**

`kobo_backup/render/json.py`:
```python
"""Render books to a single JSON document. Pure: returns {filename: content}."""
from __future__ import annotations

import json

from ..model import Book

SCHEMA = "kobo-backup/1"


def render(books, meta):
    """Return {"highlights.json": text} following the documented schema."""
    doc = {
        "schema": SCHEMA,
        "generated": meta["generated"],
        "source": meta["source"],
        "books": [
            {
                "title": b.title,
                "author": b.author,
                "volume_id": b.volume_id,
                "highlights": [
                    {
                        "text": h.text,
                        "note": h.note,
                        "date": h.date,
                        "chapter_index": h.chapter_index,
                    }
                    for h in b.highlights
                ],
            }
            for b in books
        ],
    }
    return {"highlights.json": json.dumps(doc, ensure_ascii=False, indent=2) + "\n"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_render_json.py -v`
Expected: PASS — 2 passed.

- [ ] **Step 5: Commit**

```bash
git add kobo_backup/render/json.py tests/test_render_json.py
git commit -m "feat: render books to documented JSON (kobo-backup/1)"
```

---

### Task 6: `device.py` — cross-platform detect + safe snapshot

**Files:**
- Create: `kobo_backup/device.py`
- Test: `tests/test_device.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_device.py`:
```python
import sqlite3

from kobo_backup.device import detect_device, snapshot


def _make_src(path):
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE t (x)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()


def test_snapshot_is_timestamped_and_copies_content(tmp_path):
    src = tmp_path / "src.sqlite"
    _make_src(src)
    dest = snapshot(src, tmp_path / "backups", stamp="20260601-101010")
    assert dest.name == "KoboReader-20260601-101010.sqlite"
    assert dest.is_file()
    c = sqlite3.connect(str(dest))
    assert c.execute("SELECT x FROM t").fetchone()[0] == 1
    c.close()


def test_snapshot_distinct_stamps_coexist(tmp_path):
    src = tmp_path / "src.sqlite"
    _make_src(src)
    backups = tmp_path / "backups"
    d1 = snapshot(src, backups, stamp="20260601-101010")
    d2 = snapshot(src, backups, stamp="20260601-101011")
    assert d1.is_file() and d2.is_file() and d1 != d2


def test_snapshot_leaves_no_tmp_on_success(tmp_path):
    src = tmp_path / "src.sqlite"
    _make_src(src)
    backups = tmp_path / "backups"
    snapshot(src, backups, stamp="20260601-101010")
    assert list(backups.glob("*.tmp")) == []


def test_detect_device_finds_db(tmp_path, monkeypatch):
    root = tmp_path / "KOBOeReader"
    (root / ".kobo").mkdir(parents=True)
    db = root / ".kobo" / "KoboReader.sqlite"
    db.write_text("")  # presence is enough; detect_device does not open it
    monkeypatch.setattr("kobo_backup.device._candidate_roots", lambda: [root])
    assert detect_device() == db


def test_detect_device_returns_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr("kobo_backup.device._candidate_roots",
                        lambda: [tmp_path / "nope"])
    assert detect_device() is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_device.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kobo_backup.device'`.

- [ ] **Step 3: Write the implementation**

`kobo_backup/device.py`:
```python
"""Find a connected Kobo and snapshot its database safely.

The device DB is opened READ-ONLY and copied via SQLite's online-backup API
(consistent even with an active WAL). Snapshots are timestamped and never
overwritten; a failed backup never clobbers an existing snapshot.
"""
from __future__ import annotations

import getpass
import glob
import pathlib
import sqlite3
import string
import sys

_REL_DB = pathlib.Path(".kobo") / "KoboReader.sqlite"


def _candidate_roots():
    """Likely Kobo mount points, per platform."""
    if sys.platform == "darwin":
        return [pathlib.Path("/Volumes/KOBOeReader")]
    if sys.platform.startswith("linux"):
        user = getpass.getuser()
        roots = [
            pathlib.Path(f"/media/{user}/KOBOeReader"),
            pathlib.Path(f"/run/media/{user}/KOBOeReader"),
        ]
        roots += [pathlib.Path(p) for p in glob.glob("/media/*/KOBOeReader")]
        roots += [pathlib.Path(p) for p in glob.glob("/mnt/*/KOBOeReader")]
        return roots
    if sys.platform.startswith("win"):
        return [pathlib.Path(f"{c}:/") for c in string.ascii_uppercase]
    return []


def detect_device():
    """Return the path to a connected Kobo's KoboReader.sqlite, or None."""
    for root in _candidate_roots():
        db = root / _REL_DB
        if db.is_file():
            return db
    return None


def snapshot(src, backup_dir, *, stamp):
    """Snapshot the device DB read-only to a timestamped local file; return its path.

    `stamp` is a 'YYYYmmdd-HHMMSS' string, passed in so callers own the clock.
    Writes to a .tmp and atomically renames on success.
    """
    backup_dir = pathlib.Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    dest = backup_dir / f"KoboReader-{stamp}.sqlite"
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.unlink(missing_ok=True)

    src_uri = pathlib.Path(src).resolve().as_uri() + "?mode=ro"
    try:
        source = sqlite3.connect(src_uri, uri=True)
        try:
            snap = sqlite3.connect(str(tmp))
            try:
                source.backup(snap)
            finally:
                snap.close()
        finally:
            source.close()
        tmp.replace(dest)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return dest
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_device.py -v`
Expected: PASS — 5 passed.

- [ ] **Step 5: Commit**

```bash
git add kobo_backup/device.py tests/test_device.py
git commit -m "feat: cross-platform device detection + safe read-only snapshot"
```

---

### Task 7: `cli.py` + `__main__.py` — orchestration

**Files:**
- Create: `kobo_backup/cli.py`
- Create: `kobo_backup/__main__.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

`tests/test_cli.py`:
```python
import json

from kobo_backup.cli import main


def test_cli_exports_md_and_json_from_db(kobo_db, tmp_path):
    out = tmp_path / "out"
    main(["--db", str(kobo_db), "--out", str(out),
          "--backup-dir", str(tmp_path / "backups")])
    assert (out / "index.md").is_file()
    assert (out / "highlights.json").is_file()
    book_mds = [p for p in out.glob("*.md") if p.name != "index.md"]
    assert book_mds  # at least one per-book file
    doc = json.loads((out / "highlights.json").read_text(encoding="utf-8"))
    assert doc["schema"] == "kobo-backup/1"


def test_cli_format_json_only(kobo_db, tmp_path):
    out = tmp_path / "out"
    main(["--db", str(kobo_db), "--out", str(out), "--format", "json",
          "--backup-dir", str(tmp_path / "backups")])
    assert (out / "highlights.json").is_file()
    assert not (out / "index.md").exists()


def test_cli_missing_db_exits(tmp_path):
    import pytest
    with pytest.raises(SystemExit):
        main(["--db", str(tmp_path / "nope.sqlite"), "--out", str(tmp_path / "o")])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kobo_backup.cli'`.

- [ ] **Step 3: Write the implementation**

`kobo_backup/cli.py`:
```python
"""Command-line entry point: detect → snapshot → read → render → write."""
from __future__ import annotations

import argparse
import datetime
import pathlib
import sys

from . import device, reader
from .render import json as json_render
from .render import markdown as md_render


def _resolve_source(args, *, stamp):
    """Decide which DB to read from, snapshotting the device at most once."""
    if args.db:
        p = pathlib.Path(args.db)
        if not p.is_file():
            sys.exit(f"--db not found: {args.db}")
        return p

    dev = pathlib.Path(args.device) if args.device else device.detect_device()
    if dev and pathlib.Path(dev).is_file():
        snap = device.snapshot(dev, args.backup_dir, stamp=stamp)
        print(f"✓ snapshot {snap.name} → {args.backup_dir}/")
        return snap

    snaps = sorted(pathlib.Path(args.backup_dir).glob("KoboReader-*.sqlite"))
    if snaps:
        print(f"⚠ device not connected — using latest snapshot {snaps[-1].name}")
        return snaps[-1]

    sys.exit("No Kobo device and no local snapshot found.\n"
             "Plug in the Kobo, or pass --db PATH to a KoboReader.sqlite.")


def _write(files, out_dir):
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")
    return len(files)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="kobo-backup",
        description="Safely back up and export Kobo highlights and notes.")
    ap.add_argument("--format", choices=["md", "json", "all"], default="all",
                    help="what to export (default: all)")
    ap.add_argument("--snapshot-only", action="store_true",
                    help="snapshot the device and exit (no export)")
    ap.add_argument("--db", help="export from a snapshot (skips device read)")
    ap.add_argument("--device", help="override device auto-detection")
    ap.add_argument("--out", default="output", help="output dir (default: output)")
    ap.add_argument("--backup-dir", default="backups",
                    help="snapshot dir (default: backups)")
    args = ap.parse_args(argv)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    if args.snapshot_only:
        dev = pathlib.Path(args.device) if args.device else device.detect_device()
        if not (dev and pathlib.Path(dev).is_file()):
            sys.exit("No Kobo device found. Plug in the Kobo.")
        snap = device.snapshot(dev, args.backup_dir, stamp=stamp)
        print(f"✓ snapshot {snap.name} → {args.backup_dir}/")
        return

    src = _resolve_source(args, stamp=stamp)
    books = reader.read_books(src)
    if not books:
        sys.exit("No highlights or notes found in the database.")

    meta = {"generated": datetime.date.today().isoformat(),
            "source": pathlib.Path(src).name}
    files = {}
    if args.format in ("md", "all"):
        files.update(md_render.render(books, meta))
    if args.format in ("json", "all"):
        files.update(json_render.render(books, meta))

    n = _write(files, args.out)
    total = sum(len(b.highlights) for b in books)
    print(f"✓ {total} highlights/notes · {len(books)} books "
          f"→ {args.out}/ ({n} files)")
    print(f"  source: {src}")
```

`kobo_backup/__main__.py`:
```python
from .cli import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_cli.py -v`
Expected: PASS — 3 passed.

- [ ] **Step 5: Verify the installed command and module entry both run**

Run: `kobo-backup --db .kobo/KoboReader.sqlite --out /tmp/kb_smoke --backup-dir /tmp/kb_backups`
Expected: prints `✓ <N> highlights/notes · <M> books → /tmp/kb_smoke/ (...)`; `/tmp/kb_smoke/index.md` and `highlights.json` exist.

Run: `python3 -m kobo_backup --db .kobo/KoboReader.sqlite --out /tmp/kb_smoke2 --backup-dir /tmp/kb_backups`
Expected: same kind of output into `/tmp/kb_smoke2/`.

(Cleanup: `rm -rf /tmp/kb_smoke /tmp/kb_smoke2 /tmp/kb_backups`.)

- [ ] **Step 6: Commit**

```bash
git add kobo_backup/cli.py kobo_backup/__main__.py tests/test_cli.py
git commit -m "feat: CLI orchestration (detect/snapshot/read/render/write)"
```

---

### Task 8: README + LICENSE

**Files:**
- Create: `README.md`
- Create: `LICENSE`

- [ ] **Step 1: Write `LICENSE` (MIT)**

`LICENSE`:
```
MIT License

Copyright (c) 2026 Eric Tu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Write `README.md`**

`README.md`:
````markdown
# kobo-backup

Safely back up and export your [Kobo](https://www.kobo.com/) highlights and
notes to Markdown and JSON. Cross-platform, zero dependencies (Python standard
library only).

## Why

Your highlights and notes are the irreplaceable part of your reading. `kobo-backup`:

- **Never writes to your device.** It opens the Kobo database read-only and copies
  it with SQLite's online-backup API.
- **Keeps every snapshot.** Backups are timestamped and never overwritten, so you
  have a full history of your reading database.
- **Gives you portable output.** Human-readable Markdown *and* a documented JSON
  file you can feed into Obsidian, Anki, Readwise, or your own scripts.

## Install

```bash
pip install kobo-backup
```

## Usage

Plug in your Kobo, then:

```bash
kobo-backup                 # snapshot the device, then export Markdown + JSON
kobo-backup --format md     # Markdown only
kobo-backup --format json   # JSON only
kobo-backup --snapshot-only # just back up the database, no export
kobo-backup --db PATH       # export from an existing snapshot (no device read)
kobo-backup --device PATH   # override auto-detection of the Kobo mount
kobo-backup --out DIR       # output directory (default: ./output)
```

Output:

```
backups/
└── KoboReader-YYYYMMDD-HHMMSS.sqlite   timestamped, never overwritten
output/
├── index.md            all books, counts, links
├── <book>.md           one file per book, highlights in reading order
└── highlights.json     machine-readable export (schema "kobo-backup/1")
```

## How it works

`detect device → snapshot once (read-only) → read snapshot → Markdown + JSON`

The device is read at most once per run and never modified. Exports are a
projection of the latest snapshot; your snapshot history preserves everything,
so re-running after un-highlighting on the device never loses old data.

## JSON format

```json
{
  "schema": "kobo-backup/1",
  "generated": "2026-06-01",
  "source": "KoboReader-20260601-101010.sqlite",
  "books": [
    {
      "title": "…", "author": "…", "volume_id": "…",
      "highlights": [
        { "text": "…", "note": null, "date": "2025-03-17", "chapter_index": 4 }
      ]
    }
  ]
}
```

## Notes & compatibility

- Tested against Kobo firmware schemas with `Bookmark` and `content` tables. If a
  firmware update changes the schema, please open an issue.
- Note (annotation) support reads `Bookmark.Annotation`; if you write notes on
  highlights, they appear under each highlight.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).
````

- [ ] **Step 3: Commit**

```bash
git add README.md LICENSE
git commit -m "docs: add README and MIT license"
```

---

### Task 9: Retire the legacy script + full verification

**Files:**
- Delete: `kobo_highlights.py`

- [ ] **Step 1: Confirm the package fully replaces the old script**

Run: `python3 -m pytest -v`
Expected: all tests pass (test_package, test_model, test_reader, test_render_markdown, test_render_json, test_device, test_cli).

- [ ] **Step 2: Remove the legacy single-file script**

It is preserved in git history (baseline commit `ab90b6b`) and fully superseded by the package.

Run: `git rm kobo_highlights.py`
Expected: `rm 'kobo_highlights.py'`.

- [ ] **Step 3: Run the whole suite once more**

Run: `python3 -m pytest -q`
Expected: all tests pass; no reference to `kobo_highlights` remains.

- [ ] **Step 4: Commit**

```bash
git commit -m "refactor: retire kobo_highlights.py in favor of kobo_backup package"
```

---

## Self-review

**Spec coverage** (each spec section → task):
- §3 cross-platform detection → Task 6 (`_candidate_roots`, `detect_device`); read-only snapshot → Task 6 (`snapshot`); highlights **+ notes** → Task 3 (`reader`); Markdown + JSON → Tasks 4–5; `pip install` + `kobo-backup` command → Tasks 1 & 7; tests → every task; README/LICENSE → Task 8.
- §4 module layout → Tasks 2–7 create exactly the specced modules.
- §5 data model + notes caveat → Task 2 (model), Task 3 (fixture includes a note row, exercised by `test_read_books_captures_notes`).
- §6 CLI surface (`--format/--snapshot-only/--db/--device/--out`) → Task 7.
- §8 JSON schema `kobo-backup/1` → Task 5.
- §9 safety model → Task 6 (read-only URI, `.tmp`+atomic rename, timestamped, no-overwrite).
- §10 re-run semantics → documented in README (Task 8); snapshot append-only is structural in Task 6.
- §11 testing incl. a note row → Task 3 fixture.
- §12 zero runtime deps → no third-party imports in any module; only `dev = ["pytest"]`.
- §14 privacy/git → already enforced by committed `.gitignore`; no task adds personal data.

**Placeholder scan:** no "TBD/TODO/handle edge cases"; every code step contains complete code; every test step contains real assertions.

**Type/name consistency:** `read_books(db_path) -> list[Book]`; `Book(title, author, volume_id, highlights)` + `.year_range`; `Highlight(text, note, date, chapter_index)`; both renderers expose `render(books, meta) -> {filename: content}` with `meta={"generated","source"}`; `device.snapshot(src, backup_dir, *, stamp)`, `device.detect_device()`, `device._candidate_roots()` (the name patched in tests); `cli.main(argv)`. Cross-checked across tasks — consistent.

**Deferred verification (from spec §15):** real-note representation is exercised via a synthetic note row; confirm against a real notes-bearing DB when one is available. Windows volume-label detection uses `.kobo/KoboReader.sqlite` presence on each drive (label-based refinement deferred).
