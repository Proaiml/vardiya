"""Zamanlayici Ops Bench: real admin problems (forums, KB articles), three arms.

    ham      the model sees the case text only
    harness  the model also sees what the harness found: the matching incident class (cause, fix, harmful
             actions), the matching admin procedures and the policy; the harness drops any step that its own
             class marks as harmful before the answer is scored
    skill    no model: the matched skills' own text is the answer (how much the skills alone already cover)
    skill0, harness0   the same arms without the general server skills (skills/genel-yetenekler) and without
             solution chains: the ablation that shows what the product-independent OS skills add
    skillg, harnessg   with the general skills but without the solution chains (skills/cozum-zincirleri): what
             the order learned from correctly solved development cases adds
    skillc, harnessc   general skills and chains, without the graph model's first guess (vardiya/gnn.py); the plain
             skill and harness arms add that guess: what a fast trained pre-diagnosis adds for the language model
    usta     the agent's own protocol, two model calls: (1) the model drafts an answer with no help, exactly as in
             `ham`; (2) the harness hands back the draft with its review sheet (candidate causes, verified fixes,
             procedures, server checks, the order that solved similar cases) and the answer contract, and the model
             writes the final answer; (3) the harness moves harmful steps to `avoid` and restores every draft step
             the review neither kept nor explicitly dropped. The harness may add knowledge and remove harm; it may
             not silently lose what the model already knew, so the final answer is never thinner than the draft.
             Then two more harness steps: (4) the gate: an answer that does not meet the contract (too few steps,
             no command or parameter named, no verification, nothing to avoid) is returned once with the list of
             what is missing, as an incomplete request is returned at the request desk; (5) verified notes: for a
             cause the harness is sure of (two of its own signs, or the rule matcher and the graph model agreeing)
             it attaches that class's verified fix and read-only check under its own name.
    usta0    the same protocol with the answer contract and the gate only, no review sheet and no notes: what the
             protocol alone adds

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
from .skills import (fold, host_os, load_chains, load_general_skills, load_incident_classes, load_procedures, match_general,
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
          "fix of a likely class or a matching procedure; treat a possible (weak) class as a hint and drop it when the "
          "evidence points elsewhere; never recommend an action a likely class marks as harmful, and never force a "
          "job to OK.")


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


def class_signs(classes, text):
    """{class: the specific signs of that class found in the text}, for the classes that matched at all."""
    return {k: sorted(exact) for rank, k, exact in _ranked(classes, text)}


def strength(classes, text, found_classes):
    """How sure the harness is of each matched class: 'strong' when two or more of the class's own (non-generic)
    signs occur and no other class ranks the same, otherwise 'weak'. A weak match is handed over as a hint."""
    ranked = _ranked(classes, text)
    rank = {k: r for r, k, _ in ranked}
    top = ranked[0][0] if ranked else None
    tied = sum(1 for r, _, _ in ranked if r == top) > 1
    out = {}
    for k in found_classes:
        exact, specific, _ = rank[k]
        out[k] = "strong" if specific >= 2 and not (tied and rank[k] == top) else "weak"
    return out


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
            "systemd": ["systemd", "systemctl", "oncalendar", ".timer", ".service"], "rundeck": ["rundeck"],
            "gorev_zamanlayici": ["task scheduler", "gorev zamanlayici", "schtasks", "scheduled task", "zamanlanmis gorev"],
            "controlm": ["control-m", "ctm", "ccm", "user daily", "new day", " agent", "smart folder", "oscompstat", "zamanlayici sunucusu"]}


def product(text):
    """The scheduler the text talks about (most mentions), or None."""
    low = " " + fold(text) + " "
    best = max(((sum(low.count(w) for w in ws), p) for p, ws in PRODUCTS.items()), default=(0, None))
    return best[1] if best[0] else None


def general_text(g, os_name):
    """One general skill as the harness hands it over: the read-only check and the fix for the host's OS."""
    rows = [f"General server skill: {g['title']}"]
    if not os_name and g["check"]["unix"] == g["check"]["windows"]:
        os_name = "unix"  # a product-level skill: the same text for both, shown once
    for o in [os_name] if os_name else ["unix", "windows"]:
        if g["check"][o] and not g["check"][o].startswith("(uygulanmaz"):
            rows.append(f"Check on {o} (read-only): {g['check'][o]}")
            rows.append(f"Fix on {o}: {g['fix'][o]}")
    rows.append(f"Caution: {g['caution']}")
    return "\n".join(rows)


