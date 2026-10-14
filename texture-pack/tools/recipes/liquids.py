"""Animated liquids and fire. Every flipbook loops seamlessly: waves use whole-number wave vectors and
temporal frequencies, and drifting noise moves along closed paths through its periodic domain."""
import numpy as np

from engine.noise import F32, fbm, grid, norm01, smoothstep, rng, ridged
from engine.color import ramp, mix, match_mean, hexrgb
from engine.material import Tex, MASTER
from engine.draw import X, Y
from registry import CALIBRATION

N = MASTER


def cal(path):
    c = CALIBRATION['textures/blocks/' + path]
    return np.array(c['mean'], F32), float(c['lum'])


GX, GY = grid(N)


def waves(seed, t, count=9, kmin=2, kmax=6, wmin=1, wmax=3, flow=0.0):
    """Sum of travelling sine waves, periodic in space (tile) and in t (0..1 = one loop)."""
    r = rng(seed)
    h = np.zeros((N, N), F32)
    gx = np.zeros((N, N), F32)
    gy = np.zeros((N, N), F32)
    for i in range(count):
        kx, ky = 0, 0
        while kx == 0 and ky == 0:
            kx, ky = int(r.integers(-kmax, kmax + 1)), int(r.integers(-kmax, kmax + 1))
            if kx * kx + ky * ky < kmin * kmin:
                kx, ky = 0, 0
        w = int(r.integers(wmin, wmax + 1)) * r.choice([-1, 1])
        a = 1.0 / np.sqrt(kx * kx + ky * ky)
        ph = r.uniform(0, 2 * np.pi)
        arg = 2 * np.pi * (kx * GX + ky * (GY - flow * t) + w * t) + ph
        h += a * np.sin(arg)
        gx += a * np.cos(arg) * kx
        gy += a * np.cos(arg) * ky
    return h, gx, gy


def drift(seed, t, freq, octaves=4, radius=0.25, flow=0.0):
    """Periodic fbm sampled along a closed loop in its domain: animated, seamless in space and time."""
    ox = radius * np.cos(2 * np.pi * t)
    oy = radius * np.sin(2 * np.pi * t) - flow * t
    return fbm(N, freq, seed, octaves, x=GX + ox, y=GY + oy)


# ------------------------------------------------------------------ water
def water(frame, frames, seed=3000, path='water_still_grey', tint=None, flow=0.0, alpha_base=0.86):
    t = frame / frames
    h, gx, gy = waves(seed, t, flow=flow)
    h2, gx2, gy2 = waves(seed + 1, t, count=6, kmin=6, kmax=11, wmin=2, wmax=5, flow=flow)
    h = h + 0.35 * h2
    gx, gy = gx + 0.35 * gx2, gy + 0.35 * gy2
    s = 0.035
    nx, ny = -gx * s, -gy * s
    nz = np.ones_like(nx)
    inv = 1 / np.sqrt(nx * nx + ny * ny + 1)
    nx, ny, nz = nx * inv, ny * inv, nz * inv
    hx, hy, hz = -0.35, -0.55, 0.76
    spec = np.clip(nx * hx + ny * hy + nz * hz, 0, 1) ** 14
    crest = smoothstep(0.82, 0.97, 1 - np.abs(np.sin(np.pi * norm01(h2) * 2.0)))
    lum = 0.48 + 0.22 * norm01(h) + 0.3 * spec + 0.12 * crest
    if flow:
        streak = drift(seed + 3, t, (3, 10), 3, flow=flow * 1.0)
        lum = lum + 0.05 * streak
    mean, lumt = cal(path)
    rgb = np.repeat(np.clip(lum, 0, 1)[..., None], 3, axis=-1)
    rgb = match_mean(rgb, lumt)
    if tint is not None:
        rgb = np.clip(rgb * hexrgb(tint) / max(lumt, 1e-3) * lumt, 0, 1)
        rgb = match_mean(rgb, lumt)
    alpha = np.clip(alpha_base + 0.12 * spec + 0.06 * crest + 0.04 * norm01(h), 0, 1)
    return Tex(rgb.astype(F32), None, alpha.astype(F32), light='none', sharpen=0.0)


