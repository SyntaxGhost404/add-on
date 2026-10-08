// @ts-check
// The Codex of the Unnamed: a book UI showing deciphered chapters, a field guide,
// a bestiary that fills in as you learn, and personal discovery statistics.
import { system } from "@minecraft/server";
import { ActionFormData, FormCancelationReason } from "@minecraft/server-ui";
import { CHAPTERS, FIELD_GUIDE, BESTIARY, nextHint } from "./lore.js";
import { getProgress, syncInventoryFlags, CHAPTER_COUNT } from "./progress.js";

/** @typedef {import("@minecraft/server").Player} Player */
/** @typedef {import("@minecraft/server-ui").ActionFormResponse} ActionFormResponse */
/** @typedef {import("./progress.js").Progress} Progress */

const TABLET_ICON = "textures/rotu/items/inscribed_tablet";
const LOCKED_ICON = "textures/rotu/items/glyph_shard";
const CODEX_ICON = "textures/rotu/items/codex";

/** Players with an open codex (prevents stacking forms). @type {Set<string>} */
const reading = new Set();

/**
 * Show a form. If the player is busy (chat or another screen open) retry for a few seconds.
 * @param {Player} player @param {ActionFormData} form
 * @returns {Promise<ActionFormResponse | undefined>}
 */
async function present(player, form) {
  for (let attempt = 0; attempt < 8; attempt++) {
    if (!player.isValid) return undefined;
    const res = await form.show(player);
    if (!res.canceled || res.cancelationReason !== FormCancelationReason.UserBusy) return res;
    await system.waitTicks(10);
  }
  return undefined;
}

/** @param {ActionFormResponse | undefined} res */
const picked = (res) => (res && !res.canceled && res.selection !== undefined ? res.selection : -1);

/** @param {boolean} on @param {string} name */
const mark = (on, name) => (on ? `§a${name}§r` : `§8${name}§r`);

/** Roman numeral prefix of a chapter title ("IV. The Choir" -> "IV"). @param {string} title */
const numeral = (title) => title.split(".")[0];

/** @param {Progress} p */
function summary(p) {
  const f = p.flags;
  const lines = [
    `§7Chapters deciphered: §f${p.chapters.length}/${CHAPTER_COUNT}`,
    `§7Sigil shards: ${mark(!!f.lantern, "Lantern")}  ${mark(!!f.bone, "Bone")}  ${mark(!!f.hush, "Hush")}`,
  ];
  if (f.key) lines.push("§dThe Sigil Key is whole.");
  if (f.cantor) lines.push("§bThe Last Cantor is silent.");
  lines.push("", `§6Next step:§r ${nextHint(p)}`);
  return lines.join("\n");
}

/**
 * A single page of text with a Back button.
 * @param {Player} player @param {string} title @param {string} text
 * @returns {Promise<boolean>} true = go back, false = close the codex
 */
async function readPage(player, title, text) {
  const res = await present(player, new ActionFormData().title(title).body(text).button("Back"));
  return picked(res) === 0;
}

/** @param {Player} player @returns {Promise<boolean>} */
async function chapterList(player) {
  for (;;) {
    const p = getProgress(player);
    const form = new ActionFormData()
      .title("Chapters")
      .body(
        `${p.chapters.length} of ${CHAPTER_COUNT} chapters deciphered.\n` +
          "Read Inscribed Tablets at a Scriptorium Desk to reveal the next chapter."
      );
    CHAPTERS.forEach((c, i) => {
      const known = p.chapters.includes(i + 1);
      form.button(known ? c.title : `§8${numeral(c.title)}. ???`, known ? TABLET_ICON : LOCKED_ICON);
    });
    form.button("Back");
    const sel = picked(await present(player, form));
    if (sel < 0) return false;
    if (sel >= CHAPTERS.length) return true;
    const chapter = CHAPTERS[sel];
    const text = p.chapters.includes(sel + 1)
      ? chapter.text
      : sel + 1 === CHAPTER_COUNT
        ? "§8This chapter is not written on any tablet. It will be written when the last note ends."
        : "§8You have not deciphered this tablet yet.";
    if (!(await readPage(player, chapter.title, text))) return false;
  }
}

