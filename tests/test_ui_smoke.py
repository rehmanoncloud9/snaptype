"""Builds the whole UI and drives it. Needs a display (CI runs it under xvfb / on Windows);
skipped when Tk or a display isn't available."""
import threading
import types

import pytest

tk = pytest.importorskip("tkinter")
try:
    _probe = tk.Tk()
    _probe.destroy()
except tk.TclError:                                       # no display
    pytest.skip("no display available", allow_module_level=True)

from snapcore.snippets import SnippetManager  # noqa: E402
from snapcore.storage import save_json  # noqa: E402
from snapui import dialogs  # noqa: E402
from snapui.app import PAGES, SnapTypeApp  # noqa: E402


class NullKeyboard:
    def __init__(self):
        self.hotkeys = {}

    def on_press(self, cb): self.cb = cb
    def unhook_all(self): self.hotkeys.clear()
    def add_hotkey(self, combo, fn): self.hotkeys[combo] = fn
    def is_pressed(self, k): return False
    def backspace(self, n): pass
    def write(self, text, delay): pass

    def parse_hotkey(self, combo):
        if combo in ("ctrl+f4",):
            raise ValueError("unsupported")
        return combo


def make_app(tmp_path, consent=True, snippets=None, **cfg):
    save_json(tmp_path / "config.json", {"consent_given": consent, "auto_start": False, **cfg})
    if snippets:
        sm = SnippetManager(tmp_path / "snippets.json")
        for a, e in snippets.items():
            sm.upsert(a, e)
    app = SnapTypeApp(data_dir=tmp_path, keyboard_backend=NullKeyboard(), enable_tray=False)
    app.toasted = []
    app.toast = lambda msg, kind="info", action=None: app.toasted.append((msg, kind, action))
    return app


def answer_modal(app, result):
    """Close the next modal dialog that opens, as a person clicking a button would."""
    def go():
        for w in app.root.winfo_children():
            if isinstance(w, dialogs.Modal):
                w.finish(result)
                return
        app.root.after(20, go)
    app.root.after(20, go)


@pytest.fixture
def app(tmp_path):
    a = make_app(tmp_path, snippets={"omw": "on my way", "sig": "Best,\nMe"})
    yield a
    if not a._quitting:
        a.quit()


def test_every_page_builds_and_shows(app):
    for name, _, _ in PAGES:
        app.navigate(name)
        assert app.current == name and name in app.pages
        app.root.update_idletasks()
    # revisiting must not rebuild
    page = app.pages["Settings"]
    app.navigate("Settings")
    assert app.pages["Settings"] is page


def test_state_machine_snooze_rules(app):
    assert app.state == "off"
    app.snooze()                                          # snoozing while stopped must do nothing
    assert app.state == "off" and not app.engine.active
    app.toggle()
    assert app.state == "on" and app.engine.active
    app.snooze()
    assert app.state == "snoozed" and not app.engine.active
    app.toggle()                                          # Resume
    assert app.state == "on" and app.engine.active and app.engine._snooze is None
    app.toggle()
    assert app.state == "off" and not app.engine.active


def test_hotkey_thread_never_touches_tk_directly(app):
    t = threading.Thread(target=app.engine._toggle_fn)
    t.start()
    t.join()
    assert app.state == "off"                             # only queued
    app._drain()
    assert app.state == "on"


def test_activity_feed_and_metrics(app):
    app.navigate("Dashboard")
    app._record_activity("omw", "on my way\nthanks")
    page = app.pages["Dashboard"]
    assert len(app.activity) == 1
    assert page.feed.winfo_children()
    app.navigate("Stats")


def test_snippet_add_edit_rename_delete_undo(app):
    app.navigate("Snippets")
    page = app.pages["Snippets"]
    page.abbr_var.set("brb")
    page.exp.set_value("be right back")
    assert page.save_btn._cfg["state"] == "normal"
    page._save()
    assert app.sm.snippets["brb"]["exp"] == "be right back"
    assert page._editing is None                           # form cleared for the next one

    page._load("brb")
    page.abbr_var.set("brb2")
    page._save()
    assert "brb2" in app.sm.snippets and "brb" not in app.sm.snippets      # rename, not duplicate

    page._load("brb2")
    page._delete()
    assert "brb2" not in app.sm.snippets
    msg, kind, action = app.toasted[-1]
    assert action and action[0] == "Undo"
    action[1]()
    assert app.sm.snippets["brb2"]["exp"] == "be right back"


def test_snippet_validation_blocks_bad_input(app):
    app.navigate("Snippets")
    page = app.pages["Snippets"]
    page.abbr_var.set("Bad Abbr!")
    page.exp.set_value("x")
    assert page.save_btn._cfg["state"] == "disabled"
    page.abbr_var.set("wfh")
    page.exp.set_value("y" * 4001)
    assert page.save_btn._cfg["state"] == "disabled"       # over the 4000 limit
    page.exp.set_value("fine")
    assert page.save_btn._cfg["state"] == "normal"


def test_replacing_existing_snippet_is_explicit(app):
    app.navigate("Snippets")
    page = app.pages["Snippets"]
    page.abbr_var.set("omw")
    page.exp.set_value("different")
    assert page.save_btn._cfg["text"] == "Replace"
    assert "already exists" in page.abbr_msg.cget("text")


