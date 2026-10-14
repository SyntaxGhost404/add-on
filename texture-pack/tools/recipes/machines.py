"""Functional blocks: workstations, furnaces, storage, redstone machines, rails, lights and small parts.

Faces are composed from shared materials (planks, stone, iron, deepslate) plus drawn features: frames,
openings, grilles, inlays and glowing elements. Model-mapped parts (torches, lanterns, levers, chains…)
are painted inside the vanilla UV-island silhouettes so they fit the block models."""
import numpy as np

from engine.noise import F32, fbm, ridged, worley, cell_random, blur, warped_coords, norm01, smoothstep, rng
from engine.color import ramp, mix, match_mean, hexrgb
from engine.material import Tex, MASTER
from engine.draw import X, Y, rect, circle, ellipse, polygon, polyline, capsules, scatter
from recipes.terrain import stone, cobblestone, speckles
from recipes.stones import masonry, polished, smooth_face, frame_mask, deepslate, blackstone
from recipes.wood import planks, wood_face
from recipes.plants import mask_of
from registry import CALIBRATION

N = MASTER


def cal(path):
    c = CALIBRATION['textures/blocks/' + path]
    return np.array(c['mean'], F32), float(c['lum'])


def tex(rgb, h, path, *, alpha=None, light='top', bump=1.2, ao=0.55, gloss=0.0, emissive=None, cutout=False,
        target=None, recolour=0.0):
    mean, lum = cal(path)
    m = None if alpha is None else alpha > 0.5
    if recolour:
        cur = rgb[m].mean(0) if m is not None and m.any() else rgb.reshape(-1, 3).mean(0)
        rgb = np.clip(rgb * (1 - recolour) + rgb * (np.asarray(mean) / np.maximum(cur, 1e-3)) * recolour, 0, 1)
    rgb = match_mean(rgb, target if target is not None else lum, m)
    return Tex(rgb.astype(F32), None if h is None else norm01(h), alpha, light=light, bump=bump, ao=ao, gloss=gloss,
               emissive=emissive, cutout=cutout or alpha is not None, sharpen=0.35)


# ------------------------------------------------------------------ shared materials
def oak(seed, path='planks_oak'):
    t = planks(seed, path)
    return t.albedo, t.height


def board(seed, path='planks_oak', vertical=False):
    t, h, stops, lum = wood_face(seed, path, vertical)
    return ramp(np.clip(t, 0, 1), stops), h


def stonework(seed, kind='cobble'):
    if kind == 'cobble':
        t = cobblestone(seed)
    elif kind == 'smooth':
        t = polished(smooth_face(seed, [(0, '#7a7a78'), (0.5, '#9a9a98'), (1, '#b4b4b2')]), seed + 1)
    elif kind == 'bricks':
        t = masonry(seed, [4, 4, 4, 4], 8, 4, stone(seed), mortar=0.5, mortar_col=('#4a4741', '#5e5a53'))
    elif kind == 'deepslate':
        t = masonry(seed, [4, 4, 4, 4], 8, 4, deepslate(seed, 'top', 0.3), mortar=0.45,
                    mortar_col=('#151518', '#24242a'))
    else:
        t = stone(seed)
    return t.albedo, t.height


def iron(seed, tone=0.6, streak='x'):
    s = fbm(N, (2, 40) if streak == 'x' else (40, 2), seed, 3)
    m = fbm(N, 4, seed + 1, 3)
    t = np.clip(tone + 0.05 * s + 0.07 * m, 0, 1)
    rgb = ramp(t, [(0, '#3a3a3e'), (0.5, '#8a8a90'), (1, '#d6d6da')])
    return rgb, 0.6 + 0.02 * s


def dark_iron(seed):
    rgb, h = iron(seed, 0.3)
    return rgb, h


def frame(width=1.2, inset=0.0):
    return frame_mask(inset, width)


def bevel(x0, y0, x1, y1, w=0.5):
    d = np.minimum(np.minimum(X - x0, x1 - X), np.minimum(Y - y0, y1 - Y))
    return np.clip(d / w, 0, 1) * (d > 0)


def recess(x0, y0, x1, y1, depth=0.5, w=0.35):
    """Height offset and shadow mask for a recessed rectangular opening."""
    inside = rect(x0, y0, x1, y1)
    lip = np.clip((np.minimum(np.minimum(X - x0, x1 - X), np.minimum(Y - y0, y1 - Y))) / w, 0, 1) * inside
    return inside, -depth * inside, inside * (1 - 0.6 * lip)


def put(rgb, h, mask, col, hval=None, mode='set'):
    m = np.clip(mask, 0, 1)
    col = np.asarray(col, F32)
    rgb = rgb * (1 - m[..., None]) + (col if col.ndim == 3 else col[None, None, :]) * m[..., None]
    if hval is not None:
        hv = hval if np.ndim(hval) else np.full((N, N), hval, F32)
        h = h * (1 - m) + hv * m if mode == 'set' else h + hv * m
    return rgb.astype(F32), h.astype(F32)


def glow_fire(seed, x0, y0, x1, y1, soul=False, phase=0.0):
    from recipes.liquids import drift
    t = phase
    f = drift(seed, t, (5, 4), 3, 0.0, -1.0)
    xx = (X - x0) / (x1 - x0)
    yy = (Y - y0) / (y1 - y0)
    flame = np.clip((yy * 1.2 - 0.15) * (1 - np.abs(xx - 0.5) * 1.4) + 0.4 * f, 0, 1)
    stops = [(0, '#3a0a02'), (0.4, '#c23a0a'), (0.7, '#f2961a'), (1, '#fff2b0')] if not soul else \
        [(0, '#04222a'), (0.4, '#1a8a9a'), (0.7, '#4ad6e0'), (1, '#e8ffff')]
    return ramp(flame, stops), flame


# ------------------------------------------------------------------ workstations (wood)
def crafting_table(face, seed=4000):
    path = 'crafting_table_' + face
    rgb, h = oak(seed, 'planks_oak')
    if face == 'top':
        top = rect(1.4, 1.4, 14.6, 14.6)
        work, wh = board(seed + 1, 'planks_birch')
        rgb, h = put(rgb, h, top, work * 1.02, 0.7 + 0.1 * wh)
        grid = np.zeros((N, N), F32)
        for k in (5.6, 10.4):
            grid = np.maximum(grid, 1 - smoothstep(0.12, 0.28, np.abs(X - k)))
            grid = np.maximum(grid, 1 - smoothstep(0.12, 0.28, np.abs(Y - k)))
        grid = grid * top
        rgb = rgb * (1 - 0.35 * grid[..., None])
        h = h - 0.25 * grid
        cuts = smoothstep(0.96, 0.995, ridged(N, (6, 6), seed + 2, 2, sharp=4)) * top * 0.6
        rgb = rgb * (1 - 0.15 * cuts[..., None])
        fr = frame(1.4)
        rgb = rgb * (1 - 0.18 * fr[..., None])
        return tex(rgb, h, path)
    # sides: a framed panel with hanging tools (front: a saw and a mallet; side: a square and chisel)
    fr = frame(1.2)
    panel = rect(1.2, 1.2, 14.8, 14.8)
    pv, ph = board(seed + 3, 'planks_oak', vertical=True)
    rgb, h = put(rgb, h, panel, pv * 0.92, 0.45 + 0.1 * ph)
    rgb, h = put(rgb, h, fr, rgb * 1.05, 0.85)
    tool_rgb, _ = iron(seed + 4, 0.55)
    wood_dark = hexrgb('#5a3a1e')
    if face == 'front':
        saw = polygon([(3.0, 4.0), (8.6, 4.0), (8.6, 6.4), (3.6, 6.0)])
        teeth = (np.abs(((X - 3) * 2) % 1 - 0.5) < 0.25) & (Y > 5.9) & (Y < 6.4) & (X > 3.2) & (X < 8.6)
        handle = rect(8.6, 3.6, 10.6, 6.6) - rect(9.2, 4.4, 10.0, 5.8)
        rgb, h = put(rgb, h, np.clip(saw + teeth, 0, 1), tool_rgb, 0.8)
        rgb, h = put(rgb, h, handle, wood_dark, 0.85)
        mallet_h = rect(10.8, 8.0, 11.6, 13.6)
        mallet = rect(9.4, 7.0, 13.0, 8.8)
        rgb, h = put(rgb, h, mallet_h, wood_dark, 0.8)
        rgb, h = put(rgb, h, mallet, hexrgb('#8a6a42'), 0.9)
        peg = circle(5.8, 3.2, 0.35) + circle(11.2, 6.4, 0.35)
        rgb, h = put(rgb, h, np.clip(peg, 0, 1), hexrgb('#3a2a1a'), 0.9)
    else:
        sq = np.clip(rect(3.0, 3.0, 4.0, 10.0) + rect(3.0, 9.0, 8.0, 10.0), 0, 1)
        rgb, h = put(rgb, h, sq, tool_rgb, 0.8)
        chisel = rect(10.6, 3.4, 11.4, 8.8)
        chisel_h = rect(10.4, 8.8, 11.6, 12.6)
        rgb, h = put(rgb, h, chisel, tool_rgb, 0.8)
        rgb, h = put(rgb, h, chisel_h, wood_dark, 0.85)
    return tex(rgb, h, path)


