"""Ariza katalogu ve senaryo ureteci: Docker gerektirmeyen birim testleri."""
import json
import random
import re
import unittest

from vardiya.saha import katalog as k
from vardiya.saha.senaryo import dogrula_bicim

TURLER = ("aft", "os", "db")


def _kur(idler, tur, kume="dev", n=6):
    """Bir arizanin (ya da cift arizanin) bir is tipinde uretebildigi senaryolar (farkli baglamlarla)."""
    out = []
    for i in range(n):
        d = k.olustur(0, i + 1, idler, tur, kume, random.Random(f"test:{'-'.join(idler)}:{tur}:{i}"))
        if d:
            out.append(d)
    return out


def _isler(d):
    """Kurulumdaki deploy adimlarindan {klasor: {is adlari}}."""
    out = {}
    for st in d["kurulum"]:
        if "deploy" in st:
            for ad, tanim in st["deploy"].items():
                if isinstance(tanim, dict) and tanim.get("Type") == "Folder":
                    out[ad] = {j for j, v in tanim.items() if isinstance(v, dict) and str(v.get("Type", "")).startswith("Job:")}
    return out


class KatalogTest(unittest.TestCase):
    def test_en_az_30_ariza_ve_kimlikler_benzersiz(self):
        self.assertGreaterEqual(len(k.KATALOG), 30)
        self.assertEqual(len(set(k.KATALOG)), len(k.KATALOG))
        for i, a in k.KATALOG.items():
            self.assertEqual(i, a.id)
            self.assertTrue(a.kaynak and a.kok and a.ip and a.sinif, i)
            self.assertTrue(set(a.turler) <= set(TURLER), i)
            self.assertGreaterEqual(len(a.ip), 3, f"{i}: dev ve test icin en az 3 baglam cumlesi")

    def test_her_ariza_iddia_ettigi_her_tipte_gecerli_senaryo_uretir(self):
        for i, a in k.KATALOG.items():
            for tur in a.turler:
                ds = _kur([i], tur)
                self.assertTrue(ds, f"{i} {tur}: hic senaryo uretilemedi")
                for d in ds:
                    self.assertEqual(dogrula_bicim(d), [], f"{d['id']}")
                    self.assertEqual(d["ariza"], [i])
                    self.assertTrue(d["kaynak"])

    def test_kontrol_ve_cozum_tanimdaki_islere_bakar(self):
        for i, a in k.KATALOG.items():
            for tur in a.turler:
                for d in _kur([i], tur, n=4):
                    isler = _isler(d)
                    self.assertTrue(isler, d["id"])
                    for c in d["kontroller"]:
                        if "is" in c and c["is"]["durum"] == "Ended OK":
                            self.assertIn(c["is"]["job"], isler.get(c["is"]["folder"], set()), f"{d['id']} {c}")
                    for st in d["cozum"]:
                        for ref in re.findall(r"\{jobid:([^/}]+)/([^}]+)\}", json.dumps(st)):
                            self.assertIn(ref[1], isler.get(ref[0], set()), f"{d['id']} {st}")
                    self.assertTrue(d["cozum"] and "bekle" in d["cozum"][-1], d["id"])

    def test_uretec_belirli_bir_tohum_icin_deterministik(self):
        a = json.dumps(k.uret(1, 12), sort_keys=True)
        b = json.dumps(k.uret(1, 12), sort_keys=True)
        self.assertEqual(a, b)
        self.assertNotEqual(a, json.dumps(k.uret(2, 12), sort_keys=True))

    def test_birlesik_ciftler_gecerli(self):
        self.assertGreaterEqual(len(k.COMPOUND), 20)
        for a, b in k.COMPOUND:
            self.assertIn(a, k.KATALOG)
            self.assertIn(b, k.KATALOG)
            self.assertTrue(k.cift_gecerli(a, b), f"{a} + {b}")
            ok = [d for tur in TURLER for d in _kur([a, b], tur, n=4)]
            self.assertTrue(ok, f"{a} + {b}: hicbir tipte uretilemedi")
            for d in ok:
                self.assertEqual(dogrula_bicim(d), [], d["id"])
                self.assertTrue(d["bilesik"])
                self.assertEqual(d["ariza"], [a, b])

    def test_talep_kok_nedeni_soylemez(self):
        for d in k.uret(1, 30) + k.uret(2, 40):
            for kok in d["kok_neden"].split(". "):
                kok = kok.strip().rstrip(".")
                if len(kok) > 25:
                    self.assertNotIn(kok.lower(), d["talep"].lower(), d["id"])
            self.assertNotRegex(d["talep"], r"[{}]", d["id"])
            self.assertTrue(d["talep"].isascii() and d["kok_neden"].isascii(), d["id"])

    def test_dev_kumesi_test_ozel_arizalari_icermez_ve_test_en_az_8_yeni_ariza_tasir(self):
        ozel = {i for i, a in k.KATALOG.items() if a.test_ozel}
        self.assertGreaterEqual(len(ozel), 8)
        dev = k.uret(1, 30)
        self.assertFalse({i for d in dev for i in d["ariza"]} & ozel)
        test = k.uret(2, 60)
        self.assertGreaterEqual(len({i for d in test for i in d["ariza"]} & ozel), 8)

    def test_bilesik_orani_ve_tip_dagilimi(self):
        for tohum, adet in ((1, 30), (2, 60)):
            out = k.uret(tohum, adet)
            self.assertEqual(len(out), adet)
            self.assertEqual(len({d["id"] for d in out}), adet)
            self.assertAlmostEqual(sum(d["bilesik"] for d in out) / adet, 0.3, delta=0.04)
            for t in TURLER:
                self.assertGreaterEqual(sum(d["tur"] == t for d in out), adet // 6, t)

    def test_senaryo_anahtarlari(self):
        for d in k.uret(2, 20):
            for key in ("id", "aile", "tur", "bilesik", "talep", "kurulum", "kontroller", "zarar", "kok_neden", "cozum", "kaynak", "ariza"):
                self.assertIn(key, d)
            self.assertTrue(all(i in k.KATALOG for i in d["ariza"]))
            self.assertEqual(len(d["kaynak"]), len(d["ariza"]))


if __name__ == "__main__":
    unittest.main()
