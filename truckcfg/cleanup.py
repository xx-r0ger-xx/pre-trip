"""Find sync-conflict leftovers in the game folders and move them to a quarantine folder (never deletes)."""
from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from truckcfg import core, mods

# Proton "(# Name clash 2026-09-29 abc123C #)", OneDrive "-DESKTOP-XYZ", Windows " - Copy" / " - Copy (2)"
CLUTTER_RE = re.compile(r" \(# Name clash [^)]*#\)| - Copy(?: \(\d+\))?(?=\.[^.\\/]+$|$)|-DESKTOP-[A-Z0-9]+(?=\.|$)")
SKIP_DIRS = {"mod", "mod_disabled", "cache", "screenshot", "music"}
QUARANTINE = core.STORE / "quarantine"


@dataclass(frozen=True)
class Clutter:
    game: core.Game
    path: Path
    size: int
    modified: float

    @property
    def rel(self) -> str:
        return str(self.path.relative_to(mods.game_dir(self.game)))


def is_clutter(name: str) -> bool:
    return bool(CLUTTER_RE.search(name))


def _size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def find_clutter(game: core.Game) -> list[Clutter]:
    root = mods.game_dir(game)
    out = []
    if not root.is_dir():
        return out
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        if here == root:
            dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
        for d in list(dirnames):
            if is_clutter(d):  # whole conflicted folder: report once, don't descend
                p = here / d
                out.append(Clutter(game, p, _size(p), p.stat().st_mtime))
                dirnames.remove(d)
        for f in filenames:
            if is_clutter(f):
                p = here / f
                st = p.stat()
                out.append(Clutter(game, p, st.st_size, st.st_mtime))
    return sorted(out, key=lambda c: c.rel.lower())


def quarantine(items: list[Clutter]) -> Path:
    """Move items under STORE/quarantine/<timestamp>/<game>/<relative path>, with a manifest for undo."""
    if not items:
        raise ValueError("Nothing to quarantine.")
    for g in {c.game for c in items}:
        if core.is_running(g):
            raise RuntimeError(f"Close {g.title} first.")
    dest_root = QUARANTINE / datetime.now().strftime("%Y%m%d-%H%M%S")
    moved = []
    for c in items:
        dest = dest_root / c.game.key / c.rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(c.path), dest)
        moved.append({"from": str(c.path), "to": str(dest)})
    (dest_root / "manifest.json").write_text(json.dumps(moved, indent=2), encoding="utf-8")
    return dest_root


# ---------- profile health ----------

def profile_health(profile: core.Profile) -> list[tuple[str, str]]:
    """[(level, message)] where level is 'ok', 'warn' or 'bad'."""
    out = []
    files = {p.name.lower() for p in profile.path.iterdir()}
    if "profile.sii" not in files:
        out.append(("bad", "profile.sii is missing. Launch the game with Steam Cloud enabled to restore it; "
                           "until then the game can't load this profile's mods or save list."))
    if "config_local.cfg" not in files:
        out.append(("warn", "config_local.cfg is missing (per-profile settings will reset to defaults)."))
    if not (profile.path / "save").is_dir():
        out.append(("warn", "No save folder in this profile."))
    if not out:
        out.append(("ok", "Profile files look complete."))
    return out
