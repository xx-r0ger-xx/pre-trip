"""Profile discovery, controls.sii parsing/merging, and snapshot storage for SCS truck games."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import unicodedata
import winreg
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

STORE = Path.home() / "Documents" / "TruckSim-Configs"


@dataclass(frozen=True)
class Game:
    key: str
    title: str
    exe: str


GAMES = {
    "ets2": Game("ets2", "Euro Truck Simulator 2", "eurotrucks2.exe"),
    "ats": Game("ats", "American Truck Simulator", "amtrucks.exe"),
}

# controls.sii plus per-gearbox layouts; skips stray "- Copy" / "Name clash" duplicates
CONTROL_FILE_RE = re.compile(r"^(controls|gearbox_layout_[a-z0-9_]+)\.sii$", re.I)
LINE_RE = re.compile(r'^(\s*config_lines\[\d+\]: ")(\w+) (\S+) (.*)("\s*)$')


@dataclass(frozen=True)
class Profile:
    game: Game
    path: Path

    @property
    def name(self) -> str:
        try:
            name = bytes.fromhex(self.path.name).decode("utf-8")
        except ValueError:
            return self.path.name
        # control characters mean it isn't really a name; anything else (CJK spaces, emoji, ZWJ) is shown as-is
        return self.path.name if not name.strip() or any(unicodedata.category(c) == "Cc" for c in name) else name

    @property
    def label(self) -> str:
        kind = "Steam" if self.path.parent.name == "steam_profiles" else "local"
        return f"{self.name} ({kind})"


def documents_dir() -> Path:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
        return Path(os.path.expandvars(winreg.QueryValueEx(k, "Personal")[0]))


def find_profiles(game: Game) -> list[Profile]:
    root = documents_dir() / game.title
    out = []
    for sub in ("steam_profiles", "profiles"):
        d = root / sub
        if d.is_dir():
            out += [Profile(game, p) for p in sorted(d.iterdir()) if (p / "controls.sii").exists()]
    return out


def profile_id(profile: Profile) -> str:
    """Stable id: "steam_profiles/<hex>" or "profiles/<hex>" (the same name can exist in both)."""
    return f"{profile.path.parent.name}/{profile.path.name}"


def last_played(profile: Profile) -> float:
    """When the game last saved anything for this profile."""
    from truckcfg import loadorder  # local import: loadorder imports core
    files = [profile.path / "controls.sii", profile.path / "config_local.cfg", loadorder.find_profile_sii(profile)]
    return max((f.stat().st_mtime for f in files if f and f.is_file()), default=0.0)


def _selected_file() -> Path:
    return STORE / "selected_profiles.json"


def _selected() -> dict:
    try:
        data = json.loads(_selected_file().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


_SESSION: dict[str, str] = {}  # game key -> profile id chosen automatically, held until the app restarts


def active_profile(game: Game) -> Profile | None:
    """The profile every read and write uses: the one picked in the app, else the one played most recently when
    Pre-Trip first looked. That automatic choice is held for the session, so what the screen shows and where a save
    goes can't drift apart if another profile is played while Pre-Trip is open."""
    ps = find_profiles(game)
    if not ps:
        return None
    for want in (_selected().get(game.key), _SESSION.get(game.key)):
        if p := next((p for p in ps if profile_id(p) == want), None):
            return p
    p = max(ps, key=last_played)
    _SESSION[game.key] = profile_id(p)
    return p


def select_profile(game: Game, pid: str) -> Profile:
    p = next((p for p in find_profiles(game) if profile_id(p) == pid), None)
    if not p:
        raise RuntimeError(f"That {game.title} profile isn't there any more.")
    data = _selected()
    data[game.key] = pid
    _selected_file().parent.mkdir(parents=True, exist_ok=True)
    write_text_atomic(_selected_file(), json.dumps(data, indent=1))
    return p


def control_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and CONTROL_FILE_RE.match(p.name))


def unused_path(path: Path) -> Path:
    """path, or path_1, path_2... - backups are named by the second, and two in one second must not overwrite each other."""
    n, cand = 1, path
    while cand.exists():
        cand = path.with_name(f"{path.name}_{n}")
        n += 1
    return cand


def controls_changed(profile: Profile) -> datetime:
    """When the game last saved this profile's controls.sii."""
    return datetime.fromtimestamp((profile.path / "controls.sii").stat().st_mtime)


