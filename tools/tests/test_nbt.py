"""NBT writer tests: byte-exact re-encode of reference files + synthetic round trip.

Usage: python3 tools/tests/test_nbt.py [DIR_WITH_MCSTRUCTURE_FILES ...]
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from lib import nbt, nbtread  # noqa: E402
from lib.mcstructure import Structure, B, be_chest, be_brushable  # noqa: E402

CLS = {'byte': nbt.Byte, 'short': nbt.Short, 'int': nbt.Int, 'long': nbt.Long, 'float': nbt.Float,
       'double': nbt.Double, 'string': nbt.String}


def to_tag(v):
    k = v[0]
    if k == 'compound':
        return nbt.Compound({n: to_tag(x) for n, x in v[1].items()})
    if k == 'list':
        et = v[1]
        items = [to_tag(x) for x in v[2]]
        if et == 0:
            return nbt.List([])
        cls = {1: nbt.Byte, 2: nbt.Short, 3: nbt.Int, 4: nbt.Long, 5: nbt.Float, 6: nbt.Double,
               8: nbt.String, 9: nbt.List, 10: nbt.Compound, 11: nbt.IntArray}[et]
        return nbt.List(items, cls)
    if k == 'int_array':
        return nbt.IntArray(v[1])
    return CLS[k](v[1])


def reencode(path):
    data = open(path, 'rb').read()
    name, root = nbtread.Reader(data).root()
    out = nbt.dumps(to_tag(root), name)
    return data, out


def main(ref_dirs):
    n = same = 0
    for d in ref_dirs:
        for dp, dn, fn in os.walk(d):
            for f in fn:
                if f.endswith('.mcstructure'):
                    a, b = reencode(os.path.join(dp, f))
                    n += 1
                    if a == b:
                        same += 1
                    elif n - same <= 3:
                        print('DIFF', f, len(a), len(b))
    print(f'reencoded {n} reference files, byte-identical: {same}')

    s = Structure(5, 4, 6)
    s.fill(0, 0, 0, 4, 0, 5, B('deepslate_bricks'))
    s.set(2, 1, 2, B('chest', minecraft__cardinal_direction='east'), be_chest('loot_tables/test.json'))
    s.set(1, 1, 1, B('deepslate_brick_stairs', weirdo_direction=2, upside_down_bit=False))
    s.set(3, 1, 3, B('suspicious_gravel'), be_brushable('minecraft:suspicious_gravel', 'loot_tables/x.json'))
    s.fill(0, 1, 5, 4, 1, 5, B('deepslate_brick_wall'))
    s.jigsaw(4, 1, 0, 'east', 'rotu:test', 'rotu:target', 'rotu:pool', 'minecraft:air')
    s.autoconnect()
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, 'rotu_test.mcstructure')
        s.write(path)
        name, root = nbtread.load(path)
    p = nbtread.plain(root)
    pal = p['structure']['palette']['default']['block_palette']
    assert p['size'] == [5, 4, 6], p['size']
    idx = p['structure']['block_indices'][0]
    sy, sz = 4, 6
    chest_i = idx[2 * sy * sz + 1 * sz + 2]
    assert pal[chest_i]['name'] == 'minecraft:chest'
    assert pal[chest_i]['states'] == {'minecraft:cardinal_direction': 'east'}
    bpd = p['structure']['palette']['default']['block_position_data']
    assert bpd[str(2 * sy * sz + 1 * sz + 2)]['block_entity_data']['LootTable'] == 'loot_tables/test.json'
    walls = [b for b in pal if b['name'].endswith('_wall')]
    assert any(b['states']['wall_connection_type_east'] == 'short' for b in walls), walls
    assert idx[0 * sy * sz + 3 * sz + 0] == -1  # untouched cell is structure void
    stairs = [b for b in pal if b['name'].endswith('_stairs')][0]
    assert stairs['states']['minecraft:corner'] == 'none'
    print('synthetic structure round-trip OK; palette:', [b['name'] for b in pal])


if __name__ == '__main__':
    main(sys.argv[1:])
