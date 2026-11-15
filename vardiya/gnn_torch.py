"""A trainable two-layer GCN (Kipf and Welling 2017) on the same graph as vardiya/gnn.py, in PyTorch.

Nodes: cases, incident classes, skills and words; edges: a document (case, class or skill text) to its words,
weighted by tf-idf, plus self loops, symmetric normalised. Input: a document is its tf-idf row, a word is itself.
Hidden layer, ReLU and dropout, then a second propagation into class logits. Trained on the development cases and
the class nodes only (class nodes weigh `node_weight` cases, classes balanced).

CPU only, at most two threads: the GPU belongs to another job on this machine. CUDA is hidden before torch loads.

    py -3.11 -m vardiya.gnn_torch cv          # 5-fold cross-validation on the development split
    py -3.11 -m vardiya.gnn_torch eval --split test

Result (15 Nov 2026, development split, 5-fold CV, same folds as the SGC): best GCN (hidden 32, dropout 0.5, node
weight 20) top-1 0.631, top-3 0.816; the SGC in vardiya/gnn.py top-1 0.615, top-3 0.832. Top-3 was fixed as the
criterion beforehand, so the harness keeps the SGC; with ~180 labelled cases a deeper model does not pay off yet.
The GCN was not run on any test split.
"""
import os

os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ.setdefault("OMP_NUM_THREADS", "2")

import argparse  # noqa: E402
import json  # noqa: E402
import random  # noqa: E402

import numpy as np  # noqa: E402
import torch  # noqa: E402

from . import gnn  # noqa: E402
from .skills import load_general_skills, load_incident_classes, load_procedures  # noqa: E402

torch.set_num_threads(2)


def _sparse(m):
    m = m.tocoo() if hasattr(m, "tocoo") else m
    idx = np.vstack(np.nonzero(m))
    return torch.sparse_coo_tensor(torch.tensor(idx), torch.tensor(m[idx[0], idx[1]], dtype=torch.float32),
                                   m.shape).coalesce()


class GCN:
    def __init__(self, hidden=64, dropout=0.5, epochs=200, lr=0.01, weight_decay=5e-4, node_weight=20.0, seed=0):
        self.hidden, self.dropout, self.epochs, self.lr = hidden, dropout, epochs, lr
        self.wd, self.node_weight, self.seed = weight_decay, node_weight, seed

    def build(self, cases, classes, procedures, general):
        g = gnn.GraphModel().build(cases, classes, procedures, general)
        self.kind, self.row = g.kind, g.row
        B, n_doc = g.B, g.n_doc
        n_w = B.shape[1]
        n = n_doc + n_w
        # sparse A + I with tf-idf weights, normalised D^-1/2 (A + I) D^-1/2
        r, c = np.nonzero(B)
        v = B[r, c]
        rows = np.concatenate([r, c + n_doc, np.arange(n)])
        cols = np.concatenate([c + n_doc, r, np.arange(n)])
        vals = np.concatenate([v, v, np.ones(n)])
        deg = np.bincount(rows, weights=vals, minlength=n)
        vals = vals / np.sqrt(deg[rows]) / np.sqrt(deg[cols])
        self.A = torch.sparse_coo_tensor(torch.tensor(np.vstack([rows, cols])), torch.tensor(vals, dtype=torch.float32),
                                         (n, n)).coalesce()
        # features: documents = normalised tf-idf rows, words = identity
        Bn = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-9)
        dr, dc = np.nonzero(Bn)
        frows = np.concatenate([dr, np.arange(n_w) + n_doc])
        fcols = np.concatenate([dc, np.arange(n_w)])
        fvals = np.concatenate([Bn[dr, dc], np.ones(n_w)])
        self.X = torch.sparse_coo_tensor(torch.tensor(np.vstack([frows, fcols])), torch.tensor(fvals, dtype=torch.float32),
                                         (n, n_w)).coalesce()
        self.n_feat = n_w
        return self

    def _forward(self, train):
        h = torch.sparse.mm(self.A, torch.sparse.mm(self.X, self.W1))
        h = torch.relu(h)
        h = torch.nn.functional.dropout(h, self.dropout, training=train)
        return torch.sparse.mm(self.A, h @ self.W2)

    def fit(self, train_cases):
        torch.manual_seed(self.seed)
        rows, ys = [], []
        for c in train_cases:
            rows.append(self.row[("case", c["id"])]); ys.append(c["class"])
        n_cases = len(rows)
        for kind, name in self.kind:
            if kind == "sinif":
                rows.append(self.row[(kind, name)]); ys.append(name)
        self.classes = sorted(set(ys))
        y = torch.tensor([self.classes.index(v) for v in ys])
        count = torch.bincount(y, minlength=len(self.classes)).float()
        w = 1.0 / count[y]
        w[n_cases:] *= self.node_weight
        w = w / w.sum()
        self.W1 = torch.nn.Parameter(torch.empty(self.n_feat, self.hidden))
        self.W2 = torch.nn.Parameter(torch.empty(self.hidden, len(self.classes)))
        torch.nn.init.xavier_uniform_(self.W1)
        torch.nn.init.xavier_uniform_(self.W2)
        opt = torch.optim.Adam([self.W1, self.W2], lr=self.lr, weight_decay=self.wd)
        idx = torch.tensor(rows)
        for _ in range(self.epochs):
            opt.zero_grad()
            logits = self._forward(True)[idx]
            loss = (torch.nn.functional.cross_entropy(logits, y, reduction="none") * w).sum()
            loss.backward()
            opt.step()
        with torch.no_grad():
            self.P = torch.softmax(self._forward(False), dim=1)
        return self

    def predict(self, case_id, k=3):
        p = self.P[self.row[("case", case_id)]]
        top = torch.argsort(p, descending=True)[:k]
        return {"class": [(self.classes[int(i)], round(float(p[i]), 3)) for i in top], "skills": []}


