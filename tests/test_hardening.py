"""Regression tests for the 2026-10 review fixes: damaged files and odd failures degrade one item, never a whole page."""
import json
from types import SimpleNamespace
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import os

from sandbox import CONTROLS, Sandbox, _profile_sii, api, make_scs

from truckcfg import cleanup, core, mods, steamugc


def add_old_profile(sb, key="ets2"):
    """A second, older profile whose folder name sorts FIRST - the one the old [0] logic silently used."""
    d = sb.game_docs(key) / "steam_profiles" / "0000"  # sorts before the sandbox's profile
    d.mkdir(parents=True)
    core.write_text_atomic(d / "controls.sii", CONTROLS.format(horn="joy.b1?0", light="joy.b2?0", sens="0.1"))
    core.write_text_atomic(d / "profile.sii", _profile_sii([("old_mod", "Old Mod")]))
    for f in (d / "controls.sii", d / "profile.sii"):
        os.utime(f, (1_000_000, 1_000_000))  # played long ago
    return d


class Profiles(unittest.TestCase):
    def test_defaults_to_last_played_not_first_folder(self):
        with Sandbox() as sb:
            add_old_profile(sb)
            p = core.active_profile(core.GAMES["ets2"])
            self.assertEqual(p.path, sb.profile_dir("ets2"))
            self.assertEqual(len(api().overview()["ets2"]["profiles"]), 2)

    def test_picked_profile_is_the_only_one_written_and_survives_restart(self):
        with Sandbox() as sb:
            old = add_old_profile(sb)
            before_main = sb.profile_sii("ets2").read_text()
            a = api()
            a.select_profile("ets2", "steam_profiles/0000")
            self.assertEqual(api().overview()["ets2"]["profile"], core.Profile(core.GAMES["ets2"], old).name)
            a.save_order("ets2", ["loud_horn"])
            self.assertIn("loud_horn", (old / "profile.sii").read_text())
            self.assertEqual(sb.profile_sii("ets2").read_text(), before_main)  # the other profile is untouched
            with self.assertRaises(RuntimeError):
                a.select_profile("ets2", "steam_profiles/gone")

    def test_restore_refuses_another_profiles_backup_and_only_restores_the_mod_list(self):
        with Sandbox() as sb:
            old = add_old_profile(sb)
            a = api()
            a.save_order("ets2", list(reversed(sb.order("ets2"))))  # backup of the main profile
            ev = next(e for e in a.logbook("ets2")["events"] if e["kind"] == "loadorder")
            a.select_profile("ets2", "steam_profiles/0000")
            self.assertNotIn(ev["restore"]["id"], [e.get("restore", {}).get("id") for e in a.logbook("ets2")["events"]])
            with self.assertRaises(RuntimeError):
                a.restore("ets2", "profile", ev["restore"]["id"])
            self.assertIn("old_mod", (old / "profile.sii").read_text())

    def test_crash_finder_stays_on_its_profile_and_cannot_start_twice(self):
        with Sandbox() as sb:
            add_old_profile(sb)
            a = api()
            original = sb.order("ets2")
            a.bisect_start("ets2")
            with self.assertRaises(RuntimeError):
                a.bisect_start("ets2")
            with self.assertRaises(RuntimeError):
                a.select_profile("ets2", "steam_profiles/0000")
            a.bisect_stop("ets2")
            self.assertEqual(sb.order("ets2"), original)


class Snapshots(unittest.TestCase):
    def test_one_damaged_snapshot_does_not_hide_the_rest(self):
        with Sandbox() as sb:
            a = api()
            a.snapshot("ets2", "good")
            root = core.snapshot_root(core.find_profiles(core.GAMES["ets2"])[0])
            for name, meta in (("broken-json", "{nope"), ("empty", ""), ("not-a-dict", "[1, 2]")):
                (root / name).mkdir()
                (root / name / "meta.json").write_text(meta)
            (root / "no-meta").mkdir()
            snaps = core.list_snapshots(core.find_profiles(core.GAMES["ets2"])[0])
            self.assertEqual([s.label for s in snaps], ["good"])
            self.assertIn("ets2", a.inspect())


class Inspection(unittest.TestCase):
    def test_a_failing_check_is_reported_and_the_rest_still_render(self):
        with Sandbox():
            with mock.patch.object(cleanup, "find_clutter", side_effect=OSError("disk said no")):
                res = api().inspect()
            ids = [c["id"] for c in res["ets2"]["checks"]]
            self.assertIn("inspect-error", ids)
            self.assertIn("order", ids)  # the load-order check still ran
            err = next(c for c in res["ets2"]["checks"] if c["id"] == "inspect-error")
            self.assertIn("disk said no", err["detail"])
            self.assertIn("ats", res)

    def test_a_whole_game_failing_does_not_blank_the_other(self):
        with Sandbox():
            a = api()
            real = a._mod_list
            with mock.patch.object(a, "_mod_list", lambda k, fresh=False: (_ for _ in ()).throw(RuntimeError("boom"))
                                   if k == "ets2" else real(k, fresh)):
                res = a.inspect()
            self.assertEqual(res["ets2"]["checks"][0]["id"], "inspect-error")
            self.assertEqual(set(res["ets2"]["gauges"]), {"mods", "conflicts", "drift", "crash"})
            self.assertNotEqual(res["ats"]["checks"][0]["id"], "inspect-error")


