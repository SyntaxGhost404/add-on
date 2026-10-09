"""Ossuary and Sunken Sanctum: multi-piece jigsaw complexes (terrain adaptation none).

Connector convention: every child piece has one entry jigsaw named "rotu:entry" on its south side (z max) at
floor+1, facing south. Exits face outward and target "rotu:entry" in a given pool.
"""
import math

from lib.mcstructure import B, AIR
from .kit import (Builder, GB, GB_CRACK, GB_MOSS, G_TILE, G_CHISEL, G_GILD, SINGING, CHOIR_LANTERN, SEALED_GATE, VEIL,
                  pillar, mural, cipher, urn, plate, reliquary, marker, sigil_lock, candle, lantern, chain, stairs,
                  slab, WEB)

ENTRY = 'rotu:entry'
PB_STAIR = 'minecraft:polished_blackstone_brick_stairs'
PB_SLAB = 'minecraft:polished_blackstone_brick_slab'
PB_WALL = 'minecraft:polished_blackstone_brick_wall'
RING = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]


def exit_jig(b, x, y, z, facing, pool, priority=0):
    b.jigsaw(x, y, z, facing, 'rotu:exit', ENTRY, pool, priority=priority)


def entry_jig(b, x, y, z):
    b.jigsaw(x, y, z, 'south', ENTRY)


