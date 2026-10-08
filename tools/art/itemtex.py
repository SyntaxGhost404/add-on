"""Procedural 16x16 item sprites."""
import math

from lib.pixel import Canvas, glyph_mask, ramp, shade, mix, value_noise
from .palette import (GLOAM, GOLD, STAR, VIOLET, BONE, WOOD, IRON, COPPER, AMETHYST, PAPER, CLOTH, CLAY,
                      OUTLINE, BLACK)
from .glyphs import GLYPHS, SEWN_MOUTH

S = 16


def poly_fill(c, pts, color_fn):
    """Fill a polygon (list of (x,y) float vertices) using an even-odd scanline test."""
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    for y in range(max(0, int(min(ys))), min(S, int(math.ceil(max(ys))) + 1)):
        for x in range(max(0, int(min(xs))), min(S, int(math.ceil(max(xs))) + 1)):
            px, py = x + 0.5, y + 0.5
            inside = False
            j = len(pts) - 1
            for i in range(len(pts)):
                xi, yi = pts[i]
                xj, yj = pts[j]
                if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi + 1e-9) + xi:
                    inside = not inside
                j = i
            if inside:
                c.px(x, y, color_fn(x, y))


def finish(c, outline=OUTLINE):
    c.outline(outline)
    return c


def thick_line(c, x0, y0, x1, y1, col_fn, width=1):
    steps = max(abs(x1 - x0), abs(y1 - y0)) * 2 + 1
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        for dx in range(width):
            for dy in range(width):
                xx, yy = int(round(x)) + dx, int(round(y)) + dy
                c.px(xx, yy, col_fn(xx, yy, t))


def codex():
    c = Canvas(S, S)
    n = value_noise(S, S, 3, 201, 2)
    c.rect(3, 1, 13, 13, (0, 0, 0, 0))
    for y in range(1, 14):
        for x in range(3, 13):
            c.px(x, y, ramp([shade(CLOTH[3], 1.4), VIOLET[1], VIOLET[2]], 0.2 + n[y, x] * 0.5))
    for y in range(1, 14):
        c.px(3, y, VIOLET[0])
        c.px(4, y, shade(VIOLET[1], 0.8))
    for y in range(2, 14):
        c.px(13, y, PAPER[2] if y % 2 else PAPER[3])
    for x in range(4, 14):
        c.px(x, 14, PAPER[2] if x % 2 else PAPER[1])
    for (x, y) in ((5, 2), (12, 2), (5, 12), (12, 12)):
        c.px(x, y, GOLD[3])
    eye = ['.###.', '#...#', '#.#.#', '#...#', '.###.', '.#.#.']
    for (x, y) in glyph_mask(eye, 6, 4):
        c.px(x, y, GOLD[4] if y < 7 else GOLD[2])
    c.px(8, 6, STAR[4])
    return finish(c)


def glyph_shard():
    c = Canvas(S, S)
    pts = [(4, 3), (9, 1), (13, 5), (12, 10), (8, 14), (3, 11), (2, 6)]
    n = value_noise(S, S, 3, 210, 2)
    poly_fill(c, pts, lambda x, y: ramp(GLOAM, 0.4 + n[y, x] * 0.35 + (0.12 if x + y < 12 else -0.05)))
    for (x, y) in ((6, 5), (7, 6), (8, 7), (8, 8), (7, 9), (9, 6), (10, 5)):
        c.px(x, y, STAR[4])
    c.px(5, 4, shade(GLOAM[6], 1.2))
    return finish(c)


def inscribed_tablet():
    c = Canvas(S, S)
    n = value_noise(S, S, 3, 220, 2)
    for y in range(2, 15):
        for x in range(3, 13):
            if (x, y) in ((3, 2), (12, 2), (3, 14), (12, 14), (11, 2), (12, 3)):
                continue
            c.px(x, y, ramp(BONE, 0.25 + n[y, x] * 0.4))
    for row, y in enumerate((4, 6, 8, 10, 12)):
        for x in range(5, 11):
            if (x + row) % 3 != 0:
                c.px(x, y, shade(BONE[0], 0.7))
    c.px(9, 6, STAR[3])
    c.px(6, 10, STAR[3])
    for y in range(3, 15):
        c.px(12, y, shade(c.get(12, y), 0.8))
    return finish(c)


