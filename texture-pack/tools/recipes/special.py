"""Special blocks: trial chamber machines (vault, trial spawner, crafter), the sculk family, creaking
heart, spawner, cauldron/hopper/anvil/grindstone parts, cake, bell, brewing stand, campfires,
decorated pots and pottery patterns (original motifs), eggs, chests icons, shelves and more."""
import numpy as np

from engine.noise import F32, fbm, ridged, blur, warped_coords, smoothstep
from engine.color import ramp, mix, match_mean, hexrgb
from engine.material import MASTER
from engine.draw import X, Y, rect, circle, ellipse, polygon, polyline
from recipes.terrain import speckles, stone
from recipes.stones import tuff, polished, smooth_face
from recipes.machines import (tex, iron, dark_iron, board, oak, put, frame, stonework)
from recipes.wood import planks, bark, log_top
from recipes.plants import mask_of
from registry import CALIBRATION, INVENTORY

N = MASTER


def cal(path):
    c = CALIBRATION['textures/blocks/' + path]
    return np.array(c['mean'], F32), float(c['lum'])


def has(path):
    return ('textures/blocks/' + path) in INVENTORY


# ------------------------------------------------------------------ trial chambers
def chamber_metal(seed):
    t = polished(tuff(seed, 0.35), seed + 1, relief=0.4)
    ir, ih = dark_iron(seed + 2)
    return mix(t.albedo, ir, 0.35), t.height


def vault(face, state, ominous, seed=4500):
    sfx = {'off': '_off', 'on': '_on', 'ejecting': '_ejecting', 'plain': ''}[state]
    om = '_ominous' if ominous else ''
    path = f'vault_{face}{sfx}{om}' if face in ('front', 'side') else f'vault_{face}{sfx if state != "off" else ""}{om}'
    if not has(path):
        return None
    glow = '#4ad8e8' if ominous else '#f2a43a'
    rgb, h = chamber_metal(seed)
    fr = frame(1.6)
    rgb, h = put(rgb, h, fr, rgb * 0.75, 0.9)
    em = None
    alpha = None
    if face in ('front', 'side'):
        m = mask_of(path).astype(F32)
        alpha = m
        core = rect(3.0, 3.0, 13.0, 13.0) * m
        lit = state in ('on', 'ejecting')
        inner = ramp(np.clip(0.4 + 0.4 * (1 - np.sqrt((X - 8) ** 2 + (Y - 8) ** 2) / 7), 0, 1),
                     [(0, '#0a0c10'), (1, glow if lit else '#2a2e34')])
        rgb = mix(rgb, inner, core * 0.9)
        if lit:
            em = (core * 0.45)[..., None] * hexrgb(glow)
        if face == 'front':
            key = polygon([(8, 5.0), (10.2, 8), (8, 11.0), (5.8, 8)])
            rgb, h = put(rgb, h, key * m, hexrgb('#d8c070') if not ominous else hexrgb('#a8e8f0'), 0.9)
    elif face == 'top':
        ring = np.clip(circle(8, 8, 5.0) - circle(8, 8, 3.4), 0, 1)
        rgb, h = put(rgb, h, ring, rgb * 0.7, 0.4)
        if state == 'ejecting':
            rgb, h = put(rgb, h, circle(8, 8, 3.4), hexrgb(glow), 0.3)
            em = (circle(8, 8, 3.4) * 0.5)[..., None] * hexrgb(glow)
    return tex(rgb, h, path, alpha=alpha, emissive=em)


def spawner(face, state, ominous, seed=4520):
    om = '_ominous' if ominous else ''
    path = f'trial_spawner_{face}' + (f'_{state}' if state else '') + om
    if not has(path):
        return None
    glow = '#4ad8e8' if ominous else '#f2a43a'
    rgb, h = chamber_metal(seed)
    m = mask_of(path).astype(F32) if INVENTORY['textures/blocks/' + path]['alpha'] != 'none' else None
    bars = np.zeros((N, N), F32)
    for k in range(4):
        bars = np.maximum(bars, rect(1.5 + k * 4.0, 0, 2.5 + k * 4.0, 16))
    rgb = rgb * (1 - 0.15 * bars[..., None])
    em = None
    if state in ('active', 'ejecting_reward') or (face == 'top' and state == 'open'):
        r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
        core = 1 - smoothstep(3.0, 6.0, r)
        rgb = mix(rgb, hexrgb(glow), core * 0.7)
        em = (core * 0.4)[..., None] * hexrgb(glow)
    return tex(rgb, h, path, alpha=m, emissive=em)


