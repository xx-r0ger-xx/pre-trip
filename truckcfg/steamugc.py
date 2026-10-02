"""Subscribe to / unsubscribe from Steam Workshop items using the game's own steam_api64.dll.

Runs in a short-lived child process (python -m truckcfg.steamugc, or Pre-Trip.exe --steamugc) because SteamAPI_Init
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


def child_command(args: list[str]) -> list[str]:
    """How to start the helper: the packaged Pre-Trip.exe runs itself with --steamugc; from source it's python -m."""
    if getattr(sys, "frozen", False):
        return [sys.executable, "--steamugc", *args]
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe":
        exe = exe.with_name("python.exe")
    return [str(exe), "-m", "truckcfg.steamugc", *args]


def _run(game, action: str, workshop_ids: list[str]) -> None:
    import tempfile
    from truckcfg import core, mods
    if core.is_running(game):
        raise RuntimeError(f"Close {game.title} first.")
    dll = steam_dll(game.exe)
    if not dll:
        raise RuntimeError(f"Couldn't find {game.title}'s steam_api64.dll.")
    fd, out = tempfile.mkstemp(prefix="pretrip-steam-", suffix=".txt")
    os.close(fd)
    try:
        root = Path(__file__).resolve().parent.parent
        try:
            r = subprocess.run(child_command([out, action, mods.STEAM_APP[game.key], str(dll.parent), *workshop_ids]),
                               cwd=root, capture_output=True, text=True, timeout=60,
                               creationflags=subprocess.CREATE_NO_WINDOW)
        except subprocess.TimeoutExpired as e:
            raise RuntimeError("Steam didn't answer within a minute. Check Steam is running, then try again.") from e
        result = Path(out).read_text(encoding="utf-8").strip()
    finally:
        Path(out).unlink(missing_ok=True)
    if r.returncode or result != "OK":
        why = (result[5:] if result.startswith("FAIL") else (r.stderr or "").strip()[-300:]) or "unknown error"
        raise RuntimeError(f"Steam didn't {'subscribe' if action == 'sub' else 'unsubscribe'}: {why}")


def main(argv: list[str]) -> int:
    """Child entry point: <result file> <sub|unsub> <appid> <dll dir> <ids...>. Writes OK or FAIL <reason>."""
    if len(argv) < 5 or argv[1] not in ("sub", "unsub"):
        print("usage: <result file> <sub|unsub> <appid> <dll dir> <ids...>", file=sys.stderr)
        return 2
    out, action, appid, dll_dir, *ids = argv
    try:
        msg = _child(action, appid, dll_dir, [int(x) for x in ids])
    except Exception as e:  # noqa: BLE001 - report anything back to the app instead of dying silently
        msg = f"FAIL {e}"
    Path(out).write_text(msg, encoding="utf-8")
    return 0


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
    sys.exit(main(sys.argv[1:]))
