"""Stone family: igneous and metamorphic rocks, polished faces, masonry, pillars and carved panels."""
import numpy as np

from engine.noise import (F32, fbm, ridged, worley, cell_random, blur, warped_coords, norm01, smoothstep,
                          rng)
from engine.color import ramp, mix, vary, match_mean, hexrgb
from engine.material import Tex, MASTER
from engine.draw import X, Y, rect, circle, fractures
from recipes.terrain import rock, fissures, speckles, moss, stone, cobblestone, edged

N = MASTER


# ------------------------------------------------------------------ crystalline rocks
def crystalline(seed, minerals, *, freq=46, big=None, mottling=0.5, bump=1.0, light='top', target=None,
                cracks=0.4, boundary=0.2, contrast=0.6):
    """Granular rock built from mineral grains.

    minerals: [(weight, '#hex'), ...] for the matrix grains; big: optional (freq, density, [(w, '#hex')])
    for sparse larger crystals (phenocrysts).
    """
    x, y = warped_coords(N, 0.03, seed, freq=4)
    f1, f2, cid = worley(N, freq, seed + 1, 1.0, x, y)
    w = np.array([m[0] for m in minerals], F32)
    cum = np.cumsum(w) / w.sum()
    pick = np.searchsorted(cum, cell_random(cid, seed + 2))
    cols = np.array([hexrgb(m[1]) for m in minerals], F32)
    avg = (cols * (w / w.sum())[:, None]).sum(0)
    cols = avg + (cols - avg) * contrast
    alb = cols[np.clip(pick, 0, len(minerals) - 1)]
    alb = alb * (0.9 + 0.2 * cell_random(cid, seed + 3))[..., None]
    edge = 1 - smoothstep(0.0, 0.12, f2 - f1)
    h = 0.5 + 0.15 * cell_random(cid, seed + 4) - 0.1 * edge
    if big:
        bf, dens, bmin = big
        g1, g2, gid = worley(N, bf, seed + 5, 1.0, x, y)
        bpick = cell_random(gid, seed + 6) < dens
        bw = np.array([m[0] for m in bmin], F32)
        bcum = np.cumsum(bw) / bw.sum()
        bsel = np.searchsorted(bcum, cell_random(gid, seed + 7))
        bcols = np.array([hexrgb(m[1]) for m in bmin], F32)[np.clip(bsel, 0, len(bmin) - 1)]
        bcols = avg + (bcols - avg) * (contrast + 0.15)
        shape = (1 - smoothstep(0.26, 0.36, g1)) * bpick
        alb = mix(alb, bcols * (0.9 + 0.2 * cell_random(gid, seed + 8))[..., None], shape)
        h = h + 0.12 * shape
    mot = fbm(N, 3, seed + 9, 5, x=x, y=y)
    mid = fbm(N, 8, seed + 10, 3)
    alb = alb * (1 + mottling * (0.12 * mot + 0.06 * mid))[..., None]
    alb = mix(alb, alb * 0.8, edge * boundary)
    h = h + 0.15 * mot + 0.08 * mid
    if cracks:
        fis = fissures(N, seed + 11, 3, 0.96, 0.55, 0.6) * cracks
        alb = alb * (1 - 0.3 * fis[..., None])
        h = h - 0.15 * fis
    if target:
        alb = match_mean(alb, target)
    return Tex(alb, norm01(h), light=light, bump=bump, ao=0.5)


def granite(seed=200, target=0.44):
    return crystalline(seed, [(5, '#b8775f'), (3, '#9a5c48'), (2, '#c99a86'), (2, '#8d8580'), (0.8, '#2b2422'),
                              (0.8, '#d9c9bd')],
                       freq=48, big=(10, 0.3, [(3, '#c4826a'), (1, '#a86650'), (1, '#d8b2a0')]), target=target,
                       mottling=0.8)


def diorite(seed=210, target=0.74):
    return crystalline(seed, [(6, '#d9d8d6'), (3, '#c4c3c1'), (2, '#eeeeec'), (0.7, '#3d3d3f'), (0.6, '#8a8a8d')],
                       freq=44, big=(12, 0.16, [(1, '#3a3a3d'), (1, '#55555a')]), mottling=0.5, target=target,
                       boundary=0.12, contrast=0.7)


def andesite(seed=220, target=0.53):
    return crystalline(seed, [(6, '#86868a'), (4, '#7a7a7d'), (2, '#97979a'), (0.7, '#4c4c50'), (0.6, '#bdbdbd')],
                       freq=52, big=(13, 0.14, [(2, '#b9b9b7'), (1, '#55565a')]), mottling=0.9, target=target,
                       boundary=0.08, contrast=0.55)


def polished(base, seed, *, border=0.55, relief=0.25, gloss=0.18, target=None, frame=0.12):
    """A polished face of a rock: flattened relief, clearer colour, crisp chamfered border."""
    b = np.minimum(np.minimum(X, 16 - X), np.minimum(Y, 16 - Y))
    chamfer = smoothstep(0.0, border, b)
    lip = smoothstep(border, border + 0.35, b)
    alb = base.albedo * (0.92 + 0.08 * chamfer[..., None])
    alb = mix(alb, alb * 1.08, (1 - lip) * chamfer * frame * 4)
    h = 0.6 + relief * (base.height - 0.5) * 0.4 + 0.4 * chamfer
    wear = smoothstep(0.75, 0.95, fbm(N, 12, seed, 3)) * 0.08
    alb = alb * (1 - wear[..., None])
    if target:
        alb = match_mean(alb, target)
    return Tex(alb, norm01(h), light='top', bump=1.2, ao=0.45, gloss=gloss)


