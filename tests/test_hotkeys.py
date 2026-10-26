import pytest

from snapcore.hotkeys import from_tk_event, normalize, pretty, try_normalize


@pytest.mark.parametrize("raw,expected", [
    ("Ctrl+Shift+S", "ctrl+shift+s"), ("shift+ctrl+s", "ctrl+shift+s"),
    ("control+alt+delete", "ctrl+alt+delete"), ("alt+F4", "alt+f4"), ("F9", "f9"),
    ("win+z", "windows+z"), ("ctrl+Escape", "ctrl+esc"),
])
def test_normalize_accepts(raw, expected):
    assert normalize(raw) == expected


@pytest.mark.parametrize("raw", ["a", "shift+a", "", "  ", "ctrl", "ctrl+a+b", "ctrl+nonsense", "space"])
def test_normalize_rejects_combos_that_would_break_typing(raw):
    with pytest.raises(ValueError):
        normalize(raw)


def test_try_normalize_falls_back():
    assert try_normalize("a", "ctrl+shift+s") == "ctrl+shift+s"
    assert try_normalize("Ctrl+K", "x") == "ctrl+k"


def test_pretty_keycaps():
    assert pretty("ctrl+shift+s") == ["Ctrl", "Shift", "S"]
    assert pretty("alt+page down") == ["Alt", "PgDn"]
    assert pretty("ctrl+up") == ["Ctrl", "Up"]
    assert pretty("f5") == ["F5"]


def test_modifier_only_press_is_pending():
    assert from_tk_event("Control_L", 0x4, "win32") is None
    assert from_tk_event("Shift_R", 0x1, "win32") is None


def test_tk_event_translation_windows():
    assert from_tk_event("S", 0x5, "win32") == "ctrl+shift+s"
    assert from_tk_event("F5", 0x20000, "win32") == "alt+f5"
    assert from_tk_event("exclam", 0x5, "win32") == "ctrl+shift+1"
    assert from_tk_event("Prior", 0x4, "win32") == "ctrl+page up"
    assert from_tk_event("space", 0x20004, "win32") == "ctrl+alt+space"


def test_tk_event_alt_mask_differs_on_x11():
    assert from_tk_event("k", 0x8, "linux") == "alt+k"
    assert from_tk_event("k", 0x8, "win32") == "k"      # 0x8 is NumLock on Windows, not Alt


def test_unknown_keysym_is_rejected_by_normalize():
    combo = from_tk_event("dead_acute", 0x4, "win32")
    with pytest.raises(ValueError):
        normalize(combo)
