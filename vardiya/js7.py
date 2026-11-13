"""JS7 JobScheduler client: the external-validity scheduler.

Thin wrapper over the JOC Cockpit REST API (login, then POST with X-Access-Token).
Only the standard library is used. The emulator stays the core engine; this exists
to show that results carry over to a real scheduler.
"""
import base64
import json
import os
import pathlib
import urllib.error
import urllib.request

LAB = pathlib.Path(__file__).resolve().parent.parent / "lab" / "js7" / "lab.json"


def lab_config(path=LAB):
    cfg = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    for key, env in (("url", "JS7_URL"), ("account", "JS7_ACCOUNT"), ("password", "JS7_PASSWORD")):
        cfg[key] = os.environ.get(env, cfg[key])
    return cfg


class JS7Error(RuntimeError):
    def __init__(self, status, body):
        super().__init__(f"JS7 {status}: {str(body)[:500]}")
        self.status, self.body = status, body


class JS7:
    def __init__(self, url, account, password, timeout=60):
        self.api, self.timeout, self.token = url.rstrip("/") + "/joc/api", timeout, None
        self._basic = base64.b64encode(f"{account}:{password}".encode()).decode()

    def _request(self, path, body, headers):
        data = json.dumps(body or {}).encode()
        req = urllib.request.Request(self.api + path, data, {"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read()
                return r.headers, (json.loads(raw) if raw else {})
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                raw = json.loads(raw)
            except ValueError:
                pass
            raise JS7Error(e.code, raw) from None

    def login(self):
        headers, body = self._request("/authentication/login", None, {"Authorization": "Basic " + self._basic})
        self.token = headers.get("X-Access-Token") or body.get("accessToken")
        return body

    def post(self, path, body=None):
        if self.token is None:
            self.login()
        return self._request(path, body, {"X-Access-Token": self.token})[1]

    def logout(self):
        if self.token:
            try:
                self.post("/authentication/logout")
            finally:
                self.token = None

    # ---- inventory --------------------------------------------------------------
    def store(self, path, object_type, configuration, ticket=None, comment=None):
        """Save a draft. JS7 records who did it; the request number goes into its audit log."""
        return self.post("/inventory/store", {"path": path, "objectType": object_type, "configuration": configuration,
                                              "auditLog": _audit(ticket, comment)})

    def read(self, path, object_type):
        return self.post("/inventory/read/configuration", {"path": path, "objectType": object_type})

    def deploy(self, controller_id, path, object_type, ticket=None, comment=None):
        item = {"configuration": {"path": path, "objectType": object_type}}
        return self.post("/inventory/deployment/deploy", {
            "controllerIds": [controller_id], "store": {"draftConfigurations": [item]},
            "auditLog": _audit(ticket, comment)})


def _audit(ticket, comment):
    out = {"comment": (comment or "vardiya")[:255]}
    if ticket:
        out["ticketLink"] = str(ticket)[:255]
    return out
