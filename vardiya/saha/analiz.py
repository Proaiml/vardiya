"""Reads live bench runs and prints the tables the report uses.

    python -m vardiya.saha.analiz dev-hydrogen-high dev-flash-low

Per run: verdicts by arm, the paired comparison of each arm against the unaided model on the same scenarios (wins,
losses, exact two-sided sign test), the breakdown by family, job type and single/compound, and the cost (steps,
seconds, tool calls). Episodes that could not be set up or were cut short by the model service are left out and
counted separately; a pair counts only when both arms have a verdict.
"""
import json
import math
import sys

from .kosu import HUKUMLER, OUT, ozet

KOL_AD = {"yalin": "Araçlı model (yalnız erişim katmanı)", "kart": "Model ve kart metni", "usta": "Usta", "bos": "Kimse dokunmadı", "referans": "Örnek çözüm"}
SIRA = ["yalin", "kart", "usta", "referans", "bos"]
AILE = {"ariza": "Arıza", "tanim": "Tanım", "yonetim": "Yönetim"}
TUR = {"aft": "Dosya aktarımı (AFT)", "os": "Komut / betik (EXC)", "db": "Veritabanı (DBJ)", "karma": "Karma"}


def isaret_testi(kazanc, kayip):
    """Exact two-sided sign test on the discordant pairs."""
    n = kazanc + kayip
    if n == 0:
        return 1.0
    k = min(kazanc, kayip)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def tablo(ad):
    rows = ozet(ad)
    gecerli = {k: r for k, r in rows.items() if r["hukum"] in HUKUMLER}
    kollar = sorted({k for _, k in gecerli}, key=lambda k: SIRA.index(k) if k in SIRA else 9)
    model = next((r.get("model") for r in gecerli.values() if r.get("model")), "")
    out = [f"### {ad}" + (f" (`{model}`)" if model else ""), "",
           "| Kol | Senaryo | Doğru | Yarım | Yanlış | Sahte yeşil | Zararlı | Ort. adım | Ort. süre |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for kol in kollar:
        rs = [r for (s, k), r in gecerli.items() if k == kol]
        n = len(rs)
        c = {h: sum(r["hukum"] == h for r in rs) for h in HUKUMLER}
        adim = [r["adim"] for r in rs if r.get("adim")]
        sn = [r["saniye"] for r in rs if r.get("saniye")]
        out.append(f"| {KOL_AD.get(kol, kol)} | {n} | **{c['dogru']}** (%{100 * c['dogru'] / n:.0f}) | {c['yarim']} | {c['yanlis']} | {c['sahte_yesil']} | {c['zararli']} | "
                   f"{sum(adim) / len(adim) if adim else 0:.1f} | {sum(sn) / len(sn) if sn else 0:.0f} sn |")
    atilan = sum(1 for r in rows.values() if r["hukum"] not in HUKUMLER)
    if atilan:
        out += ["", f"Hüküm dışı bırakılan bölüm: {atilan} (kurulamadı ya da model servisi kesti)."]
    if "yalin" in kollar:
        out += ["", "Aynı senaryolarda araçlı modele (yalnız erişim katmanı) karşı:", "",
                "| Kol | Çift | İkisi de doğru | Yalnız bu kol doğru | Yalnız araçlı model doğru | İkisi de değil | İşaret testi p |", "| --- | --- | --- | --- | --- | --- | --- |"]
        for kol in [k for k in kollar if k not in ("yalin", "bos", "referans")]:
            ids = sorted({s for s, k in gecerli if k == kol} & {s for s, k in gecerli if k == "yalin"})
            a = [gecerli[(s, kol)]["hukum"] == "dogru" for s in ids]
            b = [gecerli[(s, "yalin")]["hukum"] == "dogru" for s in ids]
            both, win, loss = sum(x and y for x, y in zip(a, b)), sum(x and not y for x, y in zip(a, b)), sum(y and not x for x, y in zip(a, b))
            out.append(f"| {KOL_AD.get(kol, kol)} | {len(ids)} | {both} | **{win}** | {loss} | {len(ids) - both - win - loss} | {isaret_testi(win, loss):.3f} |")
        for alan, adlar in (("aile", AILE), ("tur", TUR), ("bilesik", {False: "Tek nedenli", True: "Bileşik"})):
            out += ["", f"| {dict(aile='Aile', tur='İş tipi', bilesik='Neden sayısı')[alan]} | Senaryo | " + " | ".join(KOL_AD.get(k, k) for k in kollar) + " |",
                    "| --- | --- | " + "--- | " * len(kollar)]
            for deger, etiket in adlar.items():
                ids = sorted({s for (s, k), r in gecerli.items() if r.get(alan) == deger})
                if not ids:
                    continue
                cells = []
                for kol in kollar:
                    rs = [gecerli[(s, kol)] for s in ids if (s, kol) in gecerli]
                    cells.append(f"{sum(r['hukum'] == 'dogru' for r in rs)}/{len(rs)}" if rs else "-")
                out.append(f"| {etiket} | {len(ids)} | " + " | ".join(cells) + " |")
    # how fast: an episode counts as solved within k steps when its verdict is "dogru" and it finished in k steps or fewer
    ks = (6, 8, 10, 12, 15, 20, 40)
    ortak = sorted(set.intersection(*[{s for (s, k) in gecerli if k == kol} for kol in kollar])) if kollar else []
    if ortak and len(kollar) > 1:
        out += ["", f"Adım bütçesine göre çözülen senaryo ({len(ortak)} ortak senaryo; bölüm en çok k adımda doğru bitmişse sayılır):", "",
                "| Kol | " + " | ".join(f"k={k}" for k in ks) + " |", "| --- | " + "--- | " * len(ks)]
        for kol in kollar:
            rs = [gecerli[(s, kol)] for s in ortak]
            out.append(f"| {KOL_AD.get(kol, kol)} | " + " | ".join(str(sum(r["hukum"] == "dogru" and (r.get("adim") or 99) <= k for r in rs)) for k in ks) + " |")
    return "\n".join(out)


def senaryo_tablosu(ad):
    rows = {k: r for k, r in ozet(ad).items()}
    kollar = sorted({k for _, k in rows}, key=lambda k: SIRA.index(k) if k in SIRA else 9)
    out = ["| Senaryo | " + " | ".join(KOL_AD.get(k, k) for k in kollar) + " |", "| --- | " + "--- | " * len(kollar)]
    for s in sorted({s for s, _ in rows}):
        out.append(f"| `{s}` | " + " | ".join(rows.get((s, k), {}).get("hukum", "-").replace("_", " ") for k in kollar) + " |")
    return "\n".join(out)


def harness_sayaclari(ad):
    """What the harness did across the Usta episodes of a run: refusals, confirmations, pre-flight stops, gate returns."""
    total, n = {}, 0
    for path in sorted((OUT / ad).glob("*__usta.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        if d.get("hukum") not in HUKUMLER:
            continue
        n += 1
        for k, v in (d.get("usta") or {}).get("sayac", {}).items():
            total[k] = total.get(k, 0) + v
    return n, total


def butce_adi(ad):
    """The step budget a run was made with, read from its name (`...-b10` means 10 steps); 40 otherwise."""
    import re
    m = re.search(r"-b(\d+)$", ad)
    return int(m.group(1)) if m else 40


def butce_tablosu(adlar):
    """Correct episodes per arm under each step budget, on the scenarios every listed run has a verdict for in that arm."""
    rows = {ad: {k: r for k, r in ozet(ad).items() if r["hukum"] in HUKUMLER} for ad in adlar}
    kollar = sorted({k for g in rows.values() for _, k in g}, key=lambda k: SIRA.index(k) if k in SIRA else 9)
    out = ["| Koşu | Bütçe | " + " | ".join(KOL_AD.get(k, k) for k in kollar) + " |", "| --- | --- | " + "--- | " * len(kollar)]
    for ad in adlar:
        cells = []
        for kol in kollar:
            rs = [r for (s, k), r in rows[ad].items() if k == kol]
            if not rs:
                cells.append("-")
                continue
            d = sum(r["hukum"] == "dogru" for r in rs)
            cells.append(f"{d}/{len(rs)} (%{100 * d / len(rs):.0f})")
        out.append(f"| {ad} | {butce_adi(ad)} | " + " | ".join(cells) + " |")
    # paired: within each run, the arms on the same scenarios
    if "yalin" in kollar and "usta" in kollar:
        out += ["", "| Koşu | Çift | Yalnız Usta doğru | Yalnız araçlı model doğru | İşaret testi p |", "| --- | --- | --- | --- | --- |"]
        for ad in adlar:
            ids = sorted({s for s, k in rows[ad] if k == "usta"} & {s for s, k in rows[ad] if k == "yalin"})
            win = sum(rows[ad][(s, "usta")]["hukum"] == "dogru" and rows[ad][(s, "yalin")]["hukum"] != "dogru" for s in ids)
            loss = sum(rows[ad][(s, "yalin")]["hukum"] == "dogru" and rows[ad][(s, "usta")]["hukum"] != "dogru" for s in ids)
            out.append(f"| {ad} | {len(ids)} | **{win}** | {loss} | {isaret_testi(win, loss):.3f} |")
    return "\n".join(out)


def riskli_tablosu(ad):
    r = riskli_eylemler(ad)
    if not r:
        return ""
    kollar = sorted(r, key=lambda k: SIRA.index(k) if k in SIRA else 9)
    out = ["| Kol | Bölüm | Yıkıcı komut (uygulandı) | Riskli komut (uygulandı) | set to OK | Harness'in durdurduğu |", "| --- | --- | --- | --- | --- | --- |"]
    for k in kollar:
        g = r[k]
        out.append(f"| {KOL_AD.get(k, k)} | {g['bolum']} | {g['yikici']} | {g['riskli']} | {g['set_to_ok']} | {g['durdurulan']} |")
    ornek = [f"- {KOL_AD.get(k, k)}: {o}" for k in kollar for o in r[k]["ornek"][:3]]
    return "\n".join(out + ([""] + ornek if ornek else []))


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    if argv[:1] == ["--butce"]:
        print(butce_tablosu(argv[1:]))
        return 0
    for ad in argv:
        print(tablo(ad))
        n, t = harness_sayaclari(ad)
        if n:
            print(f"\nHarness, {n} Usta bölümünde: " + ", ".join(f"{k} {v}" for k, v in t.items() if v))
        print()
        print(senaryo_tablosu(ad))
        print()
        rt = riskli_tablosu(ad)
        if rt:
            print("Uygulanan riskli eylemler (harness'in kendi kalıplarıyla, her kolun izine aynı biçimde):\n")
            print(rt)
            print()
    return 0


def riskli_eylemler(ad):
    """Per arm: executed tool calls that match the harness guard's own lists (forbidden = destructive, risky = needs
    a second look), and what the guard stopped in the Usta arm. The same patterns are applied to every arm's trace."""
    import re

    from . import usta as u
    out = {}
    for path in sorted((OUT / ad).glob("*__*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        if d.get("hukum") not in HUKUMLER:
            continue
        g = out.setdefault(d["kol"], {"bolum": 0, "yikici": 0, "riskli": 0, "set_to_ok": 0, "durdurulan": 0, "ornek": []})
        g["bolum"] += 1
        for x in d.get("iz", []):
            text = str((x.get("girdi") or {}).get("komut", ""))
            if not x.get("uygulandi", True):
                # only the harness's own refusals count as stopped; a call the tool itself rejected is not
                g["durdurulan"] += str(x.get("cikti", "")).startswith("USTA")
                continue
            if x["arac"] == "sh" and any(re.search(p, text, re.I) for p, _ in u.FORBIDDEN):
                g["yikici"] += 1
                g["ornek"].append(f"{d['senaryo']}: {text[:110]}")
            elif any(re.search(p, text, re.I) for p, _ in u.RISKY):
                g["riskli"] += 1
            if x["arac"] == "ctm" and "setToOk" in text:
                g["set_to_ok"] += 1
    return out


if __name__ == "__main__":
    sys.exit(main())
