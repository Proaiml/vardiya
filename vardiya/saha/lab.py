"""The live lab ("saha"): a real scheduler, two agent hosts, a partner SFTP server and an application database,
all in Docker (lab/saha/docker-compose.yml). This module is the only place that talks to Docker.

Hosts as the admin sees them: ajan1, ajan2 (agent hosts where jobs run), dosya-sunucu (the SFTP server of the
other side), appdb (the application database server).
"""
import json
import os
import pathlib
import subprocess
import time
import urllib.error

from ..js7 import JS7, JS7Error

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
LAB = ROOT / "lab" / "saha" / "lab.json"
HOSTS = {"ajan1": "ajan1", "ajan2": "ajan2", "dosya-sunucu": "dosya", "dosya": "dosya", "appdb": "appdb"}
AGENTS = ("ajan1", "ajan2")


class Lab:
    def __init__(self, path=LAB):
        self.cfg = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        self.cfg["url"] = os.environ.get("SAHA_URL", self.cfg["url"])
        self.proje = os.environ.get("SAHA_PROJE", self.cfg["proje"])
        self.cid = self.cfg["controller_id"]
        self.js = JS7(self.cfg["url"], self.cfg["account"], self.cfg["password"])
        sonuc = pathlib.Path(os.environ["SAHA_SONUC"]) if os.environ.get("SAHA_SONUC") else ROOT / "results" / "saha"
        self.durum = sonuc / "durum" / f"{self.proje}.json"

    # ---- docker -----------------------------------------------------------------
    def container(self, host):
        if host not in HOSTS:
            raise KeyError(f"bilinmeyen sunucu '{host}'; sunucular: ajan1, ajan2, dosya-sunucu, appdb")
        return f"{self.proje}-{HOSTS[host]}-1"

    def docker(self, *args, stdin=None, timeout=120):
        env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
        r = subprocess.run(["docker", *args], input=stdin, capture_output=True, timeout=timeout, env=env)
        out = (r.stdout + r.stderr).decode("utf-8", "replace")
        return r.returncode, out

    def sh(self, host, command, user=None, timeout=60, stdin=None):
        """Run a shell command on a lab host. Returns (exit code, combined output)."""
        # Without input for the command itself, the command travels on stdin (`sh -s`): Windows argument quoting
        # would otherwise mangle quotes, dollar signs and newlines on their way to the container.
        base = ["exec", "-i"] + (["-u", user] if user else []) + [self.container(host), "sh"]
        if stdin is None:
            args, stdin = base + ["-s"], command + "\n"
        else:
            args = base + ["-c", command]
        try:
            return self.docker(*args, stdin=stdin.encode("utf-8") if isinstance(stdin, str) else stdin, timeout=timeout)
        except subprocess.TimeoutExpired:
            return 124, f"komut {timeout} saniyede bitmedi"

    def running(self, host):
        rc, out = self.docker("inspect", "-f", "{{.State.Running}} {{.State.Paused}}", self.container(host))
        return rc == 0 and out.split()[:2] == ["true", "false"]

    def power(self, host, action):
        """start | stop | pause | unpause | restart a host (a fault, or its repair by the lab itself)."""
        return self.docker(action, self.container(host), timeout=90)

    def write(self, host, path, content, owner=None, mode=None):
        cmd = f"mkdir -p \"$(dirname '{path}')\" && cat > '{path}'"
        if owner:
            cmd += f" && chown {owner} '{path}'"
        if mode:
            cmd += f" && chmod {mode} '{path}'"
        rc, out = self.sh(host, cmd, stdin=content)
        if rc:
            raise RuntimeError(f"{host}:{path} yazilamadi: {out}")

    def sql(self, query, db="uygulama"):
        """Run SQL on the application database as its administrator; rows come back as tab separated lines."""
        rc, out = self.sh("appdb", f"psql -U postgres -d {db} -X -At -F '\t' -v ON_ERROR_STOP=1", stdin=query)
        if rc:
            raise RuntimeError(f"SQL hatasi: {out.strip()[:400]}")
        return [ln.split("\t") for ln in out.splitlines() if ln and not ln.startswith(("SET", "DO"))]

    # ---- scheduler --------------------------------------------------------------
    def post(self, path, body=None, retries=1):
        """JOC REST call. A dropped session (JOC restart, token timeout) is logged in again once."""
        for attempt in range(retries + 1):
            try:
                return self.js.post(path, body)
            except JS7Error as e:
                if e.status in (401, 440) and attempt < retries:
                    self.js.token = None
                    continue
                raise
            except (urllib.error.URLError, ConnectionError, OSError):
                if attempt >= retries:
                    raise
                time.sleep(2)
                self.js.token = None

    def wait_ready(self, seconds=240):
        last = None
        for _ in range(seconds // 3):
            try:
                self.js.login()
                agents = self.post("/agents", {"controllerId": self.cid}).get("agents", [])
                if agents and all(a.get("state", {}).get("_text") == "COUPLED" for a in agents):
                    return True
                last = [(a.get("agentId"), a.get("state", {}).get("_text")) for a in agents]
            except (JS7Error, urllib.error.URLError, ConnectionError, OSError) as e:
                last = e
            time.sleep(3)
        raise RuntimeError(f"saha laboratuvari {seconds} saniyede hazir olmadi: {last}")

    def agent_states(self):
        try:
            agents = self.post("/agents", {"controllerId": self.cid}).get("agents", [])
        except JS7Error:
            return {}
        return {a["agentId"]: a.get("state", {}).get("_text", "?") for a in agents}


def kur(lab=None):
    """First-time registration of the Controller and the agents with JOC. Safe to run again."""
    lab = lab or Lab()
    js, cfg = lab.js, lab.cfg
    for _ in range(80):
        try:
            js.login()
            break
        except (JS7Error, urllib.error.URLError, ConnectionError, OSError):
            time.sleep(3)
    out = []
    for title, path, body in (
            ("denetleyici", "/controller/register", {"controllers": [{"url": cfg["controller_url"], "role": "STANDALONE",
                                                                      "title": "Saha"}]}),
            ("ajanlar", "/agents/inventory/store", {"controllerId": lab.cid, "agents": [
                {"agentId": a, "agentName": a, "url": u, "title": a} for a, u in cfg["agents"].items()]}),
            ("ajan dagitimi", "/agents/inventory/deploy", {"controllerId": lab.cid, "agentIds": list(cfg["agents"])})):
        try:
            js.post(path, {**body, "auditLog": {"comment": "saha kurulumu"}})
            out.append(f"[tamam] {title}")
        except JS7Error as e:
            out.append(f"[atlandi] {title}: {str(e)[:120]}")
        time.sleep(3)
    lab.wait_ready()
    out.append(f"[tamam] ajanlar: {lab.agent_states()}")
    return out
