#!/usr/bin/env python3
"""Reproducible local SW1 hub scalability benchmark (synthetic peers only).

No VST3s, DAW audio, user files, network discovery, or remote commands.
A scenario checks actual frames, dashboard responses and 32-peer limits,
then records wall-clock timings and Python allocation peaks. CI timing is
observational: it is NOT evidence of FL Studio real-time audio performance.
"""
from __future__ import annotations
import argparse
import json
import math
import socket
import statistics
import sys
import threading
import time
import tracemalloc
import urllib.request
from pathlib import Path

TOOLS = str(Path(__file__).resolve().parent)
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
from skellworld_hub import WorldServer, MAX_CLIENTS, encode, decode
from skellworld_dashboard import DashboardServer


def _percentiles(values):
    values = sorted(values)
    if not values:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0}
    return {
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": round(values[max(0, math.ceil(len(values) * .95) - 1)], 3),
        "max_ms": round(values[-1], 3),
    }


def _receive(stream):
    data = decode(stream.readline(256))
    if data is None:
        raise AssertionError("Invalid or missing SW1 frame during load test")
    return data


def exercise(peers: int, events: int = 8):
    if not (1 <= peers <= MAX_CLIENTS):
        raise ValueError("Peer count must be 1..32")
    if not (1 <= events <= 20):
        raise ValueError("Per-sender events must be 1..20 to respect rate limits")
    world = WorldServer(("127.0.0.1", 0))
    console = None
    threads = []
    sockets = []
    streams = []
    join_times, event_times, status_times = [], [], []
    begin = time.perf_counter()
    cpu_start = time.process_time()
    tracemalloc.start()
    try:
        console = DashboardServer(("127.0.0.1", 0), world)
        for server, name in ((world, "hub"), (console, "dashboard")):
            thread = threading.Thread(target=server.serve_forever,
                                      kwargs={"poll_interval": 0.05},
                                      name="SkellWorld benchmark " + name, daemon=True)
            thread.start()
            threads.append(thread)

        for i in range(peers):
            started = time.perf_counter()
            sock = socket.create_connection(world.server_address, timeout=5)
            sock.settimeout(5)
            stream = sock.makefile("rb")
            sockets.append(sock)
            streams.append(stream)
            identity = "load-" + str(i)
            sock.sendall(encode("HELLO", identity, "skell.eq", "Synthetic EQ"))
            if _receive(stream) != ["WELCOME", "hub", "status", "connected"]:
                raise AssertionError("Missing welcome")
            seen = [_receive(stream) for _ in range(i)]
            if {item[1] for item in seen} != {"load-" + str(n) for n in range(i)}:
                raise AssertionError("Incomplete peer snapshot")
            for n in range(i):
                if _receive(streams[n]) != [
                        "PEER", identity, "skell.eq", "online"]:
                    raise AssertionError("Preexisting peer missed a join")
            join_times.append((time.perf_counter() - started) * 1000)

        if world.snapshot()["peer_count"] != peers:
            raise AssertionError("Registered count mismatch")
        if peers == MAX_CLIENTS:
            extra = socket.create_connection(world.server_address, timeout=5)
            try:
                extra.settimeout(5)
                with extra.makefile("rb") as ef:
                    extra.sendall(encode("HELLO", "load-overflow",
                                         "skell.eq", "Overflow"))
                    if _receive(ef) != [
                            "ERROR", "hub", "status", "capacity_or_duplicate"]:
                        raise AssertionError("33rd peer was not rejected")
            finally:
                extra.close()
            if world.snapshot()["peer_count"] != MAX_CLIENTS:
                raise AssertionError("Capacity rejection changed peer count")

        sender = sockets[0]
        for i in range(events):
            started = time.perf_counter()
            value = "bench-" + str(i)
            sender.sendall(encode("EVENT", "load-0", "theme", value))
            for stream in streams[1:]:
                if _receive(stream) != ["EVENT", "load-0", "theme", value]:
                    raise AssertionError("Broadcast frame missing or corrupted")
            event_times.append((time.perf_counter() - started) * 1000)

        url = "http://127.0.0.1:" + str(console.server_address[1]) + "/api/status"
        for _ in range(5):
            started = time.perf_counter()
            with urllib.request.urlopen(url, timeout=5) as response:
                status = json.load(response)
            status_times.append((time.perf_counter() - started) * 1000)
            if status["peer_count"] != peers or status["schema"] != "skellworld-status/1":
                raise AssertionError("Dashboard returned incomplete status")
            if len(status["events"]) > 80:
                raise AssertionError("Unbounded UI event history")
        sender_state = next(p for p in status["peers"] if p["instance_id"] == "load-0")
        if sender_state["events_sent"] != events:
            raise AssertionError("Lost or duplicated synthetic events")

        _, allocated_peak = tracemalloc.get_traced_memory()
        return {
            "scenario": "synthetic-loopback-not-fl-studio",
            "instances": peers,
            "published_events": events,
            "broadcast_recipients": max(0, peers - 1),
            "join_latency": _percentiles(join_times),
            "event_fanout_latency": _percentiles(event_times),
            "status_http_latency": _percentiles(status_times),
            "process_cpu_ms": round((time.process_time() - cpu_start) * 1000, 2),
            "elapsed_ms": round((time.perf_counter() - begin) * 1000, 2),
            "python_peak_allocated_kib": round(allocated_peak / 1024, 1),
            "result": "PASS",
        }
    finally:
        # Closing the sockets is deliberately done *before* shutting servers
        # down; no background operation or state persists after this process.
        for sock in sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        for stream in streams:
            try:
                stream.close()
            except OSError:
                pass
        for sock in sockets:
            sock.close()
        for server in (console, world):
            if server is not None:
                server.shutdown()
                server.server_close()
        for thread in threads:
            thread.join(timeout=3)
        tracemalloc.stop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", default="1,8,16,32")
    parser.add_argument("--events", type=int, default=8)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    counts = [int(v) for v in args.counts.split(",")]
    if not counts or len(counts) != len(set(counts)):
        parser.error("Provide distinct, nonempty peer counts")
    results = [exercise(count, events=args.events) for count in counts]
    summary = {"schema": "skellworld-load-benchmark/1", "results": results,
               "warning": "Synthetic localhost protocol timings, not VST3/audio-thread performance"}
    payload = json.dumps(summary, indent=2) + "\n"
    print(payload, end="")
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