def key_shape(c, bow_col, shaft_col, gem=None, ornate=False):
    cx, cy, r = 5, 5, 3.4 if ornate else 3.0
    for y in range(S):
        for x in range(S):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if r - 1.6 <= d <= r:
                c.px(x, y, bow_col(x, y))
    thick_line(c, 7, 7, 13, 13, lambda x, y, t: shaft_col(x, y), 2 if ornate else 1)
    for (x, y) in ((11, 13), (12, 12), (10, 13), (13, 10)):
        c.px(x, y, shaft_col(x, y))
    if ornate:
        for (x, y) in ((12, 14), (14, 12), (13, 14)):
            c.px(x, y, shaft_col(x, y))
    if gem:
        for (x, y), col in gem:
            c.px(x, y, col)


def reliquary_key():
    c = Canvas(S, S)
    key_shape(c, lambda x, y: GOLD[3] if (x + y) % 3 else GOLD[4], lambda x, y: GOLD[2],
              gem=[((5, 5), STAR[4])])
    return finish(c)


def sigil_key():
    c = Canvas(S, S)
    key_shape(c, lambda x, y: GOLD[3] if (x + y) % 2 else GOLD[4], lambda x, y: GOLD[3] if (x + y) % 2 else GOLD[2],
              gem=[((4, 4), STAR[4]), ((6, 4), BONE[4]), ((5, 6), VIOLET[4])], ornate=True)
    return finish(c)


def shard(palette, mark_col, seed):
    c = Canvas(S, S)
    pts = [(8, 1), (12, 6), (10, 14), (6, 14), (4, 6)]
    n = value_noise(S, S, 3, seed, 2)
    poly_fill(c, pts, lambda x, y: ramp(palette, 0.35 + n[y, x] * 0.3 + (0.25 if x < 8 else -0.05)))
    for y in range(3, 13):
        c.px(8, y, shade(c.get(8, y), 1.15))
    return c, mark_col


def lantern_shard():
    c, m = shard(STAR, STAR[5], 231)
    for (x, y) in ((8, 5), (7, 6), (8, 6), (9, 6), (7, 7), (9, 7), (8, 8), (8, 9)):
        c.px(x, y, m)
    return finish(c, shade(STAR[0], 0.6))


def bone_shard():
    c, m = shard(BONE, BLACK, 232)
    for (x, y) in ((7, 6), (9, 6), (8, 7), (8, 8), (7, 9), (9, 9)):
        c.px(x, y, shade(BONE[0], 0.6))
    return finish(c, shade(BONE[0], 0.45))


def hush_shard():
    c, m = shard(VIOLET, VIOLET[4], 233)
    for (x, y) in ((7, 7), (8, 7), (9, 7), (7, 9), (8, 9), (9, 9), (8, 8)):
        c.px(x, y, VIOLET[4] if y != 8 else BLACK)
    return finish(c, shade(VIOLET[0], 0.6))


def cantors_seal():
    c = Canvas(S, S)
    for y in range(S):
        for x in range(S):
            d = math.hypot(x + 0.5 - 8, y + 0.5 - 7.5)
            if d <= 6.2:
                t = 0.45 + (0.25 if x + y < 14 else -0.1)
                if d > 5.2:
                    t = 0.75
                c.px(x, y, ramp(GOLD, t))
    for (x, y) in glyph_mask(SEWN_MOUTH, 4, 6):
        c.px(x, y, GOLD[1])
    for (x, y) in ((6, 4), (9, 4)):
        c.px(x, y, STAR[4])
    for (x, y) in ((6, 13), (6, 14), (7, 14), (9, 13), (9, 14), (10, 14)):
        c.px(x, y, VIOLET[2])
    return finish(c)


