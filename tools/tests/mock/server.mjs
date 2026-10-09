// Minimal in-memory stand-in for @minecraft/server: just enough of the API surface used by
// scripts/ to run the add-on's gameplay logic headlessly in Node (see ../script_smoke.mjs).
// Block definitions (default states, tags) are loaded from the generated behavior pack, so a
// script that reads or writes a state that does not exist fails here just as it would in game.

export const state = {
  tick: 0,
  timeouts: [],
  intervals: [],
  dims: new Map(),
  players: [],
  worldProps: new Map(),
  difficulty: "Normal",
  timeOfDay: 18000,
  blockDefs: new Map(), // id -> { states: {name: default}, allowed: {name: values}, tags: [] }
  lootTables: new Set(), // "rotu/reliquary/lesser"
  families: new Map(), // entity id -> families
  nextId: 1,
};

// ------------------------------------------------------------------ enums
export const EquipmentSlot = { Mainhand: "Mainhand", Offhand: "Offhand", Head: "Head", Chest: "Chest", Legs: "Legs", Feet: "Feet" };
export const GameMode = { Adventure: "Adventure", Creative: "Creative", Spectator: "Spectator", Survival: "Survival" };
export const Difficulty = { Easy: "Easy", Hard: "Hard", Normal: "Normal", Peaceful: "Peaceful" };
export const EntityDamageCause = { entityAttack: "entityAttack", magic: "magic" };

// ------------------------------------------------------------------ events
class Signal {
  constructor() {
    this.subs = [];
  }
  subscribe(fn, options) {
    this.subs.push({ fn, options });
    return fn;
  }
  unsubscribe(fn) {
    this.subs = this.subs.filter((s) => s.fn !== fn);
  }
  fire(event, match = () => true) {
    for (const s of this.subs) if (match(s.options || {})) s.fn(event);
  }
}

// ------------------------------------------------------------------ scheduling
function schedule(fn, ticks) {
  state.timeouts.push({ fn, at: state.tick + Math.max(0, ticks) });
  return state.timeouts.length;
}

/** Advance the simulated clock, running due timeouts and intervals. Awaits promise jobs each tick. */
export async function advance(ticks) {
  for (let i = 0; i < ticks; i++) {
    state.tick++;
    const due = state.timeouts.filter((t) => t.at <= state.tick);
    state.timeouts = state.timeouts.filter((t) => t.at > state.tick);
    for (const t of due) t.fn();
    for (const iv of state.intervals) {
      if (state.tick >= iv.next) {
        iv.next = state.tick + iv.every;
        iv.fn();
      }
    }
    await new Promise((r) => setImmediate(r));
  }
}

export const system = {
  beforeEvents: { startup: new Signal() },
  afterEvents: {},
  get currentTick() {
    return state.tick;
  },
  run(fn) {
    return schedule(fn, 0);
  },
  runTimeout(fn, ticks = 0) {
    return schedule(fn, ticks);
  },
  runInterval(fn, ticks = 1) {
    state.intervals.push({ fn, every: ticks, next: state.tick + ticks });
    return state.intervals.length;
  },
  waitTicks(ticks) {
    return new Promise((resolve) => schedule(resolve, ticks));
  },
};

// ------------------------------------------------------------------ items
export class ItemStack {
  constructor(typeId, amount = 1) {
    this.typeId = typeId.includes(":") ? typeId : `minecraft:${typeId}`;
    this.amount = amount;
    this.components = {};
  }
  getComponent(id) {
    return this.components[id];
  }
  withDurability(max, damage = 0) {
    this.components["minecraft:durability"] = { maxDurability: max, damage };
    return this;
  }
}

class Container {
  constructor(size) {
    this.size = size;
    this.slots = new Array(size).fill(undefined);
  }
  getItem(i) {
    return this.slots[i];
  }
  setItem(i, item) {
    this.slots[i] = item;
  }
  addItem(stack) {
    const free = this.slots.findIndex((s) => s === undefined);
    if (free < 0) return stack;
    this.slots[free] = stack;
    return undefined;
  }
}

class ContainerSlot {
  constructor(container, index) {
    this.c = container;
    this.i = index;
  }
  hasItem() {
    return this.c.getItem(this.i) !== undefined;
  }
  getItem() {
    return this.c.getItem(this.i);
  }
  setItem(item) {
    this.c.setItem(this.i, item);
  }
  get amount() {
    return this.getItem().amount;
  }
  set amount(v) {
    this.getItem().amount = v;
  }
  get typeId() {
    return this.getItem()?.typeId;
  }
}

// ------------------------------------------------------------------ blocks
function defaultsFor(typeId) {
  const def = state.blockDefs.get(typeId);
  return def ? { ...def.states } : {};
}

class BlockPermutation {
  constructor(type, states) {
    this.type = type;
    this.states = { ...states };
  }
  getState(name) {
    return this.states[name];
  }
  withState(name, value) {
    const def = state.blockDefs.get(this.type);
    if (!def || !(name in def.allowed)) throw new Error(`${this.type} has no state ${name}`);
    if (!def.allowed[name].includes(value)) throw new Error(`${this.type}: ${name}=${value} not allowed`);
    return new BlockPermutation(this.type, { ...this.states, [name]: value });
  }
  getAllStates() {
    return { ...this.states };
  }
  hasTag(tag) {
    return (state.blockDefs.get(this.type)?.tags || []).includes(tag);
  }
}

