"""Ores (in stone, deepslate and netherrack) and mineral storage blocks."""
import numpy as np

from engine.noise import (F32, fbm, worley, cell_random, blur, warped_coords, norm01, smoothstep, rng)
from engine.color import ramp, mix, match_mean, hexrgb
from engine.material import Tex, MASTER
from engine.draw import X, Y, circle, polygon
from recipes.terrain import stone, speckles
from recipes.stones import deepslate, polished, crystalline
from registry import CALIBRATION

N = MASTER


def cal(path):
    c = CALIBRATION['textures/blocks/' + path]
    return np.array(c['mean'], F32), float(c['lum'])


def netherrack(seed=1500, target=0.25):
    """Rough, porous, fleshy-red rock: lumpy relief, pits and veins of darker scoria."""
    from recipes.terrain import rock
    t = rock(seed, [(0.0, '#2e0a0b'), (0.3, '#5a1717'), (0.55, '#7a2523'), (0.8, '#953a33'), (1.0, '#b2564a')],
             mottling=1.2, cracks=0.5, pits=1.2, lumps=1.6, bump=1.5, ao=0.7, crack_freq=4,
             fleck=[(22, 0.10, 0.35, '#3a0c0c', 0.6), (36, 0.07, 0.3, '#c46a58', 0.4)])
    ves = smoothstep(0.6, 0.85, fbm(N, 18, seed + 9, 3))
    alb = t.albedo * (1 - 0.35 * ves[..., None])
    return t.but(albedo=match_mean(alb, target), height=norm01(t.height - 0.2 * ves))


# ------------------------------------------------------------------ inclusions
def inclusions(seed, *, clusters=4, per=(4, 8), size=(0.5, 1.1), spread=1.6, shape='nugget', band=None):
    """Mineral grains grouped in clusters (optionally along a curving vein band).

    Returns (mask 0..1, dome height 0..1, facet tone 0..1, rim mask)."""
    r = rng(seed)
    mask = np.zeros((N, N), F32)
    dome = np.zeros((N, N), F32)
    facet = np.zeros((N, N), F32)
    centres = []
    for c in range(clusters):
        if band is not None:
            t = (c + r.uniform(0.2, 0.8)) / clusters
            cx = t * 16
            cy = band[0] + band[1] * np.sin(2 * np.pi * t + band[2])
        else:
            cx, cy = r.uniform(0, 16), r.uniform(0, 16)
        centres.append((cx, cy))
        for k in range(r.integers(per[0], per[1] + 1)):
            px, py = cx + r.normal(0, spread), cy + r.normal(0, spread)
            s = r.uniform(*size)
            ang = r.uniform(0, np.pi)
            for ox in (-16, 0, 16):
                for oy in (-16, 0, 16):
                    qx, qy = px + ox, py + oy
                    if abs(qx - 8) > 8 + s + 1 or abs(qy - 8) > 8 + s + 1:
                        continue
                    if shape == 'crystal':
                        n = r.integers(5, 7)
                        pts = [(qx + s * np.cos(ang + 2 * np.pi * i / n) * r.uniform(0.75, 1.0),
                                qy + s * np.sin(ang + 2 * np.pi * i / n) * r.uniform(0.75, 1.0)) for i in range(n)]
                        m = polygon(pts)
                        d = np.sqrt((X - qx) ** 2 + (Y - qy) ** 2) / s
                        a = np.arctan2(Y - qy, X - qx)
                        f = (np.floor((a - ang) / (2 * np.pi / n)) % n) / n
                        hh = np.clip(1 - d, 0, 1)
                    else:
                        c2, s2 = np.cos(ang), np.sin(ang)
                        u = ((X - qx) * c2 + (Y - qy) * s2) / s
                        v = (-(X - qx) * s2 + (Y - qy) * c2) / (s * r.uniform(0.6, 0.9))
                        d = np.sqrt(u * u + v * v) + 0.15 * fbm(N, 12, seed + c * 13 + k, 2)
                        m = 1 - smoothstep(0.92, 1.05, d)
                        hh = np.sqrt(np.clip(1 - d * d, 0, 1))
                        f = 0.5 + 0.5 * np.clip(-(u * 0.45 + v * 0.75), -1, 1)
                    upd = m > mask
                    mask = np.maximum(mask, m)
                    dome = np.where(upd, hh, dome)
                    facet = np.where(upd, f, facet)
    rim = np.clip(blur(mask, 2.0) * 1.6 - mask, 0, 1)
    return mask, dome, facet, rim


