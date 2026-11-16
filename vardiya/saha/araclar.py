"""The tools an admin agent has on the live lab, and the handbook that documents them.

Both arms get exactly these tools and this handbook: the unaided model and the harnessed one reach the same data.
Every call is recorded with its input, exit code and output; that record is the evidence of what was really done.
"""
import json
import time

from .ctm import CtmError

EL_KITABI = """\
# Saha el kitabi (bu ortamda nasil calisilir)

Sen bu sitenin Control-M yoneticisisin. Ortam gercek: isler gercek sunucularda calisir, dosyalar gercekten aktarilir,
veritabani gercektir. Zamanlayici Control-M Automation API sozdizimini konusur (uyumlu bir alt kume).

## Sunucular
- ajan1, ajan2: islerin calistigi ajan sunuculari (Linux). Is hesaplari: batch, etl, finans, mft. Ajan sureci
  `jobscheduler` hesabiyla calisir. Dizinler: /data/gelen, /data/giden, /data/arsiv, /data/dar (kucuk disk bolumu),
  /app/scripts, /app/sql, /var/log/app. Baglanti profilleri /opt/ctm/cp, SSH anahtarlari /opt/ctm/keys altinda.
  Ajan servisi: `ctmag status|start|stop|restart` (root). Ajan durursa sunucu ayakta kalir, isler Wait Host'ta bekler.
  Servis gunlugu /var/log/ctmagent.log, ayar /etc/ctm/ajan.conf, ajanin kendi gunlukleri /var/sos-berlin.com/js7/agent/logs.
- dosya-sunucu: karsi taraf SFTP sunucusu. Hesaplar: mftuser (parola), banka (yalnizca anahtar), rapor (parola).
  Her hesabin evinde in/, out/, arsiv/ dizinleri vardir.
  Karsi dizini bir profille listelemek icin (kabuk erisimin olmasa da): sh ajan1 "python3 /opt/ctm/bin/runjob.py ls PROFIL /dizin"
- appdb: PostgreSQL, veritabani `uygulama`. Yonetici olarak: sh appdb "psql -U postgres -d uygulama -c '...'".
  Uygulama hesaplari: etl_user (yazar), rapor_user (yalnizca okur).

## Araclar (her adimda TEK bir JSON nesnesiyle bir arac cagir)
1. {"arac": "ctm", "komut": "<ctm komut satiri>"}  ve tanim dagitirken  {"arac": "ctm", "komut": "deploy", "json": {...}}
2. {"arac": "sh", "sunucu": "ajan1|ajan2|dosya-sunucu|appdb", "komut": "<kabuk komutu>"}   (root olarak calisir, 60 sn sinir)
3. {"arac": "bitir", "rapor": "<ne buldun, ne yaptin, nasil dogruladin>"}   (isi kapatir; sonrasinda arac cagiramazsin)

## ctm komutlari
- build  /  deploy                       "json" alanindaki tanimi dogrular / dagitir (klasor butun olarak degisir)
- deploy jobs::get -s "folder=AD"        dagitilmis tanimlari getirir
- deploy folder::delete AD
- deploy connectionprofiles::get [-s "name=AD"]     (parolalar gizlenir)
- deploy connectionprofile::test AD [ajan]          profili ajandan dener (SFTP girisi, veritabani girisi)
- deploy connectionprofile::delete AD
- run order KLASOR [IS]                  klasoru ya da tek isi siparis eder; jobId'leri dondurur
- run jobs:status::get [-s "folder=AD&jobname=AD&status=Ended Not OK"]
- run job:status::get JOBID  |  run job:output::get JOBID [-s "runNo=2"]  |  run job:log::get JOBID
- run job:waitingInfo::get JOBID         is neden bekliyor
- run job::rerun JOBID | run job::hold JOBID | run job::free JOBID | run job::kill JOBID
- run job::setToOk JOBID                 isi CALISTIRMADAN yesile ceker ve ardillarini serbest birakir
- run job::delete JOBID                  isi aktif ortamdan siler
- run event::add AD | run event::delete AD | run events::get
- config server:agents::get | config server:agent::ping AJAN

Durumlar: Wait Condition, Wait Host, Executing, Ended OK, Ended Not OK. Siparis edilen is, siparis anindaki tanimin
KOPYASIDIR: tanimi sonradan duzeltip dagitmak aktif isi degistirmez (yeniden siparis gerekir). Baglanti profilleri ise
calisma aninda okunur: profili duzeltip isi yeniden calistirmak yeterlidir.

## Tanim bicimi (Automation API JSON)
{"KLASOR": {"Type": "Folder", "Host": "ajan1", "RunAs": "batch", "Variables": [{"AD": "deger"}],
   "IS1": {"Type": "Job:Command", "Command": "echo %%$ODATE", "RunAs": "etl"},
   "IS2": {"Type": "Job:Script", "FilePath": "/app/scripts", "FileName": "x.sh", "Arguments": ["a"]},
   "IS3": {"Type": "Job:FileTransfer", "ConnectionProfileSrc": "YEREL_BATCH", "ConnectionProfileDest": "SFTP_KARSI",
           "FileTransfers": [{"Src": "/data/giden/a_*.csv", "Dest": "/home/mftuser/in/", "TransferType": "Binary",
                              "TransferOption": "SrcToDest"}]},
   "IS4": {"Type": "Job:Database:SQLScript", "ConnectionProfile": "PG_UYG", "SQLScript": "/app/sql/x.sql",
           "Parameters": [{"gun": "%%$ODATE"}]},
   "IS5": {"Type": "Job:Database:EmbeddedQuery", "ConnectionProfile": "PG_UYG", "Query": "select 1", "Autocommit": "N"},
   "akis": {"Type": "Flow", "Sequence": ["IS1", "IS2", "IS3"]}}}
- Diger is tipleri: Job:Database:StoredProcedure (StoredProcedure, Schema, Parameters), Job:FileWatcher:Create (Path,
  TimeLimit dakika, SearchInterval saniye, MinDetectedSize), Job:Dummy.
- Aktarim secenekleri: TransferOption SrcToDest|DestToSrc; TransferType Binary|Ascii; IF_EXIST 0 uzerine yaz, 2 durdur,
  3 atla; SRCOPT 0 birak, 1 sil, 2 yeniden adlandir, 3 tasi (SRCNAME hedef ad/dizin); DSTOPT 1 gecici adla yazip
  sonunda adlandir; FailJobOnSourceMissing 0 kaynak yoksa hata sayma. Src son parcasi joker (*, ?) icerebilir.
- Olaylar: "WaitForEvents"/"AddEvents"/"DeleteEvents": {"Type": "...", "Events": [{"Event": "AD"}]}. Flow, A-TO-B adli
  olayi kendisi kurar; ardil is OK bitince bu olayi siler.
- Yeniden deneme: "Rerun": {"Times": "2", "Interval": "1", "Units": "Minutes"}.
- Degiskenler: %%ODATE (YYMMDD), %%$ODATE (YYYYMMDD), %%JOBNAME, %%ORDERID ve Variables icindeki adlar.
- Baglanti profilleri: ConnectionProfile:FileTransfer:SFTP (HostName, Port, User, Password ya da PrivateKeyName),
  ConnectionProfile:FileTransfer:Local (User), ConnectionProfile:Database:PostgreSQL (Host, Port, User, Password,
  DatabaseName). Mevcut profiller: SFTP_KARSI, SFTP_BANKA, YEREL_BATCH, YEREL_ETL, PG_UYG, PG_RAPOR.
"""

