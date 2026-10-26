"""Snippet storage, validation and CSV import/export."""
from __future__ import annotations

import csv
import datetime
import re
import threading
from pathlib import Path

from .storage import load_json, save_json

ABBR_RE = re.compile(r"^[a-z0-9']{2,32}$")
MAX_EXPANSION = 4000

# Abbreviations that would rewrite ordinary words people type on purpose.
COMMON_WORDS = frozenset("""
    a an and are as at be but by do for from go had has have he her him his how i if in is it its
    me my no not of on or our she so that the their them then there they this to up us was we were
    what when who why will with you your yes ok am can did get got let may new now off old one out
    say see she too two use way
""".split())

DEFAULT_SNIPPETS: dict[str, tuple[str, str]] = {
    "gm": ("good morning", "Greetings"), "gn": ("good night", "Greetings"),
    "hru": ("how are you", "Greetings"), "ily": ("i love you", "Affection"),
    "ty": ("thank you", "Gratitude"), "yw": ("you're welcome", "Gratitude"),
    "np": ("no problem", "Gratitude"), "omw": ("on my way", "Status"),
    "brb": ("be right back", "Status"), "afk": ("away from keyboard", "Status"),
    "gtg": ("got to go", "Status"), "ttyl": ("talk to you later", "Status"),
    "nvm": ("never mind", "Status"), "lmk": ("let me know", "Status"),
    "idk": ("i don't know", "Opinion"), "imo": ("in my opinion", "Opinion"),
    "tbh": ("to be honest", "Opinion"), "fyi": ("for your information", "Info"),
    "asap": ("as soon as possible", "Info"), "rn": ("right now", "Info"),
}


def validate_abbr(abbr: str) -> tuple[bool, str]:
    """Return (ok, message). ok=False means it can never fire or is unsafe."""
    a = abbr.strip().lower()
    if not a:
        return False, "Abbreviation is required."
    if not ABBR_RE.match(a):
        return False, ("Use 2–32 letters, digits or apostrophes only — spaces and "
                       "symbols can never be typed as one word, so it would never fire.")
    if a in COMMON_WORDS:
        return False, f'"{a}" is a common word and would rewrite text you type on purpose.'
    return True, ""


class SnippetManager:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.enabled = True
        self._lock = threading.RLock()
        self.snippets: dict[str, dict[str, str]] = {}
        raw = load_json(self.path, None)
        if isinstance(raw, dict) and raw:
            for k, v in raw.items():
                if isinstance(v, str):
                    self.snippets[str(k).lower()] = {"exp": v, "tags": ""}
                elif isinstance(v, dict) and isinstance(v.get("exp"), str):
                    self.snippets[str(k).lower()] = {"exp": v["exp"],
                                                     "tags": str(v.get("tags", ""))}
        else:
            for k, (exp, tag) in DEFAULT_SNIPPETS.items():
                self.snippets[k] = {"exp": exp, "tags": tag}
            self._save()

    def get(self, abbr: str) -> str | None:
        if not self.enabled:
            return None
        with self._lock:
            item = self.snippets.get(abbr.lower())
            return item["exp"] if item else None

    def upsert(self, abbr: str, expansion: str, tags: str = "", _save: bool = True) -> bool:
        a, e = abbr.strip().lower(), expansion.strip()
        if not e or len(e) > MAX_EXPANSION or not validate_abbr(a)[0]:
            return False
        with self._lock:
            self.snippets[a] = {"exp": e, "tags": tags.strip()}
        if _save:
            self._save()
        return True

    def delete(self, abbr: str) -> bool:
        k = abbr.strip().lower()
        with self._lock:
            if k not in self.snippets:
                return False
            del self.snippets[k]
        self._save()
        return True

    def export_csv(self, path: str) -> None:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["abbreviation", "expansion", "tags"])
            with self._lock:
                for k, v in sorted(self.snippets.items()):
                    w.writerow([k, v["exp"], v.get("tags", "")])

    def import_csv(self, path: str) -> int:
        """Import rows; invalid ones are skipped and counted in ``last_skipped``."""
        n, self.last_skipped = 0, 0
        with open(path, encoding="utf-8-sig", newline="") as f:
            for row in csv.reader(f):
                if len(row) < 2 or row[0].strip().lower() in ("abbreviation", "abbr", ""):
                    continue
                expansion = row[1].replace("\r\n", "\n").replace("\r", "\n")
                if self.upsert(row[0], expansion, row[2] if len(row) > 2 else "", _save=False):
                    n += 1
                else:
                    self.last_skipped += 1
        if n:
            self._save()
        return n

    last_skipped = 0

    def _save(self) -> None:
        with self._lock:
            snapshot = {k: dict(v) for k, v in self.snippets.items()}
        save_json(self.path, snapshot)

    def flush(self) -> None:
        self._save()

    def get_last_saved_time(self) -> str:
        try:
            if not self.path.exists():
                return "Never"
            return datetime.datetime.fromtimestamp(self.path.stat().st_mtime).strftime("%b %d, %I:%M %p")
        except OSError:
            return "Unknown"
