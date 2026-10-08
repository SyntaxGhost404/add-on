"""Entity, armor and misc textures painted directly onto packed box-UV layouts."""
import math
import random
import zlib

from lib.pixel import Canvas, glyph_mask, ramp, shade, mix, value_noise, hexrgb
from .palette import (GLOAM, GOLD, STAR, VIOLET, BONE, WOOD, IRON, CLOTH, ASH, MOSS, BLACK, CLEAR, OUTLINE,
                      CLAY, PAPER)
from .glyphs import WEEPING_EYE, SEWN_MOUTH, GLYPHS


def sh(v):
    """Stable (process-independent) hash."""
    return zlib.crc32(repr(v).encode())


def fill_face(c, rect, palette, lo=0.25, hi=0.6, seed=0, edge=True, alpha=None, scale=3):
    x0, y0, w, h = rect
    if w <= 0 or h <= 0:
        return
    n = value_noise(max(w, 2), max(h, 2), scale, seed, 2)
    for yy in range(h):
        for xx in range(w):
            col = ramp(palette, lo + (hi - lo) * n[yy % n.shape[0], xx % n.shape[1]])
            if edge:
                if yy == 0:
                    col = shade(col, 1.15)
                elif yy == h - 1:
                    col = shade(col, 0.78)
                if xx == w - 1 and w > 2:
                    col = shade(col, 0.88)
            if alpha is not None:
                col = (col[0], col[1], col[2], alpha)
            c.px(x0 + xx, y0 + yy, col)


def fill_all(c, cube, palette, lo=0.25, hi=0.6, seed=0, alpha=None, top_boost=0.08):
    for i, (face, rect) in enumerate(cube.faces().items()):
        boost = top_boost if face == 'up' else (-top_boost if face == 'down' else 0)
        fill_face(c, rect, palette, lo + boost, hi + boost, seed + i * 13, alpha=alpha)


def stamp(c, mask, col):
    for (x, y) in mask:
        c.px(x, y, col)


# ---------------------------------------------------------------- Hushwalker

HW_ROBES = [
    [hexrgb(h) for h in ('#1d1815', '#2a231f', '#3a312b', '#4a3f37', '#5b4f45')],   # earth-brown shroud
    [hexrgb(h) for h in ('#3b3a3f', '#504e55', '#67646c', '#7f7b84', '#9893a0')],   # ash-grey shroud
    [hexrgb(h) for h in ('#120f18', '#1c1724', '#272032', '#352b43', '#443756')],   # mourning violet
]
HW_MASKS = [BONE, [hexrgb(h) for h in ('#6d6a63', '#8d8981', '#adaaa1', '#cbc8bf', '#e4e1d8')], PAPER]


