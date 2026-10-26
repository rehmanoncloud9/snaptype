"""The keystroke engine.

All OS access goes through a ``KeyboardBackend`` so the state machine can be
unit-tested without a keyboard. Safety properties:

* The hook callback does nothing but cheap bookkeeping; replacement happens
  on a short timer thread so a slow window poll can never stall typing.
* If the user types anything between the trigger key and the replacement,
  the expansion is *aborted* rather than deleting the wrong characters.
* Keystrokes SnapType injects itself are ignored (no re-triggering).
* Idle gaps and modifier combos reset the word buffer, so stale letters
  never combine with text typed later.
* Windows that look like password/sign-in prompts are skipped by default.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Protocol

from . import APP_NAME
from .config import Config
from .expand import render
from .snippets import SnippetManager
from .stats import Stats

log = logging.getLogger("snaptype.engine")

TRIGGERS = frozenset({"space", "enter", "tab", ".", "!", "?", ",", ";", ":", ")", "]", "}", "-"})
TRIGGER_CHARS = {"space": " ", "enter": "\n", "tab": "\t"}
SENSITIVE_HINTS = ("password", "passcode", "passphrase", "sign in", "log in", "login",
                   "keepass", "bitwarden", "1password", "lastpass", "dashlane",
                   "credential", "verification code", "two-factor", "2fa", "one-time")

BUFFER_IDLE_SECONDS = 4.0     # forget half-typed words after this long
FIRE_DELAY = 0.02             # wait for the trigger key to land in the app
INJECT_SETTLE = 0.12          # ignore our own echoed keystrokes this long
UNDO_WINDOW = 6.0             # backspace-to-undo is valid for this long


class KeyboardBackend(Protocol):
    def on_press(self, callback: Callable[[str], None]) -> None: ...
    def unhook_all(self) -> None: ...
    def add_hotkey(self, combo: str, callback: Callable[[], None]) -> None: ...
    def is_pressed(self, key: str) -> bool: ...
    def backspace(self, n: int) -> None: ...
    def write(self, text: str, delay: float) -> None: ...


class RealKeyboard:
    """Backend backed by the ``keyboard`` package (imported lazily)."""

    def __init__(self):
        import keyboard
        self._k = keyboard

    def on_press(self, callback):
        self._k.on_press(lambda ev: callback(ev.name or ""), suppress=False)

    def unhook_all(self):
        self._k.unhook_all()

    def add_hotkey(self, combo, callback):
        self._k.add_hotkey(combo, callback, suppress=False)

    def is_pressed(self, key):
        return self._k.is_pressed(key)

    def backspace(self, n):
        for _ in range(n):
            self._k.send("backspace")
            time.sleep(0.002)

    def write(self, text, delay):
        self._k.write(text, delay=delay)

    def parse_hotkey(self, combo):
        return self._k.parse_hotkey(combo)


def default_scheduler(delay: float, fn: Callable[[], None]) -> None:
    t = threading.Timer(delay, fn)
    t.daemon = True
    t.start()


class Engine:
    def __init__(self, sm: SnippetManager, cfg: Config, stats: Stats,
                 backend: KeyboardBackend, window_title: Callable[[], str] = lambda: "",
                 clipboard: Callable[[], str] | None = None,
                 on_fire: Callable[[str, str], None] | None = None,
                 scheduler: Callable[[float, Callable[[], None]], None] = default_scheduler,
                 clock: Callable[[], float] = time.monotonic):
        self.sm, self.cfg, self.stats, self.kb = sm, cfg, stats, backend
        self.window_title, self.clipboard, self.on_fire = window_title, clipboard, on_fire
        self._schedule, self._clock = scheduler, clock
        self.active = False
        self._buf = ""
        self._seq = 0
        self._last_key = 0.0
        self._last: dict | None = None
        self._undo_armed = False
        self._skip_once = ""
        self._ignore_until = 0.0
        self._injecting = False
        self._lock = threading.RLock()
        self._snooze: threading.Timer | None = None
        self._toggle_fn: Callable[[], None] | None = None
        # True only while the focus is in SnapType's own "Try it" box, so expansion can be
        # demonstrated there. Every other SnapType field stays protected.
        self.allow_own_window = False

    # ── lifecycle ──────────────────────────────────────────────────────
    def setup(self, toggle_fn: Callable[[], None]) -> None:
        self._toggle_fn = toggle_fn
        self._register_hotkeys(include_undo=False)

    def start(self) -> None:
        if self._snooze:                  # starting manually ends any pending snooze
            self._snooze.cancel()
            self._snooze = None
        if self.active:
            return
        self.active = True
        self._reset_state()
        self.kb.on_press(self._on_key)
        self._register_hotkeys(include_undo=True)

    def stop(self) -> None:
        if not self.active:
            return
        self.active = False
        self._reset_state()
        self.kb.unhook_all()
        self._register_hotkeys(include_undo=False)

    def reregister(self) -> None:
        self.kb.unhook_all()
        if self.active:
            self.kb.on_press(self._on_key)
        self._register_hotkeys(include_undo=self.active)

    def snooze(self, minutes: float, on_wake: Callable[[], None] | None = None) -> None:
        if self._snooze:
            self._snooze.cancel()
        self.stop()

        def _wake():
            self._snooze = None
            self.start()
            if on_wake:
                on_wake()

        self._snooze = threading.Timer(minutes * 60, _wake)
        self._snooze.daemon = True
        self._snooze.start()

    def shutdown(self) -> None:
        if self._snooze:
            self._snooze.cancel()
        self.active = False
        try:
            self.kb.unhook_all()
        except Exception:
            log.exception("unhook_all failed")

    def _reset_state(self) -> None:
        self._buf, self._last, self._undo_armed, self._skip_once = "", None, False, ""

    def _register_hotkeys(self, include_undo: bool) -> None:
        combos = [("toggle_hotkey", self._toggle_fn)]
        if include_undo:
            combos.append(("undo_hotkey", self.undo))
        for key, fn in combos:
            combo = self.cfg.get(key)
            if not combo or fn is None:
                continue
            try:
                self.kb.add_hotkey(combo, fn)
            except Exception as exc:
                log.warning("Could not register %s %r: %s", key, combo, exc)

    # ── keystroke handling (runs on the hook thread: keep it cheap) ────
    def _on_key(self, name: str) -> None:
        now = self._clock()
        if self._injecting or now < self._ignore_until:
            return
        with self._lock:
            self._seq += 1
            if now - self._last_key > BUFFER_IDLE_SECONDS:
                self._buf = ""
            self._last_key = now

            if self.kb.is_pressed("alt") or self.kb.is_pressed("ctrl"):
                self._buf, self._undo_armed = "", False
                return

            if name == "backspace":
                if self._undo_armed and self._last and self.cfg.get("undo_on_backspace") \
                        and now - self._last["t"] < UNDO_WINDOW:
                    self._undo_armed = False
                    seq = self._seq
                    self._schedule(FIRE_DELAY, lambda: self._undo_after_backspace(seq))
                    return
                self._buf = self._buf[:-1]
                self._undo_armed = False
                return

            self._undo_armed = False

            if name in TRIGGERS:
                word, self._buf = self._buf, ""
                if not word:
                    return
                key = word.lower()
                if self._skip_once == key:
                    self._skip_once = ""
                    return
                self._skip_once = ""
                exp = self.sm.get(key)
                if exp:
                    seq = self._seq
                    trig = TRIGGER_CHARS.get(name, name)
                    self._schedule(FIRE_DELAY, lambda: self._fire(word, key, exp, trig, seq))
                return

            if len(name) == 1 and (name.isalnum() or name == "'"):
                self._buf += name
            elif name not in ("shift", "right shift", "caps lock"):
                self._buf = ""

    # ── replacement (runs on a timer thread) ───────────────────────────
    def _fire(self, word: str, key: str, exp: str, trig: str, seq: int) -> None:
        with self._lock:
            if seq != self._seq:
                log.debug("Aborted expansion of %r: user kept typing", key)
                return
            if self.is_blocked():
                return
            text = render(exp, word, clipboard=self.clipboard)
            self._inject(len(word) + 1, text + trig)
            self._last = {"orig": word, "exp": text, "trig": trig, "t": self._clock()}
            self._undo_armed = True
        self.stats.record(key)
        if self.on_fire:
            try:
                self.on_fire(key, text)
            except Exception:
                log.exception("on_fire callback failed")

    def _inject(self, backspaces: int, text: str) -> None:
        self._injecting = True
        try:
            self.kb.backspace(backspaces)
            self.kb.write(text, float(self.cfg.get("replace_delay") or 0.0))
        finally:
            self._ignore_until = self._clock() + INJECT_SETTLE
            self._injecting = False
            self._buf = ""

    def _undo_after_backspace(self, seq: int) -> None:
        """User pressed Backspace right after an expansion: the app already
        deleted the trigger character, so remove the expansion and restore
        the abbreviation (without re-expanding it)."""
        with self._lock:
            info = self._last
            if not info or seq != self._seq:
                return
            self._last = None
            self._inject(len(info["exp"]), info["orig"])
            self._skip_once = info["orig"].lower()
            self._buf = info["orig"]

    def undo(self) -> None:
        """Undo hotkey: restore the abbreviation plus the trigger character."""
        with self._lock:
            info = self._last
            if not info:
                return
            self._last, self._undo_armed = None, False
            self._inject(len(info["exp"]) + len(info["trig"]), info["orig"] + info["trig"])

    # ── rules ──────────────────────────────────────────────────────────
    def is_blocked(self) -> bool:
        try:
            title = (self.window_title() or "").lower()
        except Exception:
            title = ""
        if title.startswith(APP_NAME.lower()) and not self.allow_own_window:
            return True  # never expand inside SnapType's own editor fields
        if self.cfg.get("skip_sensitive_windows") and any(h in title for h in SENSITIVE_HINTS):
            return True
        mode = self.cfg.get("app_mode") or "all"
        apps = self.cfg.get("app_list") or []
        if mode == "all" or not apps:
            return False
        match = any(a.lower() in title for a in apps)
        return (not match) if mode == "include" else match