# ------------------------------------------------------------------ foliated / volcanic rocks
def deepslate(seed=230, face='side', target=0.32):
    x, y = warped_coords(N, 0.02, seed, freq=4)
    if face == 'side':
        fol = fbm(N, (14, 2), seed, 4, x=x, y=y)
        seams = smoothstep(0.93, 0.99, ridged(N, 1, seed + 1, 3, sharp=3, stretch=(9, 1)))
    else:
        fol = fbm(N, (2, 14), seed, 4, x=x, y=y)
        seams = smoothstep(0.93, 0.99, ridged(N, 1, seed + 1, 3, sharp=3, stretch=(1, 9)))
    mot = fbm(N, 3, seed + 2, 4)
    fine = fbm(N, 48, seed + 3, 2)
    t = 0.5 + 0.12 * fol + 0.08 * mot + 0.05 * fine - 0.18 * seams
    alb = ramp(np.clip(t, 0, 1), [(0, '#1f1f24'), (0.4, '#38383e'), (0.7, '#4f4f55'), (1, '#6b6b70')])
    m, v = speckles(N, 40, seed + 4, 0.05, 0.3)
    alb = mix(alb, hexrgb('#7b7c80'), m * 0.4)
    h = 0.5 + 0.18 * fol + 0.1 * mot + 0.04 * fine - 0.25 * seams
    return Tex(match_mean(alb, target), norm01(h), light='top', bump=1.2, ao=0.55)


def tuff(seed=240, target=0.42):
    t = rock(seed, [(0.0, '#4b4d45'), (0.35, '#62655b'), (0.6, '#767a6e'), (0.85, '#8b8f82'), (1.0, '#a3a697')],
             mottling=0.8, cracks=0.3, pits=0.9, bump=1.1, ao=0.6,
             fleck=[(14, 0.10, 0.35, '#8a8475', 0.6), (24, 0.10, 0.3, '#3f403b', 0.6), (40, 0.08, 0.3, '#b5b3a6', 0.5)])
    return t.but(albedo=match_mean(t.albedo, target))


def calcite(seed=250, target=0.86):
    c = crystalline(seed, [(6, '#ecebe6'), (3, '#dcdbd4'), (2, '#f7f6f2'), (1, '#c9c7bd'), (0.3, '#b5b2a6')],
                    freq=40, mottling=0.6, cracks=0.2, boundary=0.15, bump=0.8, contrast=0.45,
                    big=(9, 0.25, [(1, '#f9f8f4'), (1, '#e2ddcf')]))
    veins = smoothstep(0.93, 0.99, ridged(N, 2, seed + 30, 5, sharp=2.5))
    alb = mix(c.albedo, hexrgb('#b9b5a9'), veins * 0.35)
    return c.but(albedo=match_mean(alb, target))


def dripstone(seed=260, target=0.44):
    t = rock(seed, [(0.0, '#4e3a2e'), (0.3, '#6e5444'), (0.6, '#8b6f5c'), (0.85, '#a68a74'), (1.0, '#bea38c')],
             mottling=0.6, cracks=0.3, pits=0.6, bump=1.1, ao=0.6)
    x, y = warped_coords(N, 0.04, seed + 5, freq=3)
    flow = fbm(N, (7, 1), seed + 6, 4, x=x, y=y)
    alb = t.albedo * (1 + 0.1 * flow[..., None])
    rings = np.sin(2 * np.pi * (y * 9 + 0.8 * fbm(N, 3, seed + 7, 3)))
    alb = alb * (1 + 0.035 * rings[..., None])
    h = norm01(t.height + 0.12 * flow + 0.03 * rings)
    return t.but(albedo=match_mean(alb, target), height=h)


def basalt(seed=270, face='side', target=0.29, polish=False):
    x, y = warped_coords(N, 0.015, seed, freq=4)
    ves = smoothstep(0.62, 0.86, fbm(N, 26, seed + 2, 3))
    rough = fbm(N, 14, seed + 3, 4)
    if face == 'side':
        cols = fbm(N, (6, 1), seed, 4, x=x, y=y)
        grooves = smoothstep(0.9, 0.98, ridged(N, 1, seed + 1, 3, sharp=3, stretch=(6, 1)))
        t = 0.5 + 0.1 * cols - 0.16 * grooves + 0.07 * rough - 0.1 * ves
        h = 0.5 + 0.18 * cols - 0.3 * grooves + 0.1 * rough - 0.15 * ves
    else:
        from engine.draw import polygon
        hexa = polygon([(8 + 8.8 * np.cos(a), 8 + 8.8 * np.sin(a)) for a in np.arange(6) * np.pi / 3 + 0.2])
        rim = 1 - smoothstep(0.0, 0.6, blur(hexa, 2.0))
        t = 0.5 + 0.08 * rough - 0.12 * rim - 0.1 * ves + 0.04 * fbm(N, 40, seed + 4, 2)
        h = 0.5 + 0.1 * rough - 0.3 * rim - 0.15 * ves
    alb = ramp(np.clip(t, 0, 1), [(0, '#18181c'), (0.4, '#2f2f35'), (0.7, '#45454c'), (1, '#5f5f66')])
    if polish:
        h = 0.5 + 0.3 * (h - 0.5)
        alb = mix(alb, ramp(np.clip(t, 0, 1), [(0, '#2a2a30'), (1, '#55555c')]), 0.4)
    return Tex(match_mean(alb, target), norm01(h), light='top', bump=1.3 if not polish else 0.9, ao=0.6,
               gloss=0.12 if polish else 0.0)


def blackstone(seed=280, target=0.15, face='side'):
    t = rock(seed, [(0.0, '#0d0b0e'), (0.3, '#1d191e'), (0.6, '#2e282f'), (0.85, '#433b43'), (1.0, '#5a505a')],
             mottling=0.9, cracks=0.8, pits=0.5, bump=1.25, ao=0.6, strata=0.6 if face == 'side' else 0.0,
             fleck=[(30, 0.06, 0.3, '#6c6168', 0.5)])
    return t.but(albedo=match_mean(t.albedo, target))


