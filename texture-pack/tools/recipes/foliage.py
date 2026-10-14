"""Foliage: leaves (fancy, opaque and inventory versions) for every tree, built from individually drawn
leaves, needles and blossoms with depth shading and contact shadows."""
import numpy as np

from engine.noise import F32, blur, smoothstep, rng
from engine.color import ramp, match_mean, hexrgb
from engine.material import Tex, MASTER
from engine.draw import U, AA, polyline, bezier
from registry import CALIBRATION

N = MASTER


def cal(path):
    c = CALIBRATION['textures/blocks/' + path]
    return np.array(c['mean'], F32), float(c['lum']), float(c['coverage'])


# ------------------------------------------------------------------ sprite canvas
class Canvas:
    """Painter's-order compositing of small sprites evaluated on local windows (wrapping)."""

    def __init__(self, wrap=True):
        self.rgb = np.zeros((N, N, 3), F32)
        self.a = np.zeros((N, N), F32)
        self.z = np.full((N, N), -1.0, F32)
        self.wrap = wrap

    def window(self, cx, cy, radius):
        c0, c1 = int(np.floor((cx - radius) * U)), int(np.ceil((cx + radius) * U)) + 1
        r0, r1 = int(np.floor((cy - radius) * U)), int(np.ceil((cy + radius) * U)) + 1
        cols, rows = np.arange(c0, c1), np.arange(r0, r1)
        if not self.wrap:
            cols = cols[(cols >= 0) & (cols < N)]
            rows = rows[(rows >= 0) & (rows < N)]
        xs = ((cols + 0.5) / U)[None, :].astype(F32)
        ys = ((rows + 0.5) / U)[:, None].astype(F32)
        return np.ix_(rows % N, cols % N), xs, ys

    def put(self, ix, mask, rgb, z):
        m = np.clip(mask, 0, 1)
        if not m.any():
            return
        rgb = np.asarray(rgb, F32)
        if rgb.ndim == 1:
            rgb = np.broadcast_to(rgb, m.shape + (3,))
        self.rgb[ix] = self.rgb[ix] * (1 - m[..., None]) + rgb * m[..., None]
        self.a[ix] = np.maximum(self.a[ix], m)
        self.z[ix] = np.where(m > 0.5, z, self.z[ix])

    def coverage(self):
        return float((self.a >= 0.5).mean())

    def stroke(self, pts, widths, z, rgb=None, lum=None, shade_along=0.0):
        """A tapered polyline stroke evaluated on its bounding window only."""
        pts = np.asarray(pts, F32)
        w = np.broadcast_to(np.asarray(widths, F32), (len(pts),))
        rad = float(w.max()) / 2 + 2 * AA
        x0, y0 = pts.min(0) - rad
        x1, y1 = pts.max(0) + rad
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        ix, xs, ys = self.window(cx, cy, max(x1 - x0, y1 - y0) / 2 + 0.1)
        best = np.full(np.broadcast(xs, ys).shape, 1e9, F32)
        rads = np.zeros_like(best)
        along = np.zeros_like(best)
        seg = np.sqrt(((pts[1:] - pts[:-1]) ** 2).sum(1))
        acc = np.concatenate([[0], np.cumsum(seg)]) / max(seg.sum(), 1e-6)
        for i in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            px, py = xs - ax, ys - ay
            vx, vy = bx - ax, by - ay
            t = np.clip((px * vx + py * vy) / (vx * vx + vy * vy + 1e-9), 0, 1)
            d = np.sqrt((px - t * vx) ** 2 + (py - t * vy) ** 2)
            closer = d < best
            best = np.where(closer, d, best)
            rads = np.where(closer, (w[i] + (w[i + 1] - w[i]) * t) / 2, rads)
            along = np.where(closer, acc[i] + t * (acc[i + 1] - acc[i]), along)
        m = 1 - smoothstep(rads - AA, rads + AA, best)
        if not m.any():
            return
        k = 1 - shade_along * (1 - along)
        across = np.clip(best / np.maximum(rads, 1e-3), 0, 1)
        k = k * (0.86 + 0.14 * (1 - across ** 2))
        if rgb is None:
            rgb = np.full(3, lum if lum is not None else 0.5, F32)
        col = np.asarray(rgb, F32) * k[..., None]
        self.put(ix, m, col, z)


