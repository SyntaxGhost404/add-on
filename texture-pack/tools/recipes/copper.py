"""Copper family across its four ageing stages. A single patina model drives every block: verdigris forms
first in recesses and seams, spreads over flat areas, and leaves raised edges coppery longest."""
import numpy as np

from engine.noise import F32, fbm, blur, smoothstep
from engine.color import ramp, mix, match_mean, hexrgb
from engine.material import Tex, MASTER, cavity
from engine.draw import X, Y, rect, circle, polygon
from recipes.stones import frame_mask
from recipes.plants import mask_of
from registry import CALIBRATION

N = MASTER
STAGES = ['', 'exposed_', 'weathered_', 'oxidized_']
METAL = [(0, '#7a3a22'), (0.35, '#b2603e'), (0.7, '#d88a62'), (1, '#f6c2a0')]
TARNISH = [(0, '#5a3a2e'), (0.5, '#94665a'), (1, '#c09a8a')]
VERDIGRIS = [(0, '#2a5a4a'), (0.4, '#3f8a72'), (0.75, '#5fb89a'), (1, '#9ae0c8')]


def cal(path):
    c = CALIBRATION['textures/blocks/' + path]
    return np.array(c['mean'], F32), float(c['lum'])


def patina(stage, h, seed, *, metal_t=None):
    """Colour a copper surface for ageing stage 0..3 given its height field (0..1)."""
    mt = metal_t if metal_t is not None else 0.5 + 0.25 * (h - 0.5) + 0.12 * fbm(N, 6, seed, 3)
    metal = ramp(np.clip(mt + 0.05 * fbm(N, (2, 40), seed + 1, 2), 0, 1), METAL)
    tarn = ramp(np.clip(mt, 0, 1), TARNISH)
    verd = ramp(np.clip(0.5 + 0.25 * fbm(N, 5, seed + 2, 4) + 0.1 * fbm(N, 30, seed + 3, 2), 0, 1), VERDIGRIS)
    cav = np.clip(cavity(h) * 2.5, 0, 1)
    spread = fbm(N, 4, seed + 4, 5) * 0.5 + 0.5
    drip = smoothstep(0.6, 0.9, fbm(N, (14, 2), seed + 5, 3))
    if stage == 0:
        spots = smoothstep(0.72, 0.85, spread) * 0.35
        return mix(metal, tarn, spots + 0.15 * cav)
    if stage == 1:
        base = mix(metal, tarn, 0.55 + 0.25 * (spread - 0.5))
        g = np.clip(smoothstep(0.55, 0.8, spread) * 0.3 + cav * 0.5, 0, 1)
        return mix(base, verd * 0.9, g)
    if stage == 2:
        base = mix(tarn, metal, 0.3)
        g = np.clip(smoothstep(0.3, 0.6, spread + 0.25 * cav - 0.2 * (h - 0.5)) + 0.6 * cav, 0, 1)
        return mix(base, verd, g * 0.95)
    out = mix(verd, verd * 0.8, drip * 0.5)
    edge = smoothstep(0.85, 0.95, h) * smoothstep(0.75, 0.9, spread) * 0.25
    return mix(out, tarn, edge)


def plates(seed, panels=2, rivets=False):
    """Height field for rolled copper sheet with panel seams."""
    roll = fbm(N, (2, 30), seed, 3)
    dent = fbm(N, 7, seed + 1, 3)
    h = 0.6 + 0.04 * roll + 0.05 * dent
    step = 16 / panels
    seam = np.zeros((N, N), F32)
    for k in range(panels + 1):
        seam = np.maximum(seam, 1 - smoothstep(0.1, 0.35, np.abs(X - k * step)))
        seam = np.maximum(seam, 1 - smoothstep(0.1, 0.35, np.abs(Y - k * step)))
    h = h - 0.35 * seam
    if rivets:
        for k in range(panels + 1):
            for j in range(panels + 1):
                cx, cy = min(max(k * step, 1.0), 15.0), min(max(j * step, 1.0), 15.0)
                h = np.maximum(h, circle(cx, cy, 0.4) * 0.95)
    return np.clip(h, 0, 1)


def copper_tex(stage, h, path, seed, *, gloss=None, alpha=None, emissive=None, cutout=False):
    mean, lum = cal(path)
    rgb = patina(stage, h, seed)
    g = gloss if gloss is not None else [0.35, 0.22, 0.12, 0.04][stage]
    rgb = match_mean(rgb, lum, None if alpha is None else alpha > 0.5)
    return Tex(rgb, h, alpha, light='top', bump=1.2, ao=0.55, gloss=g, emissive=emissive, cutout=cutout)


# ------------------------------------------------------------------ designs
def block_h(seed):
    return plates(seed, 2)


def cut_h(seed):
    h = plates(seed, 4)
    b = np.minimum(np.minimum(X % 4, 4 - X % 4), np.minimum(Y % 4, 4 - Y % 4))
    return np.clip(h * 0.6 + 0.4 * smoothstep(0.0, 0.6, b), 0, 1)


