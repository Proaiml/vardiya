"""A Control-M Automation API shaped layer over the live lab.

The admin (a person or an agent) speaks Control-M: folders and jobs as Automation API JSON, `deploy`, `run order`,
`run jobs:status::get`, `run job:output::get`, `run job::rerun`, connection profiles, events. Behind it nothing is
simulated: every job becomes a workflow on the real scheduler, waits for its events on real notice boards and runs
on a real agent host, where runjob.py does the command, the file transfer or the database call.

This is a compatible subset, not BMC's product. What it keeps from Control-M on purpose:
- an ordered job is a copy: redeploying a definition does not change jobs already ordered (order again for that);
- connection profiles are read at run time, so fixing a profile and rerunning is enough;
- a job waits for its incoming events and deletes the ones a Flow gave it once it ends OK;
- "set to OK" makes the job green and releases its successors without doing its work.
"""
import base64
import datetime
import gzip
import json
import re
import shlex
import time
import urllib.request

from ..js7 import JS7Error
from ..js7repo import purge
from .lab import AGENTS

SERVER = "saha"
ROOT = "/ctm"
NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_\-]{0,63}$")
JOB_TYPES = {
    "Job:Command": ("Command",),
    "Job:Script": ("FileName", "FilePath"),
    "Job:FileTransfer": ("ConnectionProfileSrc", "ConnectionProfileDest", "FileTransfers"),
    "Job:Database:EmbeddedQuery": ("ConnectionProfile", "Query"),
    "Job:Database:SQLScript": ("ConnectionProfile", "SQLScript"),
    "Job:Database:StoredProcedure": ("ConnectionProfile", "StoredProcedure"),
    "Job:FileWatcher:Create": ("Path",),
    "Job:Dummy": (),
}
CP_TYPES = {
    "ConnectionProfile:FileTransfer:SFTP": ("HostName", "User"),
    "ConnectionProfile:FileTransfer:Local": ("User",),
    "ConnectionProfile:Database:PostgreSQL": ("Host", "User", "Password", "DatabaseName"),
}
BOARD = {"boardType": "GLOBAL",
         "postOrderToNoticeId": "replaceAll($js7OrderId, '^#([0-9]{4}-[0-9]{2}-[0-9]{2})#.*$', '$1')",
         "expectOrderToNoticeId": "replaceAll($js7OrderId, '^#([0-9]{4}-[0-9]{2}-[0-9]{2})#.*$', '$1')",
         "endOfLife": "$js7EpochMilli + 2 * 24 * 60 * 60 * 1000"}
SCRIPT = "#!/bin/sh\nexec python3 /opt/ctm/bin/runjob.py\n"
AUDIT = {"comment": "vardiya saha"}
FINAL = ("Ended OK", "Ended Not OK")


class CtmError(Exception):
    """An error the product itself reports back to the caller (bad definition, unknown job, wrong state)."""


def _safe(name):
    return re.sub(r"[^A-Za-z0-9_]", "_", name)


def _board(event):
    return "E_" + _safe(event)


def _wf(folder, job):
    return f"{_safe(folder)}__{_safe(job)}"


