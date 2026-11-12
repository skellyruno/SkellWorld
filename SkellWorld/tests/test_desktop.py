"""Headless lifecycle smoke tests for the desktop launcher service controller."""
import http.client
import subprocess
import socket
import sys
import unittest
from pathlib import Path

TOOLS = str(Path(__file__).resolve().parents[2] / "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

from skellworld_desktop import LocalWorld


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
        # A Tk root must be created and destroyed in one process on the
        # creating main thread. Keeping GUI Tcl state in the shared unittest
        # interpreter can later crash under C++/socket test cleanup with
        # Tcl_AsyncDelete, even if the UI test itself reports 'ok'.
        script = str(Path(TOOLS) / "skellworld_desktop.py")
        def free_port():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", 0))
                return sock.getsockname()[1]
        for path in ("button", "window"):
            with self.subTest(path=path):
                first, second = free_port(), free_port()
                while first == second:
                    second = free_port()
                result = subprocess.run(
                    [sys.executable, script, "--gui-exit-smoke", path,
                     "--port", str(first), "--dashboard-port", str(second)],
                    capture_output=True, text=True, timeout=25,
                    check=False)
                self.assertEqual(result.returncode, 0,
                    f"Tk {path} close failed: {result.stderr}")

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
