"""Custom entity behavior definitions, spawn rules and client entity wiring."""
from .registry import REG, NS, FORMAT_ENTITY, FORMAT_SPAWN, nid

HOSTILE_TARGETS = {
    'any_of': [
        {'test': 'is_family', 'subject': 'other', 'value': 'player'},
        {'test': 'is_family', 'subject': 'other', 'value': 'irongolem'},
        {'test': 'is_family', 'subject': 'other', 'value': 'snowgolem'},
        {'test': 'is_family', 'subject': 'other', 'value': 'villager'},
        {'test': 'is_family', 'subject': 'other', 'value': 'wandering_trader'},
    ]
}
PLAYER_ONLY = {'test': 'is_family', 'subject': 'other', 'value': 'player'}

GLOAMSTONE_FLOORS = [
    'rotu:gloamstone_bricks', 'rotu:cracked_gloamstone_bricks', 'rotu:mossy_gloamstone_bricks',
    'rotu:gloamstone_tiles', 'rotu:chiseled_gloamstone',
]


def entity(name, en, description_extra, components, groups=None, events=None):
    ident = nid(name)
    desc = {'identifier': ident}
    desc.update(description_extra)
    body = {'description': desc, 'components': components}
    if groups:
        body['component_groups'] = groups
    if events:
        body['events'] = events
    REG.add_bp(f'entities/{name}.json', {'format_version': FORMAT_ENTITY, 'minecraft:entity': body})
    REG.tr(f'entity.{ident}.name', en)
    REG.tr(f'item.spawn_egg.entity.{ident}.name', f'Spawn {en}')
    return ident


def common_mob(health, width, height, family):
    return {
        'minecraft:type_family': {'family': family},
        'minecraft:health': {'value': health, 'max': health},
        'minecraft:collision_box': {'width': width, 'height': height},
        'minecraft:nameable': {},
        'minecraft:conditional_bandwidth_optimization': {},
        'minecraft:is_hidden_when_invisible': {},
    }


