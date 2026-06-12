"""HTTP transport for the GUI: routing, security, static files, launch.

Thin shell over `service.Service`. It binds to 127.0.0.1 on an ephemeral port,
serves the hand-written frontend and a small JSON API, and opens the browser.

Security (a local server that can touch a device and write files must not be
drivable by other processes or web pages):

  * binds 127.0.0.1 only — never a routable address;
  * a per-launch secret token is embedded in the page and required on every
    /api/* call (blocks CSRF and any caller that didn't load our page);
  * the Host header must be 127.0.0.1/localhost (blocks DNS-rebinding);
  * no CORS headers are sent (browsers block cross-origin reads);
  * a strict Content-Security-Policy backs up the (escaped) rendering of
    untrusted book text;
  * nothing the browser sends is ever used as a filesystem path or shell input
    — with one fenced exception: POST /api/settings/data-dir accepts a path
    for choice=custom only, fully validated by the service layer's data-dir
    fence; every known choice (home, cloud ids) is resolved server-side.
"""
from __future__ import annotations

import argparse
import hmac
import json
import pathlib
import secrets
import sqlite3
import sys
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .. import config
from ..export import parse_formats
from ..reader import UnsupportedSchemaError
from .service import (Service, default_data_dir, detect_cloud_roots,
                      resolve_data_dir)

_ASSETS = pathlib.Path(__file__).parent / "assets"
_TOKEN_PLACEHOLDER = "__MARKWELL_TOKEN__"
_MAX_BODY = 1 << 20  # request bodies are tiny JSON; cap to avoid memory abuse
_CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' "
        "'unsafe-inline'; script-src 'self'; base-uri 'none'; form-action 'none'")
_STATIC = {
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/i18n.js": ("i18n.js", "application/javascript; charset=utf-8"),
    "/cards.js": ("cards.js", "application/javascript; charset=utf-8"),
}


class MarkwellHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address, handler_class, *, service: Service,
                 token: str, desktop: bool = False, idle_timeout: float = 300.0,
                 now=None):
        super().__init__(server_address, handler_class)
        self.service = service
        self.token = token
        self.desktop_mode = desktop
        self.idle_timeout = idle_timeout
        self._now = now or time.monotonic
        self.last_heartbeat = self._now()
        self.shutdown_requested = threading.Event()
        actual_port = self.server_address[1]
        self.allowed_hosts = {f"127.0.0.1:{actual_port}",
                              f"localhost:{actual_port}"}

    def mark_activity(self) -> None:
        self.last_heartbeat = self._now()

    def export_running(self) -> bool:
        return self.service.export_status().get("state") == "running"

    def should_shutdown_for_idle(self) -> bool:
        if not self.desktop_mode:
            return False
        if self.export_running():
            return False
        return (self._now() - self.last_heartbeat) >= self.idle_timeout

    def request_shutdown(self) -> None:
        self.shutdown_requested.set()
        threading.Thread(target=self.shutdown, daemon=True).start()


