// In-memory stand-in for the parts of @minecraft/server 2.x that Enchant+ uses.
//
// The item and enchantment model follows the game closely enough to catch real mistakes:
// ItemStack copies (getItem returns a copy, so changes must be written back), enchantment levels and
// compatibility enforced by addEnchantment, a canAddEnchantment that refuses Swift Sneak (the behaviour
// behind issue #3), experience levels, a scoreboard and worn equipment.

export const GameMode = { Adventure: "Adventure", Creative: "Creative", Spectator: "Spectator", Survival: "Survival" };
export const EquipmentSlot = { Chest: "Chest", Feet: "Feet", Head: "Head", Legs: "Legs", Mainhand: "Mainhand", Offhand: "Offhand" };

// ------------------------------------------------------------------------------------- scheduling
export const state = { tick: 0, timers: [], dimensions: new Map() };

class Signal {
  constructor() {
    this.handlers = [];
  }
  subscribe(fn) {
    this.handlers.push(fn);
    return fn;
  }
  unsubscribe(fn) {
    this.handlers = this.handlers.filter((h) => h !== fn);
  }
  fire(event) {
    for (const h of this.handlers) h(event);
  }
}

const flush = () => new Promise((resolve) => setImmediate(resolve));

export const system = {
  beforeEvents: { startup: new Signal() },
  get currentTick() {
    return state.tick;
  },
  run(fn) {
    return system.runTimeout(fn, 0);
  },
  runTimeout(fn, ticks = 0) {
    const t = { fn, at: state.tick + Math.max(1, ticks), every: 0 };
    state.timers.push(t);
    return state.timers.length;
  },
  runInterval(fn, ticks = 1) {
    const t = { fn, at: state.tick + ticks, every: ticks };
    state.timers.push(t);
    return state.timers.length;
  },
  // Time passes on its own while a script waits, so awaited flows never stall in tests.
  async waitTicks(ticks) {
    state.tick += ticks;
    await flush();
  },
};

/** Run `ticks` game ticks, letting pending promises settle after each one. */
export async function advance(ticks = 1) {
  for (let i = 0; i < ticks; i++) {
    state.tick++;
    for (const t of [...state.timers]) {
      if (t.at > state.tick) continue;
      if (t.every) t.at += t.every;
      else state.timers.splice(state.timers.indexOf(t), 1);
      t.fn();
    }
    for (let k = 0; k < 5; k++) await flush();
  }
}

// ------------------------------------------------------------------------------------ enchantments
const MAX_LEVEL = {
  protection: 4, fire_protection: 4, feather_falling: 4, blast_protection: 4, projectile_protection: 4, thorns: 3,
  respiration: 3, depth_strider: 3, aqua_affinity: 1, frost_walker: 2, soul_speed: 3, swift_sneak: 3, binding: 1,
  vanishing: 1, sharpness: 5, smite: 5, bane_of_arthropods: 5, knockback: 2, fire_aspect: 2, looting: 3, lunge: 3,
  density: 5, breach: 4, wind_burst: 3, efficiency: 5, silk_touch: 1, fortune: 3, unbreaking: 3, mending: 1, power: 5,
  punch: 2, flame: 1, infinity: 1, multishot: 1, piercing: 4, quick_charge: 3, impaling: 5, riptide: 3, loyalty: 3,
  channeling: 1, luck_of_the_sea: 3, lure: 3,
};

export class EnchantmentType {
  constructor(id, maxLevel) {
    this.id = id;
    this.maxLevel = maxLevel;
  }
}
const TYPES = Object.entries(MAX_LEVEL).map(([id, max]) => new EnchantmentType(`minecraft:${id}`, max));
const short = (t) => (typeof t === "string" ? t : t.id).replace(/^minecraft:/, "");

export const EnchantmentTypes = {
  getAll: () => TYPES.slice(),
  get: (id) => TYPES.find((t) => short(t) === short(id)),
};

// What the engine accepts per enchantment slot (written independently of the add-on's own table).
const COMMON = ["unbreaking", "mending", "vanishing"];
const ARMOR = ["protection", "fire_protection", "blast_protection", "projectile_protection", "thorns", "binding", ...COMMON];
const ENGINE = {
  Sword: ["sharpness", "smite", "bane_of_arthropods", "knockback", "fire_aspect", "looting", ...COMMON],
  Axe: ["sharpness", "smite", "bane_of_arthropods", "efficiency", "fortune", "silk_touch", ...COMMON],
  Pickaxe: ["efficiency", "fortune", "silk_touch", ...COMMON],
  ArmorHead: [...ARMOR, "respiration", "aqua_affinity"],
  ArmorTorso: ARMOR,
  ArmorLegs: [...ARMOR, "swift_sneak"],
  ArmorFeet: [...ARMOR, "feather_falling", "depth_strider", "frost_walker", "soul_speed"],
  Bow: ["power", "punch", "flame", "infinity", ...COMMON],
};
const ENGINE_EXCLUSIVE = [
  ["protection", "fire_protection", "blast_protection", "projectile_protection"],
  ["sharpness", "smite", "bane_of_arthropods"],
  ["silk_touch", "fortune"],
  ["infinity", "mending"],
];
const engineConflict = (a, b) => a !== b && ENGINE_EXCLUSIVE.some((g) => g.includes(a) && g.includes(b));

