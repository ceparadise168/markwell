import json

from markwell.cli import main


def test_cli_exports_md_and_json_from_db(kobo_db, tmp_path):
    out = tmp_path / "out"
    main(["--db", str(kobo_db), "--out", str(out),
          "--backup-dir", str(tmp_path / "backups")])
    assert (out / "index.md").is_file()
    assert (out / "highlights.json").is_file()
    book_mds = [p for p in out.glob("*.md") if p.name != "index.md"]
    assert book_mds  # at least one per-book file
    doc = json.loads((out / "highlights.json").read_text(encoding="utf-8"))
    assert doc["schema"] == "markwell/1"


def test_cli_format_json_only(kobo_db, tmp_path):
    out = tmp_path / "out"
    main(["--db", str(kobo_db), "--out", str(out), "--format", "json",
          "--backup-dir", str(tmp_path / "backups")])
    assert (out / "highlights.json").is_file()
    assert not (out / "index.md").exists()


def test_cli_missing_db_exits(tmp_path):
    import pytest
    with pytest.raises(SystemExit):
        main(["--db", str(tmp_path / "nope.sqlite"), "--out", str(tmp_path / "o")])


def test_cli_device_accepts_mount_root(tmp_path, kobo_db):
    import shutil
    mount = tmp_path / "KOBOeReader"
    kobo_dir = mount / ".kobo"
    kobo_dir.mkdir(parents=True)
    shutil.copy(kobo_db, kobo_dir / "KoboReader.sqlite")
    out = tmp_path / "out"
    main(["--device", str(mount), "--out", str(out),
          "--backup-dir", str(tmp_path / "backups")])
    assert (out / "highlights.json").is_file()  # mount root resolved + snapshot + export
