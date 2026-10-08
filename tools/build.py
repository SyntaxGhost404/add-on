#!/usr/bin/env python3
"""Build "Ruins of the Unnamed" from source.

Generates the behavior pack and resource pack into packs/ (JSON, textures, models,
structures, sounds, scripts) and packages them into dist/ as .mcaddon / .mcpack files.
Everything is deterministic: the same sources always produce the same packs.

Usage:  python3 tools/build.py [--no-dist]
"""
import argparse
import os
import shutil
import sys
import zipfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

from content.registry import REG, NS  # noqa: E402
from content.blocks import define_blocks  # noqa: E402
from content.items import define_items  # noqa: E402
from content.entities import define_entities  # noqa: E402
from content.client import define_client  # noqa: E402
from content.sounds import define_sounds  # noqa: E402
from content.loot import define_loot  # noqa: E402
from content.recipes import define_recipes  # noqa: E402
from content.worldgen import define_worldgen, PIECES  # noqa: E402
from art import audio, blockmodeltex, entitytex, models  # noqa: E402
from art.blocktex import BLOCK_TEXTURES  # noqa: E402
from art.itemtex import ITEM_TEXTURES  # noqa: E402
from lib.jsonw import write_json, write_text  # noqa: E402

PACK_NAME = 'Ruins of the Unnamed'
VERSION = [1, 0, 0]
MIN_ENGINE = [1, 26, 50]
SCRIPT_MODULES = [('@minecraft/server', '2.10.0'), ('@minecraft/server-ui', '2.2.0')]
UUID = {
    'bp': '4977faa4-ad5d-42a7-a799-73e696058b71',
    'bp_data': 'dacb3e48-e671-435d-8a59-fe0e498995a5',
    'bp_script': 'e10b7d1d-be92-4463-bc1a-90d0d1a92144',
    'rp': 'f63734b2-a74e-4bc0-ae04-f3a44a51932e',
    'rp_res': '717d98c4-cdb0-4286-befd-ab5ce317d1c4',
}
BP_DESC = ('Uncover the lost civilization of the Unnamed: waystones, dig sites, hushed shrines, ossuaries '
           'and the Sunken Sanctum. Archaeology, puzzles, relics and a final boss. For Bedrock 1.26.52+.')
RP_DESC = 'Textures, models, sounds and particles for Ruins of the Unnamed.'
AUTHORS = ['Ruins of the Unnamed contributors']

PACKS = os.path.join(ROOT, 'packs')
BP = os.path.join(PACKS, 'ruins_of_the_unnamed_bp')
RP = os.path.join(PACKS, 'ruins_of_the_unnamed_rp')
DIST = os.path.join(ROOT, 'dist')
SCRIPTS = os.path.join(ROOT, 'scripts')


def log(msg):
    print(f'[build] {msg}')


# ---------------------------------------------------------------------------- definitions
def define_all():
    define_blocks()          # must run first: registers custom block states for the structure builder
    define_items()
    define_entities()
    define_loot()
    define_recipes()
    define_worldgen()
    define_client()
    define_sounds()


def manifest(kind):
    if kind == 'bp':
        modules = [
            {'type': 'data', 'uuid': UUID['bp_data'], 'version': VERSION},
            {'type': 'script', 'language': 'javascript', 'uuid': UUID['bp_script'], 'version': VERSION,
             'entry': 'scripts/main.js'},
        ]
        deps = [{'uuid': UUID['rp'], 'version': VERSION}]
        deps += [{'module_name': m, 'version': v} for m, v in SCRIPT_MODULES]
        uid = UUID['bp']
    else:
        modules = [{'type': 'resources', 'uuid': UUID['rp_res'], 'version': VERSION}]
        deps = [{'uuid': UUID['bp'], 'version': VERSION}]
        uid = UUID['rp']
    return {
        'format_version': 2,
        'header': {
            'name': 'pack.name',
            'description': 'pack.description',
            'uuid': uid,
            'version': VERSION,
            'min_engine_version': MIN_ENGINE,
            'pack_scope': 'world',
        },
        'modules': modules,
        'dependencies': deps,
        'metadata': {'authors': AUTHORS, 'product_type': 'addon'},
    }


