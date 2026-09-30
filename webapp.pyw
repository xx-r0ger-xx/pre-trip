"""Truck Config Manager - web UI (pywebview). The same truckcfg back end as app.pyw, with an HTML front end."""
import sys
from pathlib import Path

import webview

sys.path.insert(0, str(Path(__file__).parent))
from truckcfg.webapi import Api  # noqa: E402

if __name__ == "__main__":
    window = webview.create_window("Truck Config Manager", str(Path(__file__).parent / "web" / "index.html"),
                                   js_api=Api(), width=1480, height=940, min_size=(1100, 720),
                                   background_color="#06080c")
    webview.start(debug="--debug" in sys.argv)
