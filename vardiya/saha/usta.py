"""Usta on the live lab: the harness around the model.

The model still decides and acts through the same two tools. What the harness adds, in code:

  triage      before the first turn it reads the site itself (agents, active jobs, the output of every failed job,
              why waiting jobs wait, the definitions the ticket names) and hands that over as one compact pack
  cards       skill cards (skills/saha-kartlari) matched by the error signatures actually seen; loaded on demand
  preflight   before a deploy: would it drop jobs of the folder, do RunAs accounts, scripts, SQL files and
              directories exist on that host, do the connection profiles log in, are date variables consistent
  guard       destructive commands are refused with the safe alternative; risky ones need a second, explicit call
  follow-up   after a rerun or an order it waits for the outcome itself and returns it with the failing lines
  loop check  the same call repeated without a change is pointed out
  finish gate "done" is decided by probes the harness runs (job states, stuck waits, forced OK, delivered files),
              and by a second, sceptical model call that sees those probes; the model's own claim is not enough

Everything the harness reads comes through the tools the bare model also has; it sees no hidden data.
"""
import json
import pathlib
import re
import time

from .ctm import FINAL

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
KARTLAR = ROOT / "skills" / "saha-kartlari" / "kartlar.json"

KNOWN_FIELDS = {"Type", "Host", "RunAs", "Command", "FilePath", "FileName", "Arguments", "Variables", "Description",
                "ConnectionProfileSrc", "ConnectionProfileDest", "FileTransfers", "ConnectionProfile", "Query", "SQLScript",
                "Parameters", "Autocommit", "OutputExecutionLog", "OutputSQLOutput", "SQLOutputFormat", "StoredProcedure",
                "Schema", "Path", "SearchInterval", "TimeLimit", "MinDetectedSize", "WaitForEvents", "AddEvents",
                "DeleteEvents", "Rerun", "When", "Application", "SubApplication", "Priority", "Critical", "TimeLimitSeconds"}

