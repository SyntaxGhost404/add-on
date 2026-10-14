#!/usr/bin/env python3
"""Validate the built Terra Lucida pack (build/terra_lucida) without starting the game.

  manifest     format 3 shape, UUIDs, versions, subpack folders and memory tiers, language keys. With
               --samples (a Mojang bedrock-samples checkout) the manifest is also checked against Mojang's
               packaging 3.0.0 JSON schema.
  textures     every registered output in every tier: vanilla file type; size (16 x scale x tier, times the
               vanilla frame count); 8-bit RGB(A); vanilla's alpha class (opaque stays opaque, cutouts stay
               binary); textures the game tints stay grey; no stray files.
  definitions  terrain_texture.json variations resolve in every tier; blocks.json only uses known blocks and
               texture keys; fog and client-biome files keep vanilla's file names and identifiers, so they
               override rather than add; fog distances and colours are sane. With --samples, client biomes are
               also checked against Mojang's schema for their format version.
  budget       terrain atlas per tier (first frames plus padding) against the atlas each tier targets.

Exit status 1 on any error.

Usage:  python3 tools/validate.py [--samples DIR]
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import uuid
import zipfile

import numpy as np
from PIL import Image

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)

import build  # noqa: E402
import recipes  # noqa: E402
from registry import DATA, INVENTORY, TERRAIN_KEYS, VANILLA_BLOCKS, Registry  # noqa: E402

PACK = build.PACK_DIR
TIERS = {'root': build.ROOT_RES, **build.SUBPACK_RES}
# Atlas each tier should fit (width, height). The terrain atlas holds one frame of every block texture.
ATLAS_TARGET = {'lite': (2048, 2048), 'root': (4096, 4096), 'balanced': (4096, 4096), 'ultra': (8192, 4096)}
HEX = re.compile(r'^#[0-9a-fA-F]{6}$')
SEMVER = re.compile(r'^(0|[1-9]\d{0,4})\.(0|[1-9]\d{0,4})\.(0|[1-9]\d{0,4})$')

B = 'textures/blocks/'
# Textures the game colours itself (biome, age, power, sky or glint colour) or multiplies over blocks (break
# cracks). Vanilla draws them (near) grey; a coloured version would be coloured twice.
TINTED = {B + p for p in (
    'grass_top', 'grass_side', 'tallgrass', 'fern', 'double_plant_grass_top', 'double_plant_grass_bottom',
    'double_plant_fern_top', 'double_plant_fern_bottom', 'bush', 'leaf_litter', 'vine', 'waterlily',
    'leaves_oak', 'leaves_oak_opaque', 'leaves_spruce', 'leaves_spruce_opaque', 'leaves_birch',
    'leaves_birch_opaque', 'leaves_jungle', 'leaves_jungle_opaque', 'leaves_acacia', 'leaves_acacia_opaque',
    'leaves_big_oak', 'leaves_big_oak_opaque', 'mangrove_leaves', 'mangrove_leaves_opaque',
    'melon_stem_connected', 'melon_stem_disconnected', 'pumpkin_stem_connected', 'pumpkin_stem_disconnected',
    'pink_petals_stem', 'wildflowers_stem', 'redstone_dust_cross', 'redstone_dust_line', 'water_still_grey',
    'water_flow_grey', 'cauldron_water')}
TINTED |= {'textures/environment/clouds', 'textures/environment/end_sky', 'textures/misc/enchanted_item_glint',
           'textures/misc/enchanted_actor_glint', 'textures/particle/biome_tinted_leaves_atlas',
           'textures/particle/pale_oak_leaves_atlas'}
TINTED |= {f'textures/environment/destroy_stage_{k}' for k in range(10)}

ERRORS, WARNINGS = [], []


def err(msg):
    ERRORS.append(msg)


def warn(msg):
    WARNINGS.append(msg)


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def tier_dir(label):
    return PACK if label == 'root' else os.path.join(PACK, 'subpacks', label)


def rel(path):
    return os.path.relpath(path, PACK).replace(os.sep, '/')


# ---------------------------------------------------------------------------- manifest
def check_manifest():
    m = load(os.path.join(PACK, 'manifest.json'))
    if m.get('format_version') != 3:
        err('manifest: format_version must be 3 (subpacks with memory_performance_tier)')
    h = m.get('header', {})
    lang = {}
    with open(os.path.join(PACK, 'texts', 'en_US.lang'), encoding='utf-8') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.rstrip('\n').split('=', 1)
                lang[k] = v
    for key in ('name', 'description'):
        if h.get(key) not in lang:
            err(f'manifest: header.{key} {h.get(key)!r} has no entry in texts/en_US.lang')
    if 'en_US' not in load(os.path.join(PACK, 'texts', 'languages.json')):
        err('texts/languages.json does not list en_US')
    uuids = [h.get('uuid')] + [mod.get('uuid') for mod in m.get('modules', [])]
    for u in uuids:
        try:
            uuid.UUID(str(u))
        except ValueError:
            err(f'manifest: bad uuid {u!r}')
    if len(set(uuids)) != len(uuids):
        err('manifest: header and module uuids must differ')
    for where, v in [('header.version', h.get('version'))] + [
            (f'modules[{i}].version', mod.get('version')) for i, mod in enumerate(m.get('modules', []))]:
        if not isinstance(v, str) or not SEMVER.match(v):
            err(f'manifest: {where} must be a "major.minor.patch" string in format 3, got {v!r}')
    mev = h.get('min_engine_version')
    if not isinstance(mev, str) or not SEMVER.match(mev) or tuple(map(int, mev.split('.'))) > (1, 26, 52):
        err(f'manifest: min_engine_version {mev!r} must be a version string no newer than 1.26.52')
    if [mod.get('type') for mod in m.get('modules', [])] != ['resources']:
        err('manifest: expected exactly one "resources" module')
    subs = m.get('subpacks', [])
    tiers = []
    for s in subs:
        extra = set(s) - {'folder_name', 'name', 'memory_performance_tier'}
        if extra:
            err(f'manifest: subpack {s.get("folder_name")} has keys format 3 does not define: {sorted(extra)}')
        t = s.get('memory_performance_tier')
        if not isinstance(t, int) or isinstance(t, bool) or not 0 <= t <= 5:
            err(f'manifest: subpack {s.get("folder_name")} memory_performance_tier must be an integer 0-5')
        tiers.append(t)
        if not s.get('name'):
            err(f'manifest: subpack {s.get("folder_name")} needs a name')
        folder = os.path.join(PACK, 'subpacks', str(s.get('folder_name')))
        if not os.path.isdir(folder) or not os.listdir(folder):
            err(f'manifest: subpack folder {rel(folder)} is missing or empty')
    if tiers != sorted(tiers) or len(set(tiers)) != len(tiers):
        err('manifest: subpack memory tiers should rise strictly from the lightest subpack to the heaviest')
    if len({s.get('folder_name') for s in subs}) != len(subs):
        err('manifest: duplicate subpack folder_name')
    icon = os.path.join(PACK, 'pack_icon.png')
    if not os.path.exists(icon):
        err('pack_icon.png missing')
    else:
        with Image.open(icon) as im:
            if im.size[0] != im.size[1] or im.size[0] > 512:
                err(f'pack_icon.png should be square and at most 512 px, got {im.size}')
    return m


# ---------------------------------------------------------------------------- textures
def variant_bases(R):
    """tl/ variant path -> the vanilla path whose terrain key it shares."""
    out = {}
    for entries in R.variations.values():
        base = entries[0][0]
        for p, _ in entries[1:]:
            out[p] = base
    return out


def check_image(path, size, inv, tinted):
    """size: expected (w, h). inv: vanilla inventory entry for alpha class (None for no constraint)."""
    with Image.open(path) as im:
        if im.size != size:
            err(f'{rel(path)}: size {im.size}, expected {size}')
            return
        if im.mode not in ('RGB', 'RGBA'):
            err(f'{rel(path)}: mode {im.mode}; use 8-bit RGB or RGBA')
            return
        a = np.asarray(im.convert('RGBA'))
    alpha = a[..., 3]
    if inv is not None:
        if inv['alpha'] == 'none' and alpha.min() < 255:
            err(f'{rel(path)}: vanilla is opaque but this has transparent pixels')
        if inv['alpha'] == 'binary' and not np.isin(alpha, (0, 255)).all():
            err(f'{rel(path)}: vanilla alpha is cut-out (0/255) but this has partial alpha')
    vis = alpha > 0
    if not vis.any():
        err(f'{rel(path)}: fully transparent')
        return
    if tinted:
        rgb = a[..., :3][vis].astype(np.float32) / 255
        chroma = rgb.max(1) - rgb.min(1)
        if chroma.mean() > 0.02 or np.percentile(chroma, 99) > 0.08:
            err(f'{rel(path)}: the game tints this texture, so it must be grey '
                f'(mean chroma {chroma.mean():.3f})')


def check_textures(R):
    bases = variant_bases(R)
    expected = set()
    for out in R.outputs:
        if out.kind == 'fixed':
            f = os.path.join(PACK, f'{out.path}.{out.ext}')
            expected.add(f)
            if not os.path.exists(f):
                err(f'missing {rel(f)}')
                continue
            check_image(f, out.size, INVENTORY.get(out.path), out.path in TINTED)
            continue
        base = bases.get(out.path, out.path)
        inv = INVENTORY.get(base)
        if inv is None:
            err(f'{out.path}: not a vanilla texture path and not a variant of one')
            continue
        if out.path == base and out.ext != inv['ext']:
            err(f'{out.path}: written as .{out.ext}, vanilla is .{inv["ext"]}')
        if bases.get(out.path) and inv['ext'] == 'tga':
            warn(f'{out.path}: PNG variant of a TGA texture; fine unless the TGA alpha is a tint mask')
        frames = inv['frames'] if out.path == base else 1
        if out.frames != frames:
            err(f'{out.path}: {out.frames} frames, vanilla flipbook has {frames}')
        for label, res in TIERS.items():
            f = os.path.join(tier_dir(label), f'{out.path}.{out.ext}')
            expected.add(f)
            if not os.path.exists(f):
                err(f'missing {rel(f)}')
                continue
            w = res * out.scale
            check_image(f, (w, w * out.frames), inv, base in TINTED)
    images = set()
    for root, _, files in os.walk(PACK):
        for name in files:
            if name.endswith(('.png', '.tga')) and name != 'pack_icon.png':
                images.add(os.path.join(root, name))
    for f in sorted(images - expected):
        err(f'stray image not produced by any recipe: {rel(f)}')
    return len(expected)


# ---------------------------------------------------------------------------- definitions
def check_terrain_texture(R):
    out = {}
    for label in TIERS:
        p = os.path.join(tier_dir(label), 'textures', 'terrain_texture.json')
        if not os.path.exists(p):
            continue
        d = load(p)
        pad, mips = d.get('padding'), d.get('num_mip_levels')
        if d.get('texture_name') != 'atlas.terrain':
            err(f'{rel(p)}: texture_name must be atlas.terrain')
        if not (isinstance(pad, int) and isinstance(mips, int) and 1 <= mips <= 8 and pad >= 2 ** (mips - 1)):
            err(f'{rel(p)}: padding {pad} is below 2^(num_mip_levels-1) for {mips} levels')
        for key, entry in d.get('texture_data', {}).items():
            variations = entry.get('textures', {}).get('variations')
            if not variations:
                err(f'{rel(p)}: {key} has no variations')
                continue
            if not key.startswith('tl_') and TERRAIN_KEYS.get(key, {}).get('textures') != variations[0]['path']:
                err(f'{rel(p)}: {key} is a vanilla key; its first variation must be its own texture')
            for v in variations:
                if not isinstance(v.get('weight'), int) or v['weight'] < 1:
                    err(f'{rel(p)}: {key} has a non-positive or non-integer weight')
                for tl, res in TIERS.items():
                    hit = [e for e in ('png', 'tga') if os.path.exists(os.path.join(tier_dir(tl), f'{v["path"]}.{e}'))]
                    if not hit:
                        err(f'{rel(p)}: {key} variation {v["path"]} missing in tier {tl}')
        out[label] = (pad, mips, set(d.get('texture_data', {})))
    if 'root' not in out:
        err('textures/terrain_texture.json missing')
    return out


def check_blocks(R, atlas_keys):
    p = os.path.join(PACK, 'blocks.json')
    d = load(p)
    if d.get('format_version') != '1.21.40':
        err('blocks.json: format_version should match vanilla (1.21.40)')
    known = set(TERRAIN_KEYS) | atlas_keys
    for name, entry in d.items():
        if name == 'format_version':
            continue
        if name not in VANILLA_BLOCKS:
            err(f'blocks.json: {name} is not a vanilla block')
            continue
        for field in ('textures', 'carried_textures'):
            t = entry.get(field)
            for k in ([t] if isinstance(t, str) else list(t.values()) if isinstance(t, dict) else []):
                if k not in known:
                    err(f'blocks.json: {name}.{field} uses unknown texture key {k}')
        iso = entry.get('isotropic')
        if iso is not None and not isinstance(iso, bool) and not (
                isinstance(iso, dict) and all(isinstance(v, bool) for v in iso.values())):
            err(f'blocks.json: {name}.isotropic must be a boolean or a per-face map of booleans')
        ao = entry.get('ambient_occlusion_exponent')
        if ao is not None and not (isinstance(ao, (int, float)) and 0.0 <= ao <= 3.0):
            err(f'blocks.json: {name}.ambient_occlusion_exponent {ao} out of range 0-3')
        lost = set(VANILLA_BLOCKS[name]) - set(entry)
        if lost:
            err(f'blocks.json: {name} drops vanilla fields {sorted(lost)} (entries replace, they do not merge)')
    return len(d) - 1


def _fog_ranges(node, where):
    if isinstance(node, dict):
        if 'fog_start' in node and 'fog_end' in node:
            s, e, kind = node['fog_start'], node['fog_end'], node.get('render_distance_type')
            if kind not in ('render', 'fixed'):
                err(f'{where}: render_distance_type {kind!r}')
            if not 0 <= s < e or (kind == 'render' and e > 1.5):
                err(f'{where}: fog_start {s} / fog_end {e} out of order or range for {kind}')
            if not HEX.match(str(node.get('fog_color', ''))):
                err(f'{where}: fog_color {node.get("fog_color")!r} is not #rrggbb')
        for k, v in node.items():
            _fog_ranges(v, f'{where}.{k}')


def check_fogs_and_biomes(samples):
    vfogs = load(os.path.join(DATA, 'vanilla_fogs.json'))
    vbiomes = load(os.path.join(DATA, 'vanilla_client_biomes.json'))
    nfog = nbio = 0
    for name in sorted(os.listdir(os.path.join(PACK, 'fogs'))):
        d = load(os.path.join(PACK, 'fogs', name))
        nfog += 1
        if name not in vfogs:
            err(f'fogs/{name}: no vanilla file of that name; it would add a fog instead of overriding one')
            continue
        ident = d['minecraft:fog_settings']['description']['identifier']
        if ident != vfogs[name]['minecraft:fog_settings']['description']['identifier']:
            err(f'fogs/{name}: identifier {ident} differs from vanilla')
        _fog_ranges(d['minecraft:fog_settings'].get('distance', {}), f'fogs/{name}')
    validator = None
    if samples:
        validator = _biome_validator(samples)
    for name in sorted(os.listdir(os.path.join(PACK, 'biomes'))):
        d = load(os.path.join(PACK, 'biomes', name))
        nbio += 1
        if name not in vbiomes:
            err(f'biomes/{name}: no vanilla file of that name')
            continue
        body = d['minecraft:client_biome']
        if body['description']['identifier'] != vbiomes[name]['minecraft:client_biome']['description']['identifier']:
            err(f'biomes/{name}: identifier differs from vanilla')
        comps = body.get('components', {})
        lost = set(vbiomes[name]['minecraft:client_biome'].get('components', {})) - set(comps)
        if lost:
            err(f'biomes/{name}: drops vanilla components {sorted(lost)}')
        wa = comps.get('minecraft:water_appearance', {})
        if 'surface_opacity' in wa and not 0 <= wa['surface_opacity'] <= 1:
            err(f'biomes/{name}: surface_opacity out of 0-1')
        for c in (wa.get('surface_color'), comps.get('minecraft:sky_color', {}).get('sky_color')):
            if c is not None and not HEX.match(str(c)):
                err(f'biomes/{name}: colour {c!r} is not #rrggbb')
        fog_id = comps.get('minecraft:fog_appearance', {}).get('fog_identifier')
        if fog_id and not any(f['minecraft:fog_settings']['description']['identifier'] == fog_id
                              for f in vfogs.values()):
            err(f'biomes/{name}: fog_identifier {fog_id} is not a vanilla fog')
        if validator is not None:
            v = validator(d.get('format_version'))
            for e in (v.iter_errors(d) if v else []):
                err(f'biomes/{name}: schema: {e.message[:200]}')
    return nfog, nbio


def _schema_registry(samples):
    from referencing import Registry as RefRegistry, Resource
    base = os.path.join(samples, 'metadata', 'json_schemas')

    def retrieve(uri):
        path = urllib.parse.unquote(urllib.parse.urlparse(uri).path).lstrip('/')
        with open(os.path.join(base, path), encoding='utf-8') as f:
            return Resource.from_contents(json.load(f))
    return base, RefRegistry(retrieve=retrieve)


def _biome_validator(samples):
    from jsonschema import Draft7Validator
    base, registry = _schema_registry(samples)
    cache = {}

    def get(version):
        if version not in cache:
            p = os.path.join(base, 'client', 'biome', str(version), 'Client Biome Document.json')
            cache[version] = Draft7Validator(load(p), registry=registry) if os.path.exists(p) else None
            if cache[version] is None:
                warn(f'no Mojang client-biome schema for format_version {version}')
        return cache[version]
    return get


def check_manifest_schema(samples, m):
    from jsonschema import Draft7Validator
    base, registry = _schema_registry(samples)
    schema = load(os.path.join(base, 'client_server', 'packaging', '3.0.0', 'Manifest.json'))
    for e in Draft7Validator(schema, registry=registry).iter_errors(m):
        err(f'manifest: schema {"/".join(map(str, e.absolute_path))}: {e.message[:200]}')


# ---------------------------------------------------------------------------- budget
def atlas_paths(R):
    paths = set()
    for v in TERRAIN_KEYS.values():
        t = v.get('textures')
        items = [t] if isinstance(t, (str, dict)) else t if isinstance(t, list) else []
        for x in items:
            paths.add(x if isinstance(x, str) else x.get('path'))
    paths |= {p for entries in R.variations.values() for p, _ in entries}
    paths.discard(None)
    return paths


def check_budget(R, atlas):
    ours = {o.path: o for o in R.outputs if o.kind == 'tiered'}
    paths = atlas_paths(R)
    report = []
    for label, (tw, th) in ATLAS_TARGET.items():
        src = 'root' if label == 'balanced' else label
        res = TIERS[src]
        pad, mips, _ = atlas.get(label, atlas['root'])
        area = 0
        for p in paths:
            s = res * ours[p].scale if p in ours else INVENTORY.get(p, {}).get('w', 16)
            area += (s + 2 * pad) ** 2
        fill = area / (tw * th)
        report.append(f'{label} {res}x pad {pad} mips {mips}: {area / 1e6:.1f} MP = {fill:.0%} of {tw}x{th}')
        if fill > 0.85:
            err(f'terrain atlas for {label} is {fill:.0%} of {tw}x{th}; the game would shrink textures to fit')
    return report


def check_package(version):
    out = os.path.join(build.DIST, f'Terra_Lucida_v{version}.mcpack')
    if not os.path.exists(out):
        warn(f'{os.path.relpath(out, os.path.dirname(build.DIST))} not built (run build.py without --no-dist)')
        return None
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
    on_disk = set()
    for root, _, files in os.walk(PACK):
        for name in files:
            on_disk.add(rel(os.path.join(root, name)))
    if names != on_disk:
        err(f'{os.path.basename(out)} is stale: {len(names ^ on_disk)} entries differ from {rel(PACK)}')
    if 'manifest.json' not in names:
        err(f'{os.path.basename(out)}: manifest.json must sit at the archive root')
    return os.path.getsize(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--samples', default=os.environ.get('BEDROCK_SAMPLES'),
                    help='Mojang bedrock-samples checkout for schema checks (or set BEDROCK_SAMPLES)')
    args = ap.parse_args()
    if not os.path.isdir(PACK):
        sys.exit(f'{PACK} not found: run tools/build.py first')
    R = Registry()
    recipes.register_all(R)
    m = check_manifest()
    samples = args.samples if args.samples and os.path.isdir(args.samples) else None
    if samples:
        try:
            check_manifest_schema(samples, m)
        except ImportError:
            warn('jsonschema/referencing not installed: schema checks skipped')
            samples = None
    else:
        warn('no --samples: Mojang schema checks skipped')
    n_img = check_textures(R)
    atlas = check_terrain_texture(R)
    n_blocks = check_blocks(R, set().union(*(keys for _, _, keys in atlas.values())))
    n_fog, n_bio = check_fogs_and_biomes(samples)
    budget = check_budget(R, atlas)
    size = check_package(m['header']['version'])
    print(f'[validate] {n_img} images, {n_blocks} blocks.json entries, {n_fog} fogs, {n_bio} client biomes')
    for line in budget:
        print(f'[validate] atlas {line}')
    if size:
        print(f'[validate] package {size / 1e6:.1f} MB')
    for w in WARNINGS:
        print(f'[warn] {w}')
    for e in ERRORS:
        print(f'[error] {e}')
    print(f'[validate] {len(ERRORS)} errors, {len(WARNINGS)} warnings')
    sys.exit(1 if ERRORS else 0)


if __name__ == '__main__':
    main()
