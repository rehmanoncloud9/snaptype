"""Pages. Each is a Frame built once (lazily) and shown/hidden by the app."""
from __future__ import annotations

import tkinter as tk

from .. import theme as T
from ..widgets import ScrollFrame


class Page(tk.Frame):
    scrolls = True          # wrap content in a ScrollFrame (the Snippets page manages its own lists)

    def __init__(self, parent, app):
        super().__init__(parent, bg=T.VOID, bd=0, highlightthickness=0)
        self.app = app
        if self.scrolls:
            self._scroll = ScrollFrame(self, bg=T.VOID)
            self._scroll.pack(fill="both", expand=True)
            self.col = self._scroll.inner
        else:
            self.col = self
        self.build()

    def build(self):                # create widgets (once)
        raise NotImplementedError

    def on_show(self):              # page became visible
        self.refresh()

    def on_hide(self):
        pass

    def refresh(self):              # data changed
        pass

    def on_find(self):              # Ctrl+F
        pass

    def on_new(self):               # Ctrl+N
        pass


def build(name: str, parent, app) -> Page:
    from .about import AboutPage
    from .dashboard import DashboardPage
    from .rules import RulesPage
    from .settings import SettingsPage
    from .snippets import SnippetsPage
    from .stats import StatsPage
    return {"Dashboard": DashboardPage, "Snippets": SnippetsPage, "Stats": StatsPage, "App Rules": RulesPage,
            "Settings": SettingsPage, "About": AboutPage}[name](parent, app)
