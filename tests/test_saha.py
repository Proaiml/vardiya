"""The parts of the live lab that need no Docker: definition validation, the judge's comparisons, scenario shape,
the harness guard and the skill cards."""
import json
import re
import unittest

from vardiya.saha import senaryo, usta
from vardiya.saha.araclar import EL_KITABI
from vardiya.saha.ctm import Ctm, CtmError


class FakeLab:
    cfg = {"agents": {"ajan1": "", "ajan2": ""}}
    cid = "x"

    class durum:  # noqa: N801 - stands in for a pathlib.Path
        @staticmethod
        def exists():
            return False


def ctm():
    return Ctm(FakeLab())


FOLDER = {"GUNSONU": {"Type": "Folder", "Host": "ajan1", "RunAs": "batch",
                      "URET": {"Type": "Job:Script", "FilePath": "/app/scripts", "FileName": "a.sh"},
                      "GONDER": {"Type": "Job:FileTransfer", "ConnectionProfileSrc": "A", "ConnectionProfileDest": "B",
                                 "FileTransfers": [{"Src": "/a/x_%%$ODATE.csv", "Dest": "/b/"}]},
                      "akis": {"Type": "Flow", "Sequence": ["URET", "GONDER"]}}}


class Build(unittest.TestCase):
    def test_valid_folder_and_profile(self):
        folders, profiles = ctm().build({**FOLDER, "B": {"Type": "ConnectionProfile:FileTransfer:Local", "User": "batch"}})
        self.assertEqual(sorted(folders), ["GUNSONU"])
        self.assertEqual(sorted(profiles), ["B"])

    def test_errors_name_the_job_and_the_field(self):
        bad = json.loads(json.dumps(FOLDER))
        bad["GUNSONU"]["URET"].pop("FileName")
        bad["GUNSONU"]["GONDER"]["Host"] = "ajan9"
        bad["GUNSONU"]["akis"]["Sequence"] = ["URET", "YOK"]
        with self.assertRaises(CtmError) as e:
            ctm().build(bad)
        msg = str(e.exception)
        self.assertIn("GUNSONU/URET", msg)
        self.assertIn("FileName", msg)
        self.assertIn("ajan9", msg)
        self.assertIn("YOK", msg)

    def test_unknown_type_and_missing_runas(self):
        with self.assertRaises(CtmError) as e:
            ctm().build({"F": {"Type": "Folder", "Host": "ajan1", "J": {"Type": "Job:Command", "Command": "x"},
                               "K": {"Type": "Job:Hadoop", "Command": "x"}}})
        self.assertIn("RunAs", str(e.exception))
        self.assertIn("Job:Hadoop", str(e.exception))

    def test_flow_becomes_events(self):
        consume, keep, post = ctm()._events("GUNSONU", FOLDER["GUNSONU"])
        self.assertEqual(post["URET"], ["URET-TO-GONDER"])
        self.assertEqual(consume["GONDER"], ["URET-TO-GONDER"])
        self.assertEqual(keep["GONDER"], [])

    def test_variables_resolve_at_order_time(self):
        c = ctm()
        import datetime
        c.state["folders"].update(FOLDER)
        spec = c._spec("GUNSONU", "GONDER", "0001", datetime.date(2026, 11, 16), 1)
        self.assertEqual(spec["FileTransfers"][0]["Src"], "/a/x_20261116.csv")
        self.assertEqual(spec["RunAs"], "batch")
        c.state["folders"]["GUNSONU"]["GONDER"]["FileTransfers"][0]["Src"] = "/a/x_%%ODATE.csv"
        self.assertEqual(c._spec("GUNSONU", "GONDER", "0001", datetime.date(2026, 11, 16), 1)["FileTransfers"][0]["Src"], "/a/x_261116.csv")

    def test_cli_reports_errors_as_text(self):
        out = ctm().cli("run job::rerun saha:99999")
        self.assertTrue(out.startswith("HATA"))
        self.assertTrue(ctm().cli("olmayan komut").startswith("HATA"))


