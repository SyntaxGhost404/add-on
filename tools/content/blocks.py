"""Custom block definitions (behavior pack JSON + resource pack texture/sound wiring)."""
from lib.mcstructure import register_custom_block

from .registry import REG, NS, FORMAT_BLOCK, nid

TEX = 'textures/rotu/blocks/'
PICKAXE = 'minecraft:is_pickaxe_item_destructible'
AXE = 'minecraft:is_axe_item_destructible'
UNBREAKABLE_RESIST = 3600000
# Puzzle and reward blocks must not be shoved by pistons: reliquary claims are stored per block
# position, and a moved gate or dial would let players skip a puzzle.
IMMOVABLE = {'movement_type': 'immovable'}

BLOCK_IDS = []


def mat(texture, render='opaque', **extra):
    m = {'texture': texture, 'render_method': render}
    m.update(extra)
    return m


def tex(key, file=None):
    REG.terrain(f'{NS}:{key}', TEX + (file or key))
    return f'{NS}:{key}'


def block(name, en, components, *, category='construction', states=None, traits=None, permutations=None,
          sound='deepslate_bricks', full_solid=True, hidden=False, state_schema=None):
    ident = nid(name)
    desc = {'identifier': ident, 'menu_category': {'category': 'none' if hidden else category}}
    if hidden:
        desc['menu_category']['is_hidden_in_commands'] = False
    if states:
        desc['states'] = states
    if traits:
        desc['traits'] = traits
    body = {'description': desc, 'components': components}
    if permutations:
        body['permutations'] = permutations
    REG.add_bp(f'blocks/{name}.json', {'format_version': FORMAT_BLOCK, 'minecraft:block': body})
    REG.tr(f'tile.{ident}.name', en)
    REG.block_sounds[ident] = sound
    # register the full state schema for the structure builder (custom states + trait states)
    schema = []
    for sname, vals in (states or {}).items():
        if all(isinstance(v, bool) for v in vals):
            schema.append({'name': sname, 'type': 'bool', 'values': vals})
        elif all(isinstance(v, int) for v in vals):
            schema.append({'name': sname, 'type': 'int', 'values': vals})
        else:
            schema.append({'name': sname, 'type': 'string', 'values': vals})
    for extra in (state_schema or []):
        schema.append(extra)
    register_custom_block(ident, schema, full_solid=full_solid)
    BLOCK_IDS.append(ident)
    return ident


def stone_components(texture_or_instances, seconds=3.0, resist=6, map_color='#3b3848', tags=(PICKAXE,), light=None):
    inst = texture_or_instances if isinstance(texture_or_instances, dict) else {'*': mat(texture_or_instances)}
    c = {
        'minecraft:destructible_by_mining': {'seconds_to_destroy': seconds},
        'minecraft:destructible_by_explosion': {'explosion_resistance': resist},
        'minecraft:map_color': map_color,
        'minecraft:geometry': 'minecraft:geometry.full_block',
        'minecraft:material_instances': inst,
    }
    if tags:
        c['minecraft:tags'] = list(tags) + ['rotu:gloamstone']
    if light:
        c['minecraft:light_emission'] = light
    return c


SIDES = ('north', 'south', 'east', 'west')


def four_sides(side_tex, top_tex, bottom_tex=None, render='opaque'):
    inst = {'*': mat(side_tex, render)}
    for s in SIDES:
        inst[s] = mat(side_tex, render)
    inst['up'] = mat(top_tex, render)
    inst['down'] = mat(bottom_tex or top_tex, render)
    return inst


