/**
 * Enchantment rules: which enchantments an item accepts, which ones conflict, and how to build the
 * enchanted result. Results are built on copies, so nothing changes until the caller writes them back.
 */
import { EnchantmentTypes, ItemStack } from "@minecraft/server";
import { BOOKS, BY_ITEM, BY_SLOT, ENCHANT_NAMES, EXCLUSIVE } from "./data.js";

/** @typedef {import("@minecraft/server").EnchantmentType} EnchantmentType */
/** @typedef {import("@minecraft/server").ItemEnchantableComponent} ItemEnchantableComponent */

/** @param {string} id */
export const shortId = (id) => id.replace(/^minecraft:/, "");

/** @param {ItemStack | undefined} item @returns {ItemEnchantableComponent | undefined} */
export function enchantable(item) {
  if (!item) return undefined;
  try {
    return item.getComponent("minecraft:enchantable");
  } catch {
    return undefined;
  }
}

/** Enchantments on an item: short id -> level. @param {ItemStack} item @returns {Map<string, number>} */
export function levelsOf(item) {
  const out = new Map();
  for (const e of enchantable(item)?.getEnchantments() ?? []) out.set(shortId(e.type.id), e.level);
  return out;
}

/** Every enchantment type the game knows: short id -> type. @returns {Map<string, EnchantmentType>} */
export function allTypes() {
  const out = new Map();
  for (const t of EnchantmentTypes.getAll()) out.set(shortId(t.id), t);
  return out;
}

/** @param {string} typeId */
function freshStack(typeId) {
  try {
    return new ItemStack(typeId, 1);
  } catch {
    return undefined;
  }
}

/**
 * Enchantment types this kind of item accepts, whatever is already on it. The vanilla table decides
 * first (it includes treasure enchantments such as Swift Sneak on leggings); the game's own check on a
 * fresh stack of the same item adds anything the table does not know, such as other add-ons' items.
 * @param {ItemStack} item
 * @returns {EnchantmentType[]}
 */
export function applicableTypes(item) {
  const types = allTypes();
  if (BOOKS.has(item.typeId)) return [...types.values()];
  /** @type {Set<string>} */
  const ids = new Set(BY_ITEM[item.typeId] ?? []);
  if (!BY_ITEM[item.typeId]) {
    /** @type {string[]} */
    let slots = [];
    try {
      slots = enchantable(item)?.slots ?? [];
    } catch {
      slots = [];
    }
    for (const slot of slots) for (const id of BY_SLOT[slot] ?? []) ids.add(id);
  }
  const fresh = enchantable(freshStack(item.typeId));
  if (fresh) {
    for (const [id, type] of types) {
      if (ids.has(id)) continue;
      try {
        if (fresh.canAddEnchantment({ type, level: 1 })) ids.add(id);
      } catch {
        // unknown type or level: not applicable
      }
    }
  }
  return [...ids].filter((id) => types.has(id)).map((id) => /** @type {EnchantmentType} */ (types.get(id)));
}

/** @param {string} a @param {string} b */
export function conflict(a, b) {
  return a !== b && EXCLUSIVE.some((group) => group.includes(a) && group.includes(b));
}

/**
 * Pairs of enchantments in `ids` that cannot be together, each pair sorted, without duplicates.
 * @param {Iterable<string>} ids
 * @returns {[string, string][]}
 */
export function conflictsAmong(ids) {
  const list = [...new Set(ids)].sort();
  /** @type {[string, string][]} */
  const out = [];
  for (let i = 0; i < list.length; i++) {
    for (let j = i + 1; j < list.length; j++) if (conflict(list[i], list[j])) out.push([list[i], list[j]]);
  }
  return out;
}

/** Raw text naming an enchantment. @param {string} id */
export function enchantName(id) {
  const key = ENCHANT_NAMES[id];
  if (key) return { translate: key };
  return { text: id.split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ") };
}

/** Raw text for an enchantment level as a Roman numeral. @param {number} level */
export function levelText(level) {
  return level >= 1 && level <= 10 ? { translate: `enchantment.level.${level}` } : { text: String(level) };
}

/** The game refused an enchantment while building a result. */
export class EnchantError extends Error {
  /** @param {string} id @param {unknown} cause */
  constructor(id, cause) {
    super(`cannot apply ${id}: ${cause}`);
    this.id = id;
  }
}

/**
 * A copy of `item` (a single item: a stacked book counts as one) with the given enchantment levels;
 * level 0 removes an enchantment. A plain book becomes an enchanted book, and an enchanted book left
 * without enchantments becomes a plain book. Throws EnchantError if the game refuses an enchantment.
 * @param {ItemStack} item
 * @param {Map<string, number>} levels
 * @returns {ItemStack}
 */
export function withLevels(item, levels) {
  const types = allTypes();
  let out;
  if (item.typeId === "minecraft:book") {
    out = new ItemStack("minecraft:enchanted_book", 1);
  } else {
    out = item.clone();
    if (BOOKS.has(item.typeId)) out.amount = 1;
  }
  const comp = enchantable(out);
  if (!comp) throw new EnchantError([...levels.keys()].join(", "), "item is not enchantable");
  for (const [id, level] of levels) {
    const type = types.get(id);
    if (!type) throw new EnchantError(id, "unknown enchantment");
    try {
      if (comp.hasEnchantment(type)) comp.removeEnchantment(type);
      if (level > 0) comp.addEnchantment({ type, level });
    } catch (e) {
      throw new EnchantError(id, e);
    }
  }
  if (out.typeId === "minecraft:enchanted_book" && comp.getEnchantments().length === 0) {
    return new ItemStack("minecraft:book", 1);
  }
  return out;
}
