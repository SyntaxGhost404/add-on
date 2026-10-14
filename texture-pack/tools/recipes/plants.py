"""Plants: grasses, ferns, flowers, double-tall plants, saplings, crops, shrubs and other cross-model
vegetation. Every plant is drawn from strokes (blades, stems, twigs) and leaf/petal shapes."""
import json
import os

import numpy as np

from engine.noise import F32, fbm, blur, smoothstep, rng
from engine.color import ramp, mix, match_mean, hexrgb
from engine.material import Tex, MASTER
from engine.draw import U, AA
from recipes.foliage import Canvas, draw_leaf, depth_shade, cal

N = MASTER
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
MASKS = json.load(open(os.path.join(DATA, 'vanilla_masks.json')))

GREENS = [(0, '#24401a'), (0.45, '#3f6a26'), (0.8, '#5d8a33'), (1, '#7ba744')]
DRY = [(0, '#7a6440'), (0.5, '#a8915f'), (1, '#d2bd8a')]


def green(r, lo=0.0, hi=1.0, stops=GREENS):
    return ramp(np.array([r.uniform(lo, hi)]), stops)[0]


class Tall(Canvas):
    """A canvas `rows` blocks tall (double plants are drawn whole, then split)."""

    def __init__(self, rows=2):
        super().__init__(wrap=False)
        self.rows = rows
        self.rgb = np.zeros((N * rows, N, 3), F32)
        self.a = np.zeros((N * rows, N), F32)
        self.z = np.full((N * rows, N), -1.0, F32)

    def window(self, cx, cy, radius):
        c0, c1 = int(np.floor((cx - radius) * U)), int(np.ceil((cx + radius) * U)) + 1
        r0, r1 = int(np.floor((cy - radius) * U)), int(np.ceil((cy + radius) * U)) + 1
        cols, rows = np.arange(c0, c1), np.arange(r0, r1)
        cols = cols[(cols >= 0) & (cols < N)]
        rows = rows[(rows >= 0) & (rows < N * self.rows)]
        xs = ((cols + 0.5) / U)[None, :].astype(F32)
        ys = ((rows + 0.5) / U)[:, None].astype(F32)
        return np.ix_(rows, cols), xs, ys

    def part(self, k):
        """Sub-canvas k (0 = top block)."""
        c = Canvas(wrap=False)
        c.rgb = self.rgb[k * N:(k + 1) * N].copy()
        c.a = self.a[k * N:(k + 1) * N].copy()
        c.z = self.z[k * N:(k + 1) * N].copy()
        return c


# ------------------------------------------------------------------ primitives
def blade(cv, x, y, ang, length, width, bend, z, rgb, steps=8, shade=0.35, taper=0.85):
    pts = [(x, y)]
    a = ang
    dl = length / (steps - 1)
    for k in range(1, steps):
        t = k / (steps - 1)
        a = ang + bend * t * t
        x, y = x + np.sin(a) * dl, y - np.cos(a) * dl
        pts.append((x, y))
    t = np.linspace(0, 1, steps)
    widths = width * (1 - t * taper) ** 0.8 + 0.06
    cv.stroke(pts, widths, z, rgb=rgb, shade_along=shade)
    return pts


def path_points(x, y, ang, length, bend, steps=10):
    pts = [(x, y)]
    dl = length / (steps - 1)
    dirs = []
    for k in range(1, steps):
        t = k / (steps - 1)
        a = ang + bend * t * t
        dirs.append(a)
        x, y = x + np.sin(a) * dl, y - np.cos(a) * dl
        pts.append((x, y))
    dirs.append(dirs[-1])
    return pts, dirs


def stem(cv, x, y, ang, length, width, bend, z, rgb, steps=10):
    pts, dirs = path_points(x, y, ang, length, bend, steps)
    t = np.linspace(0, 1, steps)
    cv.stroke(pts, width * (1 - 0.45 * t), z, rgb=rgb, shade_along=0.15)
    return pts, dirs


def leaf_at(cv, x, y, direction, L, W, z, rgb, kind='lanceolate', lum=1.0, **kw):
    """direction: angle from vertical (0 = up); draw_leaf uses screen angles (0 = +x)."""
    draw_leaf(cv, x, y, direction - np.pi / 2, L, W, z, lum, kind=kind, colour=rgb, **kw)


def petals(cv, cx, cy, n, length, width, rgb, z, rot=0.0, kind='ovate', jitter=0.15, r=None, lum=(0.9, 1.05)):
    r = r or rng(1)
    for p in range(n):
        a = rot + p * 2 * np.pi / n + r.uniform(-jitter, jitter)
        draw_leaf(cv, cx, cy, a, length * r.uniform(0.9, 1.1), width, z + p * 1e-4, r.uniform(*lum), kind=kind,
                  colour=rgb, veins=0.2)


def disc(cv, cx, cy, rad, rgb, z, speckle=0.0, seed=0):
    ix, xs, ys = cv.window(cx, cy, rad + 0.2)
    d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    m = 1 - smoothstep(rad - AA, rad + AA, d)
    col = np.asarray(rgb, F32) * (0.8 + 0.25 * (1 - d / max(rad, 1e-3)))[..., None]
    if speckle:
        r = rng(seed)
        noise = r.uniform(1 - speckle, 1 + speckle, d.shape).astype(F32)
        col = col * noise[..., None]
    cv.put(ix, m, col, z)


def finish(cv, path, *, grey=False, back=0.72, shadow=0.35, target=None, sharpen=0.3):
    mean, lum, cov = cal(path)
    depth_shade(cv, back, shadow)
    rgb = cv.rgb
    if grey:
        l = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
        rgb = np.repeat(l[..., None], 3, axis=-1)
    mask = cv.a >= 0.5
    rgb = match_mean(rgb, target if target is not None else lum, mask if mask.any() else None)
    return Tex(rgb.astype(F32), None, cv.a.astype(F32), light='none', cutout=True, sharpen=sharpen)


def mask_of(path, rows=None, smooth=False):
    """Vanilla silhouette upsampled to the master grid.

    smooth=True rounds the outlines of solid areas. Texels outside every full 2x2 block (one-texel-wide
    strips and lone texels, such as the edges of leaf faces) stay whole, because a model samples them in full.
    """
    m = MASKS['textures/blocks/' + path]
    a = np.array([[c == '1' for c in row] for row in m['rows']], bool)
    if rows is not None:
        return a
    k = N // a.shape[1]
    up = np.kron(a, np.ones((k, k), bool))
    if smooth:
        pad = np.pad(up.astype(F32), k, mode='constant')
        from engine.noise import blur as _blur
        sm = _blur(pad, k * 0.45)[k:-k, k:-k]
        block = a[:-1, :-1] & a[1:, :-1] & a[:-1, 1:] & a[1:, 1:]
        solid = np.zeros_like(a)
        for dy in (0, 1):
            for dx in (0, 1):
                solid[dy:dy + block.shape[0], dx:dx + block.shape[1]] |= block
        up = (sm > 0.5) | np.kron(a & ~solid, np.ones((k, k), bool))
    return up