def murmur_essence():
    c = Canvas(S, S)
    for y in range(3, 15):
        for x in range(4, 12):
            dx = abs(x - 7.5)
            if y < 6 and dx > 1.5:
                continue
            if y >= 6 and dx > 3.5:
                continue
            c.px(x, y, (190, 230, 235, 110))
    c.rect(6, 2, 9, 3, WOOD[3])
    swirl = [(7, 13), (6, 12), (6, 11), (7, 10), (8, 10), (9, 9), (9, 8), (8, 7), (7, 7), (7, 8)]
    for i, (x, y) in enumerate(swirl):
        c.px(x, y, STAR[4] if i % 2 else STAR[5])
    c.px(5, 9, (255, 255, 255, 200))
    return finish(c)


def diviners_lens():
    c = Canvas(S, S)
    cx, cy = 9, 6.5
    for y in range(S):
        for x in range(S):
            d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if d <= 3.3:
                c.px(x, y, ramp(AMETHYST, 0.45 + (0.3 if x + y < 15 else 0)))
            elif d <= 5.0:
                c.px(x, y, ramp(GOLD, 0.45 + (0.3 if x + y < 15 else -0.1)))
    c.px(8, 5, (255, 255, 255, 255))
    thick_line(c, 5, 10, 2, 14, lambda x, y, t: WOOD[3] if t < 0.5 else WOOD[2], 2)
    c.px(5, 10, GOLD[3])
    return finish(c)


def dowsing_rod():
    c = Canvas(S, S)
    wood = lambda x, y, t: WOOD[3] if (x + y) % 3 else WOOD[4]
    thick_line(c, 8, 15, 8, 9, wood, 1)
    thick_line(c, 8, 9, 3, 2, wood, 1)
    thick_line(c, 8, 9, 13, 2, wood, 1)
    for (x, y) in ((8, 12), (8, 13), (7, 12)):
        c.px(x, y, COPPER[3])
    for (x, y) in ((8, 8), (7, 9), (9, 9), (8, 9), (8, 10)):
        c.px(x, y, STAR[4] if (x, y) != (8, 9) else STAR[5])
    c.px(3, 2, COPPER[3])
    c.px(13, 2, COPPER[3])
    return finish(c)


def delvers_pick():
    c = Canvas(S, S)
    thick_line(c, 3, 14, 10, 7, lambda x, y, t: WOOD[2] if (x + y) % 2 else WOOD[3], 1)
    head = [(4, 3), (5, 2), (6, 2), (7, 2), (8, 2), (9, 3), (10, 4), (11, 5), (12, 6), (13, 7), (13, 8),
            (5, 3), (6, 3), (7, 3), (8, 3), (9, 4), (10, 5), (11, 6), (12, 7), (9, 5), (10, 6), (11, 7), (12, 9)]
    for (x, y) in head:
        c.px(x, y, ramp(IRON, 0.35 + (0.3 if y < 4 else 0)))
    for (x, y) in ((7, 3), (9, 4), (11, 6)):
        c.px(x, y, STAR[3])
    c.px(3, 4, IRON[4])
    c.px(13, 9, IRON[4])
    return finish(c)


def dirge_blade():
    c = Canvas(S, S)
    thick_line(c, 4, 11, 13, 2, lambda x, y, t: ramp(GLOAM, 0.55 + 0.3 * t), 1)
    thick_line(c, 5, 11, 13, 3, lambda x, y, t: STAR[3] if (x + y) % 2 else STAR[4], 1)
    for (x, y) in ((2, 10), (3, 11), (4, 12), (5, 13), (3, 9), (6, 14)):
        c.px(x, y, GOLD[3])
    thick_line(c, 3, 13, 1, 15, lambda x, y, t: CLOTH[3], 1)
    c.px(1, 15, BONE[4])
    c.px(2, 14, BONE[3])
    return finish(c)