class _Handler(BaseHTTPRequestHandler):
    server_version = "Markwell"
    protocol_version = "HTTP/1.1"

    # quiet by default; only surface real problems on stderr
    def log_message(self, fmt, *args):  # noqa: A003
        if args and str(args[0]).startswith(("4", "5")):
            sys.stderr.write("  http %s\n" % (fmt % args))

    # -- security --------------------------------------------------------------

    def _host_ok(self) -> bool:
        return self.headers.get("Host") in self.server.allowed_hosts

    def _token_ok(self) -> bool:
        sent = self.headers.get("X-Markwell-Token", "")
        return hmac.compare_digest(sent, self.server.token)

    # -- response helpers ------------------------------------------------------

    def _send(self, status, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", _CSP)
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, obj, status=HTTPStatus.OK) -> None:
        body = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _error(self, status, message) -> None:
        self._json({"error": message}, status=status)

    def _read_body(self) -> bytes | None:
        """Read (and thereby drain) the request body. Returns None on a body we
        won't accept — chunked, malformed length, or over the cap — closing the
        connection so a rejected POST can't desync keep-alive."""
        if self.headers.get("Transfer-Encoding"):  # we don't decode chunked
            self.close_connection = True
            return None
        raw = self.headers.get("Content-Length")
        try:
            length = int(raw) if raw is not None else 0
        except (TypeError, ValueError):
            self.close_connection = True
            return None
        if length < 0 or length > _MAX_BODY:
            self.close_connection = True
            return None
        return self.rfile.read(length) if length > 0 else b""

    def _dispatch(self, fn, *args) -> None:
        """Run an API handler, turning backend errors into friendly JSON the UI
        can display instead of dropping the connection."""
        try:
            fn(*args)
        except UnsupportedSchemaError:
            self._error(HTTPStatus.UNPROCESSABLE_ENTITY,
                        "This saved copy is in a format Markwell doesn't "
                        "recognize yet.")
        except sqlite3.DatabaseError:
            self._error(HTTPStatus.UNPROCESSABLE_ENTITY,
                        "This saved copy could not be read — it may be damaged. "
                        "Try another copy in History.")
        except Exception:  # never let a handler kill the worker thread
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR,
                        "Something unexpected went wrong.")

    # -- routing ---------------------------------------------------------------

    def _serve_public(self, path) -> bool:
        """Serve the cheap, side-effect-free public routes (index, static assets,
        favicon). Returns True if it handled `path`. Shared by GET and HEAD so the
        route table lives in one place and HEAD never runs a device probe or
        snapshot read; `_send` already drops the body for HEAD requests."""
        if path == "/":
            self._send(HTTPStatus.OK, _load_index(self.server.token),
                       "text/html; charset=utf-8")
        elif path in _STATIC:
            self._serve_static(*_STATIC[path])
        elif path == "/favicon.ico":
            self._send(HTTPStatus.NO_CONTENT, b"", "image/x-icon")
        else:
            return False
        return True

    def do_GET(self) -> None:  # noqa: N802
        if not self._host_ok():
            self._error(HTTPStatus.FORBIDDEN, "bad host")
            return
        route = urlparse(self.path)
        path = route.path
        if self._serve_public(path):
            return
        if path.startswith("/api/"):
            if not self._token_ok():
                self._error(HTTPStatus.FORBIDDEN, "bad token")
                return
            self._dispatch(self._api_get, path, parse_qs(route.query))
            return
        self._error(HTTPStatus.NOT_FOUND, "not found")

    def do_HEAD(self) -> None:  # noqa: N802
        if not self._host_ok():
            self._error(HTTPStatus.FORBIDDEN, "bad host")
            return
        if not self._serve_public(urlparse(self.path).path):
            self._error(HTTPStatus.METHOD_NOT_ALLOWED, "use GET")

    def do_POST(self) -> None:  # noqa: N802
        raw = self._read_body()  # always drain first (keep-alive safety)
        if raw is None:
            self._error(HTTPStatus.BAD_REQUEST, "unsupported or malformed request body")
            return
        if not self._host_ok():
            self._error(HTTPStatus.FORBIDDEN, "bad host")
            return
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            self._error(HTTPStatus.NOT_FOUND, "not found")
            return
        if not self._token_ok():
            self._error(HTTPStatus.FORBIDDEN, "bad token")
            return
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError):
            body = {}
        if not isinstance(body, dict):
            body = {}
        self._dispatch(self._api_post, path, body)

    # -- API -------------------------------------------------------------------

    def _api_get(self, path, query) -> None:
        svc = self.server.service
        if path == "/api/status":
            self._json(svc.status())
        elif path == "/api/snapshots":
            self._json({"snapshots": svc.snapshot_list()})
        elif path == "/api/books":
            source = (query.get("source") or [None])[0]
            self._json(svc.library(source))
        elif path == "/api/export/status":
            self._json(svc.export_status())
        elif path == "/api/settings":
            self._json({
                "data_dir": str(svc.data_dir),
                "backup_dir": str(svc.backup_dir),
                "output_dir": str(svc.out_dir),
                "config_path": str(config.config_path()),
                "cloud_roots": detect_cloud_roots(),
                "home": str(default_data_dir()),
            })
        else:
            self._error(HTTPStatus.NOT_FOUND, "not found")

    def _api_post(self, path, body) -> None:
        svc = self.server.service
        if path == "/api/heartbeat":
            self.server.mark_activity()
            self._json({"ok": True})
        elif path == "/api/quit":
            self._json({"quitting": True})
            self.server.request_shutdown()
        elif path == "/api/export":
            use_device = bool(body.get("use_device", True))
            source = body.get("source")
            fmt = body.get("format")
            started = svc.start_export(use_device=use_device, source=source,
                                       fmt=fmt, lang=body.get("lang"))
            if not started:
                self._error(HTTPStatus.CONFLICT, "a backup is already running")
                return
            self._json({"started": True})
        elif path == "/api/open":
            which = body.get("dir", "data")
            if which not in ("data", "backups", "output"):
                self._error(HTTPStatus.BAD_REQUEST, "unknown folder")
                return
            self._json({"ok": svc.open_folder(which)})
        elif path == "/api/settings/data-dir":
            self._command(self._apply_data_dir_choice, body)
        elif path == "/api/archive":
            self._command(svc.make_archive)
        else:
            self._error(HTTPStatus.NOT_FOUND, "not found")

    def _command(self, fn, *args) -> None:
        """Run a settings/archive command under the service layer's
        stable-message error contract: ValueError -> 400 (the short message
        doubles as an error code the UI translates), RuntimeError -> 409 (a
        backup is running); success answers with the command's report dict."""
        try:
            self._json(fn(*args))
        except RuntimeError as exc:
            self._error(HTTPStatus.CONFLICT, str(exc))
        except ValueError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))

    def _apply_data_dir_choice(self, body) -> dict:
        """Resolve the browser's data-dir choice into a target and relocate.

        SECURITY: known choices never trust a browser path — "home" resolves
        to default_data_dir() and a cloud id is looked up in a fresh
        detect_cloud_roots() (target = that root + /Markwell). Only
        choice=custom carries a browser-sent path, and that single fenced
        value is fully validated by Service.change_data_dir.
        """
        choice = body.get("choice")
        if choice == "custom":
            target = body.get("path")  # the one fenced browser-supplied path
            if not isinstance(target, str):
                raise ValueError("path required")
        elif choice == "home":
            target = default_data_dir()
        else:
            matches = [r for r in detect_cloud_roots() if r["id"] == choice]
            if not matches:
                raise ValueError("unknown choice")
            target = pathlib.Path(matches[0]["path"]) / "Markwell"
        return self.server.service.change_data_dir(target)

    # -- static ----------------------------------------------------------------

    def _serve_static(self, filename, ctype) -> None:
        try:
            body = (_ASSETS / filename).read_bytes()
        except OSError:
            self._error(HTTPStatus.NOT_FOUND, "not found")
            return
        self._send(HTTPStatus.OK, body, ctype)


