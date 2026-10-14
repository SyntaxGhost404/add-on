"""Environment: sun, moon phases, clouds, rain and snow sprites, block-breaking cracks, the End sky,
enchantment glint, vegetation colour maps, falling-leaf and smoke particles, and per-biome atmosphere
(distance fog, rain haze, underwater visibility, sky and water colour) for the standard renderer.

Fog and client-biome JSON start from each vanilla definition and change only the visual values listed
here; every other component (sounds, music, and the Vibrant Visuals volumetric/lighting identifiers) is
kept as it was."""
import copy
import json
import os

import numpy as np

from engine.noise import F32, fbm, ridged, worley, cell_random, blur, smoothstep, rng
from engine.color import ramp, hexrgb
from engine.material import Tex, MASTER

N = MASTER
DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
FOGS = json.load(open(os.path.join(DATA, 'vanilla_fogs.json')))
BIOMES = json.load(open(os.path.join(DATA, 'vanilla_client_biomes.json')))
MASKS = json.load(open(os.path.join(DATA, 'vanilla_masks.json')))


def grid_xy(w, h):
    yy, xx = np.mgrid[0:h, 0:w].astype(F32)
    return (xx + 0.5) / w, (yy + 0.5) / h


# ------------------------------------------------------------------ sun and moon (additive: black is clear)
def sun(size=128):
    x, y = grid_xy(size, size)
    r = np.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2)
    core = 1 - smoothstep(0.155, 0.17, r)
    limb = np.clip(1 - (r / 0.17) ** 2, 0, 1) ** 0.35
    halo = np.exp(-((r - 0.12) / 0.11) ** 2 * 1.0) * (r > 0.12) * 0.55 + np.exp(-r / 0.09) * 0.25
    corona = halo * (1 - core)
    rgb = core[..., None] * (hexrgb('#fff8e2') * (0.82 + 0.18 * limb[..., None]))
    rgb = rgb + corona[..., None] * hexrgb('#ffd88a')
    edge = np.minimum(np.minimum(x, 1 - x), np.minimum(y, 1 - y))
    rgb = rgb * smoothstep(0.0, 0.08, edge)[..., None]
    return np.dstack([np.clip(rgb, 0, 1), np.ones((size, size), F32)]).astype(F32)


