"""Scheduler Admin Bench: parametric request scenarios.

Each scenario is a seeded site plus one situation that is built on purpose, so the
expected outcome is true by construction. Nothing here calls the checks under test.
"""
import datetime
import json
import pathlib
import random

from .repo import run_dates

FOLDERS = [("ODEME_GUNLUK", "ODM_", "odeme"), ("RAPOR", "RPR_", "rapor"), ("MUHASEBE", "MHS_", "muhasebe"),
           ("KREDI", "KRD_", "kredi"), ("HAZINE", "HZN_", "hazine"), ("MUSTERI", "MST_", "musteri")]
HOSTS = {"app01": (["batchusr", "appusr"], "uygulama sunucusu 1"), "app02": (["batchusr", "appusr"], "uygulama sunucusu 2"),
         "db01": (["dbbatch"], "veritabani sunucusu"), "rpr01": (["rprusr"], "raporlama sunucusu"),
         "etl01": (["etlusr", "batchusr"], "veri aktarim sunucusu")}
CALENDARS = {
    "HERGUN": ({"type": "daily"}, "haftanin her gunu, tatiller dahil"),
    "IS_GUNU": ({"type": "workdays"}, "pazartesiden cumaya, resmi tatiller haric"),
    "HAFTA_SONU": ({"type": "weekly", "days": [5, 6]}, "cumartesi ve pazar"),
    "PAZARTESI": ({"type": "weekly", "days": [0]}, "her pazartesi, tatil olsa da"),
    "AY_SONU_IS_GUNU": ({"type": "month_end_workday"}, "her ayin son is gunu"),
    "AY_BASI_IS_GUNU": ({"type": "month_day", "day": 1, "shift": "next"}, "her ayin ilk is gunu"),
    "AYIN_15I": ({"type": "month_day", "day": 15, "shift": "next"},
                 "her ayin 15. gunu; tatile ya da hafta sonuna gelirse sonraki is gunu"),
}
# How requesters actually write run days. Each phrase has exactly one right calendar.
PHRASES = {
    "HERGUN": ["her gün", "haftanın yedi günü, tatiller dahil", "tatil dahil her gün çalışsın", "her gun, hafta sonu da dahil"],
    "IS_GUNU": ["hafta içi her gün", "pazartesiden cumaya, resmi tatiller hariç", "sadece iş günlerinde",
                "hafta ici her gun, resmi tatillerde calismasin", "mesai günleri"],
    "HAFTA_SONU": ["cumartesi ve pazar", "sadece hafta sonları", "hafta sonu iki gün de"],
    "PAZARTESI": ["her pazartesi", "haftada bir, pazartesi günleri", "haftanın ilk günü (pazartesi), tatil de olsa"],
    "AY_SONU_IS_GUNU": ["her ayın son iş günü", "ay sonu kapanışında, ayın son çalışma gününde", "her ayin son is gunu",
                        "ayın son mesai günü"],
    "AY_BASI_IS_GUNU": ["her ayın ilk iş günü", "ay başında, ilk çalışma gününde", "ayın ilk mesai günü"],
    "AYIN_15I": ["her ayın 15'inde, tatile denk gelirse ertesi iş günü", "ayın on beşi; hafta sonuna gelirse sonraki iş günü",
                 "her ayin 15. gunu (tatilse bir sonraki is gunu)"],
}
# Run days no calendar of the site provides: the right move is to return the request.
NO_CALENDAR = ["her ayın ilk pazartesi günü", "iki haftada bir cuma", "her çeyreğin son günü", "salı ve perşembe günleri",
               "her ayın 10'unda", "yılda bir kez, 31 Aralık'ta", "çarşamba hariç hafta içi her gün",
               "her ayın son cuma günü"]
