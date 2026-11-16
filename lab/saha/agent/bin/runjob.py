#!/usr/bin/env python3
"""Runs one Control-M style job for real on this agent host.

The scheduler passes the job, already resolved at order time, in CTM_SPEC (base64 JSON). Nothing here is
simulated: commands run under the RunAs account, file transfers go through sftp to the other machine, database
jobs go through psql. The exit code and the output are what the scheduler records.

Job types: Job:Command, Job:Script, Job:FileTransfer, Job:Database:EmbeddedQuery, Job:Database:SQLScript,
Job:Database:StoredProcedure, Job:FileWatcher:Create, Job:Dummy.
"""
import base64
import fnmatch
import json
import os
import shlex
import subprocess
import sys
import time

CP_DIR, KEY_DIR, KNOWN = "/opt/ctm/cp", "/opt/ctm/keys", "/opt/ctm/cp/known_hosts"
AGENT_USER = "jobscheduler"


def say(msg):
    print(msg, flush=True)


def die(code, msg):
    print(msg, file=sys.stderr, flush=True)
    sys.exit(code)


def as_user(user, command, stdin=None, env=None):
    """Run a shell command under `user` (sudo unless it is the agent's own account). Output goes to the job log."""
    return subprocess.run(_argv(user, command), input=stdin, text=True, env={**os.environ, **(env or {})}).returncode


