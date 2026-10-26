"""SnapType's main window: shell, state machine, tray and lifecycle.

Threading rule: Tk is single-threaded. The keyboard hook, the tray and timers run on other
threads, so they only ever call ``self._post(fn)``; the Tk thread runs the queue.
"""
from __future__ import annotations

import collections
import logging
import queue
import threading
import time
import tkinter as tk
from pathlib import Path

from PIL import ImageTk

from snapcore import APP_NAME, VERSION, hotkeys, startup, winutil
from snapcore.config import Config
from snapcore.engine import Engine, RealKeyboard
from snapcore.paths import DATA_DIR
from snapcore.snippets import SnippetManager
from snapcore.stats import Stats, estimate_minutes_saved
from snapcore.winutil import WindowTracker, foreground_title, read_clipboard

from . import dialogs, icons
from . import theme as T
from .theme import dp
from .widgets import Button, Pill, ToastHost, Tooltip, icon_photo, install_wheel_router, label, style_ttk

log = logging.getLogger("snaptype.ui")

PAGES = (  # name, icon, subtitle
    ("Dashboard", "dashboard", "Your snippets at a glance"),
    ("Snippets", "bolt", "Abbreviations and the phrases they expand to"),
    ("Stats", "chart", "How much typing SnapType has saved you"),
    ("App Rules", "shield", "Choose where SnapType is allowed to expand"),
    ("Settings", "gear", "Shortcuts, behaviour and data"),
    ("About", "info", f"SnapType {VERSION}"),
)


class NavItem(tk.Frame):
    """Sidebar row: 4px active-indicator bar, icon, label. One focusable frame, so Tab shows
    Tk's own focus ring and the whole row is clickable."""

    def __init__(self, parent, icon: str, text: str, command):
        super().__init__(parent, bg=T.SURFACE, takefocus=1, bd=0, highlightthickness=dp(2),
                         highlightbackground=T.SURFACE, highlightcolor=T.CYAN, cursor="hand2")
        self.icon_name, self.text_value, self.command = icon, text, command
        self.active = self.hover = self.collapsed = False
        self.ind = tk.Frame(self, bg=T.SURFACE, width=dp(4), bd=0, highlightthickness=0)
        self.ind.pack(side="left", fill="y", pady=dp(9))
        self.icon = tk.Label(self, bd=0, highlightthickness=0, bg=T.SURFACE)
        self.text = tk.Label(self, text=text, anchor="w", bd=0, highlightthickness=0, bg=T.SURFACE)
        self._tip = Tooltip(self, lambda: self.text_value if self.collapsed else "", delay=250)
        for w in (self, self.ind, self.icon, self.text):
            w.bind("<Enter>", lambda e: self._set("hover", True), add="+")
            w.bind("<Leave>", lambda e: self._set("hover", False), add="+")
            w.bind("<ButtonRelease-1>", lambda e: self.command(), add="+")
        self.bind("<Return>", lambda e: self.command(), add="+")
        self.bind("<space>", lambda e: self.command(), add="+")
        self.set_collapsed(False)

    def _set(self, name, value):
        setattr(self, name, value)
        self._paint()

    def set_active(self, on: bool):
        self._set("active", on)

    def set_collapsed(self, collapsed: bool):
        self.collapsed = collapsed
        self.icon.pack_forget()
        self.text.pack_forget()
        if collapsed:
            self.icon.pack(side="left", expand=True, pady=dp(11))
        else:
            self.icon.pack(side="left", padx=(dp(14), dp(12)), pady=dp(11))
            self.text.pack(side="left", fill="x", expand=True)
        self._paint()

    def _paint(self):
        bg = T.CYAN_TINT if self.active else (T.PANEL_HOVER if self.hover else T.SURFACE)
        fg = T.CYAN if self.active else (T.TEXT if self.hover else T.TEXT_DIM)
        self.configure(bg=bg, highlightbackground=bg)
        self.ind.configure(bg=T.CYAN if self.active else bg)
        self.text.configure(bg=bg, fg=fg, font=T.font("body_b" if self.active else "body"))
        ph = icon_photo(self.icon_name, dp(20), fg)
        self.icon.configure(image=ph, bg=bg)
        self.icon.image = ph