class Judge(unittest.TestCase):
    def test_diff_subset_regex_and_lists(self):
        have = {"Type": "Job:FileTransfer", "Host": "ajan1", "FileTransfers": [{"Src": "/d/satis_%%$ODATE.csv", "Dest": "/in/"}]}
        self.assertEqual(senaryo._diff({"Type": "job:filetransfer", "FileTransfers": [{"Src": r"~satis_%%\$ODATE\.csv$"}]}, have), [])
        self.assertTrue(senaryo._diff({"FileTransfers": [{"Src": r"~satis_%%ODATE\.csv$"}]}, have))
        self.assertTrue(senaryo._diff({"Host": "ajan2"}, have))
        self.assertTrue(senaryo._diff({"RunAs": "batch"}, have))

    def test_every_scenario_is_well_formed(self):
        for split in ("dev", "test"):
            for s in senaryo.yukle(split):
                self.assertEqual(senaryo.dogrula_bicim(s), [], s.get("id"))
                self.assertTrue(s.get("cozum"), f"{s['id']}: referans cozum yok")
                self.assertNotIn("{GUN}", json.dumps(s))

    def test_scenario_ids_are_unique(self):
        ids = [s["id"] for split in ("dev", "test") for s in senaryo.yukle(split)]
        self.assertEqual(len(ids), len(set(ids)))


class Guard(unittest.TestCase):
    def setUp(self):
        class A:  # the guard needs no tools for these checks
            dis = set()
            iz = []
        self.u = usta.Usta.__new__(usta.Usta)
        self.u.a, self.u.talep, self.u.onay, self.u.cagri, self.u.dagitilan = A(), "is NOTOK bitti", set(), {}, set()
        self.u.sayac = {"red": 0, "onay_istendi": 0}

    def sh(self, cmd):
        return self.u.once({"arac": "sh", "sunucu": "ajan1", "komut": cmd})

    def test_destructive_commands_are_refused(self):
        for cmd in ("rm -rf /data/dar/*", "rm -rf /data/giden", "psql -c 'truncate table satis'", "psql -c \"drop table satis\"",
                    "psql -c \"delete from satis\"", "chmod 777 /app/scripts/x.sh", "chmod -R 777 /data", "pkill -9 java",
                    "psql -c \"select pg_terminate_backend(pid) from pg_stat_activity\"", "rm /opt/ctm/cp/known_hosts",
                    "psql -c \"alter table satis drop constraint satis_pkey\"", "adduser finanss",
                    "psql -c \"alter role etl_user password 'x'\""):
            self.assertIn("REDDETTI", self.sh(cmd) or "", cmd)

    def test_safe_commands_pass(self):
        for cmd in ("ls -l /data/dar", "df -h", "chmod 600 /opt/ctm/keys/banka_key", "chmod 755 /app/scripts/x.sh",
                    "psql -U postgres -d uygulama -c \"select count(*) from satis where tarih = '20261116'\"",
                    "ssh-keygen -R dosya-sunucu -f /opt/ctm/cp/known_hosts", "chown batch:batch /app/scripts/x.sh",
                    "psql -c 'truncate satis_gecici'"):
            self.assertIsNone(self.sh(cmd), cmd)

    def test_risky_commands_need_a_second_call(self):
        cmd = "psql -U postgres -d uygulama -c \"delete from satis where tarih = '20261116'\""
        self.assertIn("onay", self.sh(cmd))
        self.assertIsNone(self.sh(cmd))
        self.assertIn("onay", self.sh("rm /data/dar/uygulama_20261001.log"))

    def test_set_to_ok_only_when_the_ticket_asks(self):
        act = {"arac": "ctm", "komut": "run job::setToOk saha:00001"}
        self.assertIn("REDDETTI", self.u.once(act))
        self.u.talep = "Bu isi bu gecelik set to OK yapin, kaynak sistem kapali."
        self.assertIsNone(self.u.once(act))


