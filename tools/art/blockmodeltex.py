"""Textures for the custom-geometry blocks (urn, desk, reliquary), painted on their packed UVs."""
import zlib

from lib.pixel import Canvas, glyph_mask, ramp, shade, mix
from .palette import GLOAM, GOLD, STAR, VIOLET, BONE, WOOD, IRON, CLAY, PAPER, CLOTH, BLACK, CLEAR
from .entitytex import fill_all, fill_face
from .glyphs import GLYPHS


def _seed(*v):
    return zlib.crc32(repr(v).encode())


URN_STYLES = [
    # body palette, band color, accent
    (CLAY, GOLD[2], STAR[3]),
    ([shade(c, 0.75) for c in CLAY], STAR[2], BONE[3]),
    (GLOAM[1:], GOLD[3], VIOLET[3]),
]


def paint_urn(geo, style):
    body, band, accent = URN_STYLES[style]
    c = Canvas(geo.tex_w, geo.tex_h, CLEAR)
    for bone, cube in geo.cubes():
        f = cube.faces()
        st = cube.style
        if st == 'clay_band':
            fill_all(c, cube, [shade(band, 0.7), band, shade(band, 1.2)], 0.2, 0.9, _seed(st, style))
        elif st == 'clay_knob':
            fill_all(c, cube, [shade(band, 0.8), band], 0.3, 1.0, _seed(st, style))
        else:
            lo, hi = (0.15, 0.45) if st == 'clay_dark' else (0.3, 0.75)
            fill_all(c, cube, body, lo, hi, _seed(st, style))
        if st == 'clay_body':
            for face in ('north', 'south', 'east', 'west'):
                x, y, w, h = f[face]
                for xx in range(x, x + w):
                    c.px(xx, y + 1, band)
                    c.px(xx, y + h - 2, shade(band, 0.8))
                gi = (style + ('north', 'south', 'east', 'west').index(face)) % 4
                m = glyph_mask(GLYPHS[gi], 0, 0)
                # downscale the 7x9 glyph into the 10x7 face center (every other row)
                for (gx, gy) in m:
                    if gy % 2 == 0:
                        c.px(x + 1 + gx + (w - 9) // 2, y + 2 + gy // 2, accent)
    return c


def paint_desk(geo):
    c = Canvas(geo.tex_w, geo.tex_h, CLEAR)
    for bone, cube in geo.cubes():
        f = cube.faces()
        st = cube.style
        s = _seed(cube.name)
        if st in ('wood', 'wood_dark', 'wood_top'):
            lo, hi = {'wood': (0.4, 0.8), 'wood_dark': (0.15, 0.5), 'wood_top': (0.45, 0.95)}[st]
            fill_all(c, cube, WOOD, lo, hi, s)
            if st == 'wood_top':
                x, y, w, h = f['up']
                for yy in range(y, y + h, 3):
                    for xx in range(x, x + w):
                        c.px(xx, yy, shade(c.get(xx, yy), 0.85))
        elif st == 'stone':
            fill_all(c, cube, GLOAM, 0.35, 0.7, s)
        elif st == 'book':
            fill_all(c, cube, [VIOLET[0], VIOLET[1]], 0.2, 0.8, s)
            x, y, w, h = f['up']
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    c.px(xx, yy, PAPER[2] if (xx - x) != w // 2 else PAPER[0])
            for yy in range(y + 1, y + h - 1):
                for xx in (x + 1, x + 2, x + 5, x + 6):
                    if (xx + yy) % 2 == 0:
                        c.px(xx, yy, shade(PAPER[0], 0.7))
            c.px(x + 2, y + 2, STAR[3])
        elif st == 'tablet':
            fill_all(c, cube, BONE, 0.3, 0.7, s)
            x, y, w, h = f['up']
            for xx in range(x + 1, x + w - 1):
                c.px(xx, y + 1, shade(BONE[0], 0.7))
        elif st == 'candle':
            fill_all(c, cube, [BONE[2], BONE[3]], 0.3, 0.9, s)
        elif st == 'flame':
            fill_all(c, cube, [STAR[3], STAR[5]], 0.3, 1.0, s)
    return c


def paint_reliquary(geo, grand):
    c = Canvas(geo.tex_w, geo.tex_h, CLEAR)
    metal = GOLD if grand else [shade(x, 0.8) for x in GOLD[:4]]
    for bone, cube in geo.cubes():
        f = cube.faces()
        st = cube.style
        s = _seed(cube.name, grand)
        if st in ('stone_dark',):
            fill_all(c, cube, GLOAM, 0.15, 0.45, s)
        elif st == 'casket':
            fill_all(c, cube, VIOLET[:3] if grand else GLOAM[1:], 0.25, 0.65, s)
            for face in ('north', 'south', 'east', 'west'):
                x, y, w, h = f[face]
                for xx in range(x, x + w):
                    c.px(xx, y, metal[2])
                    c.px(xx, y + h - 1, metal[1])
                cx, cy = x + w // 2, y + h // 2
                for (dx, dy) in ((0, -2), (-1, -1), (0, -1), (1, -1), (-2, 0), (-1, 0), (0, 0), (1, 0),
                                 (-1, 1), (0, 1), (1, 1), (0, 2), (-1, 2)):
                    c.px(cx + dx, cy + dy, metal[3])
                c.px(cx, cy, STAR[4])
                c.px(cx - 1, cy, STAR[3])
        elif st == 'gilt':
            fill_all(c, cube, metal, 0.3, 0.9, s)
        elif st == 'lid':
            fill_all(c, cube, GLOAM, 0.3, 0.6, s)
            for face in ('north', 'south', 'east', 'west'):
                x, y, w, h = f[face]
                for xx in range(x, x + w):
                    c.px(xx, y + h - 1, metal[2])
            x, y, w, h = f['up']
            for xx in range(x, x + w):
                c.px(xx, y, metal[2])
                c.px(xx, y + h - 1, metal[2])
            for yy in range(y, y + h):
                c.px(x, yy, metal[2])
                c.px(x + w - 1, yy, metal[2])
        elif st == 'core':
            fill_all(c, cube, STAR[3:] if grand else STAR[2:5], 0.4, 1.0, s)
    return c