# Held-out phrases. They were written before any prompt or strategy was tuned and are never used
# while tuning; the tuning set is PHRASES / NO_CALENDAR above ("dev"), this is "test".
PHRASES_TEST = {
    "HERGUN": ["haftanın her günü", "pazar dahil her gün, bayramda da", "istisnasız her gün bir kez"],
    "IS_GUNU": ["hafta içi günlerde (tatiller hariç)", "pazartesi-cuma arası, bayram ve resmi tatillerde çalışmaz",
                "yalnızca iş günleri"],
    "HAFTA_SONU": ["her cumartesi ve her pazar", "hafta sonu günlerinde", "cumartesi-pazar"],
    "PAZARTESI": ["her hafta pazartesi günü", "pazartesileri", "haftalık, pazartesi"],
    "AY_SONU_IS_GUNU": ["ayın son iş gününde", "her ay sonunda, son iş günü", "aylık kapanış: ayın son çalışma günü"],
    "AY_BASI_IS_GUNU": ["ayın ilk iş gününde", "her ay, ilk iş günü", "ay başı ilk mesai günü"],
    "AYIN_15I": ["her ayın 15'i (tatile gelirse takip eden iş günü)",
                 "ayın 15. günü, hafta sonu ya da tatilse sonraki iş günü",
                 "15'inde; iş günü değilse bir sonraki iş gününe kaysın"],
}
NO_CALENDAR_TEST = ["her ayın ikinci salı günü", "üç ayda bir, ayın ilk günü", "her ayın 20'sinde", "pazartesi ve çarşamba",
                    "cuma hariç her gün", "ayda iki kez, 1'inde ve 16'sında", "her ayın son perşembesi",
                    "yılbaşından önceki son iş günü"]
STEMS = ["WATCH_DOSYA", "LOAD_STG", "POST_DEFTER", "MUTABAKAT", "OZET_RAPOR", "ARSIV", "KONTROL", "AKTARIM"]
NEW_STEMS = ["LOAD_IADE", "KUR_FARKI", "GUN_SONU", "TEMIZLIK", "YEDEK", "BILDIRIM", "DOGRULAMA", "ENVANTER",
             "KAPANIS", "HESAPLAMA"]
TODAYS = ["2026-11-13", "2026-12-01", "2027-01-18", "2027-02-22"]
HOLIDAYS = ["2026-10-29", "2026-12-31", "2027-01-01", "2027-04-23", "2027-05-19"]
ORDER = ["klasor", "is_adi", "tip", "host", "calistiran", "komut", "gunler", "saat", "bagimlilik", "bildirim", "aciklama"]
KEY_OF = {"folder": "klasor", "name": "is_adi", "type": "tip", "host": "host", "run_as": "calistiran",
          "command": "komut", "calendar": "gunler", "time": "saat", "deps": "bagimlilik", "notify": "bildirim",
          "description": "aciklama"}
FAMILIES = ("yeni", "degisiklik", "takvim", "t-takvim", "t-dongu", "t-mevcut", "t-olmayan", "t-standart", "t-sablon",
            "t-referans", "kaldir", "t-bagimli", "aciklamali", "t-celiski", "t-belirsiz", "t-uyumsuz")
COVER_DAYS = 400  # a job fits its predecessor if every run date in this window is one of the predecessor's
APPLIED = ("yeni", "degisiklik", "takvim", "kaldir", "aciklamali")  # families where the right move is to act
# Run days written too vaguely to act on. A site calendar may look close ("ay sonunda" next to a
# last-working-day calendar), but the requester did not say it; the right move is to ask.
VAGUE = ["ay sonunda", "ay başında", "haftada bir", "ayda bir", "haftada iki gün", "hafta sonu bir gün", "ayın ortasında",
         "uygun bir günde", "gerektiğinde", "ay sonuna doğru", "ara sıra", "yoğun olmayan günlerde", "her ay",
         "haftanın belli günleri", "tatil olmayan günlerde ama cuma şart değil"]
# What a requester writes in the description about when a job runs, by calendar.
SAYS = {"HERGUN": "her gün, hafta sonu dahil çalışır", "IS_GUNU": "yalnızca iş günlerinde çalışır",
        "HAFTA_SONU": "yalnızca hafta sonları çalışır", "PAZARTESI": "haftada bir, pazartesi günleri çalışır",
        "AY_SONU_IS_GUNU": "ayda bir kez, ayın son iş günü çalışır",
        "AY_BASI_IS_GUNU": "ayda bir kez, ayın ilk iş günü çalışır"}


