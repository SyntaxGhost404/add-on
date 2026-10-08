// @ts-check
import { world, system, BlockVolume, EquipmentSlot, GameMode, Player, ItemStack } from "@minecraft/server";

/** @typedef {import("@minecraft/server").Vector3} Vector3 */
/** @typedef {import("@minecraft/server").Dimension} Dimension */
/** @typedef {import("@minecraft/server").Entity} Entity */
/** @typedef {import("@minecraft/server").BlockPermutation} BlockPermutation */

/** @param {Vector3} a @param {Vector3} b */
export const vadd = (a, b) => ({ x: a.x + b.x, y: a.y + b.y, z: a.z + b.z });
/** @param {Vector3} a @param {Vector3} b */
export const vsub = (a, b) => ({ x: a.x - b.x, y: a.y - b.y, z: a.z - b.z });
/** @param {Vector3} a @param {number} s */
export const vscale = (a, s) => ({ x: a.x * s, y: a.y * s, z: a.z * s });
/** @param {Vector3} a */
export const vlen = (a) => Math.sqrt(a.x * a.x + a.y * a.y + a.z * a.z);
/** @param {Vector3} a @param {Vector3} b */
export const dist = (a, b) => vlen(vsub(a, b));
/** Center of the block at an integer location. @param {Vector3} p */
export const centerOf = (p) => ({ x: Math.floor(p.x) + 0.5, y: Math.floor(p.y) + 0.5, z: Math.floor(p.z) + 0.5 });
/** @param {Vector3} p */
export const posKey = (p) => `${Math.floor(p.x)},${Math.floor(p.y)},${Math.floor(p.z)}`;

/**
 * Read a block state by name (custom states are not part of the vanilla typings).
 * @param {BlockPermutation} perm @param {string} name @returns {boolean | number | string | undefined}
 */
export const getStateOf = (perm, name) => /** @type {any} */ (perm).getState(name);

/**
 * Copy of a permutation with one state changed.
 * @param {BlockPermutation} perm @param {string} name @param {boolean | number | string} value
 * @returns {BlockPermutation}
 */
export const setStateOf = (perm, name, value) => /** @type {any} */ (perm).withState(name, value);

/** Last use tick per key, for simple per-player rate limits. @type {Map<string, number>} */
const lastUse = new Map();

/**
 * True if `key` was not used in the last `ticks` ticks (and records this use).
 * @param {string} key @param {number} ticks
 */
export function throttle(key, ticks) {
  const now = system.currentTick;
  const prev = lastUse.get(key);
  if (prev !== undefined && now - prev < ticks) return false;
  lastUse.set(key, now);
  return true;
}

/** @param {Entity} entity @returns {entity is Player} */
export const isPlayer = (entity) => entity instanceof Player;

/** Run a callback and log (never throw) on failure. @param {string} label @param {() => void} fn */
export function guard(label, fn) {
  try {
    fn();
  } catch (e) {
    console.warn(`[rotu] ${label}: ${e}`);
  }
}

/** @param {Player} player */
export function isCreative(player) {
  try {
    return player.getGameMode() === GameMode.Creative;
  } catch {
    return false;
  }
}

/** @param {Player} player */
export function mainhandSlot(player) {
  const eq = player.getComponent("minecraft:equippable");
  return eq ? eq.getEquipmentSlot(EquipmentSlot.Mainhand) : undefined;
}

/** @param {Player} player */
export function mainhandItem(player) {
  const slot = mainhandSlot(player);
  return slot && slot.hasItem() ? slot.getItem() : undefined;
}

/** Remove `count` items from the main hand (no-op in creative). @param {Player} player @param {number} [count] */
export function consumeMainhand(player, count = 1) {
  if (isCreative(player)) return true;
  const slot = mainhandSlot(player);
  if (!slot || !slot.hasItem()) return false;
  if (slot.amount > count) {
    slot.amount = slot.amount - count;
  } else {
    slot.setItem(undefined);
  }
  return true;
}

/**
 * Damage the item in the main hand, honouring Unbreaking. Returns false if the item broke.
 * @param {Player} player @param {number} [amount]
 */
