"""Build dist/Pre-Trip.exe:  python build.py   (needs: pip install -r requirements.txt)"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from truckcfg import __version__  # noqa: E402

nums = tuple(int(x) for x in __version__.split(".")) + (0,) * (4 - len(__version__.split(".")))
(ROOT / "build").mkdir(exist_ok=True)
(ROOT / "build" / "version_info.txt").write_text(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'xx-r0ger-xx'),
      StringStruct('FileDescription', 'Pre-Trip - setup manager for ETS2 and ATS'),
      StringStruct('FileVersion', '{__version__}'),
      StringStruct('InternalName', 'Pre-Trip'),
      StringStruct('OriginalFilename', 'Pre-Trip.exe'),
      StringStruct('ProductName', 'Pre-Trip'),
      StringStruct('ProductVersion', '{__version__}'),
      StringStruct('LegalCopyright', 'MIT License')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)
""", encoding="utf-8")
subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", str(ROOT / "pre-trip.spec")], cwd=ROOT, check=True)
exe = ROOT / "dist" / "Pre-Trip.exe"
print(f"\nBuilt {exe}  ({exe.stat().st_size / 1e6:.1f} MB, v{__version__})")
