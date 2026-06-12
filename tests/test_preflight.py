"""Tests for the release artifact privacy gate (packaging/preflight.py).

packaging/ is intentionally not an importable package (the name would collide with
the `packaging` PyPI library), so _forbidden is loaded by file path and preflight
is driven as a subprocess — which also exercises its real CLI exit-code contract.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_PREFLIGHT = _REPO / "packaging" / "preflight.py"
_FORBIDDEN = _REPO / "packaging" / "_forbidden.py"


def _load_forbidden():
    spec = importlib.util.spec_from_file_location("_markwell_forbidden", _FORBIDDEN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_forbidden_reason_flags_every_category():
    f = _load_forbidden()
    assert f.forbidden_reason("a/b/KoboReader.sqlite")
    assert f.forbidden_reason("a/b/KoboReader.sqlite-wal")
    assert f.forbidden_reason("x/.kobo/KoboReader.sqlite")
    assert f.forbidden_reason("deep/output/index.md")
    assert f.forbidden_reason("history/backups/snap.bin")
    assert f.forbidden_reason("pkg/__pycache__/mod.pyc")


def test_forbidden_reason_flags_interrupted_and_packed_data():
    """PR #1 review: an interrupted backup's .sqlite.tmp is a complete private
    snapshot, and a Markwell archive packs the whole library — neither may ship."""
    f = _load_forbidden()
    assert f.forbidden_reason("a/KoboReader-20260601-101010.sqlite.tmp")
    assert f.forbidden_reason("a/Markwell-archive-20260612-101010.zip")
    assert f.forbidden_reason("a/Markwell-archive-20260612-101010.zip.tmp")


def test_forbidden_reason_allows_real_app_files():
    f = _load_forbidden()
    assert f.forbidden_reason("markwell/gui/assets/app.js") is None
    assert f.forbidden_reason("markwell/gui/server.py") is None
    assert f.forbidden_reason("Markwell.app/Contents/MacOS/Markwell") is None
    # release artifacts themselves stay shippable: the archive rule is
    # name-scoped, never a bare ".zip" or ".tmp" match
    assert f.forbidden_reason("Markwell-macOS.zip") is None
    assert f.forbidden_reason("build/scratch.tmp") is None


def test_preflight_passes_on_clean_tree(tmp_path):
    (tmp_path / "Markwell").mkdir()
    (tmp_path / "Markwell" / "app.js").write_text("// ok")
    result = subprocess.run(
        [sys.executable, str(_PREFLIGHT), str(tmp_path)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_preflight_fails_and_names_offenders(tmp_path):
    (tmp_path / "Markwell").mkdir()
    (tmp_path / "Markwell" / "KoboReader.sqlite").write_text("db")
    (tmp_path / "Markwell" / ".kobo").mkdir()
    (tmp_path / "Markwell" / ".kobo" / "secret").write_text("x")
    result = subprocess.run(
        [sys.executable, str(_PREFLIGHT), str(tmp_path)],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "KoboReader.sqlite" in result.stdout
    assert ".kobo" in result.stdout


def test_preflight_usage_error_on_missing_path(tmp_path):
    result = subprocess.run(
        [sys.executable, str(_PREFLIGHT), str(tmp_path / "nope")],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 2
