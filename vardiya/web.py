"""Local web front end: the request desk and the local error graph.

    python -m vardiya web                      # http://127.0.0.1:8765
    python -m vardiya web --model ollama:qwen3:8b --site benim-ortamim.json

Standard library only. The page and its JSON API talk to one in-memory site: every request that is
applied changes the jobs that the next request sees, as at a real desk. Nothing here bypasses the
desk: a request goes through the same template parser, checks, policy kernel and audit record as on
the command line. Binds to 127.0.0.1 by default; there is no login, so do not expose it.
"""
import copy
import datetime
import http.server
import json
import pathlib
import threading
import urllib.parse

from . import __version__, cozumle, gecmis, saglik
from .adapter import RepoAdapter
from .checks import redact
from .desk import Desk, render
from .graph import Graph
from .ledger import Ledger
from .repo import Repo

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATIC = pathlib.Path(__file__).resolve().parent / "static"
DEFAULT_SITE = ROOT / "ornekler" / "ortam-banka.json"  # the example site plus two folders and every job type
RESULTS = ROOT / "results"
HARMFUL = ("false_green", "destructive")
ARM_NAMES = {"noop": "Hicbir sey yapma", "naive_apply": "Yazilani aynen uygula", "naive_return": "Hepsini iade et",
             "golden": "Referans cozum", "harness": "Harness'in kod payi", "raw_llm": "Ham model",
             "runbook_llm": "Ham model + runbook", "harness_llm": "Harness + model"}


