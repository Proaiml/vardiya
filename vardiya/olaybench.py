"""Incident bench: the same small model on the same incidents, alone and inside the harness.

    python -m vardiya olay run --split dev                      # code arm only
    python -m vardiya olay run --split test --model ollama:qwen3:8b
    python -m vardiya olay report

Each case is one incident of a generated 90-day history (gecmis.py) whose root cause and right fix are known.
The question is the admin's: what is the root cause, and what do we do now?

Splits. `dev`: the demo site and the error lines the solvers were written against. `test`: every job, host,
user, table and resource renamed, and every error line written differently (another product's wording of
the same failure). A solver that only matched names or one wording fails on `test`.

Arms, all with the same facts:
  kod          the harness's code: first candidate, suggested action. No model.
  raw_llm      the model alone. It gets the failing run, the job, every failure, change and incident of the
               past 90 days as text, the list of entities and the list of actions, and answers.
  harness_llm  the model inside the harness: code gathers the evidence and ranks the candidates, the model
               picks one; the action follows from the pick.

Scoring: root right, action right, and harmful (Set OK, or re-running a job whose failure re-running is
known not to fix or that would load bad data).
"""
import argparse
import collections
import json
import pathlib
import random
import time

from . import __version__, cozumle, gecmis
from .gateway import connect

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT / "ornekler" / "ortam-banka.json"
OUT = ROOT / "results" / "olay.jsonl"
RERUN, SETOK, WAIT = "isi yeniden calistir (rerun)", "isi elle basarili say (Set OK)", "hicbir sey yapma, izle"
def _harmful():
    """Actions each class names as harmful (skills/olay-siniflari), in the words of the action list."""
    words = {"rerun": RERUN, "set_ok": SETOK}
    return {k: {words[a] for a in c.get("harmful", [])} for k, c in gecmis._C.items()}


HARMFUL = _harmful()
# test split: other names and another wording of each failure, written before any run on this split
NAMES = {"ODM_WATCH_DOSYA": "PAY_FILE_WAIT", "ODM_LOAD_ODEME": "PAY_STAGE_LOAD", "ODM_POST_DEFTER": "PAY_LEDGER_POST",
         "ODM_BANKA_GONDER": "PAY_BANK_SEND", "RPR_GUNLUK_OZET": "REP_DAILY_SUM", "RPR_HAFTALIK": "REP_MGMT",
         "MHS_WATCH_KUR": "ACC_FX_WAIT", "MHS_LOAD_KUR": "ACC_FX_LOAD", "MHS_KUR_FARKI": "ACC_FX_DIFF",
         "MHS_MUTABAKAT": "ACC_RECON", "MHS_GUN_SONU": "ACC_EOD", "KRD_TEDARIK_AL": "CRD_VENDOR_GET",
         "KRD_LOAD_SKOR": "CRD_SCORE_LOAD", "KRD_RISK_HESAP": "CRD_RISK_CALC", "KRD_RAPOR": "CRD_REPORT",
         "app01": "pay-app-1", "app02": "fin-app-2", "db01": "core-db-1", "rpr01": "rep-node-1", "etl01": "etl-node-1",
         "batchusr": "svc_batch", "odmusr": "svc_pay", "dbbatch": "svc_db", "rprusr": "svc_rep", "mhsusr": "svc_acc",
         "etlusr": "svc_etl", "DEFTER": "GL_LEDGER", "KUR": "FX_RATES", "KUR_FARKI": "FX_DIFF", "MUTABAKAT": "RECON",
         "ODEME_STG": "PAY_STAGE", "SKOR_STG": "SCORE_STAGE", "RISK": "RISK_OUT", "DB_YAZMA": "DB_WRITE_SLOTS"}