def bookshelf(seed=4010, path='bookshelf', occupied=None, side=False):
    rgb, h = oak(seed)
    if side:
        return tex(rgb, h, path)
    r = rng(seed + 1)
    shelves = [(1.6, 7.0), (9.0, 14.4)] if occupied is None else [(1.4, 7.4), (8.6, 14.6)]
    for (y0, y1) in shelves:
        inside, dh, shadow = recess(1.2, y0, 14.8, y1, 0.5)
        rgb = rgb * (1 - 0.55 * shadow[..., None])
        h = h + dh
        if occupied is None:
            x = 1.4
            while x < 14.6:
                w = r.uniform(0.8, 1.6)
                if x + w > 14.6:
                    break
                top = y0 + r.uniform(0.2, 1.4)
                book = rect(x, top, x + w * 0.92, y1)
                col = hexrgb(r.choice(['#6e2a22', '#2a4a6e', '#3a5a2a', '#7a5a2a', '#4a2a4a', '#2a2a2a', '#8a7a5a',
                                       '#5a3a22', '#2a5a5a']))
                col = col * r.uniform(0.8, 1.15)
                band = (np.abs(Y - (top + (y1 - top) * 0.25)) < 0.2) | (np.abs(Y - (y1 - 0.8)) < 0.2)
                spine = col[None, None, :] * (0.85 + 0.25 * np.cos(np.pi * (X - x - w / 2) / w))[..., None]
                spine = np.where(band[..., None], np.clip(col * 1.6 + 0.1, 0, 1), spine)
                rgb, h = put(rgb, h, book, spine, 0.7)
                x += w + r.uniform(0.0, 0.25)
        else:
            for k in range(3):
                x0 = 1.2 + k * 4.53
                slot = rect(x0 + 0.3, y0 + 0.3, x0 + 4.2, y1 - 0.3)
                rgb = rgb * (1 - 0.4 * slot[..., None])
                if occupied:
                    for j in range(3):
                        bx = x0 + 0.5 + j * 1.25
                        col = hexrgb(r.choice(['#6e2a22', '#2a4a6e', '#3a5a2a', '#7a5a2a', '#4a2a4a']))
                        rgb, h = put(rgb, h, rect(bx, y0 + r.uniform(0.6, 1.4), bx + 1.1, y1 - 0.3), col, 0.7)
    return tex(rgb, h, path)


def barrel(face, seed=4020):
    path = 'barrel_' + face
    if face == 'side':
        rgb, h = np.zeros((N, N, 3), F32), np.zeros((N, N), F32)
        for k in range(5):
            x0 = k * 3.2
            pv, ph = board(seed + k, 'planks_spruce', vertical=True)
            st = rect(x0 + 0.05, -1, x0 + 3.15, 17)
            bow = 0.6 + 0.4 * np.cos(np.pi * (X - x0 - 1.6) / 3.2)
            rgb, h = put(rgb, h, st, pv * (0.9 + 0.1 * bow[..., None]), 0.5 + 0.2 * bow + 0.1 * ph)
        hoops = np.clip(rect(-1, 2.2, 17, 3.6) + rect(-1, 12.4, 17, 13.8), 0, 1)
        ir, _ = dark_iron(seed + 9)
        rgb, h = put(rgb, h, hoops, ir, 0.9)
        rivet = sum(circle(x, y, 0.25) for x in (1.6, 8.0, 14.4) for y in (2.9, 13.1))
        rgb, h = put(rgb, h, np.clip(rivet, 0, 1), hexrgb('#9a9aa0'), 1.0)
        return tex(rgb, h, path)
    pv, ph = board(seed + 10, 'planks_spruce')
    rgb, h = pv.copy(), 0.5 + 0.1 * ph
    for k in (4.0, 8.0, 12.0):
        gap = 1 - smoothstep(0.08, 0.2, np.abs(Y - k))
        rgb = rgb * (1 - 0.4 * gap[..., None])
        h = h - 0.2 * gap
    ring = frame(1.4)
    ir, _ = dark_iron(seed + 11)
    rgb, h = put(rgb, h, ring, ir * 0.9, 0.9)
    if face == 'top_open':
        hole = rect(1.4, 1.4, 14.6, 14.6)
        inner = ramp(np.clip(0.3 + 0.2 * fbm(N, 6, seed, 3), 0, 1), [(0, '#140c06'), (1, '#3a2614')])
        rgb, h = put(rgb, h, hole, inner, 0.1)
    elif face == 'top':
        lid = circle(8, 8, 1.2)
        rgb, h = put(rgb, h, lid, hexrgb('#3a2a1a'), 0.3)
    return tex(rgb, h, path)


def hive(face, seed, nest=False, honey=False):
    path = ('bee_nest_' if nest else 'beehive_') + face + ('_honey' if honey and face == 'front' else '')
    if nest:
        x, y = warped_coords(N, 0.05, seed, freq=3)
        layers = np.sin(2 * np.pi * (y * 5 + 0.3 * fbm(N, (2, 3), seed + 1, 3, x=x, y=y)))
        t = 0.55 + 0.12 * layers + 0.1 * fbm(N, 12, seed + 2, 3)
        rgb = ramp(np.clip(t, 0, 1), [(0, '#7a5a24'), (0.5, '#c8a052'), (1, '#ecd08a')])
        h = 0.5 + 0.2 * layers
        holes, hv = speckles(N, 9, seed + 3, 0.3, 0.3)
        rgb = rgb * (1 - 0.6 * holes[..., None])
        h = h - 0.3 * holes
        if face in ('top', 'bottom'):
            r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
            ringz = 0.5 + 0.5 * np.sin(r * 2.0)
            rgb = rgb * (0.85 + 0.2 * ringz[..., None])
    else:
        rgb, h = oak(seed)
        if face == 'top':
            fr = frame(1.2)
            rgb = rgb * (1 - 0.15 * fr[..., None])
        else:
            band = rect(-1, 6.6, 17, 9.4)
            hb = ramp(np.clip(0.5 + 0.3 * fbm(N, (12, 2), seed + 4, 2), 0, 1), [(0, '#c27a1a'), (1, '#f2b84a')])
            rgb, h = put(rgb, h, band, hb, 0.85)
    if face == 'front':
        inside, dh, shadow = recess(5.4, 9.8, 10.6, 12.6, 0.6, 0.3)
        rgb = rgb * (1 - 0.85 * shadow[..., None])
        h = h + dh
        if honey:
            drip = np.clip(rect(4.6, 9.6, 11.4, 10.6) + rect(5.6, 10.6, 6.6, 12.8) + rect(9.0, 10.6, 9.9, 13.6)
                           + circle(6.1, 12.8, 0.55) + circle(9.45, 13.6, 0.5), 0, 1)
            rgb, h = put(rgb, h, drip, hexrgb('#f2a21a'), 0.9)
    return tex(rgb, h, path)


