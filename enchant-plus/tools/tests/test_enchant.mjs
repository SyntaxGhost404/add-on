// Headless tests for the Enchant+ scripts.
//
// Runs the real behavior-pack scripts in Node against an in-memory mock of the Script API
// (tools/tests/mock) and drives every menu with scripted answers: the table and its orb, enchanting,
// disenchanting, transferring, books, worn armour, prices, refunds, and the fixes for issues #3
// (Swift Sneak missing from leggings) and #7 (Enchant Essence not charged per level).
//
// Usage:  node tools/tests/test_enchant.mjs
import { register } from "node:module";
import assert from "node:assert/strict";

register("./mock/hooks.mjs", import.meta.url);

const mc = await import("@minecraft/server");
const ui = await import("@minecraft/server-ui");
const SCRIPTS = "../../packs/Enchant_Table_BP/scripts";
const { config } = await import(`${SCRIPTS}/config.js`);
await import(`${SCRIPTS}/main.js`);
const { openTable } = await import(`${SCRIPTS}/menu.js`);
const { MARK } = await import(`${SCRIPTS}/ui.js`);
const { ORB, TABLE } = await import(`${SCRIPTS}/table.js`);

const DEFAULTS = structuredClone(config);
const registered = new Map();
mc.system.beforeEvents.startup.fire({
  blockComponentRegistry: { registerCustomComponent: (name, c) => registered.set(name, c) },
  itemComponentRegistry: { registerCustomComponent: () => {} },
});
const component = registered.get("da:enchant_table");
assert.ok(component, "da:enchant_table is registered at startup");

const dim = mc.world.getDimension("minecraft:overworld");
const TABLE_AT = { x: 10, y: 64, z: 10 };
dim.setBlockType(TABLE_AT, TABLE);
const tableBlock = dim.getBlock(TABLE_AT);
const tableRef = { dimension: dim, location: tableBlock.center() };

// --------------------------------------------------------------------------------- helpers
let players = 0;
function fresh({ level = 100, essence = 64 } = {}) {
  Object.assign(config, structuredClone(DEFAULTS));
  ui.ModalFormData.placeholders = true;
  mc.world.scoreboard.objectives.clear();
  dim.sounds.length = 0;
  const p = new mc.Player(`p${++players}`, dim);
  p.level = level;
  if (essence) p.inventory.setItem(35, new mc.ItemStack("da:enchant_essence", essence));
  return p;
}

function stack(typeId, enchants = {}, amount = 1) {
  const s = new mc.ItemStack(typeId, amount);
  for (const [id, level] of Object.entries(enchants)) s.enchants.set(id, level);
  return s;
}

const enchantsOf = (item) => Object.fromEntries(item?.enchants ?? []);
const essenceOf = (p) => p.inventory.slots.filter((s) => s?.typeId === "da:enchant_essence").reduce((n, s) => n + s.amount, 0);
const said = (p, key) => p.messages.some((m) => JSON.stringify(m).includes(key));

/** Answer a modal form by slider label: { "enchantment.damage.all": 5 } sets Sharpness to 5. */
function sliders(byKey) {
  return (form) =>
    form.controls
      .filter((c) => c.type === "slider" || c.type === "toggle")
      .map((c) => {
        const hit = Object.keys(byKey).find((k) => c.text.includes(`"${k}"`));
        return hit === undefined ? null : byKey[hit];
      });
}

/** Button index whose text contains a lang key or text. */
function button(needle) {
  return (form) => {
    const i = form.buttons.findIndex((b) => b.text.includes(needle));
    if (i < 0) throw new Error(`no button with ${needle} in ${form.title}: ${form.buttons.map((b) => b.text).join(" | ")}`);
    return i;
  };
}

async function run(p, answers) {
  p.answers = answers;
  await openTable(p, tableRef);
  assert.equal(p.answers.length, 0, `unused answers: ${p.answers.length}`);
}

const tests = [];
const test = (name, fn) => tests.push({ name, fn });

