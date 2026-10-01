"""Installing, removing and Workshop actions, plus Cleanup - all inside the sandbox (see sandbox.py)."""
import unittest
import zipfile
from unittest import mock

from sandbox import Sandbox, api, make_scs

from truckcfg import cleanup, core


class Install(unittest.TestCase):
    def test_downloads_lists_mods_and_bundles_but_not_other_files(self):
        with Sandbox() as sb:
            dl = sb.root / "Downloads"
            make_scs(dl / "ats_cool_trailer.scs")
            with zipfile.ZipFile(dl / "big_pack.zip", "w") as z:  # a download zip that only wraps .scs mods
                z.writestr("big_pack/part1.scs", make_scs(sb.root / "p1.scs").read_bytes())
                z.writestr("big_pack/part2.scs", make_scs(sb.root / "p2.scs").read_bytes())
            (dl / "holiday_photos.zip").write_bytes(b"PK\x05\x06" + b"\0" * 18)  # empty zip, not a mod
            (dl / "notes.txt").write_text("x")
            items = {i["name"]: i for i in api().downloads("ets2")["items"]}
            self.assertEqual(sorted(items), ["ats_cool_trailer.scs", "big_pack.zip"])
            self.assertEqual(items["big_pack.zip"]["kind"], "bundle")
            self.assertEqual(items["big_pack.zip"]["inner"], ["part1.scs", "part2.scs"])
            self.assertTrue(items["ats_cool_trailer.scs"]["other_game"])  # name says ATS, we're in ETS2

    def test_install_mod_and_unwrap_bundle(self):
        with Sandbox() as sb:
            dl = sb.root / "Downloads"
            mod = make_scs(dl / "new_mod.scs")
            with zipfile.ZipFile(dl / "pack.zip", "w") as z:
                z.writestr("pack/a.scs", make_scs(sb.root / "a.scs").read_bytes())
            res = api().install("ets2", [str(mod), str(dl / "pack.zip")])
            self.assertTrue(all(r["ok"] for r in res), res)
            self.assertTrue((sb.game_docs("ets2") / "mod" / "new_mod.scs").is_file())
            self.assertTrue((sb.game_docs("ets2") / "mod" / "a.scs").is_file())  # unwrapped, not the zip
            self.assertFalse((sb.game_docs("ets2") / "mod" / "pack.zip").exists())
            self.assertTrue(mod.exists())  # the download itself is left alone
            self.assertIn("new_mod", api().mods("ets2")["mods"])

    def test_one_bad_file_does_not_stop_the_rest(self):
        with Sandbox() as sb:
            dl = sb.root / "Downloads"
            good = make_scs(dl / "good.scs")
            dup = make_scs(dl / "loud_horn.scs")  # already installed under that name
            junk = dl / "junk.zip"
            with zipfile.ZipFile(junk, "w") as z:
                z.writestr("readme.txt", "hello")
            res = {r["name"]: r for r in api().install("ets2", [str(junk), str(dup), str(good)])}
            self.assertFalse(res["junk.zip"]["ok"])
            self.assertIn("doesn't look like", res["junk.zip"]["error"])
            self.assertFalse(res["loud_horn.scs"]["ok"])
            self.assertIn("Already installed", res["loud_horn.scs"]["error"])
            self.assertTrue(res["good.scs"]["ok"])

    def test_refuses_while_running(self):
        with Sandbox() as sb:
            mod = make_scs(sb.root / "Downloads" / "x.scs")
            sb.running.add("ets2")
            res = api().install("ets2", [str(mod)])
            self.assertFalse(res[0]["ok"])
            self.assertFalse((sb.game_docs("ets2") / "mod" / "x.scs").exists())

    def test_inspect_dropped_files(self):
        with Sandbox() as sb:
            mod = make_scs(sb.root / "dropped.scs")
            rows = api().inspect_files("ets2", [str(mod), str(sb.root / "missing.scs")])
            self.assertEqual([r["kind"] for r in rows], ["mod", "unknown"])


