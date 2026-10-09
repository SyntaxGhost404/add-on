"""Building kit shared by all structure builders."""
import random

from lib.mcstructure import (Structure, B, AIR, be_chest, be_barrel, be_brushable, be_spawner, be_skull, be_pot,
                             be_campfire, be_simple, STAIR_WEIRDO)

R = 'rotu:'
LT = 'loot_tables/rotu/'

# --- custom blocks --------------------------------------------------------------------
GB = B(R + 'gloamstone_bricks')
GB_CRACK = B(R + 'cracked_gloamstone_bricks')
GB_MOSS = B(R + 'mossy_gloamstone_bricks')
G_TILE = B(R + 'gloamstone_tiles')
G_CHISEL = B(R + 'chiseled_gloamstone')
G_GILD = B(R + 'gilded_gloamstone')
CHOIR_LANTERN = B(R + 'choir_lantern')
SINGING = B(R + 'singing_stone')
SEALED_GATE = B(R + 'sealed_gate')
VEIL = B(R + 'veilstone', **{'rotu:revealed': False})


def pillar(axis='y'):
    face = {'y': 'up', 'x': 'east', 'z': 'south'}[axis]
    return B(R + 'gloamstone_pillar', **{'minecraft:block_face': face})


def mural(panel):
    return B(R + 'glyph_mural', **{'rotu:panel': panel})


def cipher(glyph):
    return B(R + 'cipher_stone', **{'rotu:glyph': glyph})


def dial(solution, start):
    return B(R + 'glyph_dial', **{'rotu:glyph': start, 'rotu:solution': solution})


def urn(sealed=True, style=0):
    return B(R + 'funerary_urn', **{'rotu:sealed': sealed, 'rotu:style': style})


def plate():
    return B(R + 'hushing_plate', **{'rotu:spent': False})


def reliquary(tier='lesser'):
    return B(R + 'reliquary', **{'rotu:tier': tier})


def marker(mob):
    return B(R + 'spawn_marker', **{'rotu:mob': mob})


def sigil_lock():
    return B(R + 'sigil_lock', **{'rotu:unlocked': False})


def desk(facing='south'):
    return B(R + 'scriptorium_desk', **{'minecraft:cardinal_direction': facing})


# --- vanilla helpers ------------------------------------------------------------------------
def stairs(name, ascend, upside=False):
    return B(name, weirdo_direction=STAIR_WEIRDO[ascend], upside_down_bit=upside)


def slab(name, top=False):
    return B(name, **{'minecraft:vertical_half': 'top' if top else 'bottom'})


def candle(n=1, lit=False, color=''):
    name = f'{color}_candle' if color else 'candle'
    return B(name, candles=n - 1, lit=lit)


def lantern(soul=True, hanging=False):
    return B('soul_lantern' if soul else 'lantern', hanging=hanging)


def chain():
    return B('iron_chain', pillar_axis='y')


def torch(facing='top', soul=True):
    return B('soul_torch' if soul else 'torch', torch_facing_direction=facing)


WEB = B('web')
COBWEB = WEB


