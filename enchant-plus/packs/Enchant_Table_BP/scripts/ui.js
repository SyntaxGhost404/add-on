/**
 * Form and text helpers. All player-facing text is raw text with lang keys (texts/*.lang in the
 * resource pack), so the menus follow the player's language.
 */
import { system } from "@minecraft/server";
import { FormCancelationReason } from "@minecraft/server-ui";
import { config } from "./config.js";
import { enchantName, levelText } from "./rules.js";

/** @typedef {import("@minecraft/server").Player} Player */
/** @typedef {import("@minecraft/server").RawMessage} RawMessage */
/** @typedef {import("@minecraft/server").ItemStack} ItemStack */
/** @typedef {RawMessage | string} Part */

/**
 * Prefix that ui/server_form.json looks for to draw a form in the Enchant+ window. It is made of
 * formatting codes only, so it never shows, and plain vanilla forms are used when it is absent.
 */
export const MARK = "§d§a§e§p§r";

/** Raw text from parts (strings are literal text). @param {...Part} parts @returns {RawMessage} */
export function rt(...parts) {
  return { rawtext: parts.map((p) => (typeof p === "string" ? { text: p } : p)) };
}

/** A translated lang key with arguments. @param {string} key @param {...Part} args @returns {RawMessage} */
export function tr(key, ...args) {
  if (args.length === 0) return { translate: key };
  if (args.every((a) => typeof a === "string")) return { translate: key, with: /** @type {string[]} */ (args) };
  return { translate: key, with: rt(...args) };
}

/** Form title for a lang key. @param {string} key */
export function title(key) {
  return rt(config.themedForms ? MARK : "", tr(key));
}

/** @param {ItemStack} item @returns {RawMessage} */
export function itemName(item) {
  return item.nameTag ? { text: item.nameTag } : { translate: item.localizationKey };
}

/** "Sharpness IV". @param {string} id @param {number} level */
export function enchantLine(id, level) {
  return rt(enchantName(id), " ", levelText(level));
}

/** Chat message with the Enchant+ prefix. @param {Player} player @param {Part} text */
export function tell(player, text) {
  player.sendMessage(rt("§d[Enchant+]§r ", text));
}

/**
 * Show a form and wait for the answer. While the player is busy (chat open, another screen still
 * closing) the game cancels the form, so it is shown again a moment later. Returns undefined if the
 * player leaves or stays busy for ten seconds.
 * @template {{ show(player: Player): Promise<any> }} F
 * @param {Player} player
 * @param {F} form
 * @returns {Promise<Awaited<ReturnType<F["show"]>> | undefined>}
 */
export async function present(player, form) {
  for (let attempt = 0; attempt < 40; attempt++) {
    if (!player.isValid) return undefined;
    const res = await form.show(player);
    if (!res.canceled || res.cancelationReason !== FormCancelationReason.UserBusy) return res;
    await system.waitTicks(5);
  }
  return undefined;
}

/**
 * Values a modal form returned for its input controls only. Labels, headers and dividers may or may
 * not have a placeholder in formValues, so both layouts are accepted.
 * @param {(boolean | number | string | undefined)[]} values all values the form returned
 * @param {boolean[]} isInput for every control added, whether it is an input (slider, toggle...)
 * @returns {(boolean | number | string | undefined)[]}
 */
export function inputValues(values, isInput) {
  if (values.length === isInput.length) return values.filter((_, i) => isInput[i]);
  return values;
}
