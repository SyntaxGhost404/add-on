# Ruins of the Unnamed

An exploration add-on for **Minecraft: Bedrock Edition 26.52** (build **1.26.52.3**).

Long before you arrived, a civilisation called **the Choir** followed a cold light down into the
earth and found **the Low Star**, a star that fell the wrong way and came to rest beneath the world,
singing. Its song taught them everything. In return it took their words, then their names. To hide
from it they performed **the Unsaying** and erased their own names from the world. Explorers now call
them **the Unnamed**.

Their ruins are scattered across the Overworld: dark waystones, abandoned dig sites, shrines sealed by
glyph puzzles, catacombs full of restless dead and, beneath a black weeping spire, the **Sunken
Sanctum** where the **Last Cantor** still holds one note against the star.

Everything in this pack is original: names, story, structures, textures, models, mobs, scripts and
synthesized sounds.

---

## Install

1. Download **`dist/Ruins_of_the_Unnamed_v1.0.0.mcaddon`** and open it. Minecraft imports both packs.
   (The two `.mcpack` files in `dist/` contain the same packs separately.)
2. Create a new world (or edit an existing one) → **Behavior Packs** → activate **Ruins of the
   Unnamed**. The resource pack is linked as a dependency and is activated with it.
3. **No experimental toggles are needed.** The pack uses only stable features: custom blocks, items
   and entities in format 1.26.50, data-driven jigsaw structures (stable since 1.21.120) and the
   stable Script API modules `@minecraft/server` 2.10.0 and `@minecraft/server-ui` 2.2.0.

Structures only generate in **newly generated chunks**. In an existing world, travel to unexplored
land.

| Requirement | Value |
|---|---|
| Minimum game version | 1.26.50 (manifest `min_engine_version`) |
| Built and checked for | 26.52 / 1.26.52.3 |
| Script modules | `@minecraft/server` 2.10.0, `@minecraft/server-ui` 2.2.0 (stable) |
| Multiplayer | Yes. Progress, codex and reliquary rewards are tracked per player |

---

## How to play

You don't need to grind. Every key item has a guaranteed source, and the **Codex** always tells you
what to do next.

| Stage | Goal | Where |
|---|---|---|
| 1. Discovery | Notice dark obelisks and kneeling statues | **Waystones** and **Mourning Statues** (common) |
| 2. Study | Brush suspicious sand/gravel for **Inscribed Tablets** and **Glyph Shards** | Waystones, **Dig Sites** |
| 3. Decipher | Read tablets at a **Scriptorium Desk** to unlock Codex chapters I–XI | Anywhere (craftable) |
| 4. Solve | Open a **Hushed Shrine** gate with its glyph dials and take the **Lantern Sigil Shard** | Hushed Shrines |
| 5. Descend | Reach the Bone Choir for the **Bone Sigil Shard**, defeat a **Graven Sentinel** for the **Hush Sigil Shard** | **Ossuaries**, shrines |
| 6. Forge | Craft the **Sigil Key** (3 shards + gold ingot) | Crafting table |
| 7. Confront | Unlock the Sanctum and silence **the Last Cantor** | **Sunken Sanctum** |
| 8. Claim | Open the **Grand Reliquaries** with Cantor's Seals | The Sanctum's vault |

**Start here:** find a Dig Site. Its supply chest always contains a brush and the expedition's
*Field Journal*, a short in-world tutorial, and usually a Codex. You can also craft a Codex from a
book and a glyph shard.

### The Codex of the Unnamed
Use it to open the book interface:
- **Chapters**: the twelve chapters of the story. Each tablet you decipher reveals the next unread
  chapter, so you never get duplicates. Chapter XII is earned by defeating the Last Cantor.
- **Field Guide**: how each mechanism and tool works.
- **Bestiary**: entries unlock when you read the right chapter or defeat the creature.
- **Discoveries**: your personal statistics.
- The front page shows a **context-aware hint** for your next step.

---

## Structures

