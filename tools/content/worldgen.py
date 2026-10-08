"""Data-driven jigsaw worldgen: structures, structure sets, template pools and processor lists.

Also builds every .mcstructure piece referenced by the pools.
"""
from .registry import REG, FORMAT_WORLDGEN
from structures.surface import STATUES, WAYSTONES, WAYSTONES_ARID, GROUND
from structures.sites import SITES, SHRINES
from structures.underground import OSSUARY, SANCTUM, OSS_GROUND, SANC_GROUND

PIECES = {}   # location ('rotu/<piece>', relative to the BP structures folder) -> builder


def piece(group, name, fn):
    stem = name if name.startswith(group) else f'{group}_{name}'
    loc = f'rotu/{stem}'
    if loc in PIECES:
        raise ValueError(f'duplicate structure piece {loc}')
    PIECES[loc] = fn
    return loc


# ------------------------------------------------------------------ biome filters
def tags_any(*tags):
    return {'any_of': [{'test': 'has_biome_tag', 'operator': '==', 'value': t} for t in tags]}


def tags_none(*tags):
    return [{'test': 'has_biome_tag', 'operator': '!=', 'value': t} for t in tags]


WATERY = ('ocean', 'river', 'beach', 'mooshroom_island', 'deep_dark', 'caves')
OVERWORLD = tags_any('overworld', 'overworld_generation')


def filt(*groups, exclude=WATERY):
    return [{'all_of': [OVERWORLD] + list(groups) + tags_none(*exclude)}]


TEMPERATE = tags_any('forest', 'plains', 'taiga', 'savanna', 'extreme_hills', 'mountains', 'meadow', 'birch',
                     'roofed', 'flower_forest', 'dappled_forest', 'cherry_grove', 'pale_garden', 'swamp', 'jungle',
                     'grove')
ARID = tags_any('desert', 'mesa')
LAND = tags_any('forest', 'plains', 'taiga', 'savanna', 'extreme_hills', 'mountains', 'meadow', 'birch', 'roofed',
                'flower_forest', 'dappled_forest', 'cherry_grove', 'pale_garden', 'swamp', 'jungle', 'desert', 'mesa',
                'grove', 'ice_plains', 'mangrove_swamp')


# ------------------------------------------------------------------ writers
def processor_list(name, rules):
    REG.add_bp(f'worldgen/processors/{name}.json', {
        'format_version': FORMAT_WORLDGEN,
        'minecraft:processor_list': {
            'description': {'identifier': f'rotu:{name}'},
            'processors': [{'processor_type': 'minecraft:rule', 'rules': rules}],
        }
    })


def rule(block, prob, out):
    return {'input_predicate': {'predicate_type': 'minecraft:random_block_match', 'block': block, 'probability': prob},
            'output_state': {'name': out}}


def pool(name, elements, fallback=None):
    els = []
    for loc, weight, proc in elements:
        e = {'element_type': 'minecraft:single_pool_element', 'location': loc, 'projection': 'rigid'}
        if proc:
            e['processors'] = f'rotu:{proc}'
        els.append({'element': e, 'weight': weight})
    body = {'description': {'identifier': f'rotu:{name}'}, 'elements': els}
    if fallback:
        body['fallback'] = f'rotu:{fallback}'
    REG.add_bp(f'worldgen/template_pools/{name}.json', {'format_version': FORMAT_WORLDGEN,
                                                         'minecraft:template_pool': body})


def jigsaw_structure(name, start_pool, start_height, adaptation, biomes, max_depth=1, max_dist=48,
                     step='surface_structures', padding=(10, 8)):
    REG.add_bp(f'worldgen/structures/{name}.json', {
        'format_version': FORMAT_WORLDGEN,
        'minecraft:jigsaw': {
            'description': {'identifier': f'rotu:{name}'},
            'biome_filters': biomes,
            'step': step,
            'terrain_adaptation': adaptation,
            'start_pool': f'rotu:{start_pool}',
            'start_height': {'type': 'constant', 'value': {'absolute': start_height}},
            'heightmap_projection': 'world_surface',
            'max_depth': max_depth,
            'max_distance_from_center': max_dist,
            'dimension_padding': {'top': padding[0], 'bottom': padding[1]},
            'liquid_settings': 'ignore_waterlogging',
        }
    })


def structure_set(name, structures, spacing, separation, salt):
    REG.add_bp(f'worldgen/structure_sets/{name}.json', {
        'format_version': FORMAT_WORLDGEN,
        'minecraft:structure_set': {
            'description': {'identifier': f'rotu:{name}'},
            'placement': {'type': 'minecraft:random_spread', 'salt': salt, 'spacing': spacing,
                          'separation': separation, 'spread_type': 'linear'},
            'structures': [{'structure': f'rotu:{s}', 'weight': w} for s, w in structures],
        }
    })


STRUCTURE_INFO = {}   # id -> (english name, description) used for docs and the codex