def crafter(face, state, seed=4540):
    path = f'crafter_{face}' + (f'_{state}' if state else '')
    if not has(path):
        return None
    rgb, h = stonework(seed, 'smooth')
    rgb = rgb * 0.85
    fr = frame(1.6)
    pv, ph = board(seed + 1, 'planks_oak')
    rgb, h = put(rgb, h, fr, pv * 0.85, 0.9)
    em = None
    if face == 'top':
        grid = np.zeros((N, N), F32)
        for i in range(3):
            for j in range(3):
                grid = np.maximum(grid, rect(2.4 + i * 3.9, 2.4 + j * 3.9, 5.7 + i * 3.9, 5.7 + j * 3.9))
        slot = ramp(np.clip(0.3 + 0.2 * fbm(N, 8, seed, 2), 0, 1), [(0, '#1a1410'), (1, '#3a2e24')])
        lit = state == 'crafting'
        if lit:
            slot = mix(slot, hexrgb('#f2c25a'), 0.6)
            em = (grid * 0.3)[..., None] * hexrgb('#ffd27a')
        rgb, h = put(rgb, h, grid, slot, 0.3)
    elif face == 'bottom':
        pass
    else:
        mouth = rect(4.0, 5.0, 12.0, 11.0)
        dark = hexrgb('#120e0a')
        if state == 'triggered':
            dark = hexrgb('#5a1a10')
        elif state == 'crafting':
            dark = hexrgb('#f2a23a')
            em = (mouth * 0.4)[..., None] * hexrgb('#ffb04a')
        rgb, h = put(rgb, h, mouth, dark, 0.2)
        teeth = np.zeros((N, N), F32)
        for k in range(4):
            teeth = np.maximum(teeth, polygon([(4.4 + 2 * k, 5.0), (5.8 + 2 * k, 5.0), (5.1 + 2 * k, 6.4)]))
        ir, _ = iron(seed + 2, 0.5)
        rgb, h = put(rgb, h, teeth, ir, 0.7)
    return tex(rgb, h, path, emissive=em)


def creaking_heart(face, state, seed=4560):
    path = f'creaking_heart_{face}_{state}'
    if face == 'side':
        b = bark(seed, 'pale_oak_log_side', 'shallow', plates=(8, 2), inner='#3a3433')
    else:
        b = log_top(seed + 1, 'pale_oak_log_top', bark_path='pale_oak_log_side')
    rgb, h = b.albedo, b.height
    heart = ellipse(8, 8, 3.2, 4.4) if face == 'side' else circle(8, 8, 3.8)
    r = np.sqrt((X - 8) ** 2 + ((Y - 8) * (0.75 if face == 'side' else 1)) ** 2)
    if state == 'active':
        core = ramp(np.clip(1 - r / 4.0, 0, 1), [(0, '#5a1e0a'), (0.5, '#e2721a'), (1, '#ffd27a')])
        em = (heart * np.clip(1 - r / 4, 0, 1) * 0.6)[..., None] * hexrgb('#ff9a3a')
    elif state == 'dormant':
        core = ramp(np.clip(1 - r / 4.0, 0, 1), [(0, '#3a1a0a'), (1, '#8a4a1e')])
        em = (heart * 0.12)[..., None] * hexrgb('#ff9a3a')
    else:
        core = ramp(np.clip(1 - r / 4.0, 0, 1), [(0, '#2a2622'), (1, '#4a4440')])
        em = None
    veins = smoothstep(0.85, 0.97, ridged(N, 3, seed + 2, 3, sharp=2.0)) * (1 - heart)
    rgb = mix(rgb, core, heart)
    if state == 'active':
        rgb = mix(rgb, hexrgb('#c25a1a'), veins * 0.6)
    h = np.where(heart > 0.5, 0.3 + 0.2 * (1 - r / 4), h)
    return tex(rgb, h, path, emissive=em)


# ------------------------------------------------------------------ sculk
SCULK = [(0, '#020a0e'), (0.4, '#06222c'), (0.7, '#0c3a48'), (1, '#1a6a78')]


def sculk_surface(seed, frame_i=0, frames=1, density=1.0):
    x, y = warped_coords(N, 0.06, seed, freq=3)
    m = fbm(N, 5, seed + 1, 4, x=x, y=y)
    folds = smoothstep(0.8, 0.95, ridged(N, 6, seed + 2, 3, sharp=2.0))
    t = 0.45 + 0.2 * m - 0.15 * folds
    rgb = ramp(np.clip(t, 0, 1), SCULK)
    sp, sv = speckles(N, 22, seed + 3, 0.12 * density, 0.3)
    phase = frame_i / max(frames, 1)
    pulse = 0.5 + 0.5 * np.sin(2 * np.pi * (phase + sv))
    glow = sp * (0.3 + 0.7 * pulse)
    rgb = mix(rgb, hexrgb('#3ae8f0'), glow * 0.8)
    em = (glow * 0.35)[..., None] * hexrgb('#5af0ff')
    return rgb, 0.5 + 0.25 * m - 0.2 * folds, em


def sculk_block(frame_i, frames, seed=4600, path='sculk'):
    rgb, h, em = sculk_surface(seed, frame_i, frames)
    return tex(rgb, h, path, emissive=em)


def sculk_vein(frame_i, frames, seed=4601):
    path = 'sculk_vein'
    rgb, h, em = sculk_surface(seed, frame_i, frames, 1.5)
    veins = smoothstep(0.72, 0.9, ridged(N, 3, seed + 4, 4, sharp=1.6))
    blobs = smoothstep(0.35, 0.6, fbm(N, 5, seed + 5, 3))
    a = np.clip(veins + blobs * 0.8, 0, 1)
    a = (a > 0.5).astype(F32)
    return tex(rgb, h, path, alpha=a, emissive=em * a[..., None])


