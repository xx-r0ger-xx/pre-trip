# Changelog

## 1.0.0 - 2026-10-01

First public release.

**Inspection**
- Health check for Euro Truck Simulator 2 and American Truck Simulator, with clickable gauges: mods current for
  the installed game version, file overlaps between active mods, bindings changed since the last snapshot, and
  days since the last crash.
- Alerts with one clear next step each (review binding changes, fix the load order with auto-sort, see a mod's
  files, open crash details, clean up sync leftovers). Acknowledge an alert to hide it; it comes back if anything
  changes.
- Checks unsaved Studio changes as well as what's saved in the game.

**ATS/ETS2 Sync**
- Compare and copy controls, graphics settings (`config.cfg`) and ReShade between the two games, in either
  direction, with one Sync button. Shows which game changed most recently.
- Lists the mods both games share.

**Studio**
- Drag-and-drop load order in coloured groups (fixes, graphics, sound, ... maps last).
- Live badges for files a mod wins or loses to another mod.
- Auto-sort that follows each mod author's own load-order notes ("place above X", "high priority").

**Garage**
- Mod gallery with each mod's preview image, and named loadouts you can switch between.

**Install and remove mods**
- Subscribe with a Steam Workshop link, install `.scs`/`.zip` files from Downloads, Browse, or drop files onto
  the window. Zips that only wrap `.scs` mods are unpacked.
- Remove a mod: local mods go to the Recycle Bin, Workshop mods are unsubscribed.

**Logbook**
- Timeline of controls snapshots, load-order and graphics backups, game updates and crashes, each restorable.
- Crash details from `game.crash.txt` / `game.log.txt`, and a crash finder that switches half your mods off per
  round to find the one crashing the game, then puts your load order back.

**Cleanup**
- Profile health, and quarantine for conflict copies left by cloud sync apps (nothing is deleted).

**Safety**
- Nothing is written while the game is running, and everything is backed up before it changes.
- Works on PCs with only one of the two games.
