"""Resource-pack definitions: client entities, animations, render controllers, attachables, particles."""
from .registry import REG, NS, nid

ETEX = 'textures/rotu/entity/'

WALK = 'query.modified_distance_moved * 38.17'
SPEED = 'query.modified_move_speed'


def anim_file(name, animations):
    REG.add_rp(f'animations/{name}.animation.json', {'format_version': '1.10.0', 'animations': animations})


def rc_file(name, controllers):
    REG.add_rp(f'render_controllers/{name}.render_controllers.json',
               {'format_version': '1.10.0', 'render_controllers': controllers})


def client_entity(name, *, materials, textures, geometry, animations, animate, render_controllers,
                  egg=None, particles=None, scripts_extra=None):
    desc = {
        'identifier': nid(name),
        'materials': materials,
        'textures': textures,
        'geometry': geometry,
        'animations': animations,
        'scripts': {'animate': animate},
        'render_controllers': render_controllers,
    }
    if scripts_extra:
        desc['scripts'].update(scripts_extra)
    if egg:
        desc['spawn_egg'] = {'base_color': egg[0], 'overlay_color': egg[1]}
    if particles:
        desc['particle_effects'] = particles
    REG.add_rp(f'entity/{name}.entity.json', {'format_version': '1.10.0', 'minecraft:client_entity': {'description': desc}})


LOOK = {'head': {'rotation': ['query.target_x_rotation', 'query.target_y_rotation', 0]}}


