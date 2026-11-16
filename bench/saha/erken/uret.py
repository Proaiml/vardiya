"""Generates the precursor scenarios of the early-warning bench.

    python bench/saha/erken/uret.py dev         # the development half: fixed risk mixes, seed 11
    python bench/saha/erken/uret.py test        # the held-out half: mixes and parameters drawn from seed 4242
    python bench/saha/erken/uret.py kapali      # the closed-loop site: three twin pairs, one acted on, one left alone

The held-out half is written to disk and never printed: nothing here shows what it holds. The development half is the
only one that was read and tuned on.
"""
import json
import pathlib
import random
import sys

AD = pathlib.Path(__file__).resolve().parent
KLASORLER = ["SATIS_AKTAR", "FINANS_GUNSONU", "MUHASEBE_KAPANIS", "KREDI_DEGERLEME", "TEDARIK_ALIM", "RAPOR_DAGITIM", "ODEME_MUTABAKAT",
             "STOK_SAYIM", "MUSTERI_BILDIRIM", "FATURA_ISLE", "BORDRO_HAZIR", "KUR_GUNCELLE", "SIGORTA_TAHSIL", "ARSIV_YENILE",
             "PERSONEL_AKTAR", "SUBE_TOPLAMA", "HAZINE_ONAY", "DENETIM_CIKAR", "KAMPANYA_HESAP", "LOJISTIK_PLAN"]
ISLER = ["YUKLE", "HAZIRLA", "GONDER", "TOPLA", "ISLE", "HESAPLA", "DAGIT", "KAPAT", "ONAYLA", "CIKAR", "BIRLESTIR", "AKTAR",
         "TARA", "DENETLE", "ESLE", "OZETLE"]
HOSTLAR = ["ajan1", "ajan2"]

# development mixes: (risks, look-alikes)
DEV = [
    (["disk_dolu", "hesap_suresi"], ["t_disk_durgun", "t_yavas"]),
    (["anahtar_suresi", "sure_asimi"], ["t_hesap_uzak"]),
    (["tekrarlayan_hata", "birikim"], ["t_tek_hata", "t_oturum"]),
    (["kilit_bekleme", "disk_dolu"], ["t_birikim_durgun", "t_yavas"]),
    (["hesap_suresi", "tekrarlayan_hata", "anahtar_suresi"], ["t_anahtar_uzak"]),
    ([], ["t_disk_durgun", "t_oturum", "t_tek_hata", "t_yavas"]),
]
RISKLER = ["disk_dolu", "hesap_suresi", "anahtar_suresi", "sure_asimi", "tekrarlayan_hata", "kilit_bekleme", "birikim"]
TUZAKLAR = ["t_disk_durgun", "t_yavas", "t_tek_hata", "t_hesap_uzak", "t_anahtar_uzak", "t_oturum", "t_birikim_durgun"]


