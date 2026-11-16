"""Runs live scenarios and keeps the evidence.

    python -m vardiya.saha.kosu dogrula --split dev            # every scenario: doing nothing must fail, the reference must pass
    python -m vardiya.saha.kosu kos --split dev --kollar yalin,usta --model agy:gemini-4-hydrogen-low --ad h-low
    python -m vardiya.saha.kosu rapor --ad h-low

Arms: bos (nobody touches the site), referans (the scenario's own scripted solution), yalin (bare model),
kart (model + skill cards as text), usta (model inside the harness).

Every episode writes results/saha/<ad>/<senaryo>__<kol>.json: the ticket, each tool call with its real output, the
final report, each check with what was observed on the hosts, and the verdict.
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import sys
import time

from ..gateway import connect
from . import ajan, ortam
from .araclar import Araclar
from .ctm import Ctm
from .lab import Lab
from .senaryo import Saha, dogrula_bicim, yukle

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "results" / "saha"
HUKUMLER = ("dogru", "yarim", "yanlis", "sahte_yesil", "zararli")


def _jobid(ctm, ref):
    folder, _, job = ref.partition("/")
    rows = [x for x in ctm.status(folder=folder, job=job)["statuses"] if x["folder"] == folder and x["name"] == job]
    if not rows:
        raise RuntimeError(f"referans cozum: aktif is yok: {ref}")
    return rows[-1]["jobId"]


def referans(lab, ctm, araclar, senaryo):
    """Play the scenario's scripted solution through the same tools the agent has."""
    for step in senaryo.get("cozum", []):
        if "bekle" in step:
            w = step["bekle"]
            if isinstance(w, (int, float)):
                time.sleep(w)
                continue
            deadline, last = time.time() + w.get("sure", 90), None
            while time.time() < deadline:
                rows = [x for x in ctm.status(folder=w["folder"], job=w["job"])["statuses"]
                        if x["folder"] == w["folder"] and x["name"] == w["job"]]
                last = rows[-1]["status"] if rows else None
                if last == w["durum"]:
                    break
                time.sleep(1.5)
            else:
                raise RuntimeError(f"referans cozum: {w['folder']}/{w['job']} {w['durum']} olmadi (son: {last})")
            continue
        text = json.dumps(step, ensure_ascii=False)
        text = re.sub(r"\{jobid:([^}]+)\}", lambda m: _jobid(ctm, m.group(1)), text)
        araclar.cagir(json.loads(text))
    return senaryo.get("cozum_rapor", "Referans cozum uygulandi; sorun giderildi ve dogrulandi.")


