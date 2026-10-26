"""Building blocks shared by several pages."""
from __future__ import annotations

import tkinter as tk

from .. import theme as T
from ..theme import dp
from ..widgets import Card, Surface, caps_label, divider, icon_label, label


def clip(text: str, n: int = 64) -> str:
    """One-line preview of possibly multi-line text."""
    one = text.replace("\r", "").replace("\n", " \u21b5 ")
    return one if len(one) <= n else one[: n - 1].rstrip() + "\u2026"


class MetricCard(Card):
    """Caption, one big number, one supporting line (and optionally a chart in ``.extra``)."""

    def __init__(self, parent, caption: str, color: str = T.CYAN):
        super().__init__(parent, pad_x=18, pad_y=16)
        c = self.content
        caps_label(c, caption, T.TEXT_FAINT, self.fill).pack(anchor="w")
        self.value = label(c, "0", "display", color, self.fill)
        self.value.pack(anchor="w", pady=(dp(4), 0))
        self.sub = label(c, "", "small", T.TEXT_DIM, self.fill)
        self.sub.pack(anchor="w")
        self.extra = tk.Frame(c, bg=self.fill)
        self.extra.pack(fill="x", pady=(dp(10), 0))

    def set(self, value: str, sub: str = ""):
        self.value.configure(text=value)
        self.sub.configure(text=sub)


class BarChart(tk.Canvas):
    """Small bar chart of (label, value) pairs; the newest bar is highlighted."""

    def __init__(self, parent, height=64, labels=False, bg=None):
        self._height = dp(height)
        super().__init__(parent, height=self._height, bg=bg or parent.cget("bg"), bd=0, highlightthickness=0)
        self._data: list = []
        self._labels = labels
        self.bind("<Configure>", lambda e: self._draw(), add="+")

    def set(self, data):
        self._data = list(data)
        self._draw()

    def _draw(self):
        self.delete("all")
        n = len(self._data)
        w = self.winfo_width()
        if not n or w < 20:
            return
        label_h = dp(18) if self._labels else 0
        top = dp(4)
        area = max(self._height - label_h - top, 4)
        gap = dp(6)
        bw = max((w - gap * (n - 1)) / n, 2)
        peak = max((v for _, v in self._data), default=0) or 1
        for i, (name, v) in enumerate(self._data):
            x0 = i * (bw + gap)
            h = max(area * v / peak, dp(3)) if v else dp(3)
            color = (T.CYAN if i == n - 1 else T.blend(T.CYAN, 0.40, T.PANEL)) if v else T.BORDER_STRONG
            self.create_rectangle(x0, top + area - h, x0 + bw, top + area, fill=color, outline="")
            if self._labels:
                self.create_text(x0 + bw / 2, self._height - dp(7), text=name, fill=T.TEXT_FAINT, font=T.font("small"))


class BarRow(tk.Frame):
    """abbr | expansion | bar | count"""

    def __init__(self, parent, abbr, text, count, frac, bg):
        super().__init__(parent, bg=bg)
        self._frac = frac
        label(self, abbr, "mono_b", T.CYAN, bg, width=10).pack(side="left")
        label(self, clip(text, 36), "small", T.TEXT_DIM, bg, width=30).pack(side="left", padx=(0, dp(12)))
        label(self, f"{count:,}", "mono_b", T.TEXT, bg, width=7, anchor="e").pack(side="right")
        self.bar = tk.Canvas(self, height=dp(8), bg=bg, bd=0, highlightthickness=0)
        self.bar.pack(side="left", fill="x", expand=True, padx=(0, dp(12)))
        self.bar.bind("<Configure>", lambda e: self._draw(), add="+")

    def _draw(self):
        w, h = self.bar.winfo_width(), dp(8)
        self.bar.delete("all")
        if w < 4:
            return
        self.bar.create_line(h / 2, h / 2, w - h / 2, h / 2, width=h, fill=T.BORDER, capstyle="round")
        fw = max(w * self._frac, h)
        self.bar.create_line(h / 2, h / 2, fw - h / 2, h / 2, width=h, fill=T.CYAN, capstyle="round")


def empty_state(parent, icon: str, title: str, body: str, bg=None) -> tk.Frame:
    f = tk.Frame(parent, bg=bg or parent.cget("bg"))
    icon_label(f, icon, 28, T.TEXT_FAINT, f.cget("bg")).pack(pady=(dp(8), dp(8)))
    label(f, title, "body_b", T.TEXT, f.cget("bg"), anchor="center").pack()
    label(f, body, "small", T.TEXT_DIM, f.cget("bg"), anchor="center", wraplength=dp(320), justify="center").pack(
        pady=(dp(4), dp(8)))
    return f


def setting_row(card: Card, title: str, desc: str | None = None, first: bool = False) -> tk.Frame:
    """A label/description on the left; returns the right-hand frame for the control."""
    if not first:
        divider(card.content, T.DIVIDER).pack(fill="x", pady=dp(12))
    row = tk.Frame(card.content, bg=card.fill)
    row.pack(fill="x")
    left = tk.Frame(row, bg=card.fill)
    left.pack(side="left", fill="x", expand=True, padx=(0, dp(16)))
    label(left, title, "body_b", T.TEXT, card.fill).pack(anchor="w")
    if desc:
        label(left, desc, "small", T.TEXT_DIM, card.fill, wraplength=dp(430), justify="left").pack(anchor="w")
    right = tk.Frame(row, bg=card.fill)
    right.pack(side="right")
    right.left = left            # lets callers make the text clickable
    return right


def note(parent, text: str, color: str = T.TEXT_DIM, fill: str = T.PANEL_HOVER, icon: str = "info") -> Surface:
    """Inline callout."""
    s = Surface(parent, radius=T.R_MD, fill=fill, border=T.blend(color, 0.30, T.PANEL), hl=0.0)
    row = tk.Frame(s.body, bg=fill)
    row.pack(fill="x", padx=dp(12), pady=dp(8))
    icon_label(row, icon, 16, color, fill).pack(side="left", anchor="n", padx=(0, dp(10)), pady=dp(1))
    label(row, text, "small", T.TEXT, fill, wraplength=dp(520), justify="left").pack(side="left", fill="x", expand=True)
    return s
