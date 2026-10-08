"""Loot tables. Key progression items are always guaranteed in a specific room; RNG only adds bonuses."""
from .registry import REG

LT = 'loot_tables/rotu/'


def item(name, weight=1, count=None, functions=None, conditions=None):
    e = {'type': 'item', 'name': name if ':' in name else 'minecraft:' + name, 'weight': weight}
    fn = []
    if count is not None:
        if isinstance(count, tuple):
            fn.append({'function': 'set_count', 'count': {'min': count[0], 'max': count[1]}})
        elif count != 1:
            fn.append({'function': 'set_count', 'count': count})
    if functions:
        fn.extend(functions)
    if fn:
        e['functions'] = fn
    if conditions:
        e['conditions'] = conditions
    return e


def empty(weight):
    return {'type': 'empty', 'weight': weight}


def pool(rolls, entries, conditions=None):
    p = {'rolls': rolls if not isinstance(rolls, tuple) else {'min': rolls[0], 'max': rolls[1]}, 'entries': entries}
    if conditions:
        p['conditions'] = conditions
    return p


def table(path, *pools):
    REG.add_bp(LT + path + '.json', {'pools': list(pools)})


CHANCE = lambda c: [{'condition': 'random_chance', 'chance': c}]
BY_PLAYER = [{'condition': 'killed_by_player'}]
ENCHANT_BOOK = item('book', 1, functions=[{'function': 'enchant_randomly', 'treasure': True}])
LOOTING = lambda lo, hi: {'function': 'looting_enchant', 'count': {'min': lo, 'max': hi}}

JOURNAL_PAGES = [
    "FIELD JOURNAL\nArchivist I. Hale\n\nDay 9. The tablets are real. Every one bears the same scar where a name should be. Whoever these people were, they erased themselves on purpose.",
    "Day 12. I can read them now. The glyphs are a tuning system, not an alphabet. Set a tablet on a Scriptorium Desk (planks, a book, a glyph shard) and the meaning rises like frost on glass.",
    "I copy everything into a Codex - any book bound with a glyph shard will do. It keeps the chapters in order and it seems to know what we should look for next.",
    "Day 15. Brush the loose sand and gravel near the old stones; that is where the tablets sleep. Mind the urns. Something comes out of some of them.",
    "Day 19. The shrines have dials. The answer is always carved above the gate, left to right. M. turned them wrong twice and the ground went quiet under her feet.",
    "Day 21. A lens of amethyst shows walls that are not walls. A forked rod hums near the singing stones, even through rock. Dig where it pulls hardest.",
    "Day 23. The stones hum at night. The crew will not sleep. I am going below tomorrow to find the source.\n\nIf you are reading this, I did not come back up. Do not say your name down there.",
]


