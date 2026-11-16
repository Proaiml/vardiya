"""The heat watchdog's decision rule (tools/isi_bekcisi.py), without touching the machine."""
import importlib.util
import pathlib
import unittest

spec = importlib.util.spec_from_file_location("isi_bekcisi", pathlib.Path(__file__).resolve().parent.parent / "tools" / "isi_bekcisi.py")
bekci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bekci)


def olcum(gpu=60, cpu=20, ram=8.0):
    return {"gpu_c": gpu, "cpu": cpu, "ram": ram}


class Karar(unittest.TestCase):
    def setUp(self):
        self.d = {"hal": "calis", "sicak": 0, "serin": 0}

    def adim(self, **kw):
        yeni, _ = bekci.karar(olcum(**kw), self.d)
        if yeni != self.d["hal"]:
            self.d.update(hal=yeni, sicak=0, serin=0)
        return yeni

    def test_cool_machine_keeps_running(self):
        self.assertEqual([self.adim() for _ in range(3)], ["calis"] * 3)

    def test_hot_gpu_pauses_at_once_and_resumes_after_two_calm_minutes(self):
        self.assertEqual(self.adim(gpu=bekci.GPU_BEKLE), "bekle")
        self.assertEqual(self.adim(gpu=bekci.GPU_DEVAM + 3), "bekle")      # cooler, but not cool enough
        self.assertEqual(self.adim(gpu=bekci.GPU_DEVAM), "bekle")          # first calm minute
        self.assertEqual(self.adim(gpu=bekci.GPU_DEVAM - 2), "calis")      # second calm minute

    def test_cpu_load_needs_two_minutes(self):
        self.assertEqual(self.adim(cpu=bekci.CPU_BEKLE + 10), "calis")
        self.assertEqual(self.adim(cpu=bekci.CPU_BEKLE + 10), "bekle")

    def test_low_memory_pauses_and_very_low_stops(self):
        self.assertEqual(self.adim(ram=bekci.RAM_BEKLE - 0.5), "bekle")
        self.assertEqual(self.adim(ram=bekci.RAM_DUR - 0.2), "dur")

    def test_emergency_temperature_stops(self):
        self.assertEqual(self.adim(gpu=bekci.GPU_DUR), "dur")

    def test_missing_gpu_reading_does_not_pause(self):
        self.assertEqual(self.adim(gpu=None), "calis")


if __name__ == "__main__":
    unittest.main()
