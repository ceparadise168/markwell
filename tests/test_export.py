"""The shared render+write core used by both the CLI and the GUI."""
import json

from markwell.export import build_files, write_outputs
from markwell.model import Book, Highlight
from markwell.render import json as json_render

_META = {"generated": "2026-06-02", "source": "snap.sqlite",
         "source_freshness": "device", "version": "0.1.0"}
_BOOKS = [Book("A Title", "An Author", "vol-1",
               [Highlight("a passage", "a note", "2025-01-01", 1)])]


def test_build_files_all_has_md_and_json():
    files = build_files(_BOOKS, _META, "all")
    assert "highlights.json" in files
    assert "index.md" in files
    assert any(n.endswith(".md") and n != "index.md" for n in files)


def test_build_files_json_only():
    files = build_files(_BOOKS, _META, "json")
    assert set(files) == {"highlights.json"}


def test_document_matches_rendered_json():
    doc = json_render.document(_BOOKS, _META)
    text = json_render.render(_BOOKS, _META)["highlights.json"]
    assert json.loads(text) == doc
    assert doc["schema"] == "markwell/1"
    assert doc["books"][0]["highlights"][0]["note"] == "a note"


def test_write_outputs_is_atomic_and_counts(tmp_path):
    files = build_files(_BOOKS, _META, "all")
    n = write_outputs(files, tmp_path)
    assert n == len(files)
    assert not list(tmp_path.glob("*.tmp"))
    assert (tmp_path / "highlights.json").is_file()
