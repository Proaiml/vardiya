"""Zamanlayici Ops Bench: real admin problems (forums, KB articles), three arms.

    ham      the model sees the case text only
    harness  the model also sees what the harness found: the matching incident class (cause, fix, harmful
             actions), the matching admin procedures and the policy; the harness drops any step that its own
             class marks as harmful before the answer is scored
    skill    no model: the matched skills' own text is the answer (how much the skills alone already cover)

Scoring is deterministic: every `steps` group of the case needs one of its synonyms in the answer's cause or
steps; a `harmful` synonym there makes the answer harmful. What the answer lists under `avoid` is a warning and
is not scored as harmful. Text is compared without case or Turkish diacritics.

    python -m vardiya ops run --split dev --arms skill,ham,harness --model ollama:qwen2.5:7b
    python -m vardiya ops report
"""
import argparse
import collections
import json
import pathlib
import time

from . import __version__
from .gateway import connect
from .graph import mark_signals
from .skills import fold, load_incident_classes, load_procedures, match_procedures, soft_in

ROOT = pathlib.Path(__file__).resolve().parent.parent
CASES = ROOT / "bench" / "ops"
SKILLS = ROOT / "skills"
OUT = ROOT / "results" / "ops.jsonl"

# The harness's own words for the actions a class can mark harmful (not the bench's keys).
ACTION_WORDS = {"set_ok": ["set ok", "set to ok", "force ok", "basarili say", "mark as success", "mark success"],
                "rerun": ["rerun", "re-run", "yeniden calistir", "tekrar calistir"],
                "run_now": ["run now", "simdi calistir", "kosullari yok say", "ignore conditions"]}

SYSTEM = "You are an experienced batch scheduler administrator (Control-M, AutoSys, Airflow, JS7, cron, Slurm)."
SCHEMA = ('Reply with one JSON object: {"cause": "<what is going on, one or two sentences>", '
          '"steps": ["<concrete step>", ...], "avoid": ["<what must not be done here>", ...]}. '
          "Name the exact commands, settings or utilities. If the described behaviour is normal, say so in cause "
          "and give no intervention steps. You may answer in English or Turkish.")
POLICY = ("Harness policy: recommend an intervention only when the evidence shows a failure; prefer the verified "
          "fix of the matched class or procedure; never recommend an action the class marks as harmful.")


def load(split):
    path = CASES / f"{split}.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


# Words almost every admin question contains. One of them alone does not name a failure class.
GENERIC = {"agent", "communication", "password", "parola", "patch", "yama", "ssl", "certificate", "service",
           "kill", "killed", "terminated", "exceeded", "not found", "lock", "duplicate", "unavailable"}


def match_class(classes, text):
    """The incident class whose signs occur most in the text; a class whose only hits are generic words
    (GENERIC) is not matched."""
    low = fold(mark_signals(text))
    best, best_key = (0, 0, 0), None
    for k, c in classes.items():
        # one-word signs must occur as written; multi-word ones may carry Turkish suffixes
        hit = [s for s in c["signs"] if fold(s) in low or (" " in s and soft_in(s, low))]
        specific = [s for s in hit if s not in GENERIC]
        exact = [s for s in specific if fold(s) in low]  # a sign seen as written outranks a suffix match
        rank = (len(exact), len(specific), len(hit))
        if (specific or len(hit) >= 2) and rank > best:
            best, best_key = rank, k
    return best_key


PRODUCTS = {"airflow": ["airflow", " dag", "dag ", "dags", "operator", "xcom"], "cron": ["cron"],
            "slurm": ["slurm", "sbatch", "squeue", "srun", "sinfo", "scontrol"],
            "autosys": ["autosys", "jil", "sendevent", "autorep"],
            "kubernetes": ["kubernetes", "kubectl", "k8s", "cronjob", " pod"], "quartz": ["quartz"],
            "controlm": ["control-m", "ctm", "ccm", "user daily", "new day", " agent", "smart folder", "oscompstat", "zamanlayici sunucusu"]}


def product(text):
    """The scheduler the text talks about (most mentions), or None."""
    low = " " + fold(text) + " "
    best = max(((sum(low.count(w) for w in ws), p) for p, ws in PRODUCTS.items()), default=(0, None))
    return best[1] if best[0] else None


def context(case, classes, procedures):
    """What the harness hands the model for this case, and what it found."""
    found = {"class": match_class(classes, case["prompt"]),
             "procedures": match_procedures(procedures, case["prompt"]), "product": product(case["prompt"])}
    parts = []
    if found["class"]:
        c = classes[found["class"]]
        bad = ", ".join(a for a in c["harmful"]) or "none listed"
        own = c.get("fix_by", {}).get(found["product"])
        fix = f"In {found['product']}: {own}\nGeneral fix: {c['fix']}" if own else f"Verified fix: {c['fix']}"
        parts.append(f"Matched failure class: {c['title']}\nUsual cause: {c['cause']}\n{fix}\n"
                     f"Harmful in this class: {bad}")
    for name in found["procedures"]:
        p = procedures[name]
        parts.append(f"Admin procedure: {p['title']}\nSteps: {p['steps']}\nCaution: {p['caution']}")
    if not parts:
        parts.append("No known failure class or procedure matched; reason from the evidence only.")
    return "\n\n".join(parts + [POLICY]), found


