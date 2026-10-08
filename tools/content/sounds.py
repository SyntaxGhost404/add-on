"""Sound definitions (custom events remixing vanilla sounds + original synthesized ones)."""
from .registry import REG, nid


def s(name, pitch=1.0, volume=1.0, **extra):
    d = {'name': name, 'pitch': pitch, 'volume': volume}
    d.update(extra)
    return d


def many(prefix, nums, pitch=1.0, volume=1.0):
    return [s(f'{prefix}{n}', pitch, volume) for n in nums]


CUSTOM = 'sounds/rotu/'

DEFS = {
    'rotu.hushwalker.ambient': ('hostile', many('sounds/mob/husk/idle', (1, 2, 3), 0.62, 0.9)
                                + many('sounds/mob/zombie_villager/say', (1, 2, 3), 0.5, 0.7)),
    'rotu.hushwalker.hurt': ('hostile', many('sounds/mob/husk/hurt', (1, 2), 0.7)),
    'rotu.hushwalker.death': ('hostile', many('sounds/mob/husk/death', (1, 2), 0.6)),
    'rotu.hushwalker.step': ('hostile', many('sounds/mob/husk/step', (1, 2, 3, 4, 5), 0.8, 0.5)),
    'rotu.murmur.ambient': ('hostile', many('sounds/mob/vex/idle', (1, 2, 3, 4), 0.55, 0.8)
                            + many('sounds/mob/allay/idle_without_item', (1, 2, 3, 4), 0.42, 0.7)
                            + [s(CUSTOM + 'whisper1', 1.0, 0.8), s(CUSTOM + 'whisper2', 0.9, 0.8)]),
    'rotu.murmur.hurt': ('hostile', many('sounds/mob/vex/hurt', (1, 2), 0.6)),
    'rotu.murmur.death': ('hostile', many('sounds/mob/vex/death', (1, 2), 0.5)),
    'rotu.murmur.charge': ('hostile', many('sounds/mob/vex/charge', (1, 2, 3), 0.55)),
    'rotu.sentinel.step': ('hostile', many('sounds/step/stone', (1, 2, 3, 4, 5, 6), 0.45, 1.0)),
    'rotu.sentinel.hurt': ('hostile', many('sounds/dig/stone', (1, 2, 3, 4), 0.55, 1.0)),
    'rotu.sentinel.death': ('hostile', many('sounds/block/trial_spawner/break', (1, 2, 3), 0.5, 1.0)),
    'rotu.sentinel.attack': ('hostile', [s('sounds/mob/warden/attack_impact_1', 0.9), s('sounds/mob/warden/attack_impact_2', 0.85)]),
    'rotu.sentinel.awaken': ('hostile', [s('sounds/block/vault/activate', 0.5, 1.0), s('sounds/mob/creaking/activate', 0.7, 1.0)]),
    'rotu.cantor.ambient': ('hostile', many('sounds/mob/evocation_illager/idle', (1, 2, 3, 4), 0.5)),
    'rotu.cantor.hurt': ('hostile', many('sounds/mob/evocation_illager/hurt', (1, 2), 0.55)),
    'rotu.cantor.death': ('hostile', [s('sounds/mob/wither/death', 0.7, 1.0)]),
    'rotu.cantor.cast': ('hostile', many('sounds/mob/evocation_illager/cast', (1, 2), 0.6)),
    'rotu.cantor.summon': ('hostile', [s(CUSTOM + 'whisper1', 0.8), s(CUSTOM + 'whisper2', 0.7)]),
    'rotu.cantor.awaken': ('hostile', [s(CUSTOM + 'choir_drone', 0.85, 1.0)]),
    'rotu.cantor.pulse': ('hostile', [s('sounds/mob/warden/sonic_charge1', 0.75, 0.8)]),
    'rotu.cantor.blink': ('hostile', [s('sounds/mob/endermen/portal', 0.6, 0.8)]),
    'rotu.reliquary.open': ('block', [s(CUSTOM + 'choir_drone', 1.15, 0.7)]),
    'rotu.reliquary.insert': ('block', [s('sounds/block/vault/insert', 0.8)]),
    'rotu.reliquary.eject': ('block', many('sounds/block/vault/eject_item', (1, 2, 3), 0.85)),
    'rotu.reliquary.denied': ('block', [s('sounds/block/vault/insert_fail', 0.8)]),
    'rotu.reliquary.ambient': ('block', many('sounds/block/vault/ambient', (1, 2, 3), 0.7, 0.4)),
    'rotu.dial.turn': ('block', [s('sounds/random/click', 0.55, 0.8), s('sounds/dig/stone1', 0.7, 0.6)]),
    'rotu.gate.open': ('block', [s('sounds/block/end_portal/endportal', 0.65, 0.6)]),
    'rotu.puzzle.solved': ('block', [s(CUSTOM + 'glyph_chime', 1.0, 1.0)]),
    'rotu.decipher': ('block', [s(CUSTOM + 'glyph_chime', 0.85, 0.9)]),
    'rotu.singing_stone.hum': ('block', [s(CUSTOM + 'low_hum', 1.0, 0.6),
                                         s('sounds/block/amethyst/resonate1', 0.5, 0.5),
                                         s('sounds/block/amethyst/resonate2', 0.45, 0.5)]),
    'rotu.whisper': ('ambient', [s(CUSTOM + 'whisper1', 1.0, 0.7), s(CUSTOM + 'whisper2', 0.95, 0.7),
                                 s('sounds/cave/cave3', 0.8, 0.5), s('sounds/cave/cave9', 0.7, 0.5),
                                 s('sounds/cave/cave13', 0.75, 0.5)]),
    'rotu.trap.trigger': ('block', many('sounds/block/sculk_shrieker/shriek', (1, 2, 3), 0.7, 0.7)),
    'rotu.urn.break': ('block', [s('sounds/block/decorated_pot/shatter1', 0.8)]),
    'rotu.lens.use': ('player', [s('sounds/block/amethyst/shimmer', 1.25, 0.8)]),
    'rotu.dowse.ping': ('player', [s('sounds/note/icechime', 1.0, 0.7)]),
    'rotu.starcall': ('player', [s('sounds/block/respawn_anchor/set_spawn1', 0.8), s(CUSTOM + 'glyph_chime', 0.7)]),
    'rotu.dirge.echo': ('player', [s('sounds/block/bell/bell_use01', 0.5, 0.6), s('sounds/block/bell/bell_use02', 0.48, 0.6)]),
    'rotu.codex.open': ('player', many('sounds/item/book/open_flip', (1, 2, 3), 0.85)),
}