def moon_phases(cell=128):
    w, h = cell * 4, cell * 2
    out = np.zeros((h, w, 4), F32)
    out[..., 3] = 1
    lx, ly = grid_xy(cell, cell)
    dx, dy = (lx - 0.5) / 0.2, (ly - 0.5) / 0.2
    rr = np.sqrt(dx * dx + dy * dy)
    disc = 1 - smoothstep(0.96, 1.02, rr)
    z = np.sqrt(np.clip(1 - rr * rr, 0, 1))
    # surface: maria (dark seas) and craters, made once and shared by all phases
    maria = smoothstep(0.05, 0.35, fbm(cell, 2, 777, 4) + 0.15)
    f1, f2, cid = worley(cell, 9, 778, 1.0)
    craters = np.exp(-((f1 - 0.28) / 0.06) ** 2) * (cell_random(cid, 779) < 0.35)
    albedo = 0.82 - 0.28 * maria + 0.12 * craters + 0.05 * fbm(cell, 20, 780, 2)
    # phases in vanilla order: full, waning gibbous, last quarter, waning crescent, new, waxing crescent, first
    # quarter, waxing gibbous; light direction rotates around the moon
    for k in range(8):
        ang = np.pi * k / 4
        lxv, lzv = -np.sin(ang), np.cos(ang)
        lit = np.clip(dx * lxv + z * lzv, 0, 1) if k else np.clip(z, 0, 1) ** 0.25
        shade = smoothstep(0.0, 0.18, lit)
        earth = 0.035
        v = disc * albedo * (earth + (1 - earth) * shade) * (0.85 + 0.15 * z)
        glow = np.exp(-np.maximum(rr - 1.0, 0) / 0.25) * (rr > 1.0) * 0.06 * (1 - k / 8 if k <= 4 else k / 8)
        col = v[..., None] * hexrgb('#f2f0ea') + glow[..., None] * hexrgb('#9ab0d8')
        cx, cy = (k % 4) * cell, (k // 4) * cell
        out[cy:cy + cell, cx:cx + cell, :3] = np.clip(col, 0, 1)
    return out


# ------------------------------------------------------------------ clouds (binary mask: each texel is a cloud cell)
def clouds(size=256, cover=0.28, seed=5000):
    x, y = grid_xy(size, size)
    wx = x + 0.04 * fbm(size, 3, seed, 3)
    wy = y + 0.04 * fbm(size, 3, seed + 1, 3)
    field = fbm(size, 6, seed + 2, 5, x=wx, y=wy) + 0.45 * fbm(size, 2, seed + 3, 3)
    t = np.quantile(field, 1 - cover)
    a = (field >= t).astype(F32)
    return np.dstack([np.ones((size, size, 3), F32), a]).astype(F32)


# ------------------------------------------------------------------ rain and snow sprites (inside vanilla UV cells)
def weather(scale=4):
    m = MASKS['textures/environment/weather']
    a16 = np.array([[c == '1' for c in row] for row in m['rows']], bool)
    h0, w0 = a16.shape
    up = np.kron(a16, np.ones((scale, scale), bool))
    H, W = up.shape
    yy, xx = np.mgrid[0:H, 0:W].astype(F32)
    # label each vertical run in the mask and give it a head-bright, tail-fading streak (rain) or a soft flake
    rgb = np.ones((H, W, 3), F32) * hexrgb('#e8eef8')
    alpha = np.zeros((H, W), F32)
    for c in range(w0):
        col = a16[:, c]
        r = 0
        while r < h0:
            if col[r]:
                s = r
                while r < h0 and col[r]:
                    r += 1
                e = r
                y0, y1 = s * scale, e * scale
                x0, x1 = c * scale, (c + 1) * scale
                L = e - s
                t = (yy[y0:y1, x0:x1] - y0) / max(y1 - y0, 1)
                if L >= 4:
                    alpha[y0:y1, x0:x1] = np.maximum(alpha[y0:y1, x0:x1], 0.12 + 0.45 * (1 - t) ** 1.5)
                else:
                    cx = (xx[y0:y1, x0:x1] - (x0 + x1) / 2) / scale
                    cy = (yy[y0:y1, x0:x1] - (y0 + y1) / 2) / scale
                    alpha[y0:y1, x0:x1] = np.maximum(alpha[y0:y1, x0:x1], np.clip(0.95 - (cx * cx + cy * cy) * 0.9, 0, 1))
            else:
                r += 1
    return np.dstack([rgb, alpha]).astype(F32)


# ------------------------------------------------------------------ block breaking cracks (multiplied over the block)
def destroy(stage, seed=5100):
    from engine.draw import polyline
    r = rng(seed)
    lines = np.zeros((N, N), F32)
    edge = np.zeros((N, N), F32)
    n = 2 + stage * 2
    for k in range(n):
        a = r.uniform(0, 2 * np.pi)
        L = 2.5 + stage * 0.75 + r.uniform(0, 1.5)
        pts = [(8.0 + r.uniform(-0.6, 0.6), 8.0 + r.uniform(-0.6, 0.6))]
        for j in range(5):
            a += r.uniform(-0.6, 0.6)
            x, y = pts[-1]
            pts.append((x + np.cos(a) * L / 5, y + np.sin(a) * L / 5))
        w = 0.32 - 0.02 * k / max(n, 1)
        m, _ = polyline(pts, np.linspace(w, 0.08, len(pts)))
        lines = np.maximum(lines, m)
        if stage >= 4 and k % 2 == 0:
            bx, by = pts[r.integers(2, 5)]
            b = a + r.choice([-1, 1]) * r.uniform(0.7, 1.2)
            bpts = [(bx, by), (bx + np.cos(b) * L * 0.35, by + np.sin(b) * L * 0.35)]
            m2, _ = polyline(bpts, [0.18, 0.06])
            lines = np.maximum(lines, m2)
    edge = np.clip(blur(lines, 1.6) * 2.2 - lines, 0, 1)
    grey = 1.0 - 0.76 * lines - 0.4 * edge
    alpha = np.clip(lines + edge * 0.9, 1 / 255, 1)
    rgb = np.repeat(np.clip(grey, 0, 1)[..., None], 3, axis=-1)
    rgb = np.where((alpha <= 1 / 255 + 1e-6)[..., None], 1.0, rgb)
    return Tex(rgb.astype(F32), None, alpha.astype(F32), light='none', sharpen=0.0)


def end_sky(size=256, seed=5200):
    x, y = grid_xy(size, size)
    neb = fbm(size, 3, seed, 5)
    wisps = ridged(size, 5, seed + 1, 4, sharp=2.5)
    stars = (fbm(size, 90, seed + 2, 1) > 0.62).astype(F32) * 0.5
    v = 0.36 + 0.18 * neb + 0.14 * wisps + stars
    rgb = np.repeat(np.clip(v, 0, 1)[..., None], 3, axis=-1)
    return np.dstack([rgb, np.ones((size, size), F32)]).astype(F32)


def glint(size=256, seed=5300):
    x, y = grid_xy(size, size)
    d = (x + y) % 1.0
    bands = np.exp(-((d - 0.3) / 0.08) ** 2) + 0.6 * np.exp(-((d - 0.72) / 0.05) ** 2)
    sparkle = (fbm(size, 40, seed, 1) > 0.55).astype(F32) * 0.4
    v = np.clip(0.25 + 0.6 * bands + 0.2 * fbm(size, 6, seed + 1, 3) + sparkle * bands, 0, 1)
    rgb = np.repeat(v[..., None], 3, axis=-1)
    return np.dstack([rgb, np.ones((size, size), F32)]).astype(F32)


# ------------------------------------------------------------------ colour maps (temperature x downfall)
def colormap(corners, size=256):
    """corners: colours at (hot & wet), (hot & dry), (cold). Barycentric blend over the valid triangle,
    with gentle noise so neighbouring biomes don't band."""
    yy, xx = np.mgrid[0:size, 0:size].astype(F32)
    temp = 1 - xx / (size - 1)
    wet = 1 - yy / (size - 1)
    rain = np.clip(wet / np.maximum(temp, 1e-3), 0, 1)
    hw, hd, cold = (hexrgb(c) for c in corners)
    hot = hw * rain[..., None] + hd * (1 - rain[..., None])
    rgb = hot * temp[..., None] + cold * (1 - temp[..., None])
    rgb = rgb * (1 + 0.025 * fbm(size, 4, 5400, 3))[..., None]
    return np.dstack([np.clip(rgb, 0, 1), np.ones((size, size), F32)]).astype(F32)


def flat_colormap(c1, c2, size=256):
    yy, xx = np.mgrid[0:size, 0:size].astype(F32)
    t = (xx + yy) / (2 * (size - 1))
    rgb = hexrgb(c1) * (1 - t[..., None]) + hexrgb(c2) * t[..., None]
    rgb = rgb * (1 + 0.02 * fbm(size, 4, 5401, 3))[..., None]
    return np.dstack([np.clip(rgb, 0, 1), np.ones((size, size), F32)]).astype(F32)


# ------------------------------------------------------------------ particles
def leaf_atlas(cols, rows, cell, scale=4, grey=True, colours=None, seed=5500, kind='lobed', petal=False):
    from recipes.foliage import Canvas, draw_leaf
    W, H = cols * cell * scale, rows * cell * scale
    out = np.zeros((H, W, 4), F32)
    r = rng(seed)
    for j in range(rows):
        for i in range(cols):
            S = cell * scale
            cv = Canvas(wrap=False)
            ang = r.uniform(0, 2 * np.pi)
            L = 12.5 if not petal else 11.0
            col = None if grey else ramp(np.array([r.uniform(0, 1)]), colours)[0]
            draw_leaf(cv, 8 - 5.5 * np.cos(ang), 8 - 5.5 * np.sin(ang), ang, L, 8.0 if not petal else 9.0, 0.5,
                      r.uniform(0.75, 1.0), kind='round' if petal else kind, colour=col)
            from PIL import Image
            prem = np.dstack([cv.rgb * cv.a[..., None], cv.a])
            chans = [np.asarray(Image.fromarray(prem[..., c].astype(np.float32), 'F').resize((S, S), Image.BOX))
                     for c in range(4)]
            small = np.dstack(chans).astype(F32)
            a = (small[..., 3] >= 0.5).astype(F32)
            rgb = small[..., :3] / np.maximum(small[..., 3:4], 1e-3)
            if grey:
                l = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
                rgb = np.repeat(l[..., None], 3, axis=-1)
            out[j * S:(j + 1) * S, i * S:(i + 1) * S, :3] = np.clip(rgb, 0, 1)
            out[j * S:(j + 1) * S, i * S:(i + 1) * S, 3] = a
    return out


def campfire_smoke(frames=12, scale=4, seed=5600):
    S = 16 * scale
    out = np.zeros((S * frames, S, 4), F32)
    x, y = grid_xy(S, S)
    for f in range(frames):
        t = f / (frames - 1)
        puff = fbm(S, 4, seed + f, 4) * 0.35
        r = np.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2) + puff * (0.2 + 0.5 * t)
        rad = 0.18 + 0.22 * t
        density = 1 - smoothstep(rad * 0.7, rad, r)
        thin = smoothstep(0.5, 1.0, t)
        dither = fbm(S, 24, seed + 50 + f, 2) * 0.5 + 0.5
        a = (density * (1 - 0.7 * thin) > dither * 0.6 + 0.2).astype(F32)
        v = 0.62 + 0.25 * (1 - r / max(rad, 1e-3)) - 0.15 * t
        out[f * S:(f + 1) * S, :, :3] = np.clip(v, 0, 1)[..., None] * hexrgb('#e8e4e0')
        out[f * S:(f + 1) * S, :, 3] = a
    return out


