"""Natural and organic blocks: nether ground and light sources, froglights, bone, mushrooms, sponge, hay,
honey, slime, melons and pumpkins, cobwebs, dripstone and sulfur spikes, amethyst buds and other shapes."""
import numpy as np

from engine.noise import F32, fbm, ridged, worley, cell_random, blur, warped_coords, norm01, smoothstep, rng
from engine.color import ramp, mix, match_mean, hexrgb
from engine.material import Tex, MASTER
from engine.draw import X, Y, rect, circle, polygon, capsules, scatter
from recipes.terrain import speckles, grains, layer_side, moss
from recipes.foliage import Canvas
from recipes.plants import mask_of, finish, disc
from registry import CALIBRATION

N = MASTER


def cal(path):
    c = CALIBRATION['textures/blocks/' + path]
    return np.array(c['mean'], F32), float(c['lum'])


def pal(mean, spread=0.4):
    m = np.asarray(mean, F32)
    return [(0, np.clip(m * (1 - spread), 0, 1)), (0.5, m), (1, np.clip(m * (1 + spread * 0.8) + 0.03, 0, 1))]


# ------------------------------------------------------------------ nether ground
def nylium_top(seed, path, stops):
    from engine.draw import fibres
    base = fbm(N, 4, seed, 5)
    lum = 0.25 + 0.1 * fbm(N, 20, seed + 1, 3)
    for k, (count, lo, hi) in enumerate(((1600, 0.3, 0.65), (1100, 0.45, 0.95))):
        l, c, z = fibres(seed + 3 + k, count, (0.35, 0.85), (0.1, 0.16), lo, hi, parts=2, curve=0.8, z0=k)
        lum = lum * (1 - c) + l * c
    lum = lum * (0.8 + 0.3 * base)
    rgb = ramp(np.clip(lum, 0, 1), stops)
    spores, sv = speckles(N, 24, seed + 9, 0.06, 0.3)
    rgb = mix(rgb, np.clip(ramp(np.array([1.0]), stops)[0] * 1.3, 0, 1), spores * 0.6)
    mean, lumt = cal(path)
    return Tex(match_mean(rgb, lumt), norm01(0.5 + 0.25 * lum + 0.2 * base), light='over', bump=1.2, ao=0.65)


def soul_ground(seed, path, faces=True):
    """Soul sand / soul soil: dark umber grains; soul sand shows faint anguished hollows in the grain."""
    x, y = warped_coords(N, 0.05, seed, freq=3)
    dome, gap, cid = grains(N, 40, seed + 1, 1.0)
    tone = cell_random(cid, seed + 2)
    base = fbm(N, 4, seed + 3, 4, x=x, y=y)
    t = 0.45 + 0.12 * base + 0.15 * dome + 0.12 * (tone - 0.5) - 0.15 * gap
    h = 0.5 + 0.25 * dome + 0.1 * base - 0.2 * gap
    if faces:
        r = rng(seed + 4)
        for _ in range(3):
            cx, cy = r.uniform(2, 14), r.uniform(2, 14)
            hol = np.clip(circle(cx - 1.0, cy, 0.7) + circle(cx + 1.0, cy, 0.7)
                          + (np.abs((X - cx) / 1.3) ** 2 + ((Y - cy - 1.9) / 0.7) ** 2 < 1), 0, 1)
            hol = blur(hol, 1.2)
            t = t - 0.25 * hol
            h = h - 0.35 * hol
    mean, lum = cal(path)
    rgb = ramp(np.clip(t, 0, 1), pal(mean, 0.5))
    return Tex(match_mean(rgb, lum), norm01(h), light='over', bump=1.3, ao=0.65)


def wart_block(seed, path, stops):
    x, y = warped_coords(N, 0.1, seed, freq=3)
    lumps = fbm(N, 6, seed + 1, 4, x=x, y=y)
    bumps = fbm(N, 14, seed + 4, 3, x=x, y=y)
    pores = smoothstep(0.55, 0.85, fbm(N, 28, seed + 2, 2))
    folds = smoothstep(0.86, 0.97, ridged(N, 5, seed + 3, 3, sharp=2.2))
    t = 0.5 + 0.22 * lumps + 0.12 * bumps - 0.12 * pores - 0.2 * folds
    rgb = ramp(np.clip(t, 0, 1), stops)
    mean, lum = cal(path)
    return Tex(match_mean(rgb, lum), norm01(0.5 + 0.3 * lumps + 0.15 * bumps - 0.15 * pores - 0.25 * folds),
               light='top', bump=1.5, ao=0.7)