def sculk_part(path, seed, frame_i=0, frames=1, bloom=False, mask=False, tendril=False):
    rgb, h, em = sculk_surface(seed, frame_i, frames)
    if 'catalyst' in path and ('side' in path or 'bottom' in path):
        bone = ramp(np.clip(0.6 + 0.2 * fbm(N, (4, 12), seed + 6, 3), 0, 1), [(0, '#7a7a6a'), (1, '#d2d2c2')])
        lower = smoothstep(4.0, 6.0, Y) if 'side' in path else np.ones((N, N), F32)
        rgb = mix(rgb, bone, lower)
        h = mix(h, 0.6 + 0.1 * fbm(N, (4, 12), seed + 6, 3), lower)
        em = em * (1 - lower[..., None])
    if 'catalyst' in path and bloom:
        sp, sv = speckles(N, 6, seed + 7, 0.5, 0.45)
        pulse = 0.5 + 0.5 * np.sin(2 * np.pi * (frame_i / max(frames, 1) + sv))
        rgb = mix(rgb, hexrgb('#7af6ff'), sp * pulse)
        em = em + (sp * pulse * 0.5)[..., None] * hexrgb('#7af6ff')
    if 'shrieker' in path and 'side' in path:
        bone = ramp(np.clip(0.6 + 0.2 * fbm(N, (12, 4), seed + 8, 3), 0, 1), [(0, '#8a8a7a'), (1, '#e2e2d2')])
        rgb = mix(rgb, bone, smoothstep(9.0, 11.0, Y))
    if 'shrieker' in path and 'top' in path and 'inner' not in path:
        bone = ramp(np.clip(0.6 + 0.2 * fbm(N, 8, seed + 9, 3), 0, 1), [(0, '#b8b8a8'), (1, '#f2f2e2')])
        rgb = bone
    if 'inner_top' in path:
        r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
        pulse = 0.5 + 0.5 * np.sin(2 * np.pi * (frame_i / max(frames, 1)) - r * 0.6)
        col = '#3ae8f0' if 'can_summon' not in path else '#e8f8ff'
        rgb = mix(rgb, hexrgb(col), (1 - smoothstep(2.0, 6.0, r)) * pulse * 0.8)
        em = em + ((1 - smoothstep(2.0, 6.0, r)) * pulse * 0.4)[..., None] * hexrgb(col)
    if tendril:
        rgb = mix(rgb, hexrgb('#1ab8c8' if 'active' in path else '#0a5a68'), 0.6)
        if 'active' in path:
            em = em + 0.15 * hexrgb('#4af0ff')
    if 'calibrated' in path and 'amethyst' in path:
        rgb = ramp(np.clip(0.5 + 0.3 * fbm(N, 6, seed, 3), 0, 1), [(0, '#5a3a8a'), (1, '#d8b8ff')])
    alpha = None
    info = INVENTORY['textures/blocks/' + path]
    if info['alpha'] != 'none':
        alpha = mask_of(path).astype(F32)
    return tex(rgb, h, path, alpha=alpha, emissive=em)


# ------------------------------------------------------------------ cauldron, hopper, anvil, grindstone, spawner
def metal_part(path, seed, tone=0.35, rim_hole=None):
    rgb, h = iron(seed, tone)
    fr = frame(1.4)
    rgb = rgb * (1 - 0.2 * fr[..., None])
    alpha = mask_of(path).astype(F32) if INVENTORY['textures/blocks/' + path]['alpha'] != 'none' else None
    return tex(rgb, h + 0.2 * fr, path, alpha=alpha, gloss=0.15)


def anvil(path, seed=4700, damage=-1):
    rgb, h = iron(seed, 0.3)
    alpha = mask_of(path).astype(F32) if INVENTORY['textures/blocks/' + path]['alpha'] != 'none' else None
    if damage >= 0:
        from engine.draw import fractures
        lines, sheet = fractures(seed + damage, 2 + 3 * damage, (2, 6), (0.12, 0.22), kinks=4, jag=1.2, plane=0.3)
        rgb = rgb * (1 - 0.6 * lines[..., None])
        h = h - 0.3 * lines
    hammered = fbm(N, 10, seed + 1, 2)
    return tex(rgb, h + 0.05 * hammered, path, alpha=alpha, gloss=0.2)


def grindstone(path, seed=4710):
    if path == 'grindstone_pivot':
        rgb, h = board(seed, 'planks_big_oak', vertical=True)
    else:
        t = polished(stone(seed), seed + 1, relief=0.6)
        rgb, h = t.albedo, t.height
        if path == 'grindstone_round':
            r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
            rgb = rgb * (0.85 + 0.15 * np.cos(r * 3.0))[..., None]
    alpha = mask_of(path).astype(F32)
    return tex(rgb, h, path, alpha=alpha)


def mob_spawner(seed=4720):
    path = 'mob_spawner'
    rgb, h = dark_iron(seed)
    alpha = mask_of(path).astype(F32)
    return tex(rgb, h, path, alpha=alpha, gloss=0.2)


