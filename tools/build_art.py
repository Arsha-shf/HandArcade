"""
tools/build_art.py

Draws every HandArcade sprite as vector art (SVG), renders it to a transparent
PNG, trims it and fits it into a square canvas, and writes it into assets/.
Also writes the editable .svg sources to art/svg/ and a preview sheet to
art/preview.png.

    pip install cairosvg          # (in requirements-dev.txt)
    python tools/build_art.py

Want a different color or shape? Edit the function for that sprite below and
re-run. You can also open art/svg/*.svg in Inkscape or Figma and re-export,
as long as you keep the same filename and a square-ish transparent PNG.

Never touches baste.png / baz.png (those are hand-drawn, not generated).

Sprite conventions (the games rely on these):
  - Every sprite is SIZE x SIZE px with the artwork trimmed and centered, so
    the game's hit radius (half the canvas) matches what you see.
  - Sprites are authored at 2x the size they appear at 720p, so they stay
    sharp at 1080p.
"""

import math
import random
import sys
from pathlib import Path

import cairosvg
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SVG_DIR = ROOT / "art" / "svg"
PREVIEW = ROOT / "art" / "preview.png"

SIZE = 192          # final sprite canvas (px)
MARGIN = 3          # empty border inside the canvas
SUPERSAMPLE = 768   # render size before downscaling (anti-aliasing quality)
ALPHA_TRIM = 40     # pixels fainter than this don't count when trimming

# ---------------------------------------------------------------------------
# SVG helpers
# ---------------------------------------------------------------------------


def svg(defs, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
            f"<defs>{defs}</defs>{body}</svg>")


def _stops(items):
    out = []
    for item in items:
        offset, color, *rest = item
        opacity = f' stop-opacity="{rest[0]}"' if rest else ""
        out.append(f'<stop offset="{offset}" stop-color="{color}"{opacity}/>')
    return "".join(out)


def rg(gid, items, cx=0.5, cy=0.5, r=0.5):
    return f'<radialGradient id="{gid}" cx="{cx}" cy="{cy}" r="{r}">{_stops(items)}</radialGradient>'


def lg(gid, items, x1=0, y1=0, x2=0, y2=1):
    return f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{_stops(items)}</linearGradient>'


def polar(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def star_points(cx, cy, r_out, r_in, n, rot=-90):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        pts.append(polar(cx, cy, r, rot + i * 180 / n))
    return pts


def poly(points, **attrs):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    extra = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<polygon points="{pts}" {extra}/>'


def smooth_path(points):
    """Closed smooth curve through the points (Catmull-Rom -> Bezier)."""
    n = len(points)
    d = f"M{points[0][0]:.1f} {points[0][1]:.1f} "
    for i in range(n):
        p0, p1, p2, p3 = points[(i - 1) % n], points[i], points[(i + 1) % n], points[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f} "
    return d + "Z"


def lumpy_rock(cx, cy, radius, lumps, seed, low=0.82):
    rnd = random.Random(seed)
    return [polar(cx, cy, radius * rnd.uniform(low, 1.0), i * 360 / lumps) for i in range(lumps)]


def wedges(cx, cy, r0, r1, n, fill_a, fill_b, gap_deg=3.0):
    """Pie-slice segments of a citrus fruit."""
    out = []
    for i in range(n):
        a0 = i * 360 / n + gap_deg / 2 - 90
        a1 = (i + 1) * 360 / n - gap_deg / 2 - 90
        x0, y0 = polar(cx, cy, r0, a0)
        x1, y1 = polar(cx, cy, r1, a0)
        x2, y2 = polar(cx, cy, r1, a1)
        x3, y3 = polar(cx, cy, r0, a1)
        d = (f"M{x0:.1f} {y0:.1f} L{x1:.1f} {y1:.1f} A{r1} {r1} 0 0 1 {x2:.1f} {y2:.1f} "
             f"L{x3:.1f} {y3:.1f} A{r0} {r0} 0 0 0 {x0:.1f} {y0:.1f}Z")
        fill = fill_a if i % 2 == 0 else fill_b
        out.append(f'<path d="{d}" fill="{fill}" stroke="{fill}" stroke-width="4" stroke-linejoin="round"/>')
    return "".join(out)


def dimples(cx, cy, radius, count, color, opacity, rx=1.7, ry=1.2):
    out = []
    for i in range(count):
        r = radius * math.sqrt((i + 0.5) / count)
        a = i * 2.39996
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        out.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx}" ry="{ry}" fill="{color}" opacity="{opacity}"/>')
    return "".join(out)