function slotsFor(typeId) {
  const id = typeId.replace(/^minecraft:/, "");
  const rules = [
    [/_sword$/, "Sword"], [/_axe$/, "Axe"], [/_pickaxe$/, "Pickaxe"], [/_helmet$/, "ArmorHead"],
    [/_chestplate$/, "ArmorTorso"], [/_leggings$/, "ArmorLegs"], [/_boots$/, "ArmorFeet"], [/^bow$/, "Bow"],
  ];
  for (const [re, slot] of rules) if (re.test(id)) return [slot];
  return undefined;
}

const KNOWN_ITEMS = new Set(["minecraft:book", "minecraft:enchanted_book", "minecraft:dirt", "minecraft:stick", "da:enchant_essence"]);

export class ItemStack {
  constructor(typeId, amount = 1) {
    if (!KNOWN_ITEMS.has(typeId) && !slotsFor(typeId)) throw new Error(`mock: unknown item ${typeId}`);
    this.typeId = typeId;
    this.amount = amount;
    this.nameTag = undefined;
    this.lore = [];
    this.enchants = new Map();
  }
  get localizationKey() {
    return `item.${this.typeId.replace(/^minecraft:/, "")}.name`;
  }
  get maxAmount() {
    return this.typeId === "minecraft:enchanted_book" || slotsFor(this.typeId) ? 1 : 64;
  }
  getLore() {
    return [...this.lore];
  }
  clone() {
    const c = new ItemStack(this.typeId, this.amount);
    c.nameTag = this.nameTag;
    c.lore = [...this.lore];
    c.enchants = new Map(this.enchants);
    return c;
  }
  isStackableWith(other) {
    return other.typeId === this.typeId && this.enchants.size === 0 && other.enchants.size === 0 && !this.nameTag && !other.nameTag;
  }
  getComponent(id) {
    if (id !== "minecraft:enchantable") return undefined;
    if (this.typeId === "minecraft:enchanted_book") return new Enchantable(this, []);
    const slots = slotsFor(this.typeId);
    return slots ? new Enchantable(this, slots) : undefined;
  }
}

class Enchantable {
  constructor(stack, slots) {
    this.stack = stack;
    this.slots = slots;
  }
  accepts(id) {
    return this.stack.typeId === "minecraft:enchanted_book" || this.slots.some((s) => (ENGINE[s] ?? []).includes(id));
  }
  check({ type, level }) {
    if (!type || !EnchantmentTypes.get(type.id)) throw new Error("EnchantmentTypeUnknownIdError");
    if (level < 1 || level > type.maxLevel) throw new Error("EnchantmentLevelOutOfBoundsError");
  }
  compatible(id) {
    if (!this.accepts(id)) return false;
    if (this.stack.typeId === "minecraft:enchanted_book") return true;
    return ![...this.stack.enchants.keys()].some((other) => engineConflict(id, other));
  }
  getEnchantments() {
    return [...this.stack.enchants].map(([id, level]) => ({ type: EnchantmentTypes.get(id), level }));
  }
  getEnchantment(t) {
    const id = short(t);
    return this.stack.enchants.has(id) ? { type: EnchantmentTypes.get(id), level: this.stack.enchants.get(id) } : undefined;
  }
  hasEnchantment(t) {
    return this.stack.enchants.has(short(t));
  }
  canAddEnchantment(e) {
    this.check(e);
    const id = short(e.type);
    if (id === "swift_sneak") return false; // engine quirk (issue #3)
    return this.compatible(id);
  }
  addEnchantment(e) {
    this.check(e);
    const id = short(e.type);
    if (this.stack.enchants.has(id)) throw new Error(`mock: ${id} already present (remove it first)`);
    if (!this.compatible(id)) throw new Error("EnchantmentTypeNotCompatibleError");
    this.stack.enchants.set(id, e.level);
  }
  removeEnchantment(t) {
    this.stack.enchants.delete(short(t));
  }
  removeAllEnchantments() {
    this.stack.enchants.clear();
  }
}

