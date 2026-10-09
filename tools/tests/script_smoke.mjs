// Headless smoke test for the add-on scripts.
//
// Runs scripts/main.js in Node against an in-memory mock of the Minecraft Script API
// (tools/tests/mock), using the block, entity and loot definitions from the built behavior
// pack, and drives every gameplay mechanic end to end: puzzles, traps, reliquaries,
// the scriptorium, spawn markers, tools, relics, the boss fight and the codex UI.
//
// Usage:  python3 tools/build.py --no-dist && node tools/tests/script_smoke.mjs
import { register } from "node:module";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

register("./mock/hooks.mjs", import.meta.url);

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "..");
const BP = path.join(ROOT, "packs", "ruins_of_the_unnamed_bp");

const mc = await import("@minecraft/server");
const { state, advance, world, ItemStack, Player, Entity, Difficulty, GameMode, EquipmentSlot } = mc;

// ------------------------------------------------------------------ load pack definitions
const TRAIT_STATES = {
  "minecraft:block_face": ["down", "up", "north", "south", "west", "east"],
  "minecraft:cardinal_direction": ["south", "west", "north", "east"],
  "minecraft:facing_direction": ["down", "up", "north", "south", "west", "east"],
};
const blockCustom = new Map(); // id -> { componentName: params }
for (const f of fs.readdirSync(path.join(BP, "blocks"))) {
  const body = JSON.parse(fs.readFileSync(path.join(BP, "blocks", f), "utf8"))["minecraft:block"];
  const id = body.description.identifier;
  const allowed = { ...(body.description.states || {}) };
  for (const trait of Object.values(body.description.traits || {})) {
    for (const s of trait.enabled_states || []) allowed[s] = TRAIT_STATES[s];
  }
  const defaults = Object.fromEntries(Object.entries(allowed).map(([k, v]) => [k, v[0]]));
  state.blockDefs.set(id, { states: defaults, allowed, tags: body.components["minecraft:tags"] || [] });
  blockCustom.set(id, Object.fromEntries(Object.entries(body.components).filter(([k]) => !k.startsWith("minecraft:"))));
}
const itemCustom = new Map();
for (const f of fs.readdirSync(path.join(BP, "items"))) {
  const body = JSON.parse(fs.readFileSync(path.join(BP, "items", f), "utf8"))["minecraft:item"];
  itemCustom.set(
    body.description.identifier,
    Object.fromEntries(Object.entries(body.components).filter(([k]) => !k.startsWith("minecraft:")))
  );
}
for (const f of fs.readdirSync(path.join(BP, "entities"))) {
  const body = JSON.parse(fs.readFileSync(path.join(BP, "entities", f), "utf8"))["minecraft:entity"];
  state.families.set(body.description.identifier, body.components["minecraft:type_family"]?.family || []);
}
(function walk(dir) {
  for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, f.name);
    if (f.isDirectory()) walk(p);
    else state.lootTables.add(path.relative(path.join(BP, "loot_tables"), p).replace(/\\/g, "/").replace(/\.json$/, ""));
  }
})(path.join(BP, "loot_tables"));

// guard() swallows exceptions and logs them; any such log is a test failure
const warnings = [];
console.warn = (...a) => warnings.push(a.join(" "));

// ------------------------------------------------------------------ load the add-on
await import(path.join(ROOT, "scripts", "main.js"));
const { getProgress } = await import(path.join(ROOT, "scripts", "progress.js"));
const blockComps = new Map();
const itemComps = new Map();
mc.system.beforeEvents.startup.fire({
  blockComponentRegistry: { registerCustomComponent: (n, c) => blockComps.set(n, c) },
  itemComponentRegistry: { registerCustomComponent: (n, c) => itemComps.set(n, c) },
});
for (const [id, comps] of [...blockCustom, ...itemCustom]) {
  for (const name of Object.keys(comps)) assert.ok(blockComps.has(name) || itemComps.has(name), `${id}: ${name} not registered`);
}

const overworld = world.getDimension("overworld");

function blockEvent(kind, loc, extra = {}) {
  const block = overworld.getBlock(loc);
  const comps = blockCustom.get(extra.typeOverride || block.typeId) || {};
  for (const [name, params] of Object.entries(comps)) {
    const handler = blockComps.get(name)?.[kind];
    if (handler) handler({ block, dimension: overworld, ...extra }, { params });
  }
}
function itemEvent(kind, typeId, event) {
  for (const [name, params] of Object.entries(itemCustom.get(typeId) || {})) {
    const handler = itemComps.get(name)?.[kind];
    if (handler) handler(event, { params });
  }
}
function newPlayer(name, loc) {
  const p = new Player(name, overworld, loc);
  state.players.push(p);
  return p;
}
const count = (p, typeId) => p.inventory.slots.reduce((n, s) => n + (s && s.typeId === typeId ? s.amount : 0), 0);
const blocksOf = (typeId) => [...overworld.blocks.values()].filter((b) => b.type === typeId).length;
const last = (arr) => arr[arr.length - 1] || "";

