"""Have a different author rewrite the free-text descriptions of the description-conflict scenarios.

The generator writes descriptions from fixed templates ("saat 11:00'de baslar; db01 sunucusunda
calisir"). A reader tuned on those may only have learned the templates. This asks a local model to
say the same facts in its own words, so the reading can be measured on wording nobody tuned on.

    python scripts/write_descriptions.py ollama:gemma4:latest scenarios/talep/_aciklamalar-gemma4.json 30 5

Facts code can check (clock times, server names, job names) must survive the rewrite literally;
a rewrite that loses or adds one is retried, then dropped.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from vardiya import sabgen  # noqa: E402
from vardiya.gateway import connect  # noqa: E402

PROMPT = (
    "Bir bankada bir ekip, toplu iş tanımlama formunun 'açıklama' alanını dolduruyor. Aşağıdaki bilgilerin hepsini "
    "içeren, gerçek bir çalışanın yazacağı gibi doğal bir açıklama yaz (bir ya da iki cümle). Kendi kelimelerini kullan, "
    "madde madde yazma. Bilgilerin anlamını değiştirme, bilgi ekleme, bilgi çıkarma. Saatleri, sunucu adlarını ve iş "
    "adlarını (büyük harfli, alt çizgili adlar) harfi harfine aynen yaz.\n\nBilgiler:\n{facts}\n\n"
    'Yalnızca JSON döndür: {{"aciklama": "..."}}')
CLOCK = re.compile(r"(?<!\d)([01]?\d|2[0-3])[:.]([0-5]\d)(?!\d)")


def literals(text, sc):
    times = sorted({f"{int(h):02d}:{m}" for h, m in CLOCK.findall(text)})
    hosts = sorted(h for h in sc["env"]["hosts"] if re.search(rf"(?<!\w){re.escape(h)}(?!\w)", text, re.I))
    jobs = sorted(j["name"] for j in sc["jobs"] if re.search(rf"(?<!\w){re.escape(j['name'])}(?!\w)", text))
    return times, hosts, jobs


def main():
    spec, out = sys.argv[1], pathlib.Path(sys.argv[2])
    per_family, seed = int(sys.argv[3]), int(sys.argv[4])
    model = connect(spec, timeout=300)
    result = {"author": spec, "per_family": per_family, "seed": seed, "descriptions": {}, "dropped": []}
    for sc in sabgen.generate(per_family, seed, ("aciklamali", "t-celiski")):
        original = next(x.split(": ", 1)[1] for x in sc["request"]["text"].splitlines() if x.startswith("aciklama:"))
        purpose, *statements = original.split("; ")
        facts = "\n".join(f"- {s}" for s in [f"işin konusu: {purpose}"] + statements)
        for attempt in range(3):
            got = model.ask_json([{"role": "user", "content": PROMPT.format(facts=facts)}]) or {}
            text = " ".join(str(got.get("aciklama") or "").split())
            if len(text) > 15 and literals(text, sc) == literals(original, sc) and ";" not in text[:0]:
                result["descriptions"][sc["id"]] = text
                break
        else:
            result["dropped"].append(sc["id"])
        print(sc["id"], "ok" if sc["id"] in result["descriptions"] else "DUSTU", flush=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"yazilan: {len(result['descriptions'])}, dusen: {len(result['dropped'])}")


if __name__ == "__main__":
    main()
