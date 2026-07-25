#!/usr/bin/env python3
"""
SnapType v1.1.0  —  Lightning-fast Typing Assistant
Type short abbreviations, get full phrases instantly.

Author: Abdul Rehman  |  2026
"""

# DPI — must run BEFORE any tkinter call
import sys as _sys

if _sys.platform == "win32":
    try:
        import ctypes as _ct

        _ct.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes as _ct

            _ct.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

import base64, collections, io, json, os, re, subprocess, sys
import threading, time, tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog, simpledialog

_missing = []
try:
    import keyboard
except:
    _missing.append("keyboard")
try:
    import pystray; from PIL import Image, ImageDraw, ImageFont
except:
    _missing.append("pystray Pillow")

if _missing:
    _r = tk.Tk();
    _r.withdraw()
    messagebox.showerror("SnapType — Missing packages",
                         f"Please run:\n\n    pip install {' '.join(_missing)}\n\nThen restart.")
    sys.exit(1)

# ════════════════════════════════════════════════════════════════════════════
#  Constants
# ════════════════════════════════════════════════════════════════════════════

APP_NAME = "SnapType"
VERSION = "1.1.0"
DATA_DIR = Path.home() / ".snaptype"
CONFIG_FILE = DATA_DIR / "config.json"
SNIPPETS_FILE = DATA_DIR / "snippets.json"
STATS_FILE = DATA_DIR / "stats.json"

_TRIGGERS = {"space", "enter", "tab", ".", "!", "?", ",", ";", ":", ")", "]", "}", "-"}

DEFAULT_SNIPPETS: dict[str, str] = {
    # Greetings
    "gm": "good morning",
    "gn": "good night",
    "wb": "welcome back",
    "hru": "how are you",
    "wyd": "what are you doing",
    "wya": "where are you",
    "wbu": "what about you",
    # Affection
    "ily": "i love you",
    "ily2": "i love you too",
    "imy": "i miss you",
    # Gratitude
    "ty": "thank you",
    "tysm": "thank you so much",
    "yw": "you're welcome",
    "np": "no problem",
    "nw": "no worries",
    "thx": "thanks",
    "ofc": "of course",
    "sry": "sorry",
    # Status
    "omw": "on my way",
    "otw": "on the way",
    "brb": "be right back",
    "bbl": "be back later",
    "bbs": "be back soon",
    "afk": "away from keyboard",
    "gtg": "got to go",
    "ttyl": "talk to you later",
    "ttys": "talk to you soon",
    "nvm": "never mind",
    "lmk": "let me know",
    "hmu": "hit me up",
    # Opinion / reaction
    "ngl": "not gonna lie",
    "tbh": "to be honest",
    "imo": "in my opinion",
    "imho": "in my humble opinion",
    "ikr": "i know right",
    "fr": "for real",
    "istg": "i swear to god",
    "smh": "shaking my head",
    "tbf": "to be fair",
    "idk": "i don't know",
    # Info
    "fyi": "for your information",
    "asap": "as soon as possible",
    "rn": "right now",
    "atm": "at the moment",
    "obv": "obviously",
    "probs": "probably",
    "def": "definitely",
    "irl": "in real life",
    "afaik": "as far as i know",
    "iirc": "if i recall correctly",
    # Casual
    "gonna": "going to",
    "wanna": "want to",
    "gotta": "got to",
    "kinda": "kind of",
    "sorta": "sort of",
    "lemme": "let me",
    "gimme": "give me",
    "bc": "because",
    "tho": "though",
    "plz": "please",
    "pls": "please",
    "omg": "oh my god",
    "lol": "laughing out loud",
    "jk": "just kidding",
}

# Enhanced modern color palette - Catppuccin Mocha with more depth
BG = "#1e1e2e"
SURFACE = "#181825"
CARD = "#313244"
OVERLAY = "#45475a"
TEXT = "#cdd6f4"
SUBTEXT = "#a6adc8"
ACCENT = "#cba6f7"
GREEN = "#a6e3a1"
RED = "#f38ba8"
YELLOW = "#f9e2af"
BLUE = "#89b4fa"
ORANGE = "#fab387"
TEAL = "#94e2d5"
PINK = "#f5c2e7"
CYAN = "#00d4ff"
PURPLE = "#b06ef3"
GOLD = "#f9e2af"
MAUVE = "#cba6f7"
PEACH = "#fab387"
SAPPHIRE = "#74c7ec"
ROSEWATER = "#f5e0dc"
LAVENDER = "#b4befe"
MAROON = "#eba0ac"

# Modern gradients and shadows
SHADOW = "#0f0f17"
HIGHLIGHT = "#45475a"

NAV_ITEMS = [
    ("🏠", "Dashboard"),
    ("⚡", "Snippets"),
    ("📊", "Stats"),
    ("🛡️", "App Rules"),
    ("⚙️", "Settings"),
    ("ℹ️", "About"),
]

POPULAR_APPS = [
    ("Chrome", "Chrome"), ("Firefox", "Firefox"), ("Edge", "Edge"),
    ("WhatsApp", "WhatsApp"), ("Discord", "Discord"), ("Telegram", "Telegram"),
    ("Slack", "Slack"), ("Teams", "Microsoft Teams"), ("VS Code", "Visual Studio Code"),
    ("Word", "Microsoft Word"), ("Notepad", "Notepad"), ("Zoom", "Zoom"),
    ("Skype", "Skype"), ("Signal", "Signal"), ("Outlook", "Outlook"),
]

AUTHOR = {
    "linkedin": "www.linkedin.com/in/arehman-builds",
    "instagram": "rehmanoncloud9",
    "email": "relentlessrehman@gmail.com",
}


# ════════════════════════════════════════════════════════════════════════════
#  Data helpers (unchanged)
# ════════════════════════════════════════════════════════════════════════════

def _load_json(path, default):
    try:
        if path.exists():
            with open(path, encoding="utf-8") as f: return json.load(f)
    except:
        pass
    return default


