/**
 * The Enchant+ menus: choose an item, then add enchantments, remove them, or move them to another item.
 *
 * Nothing is paid or changed until the player confirms. At that moment the items are read again and
 * compared with what the menu showed, so an item that moved or changed in between cancels the
 * operation instead of duplicating or losing anything. Results are built on copies first, so a
 * combination the game refuses is reported before any payment.
 */
import { ActionFormData, ModalFormData } from "@minecraft/server-ui";
import { ItemStack } from "@minecraft/server";
import { config } from "./config.js";
import { iconFor } from "./data.js";
import { balanceOf, charge, isFree, isZero, pay, priceOf, refundOf, shortfall } from "./economy.js";
import { enchantableItems, giveItem, placeOf, readItem, sameRef, signature, writeItem } from "./inventory.js";
import {
  applicableTypes,
  conflict,
  conflictsAmong,
  EnchantError,
  enchantName,
  levelText,
  levelsOf,
  shortId,
  withLevels,
} from "./rules.js";
import { enchantLine, inputValues, itemName, present, rt, tell, title, tr } from "./ui.js";

/** @typedef {import("@minecraft/server").Player} Player */
/** @typedef {import("@minecraft/server").Dimension} Dimension */
/** @typedef {import("@minecraft/server").Vector3} Vector3 */
/** @typedef {import("@minecraft/server").RawMessage} RawMessage */
/** @typedef {import("./inventory.js").ItemRef} ItemRef */
/** @typedef {import("./economy.js").Price} Price */
/** @typedef {{ dimension: Dimension, location: Vector3 }} Table */
/** @typedef {"back" | "close"} Next */

const BACK = "back";
const CLOSE = "close";

/** Players with an open Enchant+ menu: one session at a time each. @type {Set<string>} */
const sessions = new Set();

/**
 * Open the Enchant+ menu for a player at a table.
 * @param {Player} player
 * @param {Table} table
 */
export async function openTable(player, table) {
  if (sessions.has(player.id)) return;
  sessions.add(player.id);
  try {
    await home(player, table);
  } catch (e) {
    console.warn(`[Enchant+] menu error: ${e}\n${/** @type {Error} */ (e)?.stack ?? ""}`);
  } finally {
    sessions.delete(player.id);
  }
}

// ------------------------------------------------------------------------------------------- text

/** @param {RawMessage[]} parts @param {string} separator */
function join(parts, separator) {
  /** @type {(RawMessage | string)[]} */
  const out = [];
  parts.forEach((p, i) => {
    if (i > 0) out.push(separator);
    out.push(p);
  });
  return rt(...out);
}

/** @type {RawMessage | undefined} */
let essenceNameCache;
function essenceName() {
  if (!essenceNameCache) {
    try {
      essenceNameCache = { translate: new ItemStack(config.essence.item, 1).localizationKey };
    } catch {
      essenceNameCache = { text: config.essence.item };
    }
  }
  return essenceNameCache;
}

/** @param {Price} price */
function priceText(price) {
  /** @type {RawMessage[]} */
  const parts = [];
  if (price.xp > 0) parts.push(tr("enchant_plus.price.xp", String(price.xp)));
  if (price.essence > 0) parts.push(tr("enchant_plus.price.item", String(price.essence), essenceName()));
  if (price.score > 0) parts.push(tr("enchant_plus.price.score", String(price.score), config.score.displayName));
  return parts.length ? join(parts, "\n") : tr("enchant_plus.price.none");
}

/** @param {Player} player */
function balanceText(player) {
  if (isFree(player)) return tr("enchant_plus.balance.free");
  const have = balanceOf(player);
  /** @type {RawMessage[]} */
  const parts = [];
  if (config.xp.enabled) parts.push(tr("enchant_plus.balance.xp", String(have.xp)));
  if (config.essence.enabled) parts.push(tr("enchant_plus.balance.item", essenceName(), String(have.essence)));
  if (config.score.enabled) parts.push(tr("enchant_plus.balance.score", config.score.displayName, String(have.score)));
  return parts.length ? join(parts, "\n") : tr("enchant_plus.price.none");
}

/** @param {Map<string, number>} levels */
function enchantList(levels) {
  if (levels.size === 0) return tr("enchant_plus.item.no_enchantments");
  return join(
    [...levels].map(([id, level]) => rt("§d- §r", enchantLine(id, level))),
    "\n"
  );
}