def glowstone(seed=3600):
    x, y = warped_coords(N, 0.06, seed, freq=3)
    clusters = smoothstep(0.0, 0.6, fbm(N, 5, seed + 1, 4, x=x, y=y) + 0.25)
    f1, f2, cid = worley(N, 18, seed + 2, 1.0, x, y)
    facet = cell_random(cid, seed + 3)
    crystal = smoothstep(0.02, 0.12, f2 - f1) * clusters
    t = 0.15 + 0.55 * crystal * (0.6 + 0.4 * facet) + 0.15 * clusters + 0.05 * fbm(N, 30, seed + 4, 2)
    rgb = ramp(np.clip(t, 0, 1), [(0, '#3a2408'), (0.35, '#8a5a1a'), (0.65, '#e8b84a'), (1, '#fff2b8')])
    mean, lum = cal('glowstone')
    glow = np.clip(t - 0.5, 0, 1)
    return Tex(match_mean(rgb, lum), norm01(0.4 + 0.5 * crystal), light='top', bump=1.3, ao=0.6,
               emissive=(glow * 0.7)[..., None] * hexrgb('#ffe08a'))


def shroomlight(seed=3610):
    x, y = warped_coords(N, 0.06, seed, freq=3)
    f1, f2, cid = worley(N, 5, seed + 1, 1.0, x, y)
    lump = smoothstep(0.0, 0.45, f2 - f1) * np.clip(1.1 - f1, 0, 1)
    spots, sv = speckles(N, 14, seed + 2, 0.2, 0.4)
    t = 0.45 + 0.35 * lump + 0.1 * fbm(N, 8, seed + 3, 3)
    rgb = ramp(np.clip(t, 0, 1), [(0, '#9a3a12'), (0.5, '#e2782a'), (1, '#ffc87a')])
    rgb = mix(rgb, hexrgb('#fff0c8'), spots * 0.7)
    mean, lum = cal('shroomlight')
    return Tex(match_mean(rgb, lum), norm01(0.5 + 0.4 * lump), light='top', bump=1.2, ao=0.55,
               emissive=((spots * 0.5 + lump * 0.15))[..., None] * hexrgb('#ffd8a0'))


def froglight(seed, path, stops, face):
    x, y = warped_coords(N, 0.05, seed, freq=3)
    membrane = fbm(N, 4, seed + 1, 4, x=x, y=y)
    f1, f2, cid = worley(N, 5, seed + 2, 0.9, x, y)
    cells = np.clip(1 - f1 / 0.7, 0, 1) * smoothstep(0.02, 0.15, f2 - f1)
    b = np.minimum(np.minimum(X, 16 - X), np.minimum(Y, 16 - Y))
    rim = 1 - smoothstep(0.6, 1.4, b)
    if face == 'top':
        r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
        rings = 0.5 + 0.5 * np.cos(r * 1.6)
        t = 0.5 + 0.12 * membrane + 0.08 * rings - 0.3 * rim + 0.25 * cells
    else:
        bands = 0.5 + 0.5 * np.cos(Y / 16 * 2 * np.pi * 3 + 0.5 * membrane)
        t = 0.5 + 0.12 * membrane + 0.06 * bands - 0.3 * rim + 0.25 * cells
    rgb = ramp(np.clip(t, 0, 1), stops)
    mean, lum = cal(path)
    return Tex(match_mean(rgb, lum * 0.92), norm01(0.5 + 0.2 * membrane + 0.3 * (1 - rim) + 0.15 * cells), light='top',
               bump=1.0, ao=0.45, emissive=((1 - rim) * 0.08)[..., None] * np.clip(np.asarray(mean) * 1.2, 0, 1))


