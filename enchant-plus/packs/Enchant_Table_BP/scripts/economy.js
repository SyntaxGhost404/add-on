/**
 * Prices and payments. A price is per enchantment level (see config.js), in up to three currencies:
 * experience levels, an item (Enchant Essence by default) and a scoreboard objective.
 */
import { GameMode, ItemStack, world } from "@minecraft/server";
import { config } from "./config.js";
import { countItems, giveItem, takeItems } from "./inventory.js";

/** @typedef {import("@minecraft/server").Player} Player */
/** @typedef {{ xp: number, essence: number, score: number }} Price */

/** @param {Player} player */
export function isFree(player) {
  return config.creativeIsFree && player.getGameMode() === GameMode.Creative;
}

/** Price of adding or moving `levels` enchantment levels. @param {number} levels @returns {Price} */
export function priceOf(levels) {
  return {
    xp: config.xp.enabled ? levels * config.xp.costPerLevel : 0,
    essence: config.essence.enabled ? levels * config.essence.costPerLevel : 0,
    score: config.score.enabled ? levels * config.score.costPerLevel : 0,
  };
}

/** Refund for removing `levels` enchantment levels. @param {number} levels @returns {Price} */
export function refundOf(levels) {
  const full = priceOf(levels);
  return {
    xp: Math.floor(full.xp * config.xp.refund),
    essence: Math.floor(full.essence * config.essence.refund),
    score: Math.floor(full.score * config.score.refund),
  };
}

function objective() {
  const board = world.scoreboard;
  return board.getObjective(config.score.objective) ?? board.addObjective(config.score.objective, config.score.displayName);
}

/** What the player has in each enabled currency. @param {Player} player @returns {Price} */
export function balanceOf(player) {
  return {
    xp: config.xp.enabled ? player.level : 0,
    essence: config.essence.enabled ? countItems(player, config.essence.item) : 0,
    score: config.score.enabled ? objective().getScore(player) ?? 0 : 0,
  };
}

/**
 * How much of each currency the player is missing for a price (all zero if they can pay).
 * @param {Player} player @param {Price} price @returns {Price}
 */
export function shortfall(player, price) {
  if (isFree(player)) return { xp: 0, essence: 0, score: 0 };
  const have = balanceOf(player);
  return {
    xp: Math.max(0, price.xp - have.xp),
    essence: Math.max(0, price.essence - have.essence),
    score: Math.max(0, price.score - have.score),
  };
}

/** @param {Price} p */
export function isZero(p) {
  return p.xp === 0 && p.essence === 0 && p.score === 0;
}

/** Take a price from the player. Returns false, taking nothing, if they cannot pay all of it. */
export function charge(/** @type {Player} */ player, /** @type {Price} */ price) {
  if (isFree(player)) return true;
  if (!isZero(shortfall(player, price))) return false;
  if (price.essence > 0 && !takeItems(player, config.essence.item, price.essence)) return false;
  if (price.xp > 0) player.addLevels(-price.xp);
  if (price.score > 0) {
    const obj = objective();
    obj.setScore(player, (obj.getScore(player) ?? 0) - price.score);
  }
  return true;
}

/** Pay a refund to the player. Players in free (Creative) mode get nothing back. */
export function pay(/** @type {Player} */ player, /** @type {Price} */ amount) {
  if (isFree(player)) return;
  if (amount.xp > 0) player.addLevels(amount.xp);
  if (amount.score > 0) {
    const obj = objective();
    obj.setScore(player, (obj.getScore(player) ?? 0) + amount.score);
  }
  for (let left = amount.essence; left > 0; left -= 64) {
    giveItem(player, new ItemStack(config.essence.item, Math.min(64, left)));
  }
}