def leaf_uv(xs, ys, cx, cy, ang, L, W):
    c, s = np.cos(ang), np.sin(ang)
    dx, dy = xs - cx, ys - cy
    u = (dx * c + dy * s) / L
    v = (-dx * s + dy * c) / (W / 2)
    return u, v


def leaf_profile(u, kind, lobes=3, serr=0.0, teeth=7):
    uc = np.clip(u, 0, 1)
    if kind == 'ovate':
        prof = np.clip(1.9 * uc ** 0.6 * (1 - uc) ** 0.9, 0, 1)
    elif kind == 'deltoid':
        prof = np.clip(2.2 * uc ** 0.35 * (1 - uc) ** 1.2, 0, 1)
    elif kind == 'round':
        prof = np.sqrt(np.clip(1 - (2 * uc - 1) ** 2, 0, 1))
    elif kind == 'needle':
        prof = np.clip(1 - uc ** 3, 0, 1) * smoothstep(0.0, 0.08, uc)
    else:  # lanceolate
        prof = np.sin(np.pi * uc) ** 0.75
    if kind == 'lobed':
        prof = np.sin(np.pi * uc) ** 0.6 * (0.74 + 0.26 * np.cos(uc * 2 * np.pi * lobes + 0.6))
    if serr:
        prof = prof * (1 - serr * ((uc * teeth) % 1.0))
    return prof


def draw_leaf(cv, cx, cy, ang, L, W, z, base, *, kind='lanceolate', lobes=3, serr=0.0, colour=None, gloss=0.0,
              veins=0.5):
    ix, xs, ys = cv.window(cx, cy, L + 0.2)
    u, v = leaf_uv(xs, ys, cx, cy, ang, L, W)
    prof = leaf_profile(u, kind, lobes, serr)
    d = (np.abs(v) - prof) * (W / 2)
    inside = (u >= 0) & (u <= 1)
    m = (1 - smoothstep(-AA, AA, d)) * inside
    if not m.any():
        return
    av = np.clip(np.abs(v) / np.maximum(prof, 1e-3), 0, 1)
    shade = 0.8 + 0.2 * (1 - av ** 2)
    shade = shade * np.where(v > 0, 0.9, 1.0)
    rib = 1 - smoothstep(0.04, 0.12, np.abs(v) * W / 2)
    lat = np.abs(((u * 6 - av * 0.9) % 1.0) - 0.5) < 0.09
    lum = base * shade * (1 + 0.1 * rib) * (1 + 0.04 * veins * lat) * (0.93 + 0.12 * u)
    if gloss:
        lum = lum + gloss * np.exp(-((v + 0.35) ** 2) / 0.05) * np.sin(np.pi * np.clip(u, 0, 1))
    if colour is None:
        rgb = np.repeat(lum[..., None], 3, axis=-1)
    else:
        rgb = np.asarray(colour, F32) * lum[..., None]
    cv.put(ix, m, rgb, z)


def draw_twig(cv, pts, width, z, lum=0.25, colour=None):
    """A thin twig as a polyline stroke on the canvas (wrapping)."""
    mask, along = polyline(pts, np.linspace(width, width * 0.4, len(pts)), wrap=cv.wrap)
    rgb = np.repeat((lum * (0.85 + 0.3 * along))[..., None], 3, axis=-1) if colour is None else \
        np.asarray(colour, F32) * (0.85 + 0.3 * along)[..., None]
    full = (slice(None), slice(None))
    cv.put(full, mask, rgb, z)


def depth_shade(cv, back=0.62, shadow=0.55):
    """Leaves drawn later sit in front: brighten them, darken leaves behind and next to them."""
    zz = np.where(cv.a > 0.5, cv.z, -0.2)
    zn = np.clip(zz, 0, 1)
    k = back + (1 - back) * zn
    sh = np.clip((blur(zz, 2.0) - zz) * 3.0, 0, 1) * shadow
    cv.rgb = cv.rgb * (k * (1 - sh))[..., None]