# ------------------------------------------------------------------ grasses and ferns
def grass_tuft(seed, cv=None, count=34, h=(9.0, 15.0), x_spread=2.8, lean=0.45, width=(0.55, 0.95), y0=16.4,
               lum=(0.45, 1.0), stops=None, z0=0.0):
    r = rng(seed)
    cv = cv or Canvas(wrap=False)
    for i in range(count):
        x = float(np.clip(r.normal(8, x_spread), 1.0, 15.0))
        ang = (x - 8) / 8 * lean + r.normal(0, 0.18)
        L = r.uniform(*h) * (1 - 0.3 * abs(x - 8) / 8)
        bend = np.sign(ang + 1e-3) * r.uniform(0.15, 0.8)
        b = r.uniform(*lum)
        rgb = np.full(3, b, F32) if stops is None else ramp(np.array([b]), stops)[0]
        blade(cv, x, y0 + r.uniform(0, 0.6), ang, L, r.uniform(*width), bend, z0 + r.uniform(0, 1), rgb)
    return cv


def frond(cv, x, y, ang, length, z, leaf_len, rgb_fn, r, curl=0.6, pinnae=11, rach=0.32):
    pts, dirs = path_points(x, y, ang, length, curl, steps=pinnae + 2)
    cv.stroke(pts, np.linspace(rach, 0.08, len(pts)), z, rgb=rgb_fn(0.5), shade_along=0.2)
    for i in range(1, len(pts) - 1):
        t = i / (len(pts) - 1)
        L = leaf_len * (1 - t) ** 0.6 * (0.6 + 0.4 * np.sin(np.pi * min(1, t * 1.6)))
        if L < 0.25:
            continue
        px, py = pts[i]
        for side in (-1, 1):
            d = dirs[i] + side * r.uniform(0.95, 1.25)
            leaf_at(cv, px, py, d, L, L * 0.42, z + 0.001 * i, rgb_fn(r.uniform(0.6, 1.0)), kind='lanceolate')


def fern_plant(seed, cv=None, fronds=7, size=1.0, y0=16.3, z0=0.0, rgb_fn=None, curl=(0.3, 0.9), leaf=1.0):
    r = rng(seed)
    cv = cv or Canvas(wrap=False)
    rgb_fn = rgb_fn or (lambda b: np.full(3, b, F32))
    for i in range(fronds):
        ang = r.uniform(-0.9, 0.9)
        L = r.uniform(10.5, 14.0) * size
        frond(cv, 8 + r.uniform(-1.2, 1.2), y0, ang, L, z0 + r.uniform(0, 1), r.uniform(2.6, 3.4) * leaf, rgb_fn, r,
              curl=np.sign(ang) * r.uniform(*curl))
    return cv


# ------------------------------------------------------------------ flowers
def flower(seed, head, *, stem_h=(8.5, 10.5), stem_rgb='#3d6a25', leaves=2, leaf_len=(3.0, 4.2), leaf_kind='lanceolate',
           x=8.0, sway=0.8, cv=None, y0=16.3, z0=0.0, leaf_w=0.32):
    r = rng(seed)
    cv = cv or Canvas(wrap=False)
    srgb = hexrgb(stem_rgb)
    L = r.uniform(*stem_h)
    pts, dirs = stem(cv, x + r.uniform(-0.6, 0.6), y0, r.uniform(-0.12, 0.12), L, 0.42, r.uniform(-sway, sway) * 0.3,
                     z0 + 0.2, srgb)
    for k in range(leaves):
        i = int(len(pts) * r.uniform(0.05, 0.45))
        side = 1 if k % 2 == 0 else -1
        ll = r.uniform(*leaf_len)
        leaf_at(cv, pts[i][0], pts[i][1], dirs[i] + side * r.uniform(0.5, 1.0), ll, ll * leaf_w, z0 + 0.3 + 0.01 * k,
                srgb * r.uniform(0.95, 1.2), kind=leaf_kind)
    hx, hy = pts[-1]
    head(cv, hx, hy, r, z0 + 0.6)
    return cv


def head_daisy(rgb='#f4f1e6', centre='#e2b02a', n=14, size=1.9):
    def f(cv, x, y, r, z):
        petals(cv, x, y, n, size, size * 0.32, hexrgb(rgb), z, rot=r.uniform(0, 1), kind='lanceolate', r=r)
        disc(cv, x, y, size * 0.36, hexrgb(centre), z + 0.01, speckle=0.15, seed=r.integers(1 << 30))
    return f


def head_cup(rgb, size=2.2, inner='#3b2a16'):
    """Tulip: three cupped petals facing the viewer."""
    def f(cv, x, y, r, z):
        c = hexrgb(rgb)
        for k, a in enumerate((-0.45, 0.45, 0.0)):
            draw_leaf(cv, x, y + 0.6, -np.pi / 2 + a, size * (1.05 if a == 0 else 0.95), size * 0.95, z + k * 0.001,
                      0.85 + 0.15 * k, kind='ovate', colour=c, veins=0.1)
    return f


def head_poppy(rgb='#c8261d', centre='#1d1a14', size=1.8):
    def f(cv, x, y, r, z):
        petals(cv, x, y, 4, size, size * 1.15, hexrgb(rgb), z, rot=r.uniform(0, 1), kind='round', r=r, lum=(0.85, 1.05))
        disc(cv, x, y, size * 0.3, hexrgb(centre), z + 0.01)
    return f


def head_cluster(rgb, n=14, rad=1.9, floret=0.38, centre=None):
    """Spherical cluster of tiny florets (allium) or small flowers (bluet)."""
    def f(cv, x, y, r, z):
        c = hexrgb(rgb)
        for k in range(n):
            a, d = r.uniform(0, 2 * np.pi), rad * np.sqrt(r.uniform(0, 1))
            px, py = x + d * np.cos(a), y - rad * 0.6 + d * np.sin(a) * 0.9
            petals(cv, px, py, 4, floret * 1.6, floret * 1.2, c * r.uniform(0.85, 1.1), z + k * 0.001,
                   rot=r.uniform(0, 1), kind='round', r=r)
            if centre:
                disc(cv, px, py, floret * 0.35, hexrgb(centre), z + k * 0.001 + 0.0005)
    return f


