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


class Paylasim(unittest.TestCase):
    def test_another_session_on_the_card_pauses_until_it_says_done(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            hub = pathlib.Path(d) / "defter.txt"
            hub.write_text("[12:25] [ARGON] bitti: ses uretimi; ekran karti bos.\n[15:52] [ARGON] başlıyorum: ses (ekran kartı, ~14 GB)\n"
                           "[15:53] [VARDIYA] karti biraktim\n", encoding="utf-8")
            self.assertTrue(bekci.baskasi_kartta(hub))
            hub.write_text(hub.read_text(encoding="utf-8") + "[16:07] [ARGON] bitti: ekran kartı boş.\n", encoding="utf-8")
            self.assertFalse(bekci.baskasi_kartta(hub))
            self.assertFalse(bekci.baskasi_kartta(pathlib.Path(d) / "yok.txt"))

    def test_claim_pauses_and_a_busy_card_blocks_resume(self):
        d = {"hal": "calis", "sicak": 0, "serin": 0}
        self.assertEqual(bekci.karar({"gpu_c": 60, "cpu": 10, "ram": 9.0, "gpu_mb": 11000, "baskasi": True}, d)[0], "bekle")
        d = {"hal": "bekle", "sicak": 0, "serin": 0}
        busy = {"gpu_c": 60, "cpu": 10, "ram": 9.0, "gpu_mb": 9000, "baskasi": False}
        self.assertEqual([bekci.karar(busy, d)[0] for _ in range(3)], ["bekle"] * 3)
        free = {**busy, "gpu_mb": 300}
        self.assertEqual([bekci.karar(free, d)[0] for _ in range(2)], ["bekle", "calis"])
