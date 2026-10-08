"""Procedural 16x16 block textures for the Unnamed building set and mechanisms."""
import random

from lib.pixel import Canvas, glyph_mask, ramp, shade, mix, value_noise, hexrgb
from .palette import GLOAM, MORTAR, GOLD, STAR, VIOLET, MOSS, CLAY, BONE, WOOD, IRON, CLEAR, BLACK
from .glyphs import GLYPHS, WEEPING_EYE, SEWN_MOUTH

S = 16


def bricks(seed=1, palette=GLOAM, mortar=MORTAR, lo=2.3, hi=4.6):
    c = Canvas(S, S, mortar)
    rng = random.Random(seed)
    n = value_noise(S, S, 3, seed, 3)
    for row in range(4):
        y0 = row * 4
        offset = 0 if row % 2 == 0 else 4
        for b in range(3):
            x0 = (offset + b * 8) % 16
            tone = rng.uniform(-0.12, 0.12)
            for yy in range(3):
                for xx in range(7):
                    x = (x0 + xx) % 16
                    y = y0 + yy
                    t = (lo + (hi - lo) * n[y, x]) / (len(palette) - 1) + tone
                    col = ramp(palette, t)
                    if yy == 0 or xx == 0:
                        col = shade(col, 1.18)
                    if yy == 2 or xx == 6:
                        col = shade(col, 0.78)
                    c.px(x, y, col)
    c.speckle(0, 0, 15, 15, [shade(palette[3], 0.8), shade(palette[4], 1.05)], 0.06, seed + 7)
    return c


def gloamstone_bricks():
    return bricks(11)


def cracked_gloamstone_bricks():
    c = bricks(12)
    rng = random.Random(4)
    crack = [(3, 0), (4, 1), (4, 2), (5, 3), (6, 4), (6, 5), (7, 6), (9, 7), (10, 8), (10, 9), (11, 10),
             (12, 11), (12, 12), (13, 13), (5, 4), (4, 5), (3, 6), (11, 9), (13, 9), (14, 8)]
    for (x, y) in crack:
        c.px(x, y, shade(MORTAR, 0.9))
        if rng.random() < 0.6:
            c.px(x + 1, y, shade(c.get(x + 1, y), 1.15))
    for (x, y) in ((0, 12), (1, 12), (0, 13), (15, 4), (14, 4)):
        c.px(x, y, MORTAR)
    return c


def mossy_gloamstone_bricks():
    c = bricks(13)
    n = value_noise(S, S, 4, 77, 3)
    for y in range(S):
        for x in range(S):
            v = n[y, x] + (1 - y / 15) * 0.35
            if v > 0.78:
                c.px(x, y, ramp(MOSS, min(1.0, (v - 0.78) * 3 + 0.3)))
    for x, y0, ln in ((2, 3, 3), (9, 7, 2), (13, 3, 4), (6, 11, 2)):
        for y in range(y0, y0 + ln):
            c.px(x, y, MOSS[1 + (y % 2)])
    return c


def gloamstone_tiles():
    c = Canvas(S, S, MORTAR)
    n = value_noise(S, S, 4, 21, 3)
    for ty in range(2):
        for tx in range(2):
            x0, y0 = tx * 8, ty * 8
            for y in range(7):
                for x in range(7):
                    t = 0.28 + n[y0 + y, x0 + x] * 0.32
                    col = ramp(GLOAM, t)
                    if x == 0 or y == 0:
                        col = shade(col, 1.2)
                    if x == 6 or y == 6:
                        col = shade(col, 0.75)
                    c.px(x0 + x, y0 + y, col)
            # small carved diamond in each tile
            for (dx, dy) in ((3, 2), (2, 3), (4, 3), (3, 4)):
                c.px(x0 + dx, y0 + dy, shade(c.get(x0 + dx, y0 + dy), 0.62))
            c.px(x0 + 3, y0 + 3, shade(c.get(x0 + 3, y0 + 3), 1.1))
    return c


