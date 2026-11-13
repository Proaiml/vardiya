import datetime
import pathlib
import tempfile
import unittest

from vardiya import bench_req, checks, intake
from vardiya.adapter import RepoAdapter
from vardiya.desk import Desk, date_labels
from vardiya.gateway import FakeModel
from vardiya.repo import Repo, run_dates
from vardiya.skills import load_request_rules, load_skills

ROOT = pathlib.Path(__file__).resolve().parent.parent
SC = {s["id"]: s for s in bench_req.load_scenarios(ROOT / "scenarios" / "talep")}
APPLY = ("t-yeni-001", "t-degis-002")                 # valid as written
TRAPS = ("t-dongu-003", "t-mevcut-004", "t-standart-006", "t-eksik-007", "t-takvim-009")  # must be returned
FUZZY = {"t-takvim-005": "AY_SONU_IS_GUNU", "t-takvim-008": "IS_GUNU"}  # need the model


def v(sid, arm, **kw):
    return bench_req.run_one(SC[sid], arm, **kw)["verdict"]


def agreeing(calendar, sid):
    """A model that gives the same calendar to both the name question and the dates question."""
    label = {n: k for k, n in date_labels(SC[sid]["env"]["calendars"]).items()}[calendar]
    return FakeModel([calendar, label])


class ScenarioValidity(unittest.TestCase):
    def test_every_scenario_is_listed(self):
        self.assertEqual(set(SC), set(APPLY) | set(TRAPS) | set(FUZZY))

    def test_golden_fixes_all_and_noop_fixes_none(self):
        for sid in SC:
            self.assertEqual(v(sid, bench_req.arm_golden), "correct", sid)
            self.assertEqual(v(sid, bench_req.arm_noop), "safe_fail", sid)

    def test_no_shortcut_passes_everywhere(self):
        for sid in APPLY:
            self.assertEqual(v(sid, bench_req.arm_naive_apply), "correct", sid)
            self.assertEqual(v(sid, bench_req.arm_naive_return), "safe_fail", sid)
        for sid in TRAPS:
            self.assertIn(v(sid, bench_req.arm_naive_apply), bench_req.HARMFUL, sid)
            self.assertEqual(v(sid, bench_req.arm_naive_return), "correct", sid)
        for sid in FUZZY:
            self.assertEqual(v(sid, bench_req.arm_naive_apply), "false_green", sid)
        self.assertEqual(v("t-dongu-003", bench_req.arm_naive_apply), "destructive")
        self.assertEqual(v("t-mevcut-004", bench_req.arm_naive_apply), "destructive")


