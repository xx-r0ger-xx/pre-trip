"""In-game mod load order: the active_mods list inside a profile's profile.sii.

profile.sii is usually saved encrypted ("ScsC": AES-256-CBC + zlib, a publicly documented key). The game also
reads plain-text SiiNunit, so edits are written back as text and the game re-encrypts on its next save.

The file lists mods bottom-up: active_mods[0] is the BOTTOM of the in-game Mod Manager (loaded first) and the
last entry is the TOP (highest priority). This module works in Mod Manager order (top first).
"""
from __future__ import annotations

import re
import shutil
import struct
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from truckcfg import core

SCSC_KEY = bytes.fromhex("2a5fcb1791d22fb60245b3d8369ed0b2c27371563fbf1f3c9edf6b11825a5d0a")
BACKUPS = core.STORE / "profile-backups"
ACTIVE_RE = re.compile(r'^([ \t]*)active_mods:[ \t]*\d+[ \t]*\r?\n(?:[ \t]*active_mods\[\d*\]:.*\r?\n)*', re.M)
ENTRY_RE = re.compile(r'^[ \t]*active_mods\[\d*\]:[ \t]*"(.*)"', re.M)


@dataclass(frozen=True)
class Entry:
    package: str  # "early_autumn_ats_v4_6" or "mod_workshop_package.00000000B3A13883"
    display: str

    def line_value(self) -> str:
        return f"{self.package}|{self.display}".replace('"', "'")


def workshop_package(workshop_id: str) -> str:
    return f"mod_workshop_package.{int(workshop_id):016X}"


def find_profile_sii(profile: core.Profile) -> Path | None:
    """Local profiles keep profile.sii beside controls.sii; Steam Cloud profiles keep it in Steam's userdata."""
    here = profile.path / "profile.sii"
    if here.is_file():
        return here
    from truckcfg import mods  # local import: mods imports core too, keep module load order simple
    app = mods.STEAM_APP[profile.game.key]
    for lib in mods.steam_libraries()[:1]:  # userdata only lives in the main Steam install
        for user in sorted((lib / "userdata").glob("*")):
            cand = user / app / "remote" / "profiles" / profile.path.name / "profile.sii"
            if cand.is_file():
                return cand
    return None


def decode(data: bytes) -> str:
    if data[:4] == b"ScsC":
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        iv, size = data[36:52], struct.unpack("<I", data[52:56])[0]
        dec = Cipher(algorithms.AES(SCSC_KEY), modes.CBC(iv)).decryptor()
        data = zlib.decompressobj().decompress(dec.update(data[56:]) + dec.finalize())
        if len(data) != size:
            raise ValueError("profile.sii decrypted to an unexpected size - not touching it.")
    if data[:4] == b"BSII":
        raise ValueError("This profile is saved in the binary format, which the app can't edit yet. "
                         'Set  uset g_save_format "2"  in the game\'s config.cfg, launch and quit once, then retry.')
    if not data.startswith((b"SiiNunit", b"\xef\xbb\xbfSiiNunit")):
        raise ValueError("profile.sii isn't in a format the app recognises - not touching it.")
    return data.decode("utf-8")


def read_order(path: Path) -> tuple[str, list[Entry]]:
    """Returns (profile text, active mods top-first)."""
    text = decode(path.read_bytes())
    return text, parse_order(text)


def parse_order(text: str) -> list[Entry]:
    block = ACTIVE_RE.search(text)
    if not block:
        return []
    entries = []
    for value in ENTRY_RE.findall(block[0]):
        package, _, display = value.partition("|")
        entries.append(Entry(package, display or package))
    return entries[::-1]


def replace_order(text: str, order: list[Entry]) -> str:
    block = ACTIVE_RE.search(text)
    if not block:
        raise ValueError("No active_mods list in this profile.sii - not touching it.")
    indent, nl = block[1], "\r\n" if "\r\n" in block[0] else "\n"
    lines = [f"{indent}active_mods: {len(order)}"]
    lines += [f'{indent}active_mods[{i}]: "{e.line_value()}"' for i, e in enumerate(order[::-1])]
    return text[:block.start()] + nl.join(lines) + nl + text[block.end():]


# ---------- recommended order ----------
# Community consensus (Steam "Proper Load Order for Mods [1.57+]", SCS forum map-combo threads, ProMods): small
# fixes and overrides on top, then things that modify other content, then the base content itself, maps last.

@dataclass(frozen=True)
class Group:
    key: str
    title: str
    examples: str
    categories: tuple[str, ...]  # manifest category[] values
    words: tuple[str, ...]  # name keywords (regex fragments, matched on word boundaries)