/** "Sharpness II > V", or "Sharpness V" when it is new. @param {string} id @param {number} from @param {number} to */
function changeLine(id, from, to) {
  if (to === 0) return rt(enchantName(id), " ", levelText(from), " §c> ", tr("enchant_plus.removed"));
  if (from === 0) return rt(enchantName(id), " ", levelText(to));
  return rt(enchantName(id), " ", levelText(from), " §7>§r ", levelText(to));
}

/** @param {import("@minecraft/server").ItemStack} item @param {ItemRef} ref */
function itemButton(item, ref) {
  const n = levelsOf(item).size;
  const count = n === 1 ? tr("enchant_plus.count.one") : tr("enchant_plus.count.many", String(n));
  return rt(itemName(item), "\n§8", placeOf(ref), " - ", count);
}

/** @param {Table} table @param {string} sound */
function playAt(table, sound) {
  try {
    table.dimension.playSound(sound, table.location);
  } catch {
    // the table's chunk unloaded: no sound
  }
}

// ------------------------------------------------------------------------------------------ screens

/** @param {Player} player @param {Table} table */
async function home(player, table) {
  for (;;) {
    const items = enchantableItems(player);
    if (items.length === 0) {
      tell(player, tr("enchant_plus.msg.no_items"));
      return;
    }
    const form = new ActionFormData()
      .title(title("enchant_plus.title.home"))
      .body(rt(tr("enchant_plus.home.body"), "\n\n", balanceText(player)));
    for (const { ref, item } of items) form.button(itemButton(item, ref), iconFor(item.typeId));
    const res = await present(player, form);
    if (!res || res.canceled || res.selection === undefined) return;
    const pick = items[res.selection];
    if (!pick) return;
    if ((await itemMenu(player, pick.ref, table)) === CLOSE) return;
  }
}

/** @param {Player} player @param {ItemRef} ref @param {Table} table @returns {Promise<Next>} */
async function itemMenu(player, ref, table) {
  for (;;) {
    const item = readItem(player, ref);
    if (!item) return BACK;
    const levels = levelsOf(item);
    const others = enchantableItems(player).filter((e) => !sameRef(e.ref, ref));
    const form = new ActionFormData()
      .title(title("enchant_plus.title.item"))
      .body(rt(itemName(item), "\n§8", placeOf(ref), "§r\n\n", enchantList(levels), "\n\n", balanceText(player)));
    /** @type {string[]} */
    const actions = [];
    form.button(tr("enchant_plus.button.enchant"), "textures/items/book_enchanted");
    actions.push("enchant");
    if (levels.size > 0) {
      form.button(tr("enchant_plus.button.disenchant"), "textures/items/book_normal");
      actions.push("disenchant");
      if (others.length > 0) {
        form.button(tr("enchant_plus.button.transfer"), "textures/items/experience_bottle");
        actions.push("transfer");
      }
    }
    form.button(tr("enchant_plus.button.back"));
    actions.push(BACK);
    const res = await present(player, form);
    if (!res || res.canceled || res.selection === undefined) return CLOSE;
    const action = actions[res.selection];
    /** @type {Next} */
    let next;
    if (action === "enchant") next = await enchantFlow(player, ref, table);
    else if (action === "disenchant") next = await disenchantFlow(player, ref, table);
    else if (action === "transfer") next = await transferFlow(player, ref, table);
    else return BACK;
    if (next === CLOSE) return CLOSE;
  }
}

/**
 * Summary screen before anything happens: "yes" if the player confirmed, BACK or CLOSE otherwise.
 * @param {Player} player @param {string} titleKey @param {RawMessage} summary
 * @param {Price} price what the player pays (or gets back, if `refund`) @param {boolean} refund
 * @returns {Promise<"yes" | Next>}
 */
async function confirm(player, titleKey, summary, price, refund) {
  /** @type {(RawMessage | string)[]} */
  const body = [summary, "\n\n§r"];
  if (isFree(player)) {
    body.push(tr("enchant_plus.balance.free"));
  } else {
    body.push(tr(refund ? "enchant_plus.confirm.refund" : "enchant_plus.confirm.cost"), "\n", priceText(price));
    const missing = refund ? priceOf(0) : shortfall(player, price);
    if (!isZero(missing)) body.push("\n\n§c", tr("enchant_plus.confirm.missing"), "§r\n", priceText(missing));
    body.push("\n\n", balanceText(player));
  }
  const form = new ActionFormData()
    .title(title(titleKey))
    .body(rt(...body))
    .button(tr("enchant_plus.button.confirm"))
    .button(tr("enchant_plus.button.back"));
  const res = await present(player, form);
  if (!res || res.canceled) return CLOSE;
  return res.selection === 0 ? "yes" : BACK;
}