def is_running(game: Game) -> bool:
    """Whether the game is open. Guards every write, so if Windows can't tell us, that's an error - never "not running"."""
    try:
        r = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {game.exe}", "/NH"], capture_output=True, text=True,
                           errors="replace", timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
    except (OSError, subprocess.SubprocessError) as e:
        raise RuntimeError(f"Couldn't check whether {game.title} is running ({e}). Nothing was changed.") from e
    if r.returncode != 0 or r.stdout is None:
        raise RuntimeError(f"Couldn't check whether {game.title} is running (tasklist exit {r.returncode}). "
                           "Nothing was changed.")
    return game.exe.lower() in r.stdout.lower()


def seems_running(game: Game) -> bool:
    """For display only: is_running, with "can't tell" shown as running so the UI stays cautious."""
    try:
        return is_running(game)
    except RuntimeError:
        return True


# ---------- bindings ----------

Key = tuple[str, str]  # (kind, name) e.g. ("mix", "horn"), ("constant", "c_rsteersens")


def read_text(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tcm-tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)


def parse_bindings(text: str) -> dict[Key, str]:
    out = {}
    for line in text.splitlines():
        m = LINE_RE.match(line)
        if m:
            out[(m[2], m[3])] = m[4]
    return out


# any device.input reference (keyboard.h, joy.b9, mouse.x...) except the game's own semantical.* placeholders
REAL_INPUT_RE = re.compile(r"\b(?!semantical\b)[a-z_]\w*\.\w+")


def is_mapped(kind: str, value: str | None) -> bool:
    """True if a binding uses a real input. Constants are settings, not bindings, so always count."""
    if value is None:
        return False
    return kind == "constant" or bool(REAL_INPUT_RE.search(value))


_DEVICE_RE = re.compile(r"\b([a-z]+)(\d*)\.(\w+)")
_PRESS_RE = re.compile(r"\b(short|long)_press\(([^()]*)\)")
_MODIFIER_RE = re.compile(r"^modifier\(\s*([^,()]+?)\s*,\s*(.+)\)$")  # modifier(no_cstm_mod, short_press(joy.b11))


def _pretty_token(m: re.Match) -> str:
    dev, num, name = m[1], m[2], m[3]
    device = {"keyboard": "Key", "joy": "Joy", "mouse": "Mouse"}.get(dev, dev.capitalize()) + num
    if b := re.fullmatch(r"b(\d+)", name):
        name = f"Btn {b[1]}"
    elif p := re.fullmatch(r"pov(\d*)_(\w+)", name):
        name = f"POV {p[2].capitalize()}"
    elif k := re.fullmatch(r"key(\d)", name):
        name = k[1]
    else:
        name = name.upper()
    return f"{device} {name}"


def pretty_input(kind: str, value: str | None) -> str | None:
    """Human-readable binding, e.g. '`keyboard.h?0 | joy.b9?0 | semantical.horn?0`' -> 'Key H  ·  Joy Btn 9'."""
    if value is None or kind == "constant":
        return value
    parts = []
    for part in re.split(r"\s*\|\|?\s*", value.strip().strip("`")):
        part = re.sub(r"\?\d+", "", part).strip()
        if not part or part.startswith(("semantical.", "unbound")):
            continue
        part = _PRESS_RE.sub(lambda m: f"{m[2]} ({'tap' if m[1] == 'short' else 'hold'})", part)
        if m := _MODIFIER_RE.match(part):  # no_cstm_mod = only when no custom modifier is held
            part = f"{m[2]} (no modifier)" if m[1] == "no_cstm_mod" else f"{m[1]} + {m[2]}"
        parts.append(_DEVICE_RE.sub(_pretty_token, part))
    return "  ·  ".join(parts) or "Unbound"


@dataclass(frozen=True)
class DiffRow:
    kind: str
    name: str
    left: str | None  # None = action missing on that side
    right: str | None

    @property
    def mapped(self) -> bool:
        return is_mapped(self.kind, self.left) or is_mapped(self.kind, self.right)


def diff_bindings(left: dict[Key, str], right: dict[Key, str]) -> list[DiffRow]:
    keys = list(left) + [k for k in right if k not in left]
    return [DiffRow(k[0], k[1], left.get(k), right.get(k)) for k in keys if left.get(k) != right.get(k)]


def apply_bindings(text: str, updates: dict[Key, str]) -> tuple[str, list[Key]]:
    """Rewrite values of existing lines in place. Returns (new_text, keys_not_found_in_target)."""
    pending = dict(updates)
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        body = line.rstrip("\r\n")
        m = LINE_RE.match(body)
        if m and (m[2], m[3]) in pending:
            val = pending.pop((m[2], m[3]))
            lines[i] = f"{m[1]}{m[2]} {m[3]} {val}{m[5]}" + line[len(body):]
    return "".join(lines), list(pending)