SITE = {
    "MUHASEBE_KAPANIS": {"Type": "Folder", "Host": "ajan1",
                         "KAPANIS_BASLAT": {"Type": "Job:Command", "Command": "true", "WaitForEvents": {"Events": [{"Event": "STOK_KAPANDI"}]}},
                         "KAPANIS_KONTROL": {"Type": "Job:Command", "Command": "true"},
                         "akis": {"Type": "Flow", "Sequence": ["KAPANIS_BASLAT", "KAPANIS_KONTROL"]}},
    "STOK_GUNSONU": {"Type": "Folder", "Host": "ajan1",
                     "STOK_KAPAT": {"Type": "Job:Command", "Command": "true", "AddEvents": {"Events": [{"Event": "STOK_KAPANDI"}]}}},
    "DEPO_SAYIM": {"Type": "Folder", "Host": "ajan2", "SAYIM_YUKLE": {"Type": "Job:Command", "Command": "false"}},
    "LOG_TEMIZLIK": {"Type": "Folder", "Host": "ajan2", "LOG_SIK": {"Type": "Job:Command", "Command": "true"}},
}


class Scope(unittest.TestCase):
    def test_event_graph_has_explicit_and_flow_events(self):
        veren, bekler = usta.olay_grafi(SITE)
        self.assertEqual(veren["STOK_KAPANDI"], ["STOK_GUNSONU/STOK_KAPAT"])
        self.assertEqual(veren["KAPANIS_BASLAT-TO-KAPANIS_KONTROL"], ["MUHASEBE_KAPANIS/KAPANIS_BASLAT"])
        self.assertIn("STOK_KAPANDI", bekler["MUHASEBE_KAPANIS/KAPANIS_BASLAT"])

    def test_ticket_words_match_names_with_suffixes(self):
        talep = "Mali isler sabahtan beri muhasebe kapanisini bekliyor; bugunku kapanis kaydi dusmedi."
        self.assertEqual(usta.ilgi(talep, "MUHASEBE_KAPANIS"), 2)
        self.assertEqual(usta.ilgi(talep, "DEPO_SAYIM"), 0)

    def test_scope_follows_the_event_upstream_into_another_folder(self):
        talep = "Muhasebe kapanisi bugun tamamlanmadi. Sitede baska isler de basarisiz; onlar bu talebin konusu degil."
        self.assertEqual(usta.kapsam_hesapla(talep, SITE), {"MUHASEBE_KAPANIS", "STOK_GUNSONU"})
        self.assertEqual(usta.kapsam_hesapla("Bir sorun var, bakar misiniz?", SITE), set())

    def test_wait_chain_names_the_failed_giver(self):
        rows = [{"folder": "MUHASEBE_KAPANIS", "name": "KAPANIS_BASLAT", "status": "Wait Condition", "waitingFor": {"events": ["STOK_KAPANDI"]}},
                {"folder": "STOK_GUNSONU", "name": "STOK_KAPAT", "status": "Ended Not OK"}]
        lines = usta.bekleme_zinciri(rows, SITE)
        self.assertEqual(len(lines), 1)
        self.assertIn("STOK_GUNSONU/STOK_KAPAT (Ended Not OK)", lines[0])

    def test_out_of_scope_change_and_hand_made_event_need_a_second_call(self):
        class Ctm:
            def cli(self, line):
                return json.dumps({"statuses": [
                    {"jobId": "saha:1", "folder": "DEPO_SAYIM", "name": "SAYIM_YUKLE", "status": "Ended Not OK"},
                    {"jobId": "saha:2", "folder": "STOK_GUNSONU", "name": "STOK_KAPAT", "status": "Ended Not OK"}]})

        class A:
            dis, iz, ctm = set(), [], Ctm()
        u = usta.Usta.__new__(usta.Usta)
        u.a, u.talep, u.onay, u.cagri, u.dagitilan = A(), "muhasebe kapanisi", set(), {}, set()
        u.sayac = {"red": 0, "onay_istendi": 0, "yoklama": 0}
        u.kapsam, u.tanimlar, u.dokunulan = {"MUHASEBE_KAPANIS", "STOK_GUNSONU"}, SITE, set()
        rerun = {"arac": "ctm", "komut": "run job::rerun saha:1"}
        self.assertIn("kapsaminda", u.once(rerun))
        self.assertIsNone(u.once(rerun))
        self.assertIsNone(u.once({"arac": "ctm", "komut": "run job::rerun saha:2"}))
        ev = {"arac": "ctm", "komut": "run event::add STOK_KAPANDI"}
        self.assertIn("elle", u.once(ev))
        self.assertIsNone(u.once(ev))


