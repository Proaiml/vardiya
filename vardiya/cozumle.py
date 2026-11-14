"""Reading the local error graph: what is wrong now, why, what fixed it before, and what is coming.

Same division of labour as the request desk. Code walks the graph and puts together the evidence for
one failure: its error signature and the times it was seen before, what other jobs failed that day and
which host, user, connection or table they share, which definition changed just before, which
predecessor did not finish. From that, code ranks the candidate causes. A model, if one is connected,
reads the evidence and picks one candidate and explains it; code checks that the pick is one of the
candidates it offered. Without a model the top candidate stands, marked as such.
"""
import datetime
import statistics

from .graph import signature, similarity

KIND_TR = {"host": "sunucu", "user": "kullanici", "connection": "baglanti profili", "table": "tablo",
           "change": "tanim degisikligi", "job": "is", "resource": "kaynak", "run": "calisma"}


def failures(g, day=None):
    """Failed runs, newest first, each with its signature and incident if one covers it."""
    covered = {}
    for inc in g.nodes("incident"):
        for e in g.out(inc["id"], "covers"):
            covered[e["to"]] = inc["id"]
    out = [dict(r, signature=signature(r["error"]), incident=covered.get(r["id"])) for r in g.runs()
           if not r["ok"] and r.get("error") and (day is None or r["day"] == day)]
    return sorted(out, key=lambda r: (r["day"], r["job"]), reverse=True)


def _incident(g, iid):
    inc = g.get(iid)
    res = g.out(iid, "resolved_by")
    root = g.out(iid, "root")
    return {"id": iid, "day": inc["day"], "cause": inc["cause"], "open": inc["open"], "minutes": inc.get("minutes"),
            "root": root[0]["to"] if root else None, "resolution": res[0]["to"].split(":", 1)[1] if res else None,
            "verified": bool(res and res[0].get("verified")),
            "jobs": sorted({g.get(e["to"])["job"] for e in g.out(iid, "covers")})}


