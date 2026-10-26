"""Launch-at-login (Windows Run key)."""
from __future__ import annotations

import sys
from pathlib import Path

from . import APP_NAME

RUN_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"


TRAY_FLAG = "--tray"


def startup_command(frozen: bool | None = None, executable: str | None = None,
                    script: str | None = None) -> str:
    """Command line stored in the Run key.

    Frozen (.exe): just the exe — the v1.2 code appended the script path,
    which does not exist next to a PyInstaller build. From source: use
    pythonw.exe so no console window appears at login. Either way ``--tray`` starts
    SnapType hidden in the system tray instead of opening a window at every login.
    """
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    exe = executable or sys.executable
    if frozen:
        return f'"{exe}" {TRAY_FLAG}'
    p = Path(exe)
    if p.name.lower() == "python.exe" and (p.parent / "pythonw.exe").exists():
        exe = str(p.parent / "pythonw.exe")
    script = script or str(Path(sys.argv[0]).resolve())
    return f'"{exe}" "{script}" {TRAY_FLAG}'


def is_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as k:
            winreg.QueryValueEx(k, APP_NAME)
        return True
    except OSError:
        return False


def set_enabled(enable: bool) -> None:
    if sys.platform != "win32":
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if enable:
            winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(k, APP_NAME)
            except FileNotFoundError:
                pass


def refresh() -> bool:
    """Re-write the Run entry if one exists. Heals a moved .exe and upgrades entries
    written by older versions (which opened the window at every login)."""
    try:
        if is_enabled():
            set_enabled(True)
            return True
    except OSError:
        pass
    return False
