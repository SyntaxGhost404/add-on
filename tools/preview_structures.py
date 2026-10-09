#!/usr/bin/env python3
"""Render isometric previews of the generated .mcstructure pieces (development aid).

Each piece gets one sheet with three views: the exterior, a horizontal cut at half height and a
vertical section through the middle. Jigsaw blocks are drawn orange and hidden spawn markers
magenta so their placement can be checked at a glance.

Usage:  python3 tools/preview_structures.py OUT_DIR [piece-name-filter ...]
"""
import glob
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

from lib import nbtread  # noqa: E402

BP = os.path.join(ROOT, 'packs', 'ruins_of_the_unnamed_bp')
RP = os.path.join(ROOT, 'packs', 'ruins_of_the_unnamed_rp')

VANILLA = {
    'deepslate': (80, 80, 86), 'cobbled_deepslate': (77, 77, 82), 'polished_deepslate': (72, 72, 74),
    'deepslate_tiles': (54, 54, 56), 'cracked_deepslate': (64, 64, 66), 'blackstone': (42, 36, 41),
    'polished_blackstone': (53, 48, 56), 'cracked_polished_blackstone': (44, 40, 46), 'tuff': (108, 109, 102),
    'crying_obsidian': (60, 20, 110), 'bone_block': (229, 225, 207), 'sand': (219, 207, 163), 'red_sand': (190, 102, 33),
    'sandstone': (216, 203, 155), 'cut_sandstone': (217, 206, 159), 'gravel': (131, 127, 126), 'dirt': (134, 96, 67),
    'coarse_dirt': (119, 85, 59), 'podzol': (91, 63, 24), 'moss': (89, 109, 45), 'soul_soil': (75, 57, 46),
    'hay_block': (166, 136, 38), 'spruce': (115, 85, 49), 'chest': (164, 116, 46), 'barrel': (140, 105, 60),
    'crafting_table': (120, 80, 50), 'cartography_table': (100, 80, 60), 'white': (234, 236, 236),
    'brown': (114, 71, 40), 'campfire': (220, 120, 40), 'soul_campfire': (80, 200, 210), 'lantern': (230, 180, 90),
    'soul_lantern': (90, 210, 220), 'torch': (255, 210, 90), 'candle': (230, 220, 190), 'web': (220, 220, 220),
    'iron_chain': (60, 64, 72), 'skull': (200, 200, 190), 'mob_spawner': (30, 40, 60), 'deadbush': (140, 100, 40),
}
SMALL = ('carpet', 'candle', 'torch', 'lantern', 'chain', 'web', 'skull', 'campfire', 'deadbush', 'fence', 'wall',
         'slab', 'stairs', 'funerary_urn', 'reliquary', 'scriptorium_desk', 'hushing_plate')


def texture_color(ident):
    name = ident.split(':')[1]
    for cand in (name, name + '_0', name + '_lesser', name + '_side'):
        p = os.path.join(RP, 'textures', 'rotu', 'blocks', cand + '.png')
        if os.path.isfile(p):
            a = np.asarray(Image.open(p).convert('RGBA')).reshape(-1, 4).astype(float)
            a = a[a[:, 3] > 0]
            return tuple(int(v) for v in a[:, :3].mean(axis=0)) if len(a) else (128, 128, 128)
    return (150, 150, 150)


_cache = {}


def color(ident):
    if ident in _cache:
        return _cache[ident]
    if ident == 'minecraft:jigsaw':
        c = (255, 140, 0)
    elif ident == 'rotu:spawn_marker':
        c = (255, 0, 255)
    elif ident.startswith('rotu:'):
        c = texture_color(ident)
    else:
        name = ident.split(':')[1]
        c = None
        for k in sorted(VANILLA, key=len, reverse=True):
            if k in name:
                c = VANILLA[k]
                break
        c = c or (150, 150, 150)
    _cache[ident] = c
    return c


def load(path):
    d = nbtread.plain(nbtread.load(path)[1])
    sx, sy, sz = d['size']
    idx = d['structure']['block_indices'][0]
    pal = [b['name'] for b in d['structure']['palette']['default']['block_palette']]
    vox = {}
    for x in range(sx):
        for y in range(sy):
            for z in range(sz):
                i = idx[(x * sy + y) * sz + z]
                if i >= 0 and pal[i] != 'minecraft:air':
                    vox[(x, y, z)] = pal[i]
    return (sx, sy, sz), vox


def render(size, vox, s=10, keep=lambda p: True):
    sx, sy, sz = size
    w = (sx + sz) * s + 4
    h = (sx + sz) * s // 2 + sy * s + 4
    img = Image.new('RGB', (w, h), (36, 34, 42))
    dr = ImageDraw.Draw(img)
    ox, oy = sz * s + 2, sy * s + 2
    kept = {p: b for p, b in vox.items() if keep(p)}
    for (x, y, z) in sorted(kept, key=lambda p: (p[0] + p[2] + p[1], p[1])):
        b = kept[(x, y, z)]
        small = any(k in b for k in SMALL)
        c = tuple(min(255, int(48 + v * 0.85)) for v in color(b))   # lifted for legibility
        cx = ox + (x - z) * s
        cy = oy + (x + z) * s // 2 - y * s
        k = 0.5 if small else 1.0
        hw, hh, ht = s * k, s * k / 2, s * k
        base = (cx, cy + (s - ht) if small else cy)
        bx, by = base
        top = [(bx, by - ht), (bx + hw, by - ht + hh), (bx, by - ht + 2 * hh), (bx - hw, by - ht + hh)]
        left = [(bx - hw, by - ht + hh), (bx, by - ht + 2 * hh), (bx, by + 2 * hh), (bx - hw, by + hh)]
        right = [(bx, by - ht + 2 * hh), (bx + hw, by - ht + hh), (bx + hw, by + hh), (bx, by + 2 * hh)]
        if (x, y + 1, z) not in kept or small:
            dr.polygon(top, fill=c)
        if (x, y, z + 1) not in kept or small:
            dr.polygon(left, fill=tuple(int(v * 0.78) for v in c))
        if (x + 1, y, z) not in kept or small:
            dr.polygon(right, fill=tuple(int(v * 0.62) for v in c))
    return img


def sheet(path, out_dir):
    size, vox = load(path)
    sx, sy, sz = size
    views = [
        render(size, vox),
        render(size, vox, keep=lambda p: p[1] <= max(1, sy // 2)),
        render(size, vox, keep=lambda p: p[2] <= sz // 2),
    ]
    w = sum(v.width for v in views) + 20
    h = max(v.height for v in views) + 16
    out = Image.new('RGB', (w, h), (24, 22, 28))
    x = 5
    for v in views:
        out.paste(v, (x, 12))
        x += v.width + 5
    ImageDraw.Draw(out).text((6, 0), f'{os.path.basename(path)}  {sx}x{sy}x{sz}', fill=(220, 220, 220))
    name = os.path.splitext(os.path.basename(path))[0]
    out.save(os.path.join(out_dir, name + '.png'))
    return name


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out_dir = sys.argv[1]
    filters = sys.argv[2:]
    os.makedirs(out_dir, exist_ok=True)
    for path in sorted(glob.glob(os.path.join(BP, 'structures', 'rotu', '*.mcstructure'))):
        if filters and not any(f in path for f in filters):
            continue
        print(sheet(path, out_dir))


if __name__ == '__main__':
    main()
