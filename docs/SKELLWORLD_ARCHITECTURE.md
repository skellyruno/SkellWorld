# SkellWorld architecture / integration boundaries

## Goals

SkellWorld is the local ecosystem layer for SKELL products, **not** a DAW host, a cloud account service, a second DSP engine, or a remote-configuration server.

```text
SKELL plugins (JUCE / SkellCore UI)
  | each plugin's explicit JOIN WORLD (never processBlock)
  v
SW1 informational plugin bus - TCP 127.0.0.1:48673
  | bounded messages, presence + five non-privileged event topics
  v
SkellWorld hub (standard-library Python)
  | thread-safe snapshots, no parameter writes, no file system commands
  v
Read-only dashboard - HTTP 127.0.0.1:48674
  | activity + catalog inventory; no installed-product detection
  v
User's own browser (no network dependency)
```

## Core ownership

| Project | Owns | Does not own |
| --- | --- | --- |
| SkellWorld | Presence bus, event schema, catalog, local console | Plugin DSP, DAW parameter automation, software updates |
| SkellCore | Shared JUCE UI/DSP components | Inter-plugin privileged control or central update service |
| Project Hub | Project management, builds, releases | Unauthenticated access from plugin events |
| SkellyHub | Customer-facing product management | Developer-only project secrets |
| Individual plugin | DSP, host parameters, preset formats, lifecycle | Hub availability |

The duplicate SkellCore source currently bundled in this repository is a compatibility snapshot inherited from the template. Long-term: replace that snapshot with a pinned dependency after successful build and behavior parity checks.

## Transport contracts

The wire format is `SW1|KIND|INSTANCE|TOPIC|VALUE\n`. The existing SW1 reader understands HELLO, WELCOME, PEER, EVENT, BYE, ERROR. Protocol v1 is limited to printable ASCII field data, 255-byte frames, up to 32 registered peers and up to 30 incoming lines/second per peer.

- The hub **only** accepts connections on IPv4 loopback.
- The dashboard **only** accepts requests on IPv4 loopback, and exposes GET /api/status, GET /api/catalog, and static UI assets.
- Frames from different source threads are serialized per peer and have a bounded write deadline; a stalled receiver is disconnected.
- New-join notifications are sent only to peers registered before that join. Existing peers are sent in the new client's initial snapshot.
- The dashboard uses text-only rendering for event data and validates GitHub repository names before constructing outbound links.
- An inactive browser tab does not poll status. The UI avoids replacing event/peer lists if the hub event sequence has not changed.

**The bus is not authenticated.** A malicious application running on the same computer may impersonate informational events. Don't put API keys, personal data, preset files, script execution, plugin parameters, installer privileges or downloads on SW1.

## Integrating a production plugin

1. Keep its current manufacturer/plugin IDs, parameter IDs, state/preset formats and DSP unchanged.
2. Add a separate stable product identity and per-instance session ID.
3. Add an optional, **user-initiated** JOIN/LEAVE action to an existing UI; leave off by default.
4. Use the SkellCore worker-thread WorldLink; no sockets, allocations or locks in the audio callback.
5. Confirm hub down, restart, editor close/reopen, multiple instances and host project restoration.
6. Build VST3 and run host-level FL Studio smoke tests before calling it production-ready.
7. Mark the product integration status in catalog only after verification.

## Separate Project Hub integration

Project Hub remains independently deployable and can be launched separately. A future Developer Mode integration should have its own **authenticated, permissioned** app-to-app API, with permissions reviewed for each action. SkellWorld must never treat an SW1 event as permission to execute GitHub commands or alter files.

## Remaining milestones

- Production plugin adoption in separate repositories after explicit testing.
- Browser-based live connection diagnostics and better accessibility/visual regression checks.
- Authenticated developer integration and scoped permissions (Project Hub), not part of SW1.
- User-approved preset metadata browsing (no silent application of settings).
- Desktop packaging after cross-platform behavior and asset-path validation.