def chiseled_h(seed):
    base = plates(seed, 1)
    rel = np.clip(frame_mask(0.8, 1.2) + (rect(4, 4, 12, 12) - rect(5.2, 5.2, 10.8, 10.8)) + circle(8, 8, 1.6)
                  + polygon([(8, 5.8), (10.2, 8), (8, 10.2), (5.8, 8)]) * 0.0, 0, 1)
    return np.clip(0.35 + 0.5 * blur(rel, 1.0) + 0.1 * base, 0, 1)


def grate_alpha():
    holes = np.zeros((N, N), F32)
    for i in range(4):
        for j in range(4):
            x0, y0 = 1.6 + i * 3.4, 1.6 + j * 3.4
            hx = rect(x0 + 0.25, y0 + 0.25, x0 + 2.75, y0 + 2.75)
            holes = np.maximum(holes, hx)
    return 1 - holes


def bulb(stage, lit, powered, path, seed):
    h = plates(seed, 1)
    frame = frame_mask(0.0, 2.6)
    window = rect(3.2, 3.2, 12.8, 12.8)
    cross = np.clip(rect(7.4, 2.6, 8.6, 13.4) + rect(2.6, 7.4, 13.4, 8.6), 0, 1)
    h = np.clip(0.5 + 0.4 * frame + 0.3 * cross - 0.2 * window * (1 - cross), 0, 1)
    mean, lum = cal(path)
    rgb = patina(stage, h, seed)
    glass = window * (1 - cross)
    if lit:
        r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
        core = ramp(np.clip(1 - r / 7, 0, 1), [(0, '#e88a3a'), (0.6, '#ffd27a'), (1, '#fff6d8')])
        rgb = mix(rgb, core, glass)
        em = (glass * np.clip(1 - r / 9, 0.3, 1) * 0.6)[..., None] * hexrgb('#ffdc9a')
    else:
        dark = ramp(np.clip(0.4 + 0.3 * fbm(N, 6, seed, 3), 0, 1), [(0, '#2a2420'), (1, '#5a4a40')])
        rgb = mix(rgb, dark, glass)
        em = None
    if powered:
        dot = circle(8, 8, 0.9)
        rgb = mix(rgb, hexrgb('#e02a1a'), dot)
        em = (em if em is not None else 0) + (dot * 0.6)[..., None] * hexrgb('#ff3a1a')
    t = Tex(match_mean(rgb, lum), h, light='top', bump=1.2, ao=0.55, gloss=[0.35, 0.22, 0.12, 0.04][stage],
            emissive=em)
    return t


def copper_door(stage, half, path, seed):
    h = plates(seed, 2, rivets=False)
    frame = frame_mask(0.0, 2.0)
    h = np.clip(h * 0.6 + 0.35 * frame, 0, 1)
    rv = np.zeros((N, N), F32)
    for x in (1.0, 15.0):
        for y in (1.0, 5.5, 10.5, 15.0):
            rv = np.maximum(rv, circle(x, y, 0.42))
    h = np.maximum(h, rv)
    alpha = None
    if half == 'top':
        porthole = circle(8, 8, 3.6)
        ring = np.clip(circle(8, 8, 4.6) - porthole, 0, 1)
        h = np.maximum(h, ring * 0.95)
        bar = rect(7.5, 4.4, 8.5, 11.6) * porthole
        alpha = np.clip(1 - porthole + bar, 0, 1)
        h = np.maximum(h, bar * 0.8)
    else:
        handle = rect(12.4, 1.0, 13.6, 4.4)
        h = np.maximum(h, handle * 0.95)
        panel = rect(3.0, 6.0, 13.0, 13.0) - rect(3.8, 6.8, 12.2, 12.2)
        h = np.clip(h + 0.2 * panel, 0, 1)
    return copper_tex(stage, h, path, seed, alpha=alpha, cutout=alpha is not None)


def copper_trapdoor(stage, path, seed):
    h = plates(seed, 2)
    frame = frame_mask(0.0, 2.0)
    h = np.clip(h * 0.6 + 0.35 * frame, 0, 1)
    holes = np.zeros((N, N), F32)
    for (cx, cy) in ((5.2, 5.2), (10.8, 5.2), (5.2, 10.8), (10.8, 10.8)):
        holes = np.maximum(holes, circle(cx, cy, 1.6))
    ring = np.clip(blur(holes, 2.0) * 2 - holes, 0, 1)
    h = np.maximum(h, ring * 0.9)
    return copper_tex(stage, h, path, seed, alpha=1 - holes, cutout=True)