def define_loot():
    # ------------------------------------------------------------ blocks
    REG.add_bp(LT + 'blocks/empty.json', {'pools': []})
    table('blocks/urn_empty', pool(1, [item('rotu:funerary_urn')]))
    table('blocks/singing_stone',
          pool(1, [item('rotu:glyph_shard', 1, (1, 3))]),
          pool(1, [item('rotu:inscribed_tablet')], CHANCE(0.08)))
    table('blocks/urn_sealed',
          pool((1, 2), [
              item('rotu:glyph_shard', 22, (1, 2)),
              item('gold_nugget', 18, (2, 6)),
              item('bone', 14, (1, 3)),
              item('bone_meal', 10, (2, 4)),
              item('candle', 8, (1, 2)),
              item('emerald', 6, (1, 2)),
              item('rotu:inscribed_tablet', 7),
              item('rotu:murmur_essence', 5),
              item('rotu:reliquary_key', 3),
              item('amethyst_shard', 6, (1, 3)),
              empty(12),
          ]))

    # ------------------------------------------------------------ archaeology (suspicious blocks)
    table('archaeology/waystone', pool(1, [
        item('rotu:glyph_shard', 30, (1, 2)),
        item('rotu:inscribed_tablet', 26),
        item('gold_nugget', 10, (2, 4)),
        item('emerald', 6),
        item('skull_pottery_sherd', 4),
        item('danger_pottery_sherd', 3),
        item('amethyst_shard', 6),
        item('rotu:reliquary_key', 3),
        item('bone', 8),
    ]))
    table('archaeology/dig_site', pool(1, [
        item('rotu:inscribed_tablet', 32),
        item('rotu:glyph_shard', 26, (1, 3)),
        item('gold_nugget', 9, (2, 5)),
        item('emerald', 5),
        item('brick', 6),
        item('skull_pottery_sherd', 3),
        item('heartbreak_pottery_sherd', 3),
        item('rotu:reliquary_key', 4),
        item('candle', 5),
        item('bone', 7),
    ]))

    # ------------------------------------------------------------ chests
    table('chests/waystone_cache',
          pool(1, [item('rotu:inscribed_tablet', 1)], CHANCE(0.75)),
          pool((3, 5), [
              item('rotu:glyph_shard', 20, (2, 5)),
              item('gold_nugget', 12, (3, 8)),
              item('bone', 10, (1, 4)),
              item('candle', 8, (1, 3)),
              item('emerald', 6, (1, 2)),
              item('amethyst_shard', 8, (1, 4)),
              item('iron_ingot', 7, (1, 3)),
              item('bread', 6, (1, 3)),
              item('rotu:reliquary_key', 4),
              item('book', 4),
              item('rotu:murmur_essence', 3),
          ]))
    table('chests/dig_supplies',
          pool(1, [item('written_book', 1, functions=[{
              'function': 'set_book_contents', 'author': 'Archivist I. Hale', 'title': 'Field Journal',
              'pages': JOURNAL_PAGES}])]),
          pool(1, [item('brush')]),
          pool(1, [item('rotu:codex')], CHANCE(0.6)),
          pool((3, 5), [
              item('torch', 14, (3, 8)),
              item('bread', 12, (2, 4)),
              item('paper', 10, (2, 6)),
              item('rotu:glyph_shard', 10, (1, 3)),
              item('lantern', 6),
              item('copper_ingot', 8, (2, 5)),
              item('amethyst_shard', 6, (1, 3)),
              item('empty_map', 4),
              item('spyglass', 2),
              item('compass', 3),
          ]))
    table('chests/dig_finds', pool((2, 4), [
        item('rotu:inscribed_tablet', 18),
        item('rotu:glyph_shard', 18, (1, 4)),
        item('gold_ingot', 8, (1, 2)),
        item('emerald', 8, (1, 3)),
        item('decorated_pot', 4),
        item('rotu:reliquary_key', 6),
        item('rotu:murmur_essence', 5),
        item('amethyst_shard', 8, (2, 4)),
        item('bone', 10, (1, 4)),
    ]))
    common_ruin = [
        item('rotu:glyph_shard', 18, (2, 4)),
        item('rotu:inscribed_tablet', 12),
        item('gold_ingot', 8, (1, 3)),
        item('iron_ingot', 10, (2, 4)),
        item('emerald', 8, (1, 3)),
        item('bone', 10, (2, 5)),
        item('candle', 6, (1, 3)),
        item('rotu:reliquary_key', 6),
        item('rotu:murmur_essence', 5, (1, 2)),
        item('golden_carrot', 5, (1, 3)),
        item('name_tag', 2),
        item('book', 1, functions=[{'function': 'enchant_randomly', 'treasure': False}]),
    ]
    table('chests/shrine_common', pool((3, 6), common_ruin))
    table('chests/shrine_sanctum',
          pool(1, [item('rotu:lantern_shard')]),
          pool(1, [item('rotu:reliquary_key', 1, (1, 2))]),
          pool((3, 5), common_ruin + [item('diamond', 4, (1, 2)), ENCHANT_BOOK, item('golden_apple', 4)]))
    table('chests/shrine_secret',
          pool((2, 4), [
              item('diamond', 6, (1, 2)),
              item('gold_ingot', 10, (2, 5)),
              item('emerald', 10, (2, 5)),
              item('music_disc_5', 3),
              item('disc_fragment_5', 6, (1, 3)),
              item('rotu:inscribed_tablet', 10, (1, 2)),
              item('rotu:reliquary_key', 8, (1, 2)),
              item('golden_apple', 6),
              ENCHANT_BOOK,
              item('ward_armor_trim_smithing_template', 2),
          ]))
    table('chests/ossuary_crypt',
          pool(1, [item('rotu:bone_shard')], CHANCE(0.12)),
          pool((3, 6), common_ruin + [
              item('bone_block', 4, (1, 2)),
              item('skeleton_skull', 2),
              item('iron_sword', 3, functions=[{'function': 'enchant_with_levels', 'levels': {'min': 10, 'max': 25}}]),
          ]))
    table('chests/ossuary_bone_choir',
          pool(1, [item('rotu:bone_shard')]),
          pool(1, [item('rotu:reliquary_key', 1, (1, 3))]),
          pool((4, 6), [
              item('diamond', 6, (1, 3)),
              item('gold_ingot', 10, (3, 6)),
              item('emerald', 10, (3, 6)),
              item('rotu:inscribed_tablet', 10, (1, 2)),
              item('golden_apple', 6),
              item('rotu:murmur_essence', 8, (2, 4)),
              ENCHANT_BOOK,
              item('diamond_pickaxe', 2, functions=[{'function': 'enchant_with_levels', 'levels': {'min': 20, 'max': 30}}]),
              item('bone_block', 6, (2, 4)),
              item('echo_shard', 4, (1, 2)),
          ]))
    table('chests/sanctum_spire', pool((4, 7), common_ruin + [
        item('ender_pearl', 6, (1, 3)),
        item('experience_bottle', 6, (2, 6)),
        item('diamond', 3, (1, 2)),
        item('spyglass', 2),
    ]))
    table('chests/sanctum_hall', pool((4, 7), common_ruin + [
        item('diamond', 6, (1, 3)),
        item('golden_apple', 6, (1, 2)),
        item('experience_bottle', 6, (3, 8)),
        item('echo_shard', 4, (1, 3)),
        ENCHANT_BOOK,
    ]))
    table('chests/sanctum_vault',
          pool((5, 8), [
              item('diamond', 10, (2, 5)),
              item('emerald_block', 4, (1, 2)),
              item('gold_block', 5, (1, 2)),
              item('netherite_scrap', 4, (1, 2)),
              item('enchanted_golden_apple', 1),
              item('golden_apple', 8, (1, 3)),
              item('experience_bottle', 10, (4, 10)),
              item('echo_shard', 6, (2, 4)),
              item('silence_armor_trim_smithing_template', 1),
              item('book', 6, functions=[{'function': 'enchant_with_levels', 'levels': {'min': 30, 'max': 39}, 'treasure': True}]),
          ]))

    # ------------------------------------------------------------ reliquaries (generated by script, per player)
    table('reliquary/lesser',
          pool((2, 3), [
              item('emerald', 14, (2, 6)),
              item('gold_ingot', 12, (2, 5)),
              item('iron_ingot', 10, (3, 8)),
              item('diamond', 6, (1, 2)),
              item('rotu:inscribed_tablet', 10, (1, 2)),
              item('rotu:glyph_shard', 10, (3, 6)),
              item('golden_apple', 5),
              item('experience_bottle', 8, (2, 5)),
              item('rotu:murmur_essence', 6, (1, 3)),
              ENCHANT_BOOK,
          ]),
          pool(1, [
              item('rotu:choristers_mask', 5),
              item('rotu:delvers_pick', 2),
              item('diamond', 10, (2, 3)),
              item('music_disc_5', 3),
              item('echo_shard', 6, (1, 2)),
              item('ward_armor_trim_smithing_template', 3),
              item('silence_armor_trim_smithing_template', 1),
              item('enchanted_golden_apple', 1),
          ], CHANCE(0.35)))
    table('reliquary/grand',
          pool(1, [
              item('rotu:dirge_blade', 4),
              item('rotu:hushweave_mantle', 4),
              item('rotu:delvers_pick', 3),
              item('rotu:choristers_mask', 3),
              item('rotu:sentinels_maul', 2),
          ]),
          pool((3, 5), [
              item('diamond', 12, (3, 6)),
              item('netherite_scrap', 5, (1, 2)),
              item('emerald', 10, (6, 12)),
              item('golden_apple', 8, (1, 3)),
              item('experience_bottle', 10, (6, 12)),
              item('book', 6, functions=[{'function': 'enchant_with_levels', 'levels': {'min': 30, 'max': 39}, 'treasure': True}]),
          ]),
          pool(1, [item('silence_armor_trim_smithing_template', 1)], CHANCE(0.3)),
          pool(1, [item('enchanted_golden_apple', 1)], CHANCE(0.2)))

    # ------------------------------------------------------------ entities
    table('entities/hushwalker',
          pool(1, [item('bone', 1, (0, 2), functions=[LOOTING(0, 1)])]),
          pool(1, [item('string', 1, (0, 1), functions=[LOOTING(0, 1)])]),
          pool(1, [item('rotu:glyph_shard', 1, functions=[LOOTING(0, 1)])],
               [{'condition': 'killed_by_player'},
                {'condition': 'random_chance_with_looting', 'chance': 0.12, 'looting_multiplier': 0.04}]),
          pool(1, [item('rotu:inscribed_tablet')],
               [{'condition': 'killed_by_player'},
                {'condition': 'random_chance_with_looting', 'chance': 0.035, 'looting_multiplier': 0.015}]))
    table('entities/murmur',
          pool(1, [item('rotu:murmur_essence', 1, functions=[LOOTING(0, 1)])],
               [{'condition': 'random_chance_with_looting', 'chance': 0.7, 'looting_multiplier': 0.1}]))
    table('entities/graven_sentinel',
          pool(1, [item('rotu:hush_shard')]),
          pool(1, [item('rotu:gloamstone_bricks', 1, (2, 4))]),
          pool(1, [item('rotu:glyph_shard', 1, (2, 5))]),
          pool(1, [item('rotu:sentinels_maul')],
               [{'condition': 'killed_by_player'},
                {'condition': 'random_chance_with_looting', 'chance': 0.35, 'looting_multiplier': 0.05}]))
    table('entities/last_cantor',
          pool(1, [item('rotu:cantors_seal', 1, 2)]),
          pool(1, [item('rotu:low_star_fragment')]),
          pool(1, [item('rotu:murmur_essence', 1, (4, 8))]),
          pool(1, [item('rotu:glyph_shard', 1, (6, 10))]),
          pool(1, [item('rotu:inscribed_tablet', 1, (1, 2))]))
