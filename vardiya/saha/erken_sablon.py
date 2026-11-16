"""Precursor scenarios for the live lab: a site that still WORKS but carries seeded risks.

A scenario is data (bench/saha/erken/<split>/*.json):

    {"id": "ed-01", "bolum": "dev|test", "gecmis": 16,
     "bilesenler": [{"tur": "disk_dolu", ...parameters...}, ...]}

Every component is one risk or one look-alike that must NOT be flagged ("tuzak"). The site is built on the live lab:
real jobs run `gecmis` times on the real scheduler (so the scheduler's own history shows the trend), then the
final risk state is put in place (a role gets an end date, a key an expiry, a session keeps a lock), and the
ground truth is computed from what the lab really looks like then.

Risk classes (the vocabulary the models are asked to use):
    disk_dolu         a volume the job writes to fills a little with every run
    hesap_suresi      the validity of a database role a job connects with ends
    anahtar_suresi    a key the job logs in with is valid only until a time
    sure_asimi        the job takes longer every run and nears the time limit written in its command
    tekrarlayan_hata  an intermittent error that comes back more often
    kilit_bekleme     an open transaction holds a lock on a table the next load needs
    birikim           the backlog in a source directory grows past the limit the script enforces
"""
import datetime
import json
import re
import time

from . import ortam
from .ctm import FINAL

SINIFLAR = {
    "disk_dolu": "bir isin yazdigi disk bolumu her calismada biraz daha doluyor, dolunca is yazamaz",
    "hesap_suresi": "isin baglandigi veritabani hesabinin gecerlilik suresi bitiyor, bitince giris reddedilir",
    "anahtar_suresi": "isin giris yaptigi anahtarin gecerlilik suresi bitiyor, bitince giris reddedilir",
    "sure_asimi": "is her calismada biraz daha uzuyor ve komutundaki sure sinirina yaklasiyor, asinca oldurulur",
    "tekrarlayan_hata": "aralikli bir hata giderek sikilasiyor, sonunda is surekli duser",
    "kilit_bekleme": "acik duran bir islem, sonraki yuklemenin yazacagi tabloyu kilitli tutuyor, yukleme takilir",
    "birikim": "kaynak dizinde dosya birikiyor, scriptin kontrol ettigi siniri asinca is hata verir",
}
KOMPONENTLER = tuple(SINIFLAR) + ("t_disk_durgun", "t_yavas", "t_tek_hata", "t_hesap_uzak", "t_anahtar_uzak", "t_oturum",
                                  "t_birikim_durgun")
DISK_KB = 4096          # the /data/dar volumes of the agents are 4 MB tmpfs
HIST = 16               # runs of history a site gets by default

ROL_PROFIL = {"etl_user": "PG_UYG", "rapor_user": "PG_RAPOR"}
EK_PROFILLER = {"SFTP_RAPOR_ANAHTAR": {"Type": "ConnectionProfile:FileTransfer:SFTP", "HostName": "dosya-sunucu", "Port": "22",
                                       "User": "rapor", "PrivateKeyName": "banka_key"}}
HESAP_PROFIL = {"banka": "SFTP_BANKA", "rapor": "SFTP_RAPOR_ANAHTAR"}


def _tmpl(text, **kv):
    for k, v in kv.items():
        text = text.replace("@" + k.upper() + "@", str(v))
    return text


