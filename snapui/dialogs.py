"""Modal dialogs in the app's own style (native message boxes are white on a dark app and
cannot be themed). Every dialog: centred on its parent, dark title bar, Escape cancels, Enter
activates the *safe* default (Cancel for destructive confirmations)."""
from __future__ import annotations

import tkinter as tk

from snapcore import winutil

from . import theme as T
from .theme import dp
from .widgets import Button, icon_label, icon_photo, label


class Modal(tk.Toplevel):
    def __init__(self, parent, title: str, width: int = 480):
        super().__init__(parent, bg=T.SURFACE)
        self.withdraw()
        self.title(title)
        self.resizable(False, False)
        self.result = None
        self._width = dp(width)
        self._parent = parent
        self.body = tk.Frame(self, bg=T.SURFACE, bd=0, highlightthickness=0)
        self.body.pack(fill="both", expand=True, padx=dp(28), pady=dp(24))
        self.protocol("WM_DELETE_WINDOW", lambda: self.on_close())
        self.bind("<Escape>", lambda e: self.on_close())
        self._default = None

    def on_close(self):
        self.finish(None)

    def finish(self, result):
        self.result = result
        self.destroy()

    def set_default(self, button: Button):
        """Enter activates this button even when focus is elsewhere in the dialog."""
        self._default = button
        self.bind("<Return>", lambda e: button._activate(), add="+")

    def present(self, focus: tk.Misc | None = None):
        self.update_idletasks()
        w, h = self._width, self.winfo_reqheight()
        p = self._parent
        if p.winfo_viewable():
            self.transient(p)
            x = p.winfo_rootx() + (p.winfo_width() - w) // 2
            y = p.winfo_rooty() + (p.winfo_height() - h) // 3
        else:
            x = (self.winfo_screenwidth() - w) // 2
            y = (self.winfo_screenheight() - h) // 3
        self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")
        self.deiconify()
        self.update_idletasks()
        winutil.set_titlebar_theme(self.winfo_id(), True, T.SURFACE, T.TEXT)
        try:
            if not self.winfo_viewable():
                self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass                                   # still usable without the grab
        if not self.winfo_exists():
            return self.result                     # closed while waiting for visibility
        (focus or self).focus_set()
        self.wait_window(self)
        return self.result


def _button_row(parent, *buttons, gap=10):
    row = tk.Frame(parent, bg=T.SURFACE)
    for i, b in enumerate(buttons):
        b.pack(side="right", padx=(dp(gap) if i else 0, 0))
    return row


def confirm(parent, title: str, message: str, ok: str = "Confirm", cancel: str = "Cancel",
            danger: bool = False, detail: str | None = None) -> bool:
    """Yes/no question. For ``danger`` the default (Enter) button is Cancel."""
    dlg = Modal(parent, title, 460)
    head = tk.Frame(dlg.body, bg=T.SURFACE)
    head.pack(fill="x")
    icon_label(head, "alert" if danger else "info", 22, T.ERROR if danger else T.CYAN, T.SURFACE).pack(
        side="left", anchor="n", padx=(0, dp(14)))
    col = tk.Frame(head, bg=T.SURFACE)
    col.pack(side="left", fill="x", expand=True)
    label(col, title, "heading", T.TEXT, T.SURFACE).pack(anchor="w")
    label(col, message, "body", T.TEXT_DIM, T.SURFACE, wraplength=dp(340), justify="left").pack(anchor="w", pady=(dp(6), 0))
    if detail:
        box = tk.Frame(col, bg=T.INPUT, highlightthickness=1, highlightbackground=T.BORDER)
        box.pack(fill="x", pady=(dp(12), 0))
        label(box, detail, "mono_s", T.TEXT, T.INPUT, wraplength=dp(320), justify="left").pack(
            anchor="w", padx=dp(10), pady=dp(8))
    b_ok = Button(dlg.body, text=ok, variant="danger" if danger else "primary",
                  command=lambda: dlg.finish(True), bg=T.SURFACE)
    b_cancel = Button(dlg.body, text=cancel, variant="secondary", command=lambda: dlg.finish(False), bg=T.SURFACE)
    row = _button_row(dlg.body, b_ok, b_cancel)
    row.pack(fill="x", pady=(dp(22), 0))
    dlg.set_default(b_cancel if danger else b_ok)
    return bool(dlg.present(b_cancel if danger else b_ok))


def alert(parent, title: str, message: str, kind: str = "info", ok: str = "OK", detail: str | None = None) -> None:
    dlg = Modal(parent, title, 460)
    icon, color = {"error": ("alert", T.ERROR), "warn": ("alert", T.AMBER)}.get(kind, ("info", T.CYAN))
    head = tk.Frame(dlg.body, bg=T.SURFACE)
    head.pack(fill="x")
    icon_label(head, icon, 22, color, T.SURFACE).pack(side="left", anchor="n", padx=(0, dp(14)))
    col = tk.Frame(head, bg=T.SURFACE)
    col.pack(side="left", fill="x", expand=True)
    label(col, title, "heading", T.TEXT, T.SURFACE).pack(anchor="w")
    label(col, message, "body", T.TEXT_DIM, T.SURFACE, wraplength=dp(340), justify="left").pack(anchor="w", pady=(dp(6), 0))
    if detail:
        label(col, detail, "mono_s", T.TEXT_FAINT, T.SURFACE, wraplength=dp(340), justify="left").pack(
            anchor="w", pady=(dp(10), 0))
    b = Button(dlg.body, text=ok, variant="primary", command=lambda: dlg.finish(True), bg=T.SURFACE)
    _button_row(dlg.body, b).pack(fill="x", pady=(dp(22), 0))
    dlg.set_default(b)
    dlg.present(b)


