// @ts-check
// The story of the Unnamed, revealed one tablet at a time. Original text.

/** @type {{ title: string, text: string }[]} index 0 = chapter 1 */
export const CHAPTERS = [
  {
    title: "I. The Effaced Names",
    text:
      "Every inscription carries the same wound. Where a name should be - of a king, a city, a god - the stone has been gouged away with careful, patient strokes.\n\n" +
      "This was not vandalism. It was devotion. Whoever carved these words wanted them read, and whoever erased the names wanted them forgotten. The marks of the chisel match. They were the same hands.\n\n" +
      "Explorers call the builders the Unnamed. It seems they would have approved.",
  },
  {
    title: "II. The Lantern-Keepers",
    text:
      "Before the cities there were lanterns. Shepherds of the high plains saw a cold, pale light breathing up through cracks in the earth, like breath on a winter morning.\n\n" +
      "They followed it down. Over the deepest crack they raised a single shrine and kept a lantern burning there day and night, so the light below would know it was not alone.\n\n" +
      "The lantern-keepers were the first of them. The lantern became their oldest sigil.",
  },
  {
    title: "III. The Low Star",
    text:
      "The tablets speak of a star that fell the wrong way - not out of the sky, but down, through the floor of the world, until it came to rest somewhere far below.\n\n" +
      "They named it the Low Star. It did not burn. It sang.\n\n" +
      "Those who slept near the shrine woke knowing things they had never been taught: the names of herbs, the paths of rivers, the depth of every well. Each gift was one verse of its song.",
  },
  {
    title: "IV. The Choir",
    text:
      "A people taught by a song becomes a choir. They ordered their cities by voice: Tenors who quarried, Altos who built, Basses who buried the dead.\n\n" +
      "Above them stood the Cantors, who could hold a single note through an entire night and hear the Low Star answer.\n\n" +
      "The Waystones you have passed were tuning-stones. They hummed in the star's own key to guide travellers home.",
  },
  {
    title: "V. Gloamstone",
    text:
      "The deeper they dug toward the singer, the darker the stone became. They called it gloamstone: rock that had soaked in the star's song for ages and learned to swallow sound.\n\n" +
      "Halls of gloamstone are unbearably quiet. A whisper dies a hand's width from the lips. The Choir prized it above gold - it was the only place they could think without the song in their ears.\n\n" +
      "They locked their sanctums with dials of glyphs: Star, Eye, Mouth and Lantern. The answer was always carved above the door, for those patient enough to read it.",
  },
  {
    title: "VI. The Price of Verses",
    text:
      "The Low Star's gifts were never free. A ledger from the Basses' archive records the trade plainly: for every verse it sang to them, it took a word from them.\n\n" +
      "First small words - the names of colours, of birds. Then the names of streets. Then the names of mothers.\n\n" +
      "People forgot what they had known and did not notice it was gone. The Choir kept singing. The knowledge was too sweet to refuse.",
  },
  {
    title: "VII. The First Silence",
    text:
      "In a single winter, a whole district of the capital forgot its own name. Doors stood open. Tables were laid. No one could say whose house they stood in.\n\n" +
      "The survivors wandered the streets humming the star's song, because it was the only thing left inside them.\n\n" +
      "The Choir carved the names of the lost onto the district walls, so that the star could not have them. By spring the carvings were blank.",
  },
  {
    title: "VIII. The Graven",
    text:
      "If the star devoured names, then the guardians of the Choir must have none. The Altos carved sentinels from gloamstone and gave them no name, no voice - only a purpose: stand watch, and strike whatever moves within the sanctum.\n\n" +
      "The Graven Sentinels still stand. They sleep until you are close enough to touch them. Then they remember their purpose, and nothing else.\n\n" +
      "Each was given a fragment of the Hush sigil to keep. It is sealed inside them.",
  },
  {
    title: "IX. The Unsaying",
    text:
      "The Cantors devised a desperate rite. If the star feeds on names, give it none. Each citizen would unsay their own name - speak it backwards into gloamstone until it was gone from the world entirely.\n\n" +
      "A people without names could not be called. A people without names could not be eaten.\n\n" +
      "The tablets do not say whether the rite worked. They only say that afterwards, no one signed the tablets any more.",
  },
  {
    title: "X. The Three Sigils",
    text:
      "The last Cantor sealed the Sunken Sanctum - the hall raised directly above the Low Star - and broke its key into three sigils.\n\n" +
      "The Lantern sigil went to the shrines of the surface. The Bone sigil went to the deepest ossuary, the Bone Choir. The Hush sigil went into the heart of a Graven Sentinel.\n\n" +
      "Bring the three together with gold and the Sigil Key will be whole. The Sanctum stands beneath a black spire that weeps.",
  },
  {
    title: "XI. What Remains",
    text:
      "The Unnamed did not die. A people without names cannot be mourned, and so they cannot rest.\n\n" +
      "The Hushwalkers shuffle through their old halls with their mouths sewn shut by the Unsaying. The Murmurs are what is left of their voices - loose, cold and hungry for any word to wear.\n\n" +
      "Walk softly on the hushing plates. Do not speak loudly in their halls. Do not let them learn your name.",
  },
  {
    title: "XII. The Last Verse",
    text:
      "The Last Cantor kept singing after everyone else fell silent - one voice, holding one note against the star for a thousand years, so that its hunger would have something to chew on other than the world above.\n\n" +
      "You have ended that note.\n\n" +
      "Somewhere far beneath the Sanctum, in a silence older than stone, something has noticed that the singing stopped. It is listening for a new voice.",
  },
];

