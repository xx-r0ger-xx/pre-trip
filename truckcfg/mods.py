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
import zlib
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
    package_path: Path | None = None  # the .scs/.zip/folder holding manifest.sii (Workshop: the chosen version)
    icon: str = ""  # manifest icon, relative to package_path

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
    mod.icon = _first(m, "icon")
    mod.compatible = mod.compatible or m.get("compatible_versions", [])
    if desc := _first(m, "description_file"):
        mod.description = strip_markup(read(desc) or "")


def zip_read(z: zipfile.ZipFile, name: str) -> bytes | None:
    """One member's bytes, or None if it can't be read. Some mod authors set the zip "encrypted" flag on files
    that aren't really encrypted to stop people unpacking their mods; the game ignores the flag, so we do too.
    Really encrypted, exotic-compression or damaged members come back as None instead of raising."""
    try:
        info = z.getinfo(name)
        if info.flag_bits & 0x1:
            info.flag_bits &= ~0x1
        return z.read(info)
    except (KeyError, RuntimeError, NotImplementedError, zipfile.BadZipFile, zlib.error, EOFError, OSError, ValueError):
        return None


def _zip_reader(path: Path):
    try:
        zipfile.ZipFile(path).close()
    except (zipfile.BadZipFile, OSError):
        return None  # HashFS .scs or unreadable: no manifest available

    def read(name):
        try:  # opened per read so the mod file isn't left locked (Windows) and can be moved/removed
            with zipfile.ZipFile(path) as z:
                data = zip_read(z, name)
        except (zipfile.BadZipFile, OSError):
            return None
        return None if data is None else data.decode("utf-8", errors="replace")
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
            mod.package_path = p
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
            mod.package_path = pkg
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


def inspect_archive(src: Path) -> tuple[str, list[str]]:
    """What a downloaded file is: ('mod', [src.name]) for a mod the game can load as-is, ('bundle', [inner .scs
    names]) for a download zip wrapping one or more .scs mods, or ('unknown', [])."""
    if src.is_dir():
        return ("mod", [src.name]) if (src / "manifest.sii").is_file() or (src / "def").is_dir() else ("unknown", [])
    if src.suffix.lower() not in MOD_EXT:
        return "unknown", []
    try:
        with zipfile.ZipFile(src) as z:
            names = z.namelist()
    except (zipfile.BadZipFile, OSError):
        # HashFS .scs (SCS's own archive format) can't be listed, but it's a mod by definition
        return ("mod", [src.name]) if src.suffix.lower() == ".scs" else ("unknown", [])
    if "manifest.sii" in names or any(n.startswith("def/") for n in names):
        return "mod", [src.name]
    inner = [n for n in names if n.lower().endswith(".scs") and not n.endswith("/")]
    return ("bundle", inner) if inner else ("unknown", [])


def installed_names(game: core.Game) -> set[str]:
    return {p.name.lower() for d in (mod_dir(game), disabled_dir(game)) if d.is_dir() for p in d.iterdir()}


def install(game: core.Game, src: Path) -> list[Path]:
    """Copy a mod into the game's mod folder. A zip that only wraps .scs files has those extracted instead.
    Returns the installed paths."""
    kind, inner = inspect_archive(src)
    if kind == "unknown":
        raise ValueError(f"{src.name} doesn't look like an ETS2/ATS mod (no manifest.sii, def folder or .scs inside).")
    _guard(game)
    have = installed_names(game)
    targets = [Path(n).name for n in inner]
    if clash := [n for n in targets if n.lower() in have]:
        raise FileExistsError(f"Already installed: {', '.join(clash)}")
    out_dir = mod_dir(game)
    out_dir.mkdir(parents=True, exist_ok=True)
    if kind == "mod":
        dest = out_dir / src.name
        (shutil.copytree if src.is_dir() else shutil.copy2)(src, dest)
        return [dest]
    out = []
    with zipfile.ZipFile(src) as z:
        for member, name in zip(inner, targets):
            dest = out_dir / name
            info = z.getinfo(member)
            info.flag_bits &= ~0x1  # fake "encrypted" flag, see zip_read
            try:
                with z.open(info) as fin, open(dest, "wb") as fout:
                    shutil.copyfileobj(fin, fout, 1024 * 1024)
            except (RuntimeError, NotImplementedError, zipfile.BadZipFile, zlib.error, EOFError) as e:
                dest.unlink(missing_ok=True)
                raise ValueError(f"Couldn't unpack {name} from {src.name} (password-protected or damaged); "
                                 f"extract it yourself and install the .scs.") from e
            out.append(dest)
    return out


# ---------- finding downloaded mods ----------

@dataclass
class Download:
    path: Path
    kind: str  # "mod" | "bundle"
    inner: list[str]
    size: int
    modified: float
    installed: bool
    game_hint: str | None  # "ets2" / "ats" guessed from the file name


def downloads_dir() -> Path:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
            return Path(os.path.expandvars(winreg.QueryValueEx(k, "{374DE290-123F-4565-9164-39C4925E467B}")[0]))
    except OSError:
        return Path.home() / "Downloads"


def _game_hint(name: str) -> str | None:
    n = name.lower().replace("_", " ")
    ats, ets = bool(re.search(r"\bats\b|american", n)), bool(re.search(r"\bets2?\b|euro", n))
    return "ats" if ats and not ets else "ets2" if ets and not ats else None


def find_downloads(game: core.Game, folder: Path | None = None) -> list[Download]:
    """Mod files in the Downloads folder (top level), newest first."""
    folder = folder or downloads_dir()
    have = installed_names(game)
    out = []
    if not folder.is_dir():
        return out
    for p in folder.iterdir():
        if not (p.is_file() and p.suffix.lower() in MOD_EXT):
            continue
        kind, inner = inspect_archive(p)
        if kind == "unknown":
            continue
        st = p.stat()
        names = [Path(n).name.lower() for n in inner]
        out.append(Download(p, kind, inner, st.st_size, st.st_mtime, all(n in have for n in names),
                            _game_hint(p.name)))
    return sorted(out, key=lambda d: d.modified, reverse=True)


# ---------- Workshop links ----------

def parse_workshop_id(text: str) -> str | None:
    """Accepts a Workshop URL (…filedetails/?id=123), a steam:// link or a bare id."""
    text = text.strip()
    m = (re.search(r"[?&]id=(\d{6,12})\b", text) or re.fullmatch(r"(\d{6,12})", text)
         or re.search(r"CommunityFilePage/(\d{6,12})", text))
    return m[1] if m else None


def workshop_item(workshop_id: str) -> dict:
    """Public details for one Workshop item: title, app id it belongs to, size. Raises if it doesn't exist."""
    form = {"itemcount": 1, "publishedfileids[0]": workshop_id}
    req = urllib.request.Request("https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/",
                                 data=urllib.parse.urlencode(form).encode(), method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        d = (json.load(r).get("response", {}).get("publishedfiledetails") or [{}])[0]
    if d.get("result") != 1:
        raise LookupError(f"Workshop item {workshop_id} doesn't exist or is private.")
    return {"id": workshop_id, "title": d.get("title") or f"Workshop item {workshop_id}",
            "app": str(d.get("consumer_app_id", "")), "size": int(d.get("file_size") or 0)}


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