WELCOME_STEPS = (
    ("bolt_fill", "Type less. Say more.",
     "SnapType turns short abbreviations into full phrases, in any app. Type omw and a space, and it "
     "becomes \u201con my way\u201d.\n\nChanged your mind? Press Backspace right after an expansion to get "
     "your abbreviation back."),
    ("keyboard", "Make it yours",
     "Add your own snippets, with variables like {{date}} and {{clipboard}}. Use App Rules to limit "
     "SnapType to the apps you choose, and check Stats to see the time you save."),
    ("lock", "What SnapType can see",
     "Everything stays on this device: there is no account, no cloud and no network code.\n\n"
     "SnapType reads the title of the window you are typing in, only to apply App Rules and to skip "
     "password and sign-in windows. It keeps just the last few letters of the current word in memory "
     "and never records or stores what you type."),
)


def welcome(parent) -> bool:
    """First-run walkthrough that ends in the privacy acknowledgement.
    Returns True to continue, False if the person chose to quit."""
    dlg = Modal(parent, "Welcome to SnapType", 520)
    dlg.on_close = lambda: dlg.finish("quit")
    state = {"i": 0}
    hero = tk.Frame(dlg.body, bg=T.SURFACE)
    hero.pack(fill="x")
    ic = tk.Label(hero, bg=T.SURFACE, bd=0)
    ic.pack(anchor="w")
    title = label(dlg.body, "", "title", T.TEXT, T.SURFACE)
    title.pack(anchor="w", pady=(dp(14), dp(8)))
    text = label(dlg.body, "", "body", T.TEXT_DIM, T.SURFACE, wraplength=dp(460), justify="left")
    text.pack(anchor="w")
    dots = tk.Canvas(dlg.body, width=dp(60), height=dp(10), bg=T.SURFACE, bd=0, highlightthickness=0)
    dots.pack(anchor="w", pady=(dp(22), 0))
    row = tk.Frame(dlg.body, bg=T.SURFACE)
    row.pack(fill="x", pady=(dp(14), 0))
    nxt = Button(row, text="Next", variant="primary", bg=T.SURFACE)
    back = Button(row, text="Back", variant="secondary", bg=T.SURFACE)
    quit_b = Button(row, text="Quit SnapType", variant="ghost", bg=T.SURFACE, command=lambda: dlg.finish("quit"))

    def render():
        i = state["i"]
        icon, head, body = WELCOME_STEPS[i]
        last = i == len(WELCOME_STEPS) - 1
        ph = icon_photo(icon, dp(32), T.CYAN)
        ic.configure(image=ph)
        ic.image = ph
        title.configure(text=head)
        text.configure(text=body)
        dots.delete("all")
        for k in range(len(WELCOME_STEPS)):
            x = dp(5) + k * dp(18)
            dots.create_oval(x - dp(4), dp(1), x + dp(4), dp(9), fill=T.CYAN if k == i else T.BORDER_STRONG, outline="")
        for b in (nxt, back, quit_b):
            b.pack_forget()
        nxt.update_button(text="I understand, start SnapType" if last else "Next",
                          command=(lambda: dlg.finish("ok")) if last else advance)
        nxt.pack(side="right")
        if i:
            back.pack(side="right", padx=(0, dp(10)))
        if last:
            quit_b.pack(side="left")

    def advance():
        state["i"] += 1
        render()

    def go_back():
        state["i"] = max(0, state["i"] - 1)
        render()

    back.update_button(command=go_back)
    dlg.set_default(nxt)
    render()
    return dlg.present(nxt) == "ok"


def close_choice(parent) -> str:
    """Shown the first time the window is closed. Returns 'tray' or 'quit'."""
    dlg = Modal(parent, "Keep SnapType running?", 460)
    dlg.on_close = lambda: dlg.finish("tray")
    head = tk.Frame(dlg.body, bg=T.SURFACE)
    head.pack(fill="x")
    icon_label(head, "bolt", 22, T.CYAN, T.SURFACE).pack(side="left", anchor="n", padx=(0, dp(14)))
    col = tk.Frame(head, bg=T.SURFACE)
    col.pack(side="left", fill="x", expand=True)
    label(col, "Keep SnapType running?", "heading", T.TEXT, T.SURFACE).pack(anchor="w")
    label(col, "Closing the window keeps SnapType in the system tray so your snippets keep expanding. "
               "Right-click the tray icon to quit, or quit now.", "body", T.TEXT_DIM, T.SURFACE,
          wraplength=dp(340), justify="left").pack(anchor="w", pady=(dp(6), 0))
    keep = Button(dlg.body, text="Keep in tray", variant="primary", bg=T.SURFACE, command=lambda: dlg.finish("tray"))
    quit_b = Button(dlg.body, text="Quit SnapType", variant="secondary", bg=T.SURFACE, command=lambda: dlg.finish("quit"))
    _button_row(dlg.body, keep, quit_b).pack(fill="x", pady=(dp(22), 0))
    dlg.set_default(keep)
    return dlg.present(keep) or "tray"
