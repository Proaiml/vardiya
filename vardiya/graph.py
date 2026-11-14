"""Local error graph: what happened on the site, kept on the site.

A small property graph in SQLite (standard library only): jobs, their runs, the hosts, users, connections
and tables they touch, the error signatures their runs ended with, the requests that changed them and the
incidents with their root cause and resolution. Nothing leaves the machine.

The graph is where the harness remembers; reading it is code. A model is handed only the small piece of
the graph that code has picked out for one question, never the graph itself.
"""
import json
import re
import sqlite3

KINDS = ("job", "run", "host", "user", "connection", "table", "resource", "signature", "change", "incident",
         "resolution")


def signature(text):
    """The template of an error line: numbers, paths, quoted values and hex ids replaced, case folded.
    Two runs that failed for the same reason share it, whatever the file, row count or time."""
    t = str(text or "").strip().lower()
    t = re.sub(r"'[^']*'|\"[^\"]*\"", "<q>", t)
    t = re.sub(r"(?:[a-z]:)?[\\/][\w.\-*\\/]+", "<yol>", t)
    t = re.sub(r"\b0x[0-9a-f]+\b|\b[0-9a-f]{12,}\b", "<id>", t)
    # A Unix exit status from 129 to 255 means the process was ended by a signal (128 + signal number). That fact
    # is the whole diagnosis, so it survives templating as a word instead of becoming <n>.
    t = re.sub(r"\b(oscompstat|exit code|exit status|return code|rc)\s*[=:]?\s*(129|1[3-9]\d|2[0-4]\d|25[0-5])\b",
               r"\1 signal", t)
    t = re.sub(r"\d+([.,:]\d+)*", "<n>", t)
    return re.sub(r"\s+", " ", t)[:160]


def _tokens(sig):
    return {w for w in re.findall(r"[a-zçğıöşü<>_\-]{3,}", sig)}


def similarity(a, b):
    """Token overlap of two signatures (Jaccard)."""
    x, y = _tokens(a), _tokens(b)
    return len(x & y) / len(x | y) if x | y else 0.0


