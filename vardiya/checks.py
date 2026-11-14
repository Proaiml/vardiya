"""Pre-flight checks for a job definition.

Pure functions over what the read verbs return, so the harness sees nothing a bare
agent could not see. Every check here is something an admin does by eye.
"""
import re

from . import intake
from .skills import holds

TYPES = ("komut", "dosya_izleme", "veritabani", "dosya_aktarimi", "ssh", "bos")
# What each job type needs beyond the common fields. "command" means: komut the OS command, dosya_izleme the
# path or pattern to watch, veritabani the SQL file, dosya_aktarimi the source path, ssh the remote command.
NEEDS = {"komut": ("command",), "dosya_izleme": ("command", "timeout"), "veritabani": ("command", "connection"),
         "dosya_aktarimi": ("command", "connection", "target"), "ssh": ("command", "connection"), "bos": ()}
CONNECTION_KIND = ("veritabani", "dosya_aktarimi", "ssh")
TEMPLATE_KEY = {field: key for key, field in intake.FIELDS.items()}  # definition field -> template key
# password=..., sifre: ..., a URL with user:password@, an Oracle connect string user/password@db
SECRET = re.compile(r"(passw(or)?d|parola|sifre|şifre|pwd)\s*[=:]|://[^/\s:@]+:[^/\s@]+@|(^|\s)[\w.-]+/[^\s/@]+@\S+",
                    re.I)
REQUIRED = ("name", "folder", "type", "host", "run_as", "command", "calendar", "time", "notify", "description")
TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def reaches_itself(name, deps_of):
    """True if following dependencies from `name` leads back to `name`."""
    seen, stack = set(), list(deps_of.get(name, []))
    while stack:
        n = stack.pop()
        if n == name:
            return True
        if n not in seen:
            seen.add(n)
            stack.extend(deps_of.get(n, []))
    return False