// ----------------------------------------------------------------------------------- tests
test("orb: placed with the table, kept single, removed with it, orphans swept", async () => {
  for (const e of dim.getEntities({ type: ORB })) e.remove();
  component.onPlace({ block: tableBlock, dimension: dim });
  assert.equal(dim.getEntities({ type: ORB }).length, 1);
  component.onTick({ block: tableBlock, dimension: dim });
  assert.equal(dim.getEntities({ type: ORB }).length, 1, "tick does not add a second orb");
  dim.spawnEntity(ORB, { x: 10.45, y: 64.8, z: 10.47 }); // where version 1.0.5 put its orb
  component.onTick({ block: tableBlock, dimension: dim });
  assert.equal(dim.getEntities({ type: ORB }).length, 1, "duplicates (old orbs) are removed");
  for (const e of dim.getEntities({ type: ORB })) e.remove();
  const old = dim.spawnEntity(ORB, { x: 10.45, y: 64.8, z: 10.47 });
  component.onTick({ block: tableBlock, dimension: dim });
  assert.ok(old.isValid && Math.abs(old.location.x - 10.46875) < 1e-9 && Math.abs(old.location.z - 10.53125) < 1e-9, "an old orb is re-centred");
  for (const e of dim.getEntities({ type: ORB })) e.remove();
  component.onTick({ block: tableBlock, dimension: dim });
  assert.equal(dim.getEntities({ type: ORB }).length, 1, "a missing orb comes back");

  const other = { x: 20, y: 64, z: 20 };
  dim.setBlockType(other, TABLE);
  component.onPlace({ block: dim.getBlock(other), dimension: dim });
  dim.setBlockType(other, "minecraft:air");
  component.onBreak({ block: dim.getBlock(other), dimension: dim });
  assert.equal(dim.getEntities({ type: ORB }).length, 1, "breaking a table removes its orb only");

  dim.spawnEntity(ORB, { x: 30.47, y: 70.8, z: 30.53 }); // a table removed by /setblock
  await mc.advance(200);
  assert.equal(dim.getEntities({ type: ORB }).length, 1, "the sweep clears orbs without a table");

  config.orb = false;
  component.onTick({ block: tableBlock, dimension: dim });
  assert.equal(dim.getEntities({ type: ORB }).length, 0, "orbs can be switched off");
  config.orb = true;
  component.onTick({ block: tableBlock, dimension: dim });
});

test("interacting with the table opens the themed menu", async () => {
  const p = fresh();
  p.inventory.setItem(0, stack("minecraft:iron_sword"));
  p.answers = ["close"];
  component.onPlayerInteract({ block: tableBlock, dimension: dim, player: p });
  await mc.advance(3);
  assert.equal(p.formsShown.length, 1);
  assert.ok(p.formsShown[0].title.includes(MARK), "title carries the theme marker");
  assert.ok(p.formsShown[0].title.includes("enchant_plus.title.home"));
  assert.equal(p.formsShown[0].buttons[0].icon, "textures/items/iron_sword");
});

test("enchanting charges XP and essence per level (issue #7)", async () => {
  const p = fresh();
  p.inventory.setItem(0, stack("minecraft:iron_sword"));
  await run(p, [
    0,
    button("enchant_plus.button.enchant"),
    sliders({ "enchantment.damage.all": 5, "enchantment.durability": 3 }),
    button("enchant_plus.button.confirm"),
    "close",
  ]);
  assert.deepEqual(enchantsOf(p.inventory.slots[0]), { sharpness: 5, unbreaking: 3 });
  assert.equal(p.level, 100 - 3 * 8);
  assert.equal(essenceOf(p), 64 - 3 * 8, "essence scales with the 8 levels added");
  assert.ok(dim.sounds.includes("block.enchanting_table.use"));
  assert.ok(said(p, "enchant_plus.msg.enchanted"));
});

test("raising an existing enchantment only charges the added levels", async () => {
  const p = fresh();
  p.inventory.setItem(0, stack("minecraft:iron_sword", { sharpness: 3 }));
  await run(p, [0, button("enchant_plus.button.enchant"), sliders({ "enchantment.damage.all": 5 }), 0, "close"]);
  assert.deepEqual(enchantsOf(p.inventory.slots[0]), { sharpness: 5 });
  assert.equal(p.level, 100 - 6);
  assert.equal(essenceOf(p), 64 - 6);
});

test("Swift Sneak is offered for leggings and applied (issue #3)", async () => {
  const p = fresh();
  p.inventory.setItem(0, stack("minecraft:iron_leggings"));
  let offered = false;
  await run(p, [
    0,
    button("enchant_plus.button.enchant"),
    (form) => {
      offered = form.controls.some((c) => c.text.includes("enchantment.swift_sneak"));
      return sliders({ "enchantment.swift_sneak": 3 })(form);
    },
    0,
    "close",
  ]);
  assert.ok(offered, "the leggings menu lists Swift Sneak");
  assert.deepEqual(enchantsOf(p.inventory.slots[0]), { swift_sneak: 3 });
});

test("conflicting choices are refused without charging", async () => {
  const p = fresh();
  p.inventory.setItem(0, stack("minecraft:iron_sword"));
  await run(p, [0, button("enchant_plus.button.enchant"), sliders({ "enchantment.damage.all": 2, "enchantment.damage.undead": 2 }), "close"]);
  assert.deepEqual(enchantsOf(p.inventory.slots[0]), {});
  assert.equal(p.level, 100);
  assert.ok(said(p, "enchant_plus.msg.conflict"));
});