def analyse(g, run_id, window=0):
    """Evidence and ranked candidate causes for one failed run."""
    run = g.get(run_id)
    job, day = run["job"], run["day"]
    sig = signature(run["error"])
    d0 = datetime.date.fromisoformat(day)
    near = {(d0 + datetime.timedelta(days=k)).isoformat() for k in range(-window, window + 1)}
    others = [f for f in failures(g) if f["day"] in near and f["id"] != run_id]

    # 1. what the failing jobs share
    mine = set(g.attrs(job))
    shared = {}
    for f in others:
        for a in set(g.attrs(f["job"])) & mine:
            shared.setdefault(a, set()).add(f["job"])
    users_of = {a: sorted({e["from"].split(":", 1)[1] for e in g.into(a) if e["from"].startswith("job:")}) for a in shared}

    # 2. the same error before: on this job and on others, with what was done and whether it held
    past = []
    for inc in g.nodes("incident"):
        info = _incident(g, inc["id"])
        if info["day"] >= day:
            continue
        sigs = [signature(g.get(e["to"])["error"]) for e in g.out(inc["id"], "covers") if g.get(e["to"]).get("error")]
        best = max((similarity(sig, s) for s in sigs), default=0)
        if best >= 0.6:
            past.append(dict(info, similarity=round(best, 2), same_job=job in info["jobs"]))
    past.sort(key=lambda p: p["day"], reverse=True)

    # 3. a change just before: to this job, or below it on its host (a patch, an upgrade)
    changes = [dict(g.get(e["from"])) for e in g.into(f"job:{job}", "changed")]
    for a in mine:
        if a.startswith("host:"):
            changes += [dict(g.get(e["from"])) for e in g.into(a, "changed")]
    recent = [c for c in changes if 0 <= (d0 - datetime.date.fromisoformat(c["day"])).days <= 3]

    # 4. predecessors that did not end OK that day, and how long this job usually takes
    preds = [e["to"].split(":", 1)[1] for e in g.out(f"job:{job}", "after")]
    pred_bad = [p for p in preds if any(f["job"] == p and f["day"] == day for f in others)]
    # a predecessor that failed and was marked OK by hand looks green; its missing data shows up here
    pred_setok = [r for p in preds for r in g.runs(p, since=day, until=day) if r.get("set_ok")]
    durations = [r["minutes"] for r in g.runs(job) if r["ok"] and r["day"] < day][-30:]

    # candidates, ranked by code
    cand = []
    for a, js in sorted(shared.items(), key=lambda kv: -len(kv[1])):
        share = (len(js) + 1) / max(1, len(users_of[a]))
        cand.append({"id": a, "kind": a.split(":", 1)[0], "score": 2 + 3 * len(js) * share,
                     "why": f"ayni gun {len(js) + 1} is ayni {KIND_TR.get(a.split(':')[0], '')} uzerinde hata verdi "
                            f"({', '.join(sorted(js | {job}))}); bu {KIND_TR.get(a.split(':')[0], '')} toplam "
                            f"{len(users_of[a])} iste kullaniliyor"})
    for c in recent:
        where = f"{c['host']} sunucusunda" if c.get("host") else "tanim"
        cand.append({"id": c["id"], "kind": "change", "score": 4.0 if not c.get("host") else 3.5,
                     "why": f"hatadan {(d0 - datetime.date.fromisoformat(c['day'])).days} gun once {where} degisiklik: "
                            f"{c['what']}"})
    for r in pred_setok:
        cand.append({"id": r["id"], "kind": "run", "score": 6.0,
                     "why": f"oncul {r['job']} ayni gun hata verdi ve elle basarili sayildi (Set OK): zincir yesil "
                            f"gorundu ama veri gelmedi. Oncul hatasi: {r.get('error')}"})
    for p in pred_bad:
        cand.append({"id": f"job:{p}", "kind": "job", "score": 3.0, "why": f"oncul is {p} ayni gun hata verdi"})
    for p in past[:3]:
        if p["root"] and p["root"] not in {c["id"] for c in cand}:
            cand.append({"id": p["root"], "kind": p["root"].split(":", 1)[0],
                         "score": 2.5 + (1.0 if p["same_job"] else 0) + (0.5 if p["verified"] else 0),
                         "why": f"ayni hata {p['day']} tarihinde {', '.join(p['jobs'])} isinde goruldu; kok neden "
                                f"{p['root']} idi"})
    text = str(run["error"]).lower()
    have = {c["id"] for c in cand}
    for a in sorted(mine - have):  # the error line itself names a table, host or user of this job
        if a.split(":", 1)[1].lower() in text:
            co = sorted(e["from"].split(":", 1)[1] for e in g.into(a) if e["from"].startswith("job:")
                        and e["from"] != f"job:{job}")
            cand.append({"id": a, "kind": a.split(":", 1)[0], "score": 3.0,
                         "why": f"hata satiri {KIND_TR.get(a.split(':')[0], '')} {a.split(':', 1)[1]} adini veriyor"
                                + (f"; ayni {KIND_TR.get(a.split(':')[0], '')} su islerce de kullaniliyor: "
                                   f"{', '.join(co)}" if co else "")})
            have.add(a)
    known = catalog_match(sig)
    if not cand and known:  # nothing on the graph points elsewhere: the known kind of this error says where
        where = "dis:kaynak-sistem" if known["kind"] == "dosya" else f"job:{job}"
        cand.append({"id": where, "kind": where.split(":", 1)[0], "score": 2.0,
                     "why": f"bilinen hata turu: {known['cause']}"})
    for c in cand:  # a candidate the past already pointed at, or the error line names, gains weight
        c["precedents"] = sum(1 for p in past if p["root"] == c["id"])
        named = c["id"].split(":", 1)[1].lower() in text and "adini veriyor" not in c["why"]
        c["score"] = round(c["score"] + 1.5 * c["precedents"] + (1.5 if named else 0), 2)
        if named:
            c["why"] += "; hata satiri da bunu adiyla soyluyor"
    cand.sort(key=lambda c: (-c["score"], c["id"]))

    repeated_fix = [p for p in past if p["root"] and not p["verified"]]
    # one incident per cause: an open incident for the same job and the same error is extended, not duplicated
    existing = None
    for inc in g.nodes("incident"):
        info = _incident(g, inc["id"])
        if info["open"] and job in info["jobs"] and run_id not in {e["to"] for e in g.out(inc["id"], "covers")}:
            sigs = [signature(g.get(e["to"]).get("error")) for e in g.out(inc["id"], "covers")]
            if sig in sigs:
                existing = info["id"]
    return {
        "run": run_id, "job": job, "day": day, "error": run["error"], "signature": sig,
        "same_window": [{"job": f["job"], "day": f["day"], "error": f["error"]} for f in others],
        "shared": {a: sorted(js) for a, js in shared.items()}, "precedents": past[:6], "changes": recent,
        "predecessors_failed": pred_bad,
        "duration": {"median": round(statistics.median(durations), 1) if durations else None, "last": run["minutes"]},
        "candidates": cand[:5], "known": known, "existing_incident": existing,
        "predecessor_set_ok": [r["id"] for r in pred_setok],
        "lesson": (f"Bu hata daha once {len(repeated_fix)} kez '{repeated_fix[0]['resolution']}' ile kapatilmis ve "
                   "tekrar etmis: o cozum kok nedeni gidermiyor." if len(repeated_fix) >= 2 else None),
    }