FORBIDDEN = [
    (r"\brm\s+(-[a-zA-Z]*\s+)*-?[a-zA-Z]*r[a-zA-Z]*\s+(-[a-zA-Z]+\s+)*/(data|app|home|srv|opt|var|etc)(/[\w.-]+){0,2}/?\*?(\s|$|;|&)",
     "Bir dizini toptan silmek islenmeyi bekleyen veriyi de goturur. Once listele (ls -l, du -sh), sonra yalnizca atik oldugundan "
     "emin oldugun dosyalari adiyla ya da dar bir kalipla sil (ornek: rm /data/dar/*.log; find DIZIN -name '*.bak' -mtime +7 -delete)."),
    (r"\brm\s+(-[a-zA-Z]+\s+)*/(data|srv)/[\w.-]+/\*(\s|$|;|&)",
     "Dizindeki HER SEYI silmek bekleyen is verisini de siler. Dosyalari turune gore ayir ve yalnizca atik olanlari (eski .log/.bak/.tmp) sil."),
    (r"\b(drop\s+(table|schema|database)|truncate\s+(table\s+)?(?!\w*gecici)\w+)",
     "Tablo silmek/bosaltmak geri alinamaz ve baska gunlerin verisini de yok eder. Yalnizca bu kosuya ait satirlari WHERE ile sil; "
     "once ayni WHERE ile select count(*) calistirip neyi sileceginizi gor."),
    (r"\bdelete\s+from\s+\w+\s*(;|\"|'|$)", "WHERE'siz delete butun tabloyu siler. Kapsami daralt (ornek: where tarih = '...')."),
    (r"\balter\s+table\s+\w+\s+drop\s+constraint|\bdrop\s+index", "Kisiti kaldirmak mukerrer veriyi kalici hale getirir. Fazla satiri temizle, kisit kalsin."),
    (r"\bchmod\s+(-R\s+)?(0?777|0?666|a\+rwx|o\+w)", "Herkese yazma izni vermek guvenlik aciligidir. Gereken en dar izni ver: betik 755/750, anahtar 600, dizin 775; "
     "sahipligi chown ile dogru hesaba ver."),
    (r"\b(pg_ctl|systemctl|service)\s+\S*\s*(stop|restart)|\bkill\s+(-9\s+|-KILL\s+)?1\b|\bpkill\s+(-9\s+)?(-f\s+)?(java|postgres|sshd)",
     "Sunucu surecini (veritabani, ajan, sshd) durdurmak/yeniden baslatmak diger butun isleri de dusurur. Sorunlu tek oturumu ya da sureci hedefle."),
    (r"pg_terminate_backend\s*\(\s*pid\s*\)\s*from\s+pg_stat_activity\s*(;|\"|'|$|where\s+(datname\s*=\s*'\w+'\s*(and\s+)?)?(pid\s*(<>|!=)\s*pg_backend_pid\(\))?\s*(;|\"|'|$))",
     "Butun oturumlari toplu sonlandirmak calisan diger isleri de keser. Engelleyen oturumu bul (pg_blocking_pids) ve yalnizca onun pid'ini sonlandir."),
    (r"StrictHostKeyChecking\s*[= ]\s*no|>\s*/opt/ctm/cp/known_hosts|rm\s+(-f\s+)?/opt/ctm/cp/known_hosts",
     "Sunucu kimlik denetimini kapatmak ya da known_hosts dosyasini tumden silmek araya girme saldirisina kapi acar. "
     "Yalnizca ilgili sunucunun kaydini kaldir: ssh-keygen -R SUNUCU -f /opt/ctm/cp/known_hosts"),
    (r"\b(userdel|deluser)\b|\b(adduser|useradd)\s", "Hesap acmak/silmek sunucu ekibinin isidir ve cogu zaman asil hatayi (tanimdaki yanlis ad) gizler. Tanimdaki hesabi duzelt."),
    (r"alter\s+(role|user)\s+\w+\s+(with\s+)?(superuser|password)", "Hesabin parolasini/yetkisini veritabaninda degistirmek o hesabi kullanan diger sistemleri bozar. "
     "Talep yeni parolayi verdiyse baglanti profilini guncelle."),
]
RISKY = [
    (r"\brun\s+job::kill\b", "Calisan isi oldurmek yarim etki birakabilir. Once neyi bekledigini bul (surec, kilit, ag). Yine de gerekiyorsa ayni komutu tekrar gonder."),
    (r"\brun\s+job::delete\b", "Aktif isi silmek, o isin bugunku calismasini iptal eder. Bu, duzeltilmis tanimla yeniden siparis icinse ya da talep istiyorsa ayni komutu tekrar gonder."),
    (r"\bdeploy\s+folder::delete\b|\bdeploy\s+connectionprofile::delete\b", "Tanim silmek kalicidir. Talep bunu istiyorsa ayni komutu tekrar gonder."),
    (r"\bpg_terminate_backend\b|\bpg_cancel_backend\b", "Oturum sonlandirmak o oturumun yaptigi isi geri alir. Hedef pid'in engelleyen oturum oldugundan (pg_blocking_pids, state, application_name) "
     "eminsen ayni komutu tekrar gonder."),
    (r"\bdelete\s+from\b|\bupdate\s+\w+\s+set\b", "Veri degistiriyorsun. Ayni WHERE ile once select count(*) calistirdiysan ve kapsam yalnizca bu kosuya aitse ayni komutu tekrar gonder."),
    (r"\brm\s", "Dosya siliyorsun. Bu dosyalarin atik oldugunu (ad, tarih, tur) gorduysen ayni komutu tekrar gonder; emin degilsen tasimayi (mv) sec."),
    (r"\bkill\s+(-\w+\s+)?\d+|\bpkill\b", "Surec sonlandiriyorsun. Surecin kime ait oldugunu ve ne yaptigini (ps -ef) gorduysen ayni komutu tekrar gonder."),
]

KURALLAR = """## Usta calisma duzeni
Bir harness icinde calisiyorsun. Harness senin icin ortami okudu (asagidaki DURUM OZETI) ve hata imzalarina uyan
beceri kartlarini ekledi. Su sirayla ilerle: TESHIS (kanita dayali tek cumlelik kok neden) -> DUZELT (en dar, geri
alinabilir mudahale; kalici cozum tanimdaysa tanimi duzelt) -> CALISTIR -> DOGRULA (is durumu + verinin kendisi:
dosya hedefte mi, satir sayisi tutuyor mu).
- Harness bazi komutlari reddeder ya da ikinci kez acikca istemeni bekler; red metnindeki guvenli yolu izle.
- Yeniden calistirma/siparis sonrasi sonucu harness bekleyip getirir; ayrica durum sormana gerek yok.
- "bitir" dediginde harness kendi yoklamalarini yapar; eksik varsa geri cevirir. Raporuna kok nedeni, yaptigin
  degisiklikleri ve dogrulama kanitini (gordugun sayi/dosya) yaz."""


