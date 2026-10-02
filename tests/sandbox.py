"""A throwaway Documents + Steam + TruckSim-Configs tree for testing every write path.

Everything the app locates (Documents folder, Steam libraries, the data folder and the module-level paths derived
from it) is redirected into a temp directory, network calls are blocked, and every file write is checked: a write
outside the sandbox fails the test instead of touching real files.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from truckcfg import cleanup, conflicts, core, loadorder, logbook, mods, webapi

PROFILE_HEX = "70726f6669"  # "profi"
STEAM_ID = "12345"

CONTROLS = (
    'SiiNunit\r\n{{\r\ninput_config : _nameless.1 {{\r\n version: 32\r\n config_lines: 5\r\n'
    ' config_lines[0]: "device joy `xinput.xinput_gamepad_1`"\r\n'
    ' config_lines[1]: "mix horn `{horn} | semantical.horn?0`"\r\n'
    ' config_lines[2]: "mix light `{light} | semantical.light?0`"\r\n'
    ' config_lines[3]: "mix cabinlight `semantical.cabinlight?0`"\r\n'
    ' config_lines[4]: "constant c_rsteersens {sens}"\r\n}}\r\n\r\n}}\r\n'
)
CONFIG = ('# prism3d variable config data\r\n\r\nuset r_mode_width "{w}"\r\nuset r_mode_height "{h}"\r\nuset r_vsync "{vs}"\r\n'
          'uset r_aa "6"\r\nuset g_reflection "3"\r\nuset s_init_master_volume "0.75"\r\n')
CRASH = ("Crash log created on: Tue Sep 29 12:37:40 2026\nBuild: 1.61.3.0s abc\nException code: C0000025 NONCONTINUABLE\n\n"
         "Call stack (IMH):\nAddress  Frame\n00007FF6  0001:000FBDA1 {exe}\n00007FF9  0001:000C31CA C:\\WINDOWS\\System32\\KERNELBASE.dll\n\n"
         "Stack:\nnothing\n\nModules:\nC:\\Program Files\\Other\\overlay.dll\n")
LOG = ("00:00:00.001 : Prism3D ver.1.61.3.0 (x64)\n"
       '00:00:01.000 : [mod_package_manager] Mod "Rain Add-on" has been mounted. (package_name: rain_addon)\n'
       "00:00:02.000 : <ERROR> [unit] File not found: /def/weather/storm.sii\n")

# (package, display name, author, category, description, files)
MODS = {
    "ets2": [
        ("weather_base", "Weather Base", "Ann", "graphics", "High priority please.",
         ["def/weather/storm.sii", "material/road/asphalt.dds", "material/road/wet.tobj"]),
        ("rain_addon", "Rain Add-on", "Ann", "graphics", "Place above Weather Base in Mod Manager.",
         ["material/road/wet.tobj", "material/road/puddle.dds"]),
        ("loud_horn", "Loud Horn", "Bob", "sound", "", ["sound/horn.bank"]),
        ("big_map", "Big Map", "Cid", "map", "", ["map/europe.mbd"]),
    ],
    "ats": [
        ("weather_base_ats", "Weather Base", "Ann", "graphics", "", ["def/weather/storm.sii"]),
        ("loud_horn_ats", "Loud Horn", "Bob", "sound", "", ["sound/horn.bank"]),
    ],
}


def _scs(path: Path, display, author, category, description, files):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("manifest.sii", f'SiiNunit\n{{\nmod_package : .p {{\n package_version: "1.0"\n display_name: "{display}"\n'
                                   f' author: "{author}"\n category[]: "{category}"\n icon: "icon.jpg"\n'
                                   f' description_file: "desc.txt"\n compatible_versions[]: "1.61.*"\n}}\n}}\n')
        z.writestr("desc.txt", description)
        z.writestr("icon.jpg", b"\xff\xd8\xff\xe0fakejpeg")
        for f in files:
            z.writestr(f, "x")


def _profile_sii(entries) -> str:
    """entries top-first, like the in-game Mod Manager."""
    lines = [f' active_mods: {len(entries)}'] + [f' active_mods[{i}]: "{p}|{d}"' for i, (p, d) in enumerate(entries[::-1])]
    return "SiiNunit\n{\nuser_profile : _nameless.1 {\n face: 0\n" + "\n".join(lines) + "\n customization: 1\n}\n\n}\n"


class Sandbox:
    """with Sandbox() as sb: ... - sb.docs, sb.steam, sb.store, sb.running (set game keys to simulate open games)."""

    def __init__(self, games=("ets2", "ats")):
        self.games = games
        self.running: set[str] = set()
        self.steam_calls: list[tuple] = []  # (action, game key, ids) - subscribe/unsubscribe never reach Steam

    # ---- layout
    def game_docs(self, key) -> Path:
        return self.docs / core.GAMES[key].title

    def profile_dir(self, key) -> Path:
        return self.game_docs(key) / "steam_profiles" / PROFILE_HEX

    def profile_sii(self, key) -> Path:
        return self.steam / "userdata" / STEAM_ID / mods.STEAM_APP[key] / "remote" / "profiles" / PROFILE_HEX / "profile.sii"

    def bin_dir(self, key) -> Path:
        return self.steam / "steamapps" / "common" / core.GAMES[key].title / "bin" / "win_x64"

    def _build(self):
        horns = {"ets2": ("joy.b9?0", "joy.b3?0", "0.400000", "3840", "2160", "0"),
                 "ats": ("keyboard.h?0 | joy.b9?0", "keyboard.l?0 || short_press(joy.b3?0)", "0.400000", "2560", "1440", "1")}
        for key in self.games:
            game = core.GAMES[key]
            horn, light, sens, w, h, vs = horns[key]
            self.profile_dir(key).mkdir(parents=True)
            core.write_text_atomic(self.profile_dir(key) / "controls.sii", CONTROLS.format(horn=horn, light=light, sens=sens))
            core.write_text_atomic(self.game_docs(key) / "config.cfg", CONFIG.format(w=w, h=h, vs=vs))
            (self.game_docs(key) / "game.crash.txt").write_text(CRASH.format(exe=str(self.bin_dir(key) / game.exe)))
            (self.game_docs(key) / "game.log.txt").write_text(LOG)
            mod_dir = self.game_docs(key) / "mod"
            mod_dir.mkdir()
            for pkg, *rest in MODS[key]:
                _scs(mod_dir / f"{pkg}.scs", *rest)
            self.profile_sii(key).parent.mkdir(parents=True)
            active = [(p, d) for p, d, *_ in MODS[key]][:3]
            core.write_text_atomic(self.profile_sii(key), _profile_sii(active))
            self.bin_dir(key).mkdir(parents=True)
            (self.bin_dir(key) / game.exe).write_bytes(b"MZ")
        (self.root / "Downloads").mkdir()
        (self.root / "RecycleBin").mkdir()
        if "ats" in self.games:  # one Workshop mod, so unsubscribe has something to act on
            item = self.steam / "steamapps" / "workshop" / "content" / mods.STEAM_APP["ats"] / "1234567"
            (item / "universal" / "sound").mkdir(parents=True)
            (item / "versions.sii").write_text(
                'SiiNunit\n{\npackage_version_info : .universal {\n package_name: "universal"\n}\n}\n')
            (item / "universal" / "manifest.sii").write_text(
                'SiiNunit\n{\nmod_package : .p {\n display_name: "Jake Brake Pack"\n author: "Dee"\n category[]: "sound"\n}\n}\n')
            (item / "universal" / "sound" / "jake.bank").write_text("x")
        if "ats" in self.games:  # ReShade installed in ATS only
            b = self.bin_dir("ats")
            (b / "dxgi.dll").write_bytes(b"reshade")
            (b / "ReShade.ini").write_text("[GENERAL]\nPresetPath=.\\ReShadePreset.ini\n")
            (b / "ReShadePreset.ini").write_text("Techniques=CAS@CAS.fx\n\n[CAS.fx]\nSharpening=0.450000\n")
            (b / "reshade-shaders" / "Shaders").mkdir(parents=True)
            (b / "reshade-shaders" / "Shaders" / "CAS.fx").write_text("// shader")

    # ---- context
    def __enter__(self):
        self.root = Path(tempfile.mkdtemp(prefix="pretrip-sandbox-")).resolve()
        self.docs, self.steam, self.store = self.root / "Documents", self.root / "Steam", self.root / "TruckSim-Configs"
        self._stack = ExitStack()
        p = lambda target, value: self._stack.enter_context(mock.patch(target, value))  # noqa: E731
        p("truckcfg.core.documents_dir", lambda: self.docs)
        p("truckcfg.core._SESSION", {})  # each sandbox starts like a fresh app launch
        p("truckcfg.mods.steam_libraries", lambda: [self.steam])
        p("truckcfg.core.is_running", lambda game: game.key in self.running)
        p("truckcfg.mods.fetch_workshop_details", lambda ids: {})
        p("truckcfg.mods.downloads_dir", lambda: self.root / "Downloads")
        p("truckcfg.mods.recycle", lambda path: shutil.move(str(path), self.root / "RecycleBin" / Path(path).name))
        p("truckcfg.steamugc.subscribe", lambda game, ids: self.steam_calls.append(("sub", game.key, list(ids))))
        p("truckcfg.steamugc.unsubscribe", lambda game, ids: self.steam_calls.append(("unsub", game.key, list(ids))))
        for target, sub in (("truckcfg.core.STORE", ""), ("truckcfg.cleanup.QUARANTINE", "quarantine"),
                            ("truckcfg.conflicts.CACHE", "file_index_cache.json"), ("truckcfg.loadorder.BACKUPS", "profile-backups"),
                            ("truckcfg.logbook.LOADOUTS", "loadouts"), ("truckcfg.logbook.BISECT", "crash-finder"),
                            ("truckcfg.mods.WORKSHOP_CACHE", "workshop_cache.json"), ("truckcfg.webapi.ACKS", "acknowledged.json")):
            p(target, self.store / sub if sub else self.store)
        self._guard_writes()
        self._build()
        return self

    def _guard_writes(self):
        """Fail loudly if anything writes outside the sandbox."""
        root = str(self.root).lower()

        def inside(path):
            if not str(Path(path).resolve()).lower().startswith(root):
                raise AssertionError(f"write outside the sandbox: {path}")

        real_atomic, real_copy2, real_copytree, real_write_text, real_move = (core.write_text_atomic, shutil.copy2, shutil.copytree,
                                                                               Path.write_text, shutil.move)
        real_rmtree, real_unlink = shutil.rmtree, Path.unlink
        self._stack.enter_context(mock.patch("shutil.rmtree", lambda path, *a, **kw: (inside(path), real_rmtree(path, *a, **kw))[1]))
        self._stack.enter_context(mock.patch.object(Path, "unlink", lambda self_, *a, **kw: (inside(self_), real_unlink(self_, *a, **kw))[1]))
        self._stack.enter_context(mock.patch("truckcfg.core.write_text_atomic",
                                             lambda path, text: (inside(path), real_atomic(path, text))[1]))
        self._stack.enter_context(mock.patch("shutil.copy2", lambda src, dst, **kw: (inside(dst), real_copy2(src, dst, **kw))[1]))
        self._stack.enter_context(mock.patch("shutil.copytree",
                                             lambda src, dst, *a, **kw: (inside(dst), real_copytree(src, dst, *a, **kw))[1]))
        self._stack.enter_context(mock.patch("shutil.move", lambda src, dst, *a, **kw: (inside(dst), real_move(src, dst, *a, **kw))[1]))
        self._stack.enter_context(mock.patch.object(Path, "write_text",
                                                    lambda self_, data, *a, **kw: (inside(self_), real_write_text(self_, data, *a, **kw))[1]))

    def __exit__(self, *exc):
        self._stack.close()
        shutil.rmtree(self.root, ignore_errors=True)
        return False

    # ---- helpers for assertions
    def order(self, key) -> list[str]:
        return [e.package for e in loadorder.read_order(self.profile_sii(key))[1]]

    def bindings(self, key) -> dict:
        return core.parse_bindings(core.read_text(self.profile_dir(key) / "controls.sii"))

    def config(self, key) -> str:
        return core.read_text(self.game_docs(key) / "config.cfg")


def api() -> webapi.Api:
    return webapi.Api()


def make_scs(path: Path, display="Downloaded Mod", files=("def/x.sii",)):
    _scs(path, display, "Eve", "other", "", list(files))
    return path


__all__ = ["Sandbox", "api", "MODS", "make_scs", "os"]
