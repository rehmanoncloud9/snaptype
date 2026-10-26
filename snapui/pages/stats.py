"""Stats: totals, the last two weeks, and the most-used snippets."""
from __future__ import annotations

import tkinter as tk

from snapcore.stats import format_minutes

from .. import theme as T
from ..theme import dp
from ..widgets import Button, Card
from . import Page
from .common import BarChart, BarRow, MetricCard, empty_state

TOP_N = 10


class StatsPage(Page):
    def build(self):
        col = self.col
        top = tk.Frame(col, bg=T.VOID)
        top.pack(fill="x")
        for i in range(4):
            top.columnconfigure(i, weight=1, uniform="m")
        self.m = []
        for i, (cap, color) in enumerate((("Expansions", T.CYAN), ("Time saved", T.AMETHYST),
                                          ("Most used", T.TEXT), ("Active days", T.TEXT))):
            card = MetricCard(top, cap, color)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else dp(6), 0 if i == 3 else dp(6)))
            self.m.append(card)

        self.week = Card(col, "Last 14 days", "chart")
        self.week.pack(fill="x", pady=(dp(16), 0))
        self.chart = BarChart(self.week.content, height=96, labels=True, bg=self.week.fill)
        self.chart.pack(fill="x")

        self.top_card = Card(col, "Top snippets", "bolt")
        self.top_card.pack(fill="x", pady=(dp(16), dp(8)))
        Button(self.top_card.actions, text="Reset stats", icon="trash", variant="danger", size="sm",
               bg=self.top_card.fill, command=self._reset).pack()
        self.list = tk.Frame(self.top_card.content, bg=self.top_card.fill)
        self.list.pack(fill="x")

    def refresh(self):
        a = self.app
        total = a.stats.total()
        top = a.stats.top(TOP_N)
        days = a.stats.daily(14)
        self.m[0].set(f"{total:,}", "since you started")
        self.m[1].set(format_minutes(a.minutes_saved()), "estimated typing time")
        self.m[2].set(top[0][0] if top else "\u2013", f"{top[0][1]:,} uses" if top else "nothing yet")
        self.m[3].set(str(a.stats.active_days()), "days with an expansion")
        self.chart.set([(d.strftime("%a")[0], n) for d, n in days])
        for w in self.list.winfo_children():
            w.destroy()
        bg = self.top_card.fill
        if not top:
            empty_state(self.list, "chart", "No expansions recorded yet",
                        "Once SnapType expands a snippet, your most-used ones show up here.", bg).pack(fill="x", pady=dp(8))
            return
        peak = top[0][1] or 1
        for abbr, n in top:
            exp = a.sm.snippets.get(abbr, {}).get("exp", "(deleted snippet)")
            BarRow(self.list, abbr, exp, n, n / peak, bg).pack(fill="x", pady=dp(5))

    def _reset(self):
        from .. import dialogs
        if dialogs.confirm(self.app.root, "Reset statistics?",
                           "This clears every expansion count and the daily history. It can't be undone.",
                           ok="Reset statistics", danger=True):
            self.app.stats.reset()
            self.app.refresh_pages()
            self.app.toast("Statistics reset", "info")
