"""More flora: azaleas, dripleaves, cave vines, roots, lichens, bamboo, mangrove, aquatic plants (animated
kelp and seagrass), corals, chorus, and nether vegetation."""
import numpy as np

from engine.noise import F32, fbm, blur, smoothstep, rng, worley, warped_coords, norm01, ridged
from recipes.terrain import speckles
from engine.color import ramp, mix, match_mean, hexrgb, vary
from engine.material import Tex, MASTER
from engine.draw import X, Y
from recipes.foliage import Canvas, draw_leaf, depth_shade, cal
from recipes.plants import (blade, stem, leaf_at, petals, disc, finish, mask_of, path_points, green)

N = MASTER
AZALEA = [(0, '#2f5517'), (0.5, '#4f7a24'), (1, '#77a23a')]


def masked(path, rgb, *, light='top', h=None, bump=0.8, target=None, smooth=False):
    """Our colour inside the vanilla UV-island silhouette (model-mapped textures)."""
    m = mask_of(path, smooth=smooth).astype(F32)
    mean, lum, _ = cal(path)
    rgb = match_mean(rgb, target if target is not None else lum, m > 0.5)
    hh = h if h is not None else 0.5 + 0.12 * fbm(N, 8, len(path), 3)
    return Tex(rgb, hh, m, light=light, bump=bump, ao=0.3, cutout=True, sharpen=0.25)


def leafy_rgb(seed, stops=AZALEA, size=(1.2, 1.8), count=260, flowers=None):
    """A dense leafy surface (full tile) used for bush faces."""
    r = rng(seed)
    cv = Canvas()
    base = ramp(np.clip(0.3 + 0.2 * fbm(N, 8, seed, 3), 0, 1), stops)
    cv.rgb[:] = base * 0.55
    cv.a[:] = 1
    for k in range(count):
        cx, cy = r.uniform(0, 16), r.uniform(0, 16)
        L = r.uniform(*size)
        draw_leaf(cv, cx, cy, r.uniform(0, 2 * np.pi), L, L * 0.8, k / count, r.uniform(0.7, 1.0), kind='round',
                  colour=ramp(np.array([r.uniform(0.2, 1)]), stops)[0])
    if flowers:
        for k in range(flowers[0]):
            cx, cy = r.uniform(0, 16), r.uniform(0, 16)
            petals(cv, cx, cy, 5, 0.75, 0.65, hexrgb(flowers[1]) * r.uniform(0.9, 1.05), 1.0 + k * 1e-3,
                   kind='round', r=r)
            disc(cv, cx, cy, 0.22, hexrgb('#f6e3ee'), 1.01)
    depth_shade(cv, 0.65, 0.4)
    return cv.rgb


# ------------------------------------------------------------------ azalea
def azalea_side(seed, flowers=None, path='azalea_side'):
    rgb = leafy_rgb(seed, flowers=flowers)
    from recipes.terrain import hang_edge
    edge = hang_edge(seed, 0.58, wave=0.05, lobes=6, lobe_depth=(0.04, 0.12), lobe_width=(0.05, 0.12))
    a = (Y / 16 < edge[None, :]).astype(F32)
    mean, lum, _ = cal(path)
    rgb = match_mean(rgb, lum, a > 0.5)
    return Tex(rgb, None, a, light='none', cutout=True, sharpen=0.3)


def azalea_top(seed, flowers=None, path='azalea_top'):
    rgb = leafy_rgb(seed, flowers=flowers)
    mean, lum, _ = cal(path)
    return Tex(match_mean(rgb, lum), None, None, light='none', sharpen=0.3)


def azalea_plant(seed, path='azalea_plant'):
    r = rng(seed)
    cv = Canvas(wrap=False)
    tw = hexrgb('#5b4632')
    for k in range(6):
        pts, dirs = stem(cv, 8 + r.normal(0, 1.2), 16.3, r.uniform(-1.0, 1.0), r.uniform(8, 14), 0.5,
                         r.uniform(-0.5, 0.5), 0.1, tw)
        for (px, py) in pts[3:]:
            for j in range(2):
                ll = r.uniform(1.4, 2.0)
                leaf_at(cv, px + r.uniform(-1.2, 1.2), py + r.uniform(-1, 1), r.uniform(-3, 3), ll, ll * 0.75,
                        0.5 + r.uniform(0, 0.4), green(r, 0.2, 1.0, AZALEA), kind='round')
    return finish(cv, path)


