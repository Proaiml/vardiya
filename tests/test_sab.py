import json
import pathlib
import tempfile
import unittest

from vardiya import bench_req, sab, sabgen

SCENARIOS = sabgen.generate(per_family=6, seed=11)


def verdicts(arm):
    return {sc["id"]: bench_req.run_one(sc, arm)["verdict"] for sc in SCENARIOS}


class GeneratedScenarios(unittest.TestCase):
    """The validity gate every generated scenario must pass before it may count."""

    def test_generation_is_deterministic(self):
        again = sabgen.generate(per_family=6, seed=11)
        self.assertEqual(json.dumps(SCENARIOS, sort_keys=True), json.dumps(again, sort_keys=True))
        other = sabgen.generate(per_family=6, seed=12)
        self.assertNotEqual(json.dumps(SCENARIOS, sort_keys=True), json.dumps(other, sort_keys=True))

    def test_golden_solves_all_and_noop_solves_none(self):
        self.assertEqual(set(verdicts(bench_req.arm_golden).values()), {"correct"})
        self.assertEqual(set(verdicts(bench_req.arm_noop).values()), {"safe_fail"})

    def test_no_shortcut_passes_every_family(self):
        apply, refuse = verdicts(bench_req.arm_naive_apply), verdicts(bench_req.arm_naive_return)
        for sc in SCENARIOS:
            fam, sid = sc["family"], sc["id"]
            if fam in ("yeni", "degisiklik", "kaldir", "aciklamali", "yeni-tip"):
                self.assertEqual((apply[sid], refuse[sid]), ("correct", "safe_fail"), sid)
            elif fam == "takvim":
                self.assertEqual((apply[sid], refuse[sid]), ("false_green", "safe_fail"), sid)
            else:
                self.assertIn(apply[sid], bench_req.HARMFUL, sid)
                self.assertEqual(refuse[sid], "correct", sid)

    def test_what_code_can_and_cannot_do_without_a_reader(self):
        for sc in SCENARIOS:
            v = bench_req.run_one(sc, bench_req.arm_harness)["verdict"]
            if sc["family"] == "t-celiski":
                # Only a reader can see that the description disagrees with the fields. With no model
                # attached the request is applied: this family is where the model carries the safety.
                self.assertEqual(v, "false_green", sc["id"])
                continue
            self.assertIn(v, ("correct", "safe_fail") if sc["family"] == "takvim" else ("correct",), sc["id"])
            old = bench_req.run_one(sc, bench_req.arm_harness, strategy="agree2")["verdict"]
            self.assertEqual(old, "safe_fail" if sc["family"] == "takvim" else "correct", sc["id"])

    def test_description_conflict_code_brings_evidence_and_the_model_judges(self):
        from vardiya import gunler
        from vardiya.gateway import FakeModel
        traps = {s["title"].split()[2]: s for s in sabgen.generate(16, 21, ("t-celiski",))}  # one per kind
        self.assertEqual(set(traps), {"calendar", "time", "host", "deps"})
        fine = next(s for s in SCENARIOS if s["family"] == "aciklamali")
        text = lambda sc: next(x.split(": ", 1)[1] for x in sc["request"]["text"].splitlines() if x.startswith("aciklama:"))
        run = lambda sc, answer: bench_req.run_one(sc, bench_req.arm_harness, model=FakeModel(actions=[answer]))["verdict"]
        names = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

        def faithful(sc):
            """What a reader who reads the description correctly reports. It never sees the form."""
            import re
            t, out = text(sc), {"start_time": "", "server": "", "starts_after": [], "run_days": {"type": "not_stated"}}
            clock = re.search(r"\d\d:\d\d", t)
            out["start_time"] = clock.group(0) if clock else ""
            out["server"] = next((h for h in sc["env"]["hosts"] if h in t), "")
            out["starts_after"] = [j["name"] for j in sc["jobs"] if j["name"] in t]
            for part in t.split("; "):
                rule = gunler.parse(part)
                if rule:
                    rule = {**rule, "days": [names[d] for d in rule["days"]]} if "days" in rule else rule
                    out.update(run_days=rule, run_days_quote=part)
            return out

        blind = {"start_time": "", "server": "", "starts_after": [], "run_days": {"type": "not_stated"}}
        for kind, sc in traps.items():
            self.assertEqual(run(sc, faithful(sc)), "correct", kind)       # read correctly: code sees the difference
            self.assertEqual(run(sc, blind), "false_green", kind)           # not read: nothing to compare
        # a consistent description is left alone, however it is read
        self.assertEqual(run(fine, faithful(fine)), "correct")
        self.assertEqual(run(fine, blind), "correct")
        # what the model reports must be in the description: invented items cannot block a good request
        invented = {"start_time": "23:59", "server": "yok01", "starts_after": ["OLMAYAN_IS"],
                    "run_days": {"type": "weekly", "days": ["sun"]}, "run_days_quote": "uydurma alinti"}
        self.assertEqual(run(fine, invented), "correct")
        # the earlier one-question version is kept for comparison
        old = lambda sc, answer: bench_req.run_one(sc, bench_req.arm_harness, strategy="lex>rule-gloss-veto-desc1",
                                                   model=FakeModel(actions=[answer]))["verdict"]
        self.assertEqual(old(traps["time"], {"contradiction": True, "field": "saat", "quote": text(traps["time"]).split("; ")[1]}),
                         "correct")
        self.assertEqual(old(traps["time"], {"contradiction": True, "field": "saat", "quote": "yok boyle bir soz"}), "false_green")

    def test_expected_outcome_matches_family(self):
        for sc in SCENARIOS:
            want = "returned" if sc["family"] not in sabgen.APPLIED else "removed" if sc["family"] == "kaldir" else "applied"
            self.assertEqual(sc["expected"]["outcome"], want, sc["id"])

    def test_no_site_and_no_right_answer_has_a_job_outrunning_its_predecessor(self):
        # Bench 0.1 missed this: a model working without the harness returned a request the bench called
        # valid, because the new job would run on days its predecessor does not. It was right.
        for split in ("dev", "test"):
            for sc in sabgen.generate(per_family=6, seed=11, split=split):
                site, exp = {k: sc[k] for k in ("today", "env", "jobs")}, sc["expected"]
                self.assertTrue(sabgen.consistent(site), sc["id"])
                if exp["outcome"] == "applied":
                    self.assertTrue(sabgen.consistent(site, exp["definition"]), sc["id"])

    def test_calendar_mismatch_trap_is_wrong_only_as_a_pair(self):
        from vardiya import checks, intake
        from vardiya.repo import Repo
        traps = [s for s in sabgen.generate(12, 11, ("t-uyumsuz",))]
        self.assertEqual({s["title"].split()[1] for s in traps}, {"yeni", "takvim"})  # both shapes occur
        for sc in traps:
            repo = Repo(sc)
            env, jobs = repo.list_env(), dict(repo.jobs)
            values, errors = intake.parse(sc["request"]["text"])
            self.assertEqual(errors, [], sc["id"])
            asked = intake.to_definition(values)
            new = values["islem"] == "yeni"
            d = asked if new else {**jobs[asked["name"]], **asked}
            errors = lambda *more: {f["code"] for f in checks.check(env, jobs, d, new, *more) if f["severity"] == "error"}
            self.assertEqual(errors(), set(), sc["id"])  # every field is fine on its own
            codes = errors((), {c: set(repo.forecast(c, 180)) for c in env["calendars"]})
            self.assertEqual(codes, {"E_CAL_DEP"} if new else {"E_CAL_DEPENDENT"}, sc["id"])

    def test_typed_job_traps_are_caught_for_their_own_reason(self):
        from vardiya.adapter import RepoAdapter
        from vardiya.desk import Desk
        from vardiya.repo import Repo
        why = {"sure_yok": "sure_siniri", "sure_gecersiz": "sure_siniri", "parola": "gizli bilgi",
               "profil_yok": "tanimli degil", "profil_turu": "kullanilamaz", "baglanti_yok": "baglanti",
               "hedef_yok": "hedef", "ayni_yol": "kaynak yolla ayni", "bos_komut": "komut calistirmaz",
               "baglanti_fazla": "kullanilmaz"}
        seen = set()
        for sc in sabgen.generate(40, 4, ("t-tip",)):
            trap = sc["title"].rsplit(" ", 1)[1]
            seen.add(sc["title"])
            rep = Desk(RepoAdapter(Repo(sc))).handle()
            self.assertEqual(rep["outcome"], "returned", sc["id"])
            self.assertTrue(any(why[trap] in r for r in rep["reasons"]), (sc["id"], rep["reasons"]))
            self.assertFalse(any("Gizli2026" in r for r in rep["reasons"]), sc["id"])  # never echoed back
        self.assertGreaterEqual(len(seen), 15)  # every type, most of its traps
        # the earlier families are untouched by the new types: their request texts carry no new key
        for sc in sabgen.generate(2, 1, sabgen.FAMILIES[:-2]):
            self.assertNotIn("baglanti:", sc["request"]["text"], sc["id"])
            self.assertNotIn("connections", sc["env"], sc["id"])

    def test_second_look_can_only_turn_an_apply_into_a_return(self):
        # Experimental "review" step: after the coded checks, the model is asked an open question. To see
        # what it adds, the calendar-fit check is switched off and the mismatch trap is used as the unknown.
        from vardiya.gateway import FakeModel
        blind = {"start_time": "", "server": "", "starts_after": [], "run_days": {"type": "not_stated"}}
        trap = next(s for s in sabgen.generate(12, 11, ("t-uyumsuz",)) if s["title"].split()[1] == "yeni")
        fine = next(s for s in SCENARIOS if s["family"] == "yeni")
        dep = next(x for x in trap["request"]["text"].splitlines() if x.startswith("bagimlilik:")).split("[")[1].strip("]").split(", ")[0]
        run = lambda sc, answer, strategy="lex>rule-gloss-veto-review-nocaldep": bench_req.run_one(
            sc, bench_req.arm_harness, strategy=strategy, model=FakeModel(actions=[blind, answer]))["verdict"]
        seen = {"problem": "the job runs at weekends but the job it waits for does not", "field": "gunler", "other_job": dep}
        self.assertEqual(run(trap, seen), "correct")
        self.assertEqual(run(trap, {"problem": "none", "field": "none", "other_job": ""}), "false_green")
        self.assertEqual(run(trap, {**seen, "other_job": "BASKA_BIR_IS"}), "false_green")  # not a neighbour: dropped
        self.assertEqual(run(trap, {**seen, "field": "renk"}), "false_green")              # not a field: dropped
        self.assertEqual(run(trap, "evet sorun var"), "false_green")
        # on a good request a false alarm costs a return, never a wrong job; silence costs nothing
        self.assertEqual(run(fine, {"problem": "none", "field": "none"}), "correct")
        self.assertEqual(run(fine, {"problem": "this job might possibly be slow", "field": "saat", "other_job": ""}), "safe_fail")
        # off by default: the default strategy never asks the open question
        quiet = FakeModel(actions=[blind, seen])
        self.assertEqual(bench_req.run_one(fine, bench_req.arm_harness, model=quiet)["verdict"], "correct")
        self.assertEqual(quiet.calls, 1)

    def test_removing_a_job_others_wait_for_is_destructive(self):
        for sc in (s for s in SCENARIOS if s["family"] == "t-bagimli"):
            self.assertEqual(bench_req.run_one(sc, bench_req.arm_naive_apply)["verdict"], "destructive", sc["id"])

    def test_every_phrase_has_one_calendar(self):
        self.assertEqual(set(sabgen.PHRASES), set(sabgen.CALENDARS))
        flat = [p for ps in sabgen.PHRASES.values() for p in ps]
        self.assertEqual(len(flat), len(set(flat)))
        self.assertFalse(set(flat) & set(sabgen.NO_CALENDAR))


