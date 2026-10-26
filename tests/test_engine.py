"""Engine tests against a fake keyboard that simulates a text field."""
import pytest

from snapcore.config import Config
from snapcore.engine import Engine
from snapcore.snippets import SnippetManager
from snapcore.stats import Stats


class FakeKeyboard:
    """Records injected input and applies it to a simulated text box."""

    def __init__(self):
        self.text = ""
        self.cb = None
        self.pressed = set()
        self.hotkeys = {}
        self.engine = None

    # backend API
    def on_press(self, cb): self.cb = cb
    def unhook_all(self): self.cb = None; self.hotkeys.clear()
    def add_hotkey(self, combo, fn): self.hotkeys[combo] = fn
    def is_pressed(self, k): return k in self.pressed
    def backspace(self, n): self.text = self.text[:-n] if n else self.text
    def write(self, text, delay):
        self.text += text
        # the real hook sees our own keystrokes echoed back
        for ch in text:
            if self.cb:
                self.cb({" ": "space", "\n": "enter"}.get(ch, ch))

    # user-side helpers
    def type(self, s):
        for ch in s:
            self.press({" ": "space", "\n": "enter"}.get(ch, ch), ch)

    def press(self, name, ch=None):
        if name == "backspace":
            self.text = self.text[:-1]
        else:
            self.text += ch if ch is not None else name
        if self.cb:
            self.cb(name)


class Clock:
    t = 100.0
    def __call__(self): return self.t


class Rig:
    title = "Notepad"


@pytest.fixture
def rig(tmp_path):
    r = Rig()
    r.kb, r.clock, r.queue = FakeKeyboard(), Clock(), []
    r.cfg = Config(tmp_path / "c.json")
    sm = SnippetManager(tmp_path / "s.json")
    sm.upsert("gm2", "gm2 everyone")      # expansion that contains its own abbreviation
    r.stats = Stats(tmp_path / "st.json")
    r.eng = Engine(sm, r.cfg, r.stats, r.kb, window_title=lambda: r.title,
                   clipboard=lambda: "CLIP", scheduler=lambda d, fn: r.queue.append(fn),
                   clock=r.clock)
    r.eng.setup(lambda: None)
    r.eng.start()
    return r


def flush(rig):
    while rig.queue:
        rig.queue.pop(0)()


def test_basic_expansion(rig):
    rig.kb.type("omw ")
    flush(rig)
    assert rig.kb.text == "on my way "
    assert rig.stats.total() == 1


def test_case_preserved(rig):
    rig.kb.type("Omw ")
    flush(rig)
    assert rig.kb.text == "On my way "


def test_punctuation_trigger_kept(rig):
    rig.kb.type("omw.")
    flush(rig)
    assert rig.kb.text == "on my way."


def test_no_expansion_inside_other_words(rig):
    rig.kb.type("tomw ")
    flush(rig)
    assert rig.kb.text == "tomw "


def test_own_output_does_not_retrigger(rig):
    rig.kb.type("gm2 ")
    flush(rig)
    assert rig.kb.text == "gm2 everyone "
    assert rig.stats.total() == 1 and not rig.queue


def test_aborts_if_user_keeps_typing(rig):
    rig.kb.type("omw ")
    rig.kb.type("x")                      # typed before the timer fired
    flush(rig)
    assert rig.kb.text == "omw x"


def test_idle_gap_resets_buffer(rig):
    rig.kb.type("om")
    rig.clock.t += 10
    rig.kb.type("w ")
    flush(rig)
    assert rig.kb.text == "omw "


def test_ctrl_resets_buffer(rig):
    rig.kb.type("om")
    rig.kb.pressed.add("ctrl")
    rig.kb.press("v", "")
    rig.kb.pressed.clear()
    rig.kb.type("w ")
    flush(rig)
    assert rig.kb.text == "omw "


def test_backspace_edits_buffer(rig):
    rig.kb.type("omx")
    rig.kb.press("backspace")
    rig.kb.type("w ")
    flush(rig)
    assert rig.kb.text == "on my way "


def test_backspace_right_after_expansion_undoes_it(rig):
    rig.kb.type("omw ")
    flush(rig)
    rig.clock.t += 0.5                    # a human reaction time later
    rig.kb.press("backspace")             # app deletes the trailing space
    flush(rig)
    assert rig.kb.text == "omw"
    rig.kb.type(" ")                      # must not re-expand
    flush(rig)
    assert rig.kb.text == "omw "


def test_undo_hotkey_restores_abbreviation_and_trigger(rig):
    rig.kb.type("omw ")
    flush(rig)
    rig.eng.undo()
    assert rig.kb.text == "omw "
    rig.eng.undo()                        # nothing left to undo
    assert rig.kb.text == "omw "


def test_blocked_windows(rig):
    rig.title = "Bitwarden - Log in"
    rig.kb.type("omw ")
    flush(rig)
    assert rig.kb.text == "omw "
    rig.title = "SnapType  v1.5.0"
    rig.kb.text = ""
    rig.kb.type("omw ")
    flush(rig)
    assert rig.kb.text == "omw "


def test_sensitive_skip_can_be_disabled(rig):
    rig.cfg.set("skip_sensitive_windows", False)
    rig.title = "Enter password"
    rig.kb.type("omw ")
    flush(rig)
    assert rig.kb.text == "on my way "


def test_whitelist_and_blacklist(rig):
    rig.cfg.set("app_list", ["Discord"])
    rig.cfg.set("app_mode", "include")
    rig.title = "Notepad"
    rig.kb.type("omw ")
    flush(rig)
    assert rig.kb.text == "omw "
    rig.kb.text, rig.title = "", "Discord - general"
    rig.kb.type("omw ")
    flush(rig)
    assert rig.kb.text == "on my way "
    rig.cfg.set("app_mode", "exclude")
    rig.kb.text = ""
    rig.kb.type("omw ")
    flush(rig)
    assert rig.kb.text == "omw "


def test_stop_unhooks_and_keeps_toggle(rig):
    rig.eng.stop()
    assert rig.kb.cb is None
    assert "ctrl+shift+s" in rig.kb.hotkeys
    assert "ctrl+shift+u" not in rig.kb.hotkeys


def test_bad_hotkey_does_not_crash(rig):
    def bad(combo, fn):
        raise ValueError(combo)
    rig.kb.add_hotkey = bad
    rig.eng.reregister()


def test_own_window_is_blocked_except_in_the_try_it_box(rig):
    rig.title = "SnapType  v1.5.0"
    rig.kb.type("omw ")
    flush(rig)
    assert rig.kb.text == "omw "
    rig.eng.allow_own_window = True
    rig.kb.text = ""
    rig.kb.type("omw ")
    flush(rig)
    assert rig.kb.text == "on my way "


def test_manual_start_cancels_pending_snooze(rig):
    fired = []
    rig.eng.snooze(5, on_wake=lambda: fired.append(1))
    assert not rig.eng.active and rig.eng._snooze is not None
    rig.eng.start()
    assert rig.eng.active and rig.eng._snooze is None and not fired


def test_snooze_wakes_exactly_once(rig):
    woke = []
    rig.eng.snooze(0.0001, on_wake=lambda: woke.append(1))
    import time
    time.sleep(0.2)
    assert rig.eng.active and woke == [1] and rig.eng._snooze is None
