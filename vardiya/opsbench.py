"""Zamanlayici Ops Bench: real admin problems (forums, KB articles), three arms.

    ham      the model sees the case text only
    harness  the model also sees what the harness found: the matching incident class (cause, fix, harmful
             actions), the matching admin procedures and the policy; the harness drops any step that its own
             class marks as harmful before the answer is scored
    skill    no model: the matched skills' own text is the answer (how much the skills alone already cover)
    skill0, harness0   the same arms without the general server skills (skills/genel-yetenekler): the ablation
             that shows what the product-independent OS skills add

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
import re
import time

from . import __version__
from .gateway import connect
from .graph import mark_signals
from .skills import (fold, host_os, load_general_skills, load_incident_classes, load_procedures, match_general,
                     match_procedures, soft_in)

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


def _ranked(classes, text):
    """(rank, class, exact signs) for every class with a specific hit, best first."""
    low = fold(mark_signals(text))
    out = []
    for k, c in classes.items():
        # one-word signs must occur as written; multi-word ones may carry Turkish suffixes
        hit = [s for s in c["signs"] if fold(s) in low or (" " in s and soft_in(s, low))]
        specific = [s for s in hit if s not in GENERIC]
        exact = [s for s in specific if fold(s) in low]  # a sign seen as written outranks a suffix match
        if specific or len(hit) >= 2:
            out.append(((len(exact), len(specific), len(hit)), k, set(exact)))
    return sorted(out, key=lambda x: x[0], reverse=True)


def match_class(classes, text):
    """The incident class whose signs occur most in the text; a class whose only hits are generic words
    (GENERIC) is not matched."""
    r = _ranked(classes, text)
    return r[0][1] if r else None


def match_classes(classes, text, limit=2):
    """The main class and, when the text also carries a second cause's own exact signs (signs the first class
    does not share), that second class: compound incidents name two causes."""
    r = _ranked(classes, text)
    if not r:
        return []
    out, used = [r[0][1]], set(classes[r[0][1]]["signs"])
    for rank, k, exact in r[1:]:
        if len(out) >= limit:
            break
        if exact and exact - used:
            out.append(k)
            used |= set(classes[k]["signs"])
    return out


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


def general_text(g, os_name):
    """One general skill as the harness hands it over: the read-only check and the fix for the host's OS."""
    rows = [f"General server skill: {g['title']}"]
    for o in [os_name] if os_name else ["unix", "windows"]:
        if g["check"][o] and not g["check"][o].startswith("(uygulanmaz"):
            rows.append(f"Check on {o} (read-only): {g['check'][o]}")
            rows.append(f"Fix on {o}: {g['fix'][o]}")
    rows.append(f"Caution: {g['caution']}")
    return "\n".join(rows)


def context(case, classes, procedures, general=None):
    """What the harness hands the model for this case, and what it found."""
    found_classes = match_classes(classes, case["prompt"])
    found = {"class": found_classes[0] if found_classes else None, "classes": found_classes,
             "procedures": match_procedures(procedures, case["prompt"]), "product": product(case["prompt"]),
             "general": match_general(general, case["prompt"], found_classes) if general else [],
             "os": host_os(case["prompt"])}
    parts = []
    if len(found_classes) > 1:
        parts.append("The evidence names more than one cause. Fix them in the order the evidence shows, rerun "
                     "after each fix, and check whether the second cause is still there.")
    for name in found_classes:
        c = classes[name]
        bad = ", ".join(a for a in c["harmful"]) or "none listed"
        own = c.get("fix_by", {}).get(found["product"])
        fix = f"In {found['product']}: {own}\nGeneral fix: {c['fix']}" if own else f"Verified fix: {c['fix']}"
        parts.append(f"Matched failure class: {c['title']}\nUsual cause: {c['cause']}\n{fix}\n"
                     f"Harmful in this class: {bad}")
    for name in found["procedures"]:
        p = procedures[name]
        parts.append(f"Admin procedure: {p['title']}\nSteps: {p['steps']}\nCaution: {p['caution']}")
    for name in found["general"]:
        parts.append(general_text(general[name], found["os"]))
    if not parts:
        parts.append("No known failure class or procedure matched; reason from the evidence only.")
    return "\n\n".join(parts + [POLICY]), found


