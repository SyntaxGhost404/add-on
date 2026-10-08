"""Geometry model helpers with automatic box-UV packing.

The same Geometry object produces the .geo.json and tells texture painters
exactly where each cube face lives on the texture, so UVs always line up.
"""
import math


class Cube:
    def __init__(self, name, origin, size, *, inflate=0.0, pivot=None, rotation=None, style=None, uv=None,
                 face_uv=None):
        self.name = name
        self.origin = list(origin)
        self.size = list(size)
        self.inflate = inflate
        self.pivot = pivot
        self.rotation = rotation
        self.style = style or name
        self.uv = uv              # [u, v] once packed
        self.face_uv = face_uv    # explicit per-face uv dict (blocks)

    def footprint(self):
        w, h, d = (int(math.ceil(s)) for s in self.size)
        return 2 * (w + d), d + h

    def faces(self):
        """Face rectangles (x, y, w, h) on the texture for box UV."""
        u, v = self.uv
        w, h, d = (int(math.ceil(s)) for s in self.size)
        return {
            'up': (u + d, v, w, d),
            'down': (u + d + w, v, w, d),
            'east': (u, v + d, d, h),
            'north': (u + d, v + d, w, h),
            'west': (u + d + w, v + d, d, h),
            'south': (u + 2 * d + w, v + d, w, h),
        }

    def to_json(self):
        c = {'origin': self.origin, 'size': self.size}
        if self.face_uv is not None:
            c['uv'] = self.face_uv
        else:
            c['uv'] = list(self.uv)
        if self.inflate:
            c['inflate'] = self.inflate
        if self.pivot is not None:
            c['pivot'] = self.pivot
        if self.rotation is not None:
            c['rotation'] = self.rotation
        return c


class Bone:
    def __init__(self, name, pivot, parent=None, rotation=None, cubes=None):
        self.name = name
        self.pivot = list(pivot)
        self.parent = parent
        self.rotation = rotation
        self.cubes = cubes or []

    def to_json(self):
        b = {'name': self.name, 'pivot': self.pivot}
        if self.parent:
            b['parent'] = self.parent
        if self.rotation:
            b['rotation'] = self.rotation
        if self.cubes:
            b['cubes'] = [c.to_json() for c in self.cubes]
        return b


class Geometry:
    def __init__(self, identifier, tex_w, tex_h, bones, visible=(2, 3, (0, 1, 0))):
        self.identifier = identifier
        self.tex_w = tex_w
        self.tex_h = tex_h
        self.bones = bones
        self.visible = visible

    def cubes(self):
        for b in self.bones:
            for c in b.cubes:
                yield b, c

    def pack(self):
        """Shelf-pack every cube's box-UV footprint into the texture."""
        items = [c for _, c in self.cubes() if c.face_uv is None and c.uv is None]
        items.sort(key=lambda c: (-c.footprint()[1], -c.footprint()[0]))
        x = y = shelf_h = 0
        for c in items:
            fw, fh = c.footprint()
            if x + fw > self.tex_w:
                x = 0
                y += shelf_h
                shelf_h = 0
            if y + fh > self.tex_h:
                raise ValueError(f'{self.identifier}: texture {self.tex_w}x{self.tex_h} too small for {c.name}')
            c.uv = [x, y]
            x += fw
            shelf_h = max(shelf_h, fh)
        return self

    def to_json(self):
        vw, vh, off = self.visible
        return {
            'format_version': '1.16.0',
            'minecraft:geometry': [{
                'description': {
                    'identifier': self.identifier,
                    'texture_width': self.tex_w,
                    'texture_height': self.tex_h,
                    'visible_bounds_width': vw,
                    'visible_bounds_height': vh,
                    'visible_bounds_offset': list(off),
                },
                'bones': [b.to_json() for b in self.bones],
            }],
        }