class Runner(unittest.TestCase):
    def test_run_is_resumable_and_report_reads_it(self):
        few = SCENARIOS[:12]
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d) / "r.jsonl"
            done, left = sab.run(few, out, arms=["noop", "golden", "harness"])
            self.assertEqual((done, left), (36, 0))
            self.assertEqual(sab.run(few, out, arms=["noop", "golden", "harness"]), (0, 0))
            done, left = sab.run(SCENARIOS[:14], out, arms=["golden"])
            self.assertEqual((done, left), (2, 0))
            rows = sab.load(out)
            self.assertEqual(len(rows), 38)
            self.assertTrue(all(r["replay_ok"] for r in rows))
            text = sab.report(rows)
            self.assertIn("Referans cozum", text)
            self.assertIn("38/38 iz", text)

    def test_statistics(self):
        lo, hi = sab.wilson(8, 10)
        self.assertTrue(0.44 < lo < 0.50 and 0.94 < hi < 0.98)
        self.assertEqual(sab.wilson(0, 0), (0.0, 0.0))
        self.assertEqual(sab.mcnemar_exact(0, 0), 1.0)
        self.assertAlmostEqual(sab.mcnemar_exact(10, 0), 2 / 2 ** 10)
        self.assertEqual(sab.mcnemar_exact(3, 3), 1.0)

    def test_balanced_accuracy_does_not_reward_refusing_everything(self):
        rows = [{"family": sc["family"], "verdict": bench_req.run_one(sc, bench_req.arm_naive_return)["verdict"]}
                for sc in SCENARIOS]
        self.assertEqual(sab.balanced(rows), "50%")


if __name__ == "__main__":
    unittest.main()
