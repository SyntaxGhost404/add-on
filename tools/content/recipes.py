"""Crafting, stonecutting and smelting recipes."""
from .registry import REG, FORMAT_RECIPE, nid


def _id(x):
    return x if ':' in x else 'minecraft:' + x


def shaped(name, pattern, key, result, count=1, unlock=None, tags=('crafting_table',)):
    k = {}
    for ch, v in key.items():
        k[ch] = {'tag': v[1:]} if v.startswith('#') else {'item': _id(v)}
    REG.add_bp(f'recipes/{name}.json', {
        'format_version': FORMAT_RECIPE,
        'minecraft:recipe_shaped': {
            'description': {'identifier': nid(name)},
            'tags': list(tags),
            'pattern': pattern,
            'key': k,
            'unlock': [{'item': _id(u)} for u in (unlock or [])] or [{'context': 'AlwaysUnlocked'}],
            'result': {'item': _id(result), 'count': count},
        }
    })


def shapeless(name, ingredients, result, count=1, unlock=None, tags=('crafting_table',)):
    ing = []
    for x in ingredients:
        if isinstance(x, tuple):
            ing.append({'item': _id(x[0]), 'count': x[1]})
        else:
            ing.append({'item': _id(x)})
    REG.add_bp(f'recipes/{name}.json', {
        'format_version': FORMAT_RECIPE,
        'minecraft:recipe_shapeless': {
            'description': {'identifier': nid(name)},
            'tags': list(tags),
            'ingredients': ing,
            'unlock': [{'item': _id(u)} for u in (unlock or [])] or [{'context': 'AlwaysUnlocked'}],
            'result': {'item': _id(result), 'count': count},
        }
    })


def stonecut(name, src, dst, count=1):
    shapeless(name, [src], dst, count, unlock=[src], tags=('stonecutter',))


def furnace(name, src, dst):
    REG.add_bp(f'recipes/{name}.json', {
        'format_version': FORMAT_RECIPE,
        'minecraft:recipe_furnace': {
            'description': {'identifier': nid(name)},
            'tags': ['furnace', 'blast_furnace'],
            'input': _id(src),
            'output': _id(dst),
            'unlock': [{'item': _id(src)}],
        }
    })


def define_recipes():
    G = 'rotu:glyph_shard'
    shapeless('codex', ['book', G], 'rotu:codex', unlock=[G])
    shaped('scriptorium_desk', ['BG ', 'PPP', 'P P'], {'B': 'book', 'G': G, 'P': '#minecraft:planks'},
           'rotu:scriptorium_desk', unlock=[G])
    shaped('reliquary_key', [' G ', 'GIG', ' G '], {'G': G, 'I': 'gold_ingot'}, 'rotu:reliquary_key', unlock=[G])
    shaped('sigil_key', ['LBH', ' I '], {'L': 'rotu:lantern_shard', 'B': 'rotu:bone_shard', 'H': 'rotu:hush_shard',
                                         'I': 'gold_ingot'}, 'rotu:sigil_key',
           unlock=['rotu:lantern_shard', 'rotu:bone_shard', 'rotu:hush_shard'])
    shaped('diviners_lens', ['CGC', 'CAC', ' S '], {'C': 'copper_ingot', 'G': G, 'A': 'amethyst_shard', 'S': 'stick'},
           'rotu:diviners_lens', unlock=[G])
    shaped('dowsing_rod', ['S S', ' G ', ' C '], {'S': 'stick', 'G': G, 'C': 'copper_ingot'}, 'rotu:dowsing_rod',
           unlock=[G])
    shaped('gloamstone_bricks', ['DDD', 'DGD', 'DDD'], {'D': 'cobbled_deepslate', 'G': G}, 'rotu:gloamstone_bricks',
           count=8, unlock=[G])
    shaped('choir_lantern', [' B ', 'ELE', ' B '], {'B': 'rotu:gloamstone_bricks', 'E': 'rotu:murmur_essence',
                                                    'L': 'lantern'}, 'rotu:choir_lantern', count=2,
           unlock=['rotu:murmur_essence'])
    shaped('funerary_urn', [' C ', 'C C', 'CCC'], {'C': 'brick'}, 'rotu:funerary_urn', unlock=['brick'])
    shapeless('gilded_gloamstone', ['rotu:gloamstone_bricks', 'gold_nugget', 'gold_nugget'], 'rotu:gilded_gloamstone',
              unlock=['rotu:gloamstone_bricks'])
    shapeless('mossy_gloamstone_bricks', ['rotu:gloamstone_bricks', 'moss_block'], 'rotu:mossy_gloamstone_bricks',
              unlock=['rotu:gloamstone_bricks'])
    shapeless('mossy_gloamstone_bricks_from_vine', ['rotu:gloamstone_bricks', 'vine'], 'rotu:mossy_gloamstone_bricks',
              unlock=['rotu:gloamstone_bricks'])
    shapeless('veilstone', [('rotu:gloamstone_bricks', 4), 'rotu:murmur_essence'], 'rotu:veilstone', count=4,
              unlock=['rotu:murmur_essence'])
    shapeless('hushing_plate', [('rotu:gloamstone_tiles', 2), 'rotu:murmur_essence'], 'rotu:hushing_plate',
              unlock=['rotu:murmur_essence'])
    for dst in ('chiseled_gloamstone', 'gloamstone_tiles', 'gloamstone_pillar', 'glyph_mural', 'cipher_stone'):
        stonecut(f'{dst}_from_gloamstone_bricks_stonecutting', 'rotu:gloamstone_bricks', f'rotu:{dst}')
    shaped('gloamstone_pillar', ['B', 'B'], {'B': 'rotu:gloamstone_bricks'}, 'rotu:gloamstone_pillar', count=2,
           unlock=['rotu:gloamstone_bricks'])
    shaped('gloamstone_tiles', ['BB', 'BB'], {'B': 'rotu:gloamstone_bricks'}, 'rotu:gloamstone_tiles', count=4,
           unlock=['rotu:gloamstone_bricks'])
    furnace('cracked_gloamstone_bricks_furnace', 'rotu:gloamstone_bricks', 'rotu:cracked_gloamstone_bricks')
