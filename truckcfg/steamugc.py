"""Subscribe to / unsubscribe from Steam Workshop items using the game's own steam_api64.dll.

Runs in a short-lived child process (python -m truckcfg.steamugc <sub|unsub> <appid> <dll dir> <ids...>) because SteamAPI_Init
ties the whole process to the game's app id - Steam briefly shows the game as running while it works.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path

ITEM_SUBSCRIBED = 1


def steam_dll(game_exe: str) -> Path | None:
    from truckcfg import core, mods
    title = next(g.title for g in core.GAMES.values() if g.exe == game_exe)
    for lib in mods.steam_libraries():
        dll = lib / "steamapps" / "common" / title / "bin" / "win_x64" / "steam_api64.dll"
        if dll.is_file():
            return dll
    return None


def unsubscribe(game, workshop_ids: list[str]) -> None:
    """Unsubscribe and wait until Steam confirms. Raises RuntimeError with the reason if it can't."""
    _run(game, "unsub", workshop_ids)


def subscribe(game, workshop_ids: list[str]) -> None:
    """Subscribe and wait until Steam confirms; Steam then downloads the item in the background."""
    _run(game, "sub", workshop_ids)


def _run(game, action: str, workshop_ids: list[str]) -> None:
    from truckcfg import core, mods
    if core.is_running(game):
        raise RuntimeError(f"Close {game.title} first.")
    dll = steam_dll(game.exe)
    if not dll:
        raise RuntimeError(f"Couldn't find {game.title}'s steam_api64.dll.")
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":  # need stdout from the child
        exe = exe.with_name("python.exe")
    root = Path(__file__).resolve().parent.parent
    r = subprocess.run([str(exe), "-m", "truckcfg.steamugc", action, mods.STEAM_APP[game.key], str(dll.parent),
                        *workshop_ids], cwd=root, capture_output=True, text=True, timeout=60,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    result = [ln for ln in r.stdout.splitlines() if ln.startswith(("OK", "FAIL"))]
    if r.returncode or not result or result[-1] != "OK":
        why = (result[-1][5:] if result and result[-1].startswith("FAIL") else r.stderr.strip()[-300:]) or "unknown error"
        raise RuntimeError(f"Steam didn't {'subscribe' if action == 'sub' else 'unsubscribe'}: {why}")


def _child(action: str, appid: str, dll_dir: str, ids: list[int]) -> str:
    os.environ["SteamAppId"] = appid
    os.add_dll_directory(dll_dir)
    api = ctypes.CDLL(os.path.join(dll_dir, "steam_api64.dll"))
    api.SteamAPI_Init.restype = ctypes.c_bool
    if not api.SteamAPI_Init():
        return "FAIL Steam isn't running or you're not logged in."
    try:
        api.SteamAPI_SteamUGC_v017.restype = ctypes.c_void_p
        ugc = api.SteamAPI_SteamUGC_v017()
        if not ugc:
            return "FAIL this game's Steam library doesn't expose Workshop controls."
        call = api.SteamAPI_ISteamUGC_SubscribeItem if action == "sub" else api.SteamAPI_ISteamUGC_UnsubscribeItem
        call.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        call.restype = ctypes.c_uint64
        api.SteamAPI_ISteamUGC_GetItemState.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
        api.SteamAPI_ISteamUGC_GetItemState.restype = ctypes.c_uint32
        want = action == "sub"
        for i in ids:
            call(ugc, i)
        deadline = time.time() + 20
        while time.time() < deadline:
            api.SteamAPI_RunCallbacks()
            left = [i for i in ids if bool(api.SteamAPI_ISteamUGC_GetItemState(ugc, i) & ITEM_SUBSCRIBED) != want]
            if not left:
                return "OK"
            time.sleep(0.25)
        return f"FAIL Steam didn't confirm in time for {', '.join(map(str, left))}."
    finally:
        api.SteamAPI_Shutdown()


if __name__ == "__main__":
    print(_child(sys.argv[1], sys.argv[2], sys.argv[3], [int(x) for x in sys.argv[4:]]), flush=True)
