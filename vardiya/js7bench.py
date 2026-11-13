"""External validity: the same request scenarios, with the jobs living in a real JS7 scheduler.

    python -m vardiya.js7bench --per-family 1 --seed 1

For each scenario and arm the verdict is computed twice, from the emulator and from JS7, with the
same judge. Agreement means the result did not depend on the emulator; a disagreement is reported
with what JS7 itself refused, which is a finding about the real scheduler, not an error to hide.
"""
import argparse
import json
import pathlib
import time

from . import bench_req, sabgen
from .js7 import JS7, lab_config
from .js7repo import JS7Repo, purge

ARMS = {"naive_apply": bench_req.arm_naive_apply, "naive_return": bench_req.arm_naive_return,
        "golden": bench_req.arm_golden, "harness": bench_req.arm_harness}
ROOT = pathlib.Path(__file__).resolve().parent.parent


def ensure_hosts(js, cfg):
    """Every host name the generator can use becomes an alias of the lab's one Agent."""
    js.post("/agents/inventory/store", {"controllerId": cfg["controller_id"], "update": True, "agents": [{
        "agentId": cfg["agent_id"], "agentName": cfg["agent_name"], "url": cfg["agent_url"],
        "agentNameAliases": sorted(sabgen.HOSTS)}]})
    js.post("/agents/inventory/deploy", {"controllerId": cfg["controller_id"], "agentIds": [cfg["agent_id"]]})
    time.sleep(2)


def run(scenarios, arms=ARMS, out=None, log=print):
    cfg = lab_config()
    js = JS7(cfg["url"], cfg["account"], cfg["password"])
    ensure_hosts(js, cfg)
    rows = []
    for n, sc in enumerate(scenarios):
        for arm_name, arm in arms.items():
            run_id = f"s{int(time.time()) % 100000}{n:02d}{len(rows) % 10}"
            emu = bench_req.run_one(sc, arm)["verdict"]
            t0 = time.time()
            repo = JS7Repo(js, cfg["controller_id"], sc, run_id)
            try:
                seeded = repo.jobs == bench_req.Repo(sc).jobs
                arm(repo, sc)
                row = {"scenario": sc["id"], "family": sc["family"], "arm": arm_name, "emulator": emu,
                       "js7": bench_req.verdict(sc, repo), "seed_identical": seeded, "js7_refused": repo.refused,
                       "seconds": round(time.time() - t0, 1)}
            finally:
                repo.cleanup()
            rows.append(row)
            log(f"{sc['id']:<20} {arm_name:<13} emulator={row['emulator']:<12} js7={row['js7']:<12} "
                f"{'AYNI' if row['emulator'] == row['js7'] else 'FARKLI'}"
                + (f"  JS7 reddetti: {row['js7_refused'][0][1][:90]}" if row["js7_refused"] else ""))
            if out:
                with pathlib.Path(out).open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
    js.logout()
    return rows


def main(argv=None):
    p = argparse.ArgumentParser(prog="vardiya.js7bench")
    p.add_argument("--per-family", type=int, default=1)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--families")
    p.add_argument("--arms", default=",".join(ARMS))
    p.add_argument("--out", default=str(ROOT / "results" / "js7.jsonl"))
    args = p.parse_args(argv)
    fams = tuple(args.families.split(",")) if args.families else sabgen.FAMILIES
    rows = run(sabgen.generate(args.per_family, args.seed, fams), {a: ARMS[a] for a in args.arms.split(",")}, args.out)
    same = sum(r["emulator"] == r["js7"] for r in rows)
    print(f"\nayni hukum: {same}/{len(rows)}; baslangic tanimlari birebir: {sum(r['seed_identical'] for r in rows)}/{len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
