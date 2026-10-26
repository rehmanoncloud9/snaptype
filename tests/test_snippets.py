import pytest

from snapcore.snippets import SnippetManager, validate_abbr


@pytest.mark.parametrize("abbr,ok", [
    ("omw", True), ("OMW", True), ("g'd", True), ("a1", True),
    ("x", False), ("", False), ("two words", False), ("g-m", False),
    ("the", False), ("and", False), ("x" * 33, False),
])
def test_validate(abbr, ok):
    assert validate_abbr(abbr)[0] is ok


def test_defaults_seeded_and_persisted(tmp_path):
    sm = SnippetManager(tmp_path / "s.json")
    assert sm.get("omw") == "on my way"
    assert SnippetManager(tmp_path / "s.json").get("omw") == "on my way"


def test_corrupt_snippets_are_not_overwritten(tmp_path):
    p = tmp_path / "s.json"
    p.write_text("{broken")
    SnippetManager(p)
    assert list(tmp_path.glob("s.json.corrupt-*"))
    assert "{broken" in next(tmp_path.glob("s.json.corrupt-*")).read_text()


def test_upsert_rejects_unfireable(tmp_path):
    sm = SnippetManager(tmp_path / "s.json")
    assert not sm.upsert("two words", "x")
    assert not sm.upsert("ok1", "   ")
    assert sm.upsert(" Hello1 ", " hi there ")
    assert sm.get("HELLO1") == "hi there"


def test_disabled_returns_none(tmp_path):
    sm = SnippetManager(tmp_path / "s.json")
    sm.enabled = False
    assert sm.get("omw") is None


def test_csv_roundtrip_with_bom_and_bad_rows(tmp_path):
    sm = SnippetManager(tmp_path / "s.json")
    sm.upsert("sig1", "Best,\nAbdul", "Mail")
    out = tmp_path / "e.csv"
    sm.export_csv(str(out))
    fresh = SnippetManager(tmp_path / "t.json")
    fresh.snippets.clear()
    out.write_text(out.read_text(encoding="utf-8-sig") + "bad abbr,nope,\n", encoding="utf-8-sig")
    assert fresh.import_csv(str(out)) == len(sm.snippets)
    assert fresh.last_skipped == 1
    assert fresh.get("sig1") == "Best,\nAbdul"


def test_delete(tmp_path):
    sm = SnippetManager(tmp_path / "s.json")
    assert sm.delete("omw") and not sm.delete("omw")
