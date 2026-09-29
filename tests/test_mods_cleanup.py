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


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.mod_dir, self.dl = root / "mod", root / "Downloads"
        self.dl.mkdir()
        self._saved = (mods.mod_dir, mods.disabled_dir, core.is_running)
        mods.mod_dir = lambda g: self.mod_dir
        mods.disabled_dir = lambda g: root / "mod_disabled"
        core.is_running = lambda g: False
        self.game = core.GAMES["ats"]

    def tearDown(self):
        mods.mod_dir, mods.disabled_dir, core.is_running = self._saved
        self.tmp.cleanup()

    def _zip(self, name, files):
        p = self.dl / name
        with zipfile.ZipFile(p, "w") as z:
            for n, data in files.items():
                z.writestr(n, data)
        return p

    def test_inspect_and_install(self):
        plain = self._zip("rain_ats.scs", {"manifest.sii": MANIFEST})
        bundle = self._zip("big_download.zip", {"readme.txt": "hi", "folder/cool_mod.scs": "x", "other.scs": "y"})
        junk = self._zip("photos.zip", {"a.jpg": "x"})
        self.assertEqual(mods.inspect_archive(plain), ("mod", ["rain_ats.scs"]))
        self.assertEqual(mods.inspect_archive(bundle)[0], "bundle")
        self.assertEqual(mods.inspect_archive(junk), ("unknown", []))

        found = mods.find_downloads(self.game, self.dl)
        self.assertEqual({d.path.name for d in found}, {"rain_ats.scs", "big_download.zip"})
        self.assertEqual(next(d for d in found if d.path == plain).game_hint, "ats")

        self.assertEqual([p.name for p in mods.install(self.game, plain)], ["rain_ats.scs"])
        self.assertEqual(sorted(p.name for p in mods.install(self.game, bundle)), ["cool_mod.scs", "other.scs"])
        self.assertTrue(all(d.installed for d in mods.find_downloads(self.game, self.dl)))
        with self.assertRaises(FileExistsError):
            mods.install(self.game, plain)
        with self.assertRaises(ValueError):
            mods.install(self.game, junk)

    def test_workshop_ids(self):
        p = mods.parse_workshop_id
        self.assertEqual(p("https://steamcommunity.com/sharedfiles/filedetails/?id=2440659232&searchtext="),
                         "2440659232")
        self.assertEqual(p("steam://url/CommunityFilePage/3013687427"), "3013687427")
        self.assertEqual(p("  1213282672 "), "1213282672")
        self.assertIsNone(p("https://example.com/mod.scs"))


if __name__ == "__main__":
    unittest.main()