# ------------------------------------------------------------------ atmosphere (fog + client biomes)
def climate(name):
    n = name.replace('_fog_setting.json', '').replace('.client_biome.json', '')
    if n in ('hell', 'crimson_forest', 'warped_forest', 'soulsand_valley', 'basalt_deltas', 'the_end'):
        return 'keep'
    if n in ('pale_garden',):
        return 'pale'
    if n.startswith(('desert', 'mesa', 'savanna')) or n in ('dry',):
        return 'arid'
    if n.startswith(('jungle', 'bamboo_jungle')) or n in ('humid', 'lush_caves', 'semi_humid'):
        return 'humid'
    if n.startswith(('swampland', 'mangrove')):
        return 'swamp'
    if n.startswith('powder'):
        return 'keep'
    if n.startswith(('ice', 'frozen', 'cold', 'deep_frozen')) or n in ('grove', 'snowy_slopes', 'jagged_peaks',
                                                                                 'frozen_peaks'):
        return 'snowy'
    if n.startswith(('taiga', 'mega', 'redwood')):
        return 'boreal'
    if n.startswith(('warm_ocean', 'lukewarm', 'deep_warm', 'deep_lukewarm')):
        return 'tropical_sea'
    if n.startswith(('ocean', 'deep_ocean', 'deep_cold')):
        return 'sea'
    if n.startswith(('extreme_hills', 'stone_beach', 'stony_peaks', 'meadow')):
        return 'alpine'
    if n.startswith('roofed_forest'):
        return 'dark_forest'
    if n.startswith('cherry'):
        return 'blossom'
    if n.startswith('mushroom'):
        return 'mushroom'
    if n.startswith(('forest', 'birch', 'flower', 'dappled')):
        return 'forest'
    if n.startswith('sulfur'):
        return 'keep'
    return 'temperate'