# ------------------------------------------------------------------ cake, bell, brewing, campfires
def cake(part, seed=4730):
    path = 'cake_' + part
    alpha = mask_of(path).astype(F32) if INVENTORY['textures/blocks/' + path]['alpha'] != 'none' else None
    if part == 'top':
        icing = ramp(np.clip(0.75 + 0.15 * fbm(N, 6, seed, 3), 0, 1), [(0, '#e8d8d2'), (1, '#fff8f4')])
        rgb = icing
        for k in range(6):
            a = k * np.pi / 3
            rgb = mix(rgb, hexrgb('#c8242a'), circle(8 + 4.0 * np.cos(a), 8 + 4.0 * np.sin(a), 0.75))
        h = 0.6 + 0.1 * fbm(N, 6, seed, 3)
    elif part in ('side', 'inner'):
        sponge = ramp(np.clip(0.5 + 0.2 * fbm(N, 14, seed + 1, 3), 0, 1), [(0, '#a8622a'), (1, '#e2a262')])
        icing_band = Y < 6.5
        rgb = np.where(icing_band[..., None], hexrgb('#f8f0ea'), sponge)
        jam = (np.abs(Y - 11.0) < 0.6)
        rgb = np.where(jam[..., None], hexrgb('#c8242a'), rgb)
        drip = (Y >= 6.5) & (Y < 7.5 + 1.5 * (fbm(N, (8, 1), seed + 2, 2) > 0.1))
        rgb = np.where(drip[..., None], hexrgb('#f2e8e2'), rgb)
        h = 0.5 + 0.1 * fbm(N, 14, seed + 1, 3)
    else:
        rgb = ramp(np.clip(0.5 + 0.2 * fbm(N, 10, seed + 3, 2), 0, 1), [(0, '#7a3a1a'), (1, '#b86a3a')])
        h = np.full((N, N), 0.5, F32)
    return tex(rgb, h, path, alpha=alpha)


def bell(part, seed=4740):
    path = 'bell_' + part
    alpha = mask_of(path).astype(F32)
    rgb = ramp(np.clip(0.6 + 0.25 * np.cos(np.pi * (X - 3.5) / 7) + 0.05 * fbm(N, 8, seed, 2), 0, 1),
               [(0, '#8a5a0a'), (0.5, '#e2a82a'), (1, '#fff2a0')])
    return tex(rgb, 0.5 + 0.2 * np.cos(np.pi * (X - 3.5) / 7), path, alpha=alpha, gloss=0.5)


def brewing(part, seed=4750):
    path = 'brewing_stand' if part == 'stand' else 'brewing_stand_base'
    if part == 'base':
        t = polished(smooth_face(seed, [(0, '#5a5658'), (0.5, '#7a7678'), (1, '#9a9698')]), seed + 1)
        return tex(t.albedo, t.height, path)
    alpha = mask_of(path).astype(F32)
    rgb = np.where((X > 7.0)[..., None] & (X < 9.0)[..., None], hexrgb('#e2c46a'), hexrgb('#5a4a3a'))
    rgb = rgb * (0.85 + 0.15 * fbm(N, 10, seed, 2))[..., None]
    return tex(rgb, None, path, alpha=alpha, light='none')


def campfire_log(lit=False, frame_i=0, frames=1, soul=False, seed=4760):
    path = ('soul_campfire_log_lit' if soul else 'campfire_log_lit') if lit else 'campfire_log'
    b = bark(seed, 'log_oak', 'furrowed', plates=(7, 2), inner='#3b2a1c')
    rgb, h = b.albedo, b.height
    em = None
    if lit:
        embers = smoothstep(0.75, 0.92, ridged(N, 4, seed + 1, 3, sharp=2.0))
        pulse = 0.6 + 0.4 * np.sin(2 * np.pi * (frame_i / max(frames, 1) + 0.5 * fbm(N, 3, seed + 2, 2)))
        col = '#ff7a2a' if not soul else '#4ae6f0'
        rgb = mix(rgb * 0.6, hexrgb(col), embers * pulse)
        em = (embers * pulse * 0.5)[..., None] * hexrgb(col)
        return tex(rgb, h, path, emissive=em)
    alpha = mask_of(path).astype(F32)
    return tex(rgb, h, path, alpha=alpha)


def campfire_flames(frame_i, frames, soul=False, seed=4770):
    from recipes.liquids import fire
    t = fire(frame_i, frames, seed, 'soul_fire_0' if soul else 'fire_0', soul=soul)
    path = 'soul_campfire' if soul else 'campfire'
    mean, lum = cal(path)
    return t.but(albedo=match_mean(t.albedo, lum, t.alpha > 0.5))


# ------------------------------------------------------------------ decorated pot and pottery motifs
CLAY = [(0, '#6a2e1e'), (0.5, '#9a4a32'), (1, '#c46a4a')]


