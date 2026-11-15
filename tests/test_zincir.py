import pathlib
import tempfile
import unittest

from vardiya import opsbench, zincir
from vardiya.skills import load_chains, load_general_skills, load_incident_classes, load_procedures

CASE = {"id": "z1", "track": "olay", "class": "disk", "scheduler": "control-m",
        "prompt": "Job failed: No space left on device on /data",
        "steps": [["disk", "df"], ["temizle", "clean", "yer ac"]], "harmful": [["rm -rf"]]}


class Chains(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.C, cls.P = load_incident_classes(opsbench.SKILLS), load_procedures(opsbench.SKILLS)
        cls.G = load_general_skills(opsbench.SKILLS)
        cls.index = zincir.skill_index(cls.C, cls.P, cls.G)

    def test_steps_map_to_skills(self):
        self.assertEqual(zincir.map_step("df -h ile diski kontrol et", self.index), "genel:disk_alani")
        self.assertEqual(zincir.map_step("keytool -list ile guven deposuna bak", self.index), "genel:sertifika_inceleme")
        self.assertIsNone(zincir.map_step("biraz bekle", self.index))

    def test_only_correct_answers_are_mined_and_order_is_kept(self):
        good = {"id": "z1", "answer": {"cause": "disk dolu", "steps": [
            "df -h ile diski kontrol et", "eski gunlukleri temizle, yer ac", "agent'i yeniden baslat ve durumu dogrula"]}}
        bad = {"id": "z1", "answer": {"cause": "bilmiyorum", "steps": ["biraz bekle"]}}
        chains, gaps, used = zincir.mine([good, good, bad], {"z1": CASE}, self.index)
        self.assertEqual(used, 2)
        order = chains["disk"]["order"]
        self.assertEqual(order[0], "genel:disk_alani")
        self.assertEqual(order[-1], "genel:yeniden_baslatma_dogrulama")

    def test_written_chain_loads_and_reaches_the_harness(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "cozum-zincirleri" / "SKILL.md"
            zincir.write({"disk": {"order": ["genel:disk_alani", "sinif:disk"], "support": 2}}, "deneme", path)
            chains = load_chains(d)
        self.assertEqual(chains["disk"]["order"], ["genel:disk_alani", "sinif:disk"])
        ctx, found = opsbench.context(CASE, self.C, self.P, self.G, chains)
        self.assertEqual(found["chain"], ["genel:disk_alani", "sinif:disk"])
        self.assertIn("Order that solved similar cases", ctx)
        _, found0 = opsbench.context(CASE, self.C, self.P, self.G, {})
        self.assertEqual(found0["chain"], [])

    def test_arms_choose_their_skills(self):
        self.assertEqual(opsbench.arm_skills("harness0", self.G, {"x": 1}), ({}, {}))
        self.assertEqual(opsbench.arm_skills("harnessg", self.G, {"x": 1}), (self.G, {}))
        self.assertEqual(opsbench.arm_skills("harness", self.G, {"x": 1}), (self.G, {"x": 1}))


if __name__ == "__main__":
    unittest.main()
