"""Dyed families: wool, concrete, concrete powder, terracotta, glazed terracotta (original motifs), glass,
stained glass and panes, shulker tops and candles. Colours follow each vanilla texture's mean colour so
dyes stay recognisable; the materials themselves are generated here."""
import numpy as np

from engine.noise import F32, fbm, ridged, cell_random, blur, warped_coords, norm01, smoothstep
from engine.color import ramp, mix, match_mean, hexrgb
from engine.material import Tex, MASTER
from engine.draw import X, Y, rect, circle
from recipes.terrain import speckles, grains
from registry import CALIBRATION

N = MASTER
COLOURS = ['black', 'blue', 'brown', 'cyan', 'gray', 'green', 'light_blue', 'lime', 'magenta', 'orange', 'pink',
           'purple', 'red', 'silver', 'white', 'yellow']


def cal(path):
    c = CALIBRATION['textures/blocks/' + path]
    return np.array(c['mean'], F32), float(c['lum'])


def dye_ramp(mean, spread=0.35):
    m = np.asarray(mean, F32)
    lo = np.clip(m * (1 - spread) - 0.02, 0, 1)
    hi = np.clip(m * (1 + spread * 0.7) + 0.04, 0, 1)
    return [(0.0, lo), (0.5, m), (1.0, hi)]


# ------------------------------------------------------------------ wool: felted knit
def wool(seed, path):
    mean, lum = cal(path)
    k = 8.0
    u, v = X / 16 * k, Y / 16 * k
    fu, fv = u % 1.0, v % 1.0
    jit = 0.06 * fbm(N, 16, seed, 2)
    legl = np.exp(-(((fu - 0.3 + 0.28 * (fv - 0.5)) + jit) / 0.17) ** 2)
    legr = np.exp(-(((fu - 0.7 - 0.28 * (fv - 0.5)) + jit) / 0.17) ** 2)
    stitch = np.maximum(legl, legr)
    rowdip = np.exp(-((fv - 0.0) / 0.12) ** 2) + np.exp(-((fv - 1.0) / 0.12) ** 2)
    fuzz = fbm(N, 64, seed + 1, 2)
    felt = fbm(N, 6, seed + 2, 4)
    ply = 0.5 + 0.5 * np.sin(2 * np.pi * (fu * 2.5 + fv * 1.5 * np.sign(fu - 0.5)))
    t = 0.45 + 0.24 * stitch - 0.1 * rowdip + 0.05 * ply * stitch + 0.1 * fuzz + 0.06 * felt
    rgb = ramp(np.clip(t, 0, 1), dye_ramp(mean, 0.3))
    h = 0.4 + 0.4 * stitch - 0.15 * rowdip + 0.08 * fuzz
    return Tex(match_mean(rgb, lum), norm01(blur(h, 0.7)), light='top', bump=0.9, ao=0.5, sharpen=0.3)


# ------------------------------------------------------------------ concrete
def concrete(seed, path):
    mean, lum = cal(path)
    x, y = warped_coords(N, 0.05, seed, freq=3)
    cloud = fbm(N, 3, seed + 1, 5, x=x, y=y)
    fine = fbm(N, 50, seed + 2, 2)
    voids, vv = speckles(N, 34, seed + 3, 0.03, 0.22)
    t = 0.5 + 0.06 * cloud + 0.03 * fine - 0.07 * voids
    rgb = ramp(np.clip(t, 0, 1), dye_ramp(mean, 0.25))
    h = 0.5 + 0.05 * cloud + 0.02 * fine - 0.25 * voids
    return Tex(match_mean(rgb, lum), norm01(h), light='top', bump=0.7, ao=0.35, sharpen=0.25)


def concrete_powder(seed, path):
    mean, lum = cal(path)
    dome, gap, cid = grains(N, 60, seed, 1.0)
    tone = cell_random(cid, seed + 1)
    clump = fbm(N, 7, seed + 2, 3)
    t = 0.5 + 0.12 * (tone - 0.5) + 0.12 * dome - 0.1 * gap + 0.06 * clump
    rgb = ramp(np.clip(t, 0, 1), dye_ramp(mean, 0.35))
    sp, sv = speckles(N, 44, seed + 3, 0.06, 0.3)
    rgb = mix(rgb, rgb * (0.7 + 0.6 * sv[..., None]), sp * 0.6)
    h = 0.5 + 0.2 * dome + 0.1 * clump
    return Tex(match_mean(rgb, lum), norm01(h), light='over', bump=0.8, ao=0.45, sharpen=0.35)


