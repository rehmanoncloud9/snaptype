"""Hotkey parsing, validation and capture helpers (pure logic, no GUI imports).

Used by the Settings "record a shortcut" control and by config sanitising, so a
shortcut that would hijack ordinary typing (``a``, ``shift+a``) can never be saved.
"""
from __future__ import annotations

import sys

MODIFIER_ORDER = ("ctrl", "alt", "shift", "windows")
_ALIASES = {
    "control": "ctrl", "ctl": "ctrl", "option": "alt", "win": "windows", "super": "windows",
    "cmd": "windows", "command": "windows", "meta": "windows",
    "escape": "esc", "return": "enter", "del": "delete", "ins": "insert",
    "pgup": "page up", "pageup": "page up", "pgdn": "page down", "pagedown": "page down",
    "spacebar": "space",
}
FUNCTION_KEYS = frozenset(f"f{i}" for i in range(1, 25))
NAMED_KEYS = frozenset({"space", "enter", "tab", "esc", "backspace", "delete", "insert", "home",
                        "end", "page up", "page down", "up", "down", "left", "right"}) | FUNCTION_KEYS
_PRETTY = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "windows": "Win", "esc": "Esc",
           "page up": "PgUp", "page down": "PgDn", "backspace": "Backspace"}

# Tk keysym -> key name understood by the `keyboard` package.
_TK_KEYS = {
    "space": "space", "Return": "enter", "KP_Enter": "enter", "Tab": "tab", "ISO_Left_Tab": "tab",
    "Escape": "esc", "BackSpace": "backspace", "Delete": "delete", "Insert": "insert",
    "Home": "home", "End": "end", "Prior": "page up", "Next": "page down",
    "Up": "up", "Down": "down", "Left": "left", "Right": "right",
    "minus": "-", "equal": "=", "comma": ",", "period": ".", "slash": "/", "backslash": "\\",
    "semicolon": ";", "apostrophe": "'", "bracketleft": "[", "bracketright": "]", "grave": "`",
    # Shifted digit row (US layout) so Ctrl+Shift+1 can be recorded.
    "exclam": "1", "at": "2", "numbersign": "3", "dollar": "4", "percent": "5",
    "asciicircum": "6", "ampersand": "7", "asterisk": "8", "parenleft": "9", "parenright": "0",
}
_MODIFIER_KEYSYMS = frozenset({
    "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Meta_L", "Meta_R",
    "Super_L", "Super_R", "Caps_Lock", "Num_Lock", "Scroll_Lock", "ISO_Level3_Shift", "Win_L", "Win_R",
})


def _tokens(combo: str) -> list[str]:
    return [_ALIASES.get(t.strip().lower(), t.strip().lower()) for t in str(combo).split("+") if t.strip()]


def normalize(combo: str) -> str:
    """Return the canonical form (``ctrl+shift+s``) or raise ``ValueError`` with a
    message that is safe to show to the user."""
    toks = _tokens(combo)
    if not toks:
        raise ValueError("Press a key combination.")
    mods = {t for t in toks if t in MODIFIER_ORDER}
    keys = [t for t in toks if t not in MODIFIER_ORDER]
    if len(keys) != 1:
        raise ValueError("Use one main key with Ctrl, Alt or Win, for example Ctrl+Shift+S.")
    key = keys[0]
    if key not in NAMED_KEYS and not (len(key) == 1 and key.isprintable() and not key.isspace()):
        raise ValueError(f"\u201c{key}\u201d isn't a key SnapType can use in a shortcut.")
    if key not in FUNCTION_KEYS and not (mods & {"ctrl", "alt", "windows"}):
        raise ValueError("Include Ctrl, Alt or Win so the shortcut can't fire while you type normally.")
    return "+".join([m for m in MODIFIER_ORDER if m in mods] + [key])


def try_normalize(combo: str, default: str) -> str:
    try:
        return normalize(combo)
    except ValueError:
        return default


def pretty(combo: str) -> list[str]:
    """Display parts for keycap chips: ``ctrl+shift+s`` -> ``['Ctrl', 'Shift', 'S']``."""
    out = []
    for t in _tokens(combo):
        if t in _PRETTY:
            out.append(_PRETTY[t])
        elif len(t) == 1 or t in FUNCTION_KEYS:
            out.append(t.upper())
        else:
            out.append(t.capitalize())
    return out


def from_tk_event(keysym: str, state: int, platform: str | None = None) -> str | None:
    """Translate a Tk ``<KeyPress>`` into a combo string, or ``None`` while only
    modifier keys are held. The result still needs :func:`normalize`."""
    if keysym in _MODIFIER_KEYSYMS:
        return None
    platform = platform or sys.platform
    alt_mask = 0x20000 if platform == "win32" else 0x8
    mods = []
    if state & 0x4:
        mods.append("ctrl")
    if state & alt_mask:
        mods.append("alt")
    if state & 0x1:
        mods.append("shift")
    key = _TK_KEYS.get(keysym)
    if key is None:
        low = keysym.lower()
        if len(keysym) == 1:
            key = low
        elif low in FUNCTION_KEYS:
            key = low
        else:
            key = "unknown key"   # not a valid name, so normalize() rejects it
    return "+".join(mods + [key])
