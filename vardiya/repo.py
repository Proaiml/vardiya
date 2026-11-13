"""Definition repository: the planning side of a scheduler, deterministic.

Job definitions, calendars, hosts and the request ticket of one site. As with the
emulator, the verbs here are raw and unguarded: this is what a bare agent gets.
"""
import calendar as _calendar
import copy
import datetime
import hashlib
import json

DEF_FIELDS = ("name", "folder", "type", "host", "run_as", "command", "calendar", "time", "deps", "notify",
              "description")
READ_VERBS = ("get_request", "list_defs", "get_def", "list_env", "forecast")
ACTION_VERBS = ("deploy_job", "delete_job", "close_request", "return_request")
DAY = datetime.timedelta(days=1)


def normalise(definition):
    """Canonical form of a job definition: known fields only, dependencies as a sorted list."""
    out = {k: definition.get(k) for k in DEF_FIELDS}
    deps = definition.get("deps") or []
    out["deps"] = sorted(str(x) for x in deps) if isinstance(deps, (list, tuple)) else [str(deps)]
    return out


# ---- calendars ----------------------------------------------------------------
def _is_workday(d, holidays):
    return d.weekday() < 5 and d.isoformat() not in holidays


def _shift(d, holidays, step):
    while not _is_workday(d, holidays):
        d += step * DAY
    return d


def _month_run(rule, year, month, holidays):
    last = _calendar.monthrange(year, month)[1]
    if rule["type"] == "month_end_workday":
        return _shift(datetime.date(year, month, last), holidays, -1)
    d = datetime.date(year, month, min(rule["day"], last))
    step = {"next": 1, "prev": -1}.get(rule.get("shift", "none"))
    return _shift(d, holidays, step) if step else d


def run_dates(rule, holidays, start, days):
    """Dates in [start, start + days) on which a job with this calendar rule is ordered."""
    end = start + (days - 1) * DAY
    kind = rule["type"]
    if kind in ("month_end_workday", "month_day"):
        year, month = (start.year, start.month - 1) if start.month > 1 else (start.year - 1, 12)
        found = set()
        for _ in range(days // 28 + 4):  # one month back and forward: a shifted date may cross a month edge
            found.add(_month_run(rule, year, month, holidays))
            year, month = (year, month + 1) if month < 12 else (year + 1, 1)
        return sorted(d for d in found if start <= d <= end)
    out = []
    for i in range(days):
        d = start + i * DAY
        if (kind == "daily" or (kind == "workdays" and _is_workday(d, holidays))
                or (kind == "weekly" and d.weekday() in rule["days"])):
            out.append(d)
    return out


# ---- repository ---------------------------------------------------------------
class Repo:
    def __init__(self, scenario):
        s = copy.deepcopy(scenario)
        env = s["env"]
        self.today = datetime.date.fromisoformat(s["today"])
        self.hosts = env["hosts"]            # {host: {"users": [...], "desc": "..."}}
        self.calendars = env["calendars"]    # {name: {"rule": {...}, "desc": "..."}}
        self.folders = env["folders"]        # {folder: {"prefix": "..."}}
        self.standards = env["standards"]
        self.holidays = env.get("holidays", [])
        self.jobs = {j["name"]: normalise(j) for j in s.get("jobs", [])}
        self.versions = {n: [copy.deepcopy(j)] for n, j in self.jobs.items()}
        r = s["request"]
        self.tickets = {r["talep_no"]: {"text": r["text"], "status": "open", "record": None, "reason": None}}

    # ---- actions (raw, unguarded) ---------------------------------------------
    def act(self, verb, **kw):
        def fail(msg):
            return {"ok": False, "msg": msg}

        if verb == "deploy_job":
            d = kw.get("definition")
            if not isinstance(d, dict) or not isinstance(d.get("name"), str) or not d["name"]:
                return fail('pass {"definition": {...}} with a non-empty "name"')
            d = normalise(d)
            self.jobs[d["name"]] = d
            self.versions.setdefault(d["name"], []).append(copy.deepcopy(d))
        elif verb == "delete_job":
            if kw.get("job") not in self.jobs:
                return fail(f"unknown job {kw.get('job')}")
            del self.jobs[kw["job"]]
        elif verb in ("close_request", "return_request"):
            t = self.tickets.get(kw.get("talep_no"))
            if t is None:
                return fail(f"unknown request {kw.get('talep_no')}")
            if t["status"] != "open":
                return fail("request is not open")
            if verb == "close_request":
                t["status"], t["record"] = "closed", kw.get("record")
            else:
                t["status"], t["reason"] = "returned", kw.get("reason")
        else:
            return fail(f"unknown verb {verb}")
        return {"ok": True, "msg": "done"}

    # ---- reads ----------------------------------------------------------------
    def get_request(self, talep_no=None):
        no = talep_no or next(iter(self.tickets))
        t = self.tickets.get(no)
        return None if t is None else {"talep_no": no, "text": t["text"], "status": t["status"]}

    def list_defs(self):
        return [self.jobs[n] for n in sorted(self.jobs)]

    def get_def(self, job):
        return self.jobs.get(job)

    def list_env(self):
        return {"today": self.today.isoformat(), "hosts": self.hosts, "folders": self.folders,
                "calendars": {n: c["desc"] for n, c in sorted(self.calendars.items())},
                "standards": self.standards, "holidays": self.holidays}

    def forecast(self, calendar, days=60):
        c = self.calendars.get(calendar)
        if c is None:
            return None
        return [d.isoformat() for d in run_dates(c["rule"], self.holidays, self.today, int(days))]

    def state(self):
        return {"jobs": self.jobs, "tickets": self.tickets}

    def state_hash(self):
        raw = json.dumps(self.state(), sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
