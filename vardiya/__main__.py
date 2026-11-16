"""CLI: python -m vardiya <bench|fuzz|run|talep|models> ..."""
import argparse
import json
import pathlib
import sys

from . import bench, bench_req
from .adapter import EmulatorAdapter, RepoAdapter
from .desk import Desk
from .desk import render as render_request
from .emulator import Emulator
from .gateway import connect, list_ollama
from .harness import Harness, render
from .ledger import Ledger
from .repo import Repo
from .skills import load_skills
from .world import World

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main(argv=None):
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:2] == ["ops", "eylem"]:
        from . import opsagent
        ap = argparse.ArgumentParser(prog="vardiya ops eylem")
        ap.add_argument("--split", default="dev")
        ap.add_argument("--arms", default="kod,saf")
        ap.add_argument("--seeds", type=int, default=40)
        ap.add_argument("--model")
        a = ap.parse_args(argv[2:])
        rows = opsagent.run(a.split, range(a.seeds), arms=a.arms.split(","), model=connect(a.model) if a.model else None)
        print(opsagent.report(rows))
        return 0
    if argv[:1] == ["ops"]:
        from . import opsbench
        return opsbench.main(argv[1:])
    if argv[:1] == ["olay"]:
        from . import olaybench
        return olaybench.main(argv[1:])
    if argv[:1] == ["saha"]:
        if argv[1:2] == ["kur"]:
            from .saha.lab import Lab, kur
            print("\n".join(kur(Lab())))
            return 0
        from .saha import kosu
        return kosu.main(argv[1:])
    if argv[:1] == ["sab"]:
        from . import sab
        return sab.main(argv[1:])
    p = argparse.ArgumentParser(prog="vardiya")
    p.add_argument("cmd", choices=["bench", "fuzz", "run", "talep", "models", "web"])
    p.add_argument("scenario", nargs="?", help="senaryo kimligi (run ve talep icin)")
    p.add_argument("--model", help="ornek: ollama:qwen3:8b")
    p.add_argument("--base-url")
    p.add_argument("--scenarios", default=str(ROOT / "scenarios"))
    p.add_argument("--skills", default=str(ROOT / "skills"))
    p.add_argument("--ledger", default=":memory:")
    p.add_argument("--file", help="talep: senaryo yerine doldurulmus sablon dosyasi")
    p.add_argument("--site", help="talep --file ve web icin ortam dosyasi (varsayilan: scenarios/talep/_ortam.json)")
    p.add_argument("--host", default="127.0.0.1", help="web: dinlenecek adres")
    p.add_argument("--port", type=int, default=8765, help="web: port")
    p.add_argument("--licence", type=int, default=4, help="web: ajanin yetki seviyesi (2 = yalnizca oner)")
    p.add_argument("--only", choices=["ariza", "talep"], help="bench ve fuzz icin yalnizca bir taraf")
    p.add_argument("-n", type=int, default=300)
    p.add_argument("--seed", type=int, default=0)
    args = p.parse_args(argv)

    if args.cmd == "models":
        print("\n".join(list_ollama()))
        return 0
    if args.cmd == "web":
        from .web import DEFAULT_SITE, Office, serve
        model = connect(args.model, base_url=args.base_url) if args.model else None
        serve(Office(args.site or DEFAULT_SITE, model=model, licence=args.licence), args.host, args.port)
        return 0
    scenarios, skills = bench.load_scenarios(args.scenarios), load_skills(args.skills)
    requests = bench_req.load_scenarios(pathlib.Path(args.scenarios) / "talep")
    model = connect(args.model, base_url=args.base_url) if args.model else None

    if args.cmd == "bench":
        if args.only != "talep":
            print("== Ariza mudahalesi ==")
            print(bench.format_matrix(bench.run_matrix(scenarios, skills, model)))
        if args.only != "ariza":
            print("== Talep karsilama ==")
            print(bench.format_matrix(bench_req.run_matrix(requests, model), width=18))
    elif args.cmd == "fuzz":
        bad = False
        if args.only != "talep":
            tally = bench.fuzz(scenarios, n=args.n, seed=args.seed)
            for mode, t in tally.items():
                harmful = sum(t.get(k, 0) for k in bench.HARMFUL)
                print(f"ariza  {mode:<8} {dict(sorted(t.items()))}  zararli: {harmful}/{args.n}")
            bad = any(tally["harness"].get(k) for k in bench.HARMFUL)
        if args.only != "ariza":
            t = bench_req.fuzz(requests, n=args.n, seed=args.seed)
            print(f"talep  raw      zararli: {t['raw']}/{args.n}")
            print(f"talep  harness  zararli: {t['harness']}/{args.n}  (uygulanan talep: {t['harness_applied']})")
            bad = bad or t["harness"] > 0
        return 1 if bad else 0
    elif args.cmd == "run":
        sc = next((s for s in scenarios if s["id"] == args.scenario), None)
        if sc is None:
            print("senaryolar: " + ", ".join(s["id"] for s in scenarios))
            return 2
        emu = Emulator(sc)
        a = EmulatorAdapter(emu)
        site = {**sc.get("site", {}), "approval": "ask"}
        ask = lambda s: input(f"ONAY? L{s['level']} {s['action']} {s['job'] or s['event']} [e/h]: ").strip().lower() == "e"
        h = Harness(a, skills, site=site, model=model, ledger=Ledger(args.ledger), approver=ask)
        print(render(h.handle(), a.call("get_alerts")))
        print("\nHukum:", bench.verdict(sc, emu), "| durum ozeti:", emu.state_hash())
        top = World(a).slowest(3)
        print("En yavas isler:", [(r["job"], r["median"]) for r in top["slowest"]])
    elif args.cmd == "talep":
        if args.file:
            # Your own request against a site file: nothing is expected, so there is no verdict.
            lines = pathlib.Path(args.file).read_text(encoding="utf-8-sig").splitlines()
            lines = [x.strip() for x in lines if x.strip() and not x.lstrip().startswith("#")]
            no = next((x.split(":", 1)[1].strip() for x in lines if x.startswith("talep_no:")), "") or "TALEP-0"
            site = pathlib.Path(args.site) if args.site else pathlib.Path(args.scenarios) / "talep" / "_ortam.json"
            sc = {**json.loads(site.read_text(encoding="utf-8")), "request": {"talep_no": no, "text": "\n".join(lines)}}
        else:
            sc = next((s for s in requests if s["id"] == args.scenario), None)
            if sc is None:
                print("talep senaryolari: " + ", ".join(s["id"] for s in requests))
                return 2
        repo = Repo(sc)
        desk = Desk(RepoAdapter(repo), model=model, site=sc.get("site"), ledger=Ledger(args.ledger))
        print(sc["request"]["text"], "\n")
        print(render_request(desk.handle()))
        if "expected" in sc:
            print("\nHukum:", bench_req.verdict(sc, repo), "| durum ozeti:", repo.state_hash())
    return 0


if __name__ == "__main__":
    sys.exit(main())