EXT_FILE = pathlib.Path(__file__).resolve().parent.parent / "scenarios" / "talep" / "_ifadeler-gemma4.json"


def phrase_sets(split):
    """(phrases by calendar, phrases no calendar provides) for a split.
    dev: tuning set. test: same author, written before tuning. ext: written by a different author
    (a local model), curated by hand; the only set whose wording the harness author did not choose."""
    if split == "test":
        return PHRASES_TEST, NO_CALENDAR_TEST
    if split in ("ext", "ext2"):
        # ext: written by gemma4, used while tuning the consistency gate.
        # ext2: written by Gemini 4 Hydrogen after the gate was frozen; nothing was tuned on it.
        file = EXT_FILE if split == "ext" else EXT_FILE.with_name("_ifadeler-hydrogen.json")
        data = json.loads(file.read_text(encoding="utf-8"))
        return data["phrases"], data["no_calendar"]
    return PHRASES, NO_CALENDAR


def vague_phrases(split):
    """Vague run-day phrases for a split: the other-author files may carry their own list."""
    if split in ("ext", "ext2"):
        file = EXT_FILE if split == "ext" else EXT_FILE.with_name("_ifadeler-hydrogen.json")
        return json.loads(file.read_text(encoding="utf-8")).get("vague") or VAGUE
    return VAGUE


def _hhmm(minutes):
    return f"{minutes // 60 % 24:02d}:{minutes % 60:02d}"


def _fits(site):
    """fits(a, b): every run date of calendar a is a run date of calendar b, seen from the site's today."""
    today = datetime.date.fromisoformat(site["today"])
    dates = {n: set(run_dates(c["rule"], site["env"]["holidays"], today, COVER_DAYS))
             for n, c in site["env"]["calendars"].items()}
    return lambda a, b: a not in dates or b not in dates or dates[a] <= dates[b]


def _widen(site, name, calendar, fits=None):
    """Make job `name` run on every day of `calendar`, and its predecessors with it. A job ordered
    on a day its predecessor is not would wait for ever; no scenario may start from such a site."""
    fits, job = fits or _fits(site), next((j for j in site["jobs"] if j["name"] == name), None)
    if job is None or fits(calendar, job["calendar"]):
        return
    job["calendar"] = "HERGUN"
    for dep in job["deps"]:
        _widen(site, dep, "HERGUN", fits)


def _narrow(site, name, calendar, fits=None):
    """Make job `name` run on `calendar` only, and the jobs that wait for it with it."""
    fits, job = fits or _fits(site), next(j for j in site["jobs"] if j["name"] == name)
    job["calendar"] = calendar
    for j in site["jobs"]:
        if name in j["deps"] and not fits(j["calendar"], calendar):
            _narrow(site, j["name"], calendar, fits)


def _room(site, d):
    """Adjust the site, never the request, so that the requested job fits every predecessor it names."""
    fits = _fits(site)
    for dep in d.get("deps") or []:
        if dep != d.get("name"):
            _widen(site, dep, d.get("calendar"), fits)
    return d


def consistent(site, extra=None):
    """True if no job of the site (with definition `extra` in place of its namesake) runs on a day
    one of its predecessors does not."""
    fits, jobs = _fits(site), {j["name"]: j for j in site["jobs"]}
    if extra:
        jobs[extra["name"]] = extra
    return all(fits(j["calendar"], jobs[dep]["calendar"]) for j in jobs.values() for dep in j["deps"] if dep in jobs)


