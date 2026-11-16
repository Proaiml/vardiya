"""Early warnings from one telemetry snapshot: which job is likely to fail next, why, and by when.

Two producers, and every warning says which one it came from (`kaynak`):

    kural   plain trend and threshold rules, one per risk class: the right tool where the cause is a quantity with a
            limit (a disk that fills by a steady amount per run does not need a neural net)
    graf    the graph neural net of vardiya/saha/erken_graf.py, trained on the development sites only; it scores every
            job node of the live graph from the telemetry features of its neighbours

`birlesik` is the union: a job both flag keeps both tags (`kural+graf`).

`cikar` is the one place where telemetry becomes features; the rules and the net read the same extraction.
"""
import math
import statistics

from ..cozumle import theil_sen

UFUK_KOSU = 15      # runs ahead that count as "soon"
UFUK_SAAT = 72      # hours ahead that count as "soon"
SINIFLAR = ("disk_dolu", "hesap_suresi", "anahtar_suresi", "sure_asimi", "tekrarlayan_hata", "kilit_bekleme", "birikim")
ENGEL_KIPLERI = {"AccessExclusiveLock", "ExclusiveLock", "ShareRowExclusiveLock", "ShareLock", "ShareUpdateExclusiveLock"}


def egim(ys):
    return theil_sen(ys) if len(ys) >= 2 else 0.0


def cikar(snap):
    """Per job the series and limits, plus the shared resources (roles, keys, open sessions) with the jobs that depend on them."""
    simdi = snap["t"]
    isler, roller = {}, {r["rol"]: r for r in snap["roller"]}
    for j in snap["isler"]:
        e = {"id": j["id"], "durum": j["durum"], "kosu": len(j["kosular"]), "host": j["host"], "tablolar": j["tablolar"],
             "planli": j["planli"], "timeout": j["timeout"], "limit": j["limit"]}
        diskler = {}
        for r in j["kosular"]:
            for d in r["df"]:
                s = diskler.setdefault(d["mount"], {"kullanilan": [], "toplam": d["toplam_kb"]})
                s["kullanilan"].append(d["kullanilan_kb"])
        e["disk"] = diskler
        ok = [r["sn"] for r in j["kosular"] if r["ok"] and r["sn"] is not None]
        e["sure"] = ok
        e["hatalar"] = [(r["no"], r["hata"]) for r in j["kosular"] if not r["ok"]]
        e["sonuc"] = [r["ok"] for r in j["kosular"]]
        e["sayac"] = {k: [r["sayac"][k] for r in j["kosular"] if k in r["sayac"]] for k in
                      {k for r in j["kosular"] for k in r["sayac"]}}
        hesaplar, anahtarlar = [], []
        for pf in j["profiller"]:
            p = snap["profiller"].get(pf) or {}
            rol = roller.get(p.get("kullanici")) if p.get("tip", "").startswith("Database") else None
            if rol:
                t = rol["gecerlilik"]
                hesaplar.append({"rol": rol["rol"], "kalan_saat": None if t is None else (t - simdi) / 3600.0})
            if p.get("anahtar"):
                for y in snap["yetkili_anahtarlar"]:
                    if y["hesap"] == p.get("kullanici"):
                        anahtarlar.append({"hesap": y["hesap"], "kalan_saat": None if y["bitis"] is None else (y["bitis"] - simdi) / 3600.0})
        e["hesaplar"], e["anahtarlar"] = hesaplar, anahtarlar
        isler[j["id"]] = e
    tut = {}
    for k in snap["kilitler"]:
        if k["verildi"] and k["kip"] in ENGEL_KIPLERI:
            tut.setdefault(k["pid"], set()).add(k["tablo"])
    oturumlar = []
    for s in snap["oturumlar"]:
        if s["durum"].startswith("idle in transaction") and s["pid"] in tut:
            tab = sorted(tut[s["pid"]])
            oturumlar.append({"pid": s["pid"], "kullanici": s["kullanici"], "xact_sn": s["xact_sn"], "tablolar": tab,
                              "isler": sorted(i for i, e in isler.items() if set(e["tablolar"]) & set(tab))})
    return {"isler": isler, "oturumlar": oturumlar, "t": simdi}