def copy_bindings(src: Profile, dst: Profile, keys: list[Key]) -> tuple[int, list[Key]]:
    """Copy the given bindings from src's controls.sii into dst's. Snapshots dst first."""
    if is_running(dst.game):
        raise RuntimeError(f"Close {dst.game.title} first - it overwrites controls.sii on exit.")
    src_b = parse_bindings(read_text(src.path / "controls.sii"))
    updates = {k: src_b[k] for k in keys if k in src_b}
    target = dst.path / "controls.sii"
    new_text, missing = apply_bindings(read_text(target), updates)
    take_snapshot(dst, f"auto-before-copy-from-{src.game.key}")
    write_text_atomic(target, new_text)
    take_snapshot(dst, f"after-copy-from-{src.game.key}")  # so the drift check doesn't flag our own change
    return len(updates) - len(missing), missing


# ---------- snapshots ----------

@dataclass(frozen=True)
class Snapshot:
    path: Path
    meta: dict

    @property
    def created(self) -> str:
        return self.meta.get("created", "")

    @property
    def label(self) -> str:
        return self.meta.get("label", "")


def snapshot_root(profile: Profile) -> Path:
    """Snapshots live under the profile's folder name. A local profile that shares its name with a Steam one gets
    its own "-local" folder so the two never see each other's snapshots."""
    hexname = profile.path.name
    twin = profile.path.parent.parent / "steam_profiles" / hexname / "controls.sii"
    local = profile.path.parent.name == "profiles"
    return STORE / profile.game.key / (f"{hexname}-local" if local and twin.exists() else hexname)


def take_snapshot(profile: Profile, label: str = "") -> Snapshot:
    now = datetime.now()
    slug = re.sub(r"[^\w-]+", "-", label).strip("-")[:40]
    dest = snapshot_root(profile) / (now.strftime("%Y%m%d-%H%M%S") + (f"-{slug}" if slug else ""))
    n = 1
    while dest.exists():
        dest = dest.with_name(f"{dest.name}_{n}")
        n += 1
    dest.mkdir(parents=True)
    files = control_files(profile.path)
    for f in files:
        shutil.copy2(f, dest / f.name)
    meta = {"game": profile.game.key, "profile": profile.name, "source": str(profile.path),
            "created": now.isoformat(timespec="seconds"), "label": label, "files": [f.name for f in files]}
    (dest / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return Snapshot(dest, meta)


def list_snapshots(profile: Profile) -> list[Snapshot]:
    root = snapshot_root(profile)
    if not root.is_dir():
        return []
    snaps = []
    for d in root.iterdir():
        mf = d / "meta.json"
        try:  # one damaged snapshot must not hide the healthy ones
            meta = json.loads(mf.read_text(encoding="utf-8")) if mf.is_file() else None
        except (OSError, ValueError):
            meta = None
        if isinstance(meta, dict):
            snaps.append((Snapshot(d, meta), mf.stat().st_mtime_ns))
    # "created" has one-second resolution and a sync takes before+after snapshots in the same second: break ties by
    # when meta.json was written (last), so snaps[0] is really the newest and drift isn't measured from "before"
    return [s for s, _ in sorted(snaps, key=lambda x: (str(x[0].created), x[1]), reverse=True)]


def diff_snapshot(snap: Snapshot, profile: Profile) -> tuple[list[DiffRow], list[str]]:
    """Controls diff (snapshot=left, current=right) and names of other control files that differ."""
    rows = diff_bindings(parse_bindings(read_text(snap.path / "controls.sii")),
                         parse_bindings(read_text(profile.path / "controls.sii")))
    other = []
    names = {f.name for f in control_files(snap.path)} | {f.name for f in control_files(profile.path)}
    for n in sorted(names - {"controls.sii"}):
        a, b = snap.path / n, profile.path / n
        if not (a.exists() and b.exists()) or a.read_bytes() != b.read_bytes():
            other.append(n)
    return rows, other


def restore_snapshot(snap: Snapshot, profile: Profile) -> Snapshot:
    """Push snapshot files back into the game profile. Returns the safety snapshot taken first."""
    if is_running(profile.game):
        raise RuntimeError(f"Close {profile.game.title} first - it overwrites controls.sii on exit.")
    safety = take_snapshot(profile, "auto-before-restore")
    for f in control_files(snap.path):
        write_text_atomic(profile.path / f.name, read_text(f))
    take_snapshot(profile, f"after-restore-{snap.path.name}")
    return safety
