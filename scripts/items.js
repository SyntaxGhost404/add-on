// @ts-check
// Item custom components: the Codex, archaeology tools, relic weapons and the Low Star Fragment.
import { system, world, ItemStack, EntityDamageCause } from "@minecraft/server";
import { addStat, hasClaimed } from "./progress.js";
import { openCodex } from "./codex.js";
import {
  actionBar,
  centerOf,
  compass,
  damageMainhand,
  dist,
  findBlocks,
  getStateOf,
  guard,
  isCreative,
  isPlayer,
  later,
  particle,
  setStateOf,
  sound,
  throttle,
} from "./util.js";

/** @typedef {import("@minecraft/server").ItemCustomComponent} ItemCustomComponent */
/** @typedef {import("@minecraft/server").Player} Player */
/** @typedef {import("@minecraft/server").Vector3} Vector3 */

// ------------------------------------------------------------------ codex
/** @type {ItemCustomComponent} */
const codex = {
  onUse({ source: player }) {
    if (!throttle(`codex:${player.id}`, 10)) return;
    player.playSound("rotu.codex.open");
    openCodex(player);
  },
};

// ------------------------------------------------------------------ diviner's lens
/** @type {ItemCustomComponent} */
const diviningLens = {
  onUse({ source: player }) {
    if (!throttle(`lens:${player.id}`, 15)) return;
    const dim = player.dimension;
    const here = player.location;
    let revealed = 0;
    for (const loc of findBlocks(dim, here, 7, 5, 7, ["rotu:veilstone"])) {
      const b = dim.getBlock(loc);
      if (!b || getStateOf(b.permutation, "rotu:revealed")) continue;
      b.setPermutation(setStateOf(b.permutation, "rotu:revealed", true));
      particle(dim, "rotu:reveal_burst", centerOf(loc));
      revealed++;
    }
    let shimmer = 0;
    const types = ["rotu:funerary_urn", "rotu:reliquary", "rotu:singing_stone", "rotu:glyph_dial"];
    for (const loc of findBlocks(dim, here, 10, 6, 10, types)) {
      const b = dim.getBlock(loc);
      if (!b) continue;
      const perm = b.permutation;
      if (b.typeId === "rotu:glyph_dial" && getStateOf(perm, "rotu:glyph") !== getStateOf(perm, "rotu:solution")) continue;
      if (b.typeId === "rotu:funerary_urn" && !getStateOf(perm, "rotu:sealed")) continue;
      if (b.typeId === "rotu:reliquary" && hasClaimed(dim.id, loc, player)) continue;
      particle(dim, "rotu:glyph_motes", centerOf(loc));
      shimmer++;
    }
    sound(dim, "rotu.lens.use", here);
    damageMainhand(player, 1);
    if (revealed) {
      addStat(player, "veils", revealed);
      actionBar(player, `§bThe lens tears the veil from ${revealed} hidden stone${revealed === 1 ? "" : "s"}.`);
    } else if (shimmer) {
      actionBar(player, "§3Relics of the Choir shimmer around you.");
    } else {
      actionBar(player, "§7The lens shows only stone.");
    }
  },
};

// ------------------------------------------------------------------ resonant dowsing rod
/** @type {ItemCustomComponent} */
const dowsingRod = {
  onUse({ source: player }) {
    if (!throttle(`rod:${player.id}`, 20)) return;
    const dim = player.dimension;
    const here = player.location;
    let best;
    let bestDist = Infinity;
    for (const loc of findBlocks(dim, here, 28, 24, 28, ["rotu:singing_stone", "rotu:reliquary"])) {
      const d = dist(centerOf(loc), here);
      if (d >= bestDist) continue;
      const b = dim.getBlock(loc);
      if (b && b.typeId === "rotu:reliquary" && hasClaimed(dim.id, loc, player)) continue;
      best = loc;
      bestDist = d;
    }
    damageMainhand(player, 1);
    if (!best) {
      sound(dim, "rotu.dowse.ping", here, 0.6, 0.5);
      actionBar(player, "§7The rod hangs still. Nothing sings nearby.");
      return;
    }
    const target = centerOf(best);
    const dx = target.x - here.x;
    const dz = target.z - here.z;
    const dy = Math.round(target.y - (here.y + 0.5));
    const flat = Math.hypot(dx, dz);
    const way = flat < 2 ? "right beneath you" : `to the ${compass(dx, dz)}`;
    const depth = dy < -2 ? `, ${-dy} blocks down` : dy > 2 ? `, ${dy} blocks up` : "";
    const pitch = 0.7 + 1.1 * Math.max(0, 1 - bestDist / 40);
    sound(dim, "rotu.dowse.ping", here, 1.0, pitch);
    actionBar(player, `§3The rod pulls ${way} - about ${Math.round(bestDist)} blocks${depth}.`);
    const eye = player.getHeadLocation();
    const len = Math.max(0.001, Math.hypot(dx, target.y - eye.y, dz));
    for (let i = 1; i <= 4; i++) {
      const s = (i * 0.75) / len;
      particle(dim, "rotu:glyph_motes", { x: eye.x + dx * s, y: eye.y + (target.y - eye.y) * s - 0.3, z: eye.z + dz * s });
    }
  },
};

// ------------------------------------------------------------------ delver's pick
/** @type {ItemCustomComponent} */
const delversPick = {
  onMineBlock({ source, minedBlockPermutation, block }) {
    if (!isPlayer(source)) return;
    damageMainhand(source, 1);
    if (isCreative(source) || !minedBlockPermutation.hasTag("rotu:gloamstone") || Math.random() >= 0.08) return;
    const at = centerOf(block.location);
    source.dimension.spawnItem(new ItemStack("rotu:glyph_shard", 1), at);
    particle(source.dimension, "rotu:glyph_motes", at);
  },
};