def highlight(cx, cy, rx, ry, rot, opacity=0.5):
    return (f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#fff" opacity="{opacity}" '
            f'transform="rotate({rot} {cx} {cy})"/>')


def leaf(d, vein, fill_id="leafg"):
    return (f'<path d="{d}" fill="url(#{fill_id})" stroke="#1e5a14" stroke-width="3.5" stroke-linejoin="round"/>'
            f'<path d="{vein}" stroke="#1e5a14" stroke-width="2.5" fill="none" opacity=".55" stroke-linecap="round"/>')


LEAF_GRADIENT = lg("leafg", [(0, "#9be04a"), (1, "#3a9a22")], 0, 0, 1, 1)

# ---------------------------------------------------------------------------
# Fruit (whole)
# ---------------------------------------------------------------------------

APPLE_BODY = ("M100 58 C82 40 36 46 34 96 C33 138 64 172 84 170 C92 169 95 166 100 166 "
              "C105 166 108 169 116 170 C136 172 167 138 166 96 C164 46 118 40 100 58Z")


def apple():
    defs = rg("ap", [(0, "#ff7a6b"), (0.45, "#e3242d"), (1, "#9c0f1c")], 0.35, 0.3, 0.85) + LEAF_GRADIENT
    body = (f'<path d="{APPLE_BODY}" fill="url(#ap)" stroke="#5e0a12" stroke-width="5" stroke-linejoin="round"/>'
            + highlight(66, 90, 10, 22, -18, 0.5) + highlight(62, 64, 4, 6, -20, 0.7)
            + '<path d="M100 60 C99 46 103 34 112 24" stroke="#5b3a1e" stroke-width="8" fill="none" stroke-linecap="round"/>'
            + leaf("M108 38 C116 16 146 12 158 22 C150 44 124 52 108 38Z", "M112 38 C126 30 140 26 152 24"))
    return svg(defs, body)


def orange():
    defs = rg("or", [(0, "#ffc15a"), (0.5, "#ff8c10"), (1, "#d4590a")], 0.35, 0.3, 0.85) + LEAF_GRADIENT
    body = ('<circle cx="100" cy="106" r="72" fill="url(#or)" stroke="#9a4205" stroke-width="5"/>'
            + dimples(100, 106, 62, 46, "#b8480a", 0.45)
            + highlight(72, 80, 17, 9, -35, 0.45)
            + '<ellipse cx="100" cy="36" rx="9" ry="4.5" fill="#6b7a1f" stroke="#3f4a10" stroke-width="2"/>'
            + leaf("M104 34 C112 14 140 12 150 24 C142 42 118 46 104 34Z", "M108 34 C122 28 136 24 146 24"))
    return svg(defs, body)


def watermelon():
    defs = (rg("wm", [(0, "#a9ec7c"), (0.6, "#5cbf3f"), (1, "#3a9a2c")], 0.38, 0.3, 0.85)
            + '<clipPath id="wmc"><ellipse cx="100" cy="104" rx="84" ry="66"/></clipPath>')
    stripes = "".join(
        f'<path d="M{100 + k * 21} 20 C{114 + k * 21} 70 {86 + k * 21} 140 {100 + k * 21} 190" '
        f'stroke="#247a2b" stroke-width="11" fill="none" opacity=".85"/>' for k in range(-4, 5))
    body = ('<ellipse cx="100" cy="104" rx="84" ry="66" fill="url(#wm)"/>'
            f'<g clip-path="url(#wmc)">{stripes}</g>'
            '<ellipse cx="100" cy="104" rx="84" ry="66" fill="none" stroke="#1b5a22" stroke-width="5"/>'
            + highlight(62, 76, 22, 8, -25, 0.4)
            + '<path d="M97 40 C97 30 101 26 108 24" stroke="#5b3a1e" stroke-width="7" fill="none" stroke-linecap="round"/>')
    return svg(defs, body)


