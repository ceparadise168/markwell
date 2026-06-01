import json
import sqlite3

import pytest

import markwell.cli as cli
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


def test_require_device_exits_nonzero_without_device(tmp_path, monkeypatch):
    monkeypatch.setattr(cli.device, "detect_device", lambda: None)
    with pytest.raises(SystemExit) as exc:
        main(["--require-device", "--out", str(tmp_path / "out"),
              "--backup-dir", str(tmp_path / "backups")])
    assert exc.value.code not in (0, None)


def test_device_wrong_path_exits_with_assertion(tmp_path, capsys):
    bogus = tmp_path / "not-a-kobo"
    bogus.mkdir()
    with pytest.raises(SystemExit) as exc:
        main(["--device", str(bogus), "--out", str(tmp_path / "out"),
              "--backup-dir", str(tmp_path / "backups")])
    assert exc.value.code == 2
    assert "--device path has no KoboReader.sqlite" in capsys.readouterr().err


def test_atomic_write_leaves_no_tmp(kobo_db, tmp_path):
    out = tmp_path / "out"
    main(["--db", str(kobo_db), "--out", str(out),
          "--backup-dir", str(tmp_path / "backups")])
    assert not list(out.glob("*.tmp"))


def test_manifest_prunes_orphan_but_keeps_hand_authored(kobo_db, tmp_path):
    out = tmp_path / "out"
    backups = tmp_path / "backups"
    # First run: generates the standard set + writes a manifest.
    main(["--db", str(kobo_db), "--out", str(out), "--backup-dir", str(backups)])
    manifest = json.loads((out / cli._MANIFEST).read_text(encoding="utf-8"))

    # A book file Markwell generated last run, now imagine the book is gone.
    orphan = next(p for p in out.glob("*.md") if p.name != "index.md")
    assert orphan.name in manifest

    # A file the user hand-authored — never recorded in any manifest.
    hand = out / "_my_notes.md"
    hand.write_text("# my own notes\n", encoding="utf-8")

    # Forge a prior manifest that lists the orphan but NOT the hand-authored file,
    # simulating that orphan was generated last run and won't be this run.
    (out / cli._MANIFEST).write_text(
        json.dumps([orphan.name, "index.md", "highlights.json"]) + "\n",
        encoding="utf-8")

    # Second run: only vol-2 survives if vol-1 vanished — but here we just want to
    # confirm pruning logic, so re-export json only (no per-book .md regenerated).
    main(["--db", str(kobo_db), "--out", str(out), "--format", "json",
          "--backup-dir", str(backups)])

    assert not orphan.exists()          # prior-generated orphan was pruned
    assert hand.exists()                # hand-authored file untouched (critical)
    assert (out / cli._MANIFEST).is_file()  # manifest itself is never deleted


def test_first_run_deletes_nothing(kobo_db, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    # A pre-existing hand-authored file with no manifest present.
    hand = out / "_notes.md"
    hand.write_text("keep me\n", encoding="utf-8")
    main(["--db", str(kobo_db), "--out", str(out),
          "--backup-dir", str(tmp_path / "backups")])
    assert hand.exists()  # first run (no prior manifest) deletes nothing


def test_status_text_on_stderr_not_stdout(kobo_db, tmp_path, capsys):
    out = tmp_path / "out"
    main(["--db", str(kobo_db), "--out", str(out),
          "--backup-dir", str(tmp_path / "backups")])
    captured = capsys.readouterr()
    assert "highlights/notes" in captured.err
    assert "source:" in captured.err
    assert captured.out == ""  # stdout reserved for data


def _empty_db(path):
    """A readable sqlite file with none of Kobo's tables -> schema error path."""
    conn = sqlite3.connect(str(path))
    conn.close()
    return path


def test_schema_error_clean_exit_without_debug(tmp_path):
    db = _empty_db(tmp_path / "empty.sqlite")
    with pytest.raises(SystemExit):  # clean exit, not a raw traceback
        main(["--db", str(db), "--out", str(tmp_path / "out"),
              "--backup-dir", str(tmp_path / "backups")])


def test_schema_error_reraises_with_debug(tmp_path):
    db = _empty_db(tmp_path / "empty.sqlite")
    with pytest.raises(Exception) as exc:
        main(["--db", str(db), "--debug", "--out", str(tmp_path / "out"),
              "--backup-dir", str(tmp_path / "backups")])
    assert not isinstance(exc.value, SystemExit)  # --debug re-raises the real error


def test_version_prints(capsys):
    from markwell import __version__
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out
