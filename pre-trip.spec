# PyInstaller spec for Pre-Trip.exe - build with:  python build.py
from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "webapp.pyw")],
    pathex=[str(ROOT)],
    datas=[(str(ROOT / "web"), "web")],
    hiddenimports=["truckcfg.steamugc", "cryptography.hazmat.primitives.ciphers"],
    excludes=["tkinter", "truckcfg.theme"],  # the classic tkinter app isn't part of the exe
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="Pre-Trip",
    icon=str(ROOT / "web" / "tcm.ico"),
    version=str(ROOT / "build" / "version_info.txt"),
    console=False,
    upx=False,
)