def head_orchid(rgb='#2fa6c9', size=1.7):
    def f(cv, x, y, r, z):
        c = hexrgb(rgb)
        petals(cv, x, y, 5, size, size * 0.6, c, z, rot=r.uniform(0, 1), kind='ovate', r=r)
        draw_leaf(cv, x, y, np.pi / 2, size * 1.2, size * 1.0, z + 0.01, 1.05, kind='round', colour=c * 1.1)
        disc(cv, x, y, 0.3, hexrgb('#f0e8c8'), z + 0.02)
    return f


def head_ray(rgb='#3d64d4', n=11, size=1.8):
    """Cornflower: ragged, toothed ray florets around a dark heart."""
    def f(cv, x, y, r, z):
        c = hexrgb(rgb)
        petals(cv, x, y, n, size, size * 0.42, c, z, rot=r.uniform(0, 1), kind='deltoid', r=r)
        disc(cv, x, y, 0.45, hexrgb('#22285e'), z + 0.01, speckle=0.2, seed=r.integers(1 << 30))
    return f


def head_pom(rgb='#f2c624', size=1.5, n=26):
    """Dandelion: dense pompom of narrow florets."""
    def f(cv, x, y, r, z):
        c = hexrgb(rgb)
        for k in range(n):
            a = r.uniform(0, 2 * np.pi)
            draw_leaf(cv, x, y, a, size * r.uniform(0.6, 1.0), size * 0.25, z + k * 1e-4, r.uniform(0.85, 1.1),
                      kind='lanceolate', colour=c)
        disc(cv, x, y, size * 0.35, c * 0.85, z + 0.01)
    return f


def head_bells(rgb='#f4f4ee', n=5):
    """Lily of the valley: an arching raceme of small nodding bells on short pedicels."""
    def f(cv, x, y, r, z):
        pts, dirs = path_points(x, y, 0.4, 6.5, 1.9, steps=10)
        cv.stroke(pts, np.linspace(0.25, 0.1, len(pts)), z, rgb=hexrgb('#4b7a2c'), shade_along=0.1)
        for k in range(n):
            px, py = pts[2 + int(k * 1.5)]
            cv.stroke([(px, py), (px + 0.15, py + 0.8)], [0.12, 0.1], z + 0.005, rgb=hexrgb('#4b7a2c'))
            c = hexrgb(rgb) * r.uniform(0.92, 1.05)
            draw_leaf(cv, px + 0.15, py + 0.7, np.pi / 2, 0.95, 1.0, z + 0.01 + k * 0.001, 1.0, kind='ovate', colour=c)
    return f


def head_rosette(rgb, size=2.4, layers=3):
    """Peony / rose: layered petals in shrinking rings."""
    def f(cv, x, y, r, z):
        c = hexrgb(rgb)
        for l in range(layers):
            s = size * (1 - 0.28 * l)
            petals(cv, x, y, 6 - l, s, s * 0.95, c * (0.85 + 0.08 * l), z + l * 0.01, rot=r.uniform(0, 1),
                   kind='round', r=r)
    return f


def head_panicle(rgb, n=34, h=5.5, w=2.4):
    """Lilac: a conical panicle of four-petalled florets."""
    def f(cv, x, y, r, z):
        c = hexrgb(rgb)
        for k in range(n):
            t = r.uniform(0, 1)
            px = x + r.uniform(-1, 1) * w * (1 - 0.8 * t)
            py = y + 0.5 - t * h
            petals(cv, px, py, 4, 0.55, 0.45, c * r.uniform(0.8, 1.1), z + k * 0.001, rot=r.uniform(0, 1),
                   kind='round', r=r)
    return f


def head_torch(rgb='#e8742a', size=3.0):
    def f(cv, x, y, r, z):
        c = hexrgb(rgb)
        for k in range(6):
            a = -np.pi / 2 + r.uniform(-0.5, 0.5)
            draw_leaf(cv, x, y + 1.0, a, size * r.uniform(0.7, 1.0), size * 0.38, z + k * 0.001, r.uniform(0.85, 1.1),
                      kind='lanceolate', colour=c * r.uniform(0.9, 1.1))
        disc(cv, x, y + 0.6, 0.6, hexrgb('#5a2a12'), z + 0.01)
    return f


# ------------------------------------------------------------------ saplings
def sapling(seed, leaf_spec, *, trunk='#5c4127', h=(9.0, 11.0), kind='broad'):
    r = rng(seed)
    cv = Canvas(wrap=False)
    trgb = hexrgb(trunk)
    L = r.uniform(*h)
    pts, dirs = stem(cv, 8 + r.uniform(-0.4, 0.4), 16.3, r.uniform(-0.1, 0.1), L, 0.7, r.uniform(-0.3, 0.3), 0.1, trgb)
    tips = [pts[-1]]
    for k in range(r.integers(2, 4)):
        i = int(len(pts) * r.uniform(0.35, 0.8))
        bp, bd = stem(cv, pts[i][0], pts[i][1], dirs[i] + r.choice([-1, 1]) * r.uniform(0.5, 1.0), r.uniform(2.5, 4.0),
                      0.35, r.uniform(-0.4, 0.4), 0.15, trgb * 1.1)
        tips.append(bp[-1])
    if kind == 'needles':
        for i, (tx, ty) in enumerate(tips):
            for k in range(3):
                frond(cv, tx, ty + 1.5 * k, r.uniform(-1.3, 1.3), r.uniform(2.5, 4.0), 0.5 + 0.01 * i,
                      0.9, leaf_spec, r, curl=r.uniform(-0.3, 0.3), pinnae=7, rach=0.2)
        return cv
    for i, (tx, ty) in enumerate(tips):
        for k in range(r.integers(5, 9)):
            a = r.uniform(-np.pi, np.pi) * 0.9
            ll = r.uniform(1.6, 2.8)
            leaf_at(cv, tx + r.uniform(-1.2, 1.2), ty + r.uniform(-1.0, 1.5), a, ll, ll * 0.55, 0.5 + 0.01 * k + 0.1 * i,
                    leaf_spec(r.uniform(0.6, 1.0)), kind=kind if kind != 'broad' else 'ovate')
    return cv