/** Re-read an item at confirmation; tells the player and returns undefined if it changed. */
function reread(/** @type {Player} */ player, /** @type {ItemRef} */ ref, /** @type {string} */ expected) {
  const item = readItem(player, ref);
  if (!item || signature(item) !== expected) {
    tell(player, tr("enchant_plus.msg.changed"));
    return undefined;
  }
  return item;
}

/** Build a result on a copy; tells the player and returns undefined if the game refuses it. */
function build(/** @type {Player} */ player, /** @type {import("@minecraft/server").ItemStack} */ item, /** @type {Map<string, number>} */ levels) {
  try {
    return withLevels(item, levels);
  } catch (e) {
    if (!(e instanceof EnchantError)) throw e;
    tell(player, tr("enchant_plus.msg.refused", enchantName(e.id)));
    return undefined;
  }
}

/**
 * Put a result back where the item was. A stack of plain books keeps the rest of the stack in place
 * and the new enchanted book goes to the inventory (or drops at the player's feet if it is full).
 * @param {Player} player @param {ItemRef} ref @param {import("@minecraft/server").ItemStack} before
 * @param {import("@minecraft/server").ItemStack} result
 */
function store(player, ref, before, result) {
  if (before.typeId === "minecraft:book" && before.amount > 1) {
    before.amount -= 1;
    writeItem(player, ref, before);
    giveItem(player, result);
  } else {
    writeItem(player, ref, result);
  }
}

/** @param {Player} player @param {ItemRef} ref @param {Table} table @returns {Promise<Next>} */
async function enchantFlow(player, ref, table) {
  const item = readItem(player, ref);
  if (!item) return BACK;
  const expected = signature(item);
  const current = levelsOf(item);
  /** @type {{ id: string, max: number, from: number }[]} */
  const options = [];
  /** @type {{ id: string, by: string }[]} */
  const blocked = [];
  for (const type of applicableTypes(item)) {
    const id = shortId(type.id);
    const from = current.get(id) ?? 0;
    if (from >= type.maxLevel) continue;
    const by = [...current.keys()].find((other) => conflict(id, other));
    if (by) blocked.push({ id, by });
    else options.push({ id, max: type.maxLevel, from });
  }
  if (options.length === 0) {
    tell(player, tr("enchant_plus.msg.nothing_to_add"));
    return BACK;
  }

  const form = new ModalFormData().title(title("enchant_plus.title.enchant"));
  /** @type {boolean[]} */
  const isInput = [];
  form.label(rt(tr("enchant_plus.enchant.help"), "\n§7", tr("enchant_plus.price.per_level"), "§r\n", priceText(priceOf(1))));
  isInput.push(false);
  for (const o of options) {
    form.slider(rt(enchantName(o.id), " §7", tr("enchant_plus.max", levelText(o.max))), o.from, o.max, {
      valueStep: 1,
      defaultValue: o.from,
    });
    isInput.push(true);
  }
  if (blocked.length > 0) {
    const lines = blocked.map((b) => rt("\n§7- ", enchantName(b.id), " (", tr("enchant_plus.conflicts_with", enchantName(b.by)), ")"));
    form.label(rt("§7", tr("enchant_plus.enchant.blocked"), ...lines));
    isInput.push(false);
  }
  form.submitButton(tr("enchant_plus.button.review"));
  const res = await present(player, form);
  if (!res || res.canceled || !res.formValues) return CLOSE;
  const values = inputValues(res.formValues, isInput);

  /** @type {Map<string, number>} */
  const target = new Map();
  let added = 0;
  options.forEach((o, i) => {
    const to = Math.min(o.max, Math.round(Number(values[i] ?? o.from)));
    if (to > o.from) {
      target.set(o.id, to);
      added += to - o.from;
    }
  });
  if (target.size === 0) {
    tell(player, tr("enchant_plus.msg.nothing_selected"));
    return BACK;
  }
  const clash = conflictsAmong(target.keys());
  if (clash.length > 0) {
    tell(player, rt(tr("enchant_plus.msg.conflict"), ...clash.map(([a, b]) => rt("\n§c- ", enchantName(a), " + ", enchantName(b)))));
    return BACK;
  }

  const price = priceOf(added);
  const lines = [...target].map(([id, to]) => rt("\n§a+ §r", changeLine(id, current.get(id) ?? 0, to)));
  const answer = await confirm(player, "enchant_plus.title.confirm", rt(itemName(item), ...lines), price, false);
  if (answer !== "yes") return answer;

  const now = reread(player, ref, expected);
  if (!now) return BACK;
  const result = build(player, now, target);
  if (!result) return BACK;
  if (!charge(player, price)) {
    tell(player, rt(tr("enchant_plus.msg.cannot_afford"), "\n", priceText(shortfall(player, price))));
    return BACK;
  }
  store(player, ref, now, result);
  playAt(table, "block.enchanting_table.use");
  tell(player, tr("enchant_plus.msg.enchanted", itemName(result)));
  return BACK;
}