def test_unsaved_changes_are_guarded(app):
    app.navigate("Snippets")
    page = app.pages["Snippets"]
    page._load("omw")
    page.exp.set_value("edited but not saved")
    answer_modal(app, False)                               # "Keep editing"
    assert page._confirm_discard() is False
    answer_modal(app, True)
    assert page._confirm_discard() is True


def test_rules_add_remove_undo_and_modes(app):
    app.navigate("App Rules")
    page = app.pages["App Rules"]
    page._on_mode("include")
    assert app.cfg.get("app_mode") == "include"
    page._add("Word")
    page._add("word")                                      # duplicate, case-insensitive
    assert app.cfg.get("app_list") == ["Word"]
    page._add("Chrome")
    page._remove(0)
    assert app.cfg.get("app_list") == ["Chrome"]
    app.toasted[-1][2][1]()                                # Undo
    assert app.cfg.get("app_list") == ["Word", "Chrome"]


def test_rule_suggestion_extracts_app_name():
    from snapui.pages.rules import suggest_rule
    assert suggest_rule("Report.docx - Word") == "Word"
    assert suggest_rule("Inbox (3) - Gmail - Google Chrome") == "Google Chrome"
    assert suggest_rule("Untitled") == "Untitled"


def test_shortcut_recorder(app):
    app.navigate("Settings")
    row = app.pages["Settings"].hk_toggle
    ev = lambda k, s: types.SimpleNamespace(keysym=k, state=s)       # noqa: E731
    row.start()
    assert row.recording
    row._key(ev("Control_L", 0x4))                         # modifier alone: keep waiting
    assert row.recording
    row._key(ev("a", 0))                                   # would hijack typing: rejected
    assert app.cfg.get("toggle_hotkey") == "ctrl+shift+s"
    row._key(ev("u", 0x5))                                 # same as the undo shortcut: rejected
    assert app.cfg.get("toggle_hotkey") == "ctrl+shift+s"
    row._key(ev("F4", 0x4))                                # keyboard lib refuses: rejected
    assert app.cfg.get("toggle_hotkey") == "ctrl+shift+s"
    row._key(ev("k", 0x5))
    assert app.cfg.get("toggle_hotkey") == "ctrl+shift+k" and not row.recording
    assert "ctrl+shift+k" in app.engine.kb.hotkeys
    row.start()
    row._key(ev("Escape", 0))
    assert not row.recording and app.cfg.get("toggle_hotkey") == "ctrl+shift+k"


def test_settings_toggles_persist(app):
    app.navigate("Settings")
    var, t = app.pages["Settings"]._toggles["auto_start"]
    assert var.get() is False
    t.toggle()
    assert app.cfg.get("auto_start") is True


def test_try_it_box_only_unblocks_own_window_while_focused(app):
    app.navigate("Dashboard")
    app.root.update_idletasks()
    box = app.pages["Dashboard"].try_box.text
    box.event_generate("<FocusIn>")
    assert app.engine.allow_own_window is True
    app.navigate("Stats")
    assert app.engine.allow_own_window is False


def test_sidebar_collapses_on_narrow_windows(app):
    from snapui.theme import dp
    # Tk's default maximum follows the desktop size on hosted Windows runners.
    app.root.maxsize(dp(1600), dp(1000))
    app.root.geometry(f"{dp(900)}x{dp(650)}")
    app.root.update()
    app._apply_layout()
    assert app.collapsed
    app.root.geometry(f"{dp(1400)}x{dp(800)}")
    app.root.update()
    app._apply_layout()
    assert not app.collapsed


def test_welcome_flow_records_consent(tmp_path):
    app = make_app(tmp_path, consent=False)
    try:
        answer_modal(app, "ok")
        app._first_run()
        assert app.cfg.get("consent_given") is True
    finally:
        app.quit()


def test_declining_welcome_quits(tmp_path):
    app = make_app(tmp_path, consent=False)
    answer_modal(app, "quit")
    app._first_run()
    assert app._quitting and not app.cfg.get("consent_given")


def test_closing_without_a_tray_quits_instead_of_vanishing(app):
    app.tray_ok = False
    app._on_close()
    assert app._quitting


def test_first_close_asks_then_hides(app):
    app.tray_ok = True
    answer_modal(app, "tray")
    app._on_close()
    assert not app._quitting and app.cfg.get("tray_hint_shown") is True


def test_confirm_defaults_to_the_safe_button(app):
    answer_modal(app, True)
    assert dialogs.confirm(app.root, "Delete?", "Sure?", ok="Delete", danger=True) is True
    answer_modal(app, None)                                # closed with Esc / X
    assert dialogs.confirm(app.root, "Delete?", "Sure?", ok="Delete", danger=True) is False


def test_quit_persists_everything(app, tmp_path):
    app.stats.record("omw")
    app.quit()
    assert (tmp_path / "stats.json").exists() and (tmp_path / "config.json").exists()


def test_displayed_images_are_not_garbage_collected(app):
    fake = getattr(tk, "_fake", None)
    if fake is None:
        pytest.skip("only checkable against the strict fake")
    for name, _, _ in PAGES:
        app.navigate(name)
    app._record_activity("omw", "on my way")
    import gc
    gc.collect()
    assert fake.check_images() == []