const key = (l) => `${Math.floor(l.x)},${Math.floor(l.y)},${Math.floor(l.z)}`;

class Block {
  constructor(dim, loc) {
    this.dimension = dim;
    this.location = { x: Math.floor(loc.x), y: Math.floor(loc.y), z: Math.floor(loc.z) };
  }
  get x() {
    return this.location.x;
  }
  get y() {
    return this.location.y;
  }
  get z() {
    return this.location.z;
  }
  get typeId() {
    return this.dimension.raw(this.location).type;
  }
  get permutation() {
    const r = this.dimension.raw(this.location);
    return new BlockPermutation(r.type, r.states);
  }
  get isAir() {
    return this.typeId === "minecraft:air";
  }
  get isLiquid() {
    return false;
  }
  setPermutation(p) {
    this.dimension.put(this.location, p.type, p.states);
  }
  setType(t) {
    this.dimension.put(this.location, t, defaultsFor(t));
  }
  center() {
    return { x: this.location.x + 0.5, y: this.location.y + 0.5, z: this.location.z + 0.5 };
  }
  hasTag(tag) {
    return this.permutation.hasTag(tag);
  }
  above(n = 1) {
    return new Block(this.dimension, { ...this.location, y: this.location.y + n });
  }
  below(n = 1) {
    return new Block(this.dimension, { ...this.location, y: this.location.y - n });
  }
}

export class BlockVolume {
  constructor(from, to) {
    this.from = from;
    this.to = to;
  }
}

// ------------------------------------------------------------------ entities
export class Entity {
  constructor(typeId, dim, loc) {
    this.id = String(state.nextId++);
    this.typeId = typeId;
    this.dimension = dim;
    this.location = { ...loc };
    this.isValid = true;
    this.effects = {};
    this.damage = [];
    this.props = new Map();
    this.components = {};
    this.events = [];
    this.isSneaking = false;
  }
  addEffect(type, duration, options = {}) {
    this.effects[type] = { duration, ...options };
    return this.effects[type];
  }
  getEffect(type) {
    return this.effects[type];
  }
  removeEffect(type) {
    const had = type in this.effects;
    delete this.effects[type];
    return had;
  }
  applyDamage(amount, options) {
    this.damage.push({ amount, options });
    return true;
  }
  applyKnockback() {}
  applyImpulse() {}
  matches(options) {
    const fams = state.families.get(this.typeId) || [];
    return (options.families || []).every((f) => fams.includes(f));
  }
  getDynamicProperty(k) {
    return this.props.get(k);
  }
  setDynamicProperty(k, v) {
    if (v === undefined) this.props.delete(k);
    else this.props.set(k, v);
  }
  getComponent(id) {
    return this.components[id];
  }
  teleport(loc, options = {}) {
    this.location = { ...loc };
    if (options.dimension) this.dimension = options.dimension;
  }
  tryTeleport(loc, options) {
    this.teleport(loc, options);
    return true;
  }
  triggerEvent(e) {
    this.events.push(e);
  }
  runCommand(cmd) {
    (this.commands = this.commands || []).push(cmd);
    return { successCount: 1 };
  }
  getHeadLocation() {
    return { x: this.location.x, y: this.location.y + 1.62, z: this.location.z };
  }
  remove() {
    this.isValid = false;
    this.dimension.entities = this.dimension.entities.filter((e) => e !== this);
  }
}

export class Player extends Entity {
  constructor(name, dim, loc) {
    super("minecraft:player", dim, loc);
    this.name = name;
    this.gameMode = GameMode.Survival;
    this.inventory = new Container(36);
    this.selectedSlotIndex = 0;
    this.armor = {};
    this.actionbar = [];
    this.titles = [];
    this.messages = [];
    this.sounds = [];
    this.cooldowns = {};
    this.xp = 0;
    this.spawnPoint = undefined;
    this.formResponses = [];
    this.formsShown = [];
    const self = this;
    this.onScreenDisplay = {
      setActionBar: (t) => self.actionbar.push(String(t)),
      setTitle: (t, o) => self.titles.push(String(t) + (o && o.subtitle ? ` | ${o.subtitle}` : "")),
    };
    this.components["minecraft:inventory"] = { container: this.inventory };
    this.components["minecraft:equippable"] = {
      getEquipmentSlot: (slot) => {
        if (slot !== EquipmentSlot.Mainhand) throw new Error("mock: only mainhand slots");
        return new ContainerSlot(self.inventory, self.selectedSlotIndex);
      },
      getEquipment: (slot) => (slot === EquipmentSlot.Mainhand ? self.inventory.getItem(self.selectedSlotIndex) : self.armor[slot]),
    };
  }
  get mainhand() {
    return this.inventory.getItem(this.selectedSlotIndex);
  }
  hold(stack) {
    this.inventory.setItem(this.selectedSlotIndex, stack);
    return this;
  }
  getGameMode() {
    return this.gameMode;
  }
  playSound(id) {
    this.sounds.push(id);
  }
  sendMessage(m) {
    this.messages.push(String(m));
  }
  addExperience(n) {
    this.xp += n;
    return this.xp;
  }
  getSpawnPoint() {
    return this.spawnPoint;
  }
  startItemCooldown(cat, ticks) {
    this.cooldowns[cat] = ticks;
  }
  getItemCooldown(cat) {
    return this.cooldowns[cat] || 0;
  }
}