def define_blocks():
    # --- gloamstone building set ---------------------------------------
    for name, en, key, mc in (
        ('gloamstone_bricks', 'Gloamstone Bricks', 'gloamstone_bricks', '#3b3848'),
        ('cracked_gloamstone_bricks', 'Cracked Gloamstone Bricks', 'cracked_gloamstone_bricks', '#363343'),
        ('mossy_gloamstone_bricks', 'Mossy Gloamstone Bricks', 'mossy_gloamstone_bricks', '#3f4a3e'),
        ('gloamstone_tiles', 'Gloamstone Tiles', 'gloamstone_tiles', '#34313f'),
        ('gilded_gloamstone', 'Gilded Gloamstone', 'gilded_gloamstone', '#5a4a2a'),
    ):
        block(name, en, stone_components(tex(key), map_color=mc))

    block('chiseled_gloamstone', 'Chiseled Gloamstone',
          stone_components(four_sides(tex('chiseled_gloamstone'), tex('gloamstone_tiles_top', 'gloamstone_tiles'))))

    side, top = tex('gloamstone_pillar_side'), tex('gloamstone_pillar_top')
    block('gloamstone_pillar', 'Gloamstone Pillar',
          stone_components({'*': mat(side), 'up': mat(top), 'down': mat(top)}),
          traits={'minecraft:placement_position': {'enabled_states': ['minecraft:block_face']}},
          permutations=[
              {'condition': "q.block_state('minecraft:block_face') == 'north' || q.block_state('minecraft:block_face') == 'south'",
               'components': {'minecraft:transformation': {'rotation': [90, 0, 0]}}},
              {'condition': "q.block_state('minecraft:block_face') == 'east' || q.block_state('minecraft:block_face') == 'west'",
               'components': {'minecraft:transformation': {'rotation': [0, 0, 90]}}},
          ],
          state_schema=[{'name': 'minecraft:block_face', 'type': 'string',
                         'values': ['down', 'up', 'north', 'south', 'west', 'east']}])

    # --- story murals & cipher stones ------------------------------------
    tiles_top = f'{NS}:gloamstone_tiles'
    perms = []
    for p in range(4):
        t = tex(f'glyph_mural_{p}')
        perms.append({'condition': f"q.block_state('rotu:panel') == {p}",
                      'components': {'minecraft:material_instances': four_sides(t, tiles_top)}})
    block('glyph_mural', 'Glyph Mural',
          dict(stone_components(four_sides(f'{NS}:glyph_mural_0', tiles_top)),
               **{'rotu:cycler': {'state': 'rotu:panel', 'count': 4}}),
          states={'rotu:panel': [0, 1, 2, 3]}, permutations=perms)

    perms = []
    for g in range(4):
        t = tex(f'cipher_stone_{g}')
        perms.append({'condition': f"q.block_state('rotu:glyph') == {g}",
                      'components': {'minecraft:material_instances': four_sides(t, tiles_top)}})
    block('cipher_stone', 'Cipher Stone',
          dict(stone_components(four_sides(f'{NS}:cipher_stone_0', tiles_top), light=3),
               **{'rotu:cycler': {'state': 'rotu:glyph', 'count': 4}}),
          states={'rotu:glyph': [0, 1, 2, 3]}, permutations=perms)

    # --- mechanisms ------------------------------------------------------
    c = stone_components(tex('singing_stone'), seconds=2.5, map_color='#4f6f78', light=6)
    c['rotu:singing_stone'] = {}
    c['minecraft:loot'] = 'loot_tables/rotu/blocks/singing_stone.json'
    block('singing_stone', 'Singing Stone', c, sound='amethyst_block')

    c = stone_components(four_sides(tex('choir_lantern'), tex('choir_lantern_top')), seconds=1.5,
                         map_color='#7fd8cf', light=15)
    block('choir_lantern', 'Choir Lantern', c, sound='lantern')

    dial_top = tex('glyph_dial_top')
    perms = []
    for g in range(4):
        t = tex(f'glyph_dial_{g}')
        perms.append({'condition': f"q.block_state('rotu:glyph') == {g}",
                      'components': {'minecraft:material_instances': four_sides(t, dial_top)}})
    c = stone_components(four_sides(f'{NS}:glyph_dial_0', dial_top), tags=())
    c['minecraft:destructible_by_mining'] = False
    c['minecraft:destructible_by_explosion'] = False
    c['minecraft:movable'] = IMMOVABLE
    c['rotu:glyph_dial'] = {}
    block('glyph_dial', 'Glyph Dial', c,
          states={'rotu:glyph': [0, 1, 2, 3], 'rotu:solution': [0, 1, 2, 3]}, permutations=perms)

    c = stone_components(four_sides(tex('sealed_gate'), tex('sealed_gate_top')), tags=())
    c['minecraft:destructible_by_mining'] = False
    c['minecraft:destructible_by_explosion'] = False
    c['minecraft:map_color'] = '#2a2733'
    c['minecraft:movable'] = IMMOVABLE
    block('sealed_gate', 'Sealed Gate', c)

    lock_on = tex('sigil_lock_on')
    c = stone_components(four_sides(tex('sigil_lock'), f'{NS}:sealed_gate_top'), tags=())
    c['minecraft:destructible_by_mining'] = False
    c['minecraft:destructible_by_explosion'] = False
    c['minecraft:movable'] = IMMOVABLE
    c['rotu:sigil_lock'] = {}
    block('sigil_lock', 'Sigil Lock', c, states={'rotu:unlocked': [False, True]},
          permutations=[{'condition': "q.block_state('rotu:unlocked')",
                         'components': {'minecraft:material_instances': four_sides(lock_on, f'{NS}:sealed_gate_top'),
                                        'minecraft:light_emission': 10}}],
          sound='vault')

    revealed = tex('veilstone_revealed')
    c = stone_components({'*': mat(f'{NS}:gloamstone_bricks', 'alpha_test')}, seconds=4.0)
    c['minecraft:loot'] = 'loot_tables/rotu/blocks/empty.json'
    c['minecraft:light_dampening'] = 15
    c['rotu:veilstone'] = {}
    block('veilstone', 'Veilstone', c, states={'rotu:revealed': [False, True]},
          permutations=[{'condition': "q.block_state('rotu:revealed')",
                         'components': {'minecraft:material_instances': {'*': mat(revealed, 'alpha_test')},
                                        'minecraft:collision_box': False,
                                        'minecraft:light_dampening': 0,
                                        'minecraft:light_emission': 4}}])

    plate = tex('hushing_plate')
    plate_spent = tex('hushing_plate_spent')
    c = {
        'minecraft:geometry': 'geometry.rotu.hushing_plate',
        'minecraft:material_instances': {'*': mat(plate)},
        'minecraft:collision_box': {'origin': [-8, 0, -8], 'size': [16, 1, 16]},
        'minecraft:selection_box': {'origin': [-8, 0, -8], 'size': [16, 1, 16]},
        'minecraft:destructible_by_mining': {'seconds_to_destroy': 1.5},
        'minecraft:destructible_by_explosion': {'explosion_resistance': 2},
        'minecraft:light_dampening': 0,
        'minecraft:map_color': '#2f2c38',
        'minecraft:tags': [PICKAXE],
        'minecraft:tick': {'interval_range': [200, 400], 'looping': True},
        'rotu:hushing_plate': {},
    }
    block('hushing_plate', 'Hushing Plate', c, states={'rotu:spent': [False, True]},
          permutations=[{'condition': "q.block_state('rotu:spent')",
                         'components': {'minecraft:material_instances': {'*': mat(plate_spent)}}}],
          sound='stone', full_solid=False)

    # --- urns ---------------------------------------------------------------
    perms = []
    for s in range(3):
        t = tex(f'funerary_urn_{s}')
        perms.append({'condition': f"q.block_state('rotu:style') == {s}",
                      'components': {'minecraft:material_instances': {'*': mat(t)}}})
    perms.append({'condition': "q.block_state('rotu:sealed')",
                  'components': {'minecraft:loot': 'loot_tables/rotu/blocks/urn_sealed.json'}})
    c = {
        'minecraft:geometry': 'geometry.rotu.funerary_urn',
        'minecraft:material_instances': {'*': mat(f'{NS}:funerary_urn_0')},
        'minecraft:collision_box': {'origin': [-5, 0, -5], 'size': [10, 14, 10]},
        'minecraft:selection_box': {'origin': [-5, 0, -5], 'size': [10, 14, 10]},
        'minecraft:destructible_by_mining': {'seconds_to_destroy': 0.4},
        'minecraft:destructible_by_explosion': {'explosion_resistance': 1},
        'minecraft:light_dampening': 0,
        'minecraft:map_color': '#6b5a4a',
        'minecraft:loot': 'loot_tables/rotu/blocks/urn_empty.json',
        'rotu:urn': {},
    }
    block('funerary_urn', 'Funerary Urn', c, states={'rotu:sealed': [False, True], 'rotu:style': [0, 1, 2]},
          permutations=perms, sound='decorated_pot', full_solid=False)

    # --- scriptorium desk ------------------------------------------------------
    desk = tex('scriptorium_desk')
    rot = []
    for d, y in (('north', 0), ('west', 90), ('south', 180), ('east', -90)):
        rot.append({'condition': f"q.block_state('minecraft:cardinal_direction') == '{d}'",
                    'components': {'minecraft:transformation': {'rotation': [0, y, 0]}}})
    c = {
        'minecraft:geometry': 'geometry.rotu.scriptorium_desk',
        'minecraft:material_instances': {'*': mat(desk)},
        'minecraft:collision_box': {'origin': [-8, 0, -8], 'size': [16, 14, 16]},
        'minecraft:selection_box': {'origin': [-8, 0, -8], 'size': [16, 16, 16]},
        'minecraft:destructible_by_mining': {'seconds_to_destroy': 2.5},
        'minecraft:destructible_by_explosion': {'explosion_resistance': 3},
        'minecraft:light_dampening': 0,
        'minecraft:light_emission': 5,
        'minecraft:map_color': '#4b3527',
        'minecraft:tags': [AXE],
        'rotu:scriptorium': {},
    }
    block('scriptorium_desk', 'Scriptorium Desk', c, category='items',
          traits={'minecraft:placement_direction': {'enabled_states': ['minecraft:cardinal_direction'],
                                                    'y_rotation_offset': 180}},
          permutations=rot, sound='wood', full_solid=False,
          state_schema=[{'name': 'minecraft:cardinal_direction', 'type': 'string',
                         'values': ['south', 'west', 'north', 'east']}])

    # --- reliquary -------------------------------------------------------------
    lesser, grand = tex('reliquary_lesser'), tex('reliquary_grand')
    c = {
        'minecraft:geometry': 'geometry.rotu.reliquary',
        'minecraft:material_instances': {'*': mat(lesser)},
        'minecraft:collision_box': {'origin': [-7, 0, -7], 'size': [14, 13, 14]},
        'minecraft:selection_box': {'origin': [-7, 0, -7], 'size': [14, 13, 14]},
        'minecraft:destructible_by_mining': False,
        'minecraft:destructible_by_explosion': False,
        'minecraft:light_dampening': 0,
        'minecraft:light_emission': 4,
        'minecraft:map_color': '#4a4258',
        'minecraft:loot': 'loot_tables/rotu/blocks/empty.json',
        'minecraft:tick': {'interval_range': [40, 60], 'looping': True},
        'minecraft:movable': IMMOVABLE,
        'rotu:reliquary': {},
    }
    block('reliquary', 'Reliquary', c, category='items', states={'rotu:tier': ['lesser', 'grand']},
          permutations=[{'condition': "q.block_state('rotu:tier') == 'grand'",
                         'components': {'minecraft:material_instances': {'*': mat(grand)},
                                        'minecraft:light_emission': 9}}],
          sound='vault', full_solid=False)

    # --- hidden spawn marker -------------------------------------------------------
    c = {
        'minecraft:geometry': 'minecraft:geometry.full_block',
        'minecraft:material_instances': {'*': mat(tex('spawn_marker'), 'alpha_test')},
        'minecraft:collision_box': False,
        'minecraft:selection_box': False,
        'minecraft:destructible_by_mining': False,
        'minecraft:destructible_by_explosion': False,
        'minecraft:light_dampening': 0,
        'minecraft:loot': 'loot_tables/rotu/blocks/empty.json',
        'minecraft:tick': {'interval_range': [20, 30], 'looping': True},
        'minecraft:movable': IMMOVABLE,
        'rotu:spawn_marker': {},
    }
    block('spawn_marker', 'Restless Remains', c, hidden=True,
          states={'rotu:mob': ['hushwalkers', 'murmurs', 'sentinel', 'cantor']},
          sound='stone', full_solid=False)

    REG.tr('rotu.block.hint.marker', 'Restless Remains')
