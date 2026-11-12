#!/usr/bin/env python3
"""Integration smoke test for the actual frozen SkellWorld Windows EXE."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import closing
from pathlib import Path


def available_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def status(port):
    url = f"http://127.0.0.1:{port}/api/status"
    with urllib.request.urlopen(url, timeout=2) as response:
        if response.status != 200:
            raise RuntimeError("status route returned non-200")
        return json.load(response)


def wait_until(predicate, timeout=40):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            result = predicate()
            if result:
                return result
        except (OSError, TimeoutError, urllib.error.URLError, ValueError) as error:
            last_error = error
        time.sleep(0.25)
    raise RuntimeError(f"Frozen app timed out (last error: {last_error})")


def smoke(executable):
    exe = Path(executable).resolve()
    if not exe.is_file():
        raise FileNotFoundError(exe)
    hub_port, dash_port = available_port(), available_port()
    while hub_port == dash_port:
        dash_port = available_port()
    cmd = [str(exe), "--smoke-test", "--port", str(hub_port),
           "--dashboard-port", str(dash_port)]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    app = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           creationflags=flags)
    try:
        def ready():
            if app.poll() is not None:
                raise RuntimeError("EXE exited before listeners became available")
            return status(dash_port)
        initial = wait_until(ready, timeout=60)
        if initial["schema"] != "skellworld-status/1" or initial["peer_count"] != 0:
            raise AssertionError("invalid initial state")
        with urllib.request.urlopen(
                f"http://127.0.0.1:{dash_port}/api/catalog", timeout=3) as response:
            catalog = json.load(response)
        if len(catalog["plugins"]) < 20:
            raise AssertionError("missing packaged catalog")
        with urllib.request.urlopen(
                f"http://127.0.0.1:{dash_port}/api/apps", timeout=3) as response:
            apps = json.load(response)
        if (apps.get("schema") != "skellworld-apps/1" or
                not any(a.get("id") == "uno.skellyr.projecthub" for a in apps["apps"])):
            raise AssertionError("missing packaged Project Hub companion registry")
        with urllib.request.urlopen(
                f"http://127.0.0.1:{dash_port}/", timeout=3) as response:
            if b"tuning-panel" not in response.read():
                raise AssertionError("missing packaged web assets")

        with closing(socket.create_connection(("127.0.0.1", hub_port), timeout=3)) as peer:
            peer.settimeout(3)
            with peer.makefile("rb") as stream:
                peer.sendall(b"SW1|HELLO|frozen-key|skell.key|Skell Key\n")
                if not stream.readline(256).startswith(b"SW1|WELCOME|"):
                    raise AssertionError("missing hub welcome")
                peer.sendall(b"SW1|EVENT|frozen-key|musical.tuning|4,1,2773,432500\n")
                snapshot = wait_until(
                    lambda: (lambda s: s if s["tuning"] and
                            s["tuning"]["root"] == 4 else None)(status(dash_port)))
                if snapshot["tuning"]["a4_hz"] != 432.5:
                    raise AssertionError("wrong A4 value in frozen dashboard")
                peer.sendall(b"SW1|BYE|frozen-key|skell.key|offline\n")
        wait_until(lambda: status(dash_port)["tuning"] is None)
        print("PASS: packaged EXE starts, serves assets, relays Skell Key and clears status")
    finally:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(app.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=15, check=False)
        elif app.poll() is None:
            app.terminate()
        try:
            app.wait(timeout=10)
        except subprocess.TimeoutExpired:
            app.kill()
            app.wait(timeout=5)

    # Regression for user-reported TclError: "can't invoke winfo command:
    # application has been destroyed". Test the actual frozen GUI process
    # through both exit actions, not only its headless TCP service mode.
    for action in ("button", "window"):
        ui_port, ui_dash_port = available_port(), available_port()
        while ui_port == ui_dash_port:
            ui_dash_port = available_port()
        result = subprocess.run(
            [str(exe), "--gui-exit-smoke", action,
             "--port", str(ui_port),
             "--dashboard-port", str(ui_dash_port)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, creationflags=flags,
            timeout=35, check=False)
        if result.returncode != 0:
            raise AssertionError(
                f"Packaged Tk launcher exit failed via {action}: return code {result.returncode}")
        print(f"PASS: packaged Windows GUI closed cleanly via {action}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: smoke_frozen_world.py /path/to/SkellWorld.exe")
    smoke(sys.argv[1])