// ------------------------------------------------------------------ dimensions
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);

export class Dimension {
  constructor(id) {
    this.id = id;
    this.blocks = new Map();
    this.entities = [];
    this.sounds = [];
    this.particles = [];
    this.heightRange = { min: -64, max: 320 };
  }
  raw(loc) {
    return this.blocks.get(key(loc)) || { type: "minecraft:air", states: {} };
  }
  put(loc, type, states = defaultsFor(type)) {
    if (type === "minecraft:air") this.blocks.delete(key(loc));
    else this.blocks.set(key(loc), { type, states: { ...states } });
  }
  setBlock(loc, type, states = {}) {
    const merged = { ...defaultsFor(type), ...states };
    const def = state.blockDefs.get(type);
    if (def) for (const [k, v] of Object.entries(merged)) {
      if (!(k in def.allowed) || !def.allowed[k].includes(v)) throw new Error(`setBlock ${type}: bad state ${k}=${v}`);
    }
    this.put(loc, type, merged);
  }
  getBlock(loc) {
    return new Block(this, loc);
  }
  getBlocks(volume, options, allowUnloaded) {
    const lo = volume.from;
    const hi = volume.to;
    const out = [];
    for (const [k, b] of this.blocks) {
      const [x, y, z] = k.split(",").map(Number);
      if (x < lo.x || y < lo.y || z < lo.z || x > hi.x || y > hi.y || z > hi.z) continue;
      if (options.includeTypes && !options.includeTypes.includes(b.type)) continue;
      out.push({ x, y, z });
    }
    return { getBlockLocationIterator: () => out[Symbol.iterator]() };
  }
  getEntities(options = {}) {
    return this.entities.filter((e) => {
      if (!e.isValid) return false;
      if (options.type && e.typeId !== options.type) return false;
      if (options.location && options.maxDistance !== undefined && dist(e.location, options.location) > options.maxDistance) return false;
      if (options.families && !options.families.every((f) => (state.families.get(e.typeId) || []).includes(f))) return false;
      return true;
    });
  }
  getPlayers(options = {}) {
    return state.players.filter((p) => {
      if (p.dimension !== this) return false;
      if (options.location && options.maxDistance !== undefined && dist(p.location, options.location) > options.maxDistance) return false;
      if (options.excludeGameModes && options.excludeGameModes.includes(p.gameMode)) return false;
      return true;
    });
  }
  spawnEntity(id, loc, options = {}) {
    const e = new Entity(id, this, loc);
    if (options.spawnEvent) e.events.push(options.spawnEvent);
    this.entities.push(e);
    return e;
  }
  spawnItem(stack, loc) {
    const e = new Entity("minecraft:item", this, loc);
    e.item = stack;
    this.entities.push(e);
    return e;
  }
  playSound(id) {
    this.sounds.push(id);
  }
  spawnParticle(id) {
    this.particles.push(id);
  }
  getTopmostBlock(xz) {
    let best;
    for (const k of this.blocks.keys()) {
      const [x, y, z] = k.split(",").map(Number);
      if (x === Math.floor(xz.x) && z === Math.floor(xz.z) && (best === undefined || y > best)) best = y;
    }
    return best === undefined ? undefined : new Block(this, { x: xz.x, y: best, z: xz.z });
  }
  runCommand() {
    return { successCount: 1 };
  }
}

// ------------------------------------------------------------------ world
export const world = {
  afterEvents: {
    dataDrivenEntityTrigger: new Signal(),
    entityDie: new Signal(),
    playerSpawn: new Signal(),
  },
  beforeEvents: {},
  getDimension(id) {
    const name = id.replace("minecraft:", "");
    if (!state.dims.has(name)) state.dims.set(name, new Dimension(`minecraft:${name}`));
    return state.dims.get(name);
  },
  getAllPlayers() {
    return state.players.slice();
  },
  getDifficulty() {
    return state.difficulty;
  },
  getTimeOfDay() {
    return state.timeOfDay;
  },
  getDefaultSpawnLocation() {
    return { x: 100, y: 32767, z: -40 };
  },
  getDynamicProperty(k) {
    return state.worldProps.get(k);
  },
  setDynamicProperty(k, v) {
    if (v === undefined) state.worldProps.delete(k);
    else state.worldProps.set(k, v);
  },
  getLootTableManager() {
    return {
      getLootTable: (path) => (state.lootTables.has(path) ? { path } : undefined),
      generateLootFromTable: (table) => [new ItemStack("minecraft:emerald", 3), new ItemStack("minecraft:diamond", 1)],
    };
  },
};
