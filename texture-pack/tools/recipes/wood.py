"""Wood: planks, bark, log ends, stripped logs, bamboo and fungal stems, doors and trapdoors.

Colours are calibrated to the mean colour and brightness of the corresponding vanilla texture (so the
pack stays in harmony with the game's palette), but all figure, grain, bark and joinery are generated
here.
"""
import numpy as np

from engine.noise import (F32, fbm, ridged, worley, cell_random, blur, warped_coords, norm01, smoothstep,
                          rng)
from engine.color import ramp, mix, vary, match_mean, hexrgb
from engine.material import Tex, MASTER
from engine.draw import X, Y, rect, circle, ellipse, polyline, capsules, polygon
from registry import CALIBRATION

N = MASTER


def cal(path):
    c = CALIBRATION['textures/blocks/' + path]
    return np.array(c['mean'], F32), float(c['lum'])


def pal(mean, spread=0.42, warm=0.06):
    """Three-stop ramp around a mean colour: darker stops are a little warmer and more saturated."""
    m = np.asarray(mean, F32)
    lum = 0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2]
    dark = m * (1 - spread)
    dark = dark + (dark - lum * (1 - spread)) * 0.25
    dark = dark * np.array([1 + warm, 1, 1 - warm], F32)
    light = np.clip(m * (1 + spread * 0.75) + 0.02, 0, 1)
    light = light + (lum * (1 + spread * 0.75) - light) * 0.15
    return [(0.0, np.clip(dark, 0, 1)), (0.5, m), (1.0, np.clip(light, 0, 1))]


def pdist(a, b, period=16.0):
    d = (a - b + period / 2) % period - period / 2
    return d


# ------------------------------------------------------------------ figure (rings, fibre, pores, knots)
def figure(u, v, seed, *, spacing=0.55, arch=0.05, v0=-3.0, u0=8.0, wobble=0.35, pores=0.0, offset=0.0,
           knot=None):
    """Flat-sawn wood figure in block units: u runs along the grain (16-periodic), v across it.

    Returns (tone 0..1 where low = latewood line, relief) for the board surface.
    """
    du = pdist(u, u0)
    xs, ys = u / 16.0, (v + offset) / 16.0
    w = wobble * fbm(N, (2, 3), seed, 4, x=xs, y=ys)
    r = (v - v0 + arch * du * du + w)
    if knot is not None:
        ku, kv, kr = knot
        dk = np.sqrt(pdist(u, ku) ** 2 * 0.35 + (v - kv) ** 2)
        r = r + 1.6 * kr * np.exp(-(dk / (kr * 2.2)) ** 2)
    f = (r / spacing) % 1.0
    late = smoothstep(0.4, 0.9, f) * (1 - smoothstep(0.9, 1.0, f))
    fib = fbm(N, (3, 40), seed + 1, 3, x=xs, y=ys)
    tone = 0.62 - 0.24 * late + 0.07 * fib
    rel = 0.5 - 0.12 * late + 0.05 * fib
    if pores:
        pr = smoothstep(0.55, 0.85, fbm(N, (6, 64), seed + 2, 2, x=xs, y=ys)) * (0.4 + 0.6 * late)
        tone = tone - pores * 0.18 * pr
        rel = rel - 0.06 * pores * pr
    if knot is not None:
        ku, kv, kr = knot
        dk = np.sqrt(pdist(u, ku) ** 2 + ((v - kv) * 1.4) ** 2)
        core = 1 - smoothstep(kr * 0.55, kr * 0.75, dk)
        ring = np.exp(-((dk - kr * 0.7) / 0.2) ** 2)
        tone = tone * (1 - 0.45 * core) - 0.15 * ring
        rel = rel + 0.08 * core - 0.05 * ring
    return tone, rel


# ------------------------------------------------------------------ planks
def planks(seed, path, *, boards=4, joints=(1, 2), spacing=1.1, arch=0.06, pores=0.0, knot_rate=0.25,
           tone=0.08, gap=0.16, nails=True, spread=0.42, lum_scale=1.0):
    mean, lum = cal(path)
    rows = 16.0 / boards
    r = rng(seed)
    t = np.zeros((N, N), F32)
    h = np.zeros((N, N), F32)
    edge = np.full((N, N), 9.0, F32)
    nail = np.zeros((N, N), F32)
    row = np.floor(Y / rows).astype(int)
    v = Y - row * rows
    for b in range(boards):
        sel = row == b
        nj = int(r.integers(joints[0], joints[1] + 1))
        js = np.sort(r.uniform(0, 16, nj))
        count = np.zeros((N, N), int)
        for j in js:
            count += (X >= j)
        seg = count % nj
        for s in range(nj):
            m = sel & (seg == s)
            if not m.any():
                continue
            knot = None
            if r.uniform() < knot_rate:
                knot = (r.uniform(0, 16), r.uniform(0.8, rows - 0.8), r.uniform(0.35, 0.6))
            tt, rr = figure(X, v, seed + 17 * b + 5 * s, spacing=spacing * 2.0 * r.uniform(0.8, 1.25),
                            arch=arch * r.uniform(0.5, 1.5), v0=r.uniform(-4, rows + 4), u0=r.uniform(0, 16),
                            pores=pores, offset=b * 7.3 + s * 3.1, knot=knot)
            k = 1 + tone * r.uniform(-1, 1)
            t = np.where(m, tt * k, t)
            h = np.where(m, rr, h)
        for j in js:
            dj = np.abs(pdist(X, j))
            edge = np.where(sel, np.minimum(edge, dj), edge)
            if nails:
                for vy in (0.9, rows - 0.9):
                    for side in (-0.7, 0.7):
                        nail = np.maximum(nail, circle(float((j + side) % 16), b * rows + vy, 0.16))
    edge = np.minimum(edge, np.minimum(v, rows - v))
    bev = smoothstep(gap * 0.5, gap * 0.5 + 0.45, edge)
    groove = 1 - smoothstep(gap * 0.3, gap * 0.6, edge)
    t = t * (0.84 + 0.16 * bev) * (1 - 0.4 * groove)
    t = t * (1 - 0.5 * nail)
    h = h * (0.3 + 0.7 * bev) - 0.2 * groove
    alb = ramp(np.clip(t, 0, 1), pal(mean, spread))
    alb = vary(alb, dh=0.008 * fbm(N, 5, seed + 3, 3), ds=0.08 * fbm(N, 4, seed + 4, 3))
    return Tex(match_mean(alb, lum * lum_scale), norm01(h), light='top', bump=1.2, ao=0.55, sharpen=0.4)