class UstaFlow(unittest.TestCase):
    """The whole harness path (triage, pre-flight, follow-up, gate, critic) against a fake site, to catch errors that
    only show at run time."""

    def setUp(self):
        profiles = {"SFTP_RAPOR": {"Type": "ConnectionProfile:FileTransfer:SFTP", "HostName": "dosya-sunucu", "User": "mftuser", "Password": "*****"},
                    "YEREL_BATCH": {"Type": "ConnectionProfile:FileTransfer:Local", "User": "batch"}}
        site = json.loads(json.dumps(SITE))
        site["ESKI_PAYLASIM"] = {"Type": "Folder", "Host": "ajan1", "ESKI_GONDER": {
            "Type": "Job:FileTransfer", "ConnectionProfileSrc": "YEREL_BATCH", "ConnectionProfileDest": "SFTP_RAPOR",
            "FileTransfers": [{"Src": "/data/giden/a.csv", "Dest": "/home/mftuser/in/"}]}}
        rows = [{"jobId": "saha:1", "folder": "MUHASEBE_KAPANIS", "name": "KAPANIS_BASLAT", "type": "Command", "host": "ajan1",
                 "status": "Wait Condition", "numberOfRuns": 0, "waitingFor": {"events": ["STOK_KAPANDI"]}},
                {"jobId": "saha:2", "folder": "STOK_GUNSONU", "name": "STOK_KAPAT", "type": "Command", "host": "ajan1",
                 "status": "Ended Not OK", "numberOfRuns": 1},
                {"jobId": "saha:3", "folder": "DEPO_SAYIM", "name": "SAYIM_YUKLE", "type": "Command", "host": "ajan2",
                 "status": "Ended Not OK", "numberOfRuns": 1}]

        class C:
            state = {"folders": site}

            def cli(self, line, body=None):
                if "jobs:status::get" in line:
                    return json.dumps({"statuses": rows})
                if line.startswith("deploy jobs::get"):
                    return json.dumps(site)
                if "connectionprofiles::get" in line:
                    return json.dumps(profiles)
                if "agents::get" in line:
                    return json.dumps([{"nodeid": "ajan1", "status": "Available"}])
                return "is ciktisi\nPermission denied"

            def build(self, body):
                return {k: v for k, v in body.items() if v.get("Type") == "Folder"}, {k: v for k, v in body.items() if "Profile" in v.get("Type", "")}

        class L:
            def sh(self, host, cmd, timeout=40):
                if "find /app" in cmd:
                    return 0, "/app/STANDARTLAR.txt"
                if cmd.startswith("head -c"):
                    return 0, "1. Her iste Description yazilir."
                return 0, "var\ncalisir"

        class A:
            dis, iz = {"dosya-sunucu"}, []
            ctm, lab = C(), L()

            def cagir(self, eylem, kayit=True):
                return self.ctm.cli(eylem["komut"])

        class M:
            def __init__(self):
                self.calls = 0

            def ask_json(self, messages):
                self.calls += 1
                return {"maddeler": ["kapanis kaydi bugun icin 12 kalem"]} if "kabul maddelerine" in messages[-1]["content"] else {"eksik": []}
        self.critic = M()
        self.u = usta.Usta(A(), "Muhasebe kapanisi bugun dusmedi. Sitede baska isler de basarisiz; onlar bu talebin konusu degil.", elestirmen=self.critic)

    def test_triage_gate_and_preflight(self):
        pack = self.u.baslangic(self.u.talep)
        self.assertIn("STOK_GUNSONU/STOK_KAPAT (Ended Not OK)", pack)
        self.assertIn("Kabul listesi", pack)
        self.assertNotIn("Site standartlari", pack)          # not a definition request
        gate = self.u.bitis("Kok neden bulundu, betik duzeltildi, is yeniden calisti ve dogrulandi; kayit tabloda 12 satir.", {})
        self.assertIn("STOK_KAPAT", gate)
        self.assertNotIn("SAYIM_YUKLE", gate)                 # another team's failure is not this ticket's work
        body = {"RAPOR_DAGITIM": {"Type": "Folder", "Host": "ajan1", "RunAs": "batch", "OZET_GONDER": {
            "Type": "Job:FileTransfer", "ConnectionProfileSrc": "YEREL_BATCH", "ConnectionProfileDest": "SFTP_RAPOR",
            "FileTransfers": [{"Src": "/data/giden/ozet.csv", "Dest": "/home/rapor/in/"}]}}}
        stop = self.u.once({"arac": "ctm", "komut": "deploy", "json": body})
        self.assertIn("mftuser", stop)
        prof = {"SFTP_RAPOR": {"Type": "ConnectionProfile:FileTransfer:SFTP", "HostName": "dosya-sunucu", "User": "rapor", "Password": "x"}}
        stop = self.u.once({"arac": "ctm", "komut": "deploy", "json": prof})
        self.assertIn("ESKI_PAYLASIM/ESKI_GONDER", stop)
        self.u.elestirmen = self.critic
        self.u.sayac["elestiri"] = 0
        self.assertEqual(self.u._elestir("rapor"), [])


