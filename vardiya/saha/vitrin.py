"""Intervention showcase: a short, readable Turkish record of every Usta episode, built from the evidence files
alone (no model calls), with what the unaided model did on the same scenario next to it.

    python -m vardiya.saha.vitrin belge test-gpt-oss zor-dev-gpt-oss ...   # writes docs/13-mudahale-gunlugu.md
    python -m vardiya.saha.vitrin liste test-gpt-oss                        # one line per episode

The web console serves the same records (`/api/saha/vitrin`, `/api/saha/vitrin/kayit`).
"""
import json
import pathlib
import re
import sys

from .kosu import HUKUMLER, OUT, ozet

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
HUKUM_AD = {"dogru": "doğru", "yarim": "yarım", "yanlis": "yanlış", "sahte_yesil": "sahte yeşil", "zararli": "zararlı",
            "kurulamadi": "kurulamadı"}
AILE_AD = {"ariza": "Arıza", "tanim": "Tanım", "yonetim": "Yönetim"}
TUR_AD = {"aft": "Dosya aktarımı", "os": "Komut / betik", "db": "Veritabanı", "karma": "Karma"}
SAYAC_AD = {"red": "reddedilen yıkıcı komut", "onay_istendi": "ikinci çağrı istenen riskli komut", "onucus_red": "ön uçuşta durdurulan dağıtım",
            "onucus_uyari": "ön uçuş uyarısı", "kart": "gösterilen beceri kartı", "takip": "harness'in beklediği sonuç",
            "dongu": "döngü uyarısı", "bitis_red": "geri çevrilen bitiş", "elestiri": "denetçi çağrısı", "kabul": "kabul listesi"}


def _oku(ad, senaryo, kol):
    p = OUT / ad / f"{senaryo}__{kol}.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None


def _komut(x):
    g = x.get("girdi") or {}
    if x["arac"] == "sh":
        return f"sh {g.get('sunucu', '?')}: {g.get('komut', '')}"
    if g.get("json") is not None:
        body = g["json"]
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except ValueError:
                body = {}
        adlar = ", ".join(body.keys()) if isinstance(body, dict) else ""
        return f"ctm {g.get('komut', '')} ({adlar})"
    return f"ctm {g.get('komut', '')}"


def _isaret(x):
    c = str(x.get("cikti", ""))
    if c.startswith("USTA REDDETTI"):
        return "reddedildi"
    if c.startswith("USTA DURDURDU"):
        return "ikinci çağrı istendi"
    if c.startswith("USTA ON UCUS"):
        return "ön uçuşta durduruldu"
    if not x.get("uygulandi", True):
        return "uygulanmadı"
    if x.get("rc"):
        return f"çıkış {x['rc']}"
    return ""


def _kontrol_metni(c):
    k = c.get("kontrol")
    g = c.get("gorulen")
    return {"kontrol": json.dumps(k, ensure_ascii=False)[:220], "gorulen": (g if isinstance(g, str) else json.dumps(g, ensure_ascii=False))[:220],
            "tutar": bool(c.get("tutar"))}


def kayit(ad, senaryo, kol="usta", karsi="yalin"):
    """The readable record of one episode, with the other arm's episode of the same scenario next to it."""
    d = _oku(ad, senaryo, kol)
    if d is None:
        return None
    eylemler = [{"n": x["n"], "komut": _komut(x)[:300], "isaret": _isaret(x),
                 "ozet": next((ln for ln in str(x.get("cikti", "")).splitlines() if ln.strip() and not ln.startswith("[cikis kodu")), "")[:200]}
                for x in d.get("iz", [])]
    isler = [{"is": f"{j['folder']}/{j['name']}", "durum": j.get("status"), "kosu": j.get("numberOfRuns"),
              "son": [ln for ln in str(j.get("cikti", "")).splitlines() if ln.strip()][-3:]}
             for j in d.get("isler", []) if "folder" in j]
    u = d.get("usta") or {}
    rec = {"ad": ad, "senaryo": senaryo, "kol": kol, "model": d.get("model"), "aile": d.get("aile"), "tur": d.get("tur"),
           "bilesik": d.get("bilesik"), "talep": d.get("talep"), "kok_neden": d.get("kok_neden"), "hukum": d.get("hukum"),
           "tutan": d.get("tutan"), "toplam": d.get("toplam"), "adim": d.get("adim"), "saniye": d.get("saniye"),
           "bitis": d.get("bitis"), "rapor": d.get("rapor", ""), "kartlar": u.get("kartlar", []),
           "harness": {SAYAC_AD.get(k, k): v for k, v in (u.get("sayac") or {}).items() if v and k != "yoklama"},
           "bitis_notlari": u.get("bitis_notlari", []), "eylemler": eylemler,
           "kontroller": [_kontrol_metni(c) for c in d.get("kontroller", [])],
           "zarar": [_kontrol_metni(c) for c in d.get("zarar", [])], "isler": isler}
    o = _oku(ad, senaryo, karsi)
    if o is not None:
        rec["karsi"] = {"kol": karsi, "hukum": o.get("hukum"), "adim": o.get("adim"), "saniye": o.get("saniye"),
                        "tutan": o.get("tutan"), "toplam": o.get("toplam"),
                        "tutmayan": [_kontrol_metni(c) for c in o.get("kontroller", []) if not c.get("tutar")][:4],
                        "zarar": [_kontrol_metni(c) for c in o.get("zarar", []) if c.get("tutar")][:4],
                        "eylem_sayisi": len(o.get("iz", []))}
    return rec