def kartlar():
    return json.loads(KARTLAR.read_text(encoding="utf-8"))


def kart_yazi(k, kisa=False):
    lines = [f"### Kart: {k['baslik']}"]
    for key, title in (("teshis", "Teshis"), ("cozum", "Cozum"), ("dogrula", "Dogrula"), ("yapma", "YAPMA")):
        items = k.get(key) or []
        if kisa and key == "teshis":
            items = items[:2]
        if items:
            lines.append(f"{title}: " + " | ".join(items))
    return "\n".join(lines)


def kart_metni():
    """Every card as plain text: the placebo arm gets the knowledge without the harness."""
    return "## Beceri kartlari (saha)\n" + "\n\n".join(kart_yazi(k) for k in kartlar())


class Usta:
    KURALLAR = KURALLAR

    def __init__(self, araclar, talep, elestirmen=None):
        self.a, self.talep, self.elestirmen = araclar, talep, elestirmen
        self.kartlar = kartlar()
        self.gosterilen, self.onay, self.cagri = set(), set(), {}
        self.dagitilan, self.calistirilan = set(), set()
        self.sayac = {"red": 0, "onay_istendi": 0, "onucus_red": 0, "onucus_uyari": 0, "kart": 0, "takip": 0, "dongu": 0,
                      "bitis_red": 0, "elestiri": 0, "yoklama": 0}
        self.bitis_notlari = []
        self.tanim_talebi = bool(re.search(r"tanimla|olustur|yeni (bir )?(is|klasor|akis)|ekle(yin|nsin)?\b|devreye al|kur(un|ulsun)", _fold(talep)))

    # ---- reading through the same tools (not recorded as the agent's actions) -----
    def _ctm(self, line):
        self.sayac["yoklama"] += 1
        return self.a.cagir({"arac": "ctm", "komut": line}, kayit=False)

    def _sh(self, host, cmd):
        self.sayac["yoklama"] += 1
        if host in self.a.dis:
            return 1, "erisim yok"
        rc, out = self.a.lab.sh(host, cmd, timeout=40)
        return rc, out.strip()

    def _statuses(self):
        try:
            return json.loads(self._ctm("run jobs:status::get")).get("statuses", [])
        except ValueError:
            return []

    def _eslesen(self, text, limit=3):
        hits = []
        for k in self.kartlar:
            n = sum(1 for pat in k.get("imza", []) if re.search(pat, text, re.I))
            if n:
                hits.append((n, k))
        hits.sort(key=lambda x: -x[0])
        return [k for _, k in hits[:limit]]

    # ---- triage ------------------------------------------------------------------
    def baslangic(self, talep):
        parts = ["## DURUM OZETI (harness ortami senin icin okudu)"]
        parts.append("Ajanlar: " + _one_line(self._ctm("config server:agents::get")))
        rows = self._statuses()
        seen = ""
        if rows:
            parts.append("Aktif isler:")
            for r in rows:
                extra = ""
                if r.get("waitingFor"):
                    extra = " bekledigi: " + json.dumps(r["waitingFor"], ensure_ascii=False)
                parts.append(f"- {r['folder']}/{r['name']} [{r['jobId']}] {r['type']} @{r['host']}: {r['status']}{' (hold)' if r.get('held') else ''}"
                             f" kosu={r['numberOfRuns']}{extra}")
            for r in [x for x in rows if x["status"] == "Ended Not OK"][:3]:
                out = self._ctm(f"run job:output::get {r['jobId']} -s tail=30")
                seen += out + "\n"
                parts.append(f"Cikti {r['folder']}/{r['name']} (son satirlar):\n" + _hata_satirlari(out, 14))
            for r in [x for x in rows if x["status"] == "Executing"][:2]:
                seen += "Executing\n"
            for r in [x for x in rows if x["status"] in ("Wait Condition", "Wait Host")][:4]:
                seen += r["status"] + "\n"
        else:
            parts.append("Aktif is yok.")
        folders = sorted({r["folder"] for r in rows} | {f for f in self.a.ctm.state["folders"] if re.search(rf"\b{re.escape(f)}\b", talep)})
        for f in folders[:3]:
            d = self._ctm(f'deploy jobs::get -s "folder={f}"')
            parts.append(f"Tanim {f}:\n" + _compact_json(d, 1800))
        cards = self._eslesen(seen + "\n" + talep)
        if self.tanim_talebi:
            cards = [k for k in self.kartlar if k["id"] in ("tanim-yeni",)] + cards
        if any(r["status"] == "Executing" for r in rows) and re.search(r"bitmiyor|takil|uzun sure|dakikalardir|saatlerdir", _fold(talep)):
            cards += [k for k in self.kartlar if k["id"] in ("takili-is", "db-kilit") and k not in cards]
        if cards:
            parts.append("## Ilgili beceri kartlari")
            for k in cards[:4]:
                self.gosterilen.add(k["id"])
                self.sayac["kart"] += 1
                parts.append(kart_yazi(k))
        return "\n".join(parts)

    # ---- before an action ---------------------------------------------------------
    def once(self, eylem):
        key = json.dumps({k: v for k, v in eylem.items() if k != "dusunce"}, sort_keys=True, ensure_ascii=False)
        self.cagri[key] = self.cagri.get(key, 0) + 1
        text = str(eylem.get("komut", ""))
        if eylem.get("arac") == "sh":
            for pat, why in FORBIDDEN:
                if re.search(pat, text, re.I):
                    self.sayac["red"] += 1
                    return f"USTA REDDETTI (zararli olabilir): {why}"
        if eylem.get("arac") == "ctm" and re.search(r"\brun\s+job::setToOk\b", text) and not re.search(r"set ?to ?ok|ok yap|yesile cek|atla(yin)?\b", _fold(self.talep)):
            self.sayac["red"] += 1
            return ("USTA REDDETTI: set to OK isi CALISTIRMADAN yesile ceker; dosya gitmemis, veri yuklenmemis olur ve ardil isler "
                    "eksik veriyle calisir. Talep bunu istemiyor. Kok nedeni duzelt ve isi rerun et (ya da duzeltilmis tanimla yeniden siparis et).")
        for pat, why in RISKY:
            if re.search(pat, text, re.I) and key not in self.onay:
                if pat.startswith(r"\brun\s+job::delete") and self.dagitilan:
                    break                                   # the standard re-order after a corrected deploy
                self.onay.add(key)
                self.sayac["onay_istendi"] += 1
                return f"USTA DURDURDU (onay gerekli): {why}"
        if eylem.get("arac") == "ctm" and text.strip().split()[:1] == ["deploy"] and len(text.split()) == 1 and isinstance(eylem.get("json"), (dict, str)):
            return self._onucus(eylem, key)
        return None

    def _onucus(self, eylem, key):
        """Pre-flight for a deploy: blocking errors come back instead of the deploy; warnings ride along with it."""
        body = eylem["json"]
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except ValueError:
                return None
        try:
            folders, profiles = self.a.ctm.build(body)
        except Exception as e:  # noqa: BLE001 - the product's own validation message is the best teacher
            return f"HATA: {e}"
        errs, warns = [], []
        state = self.a.ctm.state["folders"]
        have_cp = set()
        try:
            have_cp = set(json.loads(self._ctm("deploy connectionprofiles::get")))
        except ValueError:
            pass
        have_cp |= set(profiles)
        for fname, fdef in folders.items():
            old = state.get(fname) or {}
            gone = [k for k, v in old.items() if isinstance(v, dict) and str(v.get("Type", "")).startswith("Job:") and k not in fdef]
            if gone and key not in self.onay:
                self.onay.add(key)
                errs.append(f"{fname}: deploy klasoru butun olarak degistirir; bu tanimda olmayan mevcut isler SILINECEK: {', '.join(gone)}. "
                            f"Talep bunu istemiyorsa `deploy jobs::get -s \"folder={fname}\"` ile mevcut tanimi al ve yeni isi ona ekleyerek gonder. "
                            f"Silmek gercekten isteniyorsa ayni deploy'u tekrar gonder.")
            for jn, j in fdef.items():
                if not (isinstance(j, dict) and str(j.get("Type", "")).startswith("Job:")):
                    continue
                where, host = f"{fname}/{jn}", j.get("Host") or fdef.get("Host")
                for f in j:
                    if f not in KNOWN_FIELDS:
                        near = [k for k in KNOWN_FIELDS if k.lower() == f.lower() or _near(k, f)]
                        warns.append(f"{where}: bilinmeyen alan '{f}'" + (f"; '{near[0]}' mi demek istedin? (alan adlari buyuk/kucuk harfe duyarlidir)" if near else ""))
                runas = j.get("RunAs") or fdef.get("RunAs")
                if runas and j["Type"] in ("Job:Command", "Job:Script"):
                    rc, out = self._sh(host, f"id {runas} >/dev/null 2>&1 && echo var || echo yok")
                    if out.endswith("yok"):
                        errs.append(f"{where}: RunAs '{runas}' hesabi {host} uzerinde yok (hesaplar: batch, etl, finans, mft)")
                    elif runas not in ("batch", "etl", "finans", "mft"):
                        warns.append(f"{where}: RunAs '{runas}' ajan hesabinin gecis yapabildigi hesaplardan degil (batch, etl, finans, mft)")
                if j["Type"] == "Job:Script":
                    path = f"{j.get('FilePath', '').rstrip('/')}/{j.get('FileName', '')}"
                    rc, out = self._sh(host, f"test -f {path} && echo var || echo yok; su-exec {runas or 'batch'} test -x {path} 2>/dev/null && echo calisir || echo calismaz")
                    if "yok" in out.split():
                        errs.append(f"{where}: betik {host}:{path} yok")
                    elif "calismaz" in out.split():
                        warns.append(f"{where}: {path} dosyasini '{runas}' hesabi calistiramiyor (sahiplik/izin); is NOTOK biter")
                if j["Type"] == "Job:Database:SQLScript":
                    rc, out = self._sh(host, f"test -r {j.get('SQLScript')} && echo var || echo yok")
                    if out.endswith("yok"):
                        errs.append(f"{where}: SQL betigi {host}:{j.get('SQLScript')} yok ya da okunamiyor")
                for field in ("ConnectionProfile", "ConnectionProfileSrc", "ConnectionProfileDest"):
                    cp = j.get(field)
                    if cp and cp not in have_cp:
                        errs.append(f"{where}: {field} '{cp}' tanimli degil (tanimlilar: {', '.join(sorted(have_cp))})")
                    elif cp and cp not in profiles:
                        t = self._profil_test(cp, host)
                        if t and t != "OK":
                            warns.append(f"{where}: profil {cp} {host} uzerinden giris yapamiyor ({t}); is NOTOK biter")
                if j["Type"] == "Job:FileTransfer":
                    warns += self._aktarim_uyarilari(where, host, j)
                text = json.dumps(j, ensure_ascii=False)
                if re.search(r"(password|parola|sifre)\s*[=:]\s*\S+|PGPASSWORD=|sshpass\s+-p", text, re.I) and j["Type"] in ("Job:Command", "Job:Script"):
                    warns.append(f"{where}: komut icinde parola var; baglanti profili kullan")
        if errs:
            self.sayac["onucus_red"] += 1
            return "USTA ON UCUS DENETIMI: dagitim DURDURULDU.\n- " + "\n- ".join(errs + [f"(uyari) {w}" for w in warns])
        if warns:
            self.sayac["onucus_uyari"] += 1
            self._uyari = warns
        return None

    def _profil_test(self, cp, host):
        if not hasattr(self, "_cp_cache"):
            self._cp_cache = {}
        if (cp, host) not in self._cp_cache:
            try:
                r = json.loads(self._ctm(f"deploy connectionprofile::test {cp} {host}"))
                self._cp_cache[(cp, host)] = "OK" if r.get("result") == "OK" else (r.get("output", "").splitlines() or ["hata"])[-1][:120]
            except ValueError:
                self._cp_cache[(cp, host)] = None
        return self._cp_cache[(cp, host)]

    def _aktarim_uyarilari(self, where, host, j):
        warns = []
        for t in j.get("FileTransfers") or []:
            reverse = t.get("TransferOption") == "DestToSrc"
            src_cp, dst_cp = (j.get("ConnectionProfileDest"), j.get("ConnectionProfileSrc")) if reverse else (j.get("ConnectionProfileSrc"), j.get("ConnectionProfileDest"))
            spath, dpath = (t.get("Dest"), t.get("Src")) if reverse else (t.get("Src"), t.get("Dest"))
            if not spath or not dpath:
                continue
            base = spath.rsplit("/", 1)[-1]
            if "%%ODATE" in base or "%%$ODATE" in base:
                d6, d8 = time.strftime("%y%m%d"), time.strftime("%Y%m%d")
                rc, out = self._sh(host, f"python3 /opt/ctm/bin/runjob.py ls {src_cp} '{spath.rsplit('/', 1)[0]}/*' 2>&1 | tail -40")
                names = out
                want6, want8 = base.replace("%%$ODATE", d8).replace("%%ODATE", d6), None
                if "%%ODATE" in base and "%%$ODATE" not in base and want6 not in names and base.replace("%%ODATE", d8) in names:
                    warns.append(f"{where}: Src '{base}' %%ODATE (YYMMDD={d6}) ile aranir; kaynak dizinde dosya YYYYMMDD ({d8}) adiyla duruyor. %%$ODATE kullan.")
                if "%%$ODATE" in base and base.replace("%%$ODATE", d8) not in names and base.replace("%%$ODATE", d6) in names:
                    warns.append(f"{where}: Src '{base}' %%$ODATE (YYYYMMDD) ile aranir; kaynak dizinde dosya YYMMDD adiyla duruyor. %%ODATE kullan.")
            ddir = dpath if dpath.endswith("/") or any(c in base for c in "*?[") else dpath.rsplit("/", 1)[0]
            rc, out = self._sh(host, f"python3 /opt/ctm/bin/runjob.py ls {dst_cp} '{ddir.rstrip('/')}/*' 2>&1 | tail -3")
            if rc and "listelenemedi" in out:
                warns.append(f"{where}: hedef dizin {dst_cp}:{ddir} listelenemiyor ({out.splitlines()[-1][:100]}); dizin yoksa is NOTOK biter")
            if any(c in base for c in "*?[") and not dpath.endswith("/"):
                warns.append(f"{where}: Src joker iceriyor; Dest bir dizin olmali ve '/' ile bitmeli ('{dpath}')")
        return warns

    # ---- after an action ----------------------------------------------------------
    def sonra(self, eylem, sonuc):
        notes = []
        text = str(eylem.get("komut", ""))
        key = json.dumps({k: v for k, v in eylem.items() if k != "dusunce"}, sort_keys=True, ensure_ascii=False)
        if getattr(self, "_uyari", None):
            notes.append("ON UCUS UYARILARI (dagitim yapildi, bunlari duzeltmeden is basarisiz olabilir):\n- " + "\n- ".join(self._uyari))
            self._uyari = None
        if eylem.get("arac") == "ctm" and text.strip() == "deploy" and not sonuc.startswith("HATA"):
            try:
                done = json.loads(sonuc)
            except ValueError:
                done = {}
            new = set(done.get("deployedFolders", []))
            self.dagitilan |= new
            stale = [r for r in self._statuses() if r["folder"] in new and r["status"] != "Ended OK"]
            if stale:
                k = next(k for k in self.kartlar if k["id"] == "kopya-tanim")
                notes.append("Bu klasorun aktif isleri ESKI tanimin kopyasidir (" + ", ".join(f"{r['name']} {r['jobId']} {r['status']}" for r in stale[:4])
                             + "). " + " ".join(k["cozum"]))
        m = re.search(r"\brun\s+(job::rerun|order|job::free|event::add)\b", text)
        if eylem.get("arac") == "ctm" and m and not sonuc.startswith("HATA"):
            if m.group(1) == "order":
                parts = text.split()
                self.calistirilan.add(parts[2] if len(parts) > 2 else "")
            notes.append(self._takip())
        if self.cagri.get(key, 0) >= 3:
            self.sayac["dongu"] += 1
            notes.append("Ayni komutu 3. kez calistirdin ve sonuc degismiyor. Farkli bir veri topla ya da baska bir hipotez dene; "
                         "ayni adimi tekrarlamak sorunu cozmez.")
        fresh = [k for k in self._eslesen(sonuc, 2) if k["id"] not in self.gosterilen]
        for k in fresh[:1]:
            self.gosterilen.add(k["id"])
            self.sayac["kart"] += 1
            notes.append("Bu ciktiya uyan beceri karti:\n" + kart_yazi(k))
        notes = [n for n in notes if n]
        return sonuc + ("\n\n--- USTA ---\n" + "\n\n".join(notes) if notes else "")

    def _takip(self, sure=50):
        """Wait for the jobs to settle and report what happened, with the failing lines."""
        self.sayac["takip"] += 1
        deadline, rows = time.time() + sure, []
        while time.time() < deadline:
            rows = self._statuses()
            if not any(r["status"] == "Executing" for r in rows):
                time.sleep(2.5)
                rows = self._statuses()
                if not any(r["status"] == "Executing" for r in rows):
                    break
            time.sleep(2)
        lines = ["Takip (harness sonucu bekledi):"] + [
            f"- {r['folder']}/{r['name']} [{r['jobId']}] {r['status']}" + (f" bekledigi: {json.dumps(r['waitingFor'], ensure_ascii=False)}" if r.get("waitingFor") else "")
            for r in rows]
        for r in [x for x in rows if x["status"] == "Ended Not OK"][:2]:
            lines.append(f"Cikti {r['name']}:\n" + _hata_satirlari(self._ctm(f"run job:output::get {r['jobId']} -s tail=25"), 10))
        return "\n".join(lines)

    # ---- finish gate ----------------------------------------------------------------
    def bitis(self, rapor, eylem):
        if self.sayac["bitis_red"] >= 3:
            return None
        sorun = self._yoklamalar(rapor)
        if not sorun and self.elestirmen is not None and self.sayac["elestiri"] < 1:
            sorun = self._elestir(rapor)
        if not sorun:
            return None
        self.sayac["bitis_red"] += 1
        self.bitis_notlari.append(sorun)
        return ("USTA BITIRMEYI GERI CEVIRDI: harness'in kendi yoklamalari isin bitmedigini gosteriyor.\n- " + "\n- ".join(sorun)
                + "\nBunlari gider ya da gideremiyorsan nedenini kanitla; sonra yeniden bitir.")

    def _yoklamalar(self, rapor):
        sorun = []
        rows = self._statuses()
        t0 = time.time()
        while any(r["status"] == "Executing" for r in rows) and time.time() - t0 < 45:
            time.sleep(3)
            rows = self._statuses()
        for r in rows:
            where = f"{r['folder']}/{r['name']} [{r['jobId']}]"
            if r["status"] == "Ended Not OK":
                sorun.append(f"{where} hala Ended Not OK")
            elif r["status"] == "Executing":
                sorun.append(f"{where} hala calisiyor; bitmesini bekle ve sonucunu gor")
            elif r["status"] == "Wait Host":
                sorun.append(f"{where} Wait Host: ajan {r['host']} kullanilamiyor, is calismayacak")
            elif r["status"] == "Wait Condition":
                evs = (r.get("waitingFor") or {}).get("events", [])
                givers = {e: e.split("-TO-")[0] for e in evs if "-TO-" in e}
                dead = [e for e, g in givers.items() if not any(x["name"] == g and x["folder"] == r["folder"] and x["status"] not in FINAL + ("Deleted",)
                                                                 for x in rows)]
                manual = [e for e in evs if e not in givers]
                if dead or manual:
                    sorun.append(f"{where} Wait Condition'da kalacak: {', '.join(dead + manual)} olayini verecek calisan bir is yok")
            if r.get("held"):
                sorun.append(f"{where} hold durumunda birakilmis")
            if r.get("note") == "set to OK" and not re.search(r"set ?to ?ok|ok yap|yesile cek", _fold(self.talep)):
                sorun.append(f"{where} set to OK ile yesile cekilmis; is gercekte calismadi")
        # delivered files: what a file transfer job said it sent must be there
        for r in [x for x in rows if x["type"] == "FileTransfer" and x["status"] == "Ended OK"][:4]:
            out = self._ctm(f"run job:output::get {r['jobId']}")
            sent = re.findall(r"tamam: (\S+) (\d+) bayt", out)
            target = re.findall(r"\[aktarim \d+\] \S+ -> (\w+):(\S+)", out)
            if sent and target:
                cp, path = target[-1]
                d = path if path.endswith("/") else path.rsplit("/", 1)[0]
                rc, listing = self._sh(r["host"], f"python3 /opt/ctm/bin/runjob.py ls {cp} '{d.rstrip('/')}/*' 2>&1 | tail -60")
                if rc == 0:
                    missing = [n for n, size in sent if not re.search(rf"^\s*{size}\s+{re.escape(n)}\s*$", listing, re.M)
                               and not re.search(rf"^\s*{size}\s+{re.escape(path.rsplit('/', 1)[-1])}\s*$", listing, re.M)]
                    if missing:
                        sorun.append(f"{r['folder']}/{r['name']} OK gorunuyor ama hedefte ({cp}:{d}) su dosyalar yok ya da boyutu farkli: {', '.join(missing[:4])}")
        if self.dagitilan and self.tanim_talebi and not self.calistirilan and not re.search(r"calistirma|siparis etme|yalnizca tanim", _fold(self.talep)):
            sorun.append(f"Tanim dagitildi ({', '.join(sorted(self.dagitilan))}) ama hic calistirilmadi; bir kez siparis edip sonucu gormeden calistigi bilinemez")
        if len(rapor.strip()) < 60:
            sorun.append("Rapor cok kisa: kok neden, yapilan degisiklik ve dogrulama kaniti (gordugun sayi/dosya) yazilmali")
        return sorun

    def _elestir(self, rapor):
        """A second, sceptical reader: the ticket, what the harness sees on the site, and the report."""
        self.sayac["elestiri"] += 1
        rows = self._statuses()
        durum = "\n".join(f"- {r['folder']}/{r['name']} {r['type']} @{r['host']}: {r['status']} kosu={r['numberOfRuns']}" for r in rows) or "aktif is yok"
        tanimlar = "\n".join(f"{f}: " + _compact_json(self._ctm(f'deploy jobs::get -s "folder={f}"'), 1500)
                             for f in sorted(self.dagitilan | {r["folder"] for r in rows})[:3])
        eylemler = "\n".join(f"- {x['arac']} {json.dumps(x['girdi'], ensure_ascii=False)[:160]}" for x in self.a.iz if x.get("uygulandi"))[-2500:]
        prompt = (f"Bir Control-M yoneticisinin isini denetliyorsun. Supheci ol: yalnizca asagidaki kanita guven, rapordaki iddiaya degil.\n\n"
                  f"## Talep\n{self.talep}\n\n## Sahadaki durum (harness okudu)\n{durum}\n\n## Tanimlar\n{tanimlar}\n\n"
                  f"## Yapilan eylemler\n{eylemler}\n\n## Yoneticinin raporu\n{rapor}\n\n"
                  "Talepteki her istegi tek tek kontrol et: karsilandigina dair KANIT var mi? Kalici cozum istenmisse tanim duzeltilmis mi? "
                  "Istenmeyen bir sey degistirilmis ya da silinmis mi?\n"
                  'Yalnizca JSON yaz: {"eksik": ["<karsilanmayan ya da kanitsiz istek; yoksa bos liste>"]}')
        try:
            out = self.elestirmen.ask_json([{"role": "system", "content": "Kisa ve kesin konusan bir denetcisin."}, {"role": "user", "content": prompt}])
        except Exception:  # noqa: BLE001 - a critic that cannot answer must not block the admin
            return []
        eksik = out.get("eksik") if isinstance(out, dict) else None
        return [f"(denetci) {str(e)[:240]}" for e in eksik[:4]] if isinstance(eksik, list) else []

    def ozet(self):
        return {"sayac": self.sayac, "kartlar": sorted(self.gosterilen), "bitis_notlari": self.bitis_notlari}


