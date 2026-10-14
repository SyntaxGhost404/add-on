# Terra Lucida — Design Document

A naturalistic, high-fidelity resource pack for **Minecraft: Bedrock Edition 26.52 (1.26.52.3)**
that runs on the **standard RenderDragon renderer**. It needs no Vibrant Visuals, no ray tracing,
no shader loaders and no experimental toggles, and it is built to run well on phones.

> Commercial-safety requirement: every texture, sprite, sky element, palette and setting in this
> pack is original and generated procedurally by the code in `tools/`. No vanilla texture is traced,
> upscaled, recoloured or otherwise reused; vanilla files are consulted only for file names, paths,
> image dimensions, animation frame counts, functional alpha/tint/UV layouts and mean colour and
> brightness (for calibration). No photographs or third-party asset packs are used, and the look does not
> imitate any existing pack.

## 1. What the standard renderer still lets a pack control

Researched against Mojang's 1.26.50 samples and schemas, Microsoft Learn and the Bedrock Wiki (sources
in the README).

| Lever | File | What Terra Lucida does with it |
|---|---|---|
| Texture resolution | any texture | 32x / 64x / 128x tiers as subpacks (section 4) |
| Texture variations | `terrain_texture.json` `textures.variations[{path, weight}]` | 31 textures get 2-3 weighted variants on 58 single-texture keys (full blocks, slabs, walls, infested blocks) |
| Random face rotation | `blocks.json` `isotropic` | Added to every block whose faces are lit from straight overhead (section 6) |
| Corner shading | `blocks.json` `ambient_occlusion_exponent` (absent = 1.0) | Deeper on rock and masonry, softer on snow (section 6) |
| Atlas mip chain | `terrain_texture.json` `padding`, `num_mip_levels` | Vanilla's 8 / 4 in the root; 16 / 5 in the 64x tier, so distant terrain mips down to 2 px and shimmers less |
| Animation | vanilla `flipbook_textures.json` (kept) | Strips use vanilla's frame counts and loop seamlessly |
| Tint masks | `.tga` alpha (grass side), grey RGB (grass, leaves, water, stems, dust) | Kept exactly: tinted textures are grey and tint regions are binary |
| Sky colour | `biomes/*.client_biome.json` `minecraft:sky_color` | Believable zenith blue per climate |
| Distance fog | `fogs/*.json` `distance.air`, `distance.weather`, `distance.water` | Aerial perspective, rain haze, underwater visibility per climate |
| Water surface | `minecraft:water_appearance` `surface_color`, `surface_opacity` | Colour and clarity per climate |
| Vegetation colour | `textures/colormap/*` | Repainted climate colour maps; vanilla's per-biome overrides (badlands, pale garden) are kept |
| Sky bodies, weather | `textures/environment/*` | Sun and moon (additive, so black is transparent), clouds, rain and snow, End sky |
| Breaking, glint | `destroy_stage_0..9`, `enchanted_*_glint` | Fracture progression; an original glint pattern |
| Particle sheets | `textures/particle/*` with vanilla layouts | Falling leaves, cherry petals, poplar leaves, campfire smoke |

Deliberately unused:
* **PBR texture sets, volumetric fog, atmospherics, lighting and colour-grading JSON, and point lights.**
  These only work with Vibrant Visuals or RTX. Vanilla's volumetric settings are carried over untouched
  in our fog files.
* **Particle JSON overrides and manifest pack settings.** The pack's improvements are textures and
  environment data, which neither of these can switch.
* **Custom shaders.** They need patched game files and unofficial loaders.

## 2. Art direction

* **Naturalism over noise.** Every material is designed in three layers: macro shape that reads at a
  distance (stones, courses, planks, leaf clusters); meso detail at mid range (cracks, grain, pores); and
  micro texture for close-ups. Low-frequency contrast inside a block is kept low, so a wall of identical
  blocks doesn't show a repeating blotch.
* **Light that agrees with the engine.** Faces the engine never rotates get a soft key light from above
  and slightly left. Faces it rotates at random get direction-free light from straight overhead, so
  neighbouring blocks never disagree about where the light comes from.
* **Physically plausible palettes.** Colours come from real minerals, soils and woods, with gentle hue
  drift: warm highlights and cool, sky-filled crevices.
* **Readable gameplay.** Block textures are calibrated to vanilla's mean colour and luminance. Ores,
  redstone states, crop ages, copper stages and the 16 dye colours keep their contrast with their
  surroundings and with each other.

## 3. Techniques