/** @type {{ title: string, icon: string, text: string }[]} */
export const FIELD_GUIDE = [
  {
    title: "Archaeology",
    icon: "textures/items/brush",
    text:
      "Suspicious sand and gravel lie around Waystones and inside Dig Sites. Brush them to recover Inscribed Tablets, Glyph Shards and old treasures.\n\n" +
      "Waystones also hide a sealed cache a few blocks beneath them. A Resonant Dowsing Rod will point the way.",
  },
  {
    title: "Deciphering",
    icon: "textures/rotu/items/inscribed_tablet",
    text:
      "Craft a Scriptorium Desk (a book, a glyph shard and planks) and use it while holding an Inscribed Tablet. Each tablet reveals the next chapter of this Codex.\n\n" +
      "Once every tablet has been read, extra tablets are broken back into Glyph Shards.\n\n" +
      "Use a Glyph Mural or Cipher Stone with an empty hand to study its carving. Holding a Glyph Shard, you can recarve it for your own buildings.",
  },
  {
    title: "Glyph Dials",
    icon: "textures/rotu/items/glyph_shard",
    text:
      "Hushed Shrines are sealed by gates of solid gloamstone. Three Cipher Stones above the gate show the answer, left to right as you face the gate.\n\n" +
      "Turn each Glyph Dial (use it) until it shows the matching glyph. When every dial agrees, the gate dissolves.",
  },
  {
    title: "Diviner's Lens",
    icon: "textures/rotu/items/diviners_lens",
    text:
      "Some walls are not walls. Use the Diviner's Lens to reveal veilstone - revealed veilstone can be walked through.\n\n" +
      "The lens also makes urns, reliquaries and singing stones shimmer, and shows which glyph dials are already correct.",
  },
  {
    title: "Resonant Dowsing Rod",
    icon: "textures/rotu/items/dowsing_rod",
    text:
      "Use the rod to feel for singing stones and unclaimed reliquaries within about thirty blocks, even through rock. It tells you the direction, the distance and whether to dig up or down.",
  },
  {
    title: "Reliquaries",
    icon: "textures/rotu/items/reliquary_key",
    text:
      "Reliquaries are sealed caskets that reward each explorer once. A lesser reliquary opens with a Reliquary Key (four glyph shards around a gold ingot). A grand reliquary needs a Cantor's Seal.",
  },
  {
    title: "Hushing Plates",
    icon: "textures/rotu/items/murmur_essence",
    text:
      "Carved plates that punish noise. Walking onto one smothers you in darkness and may wake a Murmur. Sneak across them and they stay asleep.",
  },
  {
    title: "The Sigil Key",
    icon: "textures/rotu/items/sigil_key",
    text:
      "Lantern Shard: the inner sanctum of a Hushed Shrine.\nBone Shard: the Bone Choir at the bottom of an Ossuary.\nHush Shard: inside a Graven Sentinel.\n\n" +
      "Craft them with a gold ingot into the Sigil Key, then present it to the Sigil Lock in the Sunken Sanctum.",
  },
];

