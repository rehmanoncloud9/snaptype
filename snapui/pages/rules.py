"""App Rules: where SnapType is allowed to expand."""
from __future__ import annotations

import re
import tkinter as tk

from .. import theme as T
from ..theme import dp
from ..widgets import Button, Card, Field, Surface, caps_label, icon_photo, label
from . import Page
from .common import empty_state, note

MODES = (
    ("all", "globe", "All apps", "SnapType expands everywhere you type."),
    ("include", "check_circle", "Only in these apps", "Expand only in the apps on your list."),
    ("exclude", "ban", "Everywhere except these", "Expand everywhere, but skip the apps on your list."),
)
POPULAR = (("Chrome", "Google Chrome"), ("Edge", "Microsoft Edge"), ("Firefox", "Firefox"), ("Word", "Word"),
           ("Excel", "Excel"), ("Outlook", "Outlook"), ("Slack", "Slack"), ("Teams", "Microsoft Teams"),
           ("Discord", "Discord"), ("VS Code", "Visual Studio Code"), ("Notepad", "Notepad"), ("Terminal", "Terminal"))


def suggest_rule(title: str) -> str:
    """Window titles usually end with the app name ("Report.docx - Word"): suggest that part."""
    parts = [p.strip() for p in re.split(r"\s[-\u2013\u2014|]\s", title) if p.strip()]
    return parts[-1] if parts else title.strip()


class ModeCard(Surface):
    """Selectable card (radio behaviour) with a glowing cyan edge when chosen."""

    def __init__(self, parent, value, var, icon, title, desc, command):
        super().__init__(parent, radius=T.R_LG, fill=T.PANEL, border=T.BORDER, pad=3)
        self.value, self.var, self.command = value, var, command
        self.body.configure(takefocus=1)
        inner = tk.Frame(self.body, bg=self.fill)
        inner.pack(fill="both", expand=True, padx=dp(14), pady=dp(12))
        top = tk.Frame(inner, bg=self.fill)
        top.pack(fill="x")
        self.icon_name = icon
        self.icon = tk.Label(top, bg=self.fill, bd=0)
        self.icon.pack(side="left")
        self.check = tk.Label(top, bg=self.fill, bd=0)
        self.check.pack(side="right")
        self.title = label(inner, title, "body_b", T.TEXT, self.fill)
        self.title.pack(anchor="w", pady=(dp(10), dp(2)))
        label(inner, desc, "small", T.TEXT_DIM, self.fill, wraplength=dp(210), justify="left").pack(anchor="w")
        self._bind_click(self)
        self.body.bind("<Return>", lambda e: self._pick(), add="+")
        self.body.bind("<space>", lambda e: self._pick(), add="+")
        self.body.bind("<FocusIn>", lambda e: self.update_look(focus=True), add="+")
        self.body.bind("<FocusOut>", lambda e: self.update_look(), add="+")
        self.update_look()

    def _bind_click(self, w):
        w.bind("<ButtonRelease-1>", lambda e: self._pick(), add="+")
        try:
            w.configure(cursor="hand2")
        except tk.TclError:
            pass
        for c in w.winfo_children():
            self._bind_click(c)

    def _pick(self):
        self.var.set(self.value)
        self.command(self.value)

    def update_look(self, focus=False):
        on = self.var.get() == self.value
        self.set_look(border=T.CYAN if on else (T.BORDER_STRONG if focus else T.BORDER),
                      glow=T.CYAN if on else None, glow_a=55 if on else 0)
        ph = icon_photo(self.icon_name, dp(22), T.CYAN if on else T.TEXT_DIM)
        self.icon.configure(image=ph)
        self.icon.image = ph
        ck = icon_photo("check_circle", dp(18), T.CYAN) if on else None
        self.check.configure(image=ck or "")
        self.check.image = ck
        self.title.configure(fg=T.CYAN if on else T.TEXT)