def bilesen(rng, tur, kullanilan, genis=False, host_disk=None):
    """One component with random parameters. `genis` widens the ranges (the held-out half)."""
    while True:
        klasor, is_ = rng.choice(KLASORLER), rng.choice(ISLER)
        if klasor not in kullanilan["klasor"] and is_ not in kullanilan["is"]:
            break
    kullanilan["klasor"].add(klasor)
    kullanilan["is"].add(is_)
    p = {"tur": tur, "klasor": klasor, "is": is_, "host": rng.choice(HOSTLAR)}
    lft = rng.randint(2, 9) if genis else rng.randint(3, 8)
    if tur == "disk_dolu":
        p["host"] = host_disk or p["host"]
        p["adim_kb"] = rng.choice([100, 108, 120, 128, 140, 148]) if not genis else rng.choice([96, 112, 124, 136, 150, 160])
        used = 4096 - lft * p["adim_kb"] - rng.randint(0, p["adim_kb"] // 2)
        p["onceki_kb"] = max(200, used - 16 * p["adim_kb"])
    elif tur == "hesap_suresi":
        p["rol"] = "rapor_user"
        p["bitis_saat"] = round(rng.uniform(4, 30) if not genis else rng.uniform(2, 60), 1)
    elif tur == "anahtar_suresi":
        p["hesap"] = "banka"
        p["bitis_saat"] = round(rng.uniform(6, 40) if not genis else rng.uniform(3, 60), 1)
    elif tur == "sure_asimi":
        taban, her = rng.choice([1, 2]), rng.choice([2, 3])
        gerek = -(-(16 + lft) // her)
        p.update({"taban_sn": taban, "her_kac": her, "limit_sn": taban + gerek - 1})
    elif tur == "tekrarlayan_hata":
        kosu = sorted(rng.sample(range(4, 16), 4 if not genis else rng.choice([3, 4, 5])))
        p.update({"hata_kosular": kosu, "sert_kosu": 16 + lft, "hata_no": rng.randint(0, 3)})
    elif tur == "kilit_bekleme":
        p.update({"tablo": "satis_gecici", "saat": rng.choice(["01:30", "02:00", "03:00", "23:30"])})
    elif tur == "birikim":
        ekle = rng.randint(5, 8)
        net = rng.randint(2, 3)
        base = rng.randint(5, 12)
        p.update({"ekle": ekle, "tuket": ekle - net, "baslangic": base, "sinir": base + 16 * net + net * lft - 1})
    elif tur == "t_disk_durgun":
        p["host"] = "ajan2" if host_disk != "ajan2" else "ajan1"
        p["dolu_kb"] = rng.choice([3600, 3750, 3900])
        p.pop("klasor"), p.pop("is")
    elif tur == "t_yavas":
        p.update({"sn": rng.randint(5, 8), "limit_sn": 40})
    elif tur == "t_tek_hata":
        p.update({"hata_kosu": rng.randint(3, 8), "hata_no": rng.randint(0, 3)})
    elif tur == "t_hesap_uzak":
        p.update({"rol": "etl_user", "gun": rng.randint(60, 400)})
    elif tur == "t_anahtar_uzak":
        p.update({"hesap": "rapor", "gun": rng.randint(90, 300)})
    elif tur == "t_oturum":
        p.update({"tablo": "musteri"})
        p.pop("klasor"), p.pop("is")
    elif tur == "t_birikim_durgun":
        p.update({"ekle": 3, "tuket": 3, "baslangic": rng.randint(14, 22), "sinir": 60})
    return p


def senaryo(rng, sid, bolum, riskler, tuzaklar, genis=False):
    kul = {"klasor": set(), "is": set()}
    bil, disk_host = [], None
    for tur in riskler + tuzaklar:
        if tur == "disk_dolu":
            disk_host = rng.choice(HOSTLAR)
        bil.append(bilesen(rng, tur, kul, genis, host_disk=disk_host if tur in ("disk_dolu", "t_disk_durgun") else None))
    return {"id": sid, "bolum": bolum, "gecmis": 16, "bilesenler": bil}


def yaz(klasor, sc):
    d = AD / klasor
    d.mkdir(exist_ok=True)
    (d / f"{sc['id']}.json").write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8")


def dev():
    rng = random.Random(11)
    for i, (r, t) in enumerate(DEV, 1):
        yaz("dev", senaryo(rng, f"ed-{i:02d}", "dev", r, t))
    print(f"dev: {len(DEV)} senaryo yazildi")


def test():
    """Six held-out sites from a different seed. Mixes are drawn, not chosen: at least one site carries no risk."""
    rng = random.Random(4242)
    dev_mix = {tuple(sorted(r)) for r, _ in DEV}
    n = 0
    for i in range(1, 7):
        while True:
            k = 0 if i == 1 else rng.choice([1, 2, 2, 3])
            r = rng.sample(RISKLER, k)
            if tuple(sorted(r)) not in dev_mix:
                break
        t = rng.sample([x for x in TUZAKLAR if not (x == "t_disk_durgun" and "disk_dolu" in r)], rng.choice([1, 2, 3]))
        yaz("test", senaryo(rng, f"et-{i:02d}", "test", r, t, genis=True))
        n += 1
    print(f"test: {n} senaryo yazildi (icerigi gosterilmez)")


def kapali():
    """Closed loop: three twin pairs on one site. The `eylem` twin gets the fix the warning calls for, the `kontrol`
    twin is left alone. The deadlines of the clock based risks are a few minutes away, so the failure really arrives."""
    kul = {"klasor": set(), "is": set()}
    rng = random.Random(7)
    bil = []

    def ek(tur, kapali_rol, **kw):
        p = bilesen(rng, tur, kul)
        p.update(kw)
        p["kapali"] = kapali_rol
        bil.append(p)
    ek("hesap_suresi", "eylem", rol="rapor_user", bitis_dk=5, host="ajan1")
    ek("hesap_suresi", "kontrol", rol="etl_user", bitis_dk=5, host="ajan1")
    ek("disk_dolu", "eylem", host="ajan1", adim_kb=120, onceki_kb=1100)
    ek("disk_dolu", "kontrol", host="ajan2", adim_kb=120, onceki_kb=1100)
    ek("anahtar_suresi", "eylem", hesap="banka", bitis_dk=5, host="ajan1")
    ek("anahtar_suresi", "kontrol", hesap="rapor", bitis_dk=5, host="ajan1")
    yaz("kapali", {"id": "kd-01", "bolum": "kapali", "gecmis": 16, "bilesenler": bil})
    print("kapali: kd-01 yazildi")


if __name__ == "__main__":
    {"dev": dev, "test": test, "kapali": kapali}[sys.argv[1]]()
