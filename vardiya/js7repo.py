"""The definition-side adapter on a real scheduler: same verbs as RepoAdapter, jobs live in JS7.

What is real here: every job is a JS7 workflow that is stored and deployed to the Controller,
runs on a JS7 Agent named after its host, waits for its predecessors through notice boards and
posts its own notice when it ends. What is still ours: the request ticket, the site profile
(standards, calendars, holidays) and the run-date forecast, which JS7's Daily Plan has not yet
been checked against.
"""
import copy
import datetime
import json
import time

from .js7 import JS7Error
from .repo import ACTION_VERBS, DEF_FIELDS, READ_VERBS, normalise, run_dates

META = ("folder", "type", "run_as", "command", "calendar", "time", "notify", "description", "connection", "target",
        "timeout")


def _quote(v):
    return json.dumps("" if v is None else str(v), ensure_ascii=False)


class JS7Repo:
    def __init__(self, js, controller_id, scenario, run_id):
        s = copy.deepcopy(scenario)
        self.js, self.cid = js, controller_id
        self.prefix = run_id + "_"                    # JS7 object names are global; keep runs apart
        self.root = "/sab/" + run_id
        self.env, self.today = s["env"], datetime.date.fromisoformat(s["today"])
        r = s["request"]
        self.tickets = {r["talep_no"]: {"text": r["text"], "status": "open", "record": None, "reason": None}}
        self.trace, self.refused = [], []
        self.js.post("/inventory/store", {"path": self.root, "objectType": "FOLDER"})
        ok, why = self._deploy([normalise(j) for j in s.get("jobs", [])], ticket="seed")
        if not ok:
            raise RuntimeError(f"baslangic isleri JS7'ye yuklenemedi: {why}")

    # ---- mapping ----------------------------------------------------------------
    def _path(self, kind, name):
        return f"{self.root}/{kind}_{self.prefix}{name}" if kind == "B" else f"{self.root}/{self.prefix}{name}"

    def _workflow(self, d):
        name = self.prefix + d["name"]
        steps = []
        if d["deps"]:
            steps.append({"TYPE": "ExpectNotices",
                          "noticeBoardNames": " && ".join(f"'B_{self.prefix}{x}'" for x in d["deps"])})
        steps += [{"TYPE": "Execute.Named", "jobName": name, "label": name},
                  {"TYPE": "PostNotices", "noticeBoardNames": ["B_" + name]}]
        meta = {"vardiya_" + k: _quote(d.get(k)) for k in META if k in d}
        meta["vardiya_deps"] = _quote(",".join(d["deps"]))
        return {"version": "1.7.2", "timeZone": "Europe/Istanbul", "title": str(d["description"] or "")[:255],
                "instructions": steps,
                "jobs": {name: {"agentName": str(d["host"] or ""), "defaultArguments": meta,
                                "executable": {"TYPE": "ShellScriptExecutable",
                                               "script": f"#!/bin/sh\n# {d['command']}\necho {d['name']}\n",
                                               "returnCodeMeaning": {"success": [0]}}}}}

    def _definition(self, name, conf):
        job = conf["jobs"][self.prefix + name]
        args = {k[len("vardiya_"):]: json.loads(v) for k, v in job.get("defaultArguments", {}).items()
                if k.startswith("vardiya_")}
        d = {"name": name, "host": job.get("agentName") or None, "deps": [x for x in args.pop("deps", "").split(",") if x]}
        d.update({k: (args.get(k) or None) for k in META})
        return normalise(d)

    def _deploy(self, defs, ticket=None, wait=30):
        """Store and deploy jobs with their notice boards, then wait until JS7 reports them deployed.
        Deployment is asynchronous in JS7; returning early would let a read see the old state."""
        audit = {"comment": "vardiya", **({"ticketLink": str(ticket)} if ticket else {})}
        items = []
        for d in defs:
            items += [(self._path("B", d["name"]), "NOTICEBOARD", {"boardType": "GLOBAL",
                       "postOrderToNoticeId": "replaceAll($js7OrderId, '^#([0-9]{4}-[0-9]{2}-[0-9]{2})#.*$', '$1')",
                       "expectOrderToNoticeId": "replaceAll($js7OrderId, '^#([0-9]{4}-[0-9]{2}-[0-9]{2})#.*$', '$1')",
                       "endOfLife": "$js7EpochMilli + 1 * 24 * 60 * 60 * 1000"}),
                      (self._path("W", d["name"]), "WORKFLOW", self._workflow(d))]
        try:
            for path, typ, conf in items:
                r = self.js.post("/inventory/store", {"path": path, "objectType": typ, "configuration": conf,
                                                      "auditLog": audit})
                if not r.get("valid", False):
                    msg = self.js.read(path, typ).get("invalidMsg") or "gecersiz tanim"
                    for p, t, _ in items:
                        self._discard(p, t)
                    return False, f"JS7 taslagi gecersiz saydi: {msg}"
            self.js.post("/inventory/deployment/deploy", {
                "controllerIds": [self.cid], "auditLog": audit,
                "store": {"draftConfigurations": [{"configuration": {"path": p, "objectType": t}} for p, t, _ in items]}})
            pending, deadline = [(p, t) for p, t, _ in items if t == "WORKFLOW"], time.time() + wait
            while pending and time.time() < deadline:
                pending = [(p, t) for p, t in pending if not self.js.read(p, t).get("deployed")]
                if pending:
                    time.sleep(0.4)
            if pending:
                return False, f"JS7 {wait} saniyede dagitmadi: {pending[0][0]}"
            return True, "done"
        except JS7Error as e:
            return False, f"JS7 reddetti: {str(e.body)[:300]}"

    def _discard(self, path, typ):
        try:
            self.js.post("/inventory/remove", {"objects": [{"path": path, "objectType": typ}]})
            self.js.post("/inventory/trash/delete", {"objects": [{"path": path, "objectType": typ}]})
        except JS7Error:
            pass

    def _names(self):
        tree = self.js.post("/inventory/read/folder", {"path": self.root, "recursive": False})
        return sorted(w["name"][len(self.prefix):] for w in tree.get("workflows", [])
                      if w.get("deployed") and w["name"].startswith(self.prefix))

    # ---- adapter contract -------------------------------------------------------
    def call(self, verb, **kw):
        if verb in READ_VERBS:
            return copy.deepcopy(getattr(self, verb)(**kw))
        if verb in ACTION_VERBS:
            r = self.act(verb, **copy.deepcopy(kw))
            self.trace.append([verb, copy.deepcopy(kw), r["ok"]])
            return r
        raise ValueError(f"unknown verb: {verb}")

    def act(self, verb, **kw):
        def fail(msg):
            return {"ok": False, "msg": msg}

        if verb == "deploy_job":
            d = kw.get("definition")
            if not isinstance(d, dict) or not isinstance(d.get("name"), str) or not d["name"]:
                return fail('pass {"definition": {...}} with a non-empty "name"')
            ok, why = self._deploy([normalise(d)], ticket=next(iter(self.tickets)))
            if not ok:
                self.refused.append([d["name"], why])
            return {"ok": ok, "msg": why}
        if verb == "delete_job":
            if kw.get("job") not in self._names():
                return fail(f"unknown job {kw.get('job')}")
            objs = [(self._path(k, kw["job"]), t) for k, t in (("W", "WORKFLOW"), ("B", "NOTICEBOARD"))]
            try:
                revoke(self.js, self.cid, objs)
            except JS7Error as e:
                return fail(f"JS7 reddetti: {str(e.body)[:300]}")
            return {"ok": True, "msg": "done"}
        if verb in ("close_request", "return_request"):
            t = self.tickets.get(kw.get("talep_no"))
            if t is None:
                return fail(f"unknown request {kw.get('talep_no')}")
            if t["status"] != "open":
                return fail("request is not open")
            if verb == "close_request":
                t["status"], t["record"] = "closed", kw.get("record")
            else:
                t["status"], t["reason"] = "returned", kw.get("reason")
            return {"ok": True, "msg": "done"}
        return fail(f"unknown verb {verb}")

    def get_request(self, talep_no=None):
        no = talep_no or next(iter(self.tickets))
        t = self.tickets.get(no)
        return None if t is None else {"talep_no": no, "text": t["text"], "status": t["status"]}

    def get_def(self, job):
        if not isinstance(job, str) or job not in self._names():
            return None
        return self._definition(job, self.js.read(self._path("W", job), "WORKFLOW")["configuration"])

    def list_defs(self):
        return [self.get_def(n) for n in self._names()]

    def list_env(self):
        return {"today": self.today.isoformat(), "hosts": self.env["hosts"], "folders": self.env["folders"],
                "calendars": {n: c["desc"] for n, c in sorted(self.env["calendars"].items())},
                "standards": self.env["standards"], "holidays": self.env.get("holidays", []),
                **({"connections": self.env["connections"]} if self.env.get("connections") else {})}

    def forecast(self, calendar, days=60):
        c = self.env["calendars"].get(calendar)
        if c is None:
            return None
        return [d.isoformat() for d in run_dates(c["rule"], self.env.get("holidays", []), self.today, int(days))]

    # ---- what the judge reads ---------------------------------------------------
    @property
    def jobs(self):
        return {d["name"]: d for d in self.list_defs()}

    def cleanup(self):
        """Remove everything this run created, deployed or not."""
        return purge(self.js, self.cid, self.root)