# ------------------------------------------------------------------ terracotta
def terracotta(seed, path):
    mean, lum = cal(path)
    x, y = warped_coords(N, 0.04, seed, freq=3)
    strata = np.sin(2 * np.pi * (y * 3 + 0.08 * fbm(N, (2, 2), seed + 1, 3, x=x, y=y)))
    mott = fbm(N, 4, seed + 2, 4)
    grain = fbm(N, 40, seed + 3, 2)
    sp, sv = speckles(N, 30, seed + 4, 0.05, 0.3)
    t = 0.5 + 0.018 * strata + 0.07 * mott + 0.045 * grain - 0.06 * sp
    rgb = ramp(np.clip(t, 0, 1), dye_ramp(mean, 0.3))
    h = 0.5 + 0.04 * strata + 0.06 * mott + 0.03 * grain
    return Tex(match_mean(rgb, lum), norm01(h), light='top', bump=0.8, ao=0.4)


# ------------------------------------------------------------------ glazed terracotta: original motifs
def _arc(cx, cy, r, w):
    d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    return 1 - smoothstep(w / 2 - 0.08, w / 2 + 0.08, np.abs(d - r))


def motif(k):
    """Sixteen tile motifs designed for rotation: placed in different orientations they join into larger
    patterns. Returns (primary mask, secondary mask)."""
    if k == 0:   # quarter-circle Truchet bands
        a = np.clip(_arc(0, 0, 8, 2.2) + _arc(16, 16, 8, 2.2), 0, 1)
        b = np.clip(_arc(0, 0, 4.2, 1.0) + _arc(16, 16, 4.2, 1.0) + circle(8, 8, 1.2), 0, 1)
    elif k == 1:  # diagonal sash with stepped edges
        d = (X - Y)
        a = (np.abs(d) < 3.0).astype(F32)
        b = ((np.abs(d) > 4.6) & (np.abs(d) < 5.8)).astype(F32)
    elif k == 2:  # corner fan with rays
        ang = np.arctan2(Y, X)
        rr = np.sqrt(X ** 2 + Y ** 2)
        a = ((np.cos(ang * 10) > 0.2) & (rr < 11) & (rr > 3)).astype(F32)
        b = np.clip(_arc(0, 0, 13.5, 1.2) + _arc(16, 16, 3.0, 1.0), 0, 1)
    elif k == 3:  # interlocking squares
        a = np.clip((rect(2, 2, 10, 10) - rect(3.4, 3.4, 8.6, 8.6)) + (rect(6, 6, 14, 14) - rect(7.4, 7.4, 12.6, 12.6)),
                    0, 1)
        b = rect(7.4, 7.4, 8.6, 8.6)
    elif k == 4:  # wave bands
        w = np.sin(2 * np.pi * X / 16 + np.pi / 2) * 2.0
        a = (np.abs(Y - 8 - w) < 2.0).astype(F32)
        b = ((np.abs(Y - 2.5 - w) < 0.6) | (np.abs(Y - 13.5 - w) < 0.6)).astype(F32)
    elif k == 5:  # four-petal rosette centred on a corner
        ang = np.arctan2(Y - 16, X - 16)
        rr = np.sqrt((X - 16) ** 2 + (Y - 16) ** 2)
        a = (rr < 9 * (0.55 + 0.45 * np.abs(np.cos(ang * 2)))).astype(F32) * (rr > 2)
        b = np.clip(circle(16, 16, 1.6) + _arc(0, 0, 5, 1.0), 0, 1)
    elif k == 6:  # chevron arrows
        a = (np.abs(((Y + np.abs(X - 8)) % 8) - 4) < 1.4).astype(F32)
        b = rect(7.2, 0, 8.8, 16) * 0.0 + (np.abs(((Y + np.abs(X - 8)) % 8) - 7) < 0.4).astype(F32)
    elif k == 7:  # concentric lozenge
        d = np.abs(X - 8) + np.abs(Y - 8)
        a = ((d % 5) < 2.0).astype(F32) * (d < 15)
        b = (d < 1.6).astype(F32)
    elif k == 8:  # leaf sprig from a corner
        from engine.draw import leaf
        a = np.zeros((N, N), F32)
        for ang, L in ((0.6, 9), (0.95, 7), (0.25, 7)):
            m, _, _ = leaf(1.5, 1.5, ang, L, 3.6)
            a = np.maximum(a, m)
        b = np.clip(_arc(16, 16, 6, 1.2) + circle(13, 13, 1.0), 0, 1)
    elif k == 9:  # stepped pyramid
        d = np.maximum(np.abs(X - 8), np.abs(Y - 8))
        a = ((np.floor(d / 2) % 2) == 0).astype(F32) * (d < 7)
        b = (d > 7.5).astype(F32) * ((np.floor((X + Y) / 2) % 2) == 0)
    elif k == 10:  # crescent and dots
        a = np.clip(circle(6, 6, 5) - circle(8.2, 4.8, 4.2), 0, 1)
        b = np.clip(circle(12, 12, 1.2) + circle(14, 8, 0.8) + circle(8, 14, 0.8), 0, 1)
    elif k == 11:  # woven strips
        cx, cy = np.floor(X / 4), np.floor(Y / 4)
        horiz = ((cx + cy) % 2) == 0
        a = np.where(horiz, (np.abs((Y % 4) - 2) < 1.1), (np.abs((X % 4) - 2) < 1.1)).astype(F32)
        b = ((X % 4 < 0.4) | (Y % 4 < 0.4)).astype(F32) * 0.0
    elif k == 12:  # sun quarter with zig-zag rays
        rr = np.sqrt((X - 16) ** 2 + Y ** 2)
        ang = np.arctan2(Y, X - 16)
        a = (rr < 6).astype(F32) + ((np.abs((rr + 1.5 * np.abs(np.sin(ang * 8))) % 4 - 2) < 0.7) & (rr > 7)).astype(F32)
        a = np.clip(a, 0, 1)
        b = np.clip(_arc(16, 0, 6.6, 0.6), 0, 1)
    elif k == 13:  # diagonal ladder
        d = X + Y
        a = ((np.abs(X - Y) < 4) & ((d % 4) < 2)).astype(F32)
        b = ((np.abs(np.abs(X - Y) - 5) < 0.6)).astype(F32)
    elif k == 14:  # ring knot across the tile edge
        a = np.clip(_arc(8, 0, 6, 1.8) + _arc(8, 16, 6, 1.8) + _arc(0, 8, 3, 1.4) + _arc(16, 8, 3, 1.4), 0, 1)
        b = circle(8, 8, 1.6)
    else:        # scattered seeds around a quatrefoil
        rr = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
        ang = np.arctan2(Y - 8, X - 8)
        a = (rr < 5.5 * (0.6 + 0.4 * np.abs(np.cos(ang * 2)))).astype(F32) * (rr > 1.4)
        b = np.clip(circle(2, 2, 1.0) + circle(14, 2, 1.0) + circle(2, 14, 1.0) + circle(14, 14, 1.0), 0, 1)
    return np.clip(a, 0, 1).astype(F32), np.clip(b, 0, 1).astype(F32)


