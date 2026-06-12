"""The one-click ZIP archive: output tree + latest snapshot, sources untouched."""
import os
import pathlib
import zipfile

import pytest

from conftest import symlink_or_skip
from markwell.gui.service import Service




@pytest.fixture
def service(tmp_path):
    return Service(tmp_path / "data")


def _seed_outputs(svc, names=("index.md", "cards/Book_One.png")):
    for rel in names:
        p = svc.out_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"content of {rel}", encoding="utf-8")


def _seed_snapshots(svc, stamps=("20260101-090000", "20260601-120000")):
    svc.backup_dir.mkdir(parents=True, exist_ok=True)
    for stamp in stamps:
        (svc.backup_dir / f"KoboReader-{stamp}.sqlite").write_bytes(
            b"snapshot " + stamp.encode())


def test_archive_bundles_outputs_and_latest_snapshot(service):
    _seed_outputs(service)
    _seed_snapshots(service)

    result = service.make_archive()

    assert result["name"].startswith("Markwell-archive-")
    assert result["name"].endswith(".zip")
    path = pathlib.Path(result["path"])
    assert path.parent == service.data_dir  # data-dir ROOT, outside output/
    assert result["files"] == 3

    with zipfile.ZipFile(path) as zf:
        assert zf.testzip() is None  # every member readable, CRCs OK
        # exactly the output tree + the LATEST snapshot; the older snapshot
        # is deliberately absent (the archive is a fresh pair, not a history)
        assert sorted(zf.namelist()) == [
            "backups/KoboReader-20260601-120000.sqlite",
            "output/cards/Book_One.png",
            "output/index.md",
        ]
        assert zf.read("output/index.md") == b"content of index.md"
        assert zf.read("backups/KoboReader-20260601-120000.sqlite"
                       ) == b"snapshot 20260601-120000"
    # archiving reads, never moves: every source file is still in place
    assert (service.out_dir / "index.md").is_file()
    assert (service.backup_dir / "KoboReader-20260101-090000.sqlite").is_file()


def test_archive_outputs_only_still_works(service):
    _seed_outputs(service, names=("index.md",))
    result = service.make_archive()
    assert result["files"] == 1
    with zipfile.ZipFile(result["path"]) as zf:
        assert zf.namelist() == ["output/index.md"]


def test_archive_latest_snapshot_only_still_works(service):
    _seed_snapshots(service)
    result = service.make_archive()
    assert result["files"] == 1
    with zipfile.ZipFile(result["path"]) as zf:
        assert zf.namelist() == ["backups/KoboReader-20260601-120000.sqlite"]


def test_archive_nothing_to_archive_raises(service):
    with pytest.raises(ValueError) as err:
        service.make_archive()
    assert str(err.value) == "nothing to archive"


def test_archive_refuses_while_export_running(service):
    _seed_outputs(service)
    service._job.state = "running"
    with pytest.raises(RuntimeError) as err:
        service.make_archive()
    assert str(err.value) == "export running"
    assert list(service.data_dir.glob("*.zip")) == []  # refused before writing


def test_archive_zip_is_never_swept_into_the_next_archive(service):
    # the zip lives at the data-dir root — outside output/ and outside the
    # backups/KoboReader-*.sqlite glob — so a second archive can never inhale
    # the first (no snowballing zips-of-zips)
    _seed_outputs(service)
    _seed_snapshots(service)
    service.make_archive()
    second = service.make_archive()
    with zipfile.ZipFile(second["path"]) as zf:
        assert not any(n.endswith(".zip") for n in zf.namelist())
        assert zf.testzip() is None


# ---- symlinks: never followed into an archive --------------------------------

def test_archive_excludes_symlinked_file_in_output(service, tmp_path):
    # cloud sync can plant a link in output/ pointing anywhere; dereferencing
    # it would copy the TARGET's content into a zip the reader then shares
    _seed_outputs(service, names=("index.md",))
    secret = tmp_path / "secret-outside"
    secret.write_text("private key material", encoding="utf-8")
    symlink_or_skip(secret, service.out_dir / "leak.md")

    result = service.make_archive()

    assert result["files"] == 1
    with zipfile.ZipFile(result["path"]) as zf:
        assert zf.namelist() == ["output/index.md"]


def test_archive_never_descends_into_symlinked_directory(service, tmp_path):
    # a symlinked DIRECTORY is the same leak one hop removed: the files
    # reached through it are not themselves links, so the walk must refuse
    # to descend rather than rely on filtering link entries
    _seed_outputs(service, names=("index.md",))
    outside = tmp_path / "outside-dir"
    outside.mkdir()
    (outside / "id_rsa").write_text("SECRET", encoding="utf-8")
    symlink_or_skip(outside, service.out_dir / "evil")

    result = service.make_archive()

    assert result["files"] == 1
    with zipfile.ZipFile(result["path"]) as zf:
        assert zf.namelist() == ["output/index.md"]


def test_archive_never_picks_a_symlinked_snapshot_as_latest(service, tmp_path):
    _seed_snapshots(service)
    outside = tmp_path / "outside-db"
    outside.write_bytes(b"NOT YOUR SNAPSHOT")
    # the name sorts AFTER every real snapshot, so it would win latest-pick
    symlink_or_skip(outside,
                     service.backup_dir / "KoboReader-29990101-000000.sqlite")

    result = service.make_archive()

    with zipfile.ZipFile(result["path"]) as zf:
        assert zf.namelist() == ["backups/KoboReader-20260601-120000.sqlite"]
        assert zf.read("backups/KoboReader-20260601-120000.sqlite"
                       ) == b"snapshot 20260601-120000"


def test_archive_with_only_a_symlinked_snapshot_is_nothing_to_archive(
        service, tmp_path):
    service.backup_dir.mkdir(parents=True)
    outside = tmp_path / "outside-db"
    outside.write_bytes(b"NOT YOUR SNAPSHOT")
    symlink_or_skip(outside,
                     service.backup_dir / "KoboReader-20260601-120000.sqlite")
    with pytest.raises(ValueError) as err:
        service.make_archive()
    assert str(err.value) == "nothing to archive"


# ---- atomic write -------------------------------------------------------------

def test_archive_failure_leaves_no_zip_and_no_tmp(service, monkeypatch):
    _seed_outputs(service)

    def boom(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(zipfile.ZipFile, "write", boom)
    with pytest.raises(OSError):
        service.make_archive()
    # no half-written archive and no stray staging file for cloud sync to spread
    assert list(service.data_dir.glob("*.zip")) == []
    assert list(service.data_dir.glob("*.tmp")) == []


def test_archive_success_leaves_only_the_final_zip(service):
    _seed_outputs(service, names=("index.md",))
    result = service.make_archive()
    assert sorted(p.name for p in service.data_dir.iterdir()) == [
        result["name"], "output"]