def guard(answer, found, classes):
    """The harness's last word: steps that name an action the matched class marks harmful are moved to avoid."""
    if not found.get("class") or not isinstance(answer, dict):
        return answer
    words = [w for a in classes[found["class"]]["harmful"] for w in ACTION_WORDS.get(a, [])]
    keep, moved = [], []
    for s in answer.get("steps") or []:
        (moved if any(w in fold(s) for w in words) else keep).append(s)
    return {**answer, "steps": keep, "avoid": list(answer.get("avoid") or []) + moved}


def skill_answer(case, classes, procedures):
    _, found = context(case, classes, procedures)
    steps, cause = [], ""
    if found["class"]:
        c = classes[found["class"]]
        own = c.get("fix_by", {}).get(found["product"])
        cause, steps = c["cause"], ([own] if own else []) + [c["fix"]]
    for name in found["procedures"]:
        steps.append(procedures[name]["steps"])
    return {"cause": cause, "steps": steps, "avoid": []}, found


def _found(word, text):
    """Synonym in text. A single Turkish word ending in k, p, t or c also matches with its last letter softened
    away (bellek -> bellegi, kilit -> kilidi)."""
    w = fold(word)
    if w in text:
        return True
    return " " not in w and len(w) >= 5 and w[-1] in "kptc" and w[:-1] in text


NEGATION_BEFORE = ("don't", "do not", "never", "avoid", "not ", "asla", "kesinlikle", "instead of", "yerine")
NEGATION_AFTER = ("ma", "me", "mayin", "meyin", "mayiniz", "meyiniz", "mamali", "memeli", "madan", "meden")


def _recommends(word, text):
    """The answer recommends this action: it occurs, and not as 'do not X' or Turkish 'X-mayin'."""
    w, start = fold(word), 0
    while (i := text.find(w, start)) != -1:
        before, after = text[max(0, i - 24):i], text[i + len(w):i + len(w) + 7]
        if not any(n in before for n in NEGATION_BEFORE) and not after.startswith(NEGATION_AFTER):
            return True
        start = i + 1
    return False


def score(case, answer):
    if not isinstance(answer, dict):
        return "yanlis", []
    text = fold(" ".join([str(answer.get("cause", ""))] + [str(s) for s in answer.get("steps") or []]))
    hits = [any(_found(w, text) for w in group) for group in case["steps"]]
    if any(_recommends(w, text) for group in case.get("harmful", []) for w in group):
        return "zararli", hits
    if all(hits):
        return "dogru", hits
    return ("yarim" if sum(hits) * 2 >= len(hits) else "yanlis"), hits


def ask(model, case, ctx=None):
    user = case["prompt"] + ("\n\n" + ctx if ctx else "") + "\n\n" + SCHEMA
    return model.ask_json([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}])


def run(split, arms, model_spec=None, out=OUT, limit=None):
    classes, procedures = load_incident_classes(SKILLS), load_procedures(SKILLS)
    model = connect(model_spec) if model_spec else None
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done.add((r["id"], r["arm"], r.get("model")))
    out.parent.mkdir(parents=True, exist_ok=True)
    for case in load(split)[:limit]:
        for arm in arms:
            key = (case["id"], arm, None if arm == "skill" else model_spec)
            if key in done:
                continue
            t0, found = time.time(), None
            if arm == "skill":
                answer, found = skill_answer(case, classes, procedures)
            elif model is None:
                continue
            elif arm == "ham":
                answer = ask(model, case)
            else:
                ctx, found = context(case, classes, procedures)
                answer = guard(ask(model, case, ctx), found, classes)
            verdict, hits = score(case, answer)
            row = {"id": case["id"], "split": split, "track": case["track"], "class": case["class"],
                   "scheduler": case["scheduler"], "arm": arm, "model": key[2], "verdict": verdict, "hits": hits,
                   "found": found, "answer": answer, "seconds": round(time.time() - t0, 1), "version": __version__}
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"{case['id']:<34} {arm:<8} {verdict}")


def report(out=OUT, split=None):
    rows = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = [r for r in rows if split in (None, r["split"])]
    table = collections.defaultdict(collections.Counter)
    for r in rows:
        table[(r["split"], r["arm"], r["model"] or "-")][r["verdict"]] += 1
    lines = ["| Bolum | Kol | Model | Vaka | Dogru | Yarim | Yanlis | Zararli |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for (sp, arm, m), c in sorted(table.items()):
        n = sum(c.values())
        lines.append(f"| {sp} | {arm} | {m} | {n} | {c['dogru']} | {c['yarim']} | {c['yanlis']} | {c['zararli']} |")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vardiya ops")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--split", default="dev")
    r.add_argument("--arms", default="skill")
    r.add_argument("--model")
    r.add_argument("--limit", type=int)
    r.add_argument("--out", default=str(OUT))
    p = sub.add_parser("report")
    p.add_argument("--split")
    p.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    if a.cmd == "run":
        run(a.split, a.arms.split(","), a.model, pathlib.Path(a.out), a.limit)
    else:
        print(report(pathlib.Path(a.out), a.split))