def check(env, jobs, d, is_new, rules=(), runs=None):
    """Findings for definition `d` against the site: [{"code", "field", "severity", "msg"}].

    The checks written here are the kernel: structural integrity that no skill can switch off.
    `rules` are the site's own standards, loaded from request-rule skills.
    `runs` maps each calendar to the set of dates it orders in the coming months (from `forecast`)."""
    out = []

    def add(code, field, msg, severity="error"):
        out.append({"code": code, "field": field, "severity": severity, "msg": msg})

    name = d.get("name") or ""
    if is_new and name in jobs:
        add("E_EXISTS", "name", f"{name} zaten tanimli; yeni is degil, degisiklik talebi acilmali")
    if not is_new and name not in jobs:
        add("E_MISSING", "name", f"{name} tanimli degil; degisiklik degil, yeni is talebi acilmali")
    kind = d.get("type")
    for f in REQUIRED:
        if d.get(f) in (None, "") and not (f == "command" and kind == "bos"):
            add("E_REQUIRED", f, f"zorunlu alan bos: {f}")
    _type_checks(env, jobs, d, is_new, add)

    folder = env["folders"].get(d.get("folder"))
    if d.get("folder") and folder is None:
        add("E_FOLDER", "folder", f"klasor tanimli degil: {d['folder']}. Gecerli: {', '.join(sorted(env['folders']))}")
    if d.get("type") and d["type"] not in TYPES:
        add("E_TYPE", "type", f"is tipi gecersiz: {d['type']}. Gecerli: {', '.join(TYPES)}")

    host = env["hosts"].get(d.get("host"))
    if d.get("host") and host is None:
        add("E_HOST", "host", f"host tanimli degil: {d['host']}. Gecerli: {', '.join(sorted(env['hosts']))}")
    elif host and d.get("run_as") and d["run_as"] not in host["users"]:
        add("E_RUNAS", "run_as", f"{d['run_as']} kullanicisi {d['host']} uzerinde tanimli degil. "
                                 f"Gecerli: {', '.join(host['users'])}")
    if d.get("calendar") and d["calendar"] not in env["calendars"]:
        add("E_CALENDAR", "calendar", f"takvim tanimli degil: {d['calendar']}. "
                                      f"Gecerli: {', '.join(sorted(env['calendars']))}")
    if d.get("time") and not TIME.match(str(d["time"])):
        add("E_TIME", "time", f"saat SS:DD biciminde olmali: {d['time']}")

    deps = d.get("deps") or []
    for dep in deps:
        if dep == name:
            add("E_SELF", "deps", f"{name} kendisine bagimli olamaz")
        elif dep not in jobs:
            add("E_DEP", "deps", f"bagimlilik tanimli bir is degil: {dep}")
    deps_of = {n: j["deps"] for n, j in jobs.items()}
    deps_of[name] = [x for x in deps if x in jobs and x != name]
    if name and reaches_itself(name, deps_of):
        add("E_CYCLE", "deps", f"bu bagimlilik bir dongu olusturur: {name} dolayli olarak kendisini bekler")

    if d.get("time") and TIME.match(str(d["time"])):
        for dep in deps:
            other = jobs.get(dep, {}).get("time")
            if other and d["time"] < other:
                add("W_TIME_BEFORE_DEP", "time", f"baslama saati {d['time']}, bagimli oldugu {dep} isinin saatinden "
                                                 f"({other}) once; is yine de {dep} bitene kadar bekler", "warning")

    # A job must not be ordered on a day its predecessor is not: it would wait for an event that never
    # comes. (Found by a frontier model working without the harness; no field check here caught it.)
    # Only what this request sets up is judged: a mismatch already on the site is not the requester's.
    if runs and d.get("calendar") in runs:
        mine = runs[d["calendar"]]
        before = None if is_new else jobs.get(name)
        moved = before is None or before.get("calendar") != d["calendar"]
        for dep in deps:
            if dep == name or not (moved or dep not in before["deps"]):
                continue
            other = runs.get(jobs.get(dep, {}).get("calendar"))
            if other is not None and not mine <= other:
                days = ", ".join(sorted(mine - other)[:3])
                fit = sorted((c for c in runs if runs[c] and runs[c] <= other), key=lambda c: (-len(runs[c] & mine), -len(runs[c]), c))
                add("E_CAL_DEP", "calendar",
                    f"{name} {d['calendar']} takvimiyle calisacak, ama bagimli oldugu {dep} {jobs[dep]['calendar']} "
                    f"takvimiyle calisiyor; {days} gibi gunlerde {dep} calismayacagi icin {name} bekler kalir. "
                    f"{dep} ile uyumlu takvimler: {', '.join(fit[:3]) or 'yok'}; ya da {dep} isinin takvimi genisletilmeli")
        for waiter, j in sorted(jobs.items()) if before and moved else ():
            theirs = runs.get(j.get("calendar"))
            if name in j["deps"] and waiter != name and theirs is not None and not theirs <= mine:
                days = ", ".join(sorted(theirs - mine)[:3])
                add("E_CAL_DEPENDENT", "calendar",
                    f"{waiter} isi {name} isine bagimli ve {j['calendar']} takvimiyle calisiyor; {name} {d['calendar']} "
                    f"takvimine gecerse {days} gibi gunlerde {waiter} bekler kalir")

    # Site standards come from request-rule skills. They run after the kernel checks and can only add
    # findings; a rule whose facts are missing is skipped (the kernel already reported the gap).
    facts = rule_facts(env, d, is_new)
    for rule in rules:
        used = [c.split(None, 2)[0] for c in (rule.require + (" and " + rule.when if rule.when else "")).split(" and ")]
        if any(facts.get(f) in (None, "") for f in used):
            continue
        if (not rule.when or holds(rule.when, facts)) and not holds(rule.require, facts):
            field = used[0] if used[0] in d else "name"
            left, op, right = rule.require.split(" and ")[0].split(None, 2)
            add(f"S_{rule.skill}.{rule.id}", field,
                f"{rule.message}: {facts[left]} (kural: {left} {op} {facts.get(right.strip(), right.strip())})", rule.severity)
    return out


def redact(text):
    """The text with any secret it carries replaced by ***, for whatever is kept or shown afterwards."""
    text = re.sub(r"((passw(?:or)?d|parola|sifre|şifre|pwd)\s*[=:]\s*)[^\s;,\"']+", r"\1***", str(text), flags=re.I)
    text = re.sub(r"(://[^/\s:@\"']+:)[^/\s@\"']+@", r"\1***@", text)
    return re.sub(r"((?:^|[\s\"'])[\w.-]+/)[^\s/@\"']+@", r"\1***@", text)