# ------------------------------------------------------------------ masonry
def bond(rows, length, offset, warp=0.12, seed=0, lengths=None):
    """Brick layout in block units. rows: list of course heights summing to 16. Returns
    (distance to the brick's edge, brick id, u, v, course index)."""
    from engine.noise import fbm as _fbm
    wx = X + warp * 16 * 0.01 * _fbm(N, 4, seed + 1, 3)
    wy = Y + warp * 16 * 0.01 * _fbm(N, 4, seed + 2, 3)
    bounds = np.concatenate([[0], np.cumsum(rows)])
    course = np.clip(np.searchsorted(bounds, wy % 16, side='right') - 1, 0, len(rows) - 1)
    y0 = bounds[course]
    rh = np.asarray(rows, F32)[course]
    v = (wy % 16) - y0
    L = length if lengths is None else np.asarray(lengths, F32)[course]
    off = (course % 2) * offset if np.isscalar(offset) else np.asarray(offset, F32)[course]
    xs = (wx + off) % 16
    col = np.floor(xs / L)
    u = xs - col * L
    d = np.minimum(np.minimum(u, L - u), np.minimum(v, rh - v))
    bid = (course * 64 + col).astype(np.int64)
    return d.astype(F32), bid, u.astype(F32), v.astype(F32), course


def masonry(seed, rows, length, offset, face, *, mortar=0.5, mortar_col=('#5d5953', '#77726a'), bevel=0.7,
            chip=0.5, tone=0.12, target=None, lengths=None, warp=0.12, recess=0.45, light='top', joint_dark=0.25):
    """Bricks/tiles: `face` is a Tex supplying the stone surface (albedo + height) for every brick."""
    d, bid, u, v, course = bond(rows, length, offset, warp, seed, lengths)
    half = mortar / 2
    noise_edge = 0.25 * fbm(N, 10, seed + 3, 3)
    chips = smoothstep(0.45, 0.8, fbm(N, 7, seed + 4, 4)) * chip
    dd = d - half - chips * smoothstep(1.4, 0.0, d - half) * 0.9 + 0.08 * noise_edge
    inside = smoothstep(-0.05, 0.08, dd)
    prof = smoothstep(0.0, bevel, dd)
    r = rng(seed + 5)
    tones = r.uniform(-1, 1, int(bid.max()) + 1).astype(F32)
    hue = r.uniform(-1, 1, int(bid.max()) + 1).astype(F32)
    bt = tones[bid]
    alb = face.albedo * (1 + tone * bt)[..., None]
    alb = vary(alb, dh=0.01 * hue[bid])
    mcol = ramp(0.5 + 0.4 * fbm(N, 24, seed + 6, 3), [(0, mortar_col[0]), (1, mortar_col[1])])
    alb = mix(alb, alb * (1 - joint_dark), (1 - prof) * inside * 0.6)
    alb = mix(mcol, alb, inside)
    h = (1 - recess) + recess * prof + 0.25 * (face.height - 0.5) * inside
    h = h * inside + (0.12 + 0.05 * fbm(N, 30, seed + 7, 2)) * (1 - inside)
    t = Tex(alb, norm01(h), light=light, bump=1.4, ao=0.65)
    t.mortar = 1 - inside
    t.dist = dd
    t.bid = bid
    if target:
        t.albedo = match_mean(t.albedo, target)
    return t


def cracked(t, seed, amount=1.0, target=None):
    lines, sheet = fractures(seed, int(4 + 4 * amount), (3, 9), (0.09, 0.16), kinks=6, jag=1.4, plane=0.25)
    mortar = getattr(t, 'mortar', np.zeros_like(lines))
    lines = lines * (1 - mortar)
    alb = t.albedo * (1 - 0.25 * lines[..., None]) * (1 - 0.08 * sheet[..., None] * (1 - mortar[..., None]))
    h = t.height - 0.25 * lines
    spall = smoothstep(0.78, 0.9, fbm(N, 6, seed + 1, 4)) * (1 - mortar) * amount
    alb = alb * (1 - 0.15 * spall[..., None])
    h = h - 0.15 * spall
    if target:
        alb = match_mean(alb, target)
    return t.but(albedo=alb.astype(F32), height=norm01(h))


def mossy(t, seed, amount=0.7, target=None):
    m = moss(seed + 3)
    mortar = getattr(t, 'mortar', np.zeros((N, N), F32))
    patch = smoothstep(0.25, 0.65, fbm(N, 4, seed, 5) * 0.8 + 0.35 * (Y / 16) + 0.2 * mortar - 0.35 + amount * 0.3)
    cover = np.clip(patch * (0.5 + 0.5 * mortar) + mortar * smoothstep(0.1, 0.4, patch + 0.2), 0, 1)
    alb = mix(t.albedo, m.albedo, cover * 0.95)
    h = np.maximum(t.height, (0.55 + 0.25 * m.height) * (cover > 0.5))
    if target:
        alb = match_mean(alb, target)
    return t.but(albedo=alb.astype(F32), height=norm01(h))


def carve(base, relief, depth=0.35, darken=0.15, soften=1.0, seed=0, target=None, light='top'):
    """Carve a relief mask (1 = raised) into a face: raised parts keep the face, sunk parts recess."""
    rel = blur(relief.astype(F32), soften)
    wear = smoothstep(0.3, 0.8, fbm(N, 8, seed + 1, 4)) * 0.25
    h = base.height * 0.3 + depth * rel * (1 - wear) + 0.35
    alb = base.albedo * (1 - darken * (1 - rel))[..., None]
    if target:
        alb = match_mean(alb, target)
    return Tex(alb, norm01(blur(h, 0.6)), light=light, bump=1.5, ao=0.7)


def frame_mask(inset=1.0, width=1.0):
    return rect(inset, inset, 16 - inset, 16 - inset) - rect(inset + width, inset + width, 16 - inset - width,
                                                              16 - inset - width)


