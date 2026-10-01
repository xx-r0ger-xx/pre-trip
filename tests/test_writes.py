"""Every action that writes to a game's files, exercised end to end inside a sandbox (see sandbox.py).

For each one: it does what it says, it backs up what it replaces, it refuses while that game is running, it can be
undone, and it never touches anything outside its target.
"""
import itertools
import unittest
from pathlib import Path

from sandbox import Sandbox, api

from truckcfg import core, graphics, logbook


class ControlsSync(unittest.TestCase):
    def test_both_directions_and_only_target_lines_change(self):
        with Sandbox() as sb:
            a = api()
            before_ets2 = core.read_text(sb.profile_dir("ets2") / "controls.sii")
            a.sync_controls("ats", "ets2")
            self.assertEqual(sb.bindings("ets2")[("mix", "horn")], "`keyboard.h?0 | joy.b9?0 | semantical.horn?0`")
            after = core.read_text(sb.profile_dir("ets2") / "controls.sii")
            changed = [(x, y) for x, y in zip(before_ets2.splitlines(), after.splitlines()) if x != y]
            self.assertEqual(len(changed), 2)  # horn and light only
            self.assertEqual(after.count("\r\n"), before_ets2.count("\r\n"))  # line endings kept
            labels = [s.meta["label"] for s in core.list_snapshots(core.find_profiles(core.GAMES["ets2"])[0])]
            self.assertIn("auto-before-copy-from-ats", labels)
            self.assertEqual(a.twin()["controls"], [])
            # and back the other way, for a single named binding
            core.write_text_atomic(sb.profile_dir("ats") / "controls.sii", core.read_text(sb.profile_dir("ats") / "controls.sii")
                                   .replace("keyboard.h?0 | joy.b9?0", "joy.b1?0"))
            a.sync_controls("ets2", "ats", ["horn"])
            self.assertEqual(sb.bindings("ats")[("mix", "horn")], "`keyboard.h?0 | joy.b9?0 | semantical.horn?0`")

    def test_refuses_while_target_running(self):
        with Sandbox() as sb:
            before = core.read_text(sb.profile_dir("ets2") / "controls.sii")
            sb.running.add("ets2")
            with self.assertRaises(RuntimeError):
                api().sync_controls("ats", "ets2")
            self.assertEqual(core.read_text(sb.profile_dir("ets2") / "controls.sii"), before)


class GraphicsSync(unittest.TestCase):
    def test_copies_values_backs_up_and_keeps_other_lines(self):
        with Sandbox() as sb:
            msg = api().sync_graphics("ats", "ets2")
            cfg = sb.config("ets2")
            self.assertIn('uset r_mode_width "2560"', cfg)
            self.assertIn('uset r_vsync "1"', cfg)
            self.assertIn('uset s_init_master_volume "0.75"', cfg)  # not a graphics key, untouched
            self.assertIn("\r\n", cfg)
            backups = list(sb.game_docs("ets2").glob("config.cfg.bak-*"))
            self.assertEqual(len(backups), 1)
            self.assertIn('uset r_mode_width "3840"', backups[0].read_text())
            self.assertIn("Copied 3", msg)
            self.assertEqual([r for r in api().twin()["graphics"] if not r["same"]], [])

    def test_selected_keys_only_and_missing_keys_appended(self):
        with Sandbox() as sb:
            api().sync_graphics("ats", "ets2", ["r_vsync"])
            self.assertIn('uset r_vsync "1"', sb.config("ets2"))
            self.assertIn('uset r_mode_width "3840"', sb.config("ets2"))
            graphics.write_keys(core.GAMES["ets2"], {"r_dof": "0"})
            self.assertTrue(sb.config("ets2").rstrip().endswith('uset r_dof "0"'))

    def test_refuses_while_running(self):
        with Sandbox() as sb:
            sb.running.add("ets2")
            before = sb.config("ets2")
            with self.assertRaises(RuntimeError):
                api().sync_graphics("ats", "ets2")
            self.assertEqual(sb.config("ets2"), before)
            self.assertEqual(list(sb.game_docs("ets2").glob("config.cfg.bak-*")), [])


class ReShadeSync(unittest.TestCase):
    def test_copies_dll_ini_preset_and_shaders(self):
        with Sandbox() as sb:
            api().sync_reshade("ats", "ets2")
            b = sb.bin_dir("ets2")
            for f in ("dxgi.dll", "ReShade.ini", "ReShadePreset.ini", "reshade-shaders/Shaders/CAS.fx"):
                self.assertTrue((b / f).is_file(), f)
            self.assertEqual(api().twin()["reshade"]["ets2"]["effects"], ["CAS"])

    def test_refuses_when_source_has_no_reshade_or_target_running(self):
        with Sandbox() as sb:
            with self.assertRaises(RuntimeError):
                api().sync_reshade("ets2", "ats")
            sb.running.add("ets2")
            with self.assertRaises(RuntimeError):
                api().sync_reshade("ats", "ets2")
            self.assertFalse((sb.bin_dir("ets2") / "dxgi.dll").exists())


