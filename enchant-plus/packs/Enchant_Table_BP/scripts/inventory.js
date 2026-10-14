/**
 * Where an item lives: an inventory slot or a worn/held equipment slot. Menus keep a reference and
 * re-read the item when the player confirms, so a change made in between is detected.
 */
import { EquipmentSlot } from "@minecraft/server";
import { BOOKS } from "./data.js";
import { enchantable } from "./rules.js";

/** @typedef {import("@minecraft/server").Player} Player */
/** @typedef {import("@minecraft/server").ItemStack} ItemStack */
/** @typedef {{ kind: "slot", index: number } | { kind: "equip", slot: EquipmentSlot }} ItemRef */

const WORN = [EquipmentSlot.Head, EquipmentSlot.Chest, EquipmentSlot.Legs, EquipmentSlot.Feet, EquipmentSlot.Offhand];

/** @param {Player} player */
function container(player) {
  return player.getComponent("minecraft:inventory")?.container;
}

/** @param {Player} player */
function equipment(player) {
  return player.getComponent("minecraft:equippable");
}

/** @param {Player} player @param {ItemRef} ref @returns {ItemStack | undefined} */
export function readItem(player, ref) {
  if (ref.kind === "slot") return container(player)?.getItem(ref.index);
  return equipment(player)?.getEquipment(ref.slot);
}

/** @param {Player} player @param {ItemRef} ref @param {ItemStack | undefined} item */
export function writeItem(player, ref, item) {
  if (ref.kind === "slot") container(player)?.setItem(ref.index, item);
  else equipment(player)?.setEquipment(ref.slot, item);
}

/** @param {ItemRef} a @param {ItemRef} b */
export function sameRef(a, b) {
  return a.kind === b.kind && (a.kind === "slot" ? a.index === /** @type {any} */ (b).index : a.slot === /** @type {any} */ (b).slot);
}

/** @param {ItemStack} item */
export function isEnchantable(item) {
  return BOOKS.has(item.typeId) || enchantable(item) !== undefined;
}

/**
 * Every enchantable item the player carries: worn items first, then hotbar, then inventory.
 * @param {Player} player
 * @returns {{ ref: ItemRef, item: ItemStack }[]}
 */
export function enchantableItems(player) {
  /** @type {{ ref: ItemRef, item: ItemStack }[]} */
  const out = [];
  const eq = equipment(player);
  for (const slot of WORN) {
    const item = eq?.getEquipment(slot);
    if (item && isEnchantable(item)) out.push({ ref: { kind: "equip", slot }, item });
  }
  const inv = container(player);
  for (let i = 0; inv && i < inv.size; i++) {
    const item = inv.getItem(i);
    if (item && isEnchantable(item)) out.push({ ref: { kind: "slot", index: i }, item });
  }
  return out;
}

/** Lang key and argument describing where an item is. @param {ItemRef} ref */
export function placeOf(ref) {
  if (ref.kind === "equip") return { translate: `enchant_plus.place.${ref.slot.toLowerCase()}` };
  if (ref.index < 9) return { translate: "enchant_plus.place.hotbar", with: [String(ref.index + 1)] };
  return { translate: "enchant_plus.place.inventory", with: [String(ref.index - 8)] };
}

/**
 * A fingerprint of an item, to tell whether it changed while a menu was open.
 * @param {ItemStack | undefined} item
 */
export function signature(item) {
  if (!item) return "";
  const enchants = (enchantable(item)?.getEnchantments() ?? []).map((e) => `${e.type.id}:${e.level}`).sort();
  return [item.typeId, item.amount, item.nameTag ?? "", item.getLore().join("|"), enchants.join(",")].join("#");
}

/** Number of items of a type in the inventory. @param {Player} player @param {string} typeId */
export function countItems(player, typeId) {
  const inv = container(player);
  let n = 0;
  for (let i = 0; inv && i < inv.size; i++) {
    const item = inv.getItem(i);
    if (item?.typeId === typeId) n += item.amount;
  }
  return n;
}

/** Remove `amount` items of a type from the inventory. Returns false (removing nothing) if short. */
export function takeItems(/** @type {Player} */ player, /** @type {string} */ typeId, /** @type {number} */ amount) {
  if (amount <= 0) return true;
  if (countItems(player, typeId) < amount) return false;
  const inv = container(player);
  let left = amount;
  for (let i = 0; inv && i < inv.size && left > 0; i++) {
    const item = inv.getItem(i);
    if (item?.typeId !== typeId) continue;
    if (item.amount > left) {
      item.amount -= left;
      inv.setItem(i, item);
      left = 0;
    } else {
      left -= item.amount;
      inv.setItem(i, undefined);
    }
  }
  return true;
}

/** Give an item to the player; whatever does not fit drops at their feet. */
export function giveItem(/** @type {Player} */ player, /** @type {ItemStack} */ item) {
  const left = container(player)?.addItem(item) ?? item;
  if (left) player.dimension.spawnItem(left, player.location);
}
