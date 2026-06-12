"""The shared render+write core used by both the CLI and the GUI."""
import json

import pytest

from markwell.export import FORMATS, build_files, parse_formats, write_outputs
from markwell.model import Book, Highlight
from markwell.render import json as json_render

_META = {"generated": "2026-06-02", "source": "snap.sqlite",
         "source_freshness": "device", "version": "0.1.0"}
_BOOKS = [Book("A Title", "An Author", "vol-1",
               [Highlight("a passage", "a note", "2025-01-01", 1)])]


# ---- the format registry ------------------------------------------------------

def test_formats_registry_is_the_canonical_order():
    assert list(FORMATS) == ["md", "json", "csv", "anki", "html"]


def test_parse_formats_all_expands_in_canonical_order():
    assert parse_formats("all") == ["md", "json", "csv", "anki", "html"]


def test_parse_formats_comma_list():
    assert parse_formats("md,csv") == ["md", "csv"]


def test_parse_formats_tolerates_spaces():
    assert parse_formats(" md , csv ") == ["md", "csv"]


def test_parse_formats_orders_by_registry_not_by_caller():
    assert parse_formats("csv,md") == ["md", "csv"]


def test_parse_formats_dedups():
    assert parse_formats("md,md") == ["md"]


def test_parse_formats_accepts_iterables():
    assert parse_formats(["csv", "md"]) == ["md", "csv"]
    assert parse_formats(("json",)) == ["json"]


def test_parse_formats_unknown_id_raises_with_the_choices():
    with pytest.raises(ValueError) as exc:
        parse_formats("md,bogus")
    assert str(exc.value) == ("unknown format: bogus "
                              "(choose from md, json, csv, anki, html, or all)")


def test_parse_formats_empty_specs_raise():
    for empty in ("", None, [], " , "):
        with pytest.raises(ValueError):
            parse_formats(empty)


def test_parse_formats_junk_types_raise_valueerror_only():
    # the GUI silently coerces on ValueError; no spec shape may raise anything else
    for junk in (123, ["md", 7], [["md"]], object()):
        with pytest.raises(ValueError):
            parse_formats(junk)


# ---- build_files over the registry --------------------------------------------

def test_build_files_all_renders_every_registered_format():
    files = build_files(_BOOKS, _META, "all")
    assert "highlights.json" in files
    assert "index.md" in files
    assert any(n.endswith(".md") and n != "index.md" for n in files)
    assert {"highlights.csv", "anki.tsv", "library.html"} <= set(files)


def test_build_files_json_only():
    files = build_files(_BOOKS, _META, "json")
    assert set(files) == {"highlights.json"}


def test_build_files_comma_list_renders_exactly_those():
    files = build_files(_BOOKS, _META, "md,csv")
    assert set(files) == {"index.md", "A_Title.md", "highlights.csv"}


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