ATMOS = {
    # climate: (air fog colour, start fraction, rain-haze colour, sky colour, water colour, water opacity,
    #           underwater fog colour, underwater visibility in blocks)
    'temperate': ('#c3d5e6', 0.62, '#77818a', '#79a6ea', '#3a7fbe', 0.62, '#2a6fa8', 52.0),
    'forest': ('#b6cad6', 0.6, '#6e7a7e', '#76a2e6', '#3a7aa8', 0.65, '#2a6690', 48.0),
    'dark_forest': ('#8e9e96', 0.5, '#5a6460', '#6f98d6', '#3a6a7a', 0.7, '#24505a', 40.0),
    'arid': ('#dccdae', 0.58, '#9c8e74', '#8cb6e8', '#32a3a0', 0.6, '#2a8a88', 50.0),
    'humid': ('#a8c2a8', 0.5, '#66766a', '#6e9fe0', '#2e9a8a', 0.66, '#1f7a70', 42.0),
    'swamp': ('#8e9a86', 0.45, '#5e665a', '#7e9ab8', '#4f5f3a', 0.85, '#2c3420', 18.0),
    'snowy': ('#d6e2ee', 0.56, '#aeb8c4', '#8fb6ee', '#2f5e9e', 0.75, '#1e4a7e', 46.0),
    'boreal': ('#b8c8d2', 0.58, '#727e86', '#7aa8e8', '#2f6aa0', 0.7, '#1f5682', 46.0),
    'sea': ('#b4cce6', 0.6, '#727e8a', '#7aa6ea', '#2e6fb0', 0.72, '#1a5a96', 56.0),
    'tropical_sea': ('#bcd8e6', 0.62, '#7a8a92', '#79aaee', '#30b6c6', 0.5, '#26a6b8', 72.0),
    'alpine': ('#c2d2e2', 0.6, '#7c858e', '#7ba8ee', '#3a78b0', 0.66, '#2a669a', 50.0),
    'blossom': ('#e2ccd8', 0.6, '#8a7e86', '#86aef0', '#4a8ac8', 0.6, '#3a76b0', 52.0),
    'mushroom': ('#c0b4c8', 0.55, '#7a7480', '#8aa6e0', '#6a6aa8', 0.7, '#4a4a8a', 40.0),
    'pale': (None, None, None, None, None, None, None, None),
}


