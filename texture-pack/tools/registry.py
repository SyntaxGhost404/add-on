"""Registry of everything the build produces.

Recipes register outputs against vanilla texture paths. Variants get extra files under
textures/blocks/tl/ and a weighted `variations` entry for their terrain atlas key.
"""
import json
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
INVENTORY = json.load(open(os.path.join(DATA, 'vanilla_inventory.json')))
BLOCK_KEYS = json.load(open(os.path.join(DATA, 'vanilla_block_keys.json')))
TERRAIN_KEYS = json.load(open(os.path.join(DATA, 'vanilla_terrain_keys.json')))
CALIBRATION = json.load(open(os.path.join(DATA, 'vanilla_calibration.json')))


def single_path_keys(path):
    """Every vanilla terrain key whose texture is exactly this one path (full block, slab, wall…)."""
    return sorted(k for k, v in TERRAIN_KEYS.items() if v.get('textures') == path)


class Output:
    def __init__(self, path, fn, *, kind='tiered', ext=None, frames=1, size=None, cutout=False, opaque=None,
                 variant=0, scale=1):
        self.path = path            # e.g. 'textures/blocks/stone' (no extension)
        self.fn = fn                # callable(variant) -> Tex | [Tex frames] | ndarray RGBA (fixed outputs)
        self.kind = kind            # 'tiered' (32/64/128) or 'fixed' (exact size, no tiers)
        inv = INVENTORY.get(path)
        self.ext = ext or (inv['ext'] if inv else 'png')
        self.frames = frames
        self.size = size
        self.cutout = cutout
        self.opaque = opaque
        self.variant = variant
        self.scale = scale          # 2 for flowing liquids (vanilla draws them at twice the block resolution)


class Registry:
    def __init__(self):
        self.outputs = []
        self.variations = {}        # terrain key -> [(path, weight)]
        self.blocks = {}            # blocks.json overrides (full entries)
        self.json_files = {}        # relative path -> data
        self.paths = set()

    def _add(self, out):
        if out.path in self.paths:
            raise ValueError(f'duplicate output {out.path}')
        self.paths.add(out.path)
        self.outputs.append(out)
        return out

    def block(self, path, fn, *, variants=None, key=None, ext=None, cutout=False, scale=1):
        """A tiered block texture. variants: list of weights; index 0 is the vanilla path itself."""
        if not path.startswith('textures/'):
            path = 'textures/blocks/' + path
        if path not in INVENTORY and not path.startswith('textures/blocks/tl/'):
            raise KeyError(f'{path} is not a vanilla texture path')
        inv = INVENTORY.get(path)
        if inv and inv['w'] != 16 * scale and inv['h'] // inv['frames'] == inv['w']:
            raise ValueError(f'{path}: vanilla is {inv["w"]}px wide; register it with scale={inv["w"] // 16}')
        self._add(Output(path, fn, ext=ext, cutout=cutout, variant=0, scale=scale))
        if variants:
            keys = key if key is not None else single_path_keys(path)
            keys = keys if isinstance(keys, (list, tuple)) else [keys]
            if not keys:
                raise ValueError(f'{path}: no single-path terrain key to attach variations to; pass key=')
            base = os.path.basename(path)
            entries = [(path, variants[0])]
            for i, w in enumerate(variants[1:], start=1):
                vp = f'textures/blocks/tl/{base}_v{i}'
                self._add(Output(vp, fn, ext='png', cutout=cutout, variant=i))
                entries.append((vp, w))
            for k in keys:
                if not k.startswith('tl_'):
                    tex = TERRAIN_KEYS.get(k, {}).get('textures')
                    if tex != path:
                        raise ValueError(f'terrain key {k!r} is {tex!r}, not the single path {path!r}; '
                                         f'variations would change its meaning')
                if k in self.variations:
                    raise ValueError(f'terrain key {k!r} registered twice')
                self.variations[k] = entries

    def anim(self, path, fn, frames, *, cutout=False, ext=None, scale=1):
        """A tiered vertical flipbook strip: fn(frame_index, frames) -> Tex."""
        if not path.startswith('textures/'):
            path = 'textures/blocks/' + path
        inv = INVENTORY.get(path)
        if inv and inv['frames'] != frames:
            raise ValueError(f'{path}: vanilla has {inv["frames"]} frames, recipe makes {frames}')
        if inv and inv['w'] != 16 * scale:
            raise ValueError(f'{path}: vanilla frame width {inv["w"]} needs scale={inv["w"] // 16}')
        self._add(Output(path, fn, frames=frames, ext=ext, cutout=cutout, scale=scale))

    def fixed(self, path, fn, size, *, ext='png', opaque=False):
        """An exact-size image (environment, colormaps, particle sheets): fn() -> RGBA float array."""
        self._add(Output(path, fn, kind='fixed', size=size, ext=ext, opaque=opaque))

    def block_entry(self, block, **changes):
        """Override a blocks.json entry, starting from the vanilla entry."""
        from copy import deepcopy
        vanilla = VANILLA_BLOCKS.get(block)
        if vanilla is None:
            raise KeyError(f'no vanilla blocks.json entry {block}')
        entry = deepcopy(self.blocks.get(block, vanilla))
        entry.update(changes)
        self.blocks[block] = entry

    def json(self, rel, data):
        self.json_files[rel] = data


def _load_vanilla_blocks():
    p = os.path.join(DATA, 'vanilla_blocks.json')
    return json.load(open(p)) if os.path.exists(p) else {}


VANILLA_BLOCKS = _load_vanilla_blocks()