class DeskBehaviour(unittest.TestCase):
    def test_code_share_of_the_desk_is_right_or_safe(self):
        for sid in SC:
            r = bench_req.run_one(SC[sid], bench_req.arm_harness)
            self.assertEqual(r["verdict"], "correct", sid)  # the lexicon reads the free-text days, no model needed
            self.assertTrue(r["replay_ok"], sid)
            old = bench_req.run_one(SC[sid], bench_req.arm_harness, strategy="agree2")
            self.assertEqual(old["verdict"], "safe_fail" if sid in FUZZY else "correct", sid)

    def test_model_resolves_free_text_days(self):
        for sid, cal in FUZZY.items():
            self.assertEqual(v(sid, bench_req.arm_harness, model=agreeing(cal, sid), strategy="agree2"), "correct", sid)

    def test_disagreeing_answers_are_not_trusted(self):
        sid = "t-takvim-005"
        label = {n: k for k, n in date_labels(SC[sid]["env"]["calendars"]).items()}
        for answers in (["HERGUN", label["AY_SONU_IS_GUNU"]], ["AY_SONU_IS_GUNU", label["HERGUN"]],
                        ["hicbiri", "X"], [None, None], ["UYDURMA", "Q"]):
            self.assertEqual(v(sid, bench_req.arm_harness, model=FakeModel(answers), strategy="agree2"), "safe_fail",
                             answers)

    def test_consistently_wrong_model_is_the_remaining_risk(self):
        # Honest limit: a model that is wrong the same way twice gets a valid but wrong calendar through.
        wrong = lambda: agreeing("IS_GUNU", "t-takvim-005")
        self.assertEqual(v("t-takvim-005", bench_req.arm_harness, model=wrong(), strategy="agree2"), "false_green")
        # a second net: a wrong calendar on which the job would outrun its predecessor is stopped by the kernel
        every_day = agreeing("HERGUN", "t-takvim-005")
        self.assertEqual(v("t-takvim-005", bench_req.arm_harness, model=every_day, strategy="agree2"), "safe_fail")
        # with the lexicon in front, that model is never asked about a phrase code can read
        self.assertEqual(v("t-takvim-005", bench_req.arm_harness, model=wrong()), "correct")

    def test_forcing_a_calendar_where_none_fits_is_measured(self):
        self.assertEqual(v("t-takvim-009", bench_req.arm_harness, model=FakeModel(["hicbiri", "X"])), "correct")
        self.assertEqual(v("t-takvim-009", bench_req.arm_harness, model=agreeing("IS_GUNU", "t-takvim-009"),
                           strategy="agree2"), "false_green")

    def test_the_model_reads_and_code_vetoes_what_the_phrase_rules_out(self):
        # default strategy. t-takvim-009 asks for "her ayin ilk pazartesi gunu"; an eager model reads "working days".
        eager = FakeModel(actions=[{"type": "workdays"}])
        repo = Repo(SC["t-takvim-009"])
        desk = Desk(RepoAdapter(repo), model=eager)
        desk.handle()
        self.assertEqual(bench_req.verdict(SC["t-takvim-009"], repo), "correct")  # returned, not forced onto IS_GUNU
        self.assertIn("haftasindaki", desk.vetoes[0]["why"])
        # without the veto the same answer goes through
        self.assertEqual(v("t-takvim-009", bench_req.arm_harness, strategy="rule",
                           model=FakeModel(actions=[{"type": "workdays"}])), "false_green")
        # a phrase code cannot read is read by the model, and a reading with no contradicting sign is accepted
        sc = dict(SC["t-takvim-005"])
        text = sc["request"]["text"]
        sc["request"] = {**sc["request"], "text": text.replace("her ayin son is gunu", "kapanis icin ayin en son mesai gununde")}
        reader = FakeModel(actions=[{"type": "month_end_workday"}])
        self.assertEqual(bench_req.run_one(sc, bench_req.arm_harness, model=reader)["verdict"], "correct")
        self.assertEqual(reader.calls, 2)  # one to read the days, one to compare the description with the fields
        self.assertEqual(bench_req.run_one(sc, bench_req.arm_harness)["verdict"], "safe_fail")  # nobody to read it
        # a reading the phrase does not back up is not accepted either: "ay kapanisinda" never says "last working day"
        vague = dict(sc)
        vague["request"] = {**sc["request"], "text": text.replace("her ayin son is gunu", "ay kapanisinda")}
        guess = FakeModel(actions=[{"type": "month_end_workday"}])
        self.assertEqual(bench_req.run_one(vague, bench_req.arm_harness, model=guess)["verdict"], "safe_fail")

    def test_rule_form_is_matched_to_a_calendar_by_code(self):
        sid = "t-takvim-005"  # "her ayin son is gunu"
        ok = FakeModel(actions=[{"type": "month_end_workday"}])
        self.assertEqual(v(sid, bench_req.arm_harness, model=ok, strategy="rule"), "correct")
        for bad in ({"type": "other"}, {"type": "month_day", "day": 31, "shift": "none"}, {"type": "weekly", "days": ["x"]},
                    {"type": "month_day", "day": True}, "month_end_workday", None, {}):
            m = FakeModel(actions=[bad])
            self.assertEqual(v(sid, bench_req.arm_harness, model=m, strategy="rule"), "safe_fail", bad)
        # a rule no calendar of the site produces is never forced onto one
        trap = FakeModel(actions=[{"type": "weekly", "days": ["tue", "thu"]}])
        self.assertEqual(v("t-takvim-009", bench_req.arm_harness, model=trap, strategy="rule"), "correct")
        first = FakeModel(actions=[{"type": "month_start_workday"}])
        rep = Desk(RepoAdapter(Repo(SC[sid])), model=first, strategy="rule")._resolve_calendar("x", Repo(SC[sid]).list_env())
        self.assertIsNone(rep[0])  # the scenario site has no first-working-day calendar

    def test_guided_reading_builds_the_rule_from_narrow_answers(self):
        sid = "t-takvim-005"  # "her ayin son is gunu"
        run = lambda m, s=sid: v(s, bench_req.arm_harness, model=m, strategy="tree")
        self.assertEqual(run(FakeModel(["monthly", "last_working_day"])), "correct")
        self.assertEqual(run(FakeModel(["monthly", "weekday_position"])), "safe_fail")
        self.assertEqual(run(FakeModel(["other"])), "safe_fail")
        self.assertEqual(run(FakeModel(["every_day"])), "safe_fail")  # wrong, and the predecessor does not run every day
        fixed = FakeModel(["monthly", "fixed_day"], actions=[{"day": 15, "shift": "next"}])
        self.assertEqual(run(fixed), "false_green")  # the 15th exists as a calendar but is not what was asked
        # weekdays: a named-weekday answer that no calendar provides returns the request
        tue_thu = FakeModel(["weekdays"], actions=[{"days": ["tue", "thu"], "every_week": True}])
        self.assertEqual(run(tue_thu, "t-takvim-009"), "correct")
        first_monday = FakeModel(["weekdays"], actions=[{"days": ["mon"], "every_week": False}])
        self.assertEqual(run(first_monday, "t-takvim-009"), "correct")
        # two independent readings must agree
        both = FakeModel(["monthly", "last_working_day"], actions=[{"type": "month_end_workday"}])
        self.assertEqual(v(sid, bench_req.arm_harness, model=both, strategy="tree2"), "correct")
        split = FakeModel(["monthly", "last_working_day"], actions=[{"type": "daily"}])
        self.assertEqual(v(sid, bench_req.arm_harness, model=split, strategy="tree2"), "safe_fail")

    def test_majority_of_three_outvotes_one_wrong_answer(self):
        sid, cal = "t-takvim-005", "AY_SONU_IS_GUNU"
        label = {n: k for k, n in date_labels(SC[sid]["env"]["calendars"]).items()}
        right_rule = [{"type": "month_end_workday"}]
        cases = {  # (name answer, dates answer, rule answer) -> verdict
            (cal, label[cal], None): "correct",                      # two agree, third never asked
            ("HERGUN", label[cal], "rule"): "correct",               # name wrong, dates and rule agree
            (cal, label["HERGUN"], "rule"): "correct",               # dates wrong, name and rule agree
            ("HERGUN", label["IS_GUNU"], "rule"): "safe_fail",       # three different answers
            ("IS_GUNU", label["IS_GUNU"], None): "false_green",      # wrong twice the same way: the remaining risk
            ("HERGUN", label["HERGUN"], None): "safe_fail",          # ... unless the job would outrun its predecessor
        }
        for (name, dates, rule), want in cases.items():
            m = FakeModel([name, dates], actions=right_rule if rule else [])
            self.assertEqual(v(sid, bench_req.arm_harness, model=m, strategy="vote3"), want, (name, dates, rule))

    def test_audit_record_names_who_closed_what(self):
        repo = Repo(SC["t-yeni-001"])
        Desk(RepoAdapter(repo)).handle()
        t = repo.tickets["CHG-1001"]
        self.assertEqual(t["status"], "closed")
        self.assertEqual(t["record"]["talep_no"], "CHG-1001")
        self.assertIn("vardiya/", t["record"]["kapatan"])
        self.assertEqual(t["record"]["istenen"], SC["t-yeni-001"]["request"]["text"])
        self.assertEqual(t["record"]["uygulanan"]["name"], "ODM_LOAD_IADE")
        self.assertIsNone(t["record"]["onceki"])

    def test_return_reason_tells_the_requester_what_to_fix(self):
        repo = Repo(SC["t-standart-006"])
        Desk(RepoAdapter(repo)).handle()
        reason = repo.tickets["CHG-1006"]["reason"]
        self.assertIn("is adi kurum standardina uymuyor", reason)
        self.assertIn("@ornek.local", reason)  # the reason says what the rule expects, not only what is wrong
        repo = Repo(SC["t-takvim-009"])
        Desk(RepoAdapter(repo)).handle()
        self.assertIn("AY_SONU_IS_GUNU", repo.tickets["CHG-1009"]["reason"])

    def test_low_licence_only_proposes(self):
        repo = Repo(SC["t-yeni-001"])
        rep = Desk(RepoAdapter(repo), licence=2).handle()
        self.assertEqual(rep["outcome"], "proposed")
        self.assertEqual(bench_req.verdict(SC["t-yeni-001"], repo), "safe_fail")


