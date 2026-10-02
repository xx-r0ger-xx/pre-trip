"""Which active mods change the same game files, and which one wins (the higher one in the load order)."""
from __future__ import annotations

import json
import os
import threading
import zipfile
from pathlib import Path

from truckcfg import core, mods

CACHE = core.STORE / "file_index_cache.json"
_LOCK = threading.Lock()  # pywebview runs each JS call on its own thread; ETS2 and ATS load at the same time
# package furniture every mod has; overlapping on these means nothing
_IGNORE_ROOT = {"manifest.sii", "versions.sii", "mod_description.txt", "description.txt"}
_IGNORE_EXT = {".jpg", ".jpeg", ".png", ".txt", ".md", ".pdf", ".url"}


def _meaningful(name: str) -> bool:
    name = name.replace("\\", "/").strip("/").lower()
    if "/" not in name:  # root-level files are the package's own readme/icon/manifest
        return False
    return os.path.splitext(name)[1] not in _IGNORE_EXT or name.startswith(("material/", "vehicle/", "model"))


def _list(path: Path) -> list[str] | None:
    """Content file names inside a package. None = unreadable (HashFS .scs)."""
    if path.is_dir():
        out = []
        for dirpath, _, files in os.walk(path):
            rel = os.path.relpath(dirpath, path).replace("\\", "/")
            for f in files:
                n = f if rel == "." else f"{rel}/{f}"
                if f.lower().endswith((".scs", ".zip")) and rel == ".":
                    inner = _list(path / f)
                    out += inner or []
                elif _meaningful(n):
                    out.append(n.lower())
        return out
    try:
        with zipfile.ZipFile(path) as z:
            return [n.lower() for n in z.namelist() if not n.endswith("/") and _meaningful(n)]
    except (zipfile.BadZipFile, OSError):
        return None


def _stamp(path: Path) -> str:
    st = path.stat()
    return f"{st.st_mtime_ns}:{st.st_size}"


def file_index(mod_list: list[mods.Mod]) -> dict[str, list[str] | None]:
    """package id -> content files. Cached on disk by path + modification time, so big Workshop folders scan once."""
    with _LOCK:
        return _file_index(mod_list)


def _file_index(mod_list: list[mods.Mod]) -> dict[str, list[str] | None]:
    try:
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    out, dirty = {}, False
    for m in mod_list:
        p = m.package_path or m.path
        if not p or not p.exists():
            continue
        key, stamp = str(p), _stamp(p)
        hit = cache.get(key)
        if not hit or hit["stamp"] != stamp:
            hit = cache[key] = {"stamp": stamp, "files": _list(p)}
            dirty = True
        out[m.package] = hit["files"]
    if dirty:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        core.write_text_atomic(CACHE, json.dumps(cache))
    return out


def overlaps(order: list[str], index: dict[str, list[str] | None]) -> dict[str, list[dict]]:
    """For each active package (order is top-first): the other active mods it shares files with.
    'wins' is True when this mod is higher, i.e. its copy of the shared files is the one the game uses."""
    sets = {p: set(index.get(p) or ()) for p in order}
    out: dict[str, list[dict]] = {p: [] for p in order}
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            shared = sets[a] & sets[b]
            if shared:
                sample = sorted(shared)[:6]
                out[a].append({"other": b, "count": len(shared), "wins": True, "sample": sample})
                out[b].append({"other": a, "count": len(shared), "wins": False, "sample": sample})
    return out


def owner_of(path_fragment: str, index: dict[str, list[str] | None]) -> list[str]:
    """Packages that contain a file whose path ends with the fragment (used to blame files named in game.log)."""
    frag = path_fragment.replace("\\", "/").lower().lstrip("/")
    return [pkg for pkg, files in index.items() if files and any(f.endswith(frag) for f in files)]