# ------------------------------------------------------------------ leaf canopies
def canopy(seed, spec, *, opaque=False):
    """Draw a canopy tile for a species spec; returns (rgb, alpha)."""
    r = rng(seed)
    cv = Canvas()
    target = spec.get('cover', 0.7)
    kind = spec.get('kind', 'lanceolate')
    colours = spec.get('colours')
    # twigs behind the leaves
    for _ in range(spec.get('twigs', 4)):
        x0, y0 = r.uniform(0, 16), r.uniform(0, 16)
        a = r.uniform(0, 2 * np.pi)
        L = r.uniform(4, 9)
        pts = bezier((x0, y0), (x0 + np.cos(a) * L * 0.35 + r.uniform(-1, 1), y0 + np.sin(a) * L * 0.35),
                     (x0 + np.cos(a) * L * 0.7, y0 + np.sin(a) * L * 0.7 + r.uniform(-1, 1)),
                     (x0 + np.cos(a) * L, y0 + np.sin(a) * L), 10)
        draw_twig(cv, pts, r.uniform(0.25, 0.45), 0.0, lum=0.22, colour=spec.get('twig_colour'))
    n = 0
    max_n = spec.get('max', 600)
    L0, L1 = spec['L']
    W0, W1 = spec['W']
    while n < max_n and (n < 20 or cv.coverage() < target):
        cx, cy = r.uniform(0, 16), r.uniform(0, 16)
        ang = r.uniform(0, 2 * np.pi)
        L, W = r.uniform(L0, L1), r.uniform(W0, W1)
        z = n / max_n
        base = r.uniform(*spec.get('bright', (0.55, 1.0)))
        col = None
        if colours is not None:
            col = ramp(np.array([r.uniform(0, 1)]), colours)[0]
        if kind == 'needles':
            # a spray: a short twig with needles on both sides
            k = r.integers(7, 13)
            for j in range(k):
                t = j / k
                px, py = cx + np.cos(ang) * t * L * 2.2, cy + np.sin(ang) * t * L * 2.2
                for side in (-1, 1):
                    draw_leaf(cv, px, py, ang + side * r.uniform(0.6, 1.1), r.uniform(0.9, 1.4) * L / 1.2,
                              W, z + j * 1e-4, base * r.uniform(0.85, 1.1), kind='needle', colour=col, veins=0)
            n += k
            continue
        if kind == 'pinnate':
            k = r.integers(4, 7)
            for j in range(k):
                t = (j + 0.5) / k
                px, py = cx + np.cos(ang) * t * L * 3.0, cy + np.sin(ang) * t * L * 3.0
                for side in (-1, 1):
                    draw_leaf(cv, px, py, ang + side * r.uniform(1.0, 1.4), L, W, z + j * 1e-4,
                              base * r.uniform(0.9, 1.08), kind='ovate', colour=col, veins=0.2)
            n += k
            continue
        if kind == 'blossom':
            # five-petal blossom or a leaf
            if r.uniform() < spec.get('leaf_ratio', 0.25):
                draw_leaf(cv, cx, cy, ang, L * 1.1, W * 0.8, z, base, kind='ovate',
                          colour=spec.get('leaf_colour', hexrgb('#4f7a2e')))
            else:
                pr = r.uniform(0.6, 0.85) * L / 1.6
                for p in range(5):
                    a = ang + p * 2 * np.pi / 5
                    draw_leaf(cv, cx, cy, a, pr * 1.6, pr * 1.5, z + p * 1e-4, base * r.uniform(0.92, 1.05),
                              kind='round', colour=col, veins=0.2)
                ix, xs, ys = cv.window(cx, cy, 0.5)
                cm = 1 - smoothstep(0.18 - AA, 0.18 + AA, np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2))
                cv.put(ix, cm, spec.get('centre', hexrgb('#e8c25a')), z + 0.001)
            n += 1
            continue
        draw_leaf(cv, cx, cy, ang, L, W, z, base, kind=kind, lobes=spec.get('lobes', 3), serr=spec.get('serr', 0.0),
                  colour=col, gloss=spec.get('gloss', 0.0))
        n += 1
    flowers = spec.get('flowers')
    if flowers:
        for _ in range(flowers['count']):
            cx, cy = r.uniform(0, 16), r.uniform(0, 16)
            ang = r.uniform(0, 2 * np.pi)
            pr = r.uniform(*flowers['size'])
            for p in range(flowers.get('petals', 5)):
                a = ang + p * 2 * np.pi / flowers.get('petals', 5)
                draw_leaf(cv, cx, cy, a, pr * 1.6, pr * 1.5, 1.0 + p * 1e-4, r.uniform(0.9, 1.05), kind='round',
                          colour=hexrgb(flowers['colour']), veins=0.1)
            ix, xs, ys = cv.window(cx, cy, 0.5)
            cm = 1 - smoothstep(0.2 - AA, 0.2 + AA, np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2))
            cv.put(ix, cm, hexrgb(flowers.get('centre', '#f0d070')), 1.01)
    depth_shade(cv, spec.get('back', 0.6))
    rgb, a = cv.rgb, cv.a
    if opaque:
        deep = Canvas()
        r2 = rng(seed + 999)
        while deep.coverage() < 0.995:
            cx, cy = r2.uniform(0, 16), r2.uniform(0, 16)
            draw_leaf(deep, cx, cy, r2.uniform(0, 2 * np.pi), r2.uniform(L0, L1) * 1.2, r2.uniform(W0, W1) * 1.3,
                      0.0, r2.uniform(0.3, 0.5), kind='lanceolate' if kind in ('needles', 'pinnate', 'blossom') else kind,
                      colour=None if colours is None else ramp(np.array([r2.uniform(0, 1)]), colours)[0] * 0.8)
        under = blur(deep.rgb, 0.6) * 0.55
        rgb = rgb * a[..., None] + under * (1 - a[..., None])
        a = np.ones_like(a)
    return rgb.astype(F32), a.astype(F32)