# ------------------------------------------------------------------ original carved motifs
def motif_knot(cx=8, cy=8, r=4.6, w=0.9):
    """Interlaced square knot: two rounded squares rotated 45 degrees, plus a hub."""
    from engine.draw import polygon
    ring = lambda rr, a: polygon([(cx + rr * np.cos(a + k * np.pi / 2), cy + rr * np.sin(a + k * np.pi / 2))
                                  for k in range(4)])
    outer = np.clip(ring(r, 0) + ring(r, np.pi / 4), 0, 1)
    inner = np.clip(ring(r - w * 1.5, 0) + ring(r - w * 1.5, np.pi / 4), 0, 1)
    return np.clip(outer - inner + circle(cx, cy, 1.2), 0, 1)


def motif_chevrons(n=3, w=0.8):
    m = np.zeros((N, N), F32)
    for k in range(n):
        yy = 4.0 + k * 3.2
        m = np.maximum(m, 1 - smoothstep(w / 2 - 0.06, w / 2 + 0.06, np.abs(Y - yy - 0.55 * np.abs(X - 8))))
    return m * rect(2.5, 2.5, 13.5, 13.5)


def motif_eye_panel():
    """A recessed lozenge with a horizontal groove: abstract, geometric."""
    from engine.draw import polygon
    loz = polygon([(8, 2.6), (13.4, 8), (8, 13.4), (2.6, 8)])
    inner = polygon([(8, 4.2), (11.8, 8), (8, 11.8), (4.2, 8)])
    groove = rect(5.0, 7.5, 11.0, 8.5)
    return np.clip(loz - inner + groove * inner + circle(8, 8, 1.1), 0, 1)


def motif_sunburst():
    r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
    a = np.arctan2(Y - 8, X - 8)
    rays = (np.cos(a * 12) > 0.3) * smoothstep(5.6, 5.2, r) * smoothstep(2.2, 2.6, r)
    return np.clip(rays + circle(8, 8, 1.8) + smoothstep(0.3, 0.1, np.abs(r - 6.2)), 0, 1)


# ------------------------------------------------------------------ pillars
def pillar_side(face, seed, flutes=4, target=None, groove=0.5):
    """Vertical fluting with a capital band at both ends (quartz/purpur pillars)."""
    fl = 0.5 + 0.5 * np.cos(2 * np.pi * X / 16 * flutes)
    edges = smoothstep(0.0, 0.8, np.minimum(Y, 16 - Y))
    band = rect(-1, 0.9, 17, 1.6) + rect(-1, 14.4, 17, 15.1)
    h = 0.5 + 0.25 * fl * edges - 0.25 * band + 0.08 * face.height
    alb = face.albedo * (0.94 + 0.06 * fl[..., None]) * (1 - groove * 0.15 * band[..., None])
    if target:
        alb = match_mean(alb, target)
    return Tex(alb, norm01(h), light='top', bump=1.1, ao=0.55)


def pillar_top(face, seed, target=None):
    r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
    ring = smoothstep(0.35, 0.1, np.abs(r - 6.0)) + 0.6 * smoothstep(0.3, 0.1, np.abs(r - 3.2))
    edge = smoothstep(0.0, 0.7, np.minimum(np.minimum(X, 16 - X), np.minimum(Y, 16 - Y)))
    h = 0.6 - 0.3 * ring + 0.3 * edge + 0.06 * face.height
    alb = face.albedo * (1 - 0.12 * ring[..., None])
    if target:
        alb = match_mean(alb, target)
    return Tex(alb, norm01(h), light='top', bump=1.0, ao=0.5)


# ------------------------------------------------------------------ material faces
def smooth_face(seed, stops, *, grain=0.5, mottle=0.5, target=None, veins=0.0, vein_col='#9a9a9a', light='top'):
    x, y = warped_coords(N, 0.05, seed, freq=3)
    m = fbm(N, 3, seed, 5, x=x, y=y)
    g = fbm(N, 40, seed + 1, 3)
    t = 0.5 + 0.12 * mottle * m + 0.06 * grain * g
    alb = ramp(np.clip(t, 0, 1), stops)
    h = 0.5 + 0.1 * m + 0.05 * g
    if veins:
        v = smoothstep(0.9, 0.985, ridged(N, 2, seed + 2, 5, sharp=2.5))
        alb = mix(alb, hexrgb(vein_col), v * veins)
    if target:
        alb = match_mean(alb, target)
    return Tex(alb, norm01(h), light=light, bump=0.8, ao=0.4)


QUARTZ = [(0, '#d9d2c7'), (0.5, '#ece7df'), (1, '#f8f6f1')]
PURPUR = [(0, '#8a5d8a'), (0.5, '#a77ba7'), (1, '#c39bc2')]
END_STONE = [(0, '#c9c78e'), (0.5, '#dedca6'), (1, '#efedbd')]
PRISMARINE = [(0, '#3f7f70'), (0.5, '#5aa192'), (1, '#7cc0ad')]
CINNABAR = [(0, '#6e1d1a'), (0.4, '#9b2b25'), (0.75, '#b8443a'), (1, '#c96a5d')]
SULFUR = [(0, '#9a8a3a'), (0.4, '#c4b04b'), (0.75, '#dccb63'), (1, '#efe28a')]
RESIN = [(0, '#8a3a06'), (0.4, '#c55a0e'), (0.75, '#e2781c'), (1, '#f39a3c')]


def end_stone(seed=300, target=0.84):
    x, y = warped_coords(N, 0.05, seed, freq=3)
    m = fbm(N, 4, seed, 5, x=x, y=y)
    pores = smoothstep(0.55, 0.85, fbm(N, 22, seed + 1, 3))
    p2, pv = speckles(N, 30, seed + 2, 0.07, 0.4)
    p2 = blur(p2, 0.8)
    t = 0.55 + 0.12 * m + 0.05 * fbm(N, 50, seed + 3, 2) - 0.12 * pores - 0.08 * p2
    alb = ramp(np.clip(t, 0, 1), [(0, '#9d9a62'), (0.4, '#c6c38a'), (0.75, '#dedba4'), (1, '#f0eebf')])
    h = 0.5 + 0.2 * m - 0.3 * pores - 0.2 * p2
    return Tex(match_mean(alb, target), norm01(h), light='top', bump=1.3, ao=0.65)


