"""Mod discovery (local mod folder + Steam Workshop), manifest parsing and simple mod file management."""
from __future__ import annotations

import ctypes
import fnmatch
import json
import os
import re
import shutil
import urllib.parse
import urllib.request
import winreg
import zipfile
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path

from truckcfg import core

STEAM_APP = {"ets2": "227300", "ats": "270880"}
MOD_EXT = {".scs", ".zip"}
WORKSHOP_CACHE = core.STORE / "workshop_cache.json"


@dataclass
class Mod:
    game: core.Game
    source: str  # "local" | "workshop"
    path: Path
    enabled: bool = True  # local only: False = parked in mod_disabled
    name: str = ""
    version: str = ""
    author: str = ""
    categories: list[str] = field(default_factory=list)
    compatible: list[str] = field(default_factory=list)
    description: str = ""
    size: int = 0
    modified: float = 0.0
    workshop_id: str | None = None
    universal: bool = False  # has a package with no version restriction (SCS fallback package)
    display: str = ""  # manifest display_name - what the game writes into active_mods
    pkg_id: str = ""  # set for "missing" rows: active in the profile but not installed

    @property
    def package(self) -> str:
        """The id the game uses for this mod in profile.sii's active_mods list."""
        if self.pkg_id:
            return self.pkg_id
        if self.workshop_id:
            return f"mod_workshop_package.{int(self.workshop_id):016X}"
        return self.path.name if self.path.is_dir() else self.path.stem

    def compat(self, game_version: str | None) -> str:
        """'ok', 'outdated' or 'unknown' against the installed game version."""
        if self.universal:
            return "ok"
        if not (game_version and self.compatible):
            return "unknown"
        return "ok" if any(fnmatch.fnmatch(game_version, p) for p in self.compatible) else "outdated"


# ---------- locations ----------

def game_dir(game: core.Game) -> Path:
    return core.documents_dir() / game.title


def mod_dir(game: core.Game) -> Path:
    return game_dir(game) / "mod"


def disabled_dir(game: core.Game) -> Path:
    return game_dir(game) / "mod_disabled"


