"""Snippets: searchable list on the left, an always-visible editor on the right."""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, ttk

from snapcore.expand import render
from snapcore.snippets import MAX_EXPANSION, validate_abbr

from .. import dialogs
from .. import theme as T
from ..theme import dp
from ..widgets import Button, Card, Field, ScrollFrame, TextArea, caps_label, icon_label, label
from . import Page
from .common import clip

VARIABLES = ("date", "time", "datetime", "day", "clipboard")
STARTERS = (("sig", "Best regards,\nYour name"), ("eml", "you@example.com"), ("today", "{{date}}"),
            ("paste", "{{clipboard}}"))
HEADERS = {"abbr": "ABBREVIATION", "expansion": "EXPANDS TO", "tags": "TAGS"}


class SnippetsPage(Page):
    scrolls = False

    def build(self):
        self.columnconfigure(0, weight=3, uniform="s")
        self.columnconfigure(1, weight=2, uniform="s", minsize=dp(340))
        self.rowconfigure(0, weight=1)
        self._editing: str | None = None
        self._snapshot = ("", "", "")
        self._reverting = False
        self._sort = {"col": "abbr", "reverse": False}
        self._search_job = None
        self._build_list()
        self._build_editor()
        self._clear(force=True)

    # ═══ list ═════════════════════════════════════════════════════════════
    def _build_list(self):
        card = Card(self, pad_x=16, pad_y=14)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, dp(8)), pady=(0, dp(6)))
        c = card.content
        bar = tk.Frame(c, bg=card.fill)
        bar.pack(fill="x", pady=(0, dp(10)))
        self.search_var = tk.StringVar()
        self.search = Field(bar, self.search_var, placeholder="Search snippets", icon="search", clearable=True, width=18)
        self.search.pack(side="left", fill="x", expand=True)
        Button(bar, text="New", icon="plus", variant="primary", size="sm", bg=card.fill, command=self.on_new
               ).pack(side="right")
        Button(bar, icon="download", variant="quiet", size="sm", bg=card.fill, tooltip="Export to CSV",
               command=self._export).pack(side="right")
        Button(bar, icon="upload", variant="quiet", size="sm", bg=card.fill, tooltip="Import from CSV",
               command=self._import).pack(side="right")
        self.search_var.trace_add("write", lambda *_: self._debounce_fill())

        foot = tk.Frame(c, bg=card.fill)
        foot.pack(side="bottom", fill="x", pady=(dp(10), 0))
        self.count = label(foot, "", "small", T.TEXT_FAINT, card.fill)
        self.count.pack(side="left")
        self.saved = label(foot, "", "small", T.TEXT_FAINT, card.fill, anchor="e")
        self.saved.pack(side="right")

        wrap = tk.Frame(c, bg=card.fill)
        wrap.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(wrap, columns=("abbr", "expansion", "tags"), show="headings", style="SN.Treeview",
                                 selectmode="browse", height=8)
        for col, w, stretch in (("abbr", 110, False), ("expansion", 260, True), ("tags", 100, False)):
            self.tree.column(col, width=dp(w), minwidth=dp(60), anchor="w", stretch=stretch)
            self.tree.heading(col, text=HEADERS[col], anchor="w", command=lambda k=col: self._sort_by(k))
        self.tree.tag_configure("odd", background=T.blend(T.WHITE, 0.025, T.PANEL))
        self.tree.tag_configure("even", background=T.PANEL)
        sb = ttk.Scrollbar(wrap, orient="vertical", style="SN.Vertical.TScrollbar", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select, add="+")
        self.tree.bind("<Delete>", lambda e: self._delete(), add="+")
        self.empty = label(wrap, "", "body", T.TEXT_DIM, card.fill, anchor="center", justify="center",
                           wraplength=dp(300))

    def _debounce_fill(self):
        if self._search_job is not None:
            self.after_cancel(self._search_job)
        self._search_job = self.after(120, self._fill)

    def _sort_by(self, col):
        if self._sort["col"] == col:
            self._sort["reverse"] = not self._sort["reverse"]
        else:
            self._sort.update(col=col, reverse=False)
        self._fill()

    def _fill(self):
        self._search_job = None
        sm = self.app.sm
        q = self.search_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        key = {"abbr": lambda kv: kv[0], "expansion": lambda kv: kv[1]["exp"].lower(),
               "tags": lambda kv: (kv[1].get("tags", "").lower(), kv[0])}[self._sort["col"]]
        shown = 0
        for abbr, val in sorted(sm.snippets.items(), key=key, reverse=self._sort["reverse"]):
            if q and q not in abbr and q not in val["exp"].lower() and q not in val.get("tags", "").lower():
                continue
            self.tree.insert("", "end", iid=abbr, values=(abbr, clip(val["exp"], 90), val.get("tags", "")),
                             tags=("even" if shown % 2 == 0 else "odd",))
            shown += 1
        arrow = " \u25bc" if self._sort["reverse"] else " \u25b2"
        for col, text in HEADERS.items():
            self.tree.heading(col, text=text + (arrow if col == self._sort["col"] else ""))
        if shown == 0:
            self.empty.configure(text=f"No snippets match \u201c{q}\u201d." if q else
                                 "No snippets yet. Add your first one on the right.")
            self.empty.place(relx=0.5, rely=0.45, anchor="center")
        else:
            self.empty.place_forget()
        total = len(sm.snippets)
        self.count.configure(text=f"{shown} of {total} snippets" if q else f"{total} snippet{'s' if total != 1 else ''}")
        self.saved.configure(text=f"Saved {sm.get_last_saved_time()}")
        if self._editing and self.tree.exists(self._editing):
            self._reverting = True
            self.tree.selection_set(self._editing)
            self._reverting = False

    def _on_select(self, _e=None):
        if self._reverting:
            return
        sel = self.tree.selection()
        if not sel or sel[0] == self._editing:
            return
        if not self._confirm_discard():
            self._reverting = True
            if self._editing and self.tree.exists(self._editing):
                self.tree.selection_set(self._editing)
            else:
                self.tree.selection_remove(*self.tree.selection())
            self._reverting = False
            return
        self._load(sel[0])

    # ═══ editor ═══════════════════════════════════════════════════════════
    def _build_editor(self):
        card = Card(self, pad_x=6, pad_y=6)
        card.grid(row=0, column=1, sticky="nsew", padx=(dp(8), 0), pady=(0, dp(6)))
        scroll = ScrollFrame(card.content, bg=card.fill, pad_right=12)
        scroll.pack(fill="both", expand=True)
        ed = scroll.inner
        self._ed_bg = card.fill
        pad = dict(padx=dp(14))

        head = tk.Frame(ed, bg=card.fill)
        head.pack(fill="x", pady=(dp(12), dp(14)), **pad)
        self.ed_icon = icon_label(head, "plus", 18, T.CYAN, card.fill)
        self.ed_icon.pack(side="left", padx=(0, dp(10)))
        self.ed_title = label(head, "New snippet", "heading", T.TEXT, card.fill)
        self.ed_title.pack(side="left")

        caps_label(ed, "Abbreviation", bg=card.fill).pack(anchor="w", **pad)
        self.abbr_var = tk.StringVar()
        self.abbr = Field(ed, self.abbr_var, placeholder="omw", mono=True, width=16, command=self._save)
        self.abbr.pack(fill="x", pady=(dp(6), 0), **pad)
        self.abbr_msg = label(ed, "", "small", T.TEXT_FAINT, card.fill, wraplength=dp(280), justify="left")
        self.abbr_msg.pack(anchor="w", pady=(dp(4), dp(10)), **pad)

        caps_label(ed, "Expands to", bg=card.fill).pack(anchor="w", **pad)
        self.exp = TextArea(ed, placeholder="on my way", height=4, on_change=self._changed, on_submit=self._save)
        self.exp.pack(fill="x", pady=(dp(6), dp(6)), **pad)
        chips = tk.Frame(ed, bg=card.fill)
        chips.pack(fill="x", **pad)
        for v in VARIABLES:
            Button(chips, text=v, variant="chip", size="sm", bg=card.fill,
                   command=lambda v=v: self.exp.insert_at_cursor("{{" + v + "}}")).pack(side="left", padx=(0, dp(2)))
        self.counter = label(ed, "", "small", T.TEXT_FAINT, card.fill)
        self.counter.pack(anchor="e", pady=(dp(2), dp(8)), **pad)

        caps_label(ed, "Tags (optional)", bg=card.fill).pack(anchor="w", **pad)
        self.tags_var = tk.StringVar()
        self.tags = Field(ed, self.tags_var, placeholder="Work, Casual", width=16, command=self._save)
        self.tags.pack(fill="x", pady=(dp(6), dp(12)), **pad)

        box = tk.Frame(ed, bg=T.INPUT, highlightthickness=1, highlightbackground=T.BORDER)
        box.pack(fill="x", **pad)
        caps_label(box, "Preview", bg=T.INPUT).pack(anchor="w", padx=dp(12), pady=(dp(8), 0))
        self.preview = label(box, "", "mono_s", T.TEXT, T.INPUT, wraplength=dp(270), justify="left")
        self.preview.pack(anchor="w", padx=dp(12), pady=(dp(2), dp(10)))

        row = tk.Frame(ed, bg=card.fill)
        row.pack(fill="x", pady=(dp(16), 0), **pad)
        self.save_btn = Button(row, text="Add snippet", icon="check", variant="primary", bg=card.fill,
                               command=self._save)
        self.save_btn.pack(side="left")
        self.clear_btn = Button(row, text="Clear", variant="ghost", bg=card.fill, command=lambda: self._clear())
        self.clear_btn.pack(side="left", padx=(dp(6), 0))
        self.delete_btn = Button(row, icon="trash", variant="danger", bg=card.fill, tooltip="Delete this snippet",
                                 command=self._delete)
        self.delete_btn.pack(side="right")

        caps_label(ed, "Start from an idea", bg=card.fill).pack(anchor="w", pady=(dp(18), dp(6)), **pad)
        ideas = tk.Frame(ed, bg=card.fill)
        ideas.pack(fill="x", pady=(0, dp(12)), **pad)
        for abbr, text in STARTERS:
            Button(ideas, text=abbr, variant="chip", size="sm", bg=card.fill,
                   command=lambda a=abbr, t=text: self._prefill(a, t)).pack(side="left", padx=(0, dp(2)))
        self.abbr_var.trace_add("write", lambda *_: self._changed())
        self.tags_var.trace_add("write", lambda *_: self._changed())

    # -- state --
    def _values(self):
        return self.abbr_var.get().strip().lower(), self.exp.value().strip(), self.tags_var.get().strip()

    def _dirty(self) -> bool:
        return self._values() != self._snapshot

    def _confirm_discard(self) -> bool:
        if not self._dirty():
            return True
        return dialogs.confirm(self.app.root, "Discard your changes?",
                               "This snippet has edits that haven't been saved.", ok="Discard changes",
                               cancel="Keep editing", danger=True)

    def _set_form(self, abbr, exp, tags):
        self.abbr_var.set(abbr)
        self.exp.set_value(exp)
        self.tags_var.set(tags)

    def _load(self, abbr):
        item = self.app.sm.snippets.get(abbr)
        if not item:
            return
        self._editing = abbr
        self._set_form(abbr, item["exp"], item.get("tags", ""))
        self._snapshot = self._values()
        self._changed()

    def _clear(self, force=False):
        if not force and not self._confirm_discard():
            return
        self._editing = None
        self._set_form("", "", "")
        self._snapshot = ("", "", "")
        if self.tree.selection():
            self._reverting = True
            self.tree.selection_remove(*self.tree.selection())
            self._reverting = False
        self._changed()

    def _prefill(self, abbr, text):
        if abbr in self.app.sm.snippets:
            self.app.toast(f"\u201c{abbr}\u201d already exists. Opened it for editing.", "info")
            if self._confirm_discard():
                self._load(abbr)
            return
        if not self._confirm_discard():
            return
        self._editing = None
        self._set_form(abbr, text, "")
        self._snapshot = ("", "", "")
        self.exp.focus()

    def _changed(self):
        if not hasattr(self, "save_btn"):
            return
        a, e, _t = self._values()
        sm = self.app.sm
        msg, color, bad = "", T.TEXT_FAINT, False
        ok, why = validate_abbr(a) if len(a) >= 2 else (len(a) == 0, "")
        if a and len(a) >= 2 and not ok:
            msg, color, bad = why, T.ERROR, True
        elif a and a != self._editing and a in sm.snippets:
            msg, color = f"\u201c{a}\u201d already exists. Saving will replace it.", T.AMBER
        elif not a:
            msg = "Type this and a space (or Enter, Tab, punctuation) to expand."
        self.abbr_msg.configure(text=msg, fg=color)
        self.abbr.set_error(bad)

        n = len(self.exp.value())
        over = n > MAX_EXPANSION
        self.counter.configure(text=f"{n:,} / {MAX_EXPANSION:,}",
                               fg=T.ERROR if over else (T.AMBER if n > MAX_EXPANSION * 0.9 else T.TEXT_FAINT))
        if a and e and not bad:
            shown = render(e, a, clipboard=lambda: "\u2039clipboard\u203a")
            self.preview.configure(text=f"{a} + space  \u2192  {clip(shown, 160)}", fg=T.TEXT)
        else:
            self.preview.configure(text="Fill in both fields to see what will be typed.", fg=T.TEXT_FAINT)

        editing = self._editing is not None
        self.ed_title.configure(text=f"Edit \u201c{self._editing}\u201d" if editing else "New snippet")
        self.ed_icon.configure(image=self._icon("edit" if editing else "plus"))
        self.ed_icon.image = self._icon("edit" if editing else "plus")
        can_save = bool(a and e and ok and not over and len(a) >= 2) and (self._dirty() or not editing)
        replacing = bool(a and a != self._editing and a in sm.snippets)
        self.save_btn.update_button(text="Replace" if replacing else ("Save changes" if editing else "Add snippet"),
                                    state="normal" if can_save else "disabled")
        if editing:
            self.delete_btn.pack(side="right")
        else:
            self.delete_btn.pack_forget()

    @staticmethod
    def _icon(name):
        from ..widgets import icon_photo
        return icon_photo(name, dp(18), T.CYAN)

    # ═══ actions ══════════════════════════════════════════════════════════
    def _save(self):
        if self.save_btn._cfg["state"] == "disabled":
            return
        a, e, t = self._values()
        sm = self.app.sm
        renamed_from = self._editing if (self._editing and self._editing != a) else None
        if not sm.upsert(a, e, t):
            self.app.toast("That snippet couldn't be saved. Check the abbreviation and text.", "error")
            return
        if renamed_from and renamed_from in sm.snippets:
            sm.delete(renamed_from)
        was_edit = self._editing is not None
        self.app.toast(f"Renamed to \u201c{a}\u201d" if renamed_from else (f"Saved \u201c{a}\u201d" if was_edit else
                                                                       f"Added \u201c{a}\u201d"), "success")
        self.app.refresh_pages()
        if was_edit:
            self._load(a)
        else:
            self._clear(force=True)
            self.abbr.focus()

    def _delete(self):
        a = self._editing
        if not a:
            sel = self.tree.selection()
            a = sel[0] if sel else None
        sm = self.app.sm
        if not a or a not in sm.snippets:
            return
        old = dict(sm.snippets[a])
        sm.delete(a)

        def undo():
            sm.upsert(a, old["exp"], old.get("tags", ""))
            self.app.refresh_pages()

        self._clear(force=True)
        self.app.refresh_pages()
        self.app.toast(f"Deleted \u201c{a}\u201d", "info", action=("Undo", undo))

    def _export(self):
        path = filedialog.asksaveasfilename(parent=self.app.root, defaultextension=".csv",
                                            filetypes=[("CSV", "*.csv")], initialfile="snippets.csv")
        if not path:
            return
        try:
            self.app.sm.export_csv(path)
            self.app.toast(f"Exported {len(self.app.sm.snippets)} snippets", "success")
        except OSError as exc:
            dialogs.alert(self.app.root, "Couldn't export", "SnapType couldn't write that file.", "error",
                          detail=str(exc))

    def _import(self):
        path = filedialog.askopenfilename(parent=self.app.root, filetypes=[("CSV", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        try:
            n = self.app.sm.import_csv(path)
        except (OSError, UnicodeError, ValueError) as exc:
            dialogs.alert(self.app.root, "Couldn't import", "SnapType couldn't read that file as a snippet list.",
                          "error", detail=str(exc))
            return
        skipped = self.app.sm.last_skipped
        note = f" ({skipped} skipped: invalid abbreviation or empty text)" if skipped else ""
        self.app.toast(f"Imported {n} snippet{'s' if n != 1 else ''}{note}", "success" if n else "warn")
        self.app.refresh_pages()

    # ═══ page hooks ═══════════════════════════════════════════════════════
    def on_show(self):
        self._fill()
        self._changed()
        self.after(60, lambda: self.winfo_exists() and self.search.focus())

    def refresh(self):
        self._fill()
        self._changed()

    def on_find(self):
        self.search.focus()

    def on_new(self):
        self._clear()
        self.abbr.focus()
