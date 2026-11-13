"""How well does the deterministic run-day lexicon do on a phrase set? No model involved.

    python scripts/lexicon_check.py dev
    python scripts/lexicon_check.py test
"""
import datetime
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from vardiya import gunler, sabgen  # noqa: E402
from vardiya.repo import run_dates  # noqa: E402

split = sys.argv[1] if len(sys.argv) > 1 else "dev"
if split.endswith(".json"):  # a phrase file written by scripts/write_phrases.py; keys starting with "-" are traps
    import json
    data = json.loads(pathlib.Path(split).read_text(encoding="utf-8"))["phrases"]
    phrases = {k: v["items"] for k, v in data.items() if not k.startswith("-")}
    traps = [p for k, v in data.items() if k.startswith("-") for p in v["items"]]
else:
    phrases, traps = ((sabgen.PHRASES_TEST, sabgen.NO_CALENDAR_TEST) if split == "test"
                      else (sabgen.PHRASES, sabgen.NO_CALENDAR))
today = datetime.date(2026, 11, 13)


def dates(rule):
    return run_dates(rule, sabgen.HOLIDAYS, today, 400)


def calendar_of(phrase):
    rule = gunler.parse(phrase)
    if rule is None:
        return "-", None
    same = [n for n, (r, _) in sabgen.CALENDARS.items() if dates(r) == dates(rule)]
    return rule, (same[0] if len(same) == 1 else None)


right = wrong = passed_on = 0
for want, phrase in [(c, p) for c, ps in phrases.items() for p in ps] + [(None, p) for p in traps]:
    rule, got = calendar_of(phrase)
    if rule == "-":
        passed_on += 1
        mark = ".. "
    elif got == want:
        right += 1
        mark = "OK "
    else:
        wrong += 1
        mark = "XX "
    if "-v" in sys.argv or mark == "XX ":
        print(f"{mark}{str(want):<16} {phrase:<58} {rule}")
total = right + wrong + passed_on
print(f"{split}: {total} ifade | kodla dogru karar: {right} | kodla YANLIS karar: {wrong} | anlasilmadi, modele kaldi: {passed_on}")