def doorway(b, x, y0, z, width=3, height=3, axis='x'):
    for d in range(-(width // 2), width // 2 + 1):
        for y in range(y0, y0 + height):
            if axis == 'x':
                b.set(x + d, y, z, AIR)
            else:
                b.set(x, y, z + d, AIR)


def crypt_decor(b, x0, z0, x1, z1, y=1):
    b.scatter(x0, y, z0, x1, y, z1, lambda: urn(True, b.rng.randrange(3)), 2)
    b.scatter(x0, y, z0, x1, y, z1, lambda: candle(b.rng.randint(1, 4)), 3)
    b.scatter(x0, y, z0, x1, y, z1, B('bone_block', pillar_axis='y'), 1)
    b.ceiling_webs(x0, y + 2, z0, x1, z1, 3)


def shaft_top_railing(b, cx, cz, y_top, rail_y):
    """Railing around a spiral stairwell opening, leaving a gap next to the top step."""
    k = (y_top - 1) % 8
    sx, sz = RING[k]
    # floor cells adjacent (orthogonally) to the top step that lie on the shaft's outer ring
    gaps = set()
    for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, nz = sx + dx, sz + dz
        if max(abs(nx), abs(nz)) == 2:
            gaps.add((nx, nz))
    for dx in range(-2, 3):
        for dz in range(-2, 3):
            if max(abs(dx), abs(dz)) == 2 and (abs(dx), abs(dz)) != (2, 2) and (dx, dz) not in gaps:
                b.set(cx + dx, rail_y, cz + dz, B(PB_WALL))


# =================================================================================== OSSUARY
OSS_GROUND = 14          # first air layer above ground in the mausoleum piece (start_height -14)


def ossuary_mausoleum(seed=601):
    W = 11
    G = OSS_GROUND
    b = Builder(W, G + 9, W, seed)
    cx = cz = 5
    # foundation skirt (absorbs +-1 height differences) and the ground floor
    for x in range(W):
        for z in range(W):
            for y in (G - 3, G - 2):
                if 1 <= x <= 9 and 1 <= z <= 9:
                    b.set(x, y, z, b.pick([(B('cobbled_deepslate'), 3), (B('polished_blackstone'), 1)]))
            b.set(x, G - 1, z, b.pick([(B('polished_blackstone_bricks'), 3), (G_TILE, 2),
                                       (B('cracked_polished_blackstone_bricks'), 1)])
                  if 1 <= x <= 9 and 1 <= z <= 9 else b.pick([(B('coarse_dirt'), 2), (B('podzol'), 1), (B('gravel'), 1)]))
    # mausoleum walls (x 1..9, z 1..9) and roof
    for x in range(1, 10):
        for z in range(1, 10):
            for y in range(G, G + 6):
                edge = x in (1, 9) or z in (1, 9)
                b.set(x, y, z, b.dark_wall() if edge else AIR)
            b.set(x, G + 6, z, slab(PB_SLAB, top=True) if (x + z) % 2 else B('polished_blackstone_bricks'))
    for x in range(0, 11):
        b.set(x, G + 6, 0, stairs(PB_STAIR, 'south'))
        b.set(x, G + 6, 10, stairs(PB_STAIR, 'north'))
    for z in range(1, 10):
        b.set(0, G + 6, z, stairs(PB_STAIR, 'east'))
        b.set(10, G + 6, z, stairs(PB_STAIR, 'west'))
    for (x, z) in ((1, 1), (9, 1), (1, 9), (9, 9)):
        for y in range(G, G + 7):
            b.set(x, y, z, pillar())
        b.set(x, G + 7, z, B(PB_WALL))
    b.set(5, G + 7, 5, G_CHISEL)
    b.set(5, G + 8, 5, lantern(True))
    # entrance arch (south)
    for x in (4, 5, 6):
        for y in (G, G + 1, G + 2):
            b.set(x, y, 9, AIR)
    b.set(4, G + 3, 9, stairs(PB_STAIR, 'east', upside=True))
    b.set(6, G + 3, 9, stairs(PB_STAIR, 'west', upside=True))
    b.set(5, G + 3, 9, G_CHISEL)
    # graves outside
    for (x, z) in ((0, 3), (0, 7), (10, 3), (10, 7)):
        b.set(x, G, z, B('cobbled_deepslate_wall'))
        b.skull(x, G + 1, z, rot=b.rng.choice((0.0, 90.0, 180.0, 270.0)))
    b.set(2, G, 10, candle(2))
    b.set(8, G, 10, candle(3))
    # shaft: spiral stair from corridor level (y=1) up to the mausoleum floor (y=G-1)
    b.spiral_stairs(cx, cz, 1, G - 1, lambda: b.dark_wall())
    shaft_top_railing(b, cx, cz, G - 1, G)
    b.set(cx, G, cz, pillar())
    b.set(cx, G + 1, cz, G_CHISEL)
    b.set(cx, G + 2, cz, CHOIR_LANTERN)
    b.set(2, G, 2, urn(True, 2))
    b.set(8, G, 2, candle(4))
    b.set(2, G + 2, 5, mural(0))
    # bottom landing (z 0..3) opening into the shaft's north wall (z = 3) and the exit to the boundary
    b.box(2, 0, 0, 8, 4, 3, lambda: b.dark_wall(), floor=lambda: b.gloam_floor())
    for x in (4, 5, 6):
        for z in (0, 1, 2, 3):
            for y in (1, 2, 3):
                b.set(x, y, z, AIR)
    b.set(3, 1, 1, candle(2))
    b.set(7, 1, 1, candle(1))
    b.set(5, 0, 1, SINGING)
    exit_jig(b, 5, 1, 0, 'north', 'rotu:ossuary_hub')
    return b.finish()


def ossuary_hub(seed=602):
    b = Builder(11, 6, 11, seed)
    b.box(0, 0, 0, 10, 5, 10, lambda: b.gloam_wall(), floor=lambda: b.gloam_floor(), ceiling=lambda: b.gloam_wall())
    for (x, z) in ((2, 2), (8, 2), (2, 8), (8, 8)):
        for y in range(1, 5):
            b.set(x, y, z, pillar())
    for x in range(3, 8):
        b.set(x, 0, 5, B('bone_block', pillar_axis='x'))
    b.set(5, 1, 5, plate())
    b.set(5, 4, 5, chain())
    b.set(5, 3, 5, lantern(True, hanging=True))
    doorway(b, 5, 1, 10)
    doorway(b, 5, 1, 0)
    doorway(b, 0, 1, 5, axis='z')
    doorway(b, 10, 1, 5, axis='z')
    entry_jig(b, 5, 1, 10)
    # the Bone Choir holds a guaranteed sigil shard: claim its space before the corridors branch out
    exit_jig(b, 5, 1, 0, 'north', 'rotu:ossuary_bone_choir', priority=1)
    exit_jig(b, 0, 1, 5, 'west', 'rotu:ossuary_corridors')
    exit_jig(b, 10, 1, 5, 'east', 'rotu:ossuary_corridors')
    b.set(1, 2, 1, mural(2))
    b.set(9, 2, 9, mural(3))
    crypt_decor(b, 1, 1, 9, 9)
    b.set(8, 1, 6, marker('hushwalkers'))
    return b.finish()


def corridor_walls(b, x0, z0, x1, z1):
    b.box(x0, 0, z0, x1, 4, z1, lambda: b.pick([(GB, 4), (GB_CRACK, 2), (B('bone_block', pillar_axis='y'), 1),
                                               (B('polished_blackstone_bricks'), 1)]),
          floor=lambda: b.gloam_floor(), ceiling=lambda: b.gloam_wall())


def ossuary_straight(seed=611):
    b = Builder(5, 5, 9, seed)
    corridor_walls(b, 0, 0, 4, 8)
    doorway(b, 2, 1, 8)
    doorway(b, 2, 1, 0)
    entry_jig(b, 2, 1, 8)
    exit_jig(b, 2, 1, 0, 'north', 'rotu:ossuary_corridors')
    for z in (2, 6):
        b.skull(1, 1, z, rot=270.0)
        b.skull(3, 1, z + 1, rot=90.0)
    b.set(1, 1, 4, candle(b.rng.randint(1, 4)))
    b.set(3, 1, 3, urn(True, b.rng.randrange(3)))
    if b.rng.random() < 0.5:
        b.set(2, 1, 5, plate())
    b.ceiling_webs(1, 3, 1, 3, 7, 2)
    return b.finish()


def ossuary_turn(seed=612):
    b = Builder(5, 5, 5, seed)
    corridor_walls(b, 0, 0, 4, 4)
    doorway(b, 2, 1, 4)
    doorway(b, 0, 1, 2, axis='z')
    entry_jig(b, 2, 1, 4)
    exit_jig(b, 0, 1, 2, 'west', 'rotu:ossuary_corridors')
    b.set(3, 1, 1, candle(3))
    b.set(3, 3, 1, WEB)
    return b.finish()


def ossuary_tee(seed=613):
    b = Builder(9, 5, 5, seed)
    corridor_walls(b, 0, 0, 8, 4)
    doorway(b, 4, 1, 4)
    doorway(b, 0, 1, 2, axis='z')
    doorway(b, 8, 1, 2, axis='z')
    entry_jig(b, 4, 1, 4)
    exit_jig(b, 0, 1, 2, 'west', 'rotu:ossuary_corridors')
    exit_jig(b, 8, 1, 2, 'east', 'rotu:ossuary_corridors')
    b.set(4, 2, 0, mural(b.rng.randrange(4)))
    b.set(4, 1, 1, urn(True, 1))
    b.set(2, 1, 1, candle(2))
    b.set(6, 1, 1, candle(1))
    return b.finish()


def ossuary_crypt(seed=621, reliq=False, spawner=False):
    b = Builder(9, 6, 9, seed)
    b.box(0, 0, 0, 8, 5, 8, lambda: b.gloam_wall(), floor=lambda: b.gloam_floor(), ceiling=lambda: b.gloam_wall())
    doorway(b, 4, 1, 8)
    entry_jig(b, 4, 1, 8)
    # burial niches along the side walls
    for z in (2, 4, 6):
        b.set(0, 1, z, B('bone_block', pillar_axis='z'))
        b.set(8, 1, z, B('bone_block', pillar_axis='z'))
        b.set(1, 1, z, urn(True, b.rng.randrange(3)))
        b.skull(7, 1, z, rot=90.0)
    b.chest(4, 1, 1, 'chests/ossuary_crypt', 'south')
    if reliq:
        b.set(2, 1, 1, reliquary('lesser'))
    if spawner:
        b.set(4, 0, 4, B('bone_block', pillar_axis='y'))
        b.spawner(4, 1, 4, 'rotu:hushwalker', count=2, max_nearby=4, player_range=10)
        for (x, z) in ((3, 3), (5, 3), (3, 5), (5, 5)):
            b.set(x, 1, z, candle(b.rng.randint(1, 3)))
    else:
        b.set(4, 0, 4, SINGING)
        b.set(4, 1, 5, marker('hushwalkers'))
    b.set(4, 4, 4, chain())
    b.set(4, 3, 4, lantern(True, hanging=True))
    b.ceiling_webs(1, 4, 1, 7, 7, 4)
    b.set(6, 1, 6, candle(4))
    return b.finish()


def ossuary_cap(seed=631):
    b = Builder(5, 5, 2, seed)
    for x in range(5):
        for y in range(5):
            for z in range(2):
                b.set(x, y, z, b.rubble() if b.rng.random() < 0.85 else WEB)
    b.set(2, 1, 1, WEB)
    entry_jig(b, 2, 1, 1)
    return b.finish()


def ossuary_bone_choir(seed=641):
    W = 15
    b = Builder(W, 9, W, seed)
    c = 7
    for x in range(W):
        for z in range(W):
            d = math.hypot(x - c, z - c)
            for y in range(0, 9):
                if d > 7.2:
                    b.set(x, y, z, b.gloam_wall())
                elif y == 0:
                    b.set(x, y, z, B('bone_block', pillar_axis='y') if d > 5.5 else b.gloam_floor())
                elif y == 8 or (y == 7 and d > 5.5):
                    b.set(x, y, z, b.gloam_wall())
                else:
                    b.set(x, y, z, AIR)
    # tiered choir benches facing the altar
    for x in range(W):
        for z in range(W):
            d = math.hypot(x - c, z - c)
            if 5.5 < d <= 7.2:
                dx, dz = c - x, c - z
                face = ('east' if dx > 0 else 'west') if abs(dx) >= abs(dz) else ('south' if dz > 0 else 'north')
                asc = {'east': 'west', 'west': 'east', 'south': 'north', 'north': 'south'}[face]
                b.set(x, 1, z, stairs(PB_STAIR, asc))
    for (x, z) in ((3, 3), (11, 3), (3, 11), (11, 11)):
        for y in range(1, 8):
            b.set(x, y, z, B('bone_block', pillar_axis='y'))
    # altar with the Bone Sigil chest, singing stones
    b.fill(6, 1, 4, 8, 1, 6, G_GILD)
    b.chest(7, 2, 5, 'chests/ossuary_bone_choir', 'south')
    for (x, z) in ((6, 4), (8, 4)):
        b.set(x, 2, z, candle(4))
    for (x, z) in ((c, 2), (2, c), (12, c)):
        b.set(x, 0, z, SINGING)
    b.set(c, 7, c, chain())
    b.set(c, 6, c, chain())
    b.set(c, 5, c, lantern(True, hanging=True))
    b.set(7, 2, 2, mural(2))
    b.skull(6, 2, 6, rot=180.0, wither=True)
    b.skull(8, 2, 6, rot=180.0, wither=True)
    b.set(c, 1, 9, marker('sentinel'))
    b.set(4, 2, 7, marker('murmurs'))
    for x in (6, 7, 8):
        for y in (1, 2, 3):
            b.set(x, y, W - 1, AIR)
            b.set(x, y, W - 2, AIR)
    entry_jig(b, 7, 1, W - 1)
    b.ceiling_webs(2, 6, 2, 12, 12, 5)
    return b.finish()


OSSUARY = {
    'mausoleum': ossuary_mausoleum,
    'hub': ossuary_hub,
    'straight': ossuary_straight,
    'turn': ossuary_turn,
    'tee': ossuary_tee,
    'crypt': lambda: ossuary_crypt(621, False, False),
    'crypt_reliquary': lambda: ossuary_crypt(622, True, False),
    'crypt_spawner': lambda: ossuary_crypt(623, False, True),
    'cap': ossuary_cap,
    'bone_choir': ossuary_bone_choir,
}


# =================================================================================== SUNKEN SANCTUM
SANC_GROUND = 26     # first air layer above ground in the spire piece (start_height -26)


def sanctum_spire(seed=701):
    W = 13
    G = SANC_GROUND
    b = Builder(W, G + 24, W, seed)
    cx = cz = 6
    # foundation skirt + ground floor
    for x in range(W):
        for z in range(W):
            for y in (G - 3, G - 2):
                b.set(x, y, z, b.pick([(B('cobbled_deepslate'), 3), (B('blackstone'), 1)]))
            b.set(x, G - 1, z, b.pick([(B('polished_blackstone_bricks'), 3), (G_TILE, 2), (B('soul_soil'), 1)]))
    # ground hall (interior x/z 1..11, y G..G+5), solid ceiling at G+6
    for x in range(W):
        for z in range(W):
            for y in range(G, G + 6):
                edge = x in (0, 12) or z in (0, 12)
                b.set(x, y, z, b.dark_wall() if edge else AIR)
            b.set(x, G + 6, z, B('polished_blackstone_bricks'))
    # sealed upper tower: tapering hollow spire with weeping streaks
    for y in range(G + 7, G + 17):
        for x in range(1, 12):
            for z in range(1, 12):
                edge = x in (1, 11) or z in (1, 11)
                b.set(x, y, z, b.dark_wall() if edge else AIR)
    for x in range(1, 12):
        for z in range(1, 12):
            b.set(x, G + 17, z, B('polished_blackstone_bricks'))
    for y in range(G + 18, G + 22):
        w = G + 22 - y
        for x in range(cx - w, cx + w + 1):
            for z in range(cz - w, cz + w + 1):
                b.set(x, y, z, B('polished_blackstone_bricks') if max(abs(x - cx), abs(z - cz)) == w else AIR)
    b.set(cx, G + 22, cz, B('polished_blackstone_bricks'))
    b.campfire(cx, G + 23, cz, lit=True, soul=True)
    for (x, z) in ((0, 0), (12, 0), (0, 12), (12, 12)):
        for y in range(G, G + 12):
            b.set(x, y, z, pillar())
        b.set(x, G + 12, z, G_GILD)
    for (x, z) in ((3, 1), (9, 1), (3, 11), (9, 11), (1, 3), (1, 9), (11, 3), (11, 9)):
        for y in range(G + 7, G + 17):
            if b.rng.random() < 0.6:
                b.set(x, y, z, B('crying_obsidian'))
    for (x, z) in ((6, 1), (6, 11), (1, 6), (11, 6)):
        b.set(x, G + 15, z, CHOIR_LANTERN)
    # entrance arch (south, ground level)
    for x in (5, 6, 7):
        for y in (G, G + 1, G + 2):
            b.set(x, y, 12, AIR)
    b.set(6, G + 3, 12, G_CHISEL)
    b.set(5, G + 3, 12, cipher(1))
    b.set(7, G + 3, 12, cipher(1))
    # spiral stair: from corridor level (y=1) up to the hall floor (y=G-1)
    b.spiral_stairs(cx, cz, 1, G - 1, lambda: b.dark_wall())
    shaft_top_railing(b, cx, cz, G - 1, G)
    b.set(cx, G, cz, pillar())
    b.set(cx, G + 1, cz, pillar())
    b.set(cx, G + 2, cz, G_CHISEL)
    b.set(cx, G + 3, cz, CHOIR_LANTERN)
    # hall decoration
    b.chest(2, G, 10, 'chests/sanctum_spire', 'east')
    for (x, z) in ((2, 2), (10, 2)):
        b.set(x, G, z, lantern(True))
    b.set(10, G, 10, urn(True, 0))
    b.set(2, G, 6, urn(True, 2))
    b.set(0, G + 2, 6, mural(1))
    b.set(12, G + 2, 6, mural(3))
    b.set(6, G + 2, 0, mural(0))
    b.set(10, G, 6, marker('hushwalkers'))
    # bottom landing opening into the shaft's north wall (z = 4) and the exit to the boundary
    b.box(3, 0, 0, 9, 4, 4, lambda: b.dark_wall(), floor=lambda: b.gloam_floor())
    for x in (5, 6, 7):
        for z in range(0, 5):
            for y in (1, 2, 3):
                b.set(x, y, z, AIR)
    b.set(4, 1, 2, candle(3))
    b.set(8, 1, 2, candle(2))
    exit_jig(b, 6, 1, 0, 'north', 'rotu:sanctum_antechamber')
    return b.finish()


def sanctum_antechamber(seed=702):
    b = Builder(15, 9, 13, seed)
    b.box(0, 0, 0, 14, 8, 12, lambda: b.dark_wall(), floor=lambda: b.gloam_floor(), ceiling=lambda: b.gloam_wall())
    doorway(b, 7, 1, 12)
    entry_jig(b, 7, 1, 12)
    # the inner gate (north wall) and the passage beyond it
    for x in (6, 7, 8):
        for y in (1, 2, 3, 4):
            b.set(x, y, 1, SEALED_GATE)
        for y in (1, 2, 3):
            b.set(x, y, 0, AIR)
    for x in (5, 9):
        for y in range(1, 6):
            b.set(x, y, 1, pillar())
    for x in (6, 7, 8):
        b.set(x, 5, 1, G_GILD)
    exit_jig(b, 7, 1, 0, 'north', 'rotu:sanctum_hall')
    # sigil lock on a pedestal before the gate
    b.set(7, 1, 4, G_GILD)
    b.set(7, 2, 4, sigil_lock())
    for i, z in enumerate((3, 5, 7, 9)):
        b.set(0, 3, z, mural(i))
        b.set(14, 3, z, mural(i))
    for (x, z) in ((3, 3), (11, 3), (3, 9), (11, 9)):
        for y in range(1, 8):
            b.set(x, y, z, pillar())
        b.set(x, 1, z + 1, CHOIR_LANTERN)
    b.set(7, 1, 8, plate())
    b.set(6, 1, 10, plate())
    b.set(8, 1, 6, plate())
    b.set(2, 1, 6, marker('murmurs'))
    b.set(12, 1, 6, urn(True, 2))
    b.set(2, 1, 11, urn(True, 0))
    b.ceiling_webs(1, 7, 1, 13, 11, 4)
    return b.finish()


def sanctum_hall(seed=703):
    b = Builder(13, 11, 25, seed)
    b.box(0, 0, 0, 12, 10, 24, lambda: b.dark_wall(), floor=lambda: b.gloam_floor(), ceiling=lambda: b.gloam_wall())
    doorway(b, 6, 1, 24)
    doorway(b, 6, 1, 0)
    entry_jig(b, 6, 1, 24)
    exit_jig(b, 6, 1, 0, 'north', 'rotu:sanctum_choir')
    for z in range(3, 23, 4):
        for x in (3, 9):
            for y in range(1, 10):
                b.set(x, y, z, pillar())
            b.set(x, 9, z, G_GILD)
    for z in range(2, 23):
        b.set(6, 0, z, B('polished_deepslate'))
    for z in (5, 13, 21):
        b.set(6, 0, z, SINGING)
    for i, z in enumerate((4, 8, 12, 16)):
        b.set(0, 4, z, mural(i))
    # secret niche: wall at x=10 (veilstone at z 10..12), niche at x=11, closed by walls at z=9/13 and x=12
    for z in range(9, 14):
        for y in range(1, 5):
            b.set(10, y, z, b.dark_wall())
            b.set(11, y, z, b.dark_wall())
    for z in (10, 11, 12):
        for y in (1, 2, 3):
            b.set(10, y, z, VEIL)
            b.set(11, y, z, AIR)
    b.set(11, 1, 11, reliquary('lesser'))
    b.chest(11, 1, 10, 'chests/sanctum_hall', 'west')
    b.set(11, 1, 12, urn(True, 1))
    b.set(6, 1, 18, marker('hushwalkers'))
    b.set(6, 1, 7, marker('hushwalkers'))
    for z in (15, 9):
        b.set(6, 1, z, plate())
    crypt_decor(b, 1, 1, 8, 23)
    for z in (6, 18):
        b.set(6, 9, z, chain())
        b.set(6, 8, z, lantern(True, hanging=True))
    b.chest(1, 1, 20, 'chests/sanctum_hall', 'east')
    return b.finish()


def sanctum_choir(seed=704):
    W = 23
    b = Builder(W, 15, W, seed)
    c = 11
    for x in range(W):
        for z in range(W):
            d = math.hypot(x - c, z - c)
            for y in range(15):
                dome = 13 - max(0.0, (d - 6) * 0.6)
                if d > 11.2:
                    b.set(x, y, z, b.dark_wall())
                elif y == 0:
                    b.set(x, y, z, G_TILE if d > 3.5 else G_GILD)
                elif y >= dome:
                    b.set(x, y, z, b.dark_wall())
                else:
                    b.set(x, y, z, AIR)
    # tiered stalls (2 tiers) facing the centre
    for x in range(W):
        for z in range(W):
            d = math.hypot(x - c, z - c)
            if 8.5 < d <= 11.2:
                dx, dz = c - x, c - z
                toward = ('east' if dx > 0 else 'west') if abs(dx) >= abs(dz) else ('south' if dz > 0 else 'north')
                away = {'east': 'west', 'west': 'east', 'south': 'north', 'north': 'south'}[toward]
                if d > 9.8:
                    b.set(x, 1, z, B('polished_blackstone_bricks'))
                    b.set(x, 2, z, stairs(PB_STAIR, away))
                else:
                    b.set(x, 1, z, stairs(PB_STAIR, away))
    # central dais with the boss marker
    for x in range(W):
        for z in range(W):
            d = math.hypot(x - c, z - c)
            if d <= 3.2:
                b.set(x, 1, z, G_TILE if d > 1.5 else G_CHISEL)
    b.set(c, 2, c, marker('cantor'))
    # pillars topped with soul braziers
    for ang in range(0, 360, 45):
        x = int(round(c + 7.5 * math.cos(math.radians(ang))))
        z = int(round(c + 7.5 * math.sin(math.radians(ang))))
        for y in range(1, 9):
            b.set(x, y, z, pillar())
        b.set(x, 9, z, G_GILD)
        b.campfire(x, 10, z, lit=True, soul=True)
    for (x, z) in ((c, 4), (c, 18), (4, c), (18, c)):
        b.set(x, 0, z, SINGING)
    # entry (south) and the sealed vault door (north), opened by the Cantor's death
    for x in (10, 11, 12):
        for y in (1, 2, 3):
            for z in (W - 1, W - 2, 0):
                b.set(x, y, z, AIR)
            b.set(x, y, 1, SEALED_GATE)
    b.set(11, 4, 1, G_CHISEL)
    for x in (9, 13):
        for y in range(1, 6):
            b.set(x, y, 1, pillar())
    # keep both doorways flush: no stall step in front of the entrance or the vault door
    for x in (10, 11, 12):
        for z in (2, W - 3):
            b.set(x, 1, z, AIR)
    entry_jig(b, 11, 1, W - 1)
    exit_jig(b, 11, 1, 0, 'north', 'rotu:sanctum_vault')
    b.ceiling_webs(3, 10, 3, 19, 19, 6)
    return b.finish()


def sanctum_vault(seed=705):
    """Room floor at y=6 (entry jigsaw at y=7) so the Low Star Well can sink 5 blocks inside the piece."""
    F = 6
    b = Builder(13, F + 9, 13, seed)
    b.box(0, F, 0, 12, F + 8, 12, lambda: b.gloam_wall(), floor=lambda: G_TILE, ceiling=lambda: b.gloam_wall())
    doorway(b, 6, F + 1, 12)
    entry_jig(b, 6, F + 1, 12)
    # the Low Star Well: a lined shaft with a glowing heart at the bottom
    for x in range(4, 9):
        for z in range(1, 6):
            for y in range(0, F + 1):
                ring = x in (4, 8) or z in (1, 5)
                if y == 0:
                    b.set(x, y, z, b.gloam_wall())
                elif ring:
                    b.set(x, y, z, b.gloam_wall() if y < F else G_GILD)
                else:
                    b.set(x, y, z, AIR)
    for x in range(5, 8):
        for z in range(2, 5):
            b.set(x, 1, z, CHOIR_LANTERN if (x + z) % 2 else SINGING)
    for x in range(4, 9):
        for z in range(1, 6):
            if x in (4, 8) or z in (1, 5):
                b.set(x, F + 1, z, B(PB_WALL))
    for (x, z) in ((3, 8), (9, 8)):
        b.set(x, F + 1, z, G_GILD)
        b.set(x, F + 2, z, reliquary('grand'))
    b.chest(6, F + 1, 9, 'chests/sanctum_vault', 'south')
    b.set(0, F + 3, 6, mural(3))
    b.set(12, F + 3, 6, mural(2))
    for i, x in enumerate((5, 6, 7)):
        b.set(x, F + 4, 0, cipher(i + 1))
    for (x, z) in ((1, 1), (11, 1), (1, 11), (11, 11)):
        for y in range(F + 1, F + 8):
            b.set(x, y, z, pillar())
    for (x, z) in ((1, 2), (11, 2), (1, 10), (11, 10)):
        b.set(x, F + 1, z, CHOIR_LANTERN)
    b.set(6, F + 7, 9, chain())
    b.set(6, F + 6, 9, lantern(True, hanging=True))
    return b.finish()


SANCTUM = {
    'spire': sanctum_spire,
    'antechamber': sanctum_antechamber,
    'hall': sanctum_hall,
    'choir': sanctum_choir,
    'vault': sanctum_vault,
}
