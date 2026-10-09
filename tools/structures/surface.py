"""Mourning Statues and Waystones (small, common surface structures)."""
from lib.mcstructure import B, AIR
from .kit import (Builder, GB, GB_CRACK, GB_MOSS, G_TILE, G_CHISEL, G_GILD, SINGING, CHOIR_LANTERN, pillar, mural,
                  cipher, urn, candle, lantern, chain, stairs, slab, marker, WEB)

DT_STAIR = 'minecraft:deepslate_tile_stairs'
DT_SLAB = 'minecraft:deepslate_tile_slab'


# ------------------------------------------------------------------ Mourning statues (beard_thin, layer 0 = ground)

def statue_kneeling(seed=101):
    b = Builder(5, 6, 5, seed)
    b.fill(0, 0, 0, 4, 0, 4, lambda: b.pick([(G_TILE, 3), (GB_CRACK, 2), (B('coarse_dirt'), 2), (B('moss_block'), 1)]))
    b.fill(1, 1, 1, 3, 1, 3, lambda: slab(DT_SLAB))
    # kneeling figure facing north: legs folded (stair), torso, bowed head
    b.set(2, 1, 2, B('polished_deepslate'))
    b.set(2, 2, 2, pillar())
    b.set(2, 3, 2, G_CHISEL)
    b.set(2, 4, 2, slab(DT_SLAB))
    b.set(1, 2, 2, stairs(DT_STAIR, 'east', upside=True))
    b.set(3, 2, 2, stairs(DT_STAIR, 'west', upside=True))
    b.set(2, 1, 1, stairs(DT_STAIR, 'south'))
    for (x, z) in ((0, 0), (4, 1), (1, 4)):
        b.set(x, 1, z, candle(b.rng.randint(1, 3)))
    b.set(3, 1, 4, urn(True, 0))
    return b.finish()


def statue_lantern(seed=102):
    b = Builder(5, 8, 5, seed)
    b.fill(0, 0, 0, 4, 0, 4, lambda: b.pick([(G_TILE, 3), (GB, 2), (B('coarse_dirt'), 2), (B('podzol'), 1)]))
    b.fill(1, 1, 1, 3, 1, 3, GB)
    b.set(2, 2, 2, pillar())
    b.set(2, 3, 2, pillar())
    b.set(2, 4, 2, B('polished_deepslate'))
    b.set(2, 5, 2, G_CHISEL)
    b.set(2, 6, 2, stairs(DT_STAIR, 'north'))
    b.set(1, 6, 2, slab(DT_SLAB))
    b.set(3, 6, 2, slab(DT_SLAB))
    # outstretched arm holding a hanging lantern
    b.set(2, 4, 1, stairs(DT_STAIR, 'south', upside=True))
    b.set(2, 4, 0, B('polished_deepslate_wall'))
    b.set(2, 3, 0, chain())
    b.set(2, 2, 0, lantern(True, hanging=True))
    b.set(1, 2, 2, B('polished_deepslate_wall'))
    b.set(3, 2, 2, B('polished_deepslate_wall'))
    b.set(0, 1, 3, candle(2))
    b.set(4, 1, 1, candle(1))
    # an offering buried at the statue's feet
    b.suspicious(3, 0, 0, 'archaeology/waystone')
    return b.finish()


def statue_toppled(seed=103):
    b = Builder(7, 4, 7, seed)
    b.fill(0, 0, 0, 6, 0, 6, lambda: b.pick([(G_TILE, 2), (GB_CRACK, 2), (B('coarse_dirt'), 3), (B('gravel'), 1), (B('moss_block'), 1)]))
    b.fill(2, 1, 1, 4, 1, 3, GB)
    b.set(3, 2, 2, pillar())
    b.set(3, 3, 2, B('polished_deepslate_wall'))
    # the fallen upper body lying east-west
    for x, blk in ((1, G_CHISEL), (2, pillar('x')), (4, pillar('x')), (5, slab(DT_SLAB))):
        b.set(x, 1, 5, blk)
    b.set(3, 1, 5, B('cobbled_deepslate'))
    b.set(6, 1, 0, urn(True, 2))
    b.set(0, 1, 2, candle(3))
    b.set(5, 1, 3, B('moss_carpet'))
    b.set(1, 1, 1, B('moss_carpet'))
    return b.finish()


STATUES = {'statue_kneeling': statue_kneeling, 'statue_lantern': statue_lantern, 'statue_toppled': statue_toppled}


# ------------------------------------------------------------------ Waystones (terrain adaptation none, structure void)
# Layout (7 x H x 7): layers 0-4 buried cache, 5-6 natural soil (void) with foundation + suspicious blocks,
# layer 7 = first air above ground (start_height absolute -7).
GROUND = 7


def _cache(b, arid=False, seed_glyph=0):
    wall = (lambda: b.pick([(B('sandstone'), 4), (B('cut_sandstone'), 2), (GB, 2), (GB_CRACK, 1)])) if arid else \
        (lambda: b.pick([(GB, 5), (GB_CRACK, 3), (GB_MOSS, 1), (B('cobbled_deepslate'), 1)]))
    b.box(1, 0, 1, 5, 4, 5, wall, floor=(lambda: b.pick([(G_TILE, 3), (GB, 1)])), ceiling=wall)
    b.chest(3, 1, 2, 'chests/waystone_cache', 'south')
    b.set(2, 1, 4, urn(True, 0 if not arid else 1))
    b.set(4, 1, 4, urn(True, 2))
    b.set(3, 2, 5, SINGING)
    b.set(1, 2, 3, mural(seed_glyph % 4))
    b.set(2, 1, 2, candle(2))
    b.set(4, 3, 2, WEB)
    b.set(2, 3, 4, WEB)
    b.set(4, 1, 3, B('bone_block', pillar_axis='x'))