/** @param {Player} player @returns {Promise<boolean>} */
async function fieldGuide(player) {
  for (;;) {
    const form = new ActionFormData().title("Field Guide").body("Notes on the ruins, their tools and their mechanisms.");
    for (const g of FIELD_GUIDE) form.button(g.title, g.icon);
    form.button("Back");
    const sel = picked(await present(player, form));
    if (sel < 0) return false;
    if (sel >= FIELD_GUIDE.length) return true;
    if (!(await readPage(player, FIELD_GUIDE[sel].title, FIELD_GUIDE[sel].text))) return false;
  }
}

/** @param {Progress} p @param {(typeof BESTIARY)[number]} b */
function knowsCreature(p, b) {
  return p.chapters.includes(b.chapter) || (p.stats[b.stat] || 0) > 0 || (b.stat === "cantor" && !!p.flags.cantor);
}

/** @param {Player} player @returns {Promise<boolean>} */
async function bestiary(player) {
  for (;;) {
    const p = getProgress(player);
    const form = new ActionFormData()
      .title("Bestiary")
      .body("Entries are filled in as you decipher the tablets or defeat the creatures yourself.");
    for (const b of BESTIARY) {
      const known = knowsCreature(p, b);
      form.button(known ? b.name : "§8???", known ? b.icon : LOCKED_ICON);
    }
    form.button("Back");
    const sel = picked(await present(player, form));
    if (sel < 0) return false;
    if (sel >= BESTIARY.length) return true;
    const b = BESTIARY[sel];
    const known = knowsCreature(p, b);
    const kills = p.stats[b.stat] || 0;
    const text = known
      ? `${b.text}\n\n§7Defeated: §f${kills}`
      : "§8Nothing is known about this creature yet. Keep deciphering tablets.";
    if (!(await readPage(player, known ? b.name : "???", text))) return false;
  }
}

/** @param {Player} player @returns {Promise<boolean>} */
async function discoveries(player) {
  const p = getProgress(player);
  const s = (/** @type {string} */ k) => `§f${p.stats[k] || 0}§r`;
  const text = [
    `§7Tablets deciphered: ${s("tablets")}`,
    `§7Reliquaries opened: ${s("reliquaries")}`,
    `§7Gates unsealed: ${s("gates")}`,
    `§7Hidden passages revealed: ${s("veils")}`,
    `§7Sealed urns broken: ${s("urns")}`,
    `§7Hushwalkers laid to rest: ${s("hushwalkers")}`,
    `§7Murmurs silenced: ${s("murmurs")}`,
    `§7Graven Sentinels felled: ${s("sentinels")}`,
    `§7The Last Cantor: ${p.flags.cantor ? "§bsilenced" : "§8still singing"}`,
  ].join("\n");
  return readPage(player, "Discoveries", text);
}

/** Open the Codex main page. @param {Player} player */
export async function openCodex(player) {
  if (reading.has(player.id)) return;
  reading.add(player.id);
  try {
    syncInventoryFlags(player);
    for (;;) {
      const form = new ActionFormData()
        .title("Codex of the Unnamed")
        .body(summary(getProgress(player)))
        .button("Chapters", TABLET_ICON)
        .button("Field Guide", "textures/items/brush")
        .button("Bestiary", "textures/rotu/items/murmur_essence")
        .button("Discoveries", CODEX_ICON)
        .button("Close");
      const sel = picked(await present(player, form));
      let back = false;
      if (sel === 0) back = await chapterList(player);
      else if (sel === 1) back = await fieldGuide(player);
      else if (sel === 2) back = await bestiary(player);
      else if (sel === 3) back = await discoveries(player);
      if (!back) return;
    }
  } catch (e) {
    console.warn(`[rotu] codex: ${e}`);
  } finally {
    reading.delete(player.id);
  }
}

/**
 * Show a freshly deciphered chapter.
 * @param {Player} player @param {number} chapter 1-based
 */
export async function showChapter(player, chapter) {
  const c = CHAPTERS[chapter - 1];
  if (!c || reading.has(player.id)) return;
  reading.add(player.id);
  try {
    const res = await present(
      player,
      new ActionFormData().title(c.title).body(c.text).button("Open the Codex", CODEX_ICON).button("Close")
    );
    reading.delete(player.id);
    if (picked(res) === 0) await openCodex(player);
  } catch (e) {
    console.warn(`[rotu] chapter: ${e}`);
  } finally {
    reading.delete(player.id);
  }
}
