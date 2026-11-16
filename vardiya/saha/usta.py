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


KONU_DISI = re.compile(r"konusu degil|dokunmayin|dokunulmamali|ilgilenmeyin|kapsam(i)? disi")


def kartlar():
    return json.loads(KARTLAR.read_text(encoding="utf-8"))


# ---- scope: which jobs a ticket is about, and what they wait for ------------------------------------------------
def _is_job(v):
    return isinstance(v, dict) and str(v.get("Type", "")).startswith("Job:")


def olay_grafi(tanimlar):
    """From deployed definitions: {event: [folder/job that posts it]} and {folder/job: [events it waits for]}.
    Flow sequences post A-TO-B events like the scheduler does."""
    veren, bekler = {}, {}
    for fname, fdef in (tanimlar or {}).items():
        if not isinstance(fdef, dict):
            continue
        for v in fdef.values():
            if isinstance(v, dict) and v.get("Type") == "Flow":
                seq = v.get("Sequence") or []
                for a, b in zip(seq, seq[1:]):
                    veren.setdefault(f"{a}-TO-{b}", []).append(f"{fname}/{a}")
                    bekler.setdefault(f"{fname}/{b}", []).append(f"{a}-TO-{b}")
        for jn, j in fdef.items():
            if not _is_job(j):
                continue
            for e in (j.get("WaitForEvents") or {}).get("Events", []):
                bekler.setdefault(f"{fname}/{jn}", []).append(e.get("Event"))
            for e in (j.get("AddEvents") or {}).get("Events", []):
                veren.setdefault(e.get("Event"), []).append(f"{fname}/{jn}")
    return veren, bekler


def _kokler(text):
    return [w for w in re.split(r"[^a-z0-9]+", _fold(text)) if len(w) >= 4]


def _parcalar(ad):
    return _kokler(ad.replace("_", " ").replace("-", " "))


def _anar(words, tok):
    return any(w.startswith(tok) or (len(w) >= 5 and tok.startswith(w)) for w in words)


def ilgi(talep, ad):
    """How many name parts of a folder or job (split at _ and -) the ticket mentions, allowing Turkish suffixes
    (KAPANIS matches 'kapanisini') and the plain-word form of a name ('muhasebe kapanisi')."""
    words = set(_kokler(talep))
    return sum(1 for tok in _parcalar(ad) if _anar(words, tok))