def define_client():
    # ------------------------------------------------------------ Hushwalker
    anim_file('hushwalker', {
        'animation.rotu.hushwalker.look': {'loop': True, 'bones': LOOK},
        'animation.rotu.hushwalker.move': {'loop': True, 'bones': {
            'rightLeg': {'rotation': [f'math.cos({WALK}) * 34.0 * {SPEED}', 0, 0]},
            'leftLeg': {'rotation': [f'math.cos({WALK} + 180.0) * 34.0 * {SPEED}', 0, 0]},
            'rightArm': {'rotation': [f'-28.0 + math.cos({WALK} + 180.0) * 12.0 * {SPEED}', 0, 4.0]},
            'leftArm': {'rotation': [f'-28.0 + math.cos({WALK}) * 12.0 * {SPEED}', 0, -4.0]},
            'body': {'rotation': [4.0, 0, f'math.cos(query.modified_distance_moved * 19.0) * 4.0 * {SPEED}']},
        }},
        'animation.rotu.hushwalker.idle': {'loop': True, 'bones': {
            'head': {'rotation': ['math.sin(query.life_time * 40.0) * 3.0', 0, 'math.sin(query.life_time * 23.0) * 7.0']},
            'rightArm': {'rotation': ['math.sin(query.life_time * 50.0) * 2.0', 0, 0]},
            'leftArm': {'rotation': ['math.sin(query.life_time * 50.0 + 90.0) * 2.0', 0, 0]},
        }},
        'animation.rotu.hushwalker.attack': {'loop': True, 'bones': {
            'rightArm': {'rotation': ['-60.0 - math.sin(variable.attack_time * 180.0) * 70.0', 0, 0]},
            'leftArm': {'rotation': ['-60.0 - math.sin(variable.attack_time * 180.0) * 70.0', 0, 0]},
        }},
    })
    rc_file('hushwalker', {
        'controller.render.rotu.hushwalker': {
            'arrays': {'textures': {'Array.skins': ['Texture.v0', 'Texture.v1', 'Texture.v2']}},
            'geometry': 'Geometry.default',
            'materials': [{'*': 'Material.default'}],
            'textures': ['Array.skins[query.variant]'],
        },
        'controller.render.rotu.hushwalker_eyes': {
            'geometry': 'Geometry.default',
            'materials': [{'*': 'Material.default'}],
            'textures': ['Texture.eyes'],
            'ignore_lighting': True,
            'part_visibility': [{'*': False}, {'head': '!query.is_invisible'}],
        },
    })
    client_entity('hushwalker',
                  materials={'default': 'entity_alphatest'},
                  textures={'v0': ETEX + 'hushwalker_0', 'v1': ETEX + 'hushwalker_1', 'v2': ETEX + 'hushwalker_2',
                            'eyes': ETEX + 'hushwalker_eyes'},
                  geometry={'default': 'geometry.rotu.hushwalker'},
                  animations={'look': 'animation.rotu.hushwalker.look', 'move': 'animation.rotu.hushwalker.move',
                              'idle': 'animation.rotu.hushwalker.idle', 'attack': 'animation.rotu.hushwalker.attack'},
                  animate=['look', 'move', 'idle', {'attack': 'variable.attack_time > 0.0'}],
                  render_controllers=['controller.render.rotu.hushwalker', 'controller.render.rotu.hushwalker_eyes'],
                  egg=('#2b2733', '#9be9de'))

    # ------------------------------------------------------------ Murmur
    anim_file('murmur', {
        'animation.rotu.murmur.look': {'loop': True, 'bones': LOOK},
        'animation.rotu.murmur.float': {'loop': True, 'bones': {
            'root': {'position': [0, 'math.sin(query.life_time * 120.0) * 1.2', 0]},
            'tail1': {'rotation': ['math.sin(query.life_time * 150.0) * 14.0', 0, 'math.cos(query.life_time * 90.0) * 8.0']},
            'tail2': {'rotation': ['math.sin(query.life_time * 150.0 - 50.0) * 22.0', 0, 0]},
            'rightArm': {'rotation': ['-15.0 + math.sin(query.life_time * 110.0) * 10.0', 0, 10.0]},
            'leftArm': {'rotation': ['-15.0 + math.sin(query.life_time * 110.0 + 120.0) * 10.0', 0, -10.0]},
        }, 'animation_length': 1.0, 'particle_effects': {'0.0': {'effect': 'trail'}}},
        'animation.rotu.murmur.charge': {'loop': True, 'bones': {
            'rightArm': {'rotation': [-95.0, 8.0, 0]},
            'leftArm': {'rotation': [-95.0, -8.0, 0]},
            'head': {'rotation': [-10.0, 0, 0]},
        }},
    })
    rc_file('murmur', {
        'controller.render.rotu.murmur': {
            'geometry': 'Geometry.default',
            'materials': [{'*': 'Material.default'}],
            'textures': ['Texture.default'],
            'ignore_lighting': True,
        },
    })
    client_entity('murmur',
                  materials={'default': 'entity_alphablend'},
                  textures={'default': ETEX + 'murmur'},
                  geometry={'default': 'geometry.rotu.murmur'},
                  animations={'look': 'animation.rotu.murmur.look', 'float': 'animation.rotu.murmur.float',
                              'charge': 'animation.rotu.murmur.charge'},
                  animate=['look', 'float', {'charge': 'query.is_charging'}],
                  render_controllers=['controller.render.rotu.murmur'],
                  egg=('#6fb3ad', '#e5fbf7'),
                  particles={'trail': 'rotu:murmur_trail'})

    # ------------------------------------------------------------ Graven Sentinel
    anim_file('graven_sentinel', {
        'animation.rotu.graven_sentinel.look': {'loop': True, 'bones': {
            'head': {'rotation': ['query.variant == 0 ? 0 : query.target_x_rotation',
                                  'query.variant == 0 ? 0 : query.target_y_rotation', 0]}}},
        'animation.rotu.graven_sentinel.dormant': {'loop': True, 'bones': {
            'head': {'rotation': [28.0, 0, 0]},
            'rightArm': {'rotation': [-38.0, -20.0, 8.0]},
            'leftArm': {'rotation': [-38.0, 20.0, -8.0]},
            'body': {'rotation': [6.0, 0, 0]},
        }},
        'animation.rotu.graven_sentinel.move': {'loop': True, 'bones': {
            'rightLeg': {'rotation': [f'math.cos({WALK} * 0.7) * 24.0 * {SPEED}', 0, 0]},
            'leftLeg': {'rotation': [f'math.cos({WALK} * 0.7 + 180.0) * 24.0 * {SPEED}', 0, 0]},
            'rightArm': {'rotation': [f'math.cos({WALK} * 0.7 + 180.0) * 16.0 * {SPEED}', 0, 0]},
            'leftArm': {'rotation': [f'math.cos({WALK} * 0.7) * 16.0 * {SPEED}', 0, 0]},
            'body': {'rotation': [0, f'math.cos({WALK} * 0.35) * 5.0 * {SPEED}', 0]},
        }},
        'animation.rotu.graven_sentinel.attack': {'loop': True, 'bones': {
            'rightArm': {'rotation': ['-130.0 * math.sin(variable.attack_time * 180.0)', 0, 0]},
            'leftArm': {'rotation': ['-130.0 * math.sin(variable.attack_time * 180.0)', 0, 0]},
            'body': {'rotation': ['12.0 * math.sin(variable.attack_time * 180.0)', 0, 0]},
        }},
        'animation.rotu.graven_sentinel.breathe': {'loop': True, 'bones': {
            'body': {'scale': [1.0, '1.0 + math.sin(query.life_time * 60.0) * 0.008', 1.0]},
        }},
    })
    rc_file('graven_sentinel', {
        'controller.render.rotu.graven_sentinel': {
            'geometry': 'Geometry.default',
            'materials': [{'*': 'Material.default'}],
            'textures': ['Texture.default'],
        },
        'controller.render.rotu.graven_sentinel_glow': {
            'geometry': 'Geometry.default',
            'materials': [{'*': 'Material.default'}],
            'textures': ['Texture.glow'],
            'ignore_lighting': True,
            'part_visibility': [{'*': 'query.variant == 1 && !query.is_invisible'}],
        },
    })
    client_entity('graven_sentinel',
                  materials={'default': 'entity_alphatest'},
                  textures={'default': ETEX + 'graven_sentinel', 'glow': ETEX + 'graven_sentinel_glow'},
                  geometry={'default': 'geometry.rotu.graven_sentinel'},
                  animations={'look': 'animation.rotu.graven_sentinel.look',
                              'dormant': 'animation.rotu.graven_sentinel.dormant',
                              'move': 'animation.rotu.graven_sentinel.move',
                              'attack': 'animation.rotu.graven_sentinel.attack',
                              'breathe': 'animation.rotu.graven_sentinel.breathe'},
                  animate=['look', {'dormant': 'query.variant == 0'}, {'move': 'query.variant == 1'},
                           {'breathe': 'query.variant == 1'}, {'attack': 'variable.attack_time > 0.0'}],
                  render_controllers=['controller.render.rotu.graven_sentinel',
                                      'controller.render.rotu.graven_sentinel_glow'],
                  egg=('#4c4858', '#55c2b9'))

    # ------------------------------------------------------------ The Last Cantor
    anim_file('last_cantor', {
        'animation.rotu.last_cantor.look': {'loop': True, 'bones': LOOK},
        'animation.rotu.last_cantor.float': {'loop': True, 'bones': {
            'root': {'position': [0, '2.0 + math.sin(query.life_time * 70.0) * 1.5', 0]},
            'body': {'rotation': ['math.sin(query.life_time * 35.0) * 2.0', 0, 'math.cos(query.life_time * 45.0) * 2.0']},
            'rightArm': {'rotation': ['-10.0 + math.sin(query.life_time * 60.0) * 5.0', 0, 6.0]},
            'leftArm': {'rotation': ['-10.0 + math.sin(query.life_time * 60.0 + 90.0) * 5.0', 0, -6.0]},
        }},
        'animation.rotu.last_cantor.halo': {'loop': True, 'bones': {
            'halo': {'rotation': [0, 'query.life_time * 45.0', 0]},
        }},
        'animation.rotu.last_cantor.cast': {'loop': True, 'bones': {
            'rightArm': {'rotation': ['-150.0 + math.sin(query.life_time * 400.0) * 8.0', 0, 18.0]},
            'leftArm': {'rotation': ['-150.0 + math.sin(query.life_time * 400.0 + 90.0) * 8.0', 0, -18.0]},
            'head': {'rotation': [-15.0, 0, 0]},
        }},
        'animation.rotu.last_cantor.attack': {'loop': True, 'bones': {
            'rightArm': {'rotation': ['-90.0 * math.sin(variable.attack_time * 180.0)', 0, 0]},
        }},
    })
    rc_file('last_cantor', {
        'controller.render.rotu.last_cantor': {
            'arrays': {'textures': {'Array.skins': ['Texture.phase0', 'Texture.phase1']}},
            'geometry': 'Geometry.default',
            'materials': [{'*': 'Material.default'}],
            'textures': ['Array.skins[query.variant]'],
        },
        'controller.render.rotu.last_cantor_glow': {
            'arrays': {'textures': {'Array.glow': ['Texture.glow0', 'Texture.glow1']}},
            'geometry': 'Geometry.default',
            'materials': [{'*': 'Material.default'}],
            'textures': ['Array.glow[query.variant]'],
            'ignore_lighting': True,
            'part_visibility': [{'*': '!query.is_invisible'}],
        },
    })
    client_entity('last_cantor',
                  materials={'default': 'entity_alphatest'},
                  textures={'phase0': ETEX + 'last_cantor_0', 'phase1': ETEX + 'last_cantor_1',
                            'glow0': ETEX + 'last_cantor_glow_0', 'glow1': ETEX + 'last_cantor_glow_1'},
                  geometry={'default': 'geometry.rotu.last_cantor'},
                  animations={'look': 'animation.rotu.last_cantor.look', 'float': 'animation.rotu.last_cantor.float',
                              'halo': 'animation.rotu.last_cantor.halo', 'cast': 'animation.rotu.last_cantor.cast',
                              'attack': 'animation.rotu.last_cantor.attack'},
                  animate=['look', 'float', 'halo', {'cast': 'query.is_casting'},
                           {'attack': 'variable.attack_time > 0.0'}],
                  render_controllers=['controller.render.rotu.last_cantor', 'controller.render.rotu.last_cantor_glow'],
                  egg=('#16111e', '#d1ac45'))

    # ------------------------------------------------------------ Hush bolt
    anim_file('hush_bolt', {
        'animation.rotu.hush_bolt.spin': {'loop': True, 'animation_length': 1.0, 'bones': {
            'bolt': {'rotation': ['query.life_time * 360.0', 'query.life_time * 280.0', 0]}},
            'particle_effects': {'0.0': {'effect': 'trail'}}},
    })
    rc_file('hush_bolt', {
        'controller.render.rotu.hush_bolt': {
            'geometry': 'Geometry.default',
            'materials': [{'*': 'Material.default'}],
            'textures': ['Texture.default'],
            'ignore_lighting': True,
        },
    })
    client_entity('hush_bolt',
                  materials={'default': 'entity_alphablend'},
                  textures={'default': ETEX + 'hush_bolt'},
                  geometry={'default': 'geometry.rotu.hush_bolt'},
                  animations={'spin': 'animation.rotu.hush_bolt.spin'},
                  animate=['spin'],
                  render_controllers=['controller.render.rotu.hush_bolt'],
                  particles={'trail': 'rotu:murmur_trail'})

    # ------------------------------------------------------------ armor attachables
    for item, slot, geo_h, geo_p, tex, anim in (
        ('choristers_mask', 'helmet', 'geometry.humanoid.armor.helmet', 'geometry.player.armor.helmet',
         'textures/rotu/models/armor/choristers_mask', 'animation.armor.helmet.offset'),
        ('hushweave_mantle', 'chestplate', 'geometry.humanoid.armor.chestplate', 'geometry.player.armor.chestplate',
         'textures/rotu/models/armor/hushweave_mantle', 'animation.armor.chestplate.offset'),
    ):
        layer_var = 'variable.helmet_layer_visible = 0.0;' if slot == 'helmet' else 'variable.chest_layer_visible = 0.0;'
        REG.add_rp(f'attachables/{item}.json', {'format_version': '1.8.0', 'minecraft:attachable': {'description': {
            'identifier': nid(item),
            'materials': {'default': 'armor', 'enchanted': 'armor_enchanted'},
            'textures': {'default': tex, 'enchanted': 'textures/misc/enchanted_actor_glint'},
            'geometry': {'default': geo_h},
            'scripts': {'parent_setup': layer_var},
            'render_controllers': ['controller.render.armor'],
        }}})
        desc = {
            'identifier': nid(item) + '.player',
            'item': {nid(item): "query.owner_identifier == 'minecraft:player'"},
            'materials': {'default': 'armor', 'enchanted': 'armor_enchanted'},
            'textures': {'default': tex, 'enchanted': 'textures/misc/enchanted_actor_glint'},
            'geometry': {'default': geo_p},
            'scripts': {'parent_setup': layer_var},
            'render_controllers': ['controller.render.armor'],
        }
        if anim:
            desc['scripts']['animate'] = ['offset']
            desc['animations'] = {'offset': anim}
        REG.add_rp(f'attachables/{item}.player.json', {'format_version': '1.10.0',
                                                       'minecraft:attachable': {'description': desc}})

    define_particles()


