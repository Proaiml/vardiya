"""The collector of the early-warning arm: reads the live site the way an admin does and writes one telemetry snapshot.

What it reads, and how:
    scheduler    job definitions (`deploy jobs::get`), the status of every job and the history of every run: start,
                 end, duration, result and the job output of that run (`run job:output::get`)
    hosts        `df` on both agents and the partner server, the files in the monitored volumes
    database     the validity dates and connection limits of the roles, the open sessions and the locks they hold
    keys         age, owner and permissions of the key files on the agents; the expiry options in the partner's
                 authorized_keys files
    profiles     the connection profiles and a login test of each (`deploy connectionprofile::test`)
    agents       the state of each agent

The snapshot is plain JSON, so it can be stored, replayed and used as a test fixture. `grafa_isle` turns it into the
project's local graph (vardiya/graph.py) the way vardiya/gecmis.py builds it for the generated site, so the existing
warning code (vardiya/cozumle.py) and graph model (vardiya/gnn.py) can work on live data.
"""
import datetime
import json
import re
import time

from ..graph import Graph, signature

ISLEM = {"Job:Command", "Job:Script", "Job:FileTransfer", "Job:Database:SQLScript", "Job:Database:EmbeddedQuery",
         "Job:Database:StoredProcedure", "Job:FileWatcher:Create", "Job:Dummy"}
DF_SATIRI = re.compile(r"^df: (\S+) kullanilan_kb=(\d+) toplam_kb=(\d+)", re.M)
SAYAC = re.compile(r"^([a-z_]+): (\d+)\b", re.M)
TABLO = re.compile(r"\b(?:from|into|update|join|truncate(?:\s+table)?|lock\s+table|table)\s+([a-z_][a-z0-9_]*)", re.I)
IZLENEN = ("/data", "/srv")


def _t(text):
    """ISO time of the scheduler's history -> epoch seconds."""
    if not text:
        return None
    return datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00")).timestamp()


def _cikis(cikti):
    m = re.search(r"returnCode=(\d+)", cikti)
    return int(m.group(1)) if m else None


def _hata(cikti):
    err = [ln[len("[STDERR] "):] for ln in cikti.splitlines() if ln.startswith("[STDERR] ")]
    return err[-1].strip() if err else None


def kosular(ctm, jid, a, kuyruk=40):
    """Every run of one job with its duration, result, error line and the metrics its output prints."""
    out = []
    for i, t in enumerate(ctm._tasks(a), 1):
        bas, bit = _t(t.get("startTime")), _t(t.get("endTime"))
        try:
            cikti = ctm.output(jid, run_no=i, tail=kuyruk)
        except Exception as e:  # noqa: BLE001
            cikti = f"(cikti okunamadi: {e})"
        ok = t.get("state", {}).get("_text") == "SUCCESSFUL"
        out.append({"no": i, "bas": bas, "bit": bit, "sn": round(bit - bas, 2) if bas and bit else None, "ok": ok,
                    "cikis": _cikis(cikti), "hata": None if ok else (_hata(cikti) or "bilinmeyen hata"),
                    "df": [{"mount": m, "kullanilan_kb": int(u), "toplam_kb": int(tt)} for m, u, tt in DF_SATIRI.findall(cikti)],
                    "sayac": {k: int(v) for k, v in SAYAC.findall(cikti)}})
    return out


def _oku(lab, host, yol):
    rc, out = lab.sh(host, f"cat {yol} 2>/dev/null | head -c 6000")
    return out if rc == 0 else None


def tanim_bilgisi(lab, folder, ad, fdef):
    """What a definition says, plus the script or SQL file it points to."""
    d = fdef[ad]
    host = d.get("Host") or fdef.get("Host")
    komut = d.get("Command") or ""
    metin = None
    yol = None
    if d.get("Type") == "Job:Script":
        yol = f"{d.get('FilePath', '').rstrip('/')}/{d.get('FileName', '')}"
    elif d.get("Type") == "Job:Command":
        m = re.search(r"(/\S+\.sh)\b", komut)
        yol = m.group(1) if m else None
    elif d.get("Type") == "Job:Database:SQLScript":
        yol = d.get("SQLScript")
    if yol:
        metin = _oku(lab, host, yol)
    sql = d.get("Query") or (metin if d.get("Type") == "Job:Database:SQLScript" else "") or ""
    profiller = [v for k, v in d.items() if k in ("ConnectionProfile", "ConnectionProfileSrc", "ConnectionProfileDest") and v]
    tm = re.search(r"\btimeout\s+(\d+)\b", komut)
    lm = re.search(r"^LIMIT=(\d+)", metin or "", re.M)
    when = d.get("When") or {}
    return {"host": host, "calisan": d.get("RunAs") or fdef.get("RunAs"), "tip": d["Type"], "komut": komut, "betik_yolu": yol,
            "betik_metni": metin, "sql": sql, "tablolar": sorted({t.lower() for t in TABLO.findall(sql)}), "profiller": profiller,
            "timeout": int(tm.group(1)) if tm else None, "limit": int(lm.group(1)) if lm else None,
            "planli": (when.get("FromTime") or None), "aciklama": d.get("Description"),
            "hedef_dizinler": sorted(set(re.findall(r"(/data/[a-z]+(?:/[A-Za-z0-9_]+)?)", (metin or "") + " " + komut)))}


