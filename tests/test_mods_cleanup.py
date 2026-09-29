import tempfile
import unittest
import zipfile
from pathlib import Path

from truckcfg import cleanup, core, mods

MANIFEST = '''SiiNunit
{
mod_package : .package_name {
    package_version: "2.5"
    display_name: "Realistic Rain Reflections v2.5"
    author: "Grimes"
    category[]: "graphics"
    category[]: "weather"
    compatible_versions[]: "1.61.*"
    description_file: "desc.txt"
}
}
'''


class PrettyInputTests(unittest.TestCase):
    def test_pretty(self):
        p = core.pretty_input
        self.assertEqual(p("mix", "`keyboard.h?0 | joy.b9?0 | semantical.horn?0`"), "Key H  ·  Joy Btn 9")
        self.assertEqual(p("mix", "`keyboard.key1?0 || long_press(joy.pov1_up?0) | semantical.cam1?0`"),
                         "Key 1  ·  Joy POV Up (hold)")
        self.assertEqual(p("mix", "`unbound?0 | short_press(joy2.b2?0) | semantical.x?0`"), "Joy2 Btn 2 (tap)")
        self.assertEqual(p("mix", "`semantical.airhorn?0`"), "Unbound")
        self.assertEqual(p("constant", "0.400000"), "0.400000")
        self.assertIsNone(p("mix", None))


class ModTests(unittest.TestCase):
    def test_manifest_from_zip_mod(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "rain.scs"
            with zipfile.ZipFile(path, "w") as z:
                z.writestr("manifest.sii", MANIFEST)
                z.writestr("desc.txt", "[red]Important![normal] Use HIGH priority.")
            m = mods.Mod(core.GAMES["ats"], "local", path, name="rain")
            mods._apply_manifest(m, mods._reader(path))
            self.assertEqual((m.name, m.version, m.author), ("Realistic Rain Reflections v2.5", "2.5", "Grimes"))
            self.assertEqual(m.categories, ["graphics", "weather"])
            self.assertEqual(m.description, "Important! Use HIGH priority.")
            self.assertEqual(m.compat("1.61.2.0"), "ok")
            self.assertEqual(m.compat("1.62.0.1"), "outdated")
            self.assertEqual(m.compat(None), "unknown")

    def test_non_zip_scs_is_tolerated(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "hashfs.scs"
            path.write_bytes(b"SCS#\x01\x00\x00\x00" + b"\x00" * 64)
            self.assertIsNone(mods._reader(path))

    def test_universal_package_is_compatible(self):
        m = mods.Mod(core.GAMES["ats"], "workshop", Path("x"), compatible=["1.40.*"], universal=True)
        self.assertEqual(m.compat("1.61.2.0"), "ok")

    def test_sizes(self):
        self.assertEqual(mods.fmt_size(512), "512 B")
        self.assertEqual(mods.fmt_size(5 * 1024 ** 2), "5.0 MB")
        self.assertEqual(mods.fmt_size(3 * 1024 ** 3), "3.0 GB")


class CleanupTests(unittest.TestCase):
    def test_clutter_names(self):
        yes = ["controls (# Name clash 2026-09-28 dm1phuC #).sii", "controls - Copy.sii",
               "config_local - Copy (2).cfg", "crash_detection (# Name clash 2026-09-29 0vus89C #)",
               "controls-DESKTOP-AB12CD.sii"]
        no = ["controls.sii", "gearbox_layout_zf_12_2.sii", "steam_profiles(1.61.2.0s).bak", "Copy of notes.txt"]
        for n in yes:
            self.assertTrue(cleanup.is_clutter(n), n)
        for n in no:
            self.assertFalse(cleanup.is_clutter(n), n)


if __name__ == "__main__":
    unittest.main()