/**
 * Bestiary entries unlock when the matching chapter is read or the creature is defeated.
 * @type {{ name: string, icon: string, text: string, chapter: number, stat: string }[]}
 */
export const BESTIARY = [
  {
    name: "Hushwalker",
    icon: "textures/rotu/items/inscribed_tablet",
    text: "Citizens who performed the Unsaying. They gather in the dark on gloamstone floors, burn in sunlight and slow whatever they strike. Sometimes they still carry tablets.",
    chapter: 11,
    stat: "hushwalkers",
  },
  {
    name: "Murmur",
    icon: "textures/rotu/items/murmur_essence",
    text: "A lost voice that drifts through walls. Its touch brings darkness. Murmurs released from urns, traps or the Cantor fade after a while; slain ones leave Murmur Essence.",
    chapter: 11,
    stat: "murmurs",
  },
  {
    name: "Graven Sentinel",
    icon: "textures/rotu/items/hush_shard",
    text: "A nameless guardian carved from gloamstone. It sleeps until you come close or strike it, then hits like a landslide. Arrows do half damage. It always carries a Hush Sigil Shard.",
    chapter: 8,
    stat: "sentinels",
  },
  {
    name: "The Last Cantor",
    icon: "textures/rotu/items/cantors_seal",
    text: "The final singer of the Choir, waiting in the Sunken Sanctum. It summons Murmurs, hurls homing hush bolts, unsays the light around you and blinks away from blades. At half strength its note breaks and it grows faster. It drops the Cantor's Seal.",
    chapter: 10,
    stat: "cantor",
  },
];

/** Names of the four ritual glyphs (block state value = index). */
export const GLYPH_NAMES = ["Star", "Eye", "Mouth", "Lantern"];

/** What each Glyph Mural panel depicts. */
export const MURAL_CAPTIONS = [
  "A pale star falls the wrong way - down through the floor of the world.",
  "Three figures kneel around a light that rises from below.",
  "A sewn mouth above a line of gouged-out symbols. A name, erased.",
  "Hollow outlines of people, dissolving into scattered points of light.",
];

/** Fragments overheard near singing stones. */
export const WHISPERS = [
  "...it is listening...",
  "...do not say it... do not say your name...",
  "...the lantern must not go out...",
  "...one more verse... only one more...",
  "...we gave it the colours first...",
  "...whose house is this?...",
  "...below... it is always below...",
  "...the note is fraying...",
];

/**
 * Context-aware hint for the next step.
 * @param {import("./progress.js").Progress} p
 */
export function nextHint(p) {
  const f = p.flags;
  const read = p.chapters.length;
  if (f.cantor) return "The Last Cantor is silent. Use a Cantor's Seal on a Grand Reliquary in the Sanctum's vault - and listen.";
  if (f.key) return "Find the Sunken Sanctum beneath a black, weeping spire. Descend and present the Sigil Key to the Sigil Lock.";
  if (f.lantern && f.bone && f.hush) return "You hold all three Sigil Shards. Craft them with a gold ingot into the Sigil Key.";
  if (read === 0) return "Seek the dark Waystones and Dig Sites. Brush suspicious sand and gravel for Inscribed Tablets, then read them at a Scriptorium Desk.";
  if (read < 3) return "Keep deciphering tablets at a Scriptorium Desk. A Diviner's Lens and a Dowsing Rod will reveal what the ruins hide.";
  if (!f.lantern) return "A Hushed Shrine keeps the Lantern Sigil Shard behind a gate of Glyph Dials. Match the dials to the glyphs carved above the gate.";
  if (!f.bone) return "Ossuaries lie beneath black mausoleums. The Bone Sigil Shard rests on the altar of the Bone Choir, the deepest crypt.";
  if (!f.hush) return "The Hush Sigil Shard is sealed inside a Graven Sentinel. They stand dormant in shrines and Bone Choirs - until you come close.";
  return "Read every tablet you find; the Codex will show you the way.";
}