def sentinels_maul():
    c = Canvas(S, S)
    thick_line(c, 2, 14, 9, 7, lambda x, y, t: WOOD[2] if (x + y) % 2 else WOOD[3], 1)
    n = value_noise(S, S, 3, 260, 2)
    pts = [(7, 3), (11, 0), (15, 4), (11, 8)]
    poly_fill(c, pts, lambda x, y: ramp(GLOAM, 0.35 + n[y, x] * 0.4))
    for (x, y) in ((11, 3), (11, 4), (10, 4), (12, 4)):
        c.px(x, y, STAR[3])
    c.px(8, 6, GOLD[3])
    c.px(9, 6, GOLD[2])
    return finish(c)


def choristers_mask():
    c = Canvas(S, S)
    for y in range(S):
        for x in range(S):
            d = ((x + 0.5 - 8) / 5.6) ** 2 + ((y + 0.5 - 8) / 7.0) ** 2
            if d <= 1.0:
                c.px(x, y, ramp(BONE, 0.55 + (0.3 if x < 8 else 0.05) - (0.15 if y > 11 else 0)))
    for (x, y) in ((5, 6), (6, 6), (9, 6), (10, 6), (5, 7), (10, 7)):
        c.px(x, y, BLACK)
    for (x, y) in glyph_mask(['#####', '.#.#.', '#####'], 6, 10):
        c.px(x, y, shade(BONE[0], 0.6))
    for x in range(4, 12):
        c.px(x, 2, GOLD[3])
    c.px(6, 8, STAR[4])
    c.px(6, 9, STAR[3])
    return finish(c)


def hushweave_mantle():
    c = Canvas(S, S)
    n = value_noise(S, S, 3, 270, 2)
    pts = [(6, 1), (10, 1), (12, 4), (14, 14), (2, 14), (4, 4)]
    poly_fill(c, pts, lambda x, y: ramp(CLOTH + [VIOLET[1]], 0.3 + n[y, x] * 0.45))
    for y in range(2, 6):
        for x in range(7, 10):
            c.px(x, y, BLACK)
    for x in range(3, 14):
        c.px(x, 14, STAR[2] if x % 2 else STAR[3])
    for y in range(6, 14):
        c.px(8, y, shade(c.get(8, y), 0.7))
    c.px(8, 6, GOLD[3])
    return finish(c)


def low_star_fragment():
    c = Canvas(S, S)
    for y in range(S):
        for x in range(S):
            dx, dy = abs(x + 0.5 - 8), abs(y + 0.5 - 8)
            star = (dx * dy < 2.2 and dx + dy < 7.5) or (dx + dy < 3.2)
            if star:
                t = 1.0 - (dx + dy) / 8.0
                c.px(x, y, ramp(STAR, 0.35 + t * 0.65))
    for (x, y) in ((7, 7), (8, 7), (7, 8), (8, 8)):
        c.px(x, y, STAR[5])
    for (x, y) in ((3, 3), (12, 12), (12, 3), (3, 12)):
        c.px(x, y, (200, 255, 248, 160))
    return finish(c, shade(STAR[0], 0.6))


ITEM_TEXTURES = {
    'codex': codex,
    'glyph_shard': glyph_shard,
    'inscribed_tablet': inscribed_tablet,
    'reliquary_key': reliquary_key,
    'lantern_shard': lantern_shard,
    'bone_shard': bone_shard,
    'hush_shard': hush_shard,
    'sigil_key': sigil_key,
    'cantors_seal': cantors_seal,
    'murmur_essence': murmur_essence,
    'diviners_lens': diviners_lens,
    'dowsing_rod': dowsing_rod,
    'delvers_pick': delvers_pick,
    'dirge_blade': dirge_blade,
    'sentinels_maul': sentinels_maul,
    'choristers_mask': choristers_mask,
    'hushweave_mantle': hushweave_mantle,
    'low_star_fragment': low_star_fragment,
}
