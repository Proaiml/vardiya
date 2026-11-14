"""A site's past, generated: 90 days of runs, failures, changes and incidents, written into the local graph.

Until a real scheduler is connected, this is where the error graph gets its history. The failure kinds
are the ones admins keep asking about in public forums (docs/06, section 7): a table lock between two
jobs that write the same table, a service account whose password was rotated, an agent that stopped
answering, a stored procedure that failed without saying so, a file that did not arrive, a change that
broke the next run, a child process that kept the job open, a full disk. Each is placed on purpose, so
the right root cause of every incident is known and the analysis can be checked against it.
"""
import datetime
import pathlib
import random

from .graph import Graph
from .repo import run_dates

# kind: (error line, cause, the fix that addresses the cause)
CATALOG = {
    "kilit": ("ORA-00054: resource busy and acquire with NOWAIT specified or timeout expired (table {table})",
              "ayni tabloya ayni anda yazan iki is", "iki isi ortak bir kilit kaynagina bagla (Control-M: Resource, "
              "JS7: Resource Lock); yeniden calistirma yalnizca o geceyi kurtarir"),
    "parola": ("Logon failure: the user name or password is incorrect (user {user})",
               "servis hesabinin parolasi degistirildi, agent'in parola deposu eski", "agent parola deposunu yeni "
               "parolayla guncelle (ctmpwd), sonra bekleyen isleri yeniden calistir"),
    "host": ("Wait host: agent on {host} is not responding; no available agent for the job",
             "agent sureci durmus", "agent'i yeniden baslat (start-ag), ctmping ile dogrula"),
    "sessiz": ("rc=0 but target table {table} has {rows} rows (expected about {expected})",
               "saklı yordam hatayi yutuyor, is basarili gorunuyor", "yordamin hatayi yukseltmesini sagla "
               "(THROW/RAISE, commit), veriyi temizleyip yeniden yukle"),
    "dosya": ("File watcher: {path} did not arrive within {minutes} minutes",
              "kaynak sistem dosyayi gec gonderiyor", "kaynak sistemin sahibine haber ver; dosya gelince zinciri "
              "serbest birak, bos dosyayla devam etme"),
    "degisiklik": ("/bin/sh: {path}: not found (exit 127)", "son tanim degisikligi var olmayan bir betigi gosteriyor",
                   "tanimi onceki surume geri al, sonra degisikligi dogru yolla yeniden iste"),
    "takili": ("job still running after {minutes} min: child process {proc} keeps the job open",
               "betik bir alt sureci beklemeden cikiyor", "betigi alt sureci bekleyecek bicimde duzelt (start /wait, "
               "wait), takili isi sonlandir"),
    "disk": ("write error: No space left on device ({host}:/data)", "sunucuda disk doldu",
             "eski cikti ve raporlari temizle, sonra yeniden calistir"),
    # from the BMC Community Control-M topic (docs/06, section 7.1)
    "kaynak": ("Wait resource: {resource} has 0 of 2 free for {minutes} min; holders ended hours ago",
               "kaynagi tutan isler bitmis ama kaynak serbest birakilmamis (asili kayit)",
               "bekleme nedenini dogrula (ctmwhy, is gunlugunde Wait Resource kodu 5120); kaynaklar bossa isi bir kez "
               "hold edip free et ki yeniden degerlendirilsin; asili kayit varsa serbest birak; havuz sinirini yukseltme"),
    "yama": ("{job} failed after reboot on {host}: the application was unable to start correctly (0xc0000142)",
             "sunucuya isletim sistemi yamasi yuklendi, betik calistiricisi bozuldu",
             "yamanin etkisini dogrula, betik calistiricisini onar ya da yamayi geri al; agent'i yeniden baslat"),
    "setok": ("ORA-01403: no data found in {table} (staging bos)",
              "oncul is hata verdi ama elle basarili sayildi (Set OK); veri hic yuklenmedi",
              "once oncul isi duzeltip calistir, sonra bu isi yeniden calistir; Set OK zinciri yesil gosterir ama "
              "veriyi getirmez"),
    # classes that are frequent in other schedulers' questions (AutoSys, Airflow; docs/06, section 7.2)
    "tarih": ("Wait condition: {pred}-ENDED-OK for order date {odate} not found; the condition was added with order "
              "date {prev}",
              "oncul is New Day'i gecti; kosulunu bir onceki siparis tarihiyle uretti, ardil kendi tarihini bekliyor",
              "kosulu dogru tarihle elle ekle ve ardili serbest birak; kalici cozum: iki isi ayni siparis tarihiyle "
              "siparis et ya da kosula +1 gun kaydirma ver"),
    "mukerrer": ("{job} is already running (2 instances); duplicate transfer of {path}",
                 "ayni is ikinci kez siparis edildi, iki kopya ayni anda calisti",
                 "ikinci kopyayi durdur, hedefteki mukerrer veriyi temizle; ise 'ayni anda tek kopya' kurali koy ve "
                 "elle siparisten once aktif kopyayi kontrol et"),
    "zaman": ("{job} terminated: exceeded max run time of {limit} min (killed)",
              "isin suresi haftalardir uzuyor, sure siniri artan hacme yetismedi",
              "yeniden calistirmadan once sureyi uzatan nedeni (hacim, plan) incele; siniri son 30 calismanin %90'i "
              "arti pay olarak guncelle"),
    "aktarim": ("{job}: com.jcraft.jsch.JSchException: Session.connect: java.net.SocketException: Connection reset "
                "(profile {connection})",
                "karsi tarafta anahtar ya da algoritma degisti, baglanti profili guncel degil",
                "baglanti profilini karsi tarafla dogrula ve profilden baglanti testi yap"),
    "plan": ("{job} was not ordered on {day}: daily plan load did not complete",
             "gunluk plan yuklemesi (New Day) yarida kaldi",
             "plan yuklemesinin gunlugunu incele, eksik isleri takvimlerine gore toplu yeniden sirala; tek tek elle "
             "siparis etme"),
}
# How each kind shows itself across products and wordings: the generalised part of each solver. A signature
# matches a kind by these signs, not by looking like one particular error line.
SIGNS = {
    "kilit": ("lock", "resource busy", "nowait", "deadlock", "kilit", "ora-00054", "55p03", "timeout period exceeded"),
    "parola": ("logon failure", "password", "parola", "1326", "authentication failed", "login failed", "credentials"),
    "host": ("agent", "unavailable", "not responding", "wait host", "communication", "unreachable", "data pipe",
             "certification path", "sslhandshake"),
    "sessiz": ("rc=0", "return code 0", "row count", "rows (expected", "expected about", "beklenen"),
    "dosya": ("did not arrive", "not arrive", "file watcher", "no file matching", "dosya gelmedi"),
    "degisiklik": ("not found", "no such file", "exit 127", "rc 127", "command not found"),
    "takili": ("still running", "exceeded", "child process", "process tree", "hang", "keeps the job open"),
    "disk": ("no space", "not enough space", "disk full", "enospc", "disk dolu"),
    "kaynak": ("quantitative", "wait resource", "available 0", "0 of 2 free", "waiting for resource", "code 5120",
               "no free slots", "pool slots"),
    "yama": ("cscript", "after reboot", "patch", "yama", "cannot execute the specified program"),
    "setok": ("no data found", "no rows", "ora-01403", "nothing to post", "staging bos"),
    "tarih": ("order date", "odate", "execution_date", "logical date", "wait condition", "condition was added",
              "data interval"),
    "mukerrer": ("already running", "2 instances", "duplicate", "two instances", "max_active_runs", "overlap",
                 "previous instance"),
    "zaman": ("max run time", "timed out", "execution_timeout", "term_run_time", "killed", "sigkill", "terminated"),
    "plan": ("not ordered", "daily plan", "new day", "not scheduled", "was not triggered", "plan load"),
}
NEW_DAY = 7 * 60  # the plan day turns at 07:00 (Control-M New Day default)

