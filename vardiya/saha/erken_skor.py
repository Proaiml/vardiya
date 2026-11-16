"""Scoring of the early-warning bench: parse an arm's warnings and compare them with the truth of the site.

An arm answers with lines of the form

    UYARI | is=KLASOR/IS | sinif=<class> | ne_zaman=<ISO time or "N kosu sonra"> | neden=<one sentence>

or the single line `UYARI YOK`. The score of one site:

    bulunan     seeded risks whose job was named before it failed (the arms are read only and every risk job still works
                when they finish, which the runner checks)
    dogru_neden of those, the ones named with the right cause class
    dogru_zaman of those with the right class, the ones whose stated time is within tolerance of the deadline
    yanlis      warnings on a job that carries no risk (a look-alike or a healthy job), or on a name that is not a job
"""
import datetime
import re

ALAN = re.compile(r"(\w+)\s*=\s*(.*?)(?=\s*\|\s*\w+\s*=|$)")


def ayikla(metin):
    """[{is, sinif, ne_zaman, neden}] from an arm's final report."""
    out = []
    for ln in str(metin or "").splitlines():
        ln = ln.strip().strip("*`- ")
        if not ln.upper().startswith("UYARI") or ln.upper().startswith("UYARI YOK"):
            continue
        parts = ln.split("|", 1)
        if len(parts) < 2:
            continue
        f = {k.lower(): v.strip().strip("`\"' ") for k, v in ALAN.findall(parts[1])}
        if f.get("is"):
            out.append({"is": f["is"], "sinif": f.get("sinif", "").lower().strip(), "ne_zaman": f.get("ne_zaman", ""), "neden": f.get("neden", "")})
    return out


def is_adi(ad, isler):
    """The site's job id a warning refers to, or None. `FOLDER/JOB`, `FOLDER.JOB` and an unambiguous bare `JOB` all count."""
    a = str(ad).strip().replace("\\", "/").replace(".", "/")
    if a in isler:
        return a
    bos = [i for i in isler if i.split("/")[-1].lower() == a.split("/")[-1].lower() and (a.count("/") == 0 or i.lower() == a.lower())]
    return bos[0] if len(bos) == 1 else None


def zaman_dogru(metin, son, t0):
    """Whether the stated time matches the deadline: runs within 3 (or 40 percent), clock times within 3 hours (or 25 percent)."""
    m = str(metin).lower()
    if son["tur"] == "kosu":
        sayi = re.findall(r"\d+", m)
        if not sayi or "saat" in m or re.search(r"\d{4}-\d\d-\d\d", m):
            return False
        return abs(int(sayi[0]) - son["n"]) <= max(3, 0.4 * son["n"])
    if son["tur"] == "saat":
        iso = re.search(r"(\d{4})-(\d\d)-(\d\d)[ t](\d\d):(\d\d)", m)
        if iso:
            y, mo, d, h, mi = (int(x) for x in iso.groups())
            t = datetime.datetime(y, mo, d, h, mi, tzinfo=datetime.timezone.utc).timestamp()
        else:
            rel = re.search(r"(\d+(?:[.,]\d+)?)\s*(saat|sa\b|h\b)", m)
            gun = re.search(r"(\d+(?:[.,]\d+)?)\s*gun", m)
            dk = re.search(r"(\d+(?:[.,]\d+)?)\s*(dakika|dk)", m)
            if rel:
                t = t0 + float(rel.group(1).replace(",", ".")) * 3600
            elif gun:
                t = t0 + float(gun.group(1).replace(",", ".")) * 86400
            elif dk:
                t = t0 + float(dk.group(1).replace(",", ".")) * 60
            else:
                return False
        kalan = son["t"] - t0
        return abs(t - son["t"]) <= max(3 * 3600, 0.25 * kalan) if kalan > 1800 else abs(t - son["t"]) <= 600
    if son["tur"] == "planli":
        h, mi = son["saat"].split(":")
        # the scheduler works in Istanbul time (UTC+3): 02:00 there is 23:00 UTC the evening before
        return bool(re.search(rf"{h}:{mi}|{int(h):d}:{mi}|gece|bu aksam|sonraki|ilk kosu", m)) or bool(re.search(rf"{(int(h) - 3) % 24:02d}:{mi}", m))
    return False


def skorla(uyarilar, gercek, isler, t0):
    """Score one arm's warnings (list of dicts as `ayikla` returns) on one site."""
    risk = {r["is"]: r for r in gercek["riskler"]}
    bulunan, neden, zaman, yanlis = set(), set(), set(), []
    detay = []
    for w in uyarilar:
        j = is_adi(w["is"], isler)
        if j is None or j not in risk:
            if (j or w["is"]) not in yanlis:
                yanlis.append(j or w["is"])
            detay.append({"uyari": w, "sonuc": "yanlis alarm"})
            continue
        bulunan.add(j)
        r = risk[j]
        if w["sinif"] == r["sinif"]:
            neden.add(j)
            if zaman_dogru(w["ne_zaman"], r["son"], t0):
                zaman.add(j)
        detay.append({"uyari": w, "sonuc": "bulundu" + (" dogru neden" if w["sinif"] == r["sinif"] else f" yanlis neden (dogru: {r['sinif']})")})
    return {"risk": len(risk), "bulunan": len(bulunan), "dogru_neden": len(neden), "dogru_zaman": len(zaman), "yanlis": len(yanlis),
            "yanlis_isler": yanlis, "kacirilan": sorted(set(risk) - bulunan), "detay": detay}


def topla(skorlar):
    """Sums of a list of per-site scores; `temiz` = sites without any false alarm."""
    t = {"site": len(skorlar), "risk": 0, "bulunan": 0, "dogru_neden": 0, "dogru_zaman": 0, "yanlis": 0, "temiz": 0, "risksiz_site": 0,
         "risksiz_yanlis": 0}
    for s in skorlar:
        for k in ("risk", "bulunan", "dogru_neden", "dogru_zaman", "yanlis"):
            t[k] += s[k]
        t["temiz"] += s["yanlis"] == 0
        if s["risk"] == 0:
            t["risksiz_site"] += 1
            t["risksiz_yanlis"] += s["yanlis"]
    return t