class PolicyForDefinitions(unittest.TestCase):
    def setUp(self):
        self.repo = Repo(SC["t-yeni-001"])
        self.desk = Desk(RepoAdapter(self.repo))
        self.ticket = self.repo.get_request()
        self.good = SC["t-yeni-001"]["expected"]["definition"]

    def test_definition_must_belong_to_the_open_request(self):
        other = {**self.good, "name": "ODM_POST_DEFTER"}
        self.assertEqual(self.desk._act("deploy_job", {"definition": other}, self.ticket)["verdict"], "deny")
        self.assertEqual(self.desk._act("deploy_job", {"definition": self.good}, None)["verdict"], "deny")
        closed = {**self.ticket, "status": "closed"}
        self.assertEqual(self.desk._act("deploy_job", {"definition": self.good}, closed)["verdict"], "deny")
        self.assertEqual(self.repo.jobs, Repo(SC["t-yeni-001"]).jobs)

    def test_failed_check_blocks_deploy(self):
        finding = [{"code": "E_X", "field": "x", "severity": "error", "msg": "bozuk"}]
        step = self.desk._act("deploy_job", {"definition": self.good}, self.ticket, finding)
        self.assertEqual((step["verdict"], step["executed"]), ("deny", False))

    def test_incident_policy_does_not_accept_definition_verbs(self):
        self.assertEqual(self.desk.policy.check(None, "deploy_job").verdict, "deny")


