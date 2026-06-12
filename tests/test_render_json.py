import json

from markwell.model import Book, Highlight
from markwell.render.json import render

META = {"generated": "2026-06-01", "source": "snap.sqlite",
        "source_freshness": "device", "version": "0.2.0"}


def test_json_render_schema_and_content():
    books = [Book("T", "A", "v1", [
        Highlight("x", note="n", date="2024-01-01", chapter_index=1),
    ])]
    files = render(books, META)
    assert set(files) == {"highlights.json"}
    doc = json.loads(files["highlights.json"])
    assert doc["schema"] == "markwell/1"
    assert doc["generated"] == "2026-06-01"
    assert doc["source"] == "snap.sqlite"
    assert doc["source_freshness"] == "device"
    assert doc["generator"] == "markwell/0.2.0"
    # additive top-level fields within schema major 1; "schema" stays first
    assert set(doc) == {"schema", "generated", "source",
                        "source_freshness", "generator", "books"}
    assert list(doc)[0] == "schema"
    hl = doc["books"][0]["highlights"][0]
    assert hl == {"text": "x", "note": "n", "date": "2024-01-01", "chapter_index": 1}


def test_json_freshness_and_generator_fallback_when_meta_missing():
    # cli builds meta, but renderer must not crash if a key is absent
    books = [Book("T", "A", "v1", [Highlight("x", date="2024-01-01")])]
    doc = json.loads(render(books, {"generated": "2026-06-01",
                                    "source": "snap.sqlite"})["highlights.json"])
    assert doc["source_freshness"] is None
    assert doc["generator"] == "markwell/?"


def test_json_preserves_unicode():
    books = [Book("納瓦爾寶典", "A", "v1",
                  [Highlight("測試", date="2025-01-01")])]
    files = render(books, META)
    assert "納瓦爾寶典" in files["highlights.json"]  # not \uXXXX escaped