def suggest(g, ev, chosen=None):
    """What to do, from what fixed the same root before. Code only: a verified past fix is preferred.
    `chosen`: the candidate a model picked; by default code's first."""
    top = {"id": chosen} if chosen else (ev["candidates"][0] if ev["candidates"] else {"id": None})
    fixes = [p for p in ev["precedents"] if p["root"] == top["id"] and p["resolution"]]
    good = [p for p in fixes if p["verified"]]
    if good:
        return {"action": good[0]["resolution"], "from": good[0]["id"], "verified": True}
    known = ev.get("known") or catalog_match(ev["signature"])
    if known:
        return {"action": known["fix"], "from": "katalog", "cause": known["cause"], "verified": False}
    return {"action": fixes[0]["resolution"], "from": fixes[0]["id"], "verified": False} if fixes else None


def catalog_match(sig):
    """The known failure kind (docs/06, section 7) of a signature: by its signs (SIGNS, any product's wording),
    then by likeness to the catalog's own line."""
    from .gecmis import CATALOG, SIGNS
    fill = dict(table="T", user="U", host="H", rows=0, expected=1, path="/p", minutes=1, proc="p", resource="R")
    scored = []
    for kind, (line, cause, fix) in CATALOG.items():
        hits = sum(1 for w in SIGNS.get(kind, ()) if w in sig)
        sim = similarity(sig, signature(line.format(**fill)))
        scored.append((hits + sim, hits, sim, kind, cause, fix))
    best = max(scored, default=(0, 0, 0, None, None, None))
    return {"kind": best[3], "cause": best[4], "fix": best[5]} if best[1] >= 1 or best[2] >= 0.5 else None


def explain(model, ev):
    """The model reads the evidence and picks one of code's candidates. Code holds it to that list."""
    if model is None or not ev["candidates"]:
        return None
    ids = [c["id"] for c in ev["candidates"]]
    lines = [f"Failed job {ev['job']} on {ev['day']}: {ev['error']}",
             f"Usual duration {ev['duration']['median']} min, this run {ev['duration']['last']} min."]
    lines += [f"Same day: {x['job']} failed with: {x['error']}" for x in ev["same_window"][:6]]
    lines += [f"Earlier: {p['day']} {', '.join(p['jobs'])}, root {p['root']}, fixed by '{p['resolution']}', "
              f"{'held' if p['verified'] else 'came back'}" for p in ev["precedents"][:4]]
    lines += [f"Change before: {c['day']} {c['what']}" for c in ev["changes"]]
    lines += [f"Candidate {c['id']}: {c['why']}" for c in ev["candidates"]]
    out = model.ask_json([
        {"role": "system", "content": "You are an experienced batch scheduler administrator."},
        {"role": "user", "content": "\n".join(lines) + (
            "\n\nWhich candidate is the root cause? Answer in Turkish. Reply with ONE JSON object: "
            '{"candidate": "<one of: ' + ", ".join(ids) + '>", "explanation": "<two sentences>", '
            '"next_step": "<one concrete action>"}')}])
    if not isinstance(out, dict) or out.get("candidate") not in ids:
        return {"candidate": None, "explanation": None, "rejected": True}
    return {"candidate": out["candidate"], "explanation": str(out.get("explanation") or "")[:600],
            "next_step": str(out.get("next_step") or "")[:300], "rejected": False}


def disk_outlook(series, days=14, full=95.0):
    """Days until `full` percent at the recent pace (Theil-Sen over the last `days` points), or None."""
    ys = [v for _, v in series[-days:]]
    if len(ys) < 5:
        return None
    slope = theil_sen(ys)
    if slope <= 0.05 or ys[-1] >= full:
        return None
    return {"now": ys[-1], "per_day": round(slope, 2), "days": int((full - ys[-1]) / slope)}


def reports(g, today, days=7):
    """What an admin is asked for every week, read from the graph: recent changes, Set OK runs, failures per job
    and month, the slowest and the most time-consuming jobs."""
    t0 = datetime.date.fromisoformat(today)
    since = (t0 - datetime.timedelta(days=days)).isoformat()
    changes = sorted((c for c in g.nodes("change") if c["day"] >= since), key=lambda c: c["day"], reverse=True)
    set_ok = [r for r in g.runs() if r.get("set_ok")]
    monthly = {}
    for f in failures(g):
        monthly.setdefault(f["job"], {}).setdefault(f["day"][:7], 0)
        monthly[f["job"]][f["day"][:7]] += 1
    stats = []
    for j in g.nodes("job"):
        name = j["id"].split(":", 1)[1]
        rs = [r for r in g.runs(name, since=(t0 - datetime.timedelta(days=30)).isoformat()) if r["ok"]]
        if rs:
            ms = sorted(r["minutes"] for r in rs)
            stats.append({"job": name, "runs": len(rs), "median": round(statistics.median(ms), 1),
                          "p90": ms[int(0.9 * (len(ms) - 1))], "total": round(sum(ms), 0)})
    return {"since": since, "changes": changes,
            "set_ok": [{"id": r["id"], "job": r["job"], "day": r["day"], "error": r.get("error"),
                        "downstream": sorted({f["job"] for f in failures(g, r["day"])
                                              if f"job:{r['job']}" in {e["to"] for e in g.out(f"job:{f['job']}", "after")}})}
                       for r in set_ok],
            "failures_by_month": monthly,
            "slowest": sorted(stats, key=lambda s: -s["median"])[:6],
            "heaviest": sorted(stats, key=lambda s: -s["total"])[:6]}


