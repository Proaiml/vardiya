"""Runs the early-warning bench on the live lab and keeps the evidence.

    python -m vardiya.saha.erken_kos kur  --bolum dev  --ad erken-dev-kur                  # build each site, collect, save
    python -m vardiya.saha.erken_kos kos  --bolum dev  --ad erken-dev-gpt --model agy:gpt-oss-120b-medium --kollar yalin,usta
    python -m vardiya.saha.erken_kos kapali --ad erken-kapali                              # the closed loop

Evidence of a site: results/saha/<ad>/<senaryo>/telemetri.json (snapshot and truth), <kol>__<model>.json (the arm's
steps, report, warnings and score). The lab is taken through its lock file (results/saha/durum/<project>.kilit) only
while it is free, and the lock is refreshed on every step.
"""
import argparse
import json
import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
OUT = pathlib.Path(os.environ["SAHA_SONUC"]) if os.environ.get("SAHA_SONUC") else ROOT / "results" / "saha"
BENCH = ROOT / "bench" / "saha" / "erken"
LABLAR = [("vardiya-saha", "http://127.0.0.1:27446"), ("vardiya-saha2", "http://127.0.0.1:27447"),
          ("vardiya-saha3", "http://127.0.0.1:27448")]


class Kilit:
    """The lab lock: created only when absent, refreshed while used, removed at the end."""
    def __init__(self, ad, proje):
        self.yol = OUT / "durum" / f"{proje}.kilit"
        self.ad = ad

    def al(self):
        self.yol.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.yol, "x", encoding="utf-8") as f:
                f.write(self.ad)
            return True
        except FileExistsError:
            return False

    def yenile(self, ek=""):
        self.yol.write_text(f"{self.ad} {ek}".strip(), encoding="utf-8")

    def birak(self):
        self.yol.unlink(missing_ok=True)


def lab_bul(ad, bekle_dk=600, log=print, tercih=None):
    """Wait for a free lab (1..3) and return (Lab, Kilit) with the lock taken."""
    sinir = time.time() + bekle_dk * 60
    liste = [x for x in LABLAR if not tercih or x[0] == tercih]
    ilk = True
    while time.time() < sinir:
        for proje, url in liste:
            k = Kilit(ad, proje)
            if k.al():
                os.environ["SAHA_PROJE"], os.environ["SAHA_URL"] = proje, url
                from .lab import Lab
                log(f"laboratuvar: {proje}")
                return Lab(), k
        if ilk:
            log("laboratuvarlar dolu; bos olani bekliyorum")
            ilk = False
        time.sleep(20)
    raise TimeoutError("bos laboratuvar bulunamadi")


def yukle(bolum, ids=None):
    out = []
    for p in sorted((BENCH / bolum).glob("*.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        if not ids or s["id"] in ids:
            out.append(s)
    return out


def yaz(ad, sid, dosya, veri):
    d = OUT / ad / sid
    d.mkdir(parents=True, exist_ok=True)
    (d / dosya).write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")


def site_kur(lab, ctm, s, ad, kilit, log=print):
    """Build one site, collect its telemetry, save it. Returns (truth, ctx, snapshot)."""
    from . import erken_sablon, erken_topla
    kilit.yenile(s["id"] + " kurulum")
    gercek, ctx = erken_sablon.kur(lab, ctm, s, log)
    kilit.yenile(s["id"] + " toplama")
    snap = erken_topla.topla(lab, ctm)
    log(f"  telemetri toplandi ({snap['toplama_sn']} sn, {len(snap['isler'])} is)")
    yaz(ad, s["id"], "telemetri.json", {"senaryo": s, "gercek": gercek, "telemetri": snap})
    return gercek, ctx, snap


def kur_komutu(a):
    from .ctm import Ctm
    ids = a.id.split(",") if a.id else None
    senaryolar = yukle(a.bolum, ids)
    lab, kilit = lab_bul(a.ad, tercih=a.lab)
    try:
        lab.wait_ready(120)
        ctm = Ctm(lab)
        for s in senaryolar:
            print(f"== {s['id']}", flush=True)
            t0 = time.time()
            try:
                gercek, _, _ = site_kur(lab, ctm, s, a.ad, kilit, print)
                print(f"   tamam {time.time() - t0:.0f} sn: {len(gercek['riskler'])} risk, {len(gercek['tuzaklar'])} tuzak", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"   KURULAMADI: {type(e).__name__}: {str(e)[:300]}", flush=True)
            if (OUT / "durum" / "DUR").exists():
                print("DUR dosyasi goruldu", flush=True)
                break
    finally:
        kilit.birak()
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vardiya.saha.erken_kos")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for ad in ("kur", "kos", "kapali"):
        p = sub.add_parser(ad)
        p.add_argument("--bolum", default="dev")
        p.add_argument("--id")
        p.add_argument("--ad", required=True)
        p.add_argument("--lab", help="belirli bir laboratuvar projesi (varsayilan: ilk bos)")
        if ad == "kos":
            p.add_argument("--model", required=True)
            p.add_argument("--kollar", default="yalin,usta")
            p.add_argument("--max-adim", type=int, default=14)
            p.add_argument("--atla", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "kur":
        return kur_komutu(a)
    from . import erken_kos2
    return erken_kos2.calistir(a)


if __name__ == "__main__":
    sys.exit(main())