# ------------------------------------------------------------------ crops
def wheat(seed, stage):
    r = rng(seed)
    cv = Canvas(wrap=False)
    h = 3.0 + stage * 1.6
    ripe = stage >= 6
    stops = [(0, '#3f7a1f'), (1, '#77b03c')] if stage < 5 else ([(0, '#7c8b2c'), (1, '#b3b14a')] if stage < 7 else
                                                                 [(0, '#a7803a'), (1, '#e0be6a')])
    n = 8 + stage * 2
    for k in range(n):
        x = 2 + 12 * (k + r.uniform(-0.3, 0.3)) / n
        ang = r.normal(0, 0.12)
        L = h * r.uniform(0.75, 1.1)
        pts = blade(cv, x, 16.4, ang, L, 0.45 + 0.03 * stage, r.uniform(-0.2, 0.2), r.uniform(0, 1),
                    ramp(np.array([r.uniform(0, 1)]), stops)[0], taper=0.5 if stage > 4 else 0.85)
        if stage >= 5 and r.uniform() < 0.8:
            tx, ty = pts[-1]
            ear = hexrgb('#c9a347') if ripe else hexrgb('#9aa94a')
            for j in range(6):
                for side in (-1, 1):
                    draw_leaf(cv, tx + side * 0.18, ty + 0.45 * j - 0.4, -np.pi / 2 + side * 0.5, 0.9, 0.5,
                              0.9 + j * 0.001, r.uniform(0.85, 1.1), kind='ovate', colour=ear)
            if ripe:
                for j in range(4):
                    cv.stroke([(tx, ty - 0.4 + 0.5 * j), (tx + r.uniform(-0.9, 0.9), ty - 1.8 + 0.5 * j)],
                              [0.08, 0.05], 0.95, rgb=hexrgb('#e8d18e'))
    return cv


def leafy_crop(seed, stage, *, leaf=(2.0, 3.0), count=(3, 6, 9, 12), stops=GREENS, root=None, flowers=None,
               leaf_kind='ovate', vein_red=False, feathery=False):
    r = rng(seed)
    cv = Canvas(wrap=False)
    n = count[min(stage, len(count) - 1)]
    s = 0.45 + 0.18 * stage
    for k in range(n):
        x = 8 + r.normal(0, 2.6)
        if root is not None and stage >= 3:
            pass
        ang = r.uniform(-0.9, 0.9)
        L = r.uniform(4.0, 7.0) * s
        pts, dirs = stem(cv, x, 16.3, ang, L, 0.32,
                         np.sign(ang) * r.uniform(0.1, 0.6), r.uniform(0, 0.5),
                         hexrgb('#a43a45') if vein_red else ramp(np.array([0.5]), stops)[0])
        if feathery:
            frond(cv, pts[1][0], pts[1][1], dirs[1], L * 0.9, 0.6 + 0.001 * k, 0.9 * s + 0.5,
                  lambda b: ramp(np.array([b]), stops)[0], r, curl=np.sign(ang) * 0.4, pinnae=8, rach=0.18)
        else:
            ll = r.uniform(*leaf) * s
            leaf_at(cv, pts[-1][0], pts[-1][1], dirs[-1], ll, ll * 0.6, 0.6 + 0.01 * k,
                    ramp(np.array([r.uniform(0.3, 1.0)]), stops)[0], kind=leaf_kind)
    if root is not None and stage >= 3:
        rc = hexrgb(root)
        for k in range(r.integers(2, 4)):
            x = 8 + r.normal(0, 2.5)
            disc(cv, x, 15.6, r.uniform(0.9, 1.3), rc * r.uniform(0.85, 1.05), 0.2)
    if flowers and stage >= 3:
        for k in range(flowers[0]):
            px, py = 8 + r.normal(0, 3), r.uniform(8.5, 11.0)
            petals(cv, px, py, 5, 0.7, 0.55, hexrgb(flowers[1]), 0.95 + k * 0.001, kind='round', r=r)
            disc(cv, px, py, 0.2, hexrgb('#e6c43a'), 0.96)
    return cv


def berry_bush(seed, stage):
    r = rng(seed)
    cv = Canvas(wrap=False)
    sizes = [0.45, 0.7, 1.0, 1.0]
    s = sizes[stage]
    tw = hexrgb('#4a3626')
    tips = []
    for k in range(3 + stage * 2):
        pts, dirs = stem(cv, 8 + r.normal(0, 1.5), 16.3, r.uniform(-1.0, 1.0), r.uniform(5, 11) * s, 0.35,
                         r.uniform(-0.4, 0.4), 0.1, tw)
        tips += pts[3::2]
    for k, (tx, ty) in enumerate(tips):
        for j in range(2):
            ll = r.uniform(1.3, 2.0) * (0.6 + 0.4 * s)
            leaf_at(cv, tx, ty, r.uniform(-2.5, 2.5), ll, ll * 0.6, 0.5 + 0.001 * k, green(r, 0.2, 0.8), kind='ovate',
                    serr=0.15)
    if stage >= 2:
        col = hexrgb('#7a9b3a') if stage == 2 else hexrgb('#b8142a')
        for k in range(10 if stage == 3 else 6):
            tx, ty = tips[r.integers(len(tips))]
            disc(cv, tx + r.uniform(-0.8, 0.8), ty + r.uniform(-0.6, 0.8), r.uniform(0.45, 0.62), col * r.uniform(0.9, 1.1),
                 0.9 + k * 0.001)
    return cv


def wart(seed, stage):
    r = rng(seed)
    cv = Canvas(wrap=False)
    n = [3, 5, 8][stage]
    for k in range(n):
        x = 8 + r.normal(0, 3.0)
        L = r.uniform(3, 6) * (0.6 + 0.3 * stage)
        pts, dirs = stem(cv, x, 16.3, r.uniform(-0.5, 0.5), L, 0.9 + 0.2 * stage, r.uniform(-0.4, 0.4), r.uniform(0, 0.5),
                         hexrgb('#6e1414'))
        disc(cv, pts[-1][0], pts[-1][1], 0.9 + 0.35 * stage, hexrgb('#8f1d1d') * r.uniform(0.85, 1.15), 0.8 + k * 0.01,
             speckle=0.2, seed=seed + k)
    return cv


# ------------------------------------------------------------------ shrubs, dry plants, mushrooms
def dead_bush(seed):
    r = rng(seed)
    cv = Canvas(wrap=False)
    col = hexrgb('#6e4f2e')

    def branch(x, y, ang, L, w, depth):
        pts, dirs = stem(cv, x, y, ang, L, w, r.uniform(-0.6, 0.6), 0.1 * depth, col * r.uniform(0.85, 1.15), steps=6)
        if depth < 3:
            for k in range(2):
                i = r.integers(2, 6)
                branch(pts[i][0], pts[i][1], dirs[i] + r.choice([-1, 1]) * r.uniform(0.4, 0.9), L * 0.6, w * 0.65,
                       depth + 1)
    for k in range(4):
        branch(8 + r.uniform(-1, 1), 16.3, r.uniform(-0.7, 0.7), r.uniform(6, 9), 0.45, 0)
    return cv