# The classes are data: skills/olay-siniflari/SKILL.md. What is written above is the error line each class
# produces in the generated history; cause, fix and signs come from the skill when it is there.
SKILLS_DIR = pathlib.Path(__file__).resolve().parent.parent / "skills"


def classes():
    from .skills import load_incident_classes
    loaded = load_incident_classes(SKILLS_DIR)
    out = {k: {"title": k, "signs": list(SIGNS.get(k, ())), "cause": cause, "fix": fix, "harmful": [], "evidence": []}
           for k, (_, cause, fix) in CATALOG.items()}
    out.update(loaded)
    return out


_C = classes()
CATALOG = {k: (CATALOG[k][0] if k in CATALOG else "", c["cause"], c["fix"]) for k, c in _C.items()}
SIGNS = {k: tuple(c["signs"]) for k, c in _C.items()}
# Quantitative resources the demo site's jobs need (Control-M: Resource, JS7: Resource Lock).
RESOURCES = {"MHS_KUR_FARKI": ["DB_YAZMA"], "MHS_MUTABAKAT": ["DB_YAZMA"], "ODM_POST_DEFTER": ["DB_YAZMA"]}
# Tables the demo site's jobs write; a site file may carry its own `tables` per job.
TABLES = {"ODM_LOAD_ODEME": ["ODEME_STG"], "ODM_POST_DEFTER": ["DEFTER"], "MHS_LOAD_KUR": ["KUR"],
          "MHS_KUR_FARKI": ["DEFTER", "KUR_FARKI"], "MHS_MUTABAKAT": ["MUTABAKAT"], "KRD_LOAD_SKOR": ["SKOR_STG"],
          "KRD_RISK_HESAP": ["RISK"]}


