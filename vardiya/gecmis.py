"""A site's past, generated: 90 days of runs, failures, changes and incidents, written into the local graph.

Until a real scheduler is connected, this is where the error graph gets its history. The failure kinds
are the ones admins keep asking about in public forums (docs/06, section 7): a table lock between two
jobs that write the same table, a service account whose password was rotated, an agent that stopped
answering, a stored procedure that failed without saying so, a file that did not arrive, a change that
broke the next run, a child process that kept the job open, a full disk. Each is placed on purpose, so
the right root cause of every incident is known and the analysis can be checked against it.
"""
import datetime
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
}
# Tables the demo site's jobs write; a site file may carry its own `tables` per job.
TABLES = {"ODM_LOAD_ODEME": ["ODEME_STG"], "ODM_POST_DEFTER": ["DEFTER"], "MHS_LOAD_KUR": ["KUR"],
          "MHS_KUR_FARKI": ["DEFTER", "KUR_FARKI"], "MHS_MUTABAKAT": ["MUTABAKAT"], "KRD_LOAD_SKOR": ["SKOR_STG"],
          "KRD_RISK_HESAP": ["RISK"]}


def _day(today, offset):
    return (today + datetime.timedelta(days=offset)).isoformat()


def build(site, days=90, seed=7, graph=None):
    """Write `days` days of history for `site` (today, env, jobs) into a graph and return (graph, truth).
    `truth` lists every incident with the root cause it was built with."""
    rng = random.Random(seed)
    g = graph or Graph()
    today = datetime.date.fromisoformat(site["today"])
    jobs = [dict(j, tables=j.get("tables") or TABLES.get(j["name"], [])) for j in site["jobs"]]
    by = {j["name"]: j for j in jobs}
    env = site["env"]
    g.add_site(jobs, env.get("connections"))
    start = today - datetime.timedelta(days=days)
    dates = {j["name"]: set(d.isoformat() for d in run_dates(env["calendars"][j["calendar"]]["rule"],
                                                             env.get("holidays", []), start, days + 1))
             for j in jobs}
    base = {j["name"]: rng.uniform(4, 35) for j in jobs}
    slowing = "MHS_MUTABAKAT" if "MHS_MUTABAKAT" in by else sorted(by)[-1]

    # Episodes: (offset in days from today, kind, where). Offsets are working days of the demo site.
    plan = [(-80, "kilit", "MHS_KUR_FARKI"), (-70, "dosya", "MHS_WATCH_KUR"), (-63, "dosya", "MHS_WATCH_KUR"),
            (-64, "parola", "batchusr"), (-52, "kilit", "MHS_KUR_FARKI"), (-44, "host", "app02"),
            (-37, "sessiz", "MHS_MUTABAKAT"), (-35, "dosya", "MHS_WATCH_KUR"), (-29, "degisiklik", "ODM_LOAD_ODEME"),
            (-23, "kilit", "MHS_KUR_FARKI"), (-18, "takili", "KRD_RISK_HESAP"), (-14, "dosya", "MHS_WATCH_KUR"),
            (-9, "disk", "rpr01"), (-7, "dosya", "MHS_WATCH_KUR"), (-1, "kilit", "MHS_KUR_FARKI"),
            (0, "parola", "batchusr")]
    plan = [p for p in plan if p[2] in by or p[1] in ("parola", "host", "disk")]
    failures = {}  # (job, day) -> (kind, error, root node)
    truth = []
    for off, kind, where in plan:
        day = _day(today, off)
        line, cause, fix = CATALOG[kind]
        if kind in ("parola", "host", "disk"):
            attr = {"parola": "run_as", "host": "host", "disk": "host"}[kind]
            hit = sorted(n for n, j in by.items() if j[attr] == where and day in dates[n])
            root = f"{'user' if kind == 'parola' else 'host'}:{where}"
        else:
            hit, root = ([where] if day in dates[where] else []), None
        for n in hit:
            j = by[n]
            err = line.format(table=(j["tables"] or ["?"])[0], user=j["run_as"], host=j["host"], rows=0,
                              expected=48000, path=j.get("command") or "/data/?", minutes=j.get("timeout") or 180,
                              proc="java")
            if kind == "kilit":
                root = f"table:{j['tables'][0]}"
            if kind == "degisiklik":
                new = (j["command"] or "/opt/x.sh").replace(".sh", "_v2.sh")
                err = line.format(path=new)
                root = g.add_change(f"CHG-{1800 + abs(off)}", n, _day(today, off - 1), f"komut: {j['command']} -> {new}")
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
            f = failures.get((n, day))
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
    g.commit()
    return g, truth


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