def liste(ad, kol="usta", karsi="yalin"):
    """One row per scenario of a run that has the given arm: verdicts of both arms, steps, family, type."""
    rows = ozet(ad)
    out = []
    for (s, k), r in sorted(rows.items()):
        if k != kol:
            continue
        o = rows.get((s, karsi), {})
        out.append({"ad": ad, "senaryo": s, "aile": r.get("aile"), "tur": r.get("tur"), "bilesik": r.get("bilesik"),
                    "hukum": r["hukum"], "adim": r.get("adim"), "saniye": r.get("saniye"),
                    "karsi_hukum": o.get("hukum"), "karsi_adim": o.get("adim"),
                    "fark": r["hukum"] == "dogru" and o.get("hukum") in HUKUMLER and o.get("hukum") != "dogru",
                    "geri": o.get("hukum") == "dogru" and r["hukum"] in HUKUMLER and r["hukum"] != "dogru"})
    return out


def secim(adlar, n=20):
    """By rule: every case where the arms differ in verdict (Usta better first, then worse), then the compound cases
    with the most Usta steps, until n."""
    rows = [r for ad in adlar for r in liste(ad) if r["hukum"] in HUKUMLER and r["karsi_hukum"] in HUKUMLER]
    farkli = [r for r in rows if r["hukum"] != r["karsi_hukum"]]
    farkli.sort(key=lambda r: (0 if r["fark"] else 1 if r["geri"] else 2, r["ad"], r["senaryo"]))
    kalan = sorted([r for r in rows if r not in farkli and r["bilesik"]], key=lambda r: -(r["adim"] or 0))
    return (farkli + kalan)[:n]


