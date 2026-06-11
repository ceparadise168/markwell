"""GUI service use-cases and the HTTP server's security boundary."""
import datetime
import http.client
import shutil
import socket
import threading
import time

import pytest

from conftest import make_kobo_db
from markwell.gui import sample
from markwell.gui.server import build_server
from markwell.gui.service import (Service, _coerce_fmt, _coerce_lang,
                                  _parse_stamp)


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


def test_sample_library_ja_ko_books_and_chapter_order():
    books = sample.library()
    assert len(books) == 6  # en ×3 + zh + ja + ko — every target script
    by_author = {b.author: b for b in books}

    kusamakura = by_author["夏目漱石"]
    assert kusamakura.title == "草枕"
    texts = [h.text for h in kusamakura.highlights]
    assert "山路を登りながら、こう考えた。" in texts
    assert ("智に働けば角が立つ。情に棹させば流される。"
            "意地を通せば窮屈だ。") in texts
    assert "とかくに人の世は住みにくい。" in texts
    assert all(h.chapter_index == 1 for h in kusamakura.highlights)
    assert any(h.note for h in kusamakura.highlights)

    azaleas = by_author["김소월"]
    assert azaleas.title == "진달래꽃"
    assert len(azaleas.highlights) == 3
    assert all(h.chapter_index == 1 for h in azaleas.highlights)
    assert any(h.note for h in azaleas.highlights)

    chapters = [h.chapter_index for h in by_author["老子"].highlights]
    assert chapters == sorted(chapters)  # reading order, not shuffled


def test_snapshot_list_newest_first(service, kobo_db):
    _place_snapshot(service, kobo_db, "20260101-090000")
    _place_snapshot(service, kobo_db, "20260601-120000")
    rows = service.snapshot_list()
    assert len(rows) == 2
    assert rows[0]["name"].endswith("20260601-120000.sqlite")
    assert rows[0]["is_latest"] is True
    assert rows[1]["is_latest"] is False
    assert rows[0]["size_bytes"] > 0


def test_snapshot_list_emits_data_not_prose(service, kobo_db):
    # the backend ships a machine timestamp; the browser owns date formatting
    _place_snapshot(service, kobo_db, "20260601-101010")
    row = service.snapshot_list()[0]
    assert set(row) == {"name", "stamp", "size_bytes", "is_latest"}
    when = datetime.datetime.fromisoformat(row["stamp"])
    assert when == datetime.datetime(2026, 6, 1, 10, 10, 10)


def test_snapshot_without_stamp_has_none_stamp(service, kobo_db):
    # a hand-renamed copy still lists, with stamp=None for the browser to handle
    _place_snapshot(service, kobo_db, "handmade-copy")
    row = service.snapshot_list()[0]
    assert row["name"] == "KoboReader-handmade-copy.sqlite"
    assert row["stamp"] is None


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


def test_export_lang_localizes_output_files(service, kobo_db):
    # the exported FILES follow the reader's language even though the backend
    # leaves History presentation (dates, ages, sizes) to the browser — job
    # message prose still lives backend-side until Task 5
    name = _place_snapshot(service, kobo_db, "20260601-120000").name
    assert service.start_export(use_device=False, source=name,
                                lang="zh-TW") is True
    job = _wait_export(service)
    assert job["state"] == "done", job
    index = (service.out_dir / "index.md").read_text(encoding="utf-8")
    assert "# Kobo 書摘" in index
    book = (service.out_dir / "Book_One.md").read_text(encoding="utf-8")
    assert "**筆記：** My own note" in book


def test_export_unknown_lang_coerces_to_english(service, kobo_db):
    # browser input is untrusted: an unknown code silently means English
    name = _place_snapshot(service, kobo_db, "20260601-120000").name
    assert service.start_export(use_device=False, source=name,
                                lang="xx") is True
    job = _wait_export(service)
    assert job["state"] == "done", job
    index = (service.out_dir / "index.md").read_text(encoding="utf-8")
    assert "# Kobo Highlights" in index


