// @ts-check
// Sealed Gates: solid gloamstone doors that dissolve, top row first, when their puzzle is solved.
import { findBlocks, later, particle, sound } from "./util.js";

/** @typedef {import("@minecraft/server").Dimension} Dimension */
/** @typedef {import("@minecraft/server").Vector3} Vector3 */

export const GATE = "rotu:sealed_gate";

/**
 * Dissolve every Sealed Gate block inside a box around `center`.
 * @param {Dimension} dim @param {Vector3} center @param {number} rx @param {number} ry @param {number} rz
 * @returns {number} number of gate blocks found
 */
export function dissolveGates(dim, center, rx, ry, rz) {
  const gates = findBlocks(dim, center, rx, ry, rz, [GATE]);
  if (!gates.length) return 0;
  /** @type {Map<number, Vector3[]>} */
  const rows = new Map();
  for (const g of gates) {
    const row = rows.get(g.y);
    if (row) row.push(g);
    else rows.set(g.y, [g]);
  }
  const ys = [...rows.keys()].sort((a, b) => b - a);
  sound(dim, "rotu.gate.open", gates[0], 1.4);
  ys.forEach((y, i) => {
    later(6 + i * 7, () => {
      for (const loc of rows.get(y) || []) {
        const block = dim.getBlock(loc);
        if (!block || block.typeId !== GATE) continue;
        block.setType("minecraft:air");
        particle(dim, "rotu:hush_dust", { x: loc.x + 0.5, y: loc.y + 0.5, z: loc.z + 0.5 });
      }
    });
  });
  return gates.length;
}
