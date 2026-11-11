#!/usr/bin/env python3
"""SkellWorld standalone Windows application with a stoppable local hub."""
from __future__ import annotations

import argparse
import threading
import webbrowser

from skellworld_hub import PORT, WorldServer
from skellworld_dashboard import DashboardServer

DASHBOARD_PORT = 48674


class LocalWorld:
    """Own the two loopback listeners and their threads; never touch DSP."""

    def __init__(self, port=PORT, dashboard_port=DASHBOARD_PORT):
        self.hub = WorldServer(("127.0.0.1", port))
        try:
            self.dashboard = DashboardServer(("127.0.0.1", dashboard_port), self.hub)
        except BaseException:
            self.hub.server_close()
            raise
        self.threads = []
        self.running = False

    @property
    def dashboard_url(self):
        return "http://127.0.0.1:" + str(self.dashboard.server_address[1])

    def start(self):
        if self.running:
            return
        self.running = True
        for name, server in (("Hub", self.hub), ("Dashboard", self.dashboard)):
            thread = threading.Thread(
                target=server.serve_forever, kwargs={"poll_interval": 0.2},
                name="SkellWorld " + name, daemon=True)
            thread.start()
            self.threads.append(thread)

    def stop(self):
        if self.running:
            self.running = False
            for server in (self.dashboard, self.hub):
                server.shutdown()
        for server in (self.dashboard, self.hub):
            server.server_close()
        for thread in self.threads:
            thread.join(timeout=3)
        self.threads.clear()


def run_window(world, gui_exit_smoke=None):
    # The launcher does not require Qt, a browser engine, or third-party GUI libs.
    import tkinter as tk
    root = tk.Tk()
    root.title("SKELLWORLD")
    root.geometry("460x268")
    root.minsize(420, 258)
    root.configure(bg="#0b100d")
    root.resizable(False, False)

    outer = tk.Frame(root, bg="#0b100d", padx=26, pady=18)
    outer.pack(fill="both", expand=True)
    heading = tk.Frame(outer, bg="#0b100d")
    heading.pack(fill="x")
    tk.Label(heading, text="SKELL", bg="#0b100d", fg="#f1f8ee",
             font=("Segoe UI", 22, "bold")).pack(side="left")
    tk.Label(heading, text="WORLD", bg="#0b100d", fg="#aaff76",
             font=("Segoe UI", 22, "bold")).pack(side="left")
    tk.Label(outer, text="LOCAL ECOSYSTEM / CONNECTION HUB", bg="#0b100d",
             fg="#8aa48d", anchor="w", font=("Segoe UI", 9)).pack(fill="x", pady=(0, 16))

    summary = tk.Frame(outer, bg="#152219", padx=16, pady=14,
                       highlightbackground="#345640", highlightthickness=1)
    summary.pack(fill="x")
    status = tk.Label(summary, text="●  WORLD ONLINE", bg="#152219",
                      fg="#b5ff84", anchor="w", font=("Segoe UI", 11, "bold"))
    status.pack(fill="x")
    peers = tk.Label(summary, text="0 plugin instances joined", bg="#152219",
                     fg="#9bb2a1", anchor="w", font=("Segoe UI", 9))
    peers.pack(fill="x", pady=(6, 0))

    actions = tk.Frame(outer, bg="#0b100d")
    actions.pack(fill="x", pady=(17, 0))
    tk.Button(actions, text="OPEN DASHBOARD", command=lambda: webbrowser.open(world.dashboard_url),
              font=("Segoe UI", 10, "bold"), bg="#a6f774", fg="#0b170b",
              activebackground="#c7ff9f", activeforeground="#0b170b",
              relief="flat", padx=15, pady=9, cursor="hand2",
              borderwidth=0).pack(side="left", fill="x", expand=True)
    closing = False
    pending_callbacks = []
    callback_error = []

    def close_window():
        # A destroyed Tk interpreter cannot be queried (not even winfo_exists).
        # Cancel pending status/browser callbacks before destroying it once.
        nonlocal closing
        if closing:
            return
        closing = True
        for callback_id in pending_callbacks:
            try:
                root.after_cancel(callback_id)
            except tk.TclError:
                pass
        pending_callbacks.clear()
        root.destroy()

    def on_callback_error(exc_type, exc_value, traceback):
        callback_error.append(exc_value)
        close_window()

    root.report_callback_exception = on_callback_error

    def schedule(delay_ms, callback):
        if closing:
            return
        handle = [None]
        def invoke():
            if handle[0] in pending_callbacks:
                pending_callbacks.remove(handle[0])
            if not closing:
                callback()
        handle[0] = root.after(delay_ms, invoke)
        pending_callbacks.append(handle[0])

    exit_button = tk.Button(actions, text="EXIT SKELLWORLD", command=close_window,
              font=("Segoe UI", 9, "bold"), bg="#1b2a21", fg="#cde7cb",
              activebackground="#314837", activeforeground="#ffffff",
              relief="flat", padx=15, pady=10, cursor="hand2",
              borderwidth=0)
    exit_button.pack(side="left", padx=(10, 0))
    root.protocol("WM_DELETE_WINDOW", close_window)

    def tick():
        if closing:
            return
        try:
            count = world.hub.snapshot()["peer_count"]
            peers.config(text=str(count) + " plugin instance" + ("" if count == 1 else "s") + " joined")
        except tk.TclError:
            if not closing:
                raise
            return
        schedule(1000, tick)

    schedule(200, tick)
    if gui_exit_smoke is None:
        schedule(450, lambda: webbrowser.open(world.dashboard_url))
    elif gui_exit_smoke == "button":
        schedule(600, exit_button.invoke)  # actual button close path
    elif gui_exit_smoke == "window":
        schedule(600, close_window)        # same callback as the window X
    else:
        raise ValueError("Unknown UI smoke-test action")

    # Closing the window ends mainloop. Never query Tk or destroy a second time.
    root.mainloop()
    if callback_error:
        raise RuntimeError("SkellWorld UI callback failed") from callback_error[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--dashboard-port", type=int, default=DASHBOARD_PORT)
    parser.add_argument("--smoke-test", action="store_true", help="start listeners without GUI for CI")
    parser.add_argument("--gui-exit-smoke", choices=("button", "window"),
                        help="run real Tk window, close via chosen UI path, and exit cleanly")
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535 or not 1024 <= args.dashboard_port <= 65535:
        parser.error("ports must be in the range 1024..65535")
    if args.port == args.dashboard_port:
        parser.error("hub and dashboard ports must differ")
    world = LocalWorld(args.port, args.dashboard_port)
    try:
        world.start()
        if args.smoke_test:
            # Used only by the packaged executable CI smoke test. The test
            # parent checks HTTP and then terminates this temporary process.
            threading.Event().wait()
        else:
            run_window(world, gui_exit_smoke=args.gui_exit_smoke)
    finally:
        world.stop()


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        # Windowed EXEs have no stdout: show startup errors instead of silently
        # failing, such as when another SkellWorld copy is already running.
        try:
            import tkinter.messagebox
            tkinter.messagebox.showerror("SkellWorld could not start", str(error))
        except Exception:
            raise
