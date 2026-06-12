"""Data-dir relocation (copy-only), cloud-folder detection, boot-time resolve.

The data-dir setting is the one fenced exception to the GUI rule that nothing
the browser sends is used as a filesystem path. These tests pin the fence:
validation order, the exact (stable, i18n-ready) error messages, the
copy-never-move relocation semantics, and config persistence.
"""
import os
import pathlib
import sys

import pytest

from conftest import symlink_or_skip
from markwell import config
from markwell.gui.service import (Service, default_data_dir, detect_cloud_roots,
                                  resolve_data_dir)


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Keep every test away from the real ~/.markwell/config.json."""
    monkeypatch.setenv("MARKWELL_CONFIG_DIR", str(tmp_path / "confdir"))


@pytest.fixture
def service(tmp_path):
    svc = Service(tmp_path / "data")
    _seed(svc)
    return svc


def _seed(svc):
    """Two fake snapshots + an output tree (with a subfolder) to relocate.

    Plain bytes, not real SQLite: relocation must copy files verbatim without
    ever opening them, so unopenable content is itself part of the test.
    """
    svc.backup_dir.mkdir(parents=True, exist_ok=True)
    for stamp in ("20260101-090000", "20260601-120000"):
        (svc.backup_dir / f"KoboReader-{stamp}.sqlite").write_bytes(
            b"snapshot " + stamp.encode())
    for rel in ("index.md", "highlights.json", "cards/Book_One.png"):
        p = svc.out_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"content of {rel}", encoding="utf-8")


def _fake_kobo(tmp_path):
    """A dir detect_device would accept as a Kobo (mirrors test_device.py)."""
    root = tmp_path / "KOBOeReader"
    (root / ".kobo").mkdir(parents=True)
    (root / ".kobo" / "KoboReader.sqlite").write_text("")
    return root


# ---- change_data_dir: the relocation itself ---------------------------------

def test_change_copies_everything_and_leaves_old_intact(service, tmp_path):
    old_backup, old_out = service.backup_dir, service.out_dir
    target = tmp_path / "cloud" / "Markwell"

    result = service.change_data_dir(str(target))

    resolved = target.resolve()
    assert result == {"old": str(tmp_path / "data"), "new": str(resolved),
                      "copied_snapshots": 2, "copied_outputs": 3}
    # the service now lives in the new location...
    assert service.data_dir == resolved
    assert service.backup_dir == resolved / "backups"
    assert service.out_dir == resolved / "output"
    # ...the copies are real, structure preserved...
    assert (resolved / "backups" / "KoboReader-20260601-120000.sqlite"
            ).read_bytes() == b"snapshot 20260601-120000"
    assert (resolved / "output" / "cards" / "Book_One.png"
            ).read_text(encoding="utf-8") == "content of cards/Book_One.png"
    # ...and every old file is still exactly where it was (copy, never move)
    assert sorted(p.name for p in old_backup.iterdir()) == [
        "KoboReader-20260101-090000.sqlite",
        "KoboReader-20260601-120000.sqlite"]
    assert (old_out / "index.md").is_file()
    assert (old_out / "highlights.json").is_file()
    assert (old_out / "cards" / "Book_One.png").is_file()


def test_change_skips_existing_destination_files_without_overwriting(
        service, tmp_path):
    target = tmp_path / "synced"
    (target / "backups").mkdir(parents=True)
    (target / "backups" / "KoboReader-20260101-090000.sqlite").write_bytes(
        b"already synced, do not touch")
    (target / "output").mkdir()
    (target / "output" / "index.md").write_text("theirs", encoding="utf-8")

    result = service.change_data_dir(str(target))

    assert result["copied_snapshots"] == 1  # only the one that was missing
    assert result["copied_outputs"] == 2
    # skip means SKIP: files already at the destination are never overwritten
    assert (target / "backups" / "KoboReader-20260101-090000.sqlite"
            ).read_bytes() == b"already synced, do not touch"
    assert (target / "output" / "index.md"
            ).read_text(encoding="utf-8") == "theirs"


def test_change_to_current_dir_is_a_harmless_no_op(service):
    before = service.data_dir
    result = service.change_data_dir(str(service.data_dir))
    assert result["copied_snapshots"] == 0 and result["copied_outputs"] == 0
    assert service.data_dir == before.resolve()
    assert (service.out_dir / "index.md").is_file()


def test_change_refuses_relative_path(service):
    with pytest.raises(ValueError) as err:
        service.change_data_dir("rel/path")
    assert str(err.value) == "path must be absolute"
    assert service.data_dir.name == "data"  # nothing changed
    assert config.load() == {}              # nothing persisted


def test_change_refuses_file_target(service, tmp_path):
    blocker = tmp_path / "a-file"
    blocker.write_text("not a folder")
    with pytest.raises(ValueError) as err:
        service.change_data_dir(str(blocker))
    assert str(err.value) == "path is a file"


def test_change_refuses_target_inside_kobo_device(service, tmp_path,
                                                  monkeypatch):
    root = _fake_kobo(tmp_path)
    monkeypatch.setattr("markwell.device._candidate_roots", lambda: [root])
    for target in (root / "sub", root):  # nested, and the mount root itself
        with pytest.raises(ValueError) as err:
            service.change_data_dir(str(target))
        assert str(err.value) == "path is inside the Kobo device"
    assert config.load() == {}


def test_change_allows_candidate_mount_that_is_not_a_kobo(service, tmp_path,
                                                          monkeypatch):
    # On Windows device._candidate_roots() is EVERY existing drive letter, so
    # a bare candidate must not poison ordinary paths: only a candidate that
    # actually hosts a Kobo database (.kobo/KoboReader.sqlite) blocks targets.
    drive = tmp_path / "drive"
    drive.mkdir()
    monkeypatch.setattr("markwell.device._candidate_roots", lambda: [drive])
    result = service.change_data_dir(str(drive / "Markwell"))
    assert result["copied_snapshots"] == 2


def test_change_maps_unwritable_target_to_value_error(service, tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("")  # a FILE where a parent dir is needed: mkdir fails
    with pytest.raises(ValueError) as err:
        service.change_data_dir(str(blocker / "inner"))
    assert str(err.value) == "path is not writable"


def test_change_refuses_while_export_running(service, tmp_path):
    service._job.state = "running"
    with pytest.raises(RuntimeError) as err:
        service.change_data_dir(str(tmp_path / "elsewhere"))
    assert str(err.value) == "export running"
    assert not (tmp_path / "elsewhere").exists()  # refused before any disk work


def test_change_persists_data_dir_and_preserves_other_config_keys(service,
                                                                  tmp_path):
    config.save({"some_future_key": "kept"})
    target = tmp_path / "new-home"
    service.change_data_dir(str(target))
    saved = config.load()
    assert saved["data_dir"] == str(target.resolve())
    assert saved["some_future_key"] == "kept"


# ---- symlinks: never listed as snapshots, never copied by relocation ---------



def test_snapshot_list_excludes_symlinked_snapshot(service, tmp_path):
    # cloud sync can plant a KoboReader-*.sqlite-named link in backups/; it
    # must never be listed, win latest-pick, or become loadable by name
    outside = tmp_path / "outside-db"
    outside.write_bytes(b"NOT YOUR SNAPSHOT")
    symlink_or_skip(outside,
                     service.backup_dir / "KoboReader-29990101-000000.sqlite")
    rows = service.snapshot_list()
    assert [r["name"] for r in rows] == [
        "KoboReader-20260601-120000.sqlite",
        "KoboReader-20260101-090000.sqlite"]
    assert rows[0]["is_latest"]  # the real newest still wins latest-pick


def test_change_never_copies_symlinks(service, tmp_path):
    # links planted in output/ (file and directory) and backups/ must not be
    # dereferenced into the new folder — relocation copies only real files
    secret = tmp_path / "secret-outside"
    secret.write_text("private", encoding="utf-8")
    symlink_or_skip(secret, service.out_dir / "leak.md")
    outside_dir = tmp_path / "outside-dir"
    outside_dir.mkdir()
    (outside_dir / "id_rsa").write_text("SECRET", encoding="utf-8")
    os.symlink(str(outside_dir), str(service.out_dir / "evil"),
               target_is_directory=True)
    outside_db = tmp_path / "outside-db"
    outside_db.write_bytes(b"NOT YOUR SNAPSHOT")
    os.symlink(str(outside_db),
               str(service.backup_dir / "KoboReader-29990101-000000.sqlite"))

    target = tmp_path / "cloud" / "Markwell"
    result = service.change_data_dir(str(target))

    # counts cover only the real files (2 snapshots + 3 outputs from _seed)
    assert result["copied_snapshots"] == 2
    assert result["copied_outputs"] == 3
    resolved = target.resolve()
    copied = sorted(p.relative_to(resolved).as_posix()
                    for p in resolved.rglob("*") if not p.is_dir())
    assert copied == [
        "backups/KoboReader-20260101-090000.sqlite",
        "backups/KoboReader-20260601-120000.sqlite",
        "output/cards/Book_One.png",
        "output/highlights.json",
        "output/index.md"]


# ---- detect_cloud_roots -------------------------------------------------------

def test_cloud_roots_empty_when_nothing_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert detect_cloud_roots(home=tmp_path / "nobody") == []


def test_cloud_roots_macos_probe_map(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    home = tmp_path
    (home / "Library" / "Mobile Documents" / "com~apple~CloudDocs"
     ).mkdir(parents=True)
    (home / "Library" / "CloudStorage" / "GoogleDrive-x@y.z"
     ).mkdir(parents=True)
    (home / "Library" / "CloudStorage" / "OneDrive-Personal").mkdir()
    (home / "Dropbox").mkdir()
    roots = detect_cloud_roots(home=home)
    assert [(r["id"], r["label"]) for r in roots] == [
        ("icloud", "iCloud Drive"), ("dropbox", "Dropbox"),
        ("gdrive", "Google Drive"), ("onedrive", "OneDrive")]
    by_id = {r["id"]: r["path"] for r in roots}
    assert by_id["icloud"].endswith("com~apple~CloudDocs")
    assert by_id["gdrive"].endswith("GoogleDrive-x@y.z")
    assert by_id["onedrive"].endswith("OneDrive-Personal")


def test_cloud_roots_first_existing_candidate_wins(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    (tmp_path / "Dropbox").mkdir()
    (tmp_path / "Library" / "CloudStorage" / "Dropbox-Personal"
     ).mkdir(parents=True)
    roots = detect_cloud_roots(home=tmp_path)
    assert len(roots) == 1  # one entry per provider, not one per candidate
    assert roots[0]["path"] == str(tmp_path / "Dropbox")  # listed order wins


def test_cloud_roots_default_home_is_path_home(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    (tmp_path / "Dropbox").mkdir()
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)
    assert [r["id"] for r in detect_cloud_roots()] == ["dropbox"]


def test_cloud_roots_windows_probe_map(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    (tmp_path / "iCloudDrive").mkdir()
    (tmp_path / "Google Drive").mkdir()
    corporate = tmp_path / "OneDrive - Tailwind Co"
    corporate.mkdir()
    monkeypatch.setenv("OneDrive", str(corporate))  # env wins over ~/OneDrive
    (tmp_path / "OneDrive").mkdir()
    roots = detect_cloud_roots(home=tmp_path)
    by_id = {r["id"]: r["path"] for r in roots}
    assert by_id == {"icloud": str(tmp_path / "iCloudDrive"),
                     "gdrive": str(tmp_path / "Google Drive"),
                     "onedrive": str(corporate)}


def test_cloud_roots_linux_probe_map(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    (tmp_path / "Dropbox").mkdir()
    (tmp_path / "GoogleDrive").mkdir()
    (tmp_path / "OneDrive").mkdir()
    assert [r["id"] for r in detect_cloud_roots(home=tmp_path)] == [
        "dropbox", "gdrive", "onedrive"]


def test_cloud_roots_unknown_platform_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "platform", "sunos5")
    (tmp_path / "Dropbox").mkdir()
    assert detect_cloud_roots(home=tmp_path) == []


# ---- resolve_data_dir: boot-time precedence -----------------------------------

def test_resolve_flag_wins_over_config(tmp_path):
    config.save({"data_dir": str(tmp_path / "from-config")})
    assert resolve_data_dir(str(tmp_path / "from-flag")) == \
        tmp_path / "from-flag"


def test_resolve_uses_valid_config_when_no_flag(tmp_path):
    saved = tmp_path / "chosen"
    saved.mkdir()
    config.save({"data_dir": str(saved)})
    assert resolve_data_dir(None) == saved.resolve()


def test_resolve_falls_back_to_default_when_no_config(capsys):
    assert resolve_data_dir(None) == default_data_dir()
    assert capsys.readouterr().err == ""  # no config is normal, not a warning


def test_resolve_ignores_relative_config_with_warning(capsys):
    config.save({"data_dir": "rel/path"})
    assert resolve_data_dir(None) == default_data_dir()
    err = capsys.readouterr().err
    assert "ignoring" in err and "rel/path" in err


def test_resolve_ignores_config_that_is_a_file(tmp_path, capsys):
    blocker = tmp_path / "blocker"
    blocker.write_text("")
    config.save({"data_dir": str(blocker)})
    assert resolve_data_dir(None) == default_data_dir()
    assert "ignoring" in capsys.readouterr().err


def test_resolve_ignores_config_inside_kobo_with_warning(tmp_path, monkeypatch,
                                                         capsys):
    # the world changes between runs: a saved dir can BECOME the Kobo's mount
    root = _fake_kobo(tmp_path)
    monkeypatch.setattr("markwell.device._candidate_roots", lambda: [root])
    config.save({"data_dir": str(root / "Markwell")})
    assert resolve_data_dir(None) == default_data_dir()
    assert "Kobo" in capsys.readouterr().err


def test_resolve_ignores_non_string_config(capsys):
    config.save({"data_dir": 123})  # hand-edited config: junk must not crash
    assert resolve_data_dir(None) == default_data_dir()
    assert "ignoring" in capsys.readouterr().err