# ------------------------------------------------------------------ bark
def bark(seed, path, kind='furrowed', *, plates=(7, 2), depth=1.0, inner=None, spread=0.5):
    mean, lum = cal(path)
    xw, yw = warped_coords(N, 0.035, seed, freq=4)
    fib = fbm(N, (24, 2), seed + 1, 3)
    base = fbm(N, 4, seed + 2, 4)
    if kind in ('furrowed', 'shallow'):
        fx = plates[0]
        rid = ridged(N, (fx, 1), seed + 3, 4, sharp=2.2)
        rid2 = ridged(N, (fx * 2, 2), seed + 13, 3, sharp=3.0)
        furrow = smoothstep(0.45 if kind == 'furrowed' else 0.6, 0.9, np.maximum(rid, 0.8 * rid2))
        furrow = np.clip(furrow + 0.35 * smoothstep(0.3, 0.6, fbm(N, (fx, 2), seed + 14, 3)) * furrow, 0, 1)
        f1, f2, cid = worley(N, (fx, plates[1] * 3), seed + 4, 0.9, xw, yw)
        crossc = smoothstep(0.93, 1.0, 1 - smoothstep(0.0, 0.06, f2 - f1)) * (cell_random(cid, seed + 5) < 0.5)
        ridge = 1 - furrow
        plate = np.sqrt(np.clip(ridge, 0, 1))
        hgt = plate * depth + 0.18 * fib + 0.06 * base - 0.25 * crossc
        t = 0.22 + 0.5 * plate + 0.16 * fib + 0.07 * base + 0.08 * (cell_random(cid, seed + 6) - 0.5) - 0.18 * crossc
        gapcol = inner
    elif kind == 'scaly':
        f1, f2, cid = worley(N, plates, seed + 3, 1.0, xw, yw)
        d = f2 - f1
        cy = cell_random(cid, seed + 11)
        lift = smoothstep(0.0, 0.3, d) * (0.55 + 0.45 * smoothstep(0.2, 0.9, f1))
        flake = fbm(N, (20, 6), seed + 12, 3)
        hgt = lift + 0.12 * fib + 0.05 * base + 0.08 * flake
        t = 0.36 + 0.36 * lift + 0.1 * fib + 0.1 * flake + 0.12 * (cy - 0.5)
        ridge = smoothstep(0.0, 0.12, d)
        gapcol = inner
    elif kind == 'fibrous':
        f1, f2, cid = worley(N, plates, seed + 3, 0.95, xw, yw)
        ridge = smoothstep(0.0, 0.3, f2 - f1)
        strands = fbm(N, (40, 3), seed + 6, 3)
        scars = smoothstep(0.93, 0.99, ridged(N, (1, 6), seed + 7, 3, sharp=3))
        hgt = 0.6 * ridge + 0.25 * strands + 0.05 * base - 0.2 * scars
        t = 0.35 + 0.3 * ridge + 0.2 * strands + 0.06 * base - 0.15 * scars
        gapcol = inner
    else:  # 'smooth' with horizontal lenticels (birch, cherry)
        ridge = np.ones((N, N), F32)
        hgt = 0.5 + 0.08 * base + 0.04 * fib
        t = 0.55 + 0.08 * base + 0.05 * fib
        gapcol = None
    alb = ramp(np.clip(t, 0, 1), pal(mean, spread))
    if gapcol is not None:
        alb = mix(hexrgb(gapcol) * (0.85 + 0.2 * fib[..., None]), alb, smoothstep(0.0, 0.35, ridge))
    alb = vary(alb, ds=0.12 * fbm(N, 3, seed + 8, 3))
    lich = smoothstep(0.62, 0.8, fbm(N, 5, seed + 9, 4)) * 0.25 * (kind != 'smooth')
    alb = mix(alb, hexrgb('#7e8a62'), lich * ridge)
    return Tex(match_mean(alb, lum), norm01(hgt), light='top', bump=2.0, ao=0.8, sharpen=0.45)


def birch_bark(seed, path):
    mean, lum = cal(path)
    base = fbm(N, 4, seed, 4)
    peel = fbm(N, (2, 10), seed + 1, 3)
    t = 0.7 + 0.08 * base + 0.06 * peel
    alb = ramp(np.clip(t, 0, 1), [(0, '#b7b1a6'), (0.6, '#e2ddd3'), (1, '#f5f2ec')])
    r = rng(seed + 2)
    segs, vals = [], []
    for _ in range(46):
        x0, y0 = r.uniform(0, 16), r.uniform(0, 16)
        L = r.uniform(0.8, 3.2)
        w = r.uniform(0.18, 0.42)
        segs.append((x0, y0, x0 + L, y0 + r.uniform(-0.15, 0.15), w, w * 0.7, 0))
        vals.append((r.uniform(0.08, 0.3),))
    lv, lc, _ = capsules(np.array(segs), np.array(vals))
    alb = mix(alb, lv[..., 0:1] * np.array([1.0, 0.97, 0.95], F32) + 0.05, lc)
    blot = smoothstep(0.62, 0.8, fbm(N, 6, seed + 3, 4))
    for _ in range(3):
        cx, cy = r.uniform(0, 16), r.uniform(0, 16)
        blot = np.maximum(blot, ellipse(cx, cy, r.uniform(1.0, 1.8), r.uniform(0.5, 0.9)) * 0.9)
    alb = mix(alb, hexrgb('#2a2622'), blot * 0.85)
    h = 0.5 + 0.05 * base + 0.08 * peel - 0.15 * lc - 0.2 * blot
    return Tex(match_mean(alb, lum), norm01(h), light='top', bump=1.0, ao=0.5, sharpen=0.4)


def lenticel_bark(seed, path, lent_col, count=60, spread=0.45):
    """Smooth bark ringed with horizontal lenticels (cherry-like)."""
    mean, lum = cal(path)
    base = fbm(N, 4, seed, 4)
    bands = fbm(N, (1, 6), seed + 1, 3)
    t = 0.55 + 0.1 * base + 0.08 * bands
    alb = ramp(np.clip(t, 0, 1), pal(mean, spread))
    r = rng(seed + 2)
    segs, vals = [], []
    for _ in range(count):
        x0, y0 = r.uniform(0, 16), r.uniform(0, 16)
        L = r.uniform(0.6, 2.0)
        w = r.uniform(0.18, 0.32)
        segs.append((x0, y0, x0 + L, y0, w, w, 0))
        vals.append((r.uniform(0.7, 1.0),))
    lv, lc, _ = capsules(np.array(segs), np.array(vals))
    alb = mix(alb, hexrgb(lent_col) * lv[..., 0:1], lc * 0.8)
    h = 0.5 + 0.1 * base + 0.05 * bands + 0.12 * lc
    return Tex(match_mean(alb, lum), norm01(h), light='top', bump=1.2, ao=0.55, gloss=0.08, sharpen=0.4)