def lemon():
    defs = rg("lm", [(0, "#fff8a0"), (0.5, "#ffe033"), (1, "#e6ac00")], 0.4, 0.3, 0.85)
    shape = ("M24 100 C24 92 30 88 38 84 C50 62 78 48 100 48 C122 48 150 62 162 84 C170 88 176 92 176 100 "
             "C176 108 170 112 162 116 C150 138 122 152 100 152 C78 152 50 138 38 116 C30 112 24 108 24 100Z")
    body = (f'<g transform="rotate(-20 100 100)"><path d="{shape}" fill="url(#lm)" stroke="#a87a00" '
            f'stroke-width="5" stroke-linejoin="round"/>'
            + dimples(100, 100, 52, 28, "#c89200", 0.4)
            + highlight(82, 78, 20, 8, -12, 0.5) + "</g>")
    return svg(defs, body)


STRAWBERRY_BODY = ("M100 176 C58 152 32 114 42 82 C50 56 84 52 100 64 C116 52 150 56 158 82 "
                   "C168 114 142 152 100 176Z")
SEED_ROWS = [(84, [74, 100, 126]), (102, [58, 86, 114, 142]), (122, [66, 92, 118, 144]),
             (142, [76, 100, 124]), (160, [100])]


def _calyx():
    leaves = "".join(
        f'<ellipse cx="100" cy="50" rx="7.5" ry="19" fill="#4fb83a" stroke="#1f6a14" stroke-width="2.5" '
        f'transform="rotate({a} 100 66)"/>' for a in (-72, -36, 0, 36, 72))
    return leaves + '<path d="M100 44 L100 22" stroke="#3f8a2a" stroke-width="6" stroke-linecap="round"/>'


def strawberry():
    defs = rg("sb", [(0, "#ff6b73"), (0.55, "#e22b3f"), (1, "#a3122a")], 0.35, 0.3, 0.9)
    seeds = "".join(
        f'<ellipse cx="{x}" cy="{y}" rx="3" ry="4.6" fill="#ffe9a3" stroke="#b88a2a" stroke-width="1"/>'
        for y, xs in SEED_ROWS for x in xs)
    body = (f'<path d="{STRAWBERRY_BODY}" fill="url(#sb)" stroke="#6b0c1c" stroke-width="5" stroke-linejoin="round"/>'
            + seeds + highlight(70, 92, 8, 16, -20, 0.45) + _calyx())
    return svg(defs, body)


def kiwi():
    rnd = random.Random(7)
    fuzz = []
    for _ in range(70):
        a, r = rnd.uniform(0, 6.28), math.sqrt(rnd.random())
        x, y = 100 + 66 * r * math.cos(a), 104 + 54 * r * math.sin(a)
        da = rnd.uniform(0, 6.28)
        fuzz.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + 5 * math.cos(da):.1f}" y2="{y + 5 * math.sin(da):.1f}" '
                    f'stroke="#5c3b1a" stroke-width="1.8" opacity=".5" stroke-linecap="round"/>')
    defs = rg("kw", [(0, "#c8925a"), (0.6, "#9a6a38"), (1, "#6e4a24")], 0.35, 0.3, 0.85)
    body = ('<ellipse cx="100" cy="104" rx="74" ry="62" fill="url(#kw)" stroke="#4a2f14" stroke-width="5"/>'
            + "".join(fuzz) + highlight(68, 76, 20, 9, -30, 0.35)
            + '<path d="M96 44 C96 36 100 32 106 30" stroke="#4a2f14" stroke-width="6" fill="none" stroke-linecap="round"/>')
    return svg(defs, body)