def composter(face, seed=4040):
    path = 'composter_' + face
    rgb, h = oak(seed, 'planks_oak')
    if face == 'side':
        for k in (4.0, 8.0, 12.0):
            gap = 1 - smoothstep(0.1, 0.25, np.abs(Y - k))
            rgb = rgb * (1 - 0.4 * gap[..., None])
            h = h - 0.25 * gap
        posts = np.clip(rect(0, 0, 2.0, 16) + rect(14, 0, 16, 16), 0, 1)
        pv, ph = board(seed + 1, 'planks_oak', vertical=True)
        rgb, h = put(rgb, h, posts, pv * 0.9, 0.85)
    else:
        rim = frame(2.0)
        pv, ph = board(seed + 2, 'planks_oak')
        rgb, h = put(rgb, h, rim, pv * 0.95, 0.85)
        if face == 'top':
            inner = rect(2.0, 2.0, 14.0, 14.0)
            rgb = rgb * (1 - 0.5 * inner[..., None])
            h = h - 0.4 * inner
    return tex(rgb, h, path)


def compost(seed, ready=False):
    path = 'compost_ready' if ready else 'compost'
    from recipes.terrain import dirt
    d = dirt(seed, organic=1.5, target=0.3)
    rgb, h = d.albedo, d.height
    segs, owner = scatter(seed + 1, 160, (0.6, 1.6), (0.12, 0.2), curve=0.5, parts=2)
    cols = ramp(rng(seed + 2).uniform(0, 1, len(segs)), [(0, '#3a4a1a'), (0.5, '#6a5a2a'), (1, '#8a7a3a')])
    v, c, _ = capsules(segs, cols)
    rgb = mix(rgb, v, c * 0.8)
    if ready:
        sp, _ = speckles(N, 18, seed + 3, 0.2, 0.35)
        rgb = mix(rgb, hexrgb('#e8e2d2'), sp * 0.8)
    return tex(rgb, h, path, light='over')


def music_block(face, seed=4050):
    path = {'jukebox_side': 'jukebox_side', 'jukebox_top': 'jukebox_top', 'noteblock': 'noteblock'}[face]
    rgb, h = board(seed, 'planks_jungle' if face != 'noteblock' else 'planks_oak')
    fr = frame(1.6)
    rgb = rgb * (1 - 0.15 * fr[..., None])
    h = h + 0.3 * fr
    if face == 'jukebox_top':
        slot = rect(3.0, 7.3, 13.0, 8.7)
        plate = rect(2.0, 6.0, 14.0, 10.0)
        ir, _ = dark_iron(seed + 1)
        rgb, h = put(rgb, h, plate, ir, 0.8)
        rgb, h = put(rgb, h, slot, hexrgb('#0a0a0a'), 0.2)
    elif face == 'jukebox_side':
        inlay = np.clip(frame_mask(3.0, 0.5), 0, 1)
        rgb, h = put(rgb, h, inlay, hexrgb('#d8b878'), 0.75)
    else:
        grille = np.zeros((N, N), F32)
        for k in range(5):
            grille = np.maximum(grille, rect(3.0, 3.4 + k * 2.2, 13.0, 4.4 + k * 2.2))
        rgb = rgb * (1 - 0.6 * grille[..., None])
        h = h - 0.3 * grille
    return tex(rgb, h, path)


def table_top_paper(seed, path):
    """Cartography table top: a map sheet pinned to a dark-wood board."""
    rgb, h = board(seed, 'planks_big_oak')
    paper = rect(1.6, 1.6, 14.4, 14.4)
    x, y = warped_coords(N, 0.05, seed + 1, freq=3)
    land = smoothstep(-0.05, 0.1, fbm(N, 3, seed + 2, 5, x=x, y=y))
    contour = 1 - smoothstep(0.0, 0.05, np.abs(((fbm(N, 3, seed + 2, 5, x=x, y=y) * 6) % 1.0) - 0.5) - 0.42)
    pc = mix(np.broadcast_to(hexrgb('#e8dcc0'), (N, N, 3)), np.broadcast_to(hexrgb('#d6c69a'), (N, N, 3)), land)
    pc = mix(pc, np.broadcast_to(hexrgb('#a89a72'), (N, N, 3)), contour * land * 0.6)
    pc = np.where((land < 0.5)[..., None], pc * np.array([0.92, 0.97, 1.05], F32), pc)
    rgb, h = put(rgb, h, paper, pc, 0.7)
    pins = sum(circle(x, y, 0.4) for x in (2.4, 13.6) for y in (2.4, 13.6))
    rgb, h = put(rgb, h, np.clip(pins, 0, 1), hexrgb('#8a2a1a'), 0.9)
    return tex(rgb, h, path, target=None)


def table_side(seed, path, wood='planks_big_oak', motif=None):
    rgb, h = board(seed, wood, vertical=True)
    fr = frame(1.4)
    rgb = rgb * (1 - 0.2 * fr[..., None])
    h = h + 0.3 * fr
    if motif == 'feathers':
        for k, x0 in enumerate((5.0, 8.0, 11.0)):
            shaft = rect(x0 - 0.15, 3.0, x0 + 0.15, 12.5)
            vane = ellipse(x0, 5.0, 0.9, 2.2)
            rgb, h = put(rgb, h, vane, hexrgb('#ece8e0') * (0.9 + 0.05 * k), 0.75)
            rgb, h = put(rgb, h, shaft, hexrgb('#5a3a1a'), 0.8)
            tip = polygon([(x0 - 0.5, 12.3), (x0 + 0.5, 12.3), (x0, 13.6)])
            rgb, h = put(rgb, h, tip, hexrgb('#8a8a8a'), 0.8)
    elif motif == 'map':
        paper = rect(3.0, 3.0, 13.0, 10.0)
        rgb, h = put(rgb, h, paper, hexrgb('#e2d6b8'), 0.7)
        lines = (np.abs(Y - 5.0) < 0.15) | (np.abs(Y - 7.0) < 0.15)
        rgb, h = put(rgb, h, (lines & (paper > 0.5)).astype(F32), hexrgb('#8a7a5a'), 0.7)
    elif motif == 'tools':
        ir, _ = iron(seed + 1, 0.5)
        tongs = np.clip(rect(4.0, 3.0, 4.6, 12.0) + rect(5.4, 3.0, 6.0, 12.0) + rect(4.0, 11.4, 6.0, 12.0), 0, 1)
        hammer = np.clip(rect(10.0, 4.0, 10.8, 12.0) + rect(8.8, 3.0, 12.0, 5.0), 0, 1)
        rgb, h = put(rgb, h, tongs, ir, 0.8)
        rgb, h = put(rgb, h, hammer, ir * 0.9, 0.8)
    elif motif == 'loom':
        threads = np.zeros((N, N), F32)
        for k in range(10):
            threads = np.maximum(threads, (np.abs(X - (3.0 + k * 1.1)) < 0.18).astype(F32) * rect(2.0, 3.0, 14.0, 13.0))
        rgb, h = put(rgb, h, threads, hexrgb('#e8e0d0'), 0.7)
        beam = np.clip(rect(1.4, 2.4, 14.6, 3.6) + rect(1.4, 12.4, 14.6, 13.6), 0, 1)
        rgb, h = put(rgb, h, beam, hexrgb('#6a4a2a'), 0.85)
    return tex(rgb, h, path)


def smithing(face, seed=4070):
    path = 'smithing_table_' + face
    if face == 'top':
        ir, ih = iron(seed, 0.45)
        rgb, h = ir, ih
        fr = frame(1.2)
        rgb = rgb * (1 - 0.2 * fr[..., None])
        h = h + 0.2 * fr
        bolts = sum(circle(x, y, 0.4) for x in (2.0, 14.0) for y in (2.0, 14.0))
        rgb, h = put(rgb, h, np.clip(bolts, 0, 1), hexrgb('#b8b8c0'), 1.0)
        return tex(rgb, h, path, gloss=0.2)
    if face == 'bottom':
        rgb, h = board(seed + 1, 'planks_big_oak')
        return tex(rgb, h, path)
    rgb, h = board(seed + 2, 'planks_big_oak', vertical=True)
    top = rect(-1, 0, 17, 3.2)
    ir, _ = iron(seed + 3, 0.4)
    rgb, h = put(rgb, h, top, ir, 0.9)
    if face == 'front':
        return table_side(seed + 4, path, 'planks_big_oak', 'tools')
    return tex(rgb, h, path)


