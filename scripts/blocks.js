// @ts-check
// Block custom components: murals, dials, gates, locks, traps, urns, the scriptorium, reliquaries
// and the hidden spawn markers that wake a structure's inhabitants.
import { system, world, ItemStack, Difficulty, GameMode, EquipmentSlot } from "@minecraft/server";
import { CHAPTERS, GLYPH_NAMES, MURAL_CAPTIONS, WHISPERS } from "./lore.js";
import { addStat, getProgress, hasClaimed, markClaimed, nextTabletChapter, setFlag, unlockChapter } from "./progress.js";
import { openCodex, showChapter } from "./codex.js";
import { dissolveGates } from "./gates.js";
import {
  actionBar,
  consumeMainhand,
  findBlocks,
  getStateOf,
  giveItem,
  guard,
  isCreative,
  isPlayer,
  later,
  mainhandItem,
  particle,
  playersNear,
  posKey,
  setStateOf,
  sound,
  throttle,
} from "./util.js";

/** @typedef {import("@minecraft/server").Block} Block */
/** @typedef {import("@minecraft/server").Dimension} Dimension */
/** @typedef {import("@minecraft/server").Player} Player */
/** @typedef {import("@minecraft/server").Vector3} Vector3 */
/** @typedef {import("@minecraft/server").BlockCustomComponent} BlockCustomComponent */

const DIAL = "rotu:glyph_dial";

/** @param {Block} block @param {number} [dy] */
const top = (block, dy = 0.6) => {
  const c = block.center();
  return { x: c.x, y: c.y + dy, z: c.z };
};

const peaceful = () => world.getDifficulty() === Difficulty.Peaceful;

/**
 * Release a short-lived Murmur unless too many are already around.
 * @param {Dimension} dim @param {Vector3} at
 */
function releaseMurmur(dim, at) {
  if (peaceful()) return false;
  const nearby = dim.getEntities({ type: "rotu:murmur", location: at, maxDistance: 12 });
  if (nearby.length >= 3) return false;
  dim.spawnEntity("rotu:murmur", at, { spawnEvent: "rotu:temporary" });
  return true;
}

// ------------------------------------------------------------------ murals & cipher stones
/** @type {BlockCustomComponent} */
const cycler = {
  onPlayerInteract(e, { params }) {
    const { block, dimension, player } = e;
    if (!player) return;
    const { state, count } = /** @type {{ state: string, count: number }} */ (params);
    const value = Number(getStateOf(block.permutation, state) ?? 0);
    const held = mainhandItem(player);
    if (held && held.typeId === "rotu:glyph_shard") {
      const next = (value + 1) % count;
      block.setPermutation(setStateOf(block.permutation, state, next));
      sound(dimension, "rotu.dial.turn", block.center(), 0.8, 1.25);
      particle(dimension, "rotu:glyph_motes", block.center());
      return;
    }
    if (block.typeId === "rotu:cipher_stone") {
      actionBar(player, `§3The stone bears the ${GLYPH_NAMES[value]} glyph.`);
    } else {
      actionBar(player, `§7${MURAL_CAPTIONS[value] || ""}`);
    }
  },
};

// ------------------------------------------------------------------ singing stones
/** @type {BlockCustomComponent} */
const singingStone = {
  onRandomTick(e) {
    const { block, dimension } = e;
    const at = block.center();
    if (!playersNear(dimension, at, 24).length) return;
    const t = world.getTimeOfDay();
    const night = t > 13000 && t < 23000;
    if (!night && Math.random() < 0.5) return;
    sound(dimension, "rotu.singing_stone.hum", at, 0.9);
    particle(dimension, "rotu:glyph_motes", top(block));
  },
  onPlayerInteract(e) {
    const { block, dimension, player } = e;
    if (!player || !throttle(`sing:${player.id}`, 20)) return;
    sound(dimension, "rotu.singing_stone.hum", block.center(), 1.0);
    particle(dimension, "rotu:glyph_motes", top(block));
    actionBar(player, `§3${WHISPERS[Math.floor(Math.random() * WHISPERS.length)]}`);
  },
};

// ------------------------------------------------------------------ glyph dials
/**
 * When every dial around a gate shows its target glyph, the gate dissolves.
 * @param {Dimension} dim @param {Vector3} loc
 */
