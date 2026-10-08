// @ts-check
// World-level behaviour: the Last Cantor's abilities, Graven Sentinel awakenings, death rewards,
// relic armor perks, ambient whispers in the ruins and the first-join welcome.
import { world, system, ItemStack, EquipmentSlot, GameMode } from "@minecraft/server";
import { CHAPTERS } from "./lore.js";
import { addStat, hasFlag, setFlag, syncInventoryFlags, unlockChapter, FINAL_CHAPTER } from "./progress.js";
import { dissolveGates } from "./gates.js";
import { actionBar, dist, findBlocks, guard, isPlayer, later, particle, playersNear, sound } from "./util.js";

/** @typedef {import("@minecraft/server").Dimension} Dimension */
/** @typedef {import("@minecraft/server").Entity} Entity */
/** @typedef {import("@minecraft/server").Player} Player */
/** @typedef {import("@minecraft/server").Vector3} Vector3 */

const CANTOR = "rotu:last_cantor";
const SENTINEL = "rotu:graven_sentinel";
const MASK = "rotu:choristers_mask";
const MANTLE = "rotu:hushweave_mantle";

/** @param {Player} player @param {EquipmentSlot} slot */
function worn(player, slot) {
  const eq = player.getComponent("minecraft:equippable");
  const item = eq && eq.getEquipment(slot);
  return item ? item.typeId : undefined;
}

// ------------------------------------------------------------------ the Last Cantor
/**
 * @typedef {Object} BossState
 * @property {number} pulse next tick the pulse may fire
 * @property {number} blink next tick the blink may fire
 * @property {number} hug consecutive checks with a player in melee range
 * @property {Vector3 | undefined} home the arena center
 * @property {Vector3} last last known location
 * @property {string} dim dimension id
 */
/** @type {Map<string, BossState>} */
const bosses = new Map();

/** @param {Entity} boss @returns {Vector3 | undefined} */
function homeOf(boss) {
  const h = boss.getDynamicProperty("rotu:home");
  return typeof h === "object" ? h : undefined;
}

/** @param {Entity} boss */
function inPhaseTwo(boss) {
  const v = boss.getComponent("minecraft:variant");
  return !!v && v.value === 1;
}

/**
 * The note that unsays the light: darkness for everyone nearby; in phase two it also snuffs torches.
 * @param {Entity} boss @param {Dimension} dim @param {Player[]} players
 */
function pulse(boss, dim, players) {
  const at = boss.location;
  sound(dim, "rotu.cantor.pulse", at, 1.4);
  particle(dim, "rotu:hush_dust", { x: at.x, y: at.y + 2, z: at.z });
  for (const p of players) {
    if (dist(p.location, at) > 16) continue;
    if (worn(p, EquipmentSlot.Head) === MASK) {
      actionBar(p, "§7Your mask drowns out the Cantor's note.");
      continue;
    }
    p.addEffect("darkness", 120, { showParticles: false });
    actionBar(p, "§5The Cantor unsays the light.");
  }
  if (!inPhaseTwo(boss)) return;
  for (const loc of findBlocks(dim, at, 9, 5, 9, ["minecraft:torch", "minecraft:soul_torch"])) {
    const block = dim.getBlock(loc);
    if (!block) continue;
    const type = block.typeId;
    block.setType("minecraft:air");
    dim.spawnItem(new ItemStack(type, 1), { x: loc.x + 0.5, y: loc.y + 0.5, z: loc.z + 0.5 });
    particle(dim, "rotu:hush_dust", { x: loc.x + 0.5, y: loc.y + 0.5, z: loc.z + 0.5 });
  }
}

/**
 * Teleport the Cantor to open floor 5-9 blocks from its arena center.
 * @param {Entity} boss @param {Dimension} dim @param {Vector3 | undefined} home
 */