def ref_title(ref, classes, procedures, general):
    kind, name = ref.split(":", 1)
    src = {"genel": general, "yordam": procedures, "sinif": classes}[kind] or {}
    return src[name]["title"] if name in src else None


def ref_steps(ref, classes, procedures, general, os_name):
    """What applying a chain step means, in that skill's own words."""
    kind, name = ref.split(":", 1)
    if kind == "yordam" and name in procedures:
        return [procedures[name]["steps"]]
    if kind == "sinif" and name in classes:
        return [classes[name]["fix"]]
    if kind == "genel" and general and name in general:
        g = general[name]
        return [x for o in ([os_name] if os_name else ["unix", "windows"])
                if g["check"][o] and not g["check"][o].startswith("(uygulanmaz") for x in (g["check"][o],)]
    return []


def context(case, classes, procedures, general=None, chains=None, hint=None):
    """What the harness hands the model for this case, and what it found."""
    found_classes = match_classes(classes, case["prompt"])
    found = {"class": found_classes[0] if found_classes else None, "classes": found_classes,
             "procedures": match_procedures(procedures, case["prompt"]), "product": product(case["prompt"]),
             "general": match_general(general, case["prompt"], found_classes) if general else [],
             "os": host_os(case["prompt"]), "strength": strength(classes, case["prompt"], found_classes),
             "chain": [], "gnn": hint or {}}
    for name in found_classes:
        if chains and name in chains:
            found["chain"] = [r for r in chains[name]["order"] if ref_title(r, classes, procedures, general)]
            break
    signs = class_signs(classes, case["prompt"])
    agreed = {k for k, _ in (hint or {}).get("class", [])[:2]}
    for name in found_classes:
        if name in agreed:
            found["strength"][name] = "strong"  # two independent matchers agree
    parts = []
    if len(found_classes) > 1:
        parts.append("The evidence names more than one cause. Fix them in the order the evidence shows, rerun "
                     "after each fix, and check whether the second cause is still there.")
    for name in found_classes:
        c = classes[name]
        bad = ", ".join(a for a in c["harmful"]) or "none listed"
        own = c.get("fix_by", {}).get(found["product"])
        fix = f"In {found['product']}: {own}\nGeneral fix: {c['fix']}" if own else f"Verified fix: {c['fix']}"
        seen = ", ".join(signs.get(name) or []) or "partial wording match"
        if found["strength"][name] == "strong":
            head = f"Likely failure class: {c['title']} (signs found in the report: {seen})"
        else:
            head = (f"Possible failure class, weak match: {c['title']} (only sign found: {seen}). Use it only if the "
                    f"evidence fits; otherwise reason from the evidence")
        parts.append(f"{head}\nUsual cause: {c['cause']}\n{fix}\nHarmful in this class: {bad}")
    for name in found["procedures"]:
        p = procedures[name]
        parts.append(f"Admin procedure: {p['title']}\nSteps: {p['steps']}\nCaution: {p['caution']}")
    for name in found["general"]:
        parts.append(general_text(general[name], found["os"]))
    if hint and hint.get("class"):
        guess = ", ".join(f"{classes[k]['title'] if k in classes else k} ({p:.0%})" for k, p in hint["class"])
        row = f"Graph model first guess (trained on solved cases, can be wrong): root cause class: {guess}"
        if hint.get("skills"):
            row += "\nSkills it would start with: " + ", ".join(
                f"{ref_title(r, classes, procedures, general) or r}" for r, _ in hint["skills"])
        parts.insert(0, row)
    if found["chain"]:
        rows = [f"{i}. {ref_title(r, classes, procedures, general)} ({r})" for i, r in enumerate(found["chain"], 1)]
        parts.append("Order that solved similar cases (try the skills in this order, skip a step the evidence rules "
                     "out):\n" + "\n".join(rows))
    if not parts:
        parts.append("No known failure class or procedure matched; reason from the evidence only.")
    return "\n\n".join(parts + [POLICY]), found


