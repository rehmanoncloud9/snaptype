"""About: identity, privacy promise, shortcuts, author."""
from __future__ import annotations

import platform
import sys
import tkinter as tk
import webbrowser

from PIL import ImageTk

from snapcore import APP_NAME, VERSION

from .. import icons
from .. import theme as T
from ..theme import dp
from ..widgets import Button, Card, Keycaps, Pill, icon_label, label
from . import Page

AUTHOR = {
    "name": "Abdul Rehman",
    "role": "Python Developer",
    "linkedin": "www.linkedin.com/in/arehman-builds",
    "instagram": "rehmanoncloud9",
    "email": "relentlessrehman@gmail.com",
}
SHORTCUTS = (
    (("Ctrl", "1\u20136"), "Switch page"),
    (("Ctrl", "F"), "Search snippets"),
    (("Ctrl", "N"), "New snippet"),
    (("Ctrl", "Enter"), "Save snippet from the text box"),
    (("Ctrl", "Q"), "Quit SnapType"),
)
PROMISES = (
    "Runs entirely on your device. There is no account, cloud or network code.",
    "Keeps only the last few letters of the current word in memory. Typing is never recorded.",
    "Reads the active window's title only to apply your App Rules and skip password windows.",
    "Your snippets, stats and settings are plain files you can open, back up or delete.",
)


def version_info() -> str:
    return f"{APP_NAME} {VERSION}\nPython {sys.version.split()[0]}\n{platform.platform()}"


class AboutPage(Page):
    def build(self):
        col = self.col
        hero = Card(col, pad_x=24, pad_y=22)
        hero.pack(fill="x")
        row = tk.Frame(hero.content, bg=hero.fill)
        row.pack(fill="x")
        self._logo = ImageTk.PhotoImage(icons.make_logo(dp(96)))
        tk.Label(row, image=self._logo, bg=hero.fill, bd=0).pack(side="left", padx=(0, dp(22)))
        info = tk.Frame(row, bg=hero.fill)
        info.pack(side="left", fill="x", expand=True)
        name = tk.Frame(info, bg=hero.fill)
        name.pack(anchor="w")
        label(name, "Snap", "display", T.CYAN, hero.fill).pack(side="left")
        label(name, "Type", "display", T.AMETHYST, hero.fill).pack(side="left")
        label(info, "Smart text expansion for Windows. Type less, say more.", "body", T.TEXT_DIM, hero.fill).pack(
            anchor="w", pady=(dp(2), dp(10)))
        tags = tk.Frame(info, bg=hero.fill)
        tags.pack(anchor="w")
        Pill(tags, f"Version {VERSION}", T.CYAN, T.blend(T.CYAN, 0.10, T.PANEL), T.blend(T.CYAN, 0.4, T.PANEL),
             bg=hero.fill).pack(side="left")
        Pill(tags, "MIT licence", T.TEXT_DIM, T.PANEL_HOVER, T.BORDER, bg=hero.fill).pack(side="left", padx=dp(8))
        Button(row, text="Copy version info", icon="copy", variant="secondary", size="sm", bg=hero.fill,
               command=self._copy).pack(side="right", anchor="n")

        mid = tk.Frame(col, bg=T.VOID)
        mid.pack(fill="x", pady=(dp(16), 0))
        mid.columnconfigure(0, weight=1, uniform="a")
        mid.columnconfigure(1, weight=1, uniform="a")

        priv = Card(mid, "Private by design", "lock")
        priv.grid(row=0, column=0, sticky="nsew", padx=(0, dp(8)))
        for text in PROMISES:
            line = tk.Frame(priv.content, bg=priv.fill)
            line.pack(fill="x", pady=dp(4))
            icon_label(line, "check", 16, T.CYAN, priv.fill).pack(side="left", anchor="n", padx=(0, dp(10)), pady=dp(2))
            label(line, text, "body", T.TEXT_DIM, priv.fill, wraplength=dp(300), justify="left").pack(side="left")

        keys = Card(mid, "Keyboard shortcuts", "keyboard")
        keys.grid(row=0, column=1, sticky="nsew", padx=(dp(8), 0))
        for parts, what in SHORTCUTS:
            line = tk.Frame(keys.content, bg=keys.fill)
            line.pack(fill="x", pady=dp(5))
            Keycaps(line, parts, keys.fill).pack(side="left")
            label(line, what, "body", T.TEXT_DIM, keys.fill).pack(side="left", padx=(dp(8), 0))

        author = Card(col, "Made by", "info")
        author.pack(fill="x", pady=(dp(16), dp(8)))
        top = tk.Frame(author.content, bg=author.fill)
        top.pack(fill="x")
        av = tk.Canvas(top, width=dp(52), height=dp(52), bg=author.fill, bd=0, highlightthickness=0)
        av.create_oval(1, 1, dp(52) - 1, dp(52) - 1, fill=T.PANEL_HOVER, outline=T.BORDER_STRONG)
        av.create_text(dp(26), dp(26), text="AR", font=T.font("body_b"), fill=T.CYAN)
        av.pack(side="left", padx=(0, dp(14)))
        who = tk.Frame(top, bg=author.fill)
        who.pack(side="left")
        label(who, AUTHOR["name"], "heading", T.TEXT, author.fill).pack(anchor="w")
        label(who, AUTHOR["role"], "small", T.TEXT_DIM, author.fill).pack(anchor="w")
        links = tk.Frame(author.content, bg=author.fill)
        links.pack(fill="x", pady=(dp(14), 0))
        for text, url in (("LinkedIn", f"https://{AUTHOR['linkedin']}"),
                          ("Instagram", f"https://instagram.com/{AUTHOR['instagram']}"),
                          (AUTHOR["email"], f"mailto:{AUTHOR['email']}")):
            Button(links, text=text, icon="external", variant="secondary", size="sm", bg=author.fill,
                   command=lambda u=url: self._open(u)).pack(side="left", padx=(0, dp(8)))

    def _open(self, url):
        try:
            webbrowser.open(url)
        except webbrowser.Error:
            self.app.toast("Couldn't open your browser.", "warn")

    def _copy(self):
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(version_info())
        self.app.toast("Version info copied", "success")