**Master and tiers.** Every texture is painted once at 256 px per block (16 px per vanilla pixel unit).
It is then filtered to each tier with a premultiplied 2x2 box cascade and a light unsharp mask, so all
three tiers show the same design. All noise is periodic, so every texture tiles.

**Materials as height fields.** A recipe returns albedo, height and optional alpha. `finish()` derives
normals and lights them. It adds a multi-scale cavity term (1.5 / 5 / 14 px), tints shadowed areas cool and
lit relief warm, and can add a tight specular glint (`gloss`) for wet or polished surfaces or emissive
accents (lava cracks, glowing ores, lamps).

**Drawing primitives** (`engine/draw.py`):
* tapered capsule strokes with depth, used for straw, roots, twigs, needles, grass blades and bark plates;
* fibre carpets for moss, mycelium and nylium;
* fracture planes with one-sided glow for ice;
* grain fields for sand, gravel and powders;
* masked wrapping for model faces.

**Anti-artefact rules.**
* Strokes are at least a quarter of a vanilla pixel wide, so they don't break into dots at 64x.
* Wood rings are at least one vanilla pixel apart, to avoid moiré.
* No Voronoi "crazy paving". It reads as tiles, so clay, netherrack, coral, wart blocks and glowstone use
  warped noise instead, and ice uses fracture planes.

**Variants.**
* Faces the engine never rotates use edge-band variants: each variant keeps variant 0's border band and
  differs only inside.
* Rotated faces use fully independent variants.
* Weights favour the first variant (for example 6:3:3), so the variants stay rare enough not to be
  noticed.

**Tint-safe export.**
* Grass sides carry two full layers: the grey, tinted overhang and the untinted soil. Each tier picks
  between them with its own downsampled mask, so no grey fringe appears at any resolution.
* Cut-outs are thresholded at 50% and their colour is dilated under transparent pixels, so mipmaps never
  show dark halos.

**Model-mapped textures.** Parts drawn on a 3D model are painted inside the silhouettes of vanilla's UV
islands: lanterns, torches, candles, chains, levers, End rods, flower pots, lightning rods, pointed
dripstone, cocoa pods, sea pickles, dripleaves, the rain and snow sheet and similar. Those silhouettes are stored as 0/1 masks in `tools/data/vanilla_masks.json`. Every new pixel
lands where the model samples, and nothing appears where vanilla is transparent.

**Seamless loops.** Waves use integer wave vectors and integer temporal frequencies. Drifting textures
sample noise along closed paths or move by whole periods. Kelp's sway also tiles vertically, so stacked
kelp stays continuous. Water, lava, fire, soul fire, portals, kelp, seagrass, sea lanterns, sculk,
furnaces, campfires and lanterns therefore loop without a jump (51 animated strips).

## 4. Resolution tiers (subpacks)

Manifest format 3 subpacks carry `folder_name`, `name` and `memory_performance_tier` (0-5). A device
can't select a subpack above its tier, and the highest allowed one is the default.

| Subpack | Resolution | memory_performance_tier | Terrain atlas (padding / mips) | Target |
|---|---|---|---|---|
| Lite 32x - older phones | 32x | 0 | about 3.0 Mpx of 2048x2048 (8 / 4) | Any device |
| **Balanced 64x - most phones** | 64x | 2 | about 11.9 Mpx of 4096x4096 (16 / 5) | Mid-range phones and tablets |
| Ultra 128x - high-end devices | 128x | 4 | about 26.7 Mpx of 8192x4096 (8 / 4) | Flagship phones, consoles, PC |

The root pack holds the 64x textures and vanilla's atlas settings. Lite and Ultra override the
textures. Balanced overrides only `terrain_texture.json`, to get the deeper mip chain its atlas can
afford. If a device ignored that file, it would still get the root's safe settings.

The atlas figures are the first frame of every terrain texture plus padding, as measured by
`validate.py`. When the atlas overflows, the game shrinks every texture to fit, so each tier stays well
inside its target. Animations stay within the vanilla set, so there are no extra per-frame uploads.

## 5. Coverage

1,277 textures, 188 `blocks.json` entries, 80 fog files and 89 client biomes. The textures are:
* 1,255 written at all three resolutions: 1,206 vanilla block textures, 39 extra variants and the 10
  destroy stages;
* 22 fixed-size images: sky, weather, glint, colour maps and particle sheets.

* **Natural world:**
  * stone family (stone, granite, diorite, andesite, deepslate, tuff, calcite, dripstone, basalt,
    blackstone, bedrock, cinnabar, sulfur);
  * soils (dirt, coarse and rooted dirt, grass, podzol, mycelium, path, farmland, mud, clay, gravel, sand,
    red sand, moss);
  * snow and ice, sandstone families, liquids;
  * logs and stems of all 13 species, planks, leaves (fancy, fast and inventory versions);
  * grasses, flowers, crops, cave and Nether flora, corals, ores, obsidian, amethyst.