def define_entities():
    # ------------------------------------------------------------------ Hushwalker
    c = common_mob(24, 0.6, 1.95, ['hushwalker', 'unnamed', 'undead', 'monster', 'mob'])
    c.update({
        'minecraft:attack': {'damage': 4, 'effect_name': 'slowness', 'effect_duration': 3},
        'minecraft:movement': {'value': 0.22},
        'minecraft:movement.basic': {},
        'minecraft:navigation.walk': {'can_pass_doors': True, 'can_walk': True, 'avoid_water': True,
                                      'avoid_damage_blocks': True},
        'minecraft:jump.static': {},
        'minecraft:can_climb': {},
        'minecraft:physics': {},
        'minecraft:pushable_by_entity': {},
        'minecraft:pushable_by_block': {},
        'minecraft:burns_in_daylight': {},
        'minecraft:breathable': {'total_supply': 15, 'suffocate_time': 0, 'breathes_air': True,
                                 'breathes_water': True},
        'minecraft:despawn': {'despawn_from_distance': {}},
        'minecraft:experience_reward': {'on_death': 'query.last_hit_by_player ? 6 : 0'},
        'minecraft:loot': {'table': 'loot_tables/rotu/entities/hushwalker.json'},
        'minecraft:follow_range': {'value': 24, 'max': 24},
        'minecraft:hurt_on_condition': {'damage_conditions': [
            {'filters': {'test': 'in_lava', 'subject': 'self'}, 'cause': 'lava', 'damage_per_tick': 4}]},
        'minecraft:ambient_sound_interval': {'event_name': 'ambient', 'range': 8, 'value': 6},
        'minecraft:behavior.float': {'priority': 0},
        'minecraft:behavior.hurt_by_target': {'priority': 1},
        'minecraft:behavior.nearest_attackable_target': {
            'priority': 2, 'must_see': True, 'reselect_targets': True, 'within_radius': 20,
            'must_see_forget_duration': 8,
            'entity_types': [{'filters': HOSTILE_TARGETS, 'max_dist': 20}]},
        'minecraft:behavior.melee_box_attack': {'priority': 3, 'speed_multiplier': 1.15, 'track_target': False},
        'minecraft:behavior.random_stroll': {'priority': 6, 'speed_multiplier': 0.7},
        'minecraft:behavior.look_at_player': {'priority': 7, 'look_distance': 8},
        'minecraft:behavior.random_look_around': {'priority': 8},
    })
    groups = {f'rotu:variant_{i}': {'minecraft:variant': {'value': i}} for i in range(3)}
    events = {
        'minecraft:entity_spawned': {'randomize': [
            {'weight': 45, 'add': {'component_groups': ['rotu:variant_0']}},
            {'weight': 35, 'add': {'component_groups': ['rotu:variant_1']}},
            {'weight': 20, 'add': {'component_groups': ['rotu:variant_2']}},
        ]},
    }
    entity('hushwalker', 'Hushwalker',
           {'spawn_category': 'monster', 'is_spawnable': True, 'is_summonable': True}, c, groups, events)

    REG.add_bp('spawn_rules/hushwalker.json', {
        'format_version': FORMAT_SPAWN,
        'minecraft:spawn_rules': {
            'description': {'identifier': nid('hushwalker'), 'population_control': 'monster'},
            'conditions': [
                {
                    'minecraft:spawns_on_surface': {},
                    'minecraft:spawns_on_block_filter': GLOAMSTONE_FLOORS,
                    'minecraft:brightness_filter': {'min': 0, 'max': 7, 'adjust_for_weather': True},
                    'minecraft:difficulty_filter': {'min': 'easy', 'max': 'hard'},
                    'minecraft:weight': {'default': 60},
                    'minecraft:density_limit': {'surface': 6},
                    'minecraft:herd': {'min_size': 1, 'max_size': 2},
                    'minecraft:biome_filter': {'test': 'has_biome_tag', 'operator': '==', 'value': 'overworld'},
                },
                {
                    'minecraft:spawns_underground': {},
                    'minecraft:spawns_on_block_filter': GLOAMSTONE_FLOORS,
                    'minecraft:brightness_filter': {'min': 0, 'max': 7, 'adjust_for_weather': False},
                    'minecraft:difficulty_filter': {'min': 'easy', 'max': 'hard'},
                    'minecraft:weight': {'default': 60},
                    'minecraft:density_limit': {'underground': 6},
                    'minecraft:herd': {'min_size': 1, 'max_size': 3},
                    'minecraft:biome_filter': {'test': 'has_biome_tag', 'operator': '==', 'value': 'overworld'},
                },
            ],
        },
    })

    # ------------------------------------------------------------------ Murmur
    c = common_mob(10, 0.5, 0.9, ['murmur', 'unnamed', 'undead', 'monster', 'mob'])
    c.update({
        'minecraft:attack': {'damage': 2, 'effect_name': 'darkness', 'effect_duration': 4},
        'minecraft:movement': {'value': 0.75},
        'minecraft:movement.basic': {},
        'minecraft:navigation.walk': {'can_path_over_water': True, 'using_door_annotation': True},
        'minecraft:jump.static': {},
        'minecraft:can_climb': {},
        'minecraft:physics': {'has_collision': False, 'has_gravity': False},
        'minecraft:fire_immune': {},
        'minecraft:despawn': {'despawn_from_distance': {}},
        'minecraft:experience_reward': {'on_death': 'query.last_hit_by_player ? 4 : 0'},
        'minecraft:loot': {'table': 'loot_tables/rotu/entities/murmur.json'},
        'minecraft:ambient_sound_interval': {'event_name': 'ambient', 'range': 6, 'value': 4},
        'minecraft:damage_sensor': {'triggers': [{'cause': 'fall', 'deals_damage': 'no'},
                                                 {'cause': 'suffocation', 'deals_damage': 'no'}]},
        'minecraft:behavior.float': {'priority': 0},
        'minecraft:behavior.hurt_by_target': {'priority': 1},
        'minecraft:behavior.nearest_attackable_target': {
            'priority': 2, 'must_see': False, 'reselect_targets': True, 'within_radius': 18,
            'entity_types': [{'filters': PLAYER_ONLY, 'max_dist': 18}]},
        'minecraft:behavior.charge_attack': {'priority': 3, 'speed_multiplier': 0.85, 'success_rate': 0.15},
        'minecraft:behavior.look_at_player': {'priority': 8, 'look_distance': 10},
        'minecraft:behavior.random_look_around': {'priority': 9},
    })
    groups = {
        'rotu:temporary': {'minecraft:timer': {'looping': False, 'randomInterval': True, 'time': [25, 45],
                                               'time_down_event': {'event': 'rotu:fade', 'target': 'self'}}},
        'rotu:faded': {'minecraft:instant_despawn': {}},
    }
    events = {
        'rotu:temporary': {'add': {'component_groups': ['rotu:temporary']}},
        'rotu:fade': {'add': {'component_groups': ['rotu:faded']}},
    }
    entity('murmur', 'Murmur', {'spawn_category': 'monster', 'is_spawnable': True, 'is_summonable': True},
           c, groups, events)

    REG.add_bp('spawn_rules/murmur.json', {
        'format_version': FORMAT_SPAWN,
        'minecraft:spawn_rules': {
            'description': {'identifier': nid('murmur'), 'population_control': 'monster'},
            'conditions': [{
                'minecraft:spawns_underground': {},
                'minecraft:spawns_on_block_filter': GLOAMSTONE_FLOORS,
                'minecraft:brightness_filter': {'min': 0, 'max': 4, 'adjust_for_weather': False},
                'minecraft:difficulty_filter': {'min': 'easy', 'max': 'hard'},
                'minecraft:weight': {'default': 15},
                'minecraft:density_limit': {'underground': 3},
                'minecraft:herd': {'min_size': 1, 'max_size': 1},
                'minecraft:biome_filter': {'test': 'has_biome_tag', 'operator': '==', 'value': 'overworld'},
            }],
        },
    })

    # ------------------------------------------------------------------ Graven Sentinel
    def sentinel_damage_sensor(awaken):
        triggers = [
            {'cause': 'fall', 'deals_damage': 'no'},
            {'cause': 'projectile', 'damage_multiplier': 0.5},
        ]
        if awaken:
            triggers.insert(0, {'on_damage': {'filters': {'test': 'is_family', 'subject': 'other', 'value': 'player'},
                                              'event': 'rotu:awaken'}, 'deals_damage': 'yes'})
        return {'triggers': triggers}

    c = common_mob(90, 1.2, 2.8, ['graven_sentinel', 'unnamed', 'construct', 'monster', 'mob'])
    c.update({
        'minecraft:attack': {'damage': {'range_min': 8, 'range_max': 13}},
        'minecraft:knockback_resistance': {'value': 1.0},
        'minecraft:movement.basic': {},
        'minecraft:navigation.walk': {'can_walk': True, 'avoid_water': True, 'can_pass_doors': True,
                                      'avoid_damage_blocks': True},
        'minecraft:jump.static': {},
        'minecraft:physics': {},
        'minecraft:pushable_by_block': {},
        'minecraft:fire_immune': {},
        'minecraft:persistent': {},
        'minecraft:breathable': {'total_supply': 15, 'suffocate_time': 0, 'breathes_air': True,
                                 'breathes_water': True},
        'minecraft:experience_reward': {'on_death': 'query.last_hit_by_player ? 35 : 0'},
        'minecraft:loot': {'table': 'loot_tables/rotu/entities/graven_sentinel.json'},
        'minecraft:follow_range': {'value': 28, 'max': 28},
        'minecraft:home': {'restriction_radius': 14, 'restriction_type': 'random_movement'},
    })
    groups = {
        'rotu:dormant': {
            'minecraft:movement': {'value': 0.0},
            'minecraft:variant': {'value': 0},
            'minecraft:body_rotation_blocked': {},
            'minecraft:damage_sensor': sentinel_damage_sensor(True),
            'minecraft:entity_sensor': {
                'relative_range': False,
                'subsensors': [{
                    'range': [4.5, 3.0], 'minimum_count': 1,
                    'event_filters': {'all_of': [PLAYER_ONLY,
                                                 {'test': 'has_ability', 'subject': 'other', 'operator': '!=',
                                                  'value': 'instabuild'}]},
                    'event': 'rotu:awaken'}],
            },
        },
        'rotu:awakening': {
            'minecraft:movement': {'value': 0.0},
            'minecraft:variant': {'value': 1},
            'minecraft:damage_sensor': sentinel_damage_sensor(False),
            'minecraft:timer': {'looping': False, 'time': 2.2,
                                'time_down_event': {'event': 'rotu:activated', 'target': 'self'}},
        },
        'rotu:active': {
            'minecraft:movement': {'value': 0.23},
            'minecraft:variant': {'value': 1},
            'minecraft:damage_sensor': sentinel_damage_sensor(False),
            'minecraft:behavior.hurt_by_target': {'priority': 1},
            'minecraft:behavior.nearest_attackable_target': {
                'priority': 2, 'must_see': False, 'reselect_targets': True, 'within_radius': 24,
                'entity_types': [{'filters': HOSTILE_TARGETS, 'max_dist': 24}]},
            'minecraft:behavior.melee_box_attack': {'priority': 3, 'speed_multiplier': 1.1, 'track_target': True,
                                                    'cooldown_time': 1.4, 'horizontal_reach': 0.6},
            'minecraft:behavior.move_towards_home_restriction': {'priority': 5, 'speed_multiplier': 0.8},
            'minecraft:behavior.random_stroll': {'priority': 7, 'speed_multiplier': 0.6, 'interval': 160},
            'minecraft:behavior.look_at_player': {'priority': 8, 'look_distance': 10},
        },
    }
    events = {
        'minecraft:entity_spawned': {'add': {'component_groups': ['rotu:dormant']}},
        'rotu:awaken': {'remove': {'component_groups': ['rotu:dormant']},
                        'add': {'component_groups': ['rotu:awakening']}},
        'rotu:activated': {'remove': {'component_groups': ['rotu:awakening']},
                           'add': {'component_groups': ['rotu:active']}},
    }
    entity('graven_sentinel', 'Graven Sentinel',
           {'spawn_category': 'monster', 'is_spawnable': True, 'is_summonable': True}, c, groups, events)

    # ------------------------------------------------------------------ The Last Cantor
    c = common_mob(280, 0.9, 3.2, ['last_cantor', 'unnamed', 'undead', 'monster', 'mob'])
    c.update({
        'minecraft:boss': {'hud_range': 48, 'should_darken_sky': True},
        'minecraft:knockback_resistance': {'value': 0.8},
        'minecraft:attack': {'damage': 9},
        'minecraft:movement.basic': {},
        'minecraft:navigation.walk': {'can_walk': True, 'avoid_water': True, 'can_pass_doors': True},
        'minecraft:jump.static': {},
        'minecraft:physics': {},
        'minecraft:pushable_by_block': {},
        'minecraft:fire_immune': {},
        'minecraft:persistent': {},
        'minecraft:breathable': {'total_supply': 15, 'suffocate_time': 0, 'breathes_air': True,
                                 'breathes_water': True},
        'minecraft:damage_sensor': {'triggers': [{'cause': 'fall', 'deals_damage': 'no'},
                                                 {'cause': 'suffocation', 'deals_damage': 'no'},
                                                 {'cause': 'magic', 'damage_multiplier': 0.5}]},
        'minecraft:experience_reward': {'on_death': 'query.last_hit_by_player ? 250 : 0'},
        'minecraft:loot': {'table': 'loot_tables/rotu/entities/last_cantor.json'},
        'minecraft:follow_range': {'value': 40, 'max': 40},
        'minecraft:shooter': {'def': nid('hush_bolt')},
        'minecraft:home': {'restriction_radius': 16, 'restriction_type': 'all_movement'},
        'minecraft:ambient_sound_interval': {'event_name': 'ambient', 'range': 6, 'value': 5},
        'minecraft:behavior.float': {'priority': 0},
        'minecraft:behavior.hurt_by_target': {'priority': 1},
        'minecraft:behavior.nearest_attackable_target': {
            'priority': 2, 'must_see': False, 'reselect_targets': True, 'within_radius': 32,
            'entity_types': [{'filters': PLAYER_ONLY, 'max_dist': 32}]},
        'minecraft:behavior.look_at_player': {'priority': 9, 'look_distance': 16},
        'minecraft:behavior.random_look_around': {'priority': 10},
    })

    def phase(summon_cd, n_summon, interval, speed):
        return {
            'minecraft:movement': {'value': speed},
            'minecraft:behavior.summon_entity': {
                'priority': 3,
                'summon_choices': [{
                    'min_activation_range': 0, 'max_activation_range': 28, 'cooldown_time': summon_cd,
                    'weight': 1, 'cast_duration': 2.0, 'do_casting': True, 'particle_color': '#FF8FE3D8',
                    'start_sound_event': 'cast.spell',
                    'sequence': [{
                        'shape': 'circle', 'target': 'self', 'base_delay': 1.2, 'delay_per_summon': 0.25,
                        'num_entities_spawned': n_summon, 'entity_type': nid('murmur'), 'size': 2.5,
                        'summon_cap': 6, 'summon_cap_radius': 24, 'summon_event': 'rotu:temporary',
                        'sound_event': 'prepare.summon'}],
                }],
            },
            'minecraft:behavior.ranged_attack': {
                'priority': 4, 'attack_interval': {'min': interval[0], 'max': interval[1]},
                'attack_range': {'min': 0.0, 'max': 20.0}, 'in_range_movement_mode': 'follow_target',
                'speed_multiplier': 1.0, 'swing': True},
        }

    groups = {
        'rotu:phase_one': dict(phase(16, 2, (2.2, 3.4), 0.2), **{
            'minecraft:environment_sensor': {'triggers': [{
                'filters': {'test': 'actor_health', 'subject': 'self', 'operator': '<=', 'value': 140},
                'event': 'rotu:enter_phase_two'}]},
            'minecraft:variant': {'value': 0},
        }),
        'rotu:phase_two': dict(phase(11, 3, (1.4, 2.4), 0.25), **{'minecraft:variant': {'value': 1}}),
    }
    events = {
        'minecraft:entity_spawned': {'add': {'component_groups': ['rotu:phase_one']}},
        'rotu:enter_phase_two': {'remove': {'component_groups': ['rotu:phase_one']},
                                 'add': {'component_groups': ['rotu:phase_two']}},
    }
    entity('last_cantor', 'The Last Cantor',
           {'spawn_category': 'monster', 'is_spawnable': True, 'is_summonable': True}, c, groups, events)

    # ------------------------------------------------------------------ Hush Bolt (projectile)
    c = {
        'minecraft:type_family': {'family': ['projectile', 'hush_bolt']},
        'minecraft:collision_box': {'width': 0.4, 'height': 0.4},
        'minecraft:physics': {'has_collision': False},
        'minecraft:conditional_bandwidth_optimization': {'default_values': {
            'max_dropped_ticks': 7, 'max_optimized_distance': 80.0, 'use_motion_prediction_hints': True}},
        'minecraft:projectile': {
            'anchor': 'eye_height',
            'offset': [0, -0.3, 0],
            'homing': True,
            'destroy_on_hurt': True,
            'crit_particle_on_hurt': True,
            'gravity': 0.0,
            'power': 0.9,
            'inertia': 1.0,
            'uncertainty_base': 6,
            'uncertainty_multiplier': 2,
            'isolated_physics': False,
            'hit_sound': 'bullet.hit',
            'should_bounce': 'if_no_damage_dealt',
            'on_hit': {
                'impact_damage': {'damage': {'min': 5, 'max': 7}, 'knockback': True,
                                  'apply_knockback_to_blocking_targets': True},
                'mob_effect': {'effects': [
                    {'effect': 'darkness', 'amplifier': 0, 'durationeasy': 60, 'durationnormal': 80,
                     'durationhard': 100},
                    {'effect': 'slowness', 'amplifier': 0, 'durationeasy': 40, 'durationnormal': 60,
                     'durationhard': 80}]},
                'particle_on_hit': {'on_other_hit': True, 'on_entity_hit': True, 'particle_type': 'largeexplode'},
                'remove_on_hit': {},
            },
        },
        'minecraft:timer': {'looping': False, 'time': 12, 'time_down_event': {'event': 'rotu:expire', 'target': 'self'}},
    }
    groups = {'rotu:expired': {'minecraft:instant_despawn': {}}}
    events = {'rotu:expire': {'add': {'component_groups': ['rotu:expired']}}}
    ident = nid('hush_bolt')
    REG.add_bp('entities/hush_bolt.json', {'format_version': FORMAT_ENTITY, 'minecraft:entity': {
        'description': {'identifier': ident, 'spawn_category': 'misc', 'is_spawnable': False, 'is_summonable': True},
        'components': c, 'component_groups': groups, 'events': events}})
    REG.tr(f'entity.{ident}.name', 'Hush Bolt')
