"""Usage counters with a per-day history, debounced thread-safe persistence.

File format (v2) keeps everything in one file under reserved ``__`` keys that can
never be an abbreviation. The legacy flat ``{abbr: count}`` format still loads.
"""
from __future__ import annotations

import collections
import datetime
import threading
from pathlib import Path
from typing import Callable, Iterable, Mapping

from .storage import load_json, save_json

HISTORY_DAYS = 400
CHARS_PER_MINUTE = 200   # 40 words/min x 5 characters: a deliberately modest typist


def estimate_minutes_saved(counts: Iterable[tuple[str, int]],
                           snippets: Mapping[str, Mapping[str, str]]) -> float:
    """Typing time saved, in minutes, for snippets that still exist.

    Counts the characters you did *not* have to type (expansion minus abbreviation).
    """
    saved = 0
    for abbr, n in counts:
        item = snippets.get(abbr)
        if item:
            saved += n * max(0, len(item.get("exp", "")) - len(abbr))
    return saved / CHARS_PER_MINUTE


def format_minutes(minutes: float) -> str:
    """Compact, human wording: ``0 min``, ``14 min``, ``2.5 h``."""
    if minutes < 1:
        return "0 min" if minutes <= 0 else "<1 min"
    if minutes < 90:
        return f"{round(minutes)} min"
    return f"{minutes / 60:.1f} h"


class Stats:
    def __init__(self, path: Path, today: Callable[[], datetime.date] = datetime.date.today):
        self.path = Path(path)
        self._today = today
        self._c: dict[str, int] = collections.defaultdict(int)
        self._daily: dict[str, int] = collections.defaultdict(int)
        raw = load_json(self.path, {})
        if isinstance(raw, dict):
            counts = raw.get("__counts") if raw.get("__v") == 2 else raw
            daily = raw.get("__daily") if raw.get("__v") == 2 else {}
            for k, v in (counts if isinstance(counts, dict) else {}).items():
                if isinstance(v, int) and not isinstance(v, bool) and v >= 0 and not str(k).startswith("__"):
                    self._c[str(k)] = v
            for k, v in (daily if isinstance(daily, dict) else {}).items():
                try:
                    datetime.date.fromisoformat(str(k))
                except ValueError:
                    continue
                if isinstance(v, int) and not isinstance(v, bool) and v >= 0:
                    self._daily[str(k)] = v
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    # ── recording ──────────────────────────────────────────────────────
    def record(self, word: str) -> None:
        with self._lock:
            self._c[word] += 1
            self._daily[self._today().isoformat()] += 1
            if len(self._daily) > HISTORY_DAYS:
                for old in sorted(self._daily)[:len(self._daily) - HISTORY_DAYS]:
                    del self._daily[old]
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(0.4, self.flush)
            self._timer.daemon = True
            self._timer.start()

    # ── queries ────────────────────────────────────────────────────────
    def top(self, n: int = 50):
        with self._lock:
            return sorted(self._c.items(), key=lambda x: (-x[1], x[0]))[:n]

    def total(self) -> int:
        with self._lock:
            return sum(self._c.values())

    def daily(self, days: int = 14) -> list[tuple[datetime.date, int]]:
        """Oldest-to-newest ``(date, count)`` for the last ``days`` days, zero-filled."""
        end = self._today()
        with self._lock:
            return [(d, self._daily.get(d.isoformat(), 0))
                    for d in (end - datetime.timedelta(days=i) for i in range(days - 1, -1, -1))]

    def active_days(self) -> int:
        with self._lock:
            return sum(1 for v in self._daily.values() if v > 0)

    # ── persistence ────────────────────────────────────────────────────
    def reset(self) -> None:
        with self._lock:
            self._c.clear()
            self._daily.clear()
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        self._write({}, {})

    def flush(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            counts, daily = dict(self._c), dict(self._daily)
        self._write(counts, daily)

    def _write(self, counts: dict, daily: dict) -> None:
        save_json(self.path, {"__v": 2, "__counts": counts, "__daily": daily})