class Analysis(unittest.TestCase):
    def test_budget_is_read_from_the_run_name(self):
        from vardiya.saha import analiz
        self.assertEqual(analiz.butce_adi("test-flash-low-b10"), 10)
        self.assertEqual(analiz.butce_adi("test-flash-low-b15"), 15)
        self.assertEqual(analiz.butce_adi("test-flash-low"), 40)

    def test_sign_test(self):
        from vardiya.saha import analiz
        self.assertEqual(analiz.isaret_testi(0, 0), 1.0)
        self.assertAlmostEqual(analiz.isaret_testi(6, 0), 2 / 64)
        self.assertAlmostEqual(analiz.isaret_testi(3, 3), 1.0)


class Cards(unittest.TestCase):
    def test_cards_load_and_signatures_compile(self):
        cards = usta.kartlar()
        self.assertGreaterEqual(len(cards), 15)
        for k in cards:
            for pat in k["imza"]:
                re.compile(pat)
            self.assertTrue(k["cozum"] and k["dogrula"] and k["yapma"], k["id"])

    def test_signatures_pick_the_right_card(self):
        u = usta.Usta.__new__(usta.Usta)
        u.kartlar = usta.kartlar()
        pick = lambda text: [k["id"] for k in u._eslesen(text)]  # noqa: E731
        self.assertEqual(pick("mftuser@dosya-sunucu: Permission denied (publickey,password,keyboard-interactive).")[0], "sftp-kimlik")
        self.assertIn("sftp-anahtar", pick("WARNING: UNPROTECTED PRIVATE KEY FILE!"))
        self.assertIn("db-mukerrer", pick('ERROR:  duplicate key value violates unique constraint "satis_pkey"'))
        self.assertIn("aft-kaynak-yok", pick("CTM5322 kaynakta eslesen dosya yok: /data/giden/satis_261116.csv"))
        self.assertIn("disk-dolu", pick("tar: write error: No space left on device"))

    def test_cards_do_not_name_bench_scenarios(self):
        text = json.dumps(usta.kartlar(), ensure_ascii=False)
        for word in ("GUNSONU", "SATIS_YUKLEME", "BANKA_GONDERIM", "MUTABAKAT", "RAPORLAMA", "Mft-2026", "Etl-2026", "rapor_araci"):
            self.assertNotIn(word, text)

    def test_handbook_documents_every_tool(self):
        for word in ('"arac": "ctm"', '"arac": "sh"', '"arac": "bitir"', "run job::rerun", "deploy connectionprofile::test", "runjob.py ls"):
            self.assertIn(word, EL_KITABI)


if __name__ == "__main__":
    unittest.main()
