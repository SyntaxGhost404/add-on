/**
 * Vanilla enchanting data for Minecraft Bedrock 1.26.5x: display names, which enchantments each kind of
 * item accepts, which enchantments exclude each other, and item icons for the menus.
 */

/** Short enchantment id (no namespace) -> vanilla lang key of its name. @type {Record<string, string>} */
export const ENCHANT_NAMES = {
  protection: "enchantment.protect.all",
  fire_protection: "enchantment.protect.fire",
  feather_falling: "enchantment.protect.fall",
  blast_protection: "enchantment.protect.explosion",
  projectile_protection: "enchantment.protect.projectile",
  thorns: "enchantment.thorns",
  respiration: "enchantment.oxygen",
  depth_strider: "enchantment.waterWalker",
  aqua_affinity: "enchantment.waterWorker",
  frost_walker: "enchantment.frostwalker",
  soul_speed: "enchantment.soul_speed",
  swift_sneak: "enchantment.swift_sneak",
  binding: "enchantment.curse.binding",
  vanishing: "enchantment.curse.vanishing",
  sharpness: "enchantment.damage.all",
  smite: "enchantment.damage.undead",
  bane_of_arthropods: "enchantment.damage.arthropods",
  knockback: "enchantment.knockback",
  fire_aspect: "enchantment.fire",
  looting: "enchantment.lootBonus",
  lunge: "enchantment.lunge",
  density: "enchantment.heavy_weapon.density",
  breach: "enchantment.heavy_weapon.breach",
  wind_burst: "enchantment.heavy_weapon.windburst",
  efficiency: "enchantment.digging",
  silk_touch: "enchantment.untouching",
  fortune: "enchantment.lootBonusDigger",
  unbreaking: "enchantment.durability",
  mending: "enchantment.mending",
  power: "enchantment.arrowDamage",
  punch: "enchantment.arrowKnockback",
  flame: "enchantment.arrowFire",
  infinity: "enchantment.arrowInfinite",
  multishot: "enchantment.crossbowMultishot",
  piercing: "enchantment.crossbowPiercing",
  quick_charge: "enchantment.crossbowQuickCharge",
  impaling: "enchantment.tridentImpaling",
  riptide: "enchantment.tridentRiptide",
  loyalty: "enchantment.tridentLoyalty",
  channeling: "enchantment.tridentChanneling",
  luck_of_the_sea: "enchantment.lootBonusFishing",
  lure: "enchantment.fishingSpeed",
};

const COMMON = ["unbreaking", "mending", "vanishing"];
const ARMOR = ["protection", "fire_protection", "blast_protection", "projectile_protection", "thorns", "binding", ...COMMON];
const MELEE = ["sharpness", "smite", "bane_of_arthropods", "knockback", "fire_aspect", "looting", ...COMMON];
const TOOL = ["efficiency", "fortune", "silk_touch", ...COMMON];

/**
 * Enchantments each item enchantment slot accepts (anvil rules, so treasure enchantments such as
 * Mending, Frost Walker, Soul Speed and Swift Sneak are included). Keys are EnchantmentSlot values.
 * @type {Record<string, string[]>}
 */
export const BY_SLOT = {
  ArmorHead: [...ARMOR, "respiration", "aqua_affinity"],
  ArmorTorso: ARMOR,
  ArmorLegs: [...ARMOR, "swift_sneak"],
  ArmorFeet: [...ARMOR, "feather_falling", "depth_strider", "frost_walker", "soul_speed"],
  Elytra: ["binding", ...COMMON],
  CosmeticHead: ["binding", "vanishing"],
  Sword: MELEE,
  MeleeSpear: [...MELEE, "lunge"],
  Axe: ["sharpness", "smite", "bane_of_arthropods", ...TOOL],
  Pickaxe: TOOL,
  Shovel: TOOL,
  Hoe: TOOL,
  Shears: ["efficiency", ...COMMON],
  Bow: ["power", "punch", "flame", "infinity", ...COMMON],
  Crossbow: ["multishot", "piercing", "quick_charge", ...COMMON],
  Spear: ["impaling", "riptide", "loyalty", "channeling", ...COMMON],
  FishingRod: ["luck_of_the_sea", "lure", ...COMMON],
  Flintsteel: COMMON,
  CarrotStick: COMMON,
  Shield: COMMON,
};

