"""Dig Site (excavation + expedition camp) and Hushed Shrine builders (beard_thin, layer 0 = ground)."""
from lib.mcstructure import B, AIR
from .kit import (Builder, GB, GB_CRACK, GB_MOSS, G_TILE, G_CHISEL, G_GILD, SINGING, CHOIR_LANTERN, SEALED_GATE, VEIL,
                  pillar, mural, cipher, dial, urn, plate, reliquary, marker, desk, candle, lantern, chain, stairs,
                  slab, torch, WEB)

DT_STAIR = 'minecraft:deepslate_tile_stairs'
DT_SLAB = 'minecraft:deepslate_tile_slab'
DT_WALL = 'minecraft:deepslate_tile_wall'


# ------------------------------------------------------------------------------------------------ Dig site

def dig_excavation(seed=401, arid=False):
    b = Builder(15, 6, 15, seed)
    soil = (lambda: b.pick([(B('sand'), 5), (B('red_sand'), 1), (B('sandstone'), 1), (B('gravel'), 1)])) if arid else \
        (lambda: b.pick([(B('coarse_dirt'), 5), (B('dirt'), 3), (B('gravel'), 2), (B('podzol'), 1)]))
    b.fill(0, 0, 0, 14, 0, 14, soil)
    # spoil heaps ringing the excavation (layer 1-2), leaving the trench floor at layer 0
    for x in range(15):
        for z in range(15):
            ring = x in (0, 1, 13, 14) or z in (0, 1, 13, 14)
            if ring and b.rng.random() < 0.55:
                b.set(x, 1, z, soil())
                if b.rng.random() < 0.3:
                    b.set(x, 2, z, B('gravel') if not arid else B('sand'))
    # exposed ruin: a corner of gloamstone walls and a floor of tiles
    for x in range(3, 12):
        for z in range(3, 12):
            if b.rng.random() < 0.7:
                b.set(x, 0, z, b.gloam_floor())
    for x in range(3, 12):
        h = b.rng.randint(1, 3)
        for y in range(1, h + 1):
            b.set(x, y, 3, b.gloam_wall())
    for z in range(3, 12):
        h = b.rng.randint(0, 3)
        for y in range(1, h + 1):
            b.set(3, y, z, b.gloam_wall())
    b.set(3, 2, 7, mural(0))
    b.set(7, 2, 3, mural(1))
    # fallen pillar and a standing stub
    for x in range(6, 10):
        b.set(x, 1, 9, pillar('x'))
    b.set(10, 1, 6, pillar())
    b.set(10, 2, 6, G_CHISEL)
    # suspicious finds in the trench floor
    finds = [(5, 6), (6, 5), (8, 7), (9, 11), (11, 8), (5, 10), (7, 12), (12, 4)]
    for (x, z) in finds:
        b.suspicious(x, 0, z, 'archaeology/dig_site', sand=arid)
    # urns, a finds crate, grid stakes with lines
    b.set(4, 1, 4, urn(True, 0))
    b.set(11, 1, 11, urn(True, 1))
    b.set(4, 1, 11, urn(True, 2))
    b.barrel(12, 1, 12, 'chests/dig_finds', facing=1)
    for (x, z) in ((2, 2), (12, 2), (2, 12)):
        b.set(x, 1, z, B('spruce_fence'))
        b.set(x, 2, z, B('spruce_fence'))
    b.set(6, 1, 6, B('brown_carpet'))
    b.set(8, 1, 10, torch('top', soul=False))
    # connection to the camp (east side, ground level)
    b.jigsaw(14, 1, 7, 'east', 'rotu:dig_exit', 'rotu:camp', 'rotu:dig_camp')
    return b.finish()


