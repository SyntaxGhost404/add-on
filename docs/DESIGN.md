# Ruins of the Unnamed — Design Document

Target: **Minecraft Bedrock Edition 26.52** (server/build version **1.26.52.3**).
Namespace: `rotu`. Behavior pack + resource pack, packaged as one `.mcaddon`.

> Commercial-safety requirement: every name, story element, texture, model,
> structure and line of code in this pack is original. Nothing is copied from
> or designed to imitate any existing IP, commercial title, brand, character,
> logo, artwork, music, UI/trade dress or third-party asset pack. The two
> reference add-ons were studied only for technical architecture. Vanilla
> Minecraft sounds are referenced through the official sound-definition
> system (they are never copied or redistributed).

## 1. Premise

Explorers call them **the Unnamed**: on every inscription they left behind,
the name of a king, a city or a god has been patiently chiselled away by the
same hands that carved it. They were once **the Choir**, a civilisation that
followed a cold light down into the earth and found **the Low Star** — a star
that fell the wrong way and came to rest far below the world, singing.

The star's song taught them everything, and in exchange it took their words —
first small ones, then names. To hide from it, the Choir performed **the
Unsaying**: every citizen unspoke their own name into **gloamstone**, a dark
stone that swallows sound. It worked too well. What is left are nameless
**Hushwalkers** shuffling through silent halls, **Murmurs** (loose, hungry
voices), the never-sleeping **Graven Sentinels**, and the **Last Cantor**, who
has held one note against the star for a thousand years in the Sunken Sanctum.

## 2. Player progression loop

| Stage | Player goal | Where | Key rewards |
|-------|-------------|-------|-------------|
| 1. Discovery | Notice strange dark obelisks and statues | Waystones, Mourning Statues (common, surface) | Glyph Shards, Inscribed Tablets (brushing), buried caches |
| 2. Study | Learn the archaeology loop | Dig Sites (expedition camp + excavation) | Field Journal (tutorial book), Codex, brushing loot |
| 3. Decipher | Read tablets → lore chapters + hints | Scriptorium Desk (craftable) | Codex chapters 1–11, glyph shards |
| 4. Explore | Solve the dial gate, find secrets | Hushed Shrines | **Lantern Sigil Shard**, Lesser Reliquaries |
| 5. Descend | Clear a catacomb, defeat a sentinel | Ossuaries | **Bone Sigil Shard**, **Hush Sigil Shard** (Graven Sentinel) |
| 6. Forge | Combine the three shards | Crafting table | **Sigil Key** |
| 7. Confront | Unlock the Sanctum, defeat the boss | Sunken Sanctum (rare, landmark spire) | The Last Cantor → Cantor's Seal, Low Star Fragment, chapter 12 |
| 8. Claim | Open Grand Reliquaries | Sanctum vault | Relic gear (Dirge Blade, Hushweave Mantle, Delver's Pick, Chorister's Mask) |

Anti-tedium rules:
* Each tablet always reveals the **next unread chapter** (no duplicates). Extra tablets become glyph shards + XP.
* The Codex always shows a **context-aware hint** for the next step.
* Key items are **guaranteed** in specific rooms (no pure RNG gates); RNG only adds bonus loot.
* The Dowsing Rod points to buried caches and reliquaries so digging is guided, not blind.
* Reliquaries are **per player** (multiplayer friendly), like vanilla vaults.

## 3. Mechanisms

* **Glyph Dials + Sealed Gate** — three dials in front of a gate; three Cipher Stones above it show the answer (left → right). Turning a dial cycles its glyph; when every dial near a gate matches its hidden target, all Sealed Gate blocks nearby dissolve.
* **Veilstone** — indistinguishable from gloamstone bricks until the **Diviner's Lens** reveals it; revealed veilstone is a walk-through shimmer hiding secret alcoves.
* **Hushing Plate** — floor trap. Walking onto it smothers you in Darkness and may summon a Murmur. **Sneaking across is safe.** Recharges after a while.
* **Singing Stone** — hums at night, sheds faint light and glyph motes; the Dowsing Rod resonates with it. Drops Glyph Shards.
* **Funerary Urn** — breakable loot vessel; sealed urns sometimes release a Murmur.
* **Reliquary** — per-player locked casket. Lesser tier opens with a Reliquary Key, Grand tier with a Cantor's Seal. Ejects loot with an animation.
* **Sigil Lock** — present the Sigil Key to open the Sanctum's inner gate.
* **Scriptorium Desk** — decipher Inscribed Tablets into Codex chapters.
* **Spawn markers** — invisible blocks inside structures that wake mobs when a player comes near (no command blocks needed).

## 4. Content list

### Blocks
`gloamstone_bricks`, `cracked_gloamstone_bricks`, `mossy_gloamstone_bricks`, `chiseled_gloamstone`,
`gloamstone_tiles`, `gloamstone_pillar`, `gilded_gloamstone`, `glyph_mural` (4 panels),
`cipher_stone` (4 glyphs), `singing_stone`, `choir_lantern`, `funerary_urn`, `glyph_dial`,
`sealed_gate`, `sigil_lock`, `veilstone`, `hushing_plate`, `scriptorium_desk`, `reliquary`
(lesser/grand), `spawn_marker` (hidden).

### Items
`codex`, `glyph_shard`, `inscribed_tablet`, `reliquary_key`, `lantern_shard`, `bone_shard`,
`hush_shard`, `sigil_key`, `cantors_seal`, `diviners_lens`, `dowsing_rod`, `murmur_essence`,
`delvers_pick`, `dirge_blade`, `sentinels_maul`, `choristers_mask`, `hushweave_mantle`,
`low_star_fragment`.

### Entities
`hushwalker` (common undead, slows on hit), `murmur` (flying spirit, darkness on hit, drifts
through walls), `graven_sentinel` (dormant statue mini-boss, drops Hush Shard),
`last_cantor` (boss with boss bar, summons Murmurs, hush bolts, blink, second phase),
`hush_bolt` (boss projectile).

### Structures (data-driven jigsaw, stable since 1.21.120)
| Structure | Pieces | Placement | Terrain |
|-----------|--------|-----------|---------|
| `mourning_statue` | 3 variants | very common, most overworld land biomes | beard_thin |
| `waystone` | 4 variants, buried cache | common, temperate land | none (structure-void) |
| `waystone_arid` | 2 variants | common, desert/badlands | none |
| `dig_site` | excavation + expedition camp | uncommon | beard_thin |
| `hushed_shrine` | 2 variants | uncommon | beard_thin |
| `ossuary` | mausoleum → hub → corridors/crypts → Bone Choir | rare | none |
| `sunken_sanctum` | spire → antechamber → hall → choir arena → vault | very rare landmark | none |

## 5. Technical notes (verified against 26.50/26.52 sources)

* Manifests: format 2, `min_engine_version [1, 26, 50]`.
* Script API: `@minecraft/server` **2.10.0** and `@minecraft/server-ui` **2.2.0** (both stable in 26.50+, unchanged in 26.52).
* Custom components V2 registered in `system.beforeEvents.startup`.
* Block/item/entity format versions 1.26.50 (entity files validated against Mojang's 1.26.50 JSON schemas, which are stricter).
* `.mcstructure` files written with block version 1.21.60.33 (the engine's current serialization version) and complete 26.50 block-state sets (including the new `minecraft:corner` stair state and bar/pane connection states).
* Jigsaw worldgen files under `worldgen/structures|structure_sets|template_pools|processors`.
* All textures, models, structures and synthesized sounds are generated by `tools/build.py` (deterministic, seeded).