ACCENTS = {
    'black': ('#2a2a32', '#c43a2a'), 'blue': ('#e8e4d8', '#f2c23a'), 'brown': ('#d8b27a', '#3a5a8a'),
    'cyan': ('#e8f0ea', '#1f3f5a'), 'gray': ('#a8b0b8', '#e2a43a'), 'green': ('#e2d6a2', '#3a2a1a'),
    'light_blue': ('#f2f2f2', '#2a4a9a'), 'lime': ('#f2f0c2', '#3a7a2a'), 'magenta': ('#f6d2ea', '#5a1a5a'),
    'orange': ('#2a8a8a', '#f6e6c2'), 'pink': ('#f8ecf0', '#c43a6a'), 'purple': ('#e2c23a', '#2a1a3a'),
    'red': ('#f2e2c2', '#2a2a2a'), 'silver': ('#5a7a9a', '#f2f2f2'), 'white': ('#2a8a9a', '#e2a23a'),
    'yellow': ('#3a6a9a', '#f6f6e6'),
}


def glazed(seed, colour, k):
    path = f'glazed_terracotta_{colour}'
    mean, lum = cal(path)
    a, b = motif(k)
    a, b = blur(a, 0.8), blur(b, 0.8)
    c2, c3 = (hexrgb(c) for c in ACCENTS[colour])
    base = np.asarray(mean, F32)
    pool = fbm(N, 5, seed, 4)
    rgb = base * (0.92 + 0.12 * pool[..., None])
    rgb = mix(rgb, c2 * (0.92 + 0.1 * pool[..., None]), a)
    rgb = mix(rgb, c3, b)
    crack = smoothstep(0.94, 0.985, ridged(N, 5, seed + 1, 3, sharp=2.5))
    rgb = rgb * (1 - 0.12 * crack[..., None])
    bevel = smoothstep(0.0, 0.7, np.minimum(np.minimum(X, 16 - X), np.minimum(Y, 16 - Y)))
    h = 0.6 + 0.08 * a + 0.04 * b + 0.35 * bevel - 0.05 * crack
    rgb = rgb * (0.85 + 0.15 * bevel[..., None])
    return Tex(match_mean(rgb, lum), norm01(blur(h, 0.6)), light='top', bump=1.0, ao=0.4, gloss=0.35)