# ------------------------------------------------------------------ dripleaf
def dripleaf_top(seed, path, quadrant=False):
    cx, cy, rad = (8.0, 8.0, 8.2) if not quadrant else (4.0, 4.0, 4.1)
    d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    ang = np.arctan2(Y - cy, X - cx)
    veins = np.abs(((ang * 7 / (2 * np.pi)) % 1.0) - 0.5) < 0.06
    t = 0.55 + 0.2 * (1 - d / rad) - 0.12 * veins + 0.06 * fbm(N, 10, seed, 3)
    rgb = ramp(np.clip(t, 0, 1), [(0, '#3a5f1a'), (0.5, '#5f8a2a'), (1, '#86b046')])
    wave = rad * (0.96 + 0.04 * np.sin(ang * 6))
    a = (d < wave).astype(F32)
    if not quadrant:
        a = np.maximum(a, ((X > 0.5) & (X < 15.5) & (Y > 0.5) & (Y < 15.5) & (d < rad * 1.15)).astype(F32))
    m = mask_of(path).astype(F32)
    a = a * np.maximum(m, blur(m, 1.0) > 0.5)
    mean, lum, _ = cal(path)
    return Tex(match_mean(rgb, lum, a > 0.5), 0.5 + 0.2 * (1 - d / rad) - 0.1 * veins, a, light='top', bump=1.0,
               ao=0.3, cutout=True)


# ------------------------------------------------------------------ cave vines, roots, lichen, spore blossom
def cave_vine(seed, berries=False, head=False, path='cave_vines_body'):
    r = rng(seed)
    cv = Canvas(wrap=False)
    for k, x in enumerate((5.0, 11.0)):
        x += r.uniform(-0.6, 0.6)
        y_end = 14.0 if head else 17.0
        pts = [(x + 0.7 * np.sin(t * 0.8 + k * 2), t) for t in np.linspace(-1, y_end, 10)]
        cv.stroke(pts, [0.45] * 10, 0.2, rgb=hexrgb('#4b6a22'))
        for j in range(7):
            px, py = pts[r.integers(1, 9)]
            ll = r.uniform(1.6, 2.4)
            leaf_at(cv, px, py, r.choice([-1, 1]) * r.uniform(1.0, 2.2), ll, ll * 0.55, 0.4 + 0.01 * j,
                    green(r, 0.2, 0.9), kind='ovate')
        if berries:
            for j in range(2):
                px, py = pts[r.integers(3, 9)]
                disc(cv, px + r.uniform(-1.2, 1.2), py + 0.8, 0.85, hexrgb('#f2a93a'), 0.9 + 0.01 * j)
    t = finish(cv, path)
    if berries:
        rgbm = t.albedo
        warm = (rgbm[..., 0] > rgbm[..., 1] * 1.25) & (t.alpha > 0.5)
        t = t.but(emissive=(warm * 0.35)[..., None] * hexrgb('#ffcf6a'))
    return t


def hanging_roots(seed, path='hanging_roots'):
    r = rng(seed)
    cv = Canvas(wrap=False)
    for k in range(14):
        x = r.uniform(1, 15)
        L = r.uniform(5, 11)
        pts, dirs = path_points(x, -0.5, np.pi + r.uniform(-0.3, 0.3), L, r.uniform(-0.6, 0.6), steps=8)
        cv.stroke(pts, np.linspace(0.45, 0.12, 8), r.uniform(0, 1), rgb=hexrgb('#b48a6e') * r.uniform(0.85, 1.1))
    return finish(cv, path)


def lichen(seed, path='glow_lichen'):
    r = rng(seed)
    cv = Canvas(wrap=False)
    for k in range(16):
        cx, cy = r.uniform(1, 15), r.uniform(1, 15)
        for j in range(r.integers(4, 8)):
            a = r.uniform(0, 2 * np.pi)
            draw_leaf(cv, cx, cy, a, r.uniform(0.8, 1.6), r.uniform(0.6, 1.0), 0.3 + 0.01 * j, r.uniform(0.8, 1.05),
                      kind='round', colour=hexrgb('#8fa79a'))
    t = finish(cv, path)
    spark = (fbm(N, 30, seed, 2) > 0.45) & (t.alpha > 0.5)
    return t.but(emissive=(spark * 0.12)[..., None] * hexrgb('#c8ffe8'))


def spore_blossom(seed, path):
    r = rng(seed)
    cv = Canvas(wrap=False)
    if path == 'spore_blossom':
        for k in range(9):
            a = -np.pi / 2 + (k - 4) * 0.36 + r.uniform(-0.08, 0.08)
            draw_leaf(cv, 8, 16.2, a, r.uniform(9.5, 12.0), r.uniform(3.0, 3.8), k / 10, r.uniform(0.85, 1.05),
                      kind='ovate', colour=hexrgb('#d5579a'))
    else:
        for k in range(10):
            a = r.uniform(0, 2 * np.pi)
            draw_leaf(cv, 8, 8, a, r.uniform(5.5, 7.5), r.uniform(2.6, 3.4), k / 10, r.uniform(0.75, 1.05),
                      kind='ovate', colour=green(r, 0.4, 1.0))
    t = finish(cv, path)
    m = mask_of(path).astype(F32)
    a = (t.alpha * np.clip(blur(m, 1.5) * 2, 0, 1) > 0.5).astype(F32)
    return t.but(alpha=a)


