"""Pure text helpers: variable substitution and case matching."""
from __future__ import annotations

import datetime
from typing import Callable


def match_case(word: str, exp: str) -> str:
    """Mirror the capitalisation the user typed: OMW -> ON MY WAY, Omw -> On my way."""
    if not exp:
        return exp
    if len(word) > 1 and word.isupper():
        return exp.upper()
    if word[:1].isupper():
        return exp[:1].upper() + exp[1:]
    return exp


def render(exp: str, word: str, now: datetime.datetime | None = None,
           clipboard: Callable[[], str] | None = None) -> str:
    """Expand {{date}}, {{time}}, {{datetime}}, {{day}}, {{clipboard}} then match case."""
    now = now or datetime.datetime.now()
    if "{{" in exp:
        exp = (exp.replace("{{date}}", now.strftime("%Y-%m-%d"))
                  .replace("{{time}}", now.strftime("%I:%M %p"))
                  .replace("{{datetime}}", now.strftime("%Y-%m-%d %I:%M %p"))
                  .replace("{{day}}", now.strftime("%A")))
        if "{{clipboard}}" in exp:
            text = ""
            try:
                text = clipboard() if clipboard else ""
            except Exception:  # clipboard held by another app, etc.
                text = ""
            exp = exp.replace("{{clipboard}}", text or "")
    return match_case(word, exp)