# ------------------------------------------------------------------ glass
def clear_glass(seed, frame=0.42):
    b = np.minimum(np.minimum(X, 16 - X), np.minimum(Y, 16 - Y))
    edge = b < frame
    streak = np.zeros((N, N), bool)
    for (x0, y0, L) in ((3.2, 2.2, 2.4), (12.8, 12.6, 2.0)):
        for k in range(2):
            d = np.abs((X - x0 - 0.9 * k) + (Y - y0)) / np.sqrt(2)
            along = np.abs((X - x0) - (Y - y0)) / np.sqrt(2)
            streak |= (d < 0.17) & (along < L * (1 - 0.4 * k))
    alpha = (edge | streak).astype(F32)
    rgb = np.zeros((N, N, 3), F32)
    rgb[:] = hexrgb('#cfe6e8')
    rgb = np.where(edge[..., None], hexrgb('#9ec2c4') * (0.85 + 0.15 * (b / frame))[..., None], rgb)
    rgb = np.where(streak[..., None], hexrgb('#f4fbfc'), rgb)
    return Tex(rgb, None, alpha, light='none', cutout=True, sharpen=0.0)


def stained_glass(seed, path, tinted=False):
    mean, lum = cal(path)
    b = np.minimum(np.minimum(X, 16 - X), np.minimum(Y, 16 - Y))
    frame = 1 - smoothstep(0.35, 0.55, b)
    wav = fbm(N, (3, 8), seed, 3)
    seeds, sv = speckles(N, 26, seed + 1, 0.06, 0.25)
    col = np.asarray(mean, F32)
    rgb = np.clip(col * (0.92 + 0.12 * wav[..., None]), 0, 1)
    rgb = mix(rgb, np.clip(col * 0.7, 0, 1), frame)
    rgb = mix(rgb, np.clip(col * 1.25 + 0.1, 0, 1), seeds * 0.6)
    base_a = 0.36 if not tinted else 0.62
    alpha = np.clip(base_a + 0.08 * wav + 0.45 * frame + 0.15 * seeds, 0, 1)
    if not tinted:
        hl = (np.abs((X - 3.5) + (Y - 3.0)) < 0.35) & (np.abs((X - 3.5) - (Y - 3.0)) < 2.4)
        rgb = np.where(hl[..., None], np.clip(rgb * 1.4 + 0.25, 0, 1), rgb)
        alpha = np.where(hl, np.maximum(alpha, 0.7), alpha)
    return Tex(rgb, None, alpha.astype(F32), light='none', sharpen=0.0)


def pane_edge(path, colour=None):
    mean, lum = cal(path)
    t = 0.5 + 0.12 * np.cos(2 * np.pi * Y / 16 * 2) + 0.05 * fbm(N, (2, 20), 9, 2)
    rgb = ramp(np.clip(t, 0, 1), dye_ramp(mean, 0.3))
    if path.endswith('_top') or path == 'glass_pane_top':
        return Tex(match_mean(rgb, lum), None, None, light='none')
    alpha = np.full((N, N), 0.75, F32)
    return Tex(match_mean(rgb, lum), None, alpha, light='none')


