"""The bridge the web UI calls (window.pywebview.api.*). Every method returns plain JSON-able data; every write goes
through the same guarded, backed-up paths as the desktop app."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
import zipfile
from datetime import datetime, timedelta

from truckcfg import conflicts, core, graphics, loadorder, logbook, mods

GAMES = core.GAMES
_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def _g(key: str) -> core.Game:
    return GAMES[key]


def _profile(game: core.Game) -> core.Profile | None:
    ps = core.find_profiles(game)
    return ps[0] if ps else None


def owned() -> list[str]:
    """Games this PC has: installed in a Steam library, or with a profile in Documents. TCM_GAMES=ats (comma list)
    narrows it, which is how the one-game experience is tested on a PC that has both."""
    only = [k.strip() for k in os.environ.get("TCM_GAMES", "").split(",") if k.strip()]
    return [k for k, g in GAMES.items()
            if (not only or k in only) and (graphics.install_dir(g) is not None or _profile(g) is not None)]


def _need_profile(game: core.Game) -> core.Profile:
    p = _profile(game)
    if not p:
        raise RuntimeError(f"{game.title} has no profile yet. Launch it once and create one, then try again.")
    return p


ACKS = core.STORE / "acknowledged.json"


def _fp(items) -> str:
    return hashlib.sha1("|".join(map(str, items)).encode()).hexdigest()[:12]


def _acks() -> dict:
    try:
        return json.loads(ACKS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _norm(name: str) -> str:
    """Mod name without versions and game tags, for matching the 'same' mod across ETS2 and ATS."""
    n = name.lower().replace("_", " ")
    n = re.sub(r"\b(v(er)?\.?\s*)?\d+(\.\d+)+[a-z]?\b|\bv\d+\b", " ", n)
    n = re.sub(r"\b(ets ?2|ats|euro truck simulator 2|american truck simulator|for|the|mod|pack)\b", " ", n)
    return re.sub(r"[^a-z0-9]+", " ", n).strip()


class Api:
    def __init__(self):
        self._mods: dict[str, list[mods.Mod]] = {}
        self._img: dict[tuple, str] = {}

    # ---------- shared loaders ----------
    def _mod_list(self, key: str, fresh: bool = False) -> list[mods.Mod]:
        if fresh or key not in self._mods:
            ms = mods.all_mods(_g(key))
            cache = mods.load_workshop_cache()
            missing = [m.workshop_id for m in ms if m.workshop_id and m.workshop_id not in cache]
            if missing:
                try:
                    cache = mods.fetch_workshop_details(missing)
                except Exception:  # noqa: BLE001 - offline is fine, names fall back to the manifest
                    pass
            mods.apply_workshop_titles(ms, cache)
            self._mods[key] = ms
        return self._mods[key]

    def _order(self, key: str) -> list[loadorder.Entry]:
        p = _profile(_g(key))
        path = loadorder.find_profile_sii(p) if p else None
        return loadorder.read_order(path)[1] if path else []

    # ---------- status ----------
    def games(self) -> dict:
        have = owned()
        return {k: {"title": g.title, "owned": k in have, "installed": graphics.install_dir(g) is not None,
                    "profile": _profile(g) is not None} for k, g in GAMES.items()}

    def running(self) -> dict:
        return {k: core.is_running(GAMES[k]) for k in owned()}

    def overview(self) -> dict:
        out = {}
        for k in owned():
            g = GAMES[k]
            p = _profile(g)
            out[k] = {"key": k, "title": g.title, "version": mods.game_version(g), "profile": p.name if p else None,
                      "controls_changed": core.controls_changed(p).isoformat(timespec="seconds") if p else None,
                      "running": core.is_running(g)}
        return out

    # ---------- pre-trip inspection ----------
    def inspect(self) -> dict:
        res = {}
        for k in owned():
            g = GAMES[k]
            checks = []
            ms = self._mod_list(k, fresh=True)
            by = {m.package: m for m in ms}
            order = self._order(k)
            ver = mods.game_version(g)
            active = [by.get(e.package) for e in order]
            outdated = [m.name for m in active if m and m.compat(ver) == "outdated"]
            missing = [e.display for e, m in zip(order, active) if m is None]
            idx = conflicts.file_index([m for m in active if m])
            ov = conflicts.overlaps([e.package for e in order], idx)
            pairs = [(a, o) for a, lst in ov.items() for o in lst if o["wins"]]
            rec = loadorder.recommended_order(order, lambda e: by[e.package].categories if e.package in by else [],
                                              lambda e: by[e.package].description if e.package in by else "")
            moves = sum(a != b for a, b in zip(rec, order))
            p = _profile(g)
            drift, rows, snaps = 0, [], []
            if p and (snaps := core.list_snapshots(p)):
                rows, _ = core.diff_snapshot(snaps[0], p)
                drift = len([r for r in rows if r.mapped])
            crash = logbook.crash_report(g)
            crash_age = None
            if crash["time"]:
                crash_age = (datetime.now() - datetime.fromisoformat(crash["time"])).days
            rs = graphics.reshade(g)
            bis = logbook.bisect_state(g)

            drift_rows = rows if p and snaps else []
            # every check: id (stable), fp (fingerprint of what it's about - an acknowledgement only holds while
            # fp is unchanged, so a new crash or more drift brings it back), and one clear next step
            add = lambda **c: checks.append({"detail": "", "action": None, "ack": True, **c})
            if not p:
                add(id="profile", fp="none", sev="warn", title="No profile yet", ack=False,
                    detail=f"Launch {g.title} once and create a profile. Controls and load order show up here after that.")
            if missing:
                add(id="missing", fp=_fp(missing), sev="crit", title=f"{len(missing)} active mod(s) aren't installed",
                    detail=", ".join(missing[:4]), action={"kind": "view", "view": "studio", "label": "Open Studio"})
            if outdated:
                add(id="outdated", fp=_fp(outdated + [ver or ""]), sev="warn",
                    title=f"{len(outdated)} active mod(s) not marked for {mods.short_version(ver)}",
                    detail=", ".join(outdated[:4]), action={"kind": "view", "view": "studio", "label": "Open Studio"})
            if moves:
                add(id="order", fp=_fp([e.package for e in order]), sev="warn",
                    title=f"Load order doesn't follow the mod authors' notes ({moves} moves)",
                    detail="Auto-sort proposes the fix. You review it, then save.",
                    action={"kind": "autosort", "label": "Fix with auto-sort"})
            for a, o in pairs[:3]:
                add(id=f"overlap:{a}:{o['other']}", fp=str(o["count"]), sev="info",
                    title=f"{self._name(by, a)} overrides {o['count']} files of {self._name(by, o['other'])}",
                    detail="Normal for add-ons. Only change it if the mod you want isn't working.",
                    action={"kind": "mod", "package": a, "label": "See files"})
            if drift:
                add(id="drift", fp=_fp([snaps[0].path.name] + [f"{r.name}={r.right}" for r in drift_rows if r.mapped]),
                    sev="warn", title=f"{drift} binding(s) changed since the last snapshot",
                    detail="Review what changed, then keep the new bindings or restore the old ones.",
                    action={"kind": "drift", "label": "Review changes"}, ack=False)
            if crash["present"] and crash_age is not None and crash_age <= 14:
                add(id="crash", fp=crash["time"], sev="crit" if crash_age <= 2 else "warn",
                    title=f"Crashed {self._ago(crash['time'])}", detail=crash["summary"],
                    action={"kind": "view", "view": "logbook", "label": "Crash details"})
            if bis:
                add(id="bisect", fp="running", sev="warn", title=f"Crash finder is running (round {bis['round']})",
                    detail="Some mods are switched off until you finish or stop it.", ack=False,
                    action={"kind": "view", "view": "logbook", "label": "Continue"})
            if not rs["installed"]:
                add(id="reshade", fp="missing", sev="info", title="ReShade isn't installed",
                    detail="Optional. Sharpening and colour presets live in Twin Rigs → ReShade.",
                    action={"kind": "view", "view": "twin", "label": "Open"} if len(owned()) > 1 else None)
            acks = _acks().get(k, {})
            for c in checks:
                c["acked"] = c["ack"] and acks.get(c["id"]) == c["fp"]
            n_active = len([m for m in active if m])
            res[k] = {
                "gauges": {
                    "mods": {"value": n_active - len(outdated), "max": max(len(order), 1), "label": "Mods current",
                             "text": f"{n_active - len(outdated)}/{len(order)}"},
                    "conflicts": {"value": len(pairs), "max": max(len(pairs), 6), "label": "File overlaps",
                                  "text": str(len(pairs))},
                    "drift": {"value": drift, "max": max(drift, 10), "label": "Binding drift", "text": str(drift)},
                    "crash": {"value": min(crash_age, 30) if crash_age is not None else 30, "max": 30,
                              "label": "Days since crash",
                              "text": str(crash_age) if crash_age is not None else "—"},
                },
                "checks": checks or [{"id": "ok", "sev": "ok", "title": "All clear", "detail": "Nothing needs attention.",
                                      "action": None, "ack": False, "acked": False}], "version": ver, "active": len(order), "installed": len(ms),
                "reshade": rs["installed"],
            }
        return res

    def ack(self, key: str, check_id: str, fp: str) -> None:
        data = _acks()
        data.setdefault(key, {})[check_id] = fp
        ACKS.parent.mkdir(parents=True, exist_ok=True)
        ACKS.write_text(json.dumps(data, indent=1), encoding="utf-8")

    def unack(self, key: str, check_id: str) -> None:
        data = _acks()
        data.get(key, {}).pop(check_id, None)
        ACKS.write_text(json.dumps(data, indent=1), encoding="utf-8")

    def drift(self, key: str) -> dict:
        """What changed in the controls since the latest snapshot, for the review dialog."""
        p = _need_profile(_g(key))
        snaps = core.list_snapshots(p)
        if not snaps:
            return {"snapshot": None, "rows": []}
        rows, other = core.diff_snapshot(snaps[0], p)
        return {"snapshot": {"id": snaps[0].path.name, "label": snaps[0].meta.get("label") or "manual",
                             "created": snaps[0].created},
                "rows": [{"name": r.name, "before": core.pretty_input(r.kind, r.left) if r.left is not None else "—",
                          "after": core.pretty_input(r.kind, r.right) if r.right is not None else "—"}
                         for r in rows if r.mapped],
                "other_files": other}

    @staticmethod
    def _name(by, pkg):
        return by[pkg].name if pkg in by else pkg

    @staticmethod
    def _ago(iso):
        d = datetime.now() - datetime.fromisoformat(iso)
        if d < timedelta(hours=1):
            return f"{int(d.total_seconds() // 60)} min ago"
        if d < timedelta(days=1):
            return f"{int(d.total_seconds() // 3600)} h ago"
        return f"{d.days} day(s) ago"

    # ---------- twin rigs ----------
    def twin(self) -> dict:
        if len(owned()) < 2:
            return {"available": False, "have": owned()}
        e, a = _profile(GAMES["ets2"]), _profile(GAMES["ats"])
        controls = []
        if e and a:
            for r in core.diff_bindings(core.parse_bindings(core.read_text(e.path / "controls.sii")),
                                        core.parse_bindings(core.read_text(a.path / "controls.sii"))):
                if r.mapped and r.left is not None and r.right is not None:
                    controls.append({"key": [r.kind, r.name], "name": r.name,
                                     "ets2": core.pretty_input(r.kind, r.left), "ats": core.pretty_input(r.kind, r.right)})
        gfx = [dict(row, ets2=row.pop("a"), ats=row.pop("b"))
               for row in graphics.diff(graphics.read_config(GAMES["ets2"]), graphics.read_config(GAMES["ats"]))]
        rs = {k: graphics.reshade(g) for k, g in GAMES.items()}
        keys = sorted(set(rs["ets2"]["values"]) | set(rs["ats"]["values"]))
        rs_rows = [{"key": k, "ets2": rs["ets2"]["values"].get(k), "ats": rs["ats"]["values"].get(k)} for k in keys]
        # mods present in both games under the same (normalised) name
        me, ma = self._mod_list("ets2"), self._mod_list("ats")
        oe, oa = {x.package for x in self._order("ets2")}, {x.package for x in self._order("ats")}
        pairs, used = [], set()
        for x in me:
            nx = _norm(x.name)
            best = None
            for y in ma:
                if y.package in used:
                    continue
                ny = _norm(y.name)
                if nx and nx == ny:
                    best, exact = y, True
                    break
                if nx and ny and len(min(nx, ny, key=len)) >= 6 and (nx.startswith(ny) or ny.startswith(nx)):
                    best, exact = y, False
            if best:
                used.add(best.package)
                pairs.append({"name": x.name, "ets2": {"name": x.name, "version": x.version, "active": x.package in oe},
                              "ats": {"name": best.name, "version": best.version, "active": best.package in oa},
                              "exact": exact})
        only = {"ets2": [x.name for x in me if not any(p["ets2"]["name"] == x.name for p in pairs)],
                "ats": [y.name for y in ma if y.package not in used]}
        ov = self.overview()
        return {"available": True, "controls": controls, "graphics": gfx, "reshade": {"ets2": {k: v for k, v in rs["ets2"].items() if k != "values"},
                                                                   "ats": {k: v for k, v in rs["ats"].items() if k != "values"},
                                                                   "rows": rs_rows},
                "mods": {"pairs": pairs, "only": only},
                "changed": {k: ov[k]["controls_changed"] for k in ov}}

    def sync_controls(self, src: str, dst: str, names: list | None = None) -> str:
        s, d = _need_profile(_g(src)), _need_profile(_g(dst))
        rows = self.twin()["controls"]
        keys = [tuple(r["key"]) for r in rows if names is None or r["name"] in names]
        n, missing = core.copy_bindings(s, d, keys)
        return f"Copied {n} binding(s) {src.upper()} → {dst.upper()}. A snapshot of {dst.upper()} was taken first."

    def sync_graphics(self, src: str, dst: str, keys: list | None = None) -> str:
        cfg = graphics.read_config(_g(src))
        rows = graphics.diff(cfg, graphics.read_config(_g(dst)))
        values = {r["key"]: r["a"] for r in rows if not r["same"] and r["a"] is not None
                  and (keys is None or r["key"] in keys)}
        if not values:
            return "Nothing to copy."
        b = graphics.write_keys(_g(dst), values)
        return f"Copied {len(values)} graphics setting(s) to {dst.upper()}. Backup: {b.name}"

    def sync_reshade(self, src: str, dst: str) -> str:
        graphics.copy_reshade(_g(src), _g(dst))
        return f"ReShade and its preset copied {src.upper()} → {dst.upper()}."

    # ---------- mods / load order ----------
    def mods(self, key: str, fresh: bool = False) -> dict:
        g = _g(key)
        ms = self._mod_list(key, fresh)
        by = {m.package: m for m in ms}
        order = self._order(key)
        ver = mods.game_version(g)
        idx = conflicts.file_index(ms)
        ov = conflicts.overlaps([e.package for e in order], idx)
        info = {}
        for m in ms:
            group, why = loadorder.classify(m.name, m.categories)
            place = loadorder.placement(m.description)
            info[m.package] = {
                "package": m.package, "name": m.name, "display": m.display or m.name, "version": m.version,
                "author": m.author, "source": m.source, "compat": m.compat(ver), "size": m.size,
                "group": group.key, "group_title": group.title, "why": why, "categories": m.categories,
                "notes": loadorder.author_notes(m.description), "placement": place.describe(),
                "has_icon": bool(m.icon), "files": len(idx.get(m.package) or []) if idx.get(m.package) is not None else None,
                "workshop_id": m.workshop_id, "enabled": m.enabled,
                "description": m.description[:1200],
            }
        for e in order:
            if e.package not in info:
                info[e.package] = {"package": e.package, "name": e.display, "display": e.display, "missing": True,
                                   "group": "ui", "group_title": "Missing", "notes": [], "placement": "",
                                   "compat": "unknown", "source": "missing", "has_icon": False}
        rec = loadorder.recommended_order(order, lambda e: by[e.package].categories if e.package in by else [],
                                          lambda e: by[e.package].description if e.package in by else "")
        return {"game": key, "version": ver, "mods": info, "order": [e.package for e in order],
                "recommended": [e.package for e in rec], "overlaps": ov,
                "groups": [{"key": gr.key, "title": gr.title} for gr in loadorder.GROUPS],
                "running": core.is_running(g)}

    def recommend(self, key: str, order: list[str]) -> list[str]:
        """Auto-sort an unsaved order (groups + each author's load-order notes)."""
        by = {m.package: m for m in self._mod_list(key)}
        entries = [loadorder.Entry(p, by[p].display if p in by else p) for p in order]
        rec = loadorder.recommended_order(entries, lambda e: by[e.package].categories if e.package in by else [],
                                          lambda e: by[e.package].description if e.package in by else "")
        return [e.package for e in rec]

    def overlaps_for(self, key: str, order: list[str]) -> dict:
        idx = conflicts.file_index(self._mod_list(key))
        return conflicts.overlaps(order, idx)

    def save_order(self, key: str, order: list[str]) -> str:
        g = _g(key)
        info = {m.package: m for m in self._mod_list(key)}
        current = {e.package: e for e in self._order(key)}
        entries = [current.get(p) or loadorder.Entry(p, info[p].display or info[p].name) for p in order]
        path = loadorder.find_profile_sii(_need_profile(g))
        if not path:
            raise RuntimeError(f"No profile.sii found for {g.title}. Launch the game and load your profile once.")
        dest = loadorder.write_order(path, g, entries)
        return f"Saved {len(entries)} active mods to {key.upper()}. Backup: {dest.name}"

    def mod_image(self, key: str, package: str) -> str:
        ck = (key, package)
        if ck in self._img:
            return self._img[ck]
        m = next((x for x in self._mod_list(key) if x.package == package), None)
        uri = ""
        if m and m.icon and m.package_path:
            data = None
            try:
                if m.package_path.is_dir():
                    f = m.package_path / m.icon
                    data = f.read_bytes() if f.is_file() else None
                else:
                    with zipfile.ZipFile(m.package_path) as z:
                        data = z.read(m.icon)
            except (OSError, KeyError, zipfile.BadZipFile):
                data = None
            if data:
                mime = _MIME.get(os.path.splitext(m.icon)[1].lower(), "image/jpeg")
                uri = f"data:{mime};base64,{base64.b64encode(data).decode()}"
        self._img[ck] = uri
        return uri

    # ---------- loadouts ----------
    def loadouts(self, key: str) -> dict:
        return logbook.list_loadouts(_g(key))

    def save_loadout(self, key: str, name: str, order: list[str] | None = None) -> dict:
        info = self.mods(key)["mods"]
        order = order if order is not None else [e.package for e in self._order(key)]
        return logbook.save_loadout(_g(key), name, [[p, info.get(p, {}).get("display", p)] for p in order])

    def delete_loadout(self, key: str, name: str) -> dict:
        return logbook.delete_loadout(_g(key), name)

    def apply_loadout(self, key: str, name: str) -> str:
        lo = logbook.list_loadouts(_g(key))[name]
        installed = {m.package for m in self._mod_list(key)}
        keep = [p for p, _ in lo["order"] if p in installed]
        skipped = len(lo["order"]) - len(keep)
        msg = self.save_order(key, keep)
        return f"Loadout “{name}” applied. {msg}" + (f" Skipped {skipped} mod(s) that aren't installed." if skipped else "")

    # ---------- logbook ----------
    def logbook(self, key: str) -> dict:
        g = _g(key)
        info = {m.package: m.name for m in self._mod_list(key)}
        crash = logbook.crash_report(g)
        crash["acked"] = bool(crash["time"]) and _acks().get(key, {}).get("crash") == crash["time"]
        for s in crash["suspects"]:
            s["name"] = info.get(s["package"], s["package"])
        st = logbook.bisect_state(g)
        if st:
            names = dict(st["original"])
            st = dict(st, names={p: info.get(p, names.get(p, p)) for p in names})
        return {"events": logbook.events(g), "crash": crash, "bisect": st}

    def snapshot(self, key: str, label: str = "manual") -> str:
        core.take_snapshot(_need_profile(_g(key)), label)
        return f"Snapshot of {key.upper()} controls saved."

    def restore(self, key: str, kind: str, ident: str) -> str:
        return logbook.restore(_g(key), kind, ident)

    def bisect_start(self, key: str) -> dict:
        return logbook.bisect_start(_g(key))

    def bisect_report(self, key: str, crashed: bool) -> dict:
        return logbook.bisect_report(_g(key), crashed)

    def bisect_stop(self, key: str) -> str:
        logbook.bisect_stop(_g(key))
        return "Crash finder stopped. Your original load order is back."

    # ---------- shell ----------
    def open_folder(self, key: str, which: str = "profile") -> None:
        g = _g(key)
        target = {"profile": _profile(g).path if _profile(g) else mods.game_dir(g), "mods": mods.mod_dir(g),
                  "game": mods.game_dir(g), "store": core.STORE}.get(which, mods.game_dir(g))
        subprocess.Popen(["explorer", str(target)])

    def launch(self, key: str) -> None:
        os.startfile(f"steam://rungameid/{mods.STEAM_APP[key]}")
