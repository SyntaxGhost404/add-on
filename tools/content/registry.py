"""Central registry collecting everything the build writes into the two packs."""
from collections import OrderedDict

NS = 'rotu'
FORMAT_BLOCK = '1.26.50'
FORMAT_ITEM = '1.26.50'
FORMAT_ENTITY = '1.26.50'
FORMAT_WORLDGEN = '1.21.20'
FORMAT_RECIPE = '1.20.10'
FORMAT_SPAWN = '1.8.0'


def nid(name):
    return f'{NS}:{name}'


class Registry:
    def __init__(self):
        self.bp = OrderedDict()          # relative path -> json data
        self.rp = OrderedDict()
        self.lang = OrderedDict()        # key -> english text
        self.terrain_textures = OrderedDict()   # texture key -> path (no extension) or list
        self.item_textures = OrderedDict()
        self.block_sounds = OrderedDict()       # block id -> sound type
        self.textures_to_paint = []      # (kind, name, painter-key)

    def add_bp(self, path, data):
        if path in self.bp:
            raise ValueError(f'duplicate BP file {path}')
        self.bp[path] = data

    def add_rp(self, path, data):
        if path in self.rp:
            raise ValueError(f'duplicate RP file {path}')
        self.rp[path] = data

    def tr(self, key, text):
        if key in self.lang and self.lang[key] != text:
            raise ValueError(f'conflicting lang key {key}')
        self.lang[key] = text

    def terrain(self, key, path):
        self.terrain_textures[key] = path

    def item_tex(self, key, path):
        self.item_textures[key] = path


REG = Registry()
