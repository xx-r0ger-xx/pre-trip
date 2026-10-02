# Changelog

## 1.0.1 - 2026-10-02

**New**
- Profile picker. With more than one ETS2/ATS profile, Pre-Trip now uses the one you played most recently (it used
  to take whichever profile folder sorted first) and shows a dropdown in the Inspection header to switch. Your
  choice is remembered.

**Safety fixes**
- Load-order backups are tied to the profile they came from. Restoring one puts back only the mod list, never the
  rest of profile.sii, and a backup from another profile can't be restored over this one.
- The crash finder keeps working on the profile it started on, can't be started twice (which would have lost
  your original load order), and blocks saving load orders until you finish or stop it.
- If Windows can't say whether a game is running, Pre-Trip now refuses to write instead of assuming it's closed.
- Removing a mod that's too big for the Recycle Bin asks first instead of deleting it for good.
- Installing is all or nothing: a failed copy or a bundle with one bad .scs leaves nothing half-installed, and
  bundles that wouldn't fit on the disk are refused up front.
- Removing an active mod takes it out of the load order first, so a failed removal never leaves a dangling entry.
- Cleanup records every file it moved even if a later move fails, and two runs in the same second no longer share
  a quarantine folder.

**Fixes**
- One failing check no longer blanks the whole Inspection page: the rest still shows, with a "Some checks couldn't
  run" line saying which. If Inspection can't run at all you get the reason and a Try again button.
- A damaged controls snapshot no longer hides all the others.
- Binding drift is measured from the right snapshot when two are taken in the same second.
- A loose (unpacked) mod's manifest can't point Pre-Trip at files outside the mod's folder, and oversized
  preview images are skipped.
- Mod lists for both games loading at once no longer race on the cache files.
- Cleanup says "No sync-conflict leftovers" instead of "All clean", and the README has a Troubleshooting section
  for protected mods and what Cleanup does.
- "File 'manifest.sii' is encrypted, password required for extraction" errors with "protected" mods. Mods that
  set the zip encryption flag (the game ignores it) now load normally, and a mod file that really can't be read
  is skipped quietly instead of raising an error.
- Mod files are no longer kept open after reading their manifest, so disabling, removing or updating a mod
  isn't blocked by Pre-Trip holding the file.
- Installing a download zip whose inner .scs can't be unpacked gives a clear message instead of a raw error.

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
