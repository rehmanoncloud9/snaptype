"""Reusable widgets in the Obsidian Cyber-Glass style.

Glass in Tk: rounded translucent panels cannot be drawn natively, so every panel, button and
pill is a Pillow-rendered image (cached, supersampled for smooth corners) behind real Tk
widgets. Tk keeps no reference to an image it displays, so every widget below stores the
PhotoImage it shows; dropping that reference makes the image vanish.
"""
from __future__ import annotations

import collections
import sys
import tkinter as tk
from functools import lru_cache
from tkinter import ttk

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageTk

from . import icons
from . import theme as T
from .theme import dp

_UNSET = object()


# ═══ image plumbing ═══════════════════════════════════════════════════════════
def _rgba(color: str, alpha: int = 255):
    h = color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha


@lru_cache(maxsize=400)
def _panel_pil(w, h, radius, fill, border, border_w, glow, glow_a, hl, pad):
    """Rounded panel of total size w x h. The shape is inset by ``pad`` px so a soft glow can
    bleed into the margin. ``hl`` (0-1) adds a faint light edge along the top (the glass sheen)."""
    ss = 3
    W, H = w, h
    sw, sh = max(W - 2 * pad, 2), max(H - 2 * pad, 2)
    radius = min(radius, sw // 2, sh // 2)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if glow and pad:
        g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(g).rounded_rectangle([pad, pad, pad + sw - 1, pad + sh - 1], radius=radius,
                                            fill=_rgba(glow, glow_a))
        out.alpha_composite(g.filter(ImageFilter.GaussianBlur(max(pad / 2.0, 1))))
    outer = Image.new("L", (sw * ss, sh * ss), 0)
    ImageDraw.Draw(outer).rounded_rectangle([0, 0, sw * ss - 1, sh * ss - 1], radius=radius * ss, fill=255)
    mask = outer.resize((sw, sh), Image.BOX)
    shape = Image.new("RGBA", (sw, sh), _rgba(fill)) if fill else Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    if fill:
        shape.putalpha(mask)
    ring = None
    if border and border_w:
        bw = border_w * ss
        inner = Image.new("L", (sw * ss, sh * ss), 0)
        ImageDraw.Draw(inner).rounded_rectangle([bw, bw, sw * ss - 1 - bw, sh * ss - 1 - bw],
                                                radius=max(radius * ss - bw, 0), fill=255)
        ring = ImageChops.subtract(outer, inner).resize((sw, sh), Image.BOX)
        layer = Image.new("RGBA", (sw, sh), _rgba(border))
        layer.putalpha(ring)
        shape.alpha_composite(layer)
    if hl and fill:
        fade = Image.linear_gradient("L").transpose(Image.FLIP_TOP_BOTTOM).resize((sw, sh))
        edge = ring if ring is not None else ImageChops.subtract(
            outer, outer.filter(ImageFilter.MinFilter(3))).resize((sw, sh), Image.BOX)
        light = Image.new("RGBA", (sw, sh), (255, 255, 255, 255))
        light.putalpha(ImageChops.multiply(edge, fade.point(lambda v: int(v * hl))))
        shape.alpha_composite(light)
    out.alpha_composite(shape, (pad, pad))
    return out


_PHOTOS: "collections.OrderedDict" = collections.OrderedDict()


def panel_photo(w, h, radius, fill, border=None, glow=None, glow_a=0, hl=0.0, pad=0, border_w=None):
    """PhotoImage for a panel. Callers must keep the returned object referenced while shown."""
    bw = (dp(1) if border else 0) if border_w is None else border_w
    key = (int(w), int(h), int(radius), fill, border, bw, glow, glow_a, hl, pad)
    ph = _PHOTOS.get(key)
    if ph is None:
        ph = ImageTk.PhotoImage(_panel_pil(*key))
        _PHOTOS[key] = ph
        if len(_PHOTOS) > 300:
            _PHOTOS.popitem(last=False)      # evicted images stay alive while a widget holds them
    else:
        _PHOTOS.move_to_end(key)
    return ph


_ICON_PHOTOS: dict = {}


def icon_photo(name: str, px: int, color: str, stroke: float = 2.0):
    """Cached PhotoImage of an icon. Kept forever (the icon set is small)."""
    key = (name, px, color, stroke)
    if key not in _ICON_PHOTOS:
        _ICON_PHOTOS[key] = ImageTk.PhotoImage(icons.icon_image(name, px, color, stroke))
    return _ICON_PHOTOS[key]


def _clear_image_caches() -> None:
    """PhotoImages belong to one Tk interpreter. A new root (tests, or a restart in-process)
    must not reuse images from the old one."""
    _PHOTOS.clear()
    _ICON_PHOTOS.clear()


T._reset_hooks.append(_clear_image_caches)


def bg_of(widget) -> str:
    try:
        return widget.cget("bg")
    except tk.TclError:
        return T.VOID


# ═══ text helpers ═════════════════════════════════════════════════════════════
def label(parent, text="", role="body", color=T.TEXT, bg=None, **kw) -> tk.Label:
    kw.setdefault("anchor", "w")
    return tk.Label(parent, text=text, font=T.font(role), fg=color, bg=bg or bg_of(parent), bd=0,
                    highlightthickness=0, **kw)


def icon_label(parent, name: str, px: int = 18, color: str = T.TEXT_DIM, bg=None) -> tk.Label:
    ph = icon_photo(name, dp(px), color)
    lb = tk.Label(parent, image=ph, bg=bg or bg_of(parent), bd=0, highlightthickness=0)
    lb.image = ph
    return lb


def set_icon(lb: tk.Label, name: str, px: int, color: str) -> None:
    ph = icon_photo(name, dp(px), color)
    lb.configure(image=ph)
    lb.image = ph


def caps_label(parent, text, color=T.TEXT_FAINT, bg=None) -> tk.Label:
    """Micro-label in the spec's mono-label style (upper-case mono)."""
    return label(parent, text.upper(), "label", color, bg)


def divider(parent, color=T.DIVIDER, pady=0) -> tk.Frame:
    return tk.Frame(parent, bg=color, height=max(1, dp(1)))


# ═══ surfaces ═════════════════════════════════════════════════════════════════
class Surface(tk.Frame):
    """A rounded glass panel. Put children in ``.body``; pack/grid the Surface itself."""

    def __init__(self, parent, radius=T.R_LG, fill=T.PANEL, border=T.BORDER, glow=None, glow_a=0, hl=0.55,
                 pad=0, bg=None, **kw):
        bg = bg or bg_of(parent)
        super().__init__(parent, bg=bg, bd=0, highlightthickness=0, **kw)
        self.radius, self.fill, self.border, self.glow, self.glow_a, self.hl, self.pad = (
            dp(radius), fill, border, glow, glow_a, hl, dp(pad))
        self._photo = None
        self._painted = None
        self._job = None
        self._img = tk.Label(self, bd=0, highlightthickness=0, bg=bg)
        self._img.place(x=0, y=0)
        inset = self.pad + dp(round(radius * 0.3) + 1)
        self.body = tk.Frame(self, bg=fill, bd=0, highlightthickness=0)
        self.body.pack(fill="both", expand=True, padx=inset, pady=inset)
        self.bind("<Configure>", self._on_configure, add="+")

    def set_look(self, border=_UNSET, glow=_UNSET, glow_a=_UNSET):
        if border is not _UNSET:
            self.border = border
        if glow is not _UNSET:
            self.glow = glow
        if glow_a is not _UNSET:
            self.glow_a = glow_a
        self._paint()

    def _on_configure(self, _event=None):
        if self._painted is None:
            self._paint()
            return
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(30, self._paint)

    def _paint(self):
        self._job = None
        w, h = self.winfo_width(), self.winfo_height()
        if w < 4 or h < 4:
            return
        key = (w, h, self.border, self.glow, self.glow_a)
        if key == self._painted:
            return
        self._painted = key
        self._photo = panel_photo(w, h, self.radius, self.fill, self.border, self.glow, self.glow_a, self.hl, self.pad)
        self._img.configure(image=self._photo)
        self._img.lower()


class Card(Surface):
    """Titled panel: optional icon + title (+ right-side actions), then ``.content``."""

    def __init__(self, parent, title=None, icon=None, subtitle=None, pad_x=20, pad_y=18, **kw):
        super().__init__(parent, **kw)
        self.header = None
        self.actions = None
        b = self.body
        if title:
            self.header = tk.Frame(b, bg=self.fill)
            self.header.pack(fill="x", padx=dp(pad_x), pady=(dp(pad_y), 0))
            if icon:
                icon_label(self.header, icon, 18, T.CYAN, self.fill).pack(side="left", padx=(0, dp(10)))
            col = tk.Frame(self.header, bg=self.fill)
            col.pack(side="left", fill="x", expand=True)
            label(col, title, "heading", T.TEXT, self.fill).pack(anchor="w")
            if subtitle:
                label(col, subtitle, "small", T.TEXT_DIM, self.fill, wraplength=dp(520), justify="left").pack(anchor="w")
            self.actions = tk.Frame(self.header, bg=self.fill)
            self.actions.pack(side="right")
        self.content = tk.Frame(b, bg=self.fill)
        self.content.pack(fill="both", expand=True, padx=dp(pad_x), pady=(dp(12) if title else dp(pad_y), dp(pad_y)))


# ═══ buttons ══════════════════════════════════════════════════════════════════
GLOW = 5          # px reserved around every button for the hover/focus glow


def _lift(color, amount):
    return T.blend(T.WHITE, amount, color)


def _button_look(variant: str, state: str):
    """(fill, border, text colour, glow colour, glow alpha) for a variant in a state."""
    hov, down, foc, dis = state == "hover", state == "down", state == "focus", state == "disabled"
    if dis:
        if variant == "ghost" or variant == "quiet":
            return None, None, T.TEXT_DISABLED, None, 0
        return T.PANEL_HOVER, T.BORDER, T.TEXT_DISABLED, None, 0
    if variant == "primary":
        fill = T.CYAN_DIM if down else (_lift(T.CYAN, 0.22) if hov else T.CYAN)
        return fill, (T.CYAN if foc else None), T.ON_CYAN, T.CYAN, (130 if hov else 90 if foc else 0)
    if variant == "danger":
        fill = T.blend(T.ERROR_DEEP, 0.75 if (hov or down) else 0.45, T.PANEL)
        return fill, T.blend(T.ERROR, 0.5 if (hov or foc) else 0.28, T.PANEL), T.ERROR, T.ERROR, (70 if hov or foc else 0)
    if variant == "ghost":
        return (T.PANEL_HOVER if hov or down else None), (T.CYAN if foc else None), (T.TEXT if hov else T.TEXT_DIM), None, 0
    if variant == "quiet":     # icon-only
        return (T.PANEL_HOVER if hov or down else None), (T.CYAN if foc else None), T.TEXT_DIM, None, 0
    if variant == "chip":
        return (_lift(T.PANEL_HOVER, 0.05) if hov else T.PANEL_HOVER), (T.CYAN if foc else T.BORDER), T.TEXT_DIM, None, 0
    if variant == "chip_on":
        return T.CYAN_TINT_PANEL, (T.CYAN if foc else T.blend(T.CYAN, 0.55, T.PANEL)), T.CYAN, None, 0
    # secondary
    fill = _lift(T.PANEL_HOVER, 0.07) if (hov or down) else T.PANEL_HOVER
    return fill, (T.CYAN if foc else (T.blend(T.CYAN, 0.45, T.PANEL) if hov else T.BORDER_STRONG)), T.TEXT, \
        T.CYAN, (60 if foc else 0)


class Button(tk.Canvas):
    """Pill/rounded button drawn from a cached image. Tab-focusable, Enter/Space activate, the
    action runs on mouse *release* inside the button (so you can slide off to cancel)."""

    def __init__(self, parent, text="", command=None, icon=None, variant="secondary", size="md", min_width=0,
                 bg=None, tooltip=None, state="normal"):
        self._g = dp(GLOW)
        super().__init__(parent, bd=0, highlightthickness=0, bg=bg or bg_of(parent), takefocus=1, width=10, height=10)
        self._cfg = dict(text=text, command=command, icon=icon, variant=variant, size=size, min_width=min_width,
                         state=state)
        self._hover = self._down = self._focus = False
        self._photo = self._icon_ph = None
        self._measure()
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self.bind("<ButtonPress-1>", self._on_press, add="+")
        self.bind("<ButtonRelease-1>", self._on_release, add="+")
        self.bind("<FocusIn>", lambda e: self._set_flag("_focus", True), add="+")
        self.bind("<FocusOut>", lambda e: self._set_flag("_focus", False), add="+")
        self.bind("<Return>", self._activate, add="+")
        self.bind("<space>", self._activate, add="+")
        if tooltip:
            Tooltip(self, tooltip)

    # -- layout --
    def _measure(self):
        c = self._cfg
        small = c["size"] == "sm"
        self._bh = dp(30 if small else 38)
        font = T.font("small_b" if small else "body_b")
        self._font = font
        icon_only = bool(c["icon"]) and not c["text"]
        self._icon_px = dp(14 if small else 16)
        tw = font.measure(c["text"]) if c["text"] else 0
        pad = dp(10 if small else 16)
        gap = dp(8) if (c["icon"] and c["text"]) else 0
        iw = self._icon_px if c["icon"] else 0
        w = self._bh if icon_only else pad * 2 + iw + gap + tw
        self._bw = max(w, dp(c["min_width"]))
        self.configure(width=self._bw + self._g * 2, height=self._bh + self._g * 2)
        self._paint()

    def update_button(self, **kw):
        """Change text/icon/variant/command/state in place (no rebuild, no flicker)."""
        self._cfg.update(kw)
        self._measure()

    # -- painting --
    def _state(self):
        if self._cfg["state"] == "disabled":
            return "disabled"
        if self._down and self._hover:
            return "down"
        if self._hover:
            return "hover"
        return "focus" if self._focus else "normal"

    def _paint(self):
        c, g = self._cfg, self._g
        st = self._state()
        fill, border, fg, glow, glow_a = _button_look(c["variant"], st)
        h = self._bh + g * 2
        radius = self._bh // 2 if c["variant"] in ("chip", "chip_on") else dp(T.R_MD)
        self.delete("all")
        if fill or border:
            self._photo = panel_photo(self._bw + g * 2, h, radius, fill, border, glow, glow_a, 0.35 if fill else 0.0, g,
                                      border_w=dp(1))
            self.create_image(0, 0, image=self._photo, anchor="nw")
        cx, cy = g + self._bw / 2, g + self._bh / 2
        has_icon, has_text = bool(c["icon"]), bool(c["text"])
        if has_icon:
            self._icon_ph = icon_photo(c["icon"], self._icon_px, fg)
        if has_icon and has_text:
            tw = self._font.measure(c["text"])
            total = self._icon_px + dp(8) + tw
            x0 = cx - total / 2
            self.create_image(x0, cy, image=self._icon_ph, anchor="w")
            self.create_text(x0 + self._icon_px + dp(8), cy, text=c["text"], font=self._font, fill=fg, anchor="w")
        elif has_icon:
            self.create_image(cx, cy, image=self._icon_ph, anchor="center")
        else:
            self.create_text(cx, cy, text=c["text"], font=self._font, fill=fg, anchor="center")
        self.configure(cursor="arrow" if c["state"] == "disabled" else "hand2")

    # -- events --
    def _set_flag(self, name, value):
        setattr(self, name, value)
        self._paint()

    def _on_enter(self, _e):
        self._set_flag("_hover", True)

    def _on_leave(self, _e):
        self._hover = self._down = False
        self._paint()

    def _on_press(self, _e):
        if self._cfg["state"] != "disabled":
            self._set_flag("_down", True)

    def _on_release(self, e):
        was_down = self._down
        self._down = False
        inside = 0 <= e.x < self.winfo_width() and 0 <= e.y < self.winfo_height()
        self._paint()
        if was_down and inside:
            self._activate()

    def _activate(self, _e=None):
        if self._cfg["state"] != "disabled" and self._cfg["command"]:
            self._cfg["command"]()
        return "break"


# ═══ tooltip ══════════════════════════════════════════════════════════════════
class Tooltip:
    """Hover/focus tooltip. Uses add='+' so it never replaces a widget's own bindings, shows after
    a short delay, and only one tip exists at a time."""
    _current = None

    def __init__(self, widget, text, delay=450):
        self.widget, self.text, self.delay = widget, text, delay
        self._job = None
        self._tip = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self.hide, add="+")
        widget.bind("<ButtonPress>", self.hide, add="+")
        widget.bind("<Destroy>", self.hide, add="+")

    def _schedule(self, _e=None):
        self.hide()
        self._job = self.widget.after(self.delay, self.show)

    def show(self):
        self._job = None
        text = self.text() if callable(self.text) else self.text
        if not text or not self.widget.winfo_exists():
            return
        if Tooltip._current is not None:
            Tooltip._current.hide()
        tip = tk.Toplevel(self.widget)
        tip.wm_overrideredirect(True)
        try:
            tip.wm_attributes("-topmost", True)
        except tk.TclError:
            pass
        outer = tk.Frame(tip, bg=T.BORDER_STRONG, bd=0, highlightthickness=0)
        outer.pack()
        tk.Label(outer, text=text, font=T.font("small"), fg=T.TEXT, bg=T.PANEL_HOVER, padx=dp(10), pady=dp(5),
                 bd=0, justify="left").pack(padx=1, pady=1)
        x = self.widget.winfo_rootx() + dp(8)
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + dp(6)
        sw, sh = self.widget.winfo_screenwidth(), self.widget.winfo_screenheight()
        tip.update_idletasks()
        x = max(0, min(x, sw - tip.winfo_reqwidth() - 8))
        if y + tip.winfo_reqheight() > sh - 8:
            y = self.widget.winfo_rooty() - tip.winfo_reqheight() - dp(6)
        tip.wm_geometry(f"+{x}+{y}")
        self._tip = tip
        Tooltip._current = self

    def hide(self, _e=None):
        if self._job is not None:
            try:
                self.widget.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None
        if Tooltip._current is self:
            Tooltip._current = None