* **Building and colour families:**
  * bricks and every masonry family, smooth stone, quartz, purpur, prismarine, metal and gem blocks;
  * wool, concrete, concrete powder, terracotta, 16 original glazed-terracotta motifs;
  * glass and stained glass, all copper oxidation stages, Nether and End materials.
* **Utility:**
  * workstations and furnaces with animated lit states, dispensers, observers, pistons;
  * doors and trapdoors, rails, redstone components, lamps, lanterns, torches, chains, bars;
  * scaffolding, shelves, pots with 23 original pottery motifs, vaults, trial spawners, crafters;
  * the sculk family and the rest of the newer blocks.
* **Environment:** sun, eight moon phases, clouds, rain and snow, destroy stages, End sky, item and
  armour glint, eight colour maps, particle sheets, all fog files and client biomes.

Left to vanilla on purpose: creative-only and technical blocks (command, structure and jigsaw blocks,
barrier, border, allow/deny, camera, reactor core, missing-texture tiles), `*_mipmap` and `*_normal`
helpers, bubble columns, beds and the straw bed, conduit, End portal and gateway (non-square specials),
the shared `particles.png` sheet and screen overlays (pumpkin blur, nausea).

## 6. Environment and block tuning

**Fog** (`fogs/*.json`). The fog is set per climate group: temperate, forest, dark forest, arid, humid,
swamp, snowy, boreal, sea, tropical sea, alpine, blossom and mushroom.
* Air fog starts at 45-62% of render distance and ends at 100%. That gives aerial perspective and hides
  chunk edges without shortening the view on small mobile render distances.
* Rain haze runs from 18% to 62% in a cool grey, so storms have weight.
* Underwater visibility ranges from 18 blocks in swamps to 72 in tropical seas.
* The Nether, the End, powder snow and sulfur caves keep vanilla fog. The Pale Garden keeps its own and
  only starts its fog earlier.

**Biomes** (`biomes/*.client_biome.json`). Sky colour and water surface colour and opacity follow the same
climate groups, from murky olive swamps (opacity 0.85) to clear turquoise tropical seas (0.5). Every
other vanilla component is carried over unchanged: music, sounds, vegetation overrides, and the Vibrant
Visuals identifiers.

**Colour maps.** Grass and foliage are barycentric blends of hot-wet, hot-dry and cold corners over
vanilla's climate triangle. Birch, evergreen, swamp and mangrove maps are flat natural blends.

**`blocks.json`** (`tools/recipes/tuning.py`).

| Group | AO exponent | Blocks |
|---|---|---|
| Masonry | 1.3 | stone bricks, deepslate bricks and tiles, tuff bricks, blackstone bricks, bricks, mud bricks, End bricks, Nether bricks, resin, cinnabar and sulfur bricks, including slabs, stairs and walls |
| Rock | 1.2 | stone, cobblestone, granite, diorite, andesite, tuff, calcite, dripstone, blackstone, basalt, End stone, bedrock, deepslate and cobbled deepslate, all stone and deepslate ores, infested variants |
| Soil | 1.15 | dirt, coarse and rooted dirt, gravel, podzol |
| Snow | 0.75 | snow, snow layer, powder snow |

Every block whose faces show only textures from a group gets the group's value. Slabs, stairs and walls
therefore match their full block, ores match the rock around them, and infested blocks stay identical to
the real ones. Vanilla's own values (sand 0.55, leaves 0.8, obsidian 2.0) are kept.

`isotropic` is added to every block whose faces are all overhead-lit with no upright motif: mud, packed mud,
moss and pale moss (and their carpets), soul soil, powder snow and the 16 concrete powders. This joins
vanilla's dirt, sand, clay and snow. Soul sand stays upright because of its faces. Entries are copied
whole from vanilla before editing, because a pack's `blocks.json` entry replaces vanilla's instead of
merging with it.

## 7. Verification

* `tools/validate.py` checks the built pack without the game: manifest, textures, definitions and atlas
  budget (see the README). With Mojang's bedrock-samples it also checks the manifest against Mojang's
  packaging 3.0.0 schema and each client biome against its versioned schema.
* `tools/preview.py` renders isometric dioramas with the engine's face shading and smooth-lighting
  corners. Development used it, with per-family contact sheets at every tier, to judge tiling, colour
  harmony and readability without the game.
* `tools/icon.py` draws the pack icon from the built textures.