def make_site(rng):
    folders = rng.sample(FOLDERS, 3)
    hosts = dict(rng.sample(sorted(HOSTS.items()), 4))
    jobs = []
    for fi, (folder, prefix, team) in enumerate(folders):
        clock = 60 + 15 * fi
        chain = []
        for i, stem in enumerate(rng.sample(STEMS, rng.randint(3, 4))):
            host = rng.choice(sorted(hosts))
            deps = [chain[-1]] if chain else []
            if len(chain) >= 2 and rng.random() < 0.3:
                deps.append(chain[0])
            name = prefix + stem
            jobs.append({"name": name, "folder": folder, "type": "dosya_izleme" if i == 0 else "komut", "host": host,
                         "run_as": rng.choice(hosts[host][0]),
                         "command": f"/opt/{team}/bin/{stem.lower()}.sh" if i else f"/data/{team}/gelen/{stem.lower()}.csv",
                         "calendar": rng.choice(["IS_GUNU", "IS_GUNU", "HERGUN"]), "time": _hhmm(clock),
                         "deps": sorted(deps), "notify": f"{team}-nobet@ornek.local",
                         "description": f"{team} {stem.lower().replace('_', ' ')} isi"})
            chain.append(name)
            clock += rng.choice([30, 45, 60])
    first_chain = [j for j in jobs if j["folder"] == folders[0][0]]
    bridge = next(j for j in jobs if j["folder"] == folders[1][0] and j["type"] == "komut")
    bridge["deps"] = sorted(set(bridge["deps"]) | {first_chain[-1]["name"]})  # one dependency across folders
    env = {"hosts": {h: {"users": u, "desc": d} for h, (u, d) in hosts.items()},
           "calendars": {n: {"rule": r, "desc": d} for n, (r, d) in CALENDARS.items()},
           "folders": {f: {"prefix": p} for f, p, _ in folders},
           "standards": {"name_regex": "[A-Z][A-Z0-9_]{3,29}", "notify_suffix": "@ornek.local"},
           "holidays": HOLIDAYS}
    site = {"today": rng.choice(TODAYS), "env": env, "jobs": jobs, "_folders": folders}
    fits = _fits(site)
    for j in jobs:
        for dep in j["deps"]:
            _widen(site, dep, j["calendar"], fits)
    return site


def _descendants(jobs, name):
    out, frontier = set(), {name}
    while frontier:
        frontier = {j["name"] for j in jobs if frontier & set(j["deps"])} - out
        out |= frontier
    return out


def _form(no, team, op, fields):
    lines = [f"talep_no: {no}", f"talep_eden: {team}-ekibi", f"islem: {op}"]
    for k in ORDER:
        if k in fields:
            v = fields[k]
            lines.append(f"{k}: " + ("[" + ", ".join(v) + "]" if isinstance(v, list) else str(v)))
    return lines


def _fields(d):
    return {KEY_OF[k]: v for k, v in d.items()}


def _new_job(rng, site):
    folder, prefix, team = rng.choice(site["_folders"])
    taken = {j["name"] for j in site["jobs"]}
    name = next(prefix + s for s in rng.sample(NEW_STEMS, len(NEW_STEMS)) if prefix + s not in taken)
    host = rng.choice(sorted(site["env"]["hosts"]))
    peers = [j for j in site["jobs"] if j["folder"] == folder]
    deps = sorted(j["name"] for j in rng.sample(peers, rng.randint(0, min(2, len(peers)))))
    latest = max([int(j["time"][:2]) * 60 + int(j["time"][3:]) for j in peers if j["name"] in deps] or [120])
    stem = name[len(prefix):].lower()
    return {"name": name, "folder": folder, "type": "komut", "host": host,
            "run_as": rng.choice(site["env"]["hosts"][host]["users"]), "command": f"/opt/{team}/bin/{stem}.sh",
            "calendar": rng.choice(["IS_GUNU", "HERGUN", "HAFTA_SONU", "PAZARTESI"]),
            "time": _hhmm(latest + rng.choice([15, 30, 45])), "deps": deps,
            "notify": f"{team}-nobet@ornek.local", "description": f"{team} {stem.replace('_', ' ')} isini calistirir"}, team


def _team(site, job):
    return next(t for f, _, t in site["_folders"] if f == job["folder"])