ORES = {
    # name: (stops for the mineral, shape, gloss, glow, cluster kwargs, rim/stain colour)
    'coal': ([(0, '#08080a'), (0.5, '#1c1c20'), (0.8, '#3a3a40'), (1, '#6a6a72')], 'crystal', 0.35, None,
             dict(clusters=5, per=(3, 6), size=(0.7, 1.3)), None),
    'iron': ([(0, '#8a5a3c'), (0.5, '#c39072'), (0.8, '#dcb59a'), (1, '#f0d6c2')], 'nugget', 0.15, None,
             dict(clusters=4, per=(3, 6), size=(0.6, 1.1)), '#8a4a2a'),
    'copper': ([(0, '#7a3a1a'), (0.4, '#b8602e'), (0.75, '#e08a4a'), (1, '#f6b47a')], 'nugget', 0.3, None,
               dict(clusters=4, per=(4, 7), size=(0.5, 1.0)), '#3f8a6a'),
    'gold': ([(0, '#8a6210'), (0.4, '#d4a020'), (0.75, '#f2d04a'), (1, '#fff2a0')], 'nugget', 0.5, None,
             dict(clusters=4, per=(3, 6), size=(0.5, 0.95)), '#e8e2d2'),
    'redstone': ([(0, '#5a0606'), (0.4, '#a01010'), (0.75, '#e02a1a'), (1, '#ff7a5a')], 'crystal', 0.25, '#ff3a1a',
                 dict(clusters=5, per=(4, 7), size=(0.4, 0.8)), None),
    'lapis': ([(0, '#0c1f6a'), (0.4, '#1a3a9a'), (0.75, '#2a5ad0'), (1, '#6a92f0')], 'nugget', 0.15, None,
              dict(clusters=5, per=(3, 6), size=(0.6, 1.1)), None),
    'diamond': ([(0, '#1a6a72'), (0.4, '#3ac8d2'), (0.75, '#8ef0f4'), (1, '#e8ffff')], 'crystal', 0.6, None,
                dict(clusters=4, per=(3, 5), size=(0.6, 1.0)), None),
    'emerald': ([(0, '#04501e'), (0.4, '#0c8a34'), (0.75, '#2ac85a'), (1, '#9af2b4')], 'crystal', 0.5, None,
                dict(clusters=3, per=(2, 4), size=(0.7, 1.15)), None),
    'quartz': ([(0, '#b8aca0'), (0.5, '#e6dcd2'), (1, '#fffaf2')], 'crystal', 0.3, None,
               dict(clusters=6, per=(3, 6), size=(0.5, 1.0)), None),
    'nether_gold': ([(0, '#8a6210'), (0.4, '#d4a020'), (0.75, '#f2d04a'), (1, '#fff2a0')], 'nugget', 0.5, None,
                    dict(clusters=7, per=(3, 6), size=(0.35, 0.65)), None),
}