class RunningCheck(unittest.TestCase):
    """is_running guards every write, so "couldn't tell" must refuse, not pass."""
    def test_tasklist_missing_or_failing_raises(self):
        g = core.GAMES["ats"]
        with mock.patch("truckcfg.core.subprocess.run", side_effect=FileNotFoundError("tasklist")):
            with self.assertRaises(RuntimeError):
                core.is_running(g)
            self.assertTrue(core.seems_running(g))
        with mock.patch("truckcfg.core.subprocess.run",
                        return_value=subprocess.CompletedProcess([], 1, stdout="", stderr="Access denied")):
            with self.assertRaises(RuntimeError):
                core.is_running(g)

    def test_normal_answers(self):
        g = core.GAMES["ats"]
        for out, want in (("INFO: No tasks are running which match the specified criteria.", False),
                          (f"{g.exe}   1234 Console   1   2,000,000 K", True)):
            with mock.patch("truckcfg.core.subprocess.run", return_value=subprocess.CompletedProcess([], 0, stdout=out)):
                self.assertEqual(core.is_running(g), want)


class LooseModPaths(unittest.TestCase):
    def test_manifest_names_cannot_leave_the_mod_folder(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            mod = root / "mods" / "loose"
            (mod / "sub").mkdir(parents=True)
            (mod / "sub" / "desc.txt").write_text("inside")
            (root / "secret.txt").write_text("outside")
            read = mods._dir_reader(mod)
            self.assertEqual(read("sub/desc.txt"), "inside")
            for bad in ("../../secret.txt", "..\\..\\secret.txt", str(root / "secret.txt"), "", "."):
                self.assertIsNone(read(bad), bad)


class BundleInstall(unittest.TestCase):
    def test_a_bad_member_leaves_nothing_behind(self):
        with Sandbox() as sb:
            dl = sb.root / "Downloads"
            pack = dl / "pack.zip"
            with zipfile.ZipFile(pack, "w") as z:
                z.writestr("pack/a.scs", make_scs(sb.root / "a.scs").read_bytes())
                z.writestr("pack/b.scs", make_scs(sb.root / "b.scs").read_bytes())
            real_open = zipfile.ZipFile.open

            def flaky(self, info, *a, **kw):
                if getattr(info, "filename", info).endswith("b.scs"):
                    raise zipfile.BadZipFile("Bad CRC-32")
                return real_open(self, info, *a, **kw)
            with mock.patch.object(zipfile.ZipFile, "open", flaky):
                res = api().install("ets2", [str(pack)])
            self.assertFalse(res[0]["ok"])
            self.assertFalse((sb.game_docs("ets2") / "mod" / "a.scs").exists())
            self.assertFalse((sb.game_docs("ets2") / "mod" / "b.scs").exists())

    def test_refuses_when_the_disk_is_too_full(self):
        with Sandbox() as sb:
            pack = sb.root / "Downloads" / "pack.zip"
            with zipfile.ZipFile(pack, "w") as z:
                z.writestr("pack/a.scs", make_scs(sb.root / "a.scs").read_bytes())
            with mock.patch("truckcfg.mods.shutil.disk_usage", return_value=SimpleNamespace(total=0, used=0, free=1024)):
                res = api().install("ets2", [str(pack)])
            self.assertFalse(res[0]["ok"])
            self.assertIn("disk space", res[0]["error"])
            self.assertFalse((sb.game_docs("ets2") / "mod" / "a.scs").exists())


class Quarantine(unittest.TestCase):
    def test_same_second_runs_keep_both_manifests(self):
        with Sandbox() as sb:
            prof = sb.profile_dir("ets2")
            (prof / "controls - Copy.sii").write_text("a")
            (prof / "controls - Copy (2).sii").write_text("b")
            a = api()
            rels = [i["rel"] for i in a.cleanup("ets2")["items"]]
            with mock.patch("truckcfg.cleanup.datetime") as dt:
                dt.now.return_value.strftime.return_value = "20261002-120000"
                a.quarantine("ets2", rels[:1])
                a.quarantine("ets2", rels[1:])
            manifests = list((sb.store / "quarantine").rglob("manifest.json"))
            self.assertEqual(len(manifests), 2)
            self.assertEqual(sum(len(json.loads(m.read_text())) for m in manifests), 2)

    def test_a_failed_move_still_records_the_moves_that_happened(self):
        with Sandbox() as sb:
            prof = sb.profile_dir("ets2")
            (prof / "controls - Copy.sii").write_text("a")
            (prof / "game - Copy.sii").write_text("b")
            items = cleanup.find_clutter(core.GAMES["ets2"])
            real_move, calls = cleanup.shutil.move, []

            def move(src, dst):
                calls.append(src)
                if len(calls) == 2:
                    raise PermissionError("locked")
                return real_move(src, dst)
            with mock.patch("truckcfg.cleanup.shutil.move", move), self.assertRaises(PermissionError):
                cleanup.quarantine(items)
            m = json.loads(next((sb.store / "quarantine").rglob("manifest.json")).read_text())
            self.assertEqual(len(m), 1)
            self.assertTrue(Path(m[0]["to"]).is_file())


class SteamHelperArgs(unittest.TestCase):
    def test_malformed_or_unknown_actions_are_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            out = str(Path(t) / "r.txt")
            with mock.patch.object(steamugc, "_child") as child:
                self.assertEqual(steamugc.main([]), 2)
                self.assertEqual(steamugc.main([out, "sub"]), 2)
                self.assertEqual(steamugc.main([out, "delete", "270880", t, "1"]), 2)
                child.assert_not_called()


if __name__ == "__main__":
    unittest.main()