# ------------------------------------------------------------------ mangrove
def mangrove_roots(seed, face, path):
    r = rng(seed)
    cv = Canvas()
    col = hexrgb('#4a3b26')
    n = 7 if face == 'side' else 9
    for k in range(n):
        if face == 'side':
            x = (k + 0.5) * 16 / n + r.uniform(-0.5, 0.5)
            pts = [(x + 0.8 * np.sin(t * 0.5 + k), t) for t in np.linspace(-1, 17, 10)]
        else:
            a = r.uniform(0, np.pi)
            cx, cy = r.uniform(0, 16), r.uniform(0, 16)
            pts = [(cx + np.cos(a) * t + 0.5 * np.sin(t), cy + np.sin(a) * t) for t in np.linspace(-9, 9, 12)]
        cv.stroke(pts, [r.uniform(1.0, 1.5)] * len(pts), k / n, rgb=col * r.uniform(0.85, 1.15), shade_along=0.0)
    depth_shade(cv, 0.6, 0.5)
    mean, lum, _ = cal(path)
    a = cv.a
    return Tex(match_mean(cv.rgb, lum, a > 0.5), None, a, light='none', cutout=True, sharpen=0.3)


def muddy_roots(seed, face, path):
    from recipes.terrain import mud
    m = mud(seed)
    roots = mangrove_roots(seed + 1, face, 'mangrove_roots_' + face)
    rgb = mix(m.albedo * 1.1, roots.albedo, roots.alpha)
    h = np.maximum(m.height * 0.5, roots.alpha * 0.8)
    mean, lum, _ = cal(path)
    return Tex(match_mean(rgb, lum), h, light='top', bump=1.4, ao=0.6)


def propagule(seed, path, hanging=False):
    cv = Canvas(wrap=False)
    pod = hexrgb('#6f9a3a')
    if hanging:
        cv.stroke([(8, -0.5), (8, 2.5)], [0.4, 0.4], 0.1, rgb=hexrgb('#5a7a2a'))
        cv.stroke([(8, 2.5), (8.2, 9.0), (8.0, 14.5)], [1.0, 1.1, 0.5], 0.2, rgb=pod)
        for side in (-1, 1):
            leaf_at(cv, 8, 2.6, side * 0.9 + np.pi, 2.4, 1.2, 0.3, hexrgb('#7aa63a'), kind='ovate')
    else:
        cv.stroke([(8, 16.5), (8.1, 11), (8, 8)], [0.9, 0.9, 0.6], 0.2, rgb=pod)
        for side in (-1, 1):
            leaf_at(cv, 8, 8.2, side * 0.8, 3.0, 1.5, 0.3, hexrgb('#7aa63a'), kind='ovate')
    return finish(cv, path)


# ------------------------------------------------------------------ bamboo plant
def bamboo_stem_tex(seed, path='bamboo_stem'):
    t = 0.5 + 0.25 * np.cos(2 * np.pi * X / 16 * 2) + 0.05 * fbm(N, (30, 2), seed, 2)
    node = np.exp(-((Y - 3.5) / 0.35) ** 2)
    rgb = ramp(np.clip(t - 0.25 * node, 0, 1), [(0, '#3a5a10'), (0.5, '#5f8a1c'), (1, '#86b032')])
    mean, lum, _ = cal(path)
    return Tex(match_mean(rgb, lum), 0.5 + 0.3 * t + 0.2 * node, light='top', bump=1.2, ao=0.5)


def bamboo_leaves(seed, path, count):
    r = rng(seed)
    cv = Canvas(wrap=False)
    for k in range(count):
        x, y = r.uniform(3, 13), r.uniform(3, 13)
        leaf_at(cv, x, y, r.uniform(-np.pi, np.pi), r.uniform(4.0, 6.5), r.uniform(1.0, 1.4), k / max(count, 1),
                ramp(np.array([r.uniform(0.3, 1.0)]), [(0, '#4a7a1a'), (1, '#8fbf3a')])[0])
    return finish(cv, path)


# ------------------------------------------------------------------ pale moss
def pale_hanging_moss(seed, path, tip=False):
    r = rng(seed)
    cv = Canvas(wrap=False)
    for k in range(18):
        x = r.uniform(1, 15)
        L = r.uniform(8, 15) if tip else 18
        pts, dirs = path_points(x, -0.5, np.pi + r.uniform(-0.15, 0.15), L, r.uniform(-0.3, 0.3), steps=10)
        cv.stroke(pts, np.linspace(0.8, 0.25 if tip else 0.6, 10), r.uniform(0, 1),
                  rgb=hexrgb('#8a9186') * r.uniform(0.8, 1.15))
    return finish(cv, path)


