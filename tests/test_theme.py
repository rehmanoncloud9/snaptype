"""Design-token checks: pure Python, no display needed."""
import pytest

from snapui import theme as T

TEXT_ON_SURFACE = [
    (T.TEXT, T.PANEL), (T.TEXT_DIM, T.PANEL), (T.TEXT_FAINT, T.PANEL), (T.TEXT_FAINT, T.VOID),
    (T.TEXT_FAINT, T.INPUT), (T.TEXT, T.INPUT), (T.TEXT, T.SURFACE), (T.TEXT_DIM, T.SURFACE),
    (T.ON_CYAN, T.CYAN), (T.CYAN, T.PANEL), (T.CYAN, T.VOID), (T.CYAN, T.CYAN_TINT), (T.TEXT, T.CYAN_TINT),
    (T.AMETHYST, T.PANEL), (T.ERROR, T.PANEL), (T.ERROR, T.ERROR_TINT), (T.AMBER, T.PANEL),
    (T.AMBER, T.AMBER_TINT), (T.TEXT, T.PANEL_HOVER), (T.TEXT_DIM, T.PANEL_HOVER),
]


@pytest.mark.parametrize("fg,bg", TEXT_ON_SURFACE)
def test_text_meets_wcag_aa(fg, bg):
    assert T.contrast(fg, bg) >= 4.5, f"{fg} on {bg} is {T.contrast(fg, bg):.2f}:1"


def test_every_colour_is_valid_for_tk():
    """Tk rejects 8-digit hex and rgba(); every token must be plain #rrggbb."""
    import re
    for name in dir(T):
        v = getattr(T, name)
        if name.isupper() and isinstance(v, str) and v.startswith("#"):
            assert re.fullmatch(r"#[0-9a-f]{6}", v), f"{name}={v}"


def test_blend_matches_css_rgba():
    assert T.blend("#ffffff", 0.0, "#102030") == "#102030"
    assert T.blend("#ffffff", 1.0, "#102030") == "#ffffff"
    assert T.blend("#ffffff", 0.5, "#000000") == "#808080"


def test_every_type_role_has_pixel_size_weight_kind():
    for role, (px, weight, kind) in T.TYPE.items():
        assert px >= 11 and weight in ("normal", "bold") and kind in ("ui", "mono"), role
