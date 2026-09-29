# Truck Config Manager

Small Windows desktop app (Python + tkinter, no dependencies) for Euro Truck Simulator 2 and
American Truck Simulator controller bindings.

- **Snapshots** – saves `controls.sii` and `gearbox_layout_*.sii` from a game profile to
  `%USERPROFILE%\Documents\TruckSim-Configs\<game>\<profile>\<timestamp>`. You can diff any snapshot
  against the live file and restore it after a game update messes up your bindings.
- **Compare games** – shows every binding/constant that differs between ETS2 and ATS, and copies
  selected (or all shared) bindings from one game to the other. It edits lines in place, so actions
  that exist in only one game (e.g. ATS window shades) are left alone.
- **Drift warning** – on launch, warns if a game's controls changed since its latest snapshot.
  The first launch takes a `baseline` snapshot automatically.

Every write refuses to run while the target game is open (the game rewrites `controls.sii` on exit),
and it takes an automatic snapshot first, so every change can be undone.

## Run

```
pythonw app.pyw
```

Tests: `python -m unittest -v tests.test_core`

## Notes

- Profiles are found under the Windows *Documents* folder (wherever it is redirected, e.g. Proton Drive):
  `<Documents>\<Game>\steam_profiles\*` and `...\profiles\*`.
- Keep game profiles out of live cloud sync if you can: sync clients racing the game produce
  "Name clash" / conflict copies and can revert bindings.
