#!/usr/bin/env python3
"""
SnapType: instant text expander for Windows.
Type a short abbreviation, get the full phrase, in any app.

Author: Abdul Rehman  |  2026

This file is only the entry point. The interface lives in ``snapui`` and all
logic (engine, snippets, config, stats) in ``snapcore``.
"""
# DPI awareness must be set BEFORE any tkinter call, or Windows blurs the whole window.
import sys

if sys.platform == "win32":
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)      # per-monitor
    except (OSError, AttributeError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except (OSError, AttributeError):
            pass

import logging
import threading
import tkinter as tk
from tkinter import messagebox

from snapcore import APP_NAME, VERSION
from snapcore import paths as _paths
from snapcore.logsetup import setup_logging
from snapcore.paths import DATA_DIR, LOG_FILE
from snapcore.winutil import SingleInstance

log = logging.getLogger("snaptype")


def _fail(title: str, message: str) -> None:
    """Report a problem before (or without) the main window, using a native box."""
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title, message)
    root.destroy()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    start_hidden = "--tray" in argv                       # used by "launch at login"
    try:
        import keyboard  # noqa: F401  (checked early so a missing install is reported cleanly)
        import pystray  # noqa: F401
        from PIL import ImageTk  # noqa: F401
    except ImportError:
        _fail(f"{APP_NAME}: missing packages",
              "Please run:\n\n    pip install -r requirements.txt\n\nThen restart.")
        return 1

    _paths.migrate_legacy(DATA_DIR)
    setup_logging(LOG_FILE, debug="--debug" in argv)
    def _thread_error(args):
        name = args.thread.name if args.thread else "?"
        log.error("Unhandled error in thread %s", name,
                  exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    threading.excepthook = _thread_error

    instance = SingleInstance(APP_NAME, DATA_DIR)
    if not instance.acquire():
        if not start_hidden:                              # a silent login start must never pop a dialog
            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo(APP_NAME, "SnapType is already running. Look for it in the system tray.")
            root.destroy()
        return 0
    try:
        from snapui.app import SnapTypeApp
        SnapTypeApp(start_hidden=start_hidden).run()
        return 0
    except Exception:  # noqa: BLE001  (last-resort handler: log it and tell the person)
        log.exception("Fatal error in %s %s", APP_NAME, VERSION)
        _fail(APP_NAME, "SnapType hit an unexpected error and must close.\n\n"
                        f"Details were saved to:\n{LOG_FILE}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
