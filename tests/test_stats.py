import datetime

from snapcore.stats import Stats, estimate_minutes_saved, format_minutes
from snapcore.storage import save_json


class Day:
    d = datetime.date(2026, 10, 25)

    def __call__(self):
        return self.d


def test_record_counts_and_daily(tmp_path):
    day = Day()
    s = Stats(tmp_path / "s.json", today=day)
    s.record("omw")
    s.record("omw")
    day.d += datetime.timedelta(days=1)
    s.record("brb")
    assert s.total() == 3 and s.top(1) == [("omw", 2)]
    series = s.daily(3)
    assert [n for _, n in series] == [0, 2, 1]
    assert series[-1][0] == day.d and s.active_days() == 2


def test_persist_roundtrip(tmp_path):
    day = Day()
    s = Stats(tmp_path / "s.json", today=day)
    s.record("omw")
    s.flush()
    again = Stats(tmp_path / "s.json", today=day)
    assert again.total() == 1 and again.daily(1)[0][1] == 1


def test_legacy_flat_file_still_loads(tmp_path):
    save_json(tmp_path / "s.json", {"omw": 5, "brb": 2, "bad": "x", "neg": -1})
    s = Stats(tmp_path / "s.json", today=Day())
    assert s.total() == 7 and s.active_days() == 0


def test_reserved_keys_and_bad_dates_are_ignored(tmp_path):
    save_json(tmp_path / "s.json", {"__v": 2, "__counts": {"omw": 1, "__x": 9},
                                    "__daily": {"2026-10-25": 1, "nonsense": 4, "2026-10-24": True}})
    s = Stats(tmp_path / "s.json", today=Day())
    assert s.total() == 1 and s.active_days() == 1


def test_history_is_pruned(tmp_path):
    day = Day()
    s = Stats(tmp_path / "s.json", today=day)
    for _ in range(450):
        s.record("omw")
        day.d += datetime.timedelta(days=1)
    assert len(s._daily) == 400
    s.flush()


def test_reset_clears_everything(tmp_path):
    s = Stats(tmp_path / "s.json", today=Day())
    s.record("omw")
    s.reset()
    assert s.total() == 0 and s.active_days() == 0
    assert Stats(tmp_path / "s.json", today=Day()).total() == 0


def test_time_saved_ignores_deleted_snippets_and_negative_gain():
    snippets = {"omw": {"exp": "on my way"}, "ab": {"exp": "a"}}
    minutes = estimate_minutes_saved([("omw", 20), ("gone", 99), ("ab", 5)], snippets)
    assert minutes == 20 * (9 - 3) / 200


def test_format_minutes():
    assert format_minutes(0) == "0 min"
    assert format_minutes(0.4) == "<1 min"
    assert format_minutes(14.2) == "14 min"
    assert format_minutes(150) == "2.5 h"