# ------------------------------------------------------------------ log ends
def log_top(seed, path, *, bark_path=None, stripped=False, spacing=0.42, checks=3, heart=0.15, spread=0.45,
            bark_kind='furrowed'):
    mean, lum = cal(path)
    spacing = spacing * 2.0
    r = rng(seed)
    cx, cy = 8 + r.uniform(-0.6, 0.6), 8 + r.uniform(-0.6, 0.6)
    dx, dy = X - cx, Y - cy
    ang = np.arctan2(dy, dx)
    ecc = 1 + 0.06 * np.cos(2 * (ang - r.uniform(0, np.pi)))
    rr = np.sqrt(dx * dx + dy * dy) * ecc + 0.35 * fbm(N, 3, seed + 1, 4) + 0.1 * fbm(N, 9, seed + 2, 2)
    f = (rr / (spacing * (1 + 0.15 * fbm(N, 2, seed + 3, 2)))) % 1.0
    late = smoothstep(0.55, 0.92, f) * (1 - smoothstep(0.92, 1.0, f))
    saw = 0.5 + 0.5 * np.sin(2 * np.pi * (X * np.cos(0.6) + Y * np.sin(0.6)) * 1.6 + 2 * fbm(N, 4, seed + 4, 2))
    t = 0.62 - 0.3 * late + 0.04 * saw + 0.04 * fbm(N, 30, seed + 5, 2)
    t = t - heart * (1 - smoothstep(1.5, 4.5, rr))
    h = 0.5 - 0.1 * late + 0.04 * saw
    crack = np.zeros((N, N), F32)
    for _ in range(checks):
        a = r.uniform(0, 2 * np.pi)
        L = r.uniform(3.0, 6.5)
        pts = [(cx + k / 5 * L * np.cos(a) + r.uniform(-0.2, 0.2), cy + k / 5 * L * np.sin(a) + r.uniform(-0.2, 0.2))
               for k in range(6)]
        cm, _ = polyline(pts, np.linspace(0.06, 0.28, 6)[::-1] * 1.0)
        crack = np.maximum(crack, cm)
    pith = circle(cx, cy, 0.35)
    t = t * (1 - 0.55 * crack) * (1 - 0.4 * pith)
    h = h - 0.4 * crack
    alb = ramp(np.clip(t, 0, 1), pal(mean, spread))
    sq = (np.abs(dx) ** 6 + np.abs(dy) ** 6) ** (1 / 6)
    if not stripped and bark_path:
        bmean, blum = cal(bark_path)
        rim = 7.25 + 0.25 * fbm(N, 8, seed + 6, 3)
        outer = smoothstep(rim - 0.08, rim + 0.08, sq)
        cambium = np.exp(-((sq - rim + 0.2) / 0.22) ** 2)
        bark_t = 0.45 + 0.3 * fbm(N, (8, 8), seed + 7, 3) + 0.15 * fbm(N, 24, seed + 8, 2)
        bark_c = ramp(np.clip(bark_t, 0, 1), pal(bmean, 0.5))
        alb = alb * (1 - 0.3 * cambium[..., None])
        alb = mix(alb, match_mean(bark_c, blum * 1.05), outer)
        h = np.where(outer > 0.5, 0.65 + 0.25 * bark_t, h)
    else:
        rim = np.exp(-((sq - 7.6) / 0.35) ** 2)
        alb = alb * (1 - 0.12 * rim[..., None])
    return Tex(match_mean(alb, lum), norm01(h), light='top', bump=1.0, ao=0.5, sharpen=0.4)


# ------------------------------------------------------------------ stripped log sides
def stripped_side(seed, path, *, spacing=0.6, pores=0.0, knot_rate=0.6, spread=0.38, marks=0.6):
    spacing = spacing * 2.6
    mean, lum = cal(path)
    r = rng(seed)
    knot = (r.uniform(0, 16), r.uniform(2, 14), r.uniform(0.4, 0.7)) if r.uniform() < knot_rate else None
    if knot is not None:
        knot = (knot[1], knot[0], knot[2])
    t, h = figure(Y, X, seed + 1, spacing=spacing, arch=0.008, v0=r.uniform(-6, 22), u0=r.uniform(0, 16),
                  wobble=0.45, pores=pores, knot=knot)
    draw = 0.5 + 0.5 * np.sin(2 * np.pi * (Y / 16 * 7 + 0.3 * fbm(N, (4, 2), seed + 2, 2)))
    t = t + 0.03 * marks * draw
    h = h + 0.06 * marks * draw
    alb = ramp(np.clip(t, 0, 1), pal(mean, spread))
    return Tex(match_mean(alb, lum), norm01(h), light='top', bump=1.0, ao=0.45, sharpen=0.4)


# ------------------------------------------------------------------ bamboo
def bamboo_side(seed, path, stripped=False):
    mean, lum = cal(path)
    r = rng(seed)
    cols = [0.0]
    while cols[-1] < 16:
        cols.append(cols[-1] + r.uniform(2.6, 3.6))
    cols = np.array(cols) * 16 / cols[-1]
    t = np.zeros((N, N), F32)
    h = np.zeros((N, N), F32)
    for k in range(len(cols) - 1):
        a, b = cols[k], cols[k + 1]
        m = (X >= a) & (X < b)
        u = (X - a) / (b - a)
        round_ = np.sqrt(np.clip(1 - (2 * u - 1) ** 2, 0, 1))
        node_y = r.uniform(0, 16)
        dn = np.abs(pdist(Y, node_y))
        node = np.exp(-(dn / 0.35) ** 2)
        streak = fbm(N, (30, 2), seed + k, 2)
        tt = 0.35 + 0.35 * round_ + 0.08 * streak - 0.25 * node * (0.6 if stripped else 1.0)
        t = np.where(m, tt, t)
        h = np.where(m, round_ * 0.8 + 0.25 * node, h)
    stops = pal(mean, 0.45)
    alb = ramp(np.clip(t, 0, 1), stops)
    return Tex(match_mean(alb, lum), norm01(h), light='top', bump=1.3, ao=0.65)