def build(family, rng, site, split="dev"):
    """Return (title, request lines, expected) for one situation of `family`."""
    jobs, env = site["jobs"], site["env"]
    phrases, no_calendar = phrase_sets(split)
    no = f"CHG-{rng.randint(1000, 9999)}"
    applied = lambda d: {"outcome": "applied", "definition": d}
    returned = lambda why: {"outcome": "returned", "reason": why}

    if family == "yeni":
        d, team = _new_job(rng, site)
        return "Eksiksiz yeni is talebi", _form(no, team, "yeni", _fields(d)), applied(_room(site, d))

    if family == "degisiklik":
        job = rng.choice(jobs)
        team, kind = _team(site, job), rng.choice(["time", "command", "calendar", "host", "deps", "notify"])
        if kind == "time":
            change = {"time": _hhmm(int(job["time"][:2]) * 60 + int(job["time"][3:]) + rng.choice([15, 30, 90]))}
        elif kind == "command":
            change = {"command": job["command"].replace(".sh", "_v2.sh").replace(".csv", "_v2.csv")}
        elif kind == "calendar":
            # The jobs that wait for this one must still fit; a job others wait for can mostly only widen.
            fits = _fits(site)
            waiting = [j["calendar"] for j in jobs if job["name"] in j["deps"]]
            pool = [c for c in ("IS_GUNU", "HERGUN", "PAZARTESI")
                    if c != job["calendar"] and all(fits(w, c) for w in waiting)]
            change = {"calendar": rng.choice(pool)} if pool else {"notify": f"{team}-vardiya@ornek.local"}
        elif kind == "host":
            host = rng.choice([h for h in sorted(env["hosts"]) if h != job["host"]])
            change = {"host": host, "run_as": rng.choice(env["hosts"][host]["users"])}
        elif kind == "notify":
            change = {"notify": f"{team}-vardiya@ornek.local"}
        else:
            blocked = _descendants(jobs, job["name"]) | {job["name"]}
            pool = [j["name"] for j in jobs if j["name"] not in blocked and j["name"] not in job["deps"]]
            change = {"deps": sorted(job["deps"] + [rng.choice(pool)])} if pool else {"deps": []}
        fields = {"klasor": job["folder"], "is_adi": job["name"], **_fields(change)}
        return f"Degisiklik: yalnizca {', '.join(change)} degismeli", _form(no, team, "degisiklik", fields), \
            applied(_room(site, {**job, **change}))

    if family == "t-belirsiz":
        d, team = _new_job(rng, site)
        fields = {**_fields(d), "gunler": rng.choice(vague_phrases(split))}
        return "Tuzak: gunler belirsiz yazilmis; dogru hamle sormak", _form(no, team, "yeni", fields), \
            returned("gunler belirsiz")

    if family in ("takvim", "t-takvim"):
        d, team = _new_job(rng, site)
        if family == "takvim":
            d["calendar"] = rng.choice(sorted(phrases))
            phrase = rng.choice(phrases[d["calendar"]])
            fields = {**_fields(d), "gunler": phrase}
            return f"Gunler serbest yazilmis; dogru takvim {d['calendar']}", _form(no, team, "yeni", fields), \
                applied(_room(site, d))
        fields = {**_fields(d), "gunler": rng.choice(no_calendar)}
        return "Tuzak: istenen gunleri karsilayan takvim yok", _form(no, team, "yeni", fields), returned("uygun takvim yok")

    if family == "t-dongu":
        with_kids = [j for j in jobs if _descendants(jobs, j["name"])]
        job = rng.choice(with_kids)
        if rng.random() < 0.2:
            deps = sorted(job["deps"] + [job["name"]])
        else:
            deps = sorted(job["deps"] + [rng.choice(sorted(_descendants(jobs, job["name"])))])
        fields = {"klasor": job["folder"], "is_adi": job["name"], "bagimlilik": deps}
        return "Tuzak: istenen bagimlilik dongu olusturur", _form(no, _team(site, job), "degisiklik", fields), \
            returned("bagimlilik dongu olusturur")

    if family in ("aciklamali", "t-celiski"):
        # The fields are all valid. Only the free-text description can give the request away: in the
        # trap it states something different from one field, which no check on the fields can see.
        d, team = _new_job(rng, site)
        d["calendar"] = rng.choice(sorted(SAYS))
        if not d["deps"]:
            d["deps"] = [rng.choice([j["name"] for j in jobs if j["folder"] == d["folder"]])]
        _room(site, d)
        what = d["name"].split("_", 1)[1].lower().replace("_", " ")
        true = {"calendar": SAYS[d["calendar"]], "time": f"saat {d['time']}'de başlar",
                "host": f"{d['host']} sunucusunda çalışır", "deps": f"{d['deps'][0]} bittikten sonra başlar"}
        if family == "aciklamali":
            parts = rng.sample(sorted(true), rng.randint(2, 3))
            d["description"] = f"{team} {what} işi; " + "; ".join(true[k] for k in parts)
            return "Aciklama alanlarla tutarli: dogru hamle uygulamak", _form(no, team, "yeni", _fields(d)), applied(d)
        kind = rng.choice(sorted(true))
        hour = int(d["time"][:2])
        false = {"calendar": SAYS[rng.choice([c for c in sorted(SAYS) if c != d["calendar"]])],
                 "time": f"saat {(hour + rng.choice([6, 9, 12])) % 24:02d}:00'de başlar",
                 "host": f"{rng.choice([h for h in sorted(env['hosts']) if h != d['host']])} sunucusunda çalışır",
                 "deps": f"{rng.choice([j['name'] for j in jobs if j['name'] not in d['deps']])} bittikten sonra başlar"}
        other = rng.choice([k for k in sorted(true) if k != kind])
        d["description"] = f"{team} {what} işi; {false[kind]}; {true[other]}"
        return f"Tuzak: aciklama {kind} alaniyla celisiyor", _form(no, team, "yeni", _fields(d)), \
            returned(f"aciklama ile {kind} alani celisiyor")

    if family == "t-uyumsuz":
        # Every field is valid on its own. The request is wrong only as a pair: the job would be
        # ordered on days when a job it waits for is not, and would wait for ever on those days.
        if rng.random() < 0.6:
            d, team = _new_job(rng, site)
            if not d["deps"]:
                d["deps"] = [rng.choice([j["name"] for j in jobs if j["folder"] == d["folder"]])]
            d["calendar"] = rng.choice(["HERGUN", "HAFTA_SONU"])
            _room(site, d)
            _narrow(site, rng.choice(d["deps"]), "IS_GUNU")
            return "Tuzak: yeni is, bagimli oldugu isin calismadigi gunlerde de calisacak", \
                _form(no, team, "yeni", _fields(d)), returned("takvim, bagimli olunan isin takvimine sigmiyor")
        job = rng.choice([j for j in jobs if _descendants(jobs, j["name"])])
        change = {"calendar": rng.choice(["PAZARTESI", "AY_SONU_IS_GUNU", "HAFTA_SONU"])}
        _room(site, {**job, **change})
        fields = {"klasor": job["folder"], "is_adi": job["name"], **_fields(change)}
        return "Tuzak: takvim daralirsa bu ise bagimli isler bekler kalir", \
            _form(no, _team(site, job), "degisiklik", fields), returned("ise bagimli islerin takvimi sigmiyor")

    if family in ("kaldir", "t-bagimli"):
        leaf = family == "kaldir"
        job = rng.choice([j for j in jobs if bool(_descendants(jobs, j["name"])) != leaf])
        lines = _form(no, _team(site, job), "kaldir", {"klasor": job["folder"], "is_adi": job["name"]})
        if leaf:
            return "Kaldirma talebi: hicbir is bu ise bagimli degil", lines, {"outcome": "removed", "name": job["name"]}
        return "Tuzak: kaldirilmak istenen ise baska isler bagimli", lines, returned("ise bagimli isler var")

    if family == "t-mevcut":
        job = rng.choice(jobs)
        d = {**job, "command": job["command"].replace(".sh", "_yeni.sh").replace(".csv", "_yeni.csv"), "deps": []}
        return "Tuzak: yeni denmis ama is zaten var", _form(no, _team(site, job), "yeni", _fields(d)), \
            returned("is zaten tanimli")

    if family == "t-olmayan":
        d, team = _new_job(rng, site)
        fields = {"klasor": d["folder"], "is_adi": d["name"], "saat": d["time"]}
        return "Tuzak: degisiklik denmis ama is tanimli degil", _form(no, team, "degisiklik", fields), \
            returned("is tanimli degil")

    if family == "t-standart":
        d, team = _new_job(rng, site)
        _room(site, d)
        kind = rng.choice(["lower", "prefix", "notify", "command"])
        if kind == "lower":
            d["name"] = d["name"].lower()
        elif kind == "prefix":
            other = next(p for f, p, _ in site["_folders"] if f != d["folder"])
            d["name"] = other + d["name"].split("_", 1)[1]
        elif kind == "notify":
            d["notify"] = rng.choice(["ahmet@gmail.com", f"{team}@disfirma.com"])
        else:
            d["command"] = d["command"].rsplit("/", 1)[1]
        return f"Tuzak: standart ihlali ({kind})", _form(no, team, "yeni", _fields(d)), returned("standart ihlali")

    if family == "t-sablon":
        d, team = _new_job(rng, site)
        _room(site, d)
        lines, kind = _form(no, team, "yeni", _fields(d)), rng.choice(["missing", "missing", "unknown", "duplicate"])
        if kind == "missing":
            drop = rng.choice(["host", "saat", "komut", "bildirim", "calistiran", "aciklama", "tip", "gunler"])
            lines = [x for x in lines if not x.startswith(drop + ":")]
        elif kind == "unknown":
            lines.insert(rng.randint(3, len(lines)), rng.choice(["oncelik: yuksek", "not: acil, bugun girsin", "sla: 06:00"]))
        else:
            lines.append("saat: " + _hhmm(rng.randint(60, 600)))
        return f"Tuzak: sablona uymuyor ({kind})", lines, returned("sablon hatasi")

    if family == "t-referans":
        d, team = _new_job(rng, site)
        _room(site, d)
        kind = rng.choice(["host", "run_as", "dep", "folder", "time", "type"])
        if kind == "host":
            d["host"] = rng.choice(["app09", "prod-db", "sunucu1"])
        elif kind == "run_as":
            others = sorted({u for h in env["hosts"].values() for u in h["users"]} - set(env["hosts"][d["host"]]["users"]))
            d["run_as"] = rng.choice(others or ["root"])
        elif kind == "dep":
            d["deps"] = sorted(d["deps"] + [d["name"][:4] + "OLMAYAN_IS"])
        elif kind == "folder":
            d["folder"] = rng.choice(["GENEL", "TEST", "YENI_KLASOR"])
        elif kind == "time":
            d["time"] = rng.choice(["26:15", "2:30", "sabah 6", "24:00"])
        else:
            d["type"] = rng.choice(["sql", "python", "ftp"])
        return f"Tuzak: ortamda olmayan deger ({kind})", _form(no, team, "yeni", _fields(d)), returned("gecersiz deger")

    raise ValueError(family)