class RulesPage(Page):
    def build(self):
        a, col = self.app, self.col
        self.mode = tk.StringVar(value=a.cfg.get("app_mode"))
        row = tk.Frame(col, bg=T.VOID)
        row.pack(fill="x")
        self.cards = []
        for i, (value, icon, title, desc) in enumerate(MODES):
            row.columnconfigure(i, weight=1, uniform="mode")
            card = ModeCard(row, value, self.mode, icon, title, desc, self._on_mode)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else dp(6), 0 if i == 2 else dp(6)))
            self.cards.append(card)

        self.callout = tk.Frame(col, bg=T.VOID)
        self.callout.pack(fill="x", pady=(dp(12), 0))

        lower = tk.Frame(col, bg=T.VOID)
        lower.pack(fill="x", pady=(dp(12), dp(8)))
        lower.columnconfigure(0, weight=1, uniform="r")
        lower.columnconfigure(1, weight=1, uniform="r")

        self.list_card = Card(lower, "Your apps", "shield")
        self.list_card.grid(row=0, column=0, sticky="nsew", padx=(0, dp(8)))
        self.clear_btn = Button(self.list_card.actions, text="Clear all", variant="ghost", size="sm",
                                bg=self.list_card.fill, command=self._clear_all)
        label(self.list_card.content, "A rule matches any window whose title contains the text (capitals don't matter).",
              "small", T.TEXT_FAINT, self.list_card.fill, wraplength=dp(330), justify="left").pack(
            anchor="w", pady=(0, dp(10)))
        self.rows = tk.Frame(self.list_card.content, bg=self.list_card.fill)
        self.rows.pack(fill="x")

        add = Card(lower, "Add an app", "plus")
        add.grid(row=0, column=1, sticky="nsew", padx=(dp(8), 0))
        c = add.content
        caps_label(c, "Last active window", bg=add.fill).pack(anchor="w")
        box = tk.Frame(c, bg=T.INPUT, highlightthickness=1, highlightbackground=T.BORDER)
        box.pack(fill="x", pady=(dp(6), dp(4)))
        self.last_lbl = label(box, "", "mono_s", T.TEXT, T.INPUT, wraplength=dp(280), justify="left")
        self.last_lbl.pack(anchor="w", padx=dp(10), pady=(dp(8), dp(2)))
        self.suggest_lbl = label(box, "", "small", T.TEXT_FAINT, T.INPUT)
        self.suggest_lbl.pack(anchor="w", padx=dp(10), pady=(0, dp(8)))
        self.use_btn = Button(c, text="Use this app", icon="plus", variant="secondary", size="sm", bg=add.fill,
                              command=self._use_last)
        self.use_btn.pack(anchor="w", pady=(dp(4), dp(14)))

        caps_label(c, "Rule text", bg=add.fill).pack(anchor="w")
        line = tk.Frame(c, bg=add.fill)
        line.pack(fill="x", pady=(dp(6), dp(14)))
        self.text_var = tk.StringVar()
        self.field = Field(line, self.text_var, placeholder="e.g. Word", width=14, command=self._add_typed)
        Button(line, text="Add", variant="primary", size="sm", bg=add.fill, command=self._add_typed).pack(side="right")
        self.field.pack(side="left", fill="x", expand=True, padx=(0, dp(8)))

        caps_label(c, "Popular apps", bg=add.fill).pack(anchor="w", pady=(0, dp(6)))
        grid = tk.Frame(c, bg=add.fill)
        grid.pack(fill="x")
        for i, (name, rule) in enumerate(POPULAR):
            Button(grid, text=name, variant="chip", size="sm", bg=add.fill,
                   command=lambda r=rule: self._add(r)).grid(row=i // 4, column=i % 4, sticky="w")
        self._poll_job = None

    # ═══ data ═════════════════════════════════════════════════════════════
    def _apps(self) -> list:
        return list(self.app.cfg.get("app_list") or [])

    def _set_apps(self, apps):
        self.app.cfg.set("app_list", list(apps))
        self.refresh()

    def _on_mode(self, value):
        self.app.cfg.set("app_mode", value)
        self.refresh()

    def _add(self, text: str):
        text = text.strip()
        if not text:
            return
        apps = self._apps()
        if any(a.lower() == text.lower() for a in apps):
            self.app.toast(f"\u201c{text}\u201d is already on the list.", "info")
            return
        self._set_apps(apps + [text])
        self.app.toast(f"Added \u201c{text}\u201d", "success")

    def _add_typed(self):
        self._add(self.text_var.get())
        self.text_var.set("")

    def _use_last(self):
        title = self.app.tracker.last
        if title:
            self.text_var.set(suggest_rule(title))
            self.field.focus()

    def _remove(self, index: int):
        old = self._apps()
        if not 0 <= index < len(old):
            return
        gone = old[index]
        self._set_apps(old[:index] + old[index + 1:])
        self.app.toast(f"Removed \u201c{gone}\u201d", "info", action=("Undo", lambda: self._set_apps(old)))

    def _clear_all(self):
        old = self._apps()
        self._set_apps([])
        self.app.toast(f"Removed {len(old)} apps", "info", action=("Undo", lambda: self._set_apps(old)))

    # ═══ view ═════════════════════════════════════════════════════════════
    def refresh(self):
        apps, mode = self._apps(), self.app.cfg.get("app_mode")
        self.mode.set(mode)
        for card in self.cards:
            card.update_look()
        for w in self.callout.winfo_children():
            w.destroy()
        if mode == "include" and not apps:
            note(self.callout, "Your list is empty, so SnapType still expands everywhere. Add an app to limit it.",
                 T.AMBER, T.AMBER_TINT, "alert").pack(fill="x")
        elif mode == "all" and apps:
            note(self.callout, "Your list is saved but isn't used while \u201cAll apps\u201d is selected.",
                 T.TEXT_DIM, T.PANEL_HOVER, "info").pack(fill="x")
        for w in self.rows.winfo_children():
            w.destroy()
        fill = self.list_card.fill
        if apps:
            self.clear_btn.pack()
        else:
            self.clear_btn.pack_forget()
            empty_state(self.rows, "shield", "No apps yet", "Add one from the panel on the right.", fill).pack(
                fill="x", pady=dp(8))
        for i, name in enumerate(apps):
            chip = Surface(self.rows, radius=T.R_MD, fill=T.PANEL_HOVER, border=T.BORDER, hl=0.0)
            chip.pack(fill="x", pady=dp(3))
            line = tk.Frame(chip.body, bg=T.PANEL_HOVER)
            line.pack(fill="x", padx=dp(10), pady=dp(2))
            label(line, name, "body", T.TEXT, T.PANEL_HOVER).pack(side="left")
            Button(line, icon="x", variant="quiet", size="sm", bg=T.PANEL_HOVER, tooltip=f"Remove {name}",
                   command=lambda i=i: self._remove(i)).pack(side="right")
        self._refresh_last()

    def _refresh_last(self):
        title = self.app.tracker.last
        if title:
            self.last_lbl.configure(text=title, fg=T.TEXT)
            self.suggest_lbl.configure(text=f"Suggested rule: {suggest_rule(title)}")
        else:
            self.last_lbl.configure(text="Switch to the app you want, then come back here.", fg=T.TEXT_FAINT)
            self.suggest_lbl.configure(text="")
        self.use_btn.update_button(state="normal" if title else "disabled")

    def _poll(self):
        self._refresh_last()
        self._poll_job = self.after(1000, self._poll)

    def on_show(self):
        self.refresh()
        if self._poll_job is None:
            self._poll_job = self.after(1000, self._poll)

    def on_hide(self):
        if self._poll_job is not None:
            self.after_cancel(self._poll_job)
            self._poll_job = None
