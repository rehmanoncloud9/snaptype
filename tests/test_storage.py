import json

from snapcore.storage import load_json, save_json


def test_roundtrip_and_backup(tmp_path):
    p = tmp_path / "a.json"
    assert save_json(p, {"x": 1})
    assert save_json(p, {"x": 2})
    assert load_json(p, None) == {"x": 2}
    assert json.loads((tmp_path / "a.json.bak").read_text()) == {"x": 1}
    assert not list(tmp_path.glob("*.tmp"))


def test_corrupt_file_is_quarantined_and_backup_used(tmp_path):
    p = tmp_path / "a.json"
    save_json(p, {"x": 1})
    save_json(p, {"x": 2})
    p.write_text("{not json")
    assert load_json(p, None) == {"x": 1}          # recovered from .bak
    assert list(tmp_path.glob("a.json.corrupt-*"))  # bad file preserved


def test_corrupt_without_backup_returns_default_but_keeps_file(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("garbage")
    assert load_json(p, {"d": 1}) == {"d": 1}
    assert list(tmp_path.glob("a.json.corrupt-*"))


def test_unserialisable_does_not_clobber(tmp_path):
    p = tmp_path / "a.json"
    save_json(p, {"x": 1})
    assert not save_json(p, {"x": object()})
    assert load_json(p, None) == {"x": 1}
