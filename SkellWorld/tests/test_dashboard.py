"""Read-only localhost web console and connected activity regression tests."""
import http.client
import importlib.util
import json
from pathlib import Path
import threading
import tempfile
import time
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
        self.assertEqual(payload["peers"][0]["events_sent"], 1)
        self.assertGreaterEqual(payload["peers"][0]["connected_seconds"], 0)
        self.assertIsNotNone(payload["peers"][0]["last_event_seconds_ago"])
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

    def test_safe_companion_registry(self):
        code, raw, headers = self.request(path="/api/apps")
        self.assertEqual(code, 200)
        self.assertEqual(headers["Cache-Control"], "no-store")
        data = json.loads(raw)
        self.assertEqual(data["schema"], "skellworld-apps/1")
        project = next(x for x in data["apps"] if x["mode"] == "developer")
        self.assertEqual(project["repository"], "skellyruno/skell-project-hub")
        self.assertEqual(project["integration"], "read-only-console-discovery")
        self.assertEqual(self.request(method="POST", path="/api/apps")[0], 405)
        self.assertEqual(self.request(path="/api/launch")[0], 404)

    def test_read_only_source_integration_evidence(self):
        status, raw, _ = self.request(path="/api/integrations")
        self.assertEqual(status, 200)
        payload = json.loads(raw)
        self.assertEqual(payload["schema"], "skellworld-integrations/1")
        pilots = {p["product_id"]: p for p in payload["pilots"]}
        self.assertEqual(pilots["skell.key"]["source_status"], "implemented")
        self.assertEqual(pilots["skell.tune"]["host_test"], "pending")
        self.assertEqual(self.request(method="POST", path="/api/integrations")[0], 405)

    def test_projecthub_summary_requires_opt_in_and_valid_counts(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "projecthub-summary-v1.json"
            self.console.projecthub_file = file
            status, body, _ = self.request(path="/api/projecthub")
            self.assertEqual(status, 200)
            self.assertFalse(json.loads(body)["shared"])
            payload = {
                "schema": "skellworld-projecthub-summary/1",
                "source": "uno.skellyr.projecthub",
                "generated_at": int(time.time()),
                "counts": {"projects": 3, "ci_passed": 1, "ci_failed": 1,
                           "ci_stale": 0, "ci_unknown": 1, "blocked": 1},
                "secret": "should never be echoed"
            }
            file.write_text(json.dumps(payload), encoding="utf-8")
            code, raw, _ = self.request(path="/api/projecthub")
            self.assertEqual(code, 200)
            data = json.loads(raw)
            self.assertTrue(data["shared"])
            self.assertEqual(data["counts"]["ci_failed"], 1)
            self.assertNotIn("secret", raw.decode("utf-8"))
            self.assertEqual(self.request(method="POST", path="/api/projecthub")[0], 405)
            payload["counts"]["ci_failed"] = 999
            file.write_text(json.dumps(payload), encoding="utf-8")
            self.assertFalse(json.loads(self.request(path="/api/projecthub")[1])["shared"])
            file.unlink()
            self.assertFalse(json.loads(self.request(path="/api/projecthub")[1])["shared"])

    def test_projecthub_windows_launcher_is_only_an_opt_in_uri(self):
        status, page, _ = self.request(path="/")
        self.assertEqual(status, 200)
        self.assertIn(b'href="skellprojecthub://open"', page)
        self.assertIn(b'Requires the Project Hub Windows app', page)
        self.assertEqual(self.request(path="/api/launch")[0], 404)
        self.assertEqual(self.request(method="POST", path="/api/projecthub")[0], 405)

    def test_deesser_remains_pending_until_ci_is_verified(self):
        status, raw, _ = self.request(path="/api/integrations")
        self.assertEqual(status, 200)
        pilots = json.loads(raw)["pilots"]
        deesser = next(p for p in pilots if p["product_id"] == "skell.deesser")
        self.assertEqual(deesser["source_status"], "candidate")
        self.assertEqual(deesser["host_test"], "pending")

    def test_catalog_and_static_assets(self):
        code, raw, _ = self.request(path="/api/catalog")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(json.loads(raw)["plugins"]), 20)
        for page, marker in [("/", b"run-connection-check"), ("/style.css", b".health-grid"), ("/app.js", b"runConnectionCheck")]:
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