def _day(today, offset):
    return (today + datetime.timedelta(days=offset)).isoformat()


def rename_site(site, names):
    """The same site with jobs, hosts, users, tables and resources renamed: to test that a solver does not
    depend on the names it was written against."""
    import json as _json
    import re as _re
    text = _json.dumps(site, ensure_ascii=False)
    for old in sorted(names, key=len, reverse=True):
        text = _re.sub(rf"(?<![A-Za-z0-9_]){_re.escape(old)}(?![A-Za-z0-9_])", names[old], text)
    return _json.loads(text)


def build(site, days=90, seed=7, graph=None, names=None, wording=None):
    """Write `days` days of history for `site` (today, env, jobs) into a graph and return (graph, truth).
    `truth` lists every incident with the root cause it was built with. `names` is the renaming the site went
    through (rename_site), so the episode plan follows it; `wording` replaces error lines by kind."""
    rng = random.Random(seed)
    rn = (lambda x: (names or {}).get(x, x))
    tables = {rn(k): [rn(t) for t in v] for k, v in TABLES.items()}
    resources = {rn(k): [rn(t) for t in v] for k, v in RESOURCES.items()}
    lines = {k: (wording or {}).get(k, v[0]) for k, v in CATALOG.items()}
    g = graph or Graph()
    today = datetime.date.fromisoformat(site["today"])
    jobs = [dict(j, tables=j.get("tables") or tables.get(j["name"], []),
                 resources=j.get("resources") or resources.get(j["name"], [])) for j in site["jobs"]]
    by = {j["name"]: j for j in jobs}
    env = site["env"]
    g.add_site(jobs, env.get("connections"))
    start = today - datetime.timedelta(days=days)
    dates = {j["name"]: set(d.isoformat() for d in run_dates(env["calendars"][j["calendar"]]["rule"],
                                                             env.get("holidays", []), start, days + 1))
             for j in jobs}
    base = {j["name"]: rng.uniform(4, 35) for j in jobs}
    slowing = rn("MHS_MUTABAKAT") if rn("MHS_MUTABAKAT") in by else sorted(by)[-1]

    # Episodes: (offset in days from today, kind, where). Offsets are working days of the demo site.
    plan = [(-80, "kilit", "MHS_KUR_FARKI"), (-70, "dosya", "MHS_WATCH_KUR"), (-63, "dosya", "MHS_WATCH_KUR"),
            (-64, "parola", "batchusr"), (-52, "kilit", "MHS_KUR_FARKI"), (-44, "host", "app02"),
            (-37, "sessiz", "MHS_MUTABAKAT"), (-35, "dosya", "MHS_WATCH_KUR"), (-29, "degisiklik", "ODM_LOAD_ODEME"),
            (-31, "setok", "ODM_POST_DEFTER"), (-21, "yama", "app01"), (-16, "kaynak", "MHS_MUTABAKAT"),
            (-23, "kilit", "MHS_KUR_FARKI"), (-18, "takili", "KRD_RISK_HESAP"), (-14, "dosya", "MHS_WATCH_KUR"),
            (-10, "aktarim", "KRD_TEDARIK_AL"), (-4, "mukerrer", "ODM_BANKA_GONDER"), (-3, "tarih", "KRD_RAPOR"), (-2, "zaman", "MHS_MUTABAKAT"),
            (-9, "disk", "rpr01"), (-7, "dosya", "MHS_WATCH_KUR"), (-1, "kilit", "MHS_KUR_FARKI"),
            (0, "parola", "batchusr")]
    plan = [(o, k, rn(w)) for o, k, w in plan]
    plan = [p for p in plan if p[2] in by or p[1] in ("parola", "host", "disk", "yama")]
    set_ok = {}  # (job, day): the predecessor's failed run an operator marked OK
    long_run = {}  # (job, day): minutes of a predecessor run that crossed New Day
    failures = {}  # (job, day) -> (kind, error, root node)
    truth = []
    for off, kind, where in plan:
        day = _day(today, off)
        _, cause, fix = CATALOG[kind]
        line = lines[kind]
        if kind in ("parola", "host", "disk", "yama"):
            attr = {"parola": "run_as", "host": "host", "disk": "host", "yama": "host"}[kind]
            hit = sorted(n for n, j in by.items() if j[attr] == where and day in dates[n])
            root = f"{'user' if kind == 'parola' else 'host'}:{where}"
            if kind == "yama":
                root = g.add_host_change(f"YAMA-{day[:7]}", where, _day(today, off - 1),
                                         "isletim sistemi guvenlik yamalari yuklendi, sunucu yeniden baslatildi")
                first = [n for n in hit if not any(d in hit for d in by[n]["deps"])]
                hit = first or hit[:1]
        else:
            hit, root = ([where] if day in dates[where] else []), None
        for n in hit:
            j = by[n]
            err = line.format(table=(j["tables"] or ["?"])[0], user=j["run_as"], host=j["host"], rows=0,
                              expected=48000, path=j.get("command") or "/data/?", minutes=j.get("timeout") or 180,
                              proc="java", resource=(j["resources"] or ["?"])[0], job=n,
                              pred=(j["deps"] or ["?"])[0], odate=day[5:7] + day[8:], limit=8,
                              connection=j.get("connection") or "?",
                              prev=_day(datetime.date.fromisoformat(day), -1)[5:7] + _day(datetime.date.fromisoformat(day), -1)[8:])
            if kind == "kilit":
                root = f"table:{j['tables'][0]}"
            if kind == "degisiklik":
                new = (j["command"] or "/opt/x.sh").replace(".sh", "_v2.sh")
                err = line.format(path=new)
                root = g.add_change(f"CHG-{1800 + abs(off)}", n, _day(today, off - 1), f"komut: {j['command']} -> {new}")
            if kind == "tarih":
                pred = j["deps"][0]
                long_run[(pred, day)] = NEW_DAY + 40 - _clock(by[pred]["time"])
                root = f"run:{pred}@{day}#1"
            if kind == "mukerrer":
                root = g.add_change(f"ELLE-{day[5:7]}{day[8:]}", n, day,
                                    "is elle, bagimsiz akis olarak yeniden siparis edildi (calisan kopya varken)",
                                    by="operator")
            if kind == "zaman":
                root = f"job:{n}"
            if kind == "aktarim":
                root = f"connection:{j['connection']}"
            if kind == "kaynak":
                root = f"resource:{j['resources'][0]}"
                err = line.format(resource=j["resources"][0], minutes=95)
            if kind == "setok":
                pred = j["deps"][0]
                set_ok[(pred, day)] = True
                root = f"run:{pred}@{day}#1"
                err = line.format(table=(by[pred]["tables"] or ["STAGING"])[0])
            if kind == "sessiz":
                root = g.add_change(f"CHG-{1800 + abs(off)}", n, _day(today, off - 2),
                                    "yordama TRY/CATCH eklendi, hata kaydi tabloya yaziliyor")
            failures[(n, day)] = (kind, err, root)
        if hit:
            truth.append({"key": f"OLAY-{len(truth) + 1:03d}", "day": day, "kind": kind, "jobs": hit, "root": root,
                          "cause": cause, "fix": fix, "open": off >= -1})

    # Runs, in dependency order each day; a failed job holds back the jobs that wait for it.
    order = _topo(by)
    run_ids = {}
    for i in range(days + 1):
        day = _day(start, i)
        done_ok = set()
        for n in order:
            if day not in dates[n] or day > site["today"]:
                continue
            j = by[n]
            if any(d in by and day in dates[d] and d not in done_ok for d in j["deps"]):
                continue  # waiting for a predecessor that did not end OK
            age = (today - datetime.date.fromisoformat(day)).days
            minutes = base[n] * rng.lognormvariate(0, 0.15)
            if day[8:] >= "28" and j["type"] == "veritabani":
                minutes *= 1.6  # month-end volume
            if n == slowing and age < 35:
                minutes *= 1 + 0.018 * (35 - age)  # a job that has been slowing down for five weeks
            if (n, day) in long_run:
                minutes = long_run[(n, day)]
            f = failures.get((n, day))
            if set_ok.get((n, day)):  # failed, then marked OK by hand: green downstream, empty underneath
                run_ids[(n, day)] = g.add_run(n, day, True, minutes * 0.4, set_ok=True, rc=2,
                                              error="ORA-12541: TNS:no listener (exit 2) - Set OK yapildi")
                done_ok.add(n)
                continue
            if f is None:
                run_ids[(n, day)] = g.add_run(n, day, True, minutes)
                done_ok.add(n)
                continue
            kind, err, _ = f
            if kind == "sessiz":  # ends OK, wrongly: the damage shows downstream
                run_ids[(n, day)] = g.add_run(n, day, True, minutes * 0.3, error=None)
                g.add_run(n, day, False, minutes * 0.3, error=err, rc=0, attempt=2)
                run_ids[(n, day)] = f"run:{n}@{day}#2"
                done_ok.add(n)
                continue
            if kind == "takili":
                minutes = 340
            run_ids[(n, day)] = g.add_run(n, day, False, minutes, error=err, rc={"degisiklik": 127}.get(kind, 1))
            if kind in ("dosya",) and day != site["today"]:
                g.add_run(n, day, True, minutes + rng.uniform(60, 150), attempt=2)  # the file came late
                done_ok.add(n)

    for t in truth:
        line, cause, fix = CATALOG[t["kind"]]
        runs = [run_ids[(n, t["day"])] for n in t["jobs"] if (n, t["day"]) in run_ids]
        if t["open"]:
            fix_done, verified = None, False
        elif t["kind"] == "kilit" and t["day"] < _day(today, -20):
            fix_done, verified = "isi yeniden calistir (rerun)", False  # what the night shift did: it came back
        elif t["kind"] == "dosya":
            fix_done, verified = "dosya gelince zinciri serbest birak", True
        else:
            fix_done, verified = fix, True
        if t["kind"] == "kilit" and t["day"] == _day(today, -23):
            fix_done, verified = "isi yeniden calistir (rerun)", False
        g.add_incident(t["key"], t["day"], runs, t["root"], cause, fix_done, verified,
                       minutes=None if t["open"] else rng.randint(15, 140))
    _disk(g, env, today, days, rng, names)
    g.commit()
    return g, truth


