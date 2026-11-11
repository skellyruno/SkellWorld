#!/usr/bin/env python3
"""SkellWorld v1: local, opt-in SKELL plugin presence/event broker.
NO remote binding, NO audio processing, NO parameter control, NO credentials.
Start manually: python tools/skellworld_hub.py
"""
from __future__ import annotations
import argparse
import re
import select
import socket
from collections import deque
import socketserver
import threading
import time

PORT = 48673
MAX_CLIENTS = 32
MAX_WIRE = 256
TOPICS = {"theme", "preset.name", "transport.bpm", "transport.playing",
          "meter.peak", "musical.key", "musical.tuning"}
IDENT = re.compile(r"^[A-Za-z0-9_.-]{1,47}$")
VALUE = re.compile(r"^[\x20-\x7e]{1,95}$")
KINDS = {"HELLO", "WELCOME", "PEER", "EVENT", "BYE", "ERROR"}

def decode(raw: bytes):
    if len(raw) >= MAX_WIRE or not raw.endswith(b"\n"):
        return None
    try:
        line = raw[:-1].decode("ascii")
    except UnicodeDecodeError:
        return None
    fields = line.split("|")
    if len(fields) != 5 or fields[0] != "SW1" or fields[1] not in KINDS:
        return None
    if not IDENT.fullmatch(fields[2]) or not IDENT.fullmatch(fields[3]):
        return None
    if not VALUE.fullmatch(fields[4]) or "|" in fields[4] or "\\" in fields[4]:
        return None
    return fields[1:]

def encode(kind, instance, topic, value):
    frame = f"SW1|{kind}|{instance}|{topic}|{value}\n".encode("ascii")
    if len(frame) >= MAX_WIRE:
        raise ValueError("oversized wire frame")
    return frame

class WorldServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True
    block_on_close = False

    def __init__(self, address=("127.0.0.1", PORT)):
        if address[0] != "127.0.0.1":
            raise ValueError("SW1 hub must bind IPv4 loopback only")
        super().__init__(address, WorldHandler)
        self.guard = threading.Lock()
        self.peers = {}
        self.booted = time.monotonic()
        self.events = deque(maxlen=80)
        self.sequence = 0

    def _record_locked(self, kind, ident, product, detail):
        self.sequence += 1
        self.events.append({
            "seq": self.sequence, "at": round(time.time(), 3),
            "kind": kind, "instance_id": ident,
            "product_id": product, "detail": detail,
        })

    def snapshot(self):
        """Return a bounded, JSON-compatible, read-only state snapshot."""
        with self.guard:
            peers = sorted((
                {"instance_id": ident, "product_id": product, "display_name": name}
                for ident, product, name in self.peers.values()
            ), key=lambda p: (p["product_id"], p["instance_id"]))
            return {
                "schema": "skellworld-status/1",
                "peer_count": len(peers),
                "uptime_seconds": max(0, int(time.monotonic() - self.booted)),
                "peers": peers, "events": list(self.events),
                "sequence": self.sequence,
            }

    def record_event(self, peer, topic, value):
        with self.guard:
            info = self.peers.get(peer)
            if info is not None:
                self._record_locked("event", info[0], info[1], topic + ": " + value)

    def register(self, peer, ident, product, display):
        with self.guard:
            if (len(self.peers) >= MAX_CLIENTS or
                any(info[0] == ident for info in self.peers.values())):
                return None
            existing = list(self.peers.items())
            self.peers[peer] = (ident, product, display)
            self._record_locked("join", ident, product, display)
            return existing

    def unregister(self, peer):
        with self.guard:
            was = self.peers.pop(peer, None)
            others = list(self.peers)
            if was:
                self._record_locked("leave", was[0], was[1], "offline")
        if was:
            self.send_many(others, encode("PEER", was[0], was[1], "offline"))

    def send_many(self, peers, frame):
        # A peer serializes complete frames. A stalled reader must not freeze
        # other local plugin instances or hold the shared registry lock.
        for peer in peers:
            if not peer.send_frame(frame):
                try:
                    peer.request.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

    def broadcast(self, origin, frame):
        with self.guard:
            receivers = [p for p in self.peers if p is not origin]
        self.send_many(receivers, frame)

