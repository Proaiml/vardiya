import json
import threading
import unittest
import urllib.request

from vardiya import web

NEW = """talep_no: W-1
talep_eden: rapor-ekibi
islem: yeni
klasor: RAPOR
is_adi: RPR_AY_SONU_OZET
tip: komut
host: rpr01
calistiran: rprusr
komut: /opt/rapor/bin/ay_sonu_ozet.sh
gunler: her ayin son is gunu
saat: 06:30
bagimlilik: [RPR_GUNLUK_OZET]
bildirim: rapor-nobet@ornek.local
aciklama: Ay sonu ozet raporunu uretir"""


class OfficeTest(unittest.TestCase):
    def test_requests_change_the_site_the_next_request_sees(self):
        office = web.Office()
        first = office.submit(NEW)
        self.assertEqual(first["outcome"], "closed")
        self.assertIn("RPR_AY_SONU_OZET", office.site()["changed"])
        # the same number twice is refused before the desk sees it
        self.assertIn("error", office.submit(NEW))
        # the job now exists, so the same job as "yeni" is returned with a reason
        again = office.submit(NEW.replace("W-1", "W-2"))
        self.assertEqual(again["outcome"], "returned")
        self.assertTrue(any("zaten tanimli" in r for r in again["reasons"]))
        # a job others now wait for cannot move to days it would leave them waiting on
        later = office.submit("talep_no: W-3\ntalep_eden: r\nislem: degisiklik\nklasor: RAPOR\n"
                              "is_adi: RPR_GUNLUK_OZET\ngunler: PAZARTESI")
        self.assertEqual(later["outcome"], "returned")
        ledger = office.ledger_rows()
        self.assertTrue(ledger["chain_ok"])
        self.assertEqual(len(ledger["rows"]), 3)
        office.reset()
        self.assertEqual(office.site()["changed"], [])
        self.assertEqual(office.history, [])

    def test_a_request_without_a_number_gets_one(self):
        office = web.Office()
        out = office.submit("# yorum satiri\n" + NEW.split("\n", 1)[1])
        self.assertEqual(out["talep_no"], "WEB-0001")
        self.assertEqual(out["outcome"], "closed")

    def test_low_licence_only_proposes(self):
        office = web.Office(licence=2)
        self.assertEqual(office.submit(NEW)["outcome"], "proposed")
        self.assertEqual(office.site()["changed"], [])

    def test_a_password_in_a_request_is_returned_and_never_kept(self):
        office = web.Office()
        text = (web.ROOT / "ornekler" / "talep-aktarim-parola.txt").read_text(encoding="utf-8")
        out = office.submit(text)
        self.assertEqual(out["outcome"], "returned")
        self.assertNotIn("Gizli2026", json.dumps(office.history, ensure_ascii=False))
        self.assertEqual(office.submit((web.ROOT / "ornekler" / "talep-veritabani.txt").read_text(encoding="utf-8"))["outcome"],
                         "closed")

    def test_bench_summary_reads_only_the_results_folder(self):
        self.assertIsNone(web.bench_summary("../README.md")["file"])


class ServerTest(unittest.TestCase):
    def test_page_and_api_over_http(self):
        office = web.Office()
        httpd = web.http.server.ThreadingHTTPServer(("127.0.0.1", 0), web.make_handler(office))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{httpd.server_port}"
        try:
            page = urllib.request.urlopen(base + "/").read().decode()
            self.assertIn("Vardiya Operasyon", page)
            site = json.loads(urllib.request.urlopen(base + "/api/site").read())
            self.assertIn("RPR_GUNLUK_OZET", [j["name"] for j in site["jobs"]])
            req = urllib.request.Request(base + "/api/request", json.dumps({"text": NEW}).encode(),
                                         {"Content-Type": "application/json"})
            self.assertEqual(json.loads(urllib.request.urlopen(req).read())["outcome"], "closed")
            self.assertEqual(len(json.loads(urllib.request.urlopen(base + "/api/history").read())), 1)
            self.assertTrue(json.loads(urllib.request.urlopen(base + "/api/examples").read()))
        finally:
            httpd.shutdown()
            httpd.server_close()


if __name__ == "__main__":
    unittest.main()