class LoadOrder(unittest.TestCase):
    def test_save_backs_up_and_round_trips(self):
        with Sandbox() as sb:
            a = api()
            original = sb.order("ets2")
            a.save_order("ets2", ["big_map", "rain_addon", "weather_base"])
            self.assertEqual(sb.order("ets2"), ["big_map", "rain_addon", "weather_base"])
            backups = list((sb.store / "profile-backups" / "ets2").glob("*/profile.sii"))
            self.assertEqual(len(backups), 1)
            restored = [e.package for e in __import__("truckcfg.loadorder").loadorder.read_order(backups[0])[1]]
            self.assertEqual(restored, original)
            self.assertIn("customization: 1", sb.profile_sii("ets2").read_text())  # rest of the profile kept

    def test_refuses_while_running(self):
        with Sandbox() as sb:
            sb.running.add("ets2")
            with self.assertRaises(RuntimeError):
                api().save_order("ets2", ["big_map"])
            self.assertEqual(sb.order("ets2"), ["weather_base", "rain_addon", "loud_horn"])


class Loadouts(unittest.TestCase):
    def test_save_apply_skips_uninstalled_and_delete(self):
        with Sandbox() as sb:
            a = api()
            a.save_loadout("ets2", "Vanilla-ish", ["loud_horn"])
            a.save_loadout("ets2", "Ghost", ["rain_addon", "not_installed_mod"])
            msg = a.apply_loadout("ets2", "Ghost")
            self.assertEqual(sb.order("ets2"), ["rain_addon"])
            self.assertIn("Skipped 1", msg)
            a.apply_loadout("ets2", "Vanilla-ish")
            self.assertEqual(sb.order("ets2"), ["loud_horn"])
            self.assertEqual(sorted(a.delete_loadout("ets2", "Ghost")), ["Vanilla-ish"])
            with self.assertRaises(ValueError):
                a.save_loadout("ets2", "   ", [])


class Restore(unittest.TestCase):
    def test_snapshot_profile_and_config_restores_are_reversible(self):
        with Sandbox() as sb:
            a = api()
            # controls: snapshot, change, restore
            a.snapshot("ets2", "before")
            original_controls = core.read_text(sb.profile_dir("ets2") / "controls.sii")
            a.sync_controls("ats", "ets2")
            snap = next(s for s in core.list_snapshots(core.find_profiles(core.GAMES["ets2"])[0]) if s.meta["label"] == "before")
            a.restore("ets2", "snapshot", snap.path.name)
            self.assertEqual(core.read_text(sb.profile_dir("ets2") / "controls.sii"), original_controls)
            # load order: save, then restore the automatic backup
            original_order = sb.order("ets2")
            a.save_order("ets2", ["big_map"])
            backup = next(e for e in logbook.events(core.GAMES["ets2"]) if e["kind"] == "loadorder")
            a.restore("ets2", "profile", backup["restore"]["id"])
            self.assertEqual(sb.order("ets2"), original_order)
            # graphics: sync, then restore config backup; the overwritten config is itself backed up
            original_cfg = sb.config("ets2")
            a.sync_graphics("ats", "ets2")
            bak = next(e for e in logbook.events(core.GAMES["ets2"]) if e["kind"] == "graphics")
            a.restore("ets2", "config", bak["restore"]["id"])
            self.assertEqual(sb.config("ets2"), original_cfg)
            self.assertGreaterEqual(len(list(sb.game_docs("ets2").glob("config.cfg.bak-*"))), 2)

    def test_refuses_while_running(self):
        with Sandbox() as sb:
            a = api()
            a.snapshot("ets2", "x")
            snap = core.list_snapshots(core.find_profiles(core.GAMES["ets2"])[0])[0]
            sb.running.add("ets2")
            for kind, ident in (("snapshot", snap.path.name), ("profile", "nope"), ("config", "nope")):
                with self.assertRaises(RuntimeError):
                    a.restore("ets2", kind, ident)


