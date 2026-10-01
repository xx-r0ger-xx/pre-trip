# Roadmap

Ideas and improvements that aren't built yet. Newest first.

The web UI (`webapp.pyw`) is the main app. The tkinter app (`app.pyw`) is kept as is and isn't getting new features.

## v1.1: update check
*Logged 2026-10-01.*

Tell people when a newer Pre-Trip is out, so nobody stays on an old version by accident.

- On launch (at most once a day), ask GitHub for the latest release:
  `GET https://api.github.com/repos/xx-r0ger-xx/pre-trip/releases/latest`, then compare its tag with `__version__`.
- If it's newer, show a small "v1.1.0 available" badge in the rail and a dismissible line on Inspection, with a
  **What's new** link (the release notes) and **Download** (the release page).
- Never download or install anything by itself. The exe isn't signed, so updating stays the user's choice.
- Silent when offline or rate-limited, and the result is cached in `TruckSim-Configs`. A setting turns the check off.
- Privacy: one anonymous request to GitHub's public API, no tracking. Say so in the README.
- Tests: newer / same / older / malformed tags, offline, cache freshness.

## Winter scenery
*Logged 2026-10-01.*

A snowy road scene to swap in for the fall "Golden Hour" backdrop for the holidays (reminder set for 2026-12-21).
Could become seasonal: pick the scene by date, or let people choose it next to the scenery toggle.

## Done

### Compare page: one direction switch + one action button
*Logged 2026-09-30, done 2026-10-01 in the web UI.*

The tkinter Compare page had four buttons for one action (copy selected / sync all, in each direction). The web UI's
**ATS/ETS2 Sync** page (first called Twin Rigs) replaces it with a direction switch that defaults to the more recently changed game, one
relabelling Sync button, and a confirmation that names the game being overwritten. The tkinter page is left unchanged.