def dig_camp(seed=402):
    b = Builder(9, 6, 9, seed)
    b.fill(0, 0, 0, 8, 0, 8, lambda: b.pick([(B('coarse_dirt'), 3), (B('dirt'), 2), (B('gravel'), 1)]))
    # A-frame tent along x (from x=1 to 5), wool
    for x in range(1, 6):
        b.set(x, 1, 1, B('brown_wool'))
        b.set(x, 1, 5, B('brown_wool'))
        b.set(x, 2, 2, B('white_wool'))
        b.set(x, 2, 4, B('white_wool'))
        b.set(x, 3, 3, B('white_wool'))
        for z in (2, 3, 4):
            b.set(x, 1, z, AIR)
        b.set(x, 2, 3, AIR)
    for z in (2, 3, 4):
        b.set(1, 1, z, B('brown_wool'))
    b.set(2, 2, 3, AIR)
    b.chest(2, 1, 3, 'chests/dig_supplies', 'east')
    b.set(3, 1, 2, B('white_carpet'))
    b.set(4, 1, 2, B('white_carpet'))
    b.set(4, 1, 4, B('lantern', hanging=False))
    # extinguished campfire, logs to sit on, work tables
    b.campfire(5, 1, 7, lit=False)
    b.set(4, 1, 7, B('stripped_spruce_log', pillar_axis='z'))
    b.set(6, 1, 7, B('stripped_spruce_log', pillar_axis='z'))
    b.set(7, 1, 2, B('cartography_table'))
    b.set(7, 1, 3, B('crafting_table'))
    b.set(7, 1, 4, desk('west'))
    b.set(1, 1, 7, B('hay_block', pillar_axis='y'))
    b.set(2, 1, 7, B('barrel', facing_direction=1, open_bit=False))
    b.set(7, 1, 6, B('spruce_fence'))
    b.set(7, 2, 6, torch('top', soul=False))
    # connection back to the excavation (west side)
    b.jigsaw(0, 1, 4, 'west', 'rotu:camp')
    return b.finish()


# ------------------------------------------------------------------------------------------------ Hushed shrine