def _save_json(path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except:
        pass


# ════════════════════════════════════════════════════════════════════════════
#  Config (unchanged)
# ════════════════════════════════════════════════════════════════════════════

class Config:
    _D = {
        "toggle_hotkey": "ctrl+shift+s",
        "undo_hotkey": "ctrl+z",
        "replace_delay": 0.006,
        "snooze_minutes": 5,
        "app_mode": "all",
        "app_list": [],
        "notify_enabled": True,
        "startup_enabled": False,
    }

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        raw = _load_json(CONFIG_FILE, {})
        self._d = {**self._D, **(raw if isinstance(raw, dict) else {})}
        self._save()

    def get(self, k): return self._d.get(k, self._D.get(k))

    def set(self, k, v): self._d[k] = v; self._save()

    def _save(self): _save_json(CONFIG_FILE, self._d)


# ════════════════════════════════════════════════════════════════════════════
#  Snippet Manager (unchanged)
# ════════════════════════════════════════════════════════════════════════════

class SnippetManager:
    def __init__(self):
        self.enabled = True
        raw = _load_json(SNIPPETS_FILE, None)
        if isinstance(raw, dict) and raw:
            self.snippets = raw
        else:
            self.snippets = dict(DEFAULT_SNIPPETS)
            self._save()

    def get(self, abbr: str):
        if not self.enabled: return None
        return self.snippets.get(abbr.lower())

    def upsert(self, abbr: str, expansion: str) -> bool:
        a, e = abbr.strip().lower(), expansion.strip()
        if not a or not e: return False
        self.snippets[a] = e;
        self._save();
        return True

    def delete(self, abbr: str) -> bool:
        k = abbr.strip().lower()
        if k not in self.snippets: return False
        del self.snippets[k];
        self._save();
        return True

    def export_csv(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            f.write("abbreviation,expansion\n")
            for k, v in sorted(self.snippets.items()):
                f.write(f"{k},{v}\n")

    def import_csv(self, path: str) -> int:
        n = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                pts = line.strip().split(",", 1)
                if len(pts) == 2 and pts[0] not in ("abbreviation", "abbr", ""):
                    if self.upsert(pts[0], pts[1]): n += 1
        return n

    def _save(self):
        _save_json(SNIPPETS_FILE, self.snippets)


# ════════════════════════════════════════════════════════════════════════════
#  Stats (unchanged)
# ════════════════════════════════════════════════════════════════════════════

class Stats:
    def __init__(self):
        raw = _load_json(STATS_FILE, {})
        self._c = collections.defaultdict(int, raw if isinstance(raw, dict) else {})
        self._lock = threading.Lock()

    def record(self, word: str):
        with self._lock: self._c[word] += 1
        threading.Thread(target=lambda: _save_json(STATS_FILE, dict(self._c)), daemon=True).start()

    def top(self, n=50):
        with self._lock:
            return sorted(self._c.items(), key=lambda x: x[1], reverse=True)[:n]

    def total(self):
        with self._lock: return sum(self._c.values())

    def reset(self):
        with self._lock: self._c.clear()
        _save_json(STATS_FILE, {})


# ════════════════════════════════════════════════════════════════════════════
#  Startup helpers (unchanged)
# ════════════════════════════════════════════════════════════════════════════

def _startup_enabled():
    if sys.platform == "win32":
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            winreg.QueryValueEx(k, APP_NAME);
            winreg.CloseKey(k);
            return True
        except:
            return False
    return False


def _set_startup(enable):
    if sys.platform != "win32": return
    import winreg
    k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                       r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
    if enable:
        winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ,
                          f'"{sys.executable}" "{Path(__file__).resolve()}"')
    else:
        try:
            winreg.DeleteValue(k, APP_NAME)
        except FileNotFoundError:
            pass
    winreg.CloseKey(k)


# ════════════════════════════════════════════════════════════════════════════
#  Window tracker (unchanged)
# ════════════════════════════════════════════════════════════════════════════

_ext_window: str = ""


def _poll_window() -> str:
    try:
        if sys.platform == "win32":
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            n = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            b = ctypes.create_unicode_buffer(n + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, b, n + 1)
            return b.value
        elif sys.platform == "darwin":
            r = subprocess.run(["osascript", "-e",
                                'tell app "System Events" to get name of first process whose frontmost is true'],
                               capture_output=True, text=True, timeout=0.3)
            return r.stdout.strip()
        else:
            r = subprocess.run(["xdotool", "getactivewindow", "getwindowname"],
                               capture_output=True, text=True, timeout=0.3)
            return r.stdout.strip()
    except:
        return ""


def _window_tracker():
    global _ext_window
    while True:
        t = _poll_window()
        if t and APP_NAME not in t: _ext_window = t
        time.sleep(0.6)


def _active_window() -> str:
    return _ext_window or _poll_window()


# ════════════════════════════════════════════════════════════════════════════
#  Engine (unchanged)
# ════════════════════════════════════════════════════════════════════════════

class Engine:
    def __init__(self, sm: SnippetManager, cfg: Config, stats: Stats, on_fire=None):
        self.sm = sm;
        self.cfg = cfg;
        self.stats = stats;
        self.on_fire = on_fire
        self.active = False;
        self._buf = "";
        self._last = None
        self._snooze = None;
        self._toggle_fn = None

    def start(self):
        if self.active: return
        self.active = True;
        self._buf = "";
        self._last = None
        keyboard.on_press(self._on_key, suppress=False)
        self._hotkeys()

    def stop(self):
        if not self.active: return
        self.active = False;
        self._buf = ""
        keyboard.unhook_all();
        self._toggle_only()

    def snooze(self, minutes, on_wake=None):
        if self._snooze: self._snooze.cancel()
        self.stop()

        def _wake(): self.start(); on_wake and on_wake()

        self._snooze = threading.Timer(minutes * 60, _wake)
        self._snooze.daemon = True;
        self._snooze.start()

    def setup(self, toggle_fn):
        self._toggle_fn = toggle_fn;
        self._toggle_only()

    def reregister(self):
        keyboard.unhook_all()
        if self.active:
            keyboard.on_press(self._on_key, suppress=False);
            self._hotkeys()
        else:
            self._toggle_only()

    def _hotkeys(self):
        try:
            keyboard.add_hotkey(self.cfg.get("toggle_hotkey"), self._toggle_fn, suppress=False)
        except:
            pass
        try:
            keyboard.add_hotkey(self.cfg.get("undo_hotkey"), self._undo, suppress=False)
        except:
            pass

    def _toggle_only(self):
        try:
            keyboard.add_hotkey(self.cfg.get("toggle_hotkey"), self._toggle_fn, suppress=False)
        except:
            pass

    def _on_key(self, ev):
        name = ev.name or ""
        if keyboard.is_pressed("alt"): self._buf = ""; return
        if keyboard.is_pressed("ctrl") and name != "z": self._buf = ""; return

        if name in _TRIGGERS:
            word = self._buf;
            self._buf = "";
            self._last = None
            if word and not self._blocked():
                key = word.lower()
                exp = self.sm.get(key)
                if exp:
                    trig = (" " if name == "space" else "\n" if name == "enter"
                    else "\t" if name == "tab" else name)
                    self._last = {"orig": word, "exp": exp, "trig": trig}
                    delay = float(self.cfg.get("replace_delay") or 0.006)
                    threading.Timer(0.02, self._replace, args=(word, exp, trig, delay)).start()
                    self.stats.record(key)
                    if self.on_fire:
                        try:
                            self.on_fire(key, exp)
                        except:
                            pass
            return

        if name == "backspace": self._buf = self._buf[:-1]; self._last = None; return
        if len(name) == 1 and (name.isalpha() or name.isdigit() or name == "'"):
            self._buf += name;
            return
        if name not in ("shift", "caps lock"): self._buf = ""

    def _replace(self, word, exp, trig, delay):
        n = len(word) + 1
        keyboard.send("backspace");
        time.sleep(0.008)
        for _ in range(n - 1): keyboard.send("backspace")
        keyboard.write(exp + trig, delay=delay)

    def _undo(self):
        if not self._last: return
        info = self._last;
        self._last = None
        n = len(info["exp"]) + 1
        keyboard.send("backspace");
        time.sleep(0.008)
        for _ in range(n - 1): keyboard.send("backspace")
        keyboard.write(info["orig"] + info["trig"],
                       delay=float(self.cfg.get("replace_delay") or 0.006))

    def _blocked(self) -> bool:
        mode = self.cfg.get("app_mode") or "all"
        apps = self.cfg.get("app_list") or []
        if mode == "all" or not apps: return False
        title = _poll_window().lower() or _ext_window.lower()
        match = any(a.lower() in title for a in apps)
        return (not match) if mode == "include" else match


# ════════════════════════════════════════════════════════════════════════════
#  Enhanced UI helpers
# ════════════════════════════════════════════════════════════════════════════

def _lighten(h, amount=22):
    try:
        r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7],
                                                        16); return f"#{min(r + amount, 255):02x}{min(g + amount, 255):02x}{min(b + amount, 255):02x}"
    except:
        return h


def _darken(h, amount=22):
    try:
        r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7],
                                                        16); return f"#{max(r - amount, 0):02x}{max(g - amount, 0):02x}{max(b - amount, 0):02x}"
    except:
        return h


