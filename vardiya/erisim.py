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
# arguments with their own shape; everything else must match SAFE_ARG (no spaces, quotes, ; | & $ ` or braces)
ARG_PATTERNS = {
    "pid": re.compile(r"^[0-9]{1,10}$"),
    "port": re.compile(r"^[0-9]{1,5}$"),
    "path": re.compile(r"^[A-Za-z0-9_.:/@%+=\\-]{1,200}$"),  # Windows paths carry backslashes
    "key": re.compile(r"^HK(LM|CU):\\[A-Za-z0-9_.\\-]{1,200}$"),
    "log": re.compile(r"^(System|Application|Security)$"),
    "start_type": re.compile(r"^(Automatic|Manual|Disabled)$"),
    "owner": re.compile(r"^[A-Za-z0-9_.-]{1,64}(:[A-Za-z0-9_.-]{1,64})?$"),
}

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

# General server skills (skills/genel-yetenekler): product-independent reads, and a few writes with their own level.
GENERAL = {
    "proc_list": {"unix": "ps -eo pid,ppid,user,stat,etime,pcpu,pmem,cmd --sort=-pcpu | head -25",
                  "windows": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 25 Id,ProcessName,CPU,WS"},
    "proc_info": {"unix": "ps -o pid,ppid,user,stat,etime,cmd -p {pid}; cat /proc/{pid}/limits",
                  "windows": "Get-CimInstance Win32_Process | Where-Object ProcessId -eq {pid} | "
                             "Select-Object ProcessId,ParentProcessId,CommandLine,CreationDate"},
    "port_owner": {"unix": "ss -ltnp | grep ':{port} '",
                   "windows": "Get-NetTCPConnection -LocalPort {port} | Select-Object LocalAddress,State,OwningProcess"},
    "net_test": {"unix": "nc -vz -w 5 {target} {port}", "windows": "Test-NetConnection {target} -Port {port}"},
    "dns_lookup": {"unix": "getent hosts {name}; hostname -f", "windows": "Resolve-DnsName {name}; hostname"},
    "cert_remote": {"unix": "openssl s_client -connect {target}:{port} -servername {target} </dev/null 2>/dev/null"
                            " | openssl x509 -noout -subject -issuer -enddate"},
    "registry_read": {"windows": "Get-ItemProperty -Path '{key}'"},
    "event_log": {"windows": "Get-WinEvent -LogName {log} -MaxEvents 200 | Where-Object LevelDisplayName -in "
                             "'Error','Warning' | Select-Object -First 50 TimeCreated,ProviderName,Id,Message"},
    "service_config": {"unix": "systemctl show {service} -p ExecStart,User,LimitNOFILE,ActiveState,UnitFileState",
                       "windows": "Get-CimInstance Win32_Service | Where-Object Name -eq '{service}' | "
                                  "Select-Object Name,State,StartMode,StartName,PathName"},
    "file_acl": {"unix": "namei -l {path}; getfacl -p {path}", "windows": "icacls '{path}'"},
    "time_status": {"unix": "timedatectl; chronyc tracking", "windows": "w32tm /query /status; tzutil /g"},
    "user_status": {"unix": "chage -l {user}; id {user}",
                    "windows": "Get-LocalUser -Name {user} | Select-Object Name,Enabled,PasswordExpires,PasswordLastSet"},
    "user_rights": {"windows": "secedit /export /cfg $env:TEMP\\vardiya-ur.inf /areas USER_RIGHTS | Out-Null; "
                               "Select-String -Path $env:TEMP\\vardiya-ur.inf -Pattern "
                               "'SeBatchLogonRight|SeServiceLogonRight|SeAssignPrimaryTokenPrivilege'"},
    "disk_top": {"unix": "du -xh --max-depth=1 {path} 2>/dev/null | sort -h | tail -15",
                 "windows": "Get-ChildItem -Path '{path}' -Recurse -File -ErrorAction SilentlyContinue | "
                            "Sort-Object Length -Descending | Select-Object -First 15 FullName,Length,LastWriteTime"},
    "oom_log": {"unix": "dmesg -T | grep -i -E 'killed process|out of memory' | tail -20"},
    "mounts": {"unix": "mount | grep -E 'nfs|cifs'; df -h", "windows": "Get-SmbMapping; Get-PSDrive -PSProvider FileSystem"},
    "sched_tasks": {"unix": "crontab -l -u {user}; systemctl list-timers --all --no-pager",
                    "windows": "Get-ScheduledTask | Where-Object State -ne 'Disabled' | Select-Object TaskPath,TaskName,State"},
    "recent_changes": {"unix": "rpm -qa --last 2>/dev/null | head -20 || tail -50 /var/log/dpkg.log",
                       "windows": "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 15"},
    # writes
    "process_term": {"unix": "kill -TERM {pid}", "windows": "Stop-Process -Id {pid}"},
    "process_kill": {"unix": "kill -KILL {pid}", "windows": "Stop-Process -Id {pid} -Force"},
    "file_chown": {"unix": "chown {owner} -- {path}"},
    "time_resync": {"unix": "chronyc makestep", "windows": "w32tm /resync"},
    "service_start_type": {"unix": "systemctl enable {service}", "windows": "Set-Service -Name {service} -StartupType {start_type}"},
    "registry_set": {"windows": "$b = Join-Path $env:TEMP ('vardiya-' + (Get-Date -Format yyyyMMddHHmmss) + '.reg'); "
                                "reg export ('{key}' -replace ':','') $b /y | Out-Null; "
                                "Set-ItemProperty -Path '{key}' -Name {name} -Value {value}"},
}
COMMANDS.update(GENERAL)
GENERAL_WRITE = {"process_term": 3, "process_kill": 4, "file_chown": 3, "time_resync": 3, "service_start_type": 3,
                 "registry_set": 4}  # a registry write always backs the key up first, and needs a person's approval
LEVELS = {**WRITE, **GENERAL_WRITE, **{v: 0 for v in COMMANDS if v not in WRITE and v not in GENERAL_WRITE}}
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
            if not ARG_PATTERNS.get(k, SAFE_ARG).match(str(v)):
                raise Refused(f"{k}: izin verilmeyen karakter ya da uzunluk")
        if LEVELS.get(verb, 0) >= 4 and f"{verb}:{host}" not in self.approvals:
            raise Refused(f"{verb}: duzey 4, insan onayi gerekli")
        kinds = COMMANDS[verb]
        kind = "api" if "api" in kinds else "server" if "server" in kinds else self.inv[host]["os"]
        if kind not in kinds:
            raise Refused(f"{verb}: {kind} icin komut tanimli degil")
        text = re.sub(r"\{secret:(\w+)\}", lambda m: f"$(vault-get {m.group(1)})" if kind == "unix" else
                      f"(Get-Secret -Name {m.group(1)} -AsPlainText)", kinds[kind])
        try:
            line = text.format(**{"agent_user": self.inv.get(host, {}).get("agent_user", "ctmag"), "path": "/", **args})
        except KeyError as e:
            raise Refused(f"{verb}: eksik arguman {e}") from None
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
