"""The closed loop: act on a warning through the normal tools and show that it prevents the failure.

The site kd-01 holds three twin pairs (a role, a disk, a key), each pair with the same risk and the same deadline. The code
warns, the fix of the warning is applied to the `eylem` twin only, and the `kontrol` twin is left alone. Then the deadline is
let pass (the clock based ones really are a few minutes away; the disk ones are driven past their last free run by more
runs) and every job is run again. Expected: the `kontrol` jobs fail, the `eylem` jobs run.
"""
import time

from . import erken_skor, erken_tahmin, erken_topla
from .araclar import Araclar
from .ctm import Ctm, FINAL
from .erken_kos import OUT, lab_bul, site_kur, yaz, yukle
from .erken_kos2 import graf_egit


def _bekle(ctm, ids, sn=120):
    t0 = time.time()
    while time.time() - t0 < sn:
        rows = {r["jobId"]: r for r in ctm.status()["statuses"]}
        if all(rows[i]["status"] in FINAL for i in ids):
            return {i: rows[i]["status"] for i in ids}
        time.sleep(1.5)
    return {i: "zaman asimi" for i in ids}


def calistir(a):
    s = yukle("kapali", ["kd-01"])[0]
    lab, kilit = lab_bul(a.ad, tercih=a.lab)
    try:
        lab.wait_ready(120)
        ctm = Ctm(lab)
        gercek, ctx, snap = site_kur(lab, ctm, s, a.ad, kilit, lambda x: print(x, flush=True))
        graf = graf_egit(OUT / "erken-dev-kur1")
        k, g, birlesik = erken_tahmin.uyarilar(snap, graf)
        rol = {f"{p['klasor']}/{p['is']}": p["kapali"] for p in s["bilesenler"]}
        araclar = Araclar(lab, ctm)
        eylemler = []
        for w in birlesik:
            if rol.get(w["is"]) == "eylem":
                o = erken_tahmin.oneri(snap, w)
                if o:
                    eylemler.append({"uyari": w["is"], "sinif": w["sinif"], "kaynak": w["kaynak"], "arac": o, "cikti": araclar.cagir(o)[:300]})
                    print("   eylem:", w["is"], w["sinif"], o["komut"][:90], flush=True)
        uyarilan = {w["is"] for w in birlesik}
        jid = {f"{r['folder']}/{r['name']}": r["jobId"] for r in ctm.status()["statuses"]}
        # the clock based deadlines: wait until they have passed
        son = max(r["son"]["t"] for r in gercek["riskler"] if r["son"]["tur"] == "saat")
        while time.time() < son + 20:
            kilit.yenile("kapali bekleme")
            time.sleep(10)
        sonuc = {}
        saat = [r for r in gercek["riskler"] if r["sinif"] in ("hesap_suresi", "anahtar_suresi")]
        ids = [jid[r["is"]] for r in saat]
        for i in ids:
            ctm.rerun(i)
        durum = _bekle(ctm, ids)
        for r in saat:
            sonuc[r["is"]] = {"sinif": r["sinif"], "rol": rol[r["is"]], "uyarildi": r["is"] in uyarilan, "durum": durum[jid[r["is"]]]}
        disk = [r for r in gercek["riskler"] if r["sinif"] == "disk_dolu"]
        n = max(r["son"]["n"] for r in disk)
        ids = [jid[r["is"]] for r in disk]
        durum = {}
        for _ in range(n + 1):
            for i in ids:
                ctm.rerun(i)
                durum.update(_bekle(ctm, [i]))
            kilit.yenile("kapali disk")
        for r in disk:
            sonuc[r["is"]] = {"sinif": r["sinif"], "rol": rol[r["is"]], "uyarildi": r["is"] in uyarilan, "durum": durum[jid[r["is"]]]}
        for r in saat + disk:
            j = jid[r["is"]]
            sonuc[r["is"]]["cikti"] = ctm.output(j, tail=6)[-300:]
        yaz(a.ad, "kd-01", "kapali.json", {"gercek": gercek, "uyarilar": birlesik, "eylemler": eylemler, "sonuc": sonuc})
        for k_, v in sonuc.items():
            print(f"   {v['sinif']:<15} {v['rol']:<8} {v['durum']}", flush=True)
    finally:
        kilit.birak()
    return 0
