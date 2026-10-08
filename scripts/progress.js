// @ts-check
import { world } from "@minecraft/server";

/** @typedef {import("@minecraft/server").Player} Player */

const KEY = "rotu:progress";
export const CHAPTER_COUNT = 12;
export const FINAL_CHAPTER = 12;

/**
 * @typedef {Object} Progress
 * @property {number} v
 * @property {number[]} chapters
 * @property {Record<string, boolean>} flags
 * @property {Record<string, number>} stats
 */

/** @returns {Progress} */
function fresh() {
  return { v: 1, chapters: [], flags: {}, stats: {} };
}

/** @param {Player} player @returns {Progress} */
export function getProgress(player) {
  const raw = player.getDynamicProperty(KEY);
  if (typeof raw !== "string") return fresh();
  try {
    const p = JSON.parse(raw);
    return {
      v: 1,
      chapters: Array.isArray(p.chapters) ? p.chapters.filter((/** @type {any} */ n) => typeof n === "number") : [],
      flags: p.flags && typeof p.flags === "object" ? p.flags : {},
      stats: p.stats && typeof p.stats === "object" ? p.stats : {},
    };
  } catch {
    return fresh();
  }
}

/** @param {Player} player @param {Progress} p */
export function saveProgress(player, p) {
  player.setDynamicProperty(KEY, JSON.stringify(p));
}

/** Apply a mutation to a player's progress and persist it. @param {Player} player @param {(p: Progress) => void} fn */
export function update(player, fn) {
  const p = getProgress(player);
  fn(p);
  saveProgress(player, p);
  return p;
}

/** @param {Player} player @param {string} key @param {number} [n] */
export function addStat(player, key, n = 1) {
  update(player, (p) => {
    p.stats[key] = (p.stats[key] || 0) + n;
  });
}

/** @param {Player} player @param {string} flag */
export function setFlag(player, flag) {
  update(player, (p) => {
    p.flags[flag] = true;
  });
}

/** @param {Player} player @param {string} flag */
export function hasFlag(player, flag) {
  return getProgress(player).flags[flag] === true;
}

/**
 * The next chapter a tablet reveals (chapters 1-11 in order; 12 is earned from the Cantor).
 * @param {Progress} p
 */
export function nextTabletChapter(p) {
  for (let n = 1; n < FINAL_CHAPTER; n++) {
    if (!p.chapters.includes(n)) return n;
  }
  return 0;
}

/** @param {Player} player @param {number} chapter @returns {boolean} true if newly unlocked */
export function unlockChapter(player, chapter) {
  let added = false;
  update(player, (p) => {
    if (!p.chapters.includes(chapter)) {
      p.chapters.push(chapter);
      p.chapters.sort((a, b) => a - b);
      added = true;
    }
  });
  return added;
}

/** Item -> progress flag recorded when the item is carried. */
const CARRIED_FLAGS = {
  "rotu:lantern_shard": "lantern",
  "rotu:bone_shard": "bone",
  "rotu:hush_shard": "hush",
  "rotu:sigil_key": "key",
  "rotu:cantors_seal": "seal",
  "rotu:diviners_lens": "lens",
  "rotu:dowsing_rod": "rod",
};

/** Record sigil items the player is carrying so progress survives using/crafting them. @param {Player} player */
export function syncInventoryFlags(player) {
  const inv = player.getComponent("minecraft:inventory");
  const c = inv && inv.container;
  if (!c) return;
  /** @type {Set<string>} */
  const carried = new Set();
  for (let i = 0; i < c.size; i++) {
    const it = c.getItem(i);
    if (it && it.typeId in CARRIED_FLAGS) carried.add(it.typeId);
  }
  const p = getProgress(player);
  let changed = false;
  for (const id of carried) {
    const flag = CARRIED_FLAGS[/** @type {keyof typeof CARRIED_FLAGS} */ (id)];
    if (!p.flags[flag]) {
      p.flags[flag] = true;
      changed = true;
    }
  }
  if (p.flags.key && !(p.flags.lantern && p.flags.bone && p.flags.hush)) {
    p.flags.lantern = p.flags.bone = p.flags.hush = true;
    changed = true;
  }
  if (changed) saveProgress(player, p);
}

// ---------------------------------------------------------------- per-player reliquary claims (world storage)

/** @param {string} dimId @param {import("@minecraft/server").Vector3} loc */
function claimKey(dimId, loc) {
  return `rotu:rq:${dimId}:${Math.floor(loc.x)},${Math.floor(loc.y)},${Math.floor(loc.z)}`;
}

/** @param {string} dimId @param {import("@minecraft/server").Vector3} loc @param {Player} player */
export function hasClaimed(dimId, loc, player) {
  const raw = world.getDynamicProperty(claimKey(dimId, loc));
  return typeof raw === "string" && raw.split("|").includes(player.id);
}

/** @param {string} dimId @param {import("@minecraft/server").Vector3} loc @param {Player} player */
export function markClaimed(dimId, loc, player) {
  const k = claimKey(dimId, loc);
  const raw = world.getDynamicProperty(k);
  const ids = typeof raw === "string" && raw.length ? raw.split("|") : [];
  if (!ids.includes(player.id)) ids.push(player.id);
  world.setDynamicProperty(k, ids.join("|"));
}
