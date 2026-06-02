"""GUI service use-cases and the HTTP server's security boundary."""
import http.client
import re
import shutil
import threading
import time

import pytest

from conftest import make_kobo_db
from markwell.gui import sample
from markwell.gui.server import build_server
from markwell.gui.service import Service, _human_age, _parse_stamp
import datetime


@pytest.fixture
def service(tmp_path):
    return Service(tmp_path / "data")


def _place_snapshot(svc, src_db, stamp):
    """Drop a readable Kobo DB into the service's backup dir as a snapshot."""
    svc.backup_dir.mkdir(parents=True, exist_ok=True)
    dest = svc.backup_dir / f"KoboReader-{stamp}.sqlite"
    shutil.copy(src_db, dest)
    return dest


def _wait_export(svc, timeout=4.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = svc.export_status()
        if job["state"] != "running":
            return job
        time.sleep(0.02)
    raise AssertionError("export did not finish in time")


# ---- service: queries -------------------------------------------------------

def test_status_empty(service):
    s = service.status()
    assert s["snapshot_count"] == 0
    assert s["has_library"] is False
    assert s["data_dir"].endswith("data")
    assert isinstance(s["device_connected"], bool)


def test_library_empty_when_no_snapshot(service):
    doc = service.library()
    assert doc["source_kind"] == "empty"
    assert doc["books"] == []


def test_sample_library_shape_and_cjk(service):
    doc = service.library("sample")
    assert doc["source_kind"] == "sample"
    assert doc["schema"] == "markwell/1"
    titles = [b["title"] for b in doc["books"]]
    assert "道德經" in titles  # CJK content renders through the same path
    assert any(h["note"] for b in doc["books"] for h in b["highlights"])


def test_snapshot_list_newest_first(service, kobo_db):
    _place_snapshot(service, kobo_db, "20260101-090000")
    _place_snapshot(service, kobo_db, "20260601-120000")
    rows = service.snapshot_list()
    assert len(rows) == 2
    assert rows[0]["name"].endswith("20260601-120000.sqlite")
    assert rows[0]["is_latest"] is True
    assert rows[1]["is_latest"] is False
    assert rows[0]["size_kb"] >= 0


# ---- service: commands ------------------------------------------------------

def test_export_from_snapshot_then_view(service, kobo_db):
    name = _place_snapshot(service, kobo_db, "20260601-120000").name
    assert service.start_export(use_device=False, source=name) is True
    job = _wait_export(service)
    assert job["state"] == "done", job
    assert job["result"]["highlights"] >= 1
    assert job["result"]["books"] >= 1
    # files were written and the library now reflects the snapshot
    assert (service.out_dir / "highlights.json").is_file()
    doc = service.library("latest")
    assert doc["source_kind"] == "snapshot"
    assert doc["books"]


def test_export_no_device_reports_friendly_error(service, monkeypatch):
    monkeypatch.setattr("markwell.gui.service.device.detect_device",
                        lambda: None)
    assert service.start_export(use_device=True) is True
    job = _wait_export(service)
    assert job["state"] == "error"
    assert job["error"] == "no_device"
    assert "Kobo" in job["message"]


def test_export_rejects_unknown_source(service):
    # a name that isn't an existing snapshot must not be openable (no traversal)
    assert service.start_export(use_device=False,
                                source="../../etc/passwd") is True
    job = _wait_export(service)
    assert job["state"] == "error"
    assert job["error"] == "no_source"


def test_second_export_blocked_while_running(service, kobo_db, monkeypatch):
    # make the worker pause so the second call sees state == running
    import markwell.gui.service as mod
    monkeypatch.setattr(mod.device, "detect_device", lambda: None)
    monkeypatch.setattr(mod.reader, "read_books",
                        lambda p: time.sleep(0.3) or [])
    name = _place_snapshot(service, kobo_db, "20260601-120000").name
    assert service.start_export(use_device=False, source=name) is True
    assert service.start_export(use_device=False, source=name) is False
    _wait_export(service)


def test_helpers():
    assert _parse_stamp("KoboReader-20260601-101010.sqlite") is not None
    assert _parse_stamp("not-a-snapshot.sqlite") is None
    now = datetime.datetime(2026, 6, 2, 12, 0, 0)
    assert _human_age(now, now) == "just now"
    assert _human_age(now - datetime.timedelta(days=1), now) == "yesterday"


# ---- server: security boundary ----------------------------------------------

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


def _get(port, path, token=None, host=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.putrequest("GET", path, skip_host=True, skip_accept_encoding=True)
    conn.putheader("Host", host or f"127.0.0.1:{port}")
    if token is not None:
        conn.putheader("X-Markwell-Token", token)
    conn.endheaders()
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    conn.close()
    return resp.status, body


def test_index_served_with_token_injected(live):
    httpd, port = live
    status, body = _get(port, "/")
    assert status == 200
    assert "Markwell" in body
    assert httpd.token in body
    assert "__MARKWELL_TOKEN__" not in body  # placeholder was replaced


def test_api_requires_token(live):
    httpd, port = live
    assert _get(port, "/api/status")[0] == 403           # no token
    assert _get(port, "/api/status", token="wrong")[0] == 403
    assert _get(port, "/api/status", token=httpd.token)[0] == 200


def test_api_rejects_foreign_host(live):
    httpd, port = live
    status, _ = _get(port, "/api/status", token=httpd.token, host="evil.example")
    assert status == 403  # DNS-rebinding guard


def test_static_and_unknown_routes(live):
    httpd, port = live
    assert _get(port, "/style.css")[0] == 200
    assert _get(port, "/app.js")[0] == 200
    assert _get(port, "/api/nope", token=httpd.token)[0] == 404


def test_status_endpoint_returns_json(live):
    httpd, port = live
    status, body = _get(port, "/api/status", token=httpd.token)
    assert status == 200
    import json
    assert "data_dir" in json.loads(body)


def test_head_on_api_is_not_allowed(live):
    httpd, port = live
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request("HEAD", "/api/status", headers={"X-Markwell-Token": httpd.token})
    assert conn.getresponse().status == 405  # HEAD must never run a device probe
    conn.close()


def test_snapshot_date_is_portable(service, kobo_db):
    # guards against glibc/BSD-only strftime codes (%-d/%-I) crashing on Windows
    _place_snapshot(service, kobo_db, "20260601-101010")
    date = service.snapshot_list()[0]["date"]
    assert re.match(r"^[A-Z][a-z]{2} 1, 2026 · 10:10 [AP]M$", date), date


def _empty_sqlite(path):
    import sqlite3 as _s
    _s.connect(str(path)).close()
    return path


def test_api_books_corrupt_snapshot_returns_friendly_json(live, service):
    # a readable file with none of Kobo's tables -> UnsupportedSchemaError;
    # the server must answer with friendly JSON, not drop the connection.
    service.backup_dir.mkdir(parents=True, exist_ok=True)
    _empty_sqlite(service.backup_dir / "KoboReader-20260601-101010.sqlite")
    httpd, port = live
    status, body = _get(port, "/api/books?source=latest", token=httpd.token)
    assert status == 422
    import json
    assert "error" in json.loads(body)