def capture(user, command):
    r = subprocess.run(_argv(user, command), capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def profile(name, family):
    path = os.path.join(CP_DIR, f"{name}.json")
    if not name:
        die(40, f"CTM5311 baglanti profili adi bos ({family})")
    if not os.path.exists(path):
        die(40, f"CTM5312 baglanti profili bulunamadi: {name} (ajan: {os.uname().nodename})")
    try:
        cp = json.load(open(path, encoding="utf-8"))
    except ValueError:
        die(40, f"CTM5313 baglanti profili okunamiyor: {name}")
    if family not in cp.get("Type", ""):
        die(40, f"CTM5314 baglanti profili '{name}' tipi {cp.get('Type')}; bu is {family} profili ister")
    return cp


# ---------------------------------------------------------------- file transfer
class End:
    """One side of a transfer: the local file system (under the profile's user) or an SFTP account."""
    def __init__(self, cp, name):
        self.cp, self.name = cp, name
        self.local = cp["Type"].endswith(":Local")
        self.user = cp.get("User", "")

    def _sftp(self, batch):
        cp = self.cp
        opts = ["-o", "StrictHostKeyChecking=accept-new", "-o", f"UserKnownHostsFile={KNOWN}", "-o", "ConnectTimeout=10",
                "-o", "NumberOfPasswordPrompts=1", "-P", str(cp.get("Port", 22))]
        tail = ["-b", "-"]        # -b turns batch mode on; ssh keeps the first value, so auth options must come before it
        argv, env = ["sftp"], dict(os.environ)
        if cp.get("PrivateKeyName"):
            key = os.path.join(KEY_DIR, cp["PrivateKeyName"])
            if not os.path.exists(key):
                return 255, "", f"private key '{cp['PrivateKeyName']}' bu ajanda yok ({KEY_DIR})"
            opts += ["-i", key, "-o", "IdentitiesOnly=yes", "-o", "PasswordAuthentication=no", "-o", "BatchMode=yes"]
        else:
            env["SSHPASS"] = str(cp.get("Password", ""))
            argv = ["sshpass", "-e", "sftp"]
            opts += ["-o", "PubkeyAuthentication=no", "-o", "PreferredAuthentications=password", "-o", "BatchMode=no"]
        r = subprocess.run(argv + opts + tail + [f"{self.user}@{cp.get('HostName', '')}"], input=batch, capture_output=True,
                           text=True, env=env)
        return r.returncode, r.stdout, r.stderr

    def listing(self, pattern):
        """[(name, size)] of regular files matching a path whose last part may hold wildcards."""
        d, base = os.path.dirname(pattern) or ".", os.path.basename(pattern)
        if self.local:
            rc, out, err = capture(self.user, f"cd {shlex.quote(d)} && for f in *; do [ -f \"$f\" ] && stat -c '%s %n' \"$f\"; done; true")
            if rc:
                return None, err.strip() or f"dizin okunamadi: {d}"
            rows = [ln.split(" ", 1) for ln in out.splitlines() if " " in ln]
            return [(n, int(s)) for s, n in rows if fnmatch.fnmatchcase(n, base)], None
        rc, out, err = self._sftp(f"ls -ln {d}\n")
        if rc:
            return None, (err.strip().splitlines() or ["sftp hatasi"])[-1]
        rows = []
        for ln in out.splitlines():
            p = ln.split(None, 8)
            if len(p) == 9 and p[0].startswith("-") and p[4].isdigit():
                n = os.path.basename(p[8])
                if fnmatch.fnmatchcase(n, base):
                    rows.append((n, int(p[4])))
        return rows, None

    def run(self, action, a, b=None):
        if self.local:
            cmd = {"rm": f"rm -f {shlex.quote(a)}", "mv": f"mv {shlex.quote(a)} {shlex.quote(b or '')}"}[action]
            rc, _, err = capture(self.user, cmd)
            return rc, err.strip()
        rc, _, err = self._sftp({"rm": f"rm {a}\n", "mv": f"rename {a} {b}\n"}[action])
        return rc, (err.strip().splitlines() or [""])[-1]


def _argv(user, command):
    return ["sh", "-c", command] if user in ("", None, AGENT_USER) else ["sudo", "-n", "-H", "-u", user, "sh", "-c", command]


def copy(src, sname, dst, dpath, ascii_mode):
    """Copy one file from `src` to `dst` through this host. Returns (rc, message).
    The file is staged under /data/tmp: read with the source side's rights, written with the destination's."""
    tmp = f"/data/tmp/aft.{os.getpid()}.{os.path.basename(sname)}"
    try:
        if src.local:
            r = subprocess.run(_argv(src.user, f"cat {shlex.quote(sname)}"), capture_output=True)
            if r.returncode:
                return r.returncode, "kaynak okunamadi: " + r.stderr.decode("utf-8", "replace").strip()
            data = r.stdout
        else:
            rc, _, err = src._sftp(f"get {sname} {tmp}\n")
            if rc:
                return rc, "kaynaktan okunamadi: " + (err.strip().splitlines() or ["?"])[-1]
            data = open(tmp, "rb").read()
        if ascii_mode:
            data = data.replace(b"\r\n", b"\n")
        if dst.local:
            w = subprocess.run(_argv(dst.user, f"cat > {shlex.quote(dpath)}"), input=data, capture_output=True)
            return w.returncode, ("hedefe yazilamadi: " + w.stderr.decode("utf-8", "replace").strip()) if w.returncode else ""
        with open(tmp, "wb") as f:
            f.write(data)
        rc, _, err = dst._sftp(f"put {tmp} {dpath}\n")
        return rc, ("hedefe yazilamadi: " + (err.strip().splitlines() or ["?"])[-1]) if rc else ""
    except OSError as e:
        return 1, f"ara dosya yazilamadi: {e}"
    finally:
        subprocess.run(["rm", "-f", tmp])


def file_transfer(spec):
    a = End(profile(spec.get("ConnectionProfileSrc"), "FileTransfer"), spec.get("ConnectionProfileSrc"))
    b = End(profile(spec.get("ConnectionProfileDest"), "FileTransfer"), spec.get("ConnectionProfileDest"))
    transfers = spec.get("FileTransfers") or []
    if not transfers:
        die(41, "CTM5320 FileTransfers bos")
    total = 0
    for i, t in enumerate(transfers, 1):
        reverse = t.get("TransferOption", "SrcToDest") == "DestToSrc"
        src, dst = (b, a) if reverse else (a, b)
        spath, dpath = (t.get("Dest"), t.get("Src")) if reverse else (t.get("Src"), t.get("Dest"))
        say(f"[aktarim {i}] {src.name}:{spath} -> {dst.name}:{dpath} ({t.get('TransferType', 'Binary')})")
        files, err = src.listing(spath)
        if files is None:
            die(42, f"CTM5321 kaynak listelenemedi ({src.name}): {err}")
        if not files:
            if str(t.get("FailJobOnSourceMissing", "1")) == "0":
                say("  kaynakta eslesen dosya yok; ayar geregi hata sayilmadi")
                continue
            die(43, f"CTM5322 kaynakta eslesen dosya yok: {spath}")
        many = any(c in os.path.basename(spath) for c in "*?[")
        existing, err = dst.listing(os.path.join(dpath, "*") if many or dpath.endswith("/") else dpath)
        if existing is None:
            die(44, f"CTM5323 hedef dizin okunamadi ({dst.name}): {err}")
        have = {n for n, _ in existing}
        for name, size in sorted(files):
            sfile = os.path.join(os.path.dirname(spath), name)
            dfile = os.path.join(dpath, name) if many or dpath.endswith("/") else dpath
            dname = os.path.basename(dfile)
            mode = str(t.get("IF_EXIST", "0"))
            if dname in have and mode == "2":
                die(45, f"CTM5324 hedefte dosya zaten var, IF_EXIST=2 (durdur): {dfile}")
            if dname in have and mode == "3":
                say(f"  atlandi (hedefte var): {dname}")
                continue
            target = dfile + ".tmp" if str(t.get("DSTOPT", "0")) == "1" else dfile
            rc, msg = copy(src, sfile, dst, target, t.get("TransferType") == "Ascii")
            if rc:
                die(46, f"CTM5325 aktarim basarisiz: {name}: {msg}")
            if target != dfile:
                rc, msg = dst.run("mv", target, dfile)
                if rc:
                    die(46, f"CTM5326 gecici ad son ada cevrilemedi: {dfile}: {msg}")
            got, _ = dst.listing(dfile)
            got = dict(got or []).get(dname)
            if t.get("TransferType") != "Ascii" and got != size:
                die(47, f"CTM5327 boyut dogrulamasi tutmadi: {name} kaynak={size} hedef={got}")
            say(f"  tamam: {name} {size} bayt")
            total += 1
            opt = str(t.get("SRCOPT", "0"))
            if opt == "1":
                rc, msg = src.run("rm", sfile)
            elif opt in ("2", "3"):
                new = t.get("SRCNAME") or (sfile + ".gonderildi")
                new = os.path.join(new, name) if opt == "3" else (new if "/" in new else os.path.join(os.path.dirname(sfile), new))
                rc, msg = src.run("mv", sfile, new)
            else:
                rc, msg = 0, ""
            if rc:
                die(48, f"CTM5328 aktarim tamam ama kaynak islemi (SRCOPT={opt}) basarisiz: {msg}")
    say(f"aktarilan dosya: {total}")
    return 0


# ---------------------------------------------------------------- database
def database(spec):
    cp = profile(spec.get("ConnectionProfile"), "Database")
    env = {"PGPASSWORD": str(cp.get("Password", "")), "PGCONNECT_TIMEOUT": "8"}
    base = ["psql", "-h", str(cp.get("Host", "")), "-p", str(cp.get("Port", 5432)), "-U", str(cp.get("User", "")),
            "-d", str(cp.get("DatabaseName", "")), "-v", "ON_ERROR_STOP=1", "-X", "--no-psqlrc"]
    if str(spec.get("Autocommit", "N")).upper().startswith("N"):
        base.append("--single-transaction")
    if str(spec.get("SQLOutputFormat", "")).upper() == "CSV":
        base.append("--csv")
    for p in spec.get("Parameters") or []:
        for k, v in p.items():
            base += ["-v", f"{k}={v}"]
    kind = spec["type"].rsplit(":", 1)[1]
    if kind == "EmbeddedQuery":
        base += ["-c", spec.get("Query", "")]
    elif kind == "SQLScript":
        path = spec.get("SQLScript", "")
        if not os.path.exists(path):
            die(50, f"CTM5340 SQL betigi bulunamadi: {path} (ajan: {os.uname().nodename})")
        base += ["-f", path]
    elif kind == "StoredProcedure":
        args = ", ".join("'" + str(v).replace("'", "''") + "'" for p in spec.get("Parameters") or [] for v in p.values())
        base += ["-c", f"CALL {spec.get('Schema', 'public')}.{spec.get('StoredProcedure', '')}({args})"]
    else:
        die(51, f"CTM5341 bilinmeyen veritabani is tipi: {spec['type']}")
    say(f"[veritabani] {cp.get('User')}@{cp.get('Host')}:{cp.get('Port', 5432)}/{cp.get('DatabaseName')} profil={spec.get('ConnectionProfile')}")
    return subprocess.run(base, env={**os.environ, **env}).returncode


# ---------------------------------------------------------------- others
def file_watcher(spec):
    path, limit = spec.get("Path", ""), int(spec.get("TimeLimit", 1) or 1) * 60
    every, minsize = int(spec.get("SearchInterval", 5) or 5), int(spec.get("MinDetectedSize", 0) or 0)
    limit = int(spec.get("TimeLimitSeconds", limit))
    start = time.time()
    while True:
        if os.path.exists(path) and os.path.getsize(path) >= minsize:
            say(f"dosya bulundu: {path} {os.path.getsize(path)} bayt")
            return 0
        if time.time() - start >= limit:
            die(60, f"CTM5350 dosya {limit} saniyede gelmedi: {path}")
        time.sleep(every)


def browse(name, pattern):
    """`runjob.py ls PROFILE PATH`: list files on a file transfer profile's side (what the job itself would see)."""
    end = End(profile(name, "FileTransfer"), name)
    files, err = end.listing(pattern if any(c in os.path.basename(pattern) for c in "*?[") else os.path.join(pattern, "*"))
    if files is None:
        die(2, f"listelenemedi ({name}): {err}")
    for n, size in sorted(files):
        say(f"{size:>10} {n}")
    say(f"toplam {len(files)} dosya")


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "ls":
        browse(sys.argv[2], sys.argv[3])
        return
    try:
        spec = json.loads(base64.b64decode(os.environ.get("CTM_SPEC", "")))
    except ValueError:
        die(120, "CTM5300 is tanimi okunamadi")
    kind, runas = spec.get("type", ""), spec.get("RunAs", "")
    say(f"== ajan={os.uname().nodename} klasor={spec.get('folder')} is={spec.get('name')} tip={kind} RunAs={runas} "
        f"ODATE={spec.get('odate')} kosu={spec.get('run')} ==")
    env = {f"CTM_{k}": str(v) for k, v in (spec.get("vars") or {}).items()}
    if kind == "Job:Command":
        rc = as_user(runas, spec.get("Command", ""), env=env)
    elif kind == "Job:Script":
        path = os.path.join(spec.get("FilePath", ""), spec.get("FileName", ""))
        rc = as_user(runas, " ".join([shlex.quote(path)] + [shlex.quote(str(x)) for x in spec.get("Arguments") or []]), env=env)
    elif kind == "Job:FileTransfer":
        rc = file_transfer(spec)
    elif kind.startswith("Job:Database:"):
        rc = database(spec)
    elif kind == "Job:FileWatcher:Create":
        rc = file_watcher(spec)
    elif kind == "Job:Dummy":
        rc = 0
    else:
        die(121, f"CTM5301 desteklenmeyen is tipi: {kind}")
    say(f"== bitis kodu {rc} ==")
    sys.exit(rc)


if __name__ == "__main__":
    main()