/** @param {Player} player @param {ItemRef} ref @param {Table} table @returns {Promise<Next>} */
async function disenchantFlow(player, ref, table) {
  const item = readItem(player, ref);
  if (!item) return BACK;
  const expected = signature(item);
  const current = levelsOf(item);
  if (current.size === 0) {
    tell(player, tr("enchant_plus.msg.no_enchantments"));
    return BACK;
  }

  const choice = await present(
    player,
    new ActionFormData()
      .title(title("enchant_plus.title.disenchant"))
      .body(rt(tr("enchant_plus.disenchant.body"), "\n\n", enchantList(current)))
      .button(tr("enchant_plus.button.remove_all"))
      .button(tr("enchant_plus.button.remove_some"))
      .button(tr("enchant_plus.button.back"))
  );
  if (!choice || choice.canceled) return CLOSE;

  /** @type {Map<string, number>} */
  const target = new Map();
  if (choice.selection === 0) {
    for (const id of current.keys()) target.set(id, 0);
  } else if (choice.selection === 1) {
    const entries = [...current];
    const form = new ModalFormData().title(title("enchant_plus.title.disenchant"));
    /** @type {boolean[]} */
    const isInput = [];
    form.label(tr("enchant_plus.disenchant.help"));
    isInput.push(false);
    for (const [id, level] of entries) {
      form.slider(enchantLine(id, level), 0, level, { valueStep: 1, defaultValue: level });
      isInput.push(true);
    }
    form.submitButton(tr("enchant_plus.button.review"));
    const res = await present(player, form);
    if (!res || res.canceled || !res.formValues) return CLOSE;
    const values = inputValues(res.formValues, isInput);
    entries.forEach(([id, level], i) => {
      const keep = Math.max(0, Math.min(level, Math.round(Number(values[i] ?? level))));
      if (keep < level) target.set(id, keep);
    });
  } else {
    return BACK;
  }
  if (target.size === 0) {
    tell(player, tr("enchant_plus.msg.nothing_selected"));
    return BACK;
  }

  let removed = 0;
  for (const [id, keep] of target) removed += (current.get(id) ?? 0) - keep;
  const refund = refundOf(removed);
  const lines = [...target].map(([id, keep]) => rt("\n§c- §r", changeLine(id, current.get(id) ?? 0, keep)));
  const answer = await confirm(player, "enchant_plus.title.confirm", rt(itemName(item), ...lines), refund, true);
  if (answer !== "yes") return answer;

  const now = reread(player, ref, expected);
  if (!now) return BACK;
  const result = build(player, now, target);
  if (!result) return BACK;
  writeItem(player, ref, result);
  pay(player, refund);
  playAt(table, "block.grindstone.use");
  tell(player, tr("enchant_plus.msg.disenchanted", itemName(result)));
  return BACK;
}

