"""Settings + archive over HTTP: the security-fenced data-dir surface.

POST /api/settings/data-dir is the ONE route where the browser may send a
filesystem path — and only for choice="custom"; every named choice ("home",
cloud ids) is resolved server-side from a fresh detect_cloud_roots(), so a
hostile page can never smuggle a path through a known choice. These tests pin
that fence, the stable error-message contract (the message doubles as an
error code the UI translates), the 409-while-running conflicts, and the
boot-time --data-dir resolution wiring.
"""
import argparse
import http.client
import json
import pathlib
import threading
import zipfile

import pytest

from markwell import config
from markwell.gui.server import _service_from_args, build_server, main
from markwell.gui.service import Service


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Keep every test away from the real ~/.markwell/config.json."""
    monkeypatch.setenv("MARKWELL_CONFIG_DIR", str(tmp_path / "confdir"))


@pytest.fixture
def service(tmp_path):
    return Service(tmp_path / "data")


@pytest.fixture
def live(service):
    httpd = build_server(service, port=0)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd, port
    finally:
        httpd.shutdown()
        httpd.server_close()


def _get(port, path, token=None):
    headers = {"X-Markwell-Token": token} if token is not None else {}
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request("GET", path, headers=headers)
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    conn.close()
    return resp.status, json.loads(body) if body else {}


def _post(port, path, token=None, body=None):
    payload = json.dumps(body or {}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["X-Markwell-Token"] = token
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request("POST", path, body=payload, headers=headers)
    resp = conn.getresponse()
    text = resp.read().decode("utf-8")
    conn.close()
    return resp.status, json.loads(text) if text else {}


def _seed_library(svc):
    """A snapshot + two output files. Plain bytes, never parsed: archive and
    relocation copy files verbatim without opening them."""
    svc.backup_dir.mkdir(parents=True, exist_ok=True)
    (svc.backup_dir / "KoboReader-20260601-120000.sqlite").write_bytes(b"snap")
    svc.out_dir.mkdir(parents=True, exist_ok=True)
    (svc.out_dir / "index.md").write_text("# index", encoding="utf-8")
    (svc.out_dir / "highlights.json").write_text("{}", encoding="utf-8")


# ---- GET /api/settings --------------------------------------------------------

def test_settings_reports_dirs_machine_facts_and_config_path(
        live, service, tmp_path, monkeypatch):
    roots = [{"id": "dropbox", "label": "Dropbox",
              "path": str(tmp_path / "Dropbox")}]
    monkeypatch.setattr("markwell.gui.server.detect_cloud_roots", lambda: roots)
    monkeypatch.setattr("markwell.gui.server.default_data_dir",
                        lambda: tmp_path / "Home" / "Markwell")
    httpd, port = live
    status, doc = _get(port, "/api/settings", token=httpd.token)
    assert status == 200
    assert doc == {
        "data_dir": str(service.data_dir),
        "backup_dir": str(service.backup_dir),
        "output_dir": str(service.out_dir),
        "config_path": str(config.config_path()),
        "cloud_roots": roots,
        "home": str(tmp_path / "Home" / "Markwell"),
    }


def test_settings_routes_require_token(live):
    # These routes sit behind the same /api/* gate as everything else — this
    # pins that nobody ever special-cases them in front of the token check.
    # Bodies are empty: even a hypothetically broken gate could not relocate.
    httpd, port = live
    assert _get(port, "/api/settings")[0] == 403
    assert _get(port, "/api/settings", token="wrong")[0] == 403
    assert _post(port, "/api/settings/data-dir")[0] == 403
    assert _post(port, "/api/archive")[0] == 403
    assert _post(port, "/api/archive", token="wrong")[0] == 403


# ---- POST /api/settings/data-dir ------------------------------------------------

def test_data_dir_unknown_choice(live):
    httpd, port = live
    status, doc = _post(port, "/api/settings/data-dir", token=httpd.token,
                        body={"choice": "magic-cloud"})
    assert (status, doc["error"]) == (400, "unknown choice")


def test_data_dir_junk_choice_is_400_not_500(live):
    # untrusted browser JSON: a missing or non-string choice must map to the
    # same clean error, never an unhandled TypeError -> 500
    httpd, port = live
    for body in ({}, {"choice": None}, {"choice": 123},
                 {"choice": ["icloud"]}, {"choice": {"id": "icloud"}}):
        status, doc = _post(port, "/api/settings/data-dir", token=httpd.token,
                            body=body)
        assert (status, doc["error"]) == (400, "unknown choice"), body


def test_data_dir_custom_requires_string_path(live):
    httpd, port = live
    for body in ({"choice": "custom"}, {"choice": "custom", "path": 123},
                 {"choice": "custom", "path": ["/x"]},
                 {"choice": "custom", "path": None}):
        status, doc = _post(port, "/api/settings/data-dir", token=httpd.token,
                            body=body)
        assert (status, doc["error"]) == (400, "path required"), body


def test_data_dir_custom_relative_path_refused(live):
    httpd, port = live
    status, doc = _post(port, "/api/settings/data-dir", token=httpd.token,
                        body={"choice": "custom", "path": "rel/path"})
    assert (status, doc["error"]) == (400, "path must be absolute")


def test_data_dir_custom_file_target_refused(live, tmp_path):
    blocker = tmp_path / "a-file"
    blocker.write_text("not a folder")
    httpd, port = live
    status, doc = _post(port, "/api/settings/data-dir", token=httpd.token,
                        body={"choice": "custom", "path": str(blocker)})
    assert (status, doc["error"]) == (400, "path is a file")


def test_data_dir_custom_happy_path_end_to_end(live, service, tmp_path):
    _seed_library(service)
    target = tmp_path / "cloud" / "Markwell"
    httpd, port = live
    status, report = _post(port, "/api/settings/data-dir", token=httpd.token,
                           body={"choice": "custom", "path": str(target)})
    assert status == 200
    resolved = target.resolve()
    assert report == {"old": str(tmp_path / "data"), "new": str(resolved),
                      "copied_snapshots": 1, "copied_outputs": 2}
    # the next settings read reflects the move...
    _, doc = _get(port, "/api/settings", token=httpd.token)
    assert doc["data_dir"] == str(resolved)
    assert doc["backup_dir"] == str(resolved / "backups")
    assert doc["output_dir"] == str(resolved / "output")
    # ...and the choice survived to disk, inside the isolated config home
    assert config.config_path().is_file()
    assert str(config.config_path()).startswith(str(tmp_path / "confdir"))
    assert config.load()["data_dir"] == str(resolved)


def test_data_dir_choice_home_resolves_server_side(live, service, tmp_path,
                                                   monkeypatch):
    home_target = tmp_path / "HomeSweet" / "Markwell"
    monkeypatch.setattr("markwell.gui.server.default_data_dir",
                        lambda: home_target)
    httpd, port = live
    status, report = _post(port, "/api/settings/data-dir", token=httpd.token,
                           body={"choice": "home"})
    assert status == 200
    assert report["new"] == str(home_target.resolve())
    assert service.data_dir == home_target.resolve()


def test_data_dir_cloud_choice_never_trusts_a_browser_path(
        live, service, tmp_path, monkeypatch):
    root = tmp_path / "iCloudDocs"
    root.mkdir()
    monkeypatch.setattr(
        "markwell.gui.server.detect_cloud_roots",
        lambda: [{"id": "icloud", "label": "iCloud Drive", "path": str(root)}])
    httpd, port = live
    evil = tmp_path / "evil"
    status, report = _post(port, "/api/settings/data-dir", token=httpd.token,
                           body={"choice": "icloud", "path": str(evil)})
    assert status == 200
    # the id was resolved server-side to <detected root>/Markwell — the
    # "path" key the page smuggled alongside it was ignored entirely
    assert report["new"] == str((root / "Markwell").resolve())
    assert service.data_dir == (root / "Markwell").resolve()
    assert not evil.exists()


def test_data_dir_change_refused_while_export_running(live, service, tmp_path):
    service._set(state="running")
    httpd, port = live
    status, doc = _post(port, "/api/settings/data-dir", token=httpd.token,
                        body={"choice": "custom",
                              "path": str(tmp_path / "elsewhere")})
    assert (status, doc["error"]) == (409, "export running")
    assert not (tmp_path / "elsewhere").exists()  # refused before any disk work


# ---- POST /api/archive ----------------------------------------------------------

def test_archive_with_nothing_to_archive(live):
    httpd, port = live
    status, doc = _post(port, "/api/archive", token=httpd.token)
    assert (status, doc["error"]) == (400, "nothing to archive")


def test_archive_bundles_outputs_and_latest_snapshot(live, service):
    _seed_library(service)
    httpd, port = live
    status, doc = _post(port, "/api/archive", token=httpd.token)
    assert status == 200
    assert doc["files"] == 3  # two output files + the latest snapshot
    zip_path = pathlib.Path(doc["path"])
    assert zip_path.is_file()
    assert zip_path.name == doc["name"]
    with zipfile.ZipFile(zip_path) as zf:
        names = sorted(zf.namelist())
    assert names == ["backups/KoboReader-20260601-120000.sqlite",
                     "output/highlights.json", "output/index.md"]


def test_archive_refused_while_export_running(live, service):
    _seed_library(service)
    service._set(state="running")
    httpd, port = live
    status, doc = _post(port, "/api/archive", token=httpd.token)
    assert (status, doc["error"]) == (409, "export running")


# ---- main(): boot-time --data-dir resolution -------------------------------------

def test_service_from_args_uses_saved_config_when_no_flag(tmp_path):
    chosen = tmp_path / "chosen"
    chosen.mkdir()
    config.save({"data_dir": str(chosen)})
    args = argparse.Namespace(data_dir=None, format="md,json,html")
    svc = _service_from_args(args)
    assert svc.data_dir == chosen.resolve()
    assert svc.fmt == "md,json,html"


def test_service_from_args_flag_beats_config(tmp_path):
    config.save({"data_dir": str(tmp_path / "from-config")})
    args = argparse.Namespace(data_dir=str(tmp_path / "from-flag"), format="md")
    assert _service_from_args(args).data_dir == tmp_path / "from-flag"


def test_main_leaves_the_data_dir_default_to_the_resolver(monkeypatch):
    # main() must not bake default_data_dir() into argparse: the saved
    # Settings choice is only reachable if an absent flag arrives as None.
    seen = []

    class _Stop(Exception):
        pass

    def capture(args):
        seen.append(args.data_dir)
        raise _Stop

    monkeypatch.setattr("markwell.gui.server._service_from_args", capture)
    with pytest.raises(_Stop):
        main([])
    assert seen == [None]