def test_export_unknown_fmt_coerces_to_default(service, kobo_db):
    # fmt is untrusted browser input with teeth: unclamped, an unknown value
    # would render zero files and write_outputs would then prune every
    # previously exported file as stale — silent data deletion reported as
    # success. Junk of any shape must mean the configured default instead.
    name = _place_snapshot(service, kobo_db, "20260601-120000").name
    assert service.start_export(use_device=False, source=name) is True
    assert _wait_export(service)["state"] == "done"
    prior = [service.out_dir / "index.md", service.out_dir / "highlights.json"]
    assert all(p.is_file() for p in prior)

    for junk in ("evil", ["md"]):  # unknown string, non-string
        assert service.start_export(use_device=False, source=name,
                                    fmt=junk) is True
        job = _wait_export(service)
        assert job["state"] == "done", job
        assert job["result"]["files"] >= 2  # default "all": md + json rendered
        assert all(p.is_file() for p in prior)  # prior outputs not pruned


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
    assert _coerce_lang("zh-TW") == "zh-TW"
    assert _coerce_lang(None) == "en"
    assert _coerce_lang(["zh-TW"]) == "en"  # unhashable junk coerces, never errors
    assert _coerce_fmt("md", "all") == "md"
    assert _coerce_fmt(None, "all") == "all"
    assert _coerce_fmt(["md"], "json") == "json"  # junk type coerces, never errors


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


def _post(port, path, token=None, body=None, host=None):
    import json
    payload = json.dumps(body or {}).encode("utf-8")
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.putrequest("POST", path, skip_host=True, skip_accept_encoding=True)
    conn.putheader("Host", host or f"127.0.0.1:{port}")
    conn.putheader("Content-Type", "application/json")
    conn.putheader("Content-Length", str(len(payload)))
    if token is not None:
        conn.putheader("X-Markwell-Token", token)
    conn.endheaders(payload)
    resp = conn.getresponse()
    text = resp.read().decode("utf-8")
    conn.close()
    return resp.status, text


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


def test_desktop_lifecycle_post_endpoints_require_token(live):
    httpd, port = live
    assert _post(port, "/api/quit")[0] == 403
    assert _post(port, "/api/heartbeat")[0] == 403
    assert _post(port, "/api/heartbeat", token="wrong")[0] == 403
    assert _post(port, "/api/heartbeat", token=httpd.token)[0] == 200


def test_heartbeat_updates_activity_timestamp(service):
    ticks = iter([100.0, 125.0])
    httpd = build_server(service, port=0, now=lambda: next(ticks))
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        assert httpd.last_heartbeat == 100.0
        status, _ = _post(port, "/api/heartbeat", token=httpd.token)
        assert status == 200
        assert httpd.last_heartbeat == 125.0
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_desktop_idle_shutdown_waits_for_running_export(service):
    httpd = build_server(service, port=0, desktop=True, idle_timeout=300,
                         now=lambda: 1000.0)
    try:
        httpd.last_heartbeat = 0.0
        service._set(state="running")
        assert httpd.should_shutdown_for_idle() is False
        service._set(state="idle")
        assert httpd.should_shutdown_for_idle() is True
    finally:
        httpd.server_close()


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


def _empty_sqlite(path):
    import sqlite3 as _s
    _s.connect(str(path)).close()
    return path


def _raw_post(port, extra_header):
    """Send a hand-rolled POST so we can supply bad framing; return the response."""
    s = socket.create_connection(("127.0.0.1", port), timeout=3)
    req = (f"POST /api/open HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n"
           f"{extra_header}\r\nConnection: close\r\n\r\n")
    s.sendall(req.encode("latin1"))
    data = s.recv(4096).decode("latin1")
    s.close()
    return data


def test_malformed_content_length_is_handled(live):
    httpd, port = live
    resp = _raw_post(port, "Content-Length: not-a-number")
    assert resp.startswith("HTTP/1.1 400")  # clean error, not a crash/hang


def test_chunked_body_is_rejected(live):
    httpd, port = live
    resp = _raw_post(port, "Transfer-Encoding: chunked")
    assert resp.startswith("HTTP/1.1 400")


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


def _post_export_and_wait(live, service, kobo_db, lang):
    """Start a snapshot export over HTTP with `lang`; return (status, index.md)."""
    name = _place_snapshot(service, kobo_db, "20260601-120000").name
    httpd, port = live
    status, _ = _post(port, "/api/export", token=httpd.token,
                      body={"use_device": False, "source": name, "lang": lang})
    if status != 200:
        return status, ""
    job = _wait_export(service)
    assert job["state"] == "done", job
    return status, (service.out_dir / "index.md").read_text(encoding="utf-8")


def test_api_export_lang_localizes_output(live, service, kobo_db):
    status, index = _post_export_and_wait(live, service, kobo_db, "zh-TW")
    assert status == 200
    assert "# Kobo 書摘" in index


def test_api_export_unknown_lang_behaves_as_english(live, service, kobo_db):
    # silent coercion at the boundary: never a 4xx for a lang we don't ship
    status, index = _post_export_and_wait(live, service, kobo_db, "xx")
    assert status == 200
    assert "# Kobo Highlights" in index