# ------------------------------------------------------------------ bone, mushrooms, sponge, hay, honey, slime
def bone_block(seed, face):
    path = 'bone_block_' + face
    mean, lum = cal(path)
    if face == 'side':
        fib = fbm(N, (24, 2), seed, 3)
        pores = smoothstep(0.7, 0.9, fbm(N, (30, 8), seed + 1, 2))
        t = 0.6 + 0.08 * fib - 0.12 * pores + 0.05 * fbm(N, 4, seed + 2, 3)
        h = 0.5 + 0.1 * fib - 0.15 * pores
    else:
        r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
        marrow = 1 - smoothstep(3.2, 4.2, r)
        spongy = smoothstep(0.5, 0.75, fbm(N, 24, seed + 3, 3)) * marrow
        rim = smoothstep(6.6, 7.4, np.maximum(np.abs(X - 8), np.abs(Y - 8)))
        t = 0.62 - 0.18 * marrow - 0.15 * spongy + 0.05 * fbm(N, 8, seed + 4, 3) - 0.08 * rim
        h = 0.6 - 0.3 * marrow - 0.2 * spongy
    rgb = ramp(np.clip(t, 0, 1), [(0, '#8e8a74'), (0.5, '#d2ccb2'), (1, '#f2eedc')])
    return Tex(match_mean(rgb, lum), norm01(h), light='top', bump=1.1, ao=0.55)


def mushroom_skin(seed, path, stops, spots=None):
    x, y = warped_coords(N, 0.05, seed, freq=3)
    m = fbm(N, 4, seed + 1, 4, x=x, y=y)
    fine = fbm(N, 24, seed + 2, 2)
    t = 0.5 + 0.15 * m + 0.06 * fine
    rgb = ramp(np.clip(t, 0, 1), stops)
    h = 0.5 + 0.15 * m + 0.05 * fine
    if spots:
        sp, sv = speckles(N, 5, seed + 3, 0.6, 0.48)
        sp = blur(sp, 1.0)
        rgb = mix(rgb, hexrgb(spots), np.clip(sp * 1.4, 0, 1))
        h = h + 0.1 * sp
    mean, lum = cal(path)
    return Tex(match_mean(rgb, lum), norm01(h), light='top', bump=0.9, ao=0.45)


def sponge(seed, wet=False):
    path = 'sponge_wet' if wet else 'sponge'
    x, y = warped_coords(N, 0.04, seed, freq=4)
    f1, f2, cid = worley(N, 9, seed + 1, 1.0, x, y)
    hole = 1 - smoothstep(0.18, 0.32, f1)
    g1, g2, gid = worley(N, 20, seed + 2, 1.0)
    hole2 = 1 - smoothstep(0.15, 0.28, g1)
    holes = np.clip(hole + 0.7 * hole2, 0, 1)
    t = 0.6 + 0.1 * fbm(N, 6, seed + 3, 3) - 0.5 * holes
    stops = [(0, '#5a4a14'), (0.5, '#b8a032'), (1, '#e8d462')] if not wet else [(0, '#3a3412'), (0.5, '#8a7a2a'),
                                                                               (1, '#b8a84a')]
    rgb = ramp(np.clip(t, 0, 1), stops)
    mean, lum = cal(path)
    return Tex(match_mean(rgb, lum), norm01(1 - holes * 0.8 + 0.1 * fbm(N, 20, seed + 4, 2)), light='top', bump=1.6,
               ao=0.8, gloss=0.2 if wet else 0.0)


def hay(seed, face):
    path = 'hay_block_' + face
    mean, lum = cal(path)
    if face == 'side':
        segs, owner = scatter(seed, 900, (2.5, 6.0), (0.18, 0.32), angle=np.pi / 2, spread=0.12, curve=0.04, parts=2)
        tone = rng(seed + 1).uniform(0, 1, owner.max() + 1)[owner]
        vals = ramp(tone, [(0, '#8a6a1a'), (0.5, '#c8a238'), (1, '#ead070')])
        straw, cov, z = capsules(segs, vals)
        rgb = mix(np.full((N, N, 3), hexrgb('#5a4410')), straw, cov)
        bands = (np.abs(Y - 4.0) < 0.7) | (np.abs(Y - 12.0) < 0.7)
        rgb = np.where(bands[..., None], ramp(np.clip(0.5 + 0.3 * np.sin(X * 3.0), 0, 1),
                                              [(0, '#5a3a1a'), (1, '#8a5a2a')]), rgb)
        h = 0.4 + 0.4 * cov * (0.5 + 0.5 * np.clip(z, 0, 1)) + 0.25 * bands
    else:
        ends = speckles(N, 40, seed + 2, 0.6, 0.35)[0]
        t = 0.45 + 0.35 * ends + 0.08 * fbm(N, 6, seed + 3, 3)
        rgb = ramp(np.clip(t, 0, 1), [(0, '#5a4410'), (0.5, '#b8902a'), (1, '#e8c860')])
        bands = (np.abs(Y - 4.0) < 0.6) | (np.abs(Y - 12.0) < 0.6)
        rgb = np.where(bands[..., None], hexrgb('#6a4a22'), rgb)
        h = 0.4 + 0.4 * ends + 0.2 * bands
    return Tex(match_mean(rgb, lum), norm01(blur(h, 0.5)), light='top', bump=1.3, ao=0.65)


