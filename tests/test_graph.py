import json
import pathlib
import unittest

from vardiya import cozumle, gecmis, graph
from vardiya.gateway import FakeModel

SITE = json.loads((pathlib.Path(__file__).resolve().parent.parent / "ornekler" / "ortam-banka.json").read_text(encoding="utf-8"))


class Signatures(unittest.TestCase):
    def test_same_cause_same_signature(self):
        a = graph.signature("ORA-00054: resource busy (table DEFTER) at 02:31:07")
        b = graph.signature("ORA-00054: resource busy (table DEFTER) at 03:02:44")
        self.assertEqual(a, b)
        self.assertNotEqual(a, graph.signature("No space left on device (rpr01:/data)"))
        self.assertEqual(graph.signature("/opt/a/b_v2.sh: not found"), graph.signature("/opt/x/y.sh: not found"))
        self.assertGreater(graph.similarity(a, graph.signature("ORA-00054: resource busy (table KUR) at 01:12:00")), 0.6)


class History(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g, cls.truth = gecmis.build(SITE)

    def _first_run(self, t):
        return next(f["id"] for f in cozumle.failures(self.g, t["day"]) if f["job"] in t["jobs"])

    def test_history_is_deterministic(self):
        g2, t2 = gecmis.build(SITE)
        self.assertEqual(self.truth, t2)
        self.assertEqual(self.g.stats(), g2.stats())

    def test_code_finds_the_root_cause_it_was_built_with(self):
        # Honest limit: the history and the catalog are written by the same hand, so this checks that the
        # reasoning is wired right, not that it finds causes in the wild.
        for t in self.truth:
            ev = cozumle.analyse(self.g, self._first_run(t))
            want = t["root"] or ("dis:kaynak-sistem" if t["kind"] == "dosya" else f"job:{self.g.get(self._first_run(t))['job']}")
            self.assertEqual(ev["candidates"][0]["id"], want, (t["key"], ev["candidates"][:2]))

    def test_a_fix_that_did_not_hold_is_called_out(self):
        lock = [t for t in self.truth if t["kind"] == "kilit" and t["open"]][0]
        ev = cozumle.analyse(self.g, self._first_run(lock))
        self.assertIn("kok nedeni gidermiyor", ev["lesson"])
        self.assertIn("kilit kaynagina", cozumle.suggest(self.g, ev)["action"])  # not "rerun" again

    def test_a_verified_past_fix_is_offered_first(self):
        rotation = [t for t in self.truth if t["kind"] == "parola" and t["open"]][0]
        ev = cozumle.analyse(self.g, self._first_run(rotation))
        self.assertEqual(ev["candidates"][0]["id"], "user:batchusr")
        s = cozumle.suggest(self.g, ev)
        self.assertTrue(s["verified"])
        self.assertIn("ctmpwd", s["action"])

    def test_warnings_come_from_the_past(self):
        kinds = {(w["kind"], w["job"].split(",")[0]) for w in cozumle.warnings(self.g, SITE["today"])}
        self.assertIn(("tekrar", "MHS_WATCH_KUR"), kinds)       # the file is late on Fridays
        self.assertIn(("yavaslama", "MHS_MUTABAKAT"), kinds)    # five weeks of slowing down
        self.assertTrue(any(k == "kalici" for k, _ in kinds))    # rerun is not a fix

    def test_the_model_only_picks_from_code_candidates(self):
        rotation = [t for t in self.truth if t["kind"] == "parola" and t["open"]][0]
        ev = cozumle.analyse(self.g, self._first_run(rotation))
        good = cozumle.explain(FakeModel(actions=[{"candidate": "user:batchusr", "explanation": "x", "next_step": "y"}]), ev)
        self.assertEqual(good["candidate"], "user:batchusr")
        made_up = cozumle.explain(FakeModel(actions=[{"candidate": "host:yok99", "explanation": "x"}]), ev)
        self.assertTrue(made_up["rejected"])
        self.assertIsNone(cozumle.explain(None, ev))

    def test_the_picture_is_small(self):
        ev = cozumle.analyse(self.g, self._first_run(self.truth[-1]))
        pic = self.g.neighbourhood([ev["run"], f"job:{ev['job']}"], depth=1, limit=40)
        self.assertLessEqual(len(pic["nodes"]), 60)
        self.assertTrue(all(e[0] in {n["id"] for n in pic["nodes"]} for e in pic["edges"]))


class IncidentBench(unittest.TestCase):
    def test_code_arm_holds_on_renamed_sites_and_other_wordings(self):
        from vardiya import olaybench
        for split in ("dev", "test"):
            g, cases = olaybench.cases(split)
            self.assertGreaterEqual(len(cases), 15)
            for c in cases:
                root, action = olaybench.solve(g, c, "kod")
                self.assertEqual(olaybench.verdict(c, root, action), "dogru", (split, c["id"], root, action))

    def test_harmful_actions_are_scored_as_such(self):
        from vardiya import olaybench
        g, cases = olaybench.cases("dev")
        silent = next(c for c in cases if c["kind"] == "sessiz")
        self.assertEqual(olaybench.verdict(silent, silent["root"], olaybench.RERUN), "zararli")
        self.assertEqual(olaybench.verdict(silent, silent["root"], olaybench.SETOK), "zararli")
        self.assertEqual(olaybench.verdict(silent, "host:x", silent["actions"][0]), "yarim")

    def test_the_raw_arm_gets_the_same_facts(self):
        from vardiya import olaybench
        g, cases = olaybench.cases("test")
        c = next(x for x in cases if x["kind"] == "setok")
        text = olaybench.raw_prompt(g, c)
        self.assertIn("Set OK", text)          # what the harness sees, the raw model sees too
        self.assertIn("Past incidents", text)
        self.assertNotIn("ODM_", text)          # renamed through and through


class ClassSkills(unittest.TestCase):
    def test_classes_are_data_and_bad_ones_are_refused(self):
        import tempfile
        from vardiya.skills import load_incident_classes
        root = pathlib.Path(__file__).resolve().parent.parent / "skills"
        classes = load_incident_classes(root)
        self.assertGreaterEqual(len(classes), 15)
        self.assertIn("rerun", classes["kilit"]["harmful"])
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "x").mkdir()
            (pathlib.Path(d) / "x" / "SKILL.md").write_text('---\nname: x\nkind: incident_classes\nclasses:\n  iyi:\n    signs: [quota exceeded]\n    cause: kota doldu\n    fix: kotayi artir\n    evidence: [precedent]\n  kotu:\n    signs: [x]\n    fix: y\n    evidence: [model_ne_derse]\n  bos:\n    signs: [z]\n    evidence: [precedent]\n---\n', encoding="utf-8")
            got = load_incident_classes(d)
        self.assertEqual(set(got), {"iyi"})   # unknown evidence query, or no fix: not loaded at all


class Health(unittest.TestCase):
    def test_the_scan_finds_what_came_in_before_the_checks(self):
        from vardiya import saglik
        from vardiya.repo import Repo
        found = {(f["job"], f["code"]) for f in saglik.scan(Repo({**SITE, "request": {"talep_no": "_", "text": ""}}))}
        self.assertIn(("RPR_HAFTALIK", "E_CAL_DEP"), found)
        self.assertIn(("KRD_RISK_HESAP", "E_SECRET"), found)
        self.assertIn(("ODM_WATCH_DOSYA", "E_REQUIRED"), found)
        self.assertIn(("KRD_RAPOR", "W_SAME_COMMAND"), found)
        self.assertFalse(any("Etl2024" in f["msg"] for f in saglik.scan(Repo({**SITE, "request": {"talep_no": "_", "text": ""}}))))


if __name__ == "__main__":
    unittest.main()