def _u(is_, sinif, ne_zaman, neden, kural, **kanit):
    return {"is": is_, "sinif": sinif, "ne_zaman": ne_zaman, "neden": neden, "kaynak": "kural", "kural": kural, "kanit": kanit}


def kurallar(oz):
    """The trend and threshold rules. Returns warnings."""
    out = []
    for i, e in oz["isler"].items():
        # R1 disk: the volume a job writes to fills by a steady amount per run
        for mount, s in e["disk"].items():
            ys = s["kullanilan"]
            if len(ys) >= 5:
                m = egim(ys)
                kalan = s["toplam"] - ys[-1]
                if m > 0 and kalan / m <= UFUK_KOSU:
                    n = int(kalan // m) + 1
                    out.append(_u(i, "disk_dolu", {"tur": "kosu", "n": n},
                                  f"{e['host']}:{mount} her kosuda ~{m:.0f} KB doluyor, {kalan} KB bos; ~{n}. kosuda dolar",
                                  "R1", hiz_kb=round(m, 1), bos_kb=kalan, mount=mount))
        # R2 role validity and R3 key expiry: a date inside the horizon
        for h in e["hesaplar"]:
            if h["kalan_saat"] is not None and h["kalan_saat"] <= UFUK_SAAT:
                out.append(_u(i, "hesap_suresi", {"tur": "saat_sonra", "saat": round(h["kalan_saat"], 2)},
                              f"{h['rol']} hesabinin gecerliligi {h['kalan_saat']:.1f} saat sonra bitiyor", "R2", rol=h["rol"]))
        for h in e["anahtarlar"]:
            if h["kalan_saat"] is not None and h["kalan_saat"] <= UFUK_SAAT:
                out.append(_u(i, "anahtar_suresi", {"tur": "saat_sonra", "saat": round(h["kalan_saat"], 2)},
                              f"{h['hesap']} hesabinin giris anahtari {h['kalan_saat']:.1f} saat sonra gecersiz oluyor", "R3", hesap=h["hesap"]))
        # R4 duration: the runs take longer and the command carries a time limit
        ys = e["sure"]
        if e["timeout"] and len(ys) >= 6:
            m, med = egim(ys), statistics.median(ys)
            son = statistics.median(ys[-3:])
            if m >= max(0.15, 0.03 * med) and ys[-1] - ys[0] > 0.2 * med and son < e["timeout"] + 2:
                n = max(1, math.ceil((e["timeout"] - son) / m))
                if n <= UFUK_KOSU:
                    out.append(_u(i, "sure_asimi", {"tur": "kosu", "n": n},
                                  f"sure her kosuda ~{m:.2f} sn uzuyor (son {son:.1f} sn), komutundaki {e['timeout']} sn sinirina ~{n} kosuda varir",
                                  "R4", egim_sn=round(m, 2), son_sn=round(son, 1), limit_sn=e["timeout"]))
        # R5 recurring error: the same line three times in the last twelve runs, not tailing off, the job still green
        son12 = [(n, h) for n, h in e["hatalar"] if n > e["kosu"] - 12]
        if len(son12) >= 3 and e["sonuc"] and e["sonuc"][-1]:
            yarim = e["kosu"] - 6
            ikinci = sum(1 for n, _ in son12 if n > yarim)
            if ikinci >= len(son12) - ikinci:
                imza = {}
                for _, h in son12:
                    imza[h] = imza.get(h, 0) + 1
                en, say = max(imza.items(), key=lambda kv: kv[1])
                if say >= 3:
                    out.append(_u(i, "tekrarlayan_hata", {"tur": "belirsiz"},
                                  f"ayni hata son 12 kosuda {say} kez geldi ve sikilasiyor: {en[:80]}", "R5", hata=en[:120], sayi=say))
        # R7 backlog against the limit the script enforces
        if e["limit"] and e["sayac"].get("bekleyen_dosya") and len(e["sayac"]["bekleyen_dosya"]) >= 5:
            ys = e["sayac"]["bekleyen_dosya"]
            m = egim(ys)
            kalan = e["limit"] - ys[-1]
            if m > 0 and kalan / m <= UFUK_KOSU:
                n = int(kalan // m) + 1
                out.append(_u(i, "birikim", {"tur": "kosu", "n": n},
                              f"bekleyen dosya her kosuda ~{m:.1f} artiyor ({ys[-1]}/{e['limit']}); ~{n}. kosuda sinir asilir",
                              "R7", artis=round(m, 2), simdi=ys[-1], limit=e["limit"]))
    # R6 an open transaction holds a lock on a table a job writes to
    for s in oz["oturumlar"]:
        for i in s["isler"]:
            e = oz["isler"][i]
            out.append(_u(i, "kilit_bekleme", {"tur": "planli", "saat": e["planli"]} if e["planli"] else {"tur": "sonraki_kosu"},
                          f"{s['kullanici']} oturumu (pid {s['pid']}) {s['xact_sn']} sn'dir acik islemde, {', '.join(s['tablolar'])} tablosunu kilitli "
                          f"tutuyor; bu isin tablosu", "R6", pid=s["pid"], tablolar=s["tablolar"]))
    return out


def birlestir(kural, graf):
    """Union by (job, class). A job both flag keeps both tags; the rule's evidence and time win."""
    sonuc = {}
    for w in kural:
        sonuc[(w["is"], w["sinif"])] = dict(w, kaynak="kural")
    for w in graf:
        k = (w["is"], w["sinif"])
        if k in sonuc:
            sonuc[k]["kaynak"] = "kural+graf"
            sonuc[k]["graf_p"] = w.get("p")
        else:
            sonuc[k] = dict(w)
    return sorted(sonuc.values(), key=lambda w: (w["is"], w["sinif"]))


def uyarilar(snap, graf_modeli=None, esik=0.5):
    """(kural, graf, birlesik) warnings of a snapshot. Without a trained model the graph list is empty."""
    oz = cikar(snap)
    k = kurallar(oz)
    g = graf_modeli.uyarilar(snap, oz, esik) if graf_modeli is not None else []
    return k, g, birlestir(k, g)


# ---------------------------------------------------------------------------------------------------- what the arm is shown
def paket(snap, uyarilar_, inceleme=None):
    """The early-warning pack that goes into the prompt of the `usta` arm: the warnings with their evidence and where each
    came from, plus the things the collector looked at and decided not to warn about (so the model does not raise them)."""
    satir = ["## Erken uyari paketi (kodla uretildi; yalnizca ortamin okunan verisine dayanir)",
             "Kod siteyi okudu, her isin gecmisini ve kaynaklarini cikardi. Asagidaki uyarilar bir is DAHA BOZULMADAN verilmistir."]
    if not uyarilar_:
        satir.append("- Uyari yok: hicbir is, esik icinde bir bozulmaya dogru gitmiyor.")
    for w in uyarilar_:
        z = w["ne_zaman"]
        zt = {"kosu": f"~{z.get('n')}. kosuda", "saat_sonra": f"~{z.get('saat')} saat sonra", "planli": f"planli saatte ({z.get('saat')})",
              "sonraki_kosu": "bir sonraki kosuda", "belirsiz": "zamani belirsiz"}.get(z["tur"], "")
        satir.append(f"- UYARI is={w['is']} sinif={w['sinif']} ne_zaman={zt} kaynak={w['kaynak']}: {w['neden']}")
    if inceleme:
        satir.append("Inceleyip uyari vermedigi seyler:")
        satir += [f"- {x}" for x in inceleme]
    satir.append("Uyarilari kendin dogrula (arac ile bak); kodun gormedigi bir sey varsa onu da ekle, ama emin degilsen uyari verme.")
    return "\n".join(satir)


def inceleme(snap, oz, uyar):
    """Plain sentences for what was checked and found harmless: static or unused volumes, far dates, single failures."""
    flagged = {w["is"] for w in uyar}
    out = []
    kullanan = {(e["host"], m) for e in oz["isler"].values() for m in e["disk"]}
    for h, rows in snap["diskler"].items():
        for r in rows:
            if r["mount"].startswith("/data/dar") and r["yuzde"] >= 60:
                kim = [i for i, e in oz["isler"].items() if r["mount"] in e["disk"] and e["host"] == h]
                if not kim:
                    out.append(f"{h}:{r['mount']} %{r['yuzde']} dolu ama hicbir is bu bolume yazmiyor ve kosularda artis gormedik")
                elif not any(i in flagged for i in kim):
                    out.append(f"{h}:{r['mount']} %{r['yuzde']} dolu, ama yazan is(ler) {', '.join(kim)} artis gostermiyor")
    for r in snap["roller"]:
        kim = [i for i, e in oz["isler"].items() if any(h["rol"] == r["rol"] for h in e["hesaplar"])]
        if r["gecerlilik"] and kim and not any(i in flagged for i in kim):
            out.append(f"{r['rol']} hesabi {kim[0]} icin kullaniliyor, gecerlilik tarihi uzak: {r['gecerlilik_metni'][:10]}")
    for i, e in oz["isler"].items():
        if i in flagged:
            continue
        if len(e["hatalar"]) == 1:
            out.append(f"{i}: tek bir hata var (kosu {e['hatalar'][0][0]}), tekrar etmedi")
        if e["timeout"] and len(e["sure"]) >= 6 and egim(e["sure"]) < 0.15:
            out.append(f"{i}: {statistics.median(e['sure']):.1f} sn civarinda sabit; sure siniri {e['timeout']} sn, uzama yok")
        for k, ys in e["sayac"].items():
            if len(ys) >= 5 and egim(ys) <= 0:
                out.append(f"{i}: {k} sabit ({ys[-1]})")
    for s in snap["oturumlar"]:
        if s["durum"].startswith("idle in transaction") and not any(s["pid"] == o["pid"] and o["isler"] for o in oz["oturumlar"]):
            out.append(f"{s['kullanici']} oturumu (pid {s['pid']}) acik islemde ama kilitledigi tablolari hicbir is yazmiyor")
    return out


def oneri(snap, w):
    """The tool call that answers a warning (the normal admin tools), or None."""
    if w["sinif"] == "hesap_suresi":
        rol = w["kanit"]["rol"]
        return {"arac": "sh", "sunucu": "appdb", "komut": f"psql -U postgres -d uygulama -c \"alter role {rol} valid until 'infinity'\""}
    if w["sinif"] == "anahtar_suresi":
        h = w["kanit"]["hesap"]
        return {"arac": "sh", "sunucu": "dosya-sunucu",
                "komut": f"sed -i -E 's/^expiry-time=\"[^\"]*\" //' /home/{h}/.ssh/authorized_keys"}
    if w["sinif"] == "disk_dolu":
        j = next(x for x in snap["isler"] if x["id"] == w["is"])
        yol = f"{j['host']}:{w['kanit']['mount']}"
        yazilan = j["betik_yolu"] and (j["betik_metni"] or "")
        adaylar = [f for f in snap["dizinler"].get(yol, []) if f["ad"] not in (yazilan or "") and f["kb"] > 100]
        if adaylar:
            f = max(adaylar, key=lambda f: f["kb"])
            return {"arac": "sh", "sunucu": j["host"], "komut": f"rm -f {w['kanit']['mount']}/{f['ad']}"}
    return None
