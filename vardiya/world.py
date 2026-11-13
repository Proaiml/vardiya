"""World model: topology and derived facts, computed deterministically.

Rule: anything that can be computed is computed here, never asked of the model.
"""
import hashlib
import re
import statistics

from .emulator import NOTOK, OK, WAIT


def template(line):
    return re.sub(r"\d+", "N", line)


class World:
    def __init__(self, adapter):
        self.a = adapter
        self.clock = adapter.call("get_clock")
        self.jobs = {j["name"]: j for j in adapter.call("list_jobs")}
        self.producer = {e: n for n, j in sorted(self.jobs.items()) for e in j["out"]}
        self.pred = {n: sorted({self.producer[e] for e in j["in"] if e in self.producer})
                     for n, j in self.jobs.items()}
        self.succ = {n: [] for n in self.jobs}
        for n in sorted(self.pred):
            for p in self.pred[n]:
                self.succ[p].append(n)

    # ---- topology -------------------------------------------------------------
    def topo(self):
        indeg = {n: len(p) for n, p in self.pred.items()}
        ready, order = sorted(n for n, d in indeg.items() if d == 0), []
        while ready:
            n = ready.pop(0)
            order.append(n)
            for s in self.succ[n]:
                indeg[s] -= 1
                if indeg[s] == 0:
                    ready.append(s)
            ready.sort()
        return order

    def downstream(self, name):
        seen, queue = [], list(self.succ[name])
        while queue:
            n = queue.pop(0)
            if n not in seen:
                seen.append(n)
                queue.extend(self.succ[n])
        return seen

    def blast_radius(self, name):
        d = self.downstream(name)
        return {"count": len(d), "jobs": d, "critical": [n for n in d if self.jobs[n]["critical"]]}

    # ---- time -----------------------------------------------------------------
    def expected(self, name):
        h = self.jobs[name].get("history")
        return statistics.median(h) if h else self.jobs[name]["duration"]

    def critical_path(self):
        """Longest remaining path: ETA if every blocker were cleared now."""
        finish, via = {}, {}
        for n in self.topo():
            j = self.jobs[n]
            if j["status"] == OK:
                finish[n] = j.get("ended_at", self.clock)
                continue
            start, via[n] = self.clock, None
            for p in self.pred[n]:
                if finish[p] > start:
                    start, via[n] = finish[p], p
            finish[n] = start + self.expected(n)
        pending = [n for n in finish if self.jobs[n]["status"] != OK]
        if not pending:
            return {"eta": self.clock, "path": [], "deadline": None, "slack": None}
        end = max(pending, key=lambda n: (finish[n], n))
        path, n = [], end
        while n is not None:
            path.append(n)
            n = via.get(n)
        deadlines = [self.jobs[n]["deadline"] for n in self.jobs if "deadline" in self.jobs[n]]
        deadline = min(deadlines) if deadlines else None
        return {"eta": finish[end], "path": path[::-1], "deadline": deadline,
                "slack": None if deadline is None else deadline - finish[end]}

    def slowest(self, n=5):
        rows = [{"job": k, "median": self.expected(k), "total": sum(j.get("history", [j["duration"]]))}
                for k, j in self.jobs.items()]
        return {"slowest": sorted(rows, key=lambda r: -r["median"])[:n],
                "costliest": sorted(rows, key=lambda r: -r["total"])[:n]}

    # ---- diagnosis -------------------------------------------------------------
    def first_fault(self):
        """Earliest broken node whose predecessors are all healthy: the root candidate."""
        for n in self.topo():
            j = self.jobs[n]
            bad = j["status"] == NOTOK
            if j["status"] == WAIT and not j["held"]:
                w = self.a.call("waiting_info", job=n)
                bad = not w["missing_events"] and (w["host_down"] or bool(w["resource_busy"]))
            if bad and all(self.jobs[p]["status"] == OK for p in self.pred[n]):
                return n
        return None

    def sysout_diff(self, name):
        known = {template(x) for x in self.jobs[name].get("last_ok_sysout", [])}
        return [x for x in self.jobs[name]["sysout"] if template(x) not in known]

    def signature(self, name):
        j = self.jobs[name]
        raw = "|".join([j["class"], str(j["rc"])] + [template(x) for x in self.sysout_diff(name)])
        return hashlib.sha1(raw.encode()).hexdigest()[:12]

    def facts(self, name):
        j = self.jobs[name]
        e, br = j["effect"], self.blast_radius(name)
        target = e.get("target") if e["type"] == "load" else None
        f = {"job": name, "status": j["status"], "rc": j["rc"], "job_class": j["class"], "runs": j["runs"],
             "held": j["held"], "idempotency": j["idempotency"], "has_cleanup": bool(j.get("cleanup")),
             "expected_rc": j["rc"] in j.get("ok_codes", []),
             "target_rows": self.a.call("table_count", table=target, batch=True) if target else 0,
             "source_rows": self.a.call("table_count", table=e["source"]) if target else 0,
             "dupes": self.a.call("table_dupes", table=target, key=e.get("key", "id")) if target else 0,
             "downstream_count": br["count"], "critical_downstream": len(br["critical"]),
             "signature": self.signature(name), "sysout_diff": self.sysout_diff(name)}
        f["refs"] = {"status": f"job:{name}#status", "rc": f"sysout:{name}#last",
                     "sysout_diff": f"sysout:{name}#diff-vs-last-ok",
                     "target_rows": f"table:{target}?batch=odate", "source_rows": f"table:{e.get('source')}",
                     "dupes": f"table:{target}?dupes", "critical_downstream": f"topology:{name}#downstream"}
        return f