def theil_sen(ys):
    pairs = [(ys[j] - ys[i]) / (j - i) for i in range(len(ys)) for j in range(i + 1, len(ys))]
    return statistics.median(pairs) if pairs else 0.0


def warnings(g, today, horizon=7):
    """What is likely to go wrong soon, from the past. Each warning carries its evidence."""
    out = []
    t0 = datetime.date.fromisoformat(today)
    for j in g.nodes("job"):
        name = j["id"].split(":", 1)[1]
        runs = [r for r in g.runs(name) if r["ok"] and r["attempt"] == 1][-30:]
        if len(runs) >= 15:
            ys = [r["minutes"] for r in runs]
            slope, med = theil_sen(ys), statistics.median(ys[:10])
            if med and slope * len(ys) > 0.25 * med:
                out.append({"kind": "yavaslama", "job": name, "level": "uyari",
                            "text": f"{name} yavasliyor: son {len(ys)} calismada sure {med:.1f} dk'dan "
                                    f"{ys[-1]:.1f} dk'ya cikti (egilim her calismada +{slope:.2f} dk)",
                            "series": [round(y, 1) for y in ys]})
    by_sig = {}
    for f in failures(g):
        by_sig.setdefault((f["job"], f["signature"]), []).append(f["day"])
    for (job, sig), days in by_sig.items():
        wd = [datetime.date.fromisoformat(d).weekday() for d in days]
        common = max(set(wd), key=wd.count)
        if wd.count(common) >= 3:
            nxt = t0 + datetime.timedelta(days=(common - t0.weekday()) % 7 or 7)
            if (nxt - t0).days <= horizon:
                out.append({"kind": "tekrar", "job": job, "level": "risk",
                            "text": f"{job} ayni hatayi {wd.count(common)} kez "
                                    f"{['pazartesi', 'sali', 'carsamba', 'persembe', 'cuma', 'cumartesi', 'pazar'][common]}"
                                    f" gunu verdi; sonraki: {nxt.isoformat()}",
                            "days": sorted(days)})
    for inc in g.nodes("incident"):
        info = _incident(g, inc["id"])
        if info["open"]:
            continue
    for h in g.nodes("host"):
        o = disk_outlook(h.get("disk") or [])
        if o and o["days"] <= 21:
            name = h["id"].split(":", 1)[1]
            jobs = sorted(e["from"].split(":", 1)[1] for e in g.into(h["id"], "on") if e["from"].startswith("job:"))
            out.append({"kind": "disk", "job": name, "level": "risk" if o["days"] <= 7 else "uyari",
                        "text": f"{name} diski %{o['now']:.0f} dolu ve gunde %{o['per_day']} artiyor; bu hizla "
                                f"{o['days']} gun icinde %95'i gecer. Bu sunucuda calisan isler: {', '.join(jobs)}. "
                                "Ilk bakilacak: agent'in kendi loglari ve eski ciktilar",
                        "series": [v for _, v in (h.get("disk") or [])[-30:]]})
    for r in g.runs(since=(t0 - datetime.timedelta(days=30)).isoformat()):
        if r.get("set_ok"):
            out.append({"kind": "setok", "job": r["job"], "level": "uyari",
                        "text": f"{r['job']} {r['day']} tarihinde hata verdi ve elle basarili sayildi (Set OK). Aşağı "
                                "akistaki isler yesil gorunse de veri eksik olabilir; kok neden kapatilmadi"})
    roots = {}
    for inc in g.nodes("incident"):
        info = _incident(g, inc["id"])
        if info["root"]:
            roots.setdefault(info["root"], []).append(info)
    for root, incs in roots.items():
        unverified = [i for i in incs if not i["verified"] and not i["open"]]
        if len(unverified) >= 2:
            out.append({"kind": "kalici", "job": ", ".join(sorted({j for i in incs for j in i["jobs"]})), "level": "risk",
                        "text": f"{root} kaynakli hata {len(incs)} kez yasandi; {len(unverified)} kez kok neden "
                                f"giderilmeden kapatildi ('{unverified[0]['resolution']}')"})
    order = {"risk": 0, "uyari": 1}
    return sorted(out, key=lambda w: (order[w["level"]], w["job"]))