def lang_text(entries):
    lines = [f'{k}={v}' for k, v in entries.items()]
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------- writers
def write_packs():
    for path, data in REG.bp.items():
        write_json(os.path.join(BP, path), data)
    for path, data in REG.rp.items():
        write_json(os.path.join(RP, path), data)
    log(f'{len(REG.bp)} behavior files, {len(REG.rp)} resource files')

    write_json(os.path.join(BP, 'manifest.json'), manifest('bp'))
    write_json(os.path.join(RP, 'manifest.json'), manifest('rp'))

    write_text(os.path.join(BP, 'texts/en_US.lang'),
               lang_text({'pack.name': PACK_NAME, 'pack.description': BP_DESC}))
    write_json(os.path.join(BP, 'texts/languages.json'), ['en_US'])
    rp_lang = {'pack.name': f'{PACK_NAME} Resources', 'pack.description': RP_DESC}
    rp_lang.update(REG.lang)
    write_text(os.path.join(RP, 'texts/en_US.lang'), lang_text(rp_lang))
    write_json(os.path.join(RP, 'texts/languages.json'), ['en_US'])

    write_json(os.path.join(RP, 'textures/terrain_texture.json'), {
        'resource_pack_name': NS,
        'texture_name': 'atlas.terrain',
        'padding': 8,
        'num_mip_levels': 4,
        'texture_data': {k: {'textures': v} for k, v in REG.terrain_textures.items()},
    })
    write_json(os.path.join(RP, 'textures/item_texture.json'), {
        'resource_pack_name': NS,
        'texture_name': 'atlas.items',
        'texture_data': {k: {'textures': v} for k, v in REG.item_textures.items()},
    })
    blocks = {'format_version': '1.21.40'}
    for ident, snd in REG.block_sounds.items():
        blocks[ident] = {'sound': snd}
    write_json(os.path.join(RP, 'blocks.json'), blocks)


def write_models_and_textures():
    count = 0

    def save(canvas, rel):
        nonlocal count
        canvas.save(os.path.join(RP, rel + '.png'))
        count += 1

    # block geometries + their textures
    block_geo = {}
    for fn in models.BLOCK_MODELS:
        geo = fn()
        name = geo.identifier.split('.')[-1]
        block_geo[name] = geo
        write_json(os.path.join(RP, f'models/blocks/{name}.geo.json'), geo.to_json())
    model_textures = {
        'scriptorium_desk': lambda: blockmodeltex.paint_desk(block_geo['scriptorium_desk']),
        'reliquary_lesser': lambda: blockmodeltex.paint_reliquary(block_geo['reliquary'], False),
        'reliquary_grand': lambda: blockmodeltex.paint_reliquary(block_geo['reliquary'], True),
    }
    for style in range(3):
        model_textures[f'funerary_urn_{style}'] = (
            lambda s=style: blockmodeltex.paint_urn(block_geo['funerary_urn'], s))

    painters = dict(BLOCK_TEXTURES)
    painters.update(model_textures)
    prefix = 'textures/rotu/blocks/'
    for key, path in REG.terrain_textures.items():
        name = path[len(prefix):]
        if name not in painters:
            raise SystemExit(f'no painter for block texture {path}')
    for name, painter in painters.items():
        save(painter(), prefix + name)

    # items
    for key, path in REG.item_textures.items():
        name = path.split('/')[-1]
        if name not in ITEM_TEXTURES:
            raise SystemExit(f'no painter for item texture {path}')
    for name, painter in ITEM_TEXTURES.items():
        save(painter(), f'textures/rotu/items/{name}')

    # entities
    geos = {name: fn() for name, fn in models.ENTITY_MODELS.items()}
    for name, geo in geos.items():
        write_json(os.path.join(RP, f'models/entity/{name}.geo.json'), geo.to_json())
    ent = 'textures/rotu/entity/'
    for v in range(3):
        save(entitytex.paint_hushwalker(geos['hushwalker'], v), f'{ent}hushwalker_{v}')
    save(entitytex.hushwalker_eyes(geos['hushwalker']), f'{ent}hushwalker_eyes')
    save(entitytex.paint_murmur(geos['murmur']), f'{ent}murmur')
    save(entitytex.paint_sentinel(geos['graven_sentinel']), f'{ent}graven_sentinel')
    save(entitytex.sentinel_glow(geos['graven_sentinel']), f'{ent}graven_sentinel_glow')
    for phase in range(2):
        save(entitytex.paint_cantor(geos['last_cantor'], phase), f'{ent}last_cantor_{phase}')
        save(entitytex.cantor_glow(geos['last_cantor'], phase), f'{ent}last_cantor_glow_{phase}')
    save(entitytex.paint_bolt(geos['hush_bolt']), f'{ent}hush_bolt')

    # armor layers, particles, pack icons
    save(entitytex.armor_mask(), 'textures/rotu/models/armor/choristers_mask')
    save(entitytex.armor_mantle(), 'textures/rotu/models/armor/hushweave_mantle')
    save(entitytex.particle_mote(), 'textures/rotu/particle/mote')
    save(entitytex.particle_dust(), 'textures/rotu/particle/dust')
    entitytex.pack_icon('bp').save(os.path.join(BP, 'pack_icon.png'))
    entitytex.pack_icon('rp').save(os.path.join(RP, 'pack_icon.png'))
    log(f'{count} textures, {len(block_geo) + len(geos)} geometries')