def mushroom(seed, cap, *, spots=False, flat=False):
    r = rng(seed)
    cv = Canvas(wrap=False)
    stem(cv, 8, 16.3, 0.0, 6.5, 1.3, 0.0, 0.1, hexrgb('#e2d9c4'))
    c = hexrgb(cap)
    ix, xs, ys = cv.window(8, 9.6, 5.0)
    if flat:
        m = ((np.abs(xs - 8) / 4.6) ** 2 + ((ys - 9.8) / 1.5) ** 2 <= 1) & (ys <= 10.6)
    else:
        m = ((np.abs(xs - 8) / 3.6) ** 2 + ((ys - 10.2) / 3.0) ** 2 <= 1) & (ys <= 10.6)
    sh = np.clip(0.75 + 0.3 * (10.6 - ys) / 4 - 0.15 * np.abs(xs - 8) / 4, 0.5, 1.1)
    col = c * sh[..., None]
    if spots:
        for k in range(6):
            sx, sy = 8 + r.uniform(-2.8, 2.8), r.uniform(7.6, 10.0)
            sp = (xs - sx) ** 2 + (ys - sy) ** 2 < r.uniform(0.18, 0.3)
            col = np.where(sp[..., None], hexrgb('#f3eee2'), col)
    gill = (ys > 10.0) & m
    col = np.where(gill[..., None], col * 0.7, col)
    cv.put(ix, m.astype(F32), col, 0.5)
    return cv


def reeds(seed):
    r = rng(seed)
    cv = Canvas(wrap=False)
    for k, x in enumerate((2.0, 6.0, 10.0, 14.0)):
        x += r.uniform(-0.4, 0.4)
        base = hexrgb('#8fbf5a') * r.uniform(0.9, 1.05)
        cv.stroke([(x, 17), (x, -1)], [1.5, 1.5], 0.2 + 0.01 * k, rgb=base, shade_along=0.0)
        for j in range(2):
            ny = r.uniform(1, 15)
            ix, xs, ys = cv.window(x, ny, 1.2)
            node = (np.abs(ys - ny) < 0.18) & (np.abs(xs - x) < 0.85)
            cv.put(ix, node.astype(F32), base * 0.7, 0.3)
        if r.uniform() < 0.6:
            y = r.uniform(3, 13)
            leaf_at(cv, x, y, r.choice([-1, 1]) * r.uniform(0.5, 0.9), r.uniform(3, 5), 0.8, 0.4, base * 1.05)
    return cv


def vine(seed):
    r = rng(seed)
    cv = Canvas()
    for k in range(4):
        x = 2 + k * 4 + r.uniform(-1, 1)
        pts = [(x + 0.8 * np.sin(t * 0.9 + k), t) for t in np.linspace(-1, 17, 12)]
        cv.stroke(pts, [0.3] * len(pts), 0.1, lum=0.35)
        for j in range(10):
            px, py = pts[r.integers(1, len(pts) - 1)]
            ll = r.uniform(1.4, 2.4)
            draw_leaf(cv, px, py, r.uniform(0, 2 * np.pi), ll, ll * 0.8, 0.5 + 0.01 * j + 0.1 * k, r.uniform(0.6, 1.0),
                      kind='lobed', lobes=2)
    return cv


def lily_pad(seed):
    cv = Canvas(wrap=False)
    ix, xs, ys = cv.window(8, 8, 7.5)
    d = np.sqrt((xs - 8) ** 2 + (ys - 8.4) ** 2)
    ang = np.arctan2(ys - 8.4, xs - 8)
    notch = np.abs(((ang + np.pi / 2 + np.pi) % (2 * np.pi)) - np.pi) < 0.28
    m = (d < 6.6 + 0.25 * np.sin(ang * 5)) & ~(notch & (d > 0.6))
    veins = np.abs(((ang * 9 / (2 * np.pi)) % 1.0) - 0.5) < 0.05
    lum = 0.75 + 0.2 * (1 - d / 6.6) - 0.12 * veins
    cv.put(ix, m.astype(F32), np.repeat(lum[..., None], 3, axis=-1), 0.5)
    return cv


def litter(seed, grey=True, colours=None, quads=True):
    """Fallen leaves / petals in four quadrant clusters (the block shows 1–4 of them)."""
    r = rng(seed)
    cv = Canvas(wrap=False)
    centres = [(4, 4), (12, 4), (4, 12), (12, 12)]
    for qi, (cx, cy) in enumerate(centres):
        for k in range(r.integers(5, 8)):
            px, py = cx + r.uniform(-2.0, 2.0), cy + r.uniform(-2.0, 2.0)
            col = None if colours is None else ramp(np.array([r.uniform(0, 1)]), colours)[0]
            draw_leaf(cv, px, py, r.uniform(0, 2 * np.pi), r.uniform(2.4, 3.2), r.uniform(1.5, 2.0), 0.5 + 0.1 * k,
                      r.uniform(0.7, 1.0), kind='ovate', colour=col)
    return cv


def petal_patch(seed, rgb, centre='#f2d16b', small=0.9):
    """Pink petals / wildflowers: four quadrant clusters of tiny upward-facing blossoms."""
    r = rng(seed)
    cv = Canvas(wrap=False)
    centres = [(4, 4), (12, 4), (4, 12), (12, 12)]
    c = hexrgb(rgb)
    for qi, (cx, cy) in enumerate(centres):
        for k in range(r.integers(2, 4)):
            px, py = cx + r.uniform(-1.8, 1.8), cy + r.uniform(-1.8, 1.8)
            petals(cv, px, py, 5, small * 1.1, small, c * r.uniform(0.9, 1.08), 0.5 + 0.1 * k, rot=r.uniform(0, 1),
                   kind='round', r=r)
            disc(cv, px, py, 0.25, hexrgb(centre), 0.6 + 0.1 * k)
    return cv