def markdown(rec):
    h = HUKUM_AD.get(rec["hukum"], rec["hukum"])
    lines = [f"### {rec['senaryo']} ({rec['ad']})", "",
             f"{AILE_AD.get(rec['aile'], rec['aile'])}, {TUR_AD.get(rec['tur'], rec['tur'])}, {'bileşik' if rec['bilesik'] else 'tek nedenli'}; "
             f"model `{rec['model']}`.", "",
             f"**Talep.** {rec['talep']}", ""]
    if rec.get("kok_neden"):
        lines += [f"**Kök neden (senaryodan; ajana gösterilmez).** {rec['kok_neden']}", ""]
    k = rec.get("karsi")
    if k:
        lines += [f"**Sonuç.** Usta: {h}, {rec['tutan']}/{rec['toplam']} kontrol, {rec['adim']} adım, {rec['saniye']:.0f} sn. "
                  f"Araçlı model (yalnız erişim katmanı): {HUKUM_AD.get(k['hukum'], k['hukum'])}, {k['tutan']}/{k['toplam']} kontrol, {k['adim']} adım.", ""]
    else:
        lines += [f"**Sonuç.** Usta: {h}, {rec['tutan']}/{rec['toplam']} kontrol, {rec['adim']} adım.", ""]
    if rec["kartlar"] or rec["harness"]:
        lines += ["**Harness'in gördüğü ve yaptığı.** " + ("Kartlar: " + ", ".join(rec["kartlar"]) + ". " if rec["kartlar"] else "")
                  + "; ".join(f"{v} {k}" for k, v in rec["harness"].items()) + ".", ""]
    for notlar in rec["bitis_notlari"]:
        lines += ["- Bitiş geri çevrildi: " + " / ".join(str(n)[:200] for n in notlar)]
    if rec["bitis_notlari"]:
        lines.append("")
    lines += ["**Usta'nın eylemleri.**", ""]
    for e in rec["eylemler"]:
        lines.append(f"{e['n']}. `{e['komut'][:160]}`" + (f" ({e['isaret']})" if e["isaret"] else "") + (f": {e['ozet'][:120]}" if e["ozet"] else ""))
    lines += ["", "**Kanıt (bölüm sonunda sunuculardan okunan).**", ""]
    for c in rec["kontroller"]:
        lines.append(f"- {'tutuyor' if c['tutar'] else 'TUTMUYOR'}: `{c['kontrol'][:150]}` görülen: `{c['gorulen'][:100]}`")
    for c in rec["zarar"]:
        if c["tutar"]:
            lines.append(f"- ZARAR: `{c['kontrol'][:150]}` görülen: `{c['gorulen'][:100]}`")
    if k and (k["tutmayan"] or k["zarar"]):
        lines += ["", "**Araçlı modelde tutmayan ya da zarar veren kontroller.**", ""]
        lines += [f"- tutmuyor: `{c['kontrol'][:150]}` görülen: `{c['gorulen'][:100]}`" for c in k["tutmayan"]]
        lines += [f"- ZARAR: `{c['kontrol'][:150]}` görülen: `{c['gorulen'][:100]}`" for c in k["zarar"]]
    return "\n".join(lines) + "\n"


def belge(adlar, n=20, yol=None):
    yol = yol or ROOT / "docs" / "13-mudahale-gunlugu.md"
    secilen = secim(adlar, n)
    farkli = sum(1 for r in secilen if r["hukum"] != r["karsi_hukum"])
    head = ["# Müdahale günlüğü", "",
            "Bu belge kanıt dosyalarından betikle üretilir (`python -m vardiya.saha.vitrin belge " + " ".join(adlar) + "`); model çağrısı "
            "yoktur. Her kayıt bir Usta bölümüdür: talep, harness'in gördüğü, sırasıyla yapılan eylemler (reddedilen ve ikinci çağrı istenenler "
            "işaretli), bölüm sonunda sunuculardan okunan kanıt ve aynı senaryoda araçlı modelin (yalnız erişim katmanı: aynı araçlar ve el kitabı, harness yok) sonucu.", "",
            f"Seçim kuralı: önce iki kolun hükmünün farklı olduğu bütün bölümler (önce Usta'nın doğru, araçlı modelin doğru olmadığı, sonra tersi), sonra "
            f"bileşik senaryolardan en çok adım sürenler; en çok {n} kayıt. Bu seçimde hükmü farklı olan: {farkli}.", "",
            "Koşular: " + ", ".join(f"`{a}`" for a in adlar) + ". Ham kanıt: `results/saha/<koşu>/<senaryo>__<kol>.json` ve web "
            "konsolundaki \"Canlı saha\" ile \"Müdahale vitrini\" sayfaları.", "",
            "| # | Koşu | Senaryo | Usta | Araçlı model | Usta adım | Araçlı adım |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for i, r in enumerate(secilen, 1):
        head.append(f"| {i} | {r['ad']} | `{r['senaryo']}` | {HUKUM_AD.get(r['hukum'])} | {HUKUM_AD.get(r['karsi_hukum'])} | {r['adim']} | {r['karsi_adim']} |")
    body = [markdown(kayit(r["ad"], r["senaryo"])) for r in secilen]
    pathlib.Path(yol).write_text("\n".join(head) + "\n\n" + "\n".join(body), encoding="utf-8")
    return yol, len(secilen)


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv:
        print(__doc__)
        return 2
    cmd, adlar = argv[0], argv[1:]
    if cmd == "belge":
        yol, n = belge(adlar)
        print(f"{yol}: {n} kayit")
    elif cmd == "liste":
        for ad in adlar:
            for r in liste(ad):
                print(f"{ad:<22} {r['senaryo']:<36} usta={r['hukum']:<11} yalin={str(r['karsi_hukum']):<11} adim {r['adim']}/{r['karsi_adim']}"
                      + ("  << fark" if r["fark"] else "") + ("  >> geri" if r["geri"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
