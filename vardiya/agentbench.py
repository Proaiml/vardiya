"""Bench bridge for agent tools: lets any coding agent (Antigravity, an IDE assistant, a CLI agent)
sit in the "bare model" seat of Scheduler Admin Bench by running shell commands.

    python -m vardiya.agentbench start --name hydrogen --label "antigravity:gemini-4-hydrogen-extra"
    python -m vardiya.agentbench call list_defs
    python -m vardiya.agentbench call get_def --json "{\\"job\\": \\"ODM_LOAD_STG\\"}"
    python -m vardiya.agentbench call deploy_job --file tanim.json
    python -m vardiya.agentbench next            # close this request's turn and show the next one
    python -m vardiya.agentbench report --name hydrogen

The session lives in results/agent/<name>.json. The repository state is rebuilt by replaying the
recorded actions on every call, so nothing but that file is needed and every verdict can be
replayed. The agent is never shown the expected outcome or its verdicts.
"""
import argparse
import json
import pathlib
import sys

from . import __version__, bench_req, sabgen
from .adapter import RepoAdapter
from .repo import ACTION_VERBS, READ_VERBS, Repo

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIR = ROOT / "results" / "agent"
CURRENT = DIR / "_current.txt"
HELP = (
    "Sen bir toplu is zamanlayicisinin is tanimlarini yoneten adminsin. Acik bir talep var.\n"
    "Talebi dogru uygula ya da oldugu gibi uygulanmamasi gerekiyorsa gerekcesiyle talep sahibine iade et.\n\n"
    "Okuma: get_request, list_defs, get_def {job}, list_env, forecast {calendar, days}\n"
    "Eylem: deploy_job {definition} (definition.name adli isi olusturur ya da uzerine yazar; alanlar: "
    + ", ".join(sabgen.KEY_OF) + "),\n"
    "       delete_job {job}, close_request {talep_no, record} (record: talep_no, kapatan, istenen),\n"
    "       return_request {talep_no, reason}\n\n"
    "Komut:  python -m vardiya.agentbench call <fiil> [--json \"{...}\" | --file dosya.json]\n"
    "Bitince: python -m vardiya.agentbench next")


def _path(name):
    return DIR / f"{name}.json"


def _load(name=None):
    name = name or (CURRENT.read_text(encoding="utf-8").strip() if CURRENT.exists() else None)
    if not name or not _path(name).exists():
        raise SystemExit("oturum yok: once 'start' calistirin")
    return json.loads(_path(name).read_text(encoding="utf-8"))


def _save(s):
    DIR.mkdir(parents=True, exist_ok=True)
    _path(s["name"]).write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
    CURRENT.write_text(s["name"], encoding="utf-8")


def _scenarios(s):
    return sabgen.generate(s["per_family"], s["seed"], tuple(s["families"]), s["split"])


def _replayed(sc, trace):
    repo = Repo(sc)
    for verb, kw, _ in trace:
        repo.act(verb, **json.loads(json.dumps(kw)))
    return repo


def _show(s, sc):
    done, total = s["index"], len(_scenarios(s))
    text = [f"=== Talep {done + 1}/{total} ===", sc["request"]["text"], "", HELP]
    if s["mode"] == "runbook":
        text.append(bench_req.RUNBOOK)
    return "\n".join(text)


def _finish(s, sc):
    repo = _replayed(sc, s["trace"])
    s["rows"].append({"arm": "runbook_llm" if s["mode"] == "runbook" else "raw_llm", "model": s["label"], "variant": "",
                      "scenario": sc["id"], "family": sc["family"], "verdict": bench_req.verdict(sc, repo),
                      "actions": sum(1 for t in s["trace"] if t[2]), "replay_ok": True, "hash": repo.state_hash(),
                      "calls": s["calls"], "seconds": 0, "version": __version__, "trace": s["trace"]})
    s.update(index=s["index"] + 1, trace=[], calls=0)


def main(argv=None):
    p = argparse.ArgumentParser(prog="vardiya.agentbench")
    p.add_argument("cmd", choices=["start", "show", "call", "next", "report", "merge"])
    p.add_argument("verb", nargs="?")
    p.add_argument("--name")
    p.add_argument("--label", help="raporda gorunecek model adi")
    p.add_argument("--mode", choices=["raw", "runbook"], default="raw")
    p.add_argument("--per-family", type=int, default=2)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--split", choices=["dev", "test"], default="dev")
    p.add_argument("--families")
    p.add_argument("--json", dest="json_args")
    p.add_argument("--file")
    args = p.parse_args(argv)

    if args.cmd == "start":
        name = args.name or "ajan"
        s = {"name": name, "label": args.label or f"agent:{name}", "mode": args.mode, "per_family": args.per_family,
             "seed": args.seed, "split": args.split, "index": 0, "trace": [], "calls": 0, "rows": [],
             "families": args.families.split(",") if args.families else list(sabgen.FAMILIES)}
        _save(s)
        print(_show(s, _scenarios(s)[0]))
        return 0

    s = _load(args.name)
    scenarios = _scenarios(s)
    if args.cmd in ("report", "merge"):
        if not s["rows"]:
            print("henuz biten talep yok")
            return 0
        from . import sab
        if args.cmd == "merge":  # put the agent's rows next to the other arms so the report can pair them
            have = {sab._key(r) for r in sab.load(sab.DEFAULT_OUT)}
            new = [r for r in s["rows"] if sab._key(r) not in have]
            sab.DEFAULT_OUT.parent.mkdir(parents=True, exist_ok=True)
            with sab.DEFAULT_OUT.open("a", encoding="utf-8") as f:
                f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in new)
            print(f"{len(new)} satir {sab.DEFAULT_OUT} dosyasina eklendi")
            return 0
        print(sab.report(s["rows"]))
        print(f"biten talep: {len(s['rows'])}/{len(scenarios)}")
        return 0
    if s["index"] >= len(scenarios):
        print("Butun talepler bitti. Tesekkurler.")
        return 0
    sc = scenarios[s["index"]]

    if args.cmd == "show":
        print(_show(s, sc))
    elif args.cmd == "call":
        if args.verb not in READ_VERBS + ACTION_VERBS:
            print(json.dumps({"error": f"bilinmeyen fiil: {args.verb}", "fiiller": list(READ_VERBS + ACTION_VERBS)}))
            return 2
        raw = pathlib.Path(args.file).read_text(encoding="utf-8-sig") if args.file else (args.json_args or "{}")
        try:
            given = json.loads(raw)
        except ValueError as e:
            print(json.dumps({"error": f"JSON okunamadi: {e}"}))
            return 2
        kw = bench_req._raw_args({"verb": args.verb, "args": given if isinstance(given, dict) else {}})
        if args.verb in ("close_request", "return_request") and not kw.get("talep_no"):
            kw["talep_no"] = sc["request"]["talep_no"]
        adapter = RepoAdapter(_replayed(sc, s["trace"]))
        try:
            result = adapter.call(args.verb, **kw)
        except (TypeError, KeyError, ValueError, AttributeError) as e:
            result = {"error": str(e)}
        s["trace"] += adapter.trace
        s["calls"] += 1
        _save(s)
        print(json.dumps(result, ensure_ascii=False, indent=1, default=str))
    elif args.cmd == "next":
        _finish(s, sc)
        _save(s)
        if s["index"] >= len(scenarios):
            print(f"Butun talepler bitti ({len(scenarios)}). Tesekkurler.")
        else:
            print(_show(s, scenarios[s["index"]]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
