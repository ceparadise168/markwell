"""The one-click ZIP archive: output tree + latest snapshot, sources untouched."""
import pathlib
import zipfile

import pytest

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
