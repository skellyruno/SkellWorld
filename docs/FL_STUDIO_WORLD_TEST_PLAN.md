# SKELLWORLD — FL Studio integration acceptance plan

**Current status:** Source integrations for Skell Key and SkellyTune exist in their own GitHub repositories, and their Windows VST3 CI builds pass. The SkellWorld diagnostic uses *simulated* SW1 clients; **it is not evidence that two real VST3 instances work together in FL Studio**.

## Automated localhost protocol check

From a source checkout with Python 3:

```powershell
python tools/skellworld_pair_diagnostic.py
```

This launches an isolated hub on random loopback ports, registers two simulated clients with production product IDs `skell.key` and `skell.tune`, sends a complete E minor / 432.50 Hz A4 packet, confirms the listener receives it, checks the dashboard snapshot, then verifies cleanup after disconnect. It neither scans your plugins nor touches your DAW.

## FL Studio host certification checklist

1. **Windows VST3 load:** install the current Skell Key and SkellyTune VST3 builds from their own successful workflows; launch FL Studio and scan each plugin. Confirm both editors open without wrapper errors.
2. **Explicit opt-in:** launch SkellWorld desktop app. Open Skell Key and SkellyTune; enable their documented Send to Tune / Follow actions. Confirm the dashboard shows their *actual* instances, not the simulated test names.
3. **Complete packet:** provide a known E minor input, confirm Skell Key is stable, then verify Tune receives root 4, natural minor, the seven-note scale and the correct A4 frequency (e.g. 432.50 Hz if source tuning is calibrated accordingly). No parameter should change before Follow is enabled.
4. **Direct-no-hub mode:** close SkellWorld completely and confirm the direct SkellCore local tuning bus still works between Key and Tune. The dashboard will be unavailable; this must not interrupt audio.
5. **Multiple instances:** open two Tune instances and verify both follow the intended Key packet; close one without affecting the other. Reconnect the hub and check presence reconnection when World sharing is reenabled.
6. **Project saves/restores:** save the FLP, close and reopen FL Studio, ensure preexisting automation IDs, plugin settings and the user's opt-in semantics remain intact.
7. **Runtime:** monitor FL Studio CPU, underruns and PDC with audio playing; ensure no audio-thread blocking, pops, crashes or audible DSP changes caused by presence.
8. **Skell Silence pilot:** with SkellWorld open, use Skell Silence Settings → Join SkellWorld; verify a `skell.silence` instance appears, then Settings → Leave; verify disappears. Close the editor and ensure it leaves without a crash. Repeat with hub absent; audio must continue unchanged.
9. **Regression:** stop SkellWorld via Exit and title-bar X; no TclError. Verify stale tuning is cleared from dashboard and the hub releases both localhost ports.
10. **Evidence:** capture FL Studio version, Windows version, plugin VST3 build hashes, any alerts, and a short screen capture of Key → Tune and Silence → hub. Report pass/fail per step.

## Integration states

- **Source implemented:** code and repository CI pass; does not imply successful FL Studio playback.
- **Protocol simulated:** automated localhost fixture passes; does not imply VST3 runtime behavior.
- **Host verified:** the above checklist has been run against actual plugins in FL Studio and the evidence has been saved.
- **Planned:** not yet integrated or tested.

Project Hub is independent. SkellWorld Developer Mode only points to its repository and read-only discovery contract, not a privileged control endpoint.


## v0.5 plugin presence acceptance

- **Skell Preset** — in Settings choose **Join SkellWorld**, verify `skell.preset` presence in SkellWorld, open two instances and inspect separate ephemeral IDs, then leave or close the editors. Save/reopen the FLP and verify effect chain and automation remain unchanged.
- **Skelly EQ** — click the small **v2.7** badge → Join SkellWorld. Verify `skell.eq` presence and that the existing RANGE button still cycles graph range. Close/leave, confirm presence cleanup, and verify saved 8-band EQ curves remain unchanged.
- **Connection health** — Creator Mode → Run Check should show joined sessions and known source integrations, not assert that unjoined products are installed. Idle instances should remain joined; their event age may grow without signalling a failure.
- **Evidence** — record each tested plugin's VST3 SHA, FL Studio and Windows versions, project reload, UI close/reopen, CPU and no-crash result. Source CI success alone must never be labeled host-certified.