def lectern(face, seed=4080):
    path = 'lectern_' + face
    rgb, h = board(seed, 'planks_oak', vertical=face in ('front', 'sides'))
    fr = frame(1.0)
    rgb = rgb * (1 - 0.18 * fr[..., None])
    h = h + 0.25 * fr
    if face == 'front':
        inlay = np.clip(rect(5.0, 3.0, 11.0, 4.0) + rect(7.5, 4.0, 8.5, 12.0) + rect(5.0, 12.0, 11.0, 13.0), 0, 1)
        rgb, h = put(rgb, h, inlay, hexrgb('#4a3018'), 0.4)
    return tex(rgb, h, path)


def stonecutter(face, seed=4090, v2=False):
    base = 'stonecutter2_' if v2 else 'stonecutter_'
    path = base + face
    rgb, h = stonework(seed, 'smooth')
    if face == 'top':
        slot = rect(1.6, 7.4, 14.4, 8.6)
        rgb, h = put(rgb, h, slot, hexrgb('#141414'), 0.1)
        ir, _ = iron(seed + 1, 0.5)
        plates = np.clip(rect(1.0, 4.0, 15.0, 7.0) + rect(1.0, 9.0, 15.0, 12.0), 0, 1)
        rgb, h = put(rgb, h, plates, ir, 0.75)
    elif face in ('side', 'other_side'):
        band = rect(-1, 0, 17, 7.0)
        ir, _ = iron(seed + 2, 0.4)
        rgb, h = put(rgb, h, band, ir * 0.9, 0.7)
    return tex(rgb, h, path)


def saw(frame_i, frames, seed=4095):
    path = 'stonecutter2_saw'
    m = mask_of(path).astype(F32)
    ang = np.arctan2(Y - 8, X - 8) + frame_i / frames * 2 * np.pi / 12
    r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
    teeth = 0.5 + 0.5 * np.sign(np.sin(ang * 12))
    rgb = ramp(np.clip(0.5 + 0.3 * (1 - r / 9) + 0.1 * teeth, 0, 1), [(0, '#5a5a62'), (0.6, '#b8b8c0'), (1, '#f0f0f4')])
    return tex(rgb, None, path, alpha=m, light='none')


# ------------------------------------------------------------------ furnaces and machines (stone)
def furnace_family(kind, face, seed, frame_i=0, frames=1):
    path = {'furnace': 'furnace_', 'smoker': 'smoker_', 'blast': 'blast_furnace_'}[kind] + face
    if kind == 'blast':
        rgb, h = stonework(seed, 'smooth')
        ir, _ = iron(seed + 1, 0.45)
        fr = frame(1.6)
        rgb, h = put(rgb, h, fr, ir, 0.85)
        bolts = sum(circle(x, y, 0.35) for x in (0.8, 15.2) for y in (0.8, 5.0, 11.0, 15.2))
        rgb, h = put(rgb, h, np.clip(bolts, 0, 1), hexrgb('#c8c8d0'), 1.0)
    elif kind == 'smoker':
        rgb, h = stonework(seed, 'cobble')
        logs = np.clip(rect(-1, 0, 17, 2.4) + rect(-1, 13.6, 17, 16.2), 0, 1)
        lv, lh = board(seed + 2, 'planks_spruce')
        rgb, h = put(rgb, h, logs, lv * 0.8, 0.85)
    else:
        rgb, h = stonework(seed, 'bricks' if face != 'top' else 'smooth')
    if face == 'top':
        if kind == 'smoker':
            vent = np.zeros((N, N), F32)
            for k in range(4):
                vent = np.maximum(vent, rect(4.0, 4.0 + 2.2 * k, 12.0, 5.0 + 2.2 * k))
            rgb = rgb * (1 - 0.6 * vent[..., None])
        elif kind == 'blast':
            grille = np.zeros((N, N), F32)
            for k in range(5):
                grille = np.maximum(grille, rect(3.0 + 2.2 * k, 3.0, 4.0 + 2.2 * k, 13.0))
            rgb = rgb * (1 - 0.6 * grille[..., None])
            h = h - 0.3 * grille
        return tex(rgb, h, path)
    if not face.startswith('front'):
        return tex(rgb, h, path)
    lit = face.endswith('_on')
    # mouth: an arched opening with a lintel; smoker has an iron grate; blast furnace a slotted door
    x0, x1, y0, y1 = 3.6, 12.4, 7.6, 13.6
    mouth = np.clip(rect(x0, y0 + 1.6, x1, y1) + ellipse(8.0, y0 + 1.6, (x1 - x0) / 2, 1.6), 0, 1)
    lintel = np.clip(rect(x0 - 0.8, y0 - 1.6, x1 + 0.8, y0 - 0.2), 0, 1)
    sill = rect(x0 - 0.8, y1, x1 + 0.8, y1 + 1.0)
    st_rgb, st_h = stonework(seed + 3, 'smooth')
    rgb, h = put(rgb, h, np.clip(lintel + sill, 0, 1), st_rgb * 0.95, 0.9)
    inner = ramp(np.clip(0.3 + 0.2 * fbm(N, 6, seed + 4, 3), 0, 1), [(0, '#060505'), (1, '#1e1a18')])
    em = None
    if lit:
        fr_rgb, fl = glow_fire(seed + 5, x0, y0, x1, y1, phase=frame_i / max(frames, 1))
        inner = mix(inner, fr_rgb, np.clip(fl * 1.3, 0, 1))
        em = (mouth * np.clip(fl, 0, 1) * 0.55)[..., None] * hexrgb('#ffb04a')
    rgb, h = put(rgb, h, mouth, inner, 0.15)
    if kind in ('smoker', 'blast'):
        ir, _ = dark_iron(seed + 6)
        bars = np.zeros((N, N), F32)
        for k in range(5):
            bars = np.maximum(bars, rect(x0 + 0.6 + k * 1.75, y0, x0 + 1.2 + k * 1.75, y1))
        bars = bars * mouth
        rgb, h = put(rgb, h, bars, ir, 0.7)
    return tex(rgb, h, path, emissive=em)


def dispenser_front(seed, path, vertical=False, dropper=False):
    rgb, h = stonework(seed, 'cobble')
    if vertical:
        hole = circle(8, 8, 3.2) if not dropper else rect(5.0, 5.0, 11.0, 11.0)
    else:
        hole = circle(8, 8, 3.0) if not dropper else rect(5.0, 6.0, 11.0, 10.0)
    ring = np.clip(blur(hole, 3.0) * 2.2 - hole, 0, 1)
    sm, _ = stonework(seed + 1, 'smooth')
    rgb, h = put(rgb, h, ring, sm, 0.9)
    inner = ramp(np.clip(0.2 + 0.2 * (1 - np.sqrt((X - 8) ** 2 + (Y - 8) ** 2) / 4), 0, 1), [(0, '#0a0908'),
                                                                                            (1, '#2a2622')])
    rgb, h = put(rgb, h, hole, inner, 0.1)
    return tex(rgb, h, path)


def observer(face, seed=4110):
    path = 'observer_' + face
    rgb, h = stonework(seed, 'smooth')
    rgb = rgb * 0.75
    if face == 'front':
        for cx in (5.0, 11.0):
            eye = rect(cx - 2.4, 5.0, cx + 2.4, 10.0)
            rgb, h = put(rgb, h, eye, hexrgb('#141414'), 0.2)
            lens = rect(cx - 1.2, 6.2, cx + 1.2, 8.8)
            rgb, h = put(rgb, h, lens, hexrgb('#5a5a5a'), 0.3)
        brow = rect(1.4, 3.0, 14.6, 4.2)
        rgb, h = put(rgb, h, brow, hexrgb('#9a9a9a'), 0.9)
    elif face.startswith('back'):
        port = rect(5.0, 5.0, 11.0, 11.0)
        lit = face == 'back_lit'
        rgb, h = put(rgb, h, port, hexrgb('#ff3a2a') if lit else hexrgb('#3a1410'), 0.3)
        em = (port * 0.5)[..., None] * hexrgb('#ff4a2a') if lit else None
        return tex(rgb, h, path, emissive=em)
    elif face == 'side':
        arrow = polygon([(8, 2.0), (12.6, 7.0), (9.6, 7.0), (9.6, 14.0), (6.4, 14.0), (6.4, 7.0), (3.4, 7.0)])
        rgb, h = put(rgb, h, arrow, hexrgb('#b8b8b8'), 0.8)
        dust = arrow * (fbm(N, 20, seed, 2) > 0.3)
        rgb = mix(rgb, hexrgb('#8a1410'), dust * 0.5)
    else:
        grille = np.zeros((N, N), F32)
        for k in range(4):
            grille = np.maximum(grille, rect(3.0, 3.0 + 2.8 * k, 13.0, 4.2 + 2.8 * k))
        rgb = rgb * (1 - 0.5 * grille[..., None])
    return tex(rgb, h, path)


