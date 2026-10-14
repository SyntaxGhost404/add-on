"""blocks.json tuning: corner-shading depth and per-block random rotation.

`ambient_occlusion_exponent` shapes the engine's smooth-lighting corner shade for a block (absent = 1.0;
vanilla uses 0.55 for sand, 0.8 for leaves and 2.0 for obsidian). Rock and jointed masonry get a little more,
so cave walls and courses read as solid relief; loose snow gets less, as if light scattered through it.
Every block whose faces show only textures from a group gets that group's value: slabs, stairs and walls match
their full block, ores match the rock around them, and infested blocks stay indistinguishable from the real thing.

`isotropic` rotates and mirrors a face at random per block position, which hides tiling. It is only safe for
textures baked with overhead light ('over') and no upright motif, so that set is listed by hand.
"""
from registry import TERRAIN_KEYS, VANILLA_BLOCKS

B = 'textures/blocks/'
ORES = ('coal', 'copper', 'iron', 'gold', 'redstone', 'lapis', 'diamond', 'emerald')

ROCK = {B + p for p in (
    'stone', 'cobblestone', 'cobblestone_mossy', 'stone_granite', 'stone_diorite', 'stone_andesite', 'tuff',
    'calcite', 'dripstone_block', 'blackstone', 'blackstone_top', 'gilded_blackstone', 'basalt_side', 'basalt_top',
    'end_stone', 'bedrock', 'deepslate/deepslate', 'deepslate/deepslate_top', 'deepslate/cobbled_deepslate')}
ROCK |= {B + f'{o}_ore' for o in ORES} | {B + f'deepslate/deepslate_{o}_ore' for o in ORES}

MASONRY = {B + p for p in (
    'stonebrick', 'stonebrick_mossy', 'stonebrick_cracked', 'stonebrick_carved', 'deepslate/deepslate_bricks',
    'deepslate/deepslate_tiles', 'deepslate/cracked_deepslate_bricks', 'deepslate/cracked_deepslate_tiles',
    'tuff_bricks', 'chiseled_tuff_bricks', 'chiseled_tuff_bricks_top', 'polished_blackstone_bricks',
    'cracked_polished_blackstone_bricks', 'brick', 'mud_bricks', 'end_bricks', 'nether_brick', 'red_nether_brick',
    'cracked_nether_bricks', 'chiseled_nether_bricks', 'resin_bricks', 'cinnabar_bricks', 'sulfur_bricks')}

SOIL = {B + p for p in ('dirt', 'coarse_dirt', 'gravel', 'dirt_with_roots', 'dirt_podzol_top', 'dirt_podzol_side')}

SNOW = {B + p for p in ('snow', 'powder_snow')}

AO = ((MASONRY, 1.3), (ROCK, 1.2), (SOIL, 1.15), (SNOW, 0.75))
NOT_CUBES = ('button', 'pressure_plate', 'invisible')

# Overhead-lit textures without an upright motif (soul sand keeps its faces upright, so it is not here).
ISOTROPIC = {B + p for p in ('mud', 'packed_mud', 'moss_block', 'pale_moss_block', 'soul_soil', 'powder_snow')}
ISOTROPIC |= {B + f'concrete_powder_{c}' for c in (
    'white', 'orange', 'magenta', 'light_blue', 'yellow', 'lime', 'pink', 'gray', 'silver', 'cyan', 'purple',
    'blue', 'brown', 'green', 'red', 'black')}


def texture_paths(entry):
    """The set of texture paths a blocks.json entry shows, or None if any key isn't a plain path or path list."""
    t = entry.get('textures')
    keys = [t] if isinstance(t, str) else list(t.values()) if isinstance(t, dict) else []
    if not keys:
        return None
    out = set()
    for k in keys:
        v = TERRAIN_KEYS.get(k, {}).get('textures')
        if isinstance(v, str):
            out.add(v)
        elif isinstance(v, list) and all(isinstance(x, str) for x in v):
            out.update(v)
        else:
            return None
    return out


def register(R):
    for name in sorted(VANILLA_BLOCKS):
        entry = VANILLA_BLOCKS[name]
        if not isinstance(entry, dict) or any(s in name.lower() for s in NOT_CUBES):
            continue
        paths = texture_paths(entry)
        if not paths:
            continue
        for group, exponent in AO:
            if paths <= group:
                R.block_entry(name, ambient_occlusion_exponent=exponent)
                break
        if paths <= ISOTROPIC and entry.get('isotropic') is not True:
            R.block_entry(name, isotropic=True)