# ------------------------------------------------------------------ shulker tops, candles
def shulker_top(seed, path):
    mean, lum = cal(path)
    b = np.minimum(np.minimum(X, 16 - X), np.minimum(Y, 16 - Y))
    bev = smoothstep(0.0, 1.2, b)
    ring = 1 - smoothstep(0.2, 0.5, np.abs(b - 2.6))
    shell = fbm(N, 6, seed, 3)
    t = 0.5 + 0.06 * shell - 0.15 * ring
    rgb = ramp(np.clip(t, 0, 1), dye_ramp(mean, 0.3)) * (0.82 + 0.18 * bev[..., None])
    h = 0.4 + 0.5 * bev - 0.2 * ring
    return Tex(match_mean(rgb, lum), norm01(h), light='top', bump=1.0, ao=0.5, gloss=0.15)


def candle(path, lit=False):
    from recipes.plants import mask_of
    mean, lum = cal(path)
    m = mask_of(path).astype(F32)
    t = 0.55 + 0.25 * np.cos(np.pi * (X / 2.0)) + 0.05 * fbm(N, (4, 20), 7, 2)
    rgb = ramp(np.clip(t, 0, 1), dye_ramp(mean, 0.35))
    wick = (Y < 6.0) & (Y >= 5.0)
    rgb = np.where(wick[..., None], hexrgb('#2a2622') if not lit else hexrgb('#f2c25a'), rgb)
    drip = (Y < 7.2) & (Y >= 6.0)
    rgb = np.where(drip[..., None], np.clip(rgb * 1.12, 0, 1), rgb)
    t2 = Tex(match_mean(rgb, lum, m > 0.5), None, m, light='none', cutout=True, sharpen=0.0)
    if lit:
        t2 = t2.but(emissive=(wick * m * 0.6)[..., None] * hexrgb('#ffd27a'))
    return t2


# ------------------------------------------------------------------ registration
def register(R):
    for i, c in enumerate(COLOURS):
        s = 2000 + 10 * i
        R.block(f'wool_colored_{c}', lambda v, s=s, c=c: wool(s, f'wool_colored_{c}'))
        R.block(f'concrete_{c}', lambda v, s=s, c=c: concrete(s + 1, f'concrete_{c}'))
        R.block(f'concrete_powder_{c}', lambda v, s=s, c=c: concrete_powder(s + 2, f'concrete_powder_{c}'))
        R.block(f'hardened_clay_stained_{c}', lambda v, s=s, c=c: terracotta(s + 3, f'hardened_clay_stained_{c}'))
        R.block(f'glazed_terracotta_{c}', lambda v, s=s, c=c, i=i: glazed(s + 4, c, i))
        R.block(f'glass_{c}', lambda v, s=s, c=c: stained_glass(s + 5, f'glass_{c}'))
        R.block(f'glass_pane_top_{c}', lambda v, c=c: pane_edge(f'glass_pane_top_{c}'))
        R.block(f'shulker_top_{c}', lambda v, s=s, c=c: shulker_top(s + 6, f'shulker_top_{c}'))
    R.block('shulker_top_undyed', lambda v: shulker_top(2200, 'shulker_top_undyed'))
    R.block('hardened_clay', lambda v: terracotta(2201, 'hardened_clay'))
    R.block('glass', lambda v: clear_glass(2202), cutout=True)
    R.block('glass_pane_top', lambda v: pane_edge('glass_pane_top'))
    R.block('tinted_glass', lambda v: stained_glass(2203, 'tinted_glass', tinted=True))
    candle_names = ['candle'] + [f'{c}_candle' for c in COLOURS if c != 'silver'] + ['light_gray_candle']
    for name in candle_names:
        p = f'candles/{name}'
        if ('textures/blocks/' + p) not in CALIBRATION:
            continue
        R.block(p, lambda v, p=p: candle(p), cutout=True)
        R.block(p + '_lit', lambda v, p=p: candle(p + '_lit', lit=True), cutout=True)
