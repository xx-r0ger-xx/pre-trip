import unittest

from truckcfg import core

SAMPLE = (
    'SiiNunit\r\n{\r\ninput_config : _nameless.1 {\r\n version: 32\r\n config_lines: 3\r\n'
    ' config_lines[0]: "device joy `xinput.xinput_gamepad_1`"\r\n'
    ' config_lines[1]: "mix horn `keyboard.h?0 | joy.b9?0 | semantical.horn?0`"\r\n'
    ' config_lines[2]: "constant c_rsteersens 0.400000"\r\n}\r\n\r\n}\r\n'
)


class CoreTests(unittest.TestCase):
    def test_parse(self):
        b = core.parse_bindings(SAMPLE)
        self.assertEqual(b[("mix", "horn")], "`keyboard.h?0 | joy.b9?0 | semantical.horn?0`")
        self.assertEqual(b[("constant", "c_rsteersens")], "0.400000")
        self.assertEqual(len(b), 3)

    def test_apply_changes_only_target_lines_and_keeps_crlf(self):
        new, missing = core.apply_bindings(SAMPLE, {("mix", "horn"): "`joy.b9?0 | semantical.horn?0`",
                                                    ("mix", "nope"): "`x`"})
        self.assertEqual(missing, [("mix", "nope")])
        self.assertIn(' config_lines[1]: "mix horn `joy.b9?0 | semantical.horn?0`"\r\n', new)
        self.assertEqual(len(new.splitlines()), len(SAMPLE.splitlines()))
        self.assertEqual(new.count("\r\n"), SAMPLE.count("\r\n"))

    def test_noop_apply_is_identity(self):
        new, _ = core.apply_bindings(SAMPLE, core.parse_bindings(SAMPLE))
        self.assertEqual(new, SAMPLE)

    def test_diff_marks_missing(self):
        rows = core.diff_bindings({("mix", "a"): "1", ("mix", "b"): "2"}, {("mix", "a"): "1", ("mix", "c"): "3"})
        self.assertEqual([(r.name, r.left, r.right) for r in rows], [("b", "2", None), ("c", None, "3")])

    def test_is_mapped(self):
        self.assertTrue(core.is_mapped("mix", "`joy.b4?0 | semantical.motorbrake?0`"))
        self.assertTrue(core.is_mapped("mix", "`keyboard.f5?0 || short_press(joy.b4?0) | semantical.x?0`"))
        self.assertTrue(core.is_mapped("input", "`joy.x`"))
        self.assertTrue(core.is_mapped("constant", "0.300000"))
        self.assertFalse(core.is_mapped("mix", "`semantical.cabinlight?0`"))
        self.assertFalse(core.is_mapped("mix", "`unbound?0 | semantical.x?0`"))
        self.assertFalse(core.is_mapped("input", "``"))
        self.assertFalse(core.is_mapped("mix", None))

    def test_pretty_modifier(self):
        self.assertEqual(core.pretty_input("mix", "`unbound?0 || modifier(no_cstm_mod?0, short_press(joy.b11?0)) "
                                                  "| semantical.navmap?0`"), "Joy Btn 11 (tap) (no modifier)")
        self.assertEqual(core.pretty_input("mix", "`modifier(joy.b5?0, keyboard.h?0) | semantical.horn?0`"),
                         "Joy Btn 5 + Key H")

    def test_copy_works_both_ways(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            ets2, ats = Path(d, "e"), Path(d, "a")
            for folder, horn in ((ets2, "`joy.b9?0 | semantical.horn?0`"), (ats, "`keyboard.h?0 | semantical.horn?0`")):
                folder.mkdir()
                core.write_text_atomic(folder / "controls.sii", SAMPLE.replace(
                    "`keyboard.h?0 | joy.b9?0 | semantical.horn?0`", horn))
            e, a = core.Profile(core.GAMES["ets2"], ets2), core.Profile(core.GAMES["ats"], ats)
            with mock.patch.object(core, "is_running", return_value=False), \
                    mock.patch.object(core, "STORE", Path(d, "store")):
                core.copy_bindings(a, e, [("mix", "horn")])  # ATS -> ETS2
            self.assertEqual(core.parse_bindings(core.read_text(ets2 / "controls.sii"))[("mix", "horn")],
                             "`keyboard.h?0 | semantical.horn?0`")

    def test_real_profiles_roundtrip(self):
        for key, game in core.GAMES.items():
            for p in core.find_profiles(game):
                text = core.read_text(p.path / "controls.sii")
                b = core.parse_bindings(text)
                declared = int(text.split("config_lines:")[1].split()[0])
                self.assertEqual(len(b), declared, f"{key} {p.label}: parsed != declared line count")
                self.assertEqual(core.apply_bindings(text, b)[0], text)


if __name__ == "__main__":
    unittest.main()