def bamboo_top(seed, path, stripped=False):
    mean, lum = cal(path)
    r = rng(seed)
    alb_t = 0.18 + 0.08 * fbm(N, 12, seed + 1, 3)
    h = np.zeros((N, N), F32)
    pts = []
    for _ in range(600):
        if len(pts) >= 11:
            break
        p = (r.uniform(2.0, 14.0), r.uniform(2.0, 14.0), r.uniform(1.7, 2.3))
        if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > (p[2] + q[2] + 0.2) ** 2 for q in pts):
            pts.append(p)
    for (cx, cy, rad) in pts:
        d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        wall = (1 - smoothstep(rad - 0.1, rad + 0.1, d)) * smoothstep(rad * 0.62, rad * 0.72, d)
        hollow = 1 - smoothstep(rad * 0.62, rad * 0.72, d)
        alb_t = np.where(wall > 0.5, 0.7 + 0.1 * np.cos(d * 8), alb_t)
        alb_t = np.where(hollow > 0.5, 0.12, alb_t)
        h = np.maximum(h, wall * 0.9)
    alb = ramp(np.clip(alb_t, 0, 1), pal(mean, 0.6))
    return Tex(match_mean(alb, lum), norm01(blur(h, 0.6)), light='top', bump=1.3, ao=0.8)


def bamboo_planks(seed, path, mosaic=False):
    mean, lum = cal(path)
    t = np.zeros((N, N), F32)
    h = np.zeros((N, N), F32)
    if not mosaic:
        rows = 2.0
        row = np.floor(Y / rows)
        v = Y - row * rows
        round_ = np.sqrt(np.clip(1 - (v / rows * 2 - 1) ** 2, 0, 1))
        node_x = cell_random(row.astype(np.int64) % 64, seed) * 16
        node = np.exp(-(pdist(X, node_x) / 0.3) ** 2)
        t = 0.35 + 0.4 * round_ - 0.2 * node + 0.06 * fbm(N, (3, 30), seed + 1, 2)
        h = round_ * 0.8 + 0.2 * node
    else:
        cell = 4.0
        cx, cy = np.floor(X / cell), np.floor(Y / cell)
        horiz = ((cx + cy) % 2) == 0
        lu = np.where(horiz, Y - cy * cell, X - cx * cell)
        strip = (lu % 1.333) / 1.333
        round_ = np.sqrt(np.clip(1 - (strip * 2 - 1) ** 2, 0, 1))
        edge = np.minimum(np.minimum(X - cx * cell, (cx + 1) * cell - X), np.minimum(Y - cy * cell, (cy + 1) * cell - Y))
        bev = smoothstep(0.0, 0.3, edge)
        t = (0.35 + 0.4 * round_) * (0.7 + 0.3 * bev) + 0.05 * fbm(N, 30, seed + 1, 2)
        h = round_ * 0.6 * bev + 0.3 * bev
    alb = ramp(np.clip(t, 0, 1), pal(mean, 0.45))
    return Tex(match_mean(alb, lum), norm01(h), light='top', bump=1.2, ao=0.6)


# ------------------------------------------------------------------ fungal stems
def stem_side(seed, path, frame=0, frames=1, glow_col='#ff5a3c', base_path=None):
    """Huge-fungus stem: fibrous flesh with luminous veins that pulse along the flipbook."""
    mean, lum = cal(base_path or path)
    xw, yw = warped_coords(N, 0.04, seed, freq=4)
    strands = fbm(N, (18, 2), seed + 1, 4, x=xw, y=yw)
    f1, f2, cid = worley(N, (6, 2), seed + 2, 0.9, xw, yw)
    ridge = smoothstep(0.0, 0.35, f2 - f1)
    veins = smoothstep(0.86, 0.97, ridged(N, (3, 1), seed + 3, 4, sharp=2.5))
    phase = frame / max(frames, 1)
    pulse = 0.55 + 0.45 * np.sin(2 * np.pi * (phase + Y / 16 * 1.0 + 0.3 * fbm(N, 3, seed + 4, 2)))
    t = 0.3 + 0.35 * ridge + 0.2 * strands
    alb = ramp(np.clip(t, 0, 1), pal(mean, 0.55))
    alb = mix(alb, hexrgb(glow_col), veins * (0.45 + 0.4 * pulse))
    h = 0.5 + 0.35 * ridge + 0.15 * strands - 0.1 * veins
    em = (veins * pulse * 0.25)[..., None] * hexrgb(glow_col)
    return Tex(match_mean(alb, lum), norm01(h), light='top', bump=1.4, ao=0.65, emissive=em)


# ------------------------------------------------------------------ doors and trapdoors
def wood_face(seed, path, vertical=True, spacing=1.3, spread=0.4):
    """A single board-like surface (used for door stiles, rails and panels)."""
    mean, lum = cal(path)
    r = rng(seed)
    if vertical:
        t, h = figure(Y, X, seed, spacing=spacing, arch=0.02, v0=r.uniform(-8, 24), u0=r.uniform(0, 16), wobble=0.5)
    else:
        t, h = figure(X, Y, seed, spacing=spacing, arch=0.04, v0=r.uniform(-8, 24), u0=r.uniform(0, 16), wobble=0.5)
    return t, h, pal(mean, spread), lum