def diskler(lab):
    out = {}
    for h in ("ajan1", "ajan2", "dosya-sunucu"):
        if h != "dosya-sunucu" and not lab.running(h):
            continue
        rc, text = lab.sh(h, "df -Pk")
        rows = []
        for ln in text.splitlines()[1:]:
            f = ln.split()
            if len(f) >= 6 and f[1].isdigit() and (f[5] == "/" or f[5].startswith(IZLENEN)):
                rows.append({"mount": f[5], "toplam_kb": int(f[1]), "kullanilan_kb": int(f[2]), "yuzde": int(f[4].rstrip("%") or 0)})
        out[h] = rows
    return out


def dizin_icerigi(lab, dis):
    """The files in every monitored non-root volume: name, size, age."""
    out = {}
    for h, rows in dis.items():
        for r in rows:
            if r["mount"] == "/":
                continue
            rc, text = lab.sh(h, f"ls -lA --time-style=+%s {r['mount']} 2>/dev/null | tail -n +2 | head -40")
            files = []
            for ln in text.splitlines():
                f = ln.split(None, 6)
                if len(f) >= 7 and f[4].isdigit():
                    files.append({"ad": f[6], "kb": round(int(f[4]) / 1024, 1), "sahip": f[2],
                                  "yas_sn": max(0, int(time.time()) - int(f[5])) if f[5].isdigit() else None})
            out[f"{h}:{r['mount']}"] = files
    return out


def roller(lab):
    rows = lab.sql("select rolname, rolvaliduntil::text, rolconnlimit from pg_roles where rolcanlogin and rolname not in ('postgres')")
    out = []
    for ad, until, lim in rows:
        t = None
        if until and until not in ("infinity",):
            t = datetime.datetime.fromisoformat(until.replace("+00", "+00:00") if re.search(r"[+-]\d\d$", until) else until).timestamp()
        out.append({"rol": ad, "gecerlilik": t, "gecerlilik_metni": until or "infinity", "baglanti_siniri": int(lim)})
    return out


def oturumlar(lab):
    ses = []
    for pid, kul, durum, sn, bekle, sorgu in lab.sql(
            "select pid, usename, state, coalesce(extract(epoch from now() - xact_start)::int, 0), coalesce(wait_event_type, ''), "
            "left(replace(query, E'\\n', ' '), 70) from pg_stat_activity where datname = 'uygulama' and pid <> pg_backend_pid() "
            "and usename is not null"):
        ses.append({"pid": int(pid), "kullanici": kul, "durum": durum, "xact_sn": int(sn), "bekliyor": bekle == "Lock", "sorgu": sorgu})
    kil = [{"pid": int(p), "tablo": t, "kip": m, "verildi": g == "t"} for p, t, m, g in lab.sql(
        "select l.pid, c.relname, l.mode, l.granted from pg_locks l join pg_class c on c.oid = l.relation "
        "where c.relkind = 'r' and c.relnamespace = 'public'::regnamespace")]
    return ses, kil


def anahtarlar(lab):
    dosyalar = []
    for h in ("ajan1", "ajan2"):
        if not lab.running(h):
            continue
        rc, out = lab.sh(h, "stat -c '%n %a %U %Y' /opt/ctm/keys/* 2>/dev/null")
        for ln in out.splitlines():
            f = ln.split()
            if len(f) == 4:
                dosyalar.append({"ajan": h, "dosya": f[0], "mod": f[1], "sahip": f[2], "yas_gun": round((time.time() - int(f[3])) / 86400, 1)})
    yetkili = []
    rc, out = lab.sh("dosya-sunucu", "for f in /home/*/.ssh/authorized_keys; do u=${f#/home/}; u=${u%%/*}; "
                                     "while read -r l; do echo \"$u|$l\"; done < $f; done")
    for ln in out.splitlines():
        hesap, _, satir = ln.partition("|")
        m = re.search(r'expiry-time="(\d{8})(\d{4,6})?Z?"', satir)
        bitis = None
        if m:
            s = m.group(1) + (m.group(2) or "0000").ljust(6, "0")
            bitis = datetime.datetime.strptime(s, "%Y%m%d%H%M%S").replace(tzinfo=datetime.timezone.utc).timestamp()
        if "ssh-" in satir:
            yetkili.append({"hesap": hesap, "bitis": bitis})
    return dosyalar, yetkili