def leaves_tex(seed, spec, path, *, opaque=False, carried_path=None):
    mean, lum, cov = cal(path)
    rgb, a = canopy(seed, spec, opaque=opaque)
    mask = a > 0.5
    rgb = match_mean(rgb, lum, mask if not opaque else None)
    if carried_path:
        cmean, clum, _ = cal(carried_path)
        tint = np.clip(cmean / max(lum, 1e-3), 0, 2)
        rgb = np.clip(rgb * tint, 0, 1)
        rgb = match_mean(rgb, clum, mask)
    return Tex(rgb, None, None if opaque else a, light='none', cutout=not opaque, sharpen=0.3)


LEAVES = {
    'oak': dict(paths=('leaves_oak', 'leaves_oak_opaque', 'leaves_oak_carried'), kind='lobed', L=(2.3, 3.2),
                W=(1.5, 2.1), lobes=3, cover=0.7, twigs=4),
    'birch': dict(paths=('leaves_birch', 'leaves_birch_opaque', 'leaves_birch_carried'), kind='ovate', L=(1.5, 2.2),
                  W=(1.0, 1.4), serr=0.18, cover=0.6, twigs=5),
    'spruce': dict(paths=('leaves_spruce', 'leaves_spruce_opaque', 'leaves_spruce_carried'), kind='needles',
                   L=(1.0, 1.3), W=(0.16, 0.22), cover=0.66, twigs=6, max=900, bright=(0.5, 0.95)),
    'jungle': dict(paths=('leaves_jungle', 'leaves_jungle_opaque', 'leaves_jungle_carried'), kind='lanceolate',
                   L=(3.6, 5.4), W=(1.8, 2.6), cover=0.72, gloss=0.12, twigs=3),
    'acacia': dict(paths=('leaves_acacia', 'leaves_acacia_opaque', 'leaves_acacia_carried'), kind='pinnate',
                   L=(0.9, 1.3), W=(0.55, 0.75), cover=0.6, twigs=6, max=900),
    'big_oak': dict(paths=('leaves_big_oak', 'leaves_big_oak_opaque', 'leaves_big_oak_carried'), kind='lobed',
                    L=(2.0, 2.8), W=(1.4, 1.9), lobes=2, cover=0.74, twigs=5, back=0.5),
    'mangrove': dict(paths=('mangrove_leaves', 'mangrove_leaves_opaque', 'mangrove_leaves_carried'), kind='ovate',
                     L=(2.4, 3.2), W=(1.2, 1.6), cover=0.82, gloss=0.15, twigs=4),
}

