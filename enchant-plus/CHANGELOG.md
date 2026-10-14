# Changelog

## 1.1.0 (2026-10-14): Minecraft Bedrock 1.26.5x

This version rebuilds the add-on for Minecraft 1.26.50+, targeting 1.26.52.3. The scripts are rewritten
for the current stable Script API, `@minecraft/server` 2.10.0 and `@minecraft/server-ui` 2.2.0. The packs
are rebuilt in current formats and checked against Mojang's 1.26.50 schemas.

### Open issues

* **#3: Swift Sneak missing on leggings.** The menu now uses its own table of vanilla enchantment rules, by
  the item's enchantment slot. That table includes treasure enchantments: Swift Sneak on leggings, plus
  Mending, Frost Walker and Soul Speed. The game's own check still adds anything the table does not know.
  1.0.5 relied only on that check, which can leave out Swift Sneak.
* **#4: no orb, no interaction (1.21.20 and later).**
  * The table is now a custom block component (`da:enchant_table`). Placing it creates the orb, and every two
    seconds the table restores a missing orb and removes duplicates. Breaking it by any means (player,
    explosion) removes the orb.
  * A sweep also clears orbs whose table was removed by commands.
  * Interaction is handled by the block itself instead of a global event.
  * The old scripts used APIs that Script API 2.0 removed or changed, such as `runCommandAsync` and the
    five-argument `slider()`. They also had a crash in transfers when a stack of books had no free slot.
* **#6: resource pack warning, broken after reloading.** The report did not include the warning text. The
  audit found these faults, and all of them are fixed:
  * `ui/server_form.json` redefined vanilla's `long_form` and `custom_form` dialogs with 1.21-era copies, for
    every form in the game. Its custom screens bound to `#form_button_length`, which no longer drives the
    button list in 1.26 (labels, headers and dividers changed it), so the menus came up empty. The file now
    only adds an Enchant+ window through JSON UI `modifications`, so vanilla forms and other add-ons' forms
    are untouched.
  * `font/glyph_E0.png` replaced the game's controller-button glyph page with an old copy. It is removed.
  * `terrain_texture.json` overrode the global atlas padding and mip settings. It no longer does.
  * The manifests had metadata fields the format does not define (`license_url`) and a tool tag for a tool
    that is no longer used. Both are removed.
  * The table recipe used `minecraft:Enchanting_table`. Item ids are case-sensitive, so the recipe failed to
    load and the table could not be crafted.
  * Both recipes were registered under the `minecraft:` namespace, which belongs to vanilla content. They
    now use `da:`.
  * The essence recipe only unlocked once you already had essence. It now unlocks with amethyst or lapis.
  * The essence name used the wrong lang key, so it showed as `item.da:enchant_essence.name`.
  * `blocks.json` used a key without the `da:` namespace, so the table fell back to default sounds instead
    of the vault sound set.
  * A tick function ran a `particle` command for every orb, every tick. The orb now owns one emitter through
    its client entity. Its flipbook also no longer reads past the end of its texture.
  * The orb used the vanilla husk's render controller and was a `mob`. It now has its own render controller
    and is not a mob, so it is no longer hit by mob-targeted commands.
* **#7: Enchant Essence always cost 3.** Every currency is now charged per enchantment level: per level
  added when enchanting, per level moved when transferring. Refunds use the same rule. The default is 3
  essence per level, the same rate as XP.

### Also new

* Armour you are wearing and the off-hand item appear in the menu. Enchanting them writes them back in place.
* Maces (Density, Breach, Wind Burst), spears (Lunge) and copper gear are supported. Items from other
  add-ons work wherever the game accepts the enchantment.
* Item and enchantment names are translated through the game's own lang keys. All menu text is in
  `texts/*.lang`, ready for translation (en_US and en_GB included).
* Operations are safe:
  * Nothing is paid until you confirm.
  * Items are re-read at confirmation, and anything that changed in the meantime cancels the operation.
  * Results are built on copies first, so a refused enchantment costs nothing.
* Enchanted books made from a stack of books go to your inventory, or drop at your feet if it is full.
* Creative players enchant for free (`creativeIsFree`).
* The framed Enchant+ window can be switched off (`themedForms: false`) to fall back to plain vanilla forms.
* The orb can be switched off (`orb: false`).
* The table gives off light like a vanilla enchanting table (level 7) and cannot be pushed by pistons.
* Sounds: enchanting table on enchant, grindstone on remove, anvil on transfer.

### Changed

* Scripts are shipped as readable source instead of obfuscated code. `config.js` uses clearer names: see
  the README.
* The "Select item" grid, which no longer worked, is replaced by a list in the framed window, with item
  icons, where each item is, and how many enchantments it has.

### Not verified here

The packs are validated against Mojang's schemas and cross-checked file by file. The scripts are
type-checked against the official 2.10.0 typings and run through 23 headless tests of every menu flow.
They have not yet been played in the game itself. Please report anything that behaves differently there.
