"""The graph neural net of the early-warning arm: a two-layer graph convolution over the live site graph (numpy, CPU).

Graph. One node per job, plus a node for everything a job depends on or measures:
    vol   a volume a job writes to           (edges to the jobs that write to it)
    rol   a database role                    (edges to the jobs that connect with it)
    key   a login key / account              (edges to the jobs that log in with it)
    oturum an open transaction with locks    (edges to the jobs that write the locked tables)
    sure  the run times of a job             (edge to the job)
    imza  the error lines of a job           (edge to the job)
    kuyruk a counter the job prints          (edge to the job)
A volume nobody writes to, a role nobody uses or a session that locks only tables no job touches stays an island: it can
not push risk onto any job. That is what the graph carries that a per-job table does not.

Features per node are raw telemetry, scaled: share of capacity used, change per run relative to capacity, the log of the
hours left before a date, the share of recent runs that failed, and so on. They are NOT the rules' verdicts: the net has to
learn where "soon" starts.

Model. Z1 = A H0 W1, H1 = relu(Z1), logits = A H1 W2, with A the symmetric normalised adjacency with self loops (Kipf and
Welling). Output per job: none or one of the seven risk classes. Trained with Adam on the job nodes of the development sites
only, with the usual jittered copies; at most two threads.
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

import math  # noqa: E402
import statistics  # noqa: E402

import numpy as np  # noqa: E402

from .erken_tahmin import SINIFLAR, egim  # noqa: E402

TIPLER = ("is", "vol", "rol", "key", "oturum", "sure", "imza", "kuyruk")
SINIF_ADLARI = ("yok",) + SINIFLAR
D = len(TIPLER) + 6


def _log_saat(h):
    """Hours left before a date -> a number the net can compare: 1 for 'now' falling to 0 at about two weeks, never below -1."""
    if h is None:
        return 0.0, 0.0
    return 1.0, max(-1.0, min(1.0, 1.0 - math.log1p(max(h, 0.0)) / math.log1p(24 * 14))) if h > 0 else 1.0


def _x(tip, *f):
    v = np.zeros(D)
    v[TIPLER.index(tip)] = 1.0
    for k, val in enumerate(f):
        v[len(TIPLER) + k] = val
    return v


def cizge(snap, oz):
    """(names, X, A, job index) of one snapshot."""
    ad, X, bag = [], [], []
    idx = {}

    def yeni(ad_, x):
        ad.append(ad_)
        X.append(x)
        return len(ad) - 1
    for i, e in oz["isler"].items():
        ok = e["sonuc"]
        idx[i] = yeni(("is", i), _x("is", float(e["durum"] == "Ended OK"), (sum(1 for r in ok if not r) / max(len(ok), 1)),
                                    min(e["kosu"], 20) / 20.0))
    for i, e in oz["isler"].items():
        j = idx[i]
        for mount, s in e["disk"].items():
            ys = s["kullanilan"]
            f1 = ys[-1] / s["toplam"]
            f2 = egim(ys) / s["toplam"] * 10.0 if len(ys) >= 4 else 0.0
            v = yeni(("vol", i, mount), _x("vol", f1, f2, len(ys) / 20.0))
            bag.append((j, v))
        for h in e["hesaplar"]:
            k = yeni(("rol", i, h["rol"]), _x("rol", *_log_saat(h["kalan_saat"])))
            bag.append((j, k))
        for h in e["anahtarlar"]:
            k = yeni(("key", i, h["hesap"]), _x("key", *_log_saat(h["kalan_saat"])))
            bag.append((j, k))
        ys = e["sure"]
        if e["timeout"] and len(ys) >= 4:
            med = statistics.median(ys)
            s = yeni(("sure", i), _x("sure", min(ys[-1] / e["timeout"], 1.5), egim(ys) / max(med, 0.5) * 3.0, min((ys[-1] - ys[0]) / max(med, 0.5), 2.0)))
            bag.append((j, s))
        if e["hatalar"] and len(e["sonuc"]) >= 4:
            son = [r for r in e["sonuc"][-12:]]
            fail = [k for k, r in enumerate(son) if not r]
            yar = len(son) // 2
            imza = len({h for _, h in e["hatalar"]})
            s = yeni(("imza", i), _x("imza", len(fail) / 12.0, sum(1 for k in fail if k >= yar) / max(len(fail), 1),
                                     float(e["sonuc"][-1]), 1.0 / imza))
            bag.append((j, s))
        for ad_, ys in e["sayac"].items():
            if len(ys) >= 4 and e["limit"]:
                q = yeni(("kuyruk", i, ad_), _x("kuyruk", ys[-1] / e["limit"], egim(ys) / e["limit"] * 10.0, len(ys) / 20.0))
                bag.append((j, q))
    for o in oz["oturumlar"]:
        s = yeni(("oturum", o["pid"]), _x("oturum", 1.0, min(o["xact_sn"], 3600) / 3600.0, min(len(o["isler"]), 3) / 3.0))
        for i in o["isler"]:
            bag.append((idx[i], s))
    # resources nobody uses: islands with their own features (so training sees them too)
    kullanilan_rol = {h["rol"] for e in oz["isler"].values() for h in e["hesaplar"]}
    for r in snap["roller"]:
        if r["rol"] not in kullanilan_rol:
            h = None if r["gecerlilik"] is None else (r["gecerlilik"] - snap["t"]) / 3600.0
            yeni(("rol", "-", r["rol"]), _x("rol", *_log_saat(h)))
    for h, rows in snap["diskler"].items():
        for r in rows:
            if r["mount"].startswith("/data/dar") and not any(r["mount"] in e["disk"] and e["host"] == h for e in oz["isler"].values()):
                yeni(("vol", h, r["mount"]), _x("vol", r["kullanilan_kb"] / r["toplam_kb"], 0.0, 0.0))
    n = len(ad)
    A = np.eye(n)
    for a, b in bag:
        A[a, b] = A[b, a] = 1.0
    d = A.sum(1)
    A = A / np.sqrt(d)[:, None] / np.sqrt(d)[None, :]
    return ad, np.array(X), A, idx


def _blok(parcalar):
    n = sum(len(p[1]) for p in parcalar)
    X = np.zeros((n, D))
    A = np.zeros((n, n))
    o = 0
    sat = []
    for ad, x, a, idx, y in parcalar:
        m = len(x)
        X[o:o + m], A[o:o + m, o:o + m] = x, a
        sat += [(o + j, y.get(i, 0)) for i, j in idx.items()]
        o += m
    return X, A, sat


class GrafAgi:
    def __init__(self, gizli=14, tohum=0, cop=30, tur=900, lr=0.03, l2=1e-3):
        self.gizli, self.tohum, self.cop, self.tur, self.lr, self.l2 = gizli, tohum, cop, tur, lr, l2
        self.W1 = self.W2 = None

    # ---- training ---------------------------------------------------------------
    def egit(self, ornekler):
        """`ornekler`: [(snap, oz, {job id: class index})]. Job nodes are the labelled rows."""
        rng = np.random.default_rng(self.tohum)
        parcalar = []
        for snap, oz, y in ornekler:
            ad, X, A, idx = cizge(snap, oz)
            parcalar.append((ad, X, A, idx, y))
        X0, A, sat = _blok(parcalar)
        rows = np.array([r for r, _ in sat])
        Y = np.zeros((len(sat), len(SINIF_ADLARI)))
        for k, (_, c) in enumerate(sat):
            Y[k, c] = 1.0
        agirlik = (Y / (Y.sum(0, keepdims=True) + 1e-9)).sum(1)       # every class weighs the same in total
        agirlik = agirlik / agirlik.sum()
        self.W1 = rng.normal(0, 0.3, (D, self.gizli))
        self.W2 = rng.normal(0, 0.3, (self.gizli, len(SINIF_ADLARI)))
        m1, v1, m2, v2 = (np.zeros_like(w) for w in (self.W1, self.W1, self.W2, self.W2))
        for t in range(1, self.tur + 1):
            # jittered copy of the features: each epoch sees a slightly different site
            X = X0 * (1 + rng.normal(0, 0.06, X0.shape)) + rng.normal(0, 0.02, X0.shape) * (X0 != 0)
            AX = A @ X
            Z1 = AX @ self.W1
            H1 = np.maximum(Z1, 0)
            AH = A @ H1
            L = AH @ self.W2
            P = np.exp(L - L.max(1, keepdims=True))
            P /= P.sum(1, keepdims=True)
            dL = np.zeros_like(L)
            dL[rows] = (P[rows] - Y) * agirlik[:, None]
            g2 = AH.T @ dL + self.l2 * self.W2
            dH1 = A @ dL @ self.W2.T
            dZ1 = dH1 * (Z1 > 0)
            g1 = AX.T @ dZ1 + self.l2 * self.W1
            for w, g, m, v in ((self.W1, g1, m1, v1), (self.W2, g2, m2, v2)):
                m *= 0.9
                m += 0.1 * g
                v *= 0.999
                v += 0.001 * g * g
                w -= self.lr * (m / (1 - 0.9 ** t)) / (np.sqrt(v / (1 - 0.999 ** t)) + 1e-8)
        return self

    # ---- prediction -------------------------------------------------------------
    def olasilik(self, snap, oz):
        ad, X, A, idx = cizge(snap, oz)
        H1 = np.maximum(A @ X @ self.W1, 0)
        L = A @ H1 @ self.W2
        P = np.exp(L - L.max(1, keepdims=True))
        P /= P.sum(1, keepdims=True)
        return {i: P[j] for i, j in idx.items()}

    def uyarilar(self, snap, oz, esik=0.5):
        out = []
        for i, p in self.olasilik(snap, oz).items():
            c = int(np.argmax(p))
            risk = 1.0 - float(p[0])
            if c != 0 and risk >= esik:
                out.append({"is": i, "sinif": SINIF_ADLARI[c], "ne_zaman": {"tur": "belirsiz"}, "p": round(risk, 3), "kaynak": "graf",
                            "neden": f"graf modeli: {i} icin {SINIF_ADLARI[c]} riski %{100 * risk:.0f} (komsu dugumlerin olcumlerinden)",
                            "kanit": {"sinif_olasiliklari": {SINIF_ADLARI[k]: round(float(p[k]), 3) for k in np.argsort(-p)[:3]}}})
        return out


def etiketle(gercek):
    """{job id: class index} of a site's truth."""
    return {r["is"]: SINIF_ADLARI.index(r["sinif"]) for r in gercek["riskler"]}