def masked_metal(stage, path, seed, *, glow=None, glow_region=None, frame=0, frames=1):
    m = mask_of(path).astype(F32)
    h = 0.55 + 0.25 * np.cos(np.pi * ((X % 2) / 2 - 0.5)) + 0.08 * fbm(N, 10, seed, 2)
    rgb = patina(stage, np.clip(h, 0, 1), seed)
    mean, lum = cal(path)
    em = None
    if glow is not None and glow_region is not None:
        flick = 0.85 + 0.15 * np.sin(2 * np.pi * frame / max(frames, 1))
        g = glow_region * m
        rgb = mix(rgb, hexrgb(glow) * flick, g)
        em = (g * 0.6 * flick)[..., None] * hexrgb(glow)
    rgb = match_mean(rgb, lum, m > 0.5)
    return Tex(rgb, np.clip(h, 0, 1), m, light='top', bump=1.0, ao=0.4, cutout=True,
               gloss=[0.3, 0.2, 0.1, 0.04][stage], emissive=em)


def chest_icon(stage, face, path, seed):
    h = plates(seed, 1)
    frame = frame_mask(0.0, 1.4)
    h = np.clip(h * 0.6 + 0.35 * frame, 0, 1)
    if face in ('front', 'side'):
        lid = 1 - smoothstep(0.1, 0.3, np.abs(Y - 6.0))
        h = h - 0.3 * lid
        if face == 'front':
            latch = rect(7.0, 4.6, 9.0, 8.4)
            h = np.maximum(h, latch * 0.95)
    return copper_tex(stage, np.clip(h, 0, 1), path, seed)


# ------------------------------------------------------------------ registration
def register(R):
    for si, pre in enumerate(STAGES):
        s = 2400 + 40 * si
        base = 'copper_block' if pre == '' else f'{pre}copper'
        R.block(base, lambda v, si=si, base=base, s=s: copper_tex(si, block_h(s), base, s))
        R.block(f'{pre}cut_copper', lambda v, si=si, pre=pre, s=s: copper_tex(si, cut_h(s + 1), f'{pre}cut_copper', s + 1))
        R.block(f'{pre}chiseled_copper', lambda v, si=si, pre=pre, s=s:
                copper_tex(si, chiseled_h(s + 2), f'{pre}chiseled_copper', s + 2))
        R.block(f'{pre}copper_grate', lambda v, si=si, pre=pre, s=s:
                copper_tex(si, plates(s + 3, 4), f'{pre}copper_grate', s + 3, alpha=grate_alpha(), cutout=True),
                cutout=True)
        for lit in (False, True):
            for pw in (False, True):
                name = f'{pre}copper_bulb' + ('_lit' if lit else '') + ('_powered' if pw else '')
                R.block(name, lambda v, si=si, lit=lit, pw=pw, name=name, s=s: bulb(si, lit, pw, name, s + 4))
        R.block(f'{pre}copper_door_bottom', lambda v, si=si, pre=pre, s=s:
                copper_door(si, 'bottom', f'{pre}copper_door_bottom', s + 5))
        R.block(f'{pre}copper_door_top', lambda v, si=si, pre=pre, s=s:
                copper_door(si, 'top', f'{pre}copper_door_top', s + 6), cutout=True)
        R.block(f'{pre}copper_trapdoor', lambda v, si=si, pre=pre, s=s:
                copper_trapdoor(si, f'{pre}copper_trapdoor', s + 7), cutout=True)
        for part in ('copper_bars', 'copper_chain1', 'copper_chain2'):
            R.block(f'{pre}{part}', lambda v, si=si, p=f'{pre}{part}', s=s: masked_metal(si, p, s + 8), cutout=True)
        rod = 'lightning_rod' if pre == '' else f'{pre}lightning_rod'
        R.block(rod, lambda v, si=si, rod=rod, s=s: masked_metal(si, rod, s + 9), cutout=True)
        glass = rect(1.5, 3.0, 4.5, 13.0)
        R.anim(f'{pre}copper_lantern', lambda f, n, si=si, p=f'{pre}copper_lantern', s=s:
               masked_metal(si, p, s + 10, glow='#9af0c8', glow_region=glass, frame=f, frames=n), 3, cutout=True)
        for face in ('front', 'side', 'top'):
            p = f'{pre}copper_chest_inventory_{face}'
            R.block(p, lambda v, si=si, face=face, p=p, s=s: chest_icon(si, face, p, s + 11))

    def torch(v):
        m = mask_of('copper_torch').astype(F32)
        handle = ramp(np.clip(0.5 + 0.3 * np.cos(np.pi * ((X - 7) / 2 - 0.5)), 0, 1), METAL)
        flame = (Y < 8.0)
        rgb = np.where(flame[..., None], hexrgb('#b8f2a0'), handle)
        t = Tex(rgb, None, m, light='none', cutout=True,
                emissive=(flame * m * 0.6)[..., None] * hexrgb('#a0ffb0'))
        return t
    R.block('copper_torch', torch, cutout=True)
    R.block('lightning_rod_powered', lambda v: Tex(np.ones((N, N, 3), F32), None, mask_of('lightning_rod_powered')
                                                   .astype(F32), light='none', cutout=True), cutout=True)
