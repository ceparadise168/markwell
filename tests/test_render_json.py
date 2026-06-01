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
