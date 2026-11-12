"""Headless lifecycle smoke tests for the desktop launcher service controller."""
import http.client
from unittest import mock
import sys
import unittest
from pathlib import Path

TOOLS = str(Path(__file__).resolve().parents[2] / "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from skellworld_desktop import LocalWorld, run_window


class DesktopServiceTests(unittest.TestCase):
    def test_headless_start_and_stop(self):
        world = LocalWorld(port=0, dashboard_port=0)
        try:
            world.start()
            world.start()  # must be idempotent
            port = world.dashboard.server_address[1]
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            try:
                connection.request("GET", "/api/status",
                                   headers={"Host": f"127.0.0.1:{port}"})
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertIn(b'"peer_count": 0', response.read())
            finally:
                connection.close()
        finally:
            world.stop()
        self.assertFalse(world.running)
        self.assertTrue(all(not thread.is_alive() for thread in world.threads))

    def test_gui_exits_via_button_and_window_on_windows(self):
        # The original v0.3 crash was caused by winfo_exists after destroy.
        # Tk tests are Windows-only; the frozen EXE also exercises both paths.
        if sys.platform != "win32":
            self.skipTest("Windows Tk lifecycle regression")
        for path in ("button", "window"):
            with self.subTest(path=path):
                world = LocalWorld(port=0, dashboard_port=0)
                try:
                    world.start()
                    with mock.patch("skellworld_desktop.webbrowser.open") as browser:
                        run_window(world, gui_exit_smoke=path)
                        browser.assert_not_called()
                finally:
                    world.stop()

    def test_two_independent_listeners(self):
        world = LocalWorld(port=0, dashboard_port=0)
        try:
            self.assertNotEqual(world.hub.server_address[1],
                                world.dashboard.server_address[1])
            world.start()
            self.assertEqual(world.hub.snapshot()["peer_count"], 0)
        finally:
            world.stop()


if __name__ == "__main__":
    unittest.main()