# ═══ fields ═══════════════════════════════════════════════════════════════════
class Field(Surface):
    """Single-line input: darker than the page, glowing border on focus, working placeholder
    (click-through, works with a bound variable), optional leading icon and clear button."""

    def __init__(self, parent, variable=None, placeholder="", icon=None, mono=False, width=24, clearable=False,
                 readonly=False, command=None):
        super().__init__(parent, radius=T.R_MD, fill=T.INPUT, border=T.BORDER, hl=0.0, pad=3)
        self.var = variable if variable is not None else tk.StringVar()
        self._placeholder, self._readonly, self._clearable = placeholder, readonly, clearable
        row = tk.Frame(self.body, bg=T.INPUT)
        row.pack(fill="both", expand=True, padx=(dp(6), dp(4)), pady=dp(5))
        if icon:
            icon_label(row, icon, 16, T.TEXT_FAINT, T.INPUT).pack(side="left", padx=(0, dp(8)))
        self.entry = tk.Entry(row, textvariable=self.var, width=width, bd=0, relief="flat", highlightthickness=0,
                              bg=T.INPUT, fg=T.TEXT, insertbackground=T.CYAN, selectbackground=T.CYAN_DEEP,
                              selectforeground=T.TEXT, readonlybackground=T.INPUT, disabledforeground=T.TEXT_DISABLED,
                              font=T.font("mono" if mono else "body"))
        if readonly:
            self.entry.configure(state="readonly")
        self.entry.pack(side="left", fill="x", expand=True, ipady=dp(2))
        self._clear = None
        if clearable:
            self._clear = icon_label(row, "x", 14, T.TEXT_FAINT, T.INPUT)
            self._clear.configure(cursor="hand2")
            self._clear.bind("<ButtonPress-1>", lambda e: self.clear(), add="+")
        self._ph = None
        if placeholder:
            self._ph = tk.Label(row, text=placeholder, font=T.font("mono" if mono else "body"), fg=T.TEXT_FAINT,
                                bg=T.INPUT, bd=0, anchor="w", cursor="xterm")
            self._ph.bind("<ButtonPress-1>", lambda e: self.entry.focus_set(), add="+")   # click-through
        self.var.trace_add("write", lambda *_: self._sync())
        self.entry.bind("<FocusIn>", lambda e: self._focus(True), add="+")
        self.entry.bind("<FocusOut>", lambda e: self._focus(False), add="+")
        if command:
            self.entry.bind("<Return>", lambda e: command(), add="+")
        self._error = False
        self._sync()

    def _sync(self):
        has = bool(self.var.get())
        if self._ph is not None:
            if has:
                self._ph.place_forget()
            else:
                self._ph.place(in_=self.entry, x=0, rely=0.5, anchor="w")
        if self._clear is not None:
            if has and not self._readonly:
                self._clear.pack(side="right")
            else:
                self._clear.pack_forget()

    def _focus(self, on):
        if self._error:
            return
        self.set_look(border=T.CYAN if on else T.BORDER, glow=T.CYAN if on else None, glow_a=70 if on else 0)

    def set_error(self, on: bool):
        self._error = on
        self.set_look(border=T.ERROR if on else T.BORDER, glow=T.ERROR if on else None, glow_a=60 if on else 0)

    def clear(self):
        self.var.set("")
        self.entry.focus_set()

    def focus(self):
        self.entry.focus_set()