def _create_gradient(canvas, width, height, color1, color2, orientation="vertical"):
    """Create a gradient on a canvas using solid colors (no alpha)"""
    # Ensure width and height are integers
    width = int(width)
    height = int(height)

    steps = 20  # Fewer steps for better performance
    if orientation == "vertical":
        for i in range(steps):
            y = int(i * height / steps)
            y2 = int((i + 1) * height / steps)
            ratio = i / steps
            # Parse colors
            r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
            r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
            # Interpolate
            r = int(r1 * (1 - ratio) + r2 * ratio)
            g = int(g1 * (1 - ratio) + g2 * ratio)
            b = int(b1 * (1 - ratio) + b2 * ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"
            canvas.create_rectangle(0, y, width, y2, fill=color, outline="")
    else:
        for i in range(steps):
            x = int(i * width / steps)
            x2 = int((i + 1) * width / steps)
            ratio = i / steps
            # Parse colors
            r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
            r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
            # Interpolate
            r = int(r1 * (1 - ratio) + r2 * ratio)
            g = int(g1 * (1 - ratio) + g2 * ratio)
            b = int(b1 * (1 - ratio) + b2 * ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"
            canvas.create_rectangle(x, 0, x2, height, fill=color, outline="")


def _modern_button(parent, text, command, icon=None, style="primary", **kwargs):
    """Modern styled button with hover effects"""
    styles = {
        "primary": {"bg": ACCENT, "fg": BG, "hover": _lighten(ACCENT)},
        "success": {"bg": GREEN, "fg": BG, "hover": _lighten(GREEN)},
        "danger": {"bg": RED, "fg": BG, "hover": _lighten(RED)},
        "warning": {"bg": YELLOW, "fg": BG, "hover": _lighten(YELLOW)},
        "info": {"bg": BLUE, "fg": BG, "hover": _lighten(BLUE)},
        "secondary": {"bg": OVERLAY, "fg": TEXT, "hover": _lighten(OVERLAY)},
    }
    s = styles.get(style, styles["secondary"])

    frame = tk.Frame(parent, bg=parent["bg"])
    btn = tk.Button(frame, text=text, command=command,
                    bg=s["bg"], fg=s["fg"],
                    font=("Segoe UI", 10, "bold" if style != "secondary" else "normal"),
                    relief="flat", bd=0, cursor="hand2", padx=15, pady=8, **kwargs)

    if icon:
        btn.config(text=f"{icon}  {text}")

    def on_enter(e):
        btn.config(bg=s["hover"])
        frame.config(bg=s["hover"])

    def on_leave(e):
        btn.config(bg=s["bg"])
        frame.config(bg=parent["bg"])

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    btn.pack()
    return frame


def _card(parent, title=None, **kwargs):
    """Modern card with optional title"""
    card = tk.Frame(parent, bg=CARD, highlightbackground=OVERLAY, highlightthickness=1, **kwargs)

    if title:
        header = tk.Frame(card, bg=CARD)
        header.pack(fill="x", padx=15, pady=(12, 6))

        icon_label = tk.Label(header, text=title[0] if title else "",
                              bg=CARD, fg=ACCENT, font=("Segoe UI", 12))
        icon_label.pack(side="left", padx=(0, 8))

        title_label = tk.Label(header, text=title[1:] if title and title[0].isalpha() else title,
                               bg=CARD, fg=TEXT, font=("Segoe UI", 11, "bold"))
        title_label.pack(side="left")

        tk.Frame(card, bg=OVERLAY, height=1).pack(fill="x", padx=15, pady=(0, 8))

    return card


def _entry(parent, var=None, placeholder="", **kwargs):
    """Modern entry with placeholder"""
    entry = tk.Entry(parent, textvariable=var, bg=SURFACE, fg=TEXT,
                     insertbackground=TEXT, relief="flat",
                     font=("Segoe UI", 10), **kwargs)

    if placeholder:
        entry.insert(0, placeholder)
        entry.config(fg=SUBTEXT)

        def on_focus_in(e):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.config(fg=TEXT)

        def on_focus_out(e):
            if not entry.get():
                entry.insert(0, placeholder)
                entry.config(fg=SUBTEXT)

        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    return entry


def _create_tooltip(widget, text):
    """Create a tooltip for a widget"""

    def show_tooltip(e):
        x, y, _, _ = widget.bbox("insert")
        x += widget.winfo_rootx() + 25
        y += widget.winfo_rooty() + 25

        tip = tk.Toplevel(widget)
        tip.wm_overrideredirect(True)
        tip.wm_geometry(f"+{x}+{y}")

        frame = tk.Frame(tip, bg=OVERLAY, padx=8, pady=4)
        frame.pack()
        tk.Label(frame, text=text, bg=OVERLAY, fg=TEXT,
                 font=("Segoe UI", 9)).pack()

        def hide_tooltip():
            tip.destroy()

        widget.tip = tip
        widget.after(3000, hide_tooltip)

    def hide_tooltip(e):
        if hasattr(widget, 'tip'):
            widget.tip.destroy()

    widget.bind("<Enter>", show_tooltip)
    widget.bind("<Leave>", hide_tooltip)


def _modern_progress_bar(parent, value=0, max_value=100, width=200, height=8):
    """Modern animated progress bar"""
    frame = tk.Frame(parent, bg=parent["bg"])

    # Background
    bg_canvas = tk.Canvas(frame, width=width, height=height, bg=SURFACE,
                          highlightthickness=0)
    bg_canvas.pack()

    # Progress
    progress_width = int((value / max_value) * width)
    if progress_width > 0:
        progress_canvas = tk.Canvas(frame, width=progress_width, height=height,
                                    bg=GREEN, highlightthickness=0)
        progress_canvas.place(x=0, y=0)

    return frame


def _toggle_switch(parent, variable, on_text="ON", off_text="OFF", command=None):
    """Modern toggle switch"""
    frame = tk.Frame(parent, bg=parent["bg"])

    def toggle():
        variable.set(not variable.get())
        if command:
            command()
        update_style()

    def update_style():
        if variable.get():
            indicator.config(bg=GREEN, text=on_text)
            btn.config(bg=GREEN)
        else:
            indicator.config(bg=OVERLAY, text=off_text)
            btn.config(bg=OVERLAY)

    btn = tk.Button(frame, width=50, height=25, relief="flat", bd=0,
                    cursor="hand2", command=toggle)
    btn.pack()

    indicator = tk.Label(btn, text=on_text if variable.get() else off_text,
                         bg=GREEN if variable.get() else OVERLAY,
                         fg=BG if variable.get() else TEXT,
                         font=("Segoe UI", 8, "bold"))
    indicator.place(relx=0.5, rely=0.5, anchor="center")

    update_style()
    return frame


def _scrolled(parent, bg=BG):
    """Enhanced scrolled frame with smooth scrolling"""
    canvas = tk.Canvas(parent, bg=bg, highlightthickness=0)
    v_scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    h_scrollbar = ttk.Scrollbar(parent, orient="horizontal", command=canvas.xview)

    inner = tk.Frame(canvas, bg=bg)
    inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    canvas.create_window((0, 0), window=inner, anchor="nw")
    canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    v_scrollbar.pack(side="right", fill="y")
    h_scrollbar.pack(side="bottom", fill="x")

    # Smooth scrolling with mouse wheel
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_shift_mousewheel(event):
        canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind("<MouseWheel>", _on_mousewheel)
    canvas.bind("<Shift-MouseWheel>", _on_shift_mousewheel)
    inner.bind("<MouseWheel>", _on_mousewheel)
    inner.bind("<Shift-MouseWheel>", _on_shift_mousewheel)

    return inner, canvas


def _tree_style(name, row_h=32):
    """Enhanced treeview style"""
    style = ttk.Style()
    style.configure(f"{name}.Treeview",
                    background=CARD,
                    foreground=TEXT,
                    fieldbackground=CARD,
                    rowheight=row_h,
                    font=("Segoe UI", 10),
                    borderwidth=0)

    style.configure(f"{name}.Treeview.Heading",
                    background=OVERLAY,
                    foreground=TEXT,
                    font=("Segoe UI", 10, "bold"),
                    relief="flat")

    style.map(f"{name}.Treeview",
              background=[("selected", ACCENT)],
              foreground=[("selected", BG)])

    style.map(f"{name}.Treeview.Heading",
              background=[("active", _lighten(OVERLAY))])


# ════════════════════════════════════════════════════════════════════════════
#  Enhanced Tray / Logo
# ════════════════════════════════════════════════════════════════════════════

def _make_logo(size=256) -> "Image.Image":
    """Enhanced SB monogram with modern design"""
    sc = 4
    hi = size * sc
    img = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background with gradient effect
    pad = int(hi * 0.04)

    # Outer glow
    for i in range(3, 0, -1):
        glow_pad = pad - i * 2
        if glow_pad > 0:
            draw.rounded_rectangle([glow_pad, glow_pad, hi - glow_pad, hi - glow_pad],
                                   radius=int(hi * 0.16) + i * 4,
                                   fill=f"#1e1e2e{20 * i:02x}", outline=None)

    # Main background
    draw.rounded_rectangle([pad, pad, hi - pad, hi - pad],
                           radius=int(hi * 0.16),
                           fill="#11111b", outline="#2a2a3e", width=sc * 3)

    # S - cyan with modern styling
    sx = int(hi * 0.12)
    sy = int(hi * 0.22)
    sw = int(hi * 0.32)
    sh = int(hi * 0.56)

    # S path
    points = [
        (sx, sy), (sx + sw, sy), (sx + sw, sy + sh // 4),
        (sx + sw // 3, sy + sh // 4), (sx + sw // 3, sy + sh // 2),
        (sx + sw, sy + sh // 2), (sx + sw, sy + sh * 3 // 4),
        (sx, sy + sh * 3 // 4), (sx, sy + sh // 2),
        (sx + sw * 2 // 3, sy + sh // 2), (sx + sw * 2 // 3, sy + sh // 4),
        (sx, sy + sh // 4), (sx, sy)
    ]

    # Draw S with gradient effect
    for i, point in enumerate(points[:-1]):
        x1, y1 = point
        x2, y2 = points[i + 1]
        opacity = 255 - i * 20
        draw.line([x1, y1, x2, y2], fill=f"#00d4ff{opacity:02x}", width=sc * 8)

    # T - purple with modern styling
    tx = int(hi * 0.56)
    ty = int(hi * 0.22)
    tw = int(hi * 0.32)

    # T horizontal bar
    draw.rounded_rectangle([tx, ty, tx + tw, ty + int(hi * 0.08)],
                           radius=sc * 4, fill="#b06ef3")

    # T vertical stem
    stem_x = tx + tw // 2 - int(hi * 0.04)
    draw.rounded_rectangle([stem_x, ty + int(hi * 0.04), stem_x + int(hi * 0.08), ty + int(hi * 0.56)],
                           radius=sc * 4, fill="#b06ef3")

    return img.resize((size, size), Image.Resampling.LANCZOS)


def _make_tray_icon(active: bool, snoozed: bool = False) -> "Image.Image":
    """Enhanced tray icon with status indicators"""
    sc = 4
    sz = 64
    hi = sz * sc
    img = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background based on state
    if snoozed:
        bg_color = YELLOW
        border_color = GOLD
        status_color = YELLOW
    elif active:
        bg_color = GREEN
        border_color = "#40a870"
        status_color = GREEN
    else:
        bg_color = CARD
        border_color = OVERLAY
        status_color = None

    # Outer ring
    padding = 4 * sc
    draw.ellipse([padding, padding, hi - padding, hi - padding],
                 outline=border_color, width=sc * 2)

    # Main circle
    draw.ellipse([padding + sc * 2, padding + sc * 2, hi - padding - sc * 2, hi - padding - sc * 2],
                 fill=bg_color)

    # S letter
    sx = int(hi * 0.25)
    sy = int(hi * 0.3)
    sw = int(hi * 0.2)

    # Draw S
    points = [(sx, sy), (sx + sw, sy), (sx + sw, sy + sw // 3),
              (sx + sw // 3, sy + sw // 3), (sx + sw // 3, sy + sw // 2),
              (sx + sw, sy + sw // 2), (sx + sw, sy + sw * 2 // 3),
              (sx, sy + sw * 2 // 3), (sx, sy + sw // 2),
              (sx + sw * 2 // 3, sy + sw // 2), (sx + sw * 2 // 3, sy + sw // 3),
              (sx, sy + sw // 3), (sx, sy)]

    for i, point in enumerate(points[:-1]):
        x1, y1 = point
        x2, y2 = points[i + 1]
        draw.line([x1, y1, x2, y2], fill=CYAN, width=sc * 4)

    # T letter
    tx = int(hi * 0.55)
    ty = int(hi * 0.3)
    tw = int(hi * 0.2)

    # T horizontal
    draw.rectangle([tx, ty, tx + tw, ty + int(hi * 0.06)], fill=PURPLE)

    # T vertical
    stem_x = tx + tw // 2 - int(hi * 0.02)
    draw.rectangle([stem_x, ty + int(hi * 0.05), stem_x + int(hi * 0.04), ty + int(hi * 0.4)], fill=PURPLE)

    # Status indicator
    if status_color:
        indicator_x = hi - int(hi * 0.2)
        indicator_y = int(hi * 0.1)
        draw.ellipse([indicator_x, indicator_y,
                      indicator_x + int(hi * 0.15), indicator_y + int(hi * 0.15)],
                     fill=status_color, outline=BG, width=sc)

    return img.resize((sz, sz), Image.Resampling.LANCZOS)


# ════════════════════════════════════════════════════════════════════════════
#  Enhanced Main App
# ════════════════════════════════════════════════════════════════════════════

class SnapTypeApp:
    def __init__(self):
        self.cfg = Config()
        self.sm = SnippetManager()
        self.stats = Stats()
        self.engine = Engine(self.sm, self.cfg, self.stats, on_fire=self._on_fire)
        self.active = False
        self.snoozed = False
        self._page_cache: dict[str, tk.Frame] = {}
        self._activity: collections.deque = collections.deque(maxlen=60)

        self.root = tk.Tk()
        self.root.title(f"SnapType  v{VERSION}")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Window icon
        try:
            _pil = _make_logo(256)
            buf = io.BytesIO()
            _pil.save(buf, format="PNG")
            buf.seek(0)
            self._win_icon = tk.PhotoImage(data=base64.b64encode(buf.read()).decode())
            self.root.iconphoto(True, self._win_icon)
        except:
            pass

        # Configure styles
        style = ttk.Style()
        style.theme_use("clam")
        _tree_style("SN")

        style.configure("TCombobox",
                        fieldbackground=CARD,
                        background=CARD,
                        foreground=TEXT,
                        arrowcolor=TEXT,
                        borderwidth=0)

        style.configure("TScrollbar",
                        background=OVERLAY,
                        troughcolor=SURFACE,
                        borderwidth=0,
                        arrowcolor=TEXT)

        self._build_skeleton()
        self.engine.setup(toggle_fn=self.toggle)
        self._nav("Dashboard")

        threading.Thread(target=self._run_tray, daemon=True).start()
        threading.Thread(target=_window_tracker, daemon=True).start()

    # ──────────────────────────────────────────────────────────────────────
    #  Enhanced Skeleton
    # ──────────────────────────────────────────────────────────────────────

    def _build_skeleton(self):
        # Modern sidebar with gradient
        self.sidebar = tk.Frame(self.root, bg=SURFACE, width=240)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo area with modern design
        logo_frame = tk.Frame(self.sidebar, bg=SURFACE)
        logo_frame.pack(fill="x", pady=(30, 10))

        # Animated logo canvas
        self.logo_canvas = tk.Canvas(logo_frame, width=80, height=80,
                                     bg=SURFACE, highlightthickness=0)
        self.logo_canvas.pack()

        # Draw logo
        self._draw_logo()

        # App name with gradient effect
        name_frame = tk.Frame(logo_frame, bg=SURFACE)
        name_frame.pack(pady=(10, 5))

        snap_label = tk.Label(name_frame, text="Snap", bg=SURFACE, fg=CYAN,
                              font=("Segoe UI", 18, "bold"))
        snap_label.pack(side="left")

        type_label = tk.Label(name_frame, text="Type", bg=SURFACE, fg=PURPLE,
                              font=("Segoe UI", 18, "bold"))
        type_label.pack(side="left")

        version_label = tk.Label(logo_frame, text=f"v{VERSION}", bg=SURFACE, fg=SUBTEXT,
                                 font=("Segoe UI", 9))
        version_label.pack()

        # Separator with gradient
        sep_canvas = tk.Canvas(self.sidebar, height=2, bg=SURFACE, highlightthickness=0)
        sep_canvas.pack(fill="x", padx=20, pady=15)
        _create_gradient(sep_canvas, 200, 2, CYAN, PURPLE, "horizontal")

        # Navigation buttons with modern styling
        self._nav_btns: dict[str, tk.Button] = {}
        for icon, label in NAV_ITEMS:
            btn_frame = tk.Frame(self.sidebar, bg=SURFACE)
            btn_frame.pack(fill="x", padx=12, pady=2)

            btn = tk.Button(btn_frame, text=f"  {icon}  {label}",
                            bg=SURFACE, fg=SUBTEXT, relief="flat", bd=0,
                            font=("Segoe UI", 10), padx=15, pady=10, anchor="w",
                            cursor="hand2", activebackground=CARD, activeforeground=TEXT,
                            command=lambda l=label: self._nav(l))
            btn.pack(fill="x")

            # Hover effect
            def on_enter(e, b=btn):
                b.config(bg=CARD, fg=TEXT)

            def on_leave(e, b=btn):
                if b["text"] != f"  {icon}  {label}" or label != self._current_page:
                    b.config(bg=SURFACE, fg=SUBTEXT)

            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

            self._nav_btns[label] = btn

        # Bottom controls
        bottom_frame = tk.Frame(self.sidebar, bg=SURFACE)
        bottom_frame.pack(side="bottom", fill="x", pady=20)

        # Status indicator
        status_frame = tk.Frame(bottom_frame, bg=SURFACE)
        status_frame.pack(pady=(0, 10))

        self.status_indicator = tk.Canvas(status_frame, width=12, height=12,
                                          bg=SURFACE, highlightthickness=0)
        self.status_indicator.pack(side="left", padx=(0, 8))

        self._sb_status = tk.Label(status_frame, text="Inactive", bg=SURFACE,
                                   fg=SUBTEXT, font=("Segoe UI", 9))
        self._sb_status.pack(side="left")

        # Toggle button with modern style
        self._sb_toggle = _modern_button(bottom_frame, "Start", self.toggle,
                                         icon="▶", style="success")
        self._sb_toggle.pack(pady=5)

        # Main area with subtle shadow effect
        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)

        # Top bar with gradient
        topbar = tk.Canvas(self.main, height=70, bg=BG, highlightthickness=0)
        topbar.pack(fill="x")
        _create_gradient(topbar, 1100, 70, _darken(BG, 10), BG, "vertical")

        # Page title
        self._page_title = tk.Label(topbar, text="", bg=BG, fg=TEXT,
                                    font=("Segoe UI", 18, "bold"))
        self._page_title.place(x=30, y=20)

        # Top bar controls
        ctrl_frame = tk.Frame(topbar, bg=BG)
        ctrl_frame.place(relx=1.0, x=-30, y=15, anchor="ne")

        self._topbar_toggle = _modern_button(ctrl_frame, "Start", self.toggle,
                                             icon="▶", style="success")
        self._topbar_toggle.pack(side="left", padx=5)

        snooze_btn = _modern_button(ctrl_frame, "Snooze", self._do_snooze,
                                    icon="💤", style="warning")
        snooze_btn.pack(side="left", padx=5)

        # Page container
        self._page_container = tk.Frame(self.main, bg=BG)
        self._page_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Status bar
        status_bar = tk.Frame(self.main, bg=SURFACE, height=30)
        status_bar.pack(fill="x", side="bottom")

        self._sb_left = tk.Label(status_bar, text="", bg=SURFACE, fg=SUBTEXT,
                                 font=("Segoe UI", 9), anchor="w")
        self._sb_left.pack(side="left", padx=15)

        self._sb_right = tk.Label(status_bar, text="", bg=SURFACE, fg=SUBTEXT,
                                  font=("Segoe UI", 9), anchor="e")
        self._sb_right.pack(side="right", padx=15)

        self._refresh_status()
        self._current_page = "Dashboard"

    def _draw_logo(self):
        """Draw modern logo on canvas"""
        self.logo_canvas.delete("all")

        # Background glow - use solid colors instead of rgba
        for i in range(3, 0, -1):
            # Use solid colors with decreasing brightness instead of alpha
            colors = ["#4a3b6e", "#3a2b5e", "#2a1b4e"]  # Darker purple shades
            self.logo_canvas.create_oval(5 - i * 2, 5 - i * 2, 75 + i * 2, 75 + i * 2,
                                         fill=colors[i - 1], outline="")

        # Main circle
        self.logo_canvas.create_oval(5, 5, 75, 75, fill="#11111b", outline="#2a2a3e", width=2)

        # S in cyan
        self.logo_canvas.create_line(15, 25, 35, 25, 35, 35, 20, 35, 20, 45, 35, 45, 35, 55, 15, 55,
                                     fill=CYAN, width=4, smooth=True)

        # T in purple
        self.logo_canvas.create_line(45, 25, 65, 25, fill=PURPLE, width=4)
        self.logo_canvas.create_line(55, 25, 55, 55, fill=PURPLE, width=4)

    # ──────────────────────────────────────────────────────────────────────
    #  Navigation
    # ──────────────────────────────────────────────────────────────────────

    def _nav(self, label):
        self._current_page = label
        self._page_title.config(text=label)

        for name, btn in self._nav_btns.items():
            if name == label:
                btn.config(bg=CARD, fg=ACCENT, font=("Segoe UI", 10, "bold"))
            else:
                btn.config(bg=SURFACE, fg=SUBTEXT, font=("Segoe UI", 10))

        for f in self._page_cache.values():
            f.pack_forget()

        if label not in self._page_cache:
            container = tk.Frame(self._page_container, bg=BG)
            self._page_cache[label] = container

            builders = {
                "Dashboard": self._build_dashboard,
                "Snippets": self._build_snippets,
                "Stats": self._build_stats,
                "App Rules": self._build_apps,
                "Settings": self._build_settings,
                "About": self._build_about,
            }

            if label in builders:
                builders[label](container)

        self._page_cache[label].pack(fill="both", expand=True)

        refresh_funcs = {
            "Dashboard": self._refresh_dashboard,
            "Snippets": self._refresh_snippet_tree,
            "Stats": self._refresh_stats,
        }

        if label in refresh_funcs:
            refresh_funcs[label]()

    # ──────────────────────────────────────────────────────────────────────
    #  Toggle / Snooze
    # ──────────────────────────────────────────────────────────────────────

    def toggle(self):
        if self.active:
            self.engine.stop()
            self.active = False
            self._update_status_indicator("inactive")
        else:
            self.engine.start()
            self.active = True
            self._update_status_indicator("active")

        self.snoozed = False
        self._refresh_status()
        self._update_tray()

    def _do_snooze(self):
        self.snoozed = True
        self.active = False
        self._update_status_indicator("snoozed")
        self._refresh_status()
        self._update_tray()
        self.engine.snooze(self.cfg.get("snooze_minutes") or 5,
                           on_wake=lambda: self.root.after(0, self._on_wake))

    def _on_wake(self):
        self.active = True
        self.snoozed = False
        self._update_status_indicator("active")
        self._refresh_status()
        self._update_tray()

    def _update_status_indicator(self, state):
        colors = {
            "active": GREEN,
            "inactive": OVERLAY,
            "snoozed": YELLOW
        }
        color = colors.get(state, OVERLAY)
        self.status_indicator.delete("all")
        self.status_indicator.create_oval(0, 0, 12, 12, fill=color, outline="")

    def _on_fire(self, abbr, expansion):
        self._activity.appendleft(f"⚡ {abbr} → {expansion}")
        self.root.after(0, self._refresh_activity_log)

    def _refresh_status(self):
        n = len(self.sm.snippets)
        tot = self.stats.total()
        hk = self.cfg.get("toggle_hotkey")

        if self.snoozed:
            state = "Snoozed"
            btn_text = "Resume"
            btn_style = "warning"
            status_text = "Snoozed"
        elif self.active:
            state = "Active"
            btn_text = "Stop"
            btn_style = "danger"
            status_text = "Active"
        else:
            state = "Inactive"
            btn_text = "Start"
            btn_style = "success"
            status_text = "Inactive"

        self._sb_status.config(text=status_text)

        # Update toggle buttons
        for btn in (self._sb_toggle, self._topbar_toggle):
            btn.destroy()

        self._sb_toggle = _modern_button(self.sidebar.winfo_children()[-2],
                                         btn_text, self.toggle,
                                         icon="▶" if btn_text == "Start" else "⏸",
                                         style=btn_style)
        self._sb_toggle.pack(pady=5)

        self._topbar_toggle = _modern_button(self.main.winfo_children()[0].winfo_children()[1],
                                             btn_text, self.toggle,
                                             icon="▶" if btn_text == "Start" else "⏸",
                                             style=btn_style)
        self._topbar_toggle.pack(side="left", padx=5)

        self._sb_left.config(text=f"  {n} snippets  ·  {hk}")
        self._sb_right.config(text=f"{tot:,} expansions total  ")

        if hasattr(self, "_dash_total") and self._dash_total.winfo_exists():
            self._refresh_dashboard()

    def _flash(self, msg, ms=3000, color=SUBTEXT):
        self._sb_left.config(text=f"  {msg}", fg=color)
        self.root.after(ms, lambda: self._refresh_status())

    # ──────────────────────────────────────────────────────────────────────
    #  Enhanced Dashboard
    # ──────────────────────────────────────────────────────────────────────

    def _build_dashboard(self, p):
        # Welcome card
        welcome_card = _card(p, "👋 Welcome to SnapType")
        welcome_card.pack(fill="x", pady=(0, 15))

        content = tk.Frame(welcome_card, bg=CARD)
        content.pack(fill="x", padx=15, pady=15)

        tk.Label(content, text="Type less. Say more.", bg=CARD, fg=TEXT,
                 font=("Segoe UI", 14)).pack(anchor="w")
        tk.Label(content, text=f"Currently {len(self.sm.snippets)} snippets loaded",
                 bg=CARD, fg=SUBTEXT, font=("Segoe UI", 10)).pack(anchor="w", pady=(5, 0))

        # Stats grid
        stats_grid = tk.Frame(p, bg=BG)
        stats_grid.pack(fill="x", pady=(0, 15))

        stats_grid.columnconfigure(0, weight=1)
        stats_grid.columnconfigure(1, weight=1)

        # Total expansions card
        exp_card = _card(stats_grid, "📊 Total Expansions")
        exp_card.grid(row=0, column=0, sticky="ew", padx=(0, 7))

        self._dash_total = tk.Label(exp_card, text="0", bg=CARD, fg=CYAN,
                                    font=("Segoe UI", 32, "bold"))
        self._dash_total.pack(pady=15)

        tk.Label(exp_card, text="expansions performed", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 9)).pack(pady=(0, 15))

        # Snippets count card
        snip_card = _card(stats_grid, "⚡ Active Snippets")
        snip_card.grid(row=0, column=1, sticky="ew", padx=(7, 0))

        self._dash_count = tk.Label(snip_card, text="0", bg=CARD, fg=PURPLE,
                                    font=("Segoe UI", 32, "bold"))
        self._dash_count.pack(pady=15)

        tk.Label(snip_card, text="snippets available", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 9)).pack(pady=(0, 15))

        # Activity feed
        activity_card = _card(p, "🔄 Live Activity")
        activity_card.pack(fill="both", expand=True, pady=(0, 15))

        self._activity_box = tk.Listbox(activity_card, bg=CARD, fg=TEXT,
                                        selectbackground=ACCENT, selectforeground=BG,
                                        font=("Segoe UI", 10), relief="flat",
                                        activestyle="none", bd=0, height=8)
        self._activity_box.pack(fill="both", expand=True, padx=10, pady=10)

        # Quick actions
        actions_card = _card(p, "🚀 Quick Actions")
        actions_card.pack(fill="x")

        actions_frame = tk.Frame(actions_card, bg=CARD)
        actions_frame.pack(padx=15, pady=15)

        actions = [
            ("⚡ Manage Snippets", "Snippets", ACCENT),
            ("📊 View Stats", "Stats", GREEN),
            ("🛡️ App Rules", "App Rules", ORANGE),
            ("⚙️ Settings", "Settings", BLUE),
        ]

        for text, page, color in actions:
            # Create custom button instead of using _modern_button
            btn_frame = tk.Frame(actions_frame, bg=CARD)
            btn_frame.pack(side="left", padx=5, fill="x", expand=True)

            btn = tk.Button(btn_frame, text=text,
                            bg=color, fg=BG,
                            font=("Segoe UI", 10, "bold"),
                            relief="flat", bd=0, cursor="hand2",
                            padx=15, pady=8,
                            command=lambda p=page: self._nav(p))
            btn.pack(fill="x")

            # Add hover effect
            def on_enter(e, b=btn, c=color):
                # Lighten color for hover
                r, g, b_color = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
                r = min(r + 20, 255)
                g = min(g + 20, 255)
                b_color = min(b_color + 20, 255)
                hover_color = f"#{r:02x}{g:02x}{b_color:02x}"
                b.config(bg=hover_color)

            def on_leave(e, b=btn, c=color):
                b.config(bg=c)

            btn.bind("<Enter>", on_enter)
            btn.bind("<Leave>", on_leave)

        self._refresh_dashboard()

    def _refresh_dashboard(self):
        if not hasattr(self, "_dash_total"):
            return

        try:
            self._dash_total.config(text=f"{self.stats.total():,}")
            self._dash_count.config(text=str(len(self.sm.snippets)))
            self._refresh_activity_log()
        except:
            pass

    def _refresh_activity_log(self):
        if not hasattr(self, "_activity_box"):
            return

        try:
            self._activity_box.delete(0, tk.END)
            for entry in self._activity:
                self._activity_box.insert(0, f"  {entry}")
        except:
            pass

    # ──────────────────────────────────────────────────────────────────────
    #  Enhanced Snippets page
    # ──────────────────────────────────────────────────────────────────────

    def _build_snippets(self, p):
        # Header with controls
        header_card = _card(p, "⚡ Snippet Manager")
        header_card.pack(fill="x", pady=(0, 15))

        controls = tk.Frame(header_card, bg=CARD)
        controls.pack(fill="x", padx=15, pady=15)

        # Toggle switch
        toggle_frame = tk.Frame(controls, bg=CARD)
        toggle_frame.pack(side="left")

        tk.Label(toggle_frame, text="Snippets:", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 10)).pack(side="left", padx=(0, 10))

        self._snip_enabled_var = tk.BooleanVar(value=self.sm.enabled)
        toggle = _toggle_switch(toggle_frame, self._snip_enabled_var,
                                command=lambda: (
                                    setattr(self.sm, "enabled", self._snip_enabled_var.get()),
                                    self._flash("Snippets " + ("enabled" if self.sm.enabled else "disabled"))
                                ))
        toggle.pack(side="left")

        # Import/Export buttons
        button_frame = tk.Frame(controls, bg=CARD)
        button_frame.pack(side="right")

        _modern_button(button_frame, "Import CSV", self._snip_import_csv,
                       icon="📥", style="secondary").pack(side="left", padx=5)
        _modern_button(button_frame, "Export CSV", self._snip_export_csv,
                       icon="📤", style="secondary").pack(side="left", padx=5)

        # Search bar
        search_card = _card(p)
        search_card.pack(fill="x", pady=(0, 15))

        search_frame = tk.Frame(search_card, bg=CARD)
        search_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(search_frame, text="🔍", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 12)).pack(side="left", padx=(0, 10))

        self._snip_search = tk.StringVar()
        self._snip_search.trace("w", lambda *_: self._refresh_snippet_tree())

        search_entry = _entry(search_frame, self._snip_search, width=40,
                              placeholder="Search snippets...")
        search_entry.pack(side="left", ipady=5)

        self._snip_count_var = tk.StringVar()
        tk.Label(search_frame, textvariable=self._snip_count_var, bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 9)).pack(side="left", padx=15)

        # Quick add chips
        chips_card = _card(p, "📋 Quick Add Examples")
        chips_card.pack(fill="x", pady=(0, 15))

        chips_frame = tk.Frame(chips_card, bg=CARD)
        chips_frame.pack(padx=15, pady=15)

        examples = [
            ("ily → i love you", "ily", "i love you", PINK),
            ("omw → on my way", "omw", "on my way", BLUE),
            ("hru → how are you", "hru", "how are you", GREEN),
            ("asap → as soon as possible", "asap", "as soon as possible", ORANGE),
            ("lmk → let me know", "lmk", "let me know", PURPLE),
        ]

        for label, abbr, exp, color in examples:
            chip = tk.Button(chips_frame, text=label, bg=SURFACE, fg=color,
                             font=("Segoe UI", 9), relief="flat", padx=12, pady=6,
                             cursor="hand2", bd=0,
                             activebackground=color, activeforeground=BG,
                             command=lambda a=abbr, e=exp: self._quick_add_snippet(a, e))
            chip.pack(side="left", padx=3)

        # Treeview
        tree_card = _card(p, "📝 Your Snippets")
        tree_card.pack(fill="both", expand=True, pady=(0, 15))

        tree_frame = tk.Frame(tree_card, bg=CARD)
        tree_frame.pack(fill="both", expand=True, padx=15, pady=15)

        self._snip_tree = ttk.Treeview(tree_frame, columns=("abbr", "expansion"),
                                       show="headings", style="SN.Treeview", height=12)
        self._snip_tree.heading("abbr", text="Abbreviation", anchor="w")
        self._snip_tree.heading("expansion", text="Expands to", anchor="w")
        self._snip_tree.column("abbr", width=150, anchor="w")
        self._snip_tree.column("expansion", width=450, anchor="w")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self._snip_tree.yview)
        self._snip_tree.configure(yscrollcommand=scrollbar.set)

        self._snip_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._snip_tree.bind("<<TreeviewSelect>>", self._snip_on_select)
        self._snip_tree.bind("<Delete>", lambda _: self._snip_delete())

        # Edit form
        form_card = _card(p, "✏️ Add / Edit Snippet")
        form_card.pack(fill="x")

        form = tk.Frame(form_card, bg=CARD)
        form.pack(fill="x", padx=15, pady=15)

        # Abbreviation field
        abbr_frame = tk.Frame(form, bg=CARD)
        abbr_frame.pack(fill="x", pady=5)

        tk.Label(abbr_frame, text="Abbreviation:", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 10), width=12, anchor="w").pack(side="left")

        self._snip_abbr_var = tk.StringVar()
        abbr_entry = _entry(abbr_frame, self._snip_abbr_var, width=20,
                            placeholder="e.g., omw")
        abbr_entry.pack(side="left", padx=(10, 0), ipady=5)

        # Expansion field
        exp_frame = tk.Frame(form, bg=CARD)
        exp_frame.pack(fill="x", pady=5)

        tk.Label(exp_frame, text="Expansion:", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 10), width=12, anchor="w").pack(side="left")

        self._snip_exp_var = tk.StringVar()
        exp_entry = _entry(exp_frame, self._snip_exp_var, width=50,
                           placeholder="e.g., on my way")
        exp_entry.pack(side="left", padx=(10, 0), ipady=5)

        # Action buttons
        action_frame = tk.Frame(form, bg=CARD)
        action_frame.pack(fill="x", pady=(15, 5))

        _modern_button(action_frame, "Add / Update", self._snip_upsert,
                       icon="➕", style="success").pack(side="left", padx=5)
        _modern_button(action_frame, "Delete", self._snip_delete,
                       icon="🗑", style="danger").pack(side="left", padx=5)
        _modern_button(action_frame, "Clear", self._snip_clear,
                       icon="✖", style="secondary").pack(side="left", padx=5)

        # Status message
        self._snip_status_var = tk.StringVar()
        self._snip_status_lbl = tk.Label(form_card, textvariable=self._snip_status_var,
                                         bg=CARD, fg=SUBTEXT, font=("Segoe UI", 9))
        self._snip_status_lbl.pack(anchor="w", padx=15, pady=(0, 10))

        self._refresh_snippet_tree()

    def _quick_add_snippet(self, abbr, exp):
        """Quick add a snippet from examples"""
        if self.sm.upsert(abbr, exp):
            self._flash(f"Added: {abbr} → {exp}", color=GREEN)
            self._refresh_snippet_tree()

    def _refresh_snippet_tree(self, *_):
        if not hasattr(self, "_snip_tree"):
            return

        q = self._snip_search.get().lower() if hasattr(self, "_snip_search") else ""

        self._snip_tree.delete(*self._snip_tree.get_children())

        for abbr, exp in sorted(self.sm.snippets.items()):
            if q in abbr or q in exp.lower():
                self._snip_tree.insert("", "end", iid=abbr, values=(abbr, exp))

        n = len(self.sm.snippets)
        if hasattr(self, "_snip_count_var"):
            self._snip_count_var.set(f"{n} snippet{'s' if n != 1 else ''}")

    def _snip_on_select(self, _=None):
        sel = self._snip_tree.selection()
        if sel:
            abbr, exp = self._snip_tree.item(sel[0], "values")
            self._snip_abbr_var.set(abbr)
            self._snip_exp_var.set(exp)

    def _snip_upsert(self):
        a = self._snip_abbr_var.get().strip()
        e = self._snip_exp_var.get().strip()

        if not a or not e:
            self._snip_st("⚠️ Both fields are required.", YELLOW)
            return

        existed = a.lower() in self.sm.snippets

        if self.sm.upsert(a, e):
            self._snip_st(f"✅ {'Updated' if existed else 'Added'}: {a.lower()} → {e}", GREEN)
            self._snip_clear()
            self._refresh_snippet_tree()

    def _snip_delete(self, *_):
        a = self._snip_abbr_var.get().strip().lower()

        if not a:
            sel = self._snip_tree.selection()
            a = sel[0] if sel else ""

        if not a or a not in self.sm.snippets:
            self._snip_st("⚠️ Select a snippet first.", YELLOW)
            return

        if messagebox.askyesno("Delete Snippet", f'Delete snippet "{a}"?', parent=self.root):
            self.sm.delete(a)
            self._snip_st(f"🗑️ Deleted: {a}", RED)
            self._snip_clear()
            self._refresh_snippet_tree()

    def _snip_clear(self):
        self._snip_abbr_var.set("")
        self._snip_exp_var.set("")
        self._snip_tree.selection_remove(*self._snip_tree.selection())

    def _snip_st(self, msg, color=SUBTEXT):
        self._snip_status_var.set(msg)
        self._snip_status_lbl.config(fg=color)
        self.root.after(3000, lambda: self._snip_status_var.set(""))

    def _snip_export_csv(self):
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")], initialfile="snippets.csv")
        if path:
            self.sm.export_csv(path)
            self._snip_st("📤 Exported successfully.", GREEN)

    def _snip_import_csv(self):
        path = filedialog.askopenfilename(parent=self.root,
                                          filetypes=[("CSV", "*.csv"), ("All", "*.*")])
        if path:
            try:
                n = self.sm.import_csv(path)
                self._snip_st(f"📥 Imported {n} snippets.", GREEN)
                self._refresh_snippet_tree()
            except Exception as e:
                messagebox.showerror("Import Error", str(e), parent=self.root)

    # ──────────────────────────────────────────────────────────────────────
    #  Enhanced Stats page
    # ──────────────────────────────────────────────────────────────────────

    def _build_stats(self, p):
        # Header with total
        header_card = _card(p, "📊 Usage Statistics")
        header_card.pack(fill="x", pady=(0, 15))

        header_frame = tk.Frame(header_card, bg=CARD)
        header_frame.pack(fill="x", padx=15, pady=15)

        self._stats_total_lbl = tk.Label(header_frame, text="", bg=CARD, fg=CYAN,
                                         font=("Segoe UI", 18, "bold"))
        self._stats_total_lbl.pack(side="left")

        button_frame = tk.Frame(header_frame, bg=CARD)
        button_frame.pack(side="right")

        _modern_button(button_frame, "Refresh", self._refresh_stats,
                       icon="🔄", style="secondary").pack(side="left", padx=5)
        _modern_button(button_frame, "Reset", self._reset_stats,
                       icon="🗑", style="danger").pack(side="left", padx=5)

        # Stats table
        table_card = _card(p, "📈 Top Snippets")
        table_card.pack(fill="both", expand=True)

        table_frame = tk.Frame(table_card, bg=CARD)
        table_frame.pack(fill="both", expand=True, padx=15, pady=15)

        self._stats_tree = ttk.Treeview(table_frame,
                                        columns=("abbr", "exp", "count", "bar"),
                                        show="headings", style="SN.Treeview", height=15)

        self._stats_tree.heading("abbr", text="Abbreviation", anchor="w")
        self._stats_tree.heading("exp", text="Expands to", anchor="w")
        self._stats_tree.heading("count", text="Uses", anchor="center")
        self._stats_tree.heading("bar", text="Frequency", anchor="w")

        self._stats_tree.column("abbr", width=120, anchor="w")
        self._stats_tree.column("exp", width=300, anchor="w")
        self._stats_tree.column("count", width=70, anchor="center")
        self._stats_tree.column("bar", width=300, anchor="w")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self._stats_tree.yview)
        self._stats_tree.configure(yscrollcommand=scrollbar.set)

        self._stats_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._refresh_stats()

    def _refresh_stats(self):
        if not hasattr(self, "_stats_tree"):
            return

        self._stats_tree.delete(*self._stats_tree.get_children())

        top = self.stats.top(50)
        max_count = top[0][1] if top else 1

        for abbr, count in top:
            exp = self.sm.snippets.get(abbr, "—")
            bar_length = int(20 * count / max_count)
            bar = "█" * bar_length + "░" * (20 - bar_length)
            self._stats_tree.insert("", "end", values=(abbr, exp, count, bar))

        if hasattr(self, "_stats_total_lbl"):
            total = self.stats.total()
            self._stats_total_lbl.config(text=f"Total expansions: {total:,}")

    def _reset_stats(self):
        if messagebox.askyesno("Reset Statistics", "Clear all expansion counts?", parent=self.root):
            self.stats.reset()
            self._refresh_stats()
            self._flash("Statistics reset", color=YELLOW)

    # ──────────────────────────────────────────────────────────────────────
    #  Enhanced App Rules page
    # ──────────────────────────────────────────────────────────────────────

    def _build_apps(self, p):
        inner, _ = _scrolled(p)

        # Mode selection
        mode_card = _card(inner, "🎯 App Rules Mode")
        mode_card.pack(fill="x", pady=(0, 15))

        mode_frame = tk.Frame(mode_card, bg=CARD)
        mode_frame.pack(fill="x", padx=15, pady=15)

        self._app_mode_var = tk.StringVar(value=self.cfg.get("app_mode") or "all")

        modes = [
            ("all", "🌐 All Apps", "Active everywhere", GREEN),
            ("include", "✅ Whitelist", "Only in selected apps", BLUE),
            ("exclude", "❌ Blacklist", "Everywhere except selected", RED),
        ]

        for value, label, desc, color in modes:
            mode_row = tk.Frame(mode_frame, bg=CARD)
            mode_row.pack(fill="x", pady=5)

            rb = tk.Radiobutton(mode_row, text=label, variable=self._app_mode_var,
                                value=value, bg=CARD, fg=color, selectcolor=SURFACE,
                                activebackground=CARD, activeforeground=color,
                                font=("Segoe UI", 10, "bold"), cursor="hand2",
                                command=lambda: self.cfg.set("app_mode", self._app_mode_var.get()))
            rb.pack(side="left")

            tk.Label(mode_row, text=f"  -  {desc}", bg=CARD, fg=SUBTEXT,
                     font=("Segoe UI", 9)).pack(side="left", padx=(5, 0))

        # Window capture
        capture_card = _card(inner, "📱 Capture Window")
        capture_card.pack(fill="x", pady=(0, 15))

        capture_frame = tk.Frame(capture_card, bg=CARD)
        capture_frame.pack(fill="x", padx=15, pady=15)

        tk.Label(capture_frame, text="Switch to another app, then click Capture:",
                 bg=CARD, fg=SUBTEXT, font=("Segoe UI", 9)).pack(anchor="w")

        capture_input_frame = tk.Frame(capture_frame, bg=CARD)
        capture_input_frame.pack(fill="x", pady=(10, 0))

        self._captured_var = tk.StringVar(value="(waiting for window...)")
        capture_entry = _entry(capture_input_frame, self._captured_var, width=50,
                               state="readonly")
        capture_entry.pack(side="left", ipady=5)

        def _capture():
            window = _ext_window or _poll_window()
            if window:
                self._captured_var.set(window)

        _modern_button(capture_input_frame, "Capture", _capture,
                       icon="📸", style="info").pack(side="left", padx=(10, 0))

        def _add_captured():
            window = self._captured_var.get()
            if window and not window.startswith("("):
                self._add_keyword(window)

        _modern_button(capture_frame, "Add to List", _add_captured,
                       icon="➕", style="success").pack(pady=(10, 0))

        # Popular apps
        popular_card = _card(inner, "⭐ Popular Apps")
        popular_card.pack(fill="x", pady=(0, 15))

        popular_frame = tk.Frame(popular_card, bg=CARD)
        popular_frame.pack(fill="x", padx=15, pady=15)

        grid = tk.Frame(popular_frame, bg=CARD)
        grid.pack()

        for i, (label, app) in enumerate(POPULAR_APPS):
            row, col = divmod(i, 5)
            btn = tk.Button(grid, text=label, font=("Segoe UI", 9), bg=OVERLAY, fg=TEXT,
                            relief="flat", padx=12, pady=6, cursor="hand2", bd=0,
                            activebackground=ACCENT, activeforeground=BG,
                            command=lambda a=app: self._add_keyword(a))
            btn.grid(row=row, column=col, padx=3, pady=3, sticky="ew")
            grid.columnconfigure(col, weight=1)

        # App list
        list_card = _card(inner, "📋 Your App List")
        list_card.pack(fill="x", pady=(0, 15))

        list_frame = tk.Frame(list_card, bg=CARD)
        list_frame.pack(fill="x", padx=15, pady=15)

        # Listbox with scrollbar
        listbox_frame = tk.Frame(list_frame, bg=CARD)
        listbox_frame.pack(fill="x", pady=(0, 10))

        self._app_lb = tk.Listbox(listbox_frame, bg=SURFACE, fg=TEXT,
                                  selectbackground=ACCENT, selectforeground=BG,
                                  font=("Segoe UI", 10), relief="flat",
                                  activestyle="none", height=6, bd=0)
        self._app_lb.pack(side="left", fill="x", expand=True)

        list_scroll = ttk.Scrollbar(listbox_frame, orient="vertical",
                                    command=self._app_lb.yview)
        self._app_lb.configure(yscrollcommand=list_scroll.set)
        list_scroll.pack(side="right", fill="y")

        # Manual add
        manual_frame = tk.Frame(list_frame, bg=CARD)
        manual_frame.pack(fill="x", pady=(10, 0))

        self._manual_app_var = tk.StringVar()
        manual_entry = _entry(manual_frame, self._manual_app_var, width=40,
                              placeholder="Enter app name...")
        manual_entry.pack(side="left", ipady=5)

        _modern_button(manual_frame, "Add", self._add_manual_app,
                       icon="➕", style="success").pack(side="left", padx=(10, 5))
        _modern_button(manual_frame, "Remove", self._remove_app,
                       icon="🗑", style="danger").pack(side="left", padx=5)
        _modern_button(manual_frame, "Clear All", self._clear_apps,
                       icon="✖", style="warning").pack(side="left", padx=5)

        self._refresh_app_list()

    def _refresh_app_list(self):
        if not hasattr(self, "_app_lb"):
            return

        self._app_lb.delete(0, tk.END)
        apps = self.cfg.get("app_list") or []

        for app in apps:
            self._app_lb.insert(tk.END, f"  {app}")

        if hasattr(self, "_app_count_lbl"):
            self._app_count_lbl.config(text=f"({len(apps)} apps)")

    def _add_keyword(self, keyword):
        apps = self.cfg.get("app_list") or []
        if keyword not in apps:
            apps.append(keyword)
            self.cfg.set("app_list", apps)
            self._refresh_app_list()
            self._flash(f"Added: {keyword}", color=GREEN)

    def _add_manual_app(self):
        app = self._manual_app_var.get().strip()
        if app:
            self._add_keyword(app)
            self._manual_app_var.set("")

    def _remove_app(self):
        sel = self._app_lb.curselection()
        if sel:
            app = self._app_lb.get(sel[0]).strip()
            apps = self.cfg.get("app_list") or []
            if app in apps:
                apps.remove(app)
                self.cfg.set("app_list", apps)
                self._refresh_app_list()
                self._flash(f"Removed: {app}", color=YELLOW)

    def _clear_apps(self):
        if messagebox.askyesno("Clear All", "Remove all apps from the list?", parent=self.root):
            self.cfg.set("app_list", [])
            self._refresh_app_list()
            self._flash("App list cleared", color=YELLOW)

    # ──────────────────────────────────────────────────────────────────────
    #  Enhanced Settings page
    # ──────────────────────────────────────────────────────────────────────

    def _build_settings(self, p):
        inner, _ = _scrolled(p)

        # Startup settings
        startup_card = _card(inner, "🚀 Startup")
        startup_card.pack(fill="x", pady=(0, 15))

        startup_frame = tk.Frame(startup_card, bg=CARD)
        startup_frame.pack(fill="x", padx=15, pady=15)

        self._startup_var = tk.BooleanVar(value=_startup_enabled())
        toggle = _toggle_switch(startup_frame, self._startup_var,
                                command=self._toggle_startup)
        toggle.pack(side="left")

        tk.Label(startup_frame, text="Run SnapType when Windows starts",
                 bg=CARD, fg=SUBTEXT, font=("Segoe UI", 10)).pack(side="left", padx=(15, 0))

        # Hotkey settings
        hotkey_card = _card(inner, "⌨️ Hotkeys")
        hotkey_card.pack(fill="x", pady=(0, 15))

        hotkey_frame = tk.Frame(hotkey_card, bg=CARD)
        hotkey_frame.pack(fill="x", padx=15, pady=15)

        # Toggle hotkey
        toggle_row = tk.Frame(hotkey_frame, bg=CARD)
        toggle_row.pack(fill="x", pady=5)

        tk.Label(toggle_row, text="Toggle on/off:", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 10), width=15, anchor="w").pack(side="left")

        self._hk_toggle_var = tk.StringVar(value=self.cfg.get("toggle_hotkey"))
        toggle_entry = _entry(toggle_row, self._hk_toggle_var, width=20)
        toggle_entry.pack(side="left", padx=(10, 0), ipady=5)

        # Undo hotkey
        undo_row = tk.Frame(hotkey_frame, bg=CARD)
        undo_row.pack(fill="x", pady=5)

        tk.Label(undo_row, text="Undo expansion:", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 10), width=15, anchor="w").pack(side="left")

        self._hk_undo_var = tk.StringVar(value=self.cfg.get("undo_hotkey"))
        undo_entry = _entry(undo_row, self._hk_undo_var, width=20)
        undo_entry.pack(side="left", padx=(10, 0), ipady=5)

        _modern_button(hotkey_frame, "Save Hotkeys", self._save_hotkeys,
                       icon="💾", style="success").pack(pady=(10, 0))

        # Typing delay
        delay_card = _card(inner, "⚡ Typing Speed")
        delay_card.pack(fill="x", pady=(0, 15))

        delay_frame = tk.Frame(delay_card, bg=CARD)
        delay_frame.pack(fill="x", padx=15, pady=15)

        tk.Label(delay_frame, text="Replace delay (ms):", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 10)).pack(anchor="w")

        slider_frame = tk.Frame(delay_frame, bg=CARD)
        slider_frame.pack(fill="x", pady=(10, 0))

        self._delay_var = tk.IntVar(value=int(float(self.cfg.get("replace_delay") or 0.006) * 1000))

        slider = tk.Scale(slider_frame, variable=self._delay_var, from_=0, to=30,
                          orient="horizontal", bg=CARD, fg=TEXT, troughcolor=OVERLAY,
                          activebackground=ACCENT, highlightthickness=0, length=300,
                          command=lambda v: self.cfg.set("replace_delay", int(v) / 1000.0))
        slider.pack(side="left")

        delay_label = tk.Label(slider_frame, textvariable=self._delay_var,
                               bg=CARD, fg=CYAN, font=("Segoe UI", 12, "bold"))
        delay_label.pack(side="left", padx=(15, 0))
        tk.Label(slider_frame, text="ms", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 10)).pack(side="left")

        # Snooze duration
        snooze_card = _card(inner, "💤 Snooze")
        snooze_card.pack(fill="x", pady=(0, 15))

        snooze_frame = tk.Frame(snooze_card, bg=CARD)
        snooze_frame.pack(fill="x", padx=15, pady=15)

        tk.Label(snooze_frame, text="Snooze duration:", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 10)).pack(anchor="w")

        spin_frame = tk.Frame(snooze_frame, bg=CARD)
        spin_frame.pack(fill="x", pady=(10, 0))

        self._snooze_var = tk.IntVar(value=self.cfg.get("snooze_minutes") or 5)
        spin = tk.Spinbox(spin_frame, textvariable=self._snooze_var, from_=1, to=120,
                          bg=CARD, fg=TEXT, font=("Segoe UI", 10), width=10,
                          relief="flat", buttonbackground=OVERLAY,
                          command=lambda: self.cfg.set("snooze_minutes", self._snooze_var.get()))
        spin.pack(side="left")

        tk.Label(spin_frame, text="minutes", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 10)).pack(side="left", padx=(10, 0))

        # Data location
        data_card = _card(inner, "💾 Data")
        data_card.pack(fill="x", pady=(0, 15))

        data_frame = tk.Frame(data_card, bg=CARD)
        data_frame.pack(fill="x", padx=15, pady=15)

        tk.Label(data_frame, text="Data directory:", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 10)).pack(anchor="w")

        path_frame = tk.Frame(data_frame, bg=CARD)
        path_frame.pack(fill="x", pady=(10, 0))

        path_label = tk.Label(path_frame, text=str(DATA_DIR), bg=SURFACE, fg=BLUE,
                              font=("Consolas", 9), padx=10, pady=8)
        path_label.pack(side="left", fill="x", expand=True)

        def open_data_folder():
            if sys.platform == "win32":
                os.startfile(str(DATA_DIR))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(DATA_DIR)])
            else:
                subprocess.run(["xdg-open", str(DATA_DIR)])

        _modern_button(data_frame, "Open Folder", open_data_folder,
                       icon="📂", style="secondary").pack(pady=(10, 0))

        _modern_button(data_frame, "Reset Statistics", self._reset_stats,
                       icon="🗑", style="danger").pack(pady=(10, 0))

    def _toggle_startup(self):
        try:
            _set_startup(self._startup_var.get())
            self.cfg.set("startup_enabled", self._startup_var.get())
            status = "enabled" if self._startup_var.get() else "disabled"
            self._flash(f"Startup {status}", color=GREEN if self._startup_var.get() else YELLOW)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update startup setting:\n{e}", parent=self.root)
            self._startup_var.set(not self._startup_var.get())

    def _save_hotkeys(self):
        toggle = self._hk_toggle_var.get().strip()
        undo = self._hk_undo_var.get().strip()

        if not toggle or not undo:
            messagebox.showwarning("Invalid", "Both hotkeys must be specified.", parent=self.root)
            return

        self.cfg.set("toggle_hotkey", toggle)
        self.cfg.set("undo_hotkey", undo)
        self.engine.reregister()
        self._refresh_status()
        self._flash(f"Hotkeys saved: {toggle} / {undo}", color=GREEN)

    # ──────────────────────────────────────────────────────────────────────
    #  Enhanced About page
    # ──────────────────────────────────────────────────────────────────────

    def _build_about(self, p):
        import webbrowser

        inner, _ = _scrolled(p)

        # Hero section
        hero_card = _card(inner)
        hero_card.pack(fill="x", pady=(0, 15))

        hero_frame = tk.Frame(hero_card, bg=CARD)
        hero_frame.pack(fill="x", padx=20, pady=20)

        # Logo
        logo_canvas = tk.Canvas(hero_frame, width=100, height=100, bg=CARD,
                                highlightthickness=0)
        logo_canvas.pack(side="left", padx=(0, 20))

        # Draw logo
        logo_canvas.create_oval(5, 5, 95, 95, fill="#11111b", outline="#2a2a3e", width=2)
        logo_canvas.create_line(20, 30, 45, 30, 45, 40, 25, 40, 25, 50, 45, 50, 45, 70, 20, 70,
                                fill=CYAN, width=6, smooth=True)
        logo_canvas.create_line(55, 30, 80, 30, fill=PURPLE, width=6)
        logo_canvas.create_line(68, 30, 68, 70, fill=PURPLE, width=6)

        # Title
        title_frame = tk.Frame(hero_frame, bg=CARD)
        title_frame.pack(side="left", fill="both", expand=True)

        name_frame = tk.Frame(title_frame, bg=CARD)
        name_frame.pack(anchor="w")

        tk.Label(name_frame, text="Snap", bg=CARD, fg=CYAN,
                 font=("Segoe UI", 28, "bold")).pack(side="left")
        tk.Label(name_frame, text="Type", bg=CARD, fg=PURPLE,
                 font=("Segoe UI", 28, "bold")).pack(side="left")

        tk.Label(title_frame, text=f"Version {VERSION}", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 12)).pack(anchor="w", pady=(5, 0))

        tk.Label(title_frame, text="Type less. Say more.", bg=CARD, fg=ACCENT,
                 font=("Segoe UI", 12, "italic")).pack(anchor="w", pady=(5, 0))

        # Author section
        author_card = _card(inner, "👨‍💻 Author")
        author_card.pack(fill="x", pady=(0, 15))

        author_frame = tk.Frame(author_card, bg=CARD)
        author_frame.pack(fill="x", padx=15, pady=15)

        # Avatar
        avatar_canvas = tk.Canvas(author_frame, width=60, height=60, bg=CARD,
                                  highlightthickness=0)
        avatar_canvas.pack(side="left", padx=(0, 15))

        avatar_canvas.create_oval(2, 2, 58, 58, fill=ACCENT, outline="")
        avatar_canvas.create_text(30, 30, text="AR", fill=BG, font=("Segoe UI", 20, "bold"))

        # Author info
        info_frame = tk.Frame(author_frame, bg=CARD)
        info_frame.pack(side="left", fill="both", expand=True)

        tk.Label(info_frame, text="Abdul Rehman", bg=CARD, fg=TEXT,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(info_frame, text="Python Developer", bg=CARD, fg=SUBTEXT,
                 font=("Segoe UI", 10)).pack(anchor="w")
        tk.Label(info_frame, text="2026", bg=CARD, fg=OVERLAY,
                 font=("Segoe UI", 9)).pack(anchor="w")

        # Links
        links_card = _card(inner, "🔗 Connect")
        links_card.pack(fill="x", pady=(0, 15))

        links_frame = tk.Frame(links_card, bg=CARD)
        links_frame.pack(fill="x", padx=15, pady=15)

        links = [
            ("in", "LinkedIn", AUTHOR["linkedin"], BLUE, f"https://{AUTHOR['linkedin']}"),
            ("ig", "Instagram", AUTHOR["instagram"], PINK, f"https://instagram.com/{AUTHOR['instagram']}"),
            ("@", "Email", AUTHOR["email"], GREEN, f"mailto:{AUTHOR['email']}"),
        ]

        for icon, label, value, color, url in links:
            link_row = tk.Frame(links_frame, bg=CARD)
            link_row.pack(fill="x", pady=5)

            icon_frame = tk.Frame(link_row, width=30, height=30, bg=color)
            icon_frame.pack_propagate(False)
            icon_frame.pack(side="left", padx=(0, 10))

            tk.Label(icon_frame, text=icon, bg=color, fg=BG,
                     font=("Segoe UI", 12, "bold")).pack(expand=True)

            tk.Label(link_row, text=f"{label}:", bg=CARD, fg=SUBTEXT,
                     font=("Segoe UI", 10), width=10, anchor="w").pack(side="left")

            link_label = tk.Label(link_row, text=value, bg=CARD, fg=color,
                                  font=("Segoe UI", 10), cursor="hand2")
            link_label.pack(side="left")
            link_label.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))

            # Tooltip
            _create_tooltip(link_label, f"Click to open {label}")

    # ──────────────────────────────────────────────────────────────────────
    #  Tray
    # ──────────────────────────────────────────────────────────────────────

    def _run_tray(self):
        def _show(*_):
            self.root.after(0, self.root.deiconify)
            self.root.after(0, self.root.lift)

        def _toggle(*_):
            self.root.after(0, self.toggle)

        def _quit(*_):
            self.engine.stop()
            self.icon.stop()
            self.root.after(0, self.root.destroy)

        self.icon = pystray.Icon(APP_NAME,
                                 _make_tray_icon(False),
                                 title=APP_NAME,
                                 menu=pystray.Menu(
                                     pystray.MenuItem("Open SnapType", _show, default=True),
                                     pystray.MenuItem("Toggle On/Off", _toggle),
                                     pystray.Menu.SEPARATOR,
                                     pystray.MenuItem("Exit", _quit),
                                 ))
        self.icon.run()

    def _update_tray(self):
        if hasattr(self, "icon"):
            try:
                self.icon.icon = _make_tray_icon(self.active, self.snoozed)
            except:
                pass

    def _on_close(self):
        self.root.withdraw()

    def run(self):
        print(f"  {APP_NAME} v{VERSION}  |  data: {DATA_DIR}")
        self.root.mainloop()


if __name__ == "__main__":
    SnapTypeApp().run()