def amethyst(seed=310, target=0.44, budding=False):
    x, y = warped_coords(N, 0.04, seed, freq=3)
    f1, f2, cid = worley(N, 5, seed, 0.9, x, y)
    facet = cell_random(cid, seed + 1)
    gx = np.cos(facet * 6.28)
    gy = np.sin(facet * 6.28)
    shade = 0.5 + 0.35 * ((X - 8) * gx + (Y - 8) * gy) / 16
    edge = 1 - smoothstep(0.0, 0.05, f2 - f1)
    t = 0.45 + 0.3 * facet + 0.15 * shade + 0.05 * fbm(N, 30, seed + 2, 2)
    alb = ramp(np.clip(t, 0, 1), [(0, '#3d2366'), (0.35, '#5d3a91'), (0.7, '#8a63c0'), (1, '#c4a6ec')])
    alb = mix(alb, hexrgb('#e3d2fb'), edge * 0.55)
    h = 0.5 + 0.3 * shade + 0.2 * facet - 0.1 * edge
    if budding:
        r = rng(seed + 3)
        for _ in range(5):
            cx, cy = r.uniform(2, 14), r.uniform(2, 14)
            pit = blur(circle(cx, cy, r.uniform(1.1, 1.6)), 1.5)
            alb = mix(alb, hexrgb('#2e1a4c'), pit * 0.6)
            h = h - 0.25 * pit
            for _ in range(r.integers(3, 6)):
                a, d = r.uniform(0, 2 * np.pi), r.uniform(0, 0.9)
                px, py = cx + d * np.cos(a), cy + d * np.sin(a)
                pt = circle(px, py, r.uniform(0.25, 0.45))
                alb = mix(alb, hexrgb('#e2cdfc'), pt)
                h = h + 0.35 * pt
    return Tex(match_mean(alb, target), norm01(h), light='top', bump=1.4, ao=0.5, gloss=0.3)


def prismarine_rough(frame, frames=4, seed=320, target=0.58):
    x, y = warped_coords(N, 0.05, seed, freq=3)
    m = fbm(N, 4, seed, 5, x=x, y=y)
    patches = fbm(N, 6, seed + 1, 4)
    shift = [0.0, 0.33, -0.25, 0.6][frame % 4]
    hue = np.sin(2 * np.pi * (patches * 0.8 + shift)) * 0.5 + 0.5
    t = 0.5 + 0.12 * m + 0.06 * fbm(N, 40, seed + 2, 2)
    a = ramp(np.clip(t, 0, 1), [(0, '#356c68'), (0.5, '#4f9a8c'), (1, '#74bba6')])
    b = ramp(np.clip(t, 0, 1), [(0, '#3a5f78'), (0.5, '#548aa3'), (1, '#7cb2c5')])
    alb = mix(a, b, hue * 0.7)
    cracks = smoothstep(0.92, 0.98, ridged(N, 4, seed + 3, 3, sharp=3))
    alb = alb * (1 - 0.3 * cracks[..., None])
    h = 0.5 + 0.2 * m - 0.2 * cracks
    return Tex(match_mean(alb, target), norm01(h), light='top', bump=1.2, ao=0.6)


def resin_face(seed, target=0.46):
    x, y = warped_coords(N, 0.06, seed, freq=3)
    m = fbm(N, 3, seed, 5, x=x, y=y)
    swirl = fbm(N, 8, seed + 1, 4, x=x, y=y)
    bub, bv = speckles(N, 26, seed + 2, 0.1, 0.35)
    t = 0.5 + 0.18 * m + 0.1 * swirl
    alb = ramp(np.clip(t, 0, 1), RESIN)
    alb = mix(alb, hexrgb('#ffc56e'), bub * 0.5)
    h = 0.5 + 0.12 * m + 0.05 * swirl + 0.1 * bub
    return Tex(match_mean(alb, target), norm01(h), light='top', bump=0.8, ao=0.4, gloss=0.35)


def mineral_face(seed, stops, *, target, crystals=0.5, freq=14, gloss=0.1, host=0.25):
    """A mineral-rich rock: a granular crystalline mass in the mineral's colours with patches of host rock."""
    cols = [stops[k][1] for k in range(len(stops))]
    c = crystalline(seed, [(3, cols[1]), (3, cols[2]), (1.5, cols[-1]), (1, cols[0])], freq=40,
                    big=(freq, 0.35 * crystals, [(1, cols[-1]), (1, cols[2])]), mottling=0.8, contrast=0.7,
                    cracks=0.3)
    patch = smoothstep(0.35, 0.6, fbm(N, 4, seed + 40, 4)) * host
    hostc = ramp(0.5 + 0.4 * fbm(N, 30, seed + 41, 3), [(0, '#4f4b47'), (1, '#77716a')])
    alb = mix(c.albedo, hostc, patch)
    return Tex(match_mean(alb, target), c.height, light='top', bump=1.0, ao=0.55, gloss=gloss)