def pale_carpet_side(seed, path, tip=False):
    from recipes.terrain import hang_edge
    base = 0.18 if tip else 0.45
    edge = hang_edge(seed, base, wave=0.04, lobes=8, lobe_depth=(0.04, 0.15), lobe_width=(0.03, 0.07))
    a = (Y / 16 < edge[None, :]).astype(F32)
    if tip:
        a = a * (Y > 6.0)
        edge2 = hang_edge(seed + 1, 0.55, wave=0.04, lobes=8, lobe_depth=(0.04, 0.15))
        a = ((Y / 16 > 0.38) & (Y / 16 < edge2[None, :])).astype(F32)
    rgb = ramp(np.clip(0.5 + 0.3 * fbm(N, (12, 4), seed, 3), 0, 1), [(0, '#565d52'), (0.5, '#7b8377'), (1, '#a1a99c')])
    mean, lum, _ = cal(path)
    return Tex(match_mean(rgb, lum, a > 0.5), 0.5 + 0.2 * fbm(N, (12, 4), seed, 3), a, light='top', bump=1.0,
               cutout=True)


# ------------------------------------------------------------------ aquatic (animated)
def kelp(frame, frames, seed, path, top=False, bulb=False):
    r = rng(seed)
    cv = Canvas(wrap=not top)
    ph = 2 * np.pi * frame / frames
    col = [(0, '#3d5f1c'), (0.5, '#5a8228'), (1, '#7fa83a')]
    sway = lambda y: 0.9 * np.sin(ph + 2 * np.pi * y / 16)
    pts = [(8 + sway(y), y) for y in np.linspace(17 if not top else 16.5, -1 if not top else 4.0, 12)]
    cv.stroke(pts, [0.7] * 12, 0.2, rgb=hexrgb('#4f7524'))
    for k in range(5 if not top else 3):
        y = r.uniform(1, 15) if not top else r.uniform(6, 14)
        side = (-1) ** k
        x0 = 8 + sway(y)
        L = r.uniform(4.5, 6.5)
        leaf_at(cv, x0, y, side * (1.2 + 0.25 * np.sin(ph + k)), L, L * 0.38, 0.4 + 0.01 * k,
                ramp(np.array([r.uniform(0.3, 1.0)]), col)[0], kind='lanceolate')
    if bulb:
        disc(cv, 8 + sway(5), 5.0, 1.2, hexrgb('#9ab84a'), 0.9)
    return finish(cv, path, sharpen=0.2)


def seagrass(frame, frames, seed, path, tall=None):
    r = rng(seed)
    cv = Canvas(wrap=False)
    ph = 2 * np.pi * frame / frames
    y0 = 16.4 if tall != 'top' else 16.6
    n = 9 if tall is None else 11
    for k in range(n):
        x = 2 + 12 * (k + 0.5) / n + r.uniform(-0.5, 0.5)
        L = r.uniform(8, 14) if tall != 'bottom' else 17
        if tall == 'top':
            L = r.uniform(5, 12)
        bend = 0.5 * np.sin(ph + k * 0.7)
        blade(cv, x, y0, r.uniform(-0.2, 0.2) + 0.25 * np.sin(ph + k), L, r.uniform(0.6, 0.9), bend, r.uniform(0, 1),
              ramp(np.array([r.uniform(0.2, 1.0)]), [(0, '#2d5a12'), (1, '#5f9a24')])[0],
              taper=0.85 if tall != 'bottom' else 0.25)
    return finish(cv, path, sharpen=0.2)


# ------------------------------------------------------------------ corals
CORALS = {'blue': '#3c5fd6', 'pink': '#d9609e', 'purple': '#a33ad0', 'red': '#c72c3a', 'yellow': '#e8cf3a'}


def coral_colour(name, dead):
    return hexrgb('#9a958e') if dead else hexrgb(CORALS[name])


def coral_block(seed, name, dead, path):
    """Living rock of coral: meandering ridges (brain-like) studded with soft polyp cups."""
    x, y = warped_coords(N, 0.06, seed, freq=3)
    ridges = ridged(N, 6, seed + 1, 3, sharp=1.6)
    f1, f2, cid = worley(N, 9, seed + 2, 1.0, x, y)
    cup = smoothstep(0.3, 0.05, f1)
    t = 0.45 + 0.3 * ridges + 0.1 * fbm(N, 20, seed + 3, 2) - 0.18 * cup
    c = coral_colour(name, dead)
    rgb = ramp(np.clip(t, 0, 1), [(0, c * 0.55), (0.6, c), (1, np.clip(c * 1.25 + 0.05, 0, 1))])
    if dead:
        rgb = vary(rgb, ds=-0.6)
    h = 0.5 + 0.35 * ridges - 0.25 * cup + 0.05 * fbm(N, 30, seed + 4, 2)
    mean, lum, _ = cal(path)
    return Tex(match_mean(rgb, lum), norm01(h), light='top', bump=1.3, ao=0.65)


