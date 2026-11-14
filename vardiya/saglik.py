"""Definition health: every job already on the site, checked the way a new request would be.

Request checks guard what comes in. Sites also carry what came in before the checks existed: a file watch
with no time limit, a job ordered on days its predecessor is not, a password in a description, two jobs
running the same command. This scan finds them so an admin can clean up on purpose, not during an incident.
Code only; nothing here asks a model.
"""
from . import checks

SEVERITY = {"error": "risk", "warning": "uyari"}


def scan(repo, rules=()):
    env, jobs = repo.list_env(), dict(repo.jobs)
    runs = {c: set(repo.forecast(c, 180) or []) for c in env["calendars"]}
    out = []

    def add(job, code, msg, level):
        out.append({"job": job, "code": code, "msg": checks.redact(msg), "level": level})

    for name, d in sorted(jobs.items()):
        others = {n: j for n, j in jobs.items() if n != name}
        for f in checks.check(env, others, d, True, rules, runs):
            if f["code"] in ("E_EXISTS", "E_CAL_DEPENDENT"):
                continue  # judged from the other side by that job's own scan
            level = SEVERITY[f["severity"]]
            if f["code"] == "E_REQUIRED" and f["field"] == "timeout":
                level = "uyari"  # an old watch without a time limit: wrong, but it has been running
            add(name, f["code"], f["msg"], level)
    # what only shows across jobs
    by_cmd = {}
    for name, d in jobs.items():
        if d.get("command"):
            by_cmd.setdefault((d.get("host"), d["command"]), []).append(name)
    for (host, cmd), names in sorted(by_cmd.items()):
        if len(names) > 1:
            for n in names:
                add(n, "W_SAME_COMMAND", f"ayni komut ({cmd}) ayni sunucuda {len(names)} iste tanimli: "
                                         f"{', '.join(sorted(names))}; mukerrer calisma riski", "uyari")
    waited = {dep for d in jobs.values() for dep in d["deps"]}
    for name, d in sorted(jobs.items()):
        if not d["deps"] and name not in waited and d.get("type") != "dosya_izleme":
            add(name, "I_ALONE", "ne bekledigi ne de onu bekleyen bir is var; bilerek mi yalniz, kontrol edin", "bilgi")
    order = {"risk": 0, "uyari": 1, "bilgi": 2}
    return sorted(out, key=lambda f: (order[f["level"]], f["job"], f["code"]))