def _load():
    from .opsbench import load
    S = gnn.SKILLS
    return load, load_incident_classes(S), load_procedures(S), load_general_skills(S)


def cv(configs, folds=5):
    """Top-1 and top-3 class accuracy by k-fold cross-validation on the development split. All dev cases sit in the
    graph (transductive); only the training folds' labels are used."""
    load, C, P, G = _load()
    dev = load("dev")
    idx = list(range(len(dev)))
    random.Random(0).shuffle(idx)
    parts = [idx[i::folds] for i in range(folds)]
    out = []
    for cfg in configs:
        base = GCN(**cfg).build(dev, C, P, G)
        t1 = t3 = 0
        for f in parts:
            test_ids = set(f)
            m = base
            m.fit([dev[i] for i in idx if i not in test_ids])
            for i in f:
                pred = [k for k, _ in m.predict(dev[i]["id"])["class"]]
                t1 += pred[0] == dev[i]["class"]
                t3 += dev[i]["class"] in pred
        out.append({**cfg, "top1": round(t1 / len(dev), 3), "top3": round(t3 / len(dev), 3)})
    return out


def evaluate(split, cfg):
    load, C, P, G = _load()
    from .opsbench import match_class
    dev, cases = load("dev"), load(split)
    m = GCN(**cfg).build(dev + cases, C, P, G).fit(dev)
    t1 = t3 = rule = 0
    for c in cases:
        pred = [k for k, _ in m.predict(c["id"])["class"]]
        t1 += pred[0] == c["class"]
        t3 += c["class"] in pred
        rule += match_class(C, c["prompt"]) == c["class"]
    n = len(cases)
    return {"vaka": n, "gcn_top1": round(t1 / n, 3), "gcn_top3": round(t3 / n, 3), "kural_top1": round(rule / n, 3)}


GRID = [{"hidden": h, "dropout": d, "node_weight": w} for h in (32, 64) for d in (0.3, 0.5) for w in (5.0, 20.0)]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="vardiya.gnn_torch")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("cv")
    e = sub.add_parser("eval")
    e.add_argument("--split", default="test")
    e.add_argument("--config", default="{}")
    a = ap.parse_args(argv)
    if a.cmd == "cv":
        for r in cv(GRID):
            print(json.dumps(r))
    else:
        print(json.dumps(evaluate(a.split, json.loads(a.config))))


if __name__ == "__main__":
    main()
