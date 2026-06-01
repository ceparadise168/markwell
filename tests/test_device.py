import sqlite3

from kobo_backup.device import detect_device, snapshot


def _make_src(path):
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE t (x)")
    conn.execute("INSERT INTO t VALUES (1)")
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
    monkeypatch.setattr("kobo_backup.device._candidate_roots", lambda: [root])
    assert detect_device() == db


def test_detect_device_returns_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.setattr("kobo_backup.device._candidate_roots",
                        lambda: [tmp_path / "nope"])
    assert detect_device() is None
