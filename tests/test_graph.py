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


if __name__ == "__main__":
    unittest.main()