class Office:
    """One site, its open and finished requests, and the desk that works on them."""

    def __init__(self, site_path=DEFAULT_SITE, model=None, licence=4, graph_path=":memory:", history_days=90):
        self.site_path, self.model, self.licence = pathlib.Path(site_path), model, licence
        self.graph_path, self.history_days = graph_path, history_days
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        site = json.loads(self.site_path.read_text(encoding="utf-8"))
        self.repo = Repo({**site, "request": {"talep_no": "_", "text": ""}})
        self.repo.tickets.clear()
        self.initial = copy.deepcopy(self.repo.jobs)
        self.ledger = Ledger()
        self.history = []
        # The error graph. With a file it persists; empty, it is filled with a generated past (gecmis.py) so the
        # page has a history to read until a real scheduler feeds it.
        self.graph = Graph(self.graph_path)
        self.graph_generated = not self.graph.nodes("job")
        if self.graph_generated and self.history_days:
            gecmis.build(site, days=self.history_days, graph=self.graph)

    # ---- reads ------------------------------------------------------------------
    def site(self):
        env, jobs = self.repo.list_env(), self.repo.list_defs()
        waiting = {j["name"]: sorted(k["name"] for k in jobs if j["name"] in k["deps"]) for j in jobs}
        cals = {n: {"desc": c["desc"], "rule": c["rule"], "next": self.repo.forecast(n, 45)[:8]}
                for n, c in sorted(self.repo.calendars.items())}
        changed = sorted(n for n in set(self.initial) | set(self.repo.jobs) if self.initial.get(n) != self.repo.jobs.get(n))
        out = {"today": env["today"], "hosts": env["hosts"], "folders": env["folders"], "standards": env["standards"],
               "holidays": env["holidays"], "calendars": cals, "jobs": jobs, "waiting": waiting, "changed": changed,
               "connections": env.get("connections", {}),
               "site_file": str(self.site_path.name), "model": self.model.spec if self.model else None,
               "licence": self.licence, "version": __version__}
        return json.loads(redact(json.dumps(out, ensure_ascii=False)))  # an old definition may carry a password

    def health(self):
        with self.lock:
            return {"findings": saglik.scan(self.repo, self.rules if hasattr(self, "rules") else ())}

    def reports(self, days=7):
        with self.lock:
            out = cozumle.reports(self.graph, self.repo.today.isoformat(), days)
            out["requests"] = [{"talep_no": h["talep_no"], "at": h["at"], "outcome": h["outcome"],
                                "job": (h.get("definition") or h.get("before") or {}).get("name")} for h in self.history]
            return json.loads(redact(json.dumps(out, ensure_ascii=False, default=str)))

    # ---- the one write ---------------------------------------------------------------
    def submit(self, text):
        lines = [x.strip() for x in str(text).splitlines() if x.strip() and not x.lstrip().startswith("#")]
        text = "\n".join(lines)
        no = next((x.split(":", 1)[1].strip() for x in lines if x.startswith("talep_no:")), "")
        with self.lock:
            if not no:
                no = f"WEB-{len(self.history) + 1:04d}"
                text = f"talep_no: {no}\n" + text
            if no in self.repo.tickets:
                return {"error": f"{no} numarali talep zaten islendi; yeni bir talep numarasi verin"}
            self.repo.tickets[no] = {"text": text, "status": "open", "record": None, "reason": None}
            adapter = RepoAdapter(self.repo)
            desk = Desk(adapter, model=self.model, ledger=self.ledger, licence=self.licence)
            started = datetime.datetime.now()
            report = desk.handle(no)
            # A request that carries a password is returned for it; the page never keeps or shows the password.
            entry = {"talep_no": no, "text": redact(text), "at": started.isoformat(timespec="seconds"),
                     "seconds": round((datetime.datetime.now() - started).total_seconds(), 2),
                     "outcome": report["outcome"], "reasons": report["reasons"], "definition": report["definition"],
                     "before": report["before"], "findings": report["findings"], "notes": report["notes"],
                     "forecast": report["forecast"], "record": report.get("record"), "agent": report["agent"],
                     "steps": report["steps"], "trace": adapter.trace,
                     "model_calls": getattr(self.model, "calls", 0), "summary": render(report)}
            entry = json.loads(redact(json.dumps(entry, ensure_ascii=False, default=str)))  # every copy shown
            self.history.insert(0, entry)
            if report["outcome"] == "closed":  # the graph remembers which request changed which job, and when
                d, b = report["definition"], report["before"] or {}
                job = (d or b).get("name")
                what = ("kaldirildi" if d is None else "yeni is" if not b else
                        "; ".join(f"{k}: {b.get(k)} -> {v}" for k, v in d.items() if b.get(k) != v))
                self.graph.add_change(no, job, self.repo.today.isoformat(), what)
                self.graph.commit()
            return entry

    def ledger_rows(self):
        with self.lock:
            rows = self.ledger.db.execute("SELECT id, body, prev, hash FROM episodes ORDER BY id DESC").fetchall()
            ok = self.ledger.verify_chain()
        return {"chain_ok": ok,
                "rows": [{"id": i, **json.loads(b), "prev": p[:12], "hash": h[:12]} for i, b, p, h in rows]}


    # ---- the error graph -------------------------------------------------------------
    def graph_summary(self):
        with self.lock:
            g, today = self.graph, self.repo.today.isoformat()
            incidents = [cozumle._incident(g, i["id"]) for i in g.nodes("incident")]
            fails = cozumle.failures(g)
            sigs = {}
            for f in fails:
                s = sigs.setdefault(f["signature"], {"signature": f["signature"], "count": 0, "jobs": set(), "last": ""})
                s["count"] += 1
                s["jobs"].add(f["job"])
                s["last"] = max(s["last"], f["day"])
            runs = g.runs(since=(self.repo.today - datetime.timedelta(days=29)).isoformat())
            daily = {}
            for r in runs:
                d = daily.setdefault(r["day"], [0, 0])
                d[0 if r["ok"] and not r.get("error") else 1] += 1
            return {"stats": g.stats(), "generated": self.graph_generated, "today": today,
                    "incidents": sorted(incidents, key=lambda i: (i["open"], i["day"]), reverse=True),
                    "failures": fails[:80],
                    "signatures": sorted(({**v, "jobs": sorted(v["jobs"])} for v in sigs.values()),
                                         key=lambda v: -v["count"]),
                    "warnings": cozumle.warnings(g, today),
                    "daily": [{"day": d, "ok": v[0], "failed": v[1]} for d, v in sorted(daily.items())]}

    def graph_analyse(self, run_id, with_model=False):
        with self.lock:
            if not run_id or self.graph.get(run_id) is None or not run_id.startswith("run:"):
                return {"error": "boyle bir calisma yok"}
            ev = cozumle.analyse(self.graph, run_id)
            seeds = [run_id, f"job:{ev['job']}"] + [c["id"] for c in ev["candidates"] if ":" in c["id"]
                                                   and self.graph.get(c["id"])]
            seeds += [p["id"] for p in ev["precedents"][:3]]
            ev["suggestion"] = cozumle.suggest(self.graph, ev)
            ev["picture"] = self.graph.neighbourhood([x for x in seeds if self.graph.get(x)], depth=1, limit=40)
            ev["model"] = cozumle.explain(self.model, ev) if with_model and self.model else None
            return ev


