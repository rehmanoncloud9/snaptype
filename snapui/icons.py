"""Vector-style icons, the SnapType logo and the tray icons, drawn with Pillow.

Why not emoji or an icon font? Emoji render differently on every Windows build (and some
are several code points long), and a font would be one more file to ship. These are drawn
on a 24-unit grid at 8x supersampling, so they stay crisp at any DPI, and are tinted to
match the state they sit in. No Tk import here: build.py uses this module to make the .ico.
"""
from __future__ import annotations

import math
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from . import theme as T

SS = 8                                      # supersampling factor
_BOLT = ((0.62, 0.02), (0.24, 0.56), (0.46, 0.56), (0.38, 0.98), (0.78, 0.44), (0.54, 0.44))


def bolt_points(x0: float, y0: float, x1: float, y1: float):
    w, h = x1 - x0, y1 - y0
    return [(x0 + fx * w, y0 + fy * h) for fx, fy in _BOLT]


def _rgba(color: str, alpha: int = 255):
    h = color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha


class _Pen:
    """Draws in 24-unit icon space onto a supersampled transparent canvas."""

    def __init__(self, px: int, color: str, stroke: float):
        self.S = px * SS
        self.k = self.S / 24.0
        self.im = Image.new("RGBA", (self.S, self.S), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)
        self.col = _rgba(color)
        self.w = max(1, round(stroke * self.k))

    @staticmethod
    def _pairs(args):
        flat = []
        for a in args:
            flat.extend(a if isinstance(a, (tuple, list)) else [a])
        return list(zip(flat[0::2], flat[1::2], strict=False))

    def _p(self, pts):
        return [(x * self.k, y * self.k) for x, y in self._pairs(pts)]

    def _cap(self, x, y):
        r = self.w / 2
        self.d.ellipse([x - r, y - r, x + r, y + r], fill=self.col)

    def line(self, *pts):
        P = self._p(pts)
        self.d.line(P, fill=self.col, width=self.w, joint="curve")
        for x, y in P:
            self._cap(x, y)

    def poly(self, *pts, close=True):
        pr = self._pairs(pts)
        self.line(*(pr + ([pr[0]] if close else [])))

    def fill(self, *pts):
        self.d.polygon(self._p(pts), fill=self.col)

    def circle(self, cx, cy, r):
        k, h = self.k, self.w / 2
        self.d.ellipse([cx * k - r * k - h, cy * k - r * k - h, cx * k + r * k + h, cy * k + r * k + h],
                       outline=self.col, width=self.w)

    def ellipse(self, cx, cy, rx, ry):
        k, h = self.k, self.w / 2
        self.d.ellipse([cx * k - rx * k - h, cy * k - ry * k - h, cx * k + rx * k + h, cy * k + ry * k + h],
                       outline=self.col, width=self.w)

    def dot(self, cx, cy, r):
        k = self.k
        self.d.ellipse([(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k], fill=self.col)

    def rrect(self, x0, y0, x1, y1, r, fill=False):
        k, h = self.k, self.w / 2
        box = [x0 * k - (0 if fill else h), y0 * k - (0 if fill else h), x1 * k + (0 if fill else h),
               y1 * k + (0 if fill else h)]
        if fill:
            self.d.rounded_rectangle(box, radius=r * k, fill=self.col)
        else:
            self.d.rounded_rectangle(box, radius=r * k + h, outline=self.col, width=self.w)

    def arc(self, cx, cy, r, start, end):
        k, h = self.k, self.w / 2
        self.d.arc([cx * k - r * k - h, cy * k - r * k - h, cx * k + r * k + h, cy * k + r * k + h],
                   start, end, fill=self.col, width=self.w)
        for a in (start, end):
            self._cap((cx + r * math.cos(math.radians(a))) * k, (cy + r * math.sin(math.radians(a))) * k)

    def done(self, px):
        return self.im.resize((px, px), Image.LANCZOS)


def _gear(p: _Pen):
    pts = []
    for i in range(8):
        a = math.radians(i * 45)
        for da, r in ((-19, 6.9), (-11, 9.6), (11, 9.6), (19, 6.9)):
            t = a + math.radians(da)
            pts.append((12 + r * math.cos(t), 12 + r * math.sin(t)))
    p.poly(*pts)
    p.circle(12, 12, 3.2)


def _moon(p: _Pen):
    k = p.k
    p.d.ellipse([3 * k, 3 * k, 21 * k, 21 * k], fill=p.col)
    p.d.ellipse([8.6 * k, 0.4 * k, 25 * k, 16.8 * k], fill=(0, 0, 0, 0))


def _icon_bolt():
    return bolt_points(24 * BOLT_BOX[0] - 1.5, 24 * BOLT_BOX[1] - 1.2, 24 * BOLT_BOX[2] + 1.5, 24 * BOLT_BOX[3] + 1.2)


_ICONS = {
    "dashboard": lambda p: [p.rrect(x, y, x + 7, y + 7, 2) for x, y in ((3.5, 3.5), (13.5, 3.5), (3.5, 13.5), (13.5, 13.5))],
    "bolt": lambda p: p.poly(*_icon_bolt()),
    "bolt_fill": lambda p: (p.fill(*_icon_bolt()), p.poly(*_icon_bolt())),
    "chart": lambda p: (p.line(5.5, 20, 5.5, 13), p.line(12, 20, 12, 4.5), p.line(18.5, 20, 18.5, 9.5)),
    "shield": lambda p: (p.poly(12, 2.8, 20, 5.8, 20, 11.5, 19, 15, 12, 21.2, 5, 15, 4, 11.5, 4, 5.8),
                         p.poly(8.5, 12, 11, 14.5, 15.5, 9.5, close=False)),
    "gear": _gear,
    "info": lambda p: (p.circle(12, 12, 9), p.line(12, 11, 12, 16.5), p.dot(12, 7.8, 1.15)),
    "search": lambda p: (p.circle(10.5, 10.5, 6.5), p.line(15.5, 15.5, 20.5, 20.5)),
    "plus": lambda p: (p.line(12, 5, 12, 19), p.line(5, 12, 19, 12)),
    "minus": lambda p: p.line(5, 12, 19, 12),
    "trash": lambda p: (p.line(4, 6.5, 20, 6.5), p.poly(9, 6.5, 9, 3.5, 15, 3.5, 15, 6.5, close=False),
                        p.poly(6, 6.5, 7, 20.5, 17, 20.5, 18, 6.5, close=False),
                        p.line(10.2, 10.5, 10.2, 16.5), p.line(13.8, 10.5, 13.8, 16.5)),
    "upload": lambda p: (p.line(12, 15, 12, 4), p.poly(7.5, 8.5, 12, 4, 16.5, 8.5, close=False),
                         p.poly(4, 15, 4, 20, 20, 20, 20, 15, close=False)),
    "download": lambda p: (p.line(12, 4, 12, 15), p.poly(7.5, 10.5, 12, 15, 16.5, 10.5, close=False),
                           p.poly(4, 15, 4, 20, 20, 20, 20, 15, close=False)),
    "play": lambda p: (p.fill(7, 4.5, 19, 12, 7, 19.5), p.poly(7, 4.5, 19, 12, 7, 19.5)),
    "pause": lambda p: (p.rrect(6.5, 4.5, 10.5, 19.5, 1.4, fill=True), p.rrect(13.5, 4.5, 17.5, 19.5, 1.4, fill=True)),
    "moon": _moon,
    "check": lambda p: p.poly(5, 12.5, 10, 17.5, 19, 7, close=False),
    "x": lambda p: (p.line(6, 6, 18, 18), p.line(18, 6, 6, 18)),
    "chevron_left": lambda p: p.poly(14.5, 5.5, 8, 12, 14.5, 18.5, close=False),
    "chevron_right": lambda p: p.poly(9.5, 5.5, 16, 12, 9.5, 18.5, close=False),
    "chevron_down": lambda p: p.poly(5.5, 9.5, 12, 16, 18.5, 9.5, close=False),
    "chevron_up": lambda p: p.poly(5.5, 14.5, 12, 8, 18.5, 14.5, close=False),
    "edit": lambda p: (p.poly(4, 20, 4.8, 15.6, 15.6, 4.8, 19.2, 8.4, 8.4, 19.2), p.line(13, 7.5, 16.5, 11)),
    "folder": lambda p: p.poly(3, 6.5, 9.5, 6.5, 11.5, 9, 21, 9, 21, 19.5, 3, 19.5),
    "copy": lambda p: (p.rrect(9, 9, 20, 20, 2.2), p.poly(15, 4.5, 6.5, 4.5, 4.5, 6.5, 4.5, 15, close=False)),
    "external": lambda p: (p.poly(14, 4, 20, 4, 20, 10, close=False), p.line(20, 4, 11, 13),
                           p.poly(18, 14.5, 18, 20, 4, 20, 4, 6, 9.5, 6, close=False)),
    "keyboard": lambda p: (p.rrect(2.5, 6, 21.5, 18, 2.6), [p.dot(x, 10, 0.9) for x in (6.5, 10.2, 13.8, 17.5)],
                           p.line(7.5, 14.2, 16.5, 14.2)),
    "clock": lambda p: (p.circle(12, 12, 9), p.poly(12, 7, 12, 12, 15.5, 14, close=False)),
    "alert": lambda p: (p.poly(12, 3.5, 21.5, 20, 2.5, 20), p.line(12, 10, 12, 14.5), p.dot(12, 17.2, 1.1)),
    "globe": lambda p: (p.circle(12, 12, 9), p.ellipse(12, 12, 4, 9), p.line(3, 12, 21, 12)),
    "ban": lambda p: (p.circle(12, 12, 9), p.line(5.7, 5.7, 18.3, 18.3)),
    "check_circle": lambda p: (p.circle(12, 12, 9), p.poly(7.8, 12.4, 10.8, 15.4, 16.4, 9.2, close=False)),
    "power": lambda p: (p.arc(12, 13, 7.5, -50, 230), p.line(12, 3.5, 12, 11.5)),
    "lock": lambda p: (p.rrect(5, 11, 19, 21, 2.4), p.arc(12, 11, 4.2, 180, 360), p.dot(12, 16, 1.2)),
    "refresh": lambda p: (p.arc(12, 12, 8, 20, 320), p.poly(17.5, 2.8, 18.8, 7.8, 13.8, 8.6, close=False)),
    "sidebar": lambda p: (p.rrect(3, 4.5, 21, 19.5, 2.6), p.line(9.5, 4.5, 9.5, 19.5)),
}
ICON_NAMES = tuple(_ICONS)


@lru_cache(maxsize=512)
def icon_image(name: str, px: int, color: str, stroke: float = 2.0) -> Image.Image:
    """RGBA icon at ``px`` x ``px`` in ``color``."""
    px = max(8, int(px))
    pen = _Pen(px, color, stroke)
    _ICONS[name](pen)
    return pen.done(px)


# ── logo ───────────────────────────────────────────────────────────────────
# One brand mark, everywhere. The tile, the bolt box and the gradient recipe below are shared by
# the app icon, sidebar mark, About page, installer icon and the tray; only the palette changes
# with state, so the tray icon is literally the logo recoloured.
BOLT_BOX = (0.29, 0.14, 0.71, 0.88)        # fraction of the tile
PALETTES = {                                # bolt top, bolt bottom, glow colour (None = no glow), ring
    "on": ("#c9fcff", "#00cfdb", T.CYAN, T.CYAN),
    "snoozed": ("#f6e9ff", "#b27ae6", T.AMETHYST, T.AMETHYST),
    "off": ("#aeb9bb", "#5d6c6e", None, "#5d6c6e"),
}


def _vgrad(w: int, h: int, top: str, bottom: str) -> Image.Image:
    ramp = Image.linear_gradient("L").resize((w, h), Image.BILINEAR)
    return Image.composite(Image.new("RGBA", (w, h), _rgba(bottom)), Image.new("RGBA", (w, h), _rgba(top)), ramp)


def make_logo(size: int = 256, state: str = "on", tray: bool = False) -> Image.Image:
    """Obsidian tile, glowing bolt, hairline ring. ``tray=True`` thickens the ring and drops the
    soft glow so the mark survives at 16 px on any taskbar."""
    top, bottom, glow_col, ring_col = PALETTES.get(state, PALETTES["on"])
    s = size * 4
    pad, radius = int(s * 0.04), int(s * 0.23)
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([pad, pad, s - pad, s - pad], radius=radius, fill=255)
    img.paste(_vgrad(s, s, "#14232d", "#070d13"), (0, 0), mask)

    x0, y0, x1, y1 = BOLT_BOX
    bolt = bolt_points(s * x0, s * y0, s * x1, s * y1)
    if glow_col and not tray:
        glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(glow).polygon(bolt, fill=_rgba(glow_col, 190))
        glow = glow.filter(ImageFilter.GaussianBlur(s * 0.045))
        img = Image.alpha_composite(img, Image.composite(glow, Image.new("RGBA", (s, s), (0, 0, 0, 0)), mask))

    bmask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(bmask).polygon(bolt, fill=255)
    img.paste(_vgrad(s, s, top, bottom), (0, 0), bmask)

    ring = Image.new("L", (s, s), 0)
    ImageDraw.Draw(ring).rounded_rectangle([pad, pad, s - pad, s - pad], radius=radius, outline=255,
                                           width=max(2, s // (30 if tray else 90)))
    fade = Image.linear_gradient("L").rotate(180).resize((s, s))
    lo, gain = (170, 0.3) if tray else (40, 0.45)
    ring = ImageChops.multiply(ring, fade.point(lambda v: int(lo + v * gain)))
    img.paste(Image.new("RGBA", (s, s), _rgba(ring_col)), (0, 0), ring)
    return img.resize((size, size), Image.LANCZOS)


def make_tray_icon(state: str = "off") -> Image.Image:
    return make_logo(64, state, tray=True)
