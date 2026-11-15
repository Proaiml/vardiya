import unittest

from vardiya import opsbench
from vardiya.skills import load_incident_classes, load_procedures, match_procedures

CASE = {"id": "u1", "track": "olay", "class": "sinyal", "scheduler": "control-m",
        "prompt": "Job ended NOTOK: OSCOMPSTAT 137 on app01, RUNCNT 1",
        "steps": [["bellek", "memory", "oom"], ["dmesg"]], "harmful": [["set ok"]]}
DRAFT = {"cause": "bellek yetmedi", "steps": ["dmesg -T ile oom kaydina bak", "isi daha buyuk bellekli hosta tasi"],
         "avoid": []}


class Protocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.classes = load_incident_classes(opsbench.SKILLS)
        cls.procs = load_procedures(opsbench.SKILLS)

    def test_review_prompt_returns_the_draft_and_the_contract(self):
        with_sheet = opsbench.review_prompt(CASE, DRAFT, "Likely failure class: X")
        self.assertIn("dmesg -T ile oom kaydina bak", with_sheet)
        self.assertIn("Review sheet from the harness", with_sheet)
        self.assertIn("Final answer contract", with_sheet)
        alone = opsbench.review_prompt(CASE, DRAFT)
        self.assertNotIn("Review sheet", alone)
        self.assertIn("Final answer contract", alone)

    def test_a_silently_dropped_draft_step_is_restored(self):
        final = {"cause": "bellek", "steps": ["isi daha buyuk bellekli hosta tasi ve yeniden baslat"]}
        out = opsbench.merge(DRAFT, final, None, self.classes)
        self.assertEqual(out["restored"], 1)
        self.assertIn("dmesg -T ile oom kaydina bak", out["steps"])
        # the final answer is never thinner than the draft
        self.assertEqual(opsbench.score(CASE, out)[0], "dogru")
        self.assertEqual(opsbench.score(CASE, final)[0], "yarim")

    def test_an_explicit_drop_is_respected(self):
        final = {"cause": "bellek", "steps": ["isi daha buyuk bellekli hosta tasi"],
                 "dropped": [{"step": "dmesg -T ile oom kaydina bak", "why": "bu hostta dmesg okunamiyor"}]}
        out = opsbench.merge(DRAFT, final, None, self.classes)
        self.assertEqual(out["restored"], 0)
        self.assertEqual(len(out["steps"]), 1)

    def test_guard_still_removes_harm_after_the_merge(self):
        final = {"cause": "bellek", "steps": ["dmesg -T ile oom kaydina bak", "Set OK the job and move on"]}
        found = {"class": "sinyal", "classes": ["sinyal"], "strength": {"sinyal": "strong"}}
        out = opsbench.merge(DRAFT, final, found, self.classes)
        self.assertNotIn("Set OK the job and move on", out["steps"])
        self.assertIn("Set OK the job and move on", out["avoid"])

    def test_a_missing_final_answer_falls_back_to_the_draft(self):
        out = opsbench.merge(DRAFT, None, None, self.classes)
        self.assertEqual(out["steps"], DRAFT["steps"])
        self.assertEqual(out["cause"], DRAFT["cause"])

    def test_product_gate_keeps_other_schedulers_procedures_out(self):
        slurm = "Slurm isi OUT_OF_MEMORY ile dustu, sacct ciktisinda MaxRSS ReqMem'i asiyor"
        self.assertIn("slurm_is_dustu", match_procedures(self.procs, slurm))
        ctm = "Control-M isi timeout ile failed oldu, exit code 1"
        self.assertNotIn("slurm_is_dustu", match_procedures(self.procs, ctm))


if __name__ == "__main__":
    unittest.main()
