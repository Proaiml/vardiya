"""The arms of the early-warning bench and the closed loop (called by erken_kos.py).

Arms, all with the same data access (the two tools and the handbook) and the same step budget:
    yalin   the model, asked "is anything on this site about to fail?"
    usta    the same model with the early-warning pack (collector, rules, graph net) in its context and the same tools to verify
    kod     the warnings of the code alone, no model (`kural`, `graf` and `birlesik` are scored separately)
"""
import json
import pathlib
import re
import time

from ..gateway import connect
from . import ajan, erken_skor, erken_tahmin, erken_topla
from .araclar import Araclar
from .ctm import Ctm
from .erken_graf import GrafAgi, etiketle
from .erken_kos import BENCH, OUT, Kilit, lab_bul, site_kur, yaz, yukle  # noqa: F401
from .erken_sablon import SINIFLAR

TALEP = """Bu sitedeki hicbir is su an hata vermiyor, her sey calisiyor gorunuyor. Ama sitede, gelecekte bir isi BOZACAK sey var olabilir:
bir kaynak tukeniyor, bir gecerlilik bitiyor, bir egilim bir siniri asmak uzere olabilir. Gorevin: bu isler bozulmadan ONCE, hangi
isin yakinda bozulacagini, nedenini ve ne zaman bozulacagini bulmak.

KURALLAR
- Siteyi YALNIZCA oku. Hicbir sey degistirme: is siparis etme, yeniden calistirma, dosya silme, hesap degistirme yok.
- Sadece gercekten yaklasan bozulmalar icin uyari ver. Zaten durgun olan, hicbir isi etkilemeyen ya da uzak bir tarihte olan
  seyler icin uyari verme: her yanlis alarm bir ekibin bos yere uyanmasi demektir.
- Neden siniflari (sinif= alaninda tam olarak bunlardan birini kullan):
%s
- Bittiginde "bitir" aracinin rapor alaninda her uyari icin AYRI SATIR yaz, tam bu bicimde:
  UYARI | is=KLASOR/IS | sinif=<yukaridakilerden biri> | ne_zaman=<ISO saat (UTC) ya da "N kosu sonra"> | neden=<tek cumle>
  Yakinda bozulacak bir sey yoksa raporun tek satiri: UYARI YOK
- Baska aciklama yazma; rapor alani yalnizca bu satirlari icersin.
Su an UTC saat: %s""" % ("\n".join(f"    {k}: {v}" for k, v in SINIFLAR.items()), "%s")


def talep():
    return TALEP % time.strftime("%Y-%m-%d %H:%M", time.gmtime())


def hafif(lab, ctm):
    """A cheap fingerprint of what a read-only arm must not change."""
    isler = {f"{r['folder']}/{r['name']}": [r["status"], r["numberOfRuns"]] for r in ctm.status()["statuses"]}
    ses, _ = erken_topla.oturumlar(lab)
    _, yet = erken_topla.anahtarlar(lab)
    return {"isler": isler, "roller": {r["rol"]: r["gecerlilik_metni"] for r in erken_topla.roller(lab)},
            "anahtar": sorted((a["hesap"], a["bitis"]) for a in yet), "oturum": sorted((s["kullanici"], s["durum"]) for s in ses),
            "disk": {f"{h}:{r['mount']}": r["kullanilan_kb"] for h, rows in erken_topla.diskler(lab).items() for r in rows
                     if r["mount"].startswith("/data/dar")}}