class Graph:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path, check_same_thread=False)  # the web server serialises use behind a lock
        self.db.executescript(
            "CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, kind TEXT, label TEXT, props TEXT);"
            "CREATE TABLE IF NOT EXISTS edges (src TEXT, kind TEXT, dst TEXT, at TEXT, props TEXT,"
            " PRIMARY KEY (src, kind, dst));"
            "CREATE INDEX IF NOT EXISTS e_dst ON edges (dst, kind);"
            "CREATE INDEX IF NOT EXISTS n_kind ON nodes (kind);")

    # ---- writing --------------------------------------------------------------------
    def node(self, kind, key, label=None, **props):
        nid = f"{kind}:{key}"
        row = self.db.execute("SELECT props FROM nodes WHERE id=?", (nid,)).fetchone()
        merged = {**(json.loads(row[0]) if row else {}), **props}
        self.db.execute("INSERT OR REPLACE INTO nodes VALUES (?,?,?,?)",
                        (nid, kind, label or str(key), json.dumps(merged, ensure_ascii=False, sort_keys=True)))
        return nid

    def edge(self, src, kind, dst, at=None, **props):
        self.db.execute("INSERT OR REPLACE INTO edges VALUES (?,?,?,?,?)",
                        (src, kind, dst, at, json.dumps(props, ensure_ascii=False, sort_keys=True)))

    def commit(self):
        self.db.commit()

    def add_site(self, jobs, connections=None):
        """The static part: jobs and what they touch. Tables come from the job's `tables` list if present."""
        for j in jobs:
            jid = self.node("job", j["name"], folder=j.get("folder"), type=j.get("type"), calendar=j.get("calendar"),
                            time=j.get("time"), command=j.get("command"))
            self.edge(jid, "on", self.node("host", j["host"]))
            self.edge(jid, "as", self.node("user", j["run_as"]))
            if j.get("connection"):
                desc = (connections or {}).get(j["connection"], {}).get("desc")
                self.edge(jid, "uses", self.node("connection", j["connection"], desc=desc))
            for t in j.get("tables", []):
                self.edge(jid, "writes", self.node("table", t))
            for r in j.get("resources", []):
                self.edge(jid, "needs", self.node("resource", r))
            for d in j.get("deps", []):
                self.edge(jid, "after", f"job:{d}")
        self.commit()

    def add_run(self, job, day, ok, minutes, error=None, rc=0, attempt=1, set_ok=False):
        """`set_ok`: the run failed and an operator marked it OK by hand. It counts as green downstream, which
        is exactly why it has to stay visible (a BMC Community request open since 2022 asks for the same)."""
        rid = self.node("run", f"{job}@{day}#{attempt}", f"{job} {day}", job=job, day=day, ok=bool(ok),
                        minutes=round(minutes, 1), rc=rc, error=error, attempt=attempt, set_ok=bool(set_ok))
        self.edge(rid, "of", f"job:{job}", at=day)
        if not ok and error:
            sig = signature(error)
            sid = self.node("signature", sig, sig, example=error)
            self.edge(rid, "failed_with", sid, at=day)
        return rid

    def add_change(self, key, job, day, what, by="talep"):
        cid = self.node("change", key, f"{key} {job}", job=job, day=day, what=what, by=by)
        self.edge(cid, "changed", f"job:{job}", at=day)
        return cid

    def add_host_change(self, key, host, day, what, by="platform"):
        """A change below the jobs: a patch, an upgrade, a new Java. Forums show many incidents start here."""
        cid = self.node("change", key, f"{key} {host}", host=host, day=day, what=what, by=by)
        self.edge(cid, "changed", f"host:{host}", at=day)
        return cid

    def add_incident(self, key, day, run_ids, root, cause, resolution=None, verified=False, minutes=None):
        iid = self.node("incident", key, key, day=day, cause=cause, verified=bool(verified), minutes=minutes,
                        open=resolution is None)
        for r in run_ids:
            self.edge(iid, "covers", r, at=day)
        if root:
            self.edge(iid, "root", root, at=day)
        if resolution:
            self.edge(iid, "resolved_by", self.node("resolution", resolution, resolution), at=day,
                      verified=bool(verified))
        return iid

    # ---- reading --------------------------------------------------------------------
    def get(self, nid):
        row = self.db.execute("SELECT id, kind, label, props FROM nodes WHERE id=?", (nid,)).fetchone()
        return None if row is None else {"id": row[0], "kind": row[1], "label": row[2], **json.loads(row[3])}

    def out(self, nid, kind=None):
        q = "SELECT dst, kind, at, props FROM edges WHERE src=?" + (" AND kind=?" if kind else "")
        return [{"to": d, "kind": k, "at": a, **json.loads(p)} for d, k, a, p in
                self.db.execute(q, (nid, kind) if kind else (nid,))]

    def into(self, nid, kind=None):
        q = "SELECT src, kind, at, props FROM edges WHERE dst=?" + (" AND kind=?" if kind else "")
        return [{"from": s, "kind": k, "at": a, **json.loads(p)} for s, k, a, p in
                self.db.execute(q, (nid, kind) if kind else (nid,))]

    def nodes(self, kind):
        return [{"id": i, "label": lb, **json.loads(p)} for i, lb, p in
                self.db.execute("SELECT id, label, props FROM nodes WHERE kind=? ORDER BY id", (kind,))]

    def runs(self, job=None, since=None, until=None):
        rows = self.db.execute("SELECT id, props FROM nodes WHERE kind='run'").fetchall()
        out = [{"id": i, **json.loads(p)} for i, p in rows]
        return sorted((r for r in out if (job is None or r["job"] == job) and (since is None or r["day"] >= since)
                       and (until is None or r["day"] <= until)), key=lambda r: (r["day"], r["job"], r["attempt"]))

    def attrs(self, job):
        """Host, user, connection and tables of a job: the places a shared cause can sit."""
        return [e["to"] for e in self.out(f"job:{job}") if e["kind"] in ("on", "as", "uses", "writes", "needs")]

    def neighbourhood(self, seeds, depth=1, limit=60):
        """Nodes and edges within `depth` steps of the seeds, for drawing and for a model's context."""
        seen, frontier, edges = set(seeds), set(seeds), []
        for _ in range(depth):
            nxt = set()
            for n in sorted(frontier):
                for e in self.out(n):
                    edges.append((n, e["kind"], e["to"]))
                    nxt.add(e["to"])
                for e in self.into(n):
                    if e["from"].startswith("run:"):
                        continue  # runs are many; they come in only as seeds
                    edges.append((e["from"], e["kind"], n))
                    nxt.add(e["from"])
            frontier = nxt - seen
            seen |= nxt
            if len(seen) > limit:
                break
        nodes = [self.get(n) for n in sorted(seen) if self.get(n)]
        keep = {n["id"] for n in nodes}
        return {"nodes": nodes, "edges": sorted({e for e in edges if e[0] in keep and e[2] in keep})}

    def stats(self):
        return {k: n for k, n in self.db.execute("SELECT kind, COUNT(*) FROM nodes GROUP BY kind")} | \
               {"edges": self.db.execute("SELECT COUNT(*) FROM edges").fetchone()[0]}