def fog_json(name, src):
    data = copy.deepcopy(src)
    fs = data['minecraft:fog_settings']
    dist = fs.setdefault('distance', {})
    c = climate(name)
    if name == 'default_fog_setting.json':
        c = 'temperate'
    if c == 'keep':
        return data
    if c == 'pale':
        if 'air' in dist:
            dist['air'].update({'fog_start': 0.45, 'fog_end': 1.0})
        return data
    air, start, rain, sky, wcol, wop, uwcol, uwvis = ATMOS[c]
    dist['air'] = {'fog_color': air, 'fog_start': start, 'fog_end': 1.0, 'render_distance_type': 'render'}
    dist['weather'] = {'fog_color': rain, 'fog_start': 0.18, 'fog_end': 0.62, 'render_distance_type': 'render'}
    if 'water' in dist or name == 'default_fog_setting.json':
        w = dist.get('water', {})
        w.update({'fog_color': uwcol, 'fog_start': 0.0, 'fog_end': uwvis, 'render_distance_type': 'fixed'})
        if 'transition_fog' in w:
            w['transition_fog']['init_fog']['fog_color'] = uwcol
        dist['water'] = w
    return data


def biome_json(name, src):
    data = copy.deepcopy(src)
    comps = data['minecraft:client_biome']['components']
    c = climate(name)
    if c in ('keep', 'pale'):
        return data
    air, start, rain, sky, wcol, wop, uwcol, uwvis = ATMOS[c]
    comps['minecraft:sky_color'] = {'sky_color': sky}
    wa = comps.setdefault('minecraft:water_appearance', {})
    wa['surface_color'] = wcol
    wa['surface_opacity'] = wop
    return data


