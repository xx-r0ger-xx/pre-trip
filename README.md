# Truck Config Manager

Windows desktop utility (Python + tkinter, no dependencies, dark dashboard UI) for Euro Truck Simulator 2 and
American Truck Simulator controller bindings.

- **Snapshots** – saves `controls.sii` and `gearbox_layout_*.sii` from a game profile to
  `%USERPROFILE%\Documents\TruckSim-Configs\<game>\<profile>\<timestamp>`. You can diff any snapshot
  against the live file and restore it after a game update messes up your bindings.
- **Compare games** – shows every binding/constant that differs between ETS2 and ATS, and copies
  selected (or all shared) bindings from one game to the other. It edits lines in place, so actions
  that exist in only one game (e.g. ATS window shades) are left alone.
- **Mods** – lists local (`<Documents>\<Game>\mod`) and Steam Workshop mods with name, author,
  version, size and whether they declare support for the installed game version. Local mods can be
  installed, disabled (parked in `mod_disabled`, so the game ignores them) or sent to the Recycle Bin.
  Workshop titles come from Steam's public API and are cached in `TruckSim-Configs\workshop_cache.json`.
  Activation and load order still happen in the game's own Mod Manager.
- **Install mods** – one window with three ways in: paste a Steam Workshop link (checked against the
  selected game, then subscribed through the game's own Steam API), pick `.scs`/`.zip` files from your
  Downloads folder, or **Browse for files…**. You can also drag mod files onto the window. Zips that
  only wrap `.scs` files are unpacked, because the game can't load them wrapped.
- **Cleanup** – finds cloud-sync leftovers (`(# Name clash …)`, ` - Copy`, `-DESKTOP-…`) in the game
  folders and moves them to `TruckSim-Configs\quarantine\<timestamp>` with a manifest. Nothing is
  deleted. Also flags profiles missing `profile.sii` / `config_local.cfg` / saves.
- **Drift warning** – on launch, warns if a game's controls changed since its latest snapshot.
  The first launch takes a `baseline` snapshot automatically.

Every write refuses to run while the target game is open (the game rewrites `controls.sii` on exit),
and it takes an automatic snapshot first, so every change can be undone.

## Run

```
pythonw app.pyw
```

## Web UI (preview)

`webapp.pyw` is a new front end on the same back end, in a native window (pywebview + WebView2):

- **Pre-Trip** – health check with gauges: mods current for the installed version, file overlaps between
  active mods, bindings changed since the last snapshot, days since the last crash.
- **Twin Rigs** – ETS2 and ATS side by side: controls, graphics settings (`config.cfg`), ReShade files
  and preset, and matching mods. One direction switch and one Sync button. Hidden on PCs with one game.
- **Studio** – drag-and-drop load order in colored group lanes, live ▲/▼ badges for files a mod wins or
  loses to another, author notes, and an auto-sort that follows each author's own instructions.
- **Garage** – mod gallery using each mod's preview image, plus named loadouts
  (`TruckSim-Configs\loadouts`).
- **Logbook** – timeline of snapshots, load-order and graphics backups, game updates and crashes, each
  restorable. Reads `game.crash.txt`/`game.log.txt`, and a crash finder that switches half the mods off
  per round to find the one crashing the game.

```
pip install pywebview
pythonw webapp.pyw
```

Set `TCM_GAMES=ets2` (or `ats`) to preview the one-game experience on a PC that has both.

Tests: `python -m unittest -v tests.test_core tests.test_mods_cleanup`

## Notes

- Profiles are found under the Windows *Documents* folder (wherever it is redirected, e.g. Proton Drive):
  `<Documents>\<Game>\steam_profiles\*` and `...\profiles\*`.
- Keep game profiles out of live cloud sync if you can: sync clients racing the game produce
  "Name clash" / conflict copies and can revert bindings.