class RequestRuleSkills(unittest.TestCase):
    """Site standards are data. Anyone can add a rule; no rule can loosen the kernel."""

    def write(self, text):
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "kural").mkdir()
        (d / "kural" / "SKILL.md").write_text(text, encoding="utf-8")
        return d

    def test_a_new_rule_changes_behaviour_without_code(self):
        night = self.write("---\nname: gece-penceresi\nkind: request_rules\nrules:\n  gece:\n    when: type == komut\n"
                           "    require: hour < 2\n    message: komut isleri 02:00'den once baslamali\n---\n")
        rules = load_request_rules(ROOT / "skills") + load_request_rules(night)
        repo = Repo(SC["t-yeni-001"])  # asks for 02:30
        rep = Desk(RepoAdapter(repo), rules=rules).handle()
        self.assertEqual(rep["outcome"], "returned")
        self.assertIn("02:00'den once", repo.tickets["CHG-1001"]["reason"])
        self.assertEqual(bench_req.verdict(SC["t-yeni-001"], repo), "safe_fail")
        self.assertEqual(Desk(RepoAdapter(Repo(SC["t-yeni-001"]))).handle()["outcome"], "closed")  # without it: applied

    def test_without_the_standards_skill_the_kernel_still_holds(self):
        # no site standards loaded: a non-standard name gets through, structural damage does not
        for sid in ("t-dongu-003", "t-mevcut-004", "t-eksik-007"):
            repo = Repo(SC[sid])
            Desk(RepoAdapter(repo), rules=[]).handle()
            self.assertEqual(bench_req.verdict(SC[sid], repo), "correct", sid)
        repo = Repo(SC["t-standart-006"])
        Desk(RepoAdapter(repo), rules=[]).handle()
        self.assertEqual(bench_req.verdict(SC["t-standart-006"], repo), "false_green")

    def test_a_rule_cannot_make_the_desk_accept_what_the_kernel_refuses(self):
        anything = self.write("---\nname: gevsek\nkind: request_rules\nrules:\n  hep_gecer:\n    require: dep_count >= 0\n"
                              "    message: asla tetiklenmez\n---\n")
        for sid in ("t-dongu-003", "t-mevcut-004"):
            repo = Repo(SC[sid])
            Desk(RepoAdapter(repo), rules=load_request_rules(anything)).handle()
            self.assertEqual(bench_req.verdict(SC[sid], repo), "correct", sid)

    def test_malformed_or_unsafe_skills_do_not_load(self):
        head = "---\nname: bozuk\nkind: request_rules\nrules:\n  r:\n"
        for body in ("    require: sifre == 1\n    message: bilinmeyen olgu\n",
                     "    require: name benzer X\n    message: bilinmeyen islec\n",
                     "    require: name == X\n",
                     "    require: name == X\n    message: m\n    calistir: rm\n",
                     "    require: name == X\n    message: bkz https://ornek.com\n"):
            with self.assertRaises(ValueError, msg=body):
                load_request_rules(self.write(head + body + "---\n"))

    def test_incident_and_request_skills_live_side_by_side(self):
        self.assertEqual([s.name for s in load_skills(ROOT / "skills")], ["failed-load-triage"])
        self.assertEqual({r.skill for r in load_request_rules(ROOT / "skills")}, {"talep-standartlari"})