def _load_index(token: str) -> bytes:
    html = (_ASSETS / "index.html").read_text(encoding="utf-8")
    return html.replace(_TOKEN_PLACEHOLDER, token).encode("utf-8")


def build_server(service: Service, *, host="127.0.0.1", port=0,
                 desktop: bool = False, idle_timeout: float = 300.0, now=None):
    """Create a configured ThreadingHTTPServer (not yet serving)."""
    token = secrets.token_urlsafe(32)
    return MarkwellHTTPServer((host, port), _Handler, service=service,
                              token=token, desktop=desktop,
                              idle_timeout=idle_timeout, now=now)


def _start_idle_monitor(httpd: MarkwellHTTPServer, interval: float = 1.0) -> None:
    if not httpd.desktop_mode:
        return

    def monitor() -> None:
        while not httpd.shutdown_requested.wait(interval):
            if httpd.should_shutdown_for_idle():
                httpd.request_shutdown()
                return

    threading.Thread(target=monitor, daemon=True).start()


def _service_from_args(args) -> Service:
    """The Service main() serves. An explicit --data-dir beats the saved
    Settings choice beats ~/Markwell; resolve_data_dir owns that precedence
    (re-validating the saved choice and warning + falling back on stderr
    rather than refusing to start)."""
    return Service(resolve_data_dir(args.data_dir), fmt=args.format)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(
        prog="markwell-gui",
        description="Open the Markwell app in your web browser.")
    ap.add_argument("--data-dir", default=None,
                    help="where backups and exports are kept (default: the "
                         "folder chosen in Settings, else ~/Markwell)")
    ap.add_argument("--format", default="md,json,html", metavar="SPEC",
                    help="what to export: md,json,csv,anki,html — one id, "
                         "a comma list, or all (default: md,json,html)")
    ap.add_argument("--port", type=int, default=0,
                    help="port to listen on (default: an automatic free port)")
    ap.add_argument("--no-browser", action="store_true",
                    help="don't open the browser automatically")
    ap.add_argument("--desktop", action="store_true",
                    help="run with desktop app lifecycle controls")
    args = ap.parse_args(argv)

    try:  # validate up front, or every later export would fail confusingly
        parse_formats(args.format)
    except ValueError as e:
        print(e, file=sys.stderr)
        sys.exit(2)

    service = _service_from_args(args)
    httpd = build_server(service, port=args.port, desktop=args.desktop)
    url = "http://127.0.0.1:%d/" % httpd.server_address[1]

    print("\n  Markwell is running.", file=sys.stderr)
    print("  Open this in your browser if it didn't open automatically:",
          file=sys.stderr)
    print("    %s" % url, file=sys.stderr)
    print("  Your files live in: %s" % service.data_dir, file=sys.stderr)
    if args.desktop:
        print("  Use Quit in the app to stop.\n", file=sys.stderr)
    else:
        print("  Press Ctrl+C here to stop.\n", file=sys.stderr)

    if not args.no_browser:
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()

    _start_idle_monitor(httpd)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n  Markwell stopped. Your files are safe.\n", file=sys.stderr)
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    main()