// ------------------------------------------------------------------ dirge blade
/** @type {ItemCustomComponent} */
const dirgeBlade = {
  onHitEntity({ attackingEntity: attacker, hitEntity: target, hadEffect }) {
    if (!hadEffect || !target.isValid) return;
    const unnamed = target.matches({ families: ["unnamed"] });
    if (!unnamed && Math.random() >= 0.2) return;
    const damage = unnamed ? 5 : 3;
    // The echo lands after the target's hurt cooldown, so it is never swallowed.
    later(12, () => {
      if (!target.isValid) return;
      const options = attacker.isValid
        ? { cause: EntityDamageCause.magic, damagingEntity: attacker }
        : { cause: EntityDamageCause.magic };
      target.applyDamage(damage, options);
      const at = target.location;
      sound(target.dimension, "rotu.dirge.echo", at, 0.9);
      particle(target.dimension, "rotu:reveal_burst", { x: at.x, y: at.y + 1, z: at.z });
    });
  },
};

// ------------------------------------------------------------------ sentinel's maul
/** @type {ItemCustomComponent} */
const sentinelsMaul = {
  onHitEntity({ attackingEntity: attacker, hitEntity: target, hadEffect }) {
    if (!hadEffect || !target.isValid) return;
    const dim = target.dimension;
    const at = target.location;
    const from = attacker.location;
    const dx = at.x - from.x;
    const dz = at.z - from.z;
    const len = Math.hypot(dx, dz) || 1;
    guard("maul knockback", () => target.applyKnockback({ x: (dx / len) * 1.4, z: (dz / len) * 1.4 }, 0.4));
    for (const other of dim.getEntities({ location: at, maxDistance: 3, families: ["monster"] })) {
      if (other.id === target.id || other.id === attacker.id) continue;
      guard("maul shockwave", () => {
        other.applyDamage(3, { cause: EntityDamageCause.entityAttack, damagingEntity: attacker });
        const ox = other.location.x - at.x;
        const oz = other.location.z - at.z;
        const ol = Math.hypot(ox, oz) || 1;
        other.applyKnockback({ x: (ox / ol) * 0.8, z: (oz / ol) * 0.8 }, 0.25);
      });
    }
    sound(dim, "rotu.sentinel.attack", at, 0.6);
    particle(dim, "rotu:hush_dust", { x: at.x, y: at.y + 0.3, z: at.z });
  },
};

// ------------------------------------------------------------------ low star fragment
/**
 * After a recall to a spawn point without a fixed height, settle the player on the surface
 * once the destination chunk has loaded.
 * @param {Player} player @param {{ x: number, z: number }} xz @param {number} attempt
 */
function settleOnSurface(player, xz, attempt) {
  later(10, () => {
    if (!player.isValid) return;
    /** @type {import("@minecraft/server").Block | undefined} */
    let topBlock;
    try {
      topBlock = player.dimension.getTopmostBlock(xz);
    } catch {
      topBlock = undefined;
    }
    if (topBlock) player.teleport({ x: xz.x, y: topBlock.location.y + 1, z: xz.z });
    else if (attempt < 12) settleOnSurface(player, xz, attempt + 1);
  });
}

/** @type {ItemCustomComponent} */
const lowStarFragment = {
  onCompleteUse({ source: player }) {
    const fromDim = player.dimension;
    const from = player.location;
    particle(fromDim, "rotu:star_burst", { x: from.x, y: from.y + 1, z: from.z });
    sound(fromDim, "rotu.starcall", from, 1.2);
    const spawn = player.getSpawnPoint();
    const dim = spawn ? spawn.dimension : world.getDimension("overworld");
    const base = spawn || world.getDefaultSpawnLocation();
    const dest = { x: Math.floor(base.x) + 0.5, y: base.y, z: Math.floor(base.z) + 0.5 };
    const knownHeight = dest.y >= dim.heightRange.min && dest.y < dim.heightRange.max;
    player.addEffect("slow_falling", knownHeight ? 100 : 600, { showParticles: false });
    player.addEffect("resistance", 100, { amplifier: 1, showParticles: false });
    if (knownHeight) {
      player.teleport(dest, { dimension: dim });
    } else {
      player.teleport({ x: dest.x, y: Math.min(250, dim.heightRange.max - 2), z: dest.z }, { dimension: dim });
      settleOnSurface(player, { x: dest.x, z: dest.z }, 0);
    }
    later(3, () => {
      if (!player.isValid) return;
      const at = player.location;
      particle(player.dimension, "rotu:star_burst", { x: at.x, y: at.y + 1, z: at.z });
      sound(player.dimension, "rotu.starcall", at, 1.0);
    });
    guard("starcall cooldown", () => player.startItemCooldown("rotu:starcall", 2400));
    actionBar(player, "§bThe Low Star remembers where you rest.");
  },
};

system.beforeEvents.startup.subscribe(({ itemComponentRegistry: reg }) => {
  reg.registerCustomComponent("rotu:codex", codex);
  reg.registerCustomComponent("rotu:diviners_lens", diviningLens);
  reg.registerCustomComponent("rotu:dowsing_rod", dowsingRod);
  reg.registerCustomComponent("rotu:delvers_pick", delversPick);
  reg.registerCustomComponent("rotu:dirge_blade", dirgeBlade);
  reg.registerCustomComponent("rotu:sentinels_maul", sentinelsMaul);
  reg.registerCustomComponent("rotu:low_star_fragment", lowStarFragment);
});
