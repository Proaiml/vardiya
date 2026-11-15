import unittest

try:
    import numpy  # noqa: F401
    HAVE_NUMPY = True
except ImportError:  # the graph model is optional; the rest of the harness is standard library only
    HAVE_NUMPY = False

from vardiya import opsbench
from vardiya.skills import load_incident_classes, load_procedures


@unittest.skipUnless(HAVE_NUMPY, "numpy yok")
class GraphModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from vardiya import gnn
        cls.model, _ = gnn.train(None)

    def test_first_guess_is_a_short_ranked_list(self):
        dev = opsbench.load("dev")
        out = self.model.predict(dev[0]["id"])
        self.assertEqual(len(out["class"]), 3)
        ps = [p for _, p in out["class"]]
        self.assertEqual(ps, sorted(ps, reverse=True))

    def test_training_split_is_the_development_split_only(self):
        from vardiya import gnn
        model, others = gnn.train("test")
        self.assertTrue(others)
        trained = {self.model.kind[i][1] for i in range(len(self.model.kind)) if self.model.kind[i][0] == "case"}
        self.assertFalse(trained & {c["id"] for c in others})

    def test_guess_reaches_the_harness_context(self):
        C, P = load_incident_classes(opsbench.SKILLS), load_procedures(opsbench.SKILLS)
        case = opsbench.load("dev")[0]
        ctx, found = opsbench.context(case, C, P, None, None, self.model.predict(case["id"]))
        self.assertTrue(ctx.startswith("Graph model first guess"))
        self.assertEqual(len(found["gnn"]["class"]), 3)


if __name__ == "__main__":
    unittest.main()