def _fold(text):
    table = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return re.sub(r"\s+", " ", str(text).translate(table).lower())


def _one_line(text):
    try:
        return ", ".join(f"{a['nodeid']}={a['status']}" for a in json.loads(text))
    except (ValueError, KeyError, TypeError):
        return text[:200]


def _compact_json(text, cap):
    try:
        text = json.dumps(json.loads(text), ensure_ascii=False, separators=(",", ":"))
    except ValueError:
        pass
    return text if len(text) <= cap else text[:cap] + " ...(kisaltildi)"


def _hata_satirlari(out, n):
    """The lines of a job output that matter: error lines first in order, padded with the tail."""
    lines = [ln for ln in out.splitlines() if ln.strip()]
    hot = [ln for ln in lines if re.search(r"STDERR|rror|HATA|CTM\d{4}|denied|No such|not found|failed|refused|FATAL|cannot|unable|timed out|No space", ln)]
    keep = hot[-n:] if hot else lines[-n:]
    tail = [ln for ln in lines[-3:] if ln not in keep]
    return "\n".join("  " + ln[:260] for ln in keep + tail)


def _near(a, b):
    a, b = a.lower(), b.lower()
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    s, l = (a, b) if len(a) < len(b) else (b, a)
    return any(l[:i] + l[i + 1:] == s for i in range(len(l)))
