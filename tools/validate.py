#!/usr/bin/env python3
"""Validate the generated packs in packs/.

Always runs self-contained cross-reference checks (textures, models, loot tables, sounds,
particles, structures, jigsaw connections, lang keys, custom components, script references).

With a checkout of Mojang's bedrock-samples (https://github.com/Mojang/bedrock-samples) it also
validates JSON files against the official schemas and checks every vanilla identifier we use
(blocks + block states in structures, items, effects, biome tags, vanilla sound files).

Usage:  python3 tools/validate.py [--samples PATH_TO_BEDROCK_SAMPLES]
        (or set BEDROCK_SAMPLES)
"""
import argparse
import glob
import json
import os
import re
import sys
import urllib.parse

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

from lib.jsonc import loads as jsonc_loads  # noqa: E402
from lib import nbtread  # noqa: E402


def read_nbt(path):
    return nbtread.plain(nbtread.load(path)[1])

BP = os.path.join(ROOT, 'packs', 'ruins_of_the_unnamed_bp')
RP = os.path.join(ROOT, 'packs', 'ruins_of_the_unnamed_rp')
SCRIPTS = os.path.join(ROOT, 'scripts')

ERRORS = []
WARNINGS = []


def err(msg):
    ERRORS.append(msg)


def warn(msg):
    WARNINGS.append(msg)


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def files(base, pattern):
    return sorted(glob.glob(os.path.join(base, pattern), recursive=True))


def rel(path):
    return os.path.relpath(path, ROOT)


