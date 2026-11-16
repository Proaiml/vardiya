"""The same admin surface on a real Control-M, through its Automation API.

NOT YET RUN AGAINST A REAL CONTROL-M. No licensed Control-M (Workbench or a server) was available when this was
written; the endpoints follow BMC's Automation API reference. It is here so that the day an endpoint and a token
exist, the same scenarios, tools, harness and judge run against the real product:

    SAHA_AAPI=https://workbench:8443/automation-api SAHA_AAPI_USER=workbench SAHA_AAPI_PASS=... SAHA_AAPI_SERVER=workbench

`CtmAapi` keeps the command line of `Ctm` (the `cli` method and its dispatch) and replaces what happens behind each
verb with the REST call. What still needs the lab's own hosts (connection profile tests from an agent, the judge's
file and SQL checks) keeps working, because jobs still run on the lab's agent hosts once they are registered as
Control-M agents.

First things to verify on a real system, in this order: login, `deploy` of a one-job folder, `run order`, status
polling, output; then file transfer and database job types with their connection profiles (field names of the
profiles differ between plug-in versions).
"""
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request
import uuid

from .ctm import Ctm, CtmError


class CtmAapi(Ctm):
    def __init__(self, lab, endpoint=None, user=None, password=None, server=None, verify_tls=False):
        super().__init__(lab)
        self.endpoint = (endpoint or os.environ["SAHA_AAPI"]).rstrip("/")
        self.user, self.password = user or os.environ.get("SAHA_AAPI_USER", ""), password or os.environ.get("SAHA_AAPI_PASS", "")
        self.server = server or os.environ.get("SAHA_AAPI_SERVER", "workbench")
        self.token = os.environ.get("SAHA_AAPI_TOKEN")           # an API token (x-api-key) instead of a session login
        self._ctx = None if verify_tls else ssl._create_unverified_context()   # Workbench ships a self-signed certificate

    # ---- transport --------------------------------------------------------------
    def _call(self, method, path, body=None, files=None, query=None):
        url = self.endpoint + path + ("?" + urllib.parse.urlencode({k: v for k, v in (query or {}).items() if v not in (None, "")}) if query else "")
        headers = {}
        if os.environ.get("SAHA_AAPI_TOKEN"):
            headers["x-api-key"] = self.token
        elif path != "/session/login":
            if not self.token:
                self.token = self._call("POST", "/session/login", {"username": self.user, "password": self.password})["token"]
            headers["Authorization"] = "Bearer " + self.token
        data = None
        if files is not None:
            boundary = uuid.uuid4().hex
            parts = b"".join(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{name}.json"\r\n'
                             f"Content-Type: application/json\r\n\r\n".encode() + content.encode("utf-8") + b"\r\n" for name, content in files.items())
            data, headers["Content-Type"] = parts + f"--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"
        elif body is not None:
            data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
        req = urllib.request.Request(url, data, headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=120, context=self._ctx) as r:
                raw = r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                errs = json.loads(raw).get("errors") or []
                raise CtmError("; ".join(x.get("message", "") for x in errs) or raw[:400]) from None
            except ValueError:
                raise CtmError(f"HTTP {e.code}: {raw[:400]}") from None
        try:
            return json.loads(raw)
        except ValueError:
            return raw

    # ---- definitions ------------------------------------------------------------
    def build(self, defs):
        if isinstance(defs, str):
            defs = json.loads(defs)
        self._call("POST", "/build", files={"definitionsFile": json.dumps(defs)})
        folders = {k: v for k, v in defs.items() if isinstance(v, dict) and v.get("Type") in ("Folder", "SimpleFolder")}
        profiles = {k: v for k, v in defs.items() if isinstance(v, dict) and str(v.get("Type", "")).startswith("ConnectionProfile:")}
        return folders, profiles

    def deploy(self, defs):
        if isinstance(defs, str):
            defs = json.loads(defs)
        for v in defs.values():                                   # every folder names its server; the lab has one
            if isinstance(v, dict) and v.get("Type") in ("Folder", "SimpleFolder"):
                v.setdefault("ControlmServer", self.server)
        out = self._call("POST", "/deploy", files={"definitionsFile": json.dumps(defs)})
        for k, v in defs.items():
            if isinstance(v, dict) and v.get("Type") in ("Folder", "SimpleFolder"):
                self.state["folders"][k] = v
        self.audit("deploy", sorted(defs))
        self._save()
        return out

    def get_jobs(self, folder=None, job=None):
        return self._call("GET", "/deploy/jobs", query={"server": self.server, "folder": folder or "*", "job": job, "format": "json"})

    def delete_folder(self, folder):
        self.state["folders"].pop(folder, None)
        return self._call("DELETE", f"/deploy/folder/{self.server}/{urllib.parse.quote(folder)}")

    def get_profiles(self, name=None):
        return self._call("GET", "/deploy/connectionprofiles/centralized", query={"type": "*", "name": name or "*"})

    # ---- active jobs ------------------------------------------------------------
    def order(self, folder, job=None, hold=False):
        body = {"ctm": self.server, "folder": folder, "hold": "true" if hold else "false", "ignoreCriteria": "true"}
        if job:
            body["jobs"] = job
        r = self._call("POST", "/run/order", body)
        st = self._call("GET", f"/run/status/{r['runId']}")
        ids = [x["jobId"] for x in st.get("statuses", []) if x.get("type") != "Folder"]
        self.audit("order", {"folder": folder, "job": job, "jobIds": ids})
        return {"runId": r["runId"], "statusURI": r.get("statusURI"), "jobIds": ids}

    def status(self, folder=None, job=None, status=None, job_id=None, run_id=None):
        if run_id:
            r = self._call("GET", f"/run/status/{run_id}")
        else:
            r = self._call("GET", "/run/jobs/status", query={"server": self.server, "folder": folder, "jobname": job, "status": status,
                                                              "jobid": job_id, "limit": 500})
        rows = [{"jobId": x.get("jobId"), "folder": x.get("folder"), "name": x.get("name"), "type": x.get("type"), "host": x.get("host"),
                 "status": x.get("status"), "held": bool(x.get("held")), "numberOfRuns": x.get("numberOfRuns", 0), "orderDate": x.get("orderDate")}
                for x in r.get("statuses", []) if x.get("type") != "Folder"]
        return {"statuses": rows, "returned": len(rows), "total": r.get("total", len(rows))}

    def _job(self, job_id):
        return (job_id if ":" in job_id else f"{self.server}:{job_id}"), {}

    def output(self, job_id, run_no=None, tail=120):
        text = self._call("GET", f"/run/job/{self._job(job_id)[0]}/output", query={"runNo": run_no or 0})
        lines = str(text).splitlines()
        return "\n".join(lines[-tail:])

    def log(self, job_id):
        return str(self._call("GET", f"/run/job/{self._job(job_id)[0]}/log"))

    def waiting_info(self, job_id):
        return {"jobId": job_id, "waitingInfo": self._call("GET", f"/run/job/{self._job(job_id)[0]}/waitingInfo")}

    def _act(self, job_id, verb):
        self.audit(verb, job_id)
        return self._call("POST", f"/run/job/{self._job(job_id)[0]}/{verb}")

    def rerun(self, job_id):
        return self._act(job_id, "rerun")

    def hold(self, job_id):
        return self._act(job_id, "hold")

    def free(self, job_id):
        return self._act(job_id, "free")

    def kill(self, job_id):
        return self._act(job_id, "kill")

    def set_to_ok(self, job_id):
        return self._act(job_id, "setToOk")

    def delete_job(self, job_id):
        return self._act(job_id, "delete")

    # ---- events and agents ------------------------------------------------------
    def add_event(self, event, note=True):
        if note:
            self.audit("event_add", event)
        return self._call("POST", f"/run/event/{self.server}", {"name": event, "date": self._odat()})

    def delete_event(self, event):
        self.audit("event_delete", event)
        return self._call("DELETE", f"/run/event/{self.server}/{urllib.parse.quote(event)}/{self._odat()}")

    def events(self, name=None):
        return self._call("GET", "/run/events", query={"server": self.server, "name": name or "*"})

    def _odat(self):
        import datetime
        return datetime.date.today().strftime("%m%d")

    def agents(self):
        return self._call("GET", f"/config/server/{self.server}/agents").get("agents", [])

    def ping(self, agent):
        return self._call("POST", f"/config/server/{self.server}/agent/{agent}/ping", {"discover": False, "timeout": 20})

    def reset(self):
        """Remove the folders this lab deployed and the jobs it ordered; the Control-M server itself is left alone."""
        for row in self.status().get("statuses", []):
            try:
                self._call("POST", f"/run/job/{row['jobId']}/delete")
            except CtmError:
                pass
        for folder in list(self.state["folders"]):
            try:
                self.delete_folder(folder)
            except CtmError:
                pass
        self.state = {"folders": {}, "active": {}, "seq": 0, "boards": [], "log": []}
        self._save()
        return 0