def rewritten(scenarios, path):
    """The same scenarios with their descriptions replaced by another author's wording
    (scripts/write_descriptions.py). Scenarios that author did not rewrite are left out."""
    data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    out = []
    for sc in scenarios:
        text = data["descriptions"].get(sc["id"])
        if text is None:
            continue
        sc = json.loads(json.dumps(sc))
        sc["id"] += "-R"
        sc["request"]["text"] = "\n".join(f"aciklama: {text}" if line.startswith("aciklama:") else line
                                          for line in sc["request"]["text"].splitlines())
        if sc["id"][:-2] in data.get("relabel", {}):
            # The other author's wording changed the meaning: the description now states something the
            # fields do not, so the right move became to return the request. Found by reading the
            # harness's "false alarms"; the file says why for each one.
            sc["family"], sc["expected"] = "t-celiski", {"outcome": "returned", "reason": data["relabel"][sc["id"][:-2]]}
        elif sc["expected"]["outcome"] == "applied":
            sc["expected"]["definition"]["description"] = text
        out.append(sc)
    return out


def generate(per_family=4, seed=0, families=FAMILIES, split="dev"):
    out, mark = [], {"test": "T", "ext": "X", "ext2": "Y"}.get(split, "")
    for fam in families:
        for i in range(per_family):
            rng = random.Random(f"{seed}:{fam}:{i}")
            site = make_site(rng)
            title, lines, expected = build(fam, rng, site, split)
            out.append({"id": f"{fam}-{mark}{seed}-{i:03d}", "family": fam, "kind": "request", "title": title,
                        "today": site["today"], "env": site["env"], "jobs": site["jobs"],
                        "request": {"talep_no": lines[0].split(": ", 1)[1], "text": "\n".join(lines)},
                        "expected": expected})
    return out