def bomb():
    defs = (rg("bb", [(0, "#6b6b7a"), (0.45, "#262630"), (1, "#08080c")], 0.33, 0.28, 0.8)
            + lg("cap", [(0, "#9a9aa8"), (0.5, "#5c5c6a"), (1, "#34343e")], 0, 0, 0, 1))
    spark = (poly(star_points(128, 14, 18, 8, 8, -90), fill="#ff7a00", stroke="#b84a00", stroke_width="2", stroke_linejoin="round")
             + poly(star_points(128, 14, 11, 5, 8, -67), fill="#ffd400")
             + '<circle cx="128" cy="14" r="4" fill="#fff"/>')
    skull = ('<g opacity=".93" fill="#e8e8ee">'
             '<circle cx="100" cy="120" r="17"/><rect x="91" y="128" width="18" height="15" rx="4"/></g>'
             '<ellipse cx="93" cy="119" rx="4.5" ry="5.5" fill="#14141a"/><ellipse cx="107" cy="119" rx="4.5" ry="5.5" fill="#14141a"/>'
             '<path d="M100 124 L97.5 129 L102.5 129Z" fill="#14141a"/>'
             '<path d="M95.5 134 V142 M100 134 V142 M104.5 134 V142" stroke="#14141a" stroke-width="1.6"/>')
    body = ('<g transform="translate(0 12)">'
            '<circle cx="100" cy="118" r="66" fill="url(#bb)" stroke="#000" stroke-width="5"/>'
            + highlight(74, 96, 14, 22, -30, 0.28) + highlight(68, 84, 5, 8, -30, 0.6)
            + skull
            + '<rect x="74" y="58" width="52" height="13" rx="5" fill="url(#cap)" stroke="#14141a" stroke-width="4"/>'
            + '<rect x="78" y="40" width="44" height="24" rx="7" fill="url(#cap)" stroke="#14141a" stroke-width="4"/>'
            + '<path d="M100 40 C100 26 112 20 124 16" stroke="#d9b36a" stroke-width="6" fill="none" stroke-linecap="round"/>'
            + '<path d="M100 40 C100 26 112 20 124 16" stroke="#8a6a30" stroke-width="2" fill="none" stroke-dasharray="4 4"/>'
            + spark + "</g>")
    return svg(defs, body)

# ---------------------------------------------------------------------------
# Fruit (cut halves: drawn twice by the game, flying apart)
# ---------------------------------------------------------------------------


def _flesh_scaled(path, cx, cy, scale, fill, stroke):
    return (f'<g transform="translate({cx} {cy}) scale({scale}) translate({-cx} {-cy})">'
            f'<path d="{path}" fill="{fill}" stroke="{stroke}" stroke-width="2.4" stroke-linejoin="round"/></g>')


def apple_half():
    defs = (rg("ap", [(0, "#ff7a6b"), (0.45, "#e3242d"), (1, "#9c0f1c")], 0.35, 0.3, 0.85)
            + rg("fl", [(0, "#fffbe6"), (0.7, "#f7e8b0"), (1, "#e8cf86")], 0.45, 0.4, 0.8))
    body = (f'<path d="{APPLE_BODY}" fill="url(#ap)" stroke="#5e0a12" stroke-width="5" stroke-linejoin="round"/>'
            + _flesh_scaled(APPLE_BODY, 100, 112, 0.86, "url(#fl)", "#e9d28c")
            + '<ellipse cx="100" cy="118" rx="19" ry="27" fill="#f2dc9a" stroke="#d9bf72" stroke-width="2"/>'
            + '<ellipse cx="91" cy="118" rx="4" ry="7" fill="#5b2d12" transform="rotate(14 91 118)"/>'
            + '<ellipse cx="109" cy="118" rx="4" ry="7" fill="#5b2d12" transform="rotate(-14 109 118)"/>'
            + '<path d="M100 66 L100 82" stroke="#7a4a1f" stroke-width="3" stroke-linecap="round"/>'
            + highlight(72, 94, 9, 18, -18, 0.45))
    return svg(defs, body)


def _citrus_half(rind, rind_stroke, pith, flesh_a, flesh_b, wedge_a, wedge_b, n):
    defs = rg("cf", [(0, flesh_a), (1, flesh_b)], 0.5, 0.5, 0.6)
    body = (f'<circle cx="100" cy="100" r="74" fill="{rind}" stroke="{rind_stroke}" stroke-width="5"/>'
            f'<circle cx="100" cy="100" r="64" fill="{pith}"/>'
            f'<circle cx="100" cy="100" r="57" fill="url(#cf)"/>'
            + wedges(100, 100, 10, 54, n, wedge_a, wedge_b)
            + f'<circle cx="100" cy="100" r="8" fill="{pith}"/>'
            + '<ellipse cx="78" cy="76" rx="5" ry="2.5" fill="#fff" opacity=".6" transform="rotate(-35 78 76)"/>'
            + '<ellipse cx="124" cy="120" rx="4" ry="2" fill="#fff" opacity=".5" transform="rotate(-35 124 120)"/>')
    return svg(defs, body)