let passed = 0;
async function scenario(name, fn) {
  await fn();
  passed++;
  console.log(`  ok  ${name}`);
}

// ------------------------------------------------------------------ scenarios
await scenario("glyph dials dissolve the sealed gate only when all three match", async () => {
  for (const x of [9, 10, 11]) for (const y of [1, 2, 3]) overworld.setBlock({ x, y, z: 15 }, "rotu:sealed_gate");
  const dials = [
    [{ x: 8, y: 1, z: 18 }, 0, 1],
    [{ x: 10, y: 1, z: 18 }, 1, 2],
    [{ x: 12, y: 1, z: 18 }, 2, 3],
  ];
  for (const [loc, sol, start] of dials) overworld.setBlock(loc, "rotu:glyph_dial", { "rotu:glyph": start, "rotu:solution": sol });
  const p = newPlayer("Dialer", { x: 10, y: 1, z: 21 });
  for (const [i, [loc, sol]] of dials.entries()) {
    while (overworld.raw(loc).states["rotu:glyph"] !== sol) {
      if (i < 2) assert.equal(blocksOf("rotu:sealed_gate"), 9, "gate opened early");
      blockEvent("onPlayerInteract", loc, { player: p });
      await advance(5);
    }
  }
  await advance(30);
  assert.equal(blocksOf("rotu:sealed_gate"), 0);
  assert.equal(getProgress(p).stats.gates, 1);
  assert.match(last(p.actionbar), /dissolves/);
});

await scenario("cipher stones describe their glyph; a glyph shard recarves them", async () => {
  const loc = { x: 20, y: 5, z: 15 };
  overworld.setBlock(loc, "rotu:cipher_stone", { "rotu:glyph": 1 });
  const p = newPlayer("Reader", { x: 20, y: 5, z: 17 });
  blockEvent("onPlayerInteract", loc, { player: p });
  assert.match(last(p.actionbar), /Eye glyph/);
  p.hold(new ItemStack("rotu:glyph_shard", 1));
  blockEvent("onPlayerInteract", loc, { player: p });
  assert.equal(overworld.raw(loc).states["rotu:glyph"], 2);
  overworld.setBlock({ x: 21, y: 5, z: 15 }, "rotu:glyph_mural", { "rotu:panel": 3 });
  p.hold(undefined);
  blockEvent("onPlayerInteract", { x: 21, y: 5, z: 15 }, { player: p });
  assert.match(last(p.actionbar), /dissolving/);
});