def ore(seed, kind, host, path):
    stops, shape, gloss, glow, ckw, stain = ORES[kind]
    mean, lum = cal(path)
    m, dome, facet, rim = inclusions(seed, shape=shape, **ckw)
    t = np.clip(0.2 + 0.55 * dome + 0.35 * (facet - 0.5) + 0.1 * fbm(N, 30, seed + 1, 2), 0, 1)
    mineral = ramp(t, stops)
    rgb = host.albedo.copy()
    if stain:
        st = np.clip(blur(m, 3.0) * 2.2 - m, 0, 1) * smoothstep(0.0, 0.5, fbm(N, 8, seed + 2, 3) + 0.3)
        rgb = mix(rgb, hexrgb(stain) * (0.7 + 0.3 * host.albedo.mean(-1, keepdims=True) * 2), st * 0.45)
    rgb = rgb * (1 - 0.35 * rim[..., None])
    rgb = mix(rgb, mineral, m)
    h = np.maximum(host.height * 0.8, (0.55 + 0.45 * dome) * (m > 0.5))
    em = None
    if glow:
        em = (m * (0.25 + 0.35 * dome))[..., None] * hexrgb(glow) * 0.6
    t = Tex(rgb, norm01(blur(h, 0.5)), light='top', bump=1.4, ao=0.6, gloss=gloss, emissive=em, sharpen=0.45)
    return t


def ancient_debris(seed, face):
    x, y = warped_coords(N, 0.04, seed, freq=3)
    if face == 'side':
        bands = np.sin(2 * np.pi * (y * 6 + 0.5 * fbm(N, (2, 3), seed, 3, x=x, y=y)))
        scrape = fbm(N, (24, 2), seed + 1, 3)
        t = 0.45 + 0.16 * bands + 0.12 * scrape + 0.06 * fbm(N, 8, seed + 2, 3)
        h = 0.5 + 0.2 * bands + 0.15 * scrape
    else:
        r = np.sqrt((X - 8.4) ** 2 + (Y - 7.6) ** 2) + 2.2 * fbm(N, 3, seed, 4) + 0.5 * fbm(N, 9, seed + 5, 2)
        bands = np.sin(r * 2.1)
        scrape = fbm(N, 24, seed + 4, 3)
        t = 0.45 + 0.1 * bands + 0.1 * scrape + 0.08 * fbm(N, 6, seed + 3, 3)
        h = 0.5 + 0.18 * bands + 0.12 * scrape
    rgb = ramp(np.clip(t, 0, 1), [(0, '#2a1a18'), (0.4, '#4a302a'), (0.75, '#6a4a3e'), (1, '#8a6a5a')])
    mean, lum = cal('ancient_debris_' + face)
    return Tex(match_mean(rgb, lum), norm01(h), light='top', bump=1.5, ao=0.65, gloss=0.08)


# ------------------------------------------------------------------ storage blocks
def brushed(seed, stops, *, direction='x', target, frame=True, panels=2, gloss=0.35, hammer=0.0, rivets=True):
    """Metal: brushed (anisotropic) surface, plate seams and a bevelled frame."""
    streak = fbm(N, (2, 48) if direction == 'x' else (48, 2), seed, 3)
    mott = fbm(N, 3, seed + 1, 4)
    t = 0.55 + 0.06 * streak + 0.08 * mott
    h = 0.6 + 0.02 * streak
    if hammer:
        f1, f2, cid = worley(N, 9, seed + 2, 1.0)
        dent = np.clip(1 - f1 / 0.7, 0, 1) ** 2
        t = t + hammer * 0.1 * (cell_random(cid, seed + 3) - 0.5) - hammer * 0.05 * dent
        h = h - hammer * 0.25 * dent
    if frame:
        b = np.minimum(np.minimum(X, 16 - X), np.minimum(Y, 16 - Y))
        bev = smoothstep(0.0, 0.9, b)
        seam = np.zeros((N, N), F32)
        step = 16 / panels
        for k in range(1, panels):
            seam = np.maximum(seam, 1 - smoothstep(0.08, 0.28, np.abs(X - k * step)))
            seam = np.maximum(seam, 1 - smoothstep(0.08, 0.28, np.abs(Y - k * step)))
        t = t * (0.85 + 0.15 * bev) - 0.18 * seam
        h = h * (0.5 + 0.5 * bev) - 0.25 * seam
        if rivets:
            for k in range(panels + 1):
                for j in range(panels + 1):
                    cx, cy = min(max(k * step, 1.2), 14.8), min(max(j * step, 1.2), 14.8)
                    rv = circle(cx, cy, 0.42)
                    d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) / 0.42
                    t = np.where(rv > 0.5, 0.75 - 0.25 * d, t)
                    h = np.maximum(h, rv * (0.9 + 0.1 * np.sqrt(np.clip(1 - d * d, 0, 1))))
    rgb = ramp(np.clip(t, 0, 1), stops)
    return Tex(match_mean(rgb, target), norm01(h), light='top', bump=1.0, ao=0.5, gloss=gloss)


