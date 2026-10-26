"""Thin OS integration: foreground window, clipboard, single-instance lock."""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

log = logging.getLogger("snaptype.os")


def foreground_title() -> str:
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            u = ctypes.windll.user32
            u.GetForegroundWindow.restype = wintypes.HWND
            hwnd = u.GetForegroundWindow()
            n = u.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(hwnd, buf, n + 1)
            return buf.value
        if sys.platform == "darwin":
            r = subprocess.run(["osascript", "-e",
                                'tell app "System Events" to get name of first process '
                                'whose frontmost is true'],
                               capture_output=True, text=True, timeout=0.3)
            return r.stdout.strip()
        r = subprocess.run(["xdotool", "getactivewindow", "getwindowname"],
                           capture_output=True, text=True, timeout=0.3)
        return r.stdout.strip()
    except Exception:
        return ""


def read_clipboard() -> str:
    """Unicode text from the clipboard (Windows only). Uses explicit ctypes
    signatures — the defaults truncate 64-bit handles and can crash."""
    if sys.platform != "win32":
        return ""
    import ctypes
    from ctypes import wintypes
    u, k = ctypes.windll.user32, ctypes.windll.kernel32
    u.OpenClipboard.argtypes = [wintypes.HWND]
    u.OpenClipboard.restype = wintypes.BOOL
    u.GetClipboardData.argtypes = [wintypes.UINT]
    u.GetClipboardData.restype = wintypes.HANDLE
    u.CloseClipboard.restype = wintypes.BOOL
    k.GlobalLock.argtypes = [wintypes.HGLOBAL]
    k.GlobalLock.restype = ctypes.c_void_p
    k.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    for _ in range(5):                      # clipboard may be briefly held by another app
        if u.OpenClipboard(None):
            break
        time.sleep(0.01)
    else:
        return ""
    try:
        handle = u.GetClipboardData(13)     # CF_UNICODETEXT
        if not handle:
            return ""
        ptr = k.GlobalLock(handle)
        if not ptr:
            return ""
        try:
            return ctypes.wstring_at(ptr)
        finally:
            k.GlobalUnlock(handle)
    finally:
        u.CloseClipboard()


class WindowTracker:
    """Remembers the last focused window that isn't SnapType (for the
    'Capture window' button in App Rules)."""

    def __init__(self, app_name: str):
        self.app_name = app_name
        self.last = ""
        self._stop = threading.Event()

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.wait(0.6):
            t = foreground_title()
            if t and self.app_name not in t:
                self.last = t


class SingleInstance:
    """Prevents two SnapType processes (which would double-expand everything)."""

    def __init__(self, name: str, lock_dir: Path):
        self.name, self.lock_dir = name, Path(lock_dir)
        self._handle = None

    def acquire(self) -> bool:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            k = ctypes.windll.kernel32
            k.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
            k.CreateMutexW.restype = wintypes.HANDLE
            self._handle = k.CreateMutexW(None, False, f"Local\\{self.name}")
            return k.GetLastError() != 183  # ERROR_ALREADY_EXISTS
        try:
            import fcntl
            self.lock_dir.mkdir(parents=True, exist_ok=True)
            self._handle = open(self.lock_dir / f"{self.name}.lock", "w")
            fcntl.flock(self._handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except (OSError, ImportError):
            return False


def _colorref(hex_color: str) -> int:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16) | (int(h[2:4], 16) << 8) | (int(h[4:6], 16) << 16)


def set_titlebar_theme(window_id: int, dark: bool = True, caption: str | None = None,
                       text: str | None = None) -> bool:
    """Dark title bar (Windows 10 20H1+) and, on Windows 11, a caption/text colour that
    matches the app. A silent no-op everywhere else. Returns True if dark mode applied."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        user32, dwm = ctypes.windll.user32, ctypes.windll.dwmapi
        user32.GetParent.argtypes, user32.GetParent.restype = [wintypes.HWND], wintypes.HWND
        dwm.DwmSetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        dwm.DwmSetWindowAttribute.restype = ctypes.c_long
        hwnd = user32.GetParent(window_id) or window_id   # Tk's frame is the parent of its client HWND

        def put(attr: int, value: int) -> int:
            v = ctypes.c_int(value)
            return dwm.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v))

        ok = put(20, int(dark)) == 0 or put(19, int(dark)) == 0   # 20 on current builds, 19 on early Win10
        if caption:
            put(35, _colorref(caption))
        if text:
            put(36, _colorref(text))
        return ok
    except (OSError, AttributeError, ValueError):
        log.debug("Could not theme the title bar", exc_info=True)
        return False


def open_path(path: str | Path) -> bool:
    """Open a file or folder with the OS default handler without blocking the UI."""
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # noqa: S606
        else:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except OSError:
        log.warning("Could not open %s", path, exc_info=True)
        return False