class Builder:
    """Wraps a Structure with a seeded RNG and decoration helpers."""

    def __init__(self, sx, sy, sz, seed):
        self.s = Structure(sx, sy, sz)
        self.rng = random.Random(seed)
        self.size = (sx, sy, sz)

    # palette helpers --------------------------------------------------------------
    def pick(self, weighted):
        total = sum(w for _, w in weighted)
        r = self.rng.uniform(0, total)
        for b, w in weighted:
            r -= w
            if r <= 0:
                return b
        return weighted[-1][0]

    def gloam_wall(self):
        return self.pick([(GB, 60), (GB_CRACK, 22), (GB_MOSS, 10), (G_TILE, 4), (B('cracked_deepslate_bricks'), 4)])

    def gloam_floor(self):
        return self.pick([(G_TILE, 55), (GB, 15), (GB_CRACK, 15), (B('polished_deepslate'), 10), (B('deepslate_tiles'), 5)])

    def dark_wall(self):
        return self.pick([(B('polished_blackstone_bricks'), 45), (B('cracked_polished_blackstone_bricks'), 20),
                          (GB, 25), (GB_CRACK, 10)])

    def rubble(self):
        return self.pick([(B('cobbled_deepslate'), 40), (GB_CRACK, 25), (B('gravel'), 20), (B('tuff'), 15)])

    # geometry helpers ----------------------------------------------------------------
    def set(self, x, y, z, b, be=None):
        if self.s.inside(x, y, z):
            self.s.set(x, y, z, b, be)

    def get(self, x, y, z):
        return self.s.get(x, y, z)

    def fill(self, x0, y0, z0, x1, y1, z1, b):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set(x, y, z, b() if callable(b) else b)

    def box(self, x0, y0, z0, x1, y1, z1, wall, floor=None, ceiling=None, interior=AIR):
        """Hollow room: walls on the 4 sides, floor at y0, ceiling at y1, interior filled with `interior`."""
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    edge = x in (x0, x1) or z in (z0, z1)
                    if y == y0:
                        b = floor if floor is not None else wall
                    elif y == y1:
                        b = ceiling if ceiling is not None else wall
                    elif edge:
                        b = wall
                    else:
                        b = interior
                    if b is None:
                        continue
                    self.set(x, y, z, b() if callable(b) else b)

    def erode(self, x0, y0, z0, x1, y1, z1, chance, to=None, only=None, top_bias=0.0):
        """Randomly remove (or replace) blocks; higher blocks erode more with top_bias."""
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                for z in range(z0, z1 + 1):
                    b = self.get(x, y, z)
                    if b is None or b.name == 'minecraft:air':
                        continue
                    if only and b.name not in only:
                        continue
                    hy = (y - y0) / max(1, (y1 - y0))
                    if self.rng.random() < chance + top_bias * hy:
                        self.set(x, y, z, (to() if callable(to) else to) if to is not None else None)

    def scatter(self, x0, y0, z0, x1, y1, z1, block, count, need_floor=True, only_air=True):
        """Place decorations on air cells that rest on a solid block."""
        placed = 0
        tries = 0
        while placed < count and tries < count * 40:
            tries += 1
            x = self.rng.randint(x0, x1)
            y = self.rng.randint(y0, y1)
            z = self.rng.randint(z0, z1)
            cur = self.get(x, y, z)
            if only_air and not (cur is not None and cur.name == 'minecraft:air'):
                continue
            below = self.get(x, y - 1, z)
            if need_floor and (below is None or below.name in ('minecraft:air', 'minecraft:web')):
                continue
            b = block() if callable(block) else block
            if isinstance(b, tuple):
                self.set(x, y, z, b[0], b[1])
            else:
                self.set(x, y, z, b)
            placed += 1
        return placed

    def ceiling_webs(self, x0, y, z0, x1, z1, count):
        for _ in range(count * 10):
            if count <= 0:
                break
            x, z = self.rng.randint(x0, x1), self.rng.randint(z0, z1)
            if self.get(x, y, z) is not None and self.get(x, y, z).name == 'minecraft:air':
                above = self.get(x, y + 1, z)
                if above is not None and above.name != 'minecraft:air':
                    self.set(x, y, z, WEB)
                    count -= 1

    def spiral_stairs(self, cx, cz, y_bottom, y_top, wall, step_block='deepslate_tile_stairs', center=None,
                      landing=None):
        """Clockwise spiral in a 5x5 shaft centred on (cx, cz): walls ring, central column, 3x3 stair ring.

        The stair ring occupies the 8 cells around the column; one step per cell, rising 1 block per cell.
        """
        ring = [(-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0)]
        nxt = {i: ring[(i + 1) % 8] for i in range(8)}
        # outer wall ring and core
        for y in range(y_bottom, y_top + 1):
            for dx in range(-2, 3):
                for dz in range(-2, 3):
                    if abs(dx) == 2 or abs(dz) == 2:
                        self.set(cx + dx, y, cz + dz, wall() if callable(wall) else wall)
                    elif dx == 0 and dz == 0:
                        self.set(cx, y, cz, center or pillar())
                    else:
                        self.set(cx + dx, y, cz + dz, AIR)
        y = y_bottom
        i = 0
        while y <= y_top:
            dx, dz = ring[i % 8]
            ndx, ndz = nxt[i % 8]
            # ascend toward the next cell
            if ndx > dx:
                asc = 'east'
            elif ndx < dx:
                asc = 'west'
            elif ndz > dz:
                asc = 'south'
            else:
                asc = 'north'
            self.set(cx + dx, y, cz + dz, stairs('minecraft:' + step_block, asc))
            # solid support under the step
            if y - 1 >= y_bottom:
                below = self.get(cx + dx, y - 1, cz + dz)
                if below is None or below.name == 'minecraft:air':
                    self.set(cx + dx, y - 1, cz + dz, B('polished_deepslate'))
            y += 1
            i += 1
        if landing:
            landing()

    # block entity helpers ------------------------------------------------------------------
    def chest(self, x, y, z, loot, facing='south'):
        self.set(x, y, z, B('chest', minecraft__cardinal_direction=facing), be_chest(LT + loot + '.json'))

    def barrel(self, x, y, z, loot, facing=1):
        self.set(x, y, z, B('barrel', facing_direction=facing, open_bit=False), be_barrel(LT + loot + '.json'))

    def suspicious(self, x, y, z, loot, sand=False):
        name = 'minecraft:suspicious_sand' if sand else 'minecraft:suspicious_gravel'
        self.set(x, y, z, B(name, brushed_progress=0, hanging=False), be_brushable(name, LT + loot + '.json'))

    def spawner(self, x, y, z, entity, **kw):
        self.set(x, y, z, B('mob_spawner'), be_spawner(entity, **kw))

    def skull(self, x, y, z, rot=0.0, wither=False):
        self.set(x, y, z, B('wither_skeleton_skull' if wither else 'skeleton_skull', facing_direction=1),
                 be_skull(rot, 1 if wither else 0))

    def pot(self, x, y, z, direction=0):
        self.set(x, y, z, B('decorated_pot', direction=direction), be_pot())

    def campfire(self, x, y, z, lit=False, soul=False, facing='south'):
        self.set(x, y, z, B('soul_campfire' if soul else 'campfire', extinguished=not lit,
                            minecraft__cardinal_direction=facing), be_campfire())

    def jigsaw(self, x, y, z, facing, name, target='minecraft:empty', pool='minecraft:empty', final='minecraft:air',
               priority=0):
        self.s.jigsaw(x, y, z, facing, name, target, pool, final, selection_priority=priority)

    def finish(self):
        self.s.autoconnect()
        return self.s