def honey(seed, face):
    path = 'honey_' + face
    mean, lum = cal(path)
    b = np.minimum(np.minimum(X, 16 - X), np.minimum(Y, 16 - Y))
    rim = 1 - smoothstep(0.8, 1.6, b)
    flow = fbm(N, (3, 6), seed, 4)
    bub, bv = speckles(N, 18, seed + 1, 0.12, 0.35)
    t = 0.55 + 0.15 * flow - 0.15 * rim + 0.2 * bub
    rgb = ramp(np.clip(t, 0, 1), [(0, '#a85a08'), (0.5, '#f0a21a'), (1, '#ffe08a')])
    alpha = np.clip(0.62 + 0.3 * rim + 0.15 * bub, 0, 1)
    return Tex(match_mean(rgb, lum), None, alpha.astype(F32), light='none')


def slime(seed=3700):
    mean, lum = cal('slime')
    b = np.minimum(np.minimum(X, 16 - X), np.minimum(Y, 16 - Y))
    rim = 1 - smoothstep(0.6, 1.2, b)
    core = rect(4, 4, 12, 12)
    core = blur(core, 3.0)
    wob = fbm(N, 4, seed, 3)
    bub, bv = speckles(N, 16, seed + 1, 0.15, 0.3)
    t = 0.55 + 0.12 * wob + 0.15 * bub - 0.1 * core + 0.15 * rim
    rgb = ramp(np.clip(t, 0, 1), [(0, '#2a7a2a'), (0.5, '#6ac25a'), (1, '#c2f2a0')])
    alpha = np.clip(0.55 + 0.35 * rim + 0.25 * core + 0.15 * bub, 0, 1)
    return Tex(match_mean(rgb, lum), None, alpha.astype(F32), light='none')


def melon(seed, face):
    path = 'melon_' + face
    mean, lum = cal(path)
    if face == 'side':
        stripes = 0.5 + 0.5 * np.cos(2 * np.pi * (X / 16 * 4 + 0.15 * fbm(N, (2, 3), seed, 3)))
        mott = fbm(N, (8, 3), seed + 1, 3)
        t = 0.45 + 0.25 * stripes + 0.08 * mott
    else:
        r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
        ang = np.arctan2(Y - 8, X - 8)
        stripes = 0.5 + 0.5 * np.cos(ang * 6 + 0.4 * fbm(N, 3, seed, 2))
        t = 0.45 + 0.22 * stripes * smoothstep(1.5, 4.0, r) - 0.25 * (r < 1.0) + 0.06 * fbm(N, 10, seed + 2, 2)
    rgb = ramp(np.clip(t, 0, 1), [(0, '#1a3a12'), (0.5, '#3f7a1f'), (1, '#86b44a')])
    return Tex(match_mean(rgb, lum), norm01(0.5 + 0.3 * t), light='top', bump=0.9, ao=0.45, gloss=0.15)


