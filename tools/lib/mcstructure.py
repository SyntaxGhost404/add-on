"""Bedrock .mcstructure builder.

A Structure is a sparse voxel grid. Cells that are never set are written as
structure void (palette index -1), so natural terrain shows through when the
structure is placed. Block states are typed and validated against a state
table (vanilla states from Mojang metadata + custom block states registered
by the content definitions), and every palette entry carries the complete
state set the engine expects.
"""
import json
import os

from . import nbt
from .nbt import Byte, Short, Int, Long, Float, String, List, Compound

# The engine's current block serialization version (1.21.60.33). Mojang has
# not bumped it since; all later block upgrades are keyed to this value.
BLOCK_VERSION = (1 << 24) | (21 << 16) | (60 << 8) | 33

_HERE = os.path.dirname(os.path.abspath(__file__))

# name -> list of {"name","type","values"}
STATE_TABLE = {}


def _load_vanilla_table():
    with open(os.path.join(_HERE, 'vanilla_states.json')) as f:
        data = json.load(f)
    STATE_TABLE.update(data['blocks'])


_load_vanilla_table()


_SOLID_OVERRIDE = {}


def register_custom_block(name, states, full_solid=True):
    """states: list of {"name","type","values"} in declaration order."""
    STATE_TABLE[name] = states
    _SOLID_OVERRIDE[name] = full_solid


class Block:
    """A block reference: name + (possibly partial) states."""
    __slots__ = ('name', 'states')

    def __init__(self, name, **states):
        if ':' not in name:
            name = 'minecraft:' + name
        self.name = name
        self.states = dict(states)

    def with_states(self, **states):
        b = Block(self.name, **self.states)
        b.states.update(states)
        return b

    def __repr__(self):
        return f"Block({self.name!r}, {self.states!r})"


def B(name, **states):
    """Shorthand constructor. State keys may use '__' for ':' (e.g. minecraft__cardinal_direction)."""
    fixed = {k.replace('__', ':'): v for k, v in states.items()}
    b = Block(name)
    b.states = fixed
    return b


AIR = B('air')

# Vanilla block names considered full, solid, opaque cubes for connection logic.
_FULL_EXPLICIT = {'barrel', 'crafting_table', 'cartography_table', 'loom', 'hay_block', 'suspicious_sand',
                  'suspicious_gravel', 'mob_spawner', 'grass_block', 'moss_block', 'dripstone_block',
                  'bone_block', 'amethyst_block', 'gold_block', 'raw_gold_block', 'reinforced_deepslate',
                  'soul_sand', 'soul_soil', 'podzol', 'mud', 'packed_mud', 'clay', 'hardened_clay'}
_FULL_HINTS = ('bricks', 'tiles', 'planks', 'stone', 'deepslate', 'tuff', 'sandstone', 'blackstone',
               'calcite', 'dirt', 'gravel', 'sand', 'cobble', 'obsidian', 'log', 'wool', 'sculk',
               'bookshelf', 'magma', 'terracotta', 'ore')
_NOT_FULL = ('stairs', 'slab', 'wall', 'fence', 'pane', 'bars', 'door', 'carpet', 'torch', 'lantern',
             'candle', 'chain', 'rod', 'button', 'plate', 'pot', 'skull', 'web', 'vine', 'lichen', 'vein',
             'roots', 'flower', 'short_grass', 'tall_grass', 'fern', 'bush', 'cluster', 'campfire', 'chest',
             'ladder', 'pointed', 'spore', 'hanging', 'cauldron', 'lectern', 'water', 'fire', 'jigsaw',
             'wire', 'dry_grass', 'sculk_vein', 'sculk_sensor', 'sculk_shrieker', 'carpet')


def is_full_solid(name):
    if name is None:
        return False
    if name in _SOLID_OVERRIDE:
        return _SOLID_OVERRIDE[name]
    base = name.split(':', 1)[1]
    if base == 'air' or base == 'structure_void':
        return False
    if base in _FULL_EXPLICIT:
        return True
    for bad in _NOT_FULL:
        if bad in base:
            return False
    return any(h in base for h in _FULL_HINTS)


