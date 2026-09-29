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