# ---------------------------------------------------------------------------- pack inventory
class Packs:
    def __init__(self):
        self.blocks = {}       # id -> body
        self.items = {}
        self.entities = {}
        for p in files(BP, 'blocks/*.json'):
            body = load(p)['minecraft:block']
            self.blocks[body['description']['identifier']] = body
        for p in files(BP, 'items/*.json'):
            body = load(p)['minecraft:item']
            self.items[body['description']['identifier']] = body
        for p in files(BP, 'entities/*.json'):
            body = load(p)['minecraft:entity']
            self.entities[body['description']['identifier']] = body
        self.terrain = load(os.path.join(RP, 'textures/terrain_texture.json'))['texture_data']
        self.item_tex = load(os.path.join(RP, 'textures/item_texture.json'))['texture_data']
        self.sound_defs = load(os.path.join(RP, 'sounds/sound_definitions.json'))['sound_definitions']
        self.lang = {}
        with open(os.path.join(RP, 'texts/en_US.lang'), encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                if line and not line.startswith('#'):
                    k, _, v = line.partition('=')
                    if k in self.lang:
                        err(f'lang: duplicate key {k}')
                    self.lang[k] = v
        self.geometry = set()
        for p in files(RP, 'models/**/*.geo.json'):
            for g in load(p)['minecraft:geometry']:
                self.geometry.add(g['description']['identifier'])
        self.particles = set()
        for p in files(RP, 'particles/*.json'):
            self.particles.add(load(p)['particle_effect']['description']['identifier'])
        self.animations = set()
        for p in files(RP, 'animations/*.json'):
            self.animations.update(load(p)['animations'].keys())
        self.render_controllers = set()
        for p in files(RP, 'render_controllers/*.json'):
            self.render_controllers.update(load(p)['render_controllers'].keys())
        self.loot = {os.path.relpath(p, BP).replace(os.sep, '/') for p in files(BP, 'loot_tables/**/*.json')}
        self.pools = {}
        for p in files(BP, 'worldgen/template_pools/*.json'):
            body = load(p)['minecraft:template_pool']
            self.pools[body['description']['identifier']] = body


def rp_file_exists(path_no_ext, exts=('.png', '.tga')):
    return any(os.path.isfile(os.path.join(RP, path_no_ext + e)) for e in exts)


# ---------------------------------------------------------------------------- checks
def check_build_fresh():
    """The packaged scripts must be byte-identical to scripts/ (catches a stale build)."""
    src = {os.path.basename(p) for p in files(SCRIPTS, '*.js')}
    packed = {os.path.basename(p) for p in files(os.path.join(BP, 'scripts'), '*.js')}
    for name in sorted(src ^ packed):
        err(f'scripts/{name}: present in only one of scripts/ and the packaged behavior pack (rebuild)')
    for name in sorted(src & packed):
        with open(os.path.join(SCRIPTS, name), 'rb') as a, open(os.path.join(BP, 'scripts', name), 'rb') as b:
            if a.read() != b.read():
                err(f'scripts/{name}: packaged copy is stale (run tools/build.py)')


def check_manifests():
    bp, rp = load(os.path.join(BP, 'manifest.json')), load(os.path.join(RP, 'manifest.json'))
    if not any(d.get('uuid') == rp['header']['uuid'] for d in bp.get('dependencies', [])):
        err('manifest: behavior pack does not depend on the resource pack')
    if not any(d.get('uuid') == bp['header']['uuid'] for d in rp.get('dependencies', [])):
        err('manifest: resource pack does not depend on the behavior pack')
    uuids = [bp['header']['uuid'], rp['header']['uuid']] + [m['uuid'] for m in bp['modules'] + rp['modules']]
    if len(set(uuids)) != len(uuids):
        err('manifest: duplicate UUIDs')
    entry = [m for m in bp['modules'] if m['type'] == 'script'][0]['entry']
    if not os.path.isfile(os.path.join(BP, entry)):
        err(f'manifest: script entry {entry} missing')
    for p in (BP, RP):
        if not os.path.isfile(os.path.join(p, 'pack_icon.png')):
            err(f'{rel(p)}: missing pack_icon.png')


def check_blocks(P):
    for ident, body in P.blocks.items():
        comps = [body.get('components', {})] + [pm.get('components', {}) for pm in body.get('permutations', [])]
        for c in comps:
            for inst in c.get('minecraft:material_instances', {}).values():
                if isinstance(inst, dict) and 'texture' in inst and inst['texture'] not in P.terrain:
                    err(f'block {ident}: texture key {inst["texture"]} not in terrain_texture.json')
            geo = c.get('minecraft:geometry')
            if isinstance(geo, dict):
                geo = geo.get('identifier')
            if geo and not geo.startswith('minecraft:geometry.') and geo not in P.geometry:
                err(f'block {ident}: geometry {geo} missing')
            loot = c.get('minecraft:loot')
            if loot and loot not in P.loot:
                err(f'block {ident}: loot table {loot} missing')
        if f'tile.{ident}.name' not in P.lang:
            err(f'block {ident}: no lang name')
    for key, entry in P.terrain.items():
        tex = entry['textures']
        for t in (tex if isinstance(tex, list) else [tex]):
            if not rp_file_exists(t):
                err(f'terrain texture {key}: {t}.png missing')
    blocks_json = load(os.path.join(RP, 'blocks.json'))
    for ident in P.blocks:
        if ident not in blocks_json:
            warn(f'block {ident}: no sound in blocks.json')


def check_items(P):
    for ident, body in P.items.items():
        c = body['components']
        icon = c.get('minecraft:icon', {})
        key = icon.get('textures', {}).get('default') if isinstance(icon, dict) else icon
        if key not in P.item_tex:
            err(f'item {ident}: icon {key} not in item_texture.json')
        name = c.get('minecraft:display_name', {}).get('value', f'item.{ident}.name')
        if name not in P.lang:
            err(f'item {ident}: lang key {name} missing')
    for key, entry in P.item_tex.items():
        if not rp_file_exists(entry['textures']):
            err(f'item texture {key}: file missing')


def check_entities(P):
    for p in files(RP, 'entity/*.entity.json'):
        d = load(p)['minecraft:client_entity']['description']
        ident = d['identifier']
        if ident not in P.entities:
            err(f'client entity {ident} has no behavior definition')
        for t in d.get('textures', {}).values():
            if not rp_file_exists(t):
                err(f'client entity {ident}: texture {t} missing')
        for g in d.get('geometry', {}).values():
            if g not in P.geometry:
                err(f'client entity {ident}: geometry {g} missing')
        for a in d.get('animations', {}).values():
            if a not in P.animations:
                err(f'client entity {ident}: animation {a} missing')
        for rc in d.get('render_controllers', []):
            name = rc if isinstance(rc, str) else list(rc)[0]
            if name not in P.render_controllers:
                err(f'client entity {ident}: render controller {name} missing')
        for pe in d.get('particle_effects', {}).values():
            if pe not in P.particles:
                err(f'client entity {ident}: particle {pe} missing')
    for ident, body in P.entities.items():
        loot = body.get('components', {}).get('minecraft:loot', {}).get('table')
        if loot and loot not in P.loot:
            err(f'entity {ident}: loot {loot} missing')
        if f'entity.{ident}.name' not in P.lang:
            err(f'entity {ident}: no lang name')
        events = body.get('events', {})
        groups = body.get('component_groups', {})

        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k in ('event', 'time_down_event', 'on_damage') and isinstance(v, str):
                        if v not in events and not v.startswith('minecraft:'):
                            err(f'entity {ident}: event {v} not defined')
                    if k == 'summon_event' and node.get('entity_type') in P.entities:
                        if v not in P.entities[node['entity_type']].get('events', {}):
                            err(f'entity {ident}: summon event {v} not defined on {node["entity_type"]}')
                    if k == 'component_groups' and isinstance(v, list):
                        for g in v:
                            if g not in groups:
                                err(f'entity {ident}: component group {g} not defined')
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
        walk(body)
    for p in files(RP, 'attachables/*.json'):
        d = load(p)['minecraft:attachable']['description']
        for t in d.get('textures', {}).values():
            if not t.startswith('textures/misc/') and not rp_file_exists(t):
                err(f'attachable {d["identifier"]}: texture {t} missing')
    for p in files(RP, 'particles/*.json'):
        tex = load(p)['particle_effect']['description']['basic_render_parameters']['texture']
        if not rp_file_exists(tex):
            err(f'particle {rel(p)}: texture {tex} missing')


def loot_item_names(node, out):
    if isinstance(node, dict):
        if node.get('type') == 'item' and 'name' in node:
            out.add(node['name'])
        for v in node.values():
            loot_item_names(v, out)
    elif isinstance(node, list):
        for v in node:
            loot_item_names(v, out)


def check_loot_and_recipes(P, vanilla_items):
    known = set(P.items) | set(P.blocks)
    for p in files(BP, 'loot_tables/**/*.json'):
        names = set()
        loot_item_names(load(p), names)
        for n in names:
            if n not in known and (vanilla_items is not None and n not in vanilla_items):
                err(f'{rel(p)}: unknown item {n}')
    for p in files(BP, 'recipes/*.json'):
        d = load(p)
        body = list(v for k, v in d.items() if k != 'format_version')[0]
        refs = []
        for v in body.get('key', {}).values():
            refs.append(v.get('item'))
        for v in body.get('ingredients', []):
            refs.append(v.get('item'))
        if 'input' in body:
            refs.append(body['input'] if isinstance(body['input'], str) else body['input'].get('item'))
        res = body.get('result') or body.get('output')
        refs.append(res if isinstance(res, str) else res.get('item'))
        for r in refs:
            if r and r not in known and vanilla_items is not None and r not in vanilla_items:
                err(f'{rel(p)}: unknown item {r}')


def check_sounds(P, vanilla_sound_files):
    for name, d in P.sound_defs.items():
        for s in d['sounds']:
            path = s['name'] if isinstance(s, dict) else s
            if path.startswith('sounds/rotu/'):
                if not os.path.isfile(os.path.join(RP, path + '.ogg')):
                    err(f'sound {name}: {path}.ogg missing')
            elif vanilla_sound_files is not None and path not in vanilla_sound_files:
                err(f'sound {name}: vanilla file {path} unknown')
    sounds_json = load(os.path.join(RP, 'sounds.json'))
    for ent, d in sounds_json['entity_sounds']['entities'].items():
        for ev, v in d['events'].items():
            snd = v if isinstance(v, str) else v['sound']
            if snd not in P.sound_defs:
                err(f'sounds.json {ent}.{ev}: {snd} not defined')


def check_structures(P, vanilla_blocks):
    """Template pools -> structure files; jigsaw names/targets/pools; palette block states."""
    struct_dir = os.path.join(BP, 'structures')
    processors = {load(p)['minecraft:processor_list']['description']['identifier']
                  for p in files(BP, 'worldgen/processors/*.json')}
    names_by_pool = {}
    jigsaws_by_file = {}
    for pid, body in P.pools.items():
        if body.get('fallback') and body['fallback'] not in P.pools:
            err(f'pool {pid}: fallback {body["fallback"]} missing')
        names_by_pool[pid] = set()
        for el in body['elements']:
            e = el['element']
            path = os.path.join(struct_dir, e['location'] + '.mcstructure')
            if not os.path.isfile(path):
                err(f'pool {pid}: structure {e["location"]} missing')
                continue
            if e.get('processors') and e['processors'] not in processors:
                err(f'pool {pid}: processors {e["processors"]} missing')
            if path not in jigsaws_by_file:
                jigsaws_by_file[path] = inspect_structure(path, P, vanilla_blocks)
            for j in jigsaws_by_file[path]:
                names_by_pool[pid].add(j['name'])
    for path, jigs in jigsaws_by_file.items():
        for j in jigs:
            pool = j['target_pool']
            if pool in ('', 'minecraft:empty'):
                continue
            if pool not in P.pools:
                err(f'{rel(path)}: jigsaw targets unknown pool {pool}')
            elif j['target'] not in names_by_pool[pool]:
                err(f'{rel(path)}: jigsaw target {j["target"]} has no matching jigsaw name in {pool}')
    for p in files(BP, 'worldgen/structures/*.json'):
        body = load(p)['minecraft:jigsaw']
        if body['start_pool'] not in P.pools:
            err(f'{rel(p)}: start pool {body["start_pool"]} missing')
    structures = {load(p)['minecraft:jigsaw']['description']['identifier'] for p in files(BP, 'worldgen/structures/*.json')}
    for p in files(BP, 'worldgen/structure_sets/*.json'):
        for s in load(p)['minecraft:structure_set']['structures']:
            if s['structure'] not in structures:
                err(f'{rel(p)}: structure {s["structure"]} missing')
    seen_files = set(jigsaws_by_file)
    for path in files(struct_dir, '**/*.mcstructure'):
        if path not in seen_files:
            warn(f'{rel(path)}: not used by any template pool')


def inspect_structure(path, P, vanilla_blocks):
    root = read_nbt(path)
    st = root['structure']
    palette = st['palette']['default']
    blocks = palette['block_palette']
    for b in blocks:
        name = b['name']
        states = b.get('states', {})
        if name.startswith('rotu:'):
            body = P.blocks.get(name)
            if body is None:
                err(f'{rel(path)}: unknown block {name}')
                continue
            allowed = dict(body['description'].get('states', {}))
            for trait, cfg in body['description'].get('traits', {}).items():
                for s in cfg.get('enabled_states', []):
                    allowed[s] = None
            for s, v in states.items():
                if s not in allowed:
                    err(f'{rel(path)}: {name} has unknown state {s}')
                elif allowed[s] is not None and v not in allowed[s] and int(v) not in [int(x) for x in allowed[s]]:
                    err(f'{rel(path)}: {name} state {s}={v} not allowed')
        elif vanilla_blocks is not None:
            props = vanilla_blocks.get(name)
            if props is None:
                err(f'{rel(path)}: unknown vanilla block {name}')
                continue
            if set(states) != props:
                err(f'{rel(path)}: {name} states {sorted(states)} != {sorted(props)}')
    jigs = []
    for pos, data in palette.get('block_position_data', {}).items():
        be = data.get('block_entity_data', {})
        if be.get('id') == 'JigsawBlock':
            jigs.append({'name': be['name'], 'target': be['target'], 'target_pool': be['target_pool']})
        loot = be.get('LootTable')
        if loot and loot not in P.loot:
            err(f'{rel(path)}: container loot table {loot} missing')
        spawner = be.get('EntityIdentifier')
        if spawner and spawner.startswith('rotu:') and spawner not in P.entities:
            err(f'{rel(path)}: spawner entity {spawner} unknown')
    return jigs


def check_scripts(P, vanilla_effects):
    src = ''
    for p in files(SCRIPTS, '*.js'):
        with open(p, encoding='utf-8') as f:
            src += f.read() + '\n'
    registered = set(re.findall(r'registerCustomComponent\("([^"]+)"', src))
    used = set()
    for body in list(P.blocks.values()) + list(P.items.values()):
        comps = [body.get('components', {})] + [pm.get('components', {}) for pm in body.get('permutations', [])]
        for c in comps:
            used.update(k for k in c if not k.startswith('minecraft:'))
    for c in sorted(used - registered):
        err(f'custom component {c} used in JSON but never registered')
    for c in sorted(registered - used):
        warn(f'custom component {c} registered but unused')
    for snd in set(re.findall(r'"(rotu\.[a-z_.]+)"', src)):
        if snd not in P.sound_defs:
            err(f'script sound {snd} not defined')
    for part in set(re.findall(r'"(rotu:[a-z_]+)"', src)):
        pass  # identifiers are checked by category below
    for pe in set(re.findall(r'particle\([^,]+,\s*"([a-z_:]+)"', src)):
        if pe not in P.particles:
            err(f'script particle {pe} missing')
    for ent in set(re.findall(r'spawnEntity\("([a-z_:]+)"', src)) | set(re.findall(r'type: "([a-z_:]+)"', src)):
        if ent not in P.entities:
            err(f'script entity {ent} unknown')
    for ev in set(re.findall(r'spawnEvent: "([a-z_:]+)"', src)) | set(re.findall(r'eventTypes: \["([a-z_:]+)"', src)):
        if not any(ev in body.get('events', {}) for body in P.entities.values()):
            err(f'script entity event {ev} not defined')
    for item in set(re.findall(r'"(rotu:[a-z_]+)"', src)):
        known = set(P.items) | set(P.blocks) | set(P.entities) | {
            'rotu:progress', 'rotu:home', 'rotu:starcall', 'rotu:temporary', 'rotu:enter_phase_two', 'rotu:awaken'}
        state_names = {s for body in P.blocks.values() for s in body['description'].get('states', {})}
        state_names |= {t for body in P.blocks.values() for t in body['components'].get('minecraft:tags', [])}
        if item not in known and item not in state_names and item not in P.particles and item not in registered:
            err(f'script reference {item} unknown')
    for tex in set(re.findall(r'"(textures/[a-z_/]+)"', src)):
        if not rp_file_exists(tex) and not tex.startswith('textures/items/'):
            err(f'script icon {tex} missing')
    if vanilla_effects is not None:
        for eff in set(re.findall(r'(?:addEffect|getEffect|removeEffect)\("([a-z_]+)"', src)):
            if f'minecraft:{eff}' not in vanilla_effects:
                err(f'script effect {eff} unknown')
    for tbl in set(re.findall(r'table: "([a-z_/]+)"', src)):
        if f'loot_tables/{tbl}.json' not in P.loot:
            err(f'script loot table {tbl} missing')
    for m in re.findall(r'unlockChapter\(\w+, (\d+)\)', src):
        if not 1 <= int(m) <= 12:
            err(f'chapter {m} out of range')


def check_lang_coverage(P):
    for ident, body in P.entities.items():
        if body['description'].get('is_spawnable') and f'item.spawn_egg.entity.{ident}.name' not in P.lang:
            err(f'entity {ident}: spawn egg name missing')


def check_biome_tags(vanilla_tags):
    for p in files(BP, 'worldgen/structures/*.json'):
        text = json.dumps(load(p)['minecraft:jigsaw'].get('biome_filters', []))
        for tag in set(re.findall(r'"value": "([a-z_]+)"', text)):
            if tag not in vanilla_tags:
                err(f'{rel(p)}: biome tag {tag} is not used by any vanilla biome')
    for p in files(BP, 'spawn_rules/*.json'):
        text = json.dumps(load(p))
        for tag in set(re.findall(r'"value": "([a-z_]+)"', text)):
            if tag not in vanilla_tags:
                err(f'{rel(p)}: biome tag {tag} unknown')


# ---------------------------------------------------------------------------- schemas
# Mojang's generated JSON schemas have known defects: several `oneOf` lists contain overlapping
# alternatives (e.g. "Filter Group Map" has no required keys, so every filter matches two branches),
# spawn-rule conditions require `weight` instead of `minecraft:weight`, and custom block states only
# list string arrays although the engine also accepts integer and boolean arrays. Mojang's own vanilla
# files fail these schemas in exactly the same places. A schema finding is therefore reported only if
# it is NOT explained by (1) overlapping oneOf branches, (2) an identical failure on vanilla files, or
# (3) the documented integer/boolean custom block state form (checked separately below).
SCHEMA_TARGETS = [
    ('server/block/1.26.20/Blocks.json', 'blocks/*.json', 'minecraft:block', 'blocks'),
    ('server/item/1.26.30/ItemDocument.json', 'items/*.json', 'minecraft:item', 'items'),
    ('server/entity/1.26.50/ActorDocument.json', 'entities/*.json', 'minecraft:entity', 'entities'),
    ('client_server/spawn/1.21.60/Spawn Rules.json', 'spawn_rules/*.json', 'minecraft:spawn_rules', 'spawn_rules'),
    ('client_server/world/1.21.20/JigsawStructure.json', 'worldgen/structures/*.json', 'minecraft:jigsaw', None),
    ('client_server/world/1.21.20/Structure Set.json', 'worldgen/structure_sets/*.json', 'minecraft:structure_set', None),
    ('client_server/world/1.21.20/Processor List.json', 'worldgen/processors/*.json', 'minecraft:processor_list', None),
    ('server/world/1.21.20/Template Pool.json', 'worldgen/template_pools/*.json', 'minecraft:template_pool', None),
    ('client/particles/1.21.10/Particle Effect Data.json', 'RP:particles/*.json', 'particle_effect', None),
]


def _sig(e):
    return tuple('#' if isinstance(x, int) else x for x in e.absolute_schema_path), e.validator


def _signatures(errors):
    out = set()
    stack = list(errors)
    while stack:
        e = stack.pop()
        out.add(_sig(e))
        stack.extend(e.context or [])
    return out


def _overlap_only(e):
    """True when a oneOf failure only happens because the value matches several (overlapping) branches."""
    if e.validator != 'oneOf':
        return False
    if 'is valid under each of' in e.message:
        return True
    branches = {}
    for c in e.context or []:
        branches.setdefault(c.relative_schema_path[0], []).append(c)
    return any(errs and all(_overlap_only(c) for c in errs) for errs in branches.values())


def _custom_state_form(e, doc):
    path = list(e.absolute_path)
    if len(path) != 3 or path[:2] != ['description', 'states']:
        return False
    values = doc['description']['states'][path[2]]
    return (isinstance(values, list) and 1 <= len(values) <= 16 and len(set(map(repr, values))) == len(values)
            and (all(isinstance(v, bool) for v in values)
                 or all(isinstance(v, int) and not isinstance(v, bool) for v in values)))


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
    checked = artifacts = 0
    for schema_rel, pattern, key, vanilla_dir in SCHEMA_TARGETS:
        with open(os.path.join(base, schema_rel), encoding='utf-8') as f:
            validator = Draft7Validator(json.load(f), registry=registry)
        control = set()
        if vanilla_dir:
            for vp in files(os.path.join(samples, 'behavior_pack', vanilla_dir), '*.json'):
                with open(vp, encoding='utf-8') as f:
                    vdoc = jsonc_loads(f.read())
                if key in vdoc:
                    control |= _signatures(validator.iter_errors(vdoc[key]))
        pack, pattern = (RP, pattern[3:]) if pattern.startswith('RP:') else (BP, pattern)
        for p in files(pack, pattern):
            doc = load(p)[key]
            for e in validator.iter_errors(doc):
                if _overlap_only(e) or _sig(e) in control or (key == 'minecraft:block' and _custom_state_form(e, doc)):
                    artifacts += 1
                    continue
                where = '/'.join(str(x) for x in e.absolute_path)
                err(f'schema {rel(p)} @ {where}: {e.message[:300]}')
            checked += 1
    for manifest in (os.path.join(BP, 'manifest.json'), os.path.join(RP, 'manifest.json')):
        if load(manifest).get('format_version') != 2:
            err(f'{rel(manifest)}: expected manifest format_version 2')
    print(f'[validate] schema-checked {checked} files '
          f'({artifacts} findings explained by known schema defects that vanilla files share)')


COMPONENT_SCHEMAS = {
    'minecraft:entity': ('server/entity/1.26.50/Entity component definitions.json', 'entities'),
    'minecraft:block': ('server/block/1.26.20/Components.json', 'blocks'),
    'minecraft:item': ('server/item/1.26.30/Item Components.json', 'items'),
}


def _component_keys(body):
    keys = set(body.get('components', {}))
    for group in body.get('component_groups', {}).values():
        keys.update(group)
    for perm in body.get('permutations', []):
        keys.update(perm.get('components', {}))
    return keys


def check_component_names(samples):
    """Unknown component names are ignored by the game, so a typo would silently do nothing."""
    base = os.path.join(samples, 'metadata', 'json_schemas')
    for root, (schema_rel, folder) in COMPONENT_SCHEMAS.items():
        known = set(load(os.path.join(base, schema_rel)).get('properties', {}))
        for vp in files(os.path.join(samples, 'behavior_pack', folder), '*.json'):
            with open(vp, encoding='utf-8') as f:
                vdoc = jsonc_loads(f.read())
            if root in vdoc:
                known |= _component_keys(vdoc[root])
        for p in files(BP, f'{folder}/*.json'):
            for k in sorted(_component_keys(load(p)[root])):
                if k.startswith('minecraft:') and k not in known:
                    err(f'{rel(p)}: unknown component {k}')


def check_molang_names(samples):
    """Every query.* / q.* / math.* name in both packs must exist in Mojang's Molang registry."""
    d = load(os.path.join(samples, 'metadata', 'molang_modules', 'mojang-molang-queries.json'))
    known = {e['name'] if e['name'].startswith('query.') else 'query.' + e['name'] for e in d['queries']}
    known |= {e['name'] if e['name'].startswith('math.') else 'math.' + e['name'] for e in d['math_functions']}
    for p in files(BP, '**/*.json') + files(RP, '**/*.json'):
        with open(p, encoding='utf-8') as f:
            text = f.read()
        for prefix, name in set(re.findall(r'\b(q|query|math)\.([a-z_0-9]+)', text)):
            full = ('math.' if prefix == 'math' else 'query.') + name
            if full not in known:
                err(f'{rel(p)}: unknown Molang name {full}')


def check_block_states(P):
    """Custom block states: at most 16 unique values of one type, permutations only reference real states."""
    for ident, body in P.blocks.items():
        states = body['description'].get('states', {})
        traits = body['description'].get('traits', {})
        names = set(states) | {s for t in traits.values() for s in t.get('enabled_states', [])}
        for name, values in states.items():
            if not isinstance(values, list) or not 1 <= len(values) <= 16 or len(set(map(repr, values))) != len(values):
                err(f'block {ident}: state {name} must list 1-16 unique values')
            elif len({type(v) for v in values}) != 1:
                err(f'block {ident}: state {name} mixes value types')
        for pm in body.get('permutations', []):
            for ref in re.findall(r"block_state\('([^']+)'\)", pm['condition']):
                if ref not in names:
                    err(f'block {ident}: permutation references unknown state {ref}')


# Listed in Mojang's item id table (doc_modules/addons.json, id 522) but absent from mojang-items.json.
EXTRA_VANILLA_ITEMS = {'minecraft:written_book'}


def vanilla_data(samples):
    vd = os.path.join(samples, 'metadata', 'vanilladata_modules')
    blocks = {}
    for b in load(os.path.join(vd, 'mojang-blocks.json'))['data_items']:
        blocks[b['name']] = {p['name'] for p in b.get('properties', [])}
    items = {i['name'] for i in load(os.path.join(vd, 'mojang-items.json'))['data_items']}
    items |= set(blocks)
    items |= EXTRA_VANILLA_ITEMS
    effects = {e['name'] for e in load(os.path.join(vd, 'mojang-effects.json'))['data_items']}
    with open(os.path.join(samples, 'resource_pack', 'sounds', 'sound_definitions.json'), encoding='utf-8') as f:
        defs = jsonc_loads(f.read())['sound_definitions']
    sound_files = set()
    for d in defs.values():
        for s in d.get('sounds', []):
            sound_files.add(s['name'] if isinstance(s, dict) else s)
    tags = set()
    for p in files(os.path.join(samples, 'behavior_pack', 'biomes'), '*.json'):
        with open(p, encoding='utf-8') as f:
            d = jsonc_loads(f.read())
        comps = d['minecraft:biome'].get('components', {})
        tags.update(comps.get('minecraft:tags', {}).get('tags', []))
    return blocks, items, effects, sound_files, tags


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--samples', default=os.environ.get('BEDROCK_SAMPLES'),
                    help='path to a Mojang/bedrock-samples checkout (enables schema + vanilla checks)')
    args = ap.parse_args()
    if not os.path.isdir(BP) or not os.path.isdir(RP):
        sys.exit('packs/ not built yet: run python3 tools/build.py first')

    P = Packs()
    vblocks = vitems = veffects = vsounds = vtags = None
    if args.samples:
        vblocks, vitems, veffects, vsounds, vtags = vanilla_data(args.samples)
        schema_validate(args.samples)
        check_component_names(args.samples)
        check_molang_names(args.samples)
        check_biome_tags(vtags)
    else:
        warn('no --samples given: schema and vanilla-identifier checks skipped')

    check_build_fresh()
    check_manifests()
    check_blocks(P)
    check_block_states(P)
    check_items(P)
    check_entities(P)
    check_loot_and_recipes(P, vitems)
    check_sounds(P, vsounds)
    check_structures(P, vblocks)
    check_scripts(P, veffects)
    check_lang_coverage(P)

    for w in WARNINGS:
        print(f'[validate] warning: {w}')
    for e in ERRORS:
        print(f'[validate] ERROR: {e}')
    print(f'[validate] {len(ERRORS)} errors, {len(WARNINGS)} warnings '
          f'({len(P.blocks)} blocks, {len(P.items)} items, {len(P.entities)} entities, {len(P.pools)} pools)')
    sys.exit(1 if ERRORS else 0)


if __name__ == '__main__':
    main()
