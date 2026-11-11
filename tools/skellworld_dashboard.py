#!/usr/bin/env python3
"""Read-only, loopback-only SkellWorld web console (Python standard library)."""
from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys

# PyInstaller's one-file Windows binary extracts bundled assets under _MEIPASS.
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
WEB = ROOT / "SkellWorld" / "web"
CATALOG = ROOT / "SkellWorld" / "catalog.json"
APPS = ROOT / "SkellWorld" / "apps.json"

class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, world):
        if address[0] != "127.0.0.1":
            raise ValueError("Dashboard must bind IPv4 loopback only")
        self.world = world
        with CATALOG.open("r", encoding="utf-8") as stream:
            raw = json.load(stream)
        self.catalog = {
            "schema": raw["schema"],
            "plugins": [
                {k: item.get(k) for k in ("repository", "display_name", "product_id", "integration")}
                for item in raw["plugins"]
            ],
        }
        with APPS.open("r", encoding="utf-8") as stream:
            self.apps = json.load(stream)
        super().__init__(address, DashboardHandler)

class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "SkellWorldConsole/1"
    sys_version = ""

    def log_message(self, fmt, *args):
        pass

    def _allowed(self):
        port = self.server.server_address[1]
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if self.headers.get("Host", "") not in hosts:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin in {f"http://{h}" for h in hosts}

    def _write(self, status, payload, mime="text/plain; charset=utf-8", head=False):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; script-src 'self'; style-src 'self'; "
                         "connect-src 'self'; img-src 'self'; base-uri 'none'; "
                         "form-action 'none'; frame-ancestors 'none'")
        self.end_headers()
        if not head:
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _get(self, head=False):
        if not self._allowed():
            return self._write(403, b"Forbidden", head=head)
        paths = {
            "/": (WEB / "index.html", "text/html; charset=utf-8"),
            "/app.js": (WEB / "app.js", "application/javascript; charset=utf-8"),
            "/style.css": (WEB / "style.css", "text/css; charset=utf-8"),
        }
        if self.path == "/api/status":
            payload = json.dumps(self.server.world.snapshot(), ensure_ascii=True).encode("utf-8")
            return self._write(200, payload, "application/json; charset=utf-8", head)
        if self.path == "/api/catalog":
            payload = json.dumps(self.server.catalog, ensure_ascii=True).encode("utf-8")
            return self._write(200, payload, "application/json; charset=utf-8", head)
        if self.path == "/api/apps":
            payload = json.dumps(self.server.apps, ensure_ascii=True).encode("utf-8")
            return self._write(200, payload, "application/json; charset=utf-8", head)
        if self.path not in paths:
            return self._write(404, b"Not found", head=head)
        file, mime = paths[self.path]
        try:
            payload = file.read_bytes()
        except OSError:
            return self._write(503, b"Console assets unavailable", head=head)
        return self._write(200, payload, mime, head)

    def do_GET(self):
        self._get()

    def do_HEAD(self):
        self._get(head=True)

    def do_POST(self):
        self._write(405, b"Read-only console")

    do_PUT = do_POST
    do_DELETE = do_POST
    do_PATCH = do_POST