class Remove(unittest.TestCase):
    def test_local_mod_goes_to_recycle_bin_and_leaves_load_order(self):
        with Sandbox() as sb:
            self.assertIn("rain_addon", sb.order("ets2"))
            msg = api().remove_mod("ets2", "rain_addon")
            self.assertIn("Recycle Bin", msg)
            self.assertTrue((sb.root / "RecycleBin" / "rain_addon.scs").is_file())
            self.assertNotIn("rain_addon", sb.order("ets2"))
            self.assertTrue(list((sb.store / "profile-backups" / "ets2").glob("*/profile.sii")))  # order backed up first

    def test_workshop_mod_is_unsubscribed_not_deleted(self):
        with Sandbox() as sb:
            pkg = next(p for p, m in api().mods("ats")["mods"].items() if m["source"] == "workshop")
            api().remove_mod("ats", pkg)
            self.assertEqual(sb.steam_calls, [("unsub", "ats", ["1234567"])])

    def test_refuses_while_running(self):
        with Sandbox() as sb:
            sb.running.add("ets2")
            with self.assertRaises(RuntimeError):
                api().remove_mod("ets2", "rain_addon")
            self.assertTrue((sb.game_docs("ets2") / "mod" / "rain_addon.scs").is_file())


class Workshop(unittest.TestCase):
    item = {"id": "3217770606", "title": "Weather Pack", "app": "270880", "size": 1000}

    def test_lookup_and_subscribe_checks_the_game(self):
        with Sandbox() as sb, mock.patch("truckcfg.mods.workshop_item", lambda wid: dict(self.item, id=wid)):
            a = api()
            info = a.workshop_lookup("ats", "https://steamcommunity.com/sharedfiles/filedetails/?id=3217770606")
            self.assertEqual((info["for"], info["matches"], info["subscribed"]), ("ats", True, False))
            self.assertIn("Subscribed", a.workshop_subscribe("ats", "3217770606"))
            self.assertEqual(sb.steam_calls, [("sub", "ats", ["3217770606"])])
            with self.assertRaises(RuntimeError):  # an ATS item can't be subscribed to from ETS2
                a.workshop_subscribe("ets2", "3217770606")
            with self.assertRaises(ValueError):
                a.workshop_lookup("ats", "not a link")
            self.assertTrue(a.workshop_lookup("ats", "1234567")["subscribed"])


class Cleanup(unittest.TestCase):
    def test_finds_quarantines_and_never_deletes(self):
        with Sandbox() as sb:
            prof = sb.profile_dir("ets2")
            (prof / "controls - Copy.sii").write_text("old")
            (prof / "controls (# Name clash 2026-09-29 abc #).sii").write_text("older")
            (sb.game_docs("ets2") / "mod" / "x - Copy.scs").write_text("mods are skipped")
            a = api()
            items = [i["rel"] for i in a.cleanup("ets2")["items"]]
            self.assertEqual(len(items), 2)
            self.assertIn("clutter", [c["id"] for c in a.inspect()["ets2"]["checks"]])
            a.quarantine("ets2", items[:1])
            self.assertEqual(len(a.cleanup("ets2")["items"]), 1)
            moved = list((sb.store / "quarantine").rglob("*.sii"))
            self.assertEqual(len(moved), 1)
            self.assertTrue(list((sb.store / "quarantine").rglob("manifest.json")))
            a.quarantine("ets2")  # the rest
            self.assertEqual(a.cleanup("ets2")["items"], [])
            self.assertNotIn("clutter", [c["id"] for c in a.inspect()["ets2"]["checks"]])

    def test_refuses_while_running(self):
        with Sandbox() as sb:
            (sb.profile_dir("ets2") / "controls - Copy.sii").write_text("old")
            sb.running.add("ets2")
            with self.assertRaises(RuntimeError):
                api().quarantine("ets2")
            self.assertTrue((sb.profile_dir("ets2") / "controls - Copy.sii").exists())

    def test_profile_health_follows_steam_cloud_profile(self):
        with Sandbox() as sb:
            health = api().cleanup("ets2")["health"]
            self.assertNotIn("bad", [h["level"] for h in health])  # profile.sii lives in Steam userdata, that's fine
            sb.profile_sii("ets2").unlink()
            prof = core.find_profiles(core.GAMES["ets2"])[0]
            self.assertEqual(cleanup.profile_health(prof)[0][0], "bad")
            self.assertIn("profile-health", [c["id"] for c in api().inspect()["ets2"]["checks"]])


if __name__ == "__main__":
    unittest.main()