def coral_plant(seed, name, dead, path):
    r = rng(seed)
    cv = Canvas(wrap=False)
    c = coral_colour(name, dead)

    def branch(x, y, ang, L, w, depth):
        pts, dirs = stem(cv, x, y, ang, L, w, r.uniform(-0.4, 0.4), 0.1 * depth + r.uniform(0, 0.05),
                         c * r.uniform(0.85, 1.15), steps=6)
        if depth < 2:
            for k in range(2):
                i = r.integers(2, 6)
                branch(pts[i][0], pts[i][1], dirs[i] + r.choice([-1, 1]) * r.uniform(0.3, 0.8), L * 0.65, w * 0.75,
                       depth + 1)
        else:
            disc(cv, pts[-1][0], pts[-1][1], w * 0.7, np.clip(c * 1.25, 0, 1), 0.5 + 0.01 * depth)
    for k in range(4):
        branch(8 + r.normal(0, 2.0), 16.3, r.uniform(-0.6, 0.6), r.uniform(6, 9), 1.1, 0)
    return finish(cv, path)


def coral_fan(seed, name, dead, path):
    r = rng(seed)
    cv = Canvas(wrap=False)
    c = coral_colour(name, dead)
    for k in range(11):
        a = -np.pi / 2 + (k - 5) * 0.2 + r.uniform(-0.05, 0.05)
        L = r.uniform(8, 11)
        draw_leaf(cv, 8, 16.5, a, L, r.uniform(2.0, 2.8), k / 12, r.uniform(0.85, 1.05), kind='ovate', colour=c,
                  veins=1.0)
    t = finish(cv, path)
    holes = (fbm(N, 14, seed, 2) > 0.35) & (Y < 12)
    return t.but(alpha=(t.alpha * (~holes)).astype(F32))


# ------------------------------------------------------------------ chorus
def chorus(seed, path, flower=False, dead=False):
    """Fleshy, lumpy chorus tissue with pale speckles; flowers open into a six-lobed bloom."""
    x, y = warped_coords(N, 0.08, seed, freq=3)
    lumps = fbm(N, 5, seed + 1, 4, x=x, y=y)
    fine = fbm(N, 22, seed + 2, 3)
    veins = smoothstep(0.88, 0.97, ridged(N, 4, seed + 3, 3, sharp=2.5))
    t = 0.5 + 0.2 * lumps + 0.08 * fine - 0.12 * veins
    if flower:
        c = [(0, '#5a3a5a'), (0.6, '#a07aa2'), (1, '#ecd8ea')] if not dead else [(0, '#3a2638'), (1, '#7a5a76')]
        ang = np.arctan2(Y - 8, X - 8)
        rr = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
        petal = (np.cos(ang * 3) * 0.5 + 0.5) * smoothstep(8.5, 3.0, rr)
        t = t + 0.18 * petal - 0.15 * smoothstep(2.2, 1.2, rr)
    else:
        c = [(0, '#3a2238'), (0.6, '#6a4a68'), (1, '#a0809e')]
    rgb = ramp(np.clip(t, 0, 1), c)
    sp, _ = speckles(N, 26, seed + 4, 0.1, 0.3)
    rgb = mix(rgb, np.clip(ramp(np.array([0.95]), c)[0] * 1.1, 0, 1), sp * 0.5)
    mean, lum, _ = cal(path)
    return Tex(match_mean(rgb, lum), norm01(0.5 + 0.3 * lumps + 0.05 * fine - 0.1 * veins), light='top', bump=1.3,
               ao=0.6)


# ------------------------------------------------------------------ nether vegetation
def nether_fungus(seed, path, cap, stem_c='#d8c6a0', spots=None):
    r = rng(seed)
    cv = Canvas(wrap=False)
    stem(cv, 8, 16.3, 0.0, 7.5, 1.2, r.uniform(-0.2, 0.2), 0.1, hexrgb(stem_c))
    ix, xs, ys = cv.window(8, 8.5, 5.0)
    m = ((np.abs(xs - 8) / 4.0) ** 2 + ((ys - 9.0) / 2.6) ** 2 <= 1) & (ys <= 9.6)
    col = hexrgb(cap) * np.clip(0.8 + 0.3 * (9.6 - ys) / 3, 0.6, 1.1)[..., None]
    if spots:
        for k in range(5):
            sx, sy = 8 + r.uniform(-2.5, 2.5), r.uniform(7.0, 9.0)
            sp = (xs - sx) ** 2 + (ys - sy) ** 2 < 0.25
            col = np.where(sp[..., None], hexrgb(spots), col)
    cv.put(ix, m.astype(F32), col, 0.5)
    return finish(cv, path)


def nether_roots(seed, path, colour):
    r = rng(seed)
    cv = Canvas(wrap=False)
    for k in range(12):
        x = 8 + r.normal(0, 2.6)
        pts = blade(cv, x, 16.4, (x - 8) / 8 * 0.6 + r.normal(0, 0.15), r.uniform(5, 12), r.uniform(0.5, 0.8),
                    r.uniform(-0.6, 0.6), r.uniform(0, 1), hexrgb(colour) * r.uniform(0.8, 1.15), taper=0.6)
        if r.uniform() < 0.5:
            disc(cv, pts[-1][0], pts[-1][1], 0.45, hexrgb(colour) * 1.2, 0.9)
    return finish(cv, path)


