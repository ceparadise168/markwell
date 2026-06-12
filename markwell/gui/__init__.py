"""Markwell's graphical interface — the sibling of `cli`.

`cli` is the command-line front-end; `gui` is the graphical one. Both are thin
presentation layers over the same safe core (`device` → `reader` → `model` →
`render`/`export`); neither reimplements it.

The GUI is implemented as a small **local web app**: a standard-library HTTP
server bound to 127.0.0.1 serves a hand-written HTML/CSS/JS interface and a tiny
JSON API. That choice keeps Markwell's two promises — zero third-party
dependencies and nothing ever leaving your machine — while giving a clean,
modern UI a terminal can't. Launch it with `markwell-gui` or
`python -m markwell.gui`.
"""
from __future__ import annotations
