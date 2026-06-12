"""i18n contract: the I18N table in i18n.js is strict JSON in locale parity,
every key the front-end uses exists, and the asset is served like app.js."""
import http.client
import json
import pathlib
import re
import threading

import pytest

import markwell.gui
from markwell.gui.server import build_server
from markwell.gui.service import Service
from markwell.render import labels

# Resolve assets from the installed package, not the process cwd, so the suite
# passes no matter where pytest is invoked from.
ASSETS = pathlib.Path(markwell.gui.__file__).parent / "assets"


def _dicts():
    src = (ASSETS / "i18n.js").read_text(encoding="utf-8")
    start = src.index("const I18N =") + len("const I18N =")
    # newline-anchored terminator: a future translation containing "};" can't
    # truncate the slice; +2 keeps the closing brace inside it
    end = src.index("\n};", start) + 2
    return json.loads(src[start:end])


# ---- dictionary shape --------------------------------------------------------

def test_locales_present_and_keys_in_parity():
    d = _dicts()
    assert set(d) == {"en", "zh-TW", "ja", "ko"}
    # cross-layer parity: the GUI speaks exactly the languages exports do
    assert set(d) == set(labels.LABELS)
    base = set(d["en"])
    assert base, "en dictionary must not be empty"
    for loc, table in d.items():
        assert set(table) == base, f"{loc} drift: {set(table) ^ base}"
        assert all(isinstance(v, str) and v.strip() for v in table.values())


def test_every_t_key_used_in_js_exists_in_en():
    d = _dicts()
    used = set()
    for name in ("app.js", "i18n.js"):
        src = (ASSETS / name).read_text(encoding="utf-8")
        used |= set(re.findall(r"""(?<![\w.])t\(\s*["']([\w.-]+)["']""", src))
        # nphrase("x_one", "x_many", n) picks its key at runtime — harvest both
        for one, many in re.findall(
                r"""nphrase\(\s*["']([\w.-]+)["'],\s*["']([\w.-]+)["']""", src):
            used |= {one, many}
    missing = used - set(d["en"])
    assert not missing, f"t() keys missing from en dict: {missing}"


# ---- the full-app sweep (Task 5) ----------------------------------------------

def test_app_js_localizes_at_volume():
    """Floor on t() call sites: app.js renders through the dictionary, not
    hardcoded English. A big drop means someone re-inlined strings."""
    src = (ASSETS / "app.js").read_text(encoding="utf-8")
    calls = re.findall(r"(?<![\w.])t\(", src)
    assert len(calls) >= 60, f"only {len(calls)} t() call sites in app.js"


# Exact English literals the Task-5 sweep removed from app.js (one per major
# surface: library, progress phases, device banner, search, CTA, book detail,
# history, copy toast). Any reappearance = a hardcoded string snuck back in.
# These mirror specific en values in i18n.js — if you rename one of those
# strings there, update it here too, or this guard quietly stops covering
# that surface.
_ENGLISH_SENTINELS = [
    "Your library",
    "Finding your Kobo",
    "No Kobo detected",
    "Search your highlights",
    "Back up my Kobo",
    "All books",
    "Saved copies",
    "Highlight copied.",
    "Re-create files",
]


def test_no_hardcoded_english_sentinels_in_app_js():
    src = (ASSETS / "app.js").read_text(encoding="utf-8")
    leaked = [s for s in _ENGLISH_SENTINELS if s in src]
    assert not leaked, f"hardcoded English back in app.js: {leaked}"


def test_every_data_i18n_key_in_index_html_exists_in_en():
    d = _dicts()
    html = (ASSETS / "index.html").read_text(encoding="utf-8")
    used = set(re.findall(r'data-i18n(?:-aria|-title)?="([\w.-]+)"', html))
    assert used, "index.html must mark its chrome with data-i18n attributes"
    missing = used - set(d["en"])
    assert not missing, f"data-i18n keys missing from en dict: {missing}"


def test_index_html_wires_switcher_and_loads_i18n_before_app_js():
    html = (ASSETS / "index.html").read_text(encoding="utf-8")
    # the applier + switcher wiring live in i18n.js; app.js assumes its globals
    assert html.index('src="i18n.js"') < html.index('src="app.js"')
    assert 'id="locale-select"' in html


# ---- served asset (mirrors the /app.js static route) --------------------------

@pytest.fixture
def live(tmp_path):
    httpd = build_server(Service(tmp_path / "data"), port=0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd, httpd.server_address[1]
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_i18n_js_served_without_token(live):
    _httpd, port = live
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    conn.request("GET", "/i18n.js")  # public static route: no token header
    resp = conn.getresponse()
    body = resp.read().decode("utf-8")
    ctype = resp.getheader("Content-Type")
    conn.close()
    assert resp.status == 200
    assert ctype == "application/javascript; charset=utf-8"
    assert "const I18N =" in body