# ------------------------------------------------------------------ lava
def lava(frame, frames, seed=3100, path='lava_still', flow=0.0):
    t = frame / frames
    body = drift(seed, t, 3, 5, 0.18, flow)
    cells = drift(seed + 1, t, 6, 4, 0.12, flow)
    fine = drift(seed + 2, t, 14, 3, 0.08, flow)
    crust = smoothstep(0.15, 0.45, cells + 0.35 * body)
    heat = np.clip(0.55 + 0.35 * body - 0.6 * crust + 0.15 * fine, 0, 1)
    rgb = ramp(heat, [(0, '#2a0c04'), (0.25, '#6e1a06'), (0.45, '#c2420c'), (0.65, '#f07a18'), (0.85, '#ffc23a'),
                      (1, '#fff2a0')])
    mean, lum = cal(path)
    rgb = match_mean(rgb, lum)
    h = 0.5 + 0.4 * crust + 0.1 * fine
    em = (np.clip(heat - 0.45, 0, 1) * 0.35)[..., None] * hexrgb('#ffb04a')
    return Tex(rgb, norm01(h), None, light='top', bump=0.8, ao=0.3, emissive=em, sharpen=0.2)


def magma(frame, frames, seed=3200):
    from recipes.terrain import rock
    t = frame / frames
    base = rock(seed, [(0.0, '#1a0806'), (0.4, '#3a1208'), (0.7, '#5a1e0c'), (1.0, '#7a2e14')], cracks=0.0, pits=0.4,
                lumps=1.5)
    cracks = smoothstep(0.7, 0.9, ridged(N, 4, seed + 1, 4, sharp=1.8))
    pores = smoothstep(0.6, 0.82, fbm(N, 8, seed + 2, 3))
    glow = np.clip(cracks + 0.6 * pores, 0, 1) * (0.75 + 0.25 * np.sin(2 * np.pi * (t + 0.3 * fbm(N, 3, seed + 3, 2))))
    hot = ramp(np.clip(glow, 0, 1), [(0, '#5a1a08'), (0.5, '#e05a12'), (1, '#ffc24a')])
    rgb = mix(base.albedo, hot, np.clip(glow * 1.2, 0, 1))
    mean, lum = cal('magma')
    return Tex(match_mean(rgb, lum), norm01(base.height - 0.3 * cracks), light='top', bump=1.3, ao=0.6,
               emissive=(glow * 0.4)[..., None] * hexrgb('#ff8a2a'))


# ------------------------------------------------------------------ fire
def fire(frame, frames, seed=3300, path='fire_0', soul=False):
    t = frame / frames
    rise = drift(seed, t, (4, 3), 4, radius=0.0, flow=-2.0)
    tongues = drift(seed + 1, t, (7, 4), 3, radius=0.0, flow=-3.0)
    u = (GX - 0.5) * 2
    env = np.clip(1 - u * u * 0.55, 0, 1)
    height = 1 - GY
    streaks = drift(seed + 2, t, (12, 2), 2, radius=0.0, flow=-4.0)
    core = np.clip(1.5 - height * 1.05, 0, 1)
    inten = core * env * (0.62 + 0.45 * rise + 0.25 * tongues + 0.15 * streaks) + 0.3 * smoothstep(0.75, 1.0, GY)
    inten = np.clip(inten, 0, 1.2)
    alpha = (inten > 0.42).astype(F32)
    if soul:
        stops = [(0, '#0b3a46'), (0.45, '#1a8a9a'), (0.7, '#4ad6e0'), (0.9, '#b8fbff'), (1, '#ffffff')]
    else:
        stops = [(0, '#5a0e02'), (0.45, '#c2360a'), (0.65, '#f27a14'), (0.85, '#ffc63a'), (1, '#fff6c8')]
    rgb = ramp(np.clip((inten - 0.42) / 0.6, 0, 1), stops)
    mean, lum = cal(path)
    rgb = match_mean(rgb, lum, alpha > 0.5)
    return Tex(rgb, None, alpha, light='none', cutout=True, sharpen=0.0,
               emissive=None)


