"""Validated, debounced user configuration."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from .hotkeys import try_normalize
from .storage import load_json, save_json

APP_MODES = ("all", "include", "exclude")
CONFIG_VERSION = 2
OLD_DEFAULT_UNDO = "ctrl+z"
NEW_DEFAULT_UNDO = "ctrl+shift+u"

DEFAULTS: dict[str, Any] = {
    "config_version": CONFIG_VERSION,
    "toggle_hotkey": "ctrl+shift+s",
    "undo_hotkey": NEW_DEFAULT_UNDO,
    "undo_on_backspace": True,
    "replace_delay": 0.006,
    "snooze_minutes": 5,
    "app_mode": "all",
    "app_list": [],
    "notify_enabled": True,
    "startup_enabled": False,
    "skip_sensitive_windows": True,
    "consent_given": False,
    "auto_start": True,          # begin expanding as soon as SnapType launches
    "sidebar_collapsed": False,
    "tray_hint_shown": False,
}


def _clamp(value: Any, lo: float, hi: float, default: float, cast=float):
    try:
        return min(max(cast(value), lo), hi)
    except (TypeError, ValueError):
        return default


def sanitize(raw: Any) -> dict[str, Any]:
    """Merge ``raw`` over defaults, coercing every known key to a safe value."""
    d = {**DEFAULTS, **(raw if isinstance(raw, dict) else {})}
    # v1.x used Ctrl+Z for undo, which also undid text inside the app itself.
    if int(_clamp(raw.get("config_version", 1) if isinstance(raw, dict) else 1, 0, 99, 1, int)) < 2 \
            and d.get("undo_hotkey") == OLD_DEFAULT_UNDO:
        d["undo_hotkey"] = NEW_DEFAULT_UNDO
    d["config_version"] = CONFIG_VERSION
    d["replace_delay"] = _clamp(d["replace_delay"], 0.0, 0.1, DEFAULTS["replace_delay"])
    d["snooze_minutes"] = _clamp(d["snooze_minutes"], 1, 240, DEFAULTS["snooze_minutes"], int)
    if d["app_mode"] not in APP_MODES:
        d["app_mode"] = "all"
    apps = d["app_list"] if isinstance(d["app_list"], list) else []
    d["app_list"] = [str(a).strip() for a in apps if str(a).strip()]
    for key in ("toggle_hotkey", "undo_hotkey"):
        d[key] = try_normalize(d[key] if isinstance(d[key], str) else "", DEFAULTS[key])
    if d["toggle_hotkey"] == d["undo_hotkey"]:       # two actions on one combo can never both work
        d["undo_hotkey"] = DEFAULTS["undo_hotkey"] if d["toggle_hotkey"] != DEFAULTS["undo_hotkey"] \
            else DEFAULTS["toggle_hotkey"]
    for key in ("undo_on_backspace", "notify_enabled", "startup_enabled", "skip_sensitive_windows",
                "consent_given", "auto_start", "sidebar_collapsed", "tray_hint_shown"):
        d[key] = bool(d[key])
    return d


class Config:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._d = sanitize(load_json(self.path, {}))
        self._timer: threading.Timer | None = None
        self._save()

    def get(self, key: str) -> Any:
        with self._lock:
            return self._d.get(key, DEFAULTS.get(key))

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._d[key] = value
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(0.3, self._save)
            self._timer.daemon = True
            self._timer.start()

    def flush(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        self._save()

    def _save(self) -> None:
        with self._lock:
            snapshot = dict(self._d)
        save_json(self.path, snapshot)