class Ctm:
    def __init__(self, lab):
        self.lab, self.cid = lab, lab.cid
        self.state = {"folders": {}, "active": {}, "seq": 0, "boards": [], "log": []}
        if lab.durum.exists():
            try:
                self.state.update(json.loads(lab.durum.read_text(encoding="utf-8")))
            except ValueError:
                pass

    # ---- store ------------------------------------------------------------------
    def _save(self):
        self.lab.durum.parent.mkdir(parents=True, exist_ok=True)
        self.lab.durum.write_text(json.dumps(self.state, ensure_ascii=False, indent=1), encoding="utf-8")

    def _note(self, job_id, text):
        a = self.state["active"].get(job_id)
        if a is not None:
            a.setdefault("log", []).append(f"{datetime.datetime.now().strftime('%H:%M:%S')} {text}")

    def audit(self, verb, detail):
        self.state["log"].append([datetime.datetime.now().strftime("%H:%M:%S"), verb, detail])

    # ---- reset ------------------------------------------------------------------
    def reset(self):
        """Empty the scheduler side: cancel live orders, undeploy everything under /ctm, forget the active jobs."""
        lab = self.lab
        try:
            live = lab.post("/orders", {"controllerId": self.cid, "folders": [{"folder": ROOT, "recursive": True}]})
            ids = [o["orderId"] for o in live.get("orders", [])]
            if ids:
                lab.post("/orders/cancel", {"controllerId": self.cid, "orderIds": ids, "kill": True, "auditLog": AUDIT})
                deadline = time.time() + 20
                while time.time() < deadline and lab.post("/orders", {"controllerId": self.cid, "folders": [
                        {"folder": ROOT, "recursive": True}]}).get("orders"):
                    time.sleep(0.5)
        except JS7Error:
            pass
        left = purge(lab.js, self.cid, ROOT)
        self.state = {"folders": {}, "active": {}, "seq": self.state.get("seq", 0), "boards": [], "log": []}
        self._save()
        for host in AGENTS:
            if lab.running(host):
                lab.sh(host, "rm -f /opt/ctm/cp/*.json /opt/ctm/cp/known_hosts")
        return left

    # ---- definitions ------------------------------------------------------------
    def build(self, defs):
        """Validate definitions the way `ctm build` does. Returns (folders, profiles); raises CtmError."""
        if isinstance(defs, str):
            try:
                defs = json.loads(defs)
            except ValueError as e:
                raise CtmError(f"JSON okunamadi: {e}") from None
        if not isinstance(defs, dict) or not defs:
            raise CtmError("tanim bos: en ust duzeyde en az bir Folder ya da ConnectionProfile nesnesi olmali")
        folders, profiles, errors = {}, {}, []
        agents = set(self.lab.cfg["agents"])
        for name, obj in defs.items():
            if not isinstance(obj, dict) or "Type" not in obj:
                errors.append(f"{name}: 'Type' alani yok")
                continue
            typ = obj["Type"]
            if typ.startswith("ConnectionProfile:"):
                if typ not in CP_TYPES:
                    errors.append(f"{name}: desteklenmeyen profil tipi {typ}; desteklenenler: {', '.join(CP_TYPES)}")
                    continue
                miss = [f for f in CP_TYPES[typ] if not obj.get(f)]
                if typ.endswith(":SFTP") and not (obj.get("Password") or obj.get("PrivateKeyName")):
                    miss.append("Password ya da PrivateKeyName")
                if miss:
                    errors.append(f"{name}: eksik alan {', '.join(miss)}")
                if not NAME.match(name):
                    errors.append(f"{name}: profil adi harfle baslamali, yalnizca harf, rakam, _ ve - icermeli")
                profiles[name] = obj
            elif typ in ("Folder", "SimpleFolder"):
                if not NAME.match(name):
                    errors.append(f"{name}: klasor adi harfle baslamali, yalnizca harf, rakam, _ ve - icermeli")
                jobs = {k: v for k, v in obj.items() if isinstance(v, dict) and str(v.get("Type", "")).startswith("Job:")}
                flows = {k: v for k, v in obj.items() if isinstance(v, dict) and v.get("Type") == "Flow"}
                if not jobs:
                    errors.append(f"{name}: klasorde is yok")
                for jn, j in jobs.items():
                    where = f"{name}/{jn}"
                    if not NAME.match(jn):
                        errors.append(f"{where}: is adi harfle baslamali, yalnizca harf, rakam, _ ve - icermeli")
                    if j["Type"] not in JOB_TYPES:
                        errors.append(f"{where}: desteklenmeyen is tipi {j['Type']}; desteklenenler: {', '.join(JOB_TYPES)}")
                        continue
                    miss = [f for f in JOB_TYPES[j["Type"]] if not j.get(f)]
                    if miss:
                        errors.append(f"{where}: {j['Type']} icin eksik alan {', '.join(miss)}")
                    host = j.get("Host") or obj.get("Host")
                    if not host:
                        errors.append(f"{where}: Host yok (iste ya da klasorde tanimlanmali)")
                    elif host not in agents:
                        errors.append(f"{where}: Host '{host}' bu sunucuda tanimli bir ajan degil; ajanlar: {', '.join(sorted(agents))}")
                    needs_user = j["Type"] in ("Job:Command", "Job:Script")
                    if needs_user and not (j.get("RunAs") or obj.get("RunAs")):
                        errors.append(f"{where}: RunAs yok (iste ya da klasorde tanimlanmali)")
                    if j["Type"] == "Job:FileTransfer":
                        ft = j.get("FileTransfers")
                        if not isinstance(ft, list) or not all(isinstance(t, dict) and t.get("Src") and t.get("Dest") for t in ft or [{}]):
                            errors.append(f"{where}: FileTransfers, her biri Src ve Dest tasiyan nesnelerin listesi olmali")
                    for key in ("WaitForEvents", "AddEvents", "DeleteEvents"):
                        ev = j.get(key)
                        if ev is not None and not (isinstance(ev, dict) and isinstance(ev.get("Events"), list)
                                                   and all(isinstance(e, dict) and e.get("Event") for e in ev["Events"])):
                            errors.append(f'{where}: {key} bicimi {{"Type": "{key}", "Events": [{{"Event": "AD"}}]}} olmali')
                for fn, f in flows.items():
                    seq = f.get("Sequence")
                    if not isinstance(seq, list) or len(seq) < 2:
                        errors.append(f"{name}/{fn}: Flow.Sequence en az iki is adi tasimali")
                        continue
                    for s in seq:
                        if s not in jobs:
                            errors.append(f"{name}/{fn}: Flow.Sequence icindeki '{s}' bu klasorde tanimli bir is degil")
                folders[name] = obj
            else:
                errors.append(f"{name}: desteklenmeyen Type '{typ}' (Folder, Job:*, Flow, ConnectionProfile:* beklenir)")
        if errors:
            raise CtmError("tanim gecersiz:\n- " + "\n- ".join(errors))
        return folders, profiles

    def _events(self, folder, fdef):
        """{job: (waits consumed, waits kept, posts)} from Flow objects and explicit event fields."""
        jobs = [k for k, v in fdef.items() if isinstance(v, dict) and str(v.get("Type", "")).startswith("Job:")]
        consume, keep, post = {j: [] for j in jobs}, {j: [] for j in jobs}, {j: [] for j in jobs}
        for v in fdef.values():
            if isinstance(v, dict) and v.get("Type") == "Flow":
                seq = v["Sequence"]
                for a, b in zip(seq, seq[1:]):
                    ev = f"{a}-TO-{b}"
                    if ev not in post[a]:
                        post[a].append(ev)
                    if ev not in consume[b]:
                        consume[b].append(ev)
        for j in jobs:
            d = fdef[j]
            drop = [e["Event"] for e in (d.get("DeleteEvents") or {}).get("Events", [])]
            for e in (d.get("WaitForEvents") or {}).get("Events", []):
                (consume if e["Event"] in drop else keep)[j].append(e["Event"])
            post[j] += [e["Event"] for e in (d.get("AddEvents") or {}).get("Events", []) if e["Event"] not in post[j]]
        return consume, keep, post

    def _workflow(self, folder, fdef, job, consume, keep, post):
        d = fdef[job]
        name = _wf(folder, job)
        core = [{"TYPE": "Execute.Named", "jobName": name, "label": "calistir"}]
        rerun = d.get("Rerun") if isinstance(d.get("Rerun"), dict) else None
        tries = int(str((rerun or {}).get("Times", "0")) or 0)
        if tries > 0:
            unit = {"Seconds": 1, "Minutes": 60, "Hours": 3600}.get((rerun or {}).get("Units", "Minutes"), 60)
            delay = int(str((rerun or {}).get("Interval", "0")) or 0) * unit
            core = [{"TYPE": "Try", "maxTries": tries + 1, "retryDelays": [delay],
                     "try": {"instructions": core}, "catch": {"instructions": [{"TYPE": "Retry"}]}}]
        if consume:
            core = [{"TYPE": "ConsumeNotices", "noticeBoardNames": " && ".join(f"'{_board(e)}'" for e in consume),
                     "subworkflow": {"instructions": core}}]
        steps = ([{"TYPE": "ExpectNotices", "noticeBoardNames": " && ".join(f"'{_board(e)}'" for e in keep)}] if keep else []) + core
        if post:
            steps.append({"TYPE": "PostNotices", "noticeBoardNames": [_board(e) for e in post]})
        return {"version": "1.7.2", "timeZone": "Europe/Istanbul", "title": f"{folder}/{job}"[:255],
                "orderPreparation": {"parameters": {"spec": {"type": "String", "default": "''"}}, "allowUndeclared": False},
                "instructions": steps,
                "jobs": {name: {"agentName": d.get("Host") or fdef.get("Host"),
                                "executable": {"TYPE": "ShellScriptExecutable", "script": SCRIPT, "env": {"CTM_SPEC": "$spec"},
                                               "returnCodeMeaning": {"success": [0]}}}}}

    def _store_deploy(self, items, wait=40):
        """Store drafts and deploy them in one request; wait until the scheduler reports the workflows deployed."""
        lab = self.lab
        for path, typ, conf in items:
            r = lab.post("/inventory/store", {"path": path, "objectType": typ, "configuration": conf, "auditLog": AUDIT})
            if not r.get("valid", False):
                msg = lab.js.read(path, typ).get("invalidMsg") or "gecersiz tanim"
                raise CtmError(f"zamanlayici tanimi reddetti ({path}): {msg}")
        lab.post("/inventory/deployment/deploy", {"controllerIds": [self.cid], "auditLog": AUDIT, "store": {
            "draftConfigurations": [{"configuration": {"path": p, "objectType": t}} for p, t, _ in items]}})
        pending, deadline = [(p, t) for p, t, _ in items], time.time() + wait
        while pending and time.time() < deadline:
            pending = [(p, t) for p, t in pending if not lab.js.read(p, t).get("deployed")]
            if pending:
                time.sleep(0.3)
        if pending:
            raise CtmError(f"zamanlayici {wait} saniyede dagitmadi: {pending[0][0]}")

    def _ensure_boards(self, events):
        new = [e for e in events if _board(e) not in self.state["boards"]]
        return [(f"{ROOT}/x0olay/{_board(e)}", "NOTICEBOARD", BOARD) for e in new], [_board(e) for e in new]

    def deploy(self, defs):
        """Deploy folders and connection profiles. A folder replaces its previous definition as a whole."""
        folders, profiles = self.build(defs)
        lab = self.lab
        done = {"deployedFolders": [], "deployedJobs": [], "deployedConnectionProfiles": [], "removedJobs": []}
        for name, cp in profiles.items():
            text = json.dumps(cp, ensure_ascii=False)
            for host in AGENTS:
                if lab.running(host):
                    lab.write(host, f"/opt/ctm/cp/{name}.json", text, owner="jobscheduler", mode="600")
            done["deployedConnectionProfiles"].append(name)
        items, boards = [], []
        for fname, fdef in folders.items():
            consume, keep, post = self._events(fname, fdef)
            jobs = list(consume)
            events = sorted({e for j in jobs for e in consume[j] + keep[j] + post[j]})
            b_items, b_names = self._ensure_boards([e for e in events if _board(e) not in boards])
            items += b_items
            boards += b_names
            for j in jobs:
                items.append((f"{ROOT}/{_safe(fname)}/{_wf(fname, j)}", "WORKFLOW",
                              self._workflow(fname, fdef, j, consume[j], keep[j], post[j])))
        if items:
            lab.post("/inventory/store", {"path": ROOT, "objectType": "FOLDER"})
            self._store_deploy(sorted(items, key=lambda x: x[1] != "NOTICEBOARD"))
            self.state["boards"] += boards
        for fname, fdef in folders.items():
            old = self.state["folders"].get(fname, {})
            gone = [k for k, v in old.items() if isinstance(v, dict) and str(v.get("Type", "")).startswith("Job:")
                    and k not in fdef]
            if gone:
                self._revoke([(f"{ROOT}/{_safe(fname)}/{_wf(fname, j)}", "WORKFLOW") for j in gone])
                done["removedJobs"] += [f"{fname}/{j}" for j in gone]
            self.state["folders"][fname] = fdef
            done["deployedFolders"].append(fname)
            done["deployedJobs"] += [f"{fname}/{k}" for k, v in fdef.items()
                                     if isinstance(v, dict) and str(v.get("Type", "")).startswith("Job:")]
        self.audit("deploy", {k: v for k, v in done.items() if v})
        self._save()
        return done

    def _revoke(self, objects, wait=30):
        lab = self.lab
        try:
            lab.post("/inventory/deployment/revoke", {"controllerIds": [self.cid], "auditLog": AUDIT, "deployConfigurations": [
                {"configuration": {"path": p, "objectType": t}} for p, t in objects]})
        except JS7Error as e:
            raise CtmError(f"zamanlayici kaldirmayi reddetti: {str(e.body)[:200]}") from None
        pending, deadline = list(objects), time.time() + wait
        while pending and time.time() < deadline:
            pending = [(p, t) for p, t in pending if lab.js.read(p, t).get("deployed")]
            if pending:
                time.sleep(0.3)
        for p, t in objects:
            for call in ("/inventory/remove", "/inventory/trash/delete"):
                try:
                    lab.post(call, {"objects": [{"path": p, "objectType": t}]})
                except JS7Error:
                    pass

    def get_jobs(self, folder=None, job=None):
        out = {}
        for fname, fdef in self.state["folders"].items():
            if folder and not _match(folder, fname):
                continue
            if job:
                keep = {k: v for k, v in fdef.items() if not (isinstance(v, dict) and str(v.get("Type", "")).startswith("Job:"))
                        or _match(job, k)}
                if not any(isinstance(v, dict) and str(v.get("Type", "")).startswith("Job:") for v in keep.values()):
                    continue
                out[fname] = keep
            else:
                out[fname] = fdef
        return out

    def delete_folder(self, folder):
        fdef = self.state["folders"].get(folder)
        if fdef is None:
            raise CtmError(f"klasor bulunamadi: {folder}")
        jobs = [k for k, v in fdef.items() if isinstance(v, dict) and str(v.get("Type", "")).startswith("Job:")]
        live = [a for a in self.state["active"].values() if a["folder"] == folder and not a.get("deleted")
                and self._status(a)["status"] not in FINAL]
        if live:
            raise CtmError(f"klasorde bitmemis {len(live)} aktif is var; once onlari sonlandirin ya da silin")
        self._revoke([(f"{ROOT}/{_safe(folder)}/{_wf(folder, j)}", "WORKFLOW") for j in jobs])
        del self.state["folders"][folder]
        self.audit("delete_folder", folder)
        self._save()
        return {"message": f"klasor silindi: {folder}"}

    # ---- connection profiles ----------------------------------------------------
    def get_profiles(self, name=None):
        host = next((h for h in AGENTS if self.lab.running(h)), None)
        if host is None:
            raise CtmError("hicbir ajan calismiyor; profiller okunamadi")
        rc, out = self.lab.sh(host, "cd /opt/ctm/cp && for f in *.json; do [ -f \"$f\" ] && { printf '%s\\t' \"${f%.json}\"; tr -d '\\n' < \"$f\"; echo; }; done; true")
        res = {}
        for ln in out.splitlines():
            n, _, body = ln.partition("\t")
            if not body or (name and not _match(name, n)):
                continue
            try:
                cp = json.loads(body)
            except ValueError:
                cp = {"Type": "?", "_hata": "profil dosyasi bozuk"}
            for secret in ("Password", "Passphrase"):
                if cp.get(secret):
                    cp[secret] = "*****"
            res[n] = cp
        return res

    def delete_profile(self, name):
        for host in AGENTS:
            if self.lab.running(host):
                self.lab.sh(host, f"rm -f /opt/ctm/cp/{shlex.quote(name)}.json")
        self.audit("delete_profile", name)
        return {"message": f"profil silindi: {name}"}

    def test_profile(self, name, agent=None):
        """Try the profile from an agent host: an SFTP login, a database login, or a local account check."""
        agent = agent or AGENTS[0]
        if not self.lab.running(agent):
            raise CtmError(f"ajan calismiyor: {agent}")
        rc, body = self.lab.sh(agent, f"cat /opt/ctm/cp/{shlex.quote(name)}.json")
        if rc:
            raise CtmError(f"profil bulunamadi: {name} (ajan {agent})")
        cp = json.loads(body)
        typ = cp.get("Type", "")
        if typ.endswith(":SFTP"):
            common = (f"-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/opt/ctm/cp/known_hosts -o ConnectTimeout=8 "
                      f"-P {cp.get('Port', 22)} -b - {cp.get('User')}@{cp.get('HostName')}")
            if cp.get("PrivateKeyName"):
                cmd = f"printf 'pwd\\n' | sftp -i /opt/ctm/keys/{cp['PrivateKeyName']} -o IdentitiesOnly=yes -o BatchMode=yes {common}"
            else:
                cmd = (f"printf 'pwd\\n' | SSHPASS={shlex.quote(str(cp.get('Password', '')))} sshpass -e sftp "
                       f"-o PubkeyAuthentication=no -o PreferredAuthentications=password -o NumberOfPasswordPrompts=1 -o BatchMode=no {common}")
        elif typ.endswith(":PostgreSQL"):
            cmd = (f"PGPASSWORD={shlex.quote(str(cp.get('Password', '')))} PGCONNECT_TIMEOUT=8 psql -h {cp.get('Host')} -p {cp.get('Port', 5432)} "
                   f"-U {cp.get('User')} -d {cp.get('DatabaseName')} -X -At -c 'select current_user'")
        else:
            cmd = f"id {shlex.quote(str(cp.get('User', '')))}"
        rc, out = self.lab.sh(agent, cmd, user="jobscheduler", timeout=30)
        return {"profile": name, "agent": agent, "result": "OK" if rc == 0 else "FAILED",
                "output": "\n".join(out.strip().splitlines()[-4:])}

    # ---- ordering ---------------------------------------------------------------
    def _resolve(self, value, variables):
        if isinstance(value, str):
            return re.sub(r"%%(\$?[A-Za-z_][A-Za-z0-9_]*)", lambda m: str(variables.get(m.group(1), m.group(0))), value)
        if isinstance(value, list):
            return [self._resolve(v, variables) for v in value]
        if isinstance(value, dict):
            return {k: self._resolve(v, variables) for k, v in value.items()}
        return value

    def _spec(self, folder, job, job_id, odate, run):
        fdef = self.state["folders"][folder]
        d = fdef[job]
        variables = {}
        for src in (fdef.get("Variables") or [], d.get("Variables") or []):
            for item in src:
                if isinstance(item, dict):
                    variables.update({str(k): v for k, v in item.items()})
        variables.update({"ODATE": odate.strftime("%y%m%d"), "$ODATE": odate.strftime("%Y%m%d"), "JOBNAME": job,
                          "ORDERID": job_id, "RUNCOUNT": run, "DAY": odate.strftime("%d"), "MONTH": odate.strftime("%m"),
                          "$YEAR": odate.strftime("%Y"), "YEAR": odate.strftime("%y")})
        skip = ("Type", "Variables", "WaitForEvents", "AddEvents", "DeleteEvents", "When", "Description", "Rerun")
        spec = {k: self._resolve(v, variables) for k, v in d.items() if k not in skip}
        spec.update({"type": d["Type"], "name": job, "folder": folder, "odate": odate.strftime("%Y%m%d"), "run": run,
                     "RunAs": spec.get("RunAs") or fdef.get("RunAs", ""),
                     "vars": {k: v for k, v in variables.items() if not k.startswith("$")}})
        return spec

    def _add_order(self, folder, job, job_id, run, spec):
        body = {"controllerId": self.cid, "auditLog": AUDIT, "orders": [{
            "orderName": f"{job_id}r{run}-{_safe(job)}"[:30], "workflowPath": f"{ROOT}/{_safe(folder)}/{_wf(folder, job)}",
            "scheduledFor": "now", "arguments": {"spec": base64.b64encode(json.dumps(spec).encode()).decode()}}]}
        last = None
        for _ in range(20):           # the Controller may learn about a fresh workflow a moment after JOC says deployed
            try:
                return self.lab.post("/orders/add", body)["orderIds"][0]
            except JS7Error as e:
                last = e
                if "Unknown" not in str(e.body):
                    break
                time.sleep(0.5)
        raise CtmError(f"zamanlayici siparisi kabul etmedi: {str(last.body)[:300]}")

    def order(self, folder, job=None, hold=False):
        fdef = self.state["folders"].get(folder)
        if fdef is None:
            raise CtmError(f"klasor bulunamadi: {folder}; tanimli klasorler: {', '.join(sorted(self.state['folders'])) or '-'}")
        jobs = [k for k, v in fdef.items() if isinstance(v, dict) and str(v.get("Type", "")).startswith("Job:")]
        if job:
            if job not in jobs:
                raise CtmError(f"is bulunamadi: {folder}/{job}")
            jobs = [job]
        odate, ids = datetime.date.today(), []
        self.state["seq"] += 1
        run_id = f"{self.state['seq']:04d}"
        for j in jobs:
            self.state["seq"] += 1
            job_id = f"{SERVER}:{self.state['seq']:05x}"
            short = job_id.split(":")[1]
            spec = self._spec(folder, j, short, odate, 1)
            oid = self._add_order(folder, j, short, 1, spec)
            self.state["active"][job_id] = {"jobId": job_id, "folder": folder, "name": j, "host": fdef[j].get("Host") or fdef.get("Host"),
                                            "type": fdef[j]["Type"], "orders": [oid], "spec": spec, "runId": run_id,
                                            "odate": odate.strftime("%Y%m%d"), "log": [], "final": {}}
            self._note(job_id, f"siparis edildi (ODATE {odate.strftime('%Y%m%d')})")
            ids.append(job_id)
            if hold:
                self.hold(job_id)
        self.audit("order", {"folder": folder, "job": job, "jobIds": ids})
        self._save()
        return {"runId": run_id, "statusURI": f"run status {run_id}", "jobIds": ids}

    # ---- status -----------------------------------------------------------------
    def _live(self):
        r = self.lab.post("/orders", {"controllerId": self.cid, "folders": [{"folder": ROOT, "recursive": True}]})
        return {o["orderId"]: o for o in r.get("orders", [])}

    def _history(self, order_id):
        h = self.lab.post("/orders/history", {"controllerId": self.cid, "orderId": order_id}).get("history", [])
        return h[0] if h else None

    def _tasks(self, a):
        """Every execution of this job, oldest first, across the orders that carried it."""
        out = []
        for oid in a["orders"]:
            wf = f"{ROOT}/{_safe(a['folder'])}/{_wf(a['folder'], a['name'])}"
            t = self.lab.post("/tasks/history", {"controllerId": self.cid, "orders": [{"workflowPath": wf, "orderId": oid}]})
            out += sorted((x for x in t.get("history", []) if x.get("orderId") == oid), key=lambda x: x.get("startTime", ""))
        return out

    def _status(self, a, live=None):
        if a.get("deleted"):
            return {"status": "Deleted", "held": False}
        if a.get("forced_ok"):
            return {"status": "Ended OK", "held": False, "note": "set to OK"}
        oid = a["orders"][-1]
        if a["final"].get(oid):
            return a["final"][oid]
        live = self._live() if live is None else live
        o = live.get(oid)
        if o is not None:
            st = o.get("state", {}).get("_text", "?")
            held = bool(a.get("held")) or st == "SUSPENDED" or (o.get("marked") or {}).get("_text") == "SUSPENDING"
            agents = self.lab.agent_states()
            down = agents.get(a["host"]) not in (None, "COUPLED")
            if st == "WAITING":
                waits = [n.get("boardName", "")[2:] for n in o.get("expectedNotices") or []]
                return {"status": "Wait Condition", "held": held, "waitingFor": {"events": self._event_names(waits)}}
            if st == "FAILED":
                return {"status": "Ended Not OK", "held": held}
            if st in ("RUNNING",):
                return {"status": "Executing", "held": held, **({"note": f"ajan {a['host']} yanit vermiyor"} if down else {})}
            if st == "BLOCKED" or (st in ("INPROGRESS", "PENDING", "SCHEDULED") and down):
                return {"status": "Wait Host", "held": held, "waitingFor": {"agent": a["host"], "agentState": agents.get(a["host"])}}
            if st == "SUSPENDED":
                return {"status": "Wait User", "held": True}
            return {"status": "Wait Host" if down else "Executing", "held": held}
        # The history record is opened when the order starts and closed a moment after it ends: only a closed
        # record (it has an end time and a final order state) says how the job ended.
        closed = lambda x: x is not None and x.get("endTime") and x.get("orderState", {}).get("_text") in ("FINISHED", "CANCELLED", "FAILED")  # noqa: E731
        h = self._history(oid)
        for _ in range(12):
            if closed(h):
                break
            time.sleep(0.5)
            if oid in self._live():
                return self._status(a)
            h = self._history(oid)
        if not closed(h):
            return {"status": "Executing", "held": False}
        ok = h.get("state", {}).get("_text") == "SUCCESSFUL" and h.get("orderState", {}).get("_text") == "FINISHED"
        res = {"status": "Ended OK" if ok else "Ended Not OK", "held": False}
        if h.get("orderState", {}).get("_text") == "CANCELLED":
            res["note"] = "killed" if a.get("killed") else "cancelled"
        a["final"][oid] = res
        return res

    def _event_names(self, boards):
        known = {}
        for fname, fdef in self.state["folders"].items():
            c, k, p = self._events(fname, fdef)
            for group in (c, k, p):
                for evs in group.values():
                    for e in evs:
                        known[_safe(e)] = e
        return [known.get(b, b) for b in boards]

    def status(self, folder=None, job=None, status=None, job_id=None, run_id=None):
        live, out = self._live(), []
        for jid, a in self.state["active"].items():
            if a.get("deleted") or (folder and not _match(folder, a["folder"])) or (job and not _match(job, a["name"])) \
                    or (job_id and jid != job_id) or (run_id and a["runId"] != run_id):
                continue
            s = self._status(a, live)
            if status and s["status"].lower() != status.lower():
                continue
            row = {"jobId": jid, "folder": a["folder"], "name": a["name"], "type": a["type"].split(":", 1)[1], "host": a["host"],
                   "status": s["status"], "held": s["held"], "numberOfRuns": self._runs(a), "orderDate": a["odate"]}
            row.update({k: v for k, v in s.items() if k in ("waitingFor", "note")})
            out.append(row)
        self._save()
        return {"statuses": out, "returned": len(out), "total": len(out)}

    def _runs(self, a):
        if "runs" in a and a.get("runs_at") == len(a["orders"]) and a["final"].get(a["orders"][-1]):
            return a["runs"]
        n = len(self._tasks(a))
        if n:                                  # the task history trails the order; never cache "no runs yet"
            a["runs"], a["runs_at"] = n, len(a["orders"])
        return n

    def _job(self, job_id):
        job_id = job_id if ":" in job_id else f"{SERVER}:{job_id}"
        a = self.state["active"].get(job_id)
        if a is None or a.get("deleted"):
            raise CtmError(f"aktif is bulunamadi: {job_id} (jobId'ler `run jobs:status::get` ciktisindadir)")
        return job_id, a

    def waiting_info(self, job_id):
        job_id, a = self._job(job_id)
        s = self._status(a)
        info = []
        if s["status"] == "Wait Condition":
            info = [f"olay bekleniyor: {e} (ODAT)" for e in s.get("waitingFor", {}).get("events", [])]
        elif s["status"] == "Wait Host":
            info = [f"ajan {a['host']} kullanilamiyor (durum: {s.get('waitingFor', {}).get('agentState')})"]
        if s.get("held"):
            info.append("is tutuluyor (hold)")
        return {"jobId": job_id, "status": s["status"], "waitingInfo": info or ["bekleme nedeni yok"]}

    def output(self, job_id, run_no=None, tail=120):
        job_id, a = self._job(job_id)
        tasks = self._tasks(a)
        for _ in range(8):
            if tasks or self._status(a)["status"] not in FINAL:
                break
            time.sleep(0.5)
            tasks = self._tasks(a)
        if not tasks:
            s = self._status(a)
            return f"(bu is henuz calismadi; durum: {s['status']})"
        idx = len(tasks) if not run_no else int(run_no)
        if not 1 <= idx <= len(tasks):
            raise CtmError(f"kosu numarasi 1 ile {len(tasks)} arasinda olmali")
        text = self._task_log(tasks[idx - 1]["taskId"])
        lines = [re.sub(r"^\S+ \S+ \[(MAIN|STDOUT|STDERR)\]\s{0,4}", lambda m: "" if m.group(1) == "STDOUT" else f"[{m.group(1)}] ", ln)
                 for ln in text.splitlines()]
        if len(lines) > tail:
            lines = [f"... ({len(lines) - tail} satir kisaltildi; tamami icin -s tail=N)"] + lines[-tail:]
        return f"# {a['folder']}/{a['name']} {job_id} kosu {idx}/{len(tasks)}\n" + "\n".join(lines)

    def _task_log(self, task_id):
        req = urllib.request.Request(self.lab.js.api + "/task/log", json.dumps({"controllerId": self.cid, "taskId": task_id}).encode(),
                                     {"Content-Type": "application/json", "X-Access-Token": self.lab.js.token or ""})
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
        if raw[:2] == bytes([31, 139]):
            raw = gzip.decompress(raw)
        return raw.decode("utf-8", "replace")

    def log(self, job_id):
        job_id, a = self._job(job_id)
        lines = list(a.get("log", []))
        for i, t in enumerate(self._tasks(a), 1):
            lines.append(f"{t.get('startTime', '')[11:19]}Z kosu {i} basladi (ajan {a['host']})")
            if t.get("endTime"):
                lines.append(f"{t['endTime'][11:19]}Z kosu {i} bitti: {'OK' if t.get('state', {}).get('_text') == 'SUCCESSFUL' else 'NOTOK'} "
                             f"cikis kodu {t.get('exitCode')}")
        return f"# is gunlugu {a['folder']}/{a['name']} {job_id}\n" + "\n".join(lines)

    # ---- actions on active jobs ---------------------------------------------------
    def rerun(self, job_id):
        job_id, a = self._job(job_id)
        s = self._status(a)
        if s["status"] not in FINAL:
            raise CtmError(f"is {s['status']} durumunda; yalnizca bitmis (Ended OK / Ended Not OK) is yeniden calistirilir")
        oid, live = a["orders"][-1], self._live()
        a.pop("forced_ok", None)
        if oid in live and live[oid].get("state", {}).get("_text") == "FAILED":
            self.lab.post("/orders/resume", {"controllerId": self.cid, "orderIds": [oid], "auditLog": AUDIT})
        else:
            run = len(a["orders"]) + 1
            a["orders"].append(self._add_order(a["folder"], a["name"], job_id.split(":")[1], run, a["spec"]))
        a.pop("killed", None)
        self._note(job_id, "kullanici yeniden calistirdi (rerun); is siparis anindaki tanimiyla calisir")
        self.audit("rerun", job_id)
        self._save()
        return {"message": f"{job_id} yeniden calistirildi"}

    def hold(self, job_id):
        job_id, a = self._job(job_id)
        s = self._status(a)
        if s["status"] in FINAL or s["status"] == "Executing":
            raise CtmError(f"is {s['status']} durumunda; hold yalnizca bekleyen ise uygulanir")
        self.lab.post("/orders/suspend", {"controllerId": self.cid, "orderIds": [a["orders"][-1]], "auditLog": AUDIT})
        a["held"] = True
        self._note(job_id, "kullanici tuttu (hold)")
        self.audit("hold", job_id)
        self._save()
        return {"message": f"{job_id} tutuldu"}

    def free(self, job_id):
        job_id, a = self._job(job_id)
        if not a.get("held"):
            raise CtmError("is tutulmuyor")
        oid = a["orders"][-1]
        try:
            self.lab.post("/orders/resume", {"controllerId": self.cid, "orderIds": [oid], "auditLog": AUDIT})
        except JS7Error:
            # still waiting for its events with the hold only marked: replace the order by an identical one
            self.lab.post("/orders/cancel", {"controllerId": self.cid, "orderIds": [oid], "auditLog": AUDIT})
            a["orders"][-1] = self._add_order(a["folder"], a["name"], job_id.split(":")[1], len(a["orders"]), a["spec"])
        a["held"] = False
        self._note(job_id, "kullanici serbest birakti (free)")
        self.audit("free", job_id)
        self._save()
        return {"message": f"{job_id} serbest"}

    def kill(self, job_id):
        job_id, a = self._job(job_id)
        s = self._status(a)
        if s["status"] != "Executing":
            raise CtmError(f"is {s['status']} durumunda; kill yalnizca calisan ise uygulanir")
        self.lab.post("/orders/cancel", {"controllerId": self.cid, "orderIds": [a["orders"][-1]], "kill": True, "auditLog": AUDIT})
        a["killed"] = True
        self._note(job_id, "kullanici sonlandirdi (kill)")
        self.audit("kill", job_id)
        self._save()
        return {"message": f"{job_id} sonlandirildi"}

    def set_to_ok(self, job_id):
        job_id, a = self._job(job_id)
        s = self._status(a)
        if s["status"] == "Executing":
            raise CtmError("calisan is OK yapilamaz; once bitmesini bekleyin ya da sonlandirin")
        oid = a["orders"][-1]
        if oid in self._live():
            self.lab.post("/orders/cancel", {"controllerId": self.cid, "orderIds": [oid], "auditLog": AUDIT})
        _, _, post = self._events(a["folder"], self.state["folders"].get(a["folder"], {a["name"]: {"Type": a["type"]}}))
        for ev in post.get(a["name"], []):
            self.add_event(ev, note=False)
        a["forced_ok"] = True
        self._note(job_id, "kullanici OK yapti (set to OK); is CALISMADAN yesile cekildi")
        self.audit("setToOk", job_id)
        self._save()
        return {"message": f"{job_id} OK yapildi"}

    def delete_job(self, job_id):
        job_id, a = self._job(job_id)
        oid = a["orders"][-1]
        if oid in self._live():
            self.lab.post("/orders/cancel", {"controllerId": self.cid, "orderIds": [oid], "kill": True, "auditLog": AUDIT})
        a["deleted"] = True
        self.audit("delete_job", job_id)
        self._save()
        return {"message": f"{job_id} aktif ortamdan silindi"}

    # ---- events -----------------------------------------------------------------
    def _notice_id(self):
        return datetime.date.today().isoformat()

    def add_event(self, event, note=True):
        items, names = self._ensure_boards([event])
        if items:
            self.lab.post("/inventory/store", {"path": ROOT, "objectType": "FOLDER"})
            self._store_deploy(items)
            self.state["boards"] += names
            time.sleep(1)
        for _ in range(10):
            try:
                self.lab.post("/notice/post", {"controllerId": self.cid, "noticeBoardPath": f"{ROOT}/x0olay/{_board(event)}",
                                               "noticeId": self._notice_id(), "auditLog": AUDIT})
                break
            except JS7Error as e:
                if "Unknown" not in str(e.body):
                    raise CtmError(f"olay eklenemedi: {str(e.body)[:200]}") from None
                time.sleep(0.5)
        if note:
            self.audit("event_add", event)
            self._save()
        return {"message": f"olay eklendi: {event} (ODAT)"}

    def delete_event(self, event):
        if _board(event) not in self.state["boards"]:
            raise CtmError(f"olay bulunamadi: {event}")
        try:
            self.lab.post("/notices/delete", {"controllerId": self.cid, "noticeBoardPath": f"{ROOT}/x0olay/{_board(event)}",
                                              "noticeIds": [self._notice_id()], "auditLog": AUDIT})
        except JS7Error as e:
            raise CtmError(f"olay silinemedi: {str(e.body)[:200]}") from None
        self.audit("event_delete", event)
        self._save()
        return {"message": f"olay silindi: {event}"}

    def events(self, name=None):
        out = []
        names = dict(zip([_board(e) for e in self._event_names([b[2:] for b in self.state["boards"]])],
                         self._event_names([b[2:] for b in self.state["boards"]])))
        for b in self.state["boards"]:
            ev = names.get(b, b[2:])
            if name and not _match(name, ev):
                continue
            try:
                r = self.lab.post("/notice/board", {"controllerId": self.cid, "noticeBoardPath": f"{ROOT}/x0olay/{b}"})
            except JS7Error:
                continue
            for n in r.get("noticeBoard", {}).get("notices", []):
                if n.get("state", {}).get("_text") == "POSTED":
                    out.append({"name": ev, "date": n.get("id", "")[5:].replace("-", "")})
        return out

    # ---- agents -----------------------------------------------------------------
    def agents(self):
        states = self.lab.agent_states()
        return [{"nodeid": a, "status": "Available" if states.get(a) == "COUPLED" else "Unavailable"} for a in sorted(self.lab.cfg["agents"])]

    def ping(self, agent):
        if agent not in self.lab.cfg["agents"]:
            raise CtmError(f"tanimli olmayan ajan: {agent}")
        state = self.lab.agent_states().get(agent)
        return {"agent": agent, "message": "Agent is available" if state == "COUPLED" else f"Agent is unavailable ({state})"}

    # ---- command line ------------------------------------------------------------
    def cli(self, line, body=None):
        """One `ctm ...` command line, the way the Automation API CLI takes it. Returns text (JSON or job output)."""
        try:
            argv = shlex.split(line.strip())
        except ValueError as e:
            return f"HATA: komut satiri cozumlenemedi: {e}"
        if argv[:1] == ["ctm"]:
            argv = argv[1:]
        try:
            return _fmt(self._dispatch(argv, body))
        except CtmError as e:
            return f"HATA: {e}"
        except JS7Error as e:
            return f"HATA: zamanlayici istegi reddetti: {str(e.body)[:300]}"

    def _dispatch(self, argv, body):
        if not argv:
            raise CtmError("komut bos. " + USAGE)
        opts = {}
        while "-s" in argv:
            i = argv.index("-s")
            if i + 1 >= len(argv):
                raise CtmError("-s icin deger yok; ornek: -s \"folder=GUNSONU&status=Ended Not OK\"")
            for part in argv[i + 1].split("&"):
                k, _, v = part.partition("=")
                opts[k.strip().lower()] = v.strip()
            del argv[i:i + 2]
        cmd, sub, args = argv[0], (argv[1] if len(argv) > 1 else ""), argv[2:]
        args = [a for a in args if a != SERVER] if sub not in ("event::add", "event::delete") else args
        if cmd in ("build", "deploy") and (not sub or sub.endswith(".json")):
            if body is None:
                raise CtmError(f'`{cmd}` tanimi "json" alaninda ister (dosya yolu degil)')
            if cmd == "build":
                f, p = self.build(body)
                return {"valid": True, "folders": sorted(f), "connectionProfiles": sorted(p)}
            return self.deploy(body)
        if cmd == "deploy":
            if sub == "jobs::get":
                return self.get_jobs(opts.get("folder"), opts.get("job") or opts.get("jobname"))
            if sub == "folder::delete":
                return self.delete_folder(_need(args, "klasor adi"))
            if sub == "connectionprofiles::get":
                return self.get_profiles(opts.get("name"))
            if sub == "connectionprofile::delete":
                return self.delete_profile(_need(args, "profil adi"))
            if sub == "connectionprofile::test":
                return self.test_profile(_need(args, "profil adi"), opts.get("agent") or (args[1] if len(args) > 1 else None))
        if cmd == "run":
            if sub == "order":
                return self.order(_need(args, "klasor adi"), args[1] if len(args) > 1 else opts.get("job"), hold=opts.get("hold") == "true")
            if sub == "jobs:status::get":
                return self.status(opts.get("folder"), opts.get("jobname") or opts.get("job"), opts.get("status"), opts.get("jobid"))
            if sub == "status":
                return self.status(run_id=_need(args, "runId"))
            if sub == "job:status::get":
                return self.status(job_id=self._job(_need(args, "jobId"))[0])
            if sub == "job:output::get":
                return self.output(_need(args, "jobId"), opts.get("runno"), int(opts.get("tail", 120)))
            if sub == "job:log::get":
                return self.log(_need(args, "jobId"))
            if sub == "job:waitingInfo::get":
                return self.waiting_info(_need(args, "jobId"))
            simple = {"job::rerun": self.rerun, "job::hold": self.hold, "job::free": self.free, "job::kill": self.kill,
                      "job::setToOk": self.set_to_ok, "job::delete": self.delete_job}
            if sub in simple:
                return simple[sub](_need(args, "jobId"))
            if sub in ("event::add", "event::delete"):
                names = [a for a in args if a != SERVER and not re.fullmatch(r"\d{4}|ODAT|STAT", a)]
                return (self.add_event if sub.endswith("add") else self.delete_event)(_need(names, "olay adi"))
            if sub == "events::get":
                return self.events(opts.get("name"))
        if cmd == "config":
            if sub in ("server:agents::get", "servers::get"):
                return self.agents() if sub.startswith("server:") else [{"name": SERVER, "state": "Up"}]
            if sub == "server:agent::ping":
                return self.ping(_need(args, "ajan adi"))
        raise CtmError(f"bilinmeyen komut: {' '.join(argv[:2])}. " + USAGE)


KINDS = (("workflows", "WORKFLOW"), ("noticeBoards", "NOTICEBOARD"))
USAGE = "Komutlar icin el kitabina bakin (deploy, run order, run jobs:status::get, run job:output::get, run job::rerun ...)."


def _need(args, what):
    if not args:
        raise CtmError(f"eksik arguman: {what}")
    return args[0]


def _match(pattern, value):
    return re.fullmatch(re.escape(pattern).replace(r"\*", ".*").replace(r"\?", "."), value, re.I) is not None


def _fmt(value):
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=1)
