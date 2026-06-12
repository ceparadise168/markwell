import csv
import io

from markwell.model import Book, Highlight
from markwell.render.csv import render

META = {"generated": "2026-06-01", "source": "snap.sqlite", "version": "0.1.0"}


def _books():
    return [
        Book("書名: 副標", "張三", "v1", [
            Highlight('she said "hi, there"', note="my, note",
                      date="2024-01-01", chapter_index=1),
            Highlight("第二段重點", note=None, date="2024-02-01", chapter_index=2),
        ]),
        Book("Plain", "", "v2", [Highlight("simple", date="2025-01-01")]),
    ]


def test_csv_starts_with_bom_for_excel():
    out = render(_books(), META)["highlights.csv"]
    assert out.startswith("﻿")


def test_csv_filename_and_exact_header():
    files = render(_books(), META)
    assert set(files) == {"highlights.csv"}
    first = files["highlights.csv"].lstrip("﻿").split("\r\n", 1)[0]
    assert first == "title,author,chapter_index,date,text,note,volume_id"


def test_csv_round_trips_through_stdlib_reader():
    # also proves the module's internal `import csv` reached the STDLIB module,
    # not itself, despite the markwell/render/csv.py name collision
    out = render(_books(), META)["highlights.csv"]
    rows = list(csv.reader(io.StringIO(out.lstrip("﻿"))))
    assert len(rows) == 1 + 3  # header + one row per highlight, across books
    assert rows[1] == ["書名: 副標", "張三", "1", "2024-01-01",
                       'she said "hi, there"', "my, note", "v1"]
    assert rows[2][4] == "第二段重點"  # CJK survives the round-trip
    assert rows[2][5] == ""           # note None → empty string
    assert rows[3] == ["Plain", "", "0", "2025-01-01", "simple", "", "v2"]


def test_csv_uses_crlf_line_endings():
    out = render(_books(), META)["highlights.csv"]
    assert out.endswith("\r\n")
    assert out.count("\n") == out.count("\r\n")  # every newline is a CRLF