def gem_block(seed, stops, target, *, cells=2, facets=8, gloss=0.5):
    """Cut gemstone tiles: each tile a table facet surrounded by bevel facets."""
    cs = 16 / cells
    cx = (np.floor(X / cs) + 0.5) * cs
    cy = (np.floor(Y / cs) + 0.5) * cs
    dx, dy = X - cx, Y - cy
    ang = np.arctan2(dy, dx)
    rr = np.maximum(np.abs(dx), np.abs(dy)) / (cs / 2)
    sector = np.floor((ang + np.pi) / (2 * np.pi / facets))
    tone = cell_random(sector.astype(np.int64) % facets + (np.floor(X / cs) * 7 + np.floor(Y / cs) * 13).astype(np.int64),
                       seed)
    table = rr < 0.45
    t = np.where(table, 0.75 + 0.05 * fbm(N, 6, seed, 2), 0.35 + 0.45 * tone)
    edge = smoothstep(0.9, 1.0, rr)
    t = t - 0.2 * edge
    inner = 0.5 + 0.08 * fbm(N, 10, seed + 1, 3)
    t = t * (0.9 + 0.2 * inner)
    rgb = ramp(np.clip(t, 0, 1), stops)
    h = np.where(table, 1.0, 1.0 - 0.55 * (rr - 0.45) / 0.55) - 0.3 * edge
    spark, _ = speckles(N, 30, seed + 2, 0.05, 0.25)
    return Tex(match_mean(rgb, target), norm01(h), light='top', bump=1.2, ao=0.4, gloss=gloss,
               emissive=(spark * 0.3)[..., None] * np.array([1, 1, 1], F32))


def raw_block(seed, stops, target, stain=None):
    """Raw ore nuggets of mixed sizes compacted into a block, with dark gangue between them."""
    rgb = np.zeros((N, N, 3), F32)
    h = np.zeros((N, N), F32)
    rgb[:] = ramp(np.clip(0.2 + 0.2 * fbm(N, 20, seed, 3), 0, 1), stops) * 0.55
    for layer, (freq, cover, lo, hi) in enumerate(((3, 0.9, 0.5, 1.0), (6, 0.85, 0.35, 0.8), (11, 0.8, 0.2, 0.6))):
        x, y = warped_coords(N, 0.05, seed + 10 * layer, freq=4)
        f1, f2, cid = worley(N, freq, seed + 10 * layer + 1, 0.9, x, y)
        keep = cell_random(cid, seed + 10 * layer + 2) < cover
        rad = 0.5 + 0.12 * cell_random(cid, seed + 10 * layer + 3)
        d = f1 / rad + 0.18 * fbm(N, 14, seed + 10 * layer + 4, 2)
        m = (1 - smoothstep(0.85, 1.0, d)) * keep
        dome = np.sqrt(np.clip(1 - d * d, 0, 1))
        tone = cell_random(cid, seed + 10 * layer + 5)
        col = ramp(np.clip(0.25 + 0.5 * dome + 0.25 * (tone - 0.5) + 0.06 * fbm(N, 40, seed + layer, 2), 0, 1),
                   stops)
        z = lo + (hi - lo) * dome
        top = (z > h) & (m > 0.5)
        rgb = np.where(top[..., None], col, rgb)
        h = np.where(top, z, h)
    if stain:
        st = smoothstep(0.4, 0.7, fbm(N, 6, seed + 50, 4)) * (h < 0.45)
        rgb = mix(rgb, hexrgb(stain), st * 0.6)
    return Tex(match_mean(rgb, target), norm01(blur(h, 0.6)), light='top', bump=1.6, ao=0.75, gloss=0.25)


