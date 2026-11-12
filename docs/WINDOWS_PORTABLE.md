# SkellWorld — Portable Windows Build

## Run

1. Extract `SkellWorld-Windows-Portable.zip`.
2. Double-click `SkellWorld.exe` (Windows 10/11 x64).
3. The small SKELLWORLD launcher opens. It starts **only two loopback listeners** and opens the dashboard in your default browser.
4. Click **OPEN DASHBOARD** to reopen it any time. Click **EXIT SKELLWORLD** or close its small launcher window to stop the hub.

**Python is NOT required** for the packaged EXE. No installation, account, network discovery, auto-start or cloud connection is included. First launch may take longer because the single-file EXE extracts its bundled runtime into a temporary directory. The EXE is unsigned and may trigger Windows SmartScreen; only run files obtained from your own verified repository build.

## Ports and communication

- Browser dashboard: `http://127.0.0.1:48674` (read-only)
- Plugin SW1 protocol: `127.0.0.1:48673` (opt-in presence and informational events)
- The launcher binds only to `127.0.0.1`, not your LAN or public internet.
- Skell Key can send key, scale, and A4 metadata to the hub when you explicitly select SEND TO TUNE. This dashboard **does not** change plugin parameters.
- Source-code integration is not a substitute for testing Key and Tune together inside FL Studio.

Close any older SkellWorld hub before launching the EXE, because only one program can own these ports. If a port is busy, the app displays an error instead of opening another hub.

## Development and verification

The GitHub Actions `SkellWorld portable Windows application` workflow runs the source tests, builds a PyInstaller one-file windowed EXE, starts **that actual packaged EXE**, checks the dashboard and catalog, sends a real SW1 Skell Key tuning message, and checks disconnect cleanup. It uploads the ZIP and EXE as Actions artifacts. The ZIP is not a signed production release.

The plain source-based developer launcher remains available: `python tools/skellworld_hub.py --open-browser`.

## SkellWorld v0.3.1 — Windows exit-crash fix

The original v0.3 executable could raise a Tkinter `TclError` when the window closed because it called `winfo_exists()` **after** the Tk interpreter had already been destroyed. The launcher now uses one idempotent close callback for both **EXIT SKELLWORLD** and the title-bar **X** button, cancels queued UI callbacks before teardown, and never queries widgets after mainloop exits.

The Windows packaging workflow now launches the **real frozen GUI** twice (via Exit and window close) and requires both processes to terminate with exit code 0. A headless source test would not have detected the original crash.

The updated dashboard also offers a connected-instance inspector and a read-only Project Hub workspace directory. SkellWorld does not launch installed applications, send privileged commands, or read project files.