def pumpkin(seed, face, carved=None):
    path = {'side': 'pumpkin_side', 'top': 'pumpkin_top', 'off': 'pumpkin_face_off', 'on': 'pumpkin_face_on'}[face]
    mean, lum = cal(path)
    if face == 'top':
        r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
        ang = np.arctan2(Y - 8, X - 8)
        ribs = 0.5 + 0.5 * np.cos(ang * 8)
        t = 0.5 + 0.2 * ribs * smoothstep(1.5, 5, r) + 0.06 * fbm(N, 12, seed, 2)
        rgb = ramp(np.clip(t, 0, 1), [(0, '#8a3a0a'), (0.5, '#d8741a'), (1, '#f6a84a')])
        stemm = circle(8, 8, 1.6)
        rgb = mix(rgb, ramp(np.clip(0.5 + 0.3 * fbm(N, 20, seed + 1, 2), 0, 1), [(0, '#3a4a1a'), (1, '#7a8a3a')]), stemm)
        h = 0.5 + 0.3 * ribs * smoothstep(1.5, 5, r) + 0.3 * stemm
        return Tex(match_mean(rgb, lum), norm01(h), light='top', bump=1.1, ao=0.5)
    ribs = 0.5 + 0.5 * np.cos(2 * np.pi * X / 16 * 4)
    t = 0.5 + 0.22 * ribs + 0.06 * fbm(N, (6, 2), seed, 3)
    rgb = ramp(np.clip(t, 0, 1), [(0, '#8a3a0a'), (0.5, '#d8741a'), (1, '#f6a84a')])
    h = 0.4 + 0.45 * ribs
    em = None
    if face in ('off', 'on'):
        eyes = np.clip(polygon([(3.0, 6.0), (6.4, 6.0), (4.7, 3.6)]) + polygon([(9.6, 6.0), (13.0, 6.0), (11.3, 3.6)]), 0, 1)
        mouth = polygon([(3.0, 9.6), (13.0, 9.6), (12.0, 12.8), (10.2, 11.6), (8.0, 13.0), (5.8, 11.6), (4.0, 12.8)])
        hole = np.clip(eyes + mouth, 0, 1)
        inside = hexrgb('#2a1606') if face == 'off' else hexrgb('#ffd04a')
        rgb = mix(rgb, inside, hole)
        rimc = np.clip(blur(hole, 1.2) * 2.5 - hole, 0, 1)
        rgb = mix(rgb, hexrgb('#e8b07a') if face == 'off' else hexrgb('#ffe8a0'), rimc * 0.6)
        h = h * (1 - hole) + 0.05
        if face == 'on':
            em = (hole * 0.6)[..., None] * hexrgb('#ffc24a')
    return Tex(match_mean(rgb, lum), norm01(h), light='top', bump=1.0, ao=0.5, emissive=em)


def cobweb(seed=3720):
    cv = Canvas(wrap=False)
    r = rng(seed)
    c = np.full(3, 0.95, F32)
    cx, cy = 8 + r.uniform(-1, 1), 8 + r.uniform(-1, 1)
    spokes = 9
    angs = (np.arange(spokes) + r.uniform(-0.25, 0.25, spokes)) * 2 * np.pi / spokes
    for a in angs:
        cv.stroke([(cx, cy), (cx + 11 * np.cos(a), cy + 11 * np.sin(a))], [0.34, 0.26], 0.5, rgb=c)
    for k in range(1, 7):
        rr = k * 1.15 + r.uniform(-0.2, 0.2)
        pts = [(cx + rr * np.cos(a) * r.uniform(0.92, 1.05), cy + rr * np.sin(a) * r.uniform(0.92, 1.05)) for a in angs]
        pts.append(pts[0])
        cv.stroke(pts, [0.26] * len(pts), 0.6, rgb=c * 0.97)
    return finish(cv, 'web', back=1.0, shadow=0.0)


# ------------------------------------------------------------------ stacked spikes and crystal buds
def spike(seed, path, stops, flip=False):
    """Pointed dripstone / sulfur spike segment: our material inside the stacking silhouette."""
    m = mask_of(path, smooth=True).astype(F32)
    flow = fbm(N, (6, 1), seed, 3)
    t = 0.5 + 0.15 * flow + 0.1 * np.cos(np.pi * (X - 8) / 6) + 0.05 * fbm(N, 20, seed + 1, 2)
    rgb = ramp(np.clip(t, 0, 1), stops)
    mean, lum = cal(path)
    rgb = match_mean(rgb, lum, m > 0.5)
    return Tex(rgb, norm01(0.5 + 0.3 * np.cos(np.pi * (X - 8) / 8) + 0.1 * flow), m, light='top', bump=1.0, ao=0.4,
               cutout=True)


