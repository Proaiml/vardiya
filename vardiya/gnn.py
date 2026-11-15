"""Graph model for a fast first guess: the incident class (root cause) and the skills to start with.

A simplified graph convolution (SGC, Wu et al. 2019) over one graph that holds the cases, their words, the incident
classes and every skill. A case is linked to the words of its report; a class is linked to the words of its signs,
title and cause; a skill (general skill, admin procedure) to the words of its title and triggers. Features are
propagated K hops over the normalised adjacency, then a softmax layer is trained on the development cases only.
An unseen report thus reaches classes and skills through the words it shares with them and with solved cases.

Labels: the incident class of every development case, and, once solution chains are mined, the skills a correct
solver used (multi-label). The test splits are never used for training; their text may sit in the graph as
unlabelled nodes (transductive), their labels are only read to score.

Needs numpy; runs on the CPU with at most two threads.

    python -m vardiya.gnn eval --split test
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

import argparse  # noqa: E402
import collections  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import pathlib  # noqa: E402
import re  # noqa: E402

import numpy as np  # noqa: E402

from .graph import mark_signals  # noqa: E402
from .skills import fold, load_chains, load_general_skills, load_incident_classes, load_procedures  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
STOP = set("""bir ile icin veya olarak gibi sonra once daha kadar gore olan ama fakat ancak hem cok var yok nasil neden
mi mu bu su o ve de da ki ne the and for with from that this then when what how why are was were have has not but
our we is it to of in on at be as an or by if do does did job jobs isi isler is isin bizim""".split())
TOKEN = re.compile(r"[a-z0-9_][a-z0-9_.:-]{2,}")


def tokens(text):
    out = []
    for w in TOKEN.findall(fold(mark_signals(str(text)))):
        w = w.strip(".:-")
        if len(w) < 3 or w in STOP:
            continue
        out.append(w)
        if len(w) > 6 and not any(ch.isdigit() for ch in w):
            out.append(w[:6] + "~")  # a crude stem so Turkish suffixes meet: kilitli, kilidi -> kilitl~
    return out


class GraphModel:
    # chosen by 5-fold cross-validation on the development split only (top-3 class accuracy: the model hands the
    # language model a short list): class and skill nodes weigh 20 training cases, classes are balanced, no bias
    def __init__(self, hops=2, l2=1e-4, epochs=600, lr=20.0, node_weight=20.0):
        self.hops, self.l2, self.epochs, self.lr, self.node_weight = hops, l2, epochs, lr, node_weight

    def build(self, cases, classes, procedures, general):
        """Nodes: cases, classes, skills, words. Returns the propagated feature row of every case."""
        docs, self.kind = [], []
        for c in cases:
            docs.append(tokens(c["prompt"])); self.kind.append(("case", c["id"]))
        for n, c in classes.items():
            docs.append(tokens(" ".join([c["title"], c["cause"]] + c["signs"]))); self.kind.append(("sinif", n))
        for n, p in procedures.items():
            docs.append(tokens(" ".join([p["title"]] + p["triggers"]))); self.kind.append(("yordam", n))
        for n, g in general.items():
            docs.append(tokens(" ".join([g["title"]] + g["triggers"]))); self.kind.append(("genel", n))
        df = collections.Counter(w for d in docs for w in set(d))
        self.vocab = {w: i for i, w in enumerate(sorted(w for w, c in df.items() if c >= 1))}
        n_doc, n_w = len(docs), len(self.vocab)
        idf = np.array([math.log((1 + n_doc) / (1 + df[w])) + 1 for w in sorted(self.vocab, key=self.vocab.get)])
        # doc-word matrix (tf-idf), then the bipartite adjacency [[0, B], [B^T, 0]] + I, symmetric normalised
        B = np.zeros((n_doc, n_w))
        for i, d in enumerate(docs):
            for w, c in collections.Counter(d).items():
                B[i, self.vocab[w]] = (1 + math.log(c)) * idf[self.vocab[w]]
        self.B, self.n_doc = B, n_doc  # kept for the trainable GCN (vardiya/gnn_torch.py)
        # A + I = [[I, B], [B^T, I]], symmetric normalised into blocks; the word-word block is never formed
        # (it would be vocab x vocab): two hops for the documents expand to doc-sized products only.
        dd, dw = B.sum(1) + 1, B.sum(0) + 1
        Bn = B / np.sqrt(dd)[:, None] / np.sqrt(dw)[None, :]
        Sd, Sw = 1 / dd, 1 / dw
        # features: a document is its tf-idf row, a word is itself (identity)
        Hd = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-9)
        # hop 1: Hd1 = Sd*Hd + Bn*I ; Hw1 = Bn^T Hd + Sw*I
        # hop 2: Hd2 = Sd*Hd1 + Bn Hw1 = Sd*Hd1 + (Bn Bn^T) Hd + Bn*Sw
        Hd1 = Sd[:, None] * Hd + Bn
        H = Sd[:, None] * Hd1 + (Bn @ Bn.T) @ Hd + Bn * Sw[None, :] if self.hops >= 2 else Hd1
        self.H = H / (np.linalg.norm(H, axis=1, keepdims=True) + 1e-9)
        self.row = {k: i for i, k in enumerate(self.kind)}
        return self

    def _fit(self, rows, Y, multi, n_cases):
        """Weighted logistic layer: every label weighs the same in total (balanced), knowledge-base nodes (rows after
        the first n_cases) weigh node_weight cases."""
        X = self.H[rows]
        per_label = Y.sum(0) + 1e-9
        w = (Y / per_label).sum(1) if not multi else np.ones(len(rows))
        w[n_cases:] *= self.node_weight
        w = w / w.sum()
        W = np.zeros((X.shape[1], Y.shape[1]))
        for _ in range(self.epochs):
            Z = X @ W
            if multi:
                P = 1 / (1 + np.exp(-Z))
            else:
                Z -= Z.max(1, keepdims=True)
                P = np.exp(Z); P /= P.sum(1, keepdims=True)
            W -= self.lr * (X.T @ ((P - Y) * w[:, None]) + self.l2 * W)
        return W, np.zeros(Y.shape[1])

    def fit(self, train_cases, chains_by_case=None):
        """Class (softmax) from every training case; skills (sigmoid, multi-label) from the cases that have a mined
        chain. The class and skill nodes themselves are training rows too: a class node is labelled with its class."""
        cls_rows, cls_y = [], []
        for c in train_cases:
            cls_rows.append(self.row[("case", c["id"])]); cls_y.append(c["class"])
        for kind, name in self.kind:
            if kind == "sinif":
                cls_rows.append(self.row[(kind, name)]); cls_y.append(name)
        self.classes = sorted(set(cls_y))
        Y = np.zeros((len(cls_rows), len(self.classes)))
        for i, y in enumerate(cls_y):
            Y[i, self.classes.index(y)] = 1
        self.Wc, self.bc = self._fit(cls_rows, Y, multi=False, n_cases=len(train_cases))
        self.skills = []
        if chains_by_case:
            sk_rows, sk_y = [], []
            for c in train_cases:
                refs = chains_by_case.get(c["id"])
                if refs:
                    sk_rows.append(self.row[("case", c["id"])]); sk_y.append(refs)
            n_sk = len(sk_rows)
            for kind, name in self.kind:
                if kind in ("yordam", "genel"):
                    sk_rows.append(self.row[(kind, name)]); sk_y.append([f"{kind}:{name}"])
            self.skills = sorted({r for refs in sk_y for r in refs})
            Y = np.zeros((len(sk_rows), len(self.skills)))
            for i, refs in enumerate(sk_y):
                for r in refs:
                    Y[i, self.skills.index(r)] = 1
            self.Ws, self.bs = self._fit(sk_rows, Y, multi=True, n_cases=n_sk)
        return self

    def predict(self, case_id, k=3):
        """{"class": [(class, p), ...top k], "skills": [(ref, p), ...top k]} for one case already in the graph."""
        x = self.H[self.row[("case", case_id)]]
        z = x @ self.Wc + self.bc
        p = np.exp(z - z.max()); p /= p.sum()
        out = {"class": [(self.classes[i], round(float(p[i]), 3)) for i in np.argsort(-p)[:k]], "skills": []}
        if self.skills:
            s = 1 / (1 + np.exp(-(x @ self.Ws + self.bs)))
            out["skills"] = [(self.skills[i], round(float(s[i]), 3)) for i in np.argsort(-s)[:k]]
        return out


def chains_by_case(path):
    """{case id: [skill refs of its correct solution]} from a mining run's per-case file, when there is one."""
    p = pathlib.Path(path)
    if not p.exists():
        return {}
    return {r["id"]: r["chain"] for r in map(json.loads, p.read_text(encoding="utf-8").splitlines()) if r.get("chain")}


def train(eval_split=None, case_chains=ROOT / "results" / "zincir-vakalar.jsonl"):
    from .opsbench import load
    classes, procedures, general = load_incident_classes(SKILLS), load_procedures(SKILLS), load_general_skills(SKILLS)
    dev = load("dev")
    others = load(eval_split) if eval_split else []
    m = GraphModel().build(dev + others, classes, procedures, general)
    return m.fit(dev, chains_by_case(case_chains)), others


def evaluate(split):
    from .opsbench import load, match_class
    m, cases = train(split)
    classes = load_incident_classes(SKILLS)
    top1 = top3 = rule = 0
    for c in cases:
        pred = [k for k, _ in m.predict(c["id"])["class"]]
        top1 += pred[0] == c["class"]
        top3 += c["class"] in pred
        rule += match_class(classes, c["prompt"]) == c["class"]
    n = len(cases)
    return {"vaka": n, "gnn_top1": round(top1 / n, 3), "gnn_top3": round(top3 / n, 3), "kural_top1": round(rule / n, 3)}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vardiya.gnn")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eval")
    e.add_argument("--split", default="test")
    a = ap.parse_args(argv)
    print(json.dumps(evaluate(a.split), ensure_ascii=False))


if __name__ == "__main__":
    main()
