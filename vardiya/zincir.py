"""Solution chains: the order in which a good solver applies skills, turned into a skill of its own.

A strong model that solves a case without help still follows a path: it checks something first (often at the OS
level), then applies a product procedure, then restarts and verifies. Here every step of a CORRECT answer on the
development split is mapped to an existing skill (a general server skill, an admin procedure or an incident class's
fix); the steps of all correct answers of one incident class are merged into one ordered chain; steps that map to
no skill are kept as gaps, the raw material for new skills. Chains are written to skills/cozum-zincirleri and the
harness hands the matching chain over as "try these skills in this order".

Only the development split is mined. Mining the test split would leak the exam into the skills.

    python -m vardiya.zincir mine --answers <cozumler.jsonl> --label kron-a1
"""
import argparse
import collections
import json
import pathlib
import re

from .skills import fold, load_general_skills, load_incident_classes, load_procedures, soft_in

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
OUT = SKILLS / "cozum-zincirleri" / "SKILL.md"
GAPS = ROOT / "results" / "zincir-bosluklar.jsonl"

WORD = re.compile(r"[a-z0-9_][a-z0-9_.%$:/-]{3,}")
COMMON = set("""bir ile icin veya olarak gibi sonra once daha kadar gore olan yeniden kontrol dogrula
check verify with from that this then when the and for into onto restart ayni yalniz gerekiyorsa
varsa yoksa degil dosya dosyasi sunucu agent isin isler isi job jobs file server host""".split())


def _words(text):
    return {w.strip(".:/") for w in WORD.findall(fold(text))} - COMMON


def skill_index(classes, procedures, general):
    """{ref: (title, triggers, rare words)}: what a step is compared against. A word is rare when at most three
    skills use it; commands (keytool, ctmagcfg, Get-WinEvent) are the typical rare words."""
    raw = {}
    for n, g in general.items():
        raw[f"genel:{n}"] = (g["title"], g["triggers"], " ".join([g["title"]] + list(g["check"].values()) + list(g["fix"].values())))
    for n, p in procedures.items():
        raw[f"yordam:{n}"] = (p["title"], p["triggers"], p["title"] + " " + p["steps"])
    for n, c in classes.items():
        raw[f"sinif:{n}"] = (c["title"], c["signs"], c["title"] + " " + c["fix"])
    seen = collections.Counter(w for _, _, text in raw.values() for w in _words(text))
    return {ref: (title, trig, {w for w in _words(text) if seen[w] <= 3}) for ref, (title, trig, text) in raw.items()}


def map_step(step, index):
    """The skill a step applies, or None: two trigger hits, or one trigger and one rare word, or two rare words."""
    words, best = _words(step), (0, None)
    for ref, (_, trig, rare) in index.items():
        score = 2 * sum(soft_in(t, step) for t in trig) + len(words & rare)
        if score > best[0]:
            best = (score, ref)
    return best[1] if best[0] >= 3 else None


def mine(answers, cases, index, min_share=0.3):
    """Chains per incident class from the correct answers, and the unmapped steps."""
    from .opsbench import score  # late import: opsbench imports skills, not this module
    per_class, gaps, used = collections.defaultdict(list), [], 0
    for a in answers:
        case = cases.get(a.get("id"))
        if not case or not isinstance(a.get("answer"), dict) or score(case, a["answer"])[0] != "dogru":
            continue
        used += 1
        chain = []
        for i, step in enumerate(a["answer"].get("steps") or []):
            ref = map_step(str(step), index)
            if ref is None:
                gaps.append({"id": case["id"], "class": case["class"], "step": str(step)})
            elif ref not in chain:
                chain.append(ref)
        if chain:
            per_class[case["class"]].append(chain)
    chains = {}
    for cls, lists in per_class.items():
        pos, count = collections.defaultdict(list), collections.Counter()
        for chain in lists:
            for i, ref in enumerate(chain):
                pos[ref].append(i / max(1, len(chain) - 1))
                count[ref] += 1
        # a step enters the chain only when at least two correct solutions took it; a class with no such step gets
        # no chain (one solution is an anecdote, not an order)
        keep = [r for r, c in count.items() if c >= 2 and c / len(lists) >= min_share]
        if keep:
            chains[cls] = {"order": sorted(keep, key=lambda r: sum(pos[r]) / len(pos[r]))[:5], "support": len(lists)}
    return chains, gaps, used


def write(chains, label, path=OUT):
    lines = ["---", "name: cozum-zincirleri",
             "description: Dogru cozulmus gelistirme vakalarindan cikarilan yetenek sirasi; her olay sinifi icin once hangi "
             "yetenegin, sonra hangisinin denenecegi.", "kind: solution_chains", "chains:"]
    for cls in sorted(chains):
        c = chains[cls]
        lines += [f"  {cls}:", f"    order: [{', '.join(c['order'])}]", f"    support: {c['support']}"]
    lines += ["---", "", "# Cozum zincirleri", "",
              f"Kaynak: `{label}` ajaninin yardimsiz ve dogru cozdugu gelistirme vakalari (`python -m vardiya.zincir mine`).",
              "Her adim mevcut bir yetenege eslendi; ayni siniftaki dogru cozumlerde en az iki kez ve cozumlerin en az "
              "%30'unda gecen yetenekler, cozumdeki ortalama konumlarina gore siralandi. Eslenemeyen adimlar "
              "`results/zincir-bosluklar.jsonl` dosyasinda; yeni yetenek adaylaridir.", "",
              "`genel:` genel sunucu yetenegi, `yordam:` adminlik yordami, `sinif:` olay sinifinin dogrulanmis duzeltmesi."]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vardiya.zincir")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mine")
    m.add_argument("--answers", required=True)
    m.add_argument("--label", required=True)
    a = ap.parse_args(argv)
    from .opsbench import load
    classes, procedures, general = load_incident_classes(SKILLS), load_procedures(SKILLS), load_general_skills(SKILLS)
    index = skill_index(classes, procedures, general)
    answers = [json.loads(x) for x in pathlib.Path(a.answers).read_text(encoding="utf-8").splitlines() if x.strip()]
    chains, gaps, used = mine(answers, {c["id"]: c for c in load("dev")}, index)
    write(chains, a.label)
    GAPS.parent.mkdir(parents=True, exist_ok=True)
    GAPS.write_text("".join(json.dumps(g, ensure_ascii=False) + "\n" for g in gaps), encoding="utf-8")
    print(f"{used} dogru cozum, {len(chains)} zincir, {len(gaps)} eslenemeyen adim")


if __name__ == "__main__":
    main()