# ------------------------------------------------------------------ portal
def portal(frame, frames, seed=3400):
    t = frame / frames
    swirl = drift(seed, t, 3, 5, 0.3)
    fine = drift(seed + 1, t, 9, 3, 0.2)
    streaks = smoothstep(0.6, 0.95, ridged(N, 3, seed + 2, 3, sharp=2.0))
    v = np.clip(0.45 + 0.35 * swirl + 0.15 * fine + 0.2 * streaks, 0, 1)
    rgb = ramp(v, [(0, '#1a0640'), (0.4, '#4a10a2'), (0.7, '#8a3ae6'), (1, '#e0b8ff')])
    mean, lum = cal('portal')
    rgb = match_mean(rgb, lum)
    alpha = np.clip(0.55 + 0.25 * v, 0, 1)
    return Tex(rgb, None, alpha.astype(F32), light='none', sharpen=0.0)


# ------------------------------------------------------------------ glowing blocks
def sea_lantern(frame, frames, seed=3500):
    """A prismarine-framed lantern: faceted crystal panes glowing from within, pulsing gently."""
    t = frame / frames
    glow = drift(seed, t, 3, 4, 0.2)
    b = np.minimum(np.minimum(X, 16 - X), np.minimum(Y, 16 - Y))
    frame_m = 1 - smoothstep(1.4, 1.9, b)
    cross = np.clip(1 - smoothstep(0.5, 0.9, np.abs(X - 8)) + 1 - smoothstep(0.5, 0.9, np.abs(Y - 8)), 0, 1)
    frame_m = np.clip(frame_m + cross * 0.85, 0, 1)
    cx, cy = (np.floor(X / 8) * 8 + 4), (np.floor(Y / 8) * 8 + 4)
    ang = np.arctan2(Y - cy, X - cx)
    facet = (np.floor((ang + np.pi) / (np.pi / 3)) % 6) / 6
    rr = np.maximum(np.abs(X - cx), np.abs(Y - cy)) / 4
    v = np.clip(0.55 + 0.12 * glow + 0.18 * facet + 0.2 * (1 - rr) + 0.06 * np.sin(2 * np.pi * t), 0, 1)
    rgb = ramp(v, [(0, '#5a9a90'), (0.5, '#a8dcd2'), (0.85, '#e2f8f2'), (1, '#ffffff')])
    fr = ramp(np.clip(0.5 + 0.3 * fbm(N, 10, seed + 2, 3), 0, 1), [(0, '#3a7a6e'), (1, '#6aaa9c')])
    rgb = mix(rgb, fr, frame_m)
    mean, lum = cal('sea_lantern')
    h = 0.4 + 0.4 * frame_m + 0.15 * facet * (1 - frame_m)
    return Tex(match_mean(rgb, lum), norm01(h), light='top', bump=1.0, ao=0.4,
               emissive=((1 - frame_m) * 0.18)[..., None] * hexrgb('#e0fff8'))


# ------------------------------------------------------------------ registration
def register(R):
    R.anim('water_still_grey', lambda f, n: water(f, n), 32)
    R.anim('cauldron_water', lambda f, n: water(f, n, 3001, 'cauldron_water', alpha_base=0.8), 32)
    R.anim('water_still', lambda f, n: water(f, n, 3000, 'water_still', tint='#4a6ee0', alpha_base=1.0), 32)
    R.anim('water_flow_grey', lambda f, n: water(f, n, 3002, 'water_flow_grey', flow=2.0, alpha_base=1.0), 32,
           scale=2)
    R.anim('water_flow', lambda f, n: water(f, n, 3002, 'water_flow', tint='#4a6ee0', flow=2.0, alpha_base=1.0), 32,
           scale=2)
    R.anim('lava_still', lambda f, n: lava(f, n), 32)
    R.anim('lava_flow', lambda f, n: lava(f, n, 3101, 'lava_flow', flow=1.0), 16, scale=2)
    R.anim('magma', lambda f, n: magma(f, n), 3)
    R.anim('fire_0', lambda f, n: fire(f, n, 3300, 'fire_0'), 32, cutout=True)
    R.anim('fire_1', lambda f, n: fire(f, n, 3301, 'fire_1'), 32, cutout=True)
    R.anim('soul_fire_0', lambda f, n: fire(f, n, 3302, 'soul_fire_0', soul=True), 32, cutout=True)
    R.anim('soul_fire_1', lambda f, n: fire(f, n, 3303, 'soul_fire_1', soul=True), 32, cutout=True)
    R.anim('portal', lambda f, n: portal(f, n), 32)
    R.anim('sea_lantern', lambda f, n: sea_lantern(f, n), 5)
