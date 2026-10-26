import datetime

from snapcore.expand import match_case, render

NOW = datetime.datetime(2026, 10, 25, 14, 5)


def test_case_matching():
    assert match_case("omw", "on my way") == "on my way"
    assert match_case("Omw", "on my way") == "On my way"
    assert match_case("OMW", "on my way") == "ON MY WAY"
    assert match_case("I", "i love you") == "I love you"


def test_variables():
    assert render("{{date}}", "x", NOW) == "2026-10-25"
    assert render("{{time}}", "x", NOW) == "02:05 PM"
    assert render("{{day}}", "x", NOW) == "Sunday"
    assert render("pasted: {{clipboard}}", "x", NOW, lambda: "hello") == "pasted: hello"


def test_clipboard_failure_is_safe():
    def boom():
        raise OSError
    assert render("a{{clipboard}}b", "x", NOW, boom) == "ab"