class WorldHandler(socketserver.BaseRequestHandler):
    # Each incoming socket has one shared write lock, including welcome,
    # snapshots, broadcast messages, and disconnect notifications.
    # Never take the server registry guard while holding a network write.
    def setup(self):
        super().setup()
        self._write_guard = threading.Lock()

    def _write_locked(self, frame):
        deadline = time.monotonic() + 0.25
        remaining = memoryview(frame)
        try:
            while remaining:
                timeout = deadline - time.monotonic()
                if timeout <= 0:
                    return False
                _, writable, _ = select.select([], [self.request], [], timeout)
                if not writable:
                    return False
                sent = self.request.send(remaining)
                if sent <= 0:
                    return False
                remaining = remaining[sent:]
            return True
        except (OSError, ValueError):
            return False

    def send_frame(self, frame):
        with self._write_guard:
            return self._write_locked(frame)

    def handle(self):
        # Require HELLO promptly; an established local plugin may idle for hours.
        self.request.settimeout(3.0)
        ident = None
        product = None
        count, window = 0, time.monotonic()
        with self.request.makefile("rb") as stream:
            try:
                while True:
                    try:
                        raw = stream.readline(MAX_WIRE + 1)
                    except (OSError, TimeoutError):
                        break
                    if not raw:
                        break
                    now = time.monotonic()
                    if now - window >= 1:
                        count, window = 0, now
                    count += 1
                    if count > 30:  # bounded messages/second/connection
                        break
                    frame = decode(raw)
                    if frame is None:
                        break
                    kind, who, topic, value = frame
                    if ident is None:
                        if kind != "HELLO":
                            break
                        # Serialize the handshake with any concurrent join.
                        # Only preexisting peers get the new online announcement,
                        # eliminating duplicate peer counts during simultaneous joins.
                        with self._write_guard:
                            existing = self.server.register(self, who, topic, value)
                            if existing is None:
                                self._write_locked(encode("ERROR", "hub", "status", "capacity_or_duplicate"))
                                break
                            ident, product = who, topic
                            self.request.settimeout(None)  # established idle clients stay connected
                            ready = self._write_locked(encode("WELCOME", "hub", "status", "connected"))
                            for _peer, (pident, pproduct, _display) in existing:
                                if not ready:
                                    break
                                ready = self._write_locked(encode("PEER", pident, pproduct, "online"))
                        if not ready:
                            break
                        self.server.send_many([peer for peer, _info in existing],
                                              encode("PEER", ident, product, "online"))
                        continue
                    if who != ident:  # no spoofing another live socket identity
                        break
                    if kind == "EVENT" and topic in TOPICS:
                        if topic in {"musical.key", "musical.tuning"}:
                            # No commands or untrusted key updates. Only a
                            # registered skell.key peer may publish tuning.
                            with self.server.guard:
                                registered = self.server.peers.get(self)
                            if registered is None or registered[1] != "skell.key":
                                break
                            if topic == "musical.key":
                                if re.fullmatch(r"(?:[0-9]|1[01])\.[01]", value) is None:
                                    break
                            else:
                                # SkellCore/WorldTuning.h wire format:
                                # root,mode,absolute-pitch-mask,A4-in-millihertz.
                                fields = value.split(",")
                                if len(fields) != 4 or any(
                                        not field.isascii() or not field.isdecimal()
                                        or (len(field) > 1 and field[0] == "0")
                                        for field in fields):
                                    break
                                root, mode, mask, a4 = map(int, fields)
                                if not (0 <= root <= 11 and 0 <= mode <= 1
                                        and 1 <= mask <= 4095 and (mask & (1 << root))
                                        and 400000 <= a4 <= 480000):
                                    break
                        self.server.record_event(self, topic, value)
                        self.server.broadcast(self, encode("EVENT", ident, topic, value))
                    elif kind == "BYE":
                        break
                    else:
                        # No commands, automation, file paths, presets, audio, remote control.
                        break
            except (OSError, TimeoutError):
                pass
            finally:
                self.server.unregister(self)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--dashboard-port", type=int, default=48674)
    parser.add_argument("--no-dashboard", action="store_true", help="disable read-only local web console")
    parser.add_argument("--open-browser", action="store_true", help="open the local console in your default browser")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    if not 1024 <= args.dashboard_port <= 65535:
        parser.error("dashboard port must be between 1024 and 65535")
    if not args.no_dashboard and args.port == args.dashboard_port:
        parser.error("hub and dashboard ports must differ")
    with WorldServer(("127.0.0.1", args.port)) as server:
        console, console_thread = None, None
        try:
            if not args.no_dashboard:
                from skellworld_dashboard import DashboardServer
                console = DashboardServer(("127.0.0.1", args.dashboard_port), server)
                console_thread = threading.Thread(
                    target=console.serve_forever, kwargs={"poll_interval": 0.2},
                    name="SkellWorld read-only console", daemon=True)
                console_thread.start()
            print(f"SkellWorld local hub: 127.0.0.1:{args.port}", flush=True)
            if console is not None:
                print(f"SkellWorld dashboard: http://127.0.0.1:{args.dashboard_port}", flush=True)
            print("Opt-in informational events only. Ctrl+C to exit.", flush=True)
            if console is not None and args.open_browser:
                import webbrowser
                webbrowser.open(f"http://127.0.0.1:{args.dashboard_port}", new=1)
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
        finally:
            if console is not None:
                console.shutdown()
                console.server_close()
                console_thread.join(timeout=3)

if __name__ == "__main__":
    main()