def shrine(seed, with_sentinel):
    W = 21
    b = Builder(W, 12, W, seed)
    # platform with ragged edges (void lets the natural ground show)
    for x in range(W):
        for z in range(W):
            edge = min(x, z, W - 1 - x, W - 1 - z)
            if edge == 0 and b.rng.random() < 0.6:
                continue
            if edge == 1 and b.rng.random() < 0.2:
                continue
            b.set(x, 0, z, b.gloam_floor() if b.rng.random() < 0.85 else B('moss_block'))
    # outer colonnade
    for (x, z) in ((2, 2), (18, 2), (2, 18), (18, 18), (2, 10), (18, 10), (10, 2)):
        h = b.rng.randint(2, 5)
        for y in range(1, h + 1):
            b.set(x, y, z, pillar())
        if h >= 4:
            b.set(x, h + 1, z, slab(DT_SLAB))
    for x in range(3, 18):
        if b.rng.random() < 0.45:
            b.set(x, 1, 2, B(DT_WALL))
    # sanctum: x 4..16, z 4..15 (west wall 3 thick to hide an alcove)
    x0, x1, z0, z1 = 4, 16, 4, 15
    for x in range(x0, x1 + 1):
        for z in range(z0, z1 + 1):
            for y in range(1, 8):
                wall = x in (x0, x1) or z in (z0, z1) or x == x0 + 2
                if x == x0 + 1 and z0 < z < z1:
                    b.set(x, y, z, b.gloam_wall())     # filled wall core (alcove carved below)
                elif wall:
                    b.set(x, y, z, b.gloam_wall())
                else:
                    b.set(x, y, z, AIR)
            b.set(x, 0, z, b.gloam_floor())
            b.set(x, 8, z, slab(DT_SLAB) if (x + z) % 5 else G_TILE)
    # roof collapse
    b.erode(x0 + 4, 8, z0 + 3, x0 + 8, 8, z0 + 6, 0.55)
    # pilasters on the walls
    for z in (z0, z1):
        for x in (x0, x0 + 4, x0 + 8, x1):
            for y in range(1, 8):
                b.set(x, y, z, pillar())
    # entrance: sealed gate (3 wide x 3 tall) in the south wall
    gx = 10
    for x in (gx - 1, gx, gx + 1):
        for y in (1, 2, 3):
            b.set(x, y, z1, SEALED_GATE)
    for x in (gx - 2, gx + 2):
        for y in (1, 2, 3, 4):
            b.set(x, y, z1, pillar())
    # cipher stones above the gate show the answer, left to right as seen from outside
    solution = [b.rng.randrange(4) for _ in range(3)]
    # seen from the south (outside), "left" is west (smaller x)
    for i, x in enumerate((gx - 1, gx, gx + 1)):
        b.set(x, 5, z1, cipher(solution[i]))
    b.set(gx - 2, 5, z1, G_CHISEL)
    b.set(gx + 2, 5, z1, G_CHISEL)
    # three dials in front of the gate on pedestals, in the same left-to-right order
    for i, x in enumerate((gx - 2, gx, gx + 2)):
        b.set(x, 0, z1 + 3, G_GILD)
        start = (solution[i] + 1 + b.rng.randrange(3)) % 4
        b.set(x, 1, z1 + 3, dial(solution[i], start))
    # hushing plates on the approach (sneak to cross safely)
    b.set(gx, 1, z1 + 1, plate())
    b.set(gx - 1, 1, z1 + 2, plate())
    # flanking braziers
    for x in (gx - 4, gx + 4):
        b.set(x, 1, z1 + 2, B('polished_deepslate'))
        b.campfire(x, 2, z1 + 2, lit=True, soul=True)
    # interior: dais, reliquary, chest, singing stones, murals, hanging lanterns
    ix0, ix1 = x0 + 3, x1 - 1
    for x in range(ix0, ix1 + 1):
        for z in (z0 + 1, z0 + 2):
            b.set(x, 1, z, G_TILE)
    b.set(gx, 2, z0 + 1, reliquary('lesser'))
    b.set(gx - 2, 2, z0 + 1, CHOIR_LANTERN)
    b.set(gx + 2, 2, z0 + 1, CHOIR_LANTERN)
    b.chest(ix1, 1, z0 + 6, 'chests/shrine_sanctum', 'west')
    b.set(ix0, 0, z1 - 1, SINGING)
    b.set(ix1, 0, z1 - 1, SINGING)
    for i, z in enumerate((z0 + 4, z0 + 6, z0 + 8)):
        b.set(x1, 3, z, mural(i))
    b.set(x1, 3, z0 + 10, mural(3))
    for x in (gx - 3, gx + 3):
        b.set(x, 7, z0 + 6, chain())
        b.set(x, 6, z0 + 6, lantern(True, hanging=True))
    b.scatter(ix0, 1, z0 + 3, ix1, 1, z1 - 1, lambda: urn(True, b.rng.randrange(3)), 3)
    b.scatter(ix0, 1, z0 + 3, ix1, 1, z1 - 1, lambda: candle(b.rng.randint(1, 4)), 4)
    b.ceiling_webs(ix0, 7, z0 + 1, ix1, z1 - 1, 5)
    # hidden alcove inside the thick west wall, revealed with the Diviner's Lens
    ax = x0 + 1
    for z in (z0 + 6, z0 + 7, z0 + 8):
        b.set(ax, 1, z, AIR)
        b.set(ax, 2, z, AIR)
        b.set(x0 + 2, 1, z, VEIL)
        b.set(x0 + 2, 2, z, VEIL)
    b.chest(ax, 1, z0 + 7, 'chests/shrine_secret', 'east')
    b.set(ax, 1, z0 + 6, urn(True, 2))
    b.set(ax, 1, z0 + 8, candle(3))
    # guardians
    if with_sentinel:
        b.set(gx, 1, z0 + 5, marker('sentinel'))
    b.set(gx + 2, 1, z1 - 2, marker('hushwalkers'))
    b.set(3, 1, 17, marker('hushwalkers'))
    # outer ruin corner with a chest
    for (x, y, z) in ((17, 1, 16), (17, 2, 16), (16, 1, 17), (18, 1, 17)):
        b.set(x, y, z, b.gloam_wall())
    b.chest(17, 1, 17, 'chests/shrine_common', 'north')
    # statues facing the gate
    for x in (gx - 6, gx + 6):
        b.set(x, 1, z1 + 4, B('polished_deepslate'))
        b.set(x, 2, z1 + 4, pillar())
        b.set(x, 3, z1 + 4, G_CHISEL)
        b.set(x, 4, z1 + 4, slab(DT_SLAB))
    # weathering
    b.erode(0, 3, 0, W - 1, 7, W - 1, 0.04, only={'rotu:gloamstone_bricks', 'rotu:cracked_gloamstone_bricks'})
    b.scatter(0, 1, 0, W - 1, 1, W - 1, B('moss_carpet'), 6)
    return b.finish()


SITES = {
    'dig_excavation': lambda: dig_excavation(401, False),
    'dig_excavation_arid': lambda: dig_excavation(403, True),
    'dig_camp': dig_camp,
}
SHRINES = {
    'shrine_sentinel': lambda: shrine(501, True),
    'shrine_hollow': lambda: shrine(502, False),
}