def guard(answer, found, classes):
    """The harness's last word: steps that name an action the matched class marks harmful are moved to avoid."""
    if not found.get("class") or not isinstance(answer, dict):
        return answer
    # a likely class's harmful actions are moved out of the steps; a weak class only takes away forcing OK
    sure = found.get("strength") or {}
    words = [w for k in (found.get("classes") or [found["class"]])
             for a in (classes[k]["harmful"] if sure.get(k, "strong") == "strong" else ["set_ok"])
             for w in ACTION_WORDS.get(a, [])]
    keep, moved = [], []
    for s in answer.get("steps") or []:
        (moved if any(w in fold(s) for w in words) else keep).append(s)
    return {**answer, "steps": keep, "avoid": list(answer.get("avoid") or []) + moved}


def skill_answer(case, classes, procedures, general=None, chains=None, hint=None):
    _, found = context(case, classes, procedures, general, chains, hint)
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
                # without a model nothing confirms the diagnosis, so a general skill contributes its read-only
                # check only: its fix (kill a process, restart a service) is right only after the check agrees
                steps.append(g["check"][o])
    for ref in found["chain"]:
        steps += [x for x in ref_steps(ref, classes, procedures, general, found["os"]) if x not in steps]
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


CONTRACT = (
    "Final answer contract:" + "\n"
    "1. cause: the mechanism in one or two sentences; name the component, setting, limit or account involved. If two "
    "causes interact, name both and which one to fix first." + "\n"
    "2. steps, in the order you would do them: (a) how to confirm the cause, read-only, with the exact command, log, "
    "screen or query; (b) the fix in the product's own terms: the exact parameter, option, command or configuration key "
    "and where it lives; (c) the alternative when that fix is not possible; (d) restart or rerun, and how to verify it "
    "worked; (e) what keeps it from recurring." + "\n"
    "3. avoid: the shortcuts that look tempting in this situation." + "\n"
    "If the report describes expected behaviour and not a failure, say so plainly, name the check that confirms it and "
    "recommend no intervention.")
REVIEW_SCHEMA = ('Reply with one JSON object: {"cause": "...", "steps": ["...", ...], "avoid": ["...", ...], '
                 '"dropped": [{"step": "<a draft step you removed>", "why": "<reason>"}]}. No other text.')
USTA_ARMS = ("usta", "usta0")


def review_prompt(case, draft, sheet=None):
    """Stage 2 of the Usta protocol: the model's own draft comes back with the harness's review sheet."""
    rows = [case["prompt"], "", "Your draft answer (written without help):", json.dumps(draft, ensure_ascii=False)]
    if sheet:
        rows += ["", "Review sheet from the harness (candidates found by matching the report against solved cases and "
                     "runbooks; a candidate can be wrong):", sheet]
    rows += ["", "Now write the final answer.",
             '- Keep every step of your draft. You may remove a draft step only when it is wrong or harmful for this '
             'case; list each removed step under "dropped" with the reason.']
    if sheet:
        rows.append("- Add from the review sheet what applies to THIS report (the evidence in the report must support "
                    "it); ignore candidates that do not fit.")
    rows += ["- Complete the answer to the contract below; add the concrete commands, parameters and checks you left "
             "out of the draft.", "", CONTRACT, "", REVIEW_SCHEMA]
    return "\n".join(rows)


def _tokens(text):
    return set(re.findall(r"[a-z0-9_.%$/:-]{4,}", fold(str(text))))


def merge(draft, final, found, classes):
    """The harness's last word on a reviewed answer. A draft step that the final answer neither kept (60% of its
    words) nor listed under `dropped` is restored at the end, and a draft cause that the review rewrote away is kept
    beside the new one; then the guard moves harmful steps to `avoid`."""
    draft = draft if isinstance(draft, dict) else {}
    final = final if isinstance(final, dict) else {}
    steps = [str(x) for x in final.get("steps") or []]
    kept = _tokens(" ".join(steps + [str(final.get("cause", ""))]))
    gone = _tokens(" ".join(str(d.get("step", "")) if isinstance(d, dict) else str(d) for d in final.get("dropped") or []))
    restored = []
    for step in draft.get("steps") or []:
        words = _tokens(step)
        if words and len(words & kept) / len(words) < 0.6 and len(words & gone) / len(words) < 0.6:
            restored.append(str(step))
    # the same rule for the cause: a first assessment the review rewrote away stays on record beside the new one
    cause, first = str(final.get("cause") or ""), str(draft.get("cause") or "")
    words = _tokens(first)
    if not cause:
        cause = first
    elif words and len(words & kept) / len(words) < 0.6 and len(words & gone) / len(words) < 0.6:
        cause = f"{cause} (ilk degerlendirme: {first})"
    out = {"cause": cause, "steps": steps + restored,
           "avoid": list(final.get("avoid") or draft.get("avoid") or [])}
    if found:
        out = guard(out, found, classes)
    out["restored"] = len(restored)
    return out