def _clock(hhmm):
    return int(hhmm[:2]) * 60 + int(hhmm[3:])


def _disk(g, env, today, days, rng, names=None):
    """Daily disk use per host, in percent. rpr01 fills up and is cleaned (the disk incident); etl01 has been
    growing for a month, the way an agent's own logs grow (BMC Community: XT_*.log over 60 GB)."""
    for h in env["hosts"]:
        series, level = [], rng.uniform(35, 55)
        role = {"rpr01": "full", "etl01": "growing"}.get(h) or {v: k for k, v in (names or {}).items()}.get(h)
        for i in range(days + 1):
            day = _day(today, i - days)
            age = days - i
            if role in ("full", "rpr01"):  # fills up over two months, full on the disk incident day, then cleaned
                level = min(99.5, 48 + 0.9 * (days - age)) if age >= 9 else 44 + 0.1 * (9 - age)
            elif role in ("growing", "etl01") and age < 30:
                level = 52 + 1.1 * (30 - age) + rng.uniform(-0.4, 0.4)
            else:
                level = max(20, min(70, level + rng.uniform(-0.6, 0.6)))
            series.append([day, round(level, 1)])
        g.node("host", h, disk=series)


def _topo(by):
    seen, out = set(), []

    def visit(n):
        if n in seen:
            return
        seen.add(n)
        for d in by[n]["deps"]:
            if d in by:
                visit(d)
        out.append(n)

    for n in sorted(by):
        visit(n)
    return out