def crystal_bud(seed, path, count, height, width):
    cv = Canvas(wrap=False)
    r = rng(seed)
    for k in range(count):
        x = 8 + r.normal(0, 2.0) if count > 1 else 8.0
        ang = r.uniform(-0.45, 0.45) if count > 1 else 0.0
        H = height * r.uniform(0.7, 1.0)
        W = width * r.uniform(0.8, 1.1)
        c, s = np.cos(ang), np.sin(ang)
        tip = (x + s * H, 16.2 - c * H)
        pl = (x - c * W / 2, 16.2 - s * W / 2)
        pr = (x + c * W / 2, 16.2 + s * W / 2)
        body = polygon([pl, (pl[0] + s * H * 0.75, pl[1] - c * H * 0.75), tip, (pr[0] + s * H * 0.75, pr[1] - c * H * 0.75), pr])
        ix = (slice(None), slice(None))
        u = ((X - x) * c + (Y - 16.2) * s) / (W / 2)
        shade = np.where(u < 0, 0.75, 1.0) * (0.85 + 0.15 * np.clip(1 - np.abs(u), 0, 1))
        col = ramp(np.clip(0.5 + 0.3 * shade - 0.2 + 0.1 * fbm(N, 8, seed + k, 2), 0, 1),
                   [(0, '#4a2a7a'), (0.5, '#9a6ad6'), (1, '#e6d2ff')])
        cv.put(ix, body, col, k / count)
    return finish(cv, path, back=0.8, shadow=0.3)


def resin_clump(seed=3730):
    cv = Canvas(wrap=False)
    r = rng(seed)
    for k in range(9):
        cx, cy = r.uniform(2, 14), r.uniform(2, 14)
        disc(cv, cx, cy, r.uniform(0.7, 1.3), hexrgb('#e2781c') * r.uniform(0.85, 1.15), k / 9)
    return finish(cv, 'resin_clump')