def paint_hushwalker(geo, variant):
    c = Canvas(geo.tex_w, geo.tex_h, CLEAR)
    robe = HW_ROBES[variant]
    mask = HW_MASKS[variant]
    seed = 300 + variant * 50
    for bone, cube in geo.cubes():
        f = cube.faces()
        st = cube.style
        if st == 'hw_face':
            fill_all(c, cube, ASH, 0.2, 0.5, seed)
            x, y, w, h = f['north']
            fill_face(c, f['north'], mask, 0.45, 0.8, seed + 1)
            for ex in (x + 1, x + 2, x + 5, x + 6):
                c.px(ex, y + 3, BLACK)
            c.px(x + 2, y + 4, BLACK)
            c.px(x + 5, y + 4, BLACK)
            for mx in range(x + 2, x + 6):
                c.px(mx, y + 6, shade(mask[0], 0.55))
            for mx in (x + 2, x + 4):
                c.px(mx, y + 5, shade(mask[0], 0.55))
                c.px(mx + 1, y + 7, shade(mask[0], 0.55))
            if variant == 1:
                for yy in range(y, y + 3):
                    c.px(x + 3, yy, GOLD[3])
                    c.px(x + 4, yy, GOLD[2])
            if variant == 2:
                for yy in range(y + 1, y + h, 2):
                    for xx in range(x, x + w):
                        if (xx + yy) % 3 == 0:
                            c.px(xx, yy, shade(c.get(xx, yy), 0.82))
            c.px(x + 2, y + 5, STAR[1])
        elif st == 'hw_hood':
            fill_all(c, cube, robe, 0.3, 0.75, seed + 5)
            x, y, w, h = f['north']
            for yy in range(y + 2, y + h):
                for xx in range(x + 1, x + w - 1):
                    c.px(xx, yy, CLEAR)
            for xx in range(x, x + w):
                c.px(xx, y + 1, shade(robe[1], 0.9))
            bx, by, bw, bh = f['south']
            for xx in range(bx, bx + bw):
                if xx % 2 == 0:
                    c.px(xx, by + bh - 1, CLEAR)
        elif st == 'robe_torso':
            fill_all(c, cube, robe, 0.25, 0.7, seed + 9)
            x, y, w, h = f['north']
            for xx in range(x, x + w):
                c.px(xx, y + 8, ROPE)
            c.px(x + 3, y + 9, STAR[3])
            c.px(x + 4, y + 9, STAR[3])
            c.px(x + 3, y + 10, STAR[2])
            for yy in range(y, y + 8):
                c.px(x + 3 + (yy % 2), yy, shade(robe[1], 0.9))
        elif st == 'robe_skirt':
            fill_all(c, cube, robe, 0.2, 0.65, seed + 11)
            for face in ('north', 'south', 'east', 'west'):
                x, y, w, h = f[face]
                for xx in range(x, x + w):
                    if (xx * 7 + variant) % 3 == 0:
                        c.px(xx, y + h - 1, CLEAR)
                    if (xx * 5) % 4 == 0:
                        c.px(xx, y + h - 2, shade(c.get(xx, y + h - 2), 0.7))
        elif st == 'hw_arm':
            fill_all(c, cube, ASH, 0.15, 0.5, seed + 13)
            for face in ('north', 'south', 'east', 'west', 'up'):
                x, y, w, h = f[face]
                for yy in range(y, y + min(h, 6)):
                    for xx in range(x, x + w):
                        c.px(xx, yy, ramp(robe, 0.35 + 0.2 * ((xx + yy) % 2)))
                if face != 'up':
                    for xx in range(x, x + w):
                        c.px(xx, y + h - 1, shade(ASH[1], 0.8))
        elif st == 'hw_leg':
            fill_all(c, cube, ASH, 0.1, 0.4, seed + 17)
            for face in ('north', 'south', 'east', 'west'):
                x, y, w, h = f[face]
                for yy in range(y, y + h, 3):
                    for xx in range(x, x + w):
                        c.px(xx, yy, shade(robe[2], 1.0))
    return c


ROPE = hexrgb('#8a7350')


def hushwalker_eyes(geo):
    c = Canvas(geo.tex_w, geo.tex_h, CLEAR)
    for bone, cube in geo.cubes():
        if cube.style == 'hw_face':
            x, y, w, h = cube.faces()['north']
            c.px(x + 2, y + 3, STAR[4])
            c.px(x + 5, y + 3, STAR[4])
    return c


# ---------------------------------------------------------------- Murmur

def paint_murmur(geo):
    c = Canvas(geo.tex_w, geo.tex_h, CLEAR)
    ghost = [hexrgb(h) for h in ('#4f8f8c', '#6fb3ad', '#93d1c9', '#bfe9e2', '#e5fbf7')]
    for bone, cube in geo.cubes():
        f = cube.faces()
        st = cube.style
        if st == 'mm_face':
            fill_all(c, cube, ghost, 0.45, 0.85, 401, alpha=200)
            x, y, w, h = f['north']
            for (ex, ey) in ((x + 1, y + 2), (x + 4, y + 2), (x + 1, y + 3), (x + 4, y + 3)):
                c.px(ex, ey, (12, 18, 20, 235))
            for my in (y + 4, y + 5):
                for mx in (x + 2, x + 3):
                    c.px(mx, my, (10, 14, 16, 235))
        elif st == 'mm_hood':
            fill_all(c, cube, ghost, 0.3, 0.6, 402, alpha=110)
            x, y, w, h = f['north']
            for yy in range(y + 1, y + h):
                for xx in range(x + 1, x + w - 1):
                    c.px(xx, yy, CLEAR)
        elif st in ('mm_torso', 'mm_arm'):
            fill_all(c, cube, ghost, 0.35, 0.75, 403 if st == 'mm_torso' else 404, alpha=170)
        elif st == 'mm_tail':
            fill_all(c, cube, ghost, 0.3, 0.6, 405, alpha=130)
        elif st == 'mm_tail_end':
            fill_all(c, cube, ghost, 0.25, 0.5, 406, alpha=80)
    return c