# ---------------------------------------------------------------------------------------------------- scripts
S_DISK = """#!/bin/sh
# @IS@: uretim ciktisini @VOL@ altina ekler ve bolumun doluluk satirini yazar
f=@VOL@/@IS@.dat
dd if=/dev/zero bs=1024 count=@ADIM@ >> "$f" 2>/tmp/saha-@IS@.err || { echo "yazma hatasi: $f: $(tail -1 /tmp/saha-@IS@.err)" >&2; exit 1; }
echo "yazildi: @ADIM@ KB -> $f"
df -Pk @VOL@ | tail -1 | awk '{print "df: @VOL@ kullanilan_kb=" $3 " toplam_kb=" $2}'
"""
S_SURE = """#!/bin/sh
# @IS@: rapor hazirlar
n=$(cat /var/log/app/@IS@.n 2>/dev/null || echo 0); n=$((n + 1)); echo $n > /var/log/app/@IS@.n
d=$((@TABAN@ + n / @HER@))
echo "kosu $n basladi (rapor hazirlaniyor)"
sleep $d
echo "kosu $n bitti"
"""
S_HATA = """#!/bin/sh
# @IS@: karsi servise baglanip veriyi alir
n=$(cat /var/log/app/@IS@.n 2>/dev/null || echo 0); n=$((n + 1)); echo $n > /var/log/app/@IS@.n
case " @LISTE@ " in *" $n "*) echo "@HATA@" >&2; exit 1;; esac
if [ $n -ge @SERT@ ]; then echo "@HATA@" >&2; exit 1; fi
echo "alindi (kosu $n)"
"""
S_BIRIKIM = """#!/bin/sh
# @IS@: gelen dosyalari isler. Bekleyen dosya sayisi LIMIT'i asarsa durur.
LIMIT=@SINIR@
d=/data/gelen/@IS@; mkdir -p $d
n=$(cat /var/log/app/@IS@.n 2>/dev/null || echo 0); n=$((n + 1)); echo $n > /var/log/app/@IS@.n
i=0; while [ $i -lt @EKLE@ ]; do : > "$d/d$(printf '%06d' $n)_$i"; i=$((i + 1)); done
ls -1 $d | sort | head -n @TUKET@ | while read f; do rm -f "$d/$f"; done
N=$(ls -1 $d | wc -l)
echo "bekleyen_dosya: $N (sinir $LIMIT)"
if [ $N -gt $LIMIT ]; then echo "HATA: bekleyen dosya sayisi sinirin ustunde ($N > $LIMIT)" >&2; exit 3; fi
"""
S_YAVAS = """#!/bin/sh
# @IS@: agir rapor, hep ayni surede biter
echo "basladi"
sleep @SN@
echo "bitti"
"""

HATA_METINLERI = [
    "ERROR: karsi servis baglantisi koptu: Connection reset by peer (deneme 3/3)",
    "ERROR: TLS el sikisma zaman asimi: rapor-gw:443",
    "ERROR: ORA-00054: resource busy and acquire with NOWAIT specified or timeout expired",
    "ERROR: karsi tarafin SFTP hizmeti yanit vermedi: Connection timed out",
]


# ---------------------------------------------------------------------------------------------------- components
def _klasor(p, host, ad, isler):
    return {"Type": "Folder", "Host": host, "RunAs": "batch", **isler}


def _betik_is(p, host, ad, betik, **extra):
    return {"Type": "Job:Script", "FilePath": "/app/scripts", "FileName": f"{ad.lower()}.sh", **extra}


class Parca:
    """What one component adds to the site: folders, extra profiles, files, a final step and its truth."""
    def __init__(self, p):
        self.p = p
        self.klasorler, self.profiller = {}, {}
        self.dosyalar = []      # (host, path, content, owner, mode)
        self.once = []          # shell steps (host, cmd) before the history runs
        self.son = []           # callables(ctx) after the history runs
        self.gercek = None      # callable(ctx) -> dict of the truth, set by kur_*


def _id(p):
    return f"{p['klasor']}/{p['is']}"


def parca(p):
    return globals()["_k_" + p["tur"]](Parca(p))


def _k_disk_dolu(x):
    p = x.p
    ad, vol, host = p["is"], "/data/dar", p["host"]
    x.dosyalar.append((host, f"/app/scripts/{ad.lower()}.sh", _tmpl(S_DISK, is_=ad, IS=ad, VOL=vol, ADIM=p["adim_kb"]), "batch:batch", "0755"))
    x.klasorler[p["klasor"]] = {"Type": "Folder", "Host": host, "RunAs": "batch",
                                ad: {"Type": "Job:Script", "FilePath": "/app/scripts", "FileName": f"{ad.lower()}.sh"}}
    if p.get("onceki_kb"):
        x.once.append((host, f"dd if=/dev/zero bs=1024 count={p['onceki_kb']} > {vol}/eski_cikti.dat 2>/dev/null; chmod 666 {vol}/eski_cikti.dat"))

    def gercek(ctx):
        rc, out = ctx.lab.sh(host, f"df -Pk {vol} | tail -1")
        f = out.split()
        bos = int(f[3]) if len(f) > 3 else 0
        kalan = bos // p["adim_kb"]
        return {"is": _id(p), "sinif": "disk_dolu", "son": {"tur": "kosu", "n": kalan + 1},
                "kaynak": f"{host}:{vol}", "ayrinti": {"bos_kb": bos, "adim_kb": p["adim_kb"]}}
    x.gercek = gercek
    return x