ENTITY_EVENTS = {
    nid('hushwalker'): {'volume': 1.0, 'pitch': [0.9, 1.1], 'events': {
        'ambient': 'rotu.hushwalker.ambient', 'hurt': 'rotu.hushwalker.hurt', 'death': 'rotu.hushwalker.death',
        'step': {'sound': 'rotu.hushwalker.step', 'volume': 0.35, 'pitch': 1.0}}},
    nid('murmur'): {'volume': 0.9, 'pitch': [0.9, 1.1], 'events': {
        'ambient': 'rotu.murmur.ambient', 'hurt': 'rotu.murmur.hurt', 'death': 'rotu.murmur.death',
        'charge': 'rotu.murmur.charge'}},
    nid('graven_sentinel'): {'volume': 1.0, 'pitch': [0.9, 1.0], 'events': {
        'hurt': 'rotu.sentinel.hurt', 'death': 'rotu.sentinel.death', 'attack.strong': 'rotu.sentinel.attack',
        'step': {'sound': 'rotu.sentinel.step', 'volume': 0.8, 'pitch': 1.0}}},
    nid('last_cantor'): {'volume': 1.2, 'pitch': [0.95, 1.05], 'events': {
        'ambient': 'rotu.cantor.ambient', 'hurt': 'rotu.cantor.hurt', 'death': 'rotu.cantor.death',
        'cast.spell': 'rotu.cantor.cast', 'prepare.summon': 'rotu.cantor.summon'}},
}


def define_sounds():
    defs = {}
    for name, (cat, sounds) in DEFS.items():
        defs[name] = {'category': cat, 'sounds': sounds}
    REG.add_rp('sounds/sound_definitions.json', {'format_version': '1.20.20', 'sound_definitions': defs})
    REG.add_rp('sounds.json', {'entity_sounds': {'entities': ENTITY_EVENTS}})
