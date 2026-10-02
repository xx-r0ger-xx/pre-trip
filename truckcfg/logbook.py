"""Everything that happened to a game's setup (restore points, updates, crashes), crash analysis, the half-and-retest
crash finder, and named mod loadouts."""
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from truckcfg import conflicts, core, graphics, loadorder, mods

LOADOUTS = core.STORE / "loadouts"
BISECT = core.STORE / "crash-finder"


def _ts(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")


def _profile(game: core.Game) -> core.Profile:
    p = core.active_profile(game)
    if not p:
        raise RuntimeError(f"{game.title} has no profile yet. Launch it once and create one, then try again.")
    return p


def _profile_sii(p: core.Profile) -> Path:
    path = loadorder.find_profile_sii(p)
    if not path:
        raise RuntimeError(f"No profile.sii found for {p.name}. Launch the game and load that profile once.")
    return path


def _backup_matches(d: Path, p: core.Profile, game: core.Game) -> bool:
    """Load-order backups belong to one profile. Old ones (no id) only count when there's a single profile."""
    owner = loadorder.backup_profile(d)
    return owner == p.path.name if owner else len(core.find_profiles(game)) == 1


# ---------- timeline ----------

def events(game: core.Game) -> list[dict]:
    """Newest first. Events with a 'restore' key can be rolled back to."""
    out = []
    root = mods.game_dir(game)
    p = core.active_profile(game)
    if p:
        for s in core.list_snapshots(p):
            label = s.meta.get("label") or "manual"
            out.append({"time": s.created, "kind": "controls", "title": f"Controls snapshot · {label}",
                        "detail": f"{len(s.meta.get('files', []))} control files",
                        "restore": {"type": "snapshot", "id": s.path.name}})
    for d in sorted((loadorder.BACKUPS / game.key).glob("*")):
        if (d / "profile.sii").is_file() and p and _backup_matches(d, p, game):
            try:
                n = len(loadorder.read_order(d / "profile.sii")[1])
            except Exception:  # noqa: BLE001 - an unreadable backup is still worth listing
                n = None
            out.append({"time": _ts(d / "profile.sii"), "kind": "loadorder", "title": "Load order backup",
                        "detail": f"{n} active mods" if n is not None else "profile.sii",
                        "restore": {"type": "profile", "id": d.name}})
    for b in sorted(root.glob("config.cfg.bak-*")):
        out.append({"time": _ts(b), "kind": "graphics", "title": "Graphics settings backup", "detail": b.name,
                    "restore": {"type": "config", "id": b.name}})
    for b in root.glob("*profiles(*).bak"):
        if m := re.search(r"\(([\d.]+)", b.name):
            out.append({"time": _ts(b), "kind": "update", "title": f"Game updated to {re.sub(r'(\.0)?\.?s?$', '', m[1])}",
                        "detail": "The game backed up your profiles before migrating them."})
    if (crash := root / "game.crash.txt").is_file():
        c = crash_report(game)
        out.append({"time": c["time"], "kind": "crash", "title": "Crash", "detail": c["summary"]})
    for m in mods.local_mods(game):
        out.append({"time": datetime.fromtimestamp(m.modified).isoformat(timespec="seconds"), "kind": "mod",
                    "title": f"Installed {m.name}", "detail": f"local mod · v{m.version}" if m.version else "local mod"})
    return sorted(out, key=lambda e: e["time"], reverse=True)


def restore(game: core.Game, kind: str, ident: str) -> str:
    if core.is_running(game):
        raise RuntimeError(f"Close {game.title} first - it would overwrite the restored files when it exits.")
    if kind == "snapshot":
        prof = _profile(game)
        snap = next((s for s in core.list_snapshots(prof) if s.path.name == ident), None)
        if not snap:
            raise RuntimeError("That snapshot is gone, or belongs to another profile.")
        core.restore_snapshot(snap, prof)
        return f"Controls restored from {snap.meta.get('label') or ident}. A safety snapshot was taken first."
    if kind == "profile":
        prof = _profile(game)
        target = _profile_sii(prof)
        d = loadorder.BACKUPS / game.key / Path(ident).name
        if not ((d / "profile.sii").is_file() and _backup_matches(d, prof, game)):
            raise RuntimeError(f"That backup is gone, or belongs to a different profile than {prof.name}.")
        # only the mod list comes back: the rest of profile.sii (stats, customisation) stays as the game last saved it
        loadorder.write_order(target, game, loadorder.read_order(d / "profile.sii")[1])
        return "Load order restored. The order you had was backed up first."
    if kind == "config":
        target = graphics.config_path(game)
        src = target.with_name(Path(ident).name)
        if not (src.name.startswith("config.cfg.bak-") and src.is_file()):
            raise RuntimeError("That graphics backup is gone.")
        if target.is_file():
            shutil.copy2(target, core.unused_path(target.with_name(f"config.cfg.bak-{datetime.now():%Y%m%d-%H%M%S}")))
        shutil.copy2(src, target)
        return "Graphics settings restored. Your current config.cfg was backed up first."
    raise ValueError(f"Unknown restore type {kind!r}")


# ---------- crash analysis ----------

def crash_report(game: core.Game) -> dict:
    root = mods.game_dir(game)
    crash, log = root / "game.crash.txt", root / "game.log.txt"
    rep = {"present": crash.is_file(), "time": None, "summary": "No crash log", "exception": "", "build": "",
           "modules": [], "log_errors": [], "log_tail": [], "mounted": [], "suspects": []}
    if crash.is_file():
        text = crash.read_text(encoding="utf-8", errors="replace")
        if m := re.search(r"Crash log created on:\s*(.+)", text):
            try:
                rep["time"] = datetime.strptime(m[1].strip(), "%a %b %d %H:%M:%S %Y").isoformat(timespec="seconds")
            except ValueError:
                rep["time"] = _ts(crash)
        rep["build"] = (re.search(r"Build:\s*(\S+)", text) or [None, ""])[1]
        rep["exception"] = (re.search(r"Exception code:\s*(.+)", text) or [None, ""])[1].strip()
        # only the two call-stack sections; the "Stack:" dump and "Modules:" list after them name every loaded DLL
        stack = "".join(re.findall(r"Call stack \(\w+\):(.*?)(?=\n\S[^\n]*:\s*\n|\Z)", text, re.S))
        bin_dir = str(graphics.bin_dir(game) or "").lower()
        modules = {}
        for path in re.findall(r"([A-Za-z]:\\[^\r\n]+?\.(?:exe|dll))", stack):
            name, low = path.rsplit("\\", 1)[-1], path.lower()
            if "\\windows\\" in low:
                kind = "windows"
            elif name.lower() in ("dxgi.dll", "d3d11.dll", "dinput8.dll"):
                kind = "addon"  # ReShade or another injector sitting next to the exe
            elif bin_dir and low.startswith(bin_dir) or name.lower() == game.exe:
                kind = "game"
            elif "\\steam\\" in low:
                kind = "steam"
            else:
                kind = "addon"  # overlays, capture tools, TrackIR/Tobii bridges installed elsewhere...
            modules.setdefault(name, kind)
        rank = {"addon": 0, "game": 1, "steam": 2, "windows": 3}
        rep["modules"] = sorted(({"name": n, "kind": k} for n, k in modules.items()), key=lambda m: rank[m["kind"]])[:10]
        addons = [n for n, k in modules.items() if k == "addon"]
        rep["summary"] = (rep["exception"] or "Unknown exception") + (
            f" · add-on in the call stack: {', '.join(addons)}" if addons
            else " · raised by the game itself, no mod or add-on DLL involved")
        rep["time"] = rep["time"] or _ts(crash)
    if log.is_file():
        lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        rep["log_errors"] = [ln for ln in lines if "<ERROR>" in ln][-12:]
        rep["log_tail"] = lines[-10:]
        rep["mounted"] = re.findall(r'Mod "(.+?)" has been mounted', "\n".join(lines))
        idx = conflicts.file_index(mods.all_mods(game))
        blamed = {}
        for ln in rep["log_errors"]:
            for frag in re.findall(r"(/?[\w./-]+\.(?:sii|pmd|pmg|tobj|mat|dds|sui|ogg|bank|scs))", ln):
                for pkg in conflicts.owner_of(frag, idx):
                    blamed.setdefault(pkg, []).append(ln.split(" : ", 1)[-1][:160])
        rep["suspects"] = [{"package": p, "lines": ls[:3]} for p, ls in blamed.items()]
    return rep


# ---------- crash finder: turn half the suspects off, relaunch, repeat ----------

def _state_path(game: core.Game) -> Path:
    return BISECT / f"{game.key}.json"


def bisect_state(game: core.Game) -> dict | None:
    try:
        return json.loads(_state_path(game).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _bisect_profile(game: core.Game, st: dict) -> Path:
    """The crash finder keeps working on the profile it started on, even if another one is picked meanwhile."""
    pid = st.get("profile")
    p = next((p for p in core.find_profiles(game) if core.profile_id(p) == pid), None) if pid else _profile(game)
    if not p:
        raise RuntimeError("The profile the crash finder started on isn't there any more.")
    return _profile_sii(p)


def _apply(game: core.Game, st: dict) -> None:
    off = set(st["suspects"]) - set(st["testing"])
    order = [loadorder.Entry(p, d) for p, d in st["original"] if p not in off]
    loadorder.write_order(_bisect_profile(game, st), game, order)
    _state_path(game).parent.mkdir(parents=True, exist_ok=True)
    _state_path(game).write_text(json.dumps(st, indent=1), encoding="utf-8")


def bisect_start(game: core.Game) -> dict:
    if bisect_state(game):  # starting again would save the half-disabled order as the "original"
        raise RuntimeError("The crash finder is already running. Finish or stop it first.")
    prof = _profile(game)
    _, order = loadorder.read_order(_profile_sii(prof))
    if len(order) < 2:
        raise RuntimeError("You need at least two active mods for the crash finder to narrow anything down.")
    pk = [e.package for e in order]
    st = {"started": datetime.now().isoformat(timespec="seconds"), "round": 1, "profile": core.profile_id(prof),
          "original": [[e.package, e.display] for e in order], "suspects": pk, "testing": pk[: len(pk) // 2],
          "cleared": [], "culprit": None}
    _apply(game, st)
    return st


def bisect_report(game: core.Game, crashed: bool) -> dict:
    st = bisect_state(game)
    if not st:
        raise RuntimeError("The crash finder isn't running for this game.")
    if crashed:
        st["cleared"] += [p for p in st["suspects"] if p not in st["testing"]]
        st["suspects"] = st["testing"]
    else:
        st["cleared"] += st["testing"]
        st["suspects"] = [p for p in st["suspects"] if p not in st["testing"]]
    if len(st["suspects"]) <= 1:
        st["culprit"] = st["suspects"][0] if st["suspects"] else None
        st["testing"] = []
        bisect_stop(game)  # put everything back; the answer is in st
        return st
    st["round"] += 1
    st["testing"] = st["suspects"][: len(st["suspects"]) // 2]
    _apply(game, st)
    return st


def bisect_stop(game: core.Game) -> None:
    st = bisect_state(game)
    if not st:
        return
    order = [loadorder.Entry(p, d) for p, d in st["original"]]
    loadorder.write_order(_bisect_profile(game, st), game, order)
    _state_path(game).unlink(missing_ok=True)


# ---------- loadouts ----------

def _loadout_file(game: core.Game) -> Path:
    return LOADOUTS / f"{game.key}.json"


def list_loadouts(game: core.Game) -> dict:
    try:
        return json.loads(_loadout_file(game).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_loadout(game: core.Game, name: str, order: list[list[str]]) -> dict:
    name = name.strip()
    if not name:
        raise ValueError("Give the loadout a name.")
    data = list_loadouts(game)
    data[name] = {"created": datetime.now().isoformat(timespec="seconds"), "order": order}
    _loadout_file(game).parent.mkdir(parents=True, exist_ok=True)
    _loadout_file(game).write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data


def delete_loadout(game: core.Game, name: str) -> dict:
    data = list_loadouts(game)
    data.pop(name, None)
    _loadout_file(game).write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data