GROUPS = (
    Group("fixes", "Patches & fixes", "Compatibility patches, bug fixes, anything whose author says 'top'",
          (), (r"patch(es)?", r"compat\w*", r"hot ?fix", r"bug ?fix(es)?", r"fix for", r"add-?on for")),
    Group("graphics", "Graphics & weather", "Weather, lighting, reflections, seasons, textures",
          ("graphics", "weather"), (r"weather", r"rain", r"reflections?", r"autumn", r"winter", r"spring", r"summer",
                                    r"seasons?", r"lighting", r"lights", r"sky", r"fog", r"graphics?", r"textures?", r"reshade")),
    Group("sound", "Sound", "Engine and exhaust sounds, horns, ambient audio",
          ("sound",), (r"sounds?", r"straight ?pipe", r"exhaust", r"horns?", r"jake ?brake", r"audio")),
    Group("physics", "Physics & driving", "Truck physics, gearboxes, retarders, handling",
          ("physics",), (r"physics", r"suspension", r"handling", r"gearbox", r"transmission", r"retarder", r"i-shift")),
    Group("ui", "UI, GPS & other", "Route advisors, GPS, menus, and anything uncategorised",
          ("ui",), (r"gps", r"route advis\w*", r"navigation", r"hud", r"ui", r"menu", r"loading screens?")),
    Group("interior", "Truck parts & interiors", "Dashboards, interiors, lights, tuning parts",
          ("interior", "tuning_parts"), (r"dashboards?", r"interiors?", r"cabin", r"mirrors?", r"tuning", r"parts",
                                         r"lcd", r"accessor\w*", r"light ?bars?", r"beacons?", r"headlights?")),
    Group("traffic", "AI traffic", "AI traffic packs, traffic density, AI behaviour",
          ("ai_traffic",), (r"traffic", r"ai", r"drivers")),
    Group("cargo", "Cargo, jobs & map objects", "Cargo packs, economy, companies, billboards",
          ("cargo_pack", "cargo", "models", "prefabs"), (r"cargo", r"jobs?", r"economy", r"compan(y|ies)",
                                                         r"gas stations?", r"billboards?", r"fuel", r"prices")),
    Group("paint", "Paint jobs & skins", "Truck and trailer skins",
          ("paint_job",), (r"paint ?jobs?", r"skins?", r"liver(y|ies)")),
    Group("trailers", "Trailers", "Standalone trailers and trailer packs",
          ("trailer",), (r"trailers?",)),
    Group("trucks", "Trucks", "Standalone trucks",
          ("truck",), (r"trucks?", r"peterbilt", r"kenworth", r"freightliner", r"mack", r"scania", r"volvo", r"daf",
                       r"iveco", r"actros")),
    Group("maps", "Maps (always last)", "Map mods and map combos - follow the combo's own order exactly",
          ("map",), (r"maps?", r"promods", r"reforma", r"roextended", r"coast to coast", r"sierra nevada")),
)
DEFAULT_GROUP = next(g for g in GROUPS if g.key == "ui")
_WORD_RE = {g.key: re.compile(r"\b(" + "|".join(g.words) + r")\b", re.I) for g in GROUPS}

GUIDES = (
    ("Proper Load Order for Mods [1.57+]", "Steam guide",
     "https://steamcommunity.com/sharedfiles/filedetails/?id=3147291492"),
    ("ETS2 Mod Load Order & Crash Fixing", "Steam guide, 2026",
     "https://steamcommunity.com/sharedfiles/filedetails/?id=3751019029"),
    ("ATS Map Combos - load order", "SCS forum, kept up to date per game version",
     "https://forum.scssoft.com/viewtopic.php?t=292914"),
    ("Correct load order", "ProMods forum (ETS2 map combos)", "https://promods.net/viewtopic.php?t=19865"),
    ("Mod manager & manifest.sii", "SCS Modding Wiki",
     "https://modding.scssoft.com/wiki/Documentation/Engine/Mod_manager"),
)


def classify(name: str, categories: list[str] | tuple = ()) -> tuple[Group, str]:
    """(group, reason) from the manifest's categories and words in the name. When they disagree the higher group
    wins: a mod that tweaks something (a dashboard tagged 'truck') belongs above the base content it modifies."""
    name = name.replace("_", " ")
    hits = []
    for cat in categories:
        if g := next((g for g in GROUPS if cat.lower() in g.categories), None):
            hits.append((GROUPS.index(g), g, f"manifest category “{cat}”"))
            break
    if g_m := next(((g, m) for g in GROUPS if (m := _WORD_RE[g.key].search(name))), None):
        hits.append((GROUPS.index(g_m[0]), g_m[0], f"name mentions “{g_m[1][0]}”"))
    if not hits:
        return DEFAULT_GROUP, "no category or keyword - treated as other"
    _, g, why = min(hits, key=lambda h: h[0])
    return g, why


def recommended_order(order: list[Entry], categories_for) -> list[Entry]:
    """Stable sort by group: keeps the user's relative order inside each group. categories_for(entry) -> list."""
    rank = {g.key: i for i, g in enumerate(GROUPS)}
    return [e for _, _, e in sorted(
        (rank[classify(e.display or e.package, categories_for(e))[0].key], i, e) for i, e in enumerate(order))]


PRIORITY_NOTE_RE = re.compile(
    r"[^.!\n]*\b(priority|load order|mod manager|(place|put|load|keep|position)\w*\b[^.!\n]*\b(above|below|over|under"
    r"|higher|lower|top|bottom))\b[^.!\n]*[.!]?", re.I)


def author_notes(description: str) -> list[str]:
    """Sentences in a mod description that give load-order instructions."""
    notes = (m[0].strip() for m in PRIORITY_NOTE_RE.finditer(description))
    return [n for n in notes if len(n) > 12][:4]


def backup(path: Path, game: core.Game) -> Path:
    dest = BACKUPS / game.key / datetime.now().strftime("%Y-%m-%d_%H%M%S")
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest / path.name)
    return dest


def write_order(path: Path, game: core.Game, order: list[Entry]) -> Path:
    """Back up the current file, then write the new order as plain text. Returns the backup folder."""
    if core.is_running(game):
        raise RuntimeError(f"Close {game.title} first - it rewrites profile.sii when it exits.")
    text, _ = read_order(path)  # re-read so nothing the game saved since the scan is lost
    new = replace_order(text, order)
    dest = backup(path, game)
    core.write_text_atomic(path, new)
    return dest