test("an enchantment that conflicts with one already on the item is listed as unavailable", async () => {
  const p = fresh();
  p.inventory.setItem(0, stack("minecraft:iron_sword", { smite: 1 }));
  let blocked = false;
  let offered = true;
  await run(p, [
    0,
    button("enchant_plus.button.enchant"),
    (form) => {
      offered = form.controls.some((c) => c.type === "slider" && c.text.includes("enchantment.damage.all"));
      blocked = form.controls.some((c) => c.type === "label" && c.text.includes("enchant_plus.enchant.blocked"));
      return "close";
    },
  ]);
  assert.ok(!offered && blocked);
});

test("a player who cannot pay is told what is missing and nothing changes", async () => {
  const p = fresh({ level: 2, essence: 0 });
  p.inventory.setItem(0, stack("minecraft:iron_sword"));
  let warned = false;
  await run(p, [
    0,
    button("enchant_plus.button.enchant"),
    sliders({ "enchantment.damage.all": 5 }),
    (form) => {
      warned = form.body.includes("enchant_plus.confirm.missing");
      return 0;
    },
    "close",
  ]);
  assert.ok(warned, "the summary shows the shortfall");
  assert.ok(said(p, "enchant_plus.msg.cannot_afford"));
  assert.deepEqual(enchantsOf(p.inventory.slots[0]), {});
  assert.equal(p.level, 2);
});

test("Creative players enchant for free", async () => {
  const p = fresh({ level: 0, essence: 0 });
  p.gameMode = mc.GameMode.Creative;
  p.inventory.setItem(0, stack("minecraft:iron_sword"));
  await run(p, [0, button("enchant_plus.button.enchant"), sliders({ "enchantment.damage.all": 5 }), 0, "close"]);
  assert.deepEqual(enchantsOf(p.inventory.slots[0]), { sharpness: 5 });
});

test("a book from a stack becomes an enchanted book; the rest stay", async () => {
  const p = fresh();
  p.inventory.setItem(0, stack("minecraft:book", {}, 3));
  await run(p, [0, button("enchant_plus.button.enchant"), sliders({ "enchantment.mending": 1 }), 0, "close"]);
  assert.equal(p.inventory.slots[0].typeId, "minecraft:book");
  assert.equal(p.inventory.slots[0].amount, 2);
  const book = p.inventory.slots.find((s) => s?.typeId === "minecraft:enchanted_book");
  assert.deepEqual(enchantsOf(book), { mending: 1 });
});

test("worn armour is listed and enchanted in place", async () => {
  const p = fresh();
  p.worn.set(mc.EquipmentSlot.Chest, stack("minecraft:diamond_chestplate"));
  await run(p, [0, button("enchant_plus.button.enchant"), sliders({ "enchantment.protect.all": 4 }), 0, "close"]);
  assert.deepEqual(enchantsOf(p.worn.get(mc.EquipmentSlot.Chest)), { protection: 4 });
});

test("removing all enchantments refunds half the XP", async () => {
  const p = fresh({ level: 0 });
  p.inventory.setItem(0, stack("minecraft:iron_sword", { sharpness: 5, unbreaking: 3 }));
  await run(p, [0, button("enchant_plus.button.disenchant"), 0, 0, "close"]);
  assert.deepEqual(enchantsOf(p.inventory.slots[0]), {});
  assert.equal(p.level, Math.floor(3 * 8 * 0.5));
  assert.ok(dim.sounds.includes("block.grindstone.use"));
});

test("removing some levels keeps the rest", async () => {
  const p = fresh({ level: 0 });
  p.inventory.setItem(0, stack("minecraft:iron_sword", { sharpness: 5, unbreaking: 3 }));
  await run(p, [0, button("enchant_plus.button.disenchant"), 1, sliders({ "enchantment.damage.all": 2 }), 0, "close"]);
  assert.deepEqual(enchantsOf(p.inventory.slots[0]), { sharpness: 2, unbreaking: 3 });
  assert.equal(p.level, Math.floor(3 * 3 * 0.5));
});

test("an emptied enchanted book turns back into a book", async () => {
  const p = fresh();
  p.inventory.setItem(0, stack("minecraft:enchanted_book", { mending: 1 }));
  await run(p, [0, button("enchant_plus.button.disenchant"), 0, 0, "close"]);
  assert.equal(p.inventory.slots[0].typeId, "minecraft:book");
});