class SnapTypeApp:
    def __init__(self, *, data_dir: Path | None = None, keyboard_backend=None, enable_tray: bool = True,
                 start_hidden: bool = False):
        d = Path(data_dir) if data_dir else DATA_DIR
        self.data_dir = d
        self.cfg = Config(d / "config.json")
        self.sm = SnippetManager(d / "snippets.json")
        self.stats = Stats(d / "stats.json")
        self.tracker = WindowTracker(APP_NAME)
        self._ui_queue: queue.Queue = queue.Queue()
        self._kb = keyboard_backend or RealKeyboard()
        self.engine = Engine(self.sm, self.cfg, self.stats, self._kb, window_title=foreground_title,
                             clipboard=read_clipboard, on_fire=self._on_fire)
        self.state = "off"                  # "off" | "on" | "snoozed"
        self.snooze_until = 0.0
        self.activity: collections.deque = collections.deque(maxlen=60)
        self.pages: dict = {}
        self.current = ""
        self.icon = None
        self.tray_ok = False
        self._quitting = False
        self._last_error_toast = 0.0
        self._layout_job = None
        self._tick_job = None

        self.root = tk.Tk()
        if start_hidden:
            self.root.withdraw()
        T.init(self.root)
        self.root.report_callback_exception = self._on_callback_error
        self.root.title(f"{APP_NAME}  v{VERSION}")
        self.root.configure(bg=T.VOID)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._place_window()
        self._win_icons = [ImageTk.PhotoImage(icons.make_logo(s)) for s in (256, 64)]
        try:
            self.root.iconphoto(True, *self._win_icons)
        except tk.TclError:
            log.debug("iconphoto failed", exc_info=True)

        style_ttk(self.root)
        install_wheel_router(self.root)
        self._build_shell()
        self.toasts = ToastHost(self.main)
        self._bind_shortcuts()
        self.engine.setup(toggle_fn=lambda: self._post(self.toggle))   # hotkey runs on the keyboard thread
        self._render_state()
        self.navigate("Dashboard")
        winutil.set_titlebar_theme(self.root.winfo_id(), True, T.SURFACE, T.TEXT)
        self.root.after(50, self._drain)
        self.root.after(80, self._apply_layout)
        self.root.after(120, self._first_run)
        if enable_tray:
            self._start_tray()

    # ═══ threading ════════════════════════════════════════════════════════
    def _post(self, fn):
        self._ui_queue.put(fn)

    def _drain(self):
        while True:
            try:
                fn = self._ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except Exception:  # noqa: BLE001  (one failing task must not drop the rest)
                log.exception("UI task failed")
        if not self._quitting:
            self.root.after(50, self._drain)

    def _on_callback_error(self, exc, val, tb):
        log.error("Unhandled error in a Tk callback", exc_info=(exc, val, tb))
        now = time.monotonic()
        if now - self._last_error_toast > 10:
            self._last_error_toast = now
            self.toast("Something went wrong. The details are in the log (Settings, Data).", "error")

    # ═══ window ═══════════════════════════════════════════════════════════
    def _place_window(self):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w, h = min(dp(1180), sw - dp(80)), min(dp(780), sh - dp(100))
        self.root.geometry(f"{w}x{h}+{max((sw - w) // 2, 0)}+{max((sh - h) // 3, 0)}")
        self.root.minsize(min(dp(900), w), min(dp(620), h))

    def show_window(self):
        self.root.deiconify()
        self.root.state("normal")
        self.root.lift()
        self.root.attributes("-topmost", True)            # Windows otherwise may keep it behind
        self.root.after(150, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()
        winutil.set_titlebar_theme(self.root.winfo_id(), True, T.SURFACE, T.TEXT)

    def _on_close(self):
        self.engine.allow_own_window = False
        if not self.tray_ok:                              # nowhere to hide: closing means quitting
            self.quit()
            return
        if not self.cfg.get("tray_hint_shown"):
            choice = dialogs.close_choice(self.root)
            self.cfg.set("tray_hint_shown", True)
            if choice == "quit":
                self.quit()
                return
        self.root.withdraw()

    def quit(self):
        """Stop hooks, persist everything, close. Always runs on the Tk thread."""
        if self._quitting:
            return
        self._quitting = True
        for step in (self.tracker.stop, self.engine.shutdown, self.stats.flush, self.cfg.flush, self.sm.flush):
            try:
                step()
            except Exception:  # noqa: BLE001
                log.exception("Shutdown step failed")
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:  # noqa: BLE001
                log.debug("tray stop failed", exc_info=True)
        self.root.destroy()

    def run(self):
        log.info("%s v%s started; data dir %s", APP_NAME, VERSION, self.data_dir)
        self.root.mainloop()

    # ═══ first run & startup ══════════════════════════════════════════════
    def _first_run(self):
        if getattr(self, "_first_run_started", False):
            return
        self._first_run_started = True
        if not self.cfg.get("consent_given"):
            if not self.root.winfo_viewable():
                self.show_window()
            if not dialogs.welcome(self.root):
                self.quit()
                return
            self.cfg.set("consent_given", True)
        self.tracker.start()
        if self.cfg.get("startup_enabled"):
            startup.refresh()
        if self.cfg.get("auto_start"):
            self.toggle(announce=False)

    # ═══ shell ════════════════════════════════════════════════════════════
    def _build_shell(self):
        self.collapsed = False
        self.sidebar = tk.Frame(self.root, bg=T.SURFACE, width=dp(T.SIDEBAR_WIDE), bd=0, highlightthickness=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Frame(self.root, bg=T.DIVIDER, width=1).pack(side="left", fill="y")

        brand = tk.Frame(self.sidebar, bg=T.SURFACE)
        brand.pack(fill="x", padx=dp(18), pady=(dp(26), dp(22)))
        self._logo_ph = ImageTk.PhotoImage(icons.make_logo(dp(40)))
        self._logo = tk.Label(brand, image=self._logo_ph, bg=T.SURFACE, bd=0)
        self._logo.pack(side="left")
        self._wordmark = tk.Frame(brand, bg=T.SURFACE)
        self._wordmark.pack(side="left", padx=(dp(12), 0))
        label(self._wordmark, "Snap", "title", T.CYAN, T.SURFACE).pack(side="left")
        label(self._wordmark, "Type", "title", T.AMETHYST, T.SURFACE).pack(side="left")

        self.nav = {}
        nav_box = tk.Frame(self.sidebar, bg=T.SURFACE)
        nav_box.pack(fill="x", padx=dp(12))
        for name, icon, _ in PAGES:
            item = NavItem(nav_box, icon, name, lambda n=name: self.navigate(n))
            item.pack(fill="x", pady=dp(2))
            self.nav[name] = item

        foot = tk.Frame(self.sidebar, bg=T.SURFACE)
        foot.pack(side="bottom", fill="x", padx=dp(14), pady=(0, dp(14)))
        self._version = label(foot, f"v{VERSION}", "small", T.TEXT_FAINT, T.SURFACE)
        self._version.pack(side="left", padx=(dp(4), 0))
        self._collapse_btn = Button(foot, icon="chevron_left", variant="quiet", size="sm", bg=T.SURFACE,
                                    tooltip="Collapse sidebar", command=self._toggle_sidebar)
        self._collapse_btn.pack(side="right")

        self.main = tk.Frame(self.root, bg=T.VOID, bd=0, highlightthickness=0)
        self.main.pack(side="left", fill="both", expand=True)

        head = tk.Frame(self.main, bg=T.VOID)
        head.pack(fill="x", padx=dp(32), pady=(dp(26), dp(6)))
        titles = tk.Frame(head, bg=T.VOID)
        titles.pack(side="left", fill="x", expand=True)
        self._title = label(titles, "", "title", T.TEXT, T.VOID)
        self._title.pack(anchor="w")
        self._subtitle = label(titles, "", "body", T.TEXT_DIM, T.VOID)
        self._subtitle.pack(anchor="w")
        controls = tk.Frame(head, bg=T.VOID)
        controls.pack(side="right")
        self.pill = Pill(controls, "Paused", fg=T.TEXT_DIM, fill=T.PANEL, dot=T.TEXT_FAINT, bg=T.VOID)
        self.pill.pack(side="left", padx=(0, dp(8)))
        self.snooze_btn = Button(controls, text="Snooze", icon="moon", variant="secondary", bg=T.VOID,
                                 command=self.snooze,
                                 tooltip=lambda: f"Pause expansion for {self.cfg.get('snooze_minutes')} min")
        self.snooze_btn.pack(side="left")
        self.main_btn = Button(controls, text="Start", icon="play", variant="primary", bg=T.VOID, min_width=96,
                               command=self.toggle,
                               tooltip=lambda: f"Shortcut: {' + '.join(hotkeys.pretty(self.cfg.get('toggle_hotkey')))}")
        self.main_btn.pack(side="left")

        foot_bar = tk.Frame(self.main, bg=T.VOID)
        foot_bar.pack(side="bottom", fill="x", padx=dp(32), pady=(0, dp(10)))
        self._foot_left = label(foot_bar, "", "small", T.TEXT_FAINT, T.VOID)
        self._foot_left.pack(side="left")
        self._foot_right = label(foot_bar, "", "small", T.TEXT_FAINT, T.VOID, anchor="e")
        self._foot_right.pack(side="right")

        self.container = tk.Frame(self.main, bg=T.VOID)
        self.container.pack(fill="both", expand=True, padx=dp(32), pady=(dp(14), dp(8)))
        self.root.bind("<Configure>", self._on_root_configure, add="+")

    # -- responsive sidebar --
    def _on_root_configure(self, e):
        if e.widget is not self.root:
            return
        if self._layout_job is not None:
            self.root.after_cancel(self._layout_job)
        self._layout_job = self.root.after(80, self._apply_layout)

    def _apply_layout(self):
        self._layout_job = None
        compact = self.root.winfo_width() < dp(T.COMPACT_BELOW)
        self._set_sidebar(compact or bool(self.cfg.get("sidebar_collapsed")))

    def _toggle_sidebar(self):
        self.cfg.set("sidebar_collapsed", not self.cfg.get("sidebar_collapsed"))
        self._apply_layout()

    def _set_sidebar(self, collapsed: bool):
        if collapsed == self.collapsed and self.sidebar.winfo_width() > 1:
            return
        self.collapsed = collapsed
        self.sidebar.configure(width=dp(T.SIDEBAR_NARROW if collapsed else T.SIDEBAR_WIDE))
        if collapsed:
            self._wordmark.pack_forget()
            self._version.pack_forget()
        else:
            self._wordmark.pack(side="left", padx=(dp(12), 0))
            self._version.pack(side="left", padx=(dp(4), 0))
        for item in self.nav.values():
            item.set_collapsed(collapsed)
        self._collapse_btn.update_button(icon="chevron_right" if collapsed else "chevron_left")
        self._collapse_btn.pack_forget()
        self._collapse_btn.pack(side="top" if collapsed else "right")

    # -- navigation --
    def navigate(self, name: str):
        from . import pages
        if name == self.current and name in self.pages:
            self.pages[name].on_show()
            return
        if self.current in self.pages:
            self.pages[self.current].pack_forget()
            self.pages[self.current].on_hide()
        if name not in self.pages:
            self.pages[name] = pages.build(name, self.container, self)
        self.current = name
        sub = next(s for n, _, s in PAGES if n == name)
        self._title.configure(text=name)
        self._subtitle.configure(text=sub)
        for n, item in self.nav.items():
            item.set_active(n == name)
        self.pages[name].pack(fill="both", expand=True)
        self.pages[name].on_show()

    def refresh_pages(self):
        """Data changed somewhere: refresh footer and whichever pages are built."""
        self._render_footer()
        for page in self.pages.values():
            page.refresh()

    def _bind_shortcuts(self):
        for i, (name, _, _) in enumerate(PAGES, 1):
            self.root.bind(f"<Control-Key-{i}>", lambda e, n=name: self.navigate(n))
        self.root.bind("<Control-Key-f>", lambda e: self.pages[self.current].on_find())
        self.root.bind("<Control-Key-n>", lambda e: self.pages[self.current].on_new())
        self.root.bind("<Control-Key-q>", lambda e: self.quit())

    # ═══ state ════════════════════════════════════════════════════════════
    def toggle(self, announce: bool = True):
        if self.state == "on":
            self.engine.stop()
            self._set_state("off")
            if announce:
                self._notify("SnapType paused", "Expansion is off.")
        else:                                              # off, or Resume from a snooze
            self.engine.start()                           # also cancels any pending snooze timer
            self._set_state("on")
            if announce:
                self._notify("SnapType active", "Expansion is on.")

    def snooze(self):
        if self.state != "on":
            return
        minutes = int(self.cfg.get("snooze_minutes") or 5)
        self.snooze_until = time.monotonic() + minutes * 60
        self.engine.snooze(minutes, on_wake=lambda: self._post(self._on_wake))
        self._set_state("snoozed")
        self._notify("SnapType snoozed", f"Paused for {minutes} min. It resumes automatically.")
        self.toast(f"Snoozed for {minutes} minutes", "info", action=("Resume now", self.toggle))

    def _on_wake(self):
        if self.state == "snoozed":
            self._set_state("on")
            self._notify("SnapType resumed", "Snooze ended. Expansion is on again.")

    def _set_state(self, state: str):
        self.state = state
        self._render_state()

    def _render_state(self):
        s = self.state
        if s == "on":
            self.pill.set("Active", T.CYAN, T.blend(T.CYAN, 0.10, T.VOID), T.blend(T.CYAN, 0.45, T.VOID), T.CYAN)
            self.main_btn.update_button(text="Stop", icon="pause", variant="secondary")
        elif s == "snoozed":
            self._tick()
            self.main_btn.update_button(text="Resume", icon="play", variant="primary")
        else:
            self.pill.set("Paused", T.TEXT_DIM, T.PANEL, T.BORDER, T.TEXT_FAINT)
            self.main_btn.update_button(text="Start", icon="play", variant="primary")
        self.snooze_btn.update_button(state="normal" if s == "on" else "disabled")
        if s != "snoozed" and self._tick_job is not None:
            self.root.after_cancel(self._tick_job)
            self._tick_job = None
        self._update_tray()
        self.refresh_pages()

    def _tick(self):
        """Live countdown in the status pill while snoozed."""
        if self._tick_job is not None:
            self.root.after_cancel(self._tick_job)
            self._tick_job = None
        if self.state != "snoozed":
            return
        left = max(int(self.snooze_until - time.monotonic()), 0)
        self.pill.set(f"Snoozed {left // 60}:{left % 60:02d}", T.AMETHYST, T.blend(T.AMETHYST, 0.10, T.VOID),
                      T.blend(T.AMETHYST, 0.45, T.VOID), T.AMETHYST)
        self._tick_job = self.root.after(1000, self._tick)

    def _render_footer(self):
        n = len(self.sm.snippets)
        self._foot_left.configure(text=f"{n} snippet{'s' if n != 1 else ''}")
        self._foot_right.configure(text=f"{self.stats.total():,} expansions in total")

    # ═══ data helpers used by pages ═══════════════════════════════════════
    def minutes_saved(self) -> float:
        return estimate_minutes_saved(self.stats.top(100000), self.sm.snippets)

    def toast(self, message: str, kind: str = "info", action=None):
        self.toasts.show(message, kind, action)

    def _on_fire(self, abbr: str, expansion: str):
        """Runs on the engine's timer thread."""
        self._post(lambda: self._record_activity(abbr, expansion))

    def _record_activity(self, abbr: str, expansion: str):
        self.activity.appendleft({"t": time.strftime("%H:%M:%S"), "abbr": abbr, "exp": expansion})
        self.refresh_pages()

    # ═══ tray ═════════════════════════════════════════════════════════════
    def _notify(self, title: str, message: str):
        if self.icon is None or not self.cfg.get("notify_enabled"):
            return
        try:
            self.icon.notify(message, title)
        except Exception:  # noqa: BLE001  (not every desktop supports balloons)
            log.debug("notify failed", exc_info=True)

    def _start_tray(self):
        try:
            import pystray
            menu = pystray.Menu(
                pystray.MenuItem("Open SnapType", lambda *_: self._post(self.show_window), default=True),
                pystray.MenuItem(lambda item: "Pause expansion" if self.state == "on" else
                                 ("Resume expansion" if self.state == "snoozed" else "Start expansion"),
                                 lambda *_: self._post(self.toggle)),
                pystray.MenuItem(lambda item: f"Snooze for {self.cfg.get('snooze_minutes')} min",
                                 lambda *_: self._post(self.snooze), enabled=lambda item: self.state == "on"),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit SnapType", lambda *_: self._post(self.quit)))
            self.icon = pystray.Icon(APP_NAME, icons.make_tray_icon("off"), title=APP_NAME, menu=menu)
            threading.Thread(target=self.icon.run, name="tray", daemon=True).start()
            self.tray_ok = True
        except Exception:  # noqa: BLE001
            log.exception("System tray unavailable; closing the window will quit instead")
            self.icon, self.tray_ok = None, False

    def _update_tray(self):
        if self.icon is None:
            return
        try:
            self.icon.icon = icons.make_tray_icon({"on": "on", "snoozed": "snoozed"}.get(self.state, "off"))
            self.icon.title = f"{APP_NAME}: {({'on': 'active', 'snoozed': 'snoozed'}).get(self.state, 'paused')}"
            self.icon.update_menu()
        except Exception:  # noqa: BLE001
            log.debug("tray update failed", exc_info=True)