TECH = re.compile(r"`|\b\w+_\w+\b|(?:^|\s)--?[A-Za-z][\w-]*|/[\w.-]+/[\w.-]+|\b[A-Za-z]:\\|\b\w+=\S+"
                  r"|\b[\w-]+\.(?:dat|conf|cfg|ini|xml|json|yaml|yml|log|sh|ps1|bat|py|properties|sql)\b|\b[A-Z][A-Z0-9_]{3,}\b"
                  r"|\b(?:systemctl|kubectl|journalctl|crontab|airflow|squeue|sacct|scontrol|sinfo|sbatch|autorep|sendevent|docker"
                  r"|openssl|keytool|curl|ssh|scp|sftp|grep|netstat|nslookup|icacls|schtasks|powershell|pwsh|chmod|chown|ulimit|sudo"
                  r"|kinit|klist|tnsping|sqlplus|psql|sqlcmd|ctm\w+|ecaqrtab)\b|\b(?:Get|Set|Test|Start|Stop|Restart|New|Invoke)-[A-Z]\w+")
VERIFY = re.compile(r"dogrula|verify|kontrol et|teyit|confirm|test et|yeniden calistir|rerun|re-run|izle|monitor|check that|sina")
CALM = re.compile(r"mudahale gerek|no intervention|beklenen davranis|expected behavio|normal davranis|sorun yok|not a failure|"
                  r"ariza degil|hata degil|not an error")
MISSING = {"steps": "fewer than four steps: cover every part of the contract (confirm, fix, alternative, restart and verify, prevent)",
           "command": "no exact command, parameter, option, file or screen is named",
           "verify": "no step says how to verify that the fix worked",
           "avoid": "nothing is listed under avoid"}


def gate(answer):
    """What a final answer lacks against the contract; an empty list passes. Deterministic, no model."""
    answer = answer if isinstance(answer, dict) else {}
    steps = [str(x) for x in answer.get("steps") or []]
    text = fold(" ".join(steps))
    calm = CALM.search(fold(str(answer.get("cause", ""))) + " " + text)  # "nothing is wrong" needs fewer steps
    out = []
    if len(steps) < (2 if calm else 4):
        out.append("steps")
    if not TECH.search(" ".join(steps)):
        out.append("command")
    if not calm and not VERIFY.search(text):
        out.append("verify")
    if not (answer.get("avoid") or []):
        out.append("avoid")
    return out


def return_prompt(case, answer, missing):
    """The gate's note back to the model: its own answer and what the contract still asks for."""
    shown = {k: answer.get(k) for k in ("cause", "steps", "avoid")}
    rows = [case["prompt"], "", "Your answer:", json.dumps(shown, ensure_ascii=False), "",
            "The harness returned this answer because it does not meet the answer contract:"]
    rows += [f"- {MISSING[m]}" for m in missing]
    rows += ["", "Complete it. Keep everything that is already there and add what is missing. Do not invent a command: "
             "when you are not sure of one, name the tool, log or screen instead.", "", CONTRACT, "", REVIEW_SCHEMA]
    return "\n".join(rows)


def verified_notes(case, found, classes, procedures, general):
    """What the harness adds under its own name, only where it is sure: the verified fix and the first read-only
    check of every strongly matched class, and a procedure three of whose triggers occur in the report."""
    if not found:
        return [], []
    steps, avoid = [], []
    for name in found.get("classes") or []:
        if (found.get("strength") or {}).get(name) != "strong":
            continue
        c = classes[name]
        own = c.get("fix_by", {}).get(found.get("product"))
        steps.append(f"Usta notu ({c['title']}, dogrulanmis duzeltme): {own + '; ' if own else ''}{c['fix']}")
        avoid += [f"{c['title']}: {ACTION_WORDS.get(a, [a])[0]}" for a in c["harmful"]]
        for g_name in found.get("general") or []:
            g = (general or {}).get(g_name)
            if g and name in g["classes"]:
                oses = [found["os"]] if found.get("os") else ["unix", "windows"]
                checks = [g["check"][o] for o in oses if not g["check"][o].startswith("(uygulanmaz")]
                if checks:
                    steps.append(f"Usta notu ({g['title']}, salt okuyan kontrol): {' | '.join(dict.fromkeys(checks))}")
                break
    for name in found.get("procedures") or []:
        pr = procedures[name]
        if sum(soft_in(t, case["prompt"]) for t in pr["triggers"]) >= 3:
            steps.append(f"Usta notu ({pr['title']}, yordam): {pr['steps']}")
    return steps, avoid