def gilded_gloamstone():
    c = bricks(14)
    for y in (3, 11):
        for x in range(S):
            c.px(x, y, ramp(GOLD, 0.55 + 0.25 * ((x * 7) % 3) / 2))
    rng = random.Random(9)
    for _ in range(10):
        x, y = rng.randrange(16), rng.randrange(16)
        if y not in (3, 11):
            c.px(x, y, GOLD[3 if rng.random() < 0.5 else 4])
    # a small gold sigil
    for (x, y) in ((7, 6), (8, 6), (6, 7), (9, 7), (7, 8), (8, 8)):
        c.px(x, y, GOLD[3])
    return c


def framed_panel(seed=31, frame_lo=0.45, inner=(0.18, 0.36)):
    """Gloamstone panel: 2px beveled frame + recessed field."""
    c = Canvas(S, S)
    n = value_noise(S, S, 3, seed, 3)
    for y in range(S):
        for x in range(S):
            edge = x < 2 or y < 2 or x > 13 or y > 13
            if edge:
                col = ramp(GLOAM, frame_lo + n[y, x] * 0.25)
                if x == 0 or y == 0:
                    col = shade(col, 1.2)
                if x == 15 or y == 15:
                    col = shade(col, 0.7)
            else:
                col = ramp(GLOAM, inner[0] + n[y, x] * (inner[1] - inner[0]))
                if x == 2 or y == 2:
                    col = shade(col, 0.7)
                if x == 13 or y == 13:
                    col = shade(col, 1.15)
            c.px(x, y, col)
    return c


def chiseled_gloamstone():
    c = framed_panel(32, inner=(0.36, 0.56))
    m = glyph_mask(WEEPING_EYE, 3, 3)
    c.carve(m, 0.32, 1.45, 0.7)
    c.px(8, 6, STAR[3])
    for (x, y) in ((6, 10), (8, 11), (10, 10)):
        c.px(x, y, STAR[1])
    return c


def gloamstone_pillar_side():
    c = Canvas(S, S)
    n = value_noise(S, S, 3, 41, 3)
    for y in range(S):
        for x in range(S):
            flute = x % 4
            t = 0.32 + n[y, x] * 0.25 + (0.12 if flute == 1 else 0) - (0.14 if flute == 3 else 0)
            col = ramp(GLOAM, t)
            if y < 2 or y > 13:
                col = ramp(GLOAM, 0.5 + n[y, x] * 0.2)
                if y == 0 or y == 14:
                    col = shade(col, 1.2)
                if y == 1 or y == 15:
                    col = shade(col, 0.72)
            c.px(x, y, col)
    return c


def gloamstone_pillar_top():
    c = Canvas(S, S)
    n = value_noise(S, S, 3, 42, 3)
    for y in range(S):
        for x in range(S):
            d = max(abs(x - 7.5), abs(y - 7.5))
            ring = int(d) % 3
            t = 0.3 + n[y, x] * 0.25 + (0.12 if ring == 0 else 0)
            col = ramp(GLOAM, t)
            if d > 7:
                col = shade(col, 0.8)
            c.px(x, y, col)
    for (x, y) in ((7, 7), (8, 7), (7, 8), (8, 8)):
        c.px(x, y, STAR[2])
    return c


# --- story murals ---------------------------------------------------------------------

def _paint(c, pts, col):
    for (x, y) in pts:
        c.px(x, y, col)