def joinery(seed, path, parts, *, holes=None, iron=(), studs=(), vertical_boards=0, target=None, spread=0.4):
    """Compose a door/trapdoor face.

    parts: list of (mask, kind) where kind is 'stile' (vertical grain, raised), 'rail' (horizontal grain,
    raised) or 'panel' (vertical grain, recessed). holes: alpha mask of openings (1 = open).
    iron: list of masks painted as forged iron; studs: list of (x, y, r) nail heads.
    vertical_boards: if > 0, the base is a field of that many vertical boards (rustic doors).
    """
    mean, lum = cal(path)
    tv, hv, stops, _ = wood_face(seed, path, True, spread=spread)
    th, hh, _, _ = wood_face(seed + 1, path, False, spread=spread)
    t = tv.copy()
    h = 0.5 + 0.2 * (hv - 0.5)
    if vertical_boards:
        bw = 16.0 / vertical_boards
        col = np.floor(X / bw)
        u = X - col * bw
        gapd = np.minimum(u, bw - u)
        bev = smoothstep(0.05, 0.35, gapd)
        t = t * (0.75 + 0.25 * bev) * (1 + 0.08 * (cell_random(col.astype(np.int64) % 64, seed + 2) - 0.5))
        h = h * (0.4 + 0.6 * bev)
    for mask, kind in parts:
        m = np.clip(mask, 0, 1)
        inner = blur(m, 1.6)
        if kind == 'rail':
            t = mix(t, th, m)
            h = mix(h, 0.75 + 0.15 * (hh - 0.5) + 0.15 * inner, m)
        elif kind == 'stile':
            t = mix(t, tv * 1.02, m)
            h = mix(h, 0.75 + 0.15 * (hv - 0.5) + 0.15 * inner, m)
        else:
            t = mix(t, tv * 0.94, m)
            h = mix(h, 0.35 + 0.1 * (hv - 0.5) + 0.25 * inner, m)
    alb = ramp(np.clip(t, 0, 1), stops)
    for m in iron:
        m = np.clip(m, 0, 1)
        ir = ramp(0.5 + 0.35 * fbm(N, 20, seed + 3, 3), [(0, '#232326'), (0.6, '#3d3d42'), (1, '#5d5d63')])
        alb = mix(alb, ir, m)
        h = np.maximum(h, 0.85 * m + h * (1 - m))
    for (sx, sy, sr) in studs:
        c = circle(sx, sy, sr)
        dome = np.sqrt(np.clip(1 - ((X - sx) ** 2 + (Y - sy) ** 2) / (sr * sr), 0, 1))
        alb = mix(alb, hexrgb('#4b4b50') * (0.7 + 0.5 * dome[..., None]), c)
        h = np.maximum(h, 0.8 + 0.2 * dome * c)
    alpha = None
    if holes is not None:
        alpha = 1 - np.clip(holes, 0, 1)
        ring = np.clip(blur(holes, 1.2) * 2.0, 0, 1) * alpha
        alb = alb * (1 - 0.25 * ring[..., None])
    lum_t = target if target is not None else lum
    if alpha is not None:
        alb_m = match_mean(alb, lum_t, alpha > 0.5)
    else:
        alb_m = match_mean(alb, lum_t)
    return Tex(alb_m, norm01(blur(h, 0.5)), alpha, light='top', bump=1.3, ao=0.6, cutout=alpha is not None,
               sharpen=0.4)


def frame_parts(stile=2.6, top=2.6, bottom=2.6, mid=None):
    parts = [(rect(0, -1, stile, 17), 'stile'), (rect(16 - stile, -1, 16, 17), 'stile')]
    if top:
        parts.append((rect(stile, 0, 16 - stile, top), 'rail'))
    if bottom:
        parts.append((rect(stile, 16 - bottom, 16 - stile, 16), 'rail'))
    for (y0, y1) in (mid or []):
        parts.append((rect(stile, y0, 16 - stile, y1), 'rail'))
    return parts


def hinges(side='left', ys=(3.0,), length=5.0, width=1.1):
    out = []
    for y in ys:
        if side == 'left':
            out.append(rect(-0.2, y, length, y + width) * (1 - circle(length - 0.2, y + width / 2, 0.01)))
        else:
            out.append(rect(16 - length, y, 16.2, y + width))
    return out


def arch_window(x0, x1, y0, y1):
    """An arched (round-topped) opening."""
    w = (x1 - x0) / 2
    cx = (x0 + x1) / 2
    return np.clip(rect(x0, y0 + w, x1, y1) + ellipse(cx, y0 + w, w, w), 0, 1)


DOORS = {
    # species: (texture prefix data)
    'oak': dict(lower='door_wood_lower', upper='door_wood_upper', trap='trapdoor', planks='planks_oak'),
    'spruce': dict(lower='door_spruce_lower', upper='door_spruce_upper', trap='spruce_trapdoor', planks='planks_spruce'),
    'birch': dict(lower='door_birch_lower', upper='door_birch_upper', trap='birch_trapdoor', planks='planks_birch'),
    'jungle': dict(lower='door_jungle_lower', upper='door_jungle_upper', trap='jungle_trapdoor', planks='planks_jungle'),
    'acacia': dict(lower='door_acacia_lower', upper='door_acacia_upper', trap='acacia_trapdoor', planks='planks_acacia'),
    'dark_oak': dict(lower='door_dark_oak_lower', upper='door_dark_oak_upper', trap='dark_oak_trapdoor',
                     planks='planks_big_oak'),
    'mangrove': dict(lower='mangrove_door_bottom', upper='mangrove_door_top', trap='mangrove_trapdoor',
                     planks='mangrove_planks'),
    'cherry': dict(lower='cherry_door_bottom', upper='cherry_door_top', trap='cherry_trapdoor', planks='cherry_planks'),
    'pale_oak': dict(lower='pale_oak_door_bottom', upper='pale_oak_door_top', trap='pale_oak_trapdoor',
                     planks='pale_oak_planks'),
    'poplar': dict(lower='poplar_door_bottom', upper='poplar_door_top', trap='poplar_trapdoor', planks='poplar_planks'),
    'bamboo': dict(lower='bamboo_door_bottom', upper='bamboo_door_top', trap='bamboo_trapdoor', planks='bamboo_planks'),
    'crimson': dict(lower='huge_fungus/crimson_door_lower', upper='huge_fungus/crimson_door_top',
                    trap='huge_fungus/crimson_trapdoor', planks='huge_fungus/crimson_planks'),
    'warped': dict(lower='huge_fungus/warped_door_lower', upper='huge_fungus/warped_door_top',
                   trap='huge_fungus/warped_trapdoor', planks='huge_fungus/warped_planks'),
}