def steam_libraries() -> list[Path]:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            steam = Path(winreg.QueryValueEx(k, "SteamPath")[0])
    except OSError:
        return []
    libs = [steam]
    vdf = steam / "steamapps" / "libraryfolders.vdf"
    if vdf.is_file():
        for m in re.finditer(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8", errors="replace")):
            p = Path(m[1].replace("\\\\", "\\"))
            if p not in libs:
                libs.append(p)
    return libs


def workshop_dirs(game: core.Game) -> list[Path]:
    return [d for lib in steam_libraries()
            if (d := lib / "steamapps" / "workshop" / "content" / STEAM_APP[game.key]).is_dir()]


def game_version(game: core.Game) -> str | None:
    """Best guess at the installed version, from game.log or the game's own '(1.61.2.0s).bak' profile backups."""
    root = game_dir(game)
    found = []
    for log in root.glob("game.log*.txt"):
        try:
            with open(log, encoding="utf-8", errors="replace") as f:
                head = f.read(4000)
        except OSError:
            continue
        if m := re.search(r"ver\.(\d+\.\d+\.\d+(?:\.\d+)?)", head):
            found.append((log.stat().st_mtime, m[1]))
    for bak in root.glob("*profiles(*).bak"):
        if m := re.search(r"\((\d+\.\d+\.\d+(?:\.\d+)?)", bak.name):
            found.append((bak.stat().st_mtime, m[1]))
    return max(found)[1] if found else None


def short_version(v: str | None) -> str:
    return ".".join(v.split(".")[:2]) if v else "unknown"


# ---------- manifests ----------

SII_PAIR_RE = re.compile(r'^\s*(\w+)(\[\d*\])?\s*:\s*"([^"]*)"', re.M)


def parse_sii_strings(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for m in SII_PAIR_RE.finditer(text):
        out.setdefault(m[1], []).append(m[3])
    return out


SCS_MARKUP_RE = re.compile(r"\[(?:/?[a-z_]+|#[0-9a-f]{6,8}|img[^\]]*|link[^\]]*)\]", re.I)


def strip_markup(text: str) -> str:
    """Drop SCS description colour/format tags like [red], [normal], [#ff0000], [img src=...]."""
    return SCS_MARKUP_RE.sub("", text).strip()


def _first(d, key):
    return d.get(key, [""])[0]


def _apply_manifest(mod: Mod, read) -> None:
    """read(name) -> text or None, relative to the package root."""
    text = read("manifest.sii")
    if not text:
        return
    m = parse_sii_strings(text)
    mod.name = mod.display = _first(m, "display_name") or mod.name
    mod.version = _first(m, "package_version")
    mod.author = _first(m, "author")
    mod.categories = m.get("category", [])
    mod.compatible = mod.compatible or m.get("compatible_versions", [])
    if desc := _first(m, "description_file"):
        mod.description = strip_markup(read(desc) or "")


def _zip_reader(path: Path):
    try:
        z = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError):
        return None  # HashFS .scs or unreadable: no manifest available

    def read(name):
        try:
            return z.read(name).decode("utf-8", errors="replace")
        except KeyError:
            return None
    return read


def _dir_reader(path: Path):
    def read(name):
        f = path / name
        return f.read_text(encoding="utf-8", errors="replace") if f.is_file() else None
    return read


def _reader(path: Path):
    return _dir_reader(path) if path.is_dir() else _zip_reader(path)


def _size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for dirpath, _, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total


def _pretty_filename(stem: str) -> str:
    return re.sub(r"[_]+", " ", stem).strip()


def local_mods(game: core.Game) -> list[Mod]:
    out = []
    for folder, enabled in ((mod_dir(game), True), (disabled_dir(game), False)):
        if not folder.is_dir():
            continue
        for p in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
            if not (p.is_dir() or p.suffix.lower() in MOD_EXT):
                continue
            mod = Mod(game, "local", p, enabled, name=_pretty_filename(p.stem), size=_size(p),
                      modified=p.stat().st_mtime)
            if read := _reader(p):
                _apply_manifest(mod, read)
            out.append(mod)
    return out


def workshop_mods(game: core.Game) -> list[Mod]:
    out = []
    for root in workshop_dirs(game):
        for item in sorted(root.iterdir()):
            if not item.is_dir():
                continue
            mod = Mod(game, "workshop", item, name=f"Workshop item {item.name}", workshop_id=item.name,
                      size=_size(item), modified=item.stat().st_mtime)
            versions = item / "versions.sii"
            pkg = None
            if versions.is_file():
                text = versions.read_text(encoding="utf-8", errors="replace")
                for block in re.findall(r"package_version_info\s*:\s*\S+\s*\{(.*?)\}", text, re.S):
                    info = parse_sii_strings(block)
                    if "informational: true" in block:
                        continue
                    if not info.get("compatible_versions"):
                        mod.universal = True
                    mod.compatible += info.get("compatible_versions", [])
                    if pkg is None and (name := _first(info, "package_name")):
                        for cand in (item / name, item / f"{name}.scs", item / f"{name}.zip"):
                            if cand.exists():
                                pkg = cand
                                break
            if pkg and (read := _reader(pkg)):
                _apply_manifest(mod, read)
            out.append(mod)
    return out


def all_mods(game: core.Game) -> list[Mod]:
    return local_mods(game) + workshop_mods(game)


# ---------- workshop titles (Steam public API, cached) ----------

def load_workshop_cache() -> dict:
    try:
        return json.loads(WORKSHOP_CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def fetch_workshop_details(ids: list[str]) -> dict:
    """Title/author info for Workshop ids. Merges into the on-disk cache and returns it."""
    cache = load_workshop_cache()
    todo = [i for i in ids if i not in cache]
    if todo:
        form = {"itemcount": len(todo)} | {f"publishedfileids[{n}]": i for n, i in enumerate(todo)}
        req = urllib.request.Request(
            "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/",
            data=urllib.parse.urlencode(form).encode(), method="POST")
        with urllib.request.urlopen(req, timeout=15) as r:
            details = json.load(r).get("response", {}).get("publishedfiledetails", [])
        for d in details:
            if d.get("result") == 1:
                cache[d["publishedfileid"]] = {"title": d.get("title", ""),
                                               "time_updated": d.get("time_updated", 0)}
        WORKSHOP_CACHE.parent.mkdir(parents=True, exist_ok=True)
        WORKSHOP_CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return cache


def apply_workshop_titles(mods: list[Mod], cache: dict) -> None:
    for m in mods:
        if m.workshop_id and (t := cache.get(m.workshop_id, {}).get("title")):
            m.name = t


# ---------- file operations (local mods only) ----------

def _guard(game: core.Game):
    if core.is_running(game):
        raise RuntimeError(f"Close {game.title} first - it keeps mod files locked while running.")


def set_enabled(mod: Mod, enabled: bool) -> Path:
    if mod.source != "local":
        raise RuntimeError("Workshop mods are managed by Steam - unsubscribe on the Workshop page.")
    _guard(mod.game)
    dest_dir = mod_dir(mod.game) if enabled else disabled_dir(mod.game)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / mod.path.name
    if dest.exists():
        raise FileExistsError(f"{dest} already exists.")
    shutil.move(str(mod.path), dest)
    return dest


def install(game: core.Game, src: Path) -> Path:
    if not (src.is_dir() or src.suffix.lower() in MOD_EXT):
        raise ValueError("Mods are .scs or .zip files.")
    _guard(game)
    dest = mod_dir(game) / src.name
    if dest.exists() or (disabled_dir(game) / src.name).exists():
        raise FileExistsError(f"A mod called {src.name} is already installed.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    (shutil.copytree if src.is_dir() else shutil.copy2)(src, dest)
    return dest


class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT), ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR), ("fFlags", ctypes.c_ushort), ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR)]


def recycle(path: Path) -> None:
    """Send to the Recycle Bin (undoable) rather than deleting."""
    FO_DELETE, FOF_SILENT, FOF_NOCONFIRMATION, FOF_ALLOWUNDO, FOF_NOERRORUI = 3, 0x4, 0x10, 0x40, 0x400
    op = _SHFILEOPSTRUCTW(None, FO_DELETE, str(path) + "\0", None,
                          FOF_SILENT | FOF_NOCONFIRMATION | FOF_ALLOWUNDO | FOF_NOERRORUI, False, None, None)
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if rc or op.fAnyOperationsAborted:
        raise OSError(f"Couldn't move {path.name} to the Recycle Bin (code {rc}).")


def remove(mod: Mod) -> None:
    if mod.source != "local":
        raise RuntimeError("Workshop mods are managed by Steam - unsubscribe on the Workshop page.")
    _guard(mod.game)
    recycle(mod.path)


def fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024
