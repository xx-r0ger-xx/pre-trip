# Roadmap

Ideas and improvements that aren't built yet. Newest first.

## Compare page: one direction switch + one action button
*Logged 2026-09-30.*

The Compare page has four buttons for what is really one action: Copy selected to ATS, Copy selected to ETS2,
Sync all ETS2 → ATS, and Sync all ATS → ETS2. It feels clunky.

Replace them with:
- a segmented direction switch, `ATS → ETS2 | ETS2 → ATS`, defaulting to the game whose `controls.sii` changed
  most recently (the one marked NEWER today);
- a single action button that relabels itself: "Sync all N differences" with no selection, "Copy N selected"
  with rows selected.

Keep the confirmation dialog, and make it name the game being overwritten so the direction can't be missed.
