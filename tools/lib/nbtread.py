"""Minimal little-endian (Bedrock) NBT reader for inspecting .mcstructure files."""
import struct
import sys
import json


class Reader:
    def __init__(self, data):
        self.d = data
        self.p = 0

    def take(self, n):
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def u8(self):
        return self.take(1)[0]

    def i8(self):
        return struct.unpack('<b', self.take(1))[0]

    def i16(self):
        return struct.unpack('<h', self.take(2))[0]

    def i32(self):
        return struct.unpack('<i', self.take(4))[0]

    def i64(self):
        return struct.unpack('<q', self.take(8))[0]

    def f32(self):
        return struct.unpack('<f', self.take(4))[0]

    def f64(self):
        return struct.unpack('<d', self.take(8))[0]

    def string(self):
        n = struct.unpack('<H', self.take(2))[0]
        return self.take(n).decode('utf-8', 'replace')

    def payload(self, t):
        if t == 1:
            return ('byte', self.i8())
        if t == 2:
            return ('short', self.i16())
        if t == 3:
            return ('int', self.i32())
        if t == 4:
            return ('long', self.i64())
        if t == 5:
            return ('float', self.f32())
        if t == 6:
            return ('double', self.f64())
        if t == 7:
            n = self.i32()
            return ('byte_array', list(self.take(n)))
        if t == 8:
            return ('string', self.string())
        if t == 9:
            et = self.u8()
            n = self.i32()
            if et == 0:
                # Some Bedrock files store empty lists as type End with a nonzero count.
                return ('list', et, [])
            return ('list', et, [self.payload(et) for _ in range(n)])
        if t == 10:
            out = {}
            while True:
                tt = self.u8()
                if tt == 0:
                    break
                name = self.string()
                out[name] = self.payload(tt)
            return ('compound', out)
        if t == 11:
            n = self.i32()
            return ('int_array', [self.i32() for _ in range(n)])
        if t == 12:
            n = self.i32()
            return ('long_array', [self.i64() for _ in range(n)])
        raise ValueError('bad tag %d at %d' % (t, self.p))

    def root(self):
        t = self.u8()
        name = self.string()
        return name, self.payload(t)


def plain(v):
    """Strip type annotations into plain python values."""
    kind = v[0]
    if kind == 'compound':
        return {k: plain(x) for k, x in v[1].items()}
    if kind == 'list':
        return [plain(x) for x in v[2]]
    return v[1]


def load(path):
    with open(path, 'rb') as f:
        data = f.read()
    r = Reader(data)
    name, val = r.root()
    return name, val


if __name__ == '__main__':
    path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'summary'
    name, val = load(path)
    p = plain(val)
    if mode == 'typed':
        def show(v, ind=0, maxlist=8):
            pad = '  ' * ind
            if v[0] == 'compound':
                for k, x in v[1].items():
                    if x[0] in ('compound', 'list'):
                        print(f"{pad}{k}: <{x[0]}{'' if x[0]=='compound' else ' of '+str(x[1])+' n='+str(len(x[2]))}>")
                        show(x, ind + 1, maxlist)
                    else:
                        val = x[1]
                        if isinstance(val, list) and len(val) > maxlist:
                            val = str(val[:maxlist]) + '...(%d)' % len(x[1])
                        print(f"{pad}{k}: ({x[0]}) {val}")
            elif v[0] == 'list':
                for i, x in enumerate(v[2][:maxlist]):
                    print(f"{pad}[{i}] <{x[0]}>" if x[0] in ('compound', 'list') else f"{pad}[{i}] ({x[0]}) {x[1]}")
                    if x[0] in ('compound', 'list'):
                        show(x, ind + 1, maxlist)
                if len(v[2]) > maxlist:
                    print(f"{pad}... ({len(v[2])} items)")
        show(val)
    else:
        size = p.get('size')
        s = p.get('structure', {})
        palette = s.get('palette', {}).get('default', {})
        bp = palette.get('block_palette', [])
        ents = s.get('entities', [])
        bpd = palette.get('block_position_data', {})
        print('root name:', repr(name), 'format_version:', p.get('format_version'), 'size:', size,
              'origin:', p.get('structure_world_origin'))
        print('palette size:', len(bp), 'entities:', len(ents), 'block_position_data:', len(bpd))
        for i, b in enumerate(bp):
            print('  ', i, b.get('name'), json.dumps(b.get('states')), 'v=', b.get('version'))
        for e in ents:
            print('  ENTITY', e.get('identifier'), e.get('definitions'), {k: e[k] for k in e if k in ('Pos',)})
        for k, v in list(bpd.items())[:20]:
            print('  BPD', k, json.dumps(v)[:400])
