"""Small deterministic SW1 load benchmark regression; CI also runs full 32 peers."""
import sys
import unittest
from pathlib import Path
TOOLS = str(Path(__file__).resolve().parents[2] / "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
from benchmark_skellworld import exercise


class WorldLoadTests(unittest.TestCase):
    def test_eight_instances_multi_event_delivery_and_bounded_status(self):
        result = exercise(8, events=3)
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(result["instances"], 8)
        self.assertEqual(result["published_events"], 3)
        self.assertEqual(result["broadcast_recipients"], 7)
        self.assertGreaterEqual(result["join_latency"]["max_ms"], 0)


    def test_client_nodelay_modes_keep_protocol_and_report_mode(self):
        for enabled in (False, True):
            with self.subTest(client_nodelay=enabled):
                result = exercise(2, events=2, client_nodelay=enabled)
                self.assertEqual(result["result"], "PASS")
                self.assertEqual(result["client_tcp_nodelay"], enabled)
                self.assertEqual(result["client_tcp_nodelay_observed"], enabled)
                self.assertTrue(result["client_tcp_nodelay_sockets_verified"])
                self.assertEqual(result["client_tcp_nodelay_sockets_checked"], 2)
                self.assertEqual(result["broadcast_recipients"], 1)


if __name__ == "__main__":
    unittest.main()