def motif_shape(name):
    m = np.zeros((N, N), F32)
    if name == 'angler':
        m = np.clip(polyline([(8, 3), (8, 10), (6.4, 12), (5.0, 10.6)], [0.7] * 4)[0] + circle(8, 3, 0.9), 0, 1)
    elif name == 'archer':
        m = np.clip(polyline([(5, 3), (7.5, 8), (5, 13)], [0.7] * 3)[0] + polyline([(5, 3), (5, 13)], [0.3] * 2)[0]
                    + polyline([(5.4, 8), (12, 8)], [0.5] * 2)[0] + polygon([(12, 6.8), (13.6, 8), (12, 9.2)]), 0, 1)
    elif name == 'arms_up':
        m = np.clip(circle(8, 4, 1.4) + rect(7, 5.5, 9, 11) + polyline([(7.2, 6.5), (4.5, 3.5)], [0.9, 0.9])[0]
                    + polyline([(8.8, 6.5), (11.5, 3.5)], [0.9, 0.9])[0] + rect(6.4, 11, 7.4, 14) + rect(8.6, 11, 9.6, 14),
                    0, 1)
    elif name == 'blade':
        m = np.clip(polygon([(8, 2.5), (9.2, 4), (9.2, 10.5), (6.8, 10.5), (6.8, 4)]) + rect(5, 10.5, 11, 11.6)
                    + rect(7.4, 11.6, 8.6, 14), 0, 1)
    elif name == 'brewer':
        m = np.clip(circle(8, 10, 3.2) + rect(7, 3.5, 9, 7.5) + rect(6.2, 3, 9.8, 4), 0, 1) - circle(8, 10, 2.0) * 0.0
    elif name == 'burn':
        m = polygon([(8, 2.5), (11, 8), (10, 13), (6, 13), (5, 8), (7, 9.5)])
    elif name == 'danger':
        m = np.clip(circle(8, 7, 4) - circle(6.5, 6.5, 1.0) - circle(9.5, 6.5, 1.0) + rect(6, 10.5, 10, 13), 0, 1)
    elif name == 'explorer':
        m = np.clip(circle(8, 8, 5) - circle(8, 8, 4) + polygon([(8, 4), (9, 8), (8, 12), (7, 8)]), 0, 1)
    elif name == 'flow':
        r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
        a = np.arctan2(Y - 8, X - 8)
        m = ((np.abs(((r - a * 0.9) % 2.8) - 1.4) < 0.5) & (r < 6)).astype(F32)
    elif name == 'friend':
        m = np.clip(circle(8, 8, 5) - circle(8, 8, 4) + circle(6.3, 6.8, 0.7) + circle(9.7, 6.8, 0.7)
                    + (np.abs(np.sqrt((X - 8) ** 2 + (Y - 7.5) ** 2) - 2.8) < 0.45) * (Y > 8.6), 0, 1)
    elif name == 'guster':
        r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
        a = np.arctan2(Y - 8, X - 8)
        m = ((np.abs(((r + a * 1.2) % 3.0) - 1.5) < 0.45) & (r < 6) & (r > 1)).astype(F32)
    elif name in ('heart', 'heartbreak'):
        m = np.clip(circle(6.2, 6.5, 2.4) + circle(9.8, 6.5, 2.4) + polygon([(4.0, 7.5), (12.0, 7.5), (8, 13)]), 0, 1)
        if name == 'heartbreak':
            m = m * (np.abs((X - 8) - 0.6 * np.sign(np.sin(Y * 1.5))) > 0.5)
    elif name == 'howl':
        m = np.clip(polygon([(5, 13), (6, 6), (5, 3), (8, 5), (11, 3), (10, 6), (11, 13)]), 0, 1) - circle(7, 8, 0.6) - circle(9, 8, 0.6)
    elif name == 'miner':
        m = np.clip(polyline([(3.5, 6), (8, 3.5), (12.5, 6)], [1.0, 1.2, 1.0])[0] + rect(7.4, 4, 8.6, 13.5), 0, 1)
    elif name == 'mourner':
        m = np.clip(circle(8, 5.5, 2.4) + rect(6.4, 7.5, 9.6, 13.5) + circle(9.0, 10.5, 0.6) * 0, 0, 1)
        m = np.clip(m - circle(7.2, 5.2, 0.5) - circle(8.8, 5.2, 0.5), 0, 1)
    elif name == 'plenty':
        m = np.clip(polygon([(4, 7), (12, 7), (11, 13), (5, 13)]) + circle(6, 6, 1.2) + circle(8, 5.4, 1.3)
                    + circle(10, 6, 1.2), 0, 1)
    elif name == 'prize':
        m = polygon([(8, 3), (12.5, 7), (8, 13.5), (3.5, 7)])
        m = np.clip(m - polygon([(8, 5), (10.5, 7), (8, 10.5), (5.5, 7)]) * 0.0, 0, 1)
    elif name == 'scrape':
        m = np.clip(polygon([(5, 3), (11, 3.5), (11.5, 8), (8.5, 6.5)]) + rect(7.4, 5.5, 8.6, 13.5), 0, 1)
    elif name == 'sheaf':
        m = np.zeros((N, N), F32)
        for k in range(-2, 3):
            m = np.maximum(m, polyline([(8, 13), (8 + k * 1.4, 3.5)], [0.6, 0.6])[0])
        m = np.clip(m + rect(5.5, 8.5, 10.5, 9.5), 0, 1)
    elif name == 'shelter':
        m = np.clip(polygon([(8, 2.5), (12.5, 9), (3.5, 9)]) + rect(7.3, 9, 8.7, 13.5), 0, 1)
    elif name == 'skull':
        m = np.clip(circle(8, 7, 4) + rect(5.5, 9, 10.5, 12.5) - circle(6.5, 7, 1.1) - circle(9.5, 7, 1.1)
                    - rect(7.6, 9, 8.4, 10.5), 0, 1)
    elif name == 'snort':
        m = np.clip(ellipse(8, 8, 4.5, 3.4) - circle(6.5, 8, 0.9) - circle(9.5, 8, 0.9), 0, 1)
    return np.clip(m, 0, 1).astype(F32)


