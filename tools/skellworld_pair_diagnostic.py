#!/usr/bin/env python3
"""Developer-only SW1 Key -> Tune protocol diagnostic (simulated clients).

Runs an isolated localhost hub with ephemeral ports. Does NOT load FL Studio,
claim real VST3 host certification, modify installed plugins, or issue commands.
"""
from __future__ import annotations
import json
import socket
import sys
import threading
import urllib.request
from contextlib import ExitStack
from pathlib import Path

TOOLS = str(Path(__file__).resolve().parent)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
from skellworld_dashboard import DashboardServer
from skellworld_hub import WorldServer, decode, encode


def run_pair_diagnostic():
    hub = WorldServer(("127.0.0.1", 0))
    console = None
    threads = []
    try:
        console = DashboardServer(("127.0.0.1", 0), hub)
        for label, server in (("hub", hub), ("dashboard", console)):
            thread = threading.Thread(target=server.serve_forever, daemon=True,
                                      name="SW1 diagnostic " + label)
            thread.start()
            threads.append(thread)

        with ExitStack() as stack:
            def peer(identity, product, name):
                sock = socket.create_connection(hub.server_address, timeout=3)
                sock.settimeout(3)
                stream = sock.makefile("rb")
                stack.callback(sock.close)
                stack.callback(stream.close)
                sock.sendall(encode("HELLO", identity, product, name))
                welcome = decode(stream.readline(256))
                if welcome != ["WELCOME", "hub", "status", "connected"]:
                    raise AssertionError("No valid HELLO/WELCOME for " + identity)
                return sock, stream

            key_sock, key_stream = peer("diagnostic-key", "skell.key", "Skell Key")
            tune_sock, tune_stream = peer("diagnostic-tune", "skell.tune", "SkellyTune")
            if decode(tune_stream.readline(256)) != [
                    "PEER", "diagnostic-key", "skell.key", "online"]:
                raise AssertionError("Receiver did not discover opted-in Skell Key")
            if decode(key_stream.readline(256)) != [
                    "PEER", "diagnostic-tune", "skell.tune", "online"]:
                raise AssertionError("Sender did not discover opted-in SkellyTune")

            # E natural minor, 432.5 Hz A4, 12-note mask validated by SkellCore.
            expected_tune = "4,1,2773,432500"
            key_sock.sendall(encode("EVENT", "diagnostic-key",
                                    "musical.tuning", expected_tune))
            msg = decode(tune_stream.readline(256))
            if msg != ["EVENT", "diagnostic-key", "musical.tuning", expected_tune]:
                raise AssertionError("Receiver did not get complete typed tuning")

            url = "http://127.0.0.1:" + str(console.server_address[1]) + "/api/status"
            with urllib.request.urlopen(url, timeout=3) as response:
                status = json.load(response)
            if (status["peer_count"] != 2 or
                    status["tuning"]["root"] != 4 or
                    status["tuning"]["mode"] != 1 or
                    status["tuning"]["scale_mask"] != 2773 or
                    status["tuning"]["a4_hz"] != 432.5):
                raise AssertionError("Dashboard tuning snapshot did not match SW1")
            # No DAW parameter write or file system command is available.
            key_sock.sendall(encode("BYE", "diagnostic-key", "skell.key", "offline"))
            if decode(tune_stream.readline(256)) != [
                    "PEER", "diagnostic-key", "skell.key", "offline"]:
                raise AssertionError("Receiver did not observe sender disconnection")
            with urllib.request.urlopen(url, timeout=3) as response:
                after = json.load(response)
            if after["tuning"] is not None or after["peer_count"] != 1:
                raise AssertionError("Stale tuning was not removed on disconnect")
            tune_sock.sendall(encode("BYE", "diagnostic-tune", "skell.tune", "offline"))
            return {"key_to_tune": "pass", "tuning": "E minor / A4 432.50 Hz",
                    "disconnect_cleanup": "pass", "actual_vst3_host_test": "NOT RUN"}
    finally:
        for server in (console, hub):
            if server is not None:
                server.shutdown()
                server.server_close()
        for thread in threads:
            thread.join(timeout=3)


if __name__ == "__main__":
    print(json.dumps(run_pair_diagnostic(), indent=2))