def orange_half():
    return _citrus_half("#ff8c10", "#9a4205", "#fff0cc", "#ffd27a", "#ffb02e", "#ffc247", "#ffb42f", 10)


def lemon_half():
    return _citrus_half("#ffd21a", "#a87a00", "#fffbd0", "#fff59a", "#ffe85a", "#fff176", "#ffe94a", 9)


def watermelon_half():
    def half(r):
        return f"M{100 - r} 78 A{r} {r} 0 0 0 {100 + r} 78Z"
    defs = rg("fm", [(0, "#ff7b8a"), (0.6, "#ff3f58"), (1, "#e02045")], 0.5, 0.25, 0.9)
    seeds = "".join(
        f'<ellipse cx="{x}" cy="{y}" rx="3.6" ry="6" fill="#1a1a1a" transform="rotate({r} {x} {y})"/>'
        for x, y, r in ((68, 98, 20), (100, 112, 0), (132, 98, -20), (84, 132, 12), (116, 132, -12),
                        (52, 84, 28), (148, 84, -28), (100, 90, 0)))
    body = (f'<path d="{half(84)}" fill="#2f9a3a" stroke="#14501c" stroke-width="5" stroke-linejoin="round"/>'
            f'<path d="{half(76)}" fill="#c9eea4"/>'
            f'<path d="{half(71)}" fill="#f6fff0"/>'
            f'<path d="{half(63)}" fill="url(#fm)"/>' + seeds
            + '<path d="M44 84 Q60 120 84 150" stroke="#fff" stroke-width="3" fill="none" opacity=".25" stroke-linecap="round"/>')
    return svg(defs, body)


def strawberry_half():
    defs = (rg("sb", [(0, "#ff6b73"), (0.55, "#e22b3f"), (1, "#a3122a")], 0.35, 0.3, 0.9)
            + rg("sf", [(0, "#fff0f0"), (0.5, "#ffb3bb"), (1, "#ff7c8c")], 0.5, 0.4, 0.7))
    veins = "".join(
        f'<line x1="100" y1="106" x2="{polar(100, 106, 50, a)[0]:.1f}" y2="{polar(100, 112, 50, a)[1]:.1f}" '
        f'stroke="#ff9aa6" stroke-width="2" opacity=".6" stroke-linecap="round"/>' for a in range(-150, 31, 36))
    body = (f'<path d="{STRAWBERRY_BODY}" fill="url(#sb)" stroke="#6b0c1c" stroke-width="5" stroke-linejoin="round"/>'
            + _flesh_scaled(STRAWBERRY_BODY, 100, 112, 0.84, "url(#sf)", "#ffd0d4") + veins
            + '<path d="M100 78 C113 94 115 118 100 140 C85 118 87 94 100 78Z" fill="#fff7f7" stroke="#ffd0d4" stroke-width="2"/>'
            + _calyx())
    return svg(defs, body)


def kiwi_half():
    defs = rg("kg", [(0, "#d4ec6a"), (0.5, "#8cc63f"), (1, "#5aa02c")], 0.5, 0.5, 0.65)
    rays = "".join(
        f'<line x1="{polar(100, 104, 20, a)[0]:.1f}" y1="{polar(100, 104, 17, a)[1]:.1f}" '
        f'x2="{polar(100, 104, 52, a)[0]:.1f}" y2="{polar(100, 104, 43, a)[1]:.1f}" '
        f'stroke="#c8e68a" stroke-width="2" opacity=".7" stroke-linecap="round"/>' for a in range(0, 360, 20))
    seeds = "".join(
        f'<ellipse cx="{polar(100, 104, 30, a)[0]:.1f}" cy="{polar(100, 104, 24, a)[1]:.1f}" rx="2.3" ry="4.2" '
        f'fill="#151515" transform="rotate({a + 90} {polar(100, 104, 30, a)[0]:.1f} {polar(100, 104, 24, a)[1]:.1f})"/>'
        for a in range(0, 360, 24))
    body = ('<ellipse cx="100" cy="104" rx="74" ry="62" fill="#9a6a38" stroke="#4a2f14" stroke-width="5"/>'
            '<ellipse cx="100" cy="104" rx="67" ry="55" fill="url(#kg)"/>'
            + rays + '<ellipse cx="100" cy="104" rx="17" ry="14" fill="#f5f9d6"/>' + seeds)
    return svg(defs, body)