def attach(answer, case, found, classes, procedures, general):
    steps, avoid = verified_notes(case, found, classes, procedures, general)
    return {**answer, "steps": list(answer.get("steps") or []) + steps, "avoid": list(answer.get("avoid") or []) + avoid,
            "notes": len(steps)}


def ask_usta(model, case, sheet):
    draft = ask(model, case)
    final = model.ask_json([{"role": "system", "content": SYSTEM},
                            {"role": "user", "content": review_prompt(case, draft, sheet)}])
    return draft, final


def finish(case, draft, final, returned, found, classes, procedures, general, notes):
    """Stages 3 to 5 for one case: merge the review into the draft, merge the gate's second answer when there is one,
    then attach the verified notes (the `usta` arm only)."""
    answer = merge(draft, final, found, classes)
    restored = answer["restored"]
    if returned is not None:
        answer = merge(answer, returned, found, classes)
        restored += answer["restored"]
    if notes:
        answer = attach(answer, case, found, classes, procedures, general)
    answer["restored"] = restored
    return answer


SKILL_ARMS = ("skill", "skillc", "skillg", "skill0")
HARNESS_ARMS = ("harness", "harnessc", "harnessg", "harness0")


def arm_skills(arm, general, chains):
    """(general skills, chains) an arm may use: '0' neither, 'g' general only, 'c' and plain both."""
    if arm.endswith("0"):
        return {}, {}
    if arm.endswith("g"):
        return general, {}
    return general, chains


def uses_gnn(arm):
    return arm in ("skill", "harness", "usta")


def gnn_hints(split, arms):
    """{case id: first guess} from the graph model trained on the development split, for arms that use it."""
    if not any(uses_gnn(a) for a in arms):
        return {}
    from . import gnn  # needs numpy; only loaded when an arm uses the graph model
    model, cases = gnn.train(None if split == "dev" else split)
    ids = [c["id"] for c in (load("dev") if split == "dev" else cases)]
    return {i: model.predict(i) for i in ids}


def run(split, arms, model_spec=None, out=OUT, limit=None):
    classes, procedures, general = load_incident_classes(SKILLS), load_procedures(SKILLS), load_general_skills(SKILLS)
    chains = load_chains(SKILLS)
    hints = gnn_hints(split, arms)
    model = connect(model_spec) if model_spec else None
    done = set()
    if out.exists():
        keep = []
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["arm"] in SKILL_ARMS and r["split"] == split and r["arm"] in arms:
                continue  # the skill arm has no model and takes no time: always score it against the current skills
            keep.append(line)
            done.add((r["id"], r["arm"], r.get("model")))
        out.write_text("".join(x + "\n" for x in keep), encoding="utf-8")
    out.parent.mkdir(parents=True, exist_ok=True)
    for case in load(split)[:limit]:
        for arm in arms:
            key = (case["id"], arm, None if arm in SKILL_ARMS else model_spec)
            if key in done:
                continue
            t0, found = time.time(), None
            gen, ch = arm_skills(arm, general, chains)
            hint = hints.get(case["id"]) if uses_gnn(arm) else None
            if arm in SKILL_ARMS:
                answer, found = skill_answer(case, classes, procedures, gen, ch, hint)
            elif model is None:
                continue
            elif arm in USTA_ARMS:
                sheet = None
                if arm == "usta":
                    sheet, found = context(case, classes, procedures, general, chains, hint)
                draft, final = ask_usta(model, case, sheet)
                missing, returned = gate(merge(draft, final, found, classes)), None
                if missing:
                    returned = model.ask_json([{"role": "system", "content": SYSTEM}, {"role": "user", "content":
                                                return_prompt(case, merge(draft, final, found, classes), missing)}])
                answer = finish(case, draft, final, returned, found, classes, procedures, general, arm == "usta")
            elif arm == "ham":
                answer = ask(model, case)
            else:
                ctx, found = context(case, classes, procedures, gen, ch, hint)
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
    chains = load_chains(SKILLS)
    hints = gnn_hints(split, arms)
    rows = []
    # sorted by class, then dealt round-robin: every arm gets about the same number and mix of classes
    for i, case in enumerate(sorted(load(split), key=lambda c: (c["class"], c["id"]))):
        arm = arms[i % len(arms)] if seed_split else arms[0]
        if arm == "ham":
            ctx = None
        else:
            ctx, _ = context(case, classes, procedures, *arm_skills(arm, general, chains),
                             hints.get(case["id"]) if uses_gnn(arm) else None)
        user = case["prompt"] + ("\n\n" + ctx if ctx else "") + "\n\n" + SCHEMA
        rows.append({"id": case["id"], "arm": arm, "system": SYSTEM, "prompt": user})
    # arms in the order given: an agent answers every unaided case before it sees any harness text
    rows.sort(key=lambda r: arms.index(r["arm"]))
    pathlib.Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return collections.Counter(r["arm"] for r in rows)


