"""Settings: shortcuts, behaviour and data, as grouped rows."""
from __future__ import annotations

import tkinter as tk

from snapcore import hotkeys, startup, winutil
from snapcore.config import DEFAULTS

from .. import dialogs
from .. import theme as T
from ..theme import dp
from ..widgets import Button, Card, Keycaps, Slider, Stepper, Toggle, label
from . import Page
from .common import setting_row

SNOOZE_STEPS = (1, 2, 5, 10, 15, 30, 45, 60, 90, 120, 180, 240)


class HotkeyRow(tk.Frame):
    """Keycaps plus a Change button. Change listens for the next key combination, validates it
    (needs Ctrl/Alt/Win so it can't fire while typing) and saves it straight away."""

    def __init__(self, parent, app, key: str, other_key: str, bg: str):
        super().__init__(parent, bg=bg)
        self.app, self.key, self.other_key, self._bg = app, key, other_key, bg
        self.recording = False
        line = tk.Frame(self, bg=bg)
        line.pack(anchor="e")
        self.caps = Keycaps(line, hotkeys.pretty(app.cfg.get(key)), bg)
        self.caps.pack(side="left", padx=(0, dp(10)))
        self.btn = Button(line, text="Change", variant="secondary", size="sm", bg=bg, command=self.start)
        self.btn.pack(side="left")
        self.msg = label(self, "", "small", T.TEXT_FAINT, bg, anchor="e", wraplength=dp(280), justify="right")
        self.sink = tk.Frame(self, width=1, height=1, bg=bg, takefocus=1, bd=0, highlightthickness=0)

    def show(self):
        self.caps.set(hotkeys.pretty(self.app.cfg.get(self.key)))

    def _say(self, text, color=T.TEXT_FAINT):
        self.msg.configure(text=text, fg=color)
        if text:
            self.msg.pack(anchor="e", pady=(dp(6), 0))
        else:
            self.msg.pack_forget()

    def start(self):
        if self.recording:
            self.stop()
            return
        self.recording = True
        self.sink.place(x=0, y=0)
        self.sink.bind("<KeyPress>", self._key, add="+")
        self.sink.bind("<FocusOut>", lambda e: self.stop(), add="+")
        self.sink.focus_set()
        self.btn.update_button(text="Press keys\u2026", variant="primary")
        self._say("Press the new shortcut, or Esc to cancel.")

    def stop(self, message=""):
        self.recording = False
        self.sink.place_forget()
        self.btn.update_button(text="Change", variant="secondary")
        self._say(message)

    def _key(self, e):
        combo = hotkeys.from_tk_event(e.keysym, e.state)
        if combo is None:
            return "break"                       # only modifiers so far
        if combo == "esc":
            self.stop()
            return "break"
        try:
            combo = hotkeys.normalize(combo)
        except ValueError as exc:
            self._say(str(exc), T.AMBER)
            return "break"
        if combo == self.app.cfg.get(self.other_key):
            self._say("That shortcut is already used by the other action.", T.AMBER)
            return "break"
        parse = getattr(self.app._kb, "parse_hotkey", None)
        try:
            if parse:
                parse(combo)
        except Exception:  # noqa: BLE001  (the keyboard library raises assorted types)
            self._say("This keyboard can't register that combination. Try another.", T.AMBER)
            return "break"
        self.app.cfg.set(self.key, combo)
        self.app.engine.reregister()
        self.show()
        self.stop()
        self.app.toast("Shortcut saved", "success")
        return "break"


