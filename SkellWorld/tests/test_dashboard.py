"""Read-only localhost web console and connected activity regression tests."""
import http.client
import importlib.util
import json
from pathlib import Path
import threading
import unittest

ROOT = Path(__file__).resolve().parents[2]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

hub = load("skellworld_hub_console_test", "tools/skellworld_hub.py")
dashboard = load("skellworld_dashboard_test", "tools/skellworld_dashboard.py")

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.world = hub.WorldServer(("127.0.0.1", 0))
        self.console = dashboard.DashboardServer(("127.0.0.1", 0), self.world)
        self.thread = threading.Thread(target=self.console.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.console.server_address[1]

    def tearDown(self):
        self.console.shutdown()
        self.console.server_close()
        self.thread.join(timeout=3)
        self.world.server_close()

    def request(self, method="GET", path="/api/status", headers=None):
        con = http.client.HTTPConnection("127.0.0.1", self.port, timeout=3)
        opts = {"Host": f"127.0.0.1:{self.port}"}
        if headers:
            opts.update(headers)
        con.request(method, path, headers=opts)
        response = con.getresponse()
        data = response.read()
        status = response.status
        result_headers = dict(response.getheaders())
        con.close()
        return status, data, result_headers

    def test_status_and_event_history(self):
        participant = object()
        self.assertEqual([], self.world.register(participant, "test-1", "skell.eq", "Skelly EQ"))
        self.world.record_event(participant, "theme", "neon")
        status, raw, headers = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/json; charset=utf-8")
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        payload = json.loads(raw)
        self.assertEqual(payload["peer_count"], 1)
        self.assertEqual(payload["peers"][0]["display_name"], "Skelly EQ")
        self.assertEqual([e["kind"] for e in payload["events"]], ["join", "event"])
        self.world.unregister(participant)
        self.assertEqual(json.loads(self.request()[1])["events"][-1]["kind"], "leave")

    def test_status_contains_read_only_skell_tuning(self):
        peer = object()
        self.world.register(peer, "key-01", "skell.key", "Skell Key")
        self.world.record_event(peer, "musical.tuning", "7,0,2741,440000")
        status, raw, _ = self.request()
        self.assertEqual(status, 200)
        data = json.loads(raw)
        self.assertEqual(data["tuning"]["root"], 7)
        self.assertEqual(data["tuning"]["a4_hz"], 440.0)
        self.world.unregister(peer)
        self.assertIsNone(json.loads(self.request()[1])["tuning"])

    def test_catalog_and_static_assets(self):
        code, raw, _ = self.request(path="/api/catalog")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(json.loads(raw)["plugins"]), 20)
        for page, marker in [("/", b"catalog-search"), ("/style.css", b".filter-btn"), ("/app.js", b"filterCatalog")]:
            status, body, _ = self.request(path=page)
            self.assertEqual(status, 200)
            self.assertIn(marker, body)

    def test_reject_malicious_host_origin_mutation_and_traversal(self):
        self.assertEqual(self.request(headers={"Host": "example.com"})[0], 403)
        self.assertEqual(self.request(headers={"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.request(method="POST")[0], 405)
        self.assertEqual(self.request(path="/../../README.md")[0], 404)
        self.assertEqual(self.request(path="/api/status?x=1")[0], 404)
        self.assertEqual(self.request(method="HEAD")[0], 200)
        self.assertEqual(self.request(method="HEAD")[1], b"")

    def test_max_80_events_no_audio_or_plugin_controls(self):
        participant = object()
        self.world.register(participant, "test-1", "skell.eq", "Skelly EQ")
        for n in range(250):
            self.world.record_event(participant, "meter.peak", str(n))
        payload = json.loads(self.request()[1])
        self.assertEqual(len(payload["events"]), 80)
        self.assertEqual(payload["events"][-1]["detail"], "meter.peak: 249")
        self.assertEqual(self.request(path="/api/setParameter")[0], 404)

    def test_non_loopback_binding_rejected(self):
        with self.assertRaises(ValueError):
            dashboard.DashboardServer(("0.0.0.0", 0), self.world)

if __name__ == "__main__":
    unittest.main()