def read_answers(path):
    rows = [json.loads(x) for x in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    return {r["id"]: r.get("answer") for r in rows if r.get("id")}


def export_review(split, drafts_path, path, arms=USTA_ARMS):
    """Stage 2 prompts for an outside model: every case with a draft gets its own draft back, with the review sheet
    (`usta`) or with the contract only (`usta0`). Cases are dealt to the arms after sorting by the draft's verdict
    and the incident class, so both arms start from the same mix of solved and unsolved drafts."""
    classes, procedures, general = load_incident_classes(SKILLS), load_procedures(SKILLS), load_general_skills(SKILLS)
    chains, drafts = load_chains(SKILLS), read_answers(drafts_path)
    hints = gnn_hints(split, arms)
    cases = [c for c in load(split) if c["id"] in drafts]
    cases.sort(key=lambda c: (score(c, drafts[c["id"]])[0], c["class"], c["id"]))
    rows = []
    for i, case in enumerate(cases):
        arm = arms[i % len(arms)]
        sheet = context(case, classes, procedures, general, chains, hints.get(case["id"]))[0] if arm == "usta" else None
        rows.append({"id": case["id"], "arm": arm, "system": SYSTEM,
                     "prompt": review_prompt(case, drafts[case["id"]], sheet)})
    rows.sort(key=lambda r: r["id"])  # the file order says nothing about the arm or the draft's verdict
    pathlib.Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return collections.Counter(r["arm"] for r in rows)


def export_return(split, drafts_path, finals_path, path):
    """Stage 3 prompts for an outside model: only the stage 2 answers the gate returns, each with what it lacks."""
    classes, procedures, general = load_incident_classes(SKILLS), load_procedures(SKILLS), load_general_skills(SKILLS)
    chains, drafts = load_chains(SKILLS), read_answers(drafts_path)
    finals = [json.loads(x) for x in pathlib.Path(finals_path).read_text(encoding="utf-8").splitlines() if x.strip()]
    hints = gnn_hints(split, ["usta"])
    cases = {c["id"]: c for c in load(split)}
    rows = []
    for a in finals:
        case, arm = cases.get(a.get("id")), a.get("arm")
        if not case or arm not in USTA_ARMS or case["id"] not in drafts:
            continue
        found = context(case, classes, procedures, general, chains, hints.get(case["id"]))[1] if arm == "usta" else None
        merged = merge(drafts[case["id"]], a.get("answer"), found, classes)
        missing = gate(merged)
        if missing:
            rows.append({"id": case["id"], "arm": arm, "system": SYSTEM, "prompt": return_prompt(case, merged, missing)})
    pathlib.Path(path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return {"returned": len(rows), "passed": len(finals) - len(rows)}


def ingest(split, path, label, out=OUT, drafts_path=None, returns_path=None):
    """Score answers an outside model wrote ({"id", "arm", "answer": {cause, steps, avoid}} per line).
    The harness arms get the same guard as in `run`."""
    classes, procedures, general = load_incident_classes(SKILLS), load_procedures(SKILLS), load_general_skills(SKILLS)
    chains = load_chains(SKILLS)
    drafts = read_answers(drafts_path) if drafts_path else {}
    returns = read_answers(returns_path) if returns_path else {}
    hints = gnn_hints(split, ["usta"]) if drafts_path else {}
    cases = {c["id"]: c for c in load(split)}
    n = 0
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        a = json.loads(line)
        case, arm, answer = cases.get(a.get("id")), a.get("arm"), a.get("answer")
        if not case or arm not in ("ham",) + HARNESS_ARMS + USTA_ARMS:
            continue
        found, extra = None, {}
        if arm in USTA_ARMS:
            draft = drafts.get(case["id"])
            if draft is None:
                continue
            if arm == "usta":
                _, found = context(case, classes, procedures, general, chains, hints.get(case["id"]))
            answer = finish(case, draft, answer, returns.get(case["id"]), found, classes, procedures, general, arm == "usta")
            extra = {"draft_verdict": score(case, draft)[0], "restored": answer.get("restored", 0),
                     "returned": case["id"] in returns, "notes": answer.get("notes", 0)}
        elif arm != "ham":
            _, found = context(case, classes, procedures, *arm_skills(arm, general, chains))
            answer = guard(answer, found, classes)
        verdict, hits = score(case, answer)
        row = {"id": case["id"], "split": split, "track": case["track"], "class": case["class"],
               "scheduler": case["scheduler"], "arm": arm, "model": label, "verdict": verdict, "hits": hits,
               "found": found, "answer": answer, "seconds": None, "version": __version__, **extra}
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


def paired(model, split=None, out=OUT):
    """Draft against final answer on the same cases, for the Usta arms of one model: what the protocol changed."""
    rows = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = [r for r in rows if r["arm"] in USTA_ARMS and r["model"] == model and split in (None, r["split"])]
    latest = {(r["id"], r["arm"]): r for r in rows}  # a later ingest of the same case replaces the earlier one
    lines = ["| Kol | Vaka | Taslak dogru | Son dogru | Duzelen | Bozulan | Taslak zararli | Son zararli | Geri konan adim |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for arm in USTA_ARMS:
        rs = [r for (_, a), r in latest.items() if a == arm]
        if not rs:
            continue
        d = [r["draft_verdict"] for r in rs]
        f = [r["verdict"] for r in rs]
        up = sum(a != "dogru" and b == "dogru" for a, b in zip(d, f))
        down = sum(a == "dogru" and b != "dogru" for a, b in zip(d, f))
        lines.append(f"| {arm} | {len(rs)} | {d.count('dogru')} | {f.count('dogru')} | {up} | {down} | "
                     f"{d.count('zararli')} | {f.count('zararli')} | {sum(r.get('restored', 0) for r in rs)} |")
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
    i.add_argument("--drafts", help="stage 1 answers; needed to score the usta arms")
    i.add_argument("--returns", help="stage 3 answers (the gate's returns), when there are any")
    i.add_argument("--out", default=str(OUT))
    v = sub.add_parser("export-review", help="stage 2 of the Usta protocol for an outside model")
    v.add_argument("--split", default="test")
    v.add_argument("--drafts", required=True)
    v.add_argument("--file", required=True)
    v.add_argument("--arms", default="usta,usta0")
    w = sub.add_parser("export-return", help="stage 3 of the Usta protocol: answers the gate returns")
    w.add_argument("--split", default="test")
    w.add_argument("--drafts", required=True)
    w.add_argument("--finals", required=True)
    w.add_argument("--file", required=True)
    q = sub.add_parser("paired", help="draft against final answer for the usta arms")
    q.add_argument("--model", required=True)
    q.add_argument("--split")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        run(a.split, a.arms.split(","), a.model, pathlib.Path(a.out), a.limit)
    elif a.cmd == "export":
        print(dict(export(a.split, a.arms.split(","), a.file)))
    elif a.cmd == "ingest":
        print(ingest(a.split, a.file, a.label, pathlib.Path(a.out), a.drafts, a.returns), "cevap puanlandi")
    elif a.cmd == "export-review":
        print(dict(export_review(a.split, a.drafts, a.file, tuple(a.arms.split(",")))))
    elif a.cmd == "export-return":
        print(export_return(a.split, a.drafts, a.finals, a.file))
    elif a.cmd == "paired":
        print(paired(a.model, a.split))
    else:
        print(report(pathlib.Path(a.out), a.split))