# ---------------------------------------------------------------------------
# Catch items
# ---------------------------------------------------------------------------


def star():
    defs = lg("st", [(0, "#fff59a"), (0.5, "#ffd21a"), (1, "#ff9a00")], 0, 0, 1, 1)
    outer = star_points(100, 106, 84, 40, 5)
    inner = star_points(100, 106, 50, 24, 5)
    body = (poly(outer, fill="url(#st)", stroke="#a85d00", stroke_width="6", stroke_linejoin="round")
            + poly(inner, fill="#fff3a0", opacity=".45")
            + '<path d="M72 62 L74 52 L76 62 L86 64 L76 66 L74 76 L72 66 L62 64Z" fill="#fff" opacity=".9"/>')
    return svg(defs, body)


def gem():
    outline = "M60 56 L140 56 L172 92 L100 178 L28 92Z"
    facets = [
        ([(60, 56), (140, 56), (122, 92), (78, 92)], "#e8fbff"),
        ([(60, 56), (78, 92), (28, 92)], "#7fd8f5"),
        ([(140, 56), (172, 92), (122, 92)], "#4cb8ec"),
        ([(78, 92), (122, 92), (100, 178)], "#8fdcf8"),
        ([(28, 92), (78, 92), (100, 178)], "#3a9ad8"),
        ([(122, 92), (172, 92), (100, 178)], "#2a78c0"),
    ]
    body = "".join(poly(p, fill=c, stroke="#0f4c7a", stroke_width="3", stroke_linejoin="round") for p, c in facets)
    body += (f'<path d="{outline}" fill="none" stroke="#0f4c7a" stroke-width="5" stroke-linejoin="round"/>'
             '<path d="M52 44 L55 34 L58 44 L68 47 L58 50 L55 60 L52 50 L42 47Z" fill="#fff" opacity=".95"/>'
             '<path d="M150 70 L152 63 L154 70 L161 72 L154 74 L152 81 L150 74 L143 72Z" fill="#fff" opacity=".8"/>')
    return svg("", body)

# ---------------------------------------------------------------------------
# Dodge obstacles
# ---------------------------------------------------------------------------


def asteroid():
    defs = rg("as", [(0, "#b9afa3"), (0.5, "#7d7468"), (1, "#4a443d")], 0.35, 0.3, 0.85)
    path = smooth_path(lumpy_rock(100, 100, 80, 13, seed=11))
    craters = "".join(
        f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="#5b544b" stroke="#3a352f" stroke-width="2.5"/>'
        f'<path d="M{x - rx + 3} {y + ry * 0.55} Q{x} {y + ry + 3} {x + rx - 3} {y + ry * 0.55}" stroke="#a79d90" '
        f'stroke-width="2" fill="none" opacity=".7" stroke-linecap="round"/>'
        for x, y, rx, ry in ((74, 84, 16, 12), (122, 120, 20, 14), (112, 70, 9, 7), (80, 128, 10, 8)))
    body = (f'<path d="{path}" fill="url(#as)" stroke="#26221e" stroke-width="5" stroke-linejoin="round"/>'
            + craters + highlight(66, 66, 16, 8, -35, 0.3))
    return svg(defs, body)


