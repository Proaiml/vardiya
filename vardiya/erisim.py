"""Remote access for the action track: the same verbs as opsworld, turned into real commands on real hosts.

    Unix hosts and the scheduler server   ssh <host> -- <allowed command>    (key auth, forced-command wrapper)
    Windows hosts                          WinRM / PowerShell Remoting (Invoke-Command) or Windows OpenSSH
    The scheduler itself                   its CLI or REST API (Control-M Automation API, ctm CLI, server utilities)

No remote desktop: RDP is a graphical protocol, not an automation interface; work that only a GUI can do is handed to
a person. Only verbs in COMMANDS can run, with arguments checked against a pattern; secrets never travel on the
command line (they are referenced by name in a vault and resolved on the host); level-4 verbs need an approval token;
every call, run or refused, is appended to the audit log. `dry_run=True` prints what would run and runs nothing.

Command syntax comes from docs/arastirma/*.json; items marked there as unverified must be checked against the product
documentation of the installed version before a site turns dry_run off.
"""
import datetime
import json
import pathlib
import re
import shlex
import subprocess

from .opsworld import WRITE

SAFE_ARG = re.compile(r"^[A-Za-z0-9_.:/@%+=-]{1,200}$")

# verb -> {os: template}. {x} are checked arguments; {secret:name} is resolved on the host from the vault.
COMMANDS = {
    "agent_status": {"unix": "ag_diag_comm", "windows": "Get-Service -Name 'ctmag*' | Format-List Name,Status"},
    "agent_restart": {"unix": "shut-ag -u {agent_user} -p all; start-ag -u {agent_user} -p all",
                      "windows": "Restart-Service -Name 'ctmag*'"},
    "service_status": {"unix": "systemctl status {service} --no-pager", "windows": "Get-Service -Name {service}"},
    "service_restart": {"unix": "systemctl restart {service}", "windows": "Restart-Service -Name {service}"},
    "host_df": {"unix": "df -h {path}", "windows": "Get-Volume | Format-Table DriveLetter,SizeRemaining,Size"},
    "host_mem": {"unix": "free -m", "windows": "Get-CimInstance Win32_OperatingSystem | Select FreePhysicalMemory"},
    "syslog": {"unix": "journalctl --since '-2h' --no-pager | grep -i {grep}",
               "windows": "Get-WinEvent -LogName System -MaxEvents 200 | Where-Object Message -match '{grep}'"},
    "list_files": {"unix": "ls -la {path}", "windows": "Get-ChildItem -Path {path}"},
    "file_delete": {"unix": "rm -- {path}", "windows": "Remove-Item -LiteralPath {path}"},
    "file_move": {"unix": "mv -- {path} {to}", "windows": "Move-Item -LiteralPath {path} -Destination {to}"},
    "job_status": {"api": "ctm run jobs:status::get -s jobname={job}"},
    "job_log": {"api": "ctm run job:log::get {job_id}"},
    "job_rerun": {"api": "ctm run job::rerun {job_id}"},
    "job_hold": {"api": "ctm run job::hold {job_id}"},
    "job_free": {"api": "ctm run job::free {job_id}"},
    "job_kill": {"api": "ctm run job::kill {job_id}"},
    "password_update": {"unix": "ctmpwd -action update -user {user} -password {secret:run_as}",
                        "windows": "ctmpwd -action update -user {user} -password {secret:run_as}"},
    "cert_info": {"unix": "openssl x509 -enddate -noout -in {path}"},
    "resource_status": {"server": "ecaqrtab LIST {resource}"},
}
LEVELS = {**WRITE, **{v: 0 for v in COMMANDS if v not in WRITE}}
NEVER = {"job_set_ok", "disable_ssl", "pool_increase"}  # verbs the harness does not run on a real site


class Refused(Exception):
    pass


class Access:
    def __init__(self, inventory, audit=pathlib.Path("results") / "erisim-denetim.jsonl", dry_run=True, approvals=()):
        """inventory: {host: {"os": "unix"|"windows", "address": "...", "user": "..."}}; approvals: tokens a person
        issued for level-4 actions, as "verb:host" strings."""
        self.inv, self.audit, self.dry_run, self.approvals = inventory, pathlib.Path(audit), dry_run, set(approvals)

    def _log(self, row):
        self.audit.parent.mkdir(parents=True, exist_ok=True)
        with self.audit.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"at": datetime.datetime.now().isoformat(timespec="seconds"), **row}, ensure_ascii=False) + "\n")

    def command(self, verb, host=None, **args):
        """The exact command line for a verb, or Refused. Nothing runs here."""
        if verb in NEVER:
            raise Refused(f"{verb}: harness bu eylemi gercek sahada calistirmaz")
        if verb not in COMMANDS:
            raise Refused(f"{verb}: izin listesinde yok")
        for k, v in args.items():
            if not SAFE_ARG.match(str(v)):
                raise Refused(f"{k}: izin verilmeyen karakter ya da uzunluk")
        if LEVELS.get(verb, 0) >= 4 and f"{verb}:{host}" not in self.approvals:
            raise Refused(f"{verb}: duzey 4, insan onayi gerekli")
        kinds = COMMANDS[verb]
        kind = "api" if "api" in kinds else "server" if "server" in kinds else self.inv[host]["os"]
        if kind not in kinds:
            raise Refused(f"{verb}: {kind} icin komut tanimli degil")
        text = re.sub(r"\{secret:(\w+)\}", lambda m: f"$(vault-get {m.group(1)})" if kind == "unix" else
                      f"(Get-Secret -Name {m.group(1)} -AsPlainText)", kinds[kind])
        line = text.format(**{"agent_user": self.inv.get(host, {}).get("agent_user", "ctmag"), "path": "/", **args})
        if kind in ("api", "server"):
            return ["ssh", self.inv.get("_server", {}).get("address", "ctm-server"), "--", line]
        h = self.inv[host]
        if kind == "unix":
            return ["ssh", f"{h.get('user', 'ctmops')}@{h['address']}", "--", line]
        return ["pwsh", "-NoProfile", "-Command",
                f"Invoke-Command -ComputerName {shlex.quote(h['address'])} -ScriptBlock {{ {line} }}"]

    def run(self, verb, host=None, timeout=120, **args):
        try:
            cmd = self.command(verb, host, **args)
        except Refused as e:
            self._log({"verb": verb, "host": host, "args": args, "refused": str(e)})
            raise
        self._log({"verb": verb, "host": host, "args": args, "command": cmd, "dry_run": self.dry_run})
        if self.dry_run:
            return {"dry_run": True, "command": cmd}
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        self._log({"verb": verb, "host": host, "exit": r.returncode, "stdout": r.stdout[-2000:], "stderr": r.stderr[-1000:]})
        return {"exit": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