def piston(face, seed=4120):
    path = 'piston_' + face
    if face in ('top_normal', 'top_sticky'):
        rgb, h = oak(seed)
        fr = frame(1.6)
        ir, _ = iron(seed + 1, 0.5)
        rgb, h = put(rgb, h, fr, ir, 0.9)
        if face == 'top_sticky':
            goo = smoothstep(-0.2, 0.2, fbm(N, 4, seed + 2, 4) + 0.15) * rect(1.6, 1.6, 14.4, 14.4)
            rgb = mix(rgb, hexrgb('#6ab84a'), goo * 0.85)
            h = h + 0.15 * goo
        return tex(rgb, h, path)
    if face == 'side':
        rgb, h = stonework(seed, 'cobble')
        head = rect(-1, 0, 17, 4.0)
        pv, ph = board(seed + 3, 'planks_oak')
        rgb, h = put(rgb, h, head, pv, 0.9)
        ir, _ = iron(seed + 4, 0.45)
        band = rect(-1, 4.0, 17, 5.0)
        rgb, h = put(rgb, h, band, ir, 0.95)
        return tex(rgb, h, path)
    if face == 'bottom':
        rgb, h = stonework(seed, 'cobble')
        return tex(rgb, h, path)
    rgb, h = stonework(seed, 'cobble')
    shaft = rect(6.0, 6.0, 10.0, 10.0)
    ir, _ = iron(seed + 5, 0.5)
    rgb, h = put(rgb, h, shaft, ir, 0.8)
    return tex(rgb, h, path)


def lamp(on, seed=4130):
    path = 'redstone_lamp_on' if on else 'redstone_lamp_off'
    fr = frame(1.4)
    pv, ph = board(seed, 'planks_oak')
    glass = rect(1.4, 1.4, 14.6, 14.6)
    x, y = warped_coords(N, 0.06, seed + 1, freq=3)
    f1, f2, cid = worley(N, 6, seed + 2, 0.8, x, y)
    facet = cell_random(cid, seed + 3)
    lead = 1 - smoothstep(0.02, 0.08, f2 - f1)
    if on:
        core = ramp(np.clip(0.55 + 0.35 * facet, 0, 1), [(0, '#c26a1a'), (0.6, '#f6c25a'), (1, '#fff2c0')])
    else:
        core = ramp(np.clip(0.4 + 0.3 * facet, 0, 1), [(0, '#3a1a0e'), (0.6, '#6a3a1e'), (1, '#8a5a32')])
    rgb = mix(core, hexrgb('#2a1a10') if not on else hexrgb('#8a5a2a'), lead * 0.8)
    h = 0.55 + 0.15 * facet - 0.3 * lead
    rgb, h = put(rgb, h, fr, pv * 0.8, 0.95)
    em = ((glass * (1 - lead)) * 0.5)[..., None] * hexrgb('#ffcf7a') if on else None
    return tex(rgb, h, path, emissive=em)


def target(face, seed=4140):
    path = 'target_' + face
    from recipes.organics import hay
    base = hay(seed, 'top' if face == 'top' else 'side')
    rgb, h = base.albedo, base.height
    r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
    rings = ((r < 7.0) & (r > 5.2)) | ((r < 3.6) & (r > 1.8))
    rgb = mix(rgb, hexrgb('#e8e2d6'), (r < 7.0) * 0.85)
    rgb = mix(rgb, hexrgb('#c42a1e'), rings * 0.95)
    rgb = mix(rgb, hexrgb('#c42a1e'), (r < 0.9) * 1.0)
    return tex(rgb, h, path)


def lodestone(face, seed=4150):
    path = 'lodestone_' + face
    t = polished(stone(seed), seed + 1)
    rgb, h = t.albedo, t.height
    ir, _ = iron(seed + 2, 0.35)
    if face == 'top':
        ring = np.clip(circle(8, 8, 5.0) - circle(8, 8, 3.6), 0, 1)
        rgb, h = put(rgb, h, ring, ir, 0.9)
        rgb, h = put(rgb, h, circle(8, 8, 1.6), hexrgb('#5a2a8a'), 0.95)
    else:
        bands = np.clip(rect(-1, 2.0, 17, 3.6) + rect(-1, 12.4, 17, 14.0), 0, 1)
        rgb, h = put(rgb, h, bands, ir, 0.9)
        cross = np.clip(rect(7.2, 3.6, 8.8, 12.4), 0, 1)
        rgb, h = put(rgb, h, cross, ir * 1.2, 0.85)
    return tex(rgb, h, path)


def anchor(face, seed=4160, charge=0, frame_i=0, frames=1):
    if face == 'side':
        path = f'respawn_anchor_side{charge}'
    else:
        path = 'respawn_anchor_' + face
    t = polished(blackstone(seed, 0.2, 'top'), seed + 1)
    rgb, h = t.albedo, t.height
    from recipes.terrain import obsidian
    ob = obsidian(seed + 2, crying=True)
    em = None
    if face == 'side':
        pane = rect(3.0, 3.0, 13.0, 13.0)
        rgb, h = put(rgb, h, pane, ob.albedo, 0.5)
        lights = [circle(5.0, 13.6, 0.8), circle(8.0, 13.6, 0.8), circle(11.0, 13.6, 0.8), circle(14.0, 13.6, 0.8)]
        for k, lm in enumerate(lights[:4]):
            on = k < charge
            rgb, h = put(rgb, h, lm, hexrgb('#f2a23a') if on else hexrgb('#2a1a10'), 0.9)
            if on:
                em = (em if em is not None else 0) + (lm * 0.6)[..., None] * hexrgb('#ffb04a')
    elif face in ('top', 'top_off'):
        core = circle(8, 8, 5.0)
        if face == 'top':
            from recipes.liquids import drift
            sw = drift(seed + 3, frame_i / max(frames, 1), 4, 4, 0.25)
            pc = ramp(np.clip(0.5 + 0.4 * sw, 0, 1), [(0, '#2a0a5a'), (0.5, '#7a2ad6'), (1, '#e2b8ff')])
            rgb, h = put(rgb, h, core, pc, 0.3)
            em = (core * 0.5)[..., None] * hexrgb('#b05cff')
        else:
            rgb, h = put(rgb, h, core, ob.albedo, 0.3)
    return tex(rgb, h, path, emissive=em)


def enchanting(face, seed=4170):
    path = 'enchanting_table_' + face
    from recipes.terrain import obsidian
    ob = obsidian(seed)
    rgb, h = ob.albedo, ob.height
    if face == 'top':
        cloth = rect(1.0, 1.0, 15.0, 15.0)
        cc = ramp(np.clip(0.5 + 0.2 * fbm(N, (3, 20), seed + 1, 3), 0, 1), [(0, '#4a0a0a'), (1, '#9a1e1e')])
        rgb, h = put(rgb, h, cloth, cc, 0.6)
        trim = np.clip(frame_mask(1.6, 0.5), 0, 1)
        rgb, h = put(rgb, h, trim, hexrgb('#d8a83a'), 0.7)
        sig = np.zeros((N, N), F32)
        for k in range(4):
            a = k * np.pi / 2 + np.pi / 4
            sig = np.maximum(sig, circle(8 + 4.2 * np.cos(a), 8 + 4.2 * np.sin(a), 0.5))
        rgb, h = put(rgb, h, sig, hexrgb('#e8c25a'), 0.7)
        return tex(rgb, h, path)
    if face == 'side':
        cloth = rect(-1, 0, 17, 4.0)
        cc = ramp(np.clip(0.5 + 0.2 * fbm(N, (3, 20), seed + 1, 3), 0, 1), [(0, '#4a0a0a'), (1, '#9a1e1e')])
        rgb, h = put(rgb, h, cloth, cc, 0.6)
        tassels = np.zeros((N, N), F32)
        for k in range(4):
            tassels = np.maximum(tassels, polygon([(2.0 + 4 * k, 4.0), (4.0 + 4 * k, 4.0), (3.0 + 4 * k, 6.0)]))
        rgb, h = put(rgb, h, tassels, hexrgb('#d8a83a'), 0.6)
    return tex(rgb, h, path)