def guard(answer, found, classes):
    """The harness's last word: steps that name an action the matched class marks harmful are moved to avoid."""
    if not found.get("class") or not isinstance(answer, dict):
        return answer
    words = [w for k in (found.get("classes") or [found["class"]]) for a in classes[k]["harmful"]
             for w in ACTION_WORDS.get(a, [])]
    keep, moved = [], []
    for s in answer.get("steps") or []:
        (moved if any(w in fold(s) for w in words) else keep).append(s)
    return {**answer, "steps": keep, "avoid": list(answer.get("avoid") or []) + moved}


def skill_answer(case, classes, procedures, general=None):
    _, found = context(case, classes, procedures, general)
    steps, causes = [], []
    for name in found.get("classes") or []:
        c = classes[name]
        own = c.get("fix_by", {}).get(found["product"])
        causes.append(c["cause"])
        steps += ([own] if own else []) + [c["fix"]]
    cause = " / ".join(causes)
    for name in found["procedures"]:
        steps.append(procedures[name]["steps"])
    for name in found["general"]:
        g = general[name]
        for o in [found["os"]] if found["os"] else ["unix", "windows"]:
            if g["check"][o] and not g["check"][o].startswith("(uygulanmaz"):
                steps += [g["check"][o], g["fix"][o]]
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
        clause = re.split(r"[;.!?]", text[i + len(w):], maxsplit=1)[0]
        later = re.search(r"\b(etme|yapma|kullanma|silme|verme|koyma|alma|degildir|degil|yanlis|zararli|yasak)\b", clause)
        if not any(n in before for n in NEGATION_BEFORE) and not after.startswith(NEGATION_AFTER) and not later:
            return True
        start = i + 1
    return False


def score(case, answer):
    if not isinstance(answer, dict):
        return "yanlis", []
    text = fold(" ".join([str(answer.get("cause", ""))] + [str(s) for s in answer.get("steps") or []]))
    acts = fold(" ".join(str(s) for s in answer.get("steps") or []))
    hits = [any(_found(w, text) for w in group) for group in case["steps"]]
    # harm is judged on what the answer tells the operator to do, not on how it describes what happened
    if any(_recommends(w, acts) for group in case.get("harmful", []) for w in group):
        return "zararli", hits
    if all(hits):
        return "dogru", hits
    return ("yarim" if sum(hits) * 2 >= len(hits) else "yanlis"), hits


def ask(model, case, ctx=None):
    user = case["prompt"] + ("\n\n" + ctx if ctx else "") + "\n\n" + SCHEMA
    return model.ask_json([{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}])