/** Items whose rules are not described by their enchantment slots. @type {Record<string, string[]>} */
export const BY_ITEM = {
  "minecraft:mace": ["density", "breach", "wind_burst", "smite", "bane_of_arthropods", "fire_aspect", ...COMMON],
  "minecraft:brush": COMMON,
  "minecraft:wolf_armor": ["binding", ...COMMON],
  "minecraft:compass": ["vanishing"],
  "minecraft:lodestone_compass": ["vanishing"],
  "minecraft:recovery_compass": ["vanishing"],
  "minecraft:carved_pumpkin": ["binding", "vanishing"],
};

/** Items that accept every enchantment. A plain book turns into an enchanted book. */
export const BOOKS = new Set(["minecraft:book", "minecraft:enchanted_book"]);

/** Groups of enchantments that cannot be on the same item: any two members of a group conflict. */
export const EXCLUSIVE = [
  ["protection", "fire_protection", "blast_protection", "projectile_protection"],
  ["sharpness", "smite", "bane_of_arthropods"],
  ["density", "breach", "smite", "bane_of_arthropods"],
  ["sharpness", "density"],
  ["sharpness", "breach"],
  ["silk_touch", "fortune"],
  ["multishot", "piercing"],
  ["infinity", "mending"],
  ["riptide", "loyalty"],
  ["riptide", "channeling"],
  ["depth_strider", "frost_walker"],
];

const UNKNOWN_ICON = "textures/enchant_plus/icons/unknown_icon";
/** @type {Record<string, string>} */
const ICONS = {
  bow: "textures/items/bow_standby",
  crossbow: "textures/items/crossbow_standby",
  trident: "textures/items/trident",
  mace: "textures/items/mace",
  shears: "textures/items/shears",
  fishing_rod: "textures/items/fishing_rod_uncast",
  flint_and_steel: "textures/items/flint_and_steel",
  carrot_on_a_stick: "textures/items/carrot_on_a_stick",
  warped_fungus_on_a_stick: "textures/items/warped_fungus_on_a_stick",
  brush: "textures/items/brush",
  elytra: "textures/items/elytra",
  shield: "textures/enchant_plus/items/shield",
  turtle_helmet: "textures/items/turtle_helmet",
  wolf_armor: "textures/items/wolf_armor",
  book: "textures/items/book_normal",
  enchanted_book: "textures/items/book_enchanted",
  compass: "textures/items/compass_item",
  lodestone_compass: "textures/items/lodestonecompass_item",
  recovery_compass: "textures/items/recovery_compass_item",
  carved_pumpkin: "textures/blocks/pumpkin_face_off",
};
const GEAR = /^(wooden|stone|iron|golden|diamond|netherite|copper|leather|chainmail)_(helmet|chestplate|leggings|boots|sword|pickaxe|axe|shovel|hoe|spear)$/;
/** @type {Record<string, string>} */
const MATERIAL = { wooden: "wood", golden: "gold" };

/** Texture path for a menu button showing this item. @param {string} typeId */
export function iconFor(typeId) {
  const id = typeId.replace(/^minecraft:/, "");
  if (ICONS[id]) return ICONS[id];
  const m = typeId.startsWith("minecraft:") ? GEAR.exec(id) : null;
  if (!m) return UNKNOWN_ICON;
  const material = MATERIAL[m[1]] ?? m[1];
  return m[2] === "spear" ? `textures/items/spear/${material}_spear` : `textures/items/${material}_${m[2]}`;
}