def pottery(name, seed=4800):
    path = f'{name}_pottery_pattern'
    alpha = mask_of(path).astype(F32)
    rgb = ramp(np.clip(0.5 + 0.2 * fbm(N, 6, seed, 3) + 0.05 * fbm(N, 30, seed + 1, 2), 0, 1), CLAY)
    m = blur(motif_shape(name), 0.6)
    rgb = mix(rgb, hexrgb('#3a1a12'), m * 0.85)
    h = 0.5 - 0.15 * m
    return tex(rgb, h, path, alpha=alpha)


def pot(part, seed=4801):
    path = 'decorated_pot_' + part
    alpha = mask_of(path).astype(F32)
    rgb = ramp(np.clip(0.5 + 0.2 * fbm(N, 6, seed, 3) + 0.05 * fbm(N, 30, seed + 1, 2), 0, 1), CLAY)
    if part == 'side':
        band = (np.abs(Y - 3.0) < 0.5) | (np.abs(Y - 13.0) < 0.5)
        rgb = np.where(band[..., None], hexrgb('#4a2016'), rgb)
    return tex(rgb, 0.5 + 0.05 * fbm(N, 10, seed, 2), path, alpha=alpha)


# ------------------------------------------------------------------ eggs, frames, chest icons
def egg(path, seed, base, spots, cracks=0):
    alpha = mask_of(path).astype(F32)
    rgb = ramp(np.clip(0.5 + 0.2 * fbm(N, 6, seed, 3), 0, 1), base)
    sp, sv = speckles(N, 10, seed + 1, 0.3, 0.35)
    rgb = mix(rgb, hexrgb(spots), blur(sp, 0.8) * 0.8)
    h = 0.6 + 0.1 * fbm(N, 6, seed, 3)
    if cracks:
        from engine.draw import fractures
        lines, _ = fractures(seed + 2, 2 * cracks, (2, 5), (0.12, 0.2), kinks=4, jag=1.4, plane=0.2)
        rgb = rgb * (1 - 0.6 * lines[..., None])
        h = h - 0.3 * lines
    return tex(rgb, h, path, alpha=alpha)


def frame_bg(path, seed=4820, glow=False):
    rgb = ramp(np.clip(0.5 + 0.2 * fbm(N, (4, 12), seed, 3) + 0.08 * fbm(N, 30, seed + 1, 2), 0, 1),
               [(0, '#4a2412'), (0.5, '#7a4428'), (1, '#a8683e')])
    stitch = (np.abs(np.minimum(np.minimum(X, 16 - X), np.minimum(Y, 16 - Y)) - 1.2) < 0.15) & (((X + Y) % 1.0) < 0.5)
    rgb = np.where(stitch[..., None], hexrgb('#d8b88a'), rgb)
    em = None
    if glow:
        ink = smoothstep(0.6, 0.85, fbm(N, 5, seed + 2, 3))
        rgb = mix(rgb, hexrgb('#4ad8c8'), ink * 0.4)
        em = (ink * 0.15)[..., None] * hexrgb('#6af0e0')
    return tex(rgb, 0.5 + 0.1 * fbm(N, 12, seed, 2), path, emissive=em)


def chest_icon(face, kind, seed=4830):
    path = {'chest': f'chest_{face}', 'trapped': 'trapped_chest_front', 'ender': f'ender_chest_{face}'}[kind]
    if kind == 'ender':
        from recipes.terrain import obsidian
        o = obsidian(seed)
        rgb, h = o.albedo, o.height
        trim = np.broadcast_to(hexrgb('#2a6a5a'), (N, N, 3))
    else:
        rgb, h = oak(seed)
        trim = iron(seed + 1, 0.4)[0]
    fr = frame(1.2)
    rgb, h = put(rgb, h, fr, trim if kind != 'ender' else rgb * 0.7 + 0.1, 0.9)
    if face in ('front', 'side'):
        lid = 1 - smoothstep(0.1, 0.3, np.abs(Y - 6.0))
        rgb = rgb * (1 - 0.5 * lid[..., None])
        if face == 'front':
            latch = rect(7.0, 4.6, 9.0, 8.4)
            col = hexrgb('#c8c8d0') if kind != 'ender' else hexrgb('#4af0c8')
            rgb, h = put(rgb, h, latch, col, 0.95)
            if kind == 'trapped':
                rgb, h = put(rgb, h, rect(7.6, 9.0, 8.4, 12.0), hexrgb('#c82a1a'), 0.8)
    return tex(rgb, h, path)


def comparator(kind, on, seed=4840):
    path = f'{kind}_{"on" if on else "off"}'
    t = polished(smooth_face(seed, [(0, '#8e8e8c'), (0.5, '#a3a3a1'), (1, '#b6b6b4')]), seed + 1)
    rgb, h = t.albedo, t.height
    col = hexrgb('#e22a1a') if on else hexrgb('#5a1a14')
    trace = rect(7.4, 2.0, 8.6, 14.0)
    if kind == 'comparator':
        trace = np.clip(trace + rect(3.0, 11.0, 13.0, 12.2), 0, 1)
    rgb, h = put(rgb, h, trace, col, 0.55)
    sockets = np.clip(circle(8, 3.5, 1.1) + circle(8, 12.5, 1.1) + (circle(4.0, 11.6, 1.0) + circle(12.0, 11.6, 1.0)
                                                                      if kind == 'comparator' else 0), 0, 1)
    rgb, h = put(rgb, h, sockets, hexrgb('#3a3a3a'), 0.4)
    em = (trace * 0.4)[..., None] * hexrgb('#ff3a2a') if on else None
    return tex(rgb, h, path, emissive=em)