def bench_summary(path=None):
    """Correct and harmful share per arm and model, from a result file of `python -m vardiya sab run`."""
    files = sorted(p.name for p in RESULTS.glob("*.jsonl")) if RESULTS.exists() else []
    path = RESULTS / (path or ("sab-ext2.jsonl" if "sab-ext2.jsonl" in files else (files[0] if files else "")))
    if not path.is_file() or path.parent != RESULTS:
        return {"files": files, "file": None, "arms": [], "families": []}
    groups, families = {}, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        model = (r.get("model") or "").replace("ollama:", "").replace(":latest", "")
        key = (r["arm"], model, r.get("variant") or "")
        g = groups.setdefault(key, {"n": 0, "correct": 0, "harmful": 0, "calls": 0, "fam": {}})
        g["n"] += 1
        g["correct"] += r["verdict"] == "correct"
        g["harmful"] += r["verdict"] in HARMFUL
        g["calls"] += r.get("calls", 0)
        f = g["fam"].setdefault(r["family"], [0, 0])
        f[0] += r["verdict"] == "correct"
        f[1] += 1
        if r["family"] not in families:
            families.append(r["family"])
    order = list(ARM_NAMES)
    arms = [{"arm": a, "name": ARM_NAMES.get(a, a), "model": m, "variant": v, "n": g["n"], "correct": g["correct"],
             "harmful": g["harmful"], "calls": round(g["calls"] / g["n"], 1), "families": g["fam"]}
            for (a, m, v), g in sorted(groups.items(), key=lambda kv: (order.index(kv[0][0]) if kv[0][0] in order else 99, kv[0][1]))]
    return {"files": files, "file": path.name, "arms": arms, "families": families}


# ---- Usta: the incident side of the console (skills only; a model, when connected, reads the same sheet)
def _usta_skills():
    from . import opsbench
    from .skills import load_chains, load_general_skills, load_incident_classes, load_procedures
    d = opsbench.SKILLS
    return load_incident_classes(d), load_procedures(d), load_general_skills(d), load_chains(d)


def usta_catalog():
    """Every skill the agent carries, as titles: incident classes, admin procedures, general server skills, chains."""
    classes, procedures, general, chains = _usta_skills()
    return {"classes": [{"name": n, "title": c["title"], "signs": len(c["signs"]), "cause": c["cause"], "harmful": c["harmful"],
                         "chain": len(chains.get(n, {}).get("order", []))} for n, c in classes.items()],
            "procedures": [{"name": n, "title": p["title"], "needs": p.get("needs") or []} for n, p in procedures.items()],
            "general": [{"name": n, "title": g["title"], "classes": g["classes"],
                         "os": [o for o in ("unix", "windows") if not g["check"][o].startswith("(uygulanmaz")]}
                        for n, g in general.items()],
            "chains": len(chains)}


def usta_ask(text):
    """What the harness finds for one incident report, with no model: candidate causes and how sure it is, the
    verified fix, what must not be done, the procedures, the read-only server checks and the order to try them in."""
    from . import opsbench
    classes, procedures, general, chains = _usta_skills()
    case = {"prompt": str(text)[:6000]}
    _, found = opsbench.context(case, classes, procedures, general, chains)
    signs = opsbench.class_signs(classes, case["prompt"])
    out = {"product": found["product"], "os": found["os"], "candidates": [], "procedures": [], "checks": [], "chain": []}
    for name in found["classes"]:
        c = classes[name]
        out["candidates"].append({"name": name, "title": c["title"], "strength": found["strength"][name],
                                  "signs": signs.get(name) or [], "cause": c["cause"],
                                  "fix": c.get("fix_by", {}).get(found["product"]) or c["fix"],
                                  "harmful": [w[0] for a in c["harmful"] for w in [opsbench.ACTION_WORDS.get(a, [a])]]})
    for name in found["procedures"]:
        p = procedures[name]
        out["procedures"].append({"name": name, "title": p["title"], "steps": [x.strip() for x in p["steps"].split(";") if x.strip()],
                                  "caution": p["caution"]})
    for name in found["general"]:
        g = general[name]
        oses = [found["os"]] if found["os"] else ["unix", "windows"]
        out["checks"].append({"name": name, "title": g["title"], "caution": g["caution"],
                              "by_os": [{"os": o, "check": [x.strip() for x in g["check"][o].split(";") if x.strip()],
                                         "fix": g["fix"][o]} for o in oses if not g["check"][o].startswith("(uygulanmaz")]})
    out["chain"] = [{"ref": r, "title": opsbench.ref_title(r, classes, procedures, general)} for r in found["chain"]]
    return out