def glyph_mural(panel):
    c = framed_panel(50 + panel, inner=(0.15, 0.3))
    paint = STAR[4]
    dim = STAR[2]
    gold = GOLD[3]
    if panel == 0:  # The star falls into the earth
        _paint(c, [(7, 3), (6, 4), (7, 4), (8, 4), (7, 5), (5, 4), (9, 4), (7, 2)], paint)
        _paint(c, [(7, 6), (7, 7), (8, 8), (7, 9), (8, 10)], dim)
        _paint(c, [(x, 11) for x in range(3, 13)], gold)
        _paint(c, [(8, 11), (8, 12), (9, 12), (8, 13)], STAR[3])
    elif panel == 1:  # The choir kneels around the light
        for fx in (4, 7, 10):
            _paint(c, [(fx, 7), (fx, 8), (fx, 9), (fx - 1, 8), (fx + 1, 8), (fx - 1, 10), (fx + 1, 10)], BONE[3])
            c.px(fx, 6, BONE[4])
        _paint(c, [(7, 12), (6, 12), (8, 12), (7, 13)], paint)
        _paint(c, [(5, 4), (7, 3), (9, 4), (6, 5), (8, 5)], dim)
        _paint(c, [(x, 11) for x in range(3, 13)], gold)
    elif panel == 2:  # The Unsaying: a sealed mouth and an erased name
        m = glyph_mask(SEWN_MOUTH, 4, 7)
        _paint(c, m, BONE[3])
        _paint(c, [(5, 4), (6, 4), (9, 4), (10, 4)], paint)
        _paint(c, [(x, 3) for x in range(4, 12)], gold)
        _paint(c, [(x, 12) for x in range(3, 13)], gold)
        _paint(c, [(4, 13), (6, 13), (8, 13), (10, 13), (5, 12), (9, 12)], shade(gold, 0.5))
    else:  # The Silence: hollow outlines dissolving
        for fx in (4, 8, 11):
            _paint(c, [(fx, 6), (fx - 1, 7), (fx + 1, 7), (fx - 1, 9), (fx + 1, 9), (fx, 10)], dim)
        for (x, y) in ((6, 4), (10, 3), (12, 5), (5, 12), (9, 12), (12, 11), (3, 3), (7, 2)):
            c.px(x, y, paint)
        _paint(c, [(x, 13) for x in range(3, 13, 2)], gold)
    return c


def glyph_bitmap(c, gi, ox, oy, col, carve=False):
    m = glyph_mask(GLYPHS[gi], ox, oy)
    if carve:
        c.carve(m, 0.5, 1.3, 0.75)
    for (x, y) in m:
        c.px(x, y, col)
    return m


def cipher_stone(gi):
    c = framed_panel(60 + gi, inner=(0.12, 0.26))
    glyph_bitmap(c, gi, 4, 3, STAR[4])
    # faint glow halo around glyph pixels
    m = glyph_mask(GLYPHS[gi], 4, 3)
    for (x, y) in list(m):
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            p = (x + dx, y + dy)
            if p not in m and 2 <= p[0] <= 13 and 2 <= p[1] <= 13:
                c.px(p[0], p[1], mix(c.get(*p), STAR[1], 0.6))
    return c


def glyph_dial(gi):
    c = Canvas(S, S)
    n = value_noise(S, S, 3, 70 + gi, 3)
    for y in range(S):
        for x in range(S):
            c.px(x, y, ramp(GLOAM, 0.38 + n[y, x] * 0.22))
    # dial disc
    for y in range(S):
        for x in range(S):
            d = ((x - 7.5) ** 2 + (y - 7.5) ** 2) ** 0.5
            if d <= 7.2:
                c.px(x, y, ramp(IRON, 0.25 + n[y, x] * 0.25))
                if d > 6.2:
                    c.px(x, y, shade(GOLD[2], 1.0 if (x + y) % 2 else 0.85))
    glyph_bitmap(c, gi, 4, 3, STAR[4])
    c.px(7, 0, GOLD[4])
    c.px(8, 0, GOLD[4])
    return c


def glyph_dial_top():
    c = Canvas(S, S)
    n = value_noise(S, S, 3, 75, 3)
    for y in range(S):
        for x in range(S):
            d = ((x - 7.5) ** 2 + (y - 7.5) ** 2) ** 0.5
            col = ramp(GLOAM, 0.35 + n[y, x] * 0.25)
            if 5 < d < 6.5:
                col = GOLD[2]
            c.px(x, y, col)
    for (x, y) in ((7, 3), (8, 3), (7, 4), (8, 4)):
        c.px(x, y, GOLD[4])
    return c