def shelf(species_planks, path, seed):
    t = planks(seed, species_planks)
    return tex(t.albedo, t.height, path)


def shelf_mushroom(path, seed=4850):
    x, y = warped_coords(N, 0.05, seed, freq=3)
    bands = np.sin(2 * np.pi * (np.sqrt((X - 8) ** 2 + (Y - 16) ** 2) / 2.0 + 0.4 * fbm(N, 3, seed, 3)))
    t = 0.55 + 0.15 * bands + 0.08 * fbm(N, 20, seed + 1, 2)
    rgb = ramp(np.clip(t, 0, 1), [(0, '#7a3a14'), (0.5, '#c27a3a'), (1, '#ecc08a')])
    return tex(rgb, 0.5 + 0.2 * bands, path)


def dried_ghast(path, seed=4860):
    info = INVENTORY['textures/blocks/' + path]
    alpha = mask_of(path).astype(F32) if info['alpha'] != 'none' else None
    rgb = ramp(np.clip(0.5 + 0.2 * fbm(N, 6, seed, 3) + 0.1 * fbm(N, 24, seed + 1, 2), 0, 1),
               [(0, '#6a6466'), (0.5, '#a49e9e'), (1, '#d2cccc')])
    wrinkles = smoothstep(0.85, 0.97, ridged(N, 6, seed + 2, 3, sharp=2.0))
    rgb = rgb * (1 - 0.3 * wrinkles[..., None])
    return tex(rgb, 0.5 - 0.2 * wrinkles, path, alpha=alpha)