def typed_states(name, states):
    """Return an ordered dict of typed NBT state values, filling defaults and validating."""
    if name not in STATE_TABLE:
        raise KeyError(f"block {name} is not in the state table (unknown or unsupported)")
    schema = STATE_TABLE[name]
    known = {s['name'] for s in schema}
    for k in states:
        if k not in known:
            raise KeyError(f"{name}: unknown state {k!r} (valid: {sorted(known)})")
    out = {}
    for s in sorted(schema, key=lambda s: s['name']):
        sn, st, vals = s['name'], s['type'], s['values']
        v = states.get(sn, vals[0])
        if st == 'bool':
            if isinstance(v, int) and not isinstance(v, bool):
                v = bool(v)
            if v not in (True, False):
                raise ValueError(f"{name}.{sn} must be bool, got {v!r}")
            out[sn] = Byte(1 if v else 0)
        elif st == 'int':
            if v not in vals:
                raise ValueError(f"{name}.{sn}={v!r} not in {vals}")
            out[sn] = Int(int(v))
        elif st == 'string':
            if v not in vals:
                raise ValueError(f"{name}.{sn}={v!r} not in {vals}")
            out[sn] = String(v)
        else:
            raise ValueError(f"unsupported state type {st}")
    return out


def _palette_key(block):
    ts = typed_states(block.name, block.states)
    return (block.name, tuple((k, type(v).__name__, v.value) for k, v in ts.items()))


# --- block entity helpers -------------------------------------------------

def be_container(kind, loot_table, findable=False):
    return Compound({
        'Findable': Byte(1 if findable else 0),
        'Items': List([]),
        'LootTable': String(loot_table),
        'LootTableSeed': Int(0),
        'id': String(kind),
        'isMovable': Byte(1),
    })


def be_chest(loot_table):
    return be_container('Chest', loot_table)


def be_barrel(loot_table):
    return be_container('Barrel', loot_table)


def be_brushable(block_name, loot_table):
    return Compound({
        'LootTable': String(loot_table),
        'LootTableSeed': Int(0),
        'brush_count': Int(0),
        'brush_direction': Byte(6),
        'id': String('BrushableBlock'),
        'isMovable': Byte(1),
        'type': String(block_name),
    })


def be_spawner(entity_id, delay=20, min_delay=200, max_delay=600, count=2, max_nearby=5, player_range=12,
               spawn_range=4, height=1.9, width=0.6):
    return Compound({
        'Delay': Short(delay),
        'DisplayEntityHeight': Float(height),
        'DisplayEntityScale': Float(1.0),
        'DisplayEntityWidth': Float(width),
        'EntityIdentifier': String(entity_id),
        'MaxNearbyEntities': Short(max_nearby),
        'MaxSpawnDelay': Short(max_delay),
        'MinSpawnDelay': Short(min_delay),
        'RequiredPlayerRange': Short(player_range),
        'SpawnCount': Short(count),
        'SpawnRange': Short(spawn_range),
        'id': String('MobSpawner'),
        'isMovable': Byte(0),
    })


def be_skull(rotation_deg=0.0, skull_type=0):
    return Compound({
        'DoingAnimation': Byte(0),
        'MouthTickCount': Int(0),
        'Rotation': Float(float(rotation_deg)),
        'SkullType': Byte(skull_type),
        'id': String('Skull'),
        'isMovable': Byte(0),
    })


def be_pot():
    return Compound({
        'animation': Byte(0),
        'id': String('DecoratedPot'),
        'isMovable': Byte(0),
        'item': Compound({'Count': Byte(0), 'Damage': Short(0), 'Name': String(''), 'WasPickedUp': Byte(0)}),
    })


def be_campfire():
    return Compound({
        'ItemTime1': Int(0), 'ItemTime2': Int(0), 'ItemTime3': Int(0), 'ItemTime4': Int(0),
        'id': String('Campfire'),
        'isMovable': Byte(1),
    })


def be_simple(kind):
    return Compound({'id': String(kind), 'isMovable': Byte(1)})


def be_jigsaw(name, target='minecraft:empty', pool='minecraft:empty', final_state='minecraft:air', joint='aligned'):
    return Compound({
        'final_state': String(final_state),
        'id': String('JigsawBlock'),
        'isMovable': Byte(1),
        'joint': String(joint),
        'name': String(name),
        'placement_priority': Int(0),
        'selection_priority': Int(0),
        'target': String(target),
        'target_pool': String(pool),
    })


FACING = {'down': 0, 'up': 1, 'north': 2, 'south': 3, 'west': 4, 'east': 5}
DIR_VEC = {'north': (0, 0, -1), 'south': (0, 0, 1), 'west': (-1, 0, 0), 'east': (1, 0, 0),
           'up': (0, 1, 0), 'down': (0, -1, 0)}
OPPOSITE = {'north': 'south', 'south': 'north', 'east': 'west', 'west': 'east', 'up': 'down', 'down': 'up'}
# Bedrock stairs weirdo_direction -> the direction the stair ascends toward (its tall side)
STAIR_DIR = {0: 'east', 1: 'west', 2: 'south', 3: 'north'}
STAIR_WEIRDO = {v: k for k, v in STAIR_DIR.items()}
CW = {'north': 'east', 'east': 'south', 'south': 'west', 'west': 'north'}
CCW = {v: k for k, v in CW.items()}


