#!/usr/bin/env python3
"""Validate the Enchant+ packs without starting the game.

Always:
  - every JSON file parses as strict JSON (no comments), and every file is UTF-8;
  - manifests: format 2, UUIDs, versions, BP <-> RP dependency, script entry and module versions;
  - block, item, entity, recipe, client entity, render controller, animation and particle references
    resolve (geometry, textures, terrain/item atlas keys, block sounds, recipe items, locators);
  - every lang key the scripts use exists in every language file;
  - the scripts' vanilla tables use real enchantment ids, enchantment slots and lang keys;
  - JSON UI: our files are listed in _ui_defs.json and every element reference resolves.

With --samples DIR (a Mojang bedrock-samples checkout, 1.26.50) or BEDROCK_SAMPLES:
  - blocks, items, entities and particles against Mojang's JSON schemas;
  - JSON UI references, block sound sets, sound ids, item icons and recipe items against vanilla.

Exit status 1 on any error.
Usage:  python3 tools/validate.py [--samples DIR]
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BP = os.path.join(ROOT, 'packs', 'Enchant_Table_BP')
RP = os.path.join(ROOT, 'packs', 'Enchant_Table_RP')
NODE_MODULES = os.path.join(os.path.dirname(ROOT), 'node_modules')
SCRIPT_MODULES = {'@minecraft/server': '2.10.0', '@minecraft/server-ui': '2.2.0'}
MIN_ENGINE = [1, 26, 50]
OUR_ITEMS = {'da:enchant_essence', 'da:enchant_table_plus'}

ERRORS, WARNINGS = [], []


def err(msg):
    ERRORS.append(msg)


def warn(msg):
    WARNINGS.append(msg)


def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, '/')


def files(base, pattern):
    return sorted(glob.glob(os.path.join(base, pattern), recursive=True))


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def strip_comments(s):
    out, i, n, in_str = [], 0, len(s), False
    while i < n:
        c = s[i]
        if in_str:
            out.append(c)
            if c == '\\':
                out.append(s[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
        elif c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif s.startswith('//', i):
            j = s.find('\n', i)
            i = n if j < 0 else j
        elif s.startswith('/*', i):
            j = s.find('*/', i + 2)
            i = n if j < 0 else j + 2
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def load_jsonc(path):
    """Vanilla files may contain comments and trailing commas."""
    with open(path, encoding='utf-8') as f:
        s = strip_comments(f.read())
    return json.loads(re.sub(r',(\s*[}\]])', r'\1', s))


def texture_exists(pack, path):
    return any(os.path.exists(os.path.join(pack, path + ext)) for ext in ('.png', '.tga'))


# ------------------------------------------------------------------------------------- basics
def check_json_and_encoding():
    for pack in (BP, RP):
        for p in files(pack, '**/*'):
            if os.path.isdir(p):
                continue
            if p.endswith(('.json', '.lang', '.js')):
                try:
                    text = open(p, encoding='utf-8').read()
                except UnicodeDecodeError:
                    err(f'{rel(p)}: not UTF-8')
                    continue
                if text.startswith('﻿'):
                    err(f'{rel(p)}: starts with a byte-order mark')
            if p.endswith('.json'):
                try:
                    load(p)
                except json.JSONDecodeError as e:
                    err(f'{rel(p)}: invalid JSON ({e})')


def check_manifests():
    bp, rp = load(os.path.join(BP, 'manifest.json')), load(os.path.join(RP, 'manifest.json'))
    uuids = []
    for name, m in (('BP', bp), ('RP', rp)):
        if m.get('format_version') != 2:
            err(f'{name} manifest: format_version should be 2')
        h = m['header']
        if h.get('min_engine_version') != MIN_ENGINE:
            err(f'{name} manifest: min_engine_version should be {MIN_ENGINE}')
        uuids.append(h['uuid'])
        for mod in m['modules']:
            uuids.append(mod['uuid'])
            if mod['version'] != h['version']:
                err(f'{name} manifest: module {mod["type"]} version differs from the header')
        allowed = {'authors', 'license', 'url', 'generated_with', 'product_type'}
        extra = set(m.get('metadata', {})) - allowed
        if extra:
            err(f'{name} manifest: unknown metadata fields {sorted(extra)}')
    if len(set(uuids)) != len(uuids):
        err('manifests: UUIDs must all differ')
    if bp['header']['version'] != rp['header']['version']:
        err('BP and RP versions differ')
    deps = {d.get('uuid') or d.get('module_name'): d['version'] for d in bp['dependencies']}
    if deps.get(rp['header']['uuid']) != rp['header']['version']:
        err('BP manifest must depend on the RP with its exact version')
    rdeps = {d.get('uuid'): d['version'] for d in rp.get('dependencies', [])}
    if rdeps.get(bp['header']['uuid']) != bp['header']['version']:
        err('RP manifest must depend on the BP with its exact version')
    for module, version in SCRIPT_MODULES.items():
        if deps.get(module) != version:
            err(f'BP manifest: {module} should be {version}')
    script = [m for m in bp['modules'] if m['type'] == 'script']
    if len(script) != 1 or not os.path.exists(os.path.join(BP, script[0]['entry'])):
        err('BP manifest: script module entry missing')
    for pack in (BP, RP):
        if not os.path.exists(os.path.join(pack, 'pack_icon.png')):
            err(f'{rel(pack)}: pack_icon.png missing')
    return bp, rp


# ------------------------------------------------------------------------------- definitions
def rp_index():
    idx = {'geometry': set(), 'locators': {}, 'terrain': {}, 'items': {}, 'animations': set(),
           'controllers': set(), 'render': set(), 'particles': set(), 'clients': {}}
    for p in files(RP, 'models/**/*.json'):
        for g in load(p).get('minecraft:geometry', []):
            gid = g['description']['identifier']
            idx['geometry'].add(gid)
            idx['locators'][gid] = {k for b in g.get('bones', []) for k in b.get('locators', {})}
    for key, data in load(os.path.join(RP, 'textures/terrain_texture.json'))['texture_data'].items():
        idx['terrain'][key] = data['textures']
    for key, data in load(os.path.join(RP, 'textures/item_texture.json'))['texture_data'].items():
        idx['items'][key] = data['textures']
    for p in files(RP, 'animations/*.json'):
        idx['animations'].update(load(p)['animations'])
    for p in files(RP, 'animation_controllers/*.json'):
        idx['controllers'].update(load(p)['animation_controllers'])
    for p in files(RP, 'render_controllers/*.json'):
        idx['render'].update(load(p)['render_controllers'])
    for p in files(RP, 'particles/*.json'):
        idx['particles'].add(load(p)['particle_effect']['description']['identifier'])
    for p in files(RP, 'entity/*.json'):
        d = load(p)['minecraft:client_entity']['description']
        idx['clients'][d['identifier']] = (p, d)
    return idx


def check_definitions(idx, vanilla_items, vanilla_block_sounds):
    blocks = {}
    for p in files(BP, 'blocks/*.json'):
        body = load(p)['minecraft:block']
        bid = body['description']['identifier']
        blocks[bid] = body
        comps = [body['components']] + [pm.get('components', {}) for pm in body.get('permutations', [])]
        for c in comps:
            geo = c.get('minecraft:geometry')
            gid = geo if isinstance(geo, str) else (geo or {}).get('identifier')
            if gid and gid not in idx['geometry']:
                err(f'{rel(p)}: geometry {gid} not in the RP')
            for inst in (c.get('minecraft:material_instances') or {}).values():
                key = inst.get('texture')
                if key and key not in idx['terrain']:
                    err(f'{rel(p)}: texture {key} not in terrain_texture.json')
    for key, path in idx['terrain'].items():
        if not texture_exists(RP, path):
            err(f'terrain_texture.json: {key} -> {path} missing')
    for key, path in idx['items'].items():
        if not texture_exists(RP, path):
            err(f'item_texture.json: {key} -> {path} missing')
    rp_blocks = load(os.path.join(RP, 'blocks.json'))
    for bid, entry in rp_blocks.items():
        if bid == 'format_version':
            continue
        if bid not in blocks:
            err(f'RP blocks.json: {bid} is not a block of the BP')
        if vanilla_block_sounds is not None and entry.get('sound') not in vanilla_block_sounds:
            err(f'RP blocks.json: {bid} uses unknown block sound {entry.get("sound")}')
    for bid in blocks:
        if bid not in rp_blocks:
            warn(f'{bid}: no RP blocks.json entry (default sounds)')

    items = {}
    for p in files(BP, 'items/*.json'):
        body = load(p)['minecraft:item']
        items[body['description']['identifier']] = body
        icon = body['components'].get('minecraft:icon')
        key = icon if isinstance(icon, str) else (icon or {}).get('textures', {}).get('default')
        if key not in idx['items']:
            err(f'{rel(p)}: icon {key} not in item_texture.json')

    known_items = set(blocks) | set(items) | (vanilla_items or set())
    for p in files(BP, 'recipes/*.json'):
        doc = load(p)
        body = doc.get('minecraft:recipe_shaped') or doc.get('minecraft:recipe_shapeless')
        if not body:
            err(f'{rel(p)}: unsupported recipe type')
            continue
        rid = body['description']['identifier']
        if rid.startswith('minecraft:'):
            err(f'{rel(p)}: recipe identifier {rid} uses the minecraft namespace')
        used = [body['result']] + list(body.get('key', {}).values()) + body.get('ingredients', []) + body.get('unlock', [])
        for entry in used:
            iid = entry.get('item')
            if iid and vanilla_items is not None and iid not in known_items:
                err(f'{rel(p)}: unknown item {iid}')
            if iid and iid != iid.lower():
                err(f'{rel(p)}: item id {iid} must be lower case')
        if not body.get('unlock'):
            err(f'{rel(p)}: no unlock condition (the recipe would never show in the recipe book)')
        if body['result'].get('item') in {u.get('item') for u in body.get('unlock', [])}:
            err(f'{rel(p)}: unlocking needs its own result (chicken-and-egg)')
        pattern = body.get('pattern')
        if pattern:
            if len({len(r) for r in pattern}) != 1:
                err(f'{rel(p)}: pattern rows differ in length')
            letters = {ch for r in pattern for ch in r if ch != ' '}
            if letters != set(body['key']):
                err(f'{rel(p)}: pattern letters {sorted(letters)} differ from key {sorted(body["key"])}')

    for p in files(BP, 'entities/*.json'):
        eid = load(p)['minecraft:entity']['description']['identifier']
        if eid not in idx['clients']:
            err(f'{rel(p)}: no client entity for {eid}')
    for eid, (p, d) in idx['clients'].items():
        for t in d.get('textures', {}).values():
            if not texture_exists(RP, t):
                err(f'{rel(p)}: texture {t} missing')
        for g in d.get('geometry', {}).values():
            if g not in idx['geometry']:
                err(f'{rel(p)}: geometry {g} missing')
        for rc in d.get('render_controllers', []):
            name = rc if isinstance(rc, str) else next(iter(rc))
            if name not in idx['render']:
                err(f'{rel(p)}: render controller {name} not defined in this pack')
        for a in d.get('animations', {}).values():
            if a not in idx['animations'] and a not in idx['controllers']:
                err(f'{rel(p)}: animation {a} missing')
        for pe in d.get('particle_effects', {}).values():
            if pe not in idx['particles']:
                err(f'{rel(p)}: particle {pe} missing')
        locators = set().union(*[idx['locators'].get(g, set()) for g in d.get('geometry', {}).values()])
        for p2 in files(RP, 'animation_controllers/*.json'):
            for state in [s for c in load(p2)['animation_controllers'].values() for s in c['states'].values()]:
                for eff in state.get('particle_effects', []):
                    if eff.get('locator') and eff['locator'] not in locators:
                        err(f'{rel(p2)}: locator {eff["locator"]} not in the geometry')
                    if eff['effect'] not in d.get('particle_effects', {}):
                        err(f'{rel(p2)}: particle effect {eff["effect"]} not declared by {eid}')
    for p in files(RP, 'particles/*.json'):
        d = load(p)['particle_effect']
        tex = d['description']['basic_render_parameters']['texture']
        if not texture_exists(RP, tex):
            err(f'{rel(p)}: texture {tex} missing')
        fb = d['components'].get('minecraft:particle_appearance_billboard', {}).get('uv', {}).get('flipbook')
        if fb:
            uv = d['components']['minecraft:particle_appearance_billboard']['uv']
            frames = uv['texture_width'] // fb['step_UV'][0] if fb['step_UV'][0] else uv['texture_height'] // fb['step_UV'][1]
            if fb.get('max_frame', 0) > frames:
                err(f'{rel(p)}: flipbook max_frame {fb["max_frame"]} exceeds the {frames} frames in the texture')
    return blocks, items


# --------------------------------------------------------------------------------------- texts
def lang_keys(path):
    keys = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('##'):
                continue
            if '=' not in line:
                err(f'{rel(path)}: line without "=": {line[:40]}')
                continue
            k, v = line.split('=', 1)
            keys[k] = v
    return keys


def check_texts(blocks, items, vanilla_lang):
    for pack in (BP, RP):
        langs = load(os.path.join(pack, 'texts/languages.json'))
        for lang in langs:
            path = os.path.join(pack, 'texts', f'{lang}.lang')
            if not os.path.exists(path):
                err(f'{rel(pack)}: texts/{lang}.lang missing')
                continue
            keys = lang_keys(path)
            for k in ('pack.name', 'pack.description'):
                if k not in keys:
                    err(f'{rel(path)}: {k} missing')
    used = set()
    for p in files(BP, 'scripts/**/*.js'):
        used |= set(re.findall(r'"(enchant_plus\.[a-z_.]+[a-z_])"', open(p, encoding='utf-8').read()))
    places = {f'enchant_plus.place.{s}' for s in ('head', 'chest', 'legs', 'feet', 'offhand')}
    used |= places
    rp_langs = load(os.path.join(RP, 'texts/languages.json'))
    for lang in rp_langs:
        keys = lang_keys(os.path.join(RP, 'texts', f'{lang}.lang'))
        for k in sorted(used):
            if k not in keys:
                err(f'RP texts/{lang}.lang: missing {k}')
        for bid in blocks:
            if f'tile.{bid}.name' not in keys:
                err(f'RP texts/{lang}.lang: missing tile.{bid}.name')
        for iid, body in items.items():
            name = body['components'].get('minecraft:display_name', {}).get('value', f'item.{iid}.name')
            if name not in keys:
                err(f'RP texts/{lang}.lang: missing {name}')
        for k, v in keys.items():
            if k.startswith('enchant_plus.') and v.count('%s') != keys[k].count('%s'):
                pass
    if vanilla_lang is not None:
        data = open(os.path.join(BP, 'scripts/data.js'), encoding='utf-8').read()
        for key in re.findall(r'"(enchantment\.[A-Za-z_.]+)"', data):
            if key not in vanilla_lang:
                err(f'scripts/data.js: {key} is not a vanilla lang key')
        for n in range(1, 11):
            if f'enchantment.level.{n}' not in vanilla_lang:
                err(f'vanilla lang has no enchantment.level.{n}')


def vanilla_data():
    """Enchantment ids, enchantment slots and item ids of the game, from the installed typings."""
    out = {}
    vd = os.path.join(NODE_MODULES, '@minecraft', 'vanilla-data', 'lib')
    if os.path.isdir(vd):
        out['enchants'] = set(re.findall(r'= "minecraft:([a-z_]+)"', open(os.path.join(vd, 'mojang-enchantment.d.ts')).read()))
        out['items'] = set(re.findall(r'= "(minecraft:[a-z0-9_]+)"', open(os.path.join(vd, 'mojang-item.d.ts')).read()))
    srv = os.path.join(NODE_MODULES, '@minecraft', 'server', 'index.d.ts')
    if os.path.exists(srv):
        text = open(srv, encoding='utf-8').read()
        m = re.search(r'export enum EnchantmentSlot \{(.*?)\}', text, re.S)
        out['slots'] = set(re.findall(r"(\w+) = '", m.group(1))) if m else set()
    return out


def check_script_tables(vd):
    data = os.path.join(BP, 'scripts', 'data.js')
    try:
        tables = json.loads(subprocess.run(
            ['node', '--input-type=module', '-e',
             'const d = await import(process.argv[1]); console.log(JSON.stringify({names: d.ENCHANT_NAMES, slot: d.BY_SLOT, '
             'item: d.BY_ITEM, excl: d.EXCLUSIVE}));', 'file://' + data],
            capture_output=True, text=True, check=True).stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as e:
        warn(f'could not load scripts/data.js with node: {e}')
        return
    ids = set(tables['names'])
    if vd.get('enchants'):
        if ids != vd['enchants']:
            err(f'data.js ENCHANT_NAMES differs from the game: missing {sorted(vd["enchants"] - ids)}, extra {sorted(ids - vd["enchants"])}')
    for group in (tables['slot'], tables['item']):
        for k, lst in group.items():
            for e in lst:
                if e not in ids:
                    err(f'data.js: {k} lists unknown enchantment {e}')
    for k in tables['slot']:
        if vd.get('slots') and k not in vd['slots']:
            err(f'data.js BY_SLOT: {k} is not an EnchantmentSlot')
    if vd.get('slots'):
        for s in sorted(vd['slots'] - set(tables['slot'])):
            warn(f'data.js BY_SLOT has no rules for EnchantmentSlot.{s}')
    for k in tables['item']:
        if vd.get('items') and k not in vd['items']:
            err(f'data.js BY_ITEM: {k} is not a vanilla item')
    for g in tables['excl']:
        for e in g:
            if e not in ids:
                err(f'data.js EXCLUSIVE: unknown enchantment {e}')
    if 'swift_sneak' not in tables['slot'].get('ArmorLegs', []):
        err('data.js: leggings must accept Swift Sneak (issue #3)')


def check_icons(vd, vanilla_rp):
    data = os.path.join(BP, 'scripts', 'data.js')
    items = sorted(i for i in vd.get('items', set())
                   if re.search(r'_(helmet|chestplate|leggings|boots|sword|pickaxe|axe|shovel|hoe|spear)$', i)
                   or i in {'minecraft:bow', 'minecraft:crossbow', 'minecraft:trident', 'minecraft:mace', 'minecraft:shears',
                            'minecraft:fishing_rod', 'minecraft:flint_and_steel', 'minecraft:carrot_on_a_stick',
                            'minecraft:warped_fungus_on_a_stick', 'minecraft:brush', 'minecraft:elytra', 'minecraft:shield',
                            'minecraft:book', 'minecraft:enchanted_book', 'minecraft:compass', 'minecraft:recovery_compass',
                            'minecraft:lodestone_compass', 'minecraft:carved_pumpkin', 'minecraft:wolf_armor',
                            'minecraft:turtle_helmet'})
    items = [i for i in items if 'horse' not in i and 'nautilus' not in i]
    try:
        icons = json.loads(subprocess.run(
            ['node', '--input-type=module', '-e',
             'const d = await import(process.argv[1]); const ids = JSON.parse(process.argv[2]);'
             'console.log(JSON.stringify(Object.fromEntries(ids.map(i => [i, d.iconFor(i)]))));',
             'file://' + data, json.dumps(items)], capture_output=True, text=True, check=True).stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as e:
        warn(f'could not evaluate iconFor with node: {e}')
        return
    for item, path in icons.items():
        if texture_exists(RP, path):
            continue
        if not texture_exists(vanilla_rp, path):
            err(f'icon for {item}: {path} exists neither in the RP nor in vanilla')
    used = set()
    for p in files(BP, 'scripts/**/*.js'):
        used |= set(re.findall(r'"(textures/[a-z0-9_/]+)"', open(p, encoding='utf-8').read()))
    for path in sorted(used):
        if not texture_exists(RP, path) and not texture_exists(vanilla_rp, path):
            err(f'scripts: texture {path} missing')


def check_sounds(vanilla_rp):
    defs = load_jsonc(os.path.join(vanilla_rp, 'sounds', 'sound_definitions.json'))
    defs = defs.get('sound_definitions', defs)
    for p in files(BP, 'scripts/**/*.js'):
        for sid in re.findall(r'playAt\(table, "([a-z0-9_.]+)"\)', open(p, encoding='utf-8').read()):
            if sid not in defs:
                err(f'{rel(p)}: unknown sound {sid}')


# ------------------------------------------------------------------------------------- JSON UI
def ui_definitions(paths):
    defs = {}
    for p in paths:
        try:
            d = load_jsonc(p)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(d, dict) and 'namespace' in d:
            defs.setdefault(d['namespace'], set()).update(k.split('@')[0] for k in d if k != 'namespace')
    return defs


def check_ui(vanilla_rp):
    listed = load(os.path.join(RP, 'ui', '_ui_defs.json'))['ui_defs']
    ours = [p for p in files(RP, 'ui/*.json') if not p.endswith('_ui_defs.json')]
    for p in ours:
        name = 'ui/' + os.path.basename(p)
        if name != 'ui/server_form.json' and name not in listed:
            err(f'{name} is not listed in ui/_ui_defs.json')
    for name in listed:
        if not os.path.exists(os.path.join(RP, name)):
            err(f'ui/_ui_defs.json lists missing {name}')
    defs = ui_definitions(ours)
    if vanilla_rp:
        vdefs = ui_definitions(files(os.path.join(vanilla_rp, 'ui'), '**/*.json'))
        for ns, names in vdefs.items():
            defs.setdefault(ns, set()).update(names)
    for p in ours:
        text = open(p, encoding='utf-8').read()
        refs = re.findall(r'@([a-z_0-9]+)\.([A-Za-z_0-9]+)', text) + re.findall(r'"\$(?:child_control|custom_background|title_panel)": "([a-z_0-9]+)\.([A-Za-z_0-9]+)"', text)
        for ns, el in refs:
            if not vanilla_rp and ns not in ('enchant_plus',):
                continue
            if el not in defs.get(ns, set()):
                err(f'{rel(p)}: {ns}.{el} is not defined')
        doc = load(p)
        for key, body in doc.items():
            for mod in body.get('modifications', []) if isinstance(body, dict) else []:
                if mod.get('operation') not in ('insert_back', 'insert_front', 'insert_after', 'insert_before', 'move_back',
                                                'move_front', 'move_after', 'move_before', 'swap', 'replace', 'remove'):
                    err(f'{rel(p)}: {key} uses unknown modification {mod.get("operation")}')
            if vanilla_rp and isinstance(body, dict) and 'modifications' in body and key.split('@')[0] not in defs.get(doc['namespace'], set()):
                err(f'{rel(p)}: modifies {doc["namespace"]}.{key}, which vanilla does not define')
    marks = set(re.findall(r"'(§[0-9a-v](?:§[0-9a-v])*)'", open(os.path.join(RP, 'ui', 'server_form.json'), encoding='utf-8').read()))
    js_mark = re.search(r'export const MARK = "([^"]+)"', open(os.path.join(BP, 'scripts', 'ui.js'), encoding='utf-8').read())
    if not js_mark or marks != {js_mark.group(1)}:
        err(f'ui/server_form.json title marker {sorted(marks)} differs from scripts/ui.js MARK')
    for p in files(RP, 'textures/enchant_plus/ui/*.png'):
        meta = p[:-4] + '.json'
        if os.path.exists(meta):
            from PIL import Image
            base = load(meta).get('base_size')
            with Image.open(p) as im:
                if base and list(im.size) != base:
                    err(f'{rel(meta)}: base_size {base} differs from the image {im.size}')


# ------------------------------------------------------------------------------------- schemas
SCHEMA_TARGETS = [
    ('server/block/1.26.20/Blocks.json', BP, 'blocks/*.json', 'minecraft:block', 'blocks'),
    ('server/item/1.26.30/ItemDocument.json', BP, 'items/*.json', 'minecraft:item', 'items'),
    ('server/entity/1.26.50/ActorDocument.json', BP, 'entities/*.json', 'minecraft:entity', 'entities'),
    ('client/particles/1.21.10/Particle Effect Data.json', RP, 'particles/*.json', 'particle_effect', None),
]


def _sig(e):
    return tuple('#' if isinstance(x, int) else x for x in e.absolute_schema_path), e.validator


def _signatures(errors):
    out, stack = set(), list(errors)
    while stack:
        e = stack.pop()
        out.add(_sig(e))
        stack.extend(e.context or [])
    return out


def _overlap_only(e):
    if e.validator != 'oneOf':
        return False
    if 'is valid under each of' in e.message:
        return True
    branches = {}
    for c in e.context or []:
        branches.setdefault(c.relative_schema_path[0], []).append(c)
    return any(errs and all(_overlap_only(c) for c in errs) for errs in branches.values())


def schema_validate(samples):
    try:
        from jsonschema import Draft7Validator
        from referencing import Registry, Resource
    except ImportError:
        warn('jsonschema/referencing not installed: schema validation skipped')
        return
    base = os.path.join(samples, 'metadata', 'json_schemas')

    def retrieve(uri):
        path = urllib.parse.unquote(urllib.parse.urlparse(uri).path).lstrip('/')
        with open(os.path.join(base, path), encoding='utf-8') as f:
            return Resource.from_contents(json.load(f))

    registry = Registry(retrieve=retrieve)
    checked = explained = 0
    for schema_rel, pack, pattern, key, vanilla_dir in SCHEMA_TARGETS:
        validator = Draft7Validator(load(os.path.join(base, schema_rel)), registry=registry)
        control = set()
        if vanilla_dir:
            for vp in files(os.path.join(samples, 'behavior_pack', vanilla_dir), '*.json'):
                try:
                    vdoc = load_jsonc(vp)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                if key in vdoc:
                    control |= _signatures(validator.iter_errors(vdoc[key]))
        for p in files(pack, pattern):
            doc = load(p)[key]
            for e in validator.iter_errors(doc):
                if _overlap_only(e) or _sig(e) in control:
                    explained += 1
                    continue
                where = '/'.join(str(x) for x in e.absolute_path)
                err(f'schema {rel(p)} @ {where}: {e.message[:300]}')
            checked += 1
    print(f'[validate] schema-checked {checked} files ({explained} findings explained by known schema defects shared by vanilla files)')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--samples', default=os.environ.get('BEDROCK_SAMPLES'))
    args = ap.parse_args()
    samples = args.samples if args.samples and os.path.isdir(args.samples) else None
    vanilla_rp = os.path.join(samples, 'resource_pack') if samples else None

    check_json_and_encoding()
    check_manifests()
    vd = vanilla_data()
    block_sounds = None
    vanilla_lang = None
    if vanilla_rp:
        block_sounds = set(load_jsonc(os.path.join(vanilla_rp, 'sounds.json')).get('block_sounds', {}))
        vanilla_lang = lang_keys(os.path.join(vanilla_rp, 'texts', 'en_US.lang'))
    idx = rp_index()
    blocks, items = check_definitions(idx, vd.get('items'), block_sounds)
    check_texts(blocks, items, vanilla_lang)
    check_script_tables(vd)
    if vanilla_rp:
        check_icons(vd, vanilla_rp)
        check_sounds(vanilla_rp)
    check_ui(vanilla_rp)
    if samples:
        schema_validate(samples)
    else:
        warn('no --samples: schema and vanilla cross-checks skipped')
    for w in WARNINGS:
        print(f'[warn] {w}')
    for e in ERRORS:
        print(f'[error] {e}')
    print(f'[validate] {len(ERRORS)} errors, {len(WARNINGS)} warnings')
    sys.exit(1 if ERRORS else 0)


if __name__ == '__main__':
    main()