def topla(lab, ctm, profil_testi=True, kuyruk=40):
    """One snapshot of the whole site."""
    t0 = time.time()
    st = {r["jobId"]: r for r in ctm.status()["statuses"]}
    isler = []
    for jid, a in sorted(ctm.state["active"].items()):
        if a.get("deleted") or jid not in st:
            continue
        fdef = ctm.state["folders"].get(a["folder"], {})
        if a["name"] not in fdef:
            continue
        row = {"id": f"{a['folder']}/{a['name']}", "jobId": jid, "folder": a["folder"], "ad": a["name"], "durum": st[jid]["status"],
               "kosu_sayisi": st[jid]["numberOfRuns"]}
        row.update(tanim_bilgisi(lab, a["folder"], a["name"], fdef))
        row["kosular"] = kosular(ctm, jid, a, kuyruk)
        isler.append(row)
    dis = diskler(lab)
    prof = {}
    for ad, cp in ctm.get_profiles().items():
        e = {"tip": cp.get("Type", "?").split(":", 1)[-1], "kullanici": cp.get("User"), "anahtar": cp.get("PrivateKeyName"),
             "sunucu": cp.get("HostName") or cp.get("Host")}
        if profil_testi:
            try:
                e["test"] = ctm.test_profile(ad)["result"]
            except Exception as ex:  # noqa: BLE001
                e["test"] = f"HATA: {str(ex)[:60]}"
        prof[ad] = e
    ses, kil = oturumlar(lab)
    dosyalar, yetkili = anahtarlar(lab)
    return {"t": time.time(), "isler": isler, "diskler": dis, "dizinler": dizin_icerigi(lab, dis), "roller": roller(lab),
            "profiller": prof, "oturumlar": ses, "kilitler": kil, "anahtar_dosyalari": dosyalar, "yetkili_anahtarlar": yetkili,
            "ajanlar": lab.agent_states(), "toplama_sn": round(time.time() - t0, 1)}


def durum_izi(snap):
    """A comparable fingerprint of a snapshot: the things a read-only arm must not change."""
    return {"isler": {j["id"]: [j["durum"], j["kosu_sayisi"]] for j in snap["isler"]},
            "roller": {r["rol"]: r["gecerlilik_metni"] for r in snap["roller"]},
            "anahtar": sorted((a["hesap"], a["bitis"]) for a in snap["yetkili_anahtarlar"]),
            "oturum": sorted((s["kullanici"], s["durum"]) for s in snap["oturumlar"]),
            "disk": {f"{h}:{r['mount']}": r["kullanilan_kb"] for h, rows in snap["diskler"].items() for r in rows
                     if r["mount"].startswith("/data/dar")}}


# ---------------------------------------------------------------------------------------------------- the graph
def gun(snap, k, n):
    """The virtual day of run k of n: every run of the lab stands for one cycle of a daily batch, the last one is today."""
    today = datetime.date.fromtimestamp(snap["t"])
    return (today - datetime.timedelta(days=n - k)).isoformat()


def grafa_isle(snap):
    """The snapshot as the project's graph: jobs with their host, user, connection and tables; every run with its
    duration and error signature; hosts with the series of their monitored volume; roles as `resource` nodes."""
    g = Graph()
    today = datetime.date.fromtimestamp(snap["t"]).isoformat()
    jobs = []
    for j in snap["isler"]:
        jobs.append({"name": j["id"], "folder": j["folder"], "type": j["tip"].split(":", 1)[1], "host": j["host"] or "?",
                     "run_as": j["calisan"] or "jobscheduler", "connection": (j["profiller"] or [None])[0], "tables": j["tablolar"],
                     "resources": [], "deps": [], "time": j["planli"], "command": j["komut"] or j.get("betik_yolu")})
    conns = {n: {"desc": f"{p['tip']} {p.get('kullanici') or ''}@{p.get('sunucu') or ''}".strip()} for n, p in snap["profiller"].items()}
    g.add_site(jobs, conns)
    for j in snap["isler"]:
        n = len(j["kosular"])
        for k, r in enumerate(j["kosular"], 1):
            g.add_run(j["id"], gun(snap, k, n), r["ok"], (r["sn"] or 0) / 60.0, error=r["hata"], rc=r["cikis"] or (0 if r["ok"] else 1))
        for pf in j["profiller"]:
            p = snap["profiller"].get(pf) or {}
            for rol in snap["roller"]:
                if p.get("kullanici") == rol["rol"]:
                    g.edge(f"job:{j['id']}", "uses", g.node("resource", f"rol:{rol['rol']}", gecerlilik=rol["gecerlilik"]))
    # a host's disk series: the monitored volume that a job of that host writes to, run by run
    for h, rows in snap["diskler"].items():
        seri = {}
        for j in snap["isler"]:
            if j["host"] != h:
                continue
            n = len(j["kosular"])
            for k, r in enumerate(j["kosular"], 1):
                for d in r["df"]:
                    seri.setdefault(d["mount"], {})[gun(snap, k, n)] = round(100.0 * d["kullanilan_kb"] / d["toplam_kb"], 1)
        izlenen = [r for r in rows if r["mount"] in seri]
        if izlenen:
            m = izlenen[0]["mount"]
            pts = sorted(seri[m].items())
            g.node("host", h, disk=[[d, v] for d, v in pts], izlenen=m)
        else:
            g.node("host", h, disk=[])
    g.commit()
    return g, today