function checkDials(dim, loc) {
  const dials = findBlocks(dim, loc, 6, 2, 6, [DIAL]);
  if (!dials.length) return;
  let cx = 0;
  let cy = 0;
  let cz = 0;
  for (const d of dials) {
    const b = dim.getBlock(d);
    if (!b) return;
    if (getStateOf(b.permutation, "rotu:glyph") !== getStateOf(b.permutation, "rotu:solution")) return;
    cx += d.x;
    cy += d.y;
    cz += d.z;
  }
  const center = { x: cx / dials.length, y: cy / dials.length, z: cz / dials.length };
  if (!dissolveGates(dim, center, 7, 6, 7)) return;
  sound(dim, "rotu.puzzle.solved", center, 1.2);
  for (const d of dials) particle(dim, "rotu:reveal_burst", { x: d.x + 0.5, y: d.y + 0.5, z: d.z + 0.5 });
  for (const p of playersNear(dim, center, 16)) {
    addStat(p, "gates");
    actionBar(p, "§bThe glyphs agree. The sealed gate dissolves.");
  }
}

/** @type {BlockCustomComponent} */
const glyphDial = {
  onPlayerInteract(e) {
    const { block, dimension, player } = e;
    if (!player || !throttle(`dial:${player.id}`, 4)) return;
    const glyph = (Number(getStateOf(block.permutation, "rotu:glyph") ?? 0) + 1) % 4;
    block.setPermutation(setStateOf(block.permutation, "rotu:glyph", glyph));
    sound(dimension, "rotu.dial.turn", block.center(), 1, 0.8 + glyph * 0.12);
    actionBar(player, `§3The dial turns to the ${GLYPH_NAMES[glyph]} glyph.`);
    checkDials(dimension, block.location);
  },
};

// ------------------------------------------------------------------ sigil lock
/** @type {BlockCustomComponent} */
const sigilLock = {
  onPlayerInteract(e) {
    const { block, dimension, player } = e;
    if (!player || !throttle(`lock:${player.id}`, 10)) return;
    if (getStateOf(block.permutation, "rotu:unlocked")) {
      actionBar(player, "§7The lock stands open.");
      return;
    }
    const held = mainhandItem(player);
    if (!held || held.typeId !== "rotu:sigil_key") {
      sound(dimension, "rotu.reliquary.denied", block.center());
      actionBar(player, "§7Three sigils are carved here: a lantern, a bone and a sewn mouth.");
      return;
    }
    block.setPermutation(setStateOf(block.permutation, "rotu:unlocked", true));
    setFlag(player, "key");
    sound(dimension, "rotu.reliquary.insert", block.center());
    particle(dimension, "rotu:reveal_burst", block.center());
    const where = block.location;
    later(20, () => {
      dissolveGates(dimension, where, 6, 5, 6);
      sound(dimension, "rotu.cantor.awaken", where, 0.8);
      for (const p of playersNear(dimension, where, 24)) {
        p.onScreenDisplay.setTitle("§5The Sanctum opens", {
          subtitle: "§7Something below has stopped singing to listen.",
          fadeInDuration: 10,
          stayDuration: 60,
          fadeOutDuration: 20,
        });
      }
    });
  },
};

// ------------------------------------------------------------------ veilstone
/** @type {BlockCustomComponent} */
const veilstone = {
  onPlayerInteract(e) {
    const { block, dimension, player } = e;
    if (!player || !throttle(`veil:${player.id}`, 20)) return;
    if (getStateOf(block.permutation, "rotu:revealed")) {
      actionBar(player, "§7The veil is thin here. You could walk through it.");
      return;
    }
    sound(dimension, "rotu.whisper", block.center(), 0.4, 1.3);
    actionBar(player, "§7These bricks feel cold... and faintly hollow.");
  },
};

// ------------------------------------------------------------------ hushing plates
/** Tick a plate was last sprung, keyed by location. @type {Map<string, number>} */
const sprung = new Map();
const PLATE_RECHARGE = 200;

/** @param {Player} player */
function wearsMantle(player) {
  const eq = player.getComponent("minecraft:equippable");
  const chest = eq && eq.getEquipment(EquipmentSlot.Chest);
  return !!chest && chest.typeId === "rotu:hushweave_mantle";
}

/** @type {BlockCustomComponent} */
const hushingPlate = {
  onStepOn(e) {
    const { block, dimension, entity } = e;
    if (!entity || !isPlayer(entity)) return;
    const player = entity;
    if (player.isSneaking || isCreative(player) || player.getGameMode() === GameMode.Spectator) return;
    if (getStateOf(block.permutation, "rotu:spent")) return;
    if (wearsMantle(player)) {
      actionBar(player, "§7Your mantle muffles the plate.");
      return;
    }
    block.setPermutation(setStateOf(block.permutation, "rotu:spent", true));
    sprung.set(`${dimension.id}:${posKey(block.location)}`, system.currentTick);
    player.addEffect("darkness", 160, { showParticles: false });
    player.addEffect("slowness", 60, { amplifier: 0, showParticles: false });
    sound(dimension, "rotu.trap.trigger", block.center(), 0.9);
    particle(dimension, "rotu:hush_dust", top(block, 0.2));
    actionBar(player, "§8The plate drinks the sound of your step. §7(Sneak to cross safely.)");
    if (Math.random() < 0.35) releaseMurmur(dimension, top(block, 1.0));
  },
  onTick(e) {
    const { block, dimension } = e;
    if (!getStateOf(block.permutation, "rotu:spent")) return;
    const key = `${dimension.id}:${posKey(block.location)}`;
    const at = sprung.get(key);
    if (at !== undefined && system.currentTick - at < PLATE_RECHARGE) return;
    sprung.delete(key);
    block.setPermutation(setStateOf(block.permutation, "rotu:spent", false));
  },
};