export function damageMainhand(player, amount = 1) {
  if (isCreative(player)) return true;
  const slot = mainhandSlot(player);
  if (!slot || !slot.hasItem()) return false;
  const item = slot.getItem();
  if (!item) return false;
  const dur = item.getComponent("minecraft:durability");
  if (!dur) return true;
  let level = 0;
  const ench = item.getComponent("minecraft:enchantable");
  if (ench) {
    const unbreaking = ench.getEnchantment("unbreaking");
    level = unbreaking ? unbreaking.level : 0;
  }
  let applied = 0;
  for (let i = 0; i < amount; i++) {
    if (Math.random() < 1 / (level + 1)) applied++;
  }
  if (dur.damage + applied >= dur.maxDurability) {
    slot.setItem(undefined);
    player.playSound("random.break");
    return false;
  }
  dur.damage = dur.damage + applied;
  slot.setItem(item);
  return true;
}

/** Give an item, dropping it at the player's feet if the inventory is full. @param {Player} player @param {ItemStack} stack */
export function giveItem(player, stack) {
  const inv = player.getComponent("minecraft:inventory");
  const left = inv && inv.container ? inv.container.addItem(stack) : stack;
  if (left) player.dimension.spawnItem(left, player.location);
}

/** Count items of a type in a player's inventory. @param {Player} player @param {string} typeId */
export function countItem(player, typeId) {
  const inv = player.getComponent("minecraft:inventory");
  const c = inv && inv.container;
  if (!c) return 0;
  let n = 0;
  for (let i = 0; i < c.size; i++) {
    const it = c.getItem(i);
    if (it && it.typeId === typeId) n += it.amount;
  }
  return n;
}

/**
 * Locations of blocks of the given types inside a box around a point (empty array on any failure).
 * @param {Dimension} dim @param {Vector3} c @param {number} rx @param {number} ry @param {number} rz @param {string[]} types
 * @returns {Vector3[]}
 */
export function findBlocks(dim, c, rx, ry, rz, types) {
  const lo = dim.heightRange.min;
  const hi = dim.heightRange.max - 1;
  const from = { x: Math.floor(c.x - rx), y: Math.max(lo, Math.floor(c.y - ry)), z: Math.floor(c.z - rz) };
  const to = { x: Math.floor(c.x + rx), y: Math.min(hi, Math.floor(c.y + ry)), z: Math.floor(c.z + rz) };
  if (from.y > to.y) return [];
  try {
    const volume = dim.getBlocks(new BlockVolume(from, to), { includeTypes: types }, false);
    return [...volume.getBlockLocationIterator()];
  } catch {
    return [];
  }
}

/** Compass words for a horizontal offset. @param {number} dx @param {number} dz */
export function compass(dx, dz) {
  const names = ["south", "south-west", "west", "north-west", "north", "north-east", "east", "south-east"];
  const angle = Math.atan2(-dx, dz);
  const idx = (Math.round(angle / (Math.PI / 4)) + 8) % 8;
  return names[idx];
}

/** @param {Dimension} dim @param {string} sound @param {Vector3} at @param {number} [volume] @param {number} [pitch] */
export function sound(dim, sound, at, volume = 1, pitch = 1) {
  guard(`sound ${sound}`, () => dim.playSound(sound, at, { volume, pitch }));
}

/** @param {Dimension} dim @param {string} id @param {Vector3} at */
export function particle(dim, id, at) {
  try {
    dim.spawnParticle(id, at);
  } catch {
    // particle spawning fails silently in unloaded chunks
  }
}

/** Players within a radius of a point. @param {Dimension} dim @param {Vector3} at @param {number} radius */
export function playersNear(dim, at, radius) {
  return dim.getPlayers({ location: at, maxDistance: radius });
}

/** @param {Player} player @param {string} text */
export function actionBar(player, text) {
  guard("actionbar", () => player.onScreenDisplay.setActionBar(text));
}

/** Schedule a callback after `ticks`. @param {number} ticks @param {() => void} fn */
export function later(ticks, fn) {
  system.runTimeout(() => guard("later", fn), ticks);
}

export { world, system };
