import sqlite3
import sys

import pytest

from markwell import device
from markwell.device import detect_device, snapshot


def _make_src(path):
    # A Kobo-shaped source: snapshot() now verifies the snapshot has a Bookmark
    # table before committing it, so a valid source must carry one. The extra `t`
    # table lets the content-copy assertion below stay simple.
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE t (x)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.execute("CREATE TABLE Bookmark (BookmarkID TEXT)")
    conn.commit()
    conn.close()


def test_snapshot_is_timestamped_and_copies_content(tmp_path):
    src = tmp_path / "src.sqlite"
    _make_src(src)
    dest = snapshot(src, tmp_path / "backups", stamp="20260601-101010")
    assert dest.name == "KoboReader-20260601-101010.sqlite"
    assert dest.is_file()
    c = sqlite3.connect(str(dest))
    assert c.execute("SELECT x FROM t").fetchone()[0] == 1
    c.close()


def test_snapshot_distinct_stamps_coexist(tmp_path):
    src = tmp_path / "src.sqlite"
    _make_src(src)
    backups = tmp_path / "backups"
    d1 = snapshot(src, backups, stamp="20260601-101010")
    d2 = snapshot(src, backups, stamp="20260601-101011")
    assert d1.is_file() and d2.is_file() and d1 != d2


def test_snapshot_leaves_no_tmp_on_success(tmp_path):
    src = tmp_path / "src.sqlite"
    _make_src(src)
    backups = tmp_path / "backups"
    snapshot(src, backups, stamp="20260601-101010")
    assert list(backups.glob("*.tmp")) == []


def test_detect_device_finds_db(tmp_path, monkeypatch):
    root = tmp_path / "KOBOeReader"
    (root / ".kobo").mkdir(parents=True)
    db = root / ".kobo" / "KoboReader.sqlite"
    db.write_text("")  # presence is enough; detect_device does not open it
    monkeypatch.setattr("markwell.device._candidate_roots", lambda: [root])
    assert detect_device() == db


def test_detect_device_returns_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr("markwell.device._candidate_roots",
                        lambda: [tmp_path / "nope"])
    assert detect_device() is None


def test_snapshot_leaves_source_unmodified(tmp_path):
    src = tmp_path / "src.sqlite"
    _make_src(src)
    before = src.read_bytes()
    snapshot(src, tmp_path / "backups", stamp="20260601-101010")
    assert src.read_bytes() == before  # device DB byte-identical after snapshot


def test_snapshot_cleans_tmp_on_failure(tmp_path):
    # A non-SQLite source: connect() succeeds (lazy) but backup() fails mid-copy,
    # exercising snapshot()'s cleanup path after the .tmp has been created.
    src = tmp_path / "not_a_db.sqlite"
    src.write_bytes(b"this is definitely not a sqlite database")
    backups = tmp_path / "backups"
    with pytest.raises(sqlite3.DatabaseError):
        snapshot(src, backups, stamp="20260601-101010")
    # failure must leave neither a .tmp nor a final snapshot behind
    assert list(backups.glob("*.tmp")) == []
    assert list(backups.glob("KoboReader-*.sqlite")) == []


def test_snapshot_is_zero_touch_on_wal(wal_kobo_db, tmp_path):
    # A live WAL source (uncheckpointed -wal/-shm). The old mode=ro+backup()
    # path rewrites the device's -shm here (and fails outright on a read-only
    # mount); the copy-then-backup path must touch nothing on the source.
    src = wal_kobo_db
    src_dir = src.parent
    # Compare the device dir's own files only (the snapshot's backup dir lands
    # under tmp_path too; it is test scaffolding, not source state). This still
    # catches a rewritten -shm or any newly created -wal/-shm sibling.
    before = {p.name: p.read_bytes() for p in src_dir.iterdir() if p.is_file()}

    dest = snapshot(src, tmp_path / "backups", stamp="20260601-101010")

    after = {p.name: p.read_bytes() for p in src_dir.iterdir() if p.is_file()}
    assert after == before  # no new -wal/-shm, main file byte-identical

    # ...and the uncheckpointed WAL rows were still captured.
    c = sqlite3.connect(str(dest))
    try:
        assert c.execute("SELECT COUNT(*) FROM Bookmark").fetchone()[0] == 6
    finally:
        c.close()


def test_snapshot_rejects_db_without_bookmark_table(tmp_path):
    # A valid SQLite db that is not a Kobo DB must be refused, not committed.
    src = tmp_path / "src.sqlite"
    conn = sqlite3.connect(str(src))
    conn.execute("CREATE TABLE other (x)")
    conn.commit()
    conn.close()
    backups = tmp_path / "backups"
    with pytest.raises(sqlite3.DatabaseError):
        snapshot(src, backups, stamp="20260601-101010")
    assert list(backups.glob("*.tmp")) == []
    assert list(backups.glob("KoboReader-*.sqlite")) == []


def test_candidate_roots_darwin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    roots = device._candidate_roots()
    assert all(str(r).startswith("/Volumes/KOBOeReader") for r in roots)


def test_candidate_roots_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    roots = device._candidate_roots()
    assert any("KOBOeReader" in str(r) for r in roots)


def test_candidate_roots_windows_skips_floppy_letters(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    # Pretend every drive letter exists so the floppy-letter skip is what's tested.
    monkeypatch.setattr("markwell.device.os.path.exists", lambda p: True)
    roots = device._candidate_roots()
    letters = {str(r)[0] for r in roots}
    assert "A" not in letters and "B" not in letters
    assert "C" in letters


def test_candidate_roots_unknown_platform(monkeypatch):
    monkeypatch.setattr(sys, "platform", "sunos5")
    assert device._candidate_roots() == []
