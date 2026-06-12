"""Config round-trip and resilience: a broken config must never break startup."""
import pathlib

import pytest

from markwell import config


@pytest.fixture
def cfg_dir(tmp_path, monkeypatch):
    """Point the config at a throwaway dir so tests never touch ~/.markwell."""
    monkeypatch.setenv("MARKWELL_CONFIG_DIR", str(tmp_path))
    return tmp_path


def test_env_override_is_respected(cfg_dir):
    assert config.config_path() == cfg_dir / "config.json"


def test_default_location_is_home_dot_markwell(monkeypatch):
    monkeypatch.delenv("MARKWELL_CONFIG_DIR", raising=False)
    assert config.config_path() == pathlib.Path.home() / ".markwell" / "config.json"


def test_round_trip(cfg_dir):
    config.save({"data_dir": "/somewhere/Markwell"})
    assert config.load() == {"data_dir": "/somewhere/Markwell"}


def test_load_missing_file_is_empty_dict(cfg_dir):
    assert not (cfg_dir / "config.json").exists()
    assert config.load() == {}


def test_load_corrupt_json_is_empty_dict(cfg_dir):
    (cfg_dir / "config.json").write_text("{not json", encoding="utf-8")
    assert config.load() == {}


def test_load_non_dict_json_is_empty_dict(cfg_dir):
    # valid JSON of the wrong shape (hand-edited) must coerce, not crash
    (cfg_dir / "config.json").write_text('["data_dir"]', encoding="utf-8")
    assert config.load() == {}


def test_save_creates_parent_dirs(tmp_path, monkeypatch):
    nested = tmp_path / "deep" / "nested"
    monkeypatch.setenv("MARKWELL_CONFIG_DIR", str(nested))
    config.save({"data_dir": "/x"})
    assert config.load() == {"data_dir": "/x"}


def test_save_is_atomic_and_leaves_no_tmp_residue(cfg_dir):
    config.save({"data_dir": "/x"})
    config.save({"data_dir": "/y"})  # overwrite path goes through replace too
    assert [p.name for p in cfg_dir.iterdir()] == ["config.json"]
    assert config.load() == {"data_dir": "/y"}


def test_unicode_value_round_trips_and_stays_readable(cfg_dir):
    config.save({"data_dir": "/Users/讀者/雲端硬碟/Markwell"})
    assert config.load()["data_dir"] == "/Users/讀者/雲端硬碟/Markwell"
    raw = (cfg_dir / "config.json").read_text(encoding="utf-8")
    assert "雲端硬碟" in raw  # ensure_ascii=False: human-readable on disk
    assert raw.endswith("\n")  # trailing newline: friendly to editors and diffs