| Structure | What you'll find | Rarity |
|---|---|---|
| **Mourning Statue** | Weathered statues kneeling in grief (3 variants) | Very common, most land biomes |
| **Waystone** | Dark tuning-stone obelisks (4 variants + 2 desert/badlands variants). Suspicious blocks ring the base, and a **sealed cache** with a chest, urns and a singing stone is buried a few blocks below | Common |
| **Dig Site** | An excavation pit with suspicious blocks and finds, plus the expedition camp (supply chest, desk, field journal) | Uncommon |
| **Hushed Shrine** | A ruined temple sealed by a **glyph-dial gate**. Inside: the Lantern Sigil Shard, a lesser reliquary and a hidden alcove. One variant has a dormant **Graven Sentinel** | Uncommon, temperate biomes |
| **Ossuary** | A black mausoleum over a **spiral stair** into a catacomb of corridors and crypts (some with reliquaries or spawners), ending in the **Bone Choir** with its guardian | Rare |
| **Sunken Sanctum** | A tall black spire that weeps crying obsidian. Below it: the antechamber with the **Sigil Lock**, a hall with hidden niches, the domed **choir arena** of the Last Cantor and the **vault** around the Low Star Well | Very rare landmark |

Testing tip (cheats on): `/place structure rotu:hushed_shrine` places any of these at your
position. The IDs are `rotu:mourning_statue`, `rotu:waystone`, `rotu:waystone_arid`, `rotu:dig_site`,
`rotu:dig_site_arid`, `rotu:hushed_shrine`, `rotu:ossuary` and `rotu:sunken_sanctum`.

---

## Mechanisms

- **Glyph Dials & Sealed Gates**: three Cipher Stones above a shrine gate show the answer, left to
  right as you face the gate. Use each dial to turn it to the matching glyph (Star, Eye, Mouth,
  Lantern). When all dials agree, the gate dissolves.
- **Veilstone**: looks exactly like gloamstone bricks. The **Diviner's Lens** reveals it, and
  revealed veilstone can be walked through. Knocking on walls (using them with an empty hand) also
  gives a hint.
- **Hushing Plates**: walk onto one and darkness smothers you, and it may release a Murmur.
  **Sneak across and nothing happens.** Plates recharge after a while.
- **Singing Stones**: hum at night and shed glyph motes. Use one to hear a whisper. The Dowsing Rod
  resonates with them, and they mark buried caches.
- **Funerary Urns**: break sealed urns for loot. Sometimes something escapes.
- **Reliquaries**: locked caskets that reward **each player once**. A lesser reliquary takes a
  **Reliquary Key**. A grand reliquary takes a **Cantor's Seal**. Loot pops out one item at a time.
- **Sigil Lock**: present the Sigil Key to open the Sanctum's inner gate. The key is not used up.
- **Scriptorium Desk**: hold an Inscribed Tablet and use the desk. Once every chapter is read,
  extra tablets become glyph shards and XP.

---

## Items

| Item | How to get it | What it does |
|---|---|---|
| Glyph Shard | Brushing, urns, chests, singing stones, mobs | Crafting material for most recipes |
| Inscribed Tablet | Brushing, caches, chests, urns, Hushwalkers | Decipher at a Scriptorium Desk |
| Codex of the Unnamed | Dig Site supplies, or **book + glyph shard** | The book interface (story, guide, hints) |
| Scriptorium Desk | **Book, glyph shard, 5 planks** | Deciphers tablets |
| Reliquary Key | **4 glyph shards around a gold ingot**, or loot | Opens a lesser reliquary |
| Diviner's Lens | **4 copper ingots, glyph shard, amethyst shard, stick** | Reveals veilstone, highlights relics and correct dials |
| Resonant Dowsing Rod | **2 sticks, glyph shard, copper ingot** | Points to the nearest singing stone or unclaimed reliquary (direction, distance, depth) within about 28 blocks |
| Lantern / Bone / Hush Sigil Shard | Shrine sanctum chest / Bone Choir chest / Graven Sentinel | Sigil Key ingredients |
| Sigil Key | **Lantern + Bone + Hush shard over a gold ingot** | Opens the Sunken Sanctum |
| Cantor's Seal | The Last Cantor (2) | Opens a grand reliquary |
| Murmur Essence | Murmurs | Crafting (choir lanterns, veilstone, hushing plates) and relic repair |

### Relics

