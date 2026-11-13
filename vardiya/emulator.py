"""Deterministic batch-scheduler emulator: simulated clock, no wall time, no randomness.

Models the semantics that matter for operations: events (conditions), hosts, resource
pools, hold/free, rerun, set-to-ok, and jobs whose effects touch a small data world.
"""
import copy
import hashlib
import json

WAIT, RUN, OK, NOTOK = "wait", "executing", "ended_ok", "ended_not_ok"
READ_VERBS = ("list_jobs", "sysout", "waiting_info", "table_count", "table_dupes", "get_alerts", "get_clock")
ACTION_VERBS = ("hold", "free", "rerun", "run_cleanup", "set_to_ok", "add_event")
DEFAULTS = (("status", WAIT), ("held", False), ("runs", 0), ("rc", None), ("sysout", []), ("in", []),
            ("out", []), ("duration", 1), ("effect", {"type": "noop"}), ("idempotency", "never"),
            ("class", "generic"), ("resources", []), ("critical", False))


class Emulator:
    def __init__(self, scenario):
        s = copy.deepcopy(scenario)
        self.odate, self.clock = s["odate"], s.get("clock", 0)
        self.tables = s.get("tables", {})
        self.hosts = s.get("hosts", {})
        self.resources = s.get("resources", {})
        self.events = set(s.get("events", []))
        self.alerts = s.get("alerts", [])
        self.jobs = {}
        for j in s["jobs"]:
            for k, v in DEFAULTS:
                j.setdefault(k, copy.deepcopy(v))
            self.jobs[j["name"]] = j
        self.running = []
        self.run_until_quiet()

    # ---- engine -------------------------------------------------------------
    def _blockers(self, j):
        busy = [r for r in j["resources"]
                if sum(r in self.jobs[n]["resources"] for _, n in self.running) >= self.resources.get(r, 1)]
        return {"missing_events": sorted(e for e in j["in"] if e not in self.events),
                "host_down": not self.hosts.get(j.get("host"), True),
                "resource_busy": busy, "held": j["held"]}

    def _start_eligible(self):
        started = False
        for name in sorted(self.jobs):
            j = self.jobs[name]
            if j["status"] == WAIT and not any(self._blockers(j).values()):
                j["status"] = RUN
                self.running.append((self.clock + j["duration"], name))
                started = True
        return started

    def run_until_quiet(self):
        for _ in range(10_000):
            started = self._start_eligible()
            if not self.running:
                if not started:
                    return
                continue
            self.running.sort()
            end, name = self.running.pop(0)
            self.clock = max(self.clock, end)
            self._finish(name)
        raise RuntimeError("emulator did not settle")

    def _finish(self, name):
        j = self.jobs[name]
        j["runs"] += 1
        ok, rc, lines = self._effect(j)
        j["status"], j["rc"], j["sysout"], j["ended_at"] = (OK if ok else NOTOK), rc, lines, self.clock
        if ok:
            self.events.update(j["out"])

    def _batch(self, table):
        return [r for r in self.tables.get(table, []) if r.get("batch") == self.odate]

    def _effect(self, j):
        e, b = j["effect"], self.odate
        if e["type"] == "load":
            src, tgt = self.tables.get(e["source"], []), self.tables.setdefault(e["target"], [])
            if not src and e.get("empty_rc"):
                return False, e["empty_rc"], ["connect ok", "source is empty: 0 rows", "rc=" + e["empty_rc"]]
            f, n = e.get("fault"), len(src)
            if f and f["attempt"] == j["runs"]:
                n = f["after_rows"]
            tgt.extend(dict(r, batch=b) for r in src[:n])
            if n < len(src):
                return False, f["rc"], ["connect ok", f["msg"], f"loaded {n} rows", "rc=" + f["rc"]]
            return True, "OK", ["connect ok", f"loaded {n} rows", "commit"]
        if e["type"] in ("transform", "report"):
            src, tgt = self._batch(e["source"]), self.tables.setdefault(e["target"], [])
            keep = [r for r in tgt if r.get("batch") != b]
            if e["type"] == "transform":
                tgt[:] = keep + [dict(r) for r in src]
                return True, "OK", [f"posted {len(src)} rows"]
            total = sum(r[e.get("field", "amount")] for r in src)
            tgt[:] = keep + [{"batch": b, "total": total, "rows": len(src)}]
            return True, "OK", [f"report total={total} rows={len(src)}"]
        return True, "OK", ["done"]

    # ---- actions (raw, unguarded: this is what a bare agent gets) ------------
    def act(self, verb, job=None, event=None):
        if verb == "add_event":
            if not event:
                return {"ok": False, "msg": "event required"}
            self.events.add(event)
        else:
            j = self.jobs.get(job)
            if j is None:
                return {"ok": False, "msg": f"unknown job {job}"}
            if verb == "hold":
                j["held"] = True
            elif verb == "free":
                j["held"] = False
            elif verb == "rerun":
                if j["status"] not in (OK, NOTOK):
                    return {"ok": False, "msg": "job has not ended"}
                if j["held"]:
                    return {"ok": False, "msg": "held job must be freed before rerun"}
                j["status"] = WAIT
            elif verb == "set_to_ok":
                if j["status"] not in (NOTOK, WAIT):
                    return {"ok": False, "msg": "job is not failed or waiting"}
                j["status"], j["rc"] = OK, "FORCED"
                self.events.update(j["out"])
            elif verb == "run_cleanup":
                c = j.get("cleanup")
                if not c:
                    return {"ok": False, "msg": "job has no cleanup defined"}
                t = self.tables.get(c["target"], [])
                t[:] = [r for r in t if r.get("batch") != self.odate]
            else:
                return {"ok": False, "msg": f"unknown verb {verb}"}
        self.run_until_quiet()
        return {"ok": True, "msg": "done"}

    # ---- reads ----------------------------------------------------------------
    def list_jobs(self):
        return list(self.jobs.values())

    def sysout(self, job):
        return self.jobs[job]["sysout"]

    def waiting_info(self, job):
        return self._blockers(self.jobs[job])

    def table_count(self, table, batch=False):
        return len(self._batch(table)) if batch else len(self.tables.get(table, []))

    def table_dupes(self, table, key="id"):
        rows = self.tables.get(table, [])
        return len(rows) - len({(r.get("batch"), r.get(key)) for r in rows})

    def get_alerts(self):
        return self.alerts

    def get_clock(self):
        return self.clock

    def state(self):
        return {"jobs": {n: [j["status"], j["runs"], j["held"], j["rc"]] for n, j in sorted(self.jobs.items())},
                "events": sorted(self.events), "tables": self.tables}

    def state_hash(self):
        return hashlib.sha256(json.dumps(self.state(), sort_keys=True).encode()).hexdigest()[:16]