# ------------------------------------------------------------------ registration
def register(R):
    # natural rocks: side faces keep a shared border; polished faces are single images
    R.block('stone_granite', edged(lambda s: granite(s), 200), variants=[4, 3])
    R.block('stone_diorite', edged(lambda s: diorite(s), 210), variants=[4, 3])
    R.block('stone_andesite', edged(lambda s: andesite(s), 220), variants=[4, 3])
    R.block('stone_granite_smooth', lambda v: polished(granite(201), 202, target=0.45))
    R.block('stone_diorite_smooth', lambda v: polished(diorite(211), 212, target=0.75))
    R.block('stone_andesite_smooth', lambda v: polished(andesite(221), 222, target=0.52))

    R.block('deepslate/deepslate', edged(lambda s: deepslate(s, 'side'), 230), variants=[4, 3])
    R.block('deepslate/deepslate_top', lambda v: deepslate(231, 'top', 0.34))
    cob = lambda s: cobblestone(s, target=0.3, stops=[(0, '#202024'), (0.35, '#34343a'), (0.65, '#48484f'),
                                                      (1, '#62626a')])
    R.block('deepslate/cobbled_deepslate', edged(cob, 232), variants=[4, 3])
    R.block('deepslate/polished_deepslate', lambda v: polished(deepslate(233, 'top'), 234, target=0.29, gloss=0.1))
    ds_face = lambda s: deepslate(s, 'top', 0.3)
    R.block('deepslate/deepslate_bricks', lambda v: masonry(235, [4, 4, 4, 4], 8, 4, ds_face(235), mortar=0.45,
                                                             mortar_col=('#151518', '#24242a'), target=0.28))
    R.block('deepslate/cracked_deepslate_bricks', lambda v: cracked(
        masonry(235, [4, 4, 4, 4], 8, 4, ds_face(235), mortar=0.45, mortar_col=('#151518', '#24242a')), 236,
        target=0.26))
    R.block('deepslate/deepslate_tiles', lambda v: masonry(237, [4, 4, 4, 4], 4, 0, ds_face(237), mortar=0.5,
                                                            mortar_col=('#0f0f12', '#1c1c21'), bevel=0.5,
                                                            target=0.22))
    R.block('deepslate/cracked_deepslate_tiles', lambda v: cracked(
        masonry(237, [4, 4, 4, 4], 4, 0, ds_face(237), mortar=0.5, mortar_col=('#0f0f12', '#1c1c21'), bevel=0.5),
        238, target=0.2))
    R.block('deepslate/chiseled_deepslate', lambda v: carve(
        polished(deepslate(239, 'top'), 240), np.clip(frame_mask(0.8, 1.0) + motif_knot(), 0, 1), target=0.22,
        seed=239))
    def reinforced_side(v):
        core = deepslate(241, 'side', 0.25)
        frame = np.clip(frame_mask(0.0, 2.0) + rect(5.0, 0, 6.6, 16) + rect(9.4, 0, 11.0, 16), 0, 1)
        pale = smooth_face(241, [(0, '#5d6158'), (0.5, '#747a6e'), (1, '#8d9385')], grain=0.8, mottle=0.8)
        alb = mix(core.albedo, pale.albedo, frame)
        rivets = sum(circle(x, y, 0.45) for x in (1.0, 15.0) for y in (1.0, 5.3, 10.7, 15.0))
        alb = mix(alb, hexrgb('#a3a99a'), np.clip(rivets, 0, 1) * 0.7)
        h = 0.4 + 0.3 * blur(frame, 1.0) + 0.1 * core.height + 0.2 * np.clip(rivets, 0, 1)
        return Tex(match_mean(alb, 0.4), norm01(h), light='top', bump=1.4, ao=0.65)
    R.block('reinforced_deepslate_side', reinforced_side)
    R.block('reinforced_deepslate_top', lambda v: carve(polished(deepslate(242, 'top'), 243),
                                                        np.clip(1 - circle(8, 8, 4.6) + circle(8, 8, 2.4), 0, 1),
                                                        target=0.32, seed=242))
    R.block('reinforced_deepslate_bottom', lambda v: polished(deepslate(244, 'top'), 245, target=0.32))

    R.block('tuff', edged(lambda s: tuff(s), 246), variants=[4, 3])
    R.block('polished_tuff', lambda v: polished(tuff(247), 248, target=0.4))
    tf = lambda s: tuff(s, 0.4)
    R.block('tuff_bricks', lambda v: masonry(249, [8, 8], 8, 4, tf(249), mortar=0.55,
                                             mortar_col=('#3c3e37', '#4e5048'), target=0.4))
    R.block('chiseled_tuff', lambda v: carve(polished(tuff(250), 251), np.clip(
        frame_mask(0.6, 0.9) + rect(0.6, 7.4, 15.4, 8.6) + motif_chevrons(2) * rect(0, 0, 16, 7.4), 0, 1),
        target=0.36, seed=250))
    R.block('chiseled_tuff_top', lambda v: carve(polished(tuff(252), 253), np.clip(
        frame_mask(0.6, 0.9) + circle(8, 8, 3.2) - circle(8, 8, 2.2), 0, 1), target=0.38, seed=252))
    R.block('chiseled_tuff_bricks', lambda v: carve(
        masonry(254, [8, 8], 16, 0, tf(254), mortar=0.55, mortar_col=('#3c3e37', '#4e5048')),
        np.clip(1 - rect(3.0, 2.0, 13.0, 6.0) - rect(3.0, 10.0, 13.0, 14.0) + motif_chevrons(1, 0.6) * 0, 0, 1),
        target=0.4, seed=254))
    R.block('chiseled_tuff_bricks_top', lambda v: carve(polished(tuff(255), 256), np.clip(
        frame_mask(0.5, 1.0) + motif_sunburst() * 0.0 + circle(8, 8, 2.0), 0, 1), target=0.44, seed=255))

    R.block('calcite', edged(lambda s: calcite(s), 257), variants=[4, 3])
    R.block('dripstone_block', edged(lambda s: dripstone(s), 260), variants=[4, 3])

    R.block('basalt_side', lambda v: basalt(270, 'side'))
    R.block('basalt_top', lambda v: basalt(271, 'top', 0.32))
    R.block('polished_basalt_side', lambda v: basalt(272, 'side', 0.35, polish=True))
    R.block('polished_basalt_top', lambda v: basalt(273, 'top', 0.39, polish=True))
    R.block('smooth_basalt', lambda v: smooth_face(274, [(0, '#25252b'), (0.5, '#3a3a41'), (1, '#4e4e56')], grain=0.8,
                                                   mottle=0.7, target=0.29))

    R.block('blackstone', edged(lambda s: blackstone(s), 280), variants=[4, 3])
    R.block('blackstone_top', lambda v: blackstone(281, face='top'))
    R.block('polished_blackstone', lambda v: polished(blackstone(282, 0.2, 'top'), 283, target=0.2))
    bs_face = lambda s: blackstone(s, 0.2, 'top')
    R.block('polished_blackstone_bricks', lambda v: masonry(284, [4, 4, 4, 4], 8, 4, bs_face(284), mortar=0.5,
                                                            mortar_col=('#0b090c', '#17131a'), target=0.18))
    R.block('cracked_polished_blackstone_bricks', lambda v: cracked(
        masonry(284, [4, 4, 4, 4], 8, 4, bs_face(284), mortar=0.5, mortar_col=('#0b090c', '#17131a')), 285,
        target=0.17))
    R.block('chiseled_polished_blackstone', lambda v: carve(polished(blackstone(286, 0.2, 'top'), 287), np.clip(
        frame_mask(0.7, 1.0) + motif_eye_panel(), 0, 1), target=0.2, seed=286))

    def gilded(v):
        b = blackstone(288, 0.16)
        m1, mv = speckles(N, 11, 289, 0.16, 0.48)
        m2, _ = speckles(N, 26, 291, 0.06, 0.35)
        m1 = np.clip(m1 + m2 * 0.8, 0, 1)
        vein = smoothstep(0.94, 0.99, ridged(N, 3, 290, 4, sharp=2.5)) * 0.7
        gold = np.clip(m1 + vein, 0, 1)
        col = ramp(mv, [(0, '#8a5a12'), (0.5, '#d49a26'), (1, '#f6d25a')])
        alb = mix(b.albedo, col, gold)
        return b.but(albedo=alb, height=norm01(b.height + 0.25 * gold), gloss=0.35)
    R.block('gilded_blackstone', gilded)

    # smooth stone (stone slab family)
    sm = lambda s: smooth_face(s, [(0, '#8e8e8c'), (0.5, '#a3a3a1'), (1, '#b6b6b4')], grain=0.6, mottle=0.4)
    R.block('stone_slab_top', lambda v: polished(sm(291), 292, target=0.62, relief=0.4, frame=0.25))

    def slab_side(v):
        t = polished(sm(293), 294, relief=0.4, frame=0.2)
        seam = smoothstep(0.35, 0.0, np.abs(Y - 8))
        return t.but(albedo=match_mean(t.albedo * (1 - 0.25 * seam[..., None]), 0.65),
                     height=norm01(t.height - 0.4 * seam))
    R.block('stone_slab_side', slab_side)

    # stone bricks
    st = lambda s: stone(s)
    sb = lambda s: masonry(s, [8, 8], 8, 4, st(s), mortar=0.55, mortar_col=('#4a4741', '#605c55'), target=0.47)
    R.block('stonebrick', edged(sb, 295), variants=[4, 3])
    R.block('stonebrick_cracked', lambda v: cracked(sb(296), 297, target=0.45))
    R.block('stonebrick_mossy', lambda v: mossy(sb(298), 299, target=0.46))
    R.block('stonebrick_carved', lambda v: carve(polished(stone(300), 301), np.clip(
        frame_mask(0.6, 1.0) + motif_knot(8, 8, 4.2, 0.85), 0, 1), target=0.46, seed=300))

    # clay bricks and mud bricks
    def clay_brick_face(s):
        x, y = warped_coords(N, 0.04, s, freq=3)
        m = fbm(N, 6, s, 4, x=x, y=y)
        sp, spv = speckles(N, 36, s + 1, 0.1, 0.3)
        t = 0.5 + 0.15 * m + 0.06 * fbm(N, 40, s + 2, 2)
        alb = ramp(np.clip(t, 0, 1), [(0, '#7a3324'), (0.4, '#9a4a35'), (0.7, '#b36148'), (1, '#c78267')])
        alb = mix(alb, hexrgb('#4a2018'), sp * 0.4)
        return Tex(alb, norm01(0.5 + 0.2 * m - 0.1 * sp), light='top', bump=1.0, ao=0.5)
    R.block('brick', edged(lambda s: masonry(s, [4, 4, 4, 4], 8, 4, clay_brick_face(s), mortar=0.7, tone=0.18,
                                            mortar_col=('#9b958a', '#b8b2a6'), target=0.42, bevel=0.5), 302),
            variants=[4, 3])

    def mud_face(s):
        from recipes.terrain import packed_mud
        return packed_mud(s, 0.45, straw=0.35)
    R.block('mud_bricks', lambda v: masonry(303, [4, 4, 4, 4], 8, 4, mud_face(303), mortar=0.7, tone=0.1,
                                            mortar_col=('#6b513c', '#82654c'), target=0.43, bevel=0.8))

    # end stone, purpur, quartz
    R.block('end_stone', edged(lambda s: end_stone(s), 304), variants=[4, 3])
    R.block('end_bricks', lambda v: masonry(305, [8, 8], 8, 4, end_stone(305), mortar=0.5,
                                            mortar_col=('#9e9a69', '#b5b07b'), target=0.85))
    pf = lambda s: smooth_face(s, PURPUR, grain=0.8, mottle=0.6)
    R.block('purpur_block', lambda v: masonry(306, [4, 4, 4, 4], 4, 0, pf(306), mortar=0.35, tone=0.06,
                                              mortar_col=('#6a456a', '#7c547c'), bevel=0.5, target=0.54))
    R.block('purpur_pillar', lambda v: pillar_side(pf(307), 307, flutes=4, target=0.55))
    R.block('purpur_pillar_top', lambda v: pillar_top(pf(308), 308, target=0.55))
    qf = lambda s: smooth_face(s, QUARTZ, grain=0.4, mottle=0.5, veins=0.25, vein_col='#c9c1b4')
    R.block('quartz_block_side', lambda v: polished(qf(309), 310, target=0.9, relief=0.5))
    R.block('quartz_block_top', lambda v: polished(qf(311), 312, target=0.9, relief=0.5))
    R.block('quartz_block_bottom', lambda v: polished(qf(313), 314, target=0.9, relief=0.6))
    R.block('quartz_block_chiseled', lambda v: carve(polished(qf(315), 316), np.clip(
        frame_mask(0.6, 0.9) + rect(0.6, 4.6, 15.4, 5.4) + rect(0.6, 10.6, 15.4, 11.4) + motif_chevrons(1) * 0, 0, 1),
        target=0.89, seed=315, darken=0.08))
    R.block('quartz_block_chiseled_top', lambda v: carve(polished(qf(317), 318), np.clip(
        frame_mask(0.6, 0.9) + motif_sunburst(), 0, 1), target=0.89, seed=317, darken=0.08))
    R.block('quartz_block_lines', lambda v: pillar_side(qf(319), 319, flutes=3, target=0.9, groove=0.3))
    R.block('quartz_block_lines_top', lambda v: pillar_top(qf(320), 320, target=0.9))
    R.block('quartz_bricks', lambda v: masonry(321, [8, 8], 8, 4, qf(321), mortar=0.35, tone=0.04,
                                               mortar_col=('#bdb5a8', '#d2cbbf'), bevel=0.5, target=0.9))

    # prismarine
    R.anim('prismarine_rough', lambda f, n: prismarine_rough(f, n), 4)
    prf = lambda s: smooth_face(s, PRISMARINE, grain=0.7, mottle=0.8)
    R.block('prismarine_bricks', lambda v: masonry(322, [4, 4, 4, 4], 8, 4, prf(322), mortar=0.45, tone=0.1,
                                                   mortar_col=('#2b5a52', '#3a6e64'), target=0.6))
    pdf = lambda s: smooth_face(s, [(0, '#173a30'), (0.5, '#245243'), (1, '#356a58')], grain=0.7, mottle=0.7)
    R.block('prismarine_dark', lambda v: masonry(323, [8, 8], 8, 0, pdf(323), mortar=0.5, tone=0.08,
                                                 mortar_col=('#0d241e', '#16342b'), target=0.32))

    # amethyst
    R.block('amethyst_block', edged(lambda s: amethyst(s), 324), variants=[4, 3])
    R.block('budding_amethyst', lambda v: amethyst(325, budding=True, target=0.43))

    # cinnabar, sulfur, resin (newer mineral families)
    cf = lambda s, tg=0.38: mineral_face(s, CINNABAR, target=tg)
    R.block('cinnabar', edged(lambda s: cf(s), 326), variants=[4, 3])
    R.block('polished_cinnabar', lambda v: polished(cf(327, 0.3), 328, target=0.3))
    R.block('cinnabar_bricks', lambda v: masonry(329, [4, 4, 4, 4], 8, 4, cf(329, 0.3), mortar=0.5,
                                                 mortar_col=('#3a1210', '#4e1a17'), target=0.3))
    R.block('chiseled_cinnabar', lambda v: carve(polished(cf(330, 0.3), 331), np.clip(
        frame_mask(0.6, 1.0) + motif_eye_panel(), 0, 1), target=0.29, seed=330))
    sf = lambda s, tg=0.67: mineral_face(s, SULFUR, target=tg, crystals=0.8, freq=10)
    R.block('sulfur', edged(lambda s: sf(s), 332), variants=[4, 3])
    R.block('polished_sulfur', lambda v: polished(sf(333, 0.66), 334, target=0.66))
    R.block('sulfur_bricks', lambda v: masonry(335, [4, 4, 4, 4], 8, 4, sf(335, 0.65), mortar=0.5,
                                               mortar_col=('#7d7030', '#93853d'), target=0.65))
    R.block('chiseled_sulfur', lambda v: carve(polished(sf(336, 0.66), 337), np.clip(
        frame_mask(0.6, 1.0) + motif_chevrons(3), 0, 1), target=0.66, seed=336))

    def potent(v):
        t = sf(338, 0.75)
        glow, gv = speckles(N, 12, 339, 0.3, 0.45)
        alb = mix(t.albedo, hexrgb('#fbf3a0'), glow * 0.7)
        return t.but(albedo=match_mean(alb, 0.79), emissive=(glow * 0.25)[..., None] * hexrgb('#fff4a0'))
    R.block('potent_sulfur', potent)
    R.block('resin_block', lambda v: resin_face(340, 0.47))
    R.block('resin_bricks', lambda v: masonry(341, [4, 4, 4, 4], 8, 4, resin_face(341, 0.45), mortar=0.5, tone=0.08,
                                              mortar_col=('#6b2a04', '#863608'), target=0.43))
    R.block('chiseled_resin_bricks', lambda v: carve(resin_face(342, 0.42), np.clip(
        frame_mask(0.6, 1.0) + motif_knot(8, 8, 4.0, 0.8), 0, 1), target=0.41, seed=342))

    # nether bricks
    nbf = lambda s: smooth_face(s, [(0, '#1f0d10'), (0.5, '#33161b'), (1, '#4a2228')], grain=0.8, mottle=0.7)
    nb = lambda s: masonry(s, [4, 4, 4, 4], 8, 4, nbf(s), mortar=0.6, tone=0.15,
                           mortar_col=('#100608', '#1b0b0e'), target=0.11)
    R.block('nether_brick', edged(nb, 343), variants=[4, 3])
    R.block('cracked_nether_bricks', lambda v: cracked(nb(344), 345, target=0.1))
    R.block('chiseled_nether_bricks', lambda v: carve(polished(nbf(346), 347), np.clip(
        frame_mask(0.6, 1.0) + motif_sunburst(), 0, 1), target=0.11, seed=346))
    rnbf = lambda s: smooth_face(s, [(0, '#2a0405'), (0.5, '#430709'), (1, '#5e0e10')], grain=0.8, mottle=0.7)
    R.block('red_nether_brick', lambda v: masonry(348, [4, 4, 4, 4], 8, 4, rnbf(348), mortar=0.6, tone=0.15,
                                                  mortar_col=('#150203', '#210405'), target=0.085))