OUT_CAP = 3500


class Araclar:
    def __init__(self, lab, ctm, dis_sunucu=()):
        self.lab, self.ctm, self.dis = lab, ctm, set(dis_sunucu)
        self.iz = []

    def _kayit(self, arac, girdi, cikti, rc=0, uygulandi=True, sn=0.0):
        self.iz.append({"n": len(self.iz) + 1, "arac": arac, "girdi": girdi, "rc": rc, "uygulandi": uygulandi,
                        "sn": round(sn, 1), "cikti": cikti[:6000]})
        return cikti

    def cagir(self, eylem, kayit=True):
        """Run one tool action. Returns the text the agent sees. Unknown or malformed actions get a teaching error."""
        t0 = time.time()
        if not isinstance(eylem, dict) or eylem.get("arac") not in ("ctm", "sh"):
            return 'HATA: gecerli araclar "ctm", "sh" ve "bitir". Ornek: {"arac": "ctm", "komut": "run jobs:status::get"}'
        if eylem["arac"] == "ctm":
            line = str(eylem.get("komut", "")).strip()
            body = eylem.get("json")
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except ValueError as e:
                    return self._kayit("ctm", eylem, f"HATA: json alani okunamadi: {e}", 1, False) if kayit else f"HATA: {e}"
            out = self.ctm.cli(line, body)
            rc = 1 if out.startswith("HATA") else 0
        else:
            host, cmd = eylem.get("sunucu"), str(eylem.get("komut", ""))
            if host in self.dis:
                out, rc = f"HATA: {host} karsi kuruma aittir; bu sunucuda kabuk erisiminiz yok.", 1
                return self._kayit("sh", eylem, out, rc, False) if kayit else out
            try:
                rc, text = self.lab.sh(host, cmd, timeout=60)
            except KeyError as e:
                rc, text = 1, f"HATA: {e.args[0]}"
            out = f"[cikis kodu {rc}]\n{text.rstrip()}"
        out = _kisalt(out)
        return self._kayit(eylem["arac"], {k: v for k, v in eylem.items() if k != "arac"}, out, rc, True, time.time() - t0) if kayit else out


def _kisalt(text, cap=OUT_CAP):
    if len(text) <= cap:
        return text
    head, tail = text[:cap // 3], text[-(2 * cap // 3):]
    return f"{head}\n... ({len(text) - cap} karakter kisaltildi) ...\n{tail}"