function blink(boss, dim, home) {
  const origin = home || boss.location;
  const oy = Math.floor(origin.y);
  for (let attempt = 0; attempt < 10; attempt++) {
    const angle = Math.random() * Math.PI * 2;
    const r = 5 + Math.random() * 4;
    const x = Math.floor(origin.x + Math.cos(angle) * r);
    const z = Math.floor(origin.z + Math.sin(angle) * r);
    for (let y = oy + 2; y >= oy - 3; y--) {
      const floor = dim.getBlock({ x, y: y - 1, z });
      if (!floor || floor.isAir || floor.isLiquid) continue;
      let clear = true;
      for (let h = 0; h < 4 && clear; h++) {
        const b = dim.getBlock({ x, y: y + h, z });
        clear = !!b && b.isAir;
      }
      if (!clear) continue;
      const from = boss.location;
      if (boss.tryTeleport({ x: x + 0.5, y, z: z + 0.5 })) {
        particle(dim, "rotu:reveal_burst", { x: from.x, y: from.y + 1.5, z: from.z });
        particle(dim, "rotu:reveal_burst", { x: x + 0.5, y: y + 1.5, z: z + 0.5 });
        sound(dim, "rotu.cantor.blink", from, 1.0);
        return;
      }
    }
  }
}

function tickCantors() {
  const now = system.currentTick;
  /** @type {Set<string>} */
  const seen = new Set();
  const dim = world.getDimension("overworld");
  for (const boss of dim.getEntities({ type: CANTOR })) {
    seen.add(boss.id);
    let st = bosses.get(boss.id);
    if (!st) {
      st = { pulse: now + 200, blink: 0, hug: 0, home: homeOf(boss), last: boss.location, dim: dim.id };
      bosses.set(boss.id, st);
    }
    st.last = boss.location;
    const players = dim.getPlayers({
      location: boss.location,
      maxDistance: 24,
      excludeGameModes: [GameMode.Creative, GameMode.Spectator],
    });
    if (!players.length) continue;
    const phaseTwo = inPhaseTwo(boss);
    if (now >= st.pulse) {
      st.pulse = now + (phaseTwo ? 170 : 260);
      pulse(boss, dim, players);
    }
    const crowded = players.some((p) => dist(p.location, boss.location) < 2.8);
    st.hug = crowded ? st.hug + 1 : 0;
    if (st.hug >= 2 && now >= st.blink) {
      st.hug = 0;
      st.blink = now + (phaseTwo ? 100 : 140);
      blink(boss, dim, st.home);
    }
  }
  for (const id of [...bosses.keys()]) if (!seen.has(id)) bosses.delete(id);
}

system.runInterval(() => guard("cantor", tickCantors), 20);

// ------------------------------------------------------------------ data-driven triggers
world.afterEvents.dataDrivenEntityTrigger.subscribe(
  (e) =>
    guard("phase two", () => {
      const boss = e.entity;
      const at = boss.location;
      sound(boss.dimension, "rotu.cantor.awaken", at, 1.6);
      particle(boss.dimension, "rotu:star_burst", { x: at.x, y: at.y + 2, z: at.z });
      for (const p of playersNear(boss.dimension, at, 32)) {
        p.onScreenDisplay.setTitle("§5The note breaks", {
          subtitle: "§7The Cantor sings faster now.",
          fadeInDuration: 5,
          stayDuration: 40,
          fadeOutDuration: 15,
        });
      }
      const st = bosses.get(boss.id);
      if (st) st.pulse = system.currentTick + 40;
    }),
  { entityTypes: [CANTOR], eventTypes: ["rotu:enter_phase_two"] }
);

world.afterEvents.dataDrivenEntityTrigger.subscribe(
  (e) =>
    guard("sentinel", () => {
      const s = e.entity;
      const at = s.location;
      sound(s.dimension, "rotu.sentinel.awaken", at, 1.4);
      particle(s.dimension, "rotu:hush_dust", { x: at.x, y: at.y + 1.5, z: at.z });
      for (const p of playersNear(s.dimension, at, 16)) {
        actionBar(p, "§7The Graven Sentinel remembers its purpose.");
        guard("shake", () => p.runCommand("camerashake add @s 0.25 1.2 positional"));
      }
    }),
  { entityTypes: [SENTINEL], eventTypes: ["rotu:awaken"] }
);