class SettingsPage(Page):
    def build(self):
        a, col = self.app, self.col
        self._toggles = {}

        gen = Card(col, "General", "gear")
        gen.pack(fill="x")
        self._toggle(gen, "Launch at Windows login", "Starts SnapType quietly in the tray when you sign in.",
                     "startup_enabled", self._set_startup, first=True)
        self._toggle(gen, "Start expanding when SnapType opens",
                     "Turn off if you want to press Start yourself each time.", "auto_start")
        self._toggle(gen, "Desktop notifications", "Show a notification when expansion is paused, resumed or snoozed.",
                     "notify_enabled")
        quit_row = setting_row(gen, "Quit SnapType", "Stops expansion and closes the app completely.")
        Button(quit_row, text="Quit", icon="power", variant="danger", size="sm", bg=gen.fill,
               command=a.quit).pack()

        exp = Card(col, "Expansion", "bolt")
        exp.pack(fill="x", pady=(dp(16), 0))
        self._toggle(exp, "Undo with Backspace", "Press Backspace right after an expansion to get your abbreviation back.",
                     "undo_on_backspace", first=True)
        self._toggle(exp, "Skip password and sign-in windows",
                     "Never expand in windows whose title mentions passwords, sign-in or banking.",
                     "skip_sensitive_windows")
        right = setting_row(exp, "Typing speed", "Raise the delay if characters get dropped or scrambled, for "
                                                 "example in remote desktop or slow apps.")
        ms = int(round(a.cfg.get("replace_delay") * 1000))
        self.delay_var = tk.IntVar(value=ms)
        self.delay_lbl = label(right, f"{ms} ms", "mono_b", T.TEXT, exp.fill, width=6, anchor="e")
        self.delay_lbl.pack(side="right")
        Slider(right, self.delay_var, 0, max(30, ms), width=190, bg=exp.fill, command=self._set_delay).pack(side="right")

        keys = Card(col, "Shortcuts", "keyboard")
        keys.pack(fill="x", pady=(dp(16), 0))
        r1 = setting_row(keys, "Start or stop SnapType", "Works from any app.", first=True)
        self.hk_toggle = HotkeyRow(r1, a, "toggle_hotkey", "undo_hotkey", keys.fill)
        self.hk_toggle.pack()
        r2 = setting_row(keys, "Undo last expansion", "Brings back what you typed before it expanded.")
        self.hk_undo = HotkeyRow(r2, a, "undo_hotkey", "toggle_hotkey", keys.fill)
        self.hk_undo.pack()
        r3 = setting_row(keys, "Snooze length", "How long Snooze pauses expansion before resuming by itself.")
        self.snooze_var = tk.IntVar(value=int(a.cfg.get("snooze_minutes")))
        Stepper(r3, self.snooze_var, SNOOZE_STEPS, "{} min", command=lambda v: a.cfg.set("snooze_minutes", int(v))).pack()
        r4 = setting_row(keys, "Restore default shortcuts")
        Button(r4, text="Restore defaults", variant="ghost", size="sm", bg=keys.fill, command=self._reset_keys).pack()

        data = Card(col, "Your data", "folder")
        data.pack(fill="x", pady=(dp(16), dp(8)))
        label(data.content, "Everything SnapType stores lives in this folder on your PC and nowhere else.", "small",
              T.TEXT_DIM, data.fill, wraplength=dp(560), justify="left").pack(anchor="w")
        path = tk.Frame(data.content, bg=T.INPUT, highlightthickness=1, highlightbackground=T.BORDER)
        path.pack(fill="x", pady=(dp(10), dp(12)))
        label(path, str(a.data_dir), "mono_s", T.TEXT, T.INPUT, wraplength=dp(560), justify="left").pack(
            anchor="w", padx=dp(10), pady=dp(8))
        btns = tk.Frame(data.content, bg=data.fill)
        btns.pack(fill="x")
        Button(btns, text="Open folder", icon="folder", variant="secondary", size="sm", bg=data.fill,
               command=lambda: self._open(a.data_dir)).pack(side="left")
        Button(btns, text="Open log", icon="external", variant="secondary", size="sm", bg=data.fill,
               command=lambda: self._open(a.data_dir / "snaptype.log")).pack(side="left", padx=dp(8))
        Button(btns, text="Reset statistics", icon="trash", variant="danger", size="sm", bg=data.fill,
               command=self._reset_stats).pack(side="right")

    # ═══ rows ═════════════════════════════════════════════════════════════
    def _toggle(self, card, title, desc, key, on_change=None, first=False):
        right = setting_row(card, title, desc, first=first)
        var = tk.BooleanVar(value=bool(self.app.cfg.get(key)))
        t = Toggle(right, var, bg=card.fill)

        def changed():
            if on_change and not on_change(var.get()):
                var.set(not var.get())
                t.sync()
                return
            self.app.cfg.set(key, var.get())

        t.command = changed
        t.pack()
        for w in right.left.winfo_children():
            w.bind("<ButtonRelease-1>", lambda e: t.toggle(), add="+")
        self._toggles[key] = (var, t)

    def _set_startup(self, on: bool) -> bool:
        try:
            startup.set_enabled(on)
        except OSError as exc:
            self.app.toast(f"Windows wouldn't change the startup setting ({exc.strerror or exc}).", "error")
            return False
        return True

    def _set_delay(self, ms):
        self.app.cfg.set("replace_delay", ms / 1000)
        self.delay_lbl.configure(text=f"{ms} ms")

    def _reset_keys(self):
        for k in ("toggle_hotkey", "undo_hotkey"):
            self.app.cfg.set(k, DEFAULTS[k])
        self.app.engine.reregister()
        self.hk_toggle.show()
        self.hk_undo.show()
        self.app.toast("Shortcuts restored to their defaults", "success")

    def _open(self, path):
        if not winutil.open_path(path):
            self.app.toast("Couldn't open that. It may not exist yet.", "warn")

    def _reset_stats(self):
        if dialogs.confirm(self.app.root, "Reset statistics?",
                           "This clears every expansion count and the daily history. It can't be undone.",
                           ok="Reset statistics", danger=True):
            self.app.stats.reset()
            self.app.refresh_pages()
            self.app.toast("Statistics reset", "info")

    def on_hide(self):
        for row in (self.hk_toggle, self.hk_undo):
            if row.recording:
                row.stop()
