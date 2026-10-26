"""Dashboard: key numbers, live activity, and a box to try expansion right here."""
from __future__ import annotations

import tkinter as tk

from snapcore.stats import format_minutes

from .. import theme as T
from ..theme import dp
from ..widgets import Card, TextArea, icon_label, label
from . import Page
from .common import BarChart, MetricCard, clip, empty_state

FEED_ROWS = 7


class DashboardPage(Page):
    def build(self):
        col = self.col
        top = tk.Frame(col, bg=T.VOID)
        top.pack(fill="x")
        for i in range(3):
            top.columnconfigure(i, weight=1, uniform="metric")
        self.m_total = MetricCard(top, "Expansions", T.CYAN)
        self.m_total.grid(row=0, column=0, sticky="nsew", padx=(0, dp(12)))
        self.chart = BarChart(self.m_total.extra, height=44, bg=self.m_total.fill)
        self.chart.pack(fill="x")
        self.m_time = MetricCard(top, "Time saved", T.AMETHYST)
        self.m_time.grid(row=0, column=1, sticky="nsew", padx=dp(6))
        self.m_snips = MetricCard(top, "Snippets", T.TEXT)
        self.m_snips.grid(row=0, column=2, sticky="nsew", padx=(dp(12), 0))

        bottom = tk.Frame(col, bg=T.VOID)
        bottom.pack(fill="x", pady=(dp(16), dp(8)))
        bottom.columnconfigure(0, weight=3, uniform="b")
        bottom.columnconfigure(1, weight=2, uniform="b")

        self.feed_card = Card(bottom, "Live activity", "clock")
        self.feed_card.grid(row=0, column=0, sticky="nsew", padx=(0, dp(8)))
        self.feed = tk.Frame(self.feed_card.content, bg=self.feed_card.fill)
        self.feed.pack(fill="both", expand=True)

        self.try_card = Card(bottom, "Try it here", "keyboard")
        self.try_card.grid(row=0, column=1, sticky="nsew", padx=(dp(8), 0))
        c = self.try_card.content
        self.try_hint = label(c, "", "body", T.TEXT_DIM, self.try_card.fill, wraplength=dp(280), justify="left")
        self.try_hint.pack(anchor="w", pady=(0, dp(10)))
        self.try_box = TextArea(c, placeholder="Type here\u2026", height=6)
        self.try_box.pack(fill="x")
        self.try_status = label(c, "", "small", T.TEXT_FAINT, self.try_card.fill)
        self.try_status.pack(anchor="w", pady=(dp(10), 0))
        # Expansion is normally blocked inside SnapType's own window (so the editor fields stay
        # safe); this one box opts in so you can see it work.
        self.try_box.text.bind("<FocusIn>", lambda e: self._allow_own(True), add="+")
        self.try_box.text.bind("<FocusOut>", lambda e: self._allow_own(False), add="+")

    def _allow_own(self, on: bool):
        self.app.engine.allow_own_window = on

    def on_hide(self):
        self._allow_own(False)

    def refresh(self):
        a = self.app
        total = a.stats.total()
        days = a.stats.daily(14)
        self.m_total.set(f"{total:,}", f"{sum(n for _, n in days):,} in the last 14 days")
        self.chart.set([(d.strftime("%a")[0], n) for d, n in days])
        self.m_time.set(format_minutes(a.minutes_saved()), "estimated, at 40 words a minute")
        n = len(a.sm.snippets)
        self.m_snips.set(str(n), "ready to expand" if n else "add your first one")
        self._render_feed()
        sample = "omw" if "omw" in a.sm.snippets else (sorted(a.sm.snippets)[0] if a.sm.snippets else "your abbreviation")
        self.try_hint.configure(text=f"Click the box, type {sample} and press space.")
        if a.state == "on":
            self.try_status.configure(text="SnapType is on", fg=T.CYAN)
        elif a.state == "snoozed":
            self.try_status.configure(text="Snoozed. Press Resume to try it.", fg=T.AMETHYST)
        else:
            self.try_status.configure(text="SnapType is paused. Press Start to try it.", fg=T.AMBER)

    def _render_feed(self):
        for w in self.feed.winfo_children():
            w.destroy()
        bg = self.feed_card.fill
        rows = list(self.app.activity)[:FEED_ROWS]
        if not rows:
            empty_state(self.feed, "bolt", "Nothing expanded yet",
                        "Press Start, then type one of your abbreviations and a space in any app.", bg).pack(
                fill="x", pady=dp(10))
            return
        for r in rows:
            line = tk.Frame(self.feed, bg=bg)
            line.pack(fill="x", pady=dp(4))
            label(line, r["t"], "mono_s", T.TEXT_FAINT, bg, width=9).pack(side="left")
            tk.Label(line, text=r["abbr"], font=T.font("mono_b"), fg=T.CYAN, bg=T.CYAN_TINT_PANEL, bd=0,
                     padx=dp(8), pady=dp(2)).pack(side="left")
            icon_label(line, "chevron_right", 14, T.TEXT_FAINT, bg).pack(side="left", padx=dp(6))
            label(line, clip(r["exp"], 44), "body", T.TEXT, bg).pack(side="left", fill="x", expand=True)