/** @param {Player} player @param {ItemRef} ref @param {Table} table @returns {Promise<Next>} */
async function transferFlow(player, ref, table) {
  const source = readItem(player, ref);
  if (!source) return BACK;
  const sourceExpected = signature(source);
  const sourceLevels = levelsOf(source);
  const others = enchantableItems(player).filter((e) => !sameRef(e.ref, ref));
  if (sourceLevels.size === 0 || others.length === 0) {
    tell(player, tr(sourceLevels.size === 0 ? "enchant_plus.msg.no_enchantments" : "enchant_plus.msg.no_target"));
    return BACK;
  }

  const pickForm = new ActionFormData()
    .title(title("enchant_plus.title.transfer"))
    .body(rt(tr("enchant_plus.transfer.pick"), "\n\n", itemName(source), "\n", enchantList(sourceLevels)));
  for (const { ref: r, item } of others) pickForm.button(itemButton(item, r), iconFor(item.typeId));
  pickForm.button(tr("enchant_plus.button.back"));
  const picked = await present(player, pickForm);
  if (!picked || picked.canceled) return CLOSE;
  const pick = picked.selection === undefined ? undefined : others[picked.selection];
  if (!pick) return BACK;

  const targetRef = pick.ref;
  const targetItem = pick.item;
  const targetExpected = signature(targetItem);
  const targetLevels = levelsOf(targetItem);
  const accepts = new Map(applicableTypes(targetItem).map((t) => [shortId(t.id), t]));
  /** @type {{ id: string, level: number, has: number, max: number }[]} */
  const movable = [];
  /** @type {RawMessage[]} */
  const blocked = [];
  for (const [id, level] of sourceLevels) {
    const type = accepts.get(id);
    const has = targetLevels.get(id) ?? 0;
    const by = [...targetLevels.keys()].find((other) => conflict(id, other));
    if (!type) blocked.push(rt("\n§7- ", enchantName(id), " (", tr("enchant_plus.transfer.not_accepted"), ")"));
    else if (has >= type.maxLevel) blocked.push(rt("\n§7- ", enchantName(id), " (", tr("enchant_plus.transfer.at_max"), ")"));
    else if (by) blocked.push(rt("\n§7- ", enchantName(id), " (", tr("enchant_plus.conflicts_with", enchantName(by)), ")"));
    else movable.push({ id, level, has, max: Math.min(level, type.maxLevel - has) });
  }
  if (movable.length === 0) {
    tell(player, rt(tr("enchant_plus.msg.nothing_movable"), ...blocked));
    return BACK;
  }

  const form = new ModalFormData().title(title("enchant_plus.title.transfer"));
  /** @type {boolean[]} */
  const isInput = [];
  form.label(
    rt(tr("enchant_plus.transfer.help", itemName(source), itemName(targetItem)), "\n§7", tr("enchant_plus.price.per_level"), "§r\n", priceText(priceOf(1)))
  );
  isInput.push(false);
  for (const m of movable) {
    form.slider(rt(enchantLine(m.id, m.level), " §7", tr("enchant_plus.transfer.levels")), 0, m.max, { valueStep: 1, defaultValue: m.max });
    isInput.push(true);
  }
  if (blocked.length > 0) {
    form.label(rt("§7", tr("enchant_plus.transfer.blocked"), ...blocked));
    isInput.push(false);
  }
  form.submitButton(tr("enchant_plus.button.review"));
  const res = await present(player, form);
  if (!res || res.canceled || !res.formValues) return CLOSE;
  const values = inputValues(res.formValues, isInput);

  /** @type {Map<string, number>} */
  const sourceTarget = new Map();
  /** @type {Map<string, number>} */
  const targetTarget = new Map();
  let moved = 0;
  movable.forEach((m, i) => {
    const n = Math.max(0, Math.min(m.max, Math.round(Number(values[i] ?? 0))));
    if (n > 0) {
      sourceTarget.set(m.id, m.level - n);
      targetTarget.set(m.id, m.has + n);
      moved += n;
    }
  });
  if (moved === 0) {
    tell(player, tr("enchant_plus.msg.nothing_selected"));
    return BACK;
  }
  const clash = conflictsAmong([...targetLevels.keys(), ...targetTarget.keys()]);
  if (clash.length > 0) {
    tell(player, rt(tr("enchant_plus.msg.conflict"), ...clash.map(([a, b]) => rt("\n§c- ", enchantName(a), " + ", enchantName(b)))));
    return BACK;
  }

  const price = priceOf(moved);
  const summary = rt(
    itemName(source),
    ...[...sourceTarget].map(([id, keep]) => rt("\n§c- §r", changeLine(id, sourceLevels.get(id) ?? 0, keep))),
    "\n\n§r",
    itemName(targetItem),
    ...[...targetTarget].map(([id, to]) => rt("\n§a+ §r", changeLine(id, targetLevels.get(id) ?? 0, to)))
  );
  const answer = await confirm(player, "enchant_plus.title.confirm", summary, price, false);
  if (answer !== "yes") return answer;

  const sourceNow = reread(player, ref, sourceExpected);
  if (!sourceNow) return BACK;
  const targetNow = reread(player, targetRef, targetExpected);
  if (!targetNow) return BACK;
  const sourceResult = build(player, sourceNow, sourceTarget);
  const targetResult = sourceResult && build(player, targetNow, targetTarget);
  if (!sourceResult || !targetResult) return BACK;
  if (!charge(player, price)) {
    tell(player, rt(tr("enchant_plus.msg.cannot_afford"), "\n", priceText(shortfall(player, price))));
    return BACK;
  }
  writeItem(player, ref, sourceResult);
  store(player, targetRef, targetNow, targetResult);
  playAt(table, "random.anvil_use");
  tell(player, tr("enchant_plus.msg.transferred", itemName(sourceResult), itemName(targetResult)));
  return BACK;
}
