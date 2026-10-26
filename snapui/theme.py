"""Design tokens for "Obsidian Cyber-Glass" (see DESIGN.md).

Tk cannot do backdrop blur, ``rgba()`` fills or 8-digit hex, so every translucent colour
from the design spec is pre-blended over the surface it sits on. Colours here are plain
``#rrggbb`` strings and importing this module never touches Tk, so contrast is unit-tested.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def blend(fg: str, alpha: float, bg: str) -> str:
    """``fg`` at ``alpha`` opacity composited over ``bg`` (what CSS rgba() would show)."""
    (r1, g1, b1), (r2, g2, b2) = _rgb(fg), _rgb(bg)
    mix = lambda a, b: round(a * alpha + b * (1 - alpha))  # noqa: E731
    return f"#{mix(r1, r2):02x}{mix(g1, g2):02x}{mix(b1, b2):02x}"


def _lin(c: int) -> float:
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(h: str) -> float:
    r, g, b = _rgb(h)
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio, 1.0 (none) to 21.0 (black on white)."""
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ── surfaces ────────────────────────────────────────────────────────────────
VOID = "#080f16"                          # window background (surface-lowest)
SURFACE = "#0e141b"                       # sidebar, header (surface)
WHITE = "#ffffff"
PANEL = blend(WHITE, 0.045, VOID)         # glass panel (spec 3%; nudged so it reads without blur)
PANEL_HOVER = blend(WHITE, 0.075, VOID)   # clay: active / hovered surface (spec 7%)
INPUT = "#060b10"                         # fields are darker than the page
BORDER = blend(WHITE, 0.08, VOID)         # hairline (spec 5%)
BORDER_STRONG = blend(WHITE, 0.16, VOID)
DIVIDER = blend(WHITE, 0.06, VOID)

# ── text ────────────────────────────────────────────────────────────────────
TEXT = "#dde3ed"                          # on-surface
TEXT_DIM = "#b9cacb"                      # on-surface-variant
TEXT_FAINT = "#8a9b9c"                    # outline, lightened a touch to stay AA on panels
TEXT_DISABLED = "#566566"

# ── accents ─────────────────────────────────────────────────────────────────
CYAN = "#00f1fd"                          # primary-container: actions, "online"
CYAN_DIM = "#00dce7"
CYAN_DEEP = "#006a6f"
ON_CYAN = "#00292c"                       # text on cyan
AMETHYST = "#deb7ff"                      # secondary: creative / snooze
PURPLE = "#a258e7"
ERROR = "#ffb4ab"
ERROR_DEEP = "#93000a"
AMBER = "#f5c26b"                         # warnings only; the spec has no warning hue

CYAN_TINT = blend(CYAN, 0.10, SURFACE)    # active nav background
CYAN_TINT_PANEL = blend(CYAN, 0.10, PANEL)
ERROR_TINT = blend(ERROR_DEEP, 0.45, PANEL)
AMBER_TINT = blend(AMBER, 0.12, PANEL)
PURPLE_TINT = blend(AMETHYST, 0.12, PANEL)

# ── shape & rhythm (px at 96 dpi; always pass through dp()) ─────────────────
R_SM, R_MD, R_LG = 8, 12, 16
SP_XS, SP_SM, SP_MD, SP_LG, SP_XL = 4, 8, 16, 24, 48
GUTTER = 20
SIDEBAR_WIDE, SIDEBAR_NARROW = 256, 80
COMPACT_BELOW = 1080                      # window width that auto-collapses the sidebar

# Type scale (px, weight, family kind). Tk has no letter-spacing, so micro-labels rely on caps + mono.
TYPE = {
    "display": (40, "bold", "ui"),
    "title": (24, "bold", "ui"),
    "heading": (16, "bold", "ui"),
    "body": (14, "normal", "ui"),
    "body_b": (14, "bold", "ui"),
    "small": (12, "normal", "ui"),
    "small_b": (12, "bold", "ui"),
    "label": (11, "bold", "mono"),
    "mono": (13, "normal", "mono"),
    "mono_s": (12, "normal", "mono"),
    "mono_b": (13, "bold", "mono"),
}