def define_worldgen():
    processor_list('weathering', [
        rule('rotu:gloamstone_bricks', 0.12, 'rotu:cracked_gloamstone_bricks'),
        rule('rotu:gloamstone_bricks', 0.07, 'rotu:mossy_gloamstone_bricks'),
        rule('minecraft:web', 0.35, 'minecraft:air'),
        rule('minecraft:candle', 0.25, 'minecraft:air'),
    ])
    processor_list('crypt_decay', [
        rule('rotu:gloamstone_bricks', 0.15, 'rotu:cracked_gloamstone_bricks'),
        rule('minecraft:web', 0.3, 'minecraft:air'),
        rule('minecraft:candle', 0.3, 'minecraft:air'),
        rule('minecraft:polished_blackstone_bricks', 0.15, 'minecraft:cracked_polished_blackstone_bricks'),
    ])

    # --- mourning statues
    locs = [piece('statue', n, f) for n, f in STATUES.items()]
    pool('statue_start', [(l, 1, 'weathering') for l in locs])
    jigsaw_structure('mourning_statue', 'statue_start', -1, 'beard_thin', filt(LAND), max_dist=16)
    structure_set('mourning_statue', [('mourning_statue', 1)], 14, 5, 381904211)
    STRUCTURE_INFO['mourning_statue'] = 'Mourning Statue'

    # --- waystones
    w = {'waystone_tall': 3, 'waystone_broken': 3, 'waystone_twin': 2, 'waystone_ring': 2}
    pool('waystone_start', [(piece('waystone', n, f), w[n], 'weathering') for n, f in WAYSTONES.items()])
    jigsaw_structure('waystone', 'waystone_start', -GROUND, 'none', filt(TEMPERATE, exclude=WATERY + ('desert', 'mesa')),
                     max_dist=16)
    structure_set('waystone', [('waystone', 1)], 16, 6, 597240183)
    pool('waystone_arid_start', [(piece('waystone', n, f), 1, None) for n, f in WAYSTONES_ARID.items()])
    jigsaw_structure('waystone_arid', 'waystone_arid_start', -GROUND, 'none', filt(ARID), max_dist=16)
    structure_set('waystone_arid', [('waystone_arid', 1)], 18, 6, 728301947)
    STRUCTURE_INFO['waystone'] = 'Waystone'

    # --- dig sites (excavation start + camp)
    pool('dig_start', [(piece('dig_site', 'excavation', SITES['dig_excavation']), 1, None)])
    pool('dig_arid_start', [(piece('dig_site', 'excavation_arid', SITES['dig_excavation_arid']), 1, None)])
    pool('dig_camp', [(piece('dig_site', 'camp', SITES['dig_camp']), 1, None)])
    jigsaw_structure('dig_site', 'dig_start', -1, 'beard_thin',
                     filt(tags_any('plains', 'taiga', 'forest', 'savanna', 'meadow', 'birch', 'dappled_forest',
                                   'extreme_hills', 'cherry_grove'), exclude=WATERY + ('desert', 'mesa')),
                     max_depth=2, max_dist=32)
    jigsaw_structure('dig_site_arid', 'dig_arid_start', -1, 'beard_thin', filt(ARID), max_depth=2, max_dist=32)
    structure_set('dig_site', [('dig_site', 1)], 26, 9, 204958271)
    structure_set('dig_site_arid', [('dig_site_arid', 1)], 26, 9, 843920115)
    STRUCTURE_INFO['dig_site'] = 'Dig Site'

    # --- hushed shrines
    pool('shrine_start', [(piece('shrine', 'sentinel', SHRINES['shrine_sentinel']), 2, 'weathering'),
                          (piece('shrine', 'hollow', SHRINES['shrine_hollow']), 1, 'weathering')])
    jigsaw_structure('hushed_shrine', 'shrine_start', -1, 'beard_thin', filt(TEMPERATE), max_dist=24)
    structure_set('hushed_shrine', [('hushed_shrine', 1)], 34, 12, 130591847)
    STRUCTURE_INFO['hushed_shrine'] = 'Hushed Shrine'

    # --- ossuaries
    o = {k: piece('ossuary', k, f) for k, f in OSSUARY.items()}
    pool('ossuary_start', [(o['mausoleum'], 1, 'crypt_decay')])
    pool('ossuary_hub', [(o['hub'], 1, 'crypt_decay')])
    pool('ossuary_bone_choir', [(o['bone_choir'], 1, 'crypt_decay')], fallback='ossuary_caps')
    pool('ossuary_corridors', [(o['straight'], 6, 'crypt_decay'), (o['turn'], 3, 'crypt_decay'),
                               (o['tee'], 3, 'crypt_decay'), (o['crypt'], 3, 'crypt_decay'),
                               (o['crypt_reliquary'], 2, 'crypt_decay'), (o['crypt_spawner'], 2, 'crypt_decay')],
         fallback='ossuary_caps')
    pool('ossuary_caps', [(o['cap'], 1, None)])
    jigsaw_structure('ossuary', 'ossuary_start', -OSS_GROUND, 'none', filt(LAND), max_depth=6, max_dist=72,
                     padding=(12, 16))
    structure_set('ossuary', [('ossuary', 1)], 38, 14, 915384620)
    STRUCTURE_INFO['ossuary'] = 'Ossuary'

    # --- sunken sanctum
    s = {k: piece('sanctum', k, f) for k, f in SANCTUM.items()}
    pool('sanctum_start', [(s['spire'], 1, None)])
    pool('sanctum_antechamber', [(s['antechamber'], 1, None)])
    pool('sanctum_hall', [(s['hall'], 1, None)])
    pool('sanctum_choir', [(s['choir'], 1, None)])
    pool('sanctum_vault', [(s['vault'], 1, None)])
    jigsaw_structure('sunken_sanctum', 'sanctum_start', -SANC_GROUND, 'none',
                     filt(LAND, exclude=WATERY + ('frozen_peaks', 'jagged_peaks')), max_depth=5, max_dist=116,
                     padding=(16, 20))
    structure_set('sunken_sanctum', [('sunken_sanctum', 1)], 56, 22, 640281937)
    STRUCTURE_INFO['sunken_sanctum'] = 'Sunken Sanctum'