// --------------------------------------------------------------------------------- containers
class Container {
  constructor(size) {
    this.size = size;
    this.slots = new Array(size).fill(undefined);
  }
  getItem(i) {
    return this.slots[i]?.clone();
  }
  setItem(i, item) {
    this.slots[i] = item ? item.clone() : undefined;
  }
  addItem(stack) {
    let left = stack.clone();
    for (let i = 0; i < this.size && left.amount > 0; i++) {
      const s = this.slots[i];
      if (s && s.isStackableWith(left) && s.amount < s.maxAmount) {
        const n = Math.min(left.amount, s.maxAmount - s.amount);
        s.amount += n;
        left.amount -= n;
      }
    }
    for (let i = 0; i < this.size && left.amount > 0; i++) {
      if (!this.slots[i]) {
        this.slots[i] = left.clone();
        left.amount = 0;
      }
    }
    return left.amount > 0 ? left : undefined;
  }
}

// ----------------------------------------------------------------------------- world objects
const key = (l) => `${Math.floor(l.x)},${Math.floor(l.y)},${Math.floor(l.z)}`;

class Block {
  constructor(dimension, location) {
    this.dimension = dimension;
    this.location = { x: Math.floor(location.x), y: Math.floor(location.y), z: Math.floor(location.z) };
  }
  get typeId() {
    return this.dimension.blocks.get(key(this.location)) ?? "minecraft:air";
  }
  center() {
    return { x: this.location.x + 0.5, y: this.location.y + 0.5, z: this.location.z + 0.5 };
  }
}

export class Entity {
  constructor(typeId, dimension, location) {
    this.typeId = typeId;
    this.dimension = dimension;
    this.location = { ...location };
    this.isValid = true;
    this.id = `${typeId}#${++Entity.next}`;
    dimension.entities.add(this);
  }
  remove() {
    this.isValid = false;
    this.dimension.entities.delete(this);
  }
  teleport(location) {
    this.location = { ...location };
  }
}
Entity.next = 0;

export class Dimension {
  constructor(id) {
    this.id = id;
    this.blocks = new Map();
    this.entities = new Set();
    this.sounds = [];
    this.droppedItems = [];
  }
  setBlockType(location, typeId) {
    if (typeId === "minecraft:air") this.blocks.delete(key(location));
    else this.blocks.set(key(location), typeId);
  }
  getBlock(location) {
    return new Block(this, location);
  }
  getEntities(options = {}) {
    return [...this.entities].filter((e) => {
      if (options.type && e.typeId !== options.type) return false;
      if (options.location && options.maxDistance !== undefined) {
        const d = Math.hypot(e.location.x - options.location.x, e.location.y - options.location.y, e.location.z - options.location.z);
        if (d > options.maxDistance) return false;
      }
      return true;
    });
  }
  spawnEntity(typeId, location) {
    return new Entity(typeId, this, location);
  }
  spawnItem(stack, location) {
    this.droppedItems.push(stack.clone());
    return new Entity("minecraft:item", this, location);
  }
  playSound(id) {
    this.sounds.push(id);
  }
}

export class Player extends Entity {
  constructor(name, dimension) {
    super("minecraft:player", dimension, { x: 0, y: 64, z: 0 });
    this.name = name;
    this.id = `player:${name}`;
    this.level = 0;
    this.gameMode = GameMode.Survival;
    this.inventory = new Container(36);
    this.worn = new Map();
    this.messages = [];
    this.answers = [];
    this.formsShown = [];
  }
  getComponent(id) {
    if (id === "minecraft:inventory") return { container: this.inventory };
    if (id === "minecraft:equippable") {
      return {
        getEquipment: (slot) => this.worn.get(slot)?.clone(),
        setEquipment: (slot, item) => {
          if (item) this.worn.set(slot, item.clone());
          else this.worn.delete(slot);
          return true;
        },
      };
    }
    return undefined;
  }
  addLevels(n) {
    this.level = Math.max(0, this.level + n);
    return this.level;
  }
  getGameMode() {
    return this.gameMode;
  }
  sendMessage(m) {
    this.messages.push(m);
  }
}

// -------------------------------------------------------------------------------- scoreboard
class Objective {
  constructor(id, displayName) {
    this.id = id;
    this.displayName = displayName;
    this.scores = new Map();
  }
  getScore(p) {
    return this.scores.get(p.id);
  }
  setScore(p, v) {
    this.scores.set(p.id, v);
    return true;
  }
  addScore(p, v) {
    this.scores.set(p.id, (this.scores.get(p.id) ?? 0) + v);
    return this.scores.get(p.id);
  }
}

export const world = {
  scoreboard: {
    objectives: new Map(),
    getObjective(id) {
      return this.objectives.get(id);
    },
    addObjective(id, displayName) {
      if (this.objectives.has(id)) throw new Error(`mock: objective ${id} exists`);
      const o = new Objective(id, displayName ?? id);
      this.objectives.set(id, o);
      return o;
    },
  },
  getDimension(id) {
    const name = id.replace(/^minecraft:/, "");
    if (!state.dimensions.has(name)) state.dimensions.set(name, new Dimension(`minecraft:${name}`));
    return state.dimensions.get(name);
  },
};