// ------------------------------------------------------------------ funerary urns
/** @type {BlockCustomComponent} */
const urn = {
  onPlayerBreak(e) {
    const { block, dimension, player, brokenBlockPermutation } = e;
    if (!getStateOf(brokenBlockPermutation, "rotu:sealed")) return;
    const at = block.center();
    sound(dimension, "rotu.urn.break", at);
    particle(dimension, "rotu:hush_dust", at);
    if (player) addStat(player, "urns");
    if (Math.random() < 0.18 && releaseMurmur(dimension, at) && player) {
      actionBar(player, "§5Something was sealed inside the urn.");
    }
  },
};

// ------------------------------------------------------------------ scriptorium desk
/** @type {BlockCustomComponent} */
const scriptorium = {
  onPlayerInteract(e) {
    const { block, dimension, player } = e;
    if (!player || !throttle(`desk:${player.id}`, 20)) return;
    const held = mainhandItem(player);
    if (!held || held.typeId !== "rotu:inscribed_tablet") {
      if (held && held.typeId === "rotu:codex") {
        openCodex(player);
        return;
      }
      actionBar(player, "§7Hold an Inscribed Tablet and use the desk to decipher it.");
      return;
    }
    const chapter = nextTabletChapter(getProgress(player));
    consumeMainhand(player);
    sound(dimension, "rotu.decipher", block.center());
    particle(dimension, "rotu:glyph_motes", top(block, 0.7));
    if (chapter > 0) {
      unlockChapter(player, chapter);
      addStat(player, "tablets");
      player.addExperience(8);
      actionBar(player, `§3Deciphered: ${CHAPTERS[chapter - 1].title}`);
      later(25, () => {
        if (player.isValid) showChapter(player, chapter);
      });
    } else {
      const shards = 2 + Math.floor(Math.random() * 3);
      giveItem(player, new ItemStack("rotu:glyph_shard", shards));
      player.addExperience(4);
      actionBar(player, `§7Nothing new. The tablet crumbles into ${shards} glyph shards.`);
    }
  },
};

// ------------------------------------------------------------------ reliquaries
/** @type {Record<string, { key: string, keyName: string, table: string }>} */
const RELIQUARY = {
  lesser: { key: "rotu:reliquary_key", keyName: "a Reliquary Key", table: "rotu/reliquary/lesser" },
  grand: { key: "rotu:cantors_seal", keyName: "a Cantor's Seal", table: "rotu/reliquary/grand" },
};
/** Reliquaries currently ejecting loot. @type {Set<string>} */
const ejecting = new Set();

/** @param {string} path @returns {ItemStack[]} */
function rollLoot(path) {
  const manager = world.getLootTableManager();
  for (const candidate of [path, `loot_tables/${path}`, `loot_tables/${path}.json`]) {
    const table = manager.getLootTable(candidate);
    if (table) return manager.generateLootFromTable(table) || [];
  }
  console.warn(`[rotu] missing loot table ${path}`);
  return [new ItemStack("minecraft:emerald", 6)];
}

/** @param {Dimension} dim @param {Vector3} loc @param {ItemStack} stack */
function eject(dim, loc, stack) {
  const at = { x: loc.x + 0.5, y: loc.y + 1.0, z: loc.z + 0.5 };
  const item = dim.spawnItem(stack, at);
  guard("eject", () => item.applyImpulse({ x: (Math.random() - 0.5) * 0.15, y: 0.25, z: (Math.random() - 0.5) * 0.15 }));
  sound(dim, "rotu.reliquary.eject", at, 0.8);
  particle(dim, "rotu:glyph_motes", at);
}

