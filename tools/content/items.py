"""Custom item definitions."""
from .registry import REG, NS, FORMAT_ITEM, nid

ITEM_TEX = 'textures/rotu/items/'
ITEM_IDS = []


def item(name, en, components, *, category='items', lore=None):
    ident = nid(name)
    REG.item_tex(f'{NS}:{name}', ITEM_TEX + name)
    comps = {
        'minecraft:icon': {'textures': {'default': f'{NS}:{name}'}},
        'minecraft:display_name': {'value': f'item.{ident}.name'},
    }
    comps.update(components)
    REG.add_bp(f'items/{name}.json', {
        'format_version': FORMAT_ITEM,
        'minecraft:item': {
            'description': {'identifier': ident, 'menu_category': {'category': category}},
            'components': comps,
        }
    })
    REG.tr(f'item.{ident}.name', en)
    ITEM_IDS.append(ident)
    return ident


def define_items():
    item('codex', 'Codex of the Unnamed', {
        'minecraft:max_stack_size': 1,
        'minecraft:rarity': 'uncommon',
        'rotu:codex': {},
    })
    item('glyph_shard', 'Glyph Shard', {
        'minecraft:max_stack_size': 64,
    })
    item('inscribed_tablet', 'Inscribed Tablet', {
        'minecraft:max_stack_size': 16,
        'minecraft:rarity': 'uncommon',
    })
    item('reliquary_key', 'Reliquary Key', {
        'minecraft:max_stack_size': 16,
        'minecraft:rarity': 'uncommon',
        'minecraft:tags': {'tags': ['rotu:key']},
    })
    for shard, en in (('lantern_shard', 'Lantern Sigil Shard'), ('bone_shard', 'Bone Sigil Shard'),
                      ('hush_shard', 'Hush Sigil Shard')):
        item(shard, en, {
            'minecraft:max_stack_size': 16,
            'minecraft:rarity': 'rare',
            'minecraft:tags': {'tags': ['rotu:sigil_shard']},
        })
    item('sigil_key', 'Sigil Key', {
        'minecraft:max_stack_size': 1,
        'minecraft:rarity': 'epic',
        'minecraft:glint': True,
        'minecraft:tags': {'tags': ['rotu:key']},
    })
    item('cantors_seal', "Cantor's Seal", {
        'minecraft:max_stack_size': 16,
        'minecraft:rarity': 'epic',
        'minecraft:glint': True,
        'minecraft:tags': {'tags': ['rotu:key']},
    })
    item('murmur_essence', 'Murmur Essence', {
        'minecraft:max_stack_size': 64,
        'minecraft:rarity': 'uncommon',
    })

    # --- tools -----------------------------------------------------------
    item('diviners_lens', "Diviner's Lens", {
        'minecraft:max_stack_size': 1,
        'minecraft:rarity': 'uncommon',
        'minecraft:durability': {'max_durability': 250},
        'minecraft:repairable': {'repair_items': [
            {'items': ['minecraft:amethyst_shard'], 'repair_amount': 'query.max_durability * 0.25'}]},
        'minecraft:cooldown': {'category': 'rotu:lens', 'duration': 1.5, 'type': 'use'},
        'minecraft:use_modifiers': {'use_duration': 0.25, 'movement_modifier': 1.0},
        'minecraft:use_animation': 'spyglass',
        'rotu:diviners_lens': {},
    }, category='equipment')
    item('dowsing_rod', 'Resonant Dowsing Rod', {
        'minecraft:max_stack_size': 1,
        'minecraft:rarity': 'uncommon',
        'minecraft:hand_equipped': True,
        'minecraft:durability': {'max_durability': 128},
        'minecraft:repairable': {'repair_items': [
            {'items': ['minecraft:copper_ingot'], 'repair_amount': 'query.max_durability * 0.25'}]},
        'minecraft:cooldown': {'category': 'rotu:dowsing', 'duration': 2.0, 'type': 'use'},
        'minecraft:use_modifiers': {'use_duration': 0.25, 'movement_modifier': 1.0},
        'rotu:dowsing_rod': {},
    }, category='equipment')
    item('delvers_pick', "Delver's Pick", {
        'minecraft:max_stack_size': 1,
        'minecraft:rarity': 'rare',
        'minecraft:hand_equipped': True,
        'minecraft:durability': {'max_durability': 1900},
        'minecraft:damage': 5,
        'minecraft:enchantable': {'slot': 'pickaxe', 'value': 15},
        'minecraft:repairable': {'repair_items': [
            {'items': ['minecraft:diamond'], 'repair_amount': 'query.max_durability * 0.25'},
            {'items': ['rotu:glyph_shard'], 'repair_amount': 'query.max_durability * 0.1'}]},
        'minecraft:tags': {'tags': ['minecraft:is_pickaxe', 'minecraft:is_tool', 'minecraft:diamond_tier',
                                    'minecraft:digger']},
        'minecraft:digger': {
            'use_efficiency': True,
            'destroy_speeds': [
                {'block': {'tags': "query.any_tag('minecraft:is_pickaxe_item_destructible', 'stone', 'metal', 'rail', 'diamond_pick_diggable', 'iron_pick_diggable', 'stone_pick_diggable', 'gold_pick_diggable', 'wood_pick_diggable')"},
                 'speed': 9},
            ],
        },
        'rotu:delvers_pick': {},
    }, category='equipment')

    # --- weapons ------------------------------------------------------------
    item('dirge_blade', 'Dirge Blade', {
        'minecraft:max_stack_size': 1,
        'minecraft:rarity': 'epic',
        'minecraft:hand_equipped': True,
        'minecraft:durability': {'max_durability': 1800},
        'minecraft:damage': 7,
        'minecraft:enchantable': {'slot': 'sword', 'value': 15},
        'minecraft:repairable': {'repair_items': [
            {'items': ['rotu:murmur_essence'], 'repair_amount': 'query.max_durability * 0.25'}]},
        'minecraft:tags': {'tags': ['minecraft:is_sword', 'minecraft:is_tool']},
        'minecraft:digger': {'use_efficiency': False, 'destroy_speeds': [
            {'block': 'minecraft:web', 'speed': 15}]},
        'rotu:dirge_blade': {},
    }, category='equipment')
    item('sentinels_maul', "Sentinel's Maul", {
        'minecraft:max_stack_size': 1,
        'minecraft:rarity': 'rare',
        'minecraft:hand_equipped': True,
        'minecraft:durability': {'max_durability': 1200},
        'minecraft:damage': 9,
        'minecraft:enchantable': {'slot': 'sword', 'value': 10},
        'minecraft:repairable': {'repair_items': [
            {'items': ['rotu:gloamstone_bricks'], 'repair_amount': 'query.max_durability * 0.15'}]},
        'minecraft:cooldown': {'category': 'rotu:maul', 'duration': 1.1, 'type': 'attack'},
        'minecraft:swing_duration': {'value': 1.1},
        'minecraft:tags': {'tags': ['minecraft:is_tool']},
        'rotu:sentinels_maul': {},
    }, category='equipment')

    # --- armor ----------------------------------------------------------------
    item('choristers_mask', "Chorister's Mask", {
        'minecraft:rarity': 'rare',
        'minecraft:wearable': {'slot': 'slot.armor.head', 'protection': 2},
        'minecraft:durability': {'max_durability': 330},
        'minecraft:enchantable': {'slot': 'armor_head', 'value': 12},
        'minecraft:repairable': {'repair_items': [
            {'items': ['rotu:murmur_essence'], 'repair_amount': 'query.max_durability * 0.25'}]},
        'minecraft:tags': {'tags': ['minecraft:is_armor']},
    }, category='equipment')
    item('hushweave_mantle', 'Hushweave Mantle', {
        'minecraft:rarity': 'epic',
        'minecraft:wearable': {'slot': 'slot.armor.chest', 'protection': 7},
        'minecraft:durability': {'max_durability': 560},
        'minecraft:enchantable': {'slot': 'armor_torso', 'value': 14},
        'minecraft:repairable': {'repair_items': [
            {'items': ['rotu:murmur_essence'], 'repair_amount': 'query.max_durability * 0.25'}]},
        'minecraft:tags': {'tags': ['minecraft:is_armor']},
    }, category='equipment')

    # --- relic ----------------------------------------------------------------
    item('low_star_fragment', 'Low Star Fragment', {
        'minecraft:max_stack_size': 1,
        'minecraft:rarity': 'epic',
        'minecraft:glint': True,
        'minecraft:use_modifiers': {'use_duration': 2.5, 'movement_modifier': 0.25},
        'minecraft:use_animation': 'bow',
        'minecraft:cooldown': {'category': 'rotu:starcall', 'duration': 120, 'type': 'use'},
        'rotu:low_star_fragment': {},
    }, category='equipment')