def graf_egit(dizin, haric=None, tohum=0):
    """Train the graph net on the telemetry saved in `dizin` (development sites only), leaving `haric` out."""
    ornekler = []
    for p in sorted(pathlib.Path(dizin).glob("*/telemetri.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d["senaryo"].get("bolum") != "dev" or d["senaryo"]["id"] == haric:
            continue
        ornekler.append((d["telemetri"], erken_tahmin.cikar(d["telemetri"]), etiketle(d["gercek"])))
    if not ornekler:
        return None
    return GrafAgi(tohum=tohum).egit(ornekler)


def kod_kolu(snap, gercek, graf, t0):
    """The code arm and its three variants, scored."""
    k, g, b = erken_tahmin.uyarilar(snap, graf)
    isler = {j["id"] for j in snap["isler"]}
    out = {}
    for ad, lst in (("kural", k), ("graf", g), ("birlesik", b)):
        w = [{"is": x["is"], "sinif": x["sinif"], "ne_zaman": _zaman_metni(x["ne_zaman"], t0), "neden": x["neden"]} for x in lst]
        out[ad] = {"uyarilar": lst, "skor": erken_skor.skorla(w, gercek, isler, t0)}
    return out, b


def _zaman_metni(z, t0):
    if z["tur"] == "kosu":
        return f"{z['n']} kosu sonra"
    if z["tur"] == "saat_sonra":
        return f"{z['saat']} saat sonra"
    if z["tur"] == "planli":
        return z["saat"]
    return ""


def model_kolu(kol, model_spec, lab, ctm, snap, gercek, birlesik, t0, max_adim, log):
    araclar = Araclar(lab, ctm)
    ek = ""
    if kol == "usta":
        oz = erken_tahmin.cikar(snap)
        ek = erken_tahmin.paket(snap, birlesik, erken_tahmin.inceleme(snap, oz, birlesik))
    model = connect(model_spec)
    onceki = hafif(lab, ctm)
    kos = ajan.kos(model, araclar, talep(), ek_baglam=ek, max_adim=max_adim,
                   gunluk=lambda n, e: log(f"    {n:>2} {e.get('arac')}: {str(e.get('komut') or e.get('rapor') or '')[:100]}"))
    sonra = hafif(lab, ctm)
    rapor = kos.pop("rapor")
    mesajlar = kos.pop("mesajlar", [])
    isler = {j["id"] for j in snap["isler"]}
    w = erken_skor.ayikla(rapor)
    skor = erken_skor.skorla(w, gercek, isler, t0)
    return {"kol": kol, "model": model_spec, "rapor": rapor, "uyarilar": w, "skor": skor, "iz": araclar.iz, "adim": kos["adim"],
            "bitis": kos["bitis"], "saniye": kos["saniye"], "cagri": kos.get("cagri"), "degisti": onceki != sonra,
            "ek_baglam": ek, "mesaj_sayisi": len(mesajlar)}


def calistir(a):
    if a.cmd == "kapali":
        from . import erken_kapali
        return erken_kapali.calistir(a)
    graf_dizin = OUT / "erken-dev-kur1"
    ids = a.id.split(",") if a.id else None
    senaryolar = yukle(a.bolum, ids)
    modeller = [m for m in a.model.split(",") if m]
    kollar = [k for k in a.kollar.split(",") if k]
    for s in senaryolar:
        sid = s["id"]
        if a.atla and all((OUT / a.ad / sid / f"{k}__{m.split(':')[-1]}.json").exists() for m in modeller for k in kollar):
            continue
        if (OUT / "durum" / "DUR").exists():
            print("DUR dosyasi goruldu", flush=True)
            break
        lab, kilit = lab_bul(a.ad, tercih=a.lab)          # one site per lock: others get their turn in between
        try:
            lab.wait_ready(120)
            ctm = Ctm(lab)
            print(f"== {sid}", flush=True)
            try:
                gercek, ctx, snap = site_kur(lab, ctm, s, a.ad, kilit, lambda x: print(x, flush=True))
            except Exception as e:  # noqa: BLE001
                print(f"   KURULAMADI: {type(e).__name__}: {str(e)[:300]}", flush=True)
                continue
            t0 = snap["t"]
            graf = graf_egit(graf_dizin, haric=sid if a.bolum == "dev" else None)
            kod, birlesik = kod_kolu(snap, gercek, graf, t0)
            yaz(a.ad, sid, "kod.json", kod)
            print("   kod:", {k: (v["skor"]["bulunan"], v["skor"]["risk"], v["skor"]["yanlis"]) for k, v in kod.items()}, flush=True)
            for m in list(modeller):
                for kol in kollar:
                    kilit.yenile(f"{sid} {kol} {m}")
                    try:
                        r = model_kolu(kol, m, lab, ctm, snap, gercek, birlesik, t0, a.max_adim, lambda x: print(x, flush=True))
                    except Exception as e:  # noqa: BLE001
                        r = {"kol": kol, "model": m, "hata": f"{type(e).__name__}: {str(e)[:300]}"}
                    yaz(a.ad, sid, f"{kol}__{m.split(':')[-1]}.json", r)
                    sk = r.get("skor")
                    print(f"   {kol:<6} {m.split(':')[-1]:<22} " + (f"bulunan {sk['bulunan']}/{sk['risk']} neden {sk['dogru_neden']} yanlis {sk['yanlis']} "
                          f"adim {r['adim']} {r['saniye']:.0f}sn bitis={r['bitis']}" + (" DEGISTI" if r["degisti"] else "") if sk else r.get("hata")), flush=True)
                    if re.search(r"quota|RESOURCE_EXHAUSTED", str(r.get("hata", "")) + str(r.get("bitis", ""))):
                        print("   model kotasi kapali; bu model birakiliyor", flush=True)
                        modeller.remove(m)
                        break
        finally:
            kilit.birak()
    return 0