def hanging_vine(seed, path, colour, up=False, tip=False):
    r = rng(seed)
    cv = Canvas(wrap=False)
    for k in range(3):
        x = 4 + 4 * k + r.uniform(-1, 1)
        L = 17 if not tip else r.uniform(8, 12)
        if up:
            pts, dirs = path_points(x, 16.5, r.uniform(-0.2, 0.2), L, r.uniform(-0.6, 0.6), steps=10)
        else:
            pts, dirs = path_points(x, -0.5, np.pi + r.uniform(-0.2, 0.2), L, r.uniform(-0.6, 0.6), steps=10)
        cv.stroke(pts, np.linspace(0.9, 0.5 if not tip else 0.2, 10), 0.2, rgb=hexrgb(colour))
        for (px, py), d in zip(pts[1::2], dirs[1::2]):
            leaf_at(cv, px, py, d + r.choice([-1, 1]) * r.uniform(0.6, 1.2), r.uniform(1.2, 2.0), 0.8, 0.4,
                    hexrgb(colour) * r.uniform(0.85, 1.2), kind='ovate')
    return finish(cv, path)


def sprouts(seed, path, colour):
    r = rng(seed)
    cv = Canvas(wrap=False)
    for k in range(14):
        x = 8 + r.normal(0, 3)
        blade(cv, x, 16.4, r.normal(0, 0.4), r.uniform(2.5, 5.5), r.uniform(0.4, 0.6), r.uniform(-0.5, 0.5),
              r.uniform(0, 1), hexrgb(colour) * r.uniform(0.85, 1.15))
    return finish(cv, path)


def frogspawn(seed, path='frogspawn'):
    r = rng(seed)
    rgb = np.zeros((N, N, 3), F32)
    a = np.zeros((N, N), F32)
    for k in range(18):
        cx, cy = r.uniform(1, 15), r.uniform(1, 15)
        d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        jelly = d < 1.4
        egg = d < 0.55
        rgb = np.where(jelly[..., None] & (a[..., None] < 0.5), hexrgb('#9a8e7a'), rgb)
        a = np.maximum(a, jelly * 0.45)
        rgb = np.where(egg[..., None], hexrgb('#2a2018'), rgb)
        a = np.maximum(a, egg * 1.0)
    mean, lum, _ = cal(path)
    return Tex(match_mean(rgb, lum, a > 0.3), None, a, light='none', sharpen=0.0)


