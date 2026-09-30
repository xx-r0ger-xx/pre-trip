import os
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from truckcfg import core, loadorder, mods

PROFILE = '''SiiNunit
{
user_profile : _nameless.1fd.236c.ff48 {
 face: 0
 active_mods: 3
 active_mods[0]: "mod_workshop_package.00000000B3A13883|CAT C15 6NZ Straight pipe sound"
 active_mods[1]: "early_autumn_ats_v4_6|Early Autumn v4.6"
 active_mods[2]: "realistic_rain_reflections_v2_5|Realistic Rain Reflections v2.5"
 customization: 156148
}

}
'''


def scsc(plain: bytes) -> bytes:
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    body = padder.update(zlib.compress(plain)) + padder.finalize()
    enc = Cipher(algorithms.AES(loadorder.SCSC_KEY), modes.CBC(iv)).encryptor()
    return b"ScsC" + b"\0" * 32 + iv + struct.pack("<I", len(plain)) + enc.update(body) + enc.finalize()


class LoadOrderTests(unittest.TestCase):
    def test_parse_is_top_first(self):
        order = loadorder.parse_order(PROFILE)
        self.assertEqual([e.package for e in order],
                         ["realistic_rain_reflections_v2_5", "early_autumn_ats_v4_6",
                          "mod_workshop_package.00000000B3A13883"])
        self.assertEqual(order[0].display, "Realistic Rain Reflections v2.5")

    def test_replace_roundtrip_and_leaves_rest_alone(self):
        order = loadorder.parse_order(PROFILE)
        self.assertEqual(loadorder.replace_order(PROFILE, order), PROFILE)
        new = loadorder.replace_order(PROFILE, [order[1], loadorder.Entry("new_mod", "New")])
        self.assertIn(' active_mods: 2\n active_mods[0]: "new_mod|New"\n'
                      ' active_mods[1]: "early_autumn_ats_v4_6|Early Autumn v4.6"\n customization', new)
        self.assertEqual(loadorder.replace_order(PROFILE, []).count("active_mods"), 1)

    def test_crlf_preserved(self):
        crlf = PROFILE.replace("\n", "\r\n")
        out = loadorder.replace_order(crlf, loadorder.parse_order(crlf)[:1])
        self.assertNotIn("\n active_mods", out.replace("\r\n", ""))
        self.assertIn('active_mods: 1\r\n active_mods[0]: "realistic_rain_reflections_v2_5|', out)

    def test_decode_encrypted_and_plain(self):
        self.assertEqual(loadorder.decode(scsc(PROFILE.encode())), PROFILE)
        self.assertEqual(loadorder.decode(PROFILE.encode()), PROFILE)
        with self.assertRaises(ValueError):
            loadorder.decode(b"BSII\0\0\0\0")

    def test_write_backs_up_and_writes_text(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(loadorder, "BACKUPS", Path(d) / "bk"), \
                mock.patch.object(core, "is_running", return_value=False):
            p = Path(d) / "profile.sii"
            enc = scsc(PROFILE.encode())
            p.write_bytes(enc)
            dest = loadorder.write_order(p, core.GAMES["ats"], loadorder.parse_order(PROFILE)[::-1])
            self.assertEqual((dest / "profile.sii").read_bytes(), enc)
            self.assertTrue(p.read_text(encoding="utf-8").startswith("SiiNunit"))
            self.assertEqual(loadorder.read_order(p)[1][0].package, "mod_workshop_package.00000000B3A13883")

    def test_refuses_while_game_running(self):
        with mock.patch.object(core, "is_running", return_value=True):
            with self.assertRaises(RuntimeError):
                loadorder.write_order(Path("x"), core.GAMES["ats"], [])

    def test_package_names(self):
        g = core.GAMES["ats"]
        self.assertEqual(mods.Mod(g, "workshop", Path("x"), workshop_id="3013687427").package,
                         "mod_workshop_package.00000000B3A13883")
        self.assertEqual(mods.Mod(g, "local", Path("mod/early_autumn_ats_v4_6.scs")).package, "early_autumn_ats_v4_6")
        self.assertEqual(loadorder.workshop_package("830663438"), "mod_workshop_package.000000003182EB0E")


class RecommendedOrderTests(unittest.TestCase):
    def test_classify(self):
        c = lambda n, cats=(): loadorder.classify(n, cats)[0].key
        self.assertEqual(c("Weather_3.9_16k", ["other"]), "graphics")
        self.assertEqual(c("Sound Fixes Pack v26.66 - ATS"), "sound")
        self.assertEqual(c("Western Star 57X Improved Dashboard", ["truck"]), "interior")  # higher group wins
        self.assertEqual(c("Bright Headlights", ["graphics", "interior"]), "graphics")
        self.assertEqual(c("ProMods Canada Def Patch", ["map"]), "fixes")
        self.assertEqual(c("Some Map", ["map"]), "maps")
        self.assertEqual(c("Mystery Mod"), "ui")

    def test_stable_group_sort(self):
        E = loadorder.Entry
        order = [E("m", "Big Map"), E("t2", "Traffic B"), E("w", "Winter Weather"), E("t1", "Traffic A")]
        cats = {"m": ["map"], "t1": ["ai_traffic"], "t2": ["ai_traffic"], "w": []}
        new = loadorder.recommended_order(order, lambda e: cats[e.package])
        self.assertEqual([e.package for e in new], ["w", "t2", "t1", "m"])  # traffic keeps B before A

    def test_placement_from_notes(self):
        P = loadorder.placement
        rrr = P("Place above either New Summer, Spring, Early Autumn or Late Autumn/Mild Winter in Mod Manager")
        self.assertEqual(rrr.above, ("New Summer", "Spring", "Early Autumn", "Late Autumn", "Mild Winter"))
        self.assertEqual(P("Early Autumn should be given a HIGH priority in Mod Manager.").pin, -1)
        self.assertEqual(P("(sound fixes pack is exceptional but put my mod on top piority)").pin, -1)
        self.assertEqual(P("Load this below ProMods in the mod manager.").below, ("ProMods",))
        self.assertEqual(P("-Added Liters in the tank (At the bottom of the display)"), loadorder.Placement())
        self.assertEqual(P("Adds a light bar on top of the cab."), loadorder.Placement())

    def test_notes_drive_the_sort(self):
        E = loadorder.Entry
        notes = {"ea": "Early Autumn should be given a HIGH priority in Mod Manager.",
                 "rrr": "Place above either New Summer, Spring, Early Autumn or Late Autumn in Mod Manager",
                 "w": "", "s": ""}
        order = [E("w", "Other Weather"), E("ea", "Early Autumn v4.6"), E("s", "Sound Fixes Pack"),
                 E("rrr", "Realistic Rain Reflections v2.5")]
        new = loadorder.recommended_order(order, lambda e: [], lambda e: notes[e.package])
        self.assertEqual([e.package for e in new], ["rrr", "ea", "w", "s"])
        loop = {"a": "Place above B Mod.", "b": "Place above A Mod."}
        pair = [E("a", "A Mod"), E("b", "B Mod")]
        self.assertEqual(len(loadorder.recommended_order(pair, lambda e: [], lambda e: loop[e.package])), 2)

    def test_author_notes(self):
        self.assertEqual(loadorder.author_notes("Give this a HIGH priority in Mod Manager. Enjoy!"),
                         ["Give this a HIGH priority in Mod Manager."])
        self.assertEqual(loadorder.author_notes("Shows litres (at the bottom of the display)."), [])


if __name__ == "__main__":
    unittest.main()