def _k_sure_asimi(x):
    p = x.p
    ad = p["is"]
    x.dosyalar.append((p["host"], f"/app/scripts/{ad.lower()}.sh", _tmpl(S_SURE, IS=ad, TABAN=p["taban_sn"], HER=p["her_kac"]), "batch:batch", "0755"))
    x.klasorler[p["klasor"]] = {"Type": "Folder", "Host": p["host"], "RunAs": "batch",
                                ad: {"Type": "Job:Command", "Command": f"timeout {p['limit_sn']} /app/scripts/{ad.lower()}.sh"}}

    def gercek(ctx):
        # run n sleeps taban + n // her seconds; it is killed when that exceeds the limit
        n = ctx.gecmis
        ilk = next(k for k in range(n + 1, n + 400) if p["taban_sn"] + k // p["her_kac"] > p["limit_sn"])
        return {"is": _id(p), "sinif": "sure_asimi", "son": {"tur": "kosu", "n": ilk - n}, "kaynak": "sure",
                "ayrinti": {"limit_sn": p["limit_sn"]}}
    x.gercek = gercek
    return x


def _k_tekrarlayan_hata(x):
    p = x.p
    ad = p["is"]
    x.dosyalar.append((p["host"], f"/app/scripts/{ad.lower()}.sh",
                       _tmpl(S_HATA, IS=ad, LISTE=" ".join(str(k) for k in p["hata_kosular"]), SERT=p["sert_kosu"],
                             HATA=HATA_METINLERI[p["hata_no"] % len(HATA_METINLERI)]), "batch:batch", "0755"))
    x.klasorler[p["klasor"]] = {"Type": "Folder", "Host": p["host"], "RunAs": "batch",
                                ad: {"Type": "Job:Script", "FilePath": "/app/scripts", "FileName": f"{ad.lower()}.sh"}}
    x.gercek = lambda ctx: {"is": _id(p), "sinif": "tekrarlayan_hata", "son": {"tur": "kosu", "n": p["sert_kosu"] - ctx.gecmis},
                            "kaynak": "hata imzasi", "ayrinti": {"hata_kosular": p["hata_kosular"]}}
    return x


def _k_birikim(x, durgun=False):
    p = x.p
    ad = p["is"]
    x.dosyalar.append((p["host"], f"/app/scripts/{ad.lower()}.sh",
                       _tmpl(S_BIRIKIM, IS=ad, SINIR=p["sinir"], EKLE=p["ekle"], TUKET=p["tuket"]), "batch:batch", "0755"))
    x.klasorler[p["klasor"]] = {"Type": "Folder", "Host": p["host"], "RunAs": "batch",
                                ad: {"Type": "Job:Script", "FilePath": "/app/scripts", "FileName": f"{ad.lower()}.sh"}}
    x.once.append((p["host"], f"d=/data/gelen/{ad}; mkdir -p $d; i=0; while [ $i -lt {p['baslangic']} ]; do : > $d/a$(printf '%06d' $i); "
                              f"i=$((i+1)); done; chown -R batch:batch $d"))

    def gercek(ctx):
        artis = p["ekle"] - p["tuket"]
        simdi = p["baslangic"] + ctx.gecmis * artis
        return {"is": _id(p), "sinif": "birikim", "son": {"tur": "kosu", "n": (p["sinir"] - simdi) // max(artis, 1) + 1},
                "kaynak": f"{p['host']}:/data/gelen/{ad}", "ayrinti": {"simdi": simdi, "sinir": p["sinir"]}}
    x.gercek = None if durgun else gercek
    return x


def _k_hesap_suresi(x):
    p = x.p
    rol, ad = p["rol"], p["is"]
    x.klasorler[p["klasor"]] = {"Type": "Folder", "Host": p["host"], "RunAs": "batch",
                                ad: {"Type": "Job:Database:EmbeddedQuery", "ConnectionProfile": ROL_PROFIL[rol],
                                     "Query": "select count(*) from satis"}}

    def son(ctx):
        t = ctx.simdi + p["bitis_dk"] * 60 if "bitis_dk" in p else ctx.simdi + p["bitis_saat"] * 3600
        ts = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S+00")
        ctx.lab.sql(f"alter role {rol} valid until '{ts}'")
        ctx.sahne[ad] = t
    x.son.append(son)
    x.gercek = lambda ctx: {"is": _id(p), "sinif": "hesap_suresi", "son": {"tur": "saat", "t": ctx.sahne[p["is"]]},
                            "kaynak": f"rol:{rol}", "ayrinti": {}}
    return x


def _k_anahtar_suresi(x):
    p = x.p
    hesap, ad = p.get("hesap", "banka"), p["is"]
    prof = HESAP_PROFIL[hesap]
    if hesap in ("rapor",):
        x.profiller[prof] = EK_PROFILLER[prof]
    x.dosyalar.append((p["host"], f"/data/giden/{ad.lower()}_gunluk.csv", "id,tutar\n1,10\n2,20\n", "batch:batch", "0664"))
    x.klasorler[p["klasor"]] = {"Type": "Folder", "Host": p["host"], "RunAs": "batch",
                                ad: {"Type": "Job:FileTransfer", "ConnectionProfileSrc": "YEREL_BATCH", "ConnectionProfileDest": prof,
                                     "FileTransfers": [{"Src": f"/data/giden/{ad.lower()}_*.csv", "Dest": f"/home/{hesap}/in/",
                                                        "TransferType": "Binary", "TransferOption": "SrcToDest", "DSTOPT": "1"}]}}

    def son(ctx):
        t = ctx.simdi + p["bitis_dk"] * 60 if "bitis_dk" in p else ctx.simdi + p["bitis_saat"] * 3600
        stamp = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
        _, pub = ctx.lab.sh("ajan1", "cat /opt/ctm/keys/banka_key.pub")
        pub = pub.strip()
        ctx.lab.sh("dosya-sunucu", f"printf 'expiry-time=\"{stamp}Z\" %s\\n' \"$(cat)\" > /home/{hesap}/.ssh/authorized_keys && "
                                   f"chown {hesap}:{hesap} /home/{hesap}/.ssh/authorized_keys && chmod 600 /home/{hesap}/.ssh/authorized_keys",
                   stdin=pub)
        ctx.sahne[ad] = t
    x.son.append(son)
    x.gercek = lambda ctx: {"is": _id(p), "sinif": "anahtar_suresi", "son": {"tur": "saat", "t": ctx.sahne[p["is"]]},
                            "kaynak": f"anahtar:{hesap}", "ayrinti": {}}
    return x


def _k_kilit_bekleme(x):
    p = x.p
    ad, tablo = p["is"], p["tablo"]
    x.klasorler[p["klasor"]] = {"Type": "Folder", "Host": p["host"], "RunAs": "batch",
                                ad: {"Type": "Job:Database:EmbeddedQuery", "ConnectionProfile": "PG_UYG",
                                     "Query": f"truncate {tablo}", "Description": f"Gece yuklemesi ({p['saat']})",
                                     "When": {"FromTime": p["saat"].replace(":", ""), "ToTime": "0400"}}}

    def son(ctx):
        _oturum(ctx, p["host"], "etl_user", f"begin; lock table {tablo} in access exclusive mode;")
    x.son.append(son)

    def gercek(ctx):
        h, m = (int(v) for v in p["saat"].split(":"))
        return {"is": _id(p), "sinif": "kilit_bekleme", "son": {"tur": "planli", "saat": p["saat"]}, "kaynak": f"tablo:{tablo}",
                "ayrinti": {}}
    x.gercek = gercek
    return x


def _oturum(ctx, host, kullanici, sql):
    """A database session that runs `sql` and then stays open and idle (marked, so the site reset ends it)."""
    pw = ortam.DB_USERS[kullanici]
    sayim = f"select count(*) from pg_stat_activity where usename='{kullanici}' and state like 'idle in%'"
    onceki = int(ctx.lab.sql(sayim)[0][0])
    cmd = (f"(echo {json.dumps(sql)}; sleep 86400) | PGPASSWORD={pw} psql -h appdb -U {kullanici} -d uygulama -X -q")
    ctx.lab.sh(host, f"SAHA_ARIZA=1 nohup sh -c {json.dumps(cmd)} >/dev/null 2>&1 &")
    for _ in range(20):
        time.sleep(0.5)
        if int(ctx.lab.sql(sayim)[0][0]) > onceki:
            return
    raise RuntimeError("acik islem oturumu kurulamadi")


# ---- look-alikes (must not be flagged)
def _k_t_disk_durgun(x):
    """A volume that is full but static, and no job writes to it."""
    p = x.p
    x.once.append((p["host"], f"dd if=/dev/zero bs=1024 count={p['dolu_kb']} > /data/dar/eski_arsiv.dat 2>/dev/null; chmod 666 /data/dar/eski_arsiv.dat"))
    x.gercek = None
    return x


def _k_t_yavas(x):
    p = x.p
    ad = p["is"]
    x.dosyalar.append((p["host"], f"/app/scripts/{ad.lower()}.sh", _tmpl(S_YAVAS, IS=ad, SN=p["sn"]), "batch:batch", "0755"))
    x.klasorler[p["klasor"]] = {"Type": "Folder", "Host": p["host"], "RunAs": "batch",
                                ad: {"Type": "Job:Command", "Command": f"timeout {p['limit_sn']} /app/scripts/{ad.lower()}.sh"}}
    x.gercek = None
    return x


def _k_t_tek_hata(x):
    p = x.p
    ad = p["is"]
    x.dosyalar.append((p["host"], f"/app/scripts/{ad.lower()}.sh",
                       _tmpl(S_HATA, IS=ad, LISTE=str(p["hata_kosu"]), SERT=9999, HATA=HATA_METINLERI[p["hata_no"] % len(HATA_METINLERI)]),
                       "batch:batch", "0755"))
    x.klasorler[p["klasor"]] = {"Type": "Folder", "Host": p["host"], "RunAs": "batch",
                                ad: {"Type": "Job:Script", "FilePath": "/app/scripts", "FileName": f"{ad.lower()}.sh"}}
    x.gercek = None
    return x


def _k_t_hesap_uzak(x):
    p = x.p
    rol, ad = p["rol"], p["is"]
    x.klasorler[p["klasor"]] = {"Type": "Folder", "Host": p["host"], "RunAs": "batch",
                                ad: {"Type": "Job:Database:EmbeddedQuery", "ConnectionProfile": ROL_PROFIL[rol],
                                     "Query": "select count(*) from satis"}}
    x.son.append(lambda ctx: ctx.lab.sql(
        f"alter role {rol} valid until '{(datetime.date.today() + datetime.timedelta(days=p['gun'])).isoformat()} 00:00:00+00'"))
    x.gercek = None
    return x


def _k_t_anahtar_uzak(x):
    p = x.p
    hesap, ad = p.get("hesap", "rapor"), p["is"]
    prof = HESAP_PROFIL[hesap]
    if hesap == "rapor":
        x.profiller[prof] = EK_PROFILLER[prof]
    x.dosyalar.append((p["host"], f"/data/giden/{ad.lower()}_gunluk.csv", "id,tutar\n1,10\n", "batch:batch", "0664"))
    x.klasorler[p["klasor"]] = {"Type": "Folder", "Host": p["host"], "RunAs": "batch",
                                ad: {"Type": "Job:FileTransfer", "ConnectionProfileSrc": "YEREL_BATCH", "ConnectionProfileDest": prof,
                                     "FileTransfers": [{"Src": f"/data/giden/{ad.lower()}_*.csv", "Dest": f"/home/{hesap}/in/",
                                                        "TransferType": "Binary", "TransferOption": "SrcToDest", "DSTOPT": "1"}]}}

    def son(ctx):
        t = ctx.simdi + p["gun"] * 86400
        stamp = datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
        _, pub = ctx.lab.sh("ajan1", "cat /opt/ctm/keys/banka_key.pub")
        ctx.lab.sh("dosya-sunucu", f"printf 'expiry-time=\"{stamp}Z\" %s\\n' \"$(cat)\" > /home/{hesap}/.ssh/authorized_keys && "
                                   f"chown {hesap}:{hesap} /home/{hesap}/.ssh/authorized_keys && chmod 600 /home/{hesap}/.ssh/authorized_keys",
                   stdin=pub.strip())
    x.son.append(son)
    x.gercek = None
    return x


def _k_t_oturum(x):
    """An open transaction that holds a lock on a table no job touches."""
    p = x.p
    x.son.append(lambda ctx: _oturum(ctx, "ajan2", "etl_user", f"begin; lock table {p.get('tablo', 'musteri')} in share mode;"))
    x.gercek = None
    return x


def _k_t_birikim_durgun(x):
    _k_birikim(x, durgun=True)
    return x


GENEL = {"Type": "Folder", "Host": "ajan1", "RunAs": "batch",
         "ZAMAN_YAZ": {"Type": "Job:Command", "Command": "echo kontrol ok; date -u +%H:%M:%S"},
         "DOSYA_SAY": {"Type": "Job:Command", "Command": "ls /data/giden | wc -l"}}


class Baglam:
    def __init__(self, lab, ctm, gecmis):
        self.lab, self.ctm, self.gecmis = lab, ctm, gecmis
        self.sahne = {}
        self.simdi = time.time()


# ---------------------------------------------------------------------------------------------------- building a site
def donguler(ctm, klasorler, n, log=print, bekle=150):
    """Order every folder and rerun every job `n` times in all, the way a nightly batch repeats: one cycle after another.
    Returns the job ids."""
    ids = []
    for f in klasorler:
        ids += ctm.order(f)["jobIds"]
    for k in range(n):
        t0 = time.time()
        while True:
            rows = {r["jobId"]: r for r in ctm.status()["statuses"]}
            if all(rows[i]["status"] in FINAL for i in ids if i in rows) or time.time() - t0 > bekle:
                break
            time.sleep(1.0)
        if k < n - 1:
            for i in ids:
                try:
                    ctm.rerun(i)
                except Exception as e:  # noqa: BLE001
                    log(f"    rerun {i}: {e}")
        if (k + 1) % 4 == 0:
            log(f"    dongu {k + 1}/{n}")
    return ids


def kur(lab, ctm, senaryo, log=print):
    """Reset the site, build the scenario, return (truth, context). The site works at the end of this."""
    t0 = time.time()
    ortam.sifirla(lab, ctm)
    log(f"  site sifirlandi ({time.time() - t0:.0f} sn)")
    parcalar = [parca(p) for p in senaryo["bilesenler"]]
    gecmis = senaryo.get("gecmis", HIST)
    ctx = Baglam(lab, ctm, gecmis)
    defs = {"ISLEM_GENEL": GENEL}
    for x in parcalar:
        for k, v in x.klasorler.items():
            defs[k] = v
        defs.update(x.profiller)
        for host, path, content, owner, mode in x.dosyalar:
            lab.write(host, path, content, owner=owner, mode=mode)
        for host, cmd in x.once:
            rc, out = lab.sh(host, cmd)
            if rc:
                raise RuntimeError(f"kurulum adimi basarisiz ({host}): {cmd[:80]} -> {out[:200]}")
    # keep the public key in place for key based jobs: the standard site already holds banka_key on both agents
    if any(p["tur"] in ("anahtar_suresi", "t_anahtar_uzak") for p in senaryo["bilesenler"]):
        _, pub = lab.sh("ajan1", "cat /opt/ctm/keys/banka_key.pub")
        lab.sh("dosya-sunucu", "mkdir -p /home/rapor/.ssh && cat > /home/rapor/.ssh/authorized_keys && chown -R rapor:rapor /home/rapor/.ssh "
                               "&& chmod 700 /home/rapor/.ssh && chmod 600 /home/rapor/.ssh/authorized_keys", stdin=pub)
    ctm.deploy(defs)
    log(f"  tanimlar dagitildi ({len(defs)} klasor/profil)")
    donguler(ctm, [k for k in defs if defs[k].get("Type") == "Folder"], gecmis, log)
    log(f"  gecmis kosuldu ({gecmis} dongu, toplam {time.time() - t0:.0f} sn)")
    ctx.simdi = time.time()
    for x in parcalar:
        for fn in x.son:
            fn(ctx)
    time.sleep(1.5)
    gercek = [x.gercek(ctx) for x in parcalar if x.gercek]
    tuzak = [{"is": _id(x.p) if "is" in x.p else None, "tur": x.p["tur"]} for x in parcalar if not x.gercek]
    return {"riskler": gercek, "tuzaklar": tuzak, "kurulum_sn": round(time.time() - t0, 1), "t": ctx.simdi}, ctx
