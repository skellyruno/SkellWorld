# SkellWorld — the SKELL plugin ecosystem

SkellWorld is the **connection layer** above SkellCore, not a replacement for the existing audio engines. Plugin IDs, presets, DSP, latency contracts and existing DAW sessions must remain unchanged.

## What's implemented in v1

- **Identity** — every newly generated plugin has `skellworld.json`, a stable product ID, and an independent runtime instance ID.
- **Wire protocol** — `SkellCore/World.h` defines strict, versioned `SW1` messages limited to 255 bytes, with input validation and a fixed-size single-producer/single-consumer mailbox.
- **Local hub** — `tools/skellworld_hub.py` relays presence events across different plugin processes, plus *informational* events for theme, preset name, transport and level. It binds only to IPv4 loopback `127.0.0.1:48673`.
- **JUCE bridge** — `SkellCore/WorldLink.h` connects from a worker thread. No sockets, locks, Python or allocations are added to an audio-processing callback. A JOIN/LEAVE control in the template provides explicit consent.
- **Lifecycle** — the connection is owned by the plugin processor. Closing or reopening its editor does not disconnect a joined instance.
- **Catalog** — `catalog.json` inventories SKELL GitHub plugin repositories, including best-effort VST3 plugin-code/bundle metadata. Entries marked `planned` are **not** yet connected. The generator refuses codes that collide with catalogued products.

## Try the first connected world

On Windows, double-click **`Start-SkellWorld.bat`** in the template folder (Python 3 must be installed). Alternatively, open a terminal in the template checkout:

```sh
python tools/skellworld_hub.py
```

Launch two instances of the **Skell Quickstart** VST3 (or Standalone) and click **JOIN WORLD** in both editors. Each joined instance should show **WORLD ONLINE | 1 peers**. Closing a plugin editor does not disconnect its audio processor; re-opening shows the current world status. Clicking **LEAVE WORLD** disconnects only that instance.

All plugins still work without this helper app. No connection starts automatically, and the helper does not run at machine startup. It uses only the Python standard library. This localhost v1 bus is intentionally **not** a cloud service.

## Core event schema

Each wire line has five fields and is newline terminated:

```
SW1|HELLO|<instance-id>|<product-id>|<display-name>
SW1|WELCOME|hub|status|connected
SW1|PEER|<instance-id>|<product-id>|online
SW1|PEER|<instance-id>|<product-id>|offline
SW1|EVENT|<instance-id>|theme|neon
```

These events are informational. They must never be interpreted as a remote request to adjust host parameters, apply a preset, load files, expose audio, change latency, or execute commands. Only the originating plugin or user may authorize control actions.

**Transport rules:** product and instance tokens contain only ASCII letters/digits/period/underscore/hyphen; values are short printable ASCII without pipes, backslashes or control characters. Max line = 255 bytes; max peers = 32; max input rate per peer = 30 messages/sec. Version mismatch or malformed input disconnects the sender.

## Performance and safety

- Connecting creates one background worker per joined plugin instance; **disabled by default**.
- Worker wakes on infrequent socket checks and its only shared state with the editor is an atomic online/peer count and bounded SPSC event queue.
- Each core DSP/GUI thread remains unaffected; do **not** call `join`, `leave` or `publish` from `processBlock`.
- Hub is loopback-only, but other local processes can still send spoofed informational events. There is **no authentication or encryption in v1**. Therefore this protocol deliberately has no control messages, no private data, and no preset file transfers.
- For future user-controlled remote actions, use an authenticated, permissioned broker with explicit destination and sender approval; do not upgrade v1 EVENT to executable commands.

## Roadmap to one integrated SKELL world

1. **Now:** stable product identity, local peer presence and safe information routing (template demo complete).
2. **Next:** integrate WorldLink into select existing plugins through separate PRs, preserving sound, VST3 IDs, preset formats and UI defaults. Test each plugin under FL Studio before merging.
3. **Shared assets:** optional theme and preset metadata browsing. A preset name is not a preset file. Never silently overwrite a plugin's settings.
4. **Central app:** SKELL Hub provides a visible world map of plugins, connected sessions, theme controls, installed products and optional downloads, with explicit consent.
5. **Cross-plugin workflows:** optional transport alignment and preset-chain workflows, not sample-accurate audio routing. DAW host handles actual audio/MIDI order and plugin delay compensation.
6. **Future:** authenticated local agent, and optional cloud accounts/licensing only with a separately reviewed privacy model.

## Validate

```sh
cmake -S SkellCore -B build-world -DSKELLCORE_BUILD_TESTS=ON
cmake --build build-world --config Release
ctest --test-dir build-world -C Release --output-on-failure
python -m unittest discover -s SkellWorld/tests -v
```

Windows VST3 and Standalone builds compile the JUCE WorldLink. A real two-instance FL Studio smoke test is still needed before declaring DAW-level integration complete.

## New: local visual console

The standalone SkellWorld repository adds a **read-only localhost web dashboard** to the existing SW1 hub. Run:

    python tools/skellworld_hub.py

Then open **http://127.0.0.1:48674**. The plug-in protocol still uses **127.0.0.1:48673**. On Windows run **Start-SkellWorld.bat**.

The dashboard shows active opted-in instances, bounded informational activity, uptime, and the catalog. A planned catalog entry does not mean its plugin is installed or connected. No automatic scanning, audio streaming, remote parameter changes, cloud, or credential collection.

Security boundaries: loopback-only listener, GET/HEAD read-only endpoints, strict Host/Origin checks, restrictive Content Security Policy, no raw HTML rendering of incoming names, and bounded in-memory activity. Other local processes **can spoof informational events** in protocol v1; do not trust this bus for privileged actions.

For alternate ports or CLI-only use:

    python tools/skellworld_hub.py --port 48673 --dashboard-port 48674
    python tools/skellworld_hub.py --no-dashboard

Test: python -m unittest discover -s SkellWorld/tests -v

## Next reliability / directory milestone

The SW1 hub serializes outgoing frames per connected peer and enforces a short write deadline. New peers are only announced to already-registered peers, preventing duplicate **online** messages during concurrent joins. Registered peers remain limited to 32, and invalid/non-local listener addresses are rejected.

The dashboard now searches known SKELL repository names and offers **All / World demo / Core only / Planned** filters. Repository cards link to GitHub only if their names match the expected `skellyruno/<repository>` format. Catalog entries are not proof a product is installed, running, licensed, or integrated.

The dashboard stops polling while its browser tab is hidden and avoids recreating peer/event lists when the hub's activity sequence is unchanged. A reconnect or hub restart invalidates stale display state.

Validation includes concurrent peer-registration and simultaneous informational-event regression tests, plus HTML endpoint tests and a JavaScript syntax check. The SW1 protocol is still informational only and has no authentication: do not add privileged control or any user file access.

**Developer Mode / Project Hub:** Project Hub is a separate product and repository. A future explicit integration should use an authenticated, permissioned API rather than extending SW1 to execute commands. No automatic Project Hub connection is claimed by this milestone.