# ------------------------------------------------------------------ registration
def register(R):
    stone_host = lambda s: stone(s)
    ds_host = lambda s: deepslate(s, 'side')
    for i, kind in enumerate(('coal', 'iron', 'copper', 'gold', 'redstone', 'lapis', 'diamond', 'emerald')):
        p = f'{kind}_ore'
        R.block(p, lambda v, i=i, kind=kind, p=p: ore(1600 + 10 * i, kind, stone_host(1590), p))
        dp = f'deepslate/deepslate_{kind}_ore'
        R.block(dp, lambda v, i=i, kind=kind, dp=dp: ore(1605 + 10 * i, kind, ds_host(1591), dp))
    R.block('nether_gold_ore', lambda v: ore(1700, 'nether_gold', netherrack(1592), 'nether_gold_ore'))
    R.block('quartz_ore', lambda v: ore(1701, 'quartz', netherrack(1593), 'quartz_ore'))
    R.block('netherrack', lambda v: netherrack(1500))
    R.block('ancient_debris_side', lambda v: ancient_debris(1702, 'side'))
    R.block('ancient_debris_top', lambda v: ancient_debris(1703, 'top'))

    R.block('iron_block', lambda v: brushed(1710, [(0, '#8a8a8e'), (0.5, '#c8c8cc'), (1, '#f0f0f2')], target=0.8))
    R.block('gold_block', lambda v: brushed(1711, [(0, '#a8760e'), (0.5, '#e8b82a'), (1, '#fff09a')], target=0.72,
                                            hammer=1.0, gloss=0.5))
    R.block('netherite_block', lambda v: brushed(1712, [(0, '#1e1a1c'), (0.5, '#3a3436'), (1, '#5e5658')],
                                                 target=0.25, hammer=0.6, gloss=0.3, panels=1))
    R.block('diamond_block', lambda v: gem_block(1713, [(0, '#1a8a92'), (0.5, '#5ae0e6'), (1, '#e0ffff')], 0.72))
    R.block('emerald_block', lambda v: gem_block(1714, [(0, '#0a6a2a'), (0.5, '#20b24c'), (1, '#9af2b4')], 0.5,
                                                 facets=6))
    R.block('lapis_block', lambda v: polished(crystalline(1715, [(5, '#1d3f9e'), (3, '#2a52c0'), (2, '#163080'),
                                                                 (0.5, '#d8c060'), (0.4, '#e8e8f0')], freq=40,
                                                          contrast=0.75), 1716, target=0.3, gloss=0.25))
    R.block('redstone_block', lambda v: gem_block(1717, [(0, '#5a0606'), (0.5, '#c01a12'), (1, '#ff6a4a')], 0.3,
                                                  cells=4, facets=6, gloss=0.3))
    R.block('coal_block', lambda v: gem_block(1718, [(0, '#060608'), (0.5, '#18181c'), (1, '#4a4a52')], 0.09,
                                              cells=2, facets=7, gloss=0.4))
    R.block('raw_iron_block', lambda v: raw_block(1720, [(0, '#6a4a3a'), (0.5, '#b48a72'), (1, '#e2c4ae')], 0.55,
                                                  stain='#8a4a2a'))
    R.block('raw_gold_block', lambda v: raw_block(1721, [(0, '#8a5a0c'), (0.5, '#d8a024'), (1, '#ffe27a')], 0.62))
    R.block('raw_copper_block', lambda v: raw_block(1722, [(0, '#6a2a12'), (0.5, '#b8602e'), (1, '#f0a06a')], 0.45,
                                                    stain='#3f8a6a'))