/** @type {BlockCustomComponent} */
const reliquary = {
  onPlayerInteract(e) {
    const { block, dimension, player } = e;
    if (!player || !throttle(`rq:${player.id}`, 10)) return;
    const tier = String(getStateOf(block.permutation, "rotu:tier") || "lesser");
    const spec = RELIQUARY[tier] || RELIQUARY.lesser;
    const loc = block.location;
    const busyKey = `${dimension.id}:${posKey(loc)}`;
    if (ejecting.has(busyKey)) return;
    if (hasClaimed(dimension.id, loc, player)) {
      sound(dimension, "rotu.reliquary.denied", block.center());
      actionBar(player, "§7This reliquary has already rewarded you.");
      return;
    }
    const held = mainhandItem(player);
    if (!held || held.typeId !== spec.key) {
      sound(dimension, "rotu.reliquary.denied", block.center());
      actionBar(player, `§7The reliquary is sealed. §8(It needs ${spec.keyName}.)`);
      return;
    }
    consumeMainhand(player);
    markClaimed(dimension.id, loc, player);
    addStat(player, "reliquaries");
    ejecting.add(busyKey);
    sound(dimension, "rotu.reliquary.insert", block.center());
    const loot = rollLoot(spec.table);
    later(20, () => {
      sound(dimension, "rotu.reliquary.open", block.center(), 1.0);
      particle(dimension, "rotu:reveal_burst", top(block, 0.3));
    });
    loot.forEach((stack, i) => later(32 + i * 8, () => eject(dimension, loc, stack)));
    later(40 + loot.length * 8, () => ejecting.delete(busyKey));
  },
  onTick(e) {
    const { block, dimension } = e;
    const at = block.center();
    const near = playersNear(dimension, at, 10);
    if (!near.length || !near.some((p) => !hasClaimed(dimension.id, block.location, p))) return;
    particle(dimension, "rotu:glyph_motes", top(block, 0.4));
    if (Math.random() < 0.3) sound(dimension, "rotu.reliquary.ambient", at, 0.6);
  },
};

// ------------------------------------------------------------------ spawn markers
/** @type {Record<string, number>} */
const MARKER_RANGE = { hushwalkers: 14, murmurs: 12, sentinel: 18, cantor: 13 };

/** @param {Dimension} dim @param {Vector3} feet @param {Vector3} home */
function awakenCantor(dim, feet, home) {
  const boss = dim.spawnEntity("rotu:last_cantor", feet);
  boss.setDynamicProperty("rotu:home", home);
  sound(dim, "rotu.cantor.awaken", feet, 1.5);
  particle(dim, "rotu:star_burst", { x: feet.x, y: feet.y + 1.6, z: feet.z });
  for (const p of playersNear(dim, feet, 32)) {
    p.onScreenDisplay.setTitle("§5The Last Cantor", {
      subtitle: "§7holds the final note",
      fadeInDuration: 10,
      stayDuration: 50,
      fadeOutDuration: 20,
    });
  }
}

/** @type {BlockCustomComponent} */
const spawnMarker = {
  onTick(e) {
    const { block, dimension } = e;
    const kind = String(getStateOf(block.permutation, "rotu:mob") || "hushwalkers");
    const at = block.center();
    const players = dimension.getPlayers({
      location: at,
      maxDistance: MARKER_RANGE[kind] || 12,
      excludeGameModes: [GameMode.Spectator],
    });
    if (!players.length || peaceful()) return;
    const home = block.location;
    const feet = { x: at.x, y: home.y, z: at.z };
    block.setType("minecraft:air");
    if (kind === "hushwalkers") {
      const n = 2 + (world.getDifficulty() === Difficulty.Hard ? 1 : 0);
      for (let i = 0; i < n; i++) dimension.spawnEntity("rotu:hushwalker", feet);
    } else if (kind === "murmurs") {
      const n = 1 + Math.floor(Math.random() * 2);
      for (let i = 0; i < n; i++) dimension.spawnEntity("rotu:murmur", { x: feet.x, y: feet.y + 0.5, z: feet.z });
    } else if (kind === "sentinel") {
      dimension.spawnEntity("rotu:graven_sentinel", feet);
    } else if (kind === "cantor") {
      awakenCantor(dimension, feet, home);
    }
  },
};

system.beforeEvents.startup.subscribe(({ blockComponentRegistry: reg }) => {
  reg.registerCustomComponent("rotu:cycler", cycler);
  reg.registerCustomComponent("rotu:singing_stone", singingStone);
  reg.registerCustomComponent("rotu:glyph_dial", glyphDial);
  reg.registerCustomComponent("rotu:sigil_lock", sigilLock);
  reg.registerCustomComponent("rotu:veilstone", veilstone);
  reg.registerCustomComponent("rotu:hushing_plate", hushingPlate);
  reg.registerCustomComponent("rotu:urn", urn);
  reg.registerCustomComponent("rotu:scriptorium", scriptorium);
  reg.registerCustomComponent("rotu:reliquary", reliquary);
  reg.registerCustomComponent("rotu:spawn_marker", spawnMarker);
});