def door(species, half, seed):
    d = DOORS[species]
    path = d[half]
    up = half == 'upper'
    hin = hinges('left', (2.2,) if up else (11.8,))
    handle = []
    studs = []
    if not up:
        handle = [rect(12.6, 1.0, 13.6, 4.2)]
        studs = [(13.1, 1.4, 0.32), (13.1, 3.8, 0.32)]
    if species == 'oak':
        parts = frame_parts(2.6, 2.6 if up else 2.0, 0.0 if up else 2.6, [(13.4, 16)] if up else [(0, 1.2), (7.2, 8.8)])
        parts += [(rect(2.6, 2.6 if up else 1.2, 13.4, 13.4 if up else 7.2), 'panel')]
        if not up:
            parts += [(rect(2.6, 8.8, 13.4, 13.4), 'panel')]
        holes = (arch_window(3.6, 7.4, 3.4, 11.8) + arch_window(8.6, 12.4, 3.4, 11.8)) if up else None
        return joinery(seed, path, parts, holes=holes, iron=hin + handle, studs=studs)
    if species == 'spruce':
        brace = polygon([(1.5, 13.5), (3.0, 13.5), (14.5, 3.5), (13.0, 3.5)]) if not up else polygon(
            [(1.5, 14.0), (3.0, 14.0), (14.5, 2.5), (13.0, 2.5)])
        parts = [(rect(0, 1.0, 16, 3.2), 'rail'), (rect(0, 12.8, 16, 15.0), 'rail'), (brace, 'rail')]
        st = [(x, y, 0.28) for x in (2.0, 6.0, 10.0, 14.0) for y in (2.1, 13.9)]
        return joinery(seed, path, parts, iron=hin + handle, studs=st + studs, vertical_boards=4)
    if species == 'birch':
        parts = frame_parts(2.4, 2.4, 2.4) + [(rect(2.4, 2.4, 13.6, 13.6), 'panel')]
        holes = (circle(8, 8, 3.4) - 0) if up else None
        muntin = np.clip(rect(7.6, 4.4, 8.4, 11.6) + rect(4.4, 7.6, 11.6, 8.4), 0, 1) * circle(8, 8, 3.4) if up else None
        if up:
            holes = np.clip(holes - muntin, 0, 1)
            parts.append((circle(8, 8, 4.0) - circle(8, 8, 3.4), 'rail'))
        return joinery(seed, path, parts, holes=holes, iron=hin + handle, studs=studs)
    if species == 'jungle':
        parts = frame_parts(2.4, 2.4, 2.4)
        if up:
            lattice = np.zeros((N, N), F32)
            for k in range(-3, 4):
                lattice = np.maximum(lattice, 1 - smoothstep(0.35, 0.5, np.abs(((X - 8) + (Y - 8)) - k * 2.6)))
                lattice = np.maximum(lattice, 1 - smoothstep(0.35, 0.5, np.abs(((X - 8) - (Y - 8)) - k * 2.6)))
            win = rect(3.4, 3.4, 12.6, 12.6)
            holes = np.clip(win - lattice, 0, 1)
            parts += [(rect(2.4, 2.4, 13.6, 13.6) * (1 - win), 'panel'), (lattice * win, 'rail')]
            return joinery(seed, path, parts, holes=holes, iron=hin, studs=studs)
        parts += [(rect(2.4, 2.4, 13.6, 7.4), 'panel'), (rect(2.4, 8.6, 13.6, 13.6), 'panel'), (rect(2.4, 7.4, 13.6, 8.6), 'rail')]
        return joinery(seed, path, parts, iron=hin + handle, studs=studs)
    if species == 'acacia':
        slats = np.zeros((N, N), F32)
        for k in range(5):
            x0 = 2.6 + k * 2.2
            slats = np.maximum(slats, rect(x0, 2.6, x0 + 1.4, 13.4))
        parts = frame_parts(2.6, 2.6, 2.6) + [(slats, 'stile')]
        holes = np.clip(rect(2.6, 2.6, 13.4, 13.4) - slats, 0, 1) if up else None
        if not up:
            parts.append((np.clip(rect(2.6, 2.6, 13.4, 13.4) - slats, 0, 1), 'panel'))
        return joinery(seed, path, parts, holes=holes, iron=hin + handle, studs=studs)
    if species == 'dark_oak':
        parts = frame_parts(2.2, 2.2, 2.2) + [(rect(2.2, 2.2, 13.8, 13.8), 'panel')]
        st = [(x, y, 0.3) for x in (4.0, 8.0, 12.0) for y in (4.0, 8.0, 12.0)]
        return joinery(seed, path, parts, iron=hin + handle + [rect(2.2, 7.6, 13.8, 8.4)], studs=st + studs,
                       vertical_boards=3)
    if species == 'mangrove':
        parts = frame_parts(2.2, 2.2, 2.2)
        weave = np.zeros((N, N), F32)
        for k in range(4):
            y0 = 2.6 + k * 2.8
            weave = np.maximum(weave, rect(2.2, y0, 13.8, y0 + 2.0))
        parts.append((weave, 'rail'))
        holes = np.clip(rect(2.2, 2.2, 13.8, 13.8) - weave, 0, 1) if up else None
        if not up:
            parts.append((np.clip(rect(2.2, 2.2, 13.8, 13.8) - weave, 0, 1), 'panel'))
        return joinery(seed, path, parts, holes=holes, iron=hin + handle, studs=studs)
    if species == 'cherry':
        parts = frame_parts(2.0, 2.0, 2.0)
        if up:
            grid_m = np.zeros((N, N), F32)
            for gx in (5.5, 8.0, 10.5):
                grid_m = np.maximum(grid_m, rect(gx - 0.35, 2.0, gx + 0.35, 14.0))
            for gy in (5.0, 8.0, 11.0):
                grid_m = np.maximum(grid_m, rect(2.0, gy - 0.35, 14.0, gy + 0.35))
            win = rect(3.0, 3.0, 13.0, 13.0)
            holes = np.clip(win - grid_m, 0, 1)
            parts += [(grid_m * win, 'rail'), (rect(2.0, 2.0, 14.0, 14.0) * (1 - win), 'panel')]
            return joinery(seed, path, parts, holes=holes, iron=hin, studs=studs)
        parts += [(rect(2.0, 2.0, 14.0, 14.0), 'panel')]
        return joinery(seed, path, parts, iron=hin + handle, studs=studs)
    if species == 'pale_oak':
        parts = frame_parts(2.4, 2.4, 2.4) + [(rect(2.4, 2.4, 13.6, 13.6), 'panel')]
        holes = rect(5.4, 4.0, 10.6, 9.2) if up else None
        if up:
            parts.append((rect(4.8, 3.4, 11.2, 9.8) - rect(5.4, 4.0, 10.6, 9.2), 'rail'))
        return joinery(seed, path, parts, holes=holes, iron=hin + handle, studs=studs)
    if species == 'poplar':
        parts = frame_parts(2.4, 2.4, 2.4) + [(rect(2.4, 2.4, 13.6, 13.6), 'panel')]
        holes = (arch_window(3.8, 6.8, 3.0, 13.0) + arch_window(9.2, 12.2, 3.0, 13.0)) if up else None
        return joinery(seed, path, parts, holes=holes, iron=hin + handle, studs=studs)
    if species == 'bamboo':
        poles = np.zeros((N, N), F32)
        for k in range(6):
            x0 = 0.4 + k * 2.6
            poles = np.maximum(poles, rect(x0, -1, x0 + 2.2, 17))
        parts = [(rect(0, 1.4, 16, 3.0), 'rail'), (rect(0, 13.0, 16, 14.6), 'rail')]
        holes = None
        if up:
            gaps = np.zeros((N, N), F32)
            for k in range(6):
                x0 = 0.4 + k * 2.6 + 2.2
                gaps = np.maximum(gaps, rect(x0, 3.4, x0 + 0.4, 12.6))
            holes = gaps
        return joinery(seed, path, parts, holes=holes, iron=handle, studs=studs, vertical_boards=6)
    # crimson / warped: organic fungal joinery with round vents
    parts = frame_parts(2.2, 2.2, 2.2) + [(rect(2.2, 2.2, 13.8, 13.8), 'panel')]
    holes = None
    if up:
        holes = np.clip(circle(5.6, 6.0, 1.3) + circle(10.4, 6.0, 1.3) + circle(8.0, 10.2, 1.3), 0, 1)
    return joinery(seed, path, parts, holes=holes, iron=hin + handle, studs=studs)