class Structure:
    def __init__(self, sx, sy, sz):
        self.size = (sx, sy, sz)
        self.cells = {}
        self.be = {}

    # -- basic access -------------------------------------------------
    def inside(self, x, y, z):
        sx, sy, sz = self.size
        return 0 <= x < sx and 0 <= y < sy and 0 <= z < sz

    def set(self, x, y, z, block, be=None):
        if not self.inside(x, y, z):
            raise IndexError(f"({x},{y},{z}) outside {self.size}")
        if block is None:
            self.cells.pop((x, y, z), None)
            self.be.pop((x, y, z), None)
            return
        if isinstance(block, str):
            block = B(block)
        self.cells[(x, y, z)] = block
        if be is not None:
            self.be[(x, y, z)] = be
        else:
            self.be.pop((x, y, z), None)

    def get(self, x, y, z):
        return self.cells.get((x, y, z))

    def name_at(self, x, y, z):
        b = self.cells.get((x, y, z))
        return b.name if b else None

    def fill(self, x0, y0, z0, x1, y1, z1, block):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    self.set(x, y, z, block)

    def fill_fn(self, x0, y0, z0, x1, y1, z1, fn):
        """fn(x,y,z) -> Block or None(void) or False (skip)."""
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                for z in range(min(z0, z1), max(z0, z1) + 1):
                    b = fn(x, y, z)
                    if b is False:
                        continue
                    self.set(x, y, z, b)

    def walls(self, x0, y0, z0, x1, y1, z1, block):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, z0, block)
                self.set(x, y, z1, block)
            for z in range(z0, z1 + 1):
                self.set(x0, y, z, block)
                self.set(x1, y, z, block)

    def replace(self, pred, fn):
        for pos, b in list(self.cells.items()):
            if pred(pos, b):
                nb = fn(pos, b)
                if nb is None:
                    self.cells.pop(pos, None)
                    self.be.pop(pos, None)
                else:
                    self.cells[pos] = nb

    def jigsaw(self, x, y, z, facing, name, target='minecraft:empty', pool='minecraft:empty',
               final_state='minecraft:air', joint='aligned', rotation=0):
        self.set(x, y, z, B('jigsaw', facing_direction=FACING[facing], rotation=rotation),
                 be_jigsaw(name, target, pool, final_state, joint))

    # -- connection post-processing ------------------------------------
    def _connects_wall(self, name):
        if name is None:
            return False
        base = name.split(':', 1)[1]
        return base.endswith('_wall') or base.endswith('fence_gate') or is_full_solid(name) \
            or base.endswith('_pane') or base == 'iron_bars'

    def _connects_pane(self, name):
        if name is None:
            return False
        base = name.split(':', 1)[1]
        return base.endswith('_pane') or base == 'iron_bars' or base.endswith('_wall') or is_full_solid(name)

    def _connects_fence(self, name, own):
        if name is None:
            return False
        base = name.split(':', 1)[1]
        return name == own or (base.endswith('_fence') and 'nether' not in base) or base.endswith('fence_gate') \
            or is_full_solid(name)

    def autoconnect(self):
        """Compute wall/pane/bars/fence connection states and stair corners from neighbours."""
        for (x, y, z), b in list(self.cells.items()):
            base = b.name.split(':', 1)[1]
            if base.endswith('_wall') and b.name in STATE_TABLE and any(
                    s['name'].startswith('wall_connection') for s in STATE_TABLE[b.name]):
                above = self.name_at(x, y + 1, z)
                above_solid = above is not None and (is_full_solid(above) or above.endswith('_wall'))
                con = {}
                for d in ('north', 'south', 'east', 'west'):
                    dx, dy, dz = DIR_VEC[d]
                    n = self.name_at(x + dx, y, z + dz)
                    if self._connects_wall(n):
                        con[d] = 'tall' if above_solid else 'short'
                    else:
                        con[d] = 'none'
                straight_ns = con['north'] != 'none' and con['south'] != 'none' and con['east'] == 'none' and con['west'] == 'none'
                straight_ew = con['east'] != 'none' and con['west'] != 'none' and con['north'] == 'none' and con['south'] == 'none'
                post = not (straight_ns or straight_ew) or (above is not None and above.endswith('_wall'))
                ns = dict(b.states)
                for d in con:
                    ns[f'wall_connection_type_{d}'] = con[d]
                ns['wall_post_bit'] = post
                self.cells[(x, y, z)] = Block(b.name, **ns)
            elif (base.endswith('_pane') or base == 'iron_bars') and b.name in STATE_TABLE:
                ns = dict(b.states)
                for d in ('north', 'south', 'east', 'west'):
                    dx, dy, dz = DIR_VEC[d]
                    ns[f'minecraft:connection_{d}'] = self._connects_pane(self.name_at(x + dx, y, z + dz))
                self.cells[(x, y, z)] = Block(b.name, **ns)
            elif base.endswith('_fence') and b.name in STATE_TABLE:
                ns = dict(b.states)
                for d in ('north', 'south', 'east', 'west'):
                    dx, dy, dz = DIR_VEC[d]
                    ns[f'minecraft:connection_{d}'] = self._connects_fence(self.name_at(x + dx, y, z + dz), b.name)
                self.cells[(x, y, z)] = Block(b.name, **ns)
        # stairs corners (Java-equivalent shape rules)
        for (x, y, z), b in list(self.cells.items()):
            if not b.name.endswith('_stairs') or 'weirdo_direction' not in b.states:
                continue
            facing = STAIR_DIR[b.states['weirdo_direction']]
            half = b.states.get('upside_down_bit', False)
            shape = 'none'
            fx, _, fz = DIR_VEC[facing]
            behind = self.cells.get((x + fx, y, z + fz))
            if behind is not None and behind.name.endswith('_stairs') and behind.states.get('upside_down_bit', False) == half:
                d1 = STAIR_DIR[behind.states['weirdo_direction']]
                if d1 not in (facing, OPPOSITE[facing]) and self._can_take_shape(x, y, z, b, OPPOSITE[d1]):
                    shape = 'outer_left' if d1 == CCW[facing] else 'outer_right'
            if shape == 'none':
                front = self.cells.get((x - fx, y, z - fz))
                if front is not None and front.name.endswith('_stairs') and front.states.get('upside_down_bit', False) == half:
                    d2 = STAIR_DIR[front.states['weirdo_direction']]
                    if d2 not in (facing, OPPOSITE[facing]) and self._can_take_shape(x, y, z, b, d2):
                        shape = 'inner_left' if d2 == CCW[facing] else 'inner_right'
            ns = dict(b.states)
            ns['minecraft:corner'] = shape
            self.cells[(x, y, z)] = Block(b.name, **ns)

    def _can_take_shape(self, x, y, z, b, d):
        dx, _, dz = DIR_VEC[d]
        other = self.cells.get((x + dx, y, z + dz))
        if other is None or not other.name.endswith('_stairs'):
            return True
        return not (other.states.get('weirdo_direction') == b.states.get('weirdo_direction')
                    and other.states.get('upside_down_bit', False) == b.states.get('upside_down_bit', False))

    # -- serialization -------------------------------------------------
    def to_nbt(self):
        sx, sy, sz = self.size
        palette_index = {}
        palette = []
        layer0 = [-1] * (sx * sy * sz)
        for (x, y, z), block in self.cells.items():
            key = _palette_key(block)
            idx = palette_index.get(key)
            if idx is None:
                idx = len(palette)
                palette_index[key] = idx
                palette.append(Compound({
                    'name': String(block.name),
                    'states': Compound(typed_states(block.name, block.states)),
                    'version': Int(BLOCK_VERSION),
                }))
            layer0[x * sy * sz + y * sz + z] = idx
        layer1 = [-1] * (sx * sy * sz)
        bpd = {}
        for (x, y, z), comp in self.be.items():
            if (x, y, z) not in self.cells:
                continue
            data = Compound(dict(comp.value))
            data.value['x'] = Int(x)
            data.value['y'] = Int(y)
            data.value['z'] = Int(z)
            idx = x * sy * sz + y * sz + z
            bpd[str(idx)] = Compound({'block_entity_data': data})
        root = Compound({
            'format_version': Int(1),
            'size': List([Int(sx), Int(sy), Int(sz)]),
            'structure': Compound({
                'block_indices': List([List([Int(i) for i in layer0]), List([Int(i) for i in layer1])]),
                'entities': List([]),
                'palette': Compound({
                    'default': Compound({
                        'block_palette': List(palette, Compound) if palette else List([]),
                        'block_position_data': Compound(bpd),
                    })
                }),
            }),
            'structure_world_origin': List([Int(0), Int(0), Int(0)]),
        })
        return root

    def write(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(nbt.dumps(self.to_nbt()))

    def stats(self):
        names = {}
        for b in self.cells.values():
            names[b.name] = names.get(b.name, 0) + 1
        return names