def singing_stone():
    c = Canvas(S, S)
    n = value_noise(S, S, 4, 81, 4)
    for y in range(S):
        for x in range(S):
            c.px(x, y, ramp(GLOAM, 0.2 + n[y, x] * 0.35))
    veins = [(1, 2), (2, 3), (3, 3), (4, 4), (5, 5), (5, 6), (6, 7), (7, 7), (8, 8), (9, 8), (10, 9),
             (11, 10), (12, 10), (13, 11), (14, 12), (9, 7), (10, 6), (11, 5), (12, 4), (13, 4), (6, 8),
             (5, 9), (4, 10), (4, 11), (3, 12), (2, 13), (8, 9), (8, 10), (9, 11), (9, 12), (10, 13)]
    for i, (x, y) in enumerate(veins):
        c.px(x, y, STAR[3] if i % 3 else STAR[4])
        for dx, dy in ((1, 0), (0, 1)):
            q = (x + dx, y + dy)
            if q not in veins:
                c.px(q[0], q[1], mix(c.get(*q), STAR[1], 0.5))
    for (x, y) in ((7, 7), (12, 4), (3, 12)):
        c.px(x, y, STAR[5])
    return c


def choir_lantern():
    c = Canvas(S, S)
    n = value_noise(S, S, 3, 90, 3)
    for y in range(S):
        for x in range(S):
            frame = x < 2 or x > 13 or y < 2 or y > 13 or x in (7, 8) or y in (7, 8)
            if frame:
                col = ramp(GLOAM, 0.35 + n[y, x] * 0.25)
                if x == 0 or y == 0:
                    col = shade(col, 1.2)
            else:
                d = abs(x - 7.5) + abs(y - 7.5)
                col = ramp(STAR, 1.0 - d / 14)
            c.px(x, y, col)
    for (x, y) in ((7, 7), (8, 8), (7, 8), (8, 7)):
        c.px(x, y, GOLD[3])
    return c


def choir_lantern_top():
    c = Canvas(S, S)
    n = value_noise(S, S, 3, 91, 3)
    for y in range(S):
        for x in range(S):
            d = max(abs(x - 7.5), abs(y - 7.5))
            col = ramp(GLOAM, 0.35 + n[y, x] * 0.25)
            if d < 3:
                col = ramp(STAR, 0.9 - d / 6)
            elif d < 4:
                col = GOLD[2]
            c.px(x, y, col)
    return c


def sealed_gate():
    c = Canvas(S, S)
    n = value_noise(S, S, 3, 101, 3)
    for y in range(S):
        for x in range(S):
            col = ramp(GLOAM, 0.22 + n[y, x] * 0.22)
            if x in (7, 8):
                col = shade(col, 0.55 if x == 7 else 0.8)
            if y in (0, 15) or x in (0, 15):
                col = shade(col, 0.75)
            c.px(x, y, col)
    # sealing ring
    for y in range(S):
        for x in range(S):
            d = ((x - 7.5) ** 2 + (y - 7.5) ** 2) ** 0.5
            if 4.6 < d < 5.6:
                c.px(x, y, GOLD[2] if (x + y) % 3 else GOLD[3])
    for (x, y) in ((7, 6), (8, 6), (6, 7), (9, 7), (6, 8), (9, 8), (7, 9), (8, 9)):
        c.px(x, y, STAR[2])
    for (x, y) in ((2, 2), (13, 2), (2, 13), (13, 13)):
        c.px(x, y, IRON[3])
        c.px(x + 1, y + 1, IRON[1])
    return c


def sealed_gate_top():
    c = Canvas(S, S)
    n = value_noise(S, S, 3, 102, 3)
    for y in range(S):
        for x in range(S):
            c.px(x, y, ramp(GLOAM, 0.2 + n[y, x] * 0.2))
    return c