# ------------------------------------------------------------------ registration
def register(R):
    for om in (False, True):
        for face in ('front', 'side', 'top', 'bottom'):
            for state in ('off', 'on', 'ejecting', 'plain'):
                sfx = {'off': '_off', 'on': '_on', 'ejecting': '_ejecting', 'plain': ''}[state]
                o = '_ominous' if om else ''
                path = f'vault_{face}{sfx}{o}'
                if has(path):
                    R.block(path, lambda v, face=face, state=state, om=om: vault(face, state, om),
                            cutout=INVENTORY['textures/blocks/' + path]['alpha'] != 'none')
        for face in ('side', 'top', 'bottom'):
            for state in (None, 'active', 'inactive', 'open', 'ejecting_reward'):
                path = f'trial_spawner_{face}' + (f'_{state}' if state else '') + ('_ominous' if om else '')
                if has(path):
                    R.block(path, lambda v, face=face, state=state, om=om: spawner(face, state, om),
                            cutout=INVENTORY['textures/blocks/' + path]['alpha'] != 'none')
    for face in ('north', 'south', 'east', 'west', 'top', 'bottom'):
        for state in (None, 'crafting', 'triggered'):
            path = f'crafter_{face}' + (f'_{state}' if state else '')
            if has(path):
                R.block(path, lambda v, face=face, state=state: crafter(face, state))
    for face in ('side', 'top'):
        for state in ('active', 'dormant', 'inactive'):
            R.block(f'creaking_heart_{face}_{state}', lambda v, face=face, state=state: creaking_heart(face, state))

    R.anim('sculk', lambda f, n: sculk_block(f, n), 4)
    R.anim('sculk_vein', lambda f, n: sculk_vein(f, n), 4, cutout=True)
    for p in ('sculk_catalyst_side', 'sculk_catalyst_top', 'sculk_catalyst_bottom', 'sculk_sensor_side',
              'sculk_sensor_top', 'sculk_sensor_bottom', 'sculk_shrieker_side', 'sculk_shrieker_top',
              'sculk_shrieker_bottom', 'calibrated_sculk_sensor_amethyst', 'calibrated_sculk_sensor_input_side',
              'calibrated_sculk_sensor_top'):
        R.block(p, lambda v, p=p: sculk_part(p, 4610), cutout=INVENTORY['textures/blocks/' + p]['alpha'] != 'none')
    R.anim('sculk_catalyst_side_bloom', lambda f, n: sculk_part('sculk_catalyst_side_bloom', 4610, f, n, bloom=True), 8)
    R.anim('sculk_catalyst_top_bloom', lambda f, n: sculk_part('sculk_catalyst_top_bloom', 4610, f, n, bloom=True), 8)
    R.anim('sculk_shrieker_inner_top', lambda f, n: sculk_part('sculk_shrieker_inner_top', 4611, f, n), 10)
    R.anim('sculk_shrieker_can_summon_inner_top',
           lambda f, n: sculk_part('sculk_shrieker_can_summon_inner_top', 4611, f, n), 10)
    for p in ('sculk_sensor_tendril_active', 'sculk_sensor_tendril_inactive'):
        R.anim(p, lambda f, n, p=p: sculk_part(p, 4612, f, n, tendril=True), 16, cutout=True)

    for p in ('cauldron_top', 'cauldron_side', 'cauldron_inner', 'cauldron_bottom', 'hopper_outside', 'hopper_inside',
              'hopper_top'):
        R.block(p, lambda v, p=p: metal_part(p, 4690), cutout=INVENTORY['textures/blocks/' + p]['alpha'] != 'none')
    R.block('anvil_base', lambda v: anvil('anvil_base'))
    for d in range(3):
        R.block(f'anvil_top_damaged_{d}', lambda v, d=d: anvil(f'anvil_top_damaged_{d}', damage=d), cutout=True)
    for p in ('grindstone_pivot', 'grindstone_round', 'grindstone_side'):
        R.block(p, lambda v, p=p: grindstone(p), cutout=True)
    R.block('mob_spawner', lambda v: mob_spawner(), cutout=True)
    R.block('heavy_core', lambda v: anvil('heavy_core'), cutout=True)
    for part in ('top', 'side', 'inner', 'bottom'):
        R.block(f'cake_{part}', lambda v, part=part: cake(part), cutout=True)
    for part in ('top', 'side', 'bottom'):
        R.block(f'bell_{part}', lambda v, part=part: bell(part), cutout=True)
    R.block('brewing_stand', lambda v: brewing('stand'), cutout=True)
    R.block('brewing_stand_base', lambda v: brewing('base'))
    R.block('campfire_log', lambda v: campfire_log(), cutout=True)
    R.anim('campfire_log_lit', lambda f, n: campfire_log(True, f, n), 4)
    R.anim('soul_campfire_log_lit', lambda f, n: campfire_log(True, f, n, soul=True), 4)
    R.anim('campfire', lambda f, n: campfire_flames(f, n), 8, cutout=True)
    R.anim('soul_campfire', lambda f, n: campfire_flames(f, n, soul=True), 8, cutout=True)

    for name in ('angler', 'archer', 'arms_up', 'blade', 'brewer', 'burn', 'danger', 'explorer', 'flow', 'friend',
                 'guster', 'heart', 'heartbreak', 'howl', 'miner', 'mourner', 'plenty', 'prize', 'scrape', 'sheaf',
                 'shelter', 'skull', 'snort'):
        if has(f'{name}_pottery_pattern'):
            R.block(f'{name}_pottery_pattern', lambda v, name=name: pottery(name), cutout=True)
    R.block('decorated_pot_side', lambda v: pot('side'), cutout=True)
    R.block('decorated_pot_base', lambda v: pot('base'), cutout=True, scale=2)

    for stage, cr in (('not_cracked', 0), ('slightly_cracked', 1), ('very_cracked', 2)):
        for face in ('north', 'south', 'east', 'west', 'top', 'bottom'):
            p = f'sniffer_egg_{stage}_{face}'
            if has(p):
                R.block(p, lambda v, p=p, cr=cr: egg(p, 4870, [(0, '#5a3a1a'), (0.5, '#8a5a2a'), (1, '#a87a3a')],
                                                      '#3a6a2a', cr), cutout=True)
        p = f'turtle_egg_{stage}'
        R.block(p, lambda v, p=p, cr=cr: egg(p, 4871, [(0, '#c8c2a2'), (0.5, '#e8e2c8'), (1, '#f8f4e8')], '#7a9a5a',
                                              cr), cutout=True)
    for st in range(1, 5):
        for part in ('back', 'bottom', 'front', 'left', 'right', 'top', 'tentacles'):
            p = f'dried_ghast_state_{st}_{part}'
            if has(p):
                info = INVENTORY['textures/blocks/' + p]
                R.block(p, lambda v, p=p: dried_ghast(p), cutout=info['alpha'] != 'none',
                        scale=info['w'] // 16)
    R.block('itemframe_background', lambda v: frame_bg('itemframe_background'))
    R.block('glow_item_frame', lambda v: frame_bg('glow_item_frame', 4821, glow=True))
    for face in ('front', 'side', 'top'):
        R.block(f'chest_{face}', lambda v, face=face: chest_icon(face, 'chest'))
        R.block(f'ender_chest_{face}', lambda v, face=face: chest_icon(face, 'ender'))
    R.block('trapped_chest_front', lambda v: chest_icon('front', 'trapped'))
    for kind in ('repeater', 'comparator'):
        for on in (False, True):
            R.block(f'{kind}_{"on" if on else "off"}', lambda v, kind=kind, on=on: comparator(kind, on))
    shelves = {'acacia_shelf': 'planks_acacia', 'bamboo_shelf': 'bamboo_planks', 'birch_shelf': 'planks_birch',
               'cherry_shelf': 'cherry_planks', 'crimson_shelf': 'huge_fungus/crimson_planks',
               'dark_oak_shelf': 'planks_big_oak', 'jungle_shelf': 'planks_jungle', 'mangrove_shelf': 'mangrove_planks',
               'oak_shelf': 'planks_oak', 'pale_oak_shelf': 'pale_oak_planks', 'poplar_shelf': 'poplar_planks',
               'spruce_shelf': 'planks_spruce', 'warped_shelf': 'huge_fungus/warped_planks'}
    for i, (p, pl) in enumerate(shelves.items()):
        if has(p):
            R.block(p, lambda v, p=p, pl=pl, i=i: shelf(pl, p, 4880 + i), scale=2)
    R.block('shelf_mushroom_large', lambda v: shelf_mushroom('shelf_mushroom_large'), scale=2)
    R.block('shelf_mushroom_small', lambda v: shelf_mushroom('shelf_mushroom_small', 4851), scale=2)
