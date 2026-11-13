"""Scheduler Admin Bench (SAB): arms x scenarios, results on disk, a report anyone can regenerate.

    python -m vardiya sab run --per-family 4 --seed 1                       # scripted arms, no model
    python -m vardiya sab run --per-family 4 --seed 1 --model ollama:qwen3:8b
    python -m vardiya sab report

Runs are resumable: a cell already in the results file is skipped, and `--budget`
stops cleanly after that many seconds so a long run can be done in pieces.
Each row keeps the action trace, so every verdict can be replayed without a model.
"""
import argparse
import json
import math
import os
import pathlib
import socket
import time
import urllib.error

from . import __version__, bench_req, sabgen
from .desk import DEFAULT_STRATEGY
from .gateway import connect

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "results" / "sab.jsonl"
SCRIPTED = dict(bench_req.SCRIPTED)
LLM = {"raw_llm": bench_req.arm_raw_llm, "runbook_llm": bench_req.arm_runbook_llm, "harness_llm": bench_req.arm_harness}
VERDICTS = ("correct", "safe_fail", "false_green", "destructive")
ARM_TITLES = {"noop": "Hicbir sey yapma", "naive_apply": "Yazilani aynen uygula", "naive_return": "Hepsini iade et",
              "golden": "Referans cozum", "harness": "Harness'in kod payi", "raw_llm": "Ham model",
              "runbook_llm": "Ham model + runbook (plasebo)", "harness_llm": "Harness + model"}


def _key(r):
    return (r["arm"], r.get("model") or "", r.get("variant") or "", r["scenario"])


def load(path):
    p = pathlib.Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def run(scenarios, out, model_spec=None, arms=None, budget=None, base_url=None, variant=None, timeout=150):
    """Fill in missing cells. Returns (done_now, remaining)."""
    out = pathlib.Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    table = {**SCRIPTED, **(LLM if model_spec else {})}
    arms = [a for a in (arms or table) if a in table]
    variant = variant or DEFAULT_STRATEGY  # harness rows always say which strategy produced them
    have = {_key(r) for r in load(out)}
    # a reasoning model with and without its hidden "thinking" is two different contestants
    label = (model_spec or "") + ("+think" if model_spec and os.environ.get("VARDIYA_THINK") == "1" else "")
    todo = [(arm, sc) for arm in arms for sc in scenarios
            if (arm, label if arm in LLM else "", (variant or "") if arm.startswith("harness") else "", sc["id"]) not in have]
    started, done = time.time(), 0
    with out.open("a", encoding="utf-8") as f:
        for arm, sc in todo:
            if budget and time.time() - started > budget:
                break
            model = connect(model_spec, base_url=base_url, timeout=timeout) if arm in LLM else None
            t0 = time.time()
            try:
                r = bench_req.run_one(sc, table[arm], model=model, **({"strategy": variant} if variant and arm.startswith("harness") else {}))
            except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
                print(f"[altyapi hatasi, atlandi] {arm} {sc['id']}: {e}", flush=True)
                continue
            row = {"arm": arm, "model": label if arm in LLM else "", "scenario": sc["id"], "family": sc["family"],
                   "variant": (variant or "") if arm.startswith("harness") else "",
                   "verdict": r["verdict"], "actions": r["actions"], "replay_ok": r["replay_ok"], "hash": r["hash"],
                   "calls": model.calls if model else 0, "seconds": round(time.time() - t0, 1),
                   "version": __version__, "trace": r["trace"]}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            done += 1
    return done, len(todo) - done


# ---- report --------------------------------------------------------------------
def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p, d = k / n, 1 + z * z / n
    centre, half = p + z * z / (2 * n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - half) / d), min(1.0, (centre + half) / d)


