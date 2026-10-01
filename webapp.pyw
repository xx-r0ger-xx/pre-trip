"""Pre-Trip - setup manager for Euro Truck Simulator 2 and American Truck Simulator (pywebview + HTML front end)."""
import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

import webview

sys.path.insert(0, str(Path(__file__).parent))
from truckcfg.webapi import Api  # noqa: E402


def initial_size(pref=(1480, 940), fill=0.92):
    """Fit the window inside the screen's work area (above the taskbar), in the logical units pywebview uses."""
    try:
        r = wintypes.RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)  # SPI_GETWORKAREA
        scale = ctypes.windll.user32.GetDpiForSystem() / 96
        w, h = (r.right - r.left) / scale, (r.bottom - r.top) / scale
        return int(min(pref[0], w * fill)), int(min(pref[1], h * fill))
    except (AttributeError, OSError):
        return pref


if __name__ == "__main__":
    width, height = initial_size()
    window = webview.create_window("Pre-Trip", str(Path(__file__).parent / "web" / "index.html"),
                                   js_api=Api(), width=width, height=height, min_size=(900, 600),
                                   background_color="#06080c")
    webview.start(debug="--debug" in sys.argv)
