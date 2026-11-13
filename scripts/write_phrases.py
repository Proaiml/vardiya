"""A third phrase set, written by a different author: a local model.

The tuning and test phrase sets in sabgen.py were both written by the same hand that wrote the
lexicon. This asks a model to write run-day phrases for each meaning, so the lexicon (and any
strategy) can be measured on wording its author never saw.

    python scripts/write_phrases.py ollama:gemma4:latest results/phrases-model.json
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from vardiya.gateway import connect  # noqa: E402

MEANINGS = {
    "HERGUN": "haftanın yedi günü, hafta sonları ve resmi tatiller de dahil olmak üzere her gün",
    "IS_GUNU": "pazartesiden cumaya her gün, resmi tatil günleri hariç (yani iş günleri)",
    "HAFTA_SONU": "yalnızca cumartesi ve pazar günleri",
    "PAZARTESI": "her hafta yalnızca pazartesi günü, o gün tatil olsa bile",
    "AY_SONU_IS_GUNU": "her ayın son iş günü",
    "AY_BASI_IS_GUNU": "her ayın ilk iş günü",
    "AYIN_15I": "her ayın 15'i; 15'i hafta sonuna ya da resmi tatile denk gelirse ondan sonraki ilk iş günü",
    "-1": "her ayın ilk pazartesi günü",
    "-2": "iki haftada bir, cuma günü",
    "-3": "üç ayda bir, çeyreğin son günü",
    "-4": "yalnızca salı ve perşembe günleri",
    "-5": "her ayın 10'u (tatil olsa da o gün)",
    "-6": "çarşamba dışında hafta içi her gün",
    "-7": "her ayın son cuma günü",
}
PROMPT = (
    "Bir bankada ekipler, toplu işlerin hangi günlerde çalışacağını bir talep formunun 'günler' alanına kendi "
    "cümleleriyle yazıyor. Aşağıdaki anlamı taşıyan {n} FARKLI kısa ifade yaz. Her biri gerçek bir çalışanın "
    "yazacağı gibi olsun: farklı kelimeler, farklı uzunluklar, bazıları resmi bazıları gündelik. Anlamı "
    "değiştirme, eksiltme ya da genişletme; başka bilgi (saat gibi) ekleme.\n\nAnlam: {meaning}\n\n"
    'Yalnızca JSON döndür: {{"ifadeler": ["...", "..."]}}')


def main():
    spec, out = sys.argv[1], pathlib.Path(sys.argv[2])
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    model = connect(spec, timeout=300)
    result = {"author": spec, "phrases": {}}
    for key, meaning in MEANINGS.items():
        got = model.ask_json([{"role": "user", "content": PROMPT.format(n=n, meaning=meaning)}]) or {}
        phrases = [p.strip() for p in got.get("ifadeler", []) if isinstance(p, str) and p.strip()]
        result["phrases"][key] = {"meaning": meaning, "items": list(dict.fromkeys(phrases))}
        print(key, len(phrases), flush=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