def endframe(face, seed=4180):
    path = 'endframe_' + face
    from recipes.stones import end_stone
    es = end_stone(seed)
    rgb, h = es.albedo, es.height
    if face == 'top':
        tile = ramp(np.clip(0.5 + 0.3 * fbm(N, 6, seed + 1, 3), 0, 1), [(0, '#1a3a32'), (1, '#3a6a5a')])
        inner = rect(2.0, 2.0, 14.0, 14.0)
        rgb, h = put(rgb, h, inner, tile, 0.5)
        socket = circle(8, 8, 3.0)
        rgb, h = put(rgb, h, socket, hexrgb('#0a1a16'), 0.2)
    elif face == 'side':
        top = rect(-1, 0, 17, 3.0)
        tile = ramp(np.clip(0.5 + 0.3 * fbm(N, 6, seed + 1, 3), 0, 1), [(0, '#1a3a32'), (1, '#3a6a5a')])
        rgb, h = put(rgb, h, top, tile, 0.8)
    else:
        m = mask_of(path).astype(F32)
        r = np.sqrt((X - 8) ** 2 + (Y - 8) ** 2)
        rgb = ramp(np.clip(1 - r / 8, 0, 1), [(0, '#0a3a2a'), (0.5, '#2a8a6a'), (0.8, '#c2f2d2'), (1, '#0a0a0a')])
        return tex(rgb, None, path, alpha=m, light='none')
    return tex(rgb, h, path)


def beacon(seed=4190):
    path = 'beacon'
    x, y = warped_coords(N, 0.05, seed, freq=3)
    shards = smoothstep(0.75, 0.95, ridged(N, 4, seed + 1, 3, sharp=2.0))
    glow = fbm(N, 4, seed + 2, 4)
    rgb = ramp(np.clip(0.6 + 0.2 * glow + 0.2 * shards, 0, 1), [(0, '#3aa8a0'), (0.6, '#8ae8e0'), (1, '#f2fffe')])
    return tex(rgb, 0.5 + 0.3 * shards, path, emissive=(0.25 * np.ones((N, N)))[..., None] * hexrgb('#c8fff8'))


def daylight(face, seed=4200):
    path = {'top': 'daylight_detector_top', 'inverted': 'daylight_detector_inverted_top',
            'side': 'daylight_detector_side'}[face]
    pv, ph = board(seed, 'planks_oak')
    rgb, h = pv, 0.5 + 0.1 * ph
    if face != 'side':
        panel = rect(1.4, 1.4, 14.6, 14.6)
        cells = np.zeros((N, N), F32)
        for i in range(3):
            for j in range(3):
                cells = np.maximum(cells, rect(1.8 + i * 4.3, 1.8 + j * 4.3, 5.7 + i * 4.3, 5.7 + j * 4.3))
        glass = ramp(np.clip(0.4 + 0.3 * fbm(N, 10, seed + 1, 3), 0, 1),
                     [(0, '#1a2a4a'), (1, '#4a6a9a')] if face == 'top' else [(0, '#4a1a1a'), (1, '#9a4a3a')])
        rgb, h = put(rgb, h, cells, glass, 0.6)
        rgb = mix(rgb, hexrgb('#d8d8e0'), (panel - cells).clip(0, 1) * 0.35)
    return tex(rgb, h, path)


def tnt(face, seed=4210):
    path = 'tnt_' + face
    if face == 'side':
        rgb = np.zeros((N, N, 3), F32)
        h = np.zeros((N, N), F32)
        for k in range(5):
            x0 = k * 3.2
            r = np.abs(X - x0 - 1.6) / 1.6
            st = rect(x0 + 0.1, -1, x0 + 3.1, 17)
            col = ramp(np.clip(0.75 - 0.4 * r ** 2 + 0.05 * fbm(N, (3, 20), seed + k, 2), 0, 1),
                       [(0, '#6a1208'), (0.5, '#b8261a'), (1, '#e85a3a')])
            rgb, h = put(rgb, h, st, col, 0.6 + 0.3 * (1 - r ** 2))
        wrap = rect(-1, 5.4, 17, 10.6)
        paper = ramp(np.clip(0.6 + 0.2 * fbm(N, (4, 12), seed + 9, 2), 0, 1), [(0, '#cfc6b0'), (1, '#f2ece0')])
        rgb, h = put(rgb, h, wrap, paper, 0.85)
        mark = np.clip(rect(3.0, 7.0, 13.0, 9.0) - rect(4.0, 7.6, 12.0, 8.4), 0, 1)
        rgb, h = put(rgb, h, mark, hexrgb('#2a2622'), 0.85)
        return tex(rgb, h, path)
    rgb = ramp(np.clip(0.5 + 0.2 * fbm(N, 10, seed + 10, 3), 0, 1), [(0, '#5a1208'), (1, '#c2361e')])
    h = np.full((N, N), 0.5, F32)
    for (cx, cy) in ((4.5, 4.5), (11.5, 4.5), (4.5, 11.5), (11.5, 11.5), (8, 8)):
        end = circle(cx, cy, 2.6)
        rgb, h = put(rgb, h, end, hexrgb('#d8c8a8') if face == 'top' else hexrgb('#8a7a5a'), 0.7)
        rgb, h = put(rgb, h, circle(cx, cy, 0.7), hexrgb('#2a2622'), 0.4)
    if face == 'top':
        fuse = np.clip(polyline([(8, 8), (8.6, 6.0), (9.8, 4.6)], [0.4, 0.35, 0.3])[0], 0, 1)
        rgb, h = put(rgb, h, fuse, hexrgb('#e8e0c8'), 0.9)
    return tex(rgb, h, path)


# ------------------------------------------------------------------ model-mapped small parts
def masked_part(path, rgb, *, emissive_mask=None, glow='#ffd27a', light='none', smooth=False):
    m = mask_of(path, smooth=smooth).astype(F32)
    em = None
    if emissive_mask is not None:
        em = (emissive_mask * m * 0.6)[..., None] * hexrgb(glow)
    return tex(rgb, 0.5 + 0.1 * fbm(N, 10, 7, 2), path, alpha=m, light=light, emissive=em)


def wood_rgb(seed, path='planks_oak'):
    rgb, h = board(seed, path, vertical=True)
    return rgb


def flame_head(y0, y1, cols):
    yy = np.clip((Y - y0) / (y1 - y0), 0, 1)
    return ramp(1 - yy, cols)


def torch(path, flame_cols, seed=4300):
    rgb = wood_rgb(seed, 'planks_oak')
    head = (Y < 8.0)
    fc = flame_head(6.0, 8.0, flame_cols)
    rgb = np.where(head[..., None], fc, rgb)
    return masked_part(path, rgb, emissive_mask=head.astype(F32), glow=flame_cols[-1][1])


def lantern(frame_i, frames, path, glow='#ffc25a', seed=4310):
    m = mask_of(path).astype(F32)
    ir, _ = dark_iron(seed)
    flick = 0.9 + 0.1 * np.sin(2 * np.pi * frame_i / frames)
    window = rect(1.5, 3.0, 4.5, 13.0) * m
    gl = ramp(np.clip(0.5 + 0.5 * (1 - np.abs(X - 3.0) / 1.5), 0, 1), [(0, glow), (1, '#fff6d8')]) * flick
    rgb = mix(ir, gl, window)
    return tex(rgb, None, path, alpha=m, light='none', emissive=(window * 0.6 * flick)[..., None] * hexrgb(glow))