def write_structures():
    for loc, builder in PIECES.items():
        builder().write(os.path.join(BP, 'structures', loc + '.mcstructure'))
    log(f'{len(PIECES)} structure pieces')


def write_sounds():
    for name, synth in audio.SOUNDS.items():
        audio.write_ogg(synth(), os.path.join(RP, 'sounds/rotu', name + '.ogg'))
    log(f'{len(audio.SOUNDS)} synthesized sounds')


def copy_scripts():
    dst = os.path.join(BP, 'scripts')
    n = 0
    for name in sorted(os.listdir(SCRIPTS)):
        if name.endswith('.js'):
            os.makedirs(dst, exist_ok=True)
            shutil.copyfile(os.path.join(SCRIPTS, name), os.path.join(dst, name))
            n += 1
    log(f'{n} scripts')


# ---------------------------------------------------------------------------- packaging
FIXED_TIME = (2026, 9, 25, 0, 0, 0)


def zip_dir(zf, src, arc_prefix):
    for base, dirs, files in os.walk(src):
        dirs.sort()
        for f in sorted(files):
            full = os.path.join(base, f)
            rel = os.path.relpath(full, src).replace(os.sep, '/')
            info = zipfile.ZipInfo(f'{arc_prefix}{rel}', date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with open(full, 'rb') as fh:
                zf.writestr(info, fh.read())


def package():
    os.makedirs(DIST, exist_ok=True)
    stem = 'Ruins_of_the_Unnamed_v' + '.'.join(map(str, VERSION))
    addon = os.path.join(DIST, stem + '.mcaddon')
    with zipfile.ZipFile(addon, 'w') as zf:
        zip_dir(zf, BP, os.path.basename(BP) + '/')
        zip_dir(zf, RP, os.path.basename(RP) + '/')
    for src, suffix in ((BP, '_BP'), (RP, '_RP')):
        with zipfile.ZipFile(os.path.join(DIST, stem + suffix + '.mcpack'), 'w') as zf:
            zip_dir(zf, src, '')
    log(f'packaged {os.path.relpath(addon, ROOT)} (+ separate .mcpack files)')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--no-dist', action='store_true', help='skip packaging into dist/')
    args = ap.parse_args()
    for d in (BP, RP):
        if os.path.isdir(d):
            shutil.rmtree(d)
    define_all()
    write_packs()
    write_models_and_textures()
    write_structures()
    write_sounds()
    copy_scripts()
    if not args.no_dist:
        if os.path.isdir(DIST):
            shutil.rmtree(DIST)
        package()


if __name__ == '__main__':
    main()