def adlanan(talep, tanimlar):
    """Folders the ticket names exactly: an existing folder, the folder of an existing job, or a new folder name
    (with an underscore) that the ticket asks to be built."""
    tanimlar = tanimlar or {}
    isler = {jn: fn for fn, fd in tanimlar.items() if isinstance(fd, dict) for jn, j in fd.items() if _is_job(j)}
    out = set()
    for ident in set(re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b", talep)):
        if ident in tanimlar:
            out.add(ident)
        elif ident in isler:
            out.add(isler[ident])
        elif "_" in ident and not re.match(r"(SFTP|PG|YEREL)_", ident) and re.search(rf"\b{ident}\b\s+(adinda|adli|isimli)?\s*(yeni\s+)?(bir\s+)?klasor", talep, re.I):
            out.add(ident)            # the new folder the ticket asks for
    return out


def kapsam_hesapla(talep, tanimlar, rows=()):
    """Folders the ticket is about, plus, through the event graph, every folder whose jobs post an event an in-scope
    job waits for (the root cause may sit upstream in another folder).

    A folder or job the ticket names exactly decides alone (a folder that does not exist yet counts: it is the one
    to be built). Otherwise the ticket's words are matched to name parts, a part weighted by how rare it is on the
    site (RAPOR or GONDER in many names says little; KAPANIS in one says much). Empty when nothing is clear: then
    everything counts as in scope, as before."""
    tanimlar = tanimlar or {}
    isler = {jn: fn for fn, fd in tanimlar.items() if isinstance(fd, dict) for jn, j in fd.items() if _is_job(j)}
    exact = adlanan(talep, tanimlar)
    if exact:
        kapsam = exact
    else:
        words = set(_kokler(talep))
        sayi = {}
        for ad in list(tanimlar) + list(isler):
            for tok in set(_parcalar(ad)):
                sayi[tok] = sayi.get(tok, 0) + 1
        puan = {}
        for fname, fd in tanimlar.items():
            p = sum(2 / sayi[t] for t in set(_parcalar(fname)) if _anar(words, t))
            jp = [sum(1 / sayi[t] for t in set(_parcalar(jn)) if _anar(words, t)) for jn in fd if _is_job(fd[jn])] if isinstance(fd, dict) else []
            p += max(jp or [0])
            if p:
                puan[fname] = p
        if not puan or max(puan.values()) < 1.0:
            return set()
        top = max(puan.values())
        kapsam = {f for f, p in puan.items() if p >= 0.6 * top}
    return kapsam | yukari_zincir(kapsam & set(tanimlar), tanimlar)


def yukari_zincir(klasorler, tanimlar):
    """Folders upstream of the given ones through events (transitively)."""
    veren, bekler = olay_grafi(tanimlar)
    out, todo = set(), list(klasorler)
    seen = set(klasorler)
    while todo:
        f = todo.pop()
        for job, evs in bekler.items():
            if job.split("/")[0] != f:
                continue
            for e in evs:
                for g in veren.get(e, []):
                    gf = g.split("/")[0]
                    if gf not in seen:
                        seen.add(gf)
                        out.add(gf)
                        todo.append(gf)
    return out


def hesap_uyusmazligi(where, j, cp_defs):
    """A transfer whose remote path is in one account's home (/home/<hesap>/...) but whose profile logs in as another
    account delivers to the wrong place and still ends OK."""
    errs = []
    for t in j.get("FileTransfers") or []:
        for path, cp_field in ((t.get("Dest"), "ConnectionProfileDest"), (t.get("Src"), "ConnectionProfileSrc")):
            m = re.match(r"/home/([\w.-]+)/", str(path or ""))
            cp = cp_defs.get(j.get(cp_field) or "")
            if not m or not isinstance(cp, dict) or "SFTP" not in str(cp.get("Type", "")):
                continue
            user = str(cp.get("User", ""))
            if user and user != m.group(1):
                errs.append(f"{where}: {cp_field} '{j.get(cp_field)}' karsi tarafa '{user}' hesabiyla giriyor ama yol '{path}' "
                            f"'{m.group(1)}' hesabinin dizini. Profilin adi yaniltici olabilir: once `deploy connectionprofiles::get` ile "
                            f"profilin gercek hesabina bak. Dogru hesapla giren profil yoksa yeni bir profil tanimla (mevcut profili baska "
                            f"isler de kullaniyor olabilir). Bu dogruysa ayni deploy'u tekrar gonder.")
    return errs


def bekleme_zinciri(rows, tanimlar, klasorler=None):
    """Lines like 'A/X bekliyor: EV <- B/Y (Ended Not OK)' for every waiting job (in the given folders), so a
    wait whose giver sits in another folder or has failed is visible at once."""
    veren, _ = olay_grafi(tanimlar)
    durum = {f"{r['folder']}/{r['name']}": r["status"] for r in rows}
    lines = []
    for r in rows:
        if r["status"] != "Wait Condition" or (klasorler and r["folder"] not in klasorler):
            continue
        for e in (r.get("waitingFor") or {}).get("events", []):
            givers = veren.get(e, [])
            if givers:
                desc = ", ".join(f"{g} ({durum.get(g, 'aktif degil')})" for g in givers[:3])
            else:
                desc = "bu olayi veren tanimli bir is YOK (elle verilen olay ya da eksik tanim)"
            lines.append(f"- {r['folder']}/{r['name']} bekliyor: {e} <- {desc}")
    return lines


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
        self.kapsam, self.odak, self.tanimlar, self.dokunulan = set(), set(), {}, set()
        self.kabul = []
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

    def _tam(self, line):
        """A read through the same ctm interface, without the display cut the agent's view has: on a crowded site the
        status list and the definitions run past the cut, and a cut JSON cannot be parsed. The agent can read the
        same data in parts (filters, one folder at a time)."""
        self.sayac["yoklama"] += 1
        return self.a.ctm.cli(line)

    def _statuses(self):
        try:
            return json.loads(self._tam("run jobs:status::get")).get("statuses", [])
        except ValueError:
            return []

    def _icinde(self, folder):
        return not self.kapsam or folder in self.kapsam or folder in self.dokunulan

    def _tanimlar(self):
        try:
            d = json.loads(self._tam("deploy jobs::get"))
            return d if isinstance(d, dict) else {}
        except ValueError:
            return {}

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
        self.tanimlar = self._tanimlar()
        self.odak = kapsam_hesapla(talep, self.tanimlar, rows)
        # the scope also limits the gate and guards only when it is sure: the ticket names the folder, or says that
        # the other failures on the site are not its subject; a guess from words only orders what is shown first
        kesin = bool(adlanan(talep, self.tanimlar)) or bool(KONU_DISI.search(_fold(talep)))
        self.kapsam = set(self.odak) if kesin else set()
        icinde = lambda f: not self.odak or f in self.odak  # noqa: E731
        seen = ""
        if self.odak:
            parts.append("Talebin kapsami (harness, talepte gecen adlardan ve olay zincirinden cikardi" + ("" if kesin else "; tahmin") + "): "
                         + ", ".join(sorted(self.odak))
                         + ". Kapsam disindaki islere talep istemedikce dokunma; kok neden kapsam disinda bir klasordeyse "
                         "onu kanitla ve yalnizca o isi duzelt.")
        if rows:
            parts.append("Aktif isler:")
            disarda = {}
            for r in rows:
                if not icinde(r["folder"]):
                    disarda.setdefault(r["folder"], []).append(f"{r['name']}={r['status']}")
                    continue
                extra = ""
                if r.get("waitingFor"):
                    extra = " bekledigi: " + json.dumps(r["waitingFor"], ensure_ascii=False)
                parts.append(f"- {r['folder']}/{r['name']} [{r['jobId']}] {r['type']} @{r['host']}: {r['status']}{' (hold)' if r.get('held') else ''}"
                             f" kosu={r['numberOfRuns']}{extra}")
            if disarda:
                parts.append("Kapsam disi (yalnizca bilgi): " + "; ".join(f"{f}: {', '.join(v)}" for f, v in sorted(disarda.items())))
            zincir = bekleme_zinciri(rows, self.tanimlar, self.odak or None)
            if zincir:
                parts.append("Bekleme zinciri (bekleyen is <- olayi veren is):\n" + "\n".join(zincir[:8]))
            failed = sorted([x for x in rows if x["status"] == "Ended Not OK"], key=lambda x: not icinde(x["folder"]))
            for r in failed[:3]:
                if self.kapsam and not icinde(r["folder"]):
                    break
                out = self._ctm(f"run job:output::get {r['jobId']} -s tail=30")
                seen += out + "\n"
                parts.append(f"Cikti {r['folder']}/{r['name']} (son satirlar):\n" + _hata_satirlari(out, 14))
            for r in [x for x in rows if x["status"] == "Executing" and icinde(x["folder"])][:2]:
                seen += "Executing\n"
            for r in [x for x in rows if x["status"] in ("Wait Condition", "Wait Host") and icinde(x["folder"])][:4]:
                seen += r["status"] + "\n"
        else:
            parts.append("Aktif is yok.")
        named = {f for f in self.tanimlar if re.search(rf"\b{re.escape(f)}\b", talep)}
        folders = sorted(named | (self.odak or {r["folder"] for r in rows}), key=lambda f: (f not in named, f))
        for f in folders[:3]:
            d = json.dumps({f: self.tanimlar[f]}, ensure_ascii=False) if f in self.tanimlar else self._ctm(f'deploy jobs::get -s "folder={f}"')
            parts.append(f"Tanim {f}:\n" + _compact_json(d, 1800))
        self.standart = self._standartlar() if (self.tanim_talebi or "standart" in _fold(talep)) else ""
        if self.standart:
            parts.append("## Site standartlari (harness sunucularda buldu; yeni ve degisen tanimlar bunlara uymali)\n" + self.standart)
        self.kabul = self._kabul_listesi(talep)
        if self.kabul:
            parts.append("## Kabul listesi (harness talepten cikardi; bitis kapisi her maddeyi ayri denetler, raporunda her madde icin "
                         "gordugun kaniti yaz)\n" + "\n".join(f"{i}. {m}" for i, m in enumerate(self.kabul, 1)))
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
        if eylem.get("arac") == "ctm" and "kapsam:" + key not in self.onay:
            why = self._kapsam_disi(eylem, text) or self._elle_olay(text)
            if why:
                self.onay.add("kapsam:" + key)
                self.sayac["onay_istendi"] += 1
                return f"USTA DURDURDU (onay gerekli): {why}"
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

    def _hedef_klasorler(self, eylem, text):
        """Folders a changing ctm command acts on (empty for reads)."""
        argv = text.split()
        m = re.search(r"\brun\s+job::(rerun|setToOk|delete|kill|free|hold|confirm)\s+(\S+)", text)
        if m:
            row = next((r for r in self._statuses() if r["jobId"] == m.group(2)), None)
            return {row["folder"]} if row else set()
        if argv[:2] == ["run", "order"] and len(argv) > 2:
            return {argv[2]}
        if argv[:2] == ["deploy", "folder::delete"] and len(argv) > 2:
            return {argv[2]}
        if argv == ["deploy"] and isinstance(eylem.get("json"), (dict, str)):
            body = eylem["json"]
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except ValueError:
                    return set()
            return {k for k, v in body.items() if isinstance(v, dict) and v.get("Type") == "Folder"}
        return set()

    def _kapsam_disi(self, eylem, text):
        if not getattr(self, "kapsam", None):
            return None
        hedef = self._hedef_klasorler(eylem, text)
        # a folder the ticket does not name, that is not upstream of it, that the agent has not worked on yet,
        # and that already exists on the site (a new folder the ticket asks for is not "someone else's")
        yabanci = sorted(f for f in hedef if f not in self.kapsam and f not in self.dokunulan and f in self.tanimlar)
        if not yabanci:
            return None
        return (f"{', '.join(yabanci)} talebin kapsaminda gorunmuyor (kapsam: {', '.join(sorted(self.kapsam))}). Sitedeki baska "
                "arizalar baska ekiplerin isi olabilir; onlara dokunmak istenmeyen bir degisikliktir. Bu klasorun talebin kok "
                "nedeni oldugunu kanitladiysan (ornegin bekleyen isin olayini bu is veriyor) ayni komutu tekrar gonder.")

    def _elle_olay(self, text):
        m = re.search(r"\brun\s+event::add\s+(\S+)", text)
        if not m:
            return None
        ev = m.group(1)
        veren, _ = olay_grafi(getattr(self, "tanimlar", None) or self._tanimlar())
        givers = veren.get(ev, [])
        if not givers:
            return None
        durum = {f"{r['folder']}/{r['name']}": r["status"] for r in self._statuses()}
        # only when a giver is on the site today and has not finished OK: a giver that was not ordered at all (the
        # work was done another way) leaves adding the event by hand as the documented path
        if not any(g in durum for g in givers) or any(durum.get(g) == "Ended OK" for g in givers):
            return None
        gorulen = ", ".join(g + "=" + durum.get(g, "aktif degil") for g in givers[:3])
        return (f"{ev} olayini normalde {', '.join(givers[:3])} verir ve o is basariyla bitmedi "
                f"({gorulen}). Olayi elle eklemek, ardil isleri "
                "girdisi hazir olmadan calistirir (sahte yesil). Once olayi veren isi duzeltip calistir; olay kendiliginden gelir. "
                "Talep elle eklemeyi acikca istiyorsa ayni komutu tekrar gonder.")

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
        try:
            cp_defs = json.loads(self._tam("deploy connectionprofiles::get"))
        except ValueError:
            cp_defs = {}
        if "profil:" + key not in self.onay:
            pe = self._profil_etkisi(profiles, cp_defs, folders)
            if pe:
                self.onay.add("profil:" + key)
                errs += pe
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
                    if "hesap:" + key not in self.onay:
                        he = hesap_uyusmazligi(where, j, {**cp_defs, **profiles})
                        if he:
                            self.onay.add("hesap:" + key)
                            errs += he
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

    def _profil_etkisi(self, profiles, cp_defs, folders):
        """A profile that already exists and is redeployed with another account or server changes every job that
        uses it, in other folders too."""
        errs = []
        tanim = self.tanimlar or self._tanimlar()
        for name, new in (profiles or {}).items():
            old = cp_defs.get(name)
            if not isinstance(old, dict) or not isinstance(new, dict):
                continue
            changed = [f for f in ("User", "HostName", "Host", "DatabaseName") if f in old and str(new.get(f, old[f])) != str(old[f])]
            if not changed:
                continue
            users = [f"{fn}/{jn}" for fn, fd in tanim.items() if fn not in folders and isinstance(fd, dict)
                     for jn, j in fd.items() if _is_job(j) and name in (j.get("ConnectionProfile"), j.get("ConnectionProfileSrc"), j.get("ConnectionProfileDest"))]
            if users:
                errs.append(f"profil {name} zaten var ve su isler de onu kullaniyor: {', '.join(users[:5])}. {', '.join(changed)} alanini degistirmek "
                            "onlarin da hedefini degistirir. Yeni bir hesap/sunucu gerekiyorsa yeni adla ayri bir profil tanimla; bu profili "
                            "degistirmek gercekten isteniyorsa ayni deploy'u tekrar gonder.")
        return errs

    def _ayni_hesap(self, deployed):
        """After a profile is deployed: other profiles that log in to the same server with the same account (a changed
        password breaks them too), and the jobs that use them."""
        if not deployed:
            return None
        try:
            defs = json.loads(self._tam("deploy connectionprofiles::get"))
        except ValueError:
            return None
        tanim = self.tanimlar or self._tanimlar()
        lines = []
        for name in deployed:
            d = defs.get(name) or {}
            same = [n for n, x in defs.items() if n not in deployed and isinstance(x, dict) and x.get("User") == d.get("User")
                    and (x.get("HostName") or x.get("Host")) == (d.get("HostName") or d.get("Host")) and x.get("Type") == d.get("Type")]
            for n in same:
                users = [f"{fn}/{jn}" for fn, fd in tanim.items() if isinstance(fd, dict) for jn, j in fd.items()
                         if _is_job(j) and n in (j.get("ConnectionProfile"), j.get("ConnectionProfileSrc"), j.get("ConnectionProfileDest"))]
                lines.append(f"- {n}: ayni sunucuya ayni hesapla ({d.get('User')}) giriyor; kullanan isler: {', '.join(users[:5]) or 'yok'}")
        if not lines:
            return None
        return ("Ayni hesabi kullanan baska profiller var. Hesabin parolasi ya da anahtari degistiyse bunlar da guncellenmeli, "
                "yoksa onlari kullanan isler dusmeye devam eder:\n" + "\n".join(lines))

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
        if eylem.get("arac") == "ctm" and not sonuc.startswith("HATA"):
            hedef = self._hedef_klasorler(eylem, text)
            self.dokunulan |= hedef
            if hedef and text.strip().startswith("deploy"):
                self.tanimlar = self._tanimlar()
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
            ikiz = self._ayni_hesap(done.get("deployedConnectionProfiles", []))
            if ikiz:
                notes.append(ikiz)
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
            if m.group(1) == "order":
                notes.append(self._kopya_bekliyor(sonuc))
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

    def _kopya_bekliyor(self, sonuc):
        """A job ordered alone out of a flow is a new copy that waits for its predecessor's event; when that event
        was already given and consumed, the copy waits forever and the failed instance is still there."""
        try:
            new = set(json.loads(sonuc).get("jobIds", []))
        except (ValueError, AttributeError):
            return None
        rows = self._statuses()
        lines = []
        for r in [x for x in rows if x["jobId"] in new and x["status"] == "Wait Condition"]:
            eski = [x for x in rows if x["folder"] == r["folder"] and x["name"] == r["name"] and x["jobId"] != r["jobId"]
                    and x["status"] in ("Ended Not OK", "Wait Condition")]
            evs = ", ".join((r.get("waitingFor") or {}).get("events", []))
            lines.append(f"- {r['folder']}/{r['name']} yeni kopyasi [{r['jobId']}] {evs} olayini bekliyor; tek basina siparis edilen is, "
                         "akistaki oncusunun olayini yeniden bekler." + (f" Ayni isin eski ornegi duruyor: {', '.join(x['jobId'] + ' ' + x['status'] for x in eski[:3])}; "
                         f"duzeltmeden sonra o ornegi `run job::rerun {eski[0]['jobId']}` ile yeniden calistirmak kopya yaratmaz." if eski else ""))
        if not lines:
            return None
        return ("SIPARIS NOTU:\n" + "\n".join(lines) + "\nTanim degistiyse yeni kopya gerekir: o zaman eski ornegi sil, oncu gercekten bittiyse "
                "bekleyen olayi kanitiyla ekle. Tanim degismediyse yeni kopya siparis etmek yerine basarisiz ornegi rerun et.")

    def _takip(self, sure=50):
        """Wait for the jobs to settle and report what happened, with the failing lines."""
        self.sayac["takip"] += 1
        deadline, rows = time.time() + sure, []
        while time.time() < deadline:
            rows = [r for r in self._statuses() if self._icinde(r["folder"])]
            if not any(r["status"] == "Executing" for r in rows):
                time.sleep(2.5)
                rows = [r for r in self._statuses() if self._icinde(r["folder"])]
                if not any(r["status"] == "Executing" for r in rows):
                    break
            time.sleep(2)
        lines = ["Takip (harness sonucu bekledi" + (", talebin kapsamindaki isler" if self.kapsam else "") + "):"] + [
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
        icinde = self._icinde
        while any(r["status"] == "Executing" and icinde(r["folder"]) for r in rows) and time.time() - t0 < 45:
            time.sleep(3)
            rows = self._statuses()
        veren, _ = olay_grafi(getattr(self, "tanimlar", None) or self._tanimlar())
        canli = {f"{x['folder']}/{x['name']}" for x in rows if x["status"] not in FINAL + ("Deleted",)}
        durum = {f"{x['folder']}/{x['name']}": x["status"] for x in rows}
        for r in rows:
            if not icinde(r["folder"]):
                continue          # other teams' failures on a crowded site are not this ticket's work
            where = f"{r['folder']}/{r['name']} [{r['jobId']}]"
            if r["status"] == "Ended Not OK":
                sorun.append(f"{where} hala Ended Not OK")
            elif r["status"] == "Executing":
                sorun.append(f"{where} hala calisiyor; bitmesini bekle ve sonucunu gor")
            elif r["status"] == "Wait Host":
                sorun.append(f"{where} Wait Host: ajan {r['host']} kullanilamiyor, is calismayacak")
            elif r["status"] == "Wait Condition":
                evs = (r.get("waitingFor") or {}).get("events", [])
                olu = []
                for e in evs:
                    givers = veren.get(e) or ([f"{r['folder']}/{e.split('-TO-')[0]}"] if "-TO-" in e else [])
                    if not any(g in canli for g in givers):
                        olu.append(f"{e} (veren: " + (", ".join(f"{g}={durum.get(g, 'aktif degil')}" for g in givers[:3]) or "tanimli is yok") + ")")
                if olu:
                    sorun.append(f"{where} Wait Condition'da kalacak; olayi verecek calisan bir is yok: {'; '.join(olu)}")
            if r.get("held"):
                sorun.append(f"{where} hold durumunda birakilmis")
            if r.get("note") == "set to OK" and not re.search(r"set ?to ?ok|ok yap|yesile cek", _fold(self.talep)):
                sorun.append(f"{where} set to OK ile yesile cekilmis; is gercekte calismadi")
        # delivered files: what a file transfer job said it sent must be there
        for r in [x for x in rows if x["type"] == "FileTransfer" and x["status"] == "Ended OK" and icinde(x["folder"])][:4]:
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

    def _standartlar(self):
        """Site standards documents (a definition request must follow them), looked for where sites keep them."""
        out = []
        for host in ("ajan1", "ajan2"):
            rc, files = self._sh(host, "find /app /data /opt/ctm /etc/ctm -maxdepth 2 -type f \\( -iname '*standart*' -o -iname '*standard*' "
                                       "-o -iname '*kural*' \\) 2>/dev/null | head -3")
            for f in files.splitlines():
                if f.strip() and not any(f in o for o in out):
                    rc, body = self._sh(host, f"head -c 2500 '{f.strip()}'")
                    if rc == 0 and body:
                        out.append(f"{host}:{f.strip()}\n{body}")
            if out:
                break
        return "\n\n".join(out)[:4000]

    def _kabul_listesi(self, talep):
        """The ticket split into checkable acceptance items by a separate model call; the list lives outside the
        agent's context and is what the finish gate checks item by item."""
        if self.elestirmen is None:
            return []
        self.sayac["kabul"] = self.sayac.get("kabul", 0) + 1
        prompt = ("Asagidaki talebi, ayri ayri dogrulanabilir kabul maddelerine bol. Her madde tek bir istek ya da yasak olsun "
                  "(ornegin: 'X klasorunde Y isi var ve su alanlara sahip', 'bugunun dosyasi hedefte', 'tanim kalici duzeltildi', "
                  "'Z'ye dokunulmadi'). Sayilari, adlari, yollari ve kosullari talepteki gibi aynen koru. Talepte olmayan bir sey "
                  "ekleme, cozum onerme. En cok 12 madde.\n\n## Talep\n" + talep +
                  '\n\nYalnizca JSON yaz: {"maddeler": ["...", "..."]}')
        try:
            out = self.elestirmen.ask_json([{"role": "system", "content": "Talepleri maddelere bolen titiz bir analistsin."},
                                            {"role": "user", "content": prompt}])
        except Exception:  # noqa: BLE001 - without a list the gate still has its own probes
            return []
        items = out.get("maddeler") if isinstance(out, dict) else None
        return [str(m)[:300] for m in items[:12] if str(m).strip()] if isinstance(items, list) else []

    def _elestir(self, rapor):
        """A second, sceptical reader: the ticket, what the harness sees on the site, and the report."""
        self.sayac["elestiri"] += 1
        rows = [r for r in self._statuses() if self._icinde(r["folder"])]
        durum = "\n".join(f"- {r['folder']}/{r['name']} {r['type']} @{r['host']}: {r['status']} kosu={r['numberOfRuns']}" for r in rows) or "aktif is yok"
        if self.kapsam:
            durum += "\n(yalnizca talebin kapsamindaki ve yoneticinin dokundugu klasorler: " + ", ".join(sorted(self.kapsam | self.dokunulan)) + ")"
        tanim = self._tanimlar()
        tanimlar = "\n".join(f"{f}: " + _compact_json(json.dumps(tanim.get(f), ensure_ascii=False), 4000 if f in self.dagitilan else 1500)
                             for f in sorted(self.dagitilan | self.dokunulan | {r["folder"] for r in rows}, key=lambda f: (f not in self.dagitilan, f))[:4])
        eylemler = "\n".join(f"- {x['arac']} {json.dumps(x['girdi'], ensure_ascii=False)[:160]}" for x in self.a.iz if x.get("uygulandi"))[-2500:]
        prompt = (f"Bir Control-M yoneticisinin isini denetliyorsun. Supheci ol: yalnizca asagidaki kanita guven, rapordaki iddiaya degil.\n\n"
                  f"## Talep\n{self.talep}\n\n## Sahadaki durum (harness okudu)\n{durum}\n\n## Tanimlar\n{tanimlar}\n\n"
                  f"## Yapilan eylemler\n{eylemler}\n\n## Yoneticinin raporu\n{rapor}\n\n"
                  + (("## Kabul listesi\n" + "\n".join(f"{i}. {m}" for i, m in enumerate(self.kabul, 1)) + "\n\nHer maddeyi sirayla denetle; "
                      "tanim maddelerini yukaridaki tanimlarla alan alan karsilastir.\n") if getattr(self, "kabul", None) else "") +
                  (("## Site standartlari\n" + self.standart[:2500] + "\n\nYeni ya da degisen tanimlar bu standartlara uyuyor mu, alan alan bak.\n")
                     if getattr(self, "standart", "") else "") +
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