def rail(kind, powered=False, seed=4320):
    path = {'normal': 'rail_normal', 'turned': 'rail_normal_turned', 'golden': 'rail_golden',
            'detector': 'rail_detector', 'activator': 'rail_activator'}[kind] + ('_powered' if powered else '')
    alpha = np.zeros((N, N), F32)
    rgb = np.zeros((N, N, 3), F32)
    h = np.zeros((N, N), F32)
    tie_rgb, tie_h = board(seed, 'planks_oak')
    tie_rgb = tie_rgb * 0.8
    if kind == 'turned':
        rr = np.sqrt((X - 16) ** 2 + (Y - 16) ** 2)
        ang = np.arctan2(16 - Y, 16 - X)
        for k in range(5):
            a = (k + 0.5) / 5 * np.pi / 2
            d = np.abs(np.sin(ang - a)) * rr
            tie = ((d < 0.9) & (rr > 1.2) & (rr < 14.8) & (np.abs(ang - a) < 0.5)).astype(F32)
            rgb, h = put(rgb, h, tie, tie_rgb, 0.5)
            alpha = np.maximum(alpha, tie)
        rails = (((rr > 2.5) & (rr < 3.6)) | ((rr > 12.4) & (rr < 13.5))).astype(F32)
    else:
        for k in range(4):
            tie = rect(1.0, 1.2 + 4 * k, 15.0, 2.8 + 4 * k)
            rgb, h = put(rgb, h, tie, tie_rgb, 0.5)
            alpha = np.maximum(alpha, tie)
        rails = np.clip(rect(2.5, -1, 3.6, 17) + rect(12.4, -1, 13.5, 17), 0, 1)
    metal = {'normal': '#8a8a90', 'turned': '#8a8a90', 'golden': '#e2b23a', 'detector': '#7a7a80',
             'activator': '#8a6a5a'}[kind]
    rail_rgb = hexrgb(metal) * (0.85 + 0.2 * np.cos(np.pi * ((X % 1.1) / 1.1 - 0.5)))[..., None]
    rgb, h = put(rgb, h, rails, rail_rgb, 0.9)
    alpha = np.maximum(alpha, rails)
    em = None
    if kind in ('golden', 'detector', 'activator'):
        strip = rect(7.4, -1, 8.6, 17)
        col = '#e22a1a' if powered else '#5a1a14'
        rgb, h = put(rgb, h, strip, hexrgb(col), 0.7)
        alpha = np.maximum(alpha, strip)
        if powered:
            em = (strip * 0.5)[..., None] * hexrgb('#ff3a2a')
    return tex(rgb, h, path, alpha=alpha, light='top', emissive=em)


def ladder(seed=4330):
    path = 'ladder'
    rgb, h = board(seed, 'planks_oak', vertical=True)
    rails = np.clip(rect(1.8, -1, 3.8, 17) + rect(12.2, -1, 14.2, 17), 0, 1)
    rungs = np.zeros((N, N), F32)
    for k in range(4):
        rungs = np.maximum(rungs, rect(1.0, 1.0 + 4 * k, 15.0, 2.4 + 4 * k))
    rv, rh = board(seed + 1, 'planks_oak')
    rgb2 = mix(rgb, rv, rungs)
    alpha = np.clip(rails + rungs, 0, 1)
    h2 = 0.6 + 0.3 * rungs + 0.1 * rails
    nails = sum(circle(x, 1.7 + 4 * k, 0.25) for x in (2.8, 13.2) for k in range(4))
    rgb2 = mix(rgb2, hexrgb('#4a4a4e'), np.clip(nails, 0, 1))
    return tex(rgb2, h2, path, alpha=alpha)


def scaffold(face, seed=4340):
    path = 'scaffolding_' + face
    pole = ramp(np.clip(0.5 + 0.3 * fbm(N, (2, 16), seed, 2), 0, 1), [(0, '#a8902a'), (1, '#e8d06a')])
    fr = frame(2.0)
    rgb = pole
    alpha = fr.copy()
    h = 0.5 + 0.3 * fr
    if face == 'top':
        slats = np.zeros((N, N), F32)
        for k in range(6):
            slats = np.maximum(slats, rect(2.0, 2.2 + 2.0 * k, 14.0, 3.6 + 2.0 * k))
        alpha = np.clip(alpha + slats, 0, 1)
        h = h + 0.2 * slats
    else:
        diag = (np.abs((X - 2) - (Y - 2)) < 0.9) * rect(1.0, 1.0, 15.0, 15.0)
        alpha = np.clip(alpha + diag, 0, 1)
    twine = (np.abs(X - 2.0) < 0.6) & (np.abs(Y - 2.0) < 0.6)
    rgb = np.where(twine[..., None], hexrgb('#6a4a2a'), rgb)
    return tex(rgb, h, path, alpha=alpha)


def bars(path, seed=4350):
    rgb, _ = iron(seed, 0.5, streak='y')
    return masked_part(path, rgb)


def dust(path, cross=False):
    a = np.zeros((N, N), F32)
    line = rect(-1, 6.8, 17, 9.2)
    if cross:
        line = np.clip(line + rect(6.8, -1, 9.2, 17), 0, 1)
    grain = (fbm(N, 40, 9, 2) > -0.1).astype(F32)
    a = line * grain
    a = np.maximum(a, line * blur(grain, 1.0) > 0.6)
    rgb = np.repeat((0.85 + 0.15 * fbm(N, 30, 10, 2))[..., None], 3, axis=-1)
    return Tex(rgb.astype(F32), None, a.astype(F32), light='none', cutout=True, sharpen=0.0)


