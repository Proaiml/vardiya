"""The consistency gate, without a model: does it leave correct readings alone, and what would it stop?

For every phrase with a known calendar, the true rule must not be vetoed (a veto there costs a
correct answer). For every phrase no calendar provides, each rule that WOULD match a site calendar
is tried: the gate should veto all of them (that is the false green it exists to stop).

    python scripts/veto_check.py dev | test | ext
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from vardiya import gunler, sabgen  # noqa: E402

split = sys.argv[1] if len(sys.argv) > 1 else "dev"
if split.endswith(".json"):  # raw output of scripts/write_phrases.py
    import json
    data = json.loads(pathlib.Path(split).read_text(encoding="utf-8"))["phrases"]
    phrases = {k: v["items"] for k, v in data.items() if not k.startswith("-")}
    traps = [p for k, v in data.items() if k.startswith("-") for p in v["items"]]
else:
    phrases, traps = sabgen.phrase_sets(split)
rules = {n: r for n, (r, _) in sabgen.CALENDARS.items()}

gate = lambda p, r: gunler.contradicts(p, r) or gunler.unsupported(p, r)
lost = [(c, p, gate(p, rules[c])) for c, ps in phrases.items() for p in ps if gate(p, rules[c])]
total = sum(len(ps) for ps in phrases.values())
print(f"{split}: dogru okuma {total} ifade, kapinin yanlislikla durdurdugu: {len(lost)}")
for c, p, why in lost:
    print(f"   {c:<16} {p[:60]:<60} {why}")

open_doors = [(p, n) for p in traps for n, r in rules.items() if gate(p, r) is None]
print(f"{split}: tuzak {len(traps)} ifade x {len(rules)} takvim = {len(traps) * len(rules)} yanlis okuma; "
      f"kapinin durdurmadigi: {len(open_doors)}")
by_phrase = {}
for p, n in open_doors:
    by_phrase.setdefault(p, []).append(n)
for p, ns in by_phrase.items():
    print(f"   {p[:60]:<60} -> {', '.join(ns)}")