def meteor():
    defs = (rg("mg", [(0.6, "#ff7a00", 0.0), (0.8, "#ff7a00", 0.45), (1, "#ff3a00", 0.0)], 0.5, 0.5, 0.5)
            + rg("mr", [(0, "#7a4230"), (0.6, "#3b2018"), (1, "#1c0f0b")], 0.35, 0.3, 0.85))
    path = smooth_path(lumpy_rock(100, 100, 74, 12, seed=5))
    cracks = ["M66 72 L82 86 L78 104 L96 114", "M136 78 L122 96 L132 114 L118 130", "M80 134 L98 124 L100 146"]
    glow = "".join(f'<path d="{c}" stroke="#ff5a00" stroke-width="9" fill="none" opacity=".4" stroke-linecap="round" '
                   f'stroke-linejoin="round"/>' for c in cracks)
    lava = "".join(f'<path d="{c}" stroke="#ffb02e" stroke-width="4" fill="none" stroke-linecap="round" '
                   f'stroke-linejoin="round"/>' for c in cracks)
    body = ('<circle cx="100" cy="100" r="98" fill="url(#mg)"/>'
            f'<path d="{path}" fill="url(#mr)" stroke="#2a120a" stroke-width="5" stroke-linejoin="round"/>'
            f'<path d="{path}" fill="none" stroke="#ff6a00" stroke-width="2.5" opacity=".7" stroke-linejoin="round"/>'
            + glow + lava + highlight(70, 66, 15, 7, -35, 0.2))
    return svg(defs, body)


def crystal():
    parts = []
    # long and short shards alternate all the way round; drawn short-first so the
    # long ones sit on top
    shards = [(a, 62, 24) for a in range(22, 360, 90)] + [(a, 84, 30) for a in range(0, 360, 90)]
    for angle, length, width in shards:
        w = width / 2
        tip = (0, -length)
        shoulder = -length * 0.55
        left = [tip, (-w, shoulder), (-w, 0), (0, 0)]
        right = [tip, (w, shoulder), (w, 0), (0, 0)]
        parts.append(
            f'<g transform="translate(100 100) rotate({angle})">'
            + poly(left, fill="#d9a6ff", stroke="#3a1480", stroke_width="4", stroke_linejoin="round")
            + poly(right, fill="#8a43e0", stroke="#3a1480", stroke_width="4", stroke_linejoin="round")
            + poly([tip, (-w * 0.3, shoulder * 0.9), (-w * 0.3, shoulder * 0.45)], fill="#fff", opacity=".35")
            + "</g>")
    parts.append('<circle cx="100" cy="100" r="17" fill="#6a2cc2" stroke="#3a1480" stroke-width="4"/>'
                 '<circle cx="94" cy="94" r="5" fill="#fff" opacity=".45"/>')
    return svg("", "".join(parts))


def mine():
    defs = (rg("mb", [(0, "#8a8a98"), (0.5, "#3b3b46"), (1, "#14141a")], 0.35, 0.3, 0.85)
            + lg("sp", [(0, "#9a9aa8"), (1, "#4a4a56")], 0, 0, 1, 0)
            + rg("ml", [(0, "#fff0a0"), (0.4, "#ff4a3a"), (1, "#b00f12")], 0.5, 0.5, 0.5))
    spikes, tips = [], []
    for k in range(10):
        a = k * 36 - 90
        b1, b2, tip = polar(100, 100, 40, a - 11), polar(100, 100, 40, a + 11), polar(100, 100, 80, a)
        spikes.append(poly([b1, tip, b2], fill="url(#sp)", stroke="#0a0a0e", stroke_width="3.5", stroke_linejoin="round"))
        tips.append(f'<circle cx="{tip[0]:.1f}" cy="{tip[1]:.1f}" r="6.5" fill="#ff3b30" stroke="#7a0f0a" stroke-width="2.5"/>')
    rivets = "".join(
        f'<circle cx="{polar(100, 100, 32, k * 45)[0]:.1f}" cy="{polar(100, 100, 32, k * 45)[1]:.1f}" r="2.6" fill="#5a5a66"/>'
        for k in range(8))
    body = ("".join(spikes)
            + '<circle cx="100" cy="100" r="46" fill="url(#mb)" stroke="#0a0a0e" stroke-width="5"/>'
            + rivets + highlight(80, 78, 13, 7, -35, 0.3)
            + '<circle cx="100" cy="100" r="15" fill="url(#ml)" stroke="#4a0608" stroke-width="3"/>'
            + "".join(tips))
    return svg(defs, body)


# ---------------------------------------------------------------------------
# What gets built, and where it goes (relative to assets/)
# ---------------------------------------------------------------------------