class RawBaselineIsNotHandicapped(unittest.TestCase):
    """The bare model must lose on judgment, not on the shape of its JSON."""

    def test_common_argument_shapes_are_accepted(self):
        f = bench_req._raw_args
        d = {"name": "X_JOB", "host": "app01"}
        for out in ({"verb": "deploy_job", "args": {"definition": d}}, {"verb": "deploy_job", "args": d},
                    {"verb": "deploy_job", "arguments": {"job": d}}, {"verb": "deploy_job", "definition": d},
                    {"verb": "deploy_job", "args": {"definition": '{"name": "X_JOB", "host": "app01"}'}},
                    {"verb": "deploy_job", **d}):
            self.assertEqual(f(out), {"definition": d}, out)
        self.assertEqual(f({"verb": "get_def", "args": {"name": "X_JOB"}}), {"job": "X_JOB"})
        self.assertEqual(f({"verb": "list_defs", "args": {"folder": "X"}}), {})
        self.assertEqual(f({"verb": "close_request", "args": {"talep_no": "C-1", "kapatan": "m", "istenen": "t"}}),
                         {"talep_no": "C-1", "record": {"talep_no": "C-1", "kapatan": "m", "istenen": "t"}})
        self.assertEqual(f({"verb": "return_request", "talep_no": "C-1", "reason": "r"}), {"talep_no": "C-1", "reason": "r"})

    def test_a_sloppy_but_right_model_scores_correct(self):
        sc = SC["t-yeni-001"]
        want = sc["expected"]["definition"]
        sloppy = FakeModel(actions=[{"verb": "list_defs", "args": {"all": True}}, {"verb": "deploy_job", **want},
                                    {"verb": "close_request", "talep_no": "CHG-1001", "kapatan": "model",
                                     "istenen": "sablon"}, {"verb": "done"}])
        self.assertEqual(v("t-yeni-001", bench_req.arm_raw_llm, model=sloppy), "correct")


class SafetyTrack(unittest.TestCase):
    def test_garbled_requests_never_leave_a_broken_repository(self):
        t = bench_req.fuzz(list(SC.values()), n=900, seed=3)
        self.assertEqual(t["harness"], 0, t)
        self.assertGreater(t["raw"], 0, t)
        self.assertGreater(t["harness_applied"], 0, t)  # the desk is not passing by refusing everything