class CrashFinder(unittest.TestCase):
    def run_finder(self, sb, culprit):
        """Play the crash finder against an oracle: the game 'crashes' whenever the culprit is active."""
        a = api()
        original = sb.order("ets2")
        st = a.bisect_start("ets2")
        for _ in range(10):
            active = sb.order("ets2")
            self.assertTrue(set(active) <= set(original))  # never adds anything
            self.assertEqual(active, [p for p in original if p in active])  # keeps the relative order
            st = a.bisect_report("ets2", culprit in active)
            if st.get("culprit") is not None and not st["testing"]:
                break
        return st, original

    def test_finds_every_possible_culprit_and_restores_order(self):
        for culprit in ("weather_base", "rain_addon", "loud_horn"):
            with self.subTest(culprit=culprit), Sandbox() as sb:
                st, original = self.run_finder(sb, culprit)
                self.assertEqual(st["culprit"], culprit)
                self.assertEqual(sb.order("ets2"), original)
                self.assertIsNone(logbook.bisect_state(core.GAMES["ets2"]))

    def test_larger_lists(self):
        with Sandbox() as sb:
            api().save_order("ets2", ["weather_base", "rain_addon", "loud_horn", "big_map"])
            for culprit in ("weather_base", "big_map"):
                with self.subTest(culprit=culprit):
                    st, original = self.run_finder(sb, culprit)
                    self.assertEqual(st["culprit"], culprit)
                    self.assertEqual(sb.order("ets2"), original)

    def test_stop_restores_and_running_game_blocks(self):
        with Sandbox() as sb:
            a = api()
            original = sb.order("ets2")
            a.bisect_start("ets2")
            self.assertNotEqual(sb.order("ets2"), original)
            a.bisect_stop("ets2")
            self.assertEqual(sb.order("ets2"), original)
            sb.running.add("ets2")
            with self.assertRaises(RuntimeError):
                a.bisect_start("ets2")
            self.assertEqual(sb.order("ets2"), original)

    def test_needs_two_mods(self):
        with Sandbox() as sb:
            api().save_order("ets2", ["loud_horn"])
            with self.assertRaises(RuntimeError):
                api().bisect_start("ets2")


class Alerts(unittest.TestCase):
    def test_acknowledge_holds_until_the_problem_changes(self):
        with Sandbox() as sb:
            a = api()
            order = next(c for c in a.inspect()["ets2"]["checks"] if c["id"] == "order")
            a.ack("ets2", "order", order["fp"])
            self.assertTrue(next(c for c in a.inspect()["ets2"]["checks"] if c["id"] == "order")["acked"])
            a.save_order("ets2", ["loud_horn", "weather_base", "rain_addon"])  # a different wrong order
            again = next(c for c in a.inspect()["ets2"]["checks"] if c["id"] == "order")
            self.assertFalse(again["acked"])
            a.ack("ets2", "order", again["fp"])
            a.unack("ets2", "order")
            self.assertFalse(next(c for c in a.inspect()["ets2"]["checks"] if c["id"] == "order")["acked"])

    def test_drift_review_keep_and_restore(self):
        with Sandbox() as sb:
            a = api()
            a.snapshot("ets2", "baseline")
            a.sync_controls("ats", "ets2")  # takes its own snapshots, so drift is 0 now
            self.assertEqual(a.drift("ets2")["rows"], [])
            core.write_text_atomic(sb.profile_dir("ets2") / "controls.sii",
                                   core.read_text(sb.profile_dir("ets2") / "controls.sii").replace("keyboard.h?0 | joy.b9?0", "joy.b1?0"))
            d = a.drift("ets2")
            self.assertEqual([r["name"] for r in d["rows"]], ["horn"])
            a.restore("ets2", "snapshot", d["snapshot"]["id"])
            self.assertEqual(a.drift("ets2")["rows"], [])

    def test_unsaved_studio_order_is_inspected(self):
        with Sandbox() as sb:
            a = api()
            good = a.recommend("ets2", sb.order("ets2"))
            a.save_order("ets2", good)
            clean = [c["id"] for c in a.inspect()["ets2"]["checks"]]
            self.assertNotIn("order", clean)
            bad = [good[1], good[0]] + good[2:]
            ids = [c["id"] for c in a.inspect({"ets2": bad})["ets2"]["checks"]]
            self.assertIn("unsaved", ids)
            self.assertIn("order", ids)
            self.assertEqual(sb.order("ets2"), good)  # inspecting never writes


class Isolation(unittest.TestCase):
    def test_writes_outside_the_sandbox_are_blocked(self):
        with Sandbox():
            with self.assertRaises(AssertionError):
                core.write_text_atomic(Path.home() / "pretrip-should-not-exist.txt", "x")
        self.assertFalse((Path.home() / "pretrip-should-not-exist.txt").exists())

    def test_one_game_pc(self):
        with Sandbox(games=("ets2",)):
            a = api()
            self.assertEqual([k for k, v in a.games().items() if v["owned"]], ["ets2"])
            self.assertFalse(a.twin()["available"])
            self.assertEqual(list(a.inspect()), ["ets2"])


if __name__ == "__main__":
    unittest.main()