# ------------------------------------------------------------------ cactus
def cactus(seed, face):
    x0, x1 = 1.0, 15.0
    from engine.draw import X, Y
    if face == 'side':
        rib = 0.5 + 0.5 * np.cos(2 * np.pi * (X - x0) / (x1 - x0) * 4)
        t = 0.45 + 0.25 * rib + 0.05 * fbm(N, (4, 16), seed, 3)
        alb = ramp(np.clip(t, 0, 1), [(0, '#2d4f1b'), (0.5, '#4e7a2c'), (1, '#77a548')])
        h = 0.4 + 0.5 * rib
        inside = (X >= x0) & (X <= x1)
        sp = np.zeros((N, N), F32)
        for k in range(4):
            xr = x0 + (k + 0.5) * (x1 - x0) / 4
            for j in range(4):
                yr = (j + 0.5 + 0.5 * (k % 2)) * 4 % 16
                sp = np.maximum(sp, (np.sqrt((X - xr) ** 2 + (Y - yr) ** 2) < 0.45).astype(F32))
                for a in (-0.6, 0.0, 0.6):
                    seg = np.abs((X - xr) * np.cos(a) - (Y - yr) * np.sin(a)) < 0.06
                    seg &= (np.abs((X - xr) * np.sin(a) + (Y - yr) * np.cos(a)) < 1.0)
                    sp = np.maximum(sp, seg.astype(F32) * 0.8)
        alb = mix(alb, hexrgb('#ece6c4'), sp)
        edge_spines = np.zeros((N, N), bool)
        for j in range(4):
            yr = j * 4 + 2
            edge_spines |= (np.abs(Y - yr) < 0.5) & ((X < x0) | (X > x1))
        alpha = (inside | edge_spines).astype(F32)
        alb = np.where(edge_spines[..., None], hexrgb('#e2dcb6'), alb)
        return Tex(alb, h, alpha, light='top', bump=1.4, ao=0.5, cutout=True)
    inside = (X >= x0) & (X <= x1) & (Y >= x0) & (Y <= x1)
    d = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
    ang = np.arctan2(Y - 8, X - 8)
    rib = 0.5 + 0.5 * np.cos(ang * 8)
    t = 0.45 + 0.2 * rib * smoothstep(1.0, 4.0, d) + 0.08 * fbm(N, 10, seed, 3) + (0.2 if face == 'bottom' else 0)
    alb = ramp(np.clip(t, 0, 1), [(0, '#2d4f1b'), (0.5, '#4e7a2c'), (1, '#86b555')])
    centre = d < 1.6
    alb = mix(alb, hexrgb('#9fbf6a'), centre.astype(F32) * 0.6)
    h = 0.5 + 0.3 * rib * smoothstep(1, 5, d)
    return Tex(alb, h, inside.astype(F32), light='over', bump=1.2, ao=0.5, cutout=True)


# ------------------------------------------------------------------ model-mapped fills
def fill_mask(path, rgb_fn, seed=0, light='top'):
    """Paint our own material inside the vanilla UV island silhouette (functional layout only)."""
    m = mask_of(path).astype(F32)
    rgb = rgb_fn(seed)
    mean, lum, _ = cal(path)
    rgb = match_mean(rgb, lum, m > 0.5)
    return Tex(rgb, 0.5 + 0.1 * fbm(N, 8, seed, 3), m, light=light, bump=0.8, ao=0.3, cutout=True, sharpen=0.2)


def mat(stops, freq=12, seed=0):
    return lambda s: ramp(np.clip(0.5 + 0.35 * fbm(N, freq, s + seed, 3), 0, 1), stops)


# ------------------------------------------------------------------ registration
def _tint(path_carried, base_path, tex):
    """Carried (inventory) version: bake the tint ratio between the vanilla carried and grey means."""
    cm, clum, _ = cal(path_carried)
    gm, glum, _ = cal(base_path)
    k = np.clip(cm / max(glum, 1e-3), 0, 2)
    return tex.but(albedo=match_mean(np.clip(tex.albedo * k, 0, 1), clum, tex.alpha > 0.5))