# ------------------------------------------------------------------ registration
def register(R):
    crim = [(0, '#3a0608'), (0.4, '#7a0f14'), (0.75, '#a8242a'), (1, '#d24a4a')]
    warp = [(0, '#0a2f2c'), (0.4, '#13615a'), (0.75, '#1f8f84'), (1, '#4ac4b4')]
    R.block('crimson_nylium_top', lambda v: nylium_top(3800, 'crimson_nylium_top', crim))
    R.block('warped_nylium_top', lambda v: nylium_top(3801, 'warped_nylium_top', warp))
    from recipes.minerals import netherrack
    R.block('crimson_nylium_side', lambda v: layer_side(3802, nylium_top(3800, 'crimson_nylium_top', crim),
                                                        netherrack(3803, 0.22), 0.2, strands=20,
                                                        strand_rgb=hexrgb('#8a1a1e'), target=0.17))
    R.block('warped_nylium_side', lambda v: layer_side(3804, nylium_top(3801, 'warped_nylium_top', warp),
                                                       netherrack(3805, 0.22), 0.2, strands=20,
                                                       strand_rgb=hexrgb('#1f7f74'), target=0.25))
    R.block('soul_sand', lambda v: soul_ground(3806, 'soul_sand'))
    R.block('soul_soil', lambda v: soul_ground(3807, 'soul_soil', faces=False))
    R.block('nether_wart_block', lambda v: wart_block(3808, 'nether_wart_block', [(0, '#2a0202'), (0.5, '#6e0808'),
                                                                                 (1, '#b21e1a')]))
    R.block('warped_wart_block', lambda v: wart_block(3809, 'warped_wart_block', warp))
    R.block('glowstone', lambda v: glowstone())
    R.block('shroomlight', lambda v: shroomlight())
    for name, stops in (('ochre', [(0, '#a8823a'), (0.5, '#f2d48a'), (1, '#fffae2')]),
                        ('verdant', [(0, '#5a8a4a'), (0.5, '#c2e2a2'), (1, '#f2ffe8')]),
                        ('pearlescent', [(0, '#a27aa2'), (0.5, '#ecd2e6'), (1, '#fff6fc')])):
        for face in ('side', 'top'):
            p = f'{name}_froglight_{face}'
            R.block(p, lambda v, p=p, stops=stops, face=face: froglight(3810, p, stops, face))
    R.block('bone_block_side', lambda v: bone_block(3820, 'side'))
    R.block('bone_block_top', lambda v: bone_block(3821, 'top'))
    R.block('mushroom_block_skin_red', lambda v: mushroom_skin(3822, 'mushroom_block_skin_red',
                                                              [(0, '#7a0e0a'), (0.5, '#b8221a'), (1, '#d8443a')],
                                                              spots='#efe6d8'))
    R.block('mushroom_block_skin_brown', lambda v: mushroom_skin(3823, 'mushroom_block_skin_brown',
                                                                [(0, '#5a3a24'), (0.5, '#8a6448'), (1, '#b08a6a')]))
    R.block('mushroom_block_skin_stem', lambda v: mushroom_skin(3824, 'mushroom_block_skin_stem',
                                                               [(0, '#a8a090'), (0.5, '#d2cab6'), (1, '#efe8d8')]))
    R.block('mushroom_block_inside', lambda v: mushroom_skin(3825, 'mushroom_block_inside',
                                                            [(0, '#a88a6a'), (0.5, '#d2b48e'), (1, '#ecd4b2')]))
    R.block('sponge', lambda v: sponge(3826))
    R.block('sponge_wet', lambda v: sponge(3827, wet=True))
    R.block('hay_block_side', lambda v: hay(3828, 'side'))
    R.block('hay_block_top', lambda v: hay(3829, 'top'))
    for face in ('side', 'top', 'bottom'):
        R.block(f'honey_{face}', lambda v, face=face: honey(3830, face))
    R.block('slime', lambda v: slime())
    R.block('melon_side', lambda v: melon(3831, 'side'))
    R.block('melon_top', lambda v: melon(3832, 'top'))
    for face in ('side', 'top', 'off', 'on'):
        p = {'side': 'pumpkin_side', 'top': 'pumpkin_top', 'off': 'pumpkin_face_off', 'on': 'pumpkin_face_on'}[face]
        R.block(p, lambda v, face=face: pumpkin(3833, face))
    R.block('web', lambda v: cobweb(), cutout=True)
    drip = [(0, '#5e4636'), (0.5, '#8b6f5c'), (1, '#b89b85')]
    sulf = [(0, '#9a8a3a'), (0.5, '#d4c254'), (1, '#f2e68a')]
    for d in ('down', 'up'):
        for part in ('base', 'frustum', 'middle', 'tip', 'merge'):
            p = f'pointed_dripstone_{d}_{part}'
            R.block(p, lambda v, p=p: spike(3840, p, drip), cutout=True)
        for part in ('base', 'frustum', 'middle', 'tip', 'tip_merge'):
            p = f'sulfur_spike_{d}_{part}'
            R.block(p, lambda v, p=p: spike(3841, p, sulf), cutout=True)
    R.block('amethyst_cluster', lambda v: crystal_bud(3850, 'amethyst_cluster', 5, 11.0, 3.0), cutout=True)
    R.block('large_amethyst_bud', lambda v: crystal_bud(3851, 'large_amethyst_bud', 3, 8.0, 2.6), cutout=True)
    R.block('medium_amethyst_bud', lambda v: crystal_bud(3852, 'medium_amethyst_bud', 3, 5.5, 2.2), cutout=True)
    R.block('small_amethyst_bud', lambda v: crystal_bud(3853, 'small_amethyst_bud', 2, 3.5, 2.0), cutout=True)
    R.block('resin_clump', lambda v: resin_clump(), cutout=True)
    R.block('pale_moss', lambda v: moss(3860, stops=[(0, '#2b3129'), (0.4, '#4e5a4a'), (0.75, '#76826f'),
                                                     (1, '#a1ab96')], target=0.43))

    def red_shrub(v):
        from recipes.plants import dead_bush
        t = finish(dead_bush(3861), 'red_shrub')
        return t.but(albedo=match_mean(np.clip(t.albedo * np.array([1.6, 0.5, 0.4], F32), 0, 1), 0.21,
                                       t.alpha > 0.5))
    R.block('red_shrub', red_shrub, cutout=True)

    def glowing_obsidian(v):
        from recipes.terrain import obsidian
        o = obsidian(3862)
        veins = smoothstep(0.85, 0.97, ridged(N, 4, 3863, 4, sharp=2.0))
        rgb = mix(o.albedo * np.array([2.2, 0.4, 0.5], F32), hexrgb('#ff3a2a'), veins)
        return o.but(albedo=match_mean(np.clip(rgb, 0, 1), 0.08), emissive=(veins * 0.4)[..., None] * hexrgb('#ff4a2a'))
    R.block('glowing_obsidian', glowing_obsidian)

    def dragon_egg(v):
        x, y = warped_coords(N, 0.05, 3864, freq=3)
        m = fbm(N, 4, 3865, 4, x=x, y=y)
        sp, sv = speckles(N, 20, 3866, 0.12, 0.3)
        rgb = ramp(np.clip(0.4 + 0.2 * m, 0, 1), [(0, '#06040a'), (0.6, '#16101e'), (1, '#2e2238')])
        rgb = mix(rgb, hexrgb('#6a3a8a'), sp * 0.7)
        return Tex(match_mean(rgb, 0.045), norm01(0.5 + 0.2 * m), light='top', bump=0.8, ao=0.3, gloss=0.3)
    R.block('dragon_egg', dragon_egg)

    def dried_kelp(face, part=''):
        path = f'dried_kelp_{face}' + (f'_{part}' if part else '')
        mean, lum = cal(path)
        if face == 'side':
            wrap = fbm(N, (3, 14), 3870 + (part == 'b'), 3)
            band = (np.abs(Y - 3.0) < 0.8) | (np.abs(Y - 13.0) < 0.8)
            t = 0.45 + 0.2 * wrap - 0.2 * band
            h = 0.5 + 0.2 * wrap + 0.2 * band
        else:
            r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
            ang = np.arctan2(Y - 8, X - 8)
            spiral = 0.5 + 0.5 * np.sin(r * 2.2 - ang)
            t = 0.4 + 0.3 * spiral + 0.05 * fbm(N, 10, 3872, 2)
            h = 0.5 + 0.3 * spiral
        rgb = ramp(np.clip(t, 0, 1), [(0, '#0f140a'), (0.5, '#2a3418'), (1, '#4a5a2a')])
        return Tex(match_mean(rgb, lum), norm01(h), light='top', bump=1.2, ao=0.6, gloss=0.15)
    R.block('dried_kelp_side_a', lambda v: dried_kelp('side', 'a'))
    R.block('dried_kelp_side_b', lambda v: dried_kelp('side', 'b'))
    R.block('dried_kelp_top', lambda v: dried_kelp('top'))

    def honeycomb(v):
        cw, rh = 16 / 5, 16 / 6          # cell width and row pitch chosen so the hex lattice tiles exactly
        row = np.floor(Y / rh)
        col = np.floor(X / cw - 0.5 * (row % 2))
        best = np.full((N, N), 1e9, F32)
        second = np.full((N, N), 1e9, F32)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rrow = row + dr
                ccol = col + dc
                cx = (ccol + 0.5 + 0.5 * (rrow % 2)) * cw
                cy = (rrow + 0.5) * rh
                dx = (X - cx + 8) % 16 - 8
                dy = (Y - cy + 8) % 16 - 8
                d = np.sqrt(dx * dx + (dy * 1.08) ** 2)
                second = np.where(d < best, best, np.minimum(second, d))
                best = np.minimum(best, d)
        size = cw / 1.7
        wall = 1 - smoothstep(0.06, 0.25, second - best)
        cell = np.clip(1 - best / (size * 0.95), 0, 1)
        t = 0.42 + 0.32 * cell - 0.3 * wall + 0.05 * fbm(N, 12, 3874, 2)
        rgb = ramp(np.clip(t, 0, 1), [(0, '#a8620a'), (0.5, '#e8a22a'), (1, '#ffd87a')])
        mean, lum = cal('honeycomb')
        return Tex(match_mean(rgb, lum), norm01(0.5 + 0.35 * wall - 0.25 * cell), light='top', bump=1.3, ao=0.6,
                   gloss=0.3)
    R.block('honeycomb', honeycomb)