WORDING = {
    "kilit": "SQLSTATE 55P03: could not obtain lock on relation {table}",
    "parola": "LOGON FAILURE for account {user}: unknown user name or bad password (Win32 error 1326)",
    "host": "Agent {host} unavailable: communication timeout, job remains in Wait Host",
    "sessiz": "Completed with return code 0; post-check: {table} row count {rows}, expected about {expected}",
    "dosya": "No file matching {path} arrived before the time limit ({minutes} min)",
    "degisiklik": "sh: line 1: {path}: No such file or directory (rc 127)",
    "takili": "Job exceeded {minutes} minutes; process tree still contains {proc}",
    "disk": "IOException: There is not enough space on the disk ({host})",
    "kaynak": "Job waiting for quantitative resource {resource}: requested 1, available 0 for {minutes} min",
    "yama": "The system cannot execute the specified program after reboot on {host} (CScript)",
    "setok": "No rows selected from {table}: nothing to post",
    "tarih": "Task {job} waiting: upstream {pred} has no run for logical date {odate} (it ran for {prev})",
    "mukerrer": "Duplicate run detected: {job} started while a previous instance was still active, overlap on {path}",
    "zaman": "AutoSys term_run_time reached for {job}: job TERMINATED after {limit} minutes",
}


def cases(split="dev", seed=None):
    site = json.loads(SITE.read_text(encoding="utf-8"))
    if split == "test":
        site = gecmis.rename_site(site, NAMES)
        g, truth = gecmis.build(site, seed=seed or 11, names=NAMES, wording=WORDING)
    else:
        g, truth = gecmis.build(site, seed=seed or 7)
    out = []
    for t in truth:
        rid = next((f["id"] for f in cozumle.failures(g, t["day"]) if f["job"] in t["jobs"]), None)
        if rid is None:
            continue
        job = g.get(rid)["job"]
        root = t["root"] or ("dis:kaynak-sistem" if t["kind"] == "dosya" else f"job:{job}")
        ok_actions = {t["fix"]} | ({"dosya gelince zinciri serbest birak"} if t["kind"] == "dosya" else set())
        out.append({"id": f"{split}-{t['key']}", "split": split, "kind": t["kind"], "run": rid, "job": job,
                    "day": t["day"], "root": root, "actions": sorted(ok_actions)})
    return g, out


def actions():
    acts = sorted({fix for _, _, fix in gecmis.CATALOG.values()} | {"dosya gelince zinciri serbest birak"})
    return acts + [RERUN, SETOK, WAIT]


def _entities(g, upto):
    ids = []
    for kind in ("job", "host", "user", "connection", "table", "resource", "change"):
        ids += [n["id"] for n in g.nodes(kind) if kind != "change" or n.get("day", "") <= upto]
    return ids + ["dis:kaynak-sistem"]


def raw_prompt(g, case):
    """Everything the graph knows about the past, as an admin would see it in logs and tickets: no ranking."""
    run, job = g.get(case["run"]), g.get(f"job:{case['job']}")
    attrs = sorted(g.attrs(case["job"]))
    deps = [e["to"] for e in g.out(f"job:{case['job']}", "after")]
    fails = [f for f in cozumle.failures(g) if f["day"] <= case["day"]][:60]
    lines = [f"Failed now: {case['job']} on {case['day']}: {run['error']}",
             f"Job {case['job']}: type {job.get('type')}, calendar {job.get('calendar')}, uses {', '.join(attrs)}, "
             f"waits for {', '.join(deps) or 'nothing'}.", "", "Failures in the last 90 days (newest first):"]
    lines += [f"- {f['day']} {f['job']}: {f['error']}" for f in fails]
    lines += ["", "Changes:"] + [f"- {c['day']} {c['id']} on {c.get('job') or c.get('host')}: {c['what']}"
                                 for c in g.nodes("change") if c["day"] <= case["day"]]
    lines += ["", "Set OK by operators:"] + [f"- {r['day']} {r['job']}: {r.get('error')}" for r in g.runs()
                                             if r.get("set_ok") and r["day"] <= case["day"]]
    lines += ["", "Past incidents:"]
    for inc in g.nodes("incident"):
        i = cozumle._incident(g, inc["id"])
        if i["day"] < case["day"]:
            lines.append(f"- {i['day']} {', '.join(i['jobs'])}: root {i['root']}, done '{i['resolution']}', "
                         f"{'held' if i['verified'] else 'came back'}")
    return "\n".join(lines)


