/**
 * Enchant+ settings.
 *
 * Edit the values below, then reload the world (or run /reload as an operator) to apply them.
 *
 * Every cost is charged per enchantment level: adding Sharpness I -> III costs two levels' worth, and
 * moving Protection IV from one item to another costs four levels' worth. Refunds pay back a fraction
 * of what the removed levels would cost. Set `enabled: false` to turn a currency off.
 */
export const config = {
  /** Experience levels. */
  xp: {
    enabled: true,
    costPerLevel: 3,
    refund: 0.5,
  },

  /** Enchant Essence, or any other item: set `item` to its identifier. */
  essence: {
    enabled: true,
    item: "da:enchant_essence",
    costPerLevel: 3,
    refund: 0,
  },

  /** A scoreboard objective, for example a server economy. It is created if it does not exist. */
  score: {
    enabled: false,
    objective: "money",
    displayName: "Money",
    costPerLevel: 10,
    refund: 0.6,
  },

  /** Players in Creative mode enchant for free, as at a vanilla enchanting table. */
  creativeIsFree: true,

  /**
   * Show Enchant+ menus in the framed Enchant+ window. Set to false to use plain vanilla forms, for
   * example if another add-on also restyles server forms.
   */
  themedForms: true,

  /** Show the floating orb above every Enchant+ table. */
  orb: true,
};