def bolum(lab, ctm, senaryo, kol, model_spec=None, gunluk=None, max_adim=ajan.MAX_ADIM):
    """One episode: reset the site, set the scene, let the arm work, judge the end state."""
    t0 = time.time()
    kayit = {"senaryo": senaryo["id"], "kol": kol, "model": model_spec, "aile": senaryo.get("aile"), "tur": senaryo.get("tur"),
             "bilesik": bool(senaryo.get("bilesik")), "zaman": datetime.datetime.now().isoformat(timespec="seconds")}
    try:
        kayit["sifirlama_sn"] = ortam.sifirla(lab, ctm)
        saha = Saha(lab, ctm, senaryo)
        saha.kur()
        kayit["kurulum"] = saha.kurulum_izi
    except Exception as e:  # noqa: BLE001 - a scene that cannot be set is an infrastructure failure, not a verdict
        kayit.update({"hukum": "kurulamadi", "hata": f"{type(e).__name__}: {str(e)[:500]}"})
        return kayit
    araclar = Araclar(lab, ctm, senaryo.get("dis_sunucu", ()))
    rapor, kos = "", {}
    try:
        if kol == "bos":
            rapor = ""
        elif kol == "referans":
            rapor = referans(lab, ctm, araclar, senaryo)
        else:
            from . import usta as usta_mod
            model = connect(model_spec)
            u = usta_mod.Usta(araclar, senaryo["talep"], elestirmen=connect(model_spec)) if kol == "usta" else None
            ek = usta_mod.kart_metni() if kol == "kart" else ""
            kos = ajan.kos(model, araclar, senaryo["talep"], usta=u, ek_baglam=ek, gunluk=gunluk, max_adim=max_adim)
            rapor = kos.pop("rapor")
            if u is not None:
                kayit["usta"] = u.ozet()
    except Exception as e:  # noqa: BLE001
        kayit["hata"] = f"{type(e).__name__}: {str(e)[:500]}"
    time.sleep(2)
    h = saha.hukum(araclar.iz, rapor)
    isler = []
    try:                      # what the scheduler itself recorded: the proof that jobs really ran
        for r in ctm.status()["statuses"]:
            isler.append({**{k: r[k] for k in ("jobId", "folder", "name", "type", "host", "status", "numberOfRuns")},
                          "cikti": ctm.output(r["jobId"], tail=40)[-2500:]})
    except Exception as e:  # noqa: BLE001
        isler.append({"hata": str(e)[:200]})
    mesajlar = kos.pop("mesajlar", [])
    if str(kos.get("bitis", "")).startswith("model_hatasi"):
        # the model service failed mid-episode: an infrastructure failure, not a verdict; the episode is run again
        kayit["hata"] = kos["bitis"]
        h = {**h, "hukum": "kurulamadi"}
    kayit.update({"hukum": h["hukum"], "tutan": h["tutan"], "toplam": h["toplam"], "kontroller": h["kontroller"],
                  "zarar": h["zarar"], "isler": isler, "rapor": rapor, "iz": araclar.iz, "denetim": ctm.state.get("log", []),
                  "arac_cagrisi": len(araclar.iz), "saniye": round(time.time() - t0, 1), **kos,
                  "mesaj_sayisi": len(mesajlar), "talep": senaryo["talep"], "kok_neden": senaryo.get("kok_neden")})
    return kayit


def yaz(ad, kayit):
    d = OUT / ad
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{kayit['senaryo']}__{kayit['kol']}.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(d / "ozet.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({k: kayit.get(k) for k in ("senaryo", "kol", "model", "aile", "tur", "bilesik", "hukum", "tutan", "toplam",
                                                     "adim", "arac_cagrisi", "saniye", "bitis", "cagri", "hata", "zaman")},
                           ensure_ascii=False) + "\n")


def ozet(ad):
    """Latest row per (scenario, arm)."""
    rows = {}
    p = OUT / ad / "ozet.jsonl"
    if p.exists():
        for ln in p.read_text(encoding="utf-8").splitlines():
            r = json.loads(ln)
            rows[(r["senaryo"], r["kol"])] = r
    return rows