# ------------------------------------------------------------------ registration
def register(R):
    for face in ('top', 'side', 'front'):
        R.block(f'crafting_table_{face}', lambda v, face=face: crafting_table(face))
    R.block('bookshelf', lambda v: bookshelf())
    R.block('chiseled_bookshelf_empty', lambda v: bookshelf(4011, 'chiseled_bookshelf_empty', occupied=False))
    R.block('chiseled_bookshelf_occupied', lambda v: bookshelf(4011, 'chiseled_bookshelf_occupied', occupied=True))
    R.block('chiseled_bookshelf_side', lambda v: bookshelf(4012, 'chiseled_bookshelf_side', side=True))
    R.block('chiseled_bookshelf_top', lambda v: bookshelf(4013, 'chiseled_bookshelf_top', side=True))
    for face in ('side', 'top', 'bottom', 'top_open'):
        R.block(f'barrel_{face}', lambda v, face=face: barrel(face))
    for face in ('front', 'side', 'top'):
        R.block(f'beehive_{face}', lambda v, face=face: hive(face, 4030))
    R.block('beehive_front_honey', lambda v: hive('front', 4030, honey=True))
    for face in ('front', 'side', 'top', 'bottom'):
        R.block(f'bee_nest_{face}', lambda v, face=face: hive(face, 4031, nest=True))
    R.block('bee_nest_front_honey', lambda v: hive('front', 4031, nest=True, honey=True))
    for face in ('side', 'top', 'bottom'):
        R.block(f'composter_{face}', lambda v, face=face: composter(face))
    R.block('compost', lambda v: compost(4041))
    R.block('compost_ready', lambda v: compost(4041, ready=True))
    for p in ('jukebox_side', 'jukebox_top', 'noteblock'):
        R.block(p, lambda v, p=p: music_block(p))
    R.block('cartography_table_top', lambda v: table_top_paper(4060, 'cartography_table_top'))
    for k in (1, 2, 3):
        R.block(f'cartography_table_side{k}', lambda v, k=k: table_side(4061 + k, f'cartography_table_side{k}',
                                                                        motif='map' if k == 1 else None))
    R.block('fletcher_table_top', lambda v: table_side(4065, 'fletcher_table_top', 'planks_birch'))
    R.block('fletcher_table_side1', lambda v: table_side(4066, 'fletcher_table_side1', 'planks_birch', 'feathers'))
    R.block('fletcher_table_side2', lambda v: table_side(4067, 'fletcher_table_side2', 'planks_birch'))
    for face in ('front', 'side', 'top', 'bottom'):
        R.block(f'smithing_table_{face}', lambda v, face=face: smithing(face))
        R.block(f'loom_{face}', lambda v, face=face: table_side(4075, f'loom_{face}', 'planks_oak',
                                                                 'loom' if face == 'front' else None))
    for face in ('base', 'front', 'sides', 'top'):
        R.block(f'lectern_{face}', lambda v, face=face: lectern(face))
    for face in ('top', 'side', 'bottom', 'other_side'):
        R.block(f'stonecutter_{face}', lambda v, face=face: stonecutter(face))
    for face in ('top', 'side', 'bottom'):
        R.block(f'stonecutter2_{face}', lambda v, face=face: stonecutter(face, v2=True))
    R.anim('stonecutter2_saw', lambda f, n: saw(f, n), 3, cutout=True)

    for kind, faces in (('furnace', ('front_off', 'front_on', 'side', 'top')),
                        ('smoker', ('front_off', 'side', 'top', 'bottom')),
                        ('blast', ('front_off', 'side', 'top'))):
        for face in faces:
            p = {'furnace': 'furnace_', 'smoker': 'smoker_', 'blast': 'blast_furnace_'}[kind] + face
            R.block(p, lambda v, kind=kind, face=face: furnace_family(kind, face, 4100))
    R.anim('smoker_front_on', lambda f, n: furnace_family('smoker', 'front_on', 4100, f, n), 3)
    R.anim('blast_furnace_front_on', lambda f, n: furnace_family('blast', 'front_on', 4100, f, n), 2)
    R.block('dispenser_front_horizontal', lambda v: dispenser_front(4105, 'dispenser_front_horizontal'))
    R.block('dispenser_front_vertical', lambda v: dispenser_front(4105, 'dispenser_front_vertical', vertical=True))
    R.block('dropper_front_horizontal', lambda v: dispenser_front(4106, 'dropper_front_horizontal', dropper=True))
    R.block('dropper_front_vertical', lambda v: dispenser_front(4106, 'dropper_front_vertical', True, True))
    for face in ('front', 'back', 'back_lit', 'side', 'top'):
        R.block(f'observer_{face}', lambda v, face=face: observer(face))
    for face in ('side', 'bottom', 'inner', 'top_normal', 'top_sticky'):
        R.block(f'piston_{face}', lambda v, face=face: piston(face))
    R.block('redstone_lamp_off', lambda v: lamp(False))
    R.block('redstone_lamp_on', lambda v: lamp(True))
    R.block('target_side', lambda v: target('side'))
    R.block('target_top', lambda v: target('top'))
    R.block('lodestone_side', lambda v: lodestone('side'))
    R.block('lodestone_top', lambda v: lodestone('top'))
    R.block('respawn_anchor_bottom', lambda v: anchor('bottom'))
    R.block('respawn_anchor_top_off', lambda v: anchor('top_off'))
    R.anim('respawn_anchor_top', lambda f, n: anchor('top', frame_i=f, frames=n), 32)
    for c in range(5):
        R.block(f'respawn_anchor_side{c}', lambda v, c=c: anchor('side', charge=c))
    for face in ('top', 'side', 'bottom'):
        R.block(f'enchanting_table_{face}', lambda v, face=face: enchanting(face))
    for face in ('top', 'side', 'eye'):
        R.block(f'endframe_{face}', lambda v, face=face: endframe(face), cutout=face == 'eye')
    R.block('beacon', lambda v: beacon())
    for face in ('top', 'inverted', 'side'):
        p = {'top': 'daylight_detector_top', 'inverted': 'daylight_detector_inverted_top',
             'side': 'daylight_detector_side'}[face]
        R.block(p, lambda v, face=face: daylight(face))
    for face in ('side', 'top', 'bottom'):
        R.block(f'tnt_{face}', lambda v, face=face: tnt(face))

    fire_cols = [(0, '#c2420c'), (0.6, '#ffb03a'), (1, '#fff2c0')]
    R.block('torch_on', lambda v: torch('torch_on', fire_cols), cutout=True)
    R.block('soul_torch', lambda v: torch('soul_torch', [(0, '#1a8a9a'), (0.6, '#6ae6f0'), (1, '#e8ffff')]),
            cutout=True)
    R.block('redstone_torch_on', lambda v: torch('redstone_torch_on', [(0, '#8a0a0a'), (0.6, '#ff2a1a'),
                                                                       (1, '#ffb0a0')]), cutout=True)
    R.block('redstone_torch_off', lambda v: masked_part('redstone_torch_off', np.where(
        (Y < 8.0)[..., None], hexrgb('#4a1410'), wood_rgb(4301))), cutout=True)
    R.anim('lantern', lambda f, n: lantern(f, n, 'lantern'), 3, cutout=True)
    R.anim('soul_lantern', lambda f, n: lantern(f, n, 'soul_lantern', glow='#6ae6f0'), 3, cutout=True)
    R.block('end_rod', lambda v: masked_part('end_rod', np.where((Y < 8.0)[..., None], hexrgb('#b8a8c8'),
                                                                hexrgb('#f6f2ee')),
                                             emissive_mask=(Y >= 8.0).astype(F32), glow='#ffffff'), cutout=True)
    R.block('lever', lambda v: masked_part('lever', wood_rgb(4302)), cutout=True)
    for kind in ('normal', 'turned', 'golden', 'detector', 'activator'):
        R.block(f'rail_{kind}' if kind != 'turned' else 'rail_normal_turned',
                lambda v, kind=kind: rail(kind), cutout=True)
        if kind in ('golden', 'detector', 'activator'):
            R.block(f'rail_{kind}_powered', lambda v, kind=kind: rail(kind, True), cutout=True)
    R.block('ladder', lambda v: ladder(), cutout=True)
    for face in ('side', 'top', 'bottom'):
        R.block(f'scaffolding_{face}', lambda v, face=face: scaffold(face), cutout=True)
    R.block('iron_bars', lambda v: bars('iron_bars'), cutout=True)
    for p in ('chain1', 'chain2'):
        R.block(p, lambda v, p=p: masked_part(p, iron(4351, 0.3, 'y')[0]), cutout=True)
    R.block('redstone_dust_line', lambda v: dust('redstone_dust_line'), cutout=True)
    R.block('redstone_dust_cross', lambda v: dust('redstone_dust_cross', cross=True), cutout=True)
    for p in ('trip_wire', 'trip_wire_source', 'flower_pot', 'bamboo_fence', 'bamboo_fence_gate'):
        mat = {'trip_wire': np.full((N, N, 3), 0.8, F32), 'flower_pot': None, 'trip_wire_source': None}.get(p)
        if p == 'flower_pot':
            mat = ramp(np.clip(0.5 + 0.3 * fbm(N, 10, 4360, 3), 0, 1), [(0, '#6a2e1e'), (1, '#b45a3a')])
        elif p == 'trip_wire_source':
            mat = wood_rgb(4361)
        elif p.startswith('bamboo'):
            mat = ramp(np.clip(0.55 + 0.12 * fbm(N, (2, 12), 4362, 2), 0, 1), [(0, '#a8902a'), (1, '#ecd472')])
        R.block(p, lambda v, p=p, mat=mat: masked_part(p, mat, light='top'), cutout=True)
    R.block('door_iron_lower', lambda v: iron_door('lower'))
    R.block('door_iron_upper', lambda v: iron_door('upper'), cutout=True)
    R.block('iron_trapdoor', lambda v: iron_trapdoor(), cutout=True)


def iron_door(half, seed=4370):
    path = 'door_iron_' + half
    rgb, h = iron(seed, 0.62, streak='y')
    fr = frame(1.6)
    h = h * 0.6 + 0.35 * fr
    rv = sum(circle(x, y, 0.4) for x in (0.9, 15.1) for y in (0.9, 5.3, 10.7, 15.1))
    rgb, h = put(rgb, h, np.clip(rv, 0, 1), rgb * 1.2, 0.95)
    alpha = None
    if half == 'upper':
        win = rect(3.6, 3.6, 12.4, 10.0)
        barsm = np.zeros((N, N), F32)
        for k in range(3):
            barsm = np.maximum(barsm, rect(5.2 + k * 2.8, 3.6, 5.9 + k * 2.8, 10.0))
        alpha = np.clip(1 - win + barsm, 0, 1)
        h = np.maximum(h, barsm * 0.8)
    else:
        handle = rect(12.4, 1.0, 13.4, 4.4)
        rgb, h = put(rgb, h, handle, rgb * 0.7, 0.9)
        plate = rect(3.0, 5.0, 13.0, 12.0)
        h = h - 0.15 * plate
    return tex(rgb, h, path, alpha=alpha, gloss=0.25)


def iron_trapdoor(seed=4371):
    path = 'iron_trapdoor'
    rgb, h = iron(seed, 0.62)
    fr = frame(1.6)
    h = h * 0.6 + 0.35 * fr
    holes = np.zeros((N, N), F32)
    for (cx, cy) in ((5.0, 5.0), (11.0, 5.0), (5.0, 11.0), (11.0, 11.0)):
        holes = np.maximum(holes, rect(cx - 1.6, cy - 1.6, cx + 1.6, cy + 1.6))
    return tex(rgb, h, path, alpha=1 - holes, gloss=0.25)