# ---------------------------------------------------------------- Graven Sentinel

STATUE = [hexrgb(h) for h in ('#2b2934', '#3b3846', '#4c4858', '#5e596b', '#726c80', '#878196')]


def carve_face(c, rect, seed):
    x, y, w, h = rect
    rng = random.Random(seed)
    for _ in range(max(1, w * h // 40)):
        cx, cy = x + rng.randrange(w), y + rng.randrange(h)
        for k in range(rng.randrange(2, 5)):
            c.px(cx, cy, shade(STATUE[0], 0.8))
            cx += rng.choice((-1, 0, 1))
            cy += 1
            if not (x <= cx < x + w and y <= cy < y + h):
                break


def paint_sentinel(geo):
    c = Canvas(geo.tex_w, geo.tex_h, CLEAR)
    for bone, cube in geo.cubes():
        f = cube.faces()
        st = cube.style
        fill_all(c, cube, STATUE, 0.25 if st != 'gs_band' else 0.4, 0.7 if st != 'gs_band' else 0.9,
                 500 + sh(cube.name) % 97)
        for face, rect in f.items():
            if face in ('north', 'south', 'east', 'west'):
                carve_face(c, rect, sh((cube.name, face)) % 1000)
        if st == 'gs_face':
            x, y, w, h = f['north']
            for xx in range(x + 2, x + w - 2):
                c.px(xx, y + 4, BLACK)
            c.px(x + 2, y + 5, BLACK)
            c.px(x + w - 3, y + 5, BLACK)
            for xx in range(x + 3, x + w - 3):
                c.px(xx, y + 7, shade(STATUE[1], 0.8))
        if st == 'gs_torso':
            x, y, w, h = f['north']
            m = glyph_mask(WEEPING_EYE, x + (w - 11) // 2, y + 3)
            c.carve(m, 0.55, 1.25, 0.75)
            for xx in range(x, x + w):
                if xx % 3 == 0:
                    c.px(xx, y + h - 1, MOSS[2])
        if st == 'gs_band':
            for face in ('north', 'south', 'east', 'west'):
                x, y, w, h = f[face]
                for xx in range(x, x + w):
                    if xx % 2 == 0:
                        c.px(xx, y, mix(c.get(xx, y), GOLD[2], 0.5))
        if st in ('gs_arm', 'gs_leg'):
            for face in ('north', 'south', 'east', 'west'):
                x, y, w, h = f[face]
                for xx in range(x, x + w):
                    c.px(xx, y + h // 3, shade(STATUE[1], 0.9))
                    c.px(xx, y + 2 * h // 3, shade(STATUE[1], 0.9))
                    if (xx + y) % 4 == 0:
                        c.px(xx, y + h - 1, MOSS[1])
    return c


def sentinel_glow(geo):
    c = Canvas(geo.tex_w, geo.tex_h, CLEAR)
    for bone, cube in geo.cubes():
        f = cube.faces()
        if cube.style == 'gs_face':
            x, y, w, h = f['north']
            for xx in range(x + 2, x + w - 2):
                c.px(xx, y + 4, STAR[4] if xx % 2 else STAR[3])
        if cube.style == 'gs_torso':
            x, y, w, h = f['north']
            cx = x + (w - 11) // 2
            c.px(cx + 5, y + 3 + 3, STAR[5])
            for (dx, dy) in ((4, 7), (6, 7), (4, 8), (6, 8)):
                c.px(cx + dx, y + 3 + dy, STAR[3])
    return c


# ---------------------------------------------------------------- The Last Cantor

def paint_cantor(geo, phase):
    c = Canvas(geo.tex_w, geo.tex_h, CLEAR)
    robe = [hexrgb(h) for h in ('#0d0a12', '#16111e', '#21192d', '#2d223e', '#3b2d52')]
    trim = GOLD if phase == 0 else STAR
    for bone, cube in geo.cubes():
        f = cube.faces()
        st = cube.style
        seed = 600 + sh(cube.name) % 113
        if st in ('lc_robe', 'lc_torso', 'lc_hem', 'lc_hood'):
            fill_all(c, cube, robe, 0.2, 0.75, seed)
            for face in ('north', 'south', 'east', 'west'):
                x, y, w, h = f[face]
                if st == 'lc_hem':
                    for xx in range(x, x + w):
                        c.px(xx, y + h - 1, trim[2])
                        if xx % 2 == 0:
                            c.px(xx, y + h - 2, trim[1])
                if st == 'lc_robe' and face == 'north':
                    for yy in range(y, y + h):
                        c.px(x + w // 2, yy, trim[2] if yy % 2 else trim[1])
                if st == 'lc_torso' and face == 'north':
                    m = glyph_mask(GLYPHS[1], x + (w - 7) // 2, y + 2)
                    stamp(c, m, trim[3])
                if st == 'lc_hood':
                    for xx in range(x, x + w):
                        c.px(xx, y + h - 1, trim[2])
        elif st == 'lc_gold':
            fill_all(c, cube, trim, 0.3, 0.8, seed)
        elif st == 'lc_head':
            fill_all(c, cube, robe, 0.05, 0.35, seed)
        elif st == 'lc_mask':
            fill_all(c, cube, BONE, 0.55, 0.9, seed)
            x, y, w, h = f['north']
            for (ex, ey) in ((x + 1, y + 2), (x + 2, y + 2), (x + 4, y + 2), (x + 5, y + 2)):
                c.px(ex, ey, BLACK)
            for mx in range(x + 2, x + 5):
                c.px(mx, y + 5, shade(BONE[0], 0.5))
            c.px(x + 3, y + 4, shade(BONE[0], 0.5))
            for ty in range(y + 3, y + h):
                c.px(x + 2, ty, STAR[3] if ty % 2 else STAR[2])
                c.px(x + 5, ty, STAR[3] if ty % 2 == 0 else STAR[2])
            if phase == 1:
                for (cx, cy) in ((x + 3, y), (x + 3, y + 1), (x + 4, y + 2), (x + 3, y + 3), (x + 1, y + 4)):
                    c.px(cx, cy, STAR[4])
        elif st == 'lc_halo':
            fill_all(c, cube, trim, 0.5, 1.0, seed)
        elif st == 'lc_hand':
            fill_all(c, cube, ASH, 0.3, 0.7, seed)
            for face in ('north', 'south', 'east', 'west'):
                x, y, w, h = f[face]
                for xx in range(x, x + w):
                    if xx % 2 == 0:
                        c.px(xx, y + h - 1, CLEAR)
    return c


def cantor_glow(geo, phase):
    c = Canvas(geo.tex_w, geo.tex_h, CLEAR)
    for bone, cube in geo.cubes():
        f = cube.faces()
        if cube.style == 'lc_mask':
            x, y, w, h = f['north']
            for ty in range(y + 3, y + h):
                c.px(x + 2, ty, STAR[4])
                c.px(x + 5, ty, STAR[4])
            c.px(x + 1, y + 2, STAR[5])
            c.px(x + 5, y + 2, STAR[5])
            if phase == 1:
                for (cx, cy) in ((x + 3, y), (x + 3, y + 1), (x + 4, y + 2), (x + 3, y + 3), (x + 1, y + 4)):
                    c.px(cx, cy, STAR[5])
        if cube.style == 'lc_halo':
            for face, (x, y, w, h) in f.items():
                for yy in range(y, y + h):
                    for xx in range(x, x + w):
                        c.px(xx, yy, (GOLD if phase == 0 else STAR)[4])
    return c


# ---------------------------------------------------------------- Hush bolt

def paint_bolt(geo):
    c = Canvas(geo.tex_w, geo.tex_h, CLEAR)
    for bone, cube in geo.cubes():
        if cube.style == 'bolt_core':
            fill_all(c, cube, STAR[3:], 0.3, 1.0, 701)
        else:
            fill_all(c, cube, [VIOLET[1], VIOLET[2], STAR[2]], 0.2, 0.8, 702, alpha=120)
    return c


# ---------------------------------------------------------------- armor layers (64x32 humanoid armor UV)

def armor_mask():
    """Helmet layer for the Chorister's Mask: head box at (0,0) size 8x8x8."""
    c = Canvas(64, 32, CLEAR)
    # front face (8,8)-(15,15)
    for y in range(8, 16):
        for x in range(8, 16):
            c.px(x, y, ramp(BONE, 0.55 + (0.25 if x < 12 else 0.05)))
    for (x, y) in ((9, 11), (10, 11), (13, 11), (14, 11)):
        c.px(x, y, BLACK)
    for x in range(10, 14):
        c.px(x, 14, shade(BONE[0], 0.55))
    for x in (10, 12):
        c.px(x, 13, shade(BONE[0], 0.55))
        c.px(x + 1, 15, shade(BONE[0], 0.55))
    for x in range(8, 16):
        c.px(x, 8, GOLD[3])
    c.px(10, 12, STAR[4])
    c.px(10, 13, STAR[3])
    # straps on sides and back
    for x in range(0, 8):
        c.px(x, 11, WOOD[2])
    for x in range(16, 24):
        c.px(x, 11, WOOD[2])
    for x in range(24, 32):
        c.px(x, 11, WOOD[2])
    return c


def armor_mantle():
    """Chestplate layer: body box at (16,16) size 8x12x4, arms at (40,16) size 4x12x4."""
    c = Canvas(64, 32, CLEAR)
    n = value_noise(64, 32, 3, 811, 2)
    cloth = CLOTH + [VIOLET[1]]

    def region(x0, y0, w, h):
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                c.px(x, y, ramp(cloth, 0.3 + n[y, x] * 0.5))
    # body: box uv (16,16) w8 h12 d4 -> top(20,16,8,4) bottom(28,16,8,4) right(16,20,4,12) front(20,20,8,12) left(28,20,4,12) back(32,20,8,12)
    region(20, 16, 16, 4)
    region(16, 20, 24, 12)
    for y in range(20, 32):
        c.px(24, y, shade(c.get(24, y), 0.7))
    for x in range(20, 28):
        c.px(x, 31, STAR[2] if x % 2 else STAR[3])
    for x in range(32, 40):
        c.px(x, 31, STAR[2] if x % 2 else STAR[3])
    c.px(23, 21, GOLD[3])
    c.px(24, 21, GOLD[4])
    # arms: box uv (40,16) w4 h12 d4
    region(44, 16, 8, 4)
    region(40, 20, 16, 12)
    for x in range(40, 56):
        c.px(x, 31, STAR[2] if x % 2 else STAR[3])
    return c


# ---------------------------------------------------------------- particles & icons

def particle_mote():
    c = Canvas(8, 8, CLEAR)
    for y in range(8):
        for x in range(8):
            d = math.hypot(x + 0.5 - 4, y + 0.5 - 4)
            a = max(0.0, 1.0 - d / 4.0)
            if a > 0:
                c.px(x, y, (255, 255, 255, int(255 * min(1.0, a * 1.6))))
    return c


def particle_dust():
    c = Canvas(8, 8, CLEAR)
    rng = random.Random(5)
    for _ in range(14):
        x, y = rng.randrange(1, 7), rng.randrange(1, 7)
        c.px(x, y, (255, 255, 255, rng.choice((140, 200, 255))))
    return c


def pack_icon(kind):
    size = 128
    c = Canvas(size, size)
    n = value_noise(size, size, 16, 900 if kind == 'bp' else 901, 4)
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - 63.5, y - 63.5) / 90
            col = ramp(GLOAM, 0.15 + n[y, x] * 0.35 - d * 0.2)
            c.px(x, y, col)
    # glow
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - 63.5, y - 58) / 40
            if d < 1:
                c.px(x, y, mix(c.get(x, y), STAR[2], (1 - d) * 0.5))
    eye = Canvas(11, 10, CLEAR)
    for (x, y) in glyph_mask(WEEPING_EYE):
        eye.px(x, y, GOLD[3] if y < 7 else STAR[3])
    eye.px(5, 3, STAR[5])
    big = eye.scale(8)
    c.paste(big, 20, 20)
    # frame
    for i in range(4):
        c.rect_outline(i, i, size - 1 - i, size - 1 - i, GOLD[1 + (i % 2)] if i < 2 else GLOAM[1])
    if kind == 'rp':
        for (x, y) in ((10, 110), (118, 110), (10, 10), (118, 10)):
            c.rect(x - 2, y - 2, x + 2, y + 2, STAR[3])
    return c