class Parts(unittest.TestCase):
    def test_calendars(self):
        hol, start = ["2026-12-31", "2027-01-01"], datetime.date(2026, 11, 13)
        iso = lambda rule: [d.isoformat() for d in run_dates(rule, hol, start, 60)]
        self.assertEqual(iso({"type": "month_end_workday"}), ["2026-11-30", "2026-12-30"])
        self.assertEqual(iso({"type": "month_day", "day": 15, "shift": "next"}), ["2026-11-16", "2026-12-15"])
        self.assertEqual(iso({"type": "month_day", "day": 15})[0], "2026-11-15")
        self.assertEqual(iso({"type": "weekly", "days": [5, 6]})[:2], ["2026-11-14", "2026-11-15"])
        self.assertNotIn("2026-12-31", iso({"type": "workdays"}))
        self.assertEqual(len(iso({"type": "daily"})), 60)

    def test_template_is_strict(self):
        values, errors = intake.parse("talep_no: A-1\ntalep_eden: x\nislem: yeni\nhost: app01\nrenk: mavi\nhost: db01")
        self.assertEqual(values["host"], "app01")
        self.assertTrue(any("sablonda olmayan" in e for e in errors))
        self.assertTrue(any("iki kez" in e for e in errors))
        self.assertTrue(any("zorunlu alan bos: saat" in e for e in errors))
        self.assertTrue(any("bagimlilik" in e for e in errors))
        _, errors = intake.parse("talep_no: A-2\ntalep_eden: x\nislem: degisiklik\nklasor: K\nis_adi: J")
        self.assertEqual(errors, ["degisecek alan yazilmamis"])
        _, errors = intake.parse("talep_no: A-3\ntalep_eden: x\nislem: sil")
        self.assertIn("islem 'yeni', 'degisiklik' ya da 'kaldir' olmali", errors)
        _, errors = intake.parse("talep_no: A-4\ntalep_eden: x\nislem: kaldir\nklasor: K\nis_adi: J\nsaat: 02:00")
        self.assertTrue(any("fazla alan: saat" in e for e in errors))
        self.assertEqual(intake.parse("talep_no: A-5\ntalep_eden: x\nislem: kaldir\nklasor: K\nis_adi: J")[1], [])

    def test_checks_find_what_an_admin_would(self):
        repo = Repo(SC["t-yeni-001"])
        env, jobs = repo.list_env(), dict(repo.jobs)
        good = SC["t-yeni-001"]["expected"]["definition"]
        rules = load_request_rules(ROOT / "skills")
        codes = lambda d, new=True: {f["code"] for f in checks.check(env, jobs, d, new, rules)}
        std = "S_talep-standartlari."
        self.assertEqual(codes(good), set())
        self.assertIn("E_RUNAS", codes({**good, "run_as": "dbbatch"}))
        self.assertIn("E_HOST", codes({**good, "host": "yok01"}))
        self.assertIn(std + "ad_oneki", codes({**good, "name": "RPR_LOAD_IADE"}))
        self.assertIn(std + "ad_bicimi", codes({**good, "name": "odm_load_iade"}))
        self.assertIn(std + "komut_tam_yol", codes({**good, "command": "load.sh"}))
        self.assertIn(std + "bildirim_adresi", codes({**good, "notify": "x@gmail.com"}))
        self.assertIn("E_TIME", codes({**good, "time": "25:00"}))
        self.assertIn("E_DEP", codes({**good, "deps": ["YOK_IS"]}))
        self.assertIn("E_MISSING", codes(good, new=False))
        self.assertEqual(codes({**good, "time": "00:30"}), {"W_TIME_BEFORE_DEP"})
        loop = {**jobs["ODM_WATCH_DOSYA"], "deps": ["RPR_GUNLUK_OZET"]}
        self.assertIn("E_CYCLE", codes(loop, new=False))
        self.assertIn("E_SELF", codes({**jobs["ODM_WATCH_DOSYA"], "deps": ["ODM_WATCH_DOSYA"]}, new=False))

    def test_a_job_must_not_run_on_days_its_predecessor_does_not(self):
        repo = Repo(SC["t-yeni-001"])
        env, jobs = repo.list_env(), dict(repo.jobs)
        runs = {c: set(repo.forecast(c, 180)) for c in env["calendars"]}
        codes = lambda d, new=True, site=jobs: {f["code"] for f in checks.check(env, site, d, new, (), runs)}
        new = {**SC["t-yeni-001"]["expected"]["definition"], "deps": ["ODM_LOAD_ODEME"]}  # predecessor: working days
        self.assertEqual(codes({**new, "calendar": "IS_GUNU"}), set())
        self.assertEqual(codes({**new, "calendar": "AY_SONU_IS_GUNU"}), set())     # fewer days than the predecessor: fine
        self.assertEqual(codes({**new, "calendar": "HERGUN"}), {"E_CAL_DEP"})      # would wait for ever at weekends
        self.assertEqual(codes({**new, "calendar": "HAFTA_SONU"}), {"E_CAL_DEP"})
        self.assertEqual(codes({**new, "calendar": "HERGUN"}, site=jobs) and codes({**new, "calendar": "HERGUN"}), {"E_CAL_DEP"})
        # a change is judged the same way, and so are the jobs that wait for the changed one
        mid = jobs["ODM_LOAD_ODEME"]
        self.assertEqual(codes({**mid, "calendar": "HERGUN"}, new=False), {"E_CAL_DEP"})
        self.assertEqual(codes({**mid, "calendar": "AY_SONU_IS_GUNU"}, new=False), {"E_CAL_DEPENDENT"})
        first = jobs["ODM_WATCH_DOSYA"]
        self.assertEqual(codes({**first, "calendar": "HERGUN"}, new=False), set())  # the head of a chain may widen
        # a mismatch that is already on the site is not blamed on a request that does not touch it
        odd = {**jobs, "ODM_LOAD_ODEME": {**mid, "calendar": "HERGUN"}}
        self.assertEqual(codes({**odd["ODM_LOAD_ODEME"], "time": "03:10"}, new=False, site=odd), set())
        self.assertEqual(codes({**odd["ODM_LOAD_ODEME"], "calendar": "HAFTA_SONU"}, new=False, site=odd),
                         {"E_CAL_DEP", "E_CAL_DEPENDENT"})
        # without forecasts the check is silent rather than guessing
        self.assertEqual({f["code"] for f in checks.check(env, jobs, {**new, "calendar": "HERGUN"}, True)}, set())


if __name__ == "__main__":
    unittest.main()