// ------------------------------------------------------------------ deaths
/** @type {Record<string, string>} */
const KILL_STATS = { "rotu:hushwalker": "hushwalkers", "rotu:murmur": "murmurs", [SENTINEL]: "sentinels" };

/**
 * The Cantor's silence: open the vault, write the last chapter for everyone who was there.
 * @param {Dimension} dim @param {Vector3} center
 */
function cantorSilenced(dim, center) {
  later(40, () => {
    dissolveGates(dim, center, 14, 5, 14);
    for (const p of playersNear(dim, center, 48)) {
      setFlag(p, "cantor");
      addStat(p, "cantor");
      const fresh = unlockChapter(p, FINAL_CHAPTER);
      p.onScreenDisplay.setTitle(`§b${CHAPTERS[FINAL_CHAPTER - 1].title}`, {
        subtitle: fresh ? "§7has been written into your Codex" : "§7The note has ended.",
        fadeInDuration: 20,
        stayDuration: 80,
        fadeOutDuration: 30,
      });
    }
  });
}

world.afterEvents.entityDie.subscribe(
  ({ deadEntity, damageSource }) =>
    guard("death", () => {
      const type = deadEntity.typeId;
      const killer = damageSource.damagingEntity;
      const stat = KILL_STATS[type];
      if (stat && killer && isPlayer(killer)) addStat(killer, stat);
      if (type === SENTINEL && killer && isPlayer(killer)) {
        actionBar(killer, "§bA Hush Sigil Shard rattles loose from the Sentinel's chest.");
      }
      if (type !== CANTOR) return;
      const st = bosses.get(deadEntity.id);
      bosses.delete(deadEntity.id);
      /** @type {Vector3 | undefined} */
      let center = st && st.home;
      /** @type {Dimension} */
      let dim = world.getDimension(st ? st.dim : "overworld");
      if (!center) {
        try {
          center = deadEntity.location;
          dim = deadEntity.dimension;
        } catch {
          center = st && st.last;
        }
      }
      if (center) cantorSilenced(dim, center);
    }),
  { entityTypes: [CANTOR, SENTINEL, "rotu:hushwalker", "rotu:murmur"] }
);

// ------------------------------------------------------------------ relic armor perks
system.runInterval(
  () =>
    guard("armor", () => {
      for (const p of world.getAllPlayers()) {
        if (worn(p, EquipmentSlot.Head) === MASK) {
          if (p.getEffect("darkness")) p.removeEffect("darkness");
          if (p.getEffect("blindness")) p.removeEffect("blindness");
        }
        if (p.isSneaking && worn(p, EquipmentSlot.Chest) === MANTLE) {
          p.addEffect("invisibility", 50, { showParticles: false });
        }
      }
    }),
  10
);

// ------------------------------------------------------------------ progress sync & ambience
system.runInterval(
  () =>
    guard("ambience", () => {
      for (const p of world.getAllPlayers()) {
        syncInventoryFlags(p);
        if (Math.random() > 0.15) continue;
        const at = p.location;
        const below = p.dimension.getBlock({ x: at.x, y: at.y - 1, z: at.z });
        if (!below || !below.hasTag("rotu:gloamstone")) continue;
        const angle = Math.random() * Math.PI * 2;
        p.playSound("rotu.whisper", {
          location: { x: at.x + Math.cos(angle) * 4, y: at.y + 1, z: at.z + Math.sin(angle) * 4 },
          volume: 0.6,
          pitch: 0.85 + Math.random() * 0.3,
        });
      }
    }),
  100
);

// ------------------------------------------------------------------ welcome
world.afterEvents.playerSpawn.subscribe(({ player, initialSpawn }) => {
  if (!initialSpawn) return;
  later(80, () => {
    if (!player.isValid || hasFlag(player, "welcomed")) return;
    setFlag(player, "welcomed");
    player.sendMessage(
      "§3[Ruins of the Unnamed]§r §7Dark waystones and silent ruins have surfaced across the land. " +
        "Brush the sand around them, decipher what you find at a Scriptorium Desk, and bind a Codex of the Unnamed " +
        "(a book and a glyph shard) to follow the trail."
    );
  });
});
