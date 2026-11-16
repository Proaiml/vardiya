import unittest

try:
    import numpy  # noqa: F401
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False

from vardiya.saha import erken_skor, erken_tahmin, erken_topla

T0 = 1_800_000_000.0


def kosu(no, sn, ok=True, df=None, sayac=None, hata=None):
    return {"no": no, "bas": T0 + no, "bit": T0 + no + sn, "sn": sn, "ok": ok, "cikis": 0 if ok else 1, "hata": hata,
            "df": [{"mount": "/data/dar", "kullanilan_kb": df, "toplam_kb": 4096}] if df is not None else [],
            "sayac": sayac or {}}


def is_(ad, kosular, **kw):
    d = {"id": f"F/{ad}", "jobId": "x", "folder": "F", "ad": ad, "durum": "Ended OK", "kosu_sayisi": len(kosular), "host": "ajan1",
         "calisan": "batch", "tip": "Job:Script", "komut": "", "betik_yolu": None, "betik_metni": None, "sql": "", "tablolar": [],
         "profiller": [], "timeout": None, "limit": None, "planli": None, "aciklama": None, "hedef_dizinler": [], "kosular": kosular}
    d.update(kw)
    return d


def site():
    isler = [
        is_("DISK", [kosu(k, 2, df=1000 + 150 * k) for k in range(1, 17)]),
        is_("DURGUN", [kosu(k, 2, df=800) for k in range(1, 17)]),
        is_("SURE", [kosu(k, 1 + k // 2 + 1) for k in range(1, 17)], timeout=12),
        is_("YAVAS", [kosu(k, 7 + (k % 2) * 0.2) for k in range(1, 17)], timeout=40),
        is_("HATA", [kosu(k, 1, ok=k not in (6, 10, 13, 15), hata=None if k not in (6, 10, 13, 15) else "ERROR: reset") for k in range(1, 17)]),
        is_("TEK", [kosu(k, 1, ok=k != 4, hata=None if k != 4 else "ERROR: x") for k in range(1, 17)]),
        is_("YIGIN", [kosu(k, 1, sayac={"bekleyen_dosya": 10 + 3 * k}) for k in range(1, 17)], limit=70),
        is_("HESAP", [kosu(k, 1) for k in range(1, 17)], profiller=["PG_RAPOR"]),
        is_("YUKLE", [kosu(k, 1) for k in range(1, 17)], profiller=["PG_UYG"], tablolar=["satis_gecici"], planli="0200"),
    ]
    return {"t": T0 + 20, "isler": isler,
            "diskler": {"ajan1": [{"mount": "/data/dar", "toplam_kb": 4096, "kullanilan_kb": 3400, "yuzde": 83}], "ajan2": []},
            "dizinler": {"ajan1:/data/dar": [{"ad": "eski_cikti.dat", "kb": 900.0, "sahip": "batch", "yas_sn": 9}, {"ad": "DISK.dat", "kb": 2400.0, "sahip": "batch", "yas_sn": 1}]},
            "roller": [{"rol": "rapor_user", "gecerlilik": T0 + 20 + 5 * 3600, "gecerlilik_metni": "x", "baglanti_siniri": -1},
                       {"rol": "etl_user", "gecerlilik": None, "gecerlilik_metni": "infinity", "baglanti_siniri": -1}],
            "profiller": {"PG_RAPOR": {"tip": "Database:PostgreSQL", "kullanici": "rapor_user", "anahtar": None, "sunucu": "appdb"},
                          "PG_UYG": {"tip": "Database:PostgreSQL", "kullanici": "etl_user", "anahtar": None, "sunucu": "appdb"}},
            "oturumlar": [{"pid": 9, "kullanici": "etl_user", "durum": "idle in transaction", "xact_sn": 30, "bekliyor": False, "sorgu": ""},
                          {"pid": 10, "kullanici": "etl_user", "durum": "idle in transaction", "xact_sn": 30, "bekliyor": False, "sorgu": ""}],
            "kilitler": [{"pid": 9, "tablo": "satis_gecici", "kip": "AccessExclusiveLock", "verildi": True},
                         {"pid": 10, "tablo": "musteri", "kip": "ShareLock", "verildi": True}],
            "anahtar_dosyalari": [], "yetkili_anahtarlar": [], "ajanlar": {"ajan1": "COUPLED"}}


class Toplayici(unittest.TestCase):
    def test_output_metrics_and_exit_code(self):
        self.assertEqual(erken_topla._cikis("[MAIN] [End] [Error] returnCode=3, x"), 3)
        self.assertEqual(erken_topla._hata("a\n[STDERR] HATA: x\nb"), "HATA: x")
        m = erken_topla.DF_SATIRI.findall("df: /data/dar kullanilan_kb=120 toplam_kb=4096\n")
        self.assertEqual(m, [("/data/dar", "120", "4096")])
        self.assertEqual(erken_topla.SAYAC.findall("bekleyen_dosya: 33 (sinir 60)\n"), [("bekleyen_dosya", "33")])

    def test_graph_holds_jobs_runs_and_disk_series(self):
        g, today = erken_topla.grafa_isle(site())
        self.assertEqual(len(g.nodes("job")), 9)
        self.assertEqual(len(g.runs("F/DISK")), 16)
        self.assertEqual(len(g.get("host:ajan1")["disk"]), 16)
        self.assertEqual(len(g.nodes("run")), 9 * 16)


class Kurallar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = site()
        cls.w = {(w["is"], w["sinif"]): w for w in erken_tahmin.kurallar(erken_tahmin.cikar(cls.s))}

    def test_every_risk_is_found(self):
        for i, c in (("DISK", "disk_dolu"), ("SURE", "sure_asimi"), ("HATA", "tekrarlayan_hata"), ("YIGIN", "birikim"),
                     ("HESAP", "hesap_suresi"), ("YUKLE", "kilit_bekleme")):
            self.assertIn((f"F/{i}", c), self.w, c)

    def test_lookalikes_are_not_flagged(self):
        flagged = {i for i, _ in self.w}
        for i in ("DURGUN", "YAVAS", "TEK"):
            self.assertNotIn(f"F/{i}", flagged)
        # the lock on the table no job writes does not flag anything
        self.assertEqual([k for k in self.w if k[1] == "kilit_bekleme"], [("F/YUKLE", "kilit_bekleme")])

    def test_disk_deadline_is_the_failing_run(self):
        # 3400 KB used, 696 free, 150 KB per run: the fifth run fails
        self.assertEqual(self.w[("F/DISK", "disk_dolu")]["ne_zaman"], {"tur": "kosu", "n": 5})

    def test_remedy_removes_the_old_file_not_the_jobs_own(self):
        w = self.w[("F/DISK", "disk_dolu")]
        s = site()
        s["isler"][0]["betik_yolu"], s["isler"][0]["betik_metni"] = "/a/b.sh", "f=/data/dar/DISK.dat"
        self.assertIn("eski_cikti.dat", erken_tahmin.oneri(s, w)["komut"])

    def test_pack_names_source_and_what_was_checked(self):
        s = self.s
        b = erken_tahmin.birlestir(list(self.w.values()), [])
        p = erken_tahmin.paket(s, b, erken_tahmin.inceleme(s, erken_tahmin.cikar(s), b))
        self.assertIn("kaynak=kural", p)
        self.assertIn("uyari vermedigi", p.lower().replace("ı", "i"))


class Skor(unittest.TestCase):
    gercek = {"riskler": [{"is": "F/DISK", "sinif": "disk_dolu", "son": {"tur": "kosu", "n": 5}},
                          {"is": "F/HESAP", "sinif": "hesap_suresi", "son": {"tur": "saat", "t": T0 + 5 * 3600}}], "tuzaklar": []}
    isler = {"F/DISK", "F/HESAP", "F/DURGUN", "F/X"}

    def test_parse(self):
        w = erken_skor.ayikla("UYARI | is=F/DISK | sinif=disk_dolu | ne_zaman=5 kosu sonra | neden=doluyor\nUYARI | is=DURGUN | sinif=disk_dolu | ne_zaman= | neden=x")
        self.assertEqual([x["is"] for x in w], ["F/DISK", "DURGUN"])
        self.assertEqual(erken_skor.ayikla("UYARI YOK"), [])

    def test_score(self):
        w = erken_skor.ayikla("UYARI | is=F/DISK | sinif=disk_dolu | ne_zaman=6 kosu sonra | neden=a\n"
                              "UYARI | is=HESAP | sinif=anahtar_suresi | ne_zaman=5 saat sonra | neden=b\n"
                              "UYARI | is=DURGUN | sinif=disk_dolu | ne_zaman= | neden=c\nUYARI | is=YOKTUR | sinif=x | ne_zaman= | neden=d")
        s = erken_skor.skorla(w, self.gercek, self.isler, T0)
        self.assertEqual((s["bulunan"], s["dogru_neden"], s["dogru_zaman"], s["yanlis"]), (2, 1, 1, 2))

    def test_time_rules(self):
        son = {"tur": "saat", "t": T0 + 10 * 3600}
        self.assertTrue(erken_skor.zaman_dogru("2026-01-01 10:00", {"tur": "saat", "t": 1767261600.0}, 1767261600.0 - 36000))
        self.assertTrue(erken_skor.zaman_dogru("9.5 saat sonra", son, T0))
        self.assertFalse(erken_skor.zaman_dogru("3 kosu", son, T0))


@unittest.skipUnless(HAVE_NUMPY, "numpy yok")
class Graf(unittest.TestCase):
    def test_gradient_matches_finite_differences(self):
        import numpy as np
        from vardiya.saha import erken_graf
        s = site()
        oz = erken_tahmin.cikar(s)
        ad, X, A, idx = erken_graf.cizge(s, oz)
        rng = np.random.default_rng(0)
        W1, W2 = rng.normal(0, .3, (erken_graf.D, 5)), rng.normal(0, .3, (5, 8))
        rows = list(idx.values())
        y = rng.integers(0, 8, len(rows))

        def loss(W1_, W2_):
            L = A @ np.maximum(A @ X @ W1_, 0) @ W2_
            P = np.exp(L - L.max(1, keepdims=True))
            P /= P.sum(1, keepdims=True)
            return -np.log(P[rows, y]).sum()
        # analytic gradient of the same loss
        Z1 = A @ X @ W1
        H1 = np.maximum(Z1, 0)
        L = A @ H1 @ W2
        P = np.exp(L - L.max(1, keepdims=True))
        P /= P.sum(1, keepdims=True)
        dL = np.zeros_like(L)
        dL[rows] = P[rows]
        dL[rows, y] -= 1
        g2 = (A @ H1).T @ dL
        g1 = (A @ X).T @ ((A @ dL @ W2.T) * (Z1 > 0))
        for W, g, k in ((W1, g1, (3, 2)), (W2, g2, (1, 4))):
            e = np.zeros_like(W)
            e[k] = 1e-6
            num = (loss(W1 + (e if W is W1 else 0), W2 + (e if W is W2 else 0)) - loss(W1 - (e if W is W1 else 0), W2 - (e if W is W2 else 0))) / 2e-6
            self.assertAlmostEqual(num, g[k], places=3)

    def test_islands_do_not_reach_jobs(self):
        from vardiya.saha import erken_graf
        s = site()
        ad, X, A, idx = erken_graf.cizge(s, erken_tahmin.cikar(s))
        j = idx["F/DURGUN"]
        self.assertEqual(int((A[j] > 0).sum()), 2)      # itself and the volume node it writes to


if __name__ == "__main__":
    unittest.main()