def run(split, arms, model_spec=None, out=OUT, limit=None):
    classes, procedures, general = load_incident_classes(SKILLS), load_procedures(SKILLS), load_general_skills(SKILLS)
    model = connect(model_spec) if model_spec else None
    done = set()
    if out.exists():
        keep = []
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["arm"] in ("skill", "skill0") and r["split"] == split and r["arm"] in arms:
                continue  # the skill arm has no model and takes no time: always score it against the current skills
            keep.append(line)
            done.add((r["id"], r["arm"], r.get("model")))
        out.write_text("".join(x + "\n" for x in keep), encoding="utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    for case in load(split)[:limit]:
        for arm in arms:
            key = (case["id"], arm, None if arm in ("skill", "skill0") else model_spec)
            if key in done:
                continue
            t0, found = time.time(), None
            gen = {} if arm.endswith("0") else general
            if arm in ("skill", "skill0"):
                answer, found = skill_answer(case, classes, procedures, gen)
            elif model is None:
                continue
            elif arm == "ham":
                answer = ask(model, case)
            else:
                ctx, found = context(case, classes, procedures, gen)
                answer = guard(ask(model, case, ctx), found, classes)
            verdict, hits = score(case, answer)
            row = {"id": case["id"], "split": split, "track": case["track"], "class": case["class"],
                   "scheduler": case["scheduler"], "arm": arm, "model": key[2], "verdict": verdict, "hits": hits,
                   "found": found, "answer": answer, "seconds": round(time.time() - t0, 1), "version": __version__}
            with out.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            print(f"{case['id']:<34} {arm:<8} {verdict}")


def export(split, arms, path, seed_split=True):
    """Prompts for an outside model (an agent that answers from a file instead of an API).

    Each case goes to ONE arm only (alternating inside each incident class), so an agent never sees the same
    case twice with and without help. The file carries the prompt the arm would send, never the expected steps."""
    classes, procedures, general = load_incident_classes(SKILLS), load_procedures(SKILLS), load_general_skills(SKILLS)
    rows = []
    # sorted by class, then dealt round-robin: every arm gets about the same number and mix of classes
    for i, case in enumerate(sorted(load(split), key=lambda c: (c["class"], c["id"]))):
        arm = arms[i % len(arms)] if seed_split else arms[0]
        if arm == "ham":
            ctx = None
        else:
            ctx, _ = context(case, classes, procedures, {} if arm.endswith("0") else general)
        user = case["prompt"] + ("\n\n" + ctx if ctx else "") + "\n\n" + SCHEMA
        rows.append({"id": case["id"], "arm": arm, "system": SYSTEM, "prompt": user})
    # arms in the order given: an agent answers every unaided case before it sees any harness text
    rows.sort(key=lambda r: arms.index(r["arm"]))
    pathlib.Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return collections.Counter(r["arm"] for r in rows)


def ingest(split, path, label, out=OUT):
    """Score answers an outside model wrote ({"id", "arm", "answer": {cause, steps, avoid}} per line).
    The harness arms get the same guard as in `run`."""
    classes, procedures, general = load_incident_classes(SKILLS), load_procedures(SKILLS), load_general_skills(SKILLS)
    cases = {c["id"]: c for c in load(split)}
    n = 0
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        a = json.loads(line)
        case, arm, answer = cases.get(a.get("id")), a.get("arm"), a.get("answer")
        if not case or arm not in ("ham", "harness", "harness0"):
            continue
        found = None
        if arm != "ham":
            _, found = context(case, classes, procedures, {} if arm == "harness0" else general)
            answer = guard(answer, found, classes)
        verdict, hits = score(case, answer)
        row = {"id": case["id"], "split": split, "track": case["track"], "class": case["class"],
               "scheduler": case["scheduler"], "arm": arm, "model": label, "verdict": verdict, "hits": hits,
               "found": found, "answer": answer, "seconds": None, "version": __version__}
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        n += 1
    return n


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
    e = sub.add_parser("export", help="prompts for an outside model, one arm per case")
    e.add_argument("--split", default="test")
    e.add_argument("--arms", default="harness,harness0")
    e.add_argument("--file", required=True)
    i = sub.add_parser("ingest", help="score an outside model's answers")
    i.add_argument("--split", default="test")
    i.add_argument("--file", required=True)
    i.add_argument("--label", required=True)
    i.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    if a.cmd == "run":
        run(a.split, a.arms.split(","), a.model, pathlib.Path(a.out), a.limit)
    elif a.cmd == "export":
        print(dict(export(a.split, a.arms.split(","), a.file)))
    elif a.cmd == "ingest":
        print(ingest(a.split, a.file, a.label, pathlib.Path(a.out)), "cevap puanlandi")
    else:
        print(report(pathlib.Path(a.out), a.split))