await scenario("lesser reliquary: key consumed, loot ejected once per player", async () => {
  const loc = { x: 1000, y: 64, z: 0 };
  overworld.setBlock(loc, "rotu:reliquary", { "rotu:tier": "lesser" });
  const a = newPlayer("Alpha", { x: 1001, y: 64, z: 1 }).hold(new ItemStack("rotu:reliquary_key", 2));
  const items = () => overworld.entities.filter((e) => e.typeId === "minecraft:item").length;
  const before = items();
  blockEvent("onPlayerInteract", loc, { player: a });
  assert.equal(count(a, "rotu:reliquary_key"), 1);
  await advance(80);
  assert.equal(items() - before, 2, "loot ejected");
  await advance(15);
  blockEvent("onPlayerInteract", loc, { player: a });
  assert.equal(count(a, "rotu:reliquary_key"), 1, "second claim must not consume a key");
  assert.match(last(a.actionbar), /already rewarded/);
  const b = newPlayer("Beta", { x: 999, y: 64, z: 1 }).hold(new ItemStack("rotu:reliquary_key", 1));
  blockEvent("onPlayerInteract", loc, { player: b });
  assert.equal(count(b, "rotu:reliquary_key"), 0, "another player can still claim");
  assert.equal(getProgress(a).stats.reliquaries, 1);
  const grand = { x: 1003, y: 64, z: 0 };
  overworld.setBlock(grand, "rotu:reliquary", { "rotu:tier": "grand" });
  await advance(15);
  blockEvent("onPlayerInteract", grand, { player: a });
  assert.match(last(a.actionbar), /Cantor's Seal/);
  assert.equal(count(a, "rotu:reliquary_key"), 1);
});

await scenario("scriptorium reveals chapters 1-11 in order, then breaks tablets into shards", async () => {
  const loc = { x: 1500, y: 64, z: 0 };
  overworld.setBlock(loc, "rotu:scriptorium_desk");
  const p = newPlayer("Scribe", { x: 1500, y: 64, z: 2 }).hold(new ItemStack("rotu:inscribed_tablet", 12));
  for (let i = 0; i < 12; i++) {
    blockEvent("onPlayerInteract", loc, { player: p });
    await advance(30);
  }
  assert.deepEqual(getProgress(p).chapters, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
  assert.equal(count(p, "rotu:inscribed_tablet"), 0);
  assert.ok(count(p, "rotu:glyph_shard") >= 2, "last tablet became shards");
  assert.ok(p.formsShown.some((f) => f.title.startsWith("I. ")), "chapter page shown");
});

await scenario("hushing plate: springs on walkers, spares sneakers, recharges", async () => {
  const loc = { x: 2000, y: 64, z: 0 };
  overworld.setBlock(loc, "rotu:hushing_plate");
  const sneak = newPlayer("Sneak", { x: 2000, y: 64.1, z: 0 });
  sneak.isSneaking = true;
  blockEvent("onStepOn", loc, { entity: sneak });
  assert.equal(sneak.getEffect("darkness"), undefined);
  assert.equal(overworld.raw(loc).states["rotu:spent"], false);
  const walker = newPlayer("Walker", { x: 2000, y: 64.1, z: 0 });
  blockEvent("onStepOn", loc, { entity: walker });
  assert.ok(walker.getEffect("darkness"));
  assert.equal(overworld.raw(loc).states["rotu:spent"], true);
  blockEvent("onTick", loc);
  assert.equal(overworld.raw(loc).states["rotu:spent"], true, "no instant recharge");
  await advance(205);
  blockEvent("onTick", loc);
  assert.equal(overworld.raw(loc).states["rotu:spent"], false);
  const robed = newPlayer("Robed", { x: 2000, y: 64.1, z: 0 });
  robed.armor[EquipmentSlot.Chest] = new ItemStack("rotu:hushweave_mantle");
  blockEvent("onStepOn", loc, { entity: robed });
  assert.equal(robed.getEffect("darkness"), undefined, "mantle muffles the plate");
});

await scenario("spawn markers wake their inhabitants only when a player is near", async () => {
  const loc = { x: 3000, y: 64, z: 0 };
  overworld.setBlock(loc, "rotu:spawn_marker", { "rotu:mob": "hushwalkers" });
  const far = newPlayer("Far", { x: 3050, y: 64, z: 0 });
  blockEvent("onTick", loc);
  assert.equal(overworld.raw(loc).type, "rotu:spawn_marker");
  far.teleport({ x: 3005, y: 64, z: 0 });
  state.difficulty = Difficulty.Peaceful;
  blockEvent("onTick", loc);
  assert.equal(overworld.raw(loc).type, "rotu:spawn_marker", "peaceful keeps the marker");
  state.difficulty = Difficulty.Normal;
  blockEvent("onTick", loc);
  assert.equal(overworld.raw(loc).type, "minecraft:air");
  assert.equal(overworld.getEntities({ type: "rotu:hushwalker" }).length, 2);
});

await scenario("diviner's lens reveals veilstone and wears down", async () => {
  const p = newPlayer("Seer", { x: 4000, y: 64, z: 0 });
  const lens = new ItemStack("rotu:diviners_lens").withDurability(250);
  p.hold(lens);
  overworld.setBlock({ x: 4003, y: 64, z: 0 }, "rotu:veilstone");
  overworld.setBlock({ x: 4003, y: 65, z: 0 }, "rotu:veilstone");
  itemEvent("onUse", "rotu:diviners_lens", { source: p, itemStack: lens });
  assert.equal(overworld.raw({ x: 4003, y: 64, z: 0 }).states["rotu:revealed"], true);
  assert.equal(getProgress(p).stats.veils, 2);
  assert.equal(lens.getComponent("minecraft:durability").damage, 1);
  assert.match(last(p.actionbar), /2 hidden stones/);
  const v = { x: 4003, y: 64, z: 0 };
  blockEvent("onPlayerInteract", v, { player: p });
  assert.match(last(p.actionbar), /walk through/);
});

await scenario("dowsing rod points toward the nearest singing stone", async () => {
  const p = newPlayer("Dowser", { x: 5000.5, y: 70, z: 0.5 });
  p.hold(new ItemStack("rotu:dowsing_rod").withDurability(128));
  overworld.setBlock({ x: 5012, y: 65, z: 0 }, "rotu:singing_stone");
  overworld.setBlock({ x: 4980, y: 70, z: 0 }, "rotu:singing_stone");
  itemEvent("onUse", "rotu:dowsing_rod", { source: p });
  assert.match(last(p.actionbar), /to the east - about 13 blocks, 5 blocks down/);
});

await scenario("low star fragment recalls to the spawn point and settles on the surface", async () => {
  const p = newPlayer("Wanderer", { x: 6000, y: 20, z: 0 });
  p.spawnPoint = { dimension: overworld, x: 10, y: 70, z: 10 };
  itemEvent("onCompleteUse", "rotu:low_star_fragment", { source: p });
  assert.deepEqual(p.location, { x: 10.5, y: 70, z: 10.5 });
  assert.equal(p.getItemCooldown("rotu:starcall"), 2400);
  const q = newPlayer("Lost", { x: 6000, y: 20, z: 0 });
  overworld.setBlock({ x: 100, y: 63, z: -40 }, "rotu:gloamstone_bricks");
  itemEvent("onCompleteUse", "rotu:low_star_fragment", { source: q });
  assert.equal(q.location.y, 250);
  await advance(15);
  assert.deepEqual(q.location, { x: 100.5, y: 64, z: -39.5 });
});

await scenario("relic weapons: the dirge echoes on the Unnamed, the maul shockwave hits monsters", async () => {
  const p = newPlayer("Warden", { x: 7000, y: 64, z: 0 });
  const walker = overworld.spawnEntity("rotu:hushwalker", { x: 7001, y: 64, z: 0 });
  itemEvent("onHitEntity", "rotu:dirge_blade", { attackingEntity: p, hitEntity: walker, hadEffect: true });
  await advance(13);
  assert.deepEqual(walker.damage.map((d) => d.amount), [5]);
  const target = overworld.spawnEntity("rotu:hushwalker", { x: 7010, y: 64, z: 0 });
  const bystander = overworld.spawnEntity("rotu:murmur", { x: 7011, y: 64, z: 1 });
  itemEvent("onHitEntity", "rotu:sentinels_maul", { attackingEntity: p, hitEntity: target, hadEffect: true });
  assert.deepEqual(bystander.damage.map((d) => d.amount), [3]);
  const pick = new ItemStack("rotu:delvers_pick").withDurability(1900);
  p.hold(pick);
  const random = Math.random;
  Math.random = () => 0.01;
  const stone = { x: 7020, y: 64, z: 0 };
  overworld.setBlock(stone, "rotu:gloamstone_bricks");
  const perm = overworld.getBlock(stone).permutation;
  itemEvent("onMineBlock", "rotu:delvers_pick", { source: p, block: overworld.getBlock(stone), minedBlockPermutation: perm });
  Math.random = random;
  assert.equal(pick.getComponent("minecraft:durability").damage, 1);
  assert.ok(overworld.entities.some((e) => e.item && e.item.typeId === "rotu:glyph_shard"), "shard freed");
});

await scenario("sigil lock opens the sanctum gate for the key bearer", async () => {
  const lock = { x: 8007, y: 2, z: 4 };
  for (const x of [8006, 8007, 8008]) for (const y of [1, 2, 3, 4]) overworld.setBlock({ x, y, z: 1 }, "rotu:sealed_gate");
  overworld.setBlock(lock, "rotu:sigil_lock");
  const p = newPlayer("Keybearer", { x: 8007, y: 1, z: 6 });
  blockEvent("onPlayerInteract", lock, { player: p });
  assert.match(last(p.actionbar), /Three sigils/);
  p.hold(new ItemStack("rotu:sigil_key"));
  await advance(12);
  blockEvent("onPlayerInteract", lock, { player: p });
  assert.equal(overworld.raw(lock).states["rotu:unlocked"], true);
  await advance(60);
  assert.equal(blocksOf("rotu:sealed_gate"), 0);
  assert.equal(count(p, "rotu:sigil_key"), 1, "the key is kept");
  assert.ok(getProgress(p).flags.key);
});

await scenario("the Last Cantor: wakes from its marker, pulses, breaks, and its death opens the vault", async () => {
  const home = { x: 9011, y: 2, z: 11 };
  for (let x = 9000; x <= 9022; x++) for (let z = 0; z <= 22; z++) overworld.setBlock({ x, y: 0, z }, "rotu:gloamstone_tiles");
  overworld.setBlock(home, "rotu:spawn_marker", { "rotu:mob": "cantor" });
  for (const x of [9010, 9011, 9012]) for (const y of [1, 2, 3]) overworld.setBlock({ x, y, z: 1 }, "rotu:sealed_gate");
  const hero = newPlayer("Hero", { x: 9011, y: 1, z: 20 });
  const masked = newPlayer("Masked", { x: 9013, y: 1, z: 18 });
  masked.armor[EquipmentSlot.Head] = new ItemStack("rotu:choristers_mask");
  blockEvent("onTick", home);
  const [boss] = overworld.getEntities({ type: "rotu:last_cantor" });
  assert.ok(boss, "cantor spawned");
  assert.deepEqual(boss.getDynamicProperty("rotu:home"), home);
  assert.match(last(hero.titles), /Last Cantor/);
  await advance(230);
  assert.ok(hero.getEffect("darkness"), "pulse darkens the hero");
  assert.equal(masked.getEffect("darkness"), undefined, "mask protects");
  boss.components["minecraft:variant"] = { value: 1 };
  overworld.setBlock({ x: 9013, y: 1, z: 13 }, "minecraft:torch");
  world.afterEvents.dataDrivenEntityTrigger.fire(
    { entity: boss, eventId: "rotu:enter_phase_two", getModifiers: () => [] },
    (o) => (!o.entityTypes || o.entityTypes.includes(boss.typeId)) && (!o.eventTypes || o.eventTypes.includes("rotu:enter_phase_two"))
  );
  assert.match(last(hero.titles), /note breaks/);
  await advance(60);
  assert.equal(blocksOf("minecraft:torch"), 0, "phase-two pulse snuffs torches");
  boss.location = { x: 9012, y: 2, z: 19.5 };
  hero.location = { x: 9012, y: 2, z: 20 };
  await advance(45);
  assert.notDeepEqual(boss.location, { x: 9012, y: 2, z: 19.5 }, "blinks away from melee");
  world.afterEvents.entityDie.fire(
    { deadEntity: boss, damageSource: { cause: "entityAttack", damagingEntity: hero } },
    (o) => !o.entityTypes || o.entityTypes.includes(boss.typeId)
  );
  await advance(80);
  assert.equal(blocksOf("rotu:sealed_gate"), 0, "vault door dissolved");
  for (const p of [hero, masked]) {
    assert.ok(getProgress(p).chapters.includes(12));
    assert.ok(getProgress(p).flags.cantor);
  }
});

await scenario("graven sentinel awakening is announced, and kills are counted", async () => {
  const s = overworld.spawnEntity("rotu:graven_sentinel", { x: 9500, y: 64, z: 0 });
  const p = newPlayer("Watcher", { x: 9503, y: 64, z: 0 });
  world.afterEvents.dataDrivenEntityTrigger.fire(
    { entity: s, eventId: "rotu:awaken", getModifiers: () => [] },
    (o) => (!o.entityTypes || o.entityTypes.includes(s.typeId)) && (!o.eventTypes || o.eventTypes.includes("rotu:awaken"))
  );
  assert.match(last(p.actionbar), /remembers its purpose/);
  assert.ok((p.commands || []).some((c) => c.startsWith("camerashake")));
  world.afterEvents.entityDie.fire(
    { deadEntity: s, damageSource: { cause: "entityAttack", damagingEntity: p } },
    (o) => !o.entityTypes || o.entityTypes.includes(s.typeId)
  );
  assert.equal(getProgress(p).stats.sentinels, 1);
});

await scenario("codex UI navigates chapters, discoveries and closes cleanly", async () => {
  const p = newPlayer("Archivist", { x: 9900, y: 64, z: 0 });
  p.hold(new ItemStack("rotu:lantern_shard"));
  await advance(101); // inventory flag sync runs every 100 ticks
  assert.ok(getProgress(p).flags.lantern);
  p.formResponses.push(0, 12, 3, 0, 4);
  itemEvent("onUse", "rotu:codex", { source: p });
  await advance(5);
  assert.deepEqual(
    p.formsShown.map((f) => f.title),
    ["Codex of the Unnamed", "Chapters", "Codex of the Unnamed", "Discoveries", "Codex of the Unnamed"]
  );
  assert.match(p.formsShown[0].body, /Lantern/);
  assert.match(p.formsShown[0].body, /Next step/);
});

await scenario("welcome message on first join", async () => {
  const p = newPlayer("Newcomer", { x: 0, y: 64, z: 0 });
  world.afterEvents.playerSpawn.fire({ player: p, initialSpawn: true });
  await advance(85);
  assert.match(p.messages.join("\n"), /Ruins of the Unnamed/);
});

assert.deepEqual(warnings, [], `scripts logged errors:\n${warnings.join("\n")}`);
console.log(`script smoke test: ${passed} scenarios passed`);