def rapor(ad):
    rows = ozet(ad)
    kollar = sorted({k for _, k in rows})
    lines = [f"# {ad}", "", "| Kol | Senaryo | " + " | ".join(HUKUMLER) + " | kurulamadi | ort. adim | ort. sn |", "| --- | --- | " + "--- | " * (len(HUKUMLER) + 3)]
    for kol in kollar:
        rs = [r for (s, k), r in rows.items() if k == kol]
        n = len(rs)
        cnt = {h: sum(r["hukum"] == h for r in rs) for h in HUKUMLER + ("kurulamadi",)}
        steps = [r["adim"] for r in rs if r.get("adim")]
        secs = [r["saniye"] for r in rs if r.get("saniye")]
        lines.append(f"| {kol} | {n} | " + " | ".join(str(cnt[h]) for h in HUKUMLER) + f" | {cnt['kurulamadi']} | "
                     f"{(sum(steps) / len(steps)) if steps else 0:.1f} | {(sum(secs) / len(secs)) if secs else 0:.0f} |")
    if len(kollar) > 1:
        lines += ["", "| Senaryo | " + " | ".join(kollar) + " |", "| --- | " + "--- | " * len(kollar)]
        for s in sorted({s for s, _ in rows}):
            lines.append(f"| {s} | " + " | ".join(rows.get((s, k), {}).get("hukum", "-") for k in kollar) + " |")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vardiya.saha.kosu")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("dogrula", "kos"):
        p = sub.add_parser(name)
        p.add_argument("--split", default="dev")
        p.add_argument("--id", action="append")
        p.add_argument("--ad", default=None)
        if name == "kos":
            p.add_argument("--kollar", default="yalin,usta")
            p.add_argument("--model", required=True)
            p.add_argument("--atla", action="store_true", help="skip episodes that already have a row")
            p.add_argument("--max-adim", type=int, default=ajan.MAX_ADIM)
            p.add_argument("--parca", help="i/n: senaryolarin n parcadan i'incisi (paralel laboratuvar kopyalari icin)")
    p = sub.add_parser("rapor")
    p.add_argument("--ad", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "rapor":
        print(rapor(a.ad))
        return 0
    senaryolar = yukle(a.split, a.id)
    if getattr(a, "parca", None):
        i, n = (int(x) for x in a.parca.split("/"))
        senaryolar = [s for k, s in enumerate(senaryolar) if k % n == i - 1]
    bad = {s.get("id", s["_dosya"]): dogrula_bicim(s) for s in senaryolar}
    bad = {k: v for k, v in bad.items() if v}
    if bad:
        print("bicim hatasi:", json.dumps(bad, ensure_ascii=False, indent=1))
        return 2
    lab = Lab()
    kilit = OUT / "durum" / f"{lab.proje}.kilit"
    kilit.parent.mkdir(parents=True, exist_ok=True)
    if kilit.exists() and time.time() - kilit.stat().st_mtime < 1800:
        print(f"bu laboratuvarda baska bir kosu suruyor ({kilit}); iki kosu ayni ortami bozar. Bitmesini bekleyin.")
        return 3
    dur = OUT / "durum" / "DUR"
    lab.wait_ready(120)
    if os.environ.get("SAHA_AAPI"):          # a real Control-M behind the same tools (see ctm_aapi.py)
        from .ctm_aapi import CtmAapi
        ctm = CtmAapi(lab)
    else:
        ctm = Ctm(lab)
    ad = a.ad or (f"dogrula-{a.split}" if a.cmd == "dogrula" else f"{a.split}-{re.sub(r'[^A-Za-z0-9.]+', '-', a.model)}")
    done = ozet(ad) if getattr(a, "atla", False) else {}
    kollar = ["bos", "referans"] if a.cmd == "dogrula" else a.kollar.split(",")
    kotu = 0
    for s in senaryolar:
        for kol in kollar:
            if dur.exists():
                print("DUR dosyasi goruldu; kosu temiz durduruldu.")
                kilit.unlink(missing_ok=True)
                return 4
            kilit.write_text(f"{ad} {s['id']} {kol}", encoding="utf-8")
            if (s["id"], kol) in done and done[(s["id"], kol)]["hukum"] != "kurulamadi":
                continue
            k = bolum(lab, ctm, s, kol, getattr(a, "model", None), max_adim=getattr(a, "max_adim", ajan.MAX_ADIM),
                      gunluk=lambda n, e: print(f"    {n:>2} {e.get('arac')}: {str(e.get('komut') or e.get('rapor') or '')[:110]}", flush=True))
            yaz(ad, k)
            beklenen = {"bos": k["hukum"] != "dogru", "referans": k["hukum"] == "dogru"}.get(kol, True)
            kotu += not beklenen
            print(f"{'  ' if beklenen else '!!'} {s['id']:<34} {kol:<9} {k['hukum']:<12} {k.get('tutan', '-')}/{k.get('toplam', '-')} "
                  f"adim={k.get('adim', '-')} {k.get('saniye', 0):.0f}sn {k.get('hata', '')}", flush=True)
            if not beklenen or k["hukum"] == "kurulamadi":
                for c in k.get("kontroller", []) + k.get("zarar", []):
                    print(f"       {'+' if c['tutar'] else '-'} {json.dumps(c['kontrol'], ensure_ascii=False)[:110]} -> {str(c['gorulen'])[:110]}")
    kilit.unlink(missing_ok=True)
    print()
    print(rapor(ad))
    return 1 if (a.cmd == "dogrula" and kotu) else 0


if __name__ == "__main__":
    sys.exit(main())