def register(R):
    grey_tuft = lambda s: finish(grass_tuft(s), 'tallgrass', grey=True)
    R.block('tallgrass', lambda v: grey_tuft(900), cutout=True)
    R.block('tallgrass_carried', lambda v: _tint('tallgrass_carried', 'tallgrass', grey_tuft(900)), cutout=True)
    grey_fern = lambda s: finish(fern_plant(s), 'fern', grey=True)
    R.block('fern', lambda v: grey_fern(901), cutout=True)
    R.block('fern_carried', lambda v: _tint('fern_carried', 'fern', grey_fern(901)), cutout=True)

    def tall_grass(part):
        t = Tall(2)
        grass_tuft(902, t, count=46, h=(16.0, 28.0), y0=32.4, x_spread=3.0, lean=0.35)
        return finish(t.part(part), 'double_plant_grass_top' if part == 0 else 'double_plant_grass_bottom', grey=True)
    R.block('double_plant_grass_top', lambda v: tall_grass(0), cutout=True)
    R.block('double_plant_grass_bottom', lambda v: tall_grass(1), cutout=True)
    R.block('double_plant_grass_carried', lambda v: _tint('double_plant_grass_carried', 'double_plant_grass_top',
                                                          tall_grass(0)), cutout=True)

    def tall_fern(part):
        t = Tall(2)
        fern_plant(903, t, fronds=8, size=2.0, y0=32.3, curl=(0.1, 0.45), leaf=1.3)
        fern_plant(904, t, fronds=6, size=1.1, y0=23.0, curl=(0.05, 0.3), leaf=1.2, z0=-0.5)
        return finish(t.part(part), 'double_plant_fern_top' if part == 0 else 'double_plant_fern_bottom', grey=True)
    R.block('double_plant_fern_top', lambda v: tall_fern(0), cutout=True)
    R.block('double_plant_fern_bottom', lambda v: tall_fern(1), cutout=True)
    R.block('double_plant_fern_carried', lambda v: _tint('double_plant_fern_carried', 'double_plant_fern_top',
                                                         tall_fern(0)), cutout=True)

    flowers = {
        'flower_dandelion': (head_pom('#f2c624'), dict()),
        'golden_dandelion': (head_pom('#d89a1c', n=30), dict()),
        'flower_rose': (head_poppy('#c8261d'), dict(leaf_kind='lobed')),
        'flower_rose_blue': (head_poppy('#2e8fae', centre='#14303a'), dict()),
        'flower_blue_orchid': (head_orchid('#2fa6c9'), dict(leaf_len=(3.5, 4.8))),
        'flower_allium': (head_cluster('#a46ad2', n=16, rad=1.9, floret=0.36), dict(leaves=1, stem_h=(9.5, 11.0))),
        'flower_houstonia': (head_cluster('#c5d8f2', n=5, rad=1.6, floret=0.48, centre='#f2d65a'),
                             dict(stem_h=(6.0, 7.5), leaves=3, leaf_len=(1.6, 2.4))),
        'flower_tulip_red': (head_cup('#cf2b23'), dict(leaf_len=(4.0, 5.2), leaf_w=0.38)),
        'flower_tulip_orange': (head_cup('#e8742a'), dict(leaf_len=(4.0, 5.2), leaf_w=0.38)),
        'flower_tulip_white': (head_cup('#f1efe4'), dict(leaf_len=(4.0, 5.2), leaf_w=0.38)),
        'flower_tulip_pink': (head_cup('#e8a3bf'), dict(leaf_len=(4.0, 5.2), leaf_w=0.38)),
        'flower_oxeye_daisy': (head_daisy(), dict()),
        'flower_cornflower': (head_ray('#3d64d4'), dict()),
        'flower_lily_of_the_valley': (head_bells(), dict(leaf_len=(4.5, 6.0), leaf_w=0.45, stem_h=(5.5, 7.0))),
        'flower_paeonia': (head_rosette('#e6b2c8', size=2.2), dict()),
        'flower_wither_rose': (head_rosette('#2a2622', size=2.0), dict(stem_rgb='#2c3220')),
        'torchflower': (head_torch('#e8742a'), dict(stem_rgb='#4a6a3a')),
        'cactus_flower': (head_rosette('#ec8fa7', size=2.6, layers=2), dict(leaves=0, stem_h=(3.0, 4.0),
                                                                             stem_rgb='#5f8a3a')),
    }
    for i, (name, (head, kw)) in enumerate(flowers.items()):
        R.block(name, lambda v, i=i, head=head, kw=kw, name=name: finish(flower(920 + i, head, **kw), name),
                cutout=True)

    def tall_flower(name_top, name_bottom, head, part, seed, n=3):
        t = Tall(2)
        r = rng(seed)
        for k in range(n):
            flower(seed + k, head, cv=t, stem_h=(18.0, 26.0), x=8 + r.uniform(-3.5, 3.5), y0=32.3, leaves=5,
                   leaf_len=(3.5, 5.0), sway=1.0, z0=k)
        return finish(t.part(part), name_top if part == 0 else name_bottom)
    for j, (top, bottom, head) in enumerate((
            ('double_plant_paeonia_top', 'double_plant_paeonia_bottom', head_rosette('#e6a7c4', size=2.6)),
            ('double_plant_rose_top', 'double_plant_rose_bottom', head_rosette('#c22a2a', size=2.0)),
            ('double_plant_syringa_top', 'double_plant_syringa_bottom', head_panicle('#c08ad8')))):
        R.block(top, lambda v, top=top, bottom=bottom, head=head, j=j: tall_flower(top, bottom, head, 0, 960 + 10 * j),
                cutout=True)
        R.block(bottom, lambda v, top=top, bottom=bottom, head=head, j=j: tall_flower(top, bottom, head, 1,
                                                                                      960 + 10 * j), cutout=True)

    # sunflower: stalk halves, plus the head's front and back on their fixed discs
    def sunflower(part):
        cv = Canvas(wrap=False)
        r = rng(990)
        g = hexrgb('#4e7d2a')
        if part in ('bottom', 'top'):
            y_top = 6.0 if part == 'top' else -1.0
            stem(cv, 8, 16.5, 0.0, 16.5 - y_top, 1.2, 0.0, 0.1, g)
            for k in range(2 if part == 'bottom' else 1):
                y = 12 - 6 * k if part == 'bottom' else 12
                leaf_at(cv, 8, y, (-1) ** k * 1.0, 4.5, 2.4, 0.3 + 0.01 * k, g * 1.1, kind='ovate')
            return finish(cv, 'double_plant_sunflower_' + part)
        if part == 'front':
            petals(cv, 8, 8, 16, 3.9, 1.0, hexrgb('#f2c21d'), 0.1, kind='lanceolate', r=r)
            disc(cv, 8, 8, 2.5, hexrgb('#4a2a12'), 0.2, speckle=0.35, seed=991)
        else:
            petals(cv, 8, 8, 16, 3.9, 1.0, hexrgb('#d9ae22'), 0.1, kind='lanceolate', r=r)
            disc(cv, 8, 8, 2.6, hexrgb('#5f8a35'), 0.2)
        t = finish(cv, 'double_plant_sunflower_' + part)
        m = mask_of('double_plant_sunflower_' + part)
        return t.but(alpha=(t.alpha * blur(m.astype(F32), 2.0) > 0.25).astype(F32) * t.alpha)
    for part in ('bottom', 'top', 'front', 'back'):
        R.block('double_plant_sunflower_' + part, lambda v, part=part: sunflower(part), cutout=True)

    # saplings
    def leaf_rgb(stops):
        return lambda b: ramp(np.array([b]), stops)[0]
    saps = {
        'sapling_oak': (leaf_rgb(GREENS), dict(kind='lobed')),
        'sapling_birch': (leaf_rgb([(0, '#4a7a2a'), (1, '#8cc05a')]), dict(kind='ovate', trunk='#d8d2c4')),
        'sapling_spruce': (leaf_rgb([(0, '#1f3a20'), (1, '#3f6a3a')]), dict(kind='needles', trunk='#4a3220')),
        'sapling_jungle': (leaf_rgb([(0, '#1f4a12'), (1, '#3f7a20')]), dict(kind='lanceolate')),
        'sapling_acacia': (leaf_rgb([(0, '#5a6a12'), (1, '#8a9a28')]), dict(kind='ovate', trunk='#6e6a62')),
        'sapling_roofed_oak': (leaf_rgb([(0, '#1f3a12'), (1, '#3c6a20')]), dict(kind='lobed', trunk='#3a2a1a')),
        'cherry_sapling': (leaf_rgb([(0, '#d784a9'), (1, '#f6c4d6')]), dict(kind='round', trunk='#4a2a30')),
        'pale_oak_sapling': (leaf_rgb([(0, '#5f665c'), (1, '#a2aa9a')]), dict(kind='lobed', trunk='#5a5250')),
        'poplar_sapling': (leaf_rgb([(0, '#b85a1c'), (1, '#e8a03a')]), dict(kind='deltoid', trunk='#5a4632')),
    }
    for i, (name, (fn, kw)) in enumerate(saps.items()):
        R.block(name, lambda v, i=i, fn=fn, kw=kw, name=name: finish(sapling(1000 + i, fn, **kw), name), cutout=True)

    # crops
    for st in range(8):
        R.block(f'wheat_stage_{st}', lambda v, st=st: finish(wheat(1100 + st, st), f'wheat_stage_{st}'), cutout=True)
    for st in range(4):
        R.block(f'carrots_stage_{st}', lambda v, st=st: finish(
            leafy_crop(1110 + st, st, feathery=True, root='#e07a22' if st == 3 else None), f'carrots_stage_{st}'),
            cutout=True)
        R.block(f'potatoes_stage_{st}', lambda v, st=st: finish(
            leafy_crop(1120 + st, st, flowers=(4, '#efe9f2') if st == 3 else None), f'potatoes_stage_{st}'),
            cutout=True)
        R.block(f'beetroots_stage_{st}', lambda v, st=st: finish(
            leafy_crop(1130 + st, st, leaf=(2.8, 3.8), vein_red=True, root='#7a1630' if st == 3 else None),
            f'beetroots_stage_{st}'), cutout=True)
        R.block(f'sweet_berry_bush_stage{st}', lambda v, st=st: finish(berry_bush(1140 + st, st),
                                                                        f'sweet_berry_bush_stage{st}'), cutout=True)
    R.block('carrots_stage3', lambda v: finish(leafy_crop(1113, 3, feathery=True, root='#e07a22'), 'carrots_stage3'),
            cutout=True)
    for st in range(3):
        R.block(f'nether_wart_stage_{st}', lambda v, st=st: finish(wart(1150 + st, st), f'nether_wart_stage_{st}'),
                cutout=True)
    R.block('torchflower_crop_stage_0', lambda v: finish(leafy_crop(1160, 0, count=(3,)), 'torchflower_crop_stage_0'),
            cutout=True)
    R.block('torchflower_crop_stage_1', lambda v: finish(leafy_crop(1161, 1, count=(3, 5)),
                                                         'torchflower_crop_stage_1'), cutout=True)

    # shrubs and dry plants
    R.block('deadbush', lambda v: finish(dead_bush(1170), 'deadbush'), cutout=True)
    R.block('short_dry_grass', lambda v: finish(grass_tuft(1171, count=16, h=(4.0, 8.0), stops=DRY), 'short_dry_grass'),
            cutout=True)
    R.block('tall_dry_grass', lambda v: finish(grass_tuft(1172, count=30, h=(9.0, 15.0), stops=DRY), 'tall_dry_grass'),
            cutout=True)

    def bush(seed, path, grey=True, stops=GREENS):
        r = rng(seed)
        cv = Canvas(wrap=False)
        tw = np.full(3, 0.3, F32)
        for k in range(7):
            pts, dirs = stem(cv, 8 + r.normal(0, 1.5), 16.3, r.uniform(-1.1, 1.1), r.uniform(6, 11), 0.4,
                             r.uniform(-0.4, 0.4), 0.1, tw)
            for (px, py) in pts[2:] + pts[4:]:
                ll = r.uniform(1.8, 2.6)
                leaf_at(cv, px + r.uniform(-1, 1), py + r.uniform(-1, 1), r.uniform(-2.8, 2.8), ll, ll * 0.6,
                        0.5 + r.uniform(0, 0.4), np.full(3, r.uniform(0.6, 1.0), F32) if grey else green(r, stops=stops),
                        kind='ovate')
        return finish(cv, path, grey=grey)
    R.block('bush', lambda v: bush(1173, 'bush'), cutout=True)
    R.block('firefly_bush', lambda v: bush(1174, 'firefly_bush', grey=False,
                                           stops=[(0, '#1f2a12'), (0.5, '#36461d'), (1, '#55662c')]), cutout=True)

    def fireflies(f, n):
        r = rng(1175)
        pts = [(r.uniform(2, 14), r.uniform(2, 13), r.uniform(0, 1)) for _ in range(4)]
        rgb = np.zeros((N, N, 3), F32)
        a = np.zeros((N, N), F32)
        from engine.draw import X, Y
        for (x, y, ph) in pts:
            on = 0.5 + 0.5 * np.sin(2 * np.pi * (f / n + ph))
            if on < 0.45:
                continue
            d = np.sqrt((X - (x + 0.4 * np.sin(f / n * 6.28 + ph * 6))) ** 2 + (Y - y) ** 2)
            m = (d < 0.45).astype(F32)
            rgb = np.maximum(rgb, m[..., None] * hexrgb('#f6f08a') * on)
            a = np.maximum(a, m)
        return Tex(rgb, None, a, light='none', cutout=True, sharpen=0.0)
    R.anim('firefly_bush_firefly', fireflies, 10, cutout=True)

    R.block('leaf_litter', lambda v: finish(litter(1176), 'leaf_litter', grey=True), cutout=True)
    R.block('pink_petals', lambda v: finish(petal_patch(1177, '#f4a7c8', centre='#f7e27a'), 'pink_petals'), cutout=True)
    R.block('wildflowers', lambda v: finish(petal_patch(1178, '#f2e19a', centre='#e8a62a'), 'wildflowers'), cutout=True)
    for stemname in ('pink_petals_stem', 'wildflowers_stem'):
        R.block(stemname, lambda v, s=stemname: fill_mask(s, lambda q: np.full((N, N, 3), 0.6, F32)), cutout=True)

    R.block('mushroom_brown', lambda v: finish(mushroom(1180, '#9a7254', flat=True), 'mushroom_brown'), cutout=True)
    R.block('mushroom_red', lambda v: finish(mushroom(1181, '#c22b25', spots=True), 'mushroom_red'), cutout=True)
    R.block('reeds', lambda v: finish(reeds(1182), 'reeds'), cutout=True)
    R.block('vine', lambda v: finish(vine(1183), 'vine', grey=True), cutout=True)
    R.block('vine_carried', lambda v: _tint('vine_carried', 'vine', finish(vine(1183), 'vine', grey=True)), cutout=True)
    R.block('waterlily', lambda v: finish(lily_pad(1184), 'waterlily', grey=True), cutout=True)
    R.block('carried_waterlily', lambda v: _tint('carried_waterlily', 'waterlily',
                                                 finish(lily_pad(1184), 'waterlily', grey=True)), cutout=True)
    for face in ('side', 'top', 'bottom'):
        R.block('cactus_' + face, lambda v, face=face: cactus(1185, face), cutout=True)

    # stems of melons and pumpkins (grey, tinted by age in game)
    def gourd_stem(connected, seed):
        cv = Canvas(wrap=False)
        g = np.full(3, 0.7, F32)
        if connected:
            pts = [(8, 16.5), (8, 12), (7.6, 9.5), (5.5, 8.0), (2.5, 7.4), (-0.5, 7.2)]
            cv.stroke(pts, [0.9, 0.85, 0.8, 0.75, 0.7, 0.7], 0.2, rgb=g)
            leaf_at(cv, 6.0, 8.0, 0.4, 2.6, 1.8, 0.3, g * 1.1, kind='lobed', lobes=2)
        else:
            stem(cv, 8, 16.5, 0.0, 15.0, 0.9, 0.1, 0.2, g)
            for k in range(3):
                leaf_at(cv, 8, 6 + 3 * k, (-1) ** k * 1.1, 2.6, 1.8, 0.3 + 0.01 * k, g * 1.1, kind='lobed', lobes=2)
        return cv
    for fruit in ('melon', 'pumpkin'):
        R.block(f'{fruit}_stem_connected', lambda v, fruit=fruit: finish(gourd_stem(True, 1190), f'{fruit}_stem_connected',
                                                                         grey=True), cutout=True)
        R.block(f'{fruit}_stem_disconnected', lambda v, fruit=fruit: finish(gourd_stem(False, 1191),
                                                                            f'{fruit}_stem_disconnected', grey=True),
                cutout=True)