| Relic | Source | Ability |
|---|---|---|
| Delver's Pick | Reliquaries | Mining speed 9, 1900 durability. Mining gloamstone sometimes frees a glyph shard |
| Dirge Blade | Grand reliquary | 7 damage. Against the Unnamed, every hit **echoes** a moment later for 5 bonus damage (20% chance against others) |
| Sentinel's Maul | Graven Sentinel (35%), grand reliquary | 9 damage, slow swing. Heavy knockback, and a shockwave hits nearby monsters |
| Chorister's Mask | Reliquaries | Helmet. Immunity to Darkness and Blindness, including the Cantor's pulse |
| Hushweave Mantle | Grand reliquary | Chestplate (7 armor). Sneaking makes you invisible, and hushing plates never trigger |
| Low Star Fragment | The Last Cantor | Hold to use (2.5 s): return to your bed or respawn point. 2-minute cooldown |

### Building blocks
Gloamstone bricks (8 cobbled deepslate around a glyph shard), cracked (smelt), mossy (+ moss or
vine), gilded (+ 2 gold nuggets), tiles, pillars, chiseled gloamstone, glyph murals and cipher stones
(stonecutter). There are also choir lanterns (light 15), funerary urns (6 bricks), veilstone and
hushing plates. Holding a glyph shard, use a mural or cipher stone to recarve it.

---

## Creatures

| Creature | Notes |
|---|---|
| **Hushwalker** | 24 HP. Mouth-sewn citizens of the Unnamed in 3 variants. Their hits slow you, and they burn in daylight. They spawn in the dark on gloamstone floors |
| **Murmur** | 10 HP. A floating lost voice that drifts through walls. Its touch brings Darkness. Drops Murmur Essence |
| **Graven Sentinel** | 90 HP mini-boss. It stays dormant until you come within reach or strike it, then wakes with a shudder. Hits for 8–13, is immune to knockback and takes half damage from projectiles. Always drops the **Hush Sigil Shard** |
| **The Last Cantor** | 280 HP boss with a boss bar. It summons Murmurs, throws homing **hush bolts**, and pulses Darkness at everyone nearby. It **blinks away** if you stay in melee range. At half health its note breaks: it attacks faster, summons more and **snuffs nearby torches**. Defeat it to open the vault and write Chapter XII |

---

## Building from source

The packs are generated from the sources in `tools/` and `scripts/`. The build is deterministic.

```sh
python3 tools/build.py            # writes packs/ and dist/*.mcaddon (needs Python 3.10+, numpy, Pillow, ffmpeg)
python3 tools/validate.py --samples /path/to/bedrock-samples   # schema + cross-reference checks
npm install && npx tsc -p tsconfig.json                          # strict type-check of the scripts
python3 tools/tests/test_nbt.py [dirs with .mcstructure files]   # NBT writer tests
```

`validate.py` always runs its self-contained checks: textures, models, loot tables, sounds,
particles, jigsaw connections, structure block states, lang keys, custom components and script
references. With a checkout of [Mojang/bedrock-samples](https://github.com/Mojang/bedrock-samples)
it also validates against Mojang's JSON schemas (1.26.50) and checks every vanilla identifier. Mojang's
generated schemas contain a few known defects that vanilla's own files also fail, such as overlapping
`oneOf` branches. The validator identifies and reports those separately.

| Path | Contents |
|---|---|
| `scripts/` | Gameplay scripts (Script API, JavaScript with JSDoc types) |
| `tools/content/` | Block, item, entity, loot, recipe, worldgen, client and sound definitions |
| `tools/structures/` | Procedural builders for every structure piece |
| `tools/art/` | Pixel-art texture painters, block/entity models, sound synthesis |
| `tools/lib/` | `.mcstructure` NBT writer, image helpers |
| `packs/` | Generated behavior pack and resource pack |
| `dist/` | Packaged `.mcaddon` / `.mcpack` files |
| `docs/DESIGN.md` | Design document |

---

## Originality

All names, lore, structures, textures, models, scripts and the five synthesized sound effects
(`sounds/rotu/*.ogg`) were created for this project. The two third-party add-ons provided as
references were studied only for technical structure (file layout, worldgen conventions) and none
of their content was copied. Vanilla Minecraft sounds are referenced by path through the standard
sound-definition system and are not redistributed. "Minecraft" is a trademark of Mojang/Microsoft.
This add-on is unofficial and not affiliated with or endorsed by them.
