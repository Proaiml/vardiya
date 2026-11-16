"""Offline evaluation of the code arm on saved telemetry (no lab needed).

    python -m vardiya.saha.erken_degerlendir results/saha/erken-dev-kur1 [--egitim results/saha/erken-dev-kur1] [--ayrinti]

For development sites the graph net is trained leave-one-site-out (it never sees the site it is scored on). For held-out
sites it is trained on all development sites of `--egitim`.
"""
import argparse
import json
import pathlib

from . import erken_skor, erken_tahmin
from .erken_kos2 import graf_egit, kod_kolu


def degerlendir(dizin, egitim, tohumlar=(0,), ayrinti=False, esik=0.5):
    sonuc = {"kural": [], "graf": [], "birlesik": []}
    kayit = []
    for p in sorted(pathlib.Path(dizin).glob("*/telemetri.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        sid = d["senaryo"]["id"]
        for t in tohumlar:
            graf = graf_egit(egitim, haric=sid if d["senaryo"].get("bolum") == "dev" else None, tohum=t)
            kod, _ = kod_kolu(d["telemetri"], d["gercek"], graf, d["telemetri"]["t"])
            for k in sonuc:
                sonuc[k].append(kod[k]["skor"])
                if ayrinti:
                    s = kod[k]["skor"]
                    if s["kacirilan"] or s["yanlis"] or s["bulunan"] != s["dogru_neden"]:
                        kayit.append(f"{sid} {k} t{t}: kacirilan={s['kacirilan']} yanlis={s['yanlis_isler']} "
                                     f"{[x['sonuc'] for x in s['detay'] if 'yanlis neden' in x['sonuc']]}")
    return {k: erken_skor.topla(v) for k, v in sonuc.items()}, kayit


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dizin")
    ap.add_argument("--egitim", default=None)
    ap.add_argument("--ayrinti", action="store_true")
    ap.add_argument("--tohum", type=int, default=1)
    ap.add_argument("--esik", type=float, default=0.5)
    a = ap.parse_args(argv)
    tablo, kayit = degerlendir(a.dizin, a.egitim or a.dizin, tuple(range(a.tohum)), a.ayrinti, a.esik)
    print(json.dumps(tablo, ensure_ascii=False, indent=1))
    print("\n".join(kayit))


if __name__ == "__main__":
    main()