def _sigil_marks(c, lit):
    lantern = [(3, 3), (2, 4), (3, 4), (4, 4), (3, 5)]
    bone = [(12, 3), (13, 3), (12, 4), (12, 5), (13, 5)]
    hush = [(7, 12), (8, 12), (6, 13), (9, 13), (7, 13), (8, 13)]
    for pts, col in ((lantern, STAR[4] if lit else STAR[1]), (bone, BONE[4] if lit else BONE[1]),
                     (hush, VIOLET[4] if lit else VIOLET[1])):
        for (x, y) in pts:
            c.px(x, y, col)


def sigil_lock(lit=False):
    c = framed_panel(110 + int(lit), inner=(0.14, 0.3))
    key = [(7, 5), (8, 5), (6, 6), (9, 6), (6, 7), (9, 7), (7, 8), (8, 8), (7, 9), (8, 9), (7, 10), (8, 10)]
    for (x, y) in key:
        c.px(x, y, STAR[5] if lit else BLACK)
    if lit:
        for (x, y) in ((7, 6), (8, 6), (7, 7), (8, 7)):
            c.px(x, y, STAR[4])
    _sigil_marks(c, lit)
    return c


def veilstone_revealed():
    base = bricks(11)
    c = Canvas(S, S)
    for y in range(S):
        for x in range(S):
            if (x + y) % 2 == 0 or (x * 3 + y) % 7 == 0:
                col = mix(base.get(x, y), STAR[3], 0.45)
                c.px(x, y, (col[0], col[1], col[2], 255))
    return c


def hushing_plate(spent=False):
    c = Canvas(S, S)
    n = value_noise(S, S, 3, 120, 3)
    for y in range(S):
        for x in range(S):
            col = ramp(GLOAM, 0.3 + n[y, x] * 0.25)
            if x in (0, 15) or y in (0, 15):
                col = shade(col, 0.7)
            c.px(x, y, col)
    m = glyph_mask(SEWN_MOUTH, 3, 5)
    c.carve(m, 0.5, 1.25, 0.7)
    if not spent:
        for (x, y) in m:
            if (x + y) % 3 == 0:
                c.px(x, y, VIOLET[2])
    else:
        for (x, y) in ((2, 3), (3, 4), (4, 4), (12, 11), (13, 12), (11, 12)):
            c.px(x, y, MORTAR)
    return c


def spawn_marker():
    return Canvas(S, S, CLEAR)


BLOCK_TEXTURES = {
    'gloamstone_bricks': gloamstone_bricks,
    'cracked_gloamstone_bricks': cracked_gloamstone_bricks,
    'mossy_gloamstone_bricks': mossy_gloamstone_bricks,
    'gloamstone_tiles': gloamstone_tiles,
    'gilded_gloamstone': gilded_gloamstone,
    'chiseled_gloamstone': chiseled_gloamstone,
    'gloamstone_pillar_side': gloamstone_pillar_side,
    'gloamstone_pillar_top': gloamstone_pillar_top,
    'singing_stone': singing_stone,
    'choir_lantern': choir_lantern,
    'choir_lantern_top': choir_lantern_top,
    'sealed_gate': sealed_gate,
    'sealed_gate_top': sealed_gate_top,
    'sigil_lock': lambda: sigil_lock(False),
    'sigil_lock_on': lambda: sigil_lock(True),
    'veilstone_revealed': veilstone_revealed,
    'hushing_plate': lambda: hushing_plate(False),
    'hushing_plate_spent': lambda: hushing_plate(True),
    'glyph_dial_top': glyph_dial_top,
    'spawn_marker': spawn_marker,
}
for _p in range(4):
    BLOCK_TEXTURES[f'glyph_mural_{_p}'] = (lambda p=_p: glyph_mural(p))
    BLOCK_TEXTURES[f'cipher_stone_{_p}'] = (lambda p=_p: cipher_stone(p))
    BLOCK_TEXTURES[f'glyph_dial_{_p}'] = (lambda p=_p: glyph_dial(p))