def trapdoor(species, seed):
    d = DOORS[species]
    path = d['trap']
    if species in ('oak', 'poplar', 'pale_oak', 'cherry'):
        parts = frame_parts(2.2, 2.2, 2.2) + [(rect(2.2, 7.3, 13.8, 8.7), 'rail')]
        holes = np.clip(rect(3.6, 3.4, 7.2, 6.4) + rect(8.8, 3.4, 12.4, 6.4) + rect(3.6, 9.6, 7.2, 12.6)
                        + rect(8.8, 9.6, 12.4, 12.6), 0, 1)
        if species == 'pale_oak':
            holes = None
            parts.append((rect(2.2, 2.2, 13.8, 13.8), 'panel'))
        if species == 'cherry':
            holes = np.clip(rect(3.2, 3.2, 12.8, 12.8) - rect(7.6, 2, 8.4, 14) - rect(2, 7.6, 14, 8.4), 0, 1)
        return joinery(seed, path, parts, holes=holes, iron=[rect(-0.2, 3.0, 4.5, 4.1), rect(-0.2, 11.9, 4.5, 13.0)])
    if species in ('spruce', 'dark_oak'):
        parts = [(rect(0, 1.0, 16, 3.0), 'rail'), (rect(0, 13.0, 16, 15.0), 'rail')]
        st = [(x, y, 0.28) for x in (2.0, 6.0, 10.0, 14.0) for y in (2.0, 14.0)]
        return joinery(seed, path, parts, studs=st, vertical_boards=4)
    if species == 'birch':
        parts = frame_parts(2.0, 2.0, 2.0) + [(rect(2.0, 2.0, 14.0, 14.0), 'panel')]
        holes = np.clip(circle(8, 8, 2.6) - rect(7.6, 4, 8.4, 12) - rect(4, 7.6, 12, 8.4), 0, 1)
        return joinery(seed, path, parts, holes=holes)
    if species in ('jungle', 'mangrove'):
        parts = frame_parts(2.0, 2.0, 2.0)
        slats = np.zeros((N, N), F32)
        for k in range(4):
            y0 = 2.6 + k * 2.9
            slats = np.maximum(slats, rect(2.0, y0, 14.0, y0 + 1.9))
        parts.append((slats, 'rail'))
        holes = np.clip(rect(2.0, 2.0, 14.0, 14.0) - slats, 0, 1)
        return joinery(seed, path, parts, holes=holes)
    if species == 'acacia':
        parts = frame_parts(2.0, 2.4, 2.4)
        slats = np.zeros((N, N), F32)
        for k in range(4):
            x0 = 2.8 + k * 2.8
            slats = np.maximum(slats, rect(x0, 2.4, x0 + 1.6, 13.6))
        parts.append((slats, 'stile'))
        holes = np.clip(rect(2.0, 2.4, 14.0, 13.6) - slats, 0, 1)
        return joinery(seed, path, parts, holes=holes)
    if species == 'bamboo':
        parts = [(rect(0, 2.0, 16, 3.6), 'rail'), (rect(0, 12.4, 16, 14.0), 'rail')]
        gaps = np.zeros((N, N), F32)
        for k in range(6):
            x0 = 0.4 + k * 2.6 + 2.2
            gaps = np.maximum(gaps, rect(x0, 4.0, x0 + 0.4, 12.0))
        return joinery(seed, path, parts, holes=gaps, vertical_boards=6)
    parts = frame_parts(2.2, 2.2, 2.2) + [(rect(2.2, 2.2, 13.8, 13.8), 'panel')]
    holes = np.clip(circle(5.4, 5.4, 1.2) + circle(10.6, 5.4, 1.2) + circle(5.4, 10.6, 1.2) + circle(10.6, 10.6, 1.2), 0, 1)
    return joinery(seed, path, parts, holes=holes)


# ------------------------------------------------------------------ registration
LOGS = [
    # species, side, top, stripped side, stripped top, planks, bark kind, plank options
    ('oak', 'log_oak', 'log_oak_top', 'stripped_oak_log', 'stripped_oak_log_top', 'planks_oak',
     dict(kind='furrowed', plates=(7, 2), inner='#3b2a1c'), dict(pores=0.6, spacing=0.5)),
    ('spruce', 'log_spruce', 'log_spruce_top', 'stripped_spruce_log', 'stripped_spruce_log_top', 'planks_spruce',
     dict(kind='furrowed', plates=(11, 4), inner='#4a2616', depth=1.1), dict(spacing=0.42, knot_rate=0.45)),
    ('jungle', 'log_jungle', 'log_jungle_top', 'stripped_jungle_log', 'stripped_jungle_log_top', 'planks_jungle',
     dict(kind='furrowed', plates=(9, 3), inner='#2a2410'), dict(spacing=0.65, arch=0.04)),
    ('acacia', 'log_acacia', 'log_acacia_top', 'stripped_acacia_log', 'stripped_acacia_log_top', 'planks_acacia',
     dict(kind='furrowed', plates=(6, 2), inner='#5b2a14', depth=1.3), dict(spacing=0.55)),
    ('dark_oak', 'log_big_oak', 'log_big_oak_top', 'stripped_dark_oak_log', 'stripped_dark_oak_log_top',
     'planks_big_oak', dict(kind='furrowed', plates=(8, 3), inner='#1a120a', depth=1.2), dict(pores=0.5, spacing=0.5)),
    ('mangrove', 'mangrove_log_side', 'mangrove_log_top', 'stripped_mangrove_log_side', 'stripped_mangrove_log_top',
     'mangrove_planks', dict(kind='fibrous', plates=(10, 2), inner='#3a1712'), dict(spacing=0.6)),
    ('pale_oak', 'pale_oak_log_side', 'pale_oak_log_top', 'stripped_pale_oak_log_side', 'stripped_pale_oak_log_top',
     'pale_oak_planks', dict(kind='shallow', plates=(8, 2), inner='#3a3433'), dict(spacing=0.55, pores=0.3)),
    ('poplar', 'poplar_log_side', 'poplar_log_top', 'stripped_poplar_log_side', 'stripped_poplar_log_top',
     'poplar_planks', dict(kind='shallow', plates=(9, 3), inner='#2c2016'), dict(spacing=0.6)),
]


