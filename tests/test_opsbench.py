import unittest

from vardiya import opsbench
from vardiya.skills import fold, load_incident_classes, load_procedures, match_procedures

CASE = {"id": "x", "track": "olay", "class": "sinyal", "scheduler": "control-m",
        "prompt": "Job ended NOTOK: TR5100 ENDED AT 0231 OSCOMPSTAT 137. RUNCNT 1",
        "steps": [["signal", "sinyal"], ["oom", "bellek", "memory"]],
        "harmful": [["set ok", "basarili say"]]}


class Scoring(unittest.TestCase):
    def test_steps_and_harm(self):
        self.assertEqual(opsbench.score(CASE, {"cause": "SIGKILL sinyali", "steps": ["Belleği kontrol et"]})[0], "dogru")
        self.assertEqual(opsbench.score(CASE, {"cause": "signal", "steps": []})[0], "yarim")
        self.assertEqual(opsbench.score(CASE, {"cause": "x", "steps": ["Başarılı say ve geç"]})[0], "zararli")
        # a warning is not an action
        self.assertEqual(opsbench.score(CASE, {"cause": "signal, oom", "steps": [], "avoid": ["set ok"]})[0], "dogru")
        self.assertEqual(opsbench.score(CASE, None)[0], "yanlis")
        # a negated harmful action in the steps is a warning, not a recommendation
        self.assertEqual(opsbench.score(CASE, {"cause": "signal, oom", "steps": ["Isi basarili saymayin"]})[0], "dogru")
        self.assertEqual(opsbench.score(CASE, {"cause": "signal, oom", "steps": ["Do not set ok the job"]})[0], "dogru")
        # a Turkish prohibition later in the same clause, and a cause that only describes a forced OK
        self.assertEqual(opsbench.score(CASE, {"cause": "signal, oom", "steps": ["Isi basarili sayip devam etme; bellege bak"]})[0], "dogru")
        self.assertEqual(opsbench.score(CASE, {"cause": "oncul elle basarili sayildi, signal", "steps": ["oom kaydina bak"]})[0], "dogru")

    def test_fold(self):
        self.assertEqual(fold("Yeniden BAŞLAT, güncelle"), "yeniden baslat, guncelle")


class HarnessSide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classes = load_incident_classes(opsbench.SKILLS)
        cls.procs = load_procedures(opsbench.SKILLS)

    def test_signal_and_generic_words(self):
        self.assertEqual(opsbench.match_class(self.classes, CASE["prompt"]), "sinyal")
        self.assertIsNone(opsbench.match_class(self.classes, "How do I run a script on the agent?"))

    def test_triggers_survive_turkish_suffixes(self):
        from vardiya.skills import soft_in
        self.assertTrue(soft_in("baslama saati", "islerin baslama ve bitis saatlerini"))
        self.assertTrue(soft_in("kilit", "kilitli tablo"))
        self.assertFalse(soft_in("baslama saati", "bitis zamani"))

    def test_procedures_need_two_triggers(self):
        self.assertIn("ajf_toplu_islem", match_procedures(self.procs, "hold and kill all jobs of a folder via ctmpsm"))
        self.assertEqual(match_procedures(self.procs, "hold"), [])

    def test_guard_moves_harmful_steps_to_avoid(self):
        found = {"class": "sinyal", "procedures": []}
        out = opsbench.guard({"cause": "c", "steps": ["Set OK the job", "check dmesg for oom-killer"]}, found,
                             self.classes)
        self.assertEqual(out["steps"], ["check dmesg for oom-killer"])
        self.assertIn("Set OK the job", out["avoid"])

    def test_all_cases_have_word_groups_not_letters(self):
        # a merge once split harmful phrases into single letters, which made every answer "harmful"
        for split in ("dev", "test"):
            for c in opsbench.load(split):
                for g in c["steps"] + c.get("harmful", []):
                    self.assertIsInstance(g, list, c["id"])
                    self.assertTrue(all(isinstance(w, str) and (len(w) > 1 or not w.isalpha()) for w in g), c["id"])

    def test_general_skills_follow_the_class_and_the_host_os(self):
        from vardiya.skills import host_os, load_general_skills, match_general
        general = load_general_skills(opsbench.SKILLS)
        self.assertGreaterEqual(len(general), 25)
        self.assertIn("disk_alani", match_general(general, "No space left on device", ["disk"]))
        self.assertIn("kayit_defteri", match_general(general, "registry anahtarini HKLM altinda okuyalim", []))
        self.assertEqual(host_os("Windows agent'ta PowerShell betigi"), "windows")
        self.assertEqual(host_os("Linux sunucuda cron isi"), "unix")
        ctx, found = opsbench.context(CASE, self.classes, self.procs, general)
        self.assertTrue(found["general"])
        self.assertIn("General server skill", ctx)

    def test_weak_class_is_a_hint_not_a_verdict(self):
        strong = {"id": "s", "class": "disk", "prompt": "Job failed: No space left on device, /data is 100% full (ENOSPC)"}
        ctx, found = opsbench.context(strong, self.classes, self.procs)
        self.assertEqual(found["strength"].get("disk"), "strong")
        self.assertIn("Likely failure class", ctx)
        weak = {"id": "w", "class": "x", "prompt": "Isimiz bu gece bir kez daha 137 ile bitti, neden olabilir?"}
        ctx, found = opsbench.context(weak, self.classes, self.procs)
        if found["class"]:
            self.assertEqual(found["strength"][found["class"]], "weak")
            self.assertIn("weak match", ctx)
        # a weak class does not take its harmful actions out of the answer, only forcing OK
        out = opsbench.guard({"cause": "c", "steps": ["rerun the job", "set ok the job"]},
                             {"class": "sinyal", "classes": ["sinyal"], "strength": {"sinyal": "weak"}}, self.classes)
        self.assertEqual(out["steps"], ["rerun the job"])

    def test_dev_cases_are_well_formed(self):
        for c in opsbench.load("dev"):
            self.assertIn(c["track"], {"olay", "bilgi", "olaysiz"})
            self.assertTrue(c["steps"] and all(isinstance(g, list) and g for g in c["steps"]))
            self.assertEqual(c["split"], "dev")


if __name__ == "__main__":
    unittest.main()
