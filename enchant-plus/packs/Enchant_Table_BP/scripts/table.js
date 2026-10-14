/**
 * The Enchant+ table block (custom component "da:enchant_table") and the orb that floats above it.
 *
 * Every table keeps exactly one orb: the block's tick restores a missing orb (tables from structures,
 * commands or older versions, or an orb removed by /kill) and removes duplicates, and breaking the
 * table by any means removes its orb. A slow sweep clears orbs whose table vanished without a break
 * event, for example through /setblock or /fill.
 */
import { system, world } from "@minecraft/server";
import { config } from "./config.js";
import { openTable } from "./menu.js";

/** @typedef {import("@minecraft/server").Block} Block */
/** @typedef {import("@minecraft/server").Dimension} Dimension */
/** @typedef {import("@minecraft/server").Vector3} Vector3 */

export const TABLE = "da:enchant_table_plus";
export const ORB = "da:enchant_sphere";

// The orb model is centred half a pixel off its origin: this puts it over the middle of the table.
const ORB_OFFSET = { x: 0.5 - 1 / 32, y: 0.8, z: 0.5 + 1 / 32 };
const SWEEP_TICKS = 200;

/** @param {Vector3} at block location */
function orbSpot(at) {
  return { x: at.x + ORB_OFFSET.x, y: at.y + ORB_OFFSET.y, z: at.z + ORB_OFFSET.z };
}

/** @param {Dimension} dimension @param {Vector3} at block location */
function orbsAt(dimension, at) {
  return dimension.getEntities({ type: ORB, location: orbSpot(at), maxDistance: 0.75 });
}

/** @param {Dimension} dimension @param {Vector3} at block location */
function removeOrbs(dimension, at) {
  for (const orb of orbsAt(dimension, at)) orb.remove();
}

/** Make sure the table has one orb (or none, if orbs are switched off). @param {Block} block */
function keepOrb(block) {
  const orbs = orbsAt(block.dimension, block.location);
  if (!config.orb) {
    for (const orb of orbs) orb.remove();
    return;
  }
  const spot = orbSpot(block.location);
  if (orbs.length === 0) {
    block.dimension.spawnEntity(ORB, spot);
    return;
  }
  for (const extra of orbs.slice(1)) extra.remove();
  // Orbs from older versions stand slightly off-centre.
  const at = orbs[0].location;
  if (Math.abs(at.x - spot.x) + Math.abs(at.y - spot.y) + Math.abs(at.z - spot.z) > 0.01) orbs[0].teleport(spot);
}

/** @type {import("@minecraft/server").BlockCustomComponent} */
const tableComponent = {
  onPlace({ block }) {
    keepOrb(block);
  },
  onTick({ block }) {
    keepOrb(block);
  },
  onBreak({ block, dimension }) {
    removeOrbs(dimension, block.location);
  },
  onPlayerInteract({ block, player }) {
    if (!player) return;
    const table = { dimension: block.dimension, location: block.center() };
    system.run(() => void openTable(player, table));
  },
};

system.beforeEvents.startup.subscribe(({ blockComponentRegistry }) => {
  blockComponentRegistry.registerCustomComponent("da:enchant_table", tableComponent);
});

/** Remove orbs that no longer stand on a table. */
function sweep() {
  for (const id of ["minecraft:overworld", "minecraft:nether", "minecraft:the_end"]) {
    let dimension;
    try {
      dimension = world.getDimension(id);
    } catch {
      continue;
    }
    for (const orb of dimension.getEntities({ type: ORB })) {
      const at = orb.location;
      const below = { x: Math.floor(at.x), y: Math.floor(at.y - ORB_OFFSET.y + 0.01), z: Math.floor(at.z) };
      let block;
      try {
        block = dimension.getBlock(below);
      } catch {
        continue;
      }
      if (block && block.typeId !== TABLE) orb.remove();
    }
  }
}

system.runInterval(sweep, SWEEP_TICKS);