# ------------------------------------------------------------------ registration
def register(R):
    R.block('azalea_side', lambda v: azalea_side(1300), cutout=True)
    R.block('azalea_top', lambda v: azalea_top(1301))
    R.block('azalea_plant', lambda v: azalea_plant(1302), cutout=True)
    R.block('flowering_azalea_side', lambda v: azalea_side(1303, (14, '#d26dbf'), 'flowering_azalea_side'), cutout=True)
    R.block('flowering_azalea_top', lambda v: azalea_top(1304, (18, '#d26dbf'), 'flowering_azalea_top'))
    for kind, fl in (('azalea', None), ('flowering_azalea', (10, '#d26dbf'))):
        for part in ('side', 'top', 'plant'):
            p = f'potted_{kind}_bush_{part}'
            R.block(p, lambda v, p=p, fl=fl: masked(p, leafy_rgb(1305, flowers=fl), light='none'), cutout=True)

    R.block('big_dripleaf_top', lambda v: dripleaf_top(1310, 'big_dripleaf_top'), cutout=True)
    R.block('small_dripleaf_top', lambda v: dripleaf_top(1311, 'small_dripleaf_top', quadrant=True), cutout=True)
    stemrgb = lambda s: ramp(np.clip(0.5 + 0.3 * fbm(N, (4, 16), s, 3), 0, 1), [(0, '#3d5f1c'), (1, '#6f9a32')])
    for p in ('big_dripleaf_stem', 'big_dripleaf_side1', 'big_dripleaf_side2', 'small_dripleaf_side',
              'small_dripleaf_stem_bottom', 'small_dripleaf_stem_top'):
        R.block(p, lambda v, p=p: masked(p, stemrgb(1312), smooth=True), cutout=True)

    R.block('cave_vines_body', lambda v: cave_vine(1320, path='cave_vines_body'), cutout=True)
    R.block('cave_vines_body_berries', lambda v: cave_vine(1320, True, path='cave_vines_body_berries'), cutout=True)
    R.block('cave_vines_head', lambda v: cave_vine(1321, head=True, path='cave_vines_head'), cutout=True)
    R.block('cave_vines_head_berries', lambda v: cave_vine(1321, True, True, path='cave_vines_head_berries'),
            cutout=True)
    R.block('hanging_roots', lambda v: hanging_roots(1322), cutout=True)
    R.block('glow_lichen', lambda v: lichen(1323), cutout=True)
    R.block('spore_blossom', lambda v: spore_blossom(1324, 'spore_blossom'), cutout=True)
    R.block('spore_blossom_base', lambda v: spore_blossom(1325, 'spore_blossom_base'), cutout=True)

    R.block('mangrove_roots_side', lambda v: mangrove_roots(1330, 'side', 'mangrove_roots_side'), cutout=True)
    R.block('mangrove_roots_top', lambda v: mangrove_roots(1331, 'top', 'mangrove_roots_top'), cutout=True)
    R.block('muddy_mangrove_roots_side', lambda v: muddy_roots(1332, 'side', 'muddy_mangrove_roots_side'))
    R.block('muddy_mangrove_roots_top', lambda v: muddy_roots(1333, 'top', 'muddy_mangrove_roots_top'))
    R.block('mangrove_propagule', lambda v: propagule(1334, 'mangrove_propagule'), cutout=True)
    R.block('mangrove_propagule_hanging', lambda v: propagule(1335, 'mangrove_propagule_hanging', True), cutout=True)

    R.block('bamboo_stem', lambda v: bamboo_stem_tex(1340))
    R.block('bamboo_leaf', lambda v: bamboo_leaves(1341, 'bamboo_leaf', 9), cutout=True)
    R.block('bamboo_small_leaf', lambda v: bamboo_leaves(1342, 'bamboo_small_leaf', 4), cutout=True)
    R.block('bamboo_singleleaf', lambda v: masked('bamboo_singleleaf', np.full((N, N, 3), hexrgb('#5f8a24'))),
            cutout=True)
    R.block('bamboo_sapling', lambda v: bamboo_leaves(1343, 'bamboo_sapling', 3), cutout=True)

    R.block('pale_hanging_moss_middle', lambda v: pale_hanging_moss(1350, 'pale_hanging_moss_middle'), cutout=True)
    R.block('pale_hanging_moss_tip', lambda v: pale_hanging_moss(1351, 'pale_hanging_moss_tip', True), cutout=True)
    R.block('pale_moss_carpet_side_base', lambda v: pale_carpet_side(1352, 'pale_moss_carpet_side_base'), cutout=True)
    R.block('pale_moss_carpet_side_tip', lambda v: pale_carpet_side(1353, 'pale_moss_carpet_side_tip', True),
            cutout=True)

    # eyeblossom parts are mapped onto a special model: our colours inside its UV silhouettes
    def eyeblossom(p, rgbhex, glow=False):
        rgb = ramp(np.clip(0.5 + 0.3 * fbm(N, 10, 1360, 3), 0, 1), [(0, hexrgb(rgbhex) * 0.6), (1, hexrgb(rgbhex))])
        stemm = (Y > 9.5)
        rgb = np.where(stemm[..., None], ramp(np.clip(0.5 + 0.3 * fbm(N, 10, 1361, 3), 0, 1),
                                              [(0, '#56604a'), (1, '#7f8a70')]), rgb)
        t = masked(p, rgb, light='none', smooth=True)
        if glow:
            t = t.but(emissive=(t.alpha * 0.5)[..., None] * hexrgb('#ffb23a'))
        return t
    R.block('eyeblossom_blooming', lambda v: eyeblossom('eyeblossom_blooming', '#e6e0dc'), cutout=True)
    R.block('eyeblossom_dormant', lambda v: eyeblossom('eyeblossom_dormant', '#9a9298'), cutout=True)
    R.block('eyeblossom_stem_blooming', lambda v: eyeblossom('eyeblossom_stem_blooming', '#d8d0d0'), cutout=True)
    R.block('eyeblossom_eyes_blooming', lambda v: eyeblossom('eyeblossom_eyes_blooming', '#f29a2e', glow=True),
            cutout=True)

    # pitcher crop: pod, leaves and flower painted inside the model's islands
    pod = lambda s, stops: ramp(np.clip(0.5 + 0.3 * fbm(N, (6, 12), s, 3), 0, 1), stops)
    for p in ('pitcher_crop_bottom', 'pitcher_crop_side', 'pitcher_crop_top', 'pitcher_crop_bottom_stage_1',
              'pitcher_crop_bottom_stage_2', 'pitcher_crop_bottom_stage_3', 'pitcher_crop_bottom_stage_4',
              'pitcher_crop_top_stage_3', 'pitcher_crop_top_stage_4'):
        mean, lum, _ = cal(p)
        stops = [(0, np.asarray(mean) * 0.6), (0.5, np.asarray(mean)), (1, np.clip(np.asarray(mean) * 1.3, 0, 1))]
        R.block(p, lambda v, p=p, stops=stops: masked(p, pod(1370, stops), smooth='stage' in p), cutout=True)
    for st in range(3):
        p = f'cocoa_stage_{st}'
        mean, lum, _ = cal(p)
        rib = lambda s, mean=mean: ramp(np.clip(0.5 + 0.25 * np.cos(X * 2.4) + 0.1 * fbm(N, 12, s, 2), 0, 1),
                                        [(0, np.asarray(mean) * 0.6), (0.5, np.asarray(mean)),
                                         (1, np.clip(np.asarray(mean) * 1.3, 0, 1))])
        R.block(p, lambda v, p=p, rib=rib: masked(p, rib(1371)), cutout=True)
    mean, lum, _ = cal('sea_pickle')
    R.block('sea_pickle', lambda v: masked('sea_pickle', ramp(np.clip(0.5 + 0.3 * fbm(N, 14, 1372, 3), 0, 1),
                                                              [(0, '#3d5418'), (0.5, '#5f7a2a'), (1, '#8faa4a')])),
            cutout=True)
    R.block('frogspawn', lambda v: frogspawn(1373))

    # animated aquatic plants (frame counts match vanilla flipbooks)
    for j, k in enumerate(('kelp_a', 'kelp_b', 'kelp_c', 'kelp_d')):
        R.anim(k, lambda f, n, k=k, j=j: kelp(f, n, 1380 + j, k), 20, cutout=True)
    R.anim('kelp_top', lambda f, n: kelp(f, n, 1384, 'kelp_top', top=True), 20, cutout=True)
    R.anim('kelp_top_bulb', lambda f, n: kelp(f, n, 1385, 'kelp_top_bulb', top=True, bulb=True), 20, cutout=True)
    R.anim('seagrass', lambda f, n: seagrass(f, n, 1386, 'seagrass'), 18, cutout=True)
    R.block('seagrass_carried', lambda v: seagrass(0, 18, 1386, 'seagrass_carried'), cutout=True)
    for ab in ('a', 'b'):
        for part in ('bottom', 'top'):
            p = f'seagrass_doubletall_{part}_{ab}'
            R.anim(p, lambda f, n, p=p, part=part, ab=ab: seagrass(f, n, 1387 + (ab == 'b'), p, tall=part), 19,
                   cutout=True)

    for j, name in enumerate(CORALS):
        for dead in (False, True):
            sfx = '_dead' if dead else ''
            R.block(f'coral_{name}{sfx}', lambda v, j=j, name=name, dead=dead, sfx=sfx:
                    coral_block(1400 + j, name, dead, f'coral_{name}{sfx}'))
            R.block(f'coral_plant_{name}{sfx}', lambda v, j=j, name=name, dead=dead, sfx=sfx:
                    coral_plant(1410 + j, name, dead, f'coral_plant_{name}{sfx}'), cutout=True)
            R.block(f'coral_fan_{name}{sfx}', lambda v, j=j, name=name, dead=dead, sfx=sfx:
                    coral_fan(1420 + j, name, dead, f'coral_fan_{name}{sfx}'), cutout=True)

    R.block('chorus_plant', lambda v: chorus(1430, 'chorus_plant'))
    R.block('chorus_flower', lambda v: chorus(1431, 'chorus_flower', flower=True))
    R.block('chorus_flower_dead', lambda v: chorus(1432, 'chorus_flower_dead', flower=True, dead=True))

    R.block('crimson_fungus', lambda v: nether_fungus(1440, 'crimson_fungus', '#a82418', spots='#f2b23a'), cutout=True)
    R.block('warped_fungus', lambda v: nether_fungus(1441, 'warped_fungus', '#2a8f7a', spots='#f28a2a'), cutout=True)
    R.block('crimson_roots', lambda v: nether_roots(1442, 'crimson_roots', '#9a1438'), cutout=True)
    R.block('warped_roots', lambda v: nether_roots(1443, 'warped_roots', '#1f9a8a'), cutout=True)
    R.block('crimson_roots_pot', lambda v: nether_roots(1444, 'crimson_roots_pot', '#9a1438'), cutout=True)
    R.block('warped_roots_pot', lambda v: nether_roots(1445, 'warped_roots_pot', '#1f9a8a'), cutout=True)
    R.block('nether_sprouts', lambda v: sprouts(1446, 'nether_sprouts', '#1fa892'), cutout=True)
    R.block('twisting_vines_base', lambda v: hanging_vine(1447, 'twisting_vines_base', '#1f9a8a', up=True), cutout=True)
    R.block('twisting_vines_bottom', lambda v: hanging_vine(1448, 'twisting_vines_bottom', '#1f9a8a', up=True,
                                                            tip=True), cutout=True)
    R.block('weeping_vines', lambda v: hanging_vine(1449, 'weeping_vines', '#8f1414', tip=True), cutout=True)
    R.block('weeping_vines_base', lambda v: hanging_vine(1450, 'weeping_vines_base', '#9a1a24'), cutout=True)
    R.block('weeping_vines_bottom', lambda v: hanging_vine(1451, 'weeping_vines_bottom', '#8f1414', tip=True),
            cutout=True)
    R.block('weeping_vines_plant', lambda v: hanging_vine(1452, 'weeping_vines_plant', '#9a1a24'), cutout=True)
