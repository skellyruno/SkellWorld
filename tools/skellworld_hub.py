#!/usr/bin/env python3
"""SkellWorld v1: local, opt-in SKELL plugin presence/event broker.
NO remote binding, NO audio processing, NO parameter control, NO credentials.
Start manually: python tools/skellworld_hub.py
"""
from __future__ import annotations
import argparse
import re
import socketserver
import threading
import time

PORT = 48673
MAX_CLIENTS = 32
MAX_WIRE = 256
TOPICS = {"theme", "preset.name", "transport.bpm", "transport.playing", "meter.peak"}
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
        super().__init__(address, WorldHandler)
        self.guard = threading.Lock()
        self.peers = {}

    def register(self, peer, ident, product):
        with self.guard:
            if (len(self.peers) >= MAX_CLIENTS or
                any(i == ident for i, _ in self.peers.values())):
                return None
            existing = list(self.peers.items())
            self.peers[peer] = (ident, product)
            return existing

    def unregister(self, peer):
        with self.guard:
            was = self.peers.pop(peer, None)
            others = list(self.peers)
        if was:
            self.send_many(others, encode("PEER", was[0], was[1], "offline"))

    def send_many(self, peers, frame):
        # Never hold the peer map lock during blocking socket writes.
        for peer in peers:
            try:
                peer.request.sendall(frame)
            except (OSError, TimeoutError):
                pass

    def broadcast(self, origin, frame):
        with self.guard:
            receivers = [p for p in self.peers if p is not origin]
        self.send_many(receivers, frame)

class WorldHandler(socketserver.BaseRequestHandler):
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
                        existing = self.server.register(self, who, topic)
                        if existing is None:
                            self.request.sendall(encode("ERROR", "hub", "status", "capacity_or_duplicate"))
                            break
                        ident, product = who, topic
                        self.request.settimeout(None)  # idle links stay connected
                        self.request.sendall(encode("WELCOME", "hub", "status", "connected"))
                        for peer, (pident, pproduct) in existing:
                            self.request.sendall(encode("PEER", pident, pproduct, "online"))
                        self.server.broadcast(self, encode("PEER", ident, product, "online"))
                        continue
                    if who != ident:  # no spoofing another live socket identity
                        break
                    if kind == "EVENT" and topic in TOPICS:
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
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("port must be between 1024 and 65535")
    with WorldServer(("127.0.0.1", args.port)) as server:
        print(f"SkellWorld listening ONLY on 127.0.0.1:{args.port}", flush=True)
        print("Opt-in presence and informational events only. Ctrl+C to exit.", flush=True)
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
        server.shutdown()

if __name__ == "__main__":
    main()