def usta_examples(limit=8):
    """A few development cases to try the desk with (never the held-out test cases)."""
    from . import opsbench
    rows = [c for c in opsbench.load("dev") if c["track"] == "olay"]
    step = max(1, len(rows) // limit)
    return [{"id": c["id"], "text": c["prompt"]} for c in rows[::step][:limit]]


def ops_results():
    """Ops bench: verdict counts per split, arm and model, and the draft-against-final table of the Usta protocol."""
    from . import opsbench
    path = opsbench.OUT
    if not path.is_file():
        return {"rows": [], "paired": []}
    table, latest = {}, {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        g = table.setdefault((r["split"], r["arm"], r.get("model") or ""), {"dogru": 0, "yarim": 0, "yanlis": 0, "zararli": 0})
        g[r["verdict"]] = g.get(r["verdict"], 0) + 1
        if r["arm"] in opsbench.USTA_ARMS:
            latest[(r["id"], r["arm"], r.get("model"))] = r
    rows = [{"split": s, "arm": a, "model": m, "n": sum(g.values()), **g} for (s, a, m), g in sorted(table.items())]
    paired = {}
    for (_, arm, model), r in latest.items():
        g = paired.setdefault((r["split"], arm, model), {"n": 0, "draft": 0, "final": 0, "up": 0, "down": 0, "harm_draft": 0, "harm_final": 0})
        d, f = r.get("draft_verdict"), r["verdict"]
        g["n"] += 1
        g["draft"] += d == "dogru"
        g["final"] += f == "dogru"
        g["up"] += d != "dogru" and f == "dogru"
        g["down"] += d == "dogru" and f != "dogru"
        g["harm_draft"] += d == "zararli"
        g["harm_final"] += f == "zararli"
    return {"rows": rows, "paired": [{"split": s, "arm": a, "model": m, **g} for (s, a, m), g in sorted(paired.items())]}


def saha_runs():
    """Live bench: every run with its verdict counts per arm and the scenario-by-arm matrix."""
    from .saha import kosu
    out = []
    if not kosu.OUT.is_dir():
        return {"runs": []}
    for d in sorted(kosu.OUT.iterdir()):
        if not (d / "ozet.jsonl").is_file() or d.name.startswith("dogrula"):
            continue
        rows = kosu.ozet(d.name)
        arms = {}
        for (sid, kol), r in rows.items():
            g = arms.setdefault(kol, {"kol": kol, "model": r.get("model"), "n": 0, "adim": 0, "saniye": 0, **{h: 0 for h in kosu.HUKUMLER}, "kurulamadi": 0})
            g["n"] += 1
            g[r["hukum"]] = g.get(r["hukum"], 0) + 1
            g["adim"] += r.get("adim") or 0
            g["saniye"] += r.get("saniye") or 0
        scen = {}
        for (sid, kol), r in rows.items():
            scen.setdefault(sid, {"id": sid, "aile": r.get("aile"), "tur": r.get("tur"), "bilesik": r.get("bilesik"), "kollar": {}})["kollar"][kol] =                 {"hukum": r["hukum"], "adim": r.get("adim"), "saniye": r.get("saniye"), "tutan": r.get("tutan"), "toplam": r.get("toplam")}
        out.append({"ad": d.name, "kollar": sorted(arms.values(), key=lambda g: g["kol"]), "senaryolar": sorted(scen.values(), key=lambda x: x["id"])})
    return {"runs": out}


def saha_episode(ad, senaryo, kol):
    """The evidence of one episode: ticket, tool calls with their real output, job outputs, checks, verdict."""
    from .saha import kosu
    safe = lambda x: bool(x) and all(c.isalnum() or c in "-_." for c in x) and ".." not in x  # noqa: E731
    if not (safe(ad) and safe(senaryo) and safe(kol)):
        return None
    path = kosu.OUT / ad / f"{senaryo}__{kol}.json"
    if not path.is_file():
        return None
    d = json.loads(path.read_text(encoding="utf-8"))
    for x in d.get("iz", []):
        x["cikti"] = x.get("cikti", "")[:3000]
    return d


def examples():
    out = [{"name": "Bos sablon", "text": (ROOT / "templates" / "talep-sablonu.txt").read_text(encoding="utf-8")}]
    for p in sorted((ROOT / "ornekler").glob("*.txt")):
        out.append({"name": p.stem, "text": p.read_text(encoding="utf-8")})
    for p in sorted((ROOT / "scenarios" / "talep").glob("t-*.json")):
        sc = json.loads(p.read_text(encoding="utf-8"))
        out.append({"name": f"{sc['id']}: {sc['title']}", "text": "\n".join(sc["request"]["lines"])})
    return out


def make_handler(office):
    class Handler(http.server.BaseHTTPRequestHandler):
        server_version = f"vardiya/{__version__}"

        def log_message(self, fmt, *args):  # quiet; the page shows what happened
            pass

        def _send(self, code, body, ctype="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(url.query)
            if url.path in ("/", "/index.html"):
                return self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            if url.path == "/api/site":
                return self._send(200, office.site())
            if url.path == "/api/history":
                return self._send(200, office.history)
            if url.path == "/api/ledger":
                return self._send(200, office.ledger_rows())
            if url.path == "/api/examples":
                return self._send(200, examples())
            if url.path == "/api/health":
                return self._send(200, office.health())
            if url.path == "/api/reports":
                return self._send(200, office.reports(int((q.get("days") or ["7"])[0])))
            if url.path == "/api/graph":
                return self._send(200, office.graph_summary())
            if url.path == "/api/graph/analyse":
                out = office.graph_analyse((q.get("run") or [""])[0])
                return self._send(200 if "candidates" in out else 400, out)
            if url.path == "/api/bench":
                return self._send(200, bench_summary((q.get("file") or [None])[0]))
            if url.path == "/api/usta/catalog":
                return self._send(200, usta_catalog())
            if url.path == "/api/usta/examples":
                return self._send(200, usta_examples())
            if url.path == "/api/ops":
                return self._send(200, ops_results())
            if url.path == "/api/saha":
                return self._send(200, saha_runs())
            if url.path == "/api/saha/bolum":
                ep = saha_episode((q.get("ad") or [""])[0], (q.get("senaryo") or [""])[0], (q.get("kol") or [""])[0])
                return self._send(200 if ep else 404, ep or {"error": "yok"})
            return self._send(404, {"error": "yok"})

        def do_POST(self):
            size = int(self.headers.get("Content-Length") or 0)
            if size > 64_000:
                return self._send(413, {"error": "talep cok uzun"})
            try:
                body = json.loads(self.rfile.read(size) or b"{}")
            except ValueError:
                return self._send(400, {"error": "gecersiz JSON"})
            path = urllib.parse.urlparse(self.path).path
            if path == "/api/request":
                out = office.submit(body.get("text", ""))
                return self._send(400 if "error" in out else 200, out)
            if path == "/api/graph/explain":
                if office.model is None:
                    return self._send(400, {"error": "model bagli degil; sunucuyu --model ile baslatin"})
                out = office.graph_analyse(body.get("run", ""), with_model=True)
                return self._send(200 if "candidates" in out else 400, out)
            if path == "/api/usta/ask":
                text = str(body.get("text", "")).strip()
                if not text:
                    return self._send(400, {"error": "olay metni bos"})
                return self._send(200, usta_ask(text))
            if path == "/api/reset":
                with office.lock:
                    office.reset()
                return self._send(200, {"ok": True})
            return self._send(404, {"error": "yok"})

    return Handler


def serve(office, host="127.0.0.1", port=8765):
    httpd = http.server.ThreadingHTTPServer((host, port), make_handler(office))
    print(f"Vardiya onyuz: http://{host}:{port}  (site: {office.site_path.name}, model: "
          f"{office.model.spec if office.model else 'bagli degil'})  durdurmak icin Ctrl+C")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