test("transferring moves levels and charges per level moved (issue #7)", async () => {
  const p = fresh();
  p.inventory.setItem(0, stack("minecraft:iron_sword", { sharpness: 5, unbreaking: 3 }));
  p.inventory.setItem(1, stack("minecraft:iron_axe"));
  await run(p, [0, button("enchant_plus.button.transfer"), 0, sliders({}), 0, "close"]);
  assert.deepEqual(enchantsOf(p.inventory.slots[0]), {});
  assert.deepEqual(enchantsOf(p.inventory.slots[1]), { sharpness: 5, unbreaking: 3 });
  assert.equal(p.level, 100 - 3 * 8);
  assert.equal(essenceOf(p), 64 - 3 * 8);
});

test("transfer skips what the target cannot take", async () => {
  const p = fresh();
  p.inventory.setItem(0, stack("minecraft:enchanted_book", { power: 3, unbreaking: 2 }));
  p.inventory.setItem(1, stack("minecraft:iron_sword"));
  let blocked = false;
  await run(p, [
    0,
    button("enchant_plus.button.transfer"),
    0,
    (form) => {
      blocked = form.controls.some((c) => c.type === "label" && c.text.includes("enchant_plus.transfer.not_accepted"));
      return sliders({})(form);
    },
    0,
    "close",
  ]);
  assert.ok(blocked, "Power is listed as not accepted by a sword");
  assert.deepEqual(enchantsOf(p.inventory.slots[1]), { unbreaking: 2 });
  assert.deepEqual(enchantsOf(p.inventory.slots[0]), { power: 3 });
});

test("an item changed while the menu is open cancels the operation", async () => {
  const p = fresh();
  p.inventory.setItem(0, stack("minecraft:iron_sword"));
  await run(p, [
    0,
    button("enchant_plus.button.enchant"),
    sliders({ "enchantment.damage.all": 5 }),
    (form, player) => {
      player.inventory.setItem(0, stack("minecraft:iron_sword", { smite: 1 }));
      return 0;
    },
    "close",
  ]);
  assert.ok(said(p, "enchant_plus.msg.changed"));
  assert.deepEqual(enchantsOf(p.inventory.slots[0]), { smite: 1 });
  assert.equal(p.level, 100);
});

test("a busy player gets the form again", async () => {
  const p = fresh();
  p.inventory.setItem(0, stack("minecraft:iron_sword"));
  await run(p, ["busy", "busy", "close"]);
  assert.equal(p.formsShown.length, 3);
});

test("modal answers work with and without label placeholders", async () => {
  const p = fresh();
  ui.ModalFormData.placeholders = false;
  p.inventory.setItem(0, stack("minecraft:iron_sword"));
  await run(p, [0, button("enchant_plus.button.enchant"), sliders({ "enchantment.durability": 2 }), 0, "close"]);
  assert.deepEqual(enchantsOf(p.inventory.slots[0]), { unbreaking: 2 });
});

test("plain vanilla forms when the theme is off", async () => {
  const p = fresh();
  config.themedForms = false;
  p.inventory.setItem(0, stack("minecraft:iron_sword"));
  await run(p, ["close"]);
  assert.ok(!p.formsShown[0].title.includes(MARK));
});

test("a scoreboard currency is created and charged", async () => {
  const p = fresh();
  config.score.enabled = true;
  config.xp.enabled = false;
  config.essence.enabled = false;
  p.inventory.setItem(0, stack("minecraft:iron_sword"));
  mc.world.scoreboard.addObjective("money", "Money").setScore(p, 100);
  await run(p, [0, button("enchant_plus.button.enchant"), sliders({ "enchantment.durability": 2 }), 0, "close"]);
  assert.equal(mc.world.scoreboard.getObjective("money").getScore(p), 80);
  assert.equal(p.level, 100);
});

test("nothing to add on a fully enchanted item", async () => {
  const p = fresh();
  p.inventory.setItem(0, stack("minecraft:iron_sword", { sharpness: 5, knockback: 2, fire_aspect: 2, looting: 3, unbreaking: 3, mending: 1, vanishing: 1 }));
  await run(p, [0, button("enchant_plus.button.enchant"), "close"]);
  assert.ok(said(p, "enchant_plus.msg.nothing_to_add"));
});

test("no enchantable items: a message instead of an empty menu", async () => {
  const p = fresh({ essence: 0 });
  p.inventory.setItem(0, stack("minecraft:dirt", {}, 10));
  await run(p, []);
  assert.ok(said(p, "enchant_plus.msg.no_items"));
});

// ------------------------------------------------------------------------------------- run
let failed = 0;
for (const t of tests) {
  try {
    await t.fn();
    console.log(`ok    ${t.name}`);
  } catch (e) {
    failed++;
    console.log(`FAIL  ${t.name}\n      ${e.stack ?? e}`);
  }
}
console.log(`\n${tests.length - failed}/${tests.length} passed`);
process.exit(failed ? 1 : 0);