# ------------------------------------------------------------------ registration
def register(R):
    R.fixed('textures/environment/sun', lambda: sun(128), (128, 128), opaque=True)
    R.fixed('textures/environment/moon_phases', lambda: moon_phases(128), (512, 256), opaque=True)
    R.fixed('textures/environment/clouds', lambda: clouds(256), (256, 256))
    R.fixed('textures/environment/weather', lambda: weather(4), (128, 128))
    R.fixed('textures/environment/end_sky', lambda: end_sky(256), (256, 256), opaque=True)
    R.fixed('textures/misc/enchanted_item_glint', lambda: glint(256), (256, 256), opaque=True)
    R.fixed('textures/misc/enchanted_actor_glint', lambda: glint(256, 5301), (256, 256), opaque=True)
    for k in range(10):
        R.block(f'textures/environment/destroy_stage_{k}', lambda v, k=k: destroy(k))

    R.fixed('textures/colormap/grass', lambda: colormap(('#4f9a2e', '#b4a85a', '#74a088')), (256, 256), opaque=True)
    R.fixed('textures/colormap/foliage', lambda: colormap(('#3a8a1e', '#9a8e3a', '#5a8a6a')), (256, 256), opaque=True)
    R.fixed('textures/colormap/birch', lambda: flat_colormap('#86a85a', '#7a9e52'), (256, 256), opaque=True)
    R.fixed('textures/colormap/evergreen', lambda: flat_colormap('#5e7e5c', '#56765a'), (256, 256), opaque=True)
    R.fixed('textures/colormap/swamp_grass', lambda: flat_colormap('#6a7a3a', '#5a6a34'), (256, 256), opaque=True)
    R.fixed('textures/colormap/swamp_foliage', lambda: flat_colormap('#5e6e2e', '#52602a'), (256, 256), opaque=True)
    R.fixed('textures/colormap/mangrove_swamp_foliage', lambda: flat_colormap('#7e9a36', '#6e8a30'), (256, 256),
            opaque=True)
    R.fixed('textures/colormap/dry_foliage', lambda: colormap(('#8a6a3a', '#b08a52', '#7a6a52')), (256, 256),
            opaque=True)

    R.fixed('textures/particle/biome_tinted_leaves_atlas', lambda: leaf_atlas(4, 3, 7), (112, 84))
    R.fixed('textures/particle/pale_oak_leaves_atlas', lambda: leaf_atlas(4, 3, 7, seed=5501), (112, 84))
    R.fixed('textures/particle/cherry_petal_atlas',
            lambda: leaf_atlas(4, 3, 3, scale=8, grey=False, colours=[(0, '#e392b5'), (1, '#fcd6e2')], petal=True,
                               seed=5502), (96, 72))
    for j, (name, cols) in enumerate((('yellow', [(0, '#c98a1c'), (1, '#f2cc4a')]),
                                      ('orange', [(0, '#b04a12'), (1, '#e88a30')]),
                                      ('red', [(0, '#7f1712'), (1, '#c4432c')]))):
        R.fixed(f'textures/particle/{name}_poplar_leaves_atlas',
                lambda cols=cols, j=j: leaf_atlas(4, 1, 7, grey=False, colours=cols, kind='deltoid', seed=5510 + j),
                (112, 28))
    R.fixed('textures/particle/campfire_smoke', lambda: campfire_smoke(12, 4), (64, 768))

    for name, src in sorted(FOGS.items()):
        R.json(f'fogs/{name}', fog_json(name, src))
    for name, src in sorted(BIOMES.items()):
        R.json(f'biomes/{name}', biome_json(name, src))
