#!/usr/bin/env python3
"""Walkability test for structure pieces.

Simulates a 2-block-tall player (walk, step or jump up 1 block, drop up to 3) through each
generated .mcstructure piece and checks that the entrance reaches every exit doorway (jigsaw).
Sealed gates and veilstone are solid until "opened", so the test also proves that the puzzle
gates really are the only way through.

Surface start pieces (ossuary mausoleum, sanctum spire) are entered from the surrounding ground:
structure void below their ground layer counts as terrain and above it as open air. Every other
piece is fully underground, so its void cells count as solid rock.

Usage: python3 tools/build.py --no-dist && python3 tools/tests/test_walkability.py
"""
import glob
import os
import sys
from collections import deque

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

from lib import nbtread  # noqa: E402
from structures.underground import OSS_GROUND, SANC_GROUND  # noqa: E402

STRUCTS = os.path.join(ROOT, 'packs', 'ruins_of_the_unnamed_bp', 'structures', 'rotu')

PASSABLE = ('air', 'jigsaw', 'spawn_marker', 'carpet', 'candle', 'torch', 'web', 'chain', 'lantern', 'deadbush',
            'hushing_plate')
TALL = ('_wall', 'fence')                          # 1.5 blocks: cannot be jumped onto
SURFACE_START = {'ossuary_mausoleum': OSS_GROUND, 'sanctum_spire': SANC_GROUND}
# pieces whose exits sit behind a puzzle: (exits reachable while closed, exits reachable once opened)
GATED = {'sanctum_antechamber', 'sanctum_choir'}
PLUGS = {'ossuary_cap'}                            # deliberate rubble plug that closes a corridor


def load(path):
    d = nbtread.plain(nbtread.load(path)[1])
    sx, sy, sz = d['size']
    st = d['structure']
    idx = st['block_indices'][0]
    pal = st['palette']['default']
    names = [b['name'] for b in pal['block_palette']]
    grid = {}
    for x in range(sx):
        for y in range(sy):
            for z in range(sz):
                i = idx[(x * sy + y) * sz + z]
                grid[(x, y, z)] = None if i < 0 else names[i]
    jigsaws = []
    for k, data in pal.get('block_position_data', {}).items():
        be = data.get('block_entity_data', {})
        if be.get('id') == 'JigsawBlock':
            i = int(k)
            x, rem = divmod(i, sy * sz)
            y, z = divmod(rem, sz)
            jigsaws.append(((x, y, z), be['name']))
    return (sx, sy, sz), grid, jigsaws


class Piece:
    def __init__(self, name, size, grid, ground=None, opened=False):
        self.name, self.size, self.grid, self.ground, self.opened = name, size, grid, ground, opened

    def block(self, p):
        x, y, z = p
        sx, sy, sz = self.size
        if not (0 <= x < sx and 0 <= z < sz) or y < 0:
            # outside the piece: rock underground, open air above the surface for start pieces
            return 'air' if self.ground is not None and y >= self.ground else 'rock'
        if y >= sy:
            return 'air'
        b = self.grid[p]
        if b is None:
            return 'air' if self.ground is not None and y >= self.ground else 'rock'
        return b

    def passable(self, p):
        b = self.block(p)
        if self.opened and ('sealed_gate' in b or 'veilstone' in b):
            return True
        return any(k in b for k in PASSABLE)

    def solid(self, p):
        return not self.passable(p)

    def tall(self, p):
        b = self.block(p)
        return any(k in b for k in TALL)

    def standable(self, p):
        x, y, z = p
        return self.passable(p) and self.passable((x, y + 1, z)) and self.solid((x, y - 1, z))

    def neighbours(self, p):
        x, y, z = p
        for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, nz = x + dx, z + dz
            if self.standable((nx, y, nz)):
                yield (nx, y, nz)
            if (self.passable((x, y + 2, z)) and self.standable((nx, y + 1, nz))
                    and not self.tall((nx, y, nz))):
                yield (nx, y + 1, nz)
            if self.passable((nx, y, nz)) and self.passable((nx, y + 1, nz)):
                for drop in (1, 2, 3):
                    q = (nx, y - drop, nz)
                    if not self.passable(q):
                        break
                    if self.standable(q):
                        yield q
                        break

    def reach(self, start):
        seen = {start}
        todo = deque([start])
        sx, sy, sz = self.size
        while todo:
            p = todo.popleft()
            for q in self.neighbours(p):
                if q in seen:
                    continue
                if not (-3 <= q[0] <= sx + 2 and -3 <= q[2] <= sz + 2 and 0 <= q[1] <= sy + 2):
                    continue
                seen.add(q)
                todo.append(q)
        return seen


def check(path):
    name = os.path.splitext(os.path.basename(path))[0]
    if name in PLUGS:
        return name, None, 'plug'
    size, grid, jigs = load(path)
    ground = SURFACE_START.get(name)
    entries = [p for p, n in jigs if n == 'rotu:entry']
    exits = [p for p, n in jigs if n != 'rotu:entry']
    if not entries and ground is None:
        return name, None, 'no entrance (surface piece without jigsaws)'
    problems = []
    for opened in (False, True):
        piece = Piece(name, size, grid, ground, opened)
        if ground is not None:
            start = (-2, ground, -2)
        else:
            start = entries[0]
        if not piece.standable(start):
            problems.append(f'start {start} not standable')
            continue
        seen = piece.reach(start)
        reached = [e for e in exits if e in seen]
        if name in GATED and not opened:
            if reached:
                problems.append(f'exit {reached} reachable while the gate is still sealed')
        elif len(reached) != len(exits):
            problems.append(f'unreachable exits {[e for e in exits if e not in seen]} (opened={opened})')
    return name, len(exits), '; '.join(problems) or 'ok'


def main():
    failures = 0
    paths = sorted(glob.glob(os.path.join(STRUCTS, '*.mcstructure')))
    for path in paths:
        name, n, result = check(path)
        if n is None:
            continue
        flag = 'ok ' if result == 'ok' else 'FAIL'
        if result != 'ok':
            failures += 1
        print(f'  {flag} {name:28s} exits={n}  {result if result != "ok" else ""}')
    print(f'walkability: {failures} failing pieces')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