def ask_raw(model, g, case):
    ents, acts = _entities(g, case["day"]), actions()
    msg = raw_prompt(g, case) + (
        "\n\nYou are the batch scheduler administrator on call. What is the root cause of the failure now, and what "
        "do you do? Answer with ONE JSON object: {\"root\": \"<one entity id from the list>\", \"action\": <number of "
        "one action>, \"why\": \"<one sentence>\"}\n\nEntities: " + ", ".join(ents) + "\n\nActions:\n"
        + "\n".join(f"{i}. {a}" for i, a in enumerate(acts)))
    out = model.ask_json([{"role": "user", "content": msg}])
    if not isinstance(out, dict):
        return None, None
    a = out.get("action")
    try:
        a = acts[int(a)]
    except (TypeError, ValueError, IndexError):
        a = None
    return out.get("root"), a


def solve(g, case, arm, model=None):
    ev = cozumle.analyse(g, case["run"])
    if arm == "raw_llm":
        return ask_raw(model, g, case)
    chosen = ev["candidates"][0]["id"] if ev["candidates"] else None
    if arm == "harness_llm":
        pick = cozumle.explain(model, ev)
        chosen = pick["candidate"] if pick and not pick.get("rejected") else chosen
    s = cozumle.suggest(g, ev, chosen)
    return chosen, (s or {}).get("action")


def verdict(case, root, action):
    harmful = action in HARMFUL.get(case["kind"], {SETOK}) or action == SETOK
    if harmful:
        return "zararli"
    r, a = root == case["root"], action in case["actions"]
    return "dogru" if r and a else "yarim" if r or a else "yanlis"


def run(split, arms, model_spec=None, out=OUT, budget=None):
    g, cs = cases(split)
    model = connect(model_spec) if model_spec else None
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done.add((r["case"], r["arm"], r.get("model")))
    started, n = time.time(), 0
    for c in cs:
        for arm in arms:
            key = (c["id"], arm, model_spec if arm != "kod" else None)
            if key in done or (arm != "kod" and model is None):
                continue
            if budget and time.time() - started > budget:
                print(f"butce doldu: {n} hucre")
                return
            t0, calls0 = time.time(), getattr(model, "calls", 0)
            try:
                root, action = solve(g, c, arm, model)
            except Exception as e:  # an infrastructure error is not a verdict
                print(f"[altyapi hatasi, atlandi] {arm} {c['id']}: {e}")
                continue
            row = {"case": c["id"], "split": split, "kind": c["kind"], "arm": arm, "model": key[2], "root": root,
                   "action": action, "want_root": c["root"], "verdict": verdict(c, root, action),
                   "calls": getattr(model, "calls", 0) - calls0, "seconds": round(time.time() - t0, 1),
                   "version": __version__}
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    print(f"tamamlanan hucre: {n}, dosya: {out}")


def report(out=OUT):
    rows = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    groups = collections.defaultdict(collections.Counter)
    for r in rows:
        groups[(r["split"], r["arm"], (r.get("model") or "").replace("ollama:", "").replace(":latest", ""))][r["verdict"]] += 1
    lines = ["| Bolum | Kol | Model | n | Dogru | Yarim | Yanlis | Zararli |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for (split, arm, model), c in sorted(groups.items()):
        n = sum(c.values())
        lines.append(f"| {split} | {arm} | {model or '-'} | {n} | {c['dogru']} | {c['yarim']} | {c['yanlis']} | {c['zararli']} |")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(prog="vardiya olay")
    p.add_argument("cmd", choices=["run", "report", "list"])
    p.add_argument("--split", choices=["dev", "test"], default="dev")
    p.add_argument("--model")
    p.add_argument("--arms", default="kod,raw_llm,harness_llm")
    p.add_argument("--out", default=str(OUT))
    p.add_argument("--budget", type=float)
    a = p.parse_args(argv)
    out = pathlib.Path(a.out)
    if a.cmd == "list":
        for c in cases(a.split)[1]:
            print(c["id"], c["kind"], c["job"], c["root"])
    elif a.cmd == "run":
        run(a.split, a.arms.split(","), a.model, out, a.budget)
    else:
        print(report(out))
    return 0