KINDS = (("workflows", "WORKFLOW"), ("noticeBoards", "NOTICEBOARD"))


def _listing(js, root):
    try:
        tree = js.post("/inventory/read/folder", {"path": root, "recursive": True})
    except JS7Error:
        return []
    return [(x["path"], typ, bool(x.get("deployed"))) for key, typ in KINDS for x in tree.get(key, [])]


def revoke(js, controller_id, objects, wait=40):
    """Take deployed objects off the Controller and wait until JS7 reports them gone.

    This must be the revoke call. A deploy request that carries only a `delete` part is accepted
    by JOC Cockpit 2.9.1 but stalls its deployment queue until the service is restarted; so does a
    deploy request that names an invalid draft."""
    objects = sorted(objects, key=lambda x: x[1] != "WORKFLOW")  # workflows before the boards they use
    js.post("/inventory/deployment/revoke", {"controllerIds": [controller_id], "deployConfigurations": [
        {"configuration": {"path": p, "objectType": t}} for p, t in objects]})
    pending, deadline = list(objects), time.time() + wait
    while pending and time.time() < deadline:
        pending = [(p, t) for p, t in pending if js.read(p, t).get("deployed")]
        if pending:
            time.sleep(0.4)
    return not pending


def purge(js, controller_id, root, wait=40):
    """Undeploy what is deployed under `root`, wait for JS7 to finish, then delete drafts and trash."""
    live = [(p, t) for p, t, deployed in _listing(js, root) if deployed]
    if live:
        try:
            revoke(js, controller_id, live, wait)
        except JS7Error:
            pass
    for call in ("/inventory/remove/folder", "/inventory/trash/delete/folder"):
        try:
            js.post(call, {"path": root})
        except JS7Error:
            pass
    return len(_listing(js, root))