def particle(name, *, texture, components, material='particles_alpha'):
    REG.add_rp(f'particles/{name}.particle.json', {
        'format_version': '1.10.0',
        'particle_effect': {
            'description': {
                'identifier': nid(name),
                'basic_render_parameters': {'material': material, 'texture': texture},
            },
            'components': components,
        },
    })


def _billboard(size, w=8, h=8):
    return {
        'size': [size, size],
        'facing_camera_mode': 'rotate_xyz',
        'uv': {'texture_width': w, 'texture_height': h, 'uv': [0, 0], 'uv_size': [w, h]},
    }


def define_particles():
    mote = 'textures/rotu/particle/mote'
    dust = 'textures/rotu/particle/dust'
    teal = {'gradient': {'0.0': '#FF9BE9DE', '0.6': '#FF55C2B9', '1.0': '#002F8F8A'},
            'interpolant': 'v.particle_age / v.particle_lifetime'}
    particle('glyph_motes', texture=mote, material='particles_add', components={
        'minecraft:emitter_rate_instant': {'num_particles': 'math.random_integer(6, 10)'},
        'minecraft:emitter_lifetime_once': {'active_time': 0.2},
        'minecraft:emitter_shape_sphere': {'radius': 0.55, 'direction': 'outwards'},
        'minecraft:particle_lifetime_expression': {'max_lifetime': 'math.random(1.2, 2.0)'},
        'minecraft:particle_initial_speed': 0.15,
        'minecraft:particle_motion_dynamic': {'linear_acceleration': [0, 0.35, 0], 'linear_drag_coefficient': 1.5},
        'minecraft:particle_appearance_billboard': _billboard('0.07 + v.particle_random_1 * 0.05'),
        'minecraft:particle_appearance_tinting': {'color': teal},
        'minecraft:particle_appearance_lighting': {},
    })
    particle('reveal_burst', texture=mote, material='particles_add', components={
        'minecraft:emitter_rate_instant': {'num_particles': 28},
        'minecraft:emitter_lifetime_once': {'active_time': 0.1},
        'minecraft:emitter_shape_box': {'half_dimensions': [0.5, 0.5, 0.5], 'direction': 'outwards'},
        'minecraft:particle_lifetime_expression': {'max_lifetime': 'math.random(0.6, 1.2)'},
        'minecraft:particle_initial_speed': 0.9,
        'minecraft:particle_motion_dynamic': {'linear_drag_coefficient': 3.0},
        'minecraft:particle_appearance_billboard': _billboard('0.1 * (1 - v.particle_age / v.particle_lifetime)'),
        'minecraft:particle_appearance_tinting': {'color': teal},
    })
    particle('hush_dust', texture=dust, components={
        'minecraft:emitter_rate_instant': {'num_particles': 24},
        'minecraft:emitter_lifetime_once': {'active_time': 0.1},
        'minecraft:emitter_shape_box': {'half_dimensions': [0.5, 0.5, 0.5], 'direction': 'outwards'},
        'minecraft:particle_lifetime_expression': {'max_lifetime': 'math.random(0.8, 1.6)'},
        'minecraft:particle_initial_speed': 0.5,
        'minecraft:particle_motion_dynamic': {'linear_acceleration': [0, -0.6, 0], 'linear_drag_coefficient': 2.0},
        'minecraft:particle_appearance_billboard': _billboard('0.12 + v.particle_random_1 * 0.08'),
        'minecraft:particle_appearance_tinting': {'color': ['0.45', '0.43', '0.5', '1.0 - v.particle_age / v.particle_lifetime']},
        'minecraft:particle_appearance_lighting': {},
    })
    particle('murmur_trail', texture=mote, material='particles_add', components={
        'minecraft:emitter_rate_steady': {'spawn_rate': 6, 'max_particles': 12},
        'minecraft:emitter_lifetime_once': {'active_time': 1.0},
        'minecraft:emitter_shape_point': {'offset': [0, 0.3, 0]},
        'minecraft:particle_lifetime_expression': {'max_lifetime': 'math.random(0.6, 1.2)'},
        'minecraft:particle_initial_speed': 0.05,
        'minecraft:particle_motion_dynamic': {'linear_acceleration': [0, 0.2, 0]},
        'minecraft:particle_appearance_billboard': _billboard('0.06 * (1 - v.particle_age / v.particle_lifetime)'),
        'minecraft:particle_appearance_tinting': {'color': teal},
    })
    particle('star_burst', texture=mote, material='particles_add', components={
        'minecraft:emitter_rate_instant': {'num_particles': 80},
        'minecraft:emitter_lifetime_once': {'active_time': 0.1},
        'minecraft:emitter_shape_sphere': {'radius': 0.4, 'direction': 'outwards'},
        'minecraft:particle_lifetime_expression': {'max_lifetime': 'math.random(1.0, 2.2)'},
        'minecraft:particle_initial_speed': 'math.random(1.5, 3.5)',
        'minecraft:particle_motion_dynamic': {'linear_drag_coefficient': 2.2},
        'minecraft:particle_appearance_billboard': _billboard('0.15 * (1 - v.particle_age / v.particle_lifetime)'),
        'minecraft:particle_appearance_tinting': {'color': {
            'gradient': {'0.0': '#FFFFFFFF', '0.3': '#FF9BE9DE', '1.0': '#003B2D5A'},
            'interpolant': 'v.particle_age / v.particle_lifetime'}},
    })
