#!/usr/bin/env python3
"""Build the Terra Lucida resource pack.

Renders every registered texture at the master resolution, filters it down to the 32x / 64x / 128x
tiers (64x in the pack root, the others as subpacks), writes the JSON definitions and the manifest,
and packages dist/*.mcpack. Output is deterministic.

Usage:  python3 tools/build.py [--only SUBSTRING] [--no-dist] [--jobs N]
"""
import argparse
import json
import multiprocessing as mp
import os
import shutil
import sys
import time

import numpy as np

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

from engine.material import tiers, to_uint8, save_image  # noqa: E402
from registry import Registry  # noqa: E402
import recipes  # noqa: E402

PACK_DIR = os.path.join(ROOT, 'build', 'terra_lucida')
DIST = os.path.join(ROOT, 'dist')
VERSION = '1.0.0'
ROOT_RES = 64
SUBPACK_RES = {'lite': 32, 'ultra': 128}
# Terrain atlas (padding, num_mip_levels). Padding must be at least 2^(levels-1) texels. The root keeps vanilla's
# 8 / 4, which every tier can afford; the 64x tier adds a fifth level (mips down to 2 px, so distant terrain
# shimmers less) and fits a 4096 x 4096 atlas. Lite and ultra inherit the root file: a fifth level would double
# lite's atlas memory and push ultra past 8192 x 4096.
ATLAS = {'root': (8, 4), 'balanced': (16, 5)}

R = None


def collect():
    reg = Registry()
    recipes.register_all(reg)
    return reg


def _write_tiered(out, texs):
    """texs: list of Tex (one per frame)."""
    labels = tuple((lab, res * out.scale) for lab, res in (('root', ROOT_RES),) + tuple(SUBPACK_RES.items()))
    rendered = [tiers(t, [res for _, res in labels], cutout=out.cutout) for t in texs]
    t0 = texs[0]
    for label, res in labels:
        frames = [r[res] for r in rendered]
        img = np.concatenate(frames, axis=0) if len(frames) > 1 else frames[0]
        base = PACK_DIR if label == 'root' else os.path.join(PACK_DIR, 'subpacks', label)
        opaque = (t0.alpha is None and t0.tint_mask is None and out.ext == 'png' and out.opaque is not False)
        save_image(to_uint8(img), os.path.join(base, out.path), out.ext, opaque=opaque)


def render_one(i):
    out = R.outputs[i]
    t = time.time()
    if out.kind == 'fixed':
        rgba = out.fn()
        save_image(to_uint8(rgba), os.path.join(PACK_DIR, out.path), out.ext, opaque=out.opaque)
    elif out.frames > 1:
        texs = [out.fn(f, out.frames) for f in range(out.frames)]
        _write_tiered(out, texs)
    else:
        res = out.fn(out.variant)
        _write_tiered(out, [res])
    return out.path, time.time() - t


def write_json(rel, data):
    path = os.path.join(PACK_DIR, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')


def write_definitions(reg):
    if reg.variations:
        td = {}
        for key, entries in sorted(reg.variations.items()):
            td[key] = {'textures': {'variations': [{'path': p, 'weight': w} for p, w in entries]}}
        for label, (padding, mips) in sorted(ATLAS.items()):
            base = '' if label == 'root' else f'subpacks/{label}/'
            write_json(base + 'textures/terrain_texture.json', {
                'resource_pack_name': 'terra_lucida',
                'texture_name': 'atlas.terrain',
                'padding': padding,
                'num_mip_levels': mips,
                'texture_data': td,
            })
    if reg.blocks:
        blocks = {'format_version': '1.21.40'}
        blocks.update({k: reg.blocks[k] for k in sorted(reg.blocks)})
        write_json('blocks.json', blocks)
    for rel, data in sorted(reg.json_files.items()):
        write_json(rel, data)


def main():
    global R
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--only', help='render only outputs whose path contains this substring')
    ap.add_argument('--no-dist', action='store_true')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 2)
    args = ap.parse_args()
    t0 = time.time()
    R = collect()
    if not args.only and os.path.isdir(PACK_DIR):
        shutil.rmtree(PACK_DIR)
    idx = [i for i, o in enumerate(R.outputs) if not args.only or args.only in o.path]
    print(f'[build] {len(idx)} textures ({len(R.outputs)} registered), {args.jobs} jobs')
    ctx = mp.get_context('fork')
    slow = []
    with ctx.Pool(args.jobs) as pool:
        for path, dt in pool.imap_unordered(render_one, idx, chunksize=1):
            if dt > 4:
                slow.append((round(dt, 1), path))
    if slow:
        print('[build] slowest:', sorted(slow, reverse=True)[:5])
    write_definitions(R)
    import packaging_ as pk
    pk.write_pack_meta(PACK_DIR, VERSION)
    if not args.only:
        from icon import render_icon
        render_icon(PACK_DIR, os.path.join(PACK_DIR, 'pack_icon.png'))
    if not args.no_dist and not args.only:
        pk.package(PACK_DIR, DIST, VERSION)
    print(f'[build] done in {time.time() - t0:.0f}s')


if __name__ == '__main__':
    main()
