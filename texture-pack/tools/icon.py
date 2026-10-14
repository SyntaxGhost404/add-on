"""Pack icon: an isometric cut-away of the pack's own terrain, drawn from the built 64x textures."""
import os

import numpy as np
from PIL import Image

import preview

B = 'textures/blocks/'
PLAINS = (0.2, 0.68)        # colormap (1 - temperature, 1 - downfall x temperature) for temperature 0.8, downfall 0.4
SKY = ('#79a6ea', '#c3d5e6')


def _load(pack, path, ext='png'):
    with Image.open(os.path.join(pack, f'{path}.{ext}')) as im:
        a = np.asarray(im.convert('RGBA'), np.float32) / 255
    return a[:a.shape[1]]                   # first frame of a flipbook


def _climate(pack, name):
    m = _load(pack, f'textures/colormap/{name}')
    x, y = PLAINS
    return m[int(y * (m.shape[0] - 1)), int(x * (m.shape[1] - 1)), :3]


def _hex(c):
    return np.array([int(c[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)


def scene():
    """A 4 x 4 cut-away (deepslate, stone with ores, soil, grass) with a young oak on top."""
    world = {}
    for x in range(4):
        for z in range(4):
            for y, name in enumerate(('deepslate', 'stone', 'dirt', 'grass')):
                world[(x, y, z)] = name
    world[(1, 0, 3)] = 'diamond_ore'
    world[(3, 1, 1)] = 'iron_ore'
    world[(1, 4, 1)] = world[(1, 5, 1)] = 'log'
    for x in range(3):
        for z in range(3):
            world[(x, 6, z)] = 'leaves'
    for x, z in ((1, 1), (0, 1), (2, 1), (1, 0), (1, 2)):
        world[(x, 7, z)] = 'leaves'
    return world


def render_icon(pack, out, size=256):
    grass, foliage = _climate(pack, 'grass'), _climate(pack, 'foliage')
    side = _load(pack, B + 'grass_side', 'tga')
    mask = side[..., 3] > 0.5
    side[..., 3] = 1.0

    def plain(path):
        return {'*': (_load(pack, B + path), None)}
    textures = {
        'grass': {'up': (_load(pack, B + 'grass_top'), grass), 'south': (side, (grass, mask)),
                  'east': (side, (grass, mask))},
        'dirt': plain('dirt'),
        'stone': plain('stone'),
        'iron_ore': plain('iron_ore'),
        'deepslate': {'up': (_load(pack, B + 'deepslate/deepslate_top'), None),
                      '*': (_load(pack, B + 'deepslate/deepslate'), None)},
        'diamond_ore': plain('deepslate/deepslate_diamond_ore'),
        'log': {'up': (_load(pack, B + 'log_oak_top'), None), '*': (_load(pack, B + 'log_oak'), None)},
        'leaves': {'*': (_load(pack, B + 'leaves_oak_opaque'), foliage)},
    }
    for t in textures.values():
        for face in ('south', 'east'):
            t.setdefault(face, t.get('*'))
        t.setdefault('up', t.get('*'))
    art = preview.render(scene(), textures, scale=96, sky=None)
    # Fit into the icon with a margin, over a soft sky gradient.
    inner = int(size * 0.84)
    w, h = art.size
    k = inner / max(w, h)
    art = art.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS)
    t = np.linspace(0, 1, size, dtype=np.float32)[:, None, None]
    top, bottom = _hex(SKY[0]), _hex(SKY[1])
    bg = np.broadcast_to(top * (1 - t) + bottom * t, (size, size, 3))
    icon = Image.fromarray((bg * 255).astype(np.uint8), 'RGB').convert('RGBA')
    icon.alpha_composite(art, ((size - art.size[0]) // 2, (size - art.size[1]) // 2 + size // 40))
    icon.convert('RGB').save(out, optimize=True)
    return out
