# SkellWorld SW1 connection scalability

SkellWorld's **synthetic localhost benchmark** starts one isolated hub and
read-only dashboard on ephemeral loopback ports, joins 1, 8, 16, then 32 simulated
plugin instances, verifies each frame on every receiver, confirms the 33rd
connection is rejected, and measures joining, fanout and read-only HTTP status.

Run with Python 3:

```powershell
python tools/benchmark_skellworld.py --counts 1,8,16,32 --events 8 --output benchmark.json
```

Output contains wall-clock p50 / p95 / max latencies for each step, current
process CPU milliseconds, and **peak traced Python allocations**. These figures
are **not** DAW audio latency, plugin CPU usage, whole-process RSS, or measured
FL Studio PDC. Comparing them across machines requires repeated runs under
comparable load. CI checks **correctness, capacity, bounded history and clean
termination**; runner speed is deliberately *not* enforced as an artificial
absolute pass/fail threshold.

### Safety and performance boundaries

- The server binds `127.0.0.1` only, with a maximum of 32 registered peers and
  a per-connection input rate limit. The dashboard is read-only.
- Nothing connects to the internet or launches a host application; all clients
  use ordinary loopback TCP sockets.
- Each event goes to connected **other** peers, never to the sender; frames
  must be delivered in full and remain parseable.
- Idle instances remain connected without a required heartbeat. An event age
  does **not** mean a plugin is broken.
- For actual audio CPU, dropout, PDC, DAW save/reopen and reconnect behavior,
  use `docs/FL_STUDIO_WORLD_TEST_PLAN.md` on the target Windows machine.

If future benchmarks expose stalls, optimize the hub's communication
implementation before raising capacity or introducing remote controls.
