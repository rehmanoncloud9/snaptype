from snapcore.config import Config, sanitize


def test_sanitize_clamps_and_repairs():
    d = sanitize({"replace_delay": "oops", "snooze_minutes": 99999, "app_mode": "weird",
                  "app_list": "notalist", "toggle_hotkey": ""})
    assert d["replace_delay"] == 0.006
    assert d["snooze_minutes"] == 240
    assert d["app_mode"] == "all" and d["app_list"] == []
    assert d["toggle_hotkey"] == "ctrl+shift+s"


def test_old_ctrl_z_undo_is_migrated_once():
    assert sanitize({"undo_hotkey": "ctrl+z"})["undo_hotkey"] == "ctrl+shift+u"
    assert sanitize({"undo_hotkey": "ctrl+z", "config_version": 2})["undo_hotkey"] == "ctrl+z"


def test_persist_and_flush(tmp_path):
    c = Config(tmp_path / "c.json")
    c.set("snooze_minutes", 9)
    c.flush()
    assert Config(tmp_path / "c.json").get("snooze_minutes") == 9


def test_garbage_file_falls_back(tmp_path):
    p = tmp_path / "c.json"
    p.write_text("[1,2,3]")
    assert Config(p).get("app_mode") == "all"


def test_hotkeys_that_would_break_typing_are_replaced():
    d = sanitize({"toggle_hotkey": "a", "undo_hotkey": "shift+b"})
    assert d["toggle_hotkey"] == "ctrl+shift+s" and d["undo_hotkey"] == "ctrl+shift+u"


def test_hotkeys_are_canonicalised():
    assert sanitize({"toggle_hotkey": "Shift+Control+K"})["toggle_hotkey"] == "ctrl+shift+k"


def test_identical_hotkeys_are_separated():
    d = sanitize({"toggle_hotkey": "ctrl+k", "undo_hotkey": "ctrl+k"})
    assert d["toggle_hotkey"] != d["undo_hotkey"]


def test_new_v15_defaults():
    d = sanitize({})
    assert d["auto_start"] is True and d["sidebar_collapsed"] is False