def _type_checks(env, jobs, d, is_new, add):
    """What each job type needs. Judged when the request sets the type up (a new job, or a change of type);
    a job already on the site that lacks a field, say an old file watch without a time limit, is not the
    requester's doing."""
    kind, before = d.get("type"), None if is_new else jobs.get(d.get("name"))
    for f, v in d.items():
        if isinstance(v, str) and SECRET.search(v):
            add("E_SECRET", f, f"{TEMPLATE_KEY.get(f, f)} alaninda parola ya da gizli bilgi var; gizli bilgi talebe "
                               "yazilmaz, ortamdaki bir baglanti profili kullanilir")
    if kind not in NEEDS:
        return
    fresh = before is None or before.get("type") != kind
    if fresh:
        for f in NEEDS[kind]:
            if d.get(f) in (None, ""):
                add("E_REQUIRED", f, f"{kind} isi icin zorunlu alan bos: {TEMPLATE_KEY[f]}")
    if kind == "bos" and d.get("command") not in (None, ""):
        add("E_TYPE_FIELD", "command", "bos (Dummy) is komut calistirmaz; komut alani bos birakilmali ya da tip degistirilmeli")
    if kind != "dosya_aktarimi" and d.get("target") not in (None, "") and fresh:
        add("E_TYPE_FIELD", "target", f"hedef alani yalnizca dosya_aktarimi islerinde yazilir; bu is {kind}")
    if kind not in CONNECTION_KIND and d.get("connection") not in (None, "") and fresh:
        add("E_TYPE_FIELD", "connection", f"baglanti alani {kind} islerinde kullanilmaz")
    conn, profiles = d.get("connection"), env.get("connections") or {}
    if kind in CONNECTION_KIND and conn not in (None, ""):
        valid = ", ".join(sorted(n for n, p in profiles.items() if p.get("kind") == kind)) or "yok"
        if conn not in profiles:
            add("E_CONNECTION", "connection", f"baglanti profili tanimli degil: {conn}. Gecerli {kind} profilleri: {valid}")
        elif profiles[conn].get("kind") != kind:
            add("E_CONNECTION", "connection",
                f"{conn} bir {profiles[conn].get('kind')} profili; {kind} isi icin kullanilamaz. Gecerli: {valid}")
    if kind == "dosya_izleme" and d.get("timeout") not in (None, ""):
        t = str(d["timeout"]).strip()
        if not t.isdigit() or not 1 <= int(t) <= 1440:
            add("E_TIMEOUT", "timeout", f"sure_siniri dakika olarak 1 ile 1440 arasinda bir sayi olmali: {t}")
    if kind == "dosya_aktarimi" and d.get("target") and d.get("command") and \
            str(d["target"]).rstrip("/") == str(d["command"]).rstrip("/"):
        add("E_TARGET", "target", "hedef yol kaynak yolla ayni; aktarim dosyanin uzerine yazar")


def check_removal(jobs, name):
    """Findings for removing job `name`: it must exist and nothing may still wait for it."""
    if name not in jobs:
        return [{"code": "E_MISSING", "field": "name", "severity": "error",
                 "msg": f"{name} tanimli degil; kaldirilacak is yok"}]
    waiting = sorted(n for n, j in jobs.items() if name in j["deps"])
    if waiting:
        return [{"code": "E_DEPENDENT", "field": "name", "severity": "error",
                 "msg": f"{name} kaldirilamaz: su isler ona bagimli: {', '.join(waiting)}. "
                        "Once onlarin bagimliligi degistirilmeli"}]
    return []


def rule_facts(env, d, is_new):
    """What a request-rule skill may look at. Nothing here is beyond the read verbs."""
    facts = {k: d.get(k) for k in REQUIRED}
    time_ok = bool(d.get("time")) and TIME.match(str(d["time"]))
    folder = env["folders"].get(d.get("folder")) or {}
    facts.update(dep_count=len(d.get("deps") or []), is_new=is_new,
                 hour=int(d["time"][:2]) if time_ok else None, minute=int(d["time"][3:]) if time_ok else None,
                 folder_prefix=folder.get("prefix"), std_name_regex=env.get("standards", {}).get("name_regex"),
                 std_notify_suffix=env.get("standards", {}).get("notify_suffix"))
    return facts