UI_FAMILIES = ("Inter", "Segoe UI Variable Text", "Segoe UI Variable Display", "Segoe UI",
               "SF Pro Text", "Helvetica Neue", "DejaVu Sans", "Arial")
MONO_FAMILIES = ("Geist Mono", "Cascadia Mono", "Cascadia Code", "Consolas", "SF Mono", "Menlo",
                 "DejaVu Sans Mono", "Courier New")
_SEMIBOLD = {"Inter": "Inter SemiBold", "Segoe UI": "Segoe UI Semibold",
             "Segoe UI Variable Text": "Segoe UI Semibold", "Segoe UI Variable Display": "Segoe UI Semibold"}

# ── runtime (needs a Tk root: call init() once) ─────────────────────────────
_reset_hooks: list = []          # called by init(): caches of Tk objects must not outlive their root
_state = {"scale": 1.0, "ui": "TkDefaultFont", "mono": "TkFixedFont", "semibold": None, "fonts": {}}


def dp(px: float) -> int:
    """Scale a 96-dpi pixel value to this display (Tk pixel sizes do not scale on their own)."""
    return max(1, round(px * _state["scale"])) if px else 0


def scale() -> float:
    return _state["scale"]


def _font_dirs() -> list[Path]:
    here = Path(__file__).resolve().parent / "assets" / "fonts"
    bundled = Path(getattr(sys, "_MEIPASS", "")) / "snapui" / "assets" / "fonts" if getattr(sys, "frozen", False) else None
    return [d for d in (bundled, here) if d and d.is_dir()]


def load_private_fonts() -> int:
    """Register any .ttf/.otf in assets/fonts for this process only (Windows). Drop Inter and
    Geist Mono in there (both SIL OFL) and the design renders exactly as specified."""
    if sys.platform != "win32":
        return 0
    n = 0
    try:
        import ctypes
        add = ctypes.windll.gdi32.AddFontResourceExW
        add.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
        for d in _font_dirs():
            for f in list(d.glob("*.ttf")) + list(d.glob("*.otf")):
                n += 1 if add(str(f), 0x10, None) else 0     # FR_PRIVATE
    except (OSError, AttributeError):
        return n
    return n


def init(root) -> None:
    """Measure DPI and resolve fonts. Call once, right after creating the Tk root."""
    import tkinter.font as tkfont
    try:
        _state["scale"] = min(max(root.winfo_fpixels("1i") / 96.0, 0.75), 3.0)
    except Exception:  # noqa: BLE001  (a misreporting display must not stop the app)
        _state["scale"] = 1.0
    load_private_fonts()
    fams = set(tkfont.families(root))
    _state["ui"] = next((f for f in UI_FAMILIES if f in fams), "TkDefaultFont")
    _state["mono"] = next((f for f in MONO_FAMILIES if f in fams), "TkFixedFont")
    semi = _SEMIBOLD.get(_state["ui"])
    _state["semibold"] = semi if semi in fams else None
    _state["fonts"] = {}
    for hook in _reset_hooks:
        hook()


def font(role: str):
    """Cached ``tkinter.font.Font`` for a type role, sized in device pixels."""
    cache = _state["fonts"]
    if role not in cache:
        import tkinter.font as tkfont
        px, weight, kind = TYPE[role]
        family = _state["mono"] if kind == "mono" else _state["ui"]
        if weight == "bold" and kind == "ui" and _state["semibold"]:
            family, weight = _state["semibold"], "normal"      # 600 reads calmer than 700
        cache[role] = tkfont.Font(family=family, size=-dp(px), weight=weight)
    return cache[role]


def ui_family() -> str:
    return _state["ui"]