def register(R):
    for i, (sp, side, top, sside, stop, plank, bk, pk) in enumerate(LOGS):
        s = 400 + 20 * i
        bkw = dict(bk)
        kind = bkw.pop('kind')
        R.block(side, lambda v, s=s, side=side, kind=kind, bkw=bkw: bark(s, side, kind, **bkw))
        R.block(top, lambda v, s=s, top=top, side=side: log_top(s + 1, top, bark_path=side))
        R.block(sside, lambda v, s=s, sside=sside, pk=pk: stripped_side(s + 2, sside, spacing=pk.get('spacing', 0.55),
                                                                         pores=pk.get('pores', 0.0)))
        R.block(stop, lambda v, s=s, stop=stop: log_top(s + 3, stop, stripped=True))
        R.block(plank, lambda v, s=s, plank=plank, pk=pk: planks(s + 4, plank, **pk))
    # birch and cherry have smooth, lenticelled bark
    R.block('log_birch', lambda v: birch_bark(560, 'log_birch'))
    R.block('log_birch_top', lambda v: log_top(561, 'log_birch_top', bark_path='log_birch'))
    R.block('stripped_birch_log', lambda v: stripped_side(562, 'stripped_birch_log', spacing=0.7))
    R.block('stripped_birch_log_top', lambda v: log_top(563, 'stripped_birch_log_top', stripped=True))
    R.block('planks_birch', lambda v: planks(564, 'planks_birch', spacing=0.7, arch=0.04, knot_rate=0.15))
    R.block('cherry_log_side', lambda v: lenticel_bark(570, 'cherry_log_side', '#b9867a'))
    R.block('cherry_log_top', lambda v: log_top(571, 'cherry_log_top', bark_path='cherry_log_side'))
    R.block('stripped_cherry_log_side', lambda v: stripped_side(572, 'stripped_cherry_log_side', spacing=0.6))
    R.block('stripped_cherry_log_top', lambda v: log_top(573, 'stripped_cherry_log_top', stripped=True))
    R.block('cherry_planks', lambda v: planks(574, 'cherry_planks', spacing=0.6, arch=0.05))
    R.block('stripped_poplar_side_log', lambda v: stripped_side(575, 'stripped_poplar_side_log', spacing=0.6))
    # bamboo
    R.block('bamboo_block', lambda v: bamboo_side(580, 'bamboo_block'))
    R.block('bamboo_block_top', lambda v: bamboo_top(581, 'bamboo_block_top'))
    R.block('stripped_bamboo_block', lambda v: bamboo_side(582, 'stripped_bamboo_block', stripped=True))
    R.block('stripped_bamboo_block_top', lambda v: bamboo_top(583, 'stripped_bamboo_block_top', stripped=True))
    R.block('bamboo_planks', lambda v: bamboo_planks(584, 'bamboo_planks'))
    R.block('bamboo_mosaic', lambda v: bamboo_planks(585, 'bamboo_mosaic', mosaic=True))
    # huge fungi
    R.anim('huge_fungus/crimson_log_side', lambda f, n: stem_side(590, 'huge_fungus/crimson_log_side', f, n,
                                                                  '#ff6a3d'), 5)
    R.anim('huge_fungus/warped_stem_side', lambda f, n: stem_side(591, 'huge_fungus/warped_stem_side', f, n,
                                                                 '#3dffd5'), 5)
    R.block('huge_fungus/crimson_log_top', lambda v: log_top(592, 'huge_fungus/crimson_log_top',
                                                             bark_path='huge_fungus/stripped_crimson_stem_side',
                                                             spacing=0.6, checks=1))
    R.block('huge_fungus/warped_stem_top', lambda v: log_top(593, 'huge_fungus/warped_stem_top',
                                                            bark_path='huge_fungus/stripped_warped_stem_side',
                                                            spacing=0.6, checks=1))
    R.block('huge_fungus/stripped_crimson_stem_side',
            lambda v: stripped_side(594, 'huge_fungus/stripped_crimson_stem_side', spacing=0.8, knot_rate=0))
    R.block('huge_fungus/stripped_crimson_stem_top',
            lambda v: log_top(595, 'huge_fungus/stripped_crimson_stem_top', stripped=True, spacing=0.6, checks=1))
    R.block('huge_fungus/stripped_warped_stem_side',
            lambda v: stripped_side(596, 'huge_fungus/stripped_warped_stem_side', spacing=0.8, knot_rate=0))
    R.block('huge_fungus/stripped_warped_stem_top',
            lambda v: log_top(597, 'huge_fungus/stripped_warped_stem_top', stripped=True, spacing=0.6, checks=1))
    R.block('huge_fungus/crimson_planks', lambda v: planks(598, 'huge_fungus/crimson_planks', spacing=0.7,
                                                           knot_rate=0.0, nails=False))
    R.block('huge_fungus/warped_planks', lambda v: planks(599, 'huge_fungus/warped_planks', spacing=0.7,
                                                          knot_rate=0.0, nails=False))
    # doors and trapdoors
    for j, sp in enumerate(DOORS):
        R.block(DOORS[sp]['lower'], lambda v, sp=sp, j=j: door(sp, 'lower', 600 + 3 * j), cutout=True)
        R.block(DOORS[sp]['upper'], lambda v, sp=sp, j=j: door(sp, 'upper', 601 + 3 * j), cutout=True)
        R.block(DOORS[sp]['trap'], lambda v, sp=sp, j=j: trapdoor(sp, 602 + 3 * j), cutout=True)