SPRITES = {
    # Fruit Slice: whole fruit + cut halves
    "apple.png": apple, "apple_half.png": apple_half,
    "orange.png": orange, "orange_half.png": orange_half,
    "watermelon.png": watermelon, "watermelon_half.png": watermelon_half,
    "lemon.png": lemon, "lemon_half.png": lemon_half,
    "strawberry.png": strawberry, "strawberry_half.png": strawberry_half,
    "kiwi.png": kiwi, "kiwi_half.png": kiwi_half,
    "bomb.png": bomb,
    # Catch (also reuses apple.png and bomb.png)
    "star.png": star, "gem.png": gem,
    # Dodge
    "dodge/asteroid.png": asteroid, "dodge/meteor.png": meteor,
    "dodge/crystal.png": crystal, "dodge/mine.png": mine,
}

# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _premultiplied_resize(img, size):
    """Resize BGRA without dark fringes: premultiply, resize, un-premultiply."""
    f = img.astype(np.float32)
    a = f[:, :, 3:4] / 255.0
    f[:, :, :3] *= a
    f = cv2.resize(f, size, interpolation=cv2.INTER_AREA)
    a2 = f[:, :, 3:4] / 255.0
    f[:, :, :3] = np.where(a2 > 1e-4, f[:, :, :3] / np.maximum(a2, 1e-4), 0)
    return np.clip(f, 0, 255).astype(np.uint8)


def render_sprite(svg_text):
    png = cairosvg.svg2png(bytestring=svg_text.encode(), output_width=SUPERSAMPLE, output_height=SUPERSAMPLE)
    img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)

    ys, xs = np.where(img[:, :, 3] > ALPHA_TRIM)
    img = img[ys.min():ys.max() + 1, xs.min():xs.max() + 1]

    h, w = img.shape[:2]
    scale = (SIZE - 2 * MARGIN) / max(h, w)
    new_w, new_h = max(1, round(w * scale)), max(1, round(h * scale))
    small = _premultiplied_resize(img, (new_w, new_h))

    canvas = np.zeros((SIZE, SIZE, 4), np.uint8)
    x0, y0 = (SIZE - new_w) // 2, (SIZE - new_h) // 2
    canvas[y0:y0 + new_h, x0:x0 + new_w] = small
    return canvas


def make_preview(sprites):
    """Contact sheet: each sprite on a dark and a light half, so you can judge
    outlines against any camera background."""
    cell, label_h, cols = 150, 26, 6
    rows = math.ceil(len(sprites) / cols)
    sheet = np.full((rows * (cell + label_h), cols * cell, 3), 30, np.uint8)

    for i, (name, img) in enumerate(sprites.items()):
        r, c = divmod(i, cols)
        x0, y0 = c * cell, r * (cell + label_h)
        sheet[y0:y0 + cell, x0:x0 + cell // 2] = (55, 55, 60)
        sheet[y0:y0 + cell, x0 + cell // 2:x0 + cell] = (200, 205, 200)

        s = cv2.resize(img, (cell - 14, cell - 14), interpolation=cv2.INTER_AREA)
        a = s[:, :, 3:4].astype(np.float32) / 255.0
        region = sheet[y0 + 7:y0 + 7 + s.shape[0], x0 + 7:x0 + 7 + s.shape[1]].astype(np.float32)
        sheet[y0 + 7:y0 + 7 + s.shape[0], x0 + 7:x0 + 7 + s.shape[1]] = (
            s[:, :, :3] * a + region * (1 - a)).astype(np.uint8)

        cv2.putText(sheet, name.replace(".png", ""), (x0 + 6, y0 + cell + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1, cv2.LINE_AA)
    return sheet


def main():
    SVG_DIR.mkdir(parents=True, exist_ok=True)
    rendered = {}
    for name, builder in SPRITES.items():
        svg_text = builder()
        (SVG_DIR / (Path(name).stem + ".svg")).write_text(svg_text)

        img = render_sprite(svg_text)
        dest = ASSETS / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(dest), img)
        rendered[name] = img
        print(f"Wrote {dest.relative_to(ROOT)}")

    PREVIEW.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(PREVIEW), make_preview(rendered))
    print(f"Wrote {PREVIEW.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.exit(main())