def mcnemar_exact(b, c):
    """Two-sided exact test on the discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def _pct(k, n):
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.0f}% ({100 * lo:.0f}-{100 * hi:.0f})" if n else "-"


def balanced(rs):
    """Mean of the correct rate on requests that should be applied and on requests that should be
    returned. Most families are traps, so plain accuracy flatters an agent that refuses everything."""
    rates = []
    for want_applied in (True, False):
        part = [r for r in rs if (r["family"] in sabgen.APPLIED) == want_applied]
        if part:
            rates.append(sum(r["verdict"] == "correct" for r in part) / len(part))
    return f"{100 * sum(rates) / len(rates):.0f}%" if rates else "-"


def _label(arm, model, variant):
    name = ARM_TITLES.get(arm, arm)
    if model:
        name += f" `{model.split(':', 1)[-1]}`"
    return name + (f" [{variant}]" if variant else "")


def report(rows):
    groups = {}
    for r in rows:
        groups.setdefault((r["arm"], r.get("model") or "", r.get("variant") or ""), []).append(r)
    order = sorted(groups, key=lambda g: (g[1], list({**SCRIPTED, **LLM}).index(g[0]) if g[0] in {**SCRIPTED, **LLM} else 99, g[2]))
    out = ["# Scheduler Admin Bench sonuclari", "",
           f"Satir sayisi: {len(rows)}. Yuzdelerin yanindaki aralik %95 Wilson guven araligidir.",
           "Dengeli dogru: uygulanmasi gereken ve iade edilmesi gereken taleplerdeki dogru oranlarinin ortalamasi.", "",
           "## Genel", "",
           "| Kol | n | Dogru | Dengeli dogru | Guvenli basarisizlik | Sahte yesil | Yikici | Zararli toplam | Model cagrisi | Sure (sn) |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for g in order:
        rs, n = groups[g], len(groups[g])
        c = {v: sum(r["verdict"] == v for r in rs) for v in VERDICTS}
        harmful = c["false_green"] + c["destructive"]
        out.append(f"| {_label(*g)} | {n} | {_pct(c['correct'], n)} | {balanced(rs)} | {100 * c['safe_fail'] / n:.0f}% | "
                   f"{100 * c['false_green'] / n:.0f}% | {100 * c['destructive'] / n:.0f}% | {_pct(harmful, n)} | "
                   f"{sum(r['calls'] for r in rs) / n:.1f} | {sum(r['seconds'] for r in rs) / n:.1f} |")

    fams = [f for f in sabgen.FAMILIES if any(r["family"] == f for r in rows)]
    out += ["", "## Aileye gore dogru orani", "", "| Kol | " + " | ".join(fams) + " |", "| --- |" + " --- |" * len(fams)]
    for g in order:
        cells = []
        for fam in fams:
            rs = [r for r in groups[g] if r["family"] == fam]
            cells.append(f"{sum(r['verdict'] == 'correct' for r in rs)}/{len(rs)}" if rs else "-")
        out.append(f"| {_label(*g)} | " + " | ".join(cells) + " |")

    pairs = []
    for model in sorted({g[1] for g in groups if g[1]}):
        base = {r["scenario"]: r for r in groups.get(("raw_llm", model, ""), [])}
        for g in order:
            if g[1] != model or g[0] == "raw_llm":
                continue
            other = {r["scenario"]: r for r in groups[g]}
            both = sorted(set(base) & set(other))
            if not both:
                continue
            win = sum(other[s]["verdict"] == "correct" and base[s]["verdict"] != "correct" for s in both)
            loss = sum(other[s]["verdict"] != "correct" and base[s]["verdict"] == "correct" for s in both)
            bad = lambda r: r["verdict"] in bench_req.HARMFUL
            fixed = sum(bad(base[s]) and not bad(other[s]) for s in both)
            broke = sum(not bad(base[s]) and bad(other[s]) for s in both)
            pairs.append(f"| {_label(*g)} | {len(both)} | {win} | {loss} | {mcnemar_exact(win, loss):.3f} | {fixed} | {broke} | "
                         f"{mcnemar_exact(fixed, broke):.3f} |")
    if pairs:
        out += ["", "## Ayni senaryolarda ham modele karsi (eslestirilmis)", "",
                "| Kol | Ortak senaryo | Ham yanlis, bu dogru | Ham dogru, bu yanlis | p (dogruluk) | Zarari giderdi | Zarar ekledi | p (zarar) |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |"] + pairs
        out += ["", "p degerleri uyumsuz ciftler uzerinde iki yonlu kesin McNemar testidir."]
    bad_replay = sum(not r["replay_ok"] for r in rows)
    out += ["", f"Yeniden oynatma: {len(rows) - bad_replay}/{len(rows)} iz ayni durum ozetine ulasti."]
    return "\n".join(out) + "\n"


def main(argv=None):
    p = argparse.ArgumentParser(prog="vardiya sab")
    p.add_argument("cmd", choices=["run", "report", "list"])
    p.add_argument("--per-family", type=int, default=4)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--families", help="virgulle ayrilmis aile adlari")
    p.add_argument("--split", choices=["dev", "test", "ext", "ext2"], default="dev",
                   help="serbest yazilmis gun ifadeleri: dev = ayar kumesi, test = ayri tutulan kume, "
                        "ext = baska bir yazarin (yerel bir modelin) yazdigi kume")
    p.add_argument("--descriptions", help="aciklamalari baska bir yazarin yazdigi dosya (scripts/write_descriptions.py)")
    p.add_argument("--model")
    p.add_argument("--base-url")
    p.add_argument("--arms", help="virgulle ayrilmis kol adlari")
    p.add_argument("--variant", help="harness kollari icin strateji etiketi")
    p.add_argument("--budget", type=float, help="saniye; dolunca temiz cikis")
    p.add_argument("--out", default=str(DEFAULT_OUT))
    p.add_argument("--md", help="raporu bu dosyaya da yaz")
    p.add_argument("--think", action="store_true", help="akil yuruten modellerde gizli dusunmeyi ac (cok yavas)")
    args = p.parse_args(argv)
    if args.think:
        os.environ["VARDIYA_THINK"] = "1"

    families = tuple(args.families.split(",")) if args.families else sabgen.FAMILIES
    scenarios = sabgen.generate(args.per_family, args.seed, families, args.split)
    if args.descriptions:
        scenarios = sabgen.rewritten(scenarios, args.descriptions)
    if args.cmd == "list":
        for sc in scenarios:
            print(f"{sc['id']:<22} {sc['expected']['outcome']:<9} {sc['title']}")
        return 0
    if args.cmd == "run":
        done, left = run(scenarios, args.out, args.model, args.arms.split(",") if args.arms else None,
                         args.budget, args.base_url, args.variant)
        print(f"tamamlanan hucre: {done}, kalan: {left}, dosya: {args.out}")
        return 3 if left else 0
    text = report(load(args.out))
    if args.md:
        pathlib.Path(args.md).write_text(text, encoding="utf-8")
    print(text)
    return 0
