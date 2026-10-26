from snapcore.startup import startup_command


def test_frozen_uses_only_exe():
    assert startup_command(True, r"C:\Apps\SnapType.exe") == r'"C:\Apps\SnapType.exe" --tray'


def test_source_run_includes_script(tmp_path):
    cmd = startup_command(False, "/usr/bin/python3", "/x/snaptype.py")
    assert cmd == '"/usr/bin/python3" "/x/snaptype.py" --tray'


def test_prefers_pythonw(tmp_path):
    (tmp_path / "python.exe").write_text("")
    (tmp_path / "pythonw.exe").write_text("")
    cmd = startup_command(False, str(tmp_path / "python.exe"), "s.py")
    assert "pythonw.exe" in cmd


def test_every_login_entry_starts_hidden():
    assert startup_command(True, "a.exe").endswith(" --tray")
    assert startup_command(False, "/p", "s.py").endswith(" --tray")