class TextArea(Surface):
    """Multi-line input with the same look and a click-through placeholder."""

    def __init__(self, parent, placeholder="", height=4, mono=False, on_change=None, on_submit=None):
        super().__init__(parent, radius=T.R_MD, fill=T.INPUT, border=T.BORDER, hl=0.0, pad=3)
        self._on_change = on_change
        self._placeholder = placeholder
        self.text = tk.Text(self.body, height=height, wrap="word", bd=0, relief="flat", highlightthickness=0,
                            bg=T.INPUT, fg=T.TEXT, insertbackground=T.CYAN, selectbackground=T.CYAN_DEEP,
                            selectforeground=T.TEXT, padx=dp(8), pady=dp(8), undo=True,
                            font=T.font("mono" if mono else "body"))
        self.text.pack(fill="both", expand=True)
        self._ph = tk.Label(self.text, text=placeholder, font=T.font("mono" if mono else "body"), fg=T.TEXT_FAINT,
                            bg=T.INPUT, bd=0, anchor="nw", justify="left", cursor="xterm")
        self._ph.bind("<ButtonPress-1>", lambda e: self.text.focus_set(), add="+")
        self.text.bind("<<Modified>>", self._modified, add="+")
        self.text.bind("<FocusIn>", lambda e: self._focus(True), add="+")
        self.text.bind("<FocusOut>", lambda e: self._focus(False), add="+")
        if on_submit:
            self.text.bind("<Control-Return>", lambda e: (on_submit(), "break")[1], add="+")
        self._sync()

    def _modified(self, _e=None):
        if self.text.edit_modified():
            self.text.edit_modified(False)
            self._changed()

    def _changed(self):
        self._sync()
        if self._on_change:
            self._on_change()

    def _sync(self):
        if self.value():
            self._ph.place_forget()
        else:
            self._ph.place(x=dp(8), y=dp(8))

    def _focus(self, on):
        self.set_look(border=T.CYAN if on else T.BORDER, glow=T.CYAN if on else None, glow_a=70 if on else 0)

    def value(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set_value(self, s: str):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", s)
        self.text.edit_modified(False)
        self._changed()

    def insert_at_cursor(self, s: str):
        self.text.insert("insert", s)
        self.text.focus_set()
        self._changed()

    def focus(self):
        self.text.focus_set()


# ═══ small controls ═══════════════════════════════════════════════════════════
class Toggle(tk.Canvas):
    """Switch with a short slide animation. Space/Enter toggle it; a ring shows keyboard focus."""
    W, H = 46, 26

    def __init__(self, parent, variable, command=None, bg=None):
        self._bw, self._bh = dp(self.W), dp(self.H)
        super().__init__(parent, width=self._bw + 2 * dp(3), height=self._bh + 2 * dp(3), bd=0, highlightthickness=0,
                         bg=bg or bg_of(parent), takefocus=1, cursor="hand2")
        self.var, self.command = variable, command
        self._pos = 1.0 if variable.get() else 0.0
        self._job = None
        self._focus = False
        self._photos = []
        self.bind("<ButtonPress-1>", lambda e: self.toggle(), add="+")
        self.bind("<space>", lambda e: (self.toggle(), "break")[1], add="+")
        self.bind("<Return>", lambda e: (self.toggle(), "break")[1], add="+")
        self.bind("<FocusIn>", lambda e: self._set_focus(True), add="+")
        self.bind("<FocusOut>", lambda e: self._set_focus(False), add="+")
        self._paint()

    def _set_focus(self, on):
        self._focus = on
        self._paint()

    def toggle(self):
        self.var.set(not self.var.get())
        self._animate()
        if self.command:
            self.command()

    def sync(self):
        """Re-read the variable (after it was changed from elsewhere)."""
        self._pos = 1.0 if self.var.get() else 0.0
        self._paint()

    def _animate(self, step=0):
        target = 1.0 if self.var.get() else 0.0
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        if step >= 6:
            self._pos = target
            self._paint()
            return
        self._pos += (target - self._pos) * 0.5
        self._paint()
        self._job = self.after(16, lambda: self._animate(step + 1))

    def _paint(self):
        g = dp(3)
        on = self._pos >= 0.5
        self.delete("all")
        track = panel_photo(self._bw + 2 * g, self._bh + 2 * g, self._bh // 2,
                            T.CYAN if on else T.PANEL_HOVER,
                            T.CYAN if self._focus else (None if on else T.BORDER_STRONG),
                            T.CYAN if on else None, 80 if on else 0, 0.0, g, border_w=dp(1))
        kd = self._bh - dp(8)
        knob = panel_photo(kd, kd, kd // 2, T.ON_CYAN if on else T.TEXT_DIM, None, None, 0, 0.0, 0)
        self._photos = [track, knob]
        self.create_image(0, 0, image=track, anchor="nw")
        x = g + dp(4) + (self._bw - kd - dp(8)) * self._pos
        self.create_image(x, g + dp(4), image=knob, anchor="nw")


class Slider(tk.Canvas):
    """Integer slider: click/drag or Left/Right/Home/End."""

    def __init__(self, parent, variable, lo, hi, width=260, command=None, bg=None):
        self._bw, self._bh = dp(width), dp(28)
        super().__init__(parent, width=self._bw, height=self._bh, bd=0, highlightthickness=0, bg=bg or bg_of(parent),
                         takefocus=1, cursor="hand2")
        self.var, self.lo, self.hi, self.command = variable, lo, hi, command
        self._focus = False
        self._pad = dp(10)
        self.bind("<ButtonPress-1>", self._drag, add="+")
        self.bind("<B1-Motion>", self._drag, add="+")
        self.bind("<Left>", lambda e: self._nudge(-1), add="+")
        self.bind("<Right>", lambda e: self._nudge(1), add="+")
        self.bind("<Home>", lambda e: self._set(self.lo), add="+")
        self.bind("<End>", lambda e: self._set(self.hi), add="+")
        self.bind("<FocusIn>", lambda e: self._focus_set(True), add="+")
        self.bind("<FocusOut>", lambda e: self._focus_set(False), add="+")
        self._paint()

    def _focus_set(self, on):
        self._focus = on
        self._paint()

    def _set(self, v):
        v = min(max(int(round(v)), self.lo), self.hi)
        changed = v != self.var.get()
        self.var.set(v)
        self._paint()
        if changed and self.command:
            self.command(v)
        return "break"

    def _nudge(self, d):
        return self._set(self.var.get() + d)

    def _drag(self, e):
        span = max(self._bw - 2 * self._pad, 1)
        self._set(self.lo + (e.x - self._pad) / span * (self.hi - self.lo))

    def _paint(self):
        self.delete("all")
        y, p = self._bh / 2, self._pad
        frac = (self.var.get() - self.lo) / max(self.hi - self.lo, 1)
        x = p + (self._bw - 2 * p) * frac
        self.create_line(p, y, self._bw - p, y, width=dp(4), fill=T.BORDER_STRONG, capstyle="round")
        if frac > 0:
            self.create_line(p, y, x, y, width=dp(4), fill=T.CYAN, capstyle="round")
        r = dp(8)
        if self._focus:
            self.create_oval(x - r - dp(4), y - r - dp(4), x + r + dp(4), y + r + dp(4), outline=T.CYAN, width=dp(2))
        self.create_oval(x - r, y - r, x + r, y + r, fill=T.TEXT, outline=T.CYAN, width=dp(2))


class Stepper(tk.Frame):
    """[-] value [+] over a list of sensible values."""

    def __init__(self, parent, variable, values, fmt="{}", command=None):
        super().__init__(parent, bg=bg_of(parent))
        self.var, self.values, self.fmt, self.command = variable, sorted(set(values)), fmt, command
        cur = variable.get()
        if cur not in self.values:
            self.values = sorted(set(self.values) | {cur})
        self.minus = Button(self, icon="minus", variant="secondary", size="sm", command=lambda: self.step(-1))
        self.minus.pack(side="left")
        self.value = label(self, "", "body_b", T.TEXT, anchor="center")
        self.value.configure(width=8)
        self.value.pack(side="left")
        self.plus = Button(self, icon="plus", variant="secondary", size="sm", command=lambda: self.step(1))
        self.plus.pack(side="left")
        self._show()

    def _show(self):
        v = self.var.get()
        self.value.configure(text=self.fmt.format(v))
        i = self.values.index(v)
        self.minus.update_button(state="disabled" if i == 0 else "normal")
        self.plus.update_button(state="disabled" if i == len(self.values) - 1 else "normal")

    def step(self, d):
        i = min(max(self.values.index(self.var.get()) + d, 0), len(self.values) - 1)
        self.var.set(self.values[i])
        self._show()
        if self.command:
            self.command(self.values[i])


class Pill(tk.Canvas):
    """Small rounded status/tag pill with optional dot."""

    def __init__(self, parent, text="", fg=T.TEXT_DIM, fill=T.PANEL_HOVER, border=T.BORDER, dot=None, bg=None,
                 role="small_b"):
        super().__init__(parent, bd=0, highlightthickness=0, bg=bg or bg_of(parent), width=10, height=10)
        self._role = role
        self._photo = None
        self._text, self._fg, self._fill, self._border, self._dot = text, fg, fill, border, dot
        self._render()

    def set(self, text=None, fg=None, fill=None, border=_UNSET, dot=_UNSET):
        if text is not None:
            self._text = text
        if fg is not None:
            self._fg = fg
        if fill is not None:
            self._fill = fill
        if border is not _UNSET:
            self._border = border
        if dot is not _UNSET:
            self._dot = dot
        self._render()

    def _render(self):
        font = T.font(self._role)
        h, pad = dp(26), dp(12)
        dot_w = dp(14) if self._dot else 0
        w = pad * 2 + dot_w + font.measure(self._text)
        self.configure(width=w, height=h)
        self.delete("all")
        self._photo = panel_photo(w, h, h // 2, self._fill, self._border, None, 0, 0.0, 0, border_w=dp(1))
        self.create_image(0, 0, image=self._photo, anchor="nw")
        x = pad
        if self._dot:
            r = dp(4)
            self.create_oval(x, h / 2 - r, x + 2 * r, h / 2 + r, fill=self._dot, outline="")
            x += dot_w
        self.create_text(x, h / 2, text=self._text, font=font, fill=self._fg, anchor="w")


class Keycaps(tk.Frame):
    """A shortcut drawn as keycaps: [Ctrl] [Shift] [S]."""

    def __init__(self, parent, parts=(), bg=None):
        super().__init__(parent, bg=bg or bg_of(parent))
        self.set(parts)

    def set(self, parts):
        for w in self.winfo_children():
            w.destroy()
        for p in parts:
            tk.Label(self, text=p, font=T.font("mono_s"), fg=T.TEXT, bg=T.PANEL_HOVER, bd=0, padx=dp(8), pady=dp(3),
                     highlightthickness=1, highlightbackground=T.BORDER_STRONG).pack(side="left", padx=(0, dp(4)))


# ═══ scrolling ════════════════════════════════════════════════════════════════
class ScrollFrame(tk.Frame):
    """Vertically scrolling container. The thin scrollbar floats over the right edge and only
    appears when the content is taller than the view, so the layout never shifts."""

    def __init__(self, parent, bg=T.VOID, pad_right=14):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, bd=0, highlightthickness=0, yscrollincrement=dp(16))
        self.canvas._snap_scroll = True
        self.sb = ttk.Scrollbar(self, orient="vertical", style="SN.Vertical.TScrollbar", command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self._pad_right = dp(pad_right)
        self._sb_shown = False
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.pack(fill="both", expand=True)
        self.inner.bind("<Configure>", self._on_inner, add="+")
        self.canvas.bind("<Configure>", self._on_canvas, add="+")

    def _on_inner(self, _e=None):
        self.canvas.configure(scrollregion=(0, 0, self.inner.winfo_reqwidth(), self.inner.winfo_reqheight()))

    def _on_canvas(self, e):
        self.canvas.itemconfigure(self._win, width=max(e.width - self._pad_right, 1))

    def _on_scroll(self, first, last):
        self.sb.set(first, last)
        need = float(first) > 0.0 or float(last) < 1.0
        if need and not self._sb_shown:
            self.sb.place(relx=1.0, rely=0.0, relheight=1.0, anchor="ne", width=dp(8))
            self._sb_shown = True
        elif not need and self._sb_shown:
            self.sb.place_forget()
            self._sb_shown = False

    def scroll_top(self):
        self.canvas.yview_moveto(0)


def install_wheel_router(root: tk.Misc) -> None:
    """One mouse-wheel handler for the whole app: scroll whatever is *under the pointer*, falling
    back to the next scrollable ancestor when that widget is already at its limit. Replaces the
    per-widget focus-stealing tricks (which moved keyboard focus just by hovering)."""
    for cls in ("Treeview", "Text", "Listbox", "TScrollbar", "Scrollbar"):
        try:
            root.unbind_class(cls, "<MouseWheel>")
        except tk.TclError:
            pass

    def try_scroll(w, direction, steps):
        scrollable = isinstance(w, (ttk.Treeview, tk.Text)) or getattr(w, "_snap_scroll", False)
        if not scrollable:
            return False
        first, last = w.yview()
        if (direction < 0 and first <= 0.0) or (direction > 0 and last >= 1.0):
            return False
        w.yview_scroll(direction * steps, "units")
        return True

    def route(event, direction=None, steps=None):
        try:
            w = root.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            return None
        if direction is None:
            direction = -1 if event.delta > 0 else 1
            steps = max(1, abs(event.delta) // 120) * 3 if abs(event.delta) >= 120 else 1
        while w is not None:
            if try_scroll(w, direction, steps):
                return "break"
            w = getattr(w, "master", None)
        return None

    root.bind_all("<MouseWheel>", route, add="+")
    if sys.platform not in ("win32", "darwin"):          # X11 reports the wheel as buttons 4/5
        root.bind_all("<Button-4>", lambda e: route(e, -1, 3), add="+")
        root.bind_all("<Button-5>", lambda e: route(e, 1, 3), add="+")


def style_ttk(root: tk.Misc) -> None:
    """Dark Treeview and slim scrollbar styles ("SN.*")."""
    st = ttk.Style(root)
    st.theme_use("clam")
    sel_bg = T.blend(T.CYAN, 0.20, T.PANEL)
    st.configure("SN.Treeview", background=T.PANEL, fieldbackground=T.PANEL, foreground=T.TEXT, borderwidth=0,
                 rowheight=dp(38), font=T.font("body"), relief="flat")
    st.map("SN.Treeview", background=[("selected", sel_bg)], foreground=[("selected", T.TEXT)])
    st.layout("SN.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    st.configure("SN.Treeview.Heading", background=T.PANEL, foreground=T.TEXT_FAINT, font=T.font("label"),
                 relief="flat", borderwidth=0, padding=(dp(8), dp(8)), bordercolor=T.PANEL, lightcolor=T.PANEL,
                 darkcolor=T.PANEL)
    st.map("SN.Treeview.Heading", background=[("active", T.PANEL_HOVER)], foreground=[("active", T.TEXT)])
    st.layout("SN.Vertical.TScrollbar", [("Vertical.Scrollbar.trough", {
        "sticky": "ns", "children": [("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
    st.configure("SN.Vertical.TScrollbar", background=T.BORDER_STRONG, troughcolor=T.VOID, bordercolor=T.VOID,
                 lightcolor=T.BORDER_STRONG, darkcolor=T.BORDER_STRONG, relief="flat", borderwidth=0)
    st.map("SN.Vertical.TScrollbar", background=[("active", T.TEXT_FAINT), ("pressed", T.TEXT_DIM)],
           lightcolor=[("active", T.TEXT_FAINT)], darkcolor=[("active", T.TEXT_FAINT)])


# ═══ toast ════════════════════════════════════════════════════════════════════
_TOAST = {"success": ("check_circle", T.CYAN), "info": ("info", T.AMETHYST), "warn": ("alert", T.AMBER),
          "error": ("alert", T.ERROR)}


class ToastHost:
    """One non-blocking message at a time, bottom-right of ``parent``. A new toast replaces the
    old one and restarts the timer (stacked ``after`` calls used to clear newer messages early)."""

    def __init__(self, parent):
        self.parent = parent
        self._frame = None
        self._job = None

    def show(self, message: str, kind: str = "info", action=None, ms: int = 4500):
        self.dismiss()
        icon, color = _TOAST.get(kind, _TOAST["info"])
        card = Surface(self.parent, radius=T.R_MD, fill=T.PANEL_HOVER, border=T.blend(color, 0.45, T.PANEL), hl=0.3)
        row = tk.Frame(card.body, bg=T.PANEL_HOVER)
        row.pack(padx=dp(12), pady=dp(8))
        icon_label(row, icon, 18, color, T.PANEL_HOVER).pack(side="left", padx=(0, dp(10)))
        label(row, message, "body", T.TEXT, T.PANEL_HOVER, wraplength=dp(360), justify="left").pack(side="left")
        if action:
            text, fn = action
            Button(row, text=text, variant="ghost", size="sm", bg=T.PANEL_HOVER,
                   command=lambda: (self.dismiss(), fn())).pack(side="left", padx=(dp(8), 0))
            ms = max(ms, 7000)
        card.place(relx=1.0, rely=1.0, x=-dp(24), y=-dp(20), anchor="se")
        card.lift()
        self._frame = card
        self._job = self.parent.after(ms, self.dismiss)

    def dismiss(self):
        if self._job is not None:
            try:
                self.parent.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        if self._frame is not None:
            try:
                self._frame.destroy()
            except tk.TclError:
                pass
            self._frame = None