COLOURED = {
    'azalea_leaves': dict(paths=('azalea_leaves', 'azalea_leaves_opaque'), kind='round', L=(1.4, 2.0), W=(1.1, 1.5),
                          cover=0.77, colours=[(0, '#3f6a1d'), (0.6, '#5c8a2a'), (1, '#7aa23a')]),
    'azalea_leaves_flowers': dict(paths=('azalea_leaves_flowers', 'azalea_leaves_flowers_opaque'), kind='round',
                                  L=(1.4, 2.0), W=(1.1, 1.5), cover=0.75,
                                  colours=[(0, '#3f6a1d'), (0.6, '#5c8a2a'), (1, '#7aa23a')],
                                  flowers=dict(count=9, size=(0.45, 0.65), colour='#d66fc4', centre='#f6e0f0')),
    'cherry_leaves': dict(paths=('cherry_leaves', 'cherry_leaves_opaque'), kind='blossom', L=(1.4, 2.0),
                          W=(1.0, 1.3), cover=0.84, colours=[(0, '#e392b5'), (0.5, '#f3b2cb'), (1, '#fcd6e2')],
                          leaf_colour=hexrgb('#6f8f3a'), leaf_ratio=0.15, centre=hexrgb('#c4506f'), max=500),
    'pale_oak_leaves': dict(paths=('pale_oak_leaves', 'pale_oak_leaves_opaque'), kind='lobed', L=(2.0, 2.8),
                            W=(1.3, 1.8), lobes=3, cover=0.81,
                            colours=[(0, '#5f665c'), (0.5, '#7a8276'), (1, '#9aa294')]),
    'yellow_poplar_leaves': dict(paths=('yellow_poplar_leaves', 'yellow_poplar_leaves_opaque'), kind='deltoid',
                                 L=(1.8, 2.5), W=(1.6, 2.2), cover=0.71,
                                 colours=[(0, '#c98a1c'), (0.5, '#e2a92a'), (1, '#f2cc4a')]),
    'orange_poplar_leaves': dict(paths=('orange_poplar_leaves', 'orange_poplar_leaves_opaque'), kind='deltoid',
                                 L=(1.8, 2.5), W=(1.6, 2.2), cover=0.71,
                                 colours=[(0, '#b04a12'), (0.5, '#d2671c'), (1, '#e88a30')]),
    'red_poplar_leaves': dict(paths=('red_poplar_leaves', 'red_poplar_leaves_opaque'), kind='deltoid',
                              L=(1.8, 2.5), W=(1.6, 2.2), cover=0.71,
                              colours=[(0, '#7f1712'), (0.5, '#a2271c'), (1, '#c4432c')]),
}


def register(R):
    for i, (sp, spec) in enumerate(LEAVES.items()):
        fancy, opaque, carried = spec['paths']
        s = 700 + 10 * i
        R.block(fancy, lambda v, s=s, spec=spec, fancy=fancy: leaves_tex(s, spec, fancy), cutout=True)
        R.block(opaque, lambda v, s=s, spec=spec, opaque=opaque: leaves_tex(s, spec, opaque, opaque=True))
        R.block(carried, lambda v, s=s, spec=spec, fancy=fancy, carried=carried:
                leaves_tex(s, spec, fancy, carried_path=carried), cutout=True)
    for i, (name, spec) in enumerate(COLOURED.items()):
        fancy, opaque = spec['paths']
        s = 800 + 10 * i
        R.block(fancy, lambda v, s=s, spec=spec, fancy=fancy: leaves_tex(s, spec, fancy), cutout=True)
        R.block(opaque, lambda v, s=s, spec=spec, opaque=opaque: leaves_tex(s, spec, opaque, opaque=True))