def _foundation(b, arid=False):
    for y in (GROUND - 2, GROUND - 1):
        for x in range(2, 5):
            for z in range(2, 5):
                b.set(x, y, z, b.pick([(B('cut_sandstone'), 3), (B('sandstone'), 2)]) if arid else
                      b.pick([(B('cobbled_deepslate'), 3), (GB, 2), (B('polished_deepslate'), 1)]))


def _suspicious_ring(b, spots, arid=False):
    loot = 'archaeology/waystone'
    for (x, z) in spots:
        b.suspicious(x, GROUND - 1, z, loot, sand=arid)


def waystone_tall(seed=201, arid=False):
    b = Builder(7, GROUND + 9, 7, seed)
    _cache(b, arid, 0)
    _foundation(b, arid)
    _suspicious_ring(b, [(1, 3), (5, 2), (3, 5)], arid)
    base = (lambda: b.pick([(B('cut_sandstone'), 2), (G_TILE, 1)])) if arid else (lambda: b.pick([(G_TILE, 2), (B('polished_deepslate'), 1)]))
    b.fill(2, GROUND, 2, 4, GROUND, 4, base)
    for y in range(GROUND + 1, GROUND + 5):
        b.set(3, y, 3, pillar())
    b.set(3, GROUND + 5, 3, G_CHISEL)
    b.set(3, GROUND + 6, 3, G_GILD)
    b.set(3, GROUND + 7, 3, lantern(True))
    for (x, z) in ((2, 3), (4, 3), (3, 2), (3, 4)):
        b.set(x, GROUND + 1, z, stairs(DT_STAIR if not arid else 'minecraft:sandstone_stairs',
                                       {(2, 3): 'east', (4, 3): 'west', (3, 2): 'south', (3, 4): 'north'}[(x, z)]))
    b.set(1, GROUND, 1, candle(1))
    b.set(5, GROUND, 5, candle(2))
    if arid:
        b.set(0, GROUND, 4, B('deadbush'))
    return b.finish()


def waystone_broken(seed=202, arid=False):
    b = Builder(7, GROUND + 6, 7, seed)
    _cache(b, arid, 1)
    _foundation(b, arid)
    _suspicious_ring(b, [(2, 1), (5, 4), (1, 5)], arid)
    b.fill(2, GROUND, 2, 4, GROUND, 4, lambda: b.pick([(G_TILE, 2), (GB_CRACK, 2)]))
    b.set(3, GROUND + 1, 3, pillar())
    b.set(3, GROUND + 2, 3, pillar())
    b.set(3, GROUND + 3, 3, B('cobbled_deepslate_wall'))
    # fallen pieces
    b.set(5, GROUND, 1, G_CHISEL)
    b.set(5, GROUND, 2, pillar('z'))
    b.set(1, GROUND, 4, B('cobbled_deepslate'))
    b.set(0, GROUND, 4, slab('minecraft:cobbled_deepslate_slab'))
    b.set(4, GROUND + 1, 4, candle(3))
    b.set(2, GROUND + 1, 2, B('moss_carpet') if not arid else candle(1))
    return b.finish()


def waystone_twin(seed=203, arid=False):
    b = Builder(7, GROUND + 7, 7, seed)
    _cache(b, arid, 2)
    _foundation(b, arid)
    _suspicious_ring(b, [(3, 1), (3, 5), (0, 3)], arid)
    for x in (1, 5):
        b.set(x, GROUND, 3, G_TILE)
        for y in range(GROUND + 1, GROUND + 4):
            b.set(x, y, 3, pillar())
        b.set(x, GROUND + 4, 3, G_CHISEL)
    for x in range(1, 6):
        b.set(x, GROUND + 5, 3, slab(DT_SLAB) if x in (1, 5) else B('polished_deepslate'))
    b.set(2, GROUND + 4, 3, cipher(b.rng.randrange(4)))
    b.set(3, GROUND + 4, 3, cipher(b.rng.randrange(4)))
    b.set(4, GROUND + 4, 3, cipher(b.rng.randrange(4)))
    b.set(3, GROUND + 3, 3, chain())
    b.set(3, GROUND + 2, 3, lantern(True, hanging=True))
    b.set(3, GROUND, 3, G_TILE)
    b.set(2, GROUND, 2, candle(1))
    return b.finish()


def waystone_ring(seed=204, arid=False):
    b = Builder(7, GROUND + 4, 7, seed)
    _cache(b, arid, 3)
    _foundation(b, arid)
    _suspicious_ring(b, [(1, 1), (5, 5), (5, 1)], arid)
    b.set(3, GROUND - 1, 3, SINGING)
    for (x, z) in ((0, 3), (6, 3), (3, 0), (3, 6)):
        b.set(x, GROUND, z, GB if not arid else B('cut_sandstone'))
        b.set(x, GROUND + 1, z, G_CHISEL if (x + z) % 2 else pillar())
        b.set(x, GROUND + 2, z, slab(DT_SLAB))
    for (x, z) in ((2, 2), (4, 4)):
        b.set(x, GROUND, z, candle(b.rng.randint(1, 4)))
    b.set(4, GROUND, 2, urn(True, 1))
    return b.finish()


WAYSTONES = {
    'waystone_tall': waystone_tall,
    'waystone_broken': waystone_broken,
    'waystone_twin': waystone_twin,
    'waystone_ring': waystone_ring,
}
WAYSTONES_ARID = {
    'waystone_tall_arid': lambda: waystone_tall(301, True),
    'waystone_broken_arid': lambda: waystone_broken(302, True),
}
